"""AIP TUI: Status dashboard, interactive REPL, and session management.

Uses Rich for formatted terminal output. Not a full-screen TUI --
just a status bar and a REPL loop with slash commands.
Uses prompt_toolkit for autocomplete with descriptions (optional).
Sessions persist config, stats, history, and context across REPL invocations.
"""

# pyright: reportPossiblyUnboundVariable=false
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

HAS_PROMPT_TOOLKIT = False
try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory

    HAS_PROMPT_TOOLKIT = True
except ImportError:
    pass

if TYPE_CHECKING:
    from ai_pipeline import PipelineConfig

logger = logging.getLogger("ai_pipeline.tui")

console = Console()

SESSIONS_DIR = ".pipeline/sessions"
MAX_CONTEXT_ENTRIES = 20
MAX_SUMMARY_CHARS = 500


# ---------------------------------------------------------------------------
# Session stats (token estimation)
# ---------------------------------------------------------------------------


@dataclass
class SessionStats:
    """Track estimated token usage and timing per session."""

    claude_tokens: int = 0
    codex_tokens: int = 0
    runs_ok: int = 0
    runs_error: int = 0
    start_time: float = field(default_factory=time.monotonic)
    elapsed_seconds: float = 0.0
    last_summary: str = ""

    def add_tokens(self, provider: str, chars: int) -> None:
        """Estimate tokens from character count (chars / 4)."""
        estimated = max(chars // 4, 1)
        if provider == "claude":
            self.claude_tokens += estimated
        elif provider == "codex":
            self.codex_tokens += estimated

    def record_run(self, *, success: bool) -> None:
        """Record a run outcome."""
        if success:
            self.runs_ok += 1
        else:
            self.runs_error += 1

    @property
    def elapsed(self) -> str:
        """Human-readable elapsed time (current session + previous)."""
        current = time.monotonic() - self.start_time
        total = int(self.elapsed_seconds + current)
        mins, secs = divmod(total, 60)
        return f"{mins}m {secs:02d}s"

    def snapshot_elapsed(self) -> None:
        """Snapshot current elapsed into persistent counter (called on save)."""
        self.elapsed_seconds += time.monotonic() - self.start_time
        self.start_time = time.monotonic()

    def format_tokens(self, value: int) -> str:
        """Format token count with K suffix."""
        if value >= 1000:
            return f"~{value / 1000:.1f}k"
        return str(value)


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


@dataclass
class ContextEntry:
    """A single task+response recorded in session context."""

    task: str
    mode: str
    summary: str
    timestamp: str = ""


@dataclass
class SessionData:
    """Serializable session state."""

    session_id: str = ""
    name: str = ""
    created_at: str = ""
    updated_at: str = ""
    config_state: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    context: list[dict[str, str]] = field(default_factory=list)


class SessionManager:
    """Manage session persistence in SESSIONS_DIR."""

    def __init__(self, project: Path) -> None:
        self.sessions_dir = project / SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _history_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.history"

    def save(
        self,
        session_id: str,
        name: str,
        state: REPLState,
        config: PipelineConfig,
        context: list[ContextEntry],
    ) -> Path:
        """Save session to disk. Returns path to saved file."""
        state.stats.snapshot_elapsed()

        data = SessionData(
            session_id=session_id,
            name=name,
            created_at=state.created_at,
            updated_at=datetime.now(tz=timezone.utc).isoformat(),
            config_state={
                "mode": state.mode,
                "preset": state.preset,
                "claude_ask_model": config.claude_ask_model,
                "claude_chat_model": config.claude_chat_model,
                "claude_plan_model": config.claude_plan_model,
                "claude_review_model": config.claude_review_model,
                "codex_model": config.codex_model,
                "thinking_budget": config.thinking_budget,
            },
            stats={
                "claude_tokens": state.stats.claude_tokens,
                "codex_tokens": state.stats.codex_tokens,
                "runs_ok": state.stats.runs_ok,
                "runs_error": state.stats.runs_error,
                "elapsed_seconds": state.stats.elapsed_seconds,
            },
            context=[asdict(e) for e in context[-MAX_CONTEXT_ENTRIES:]],
        )

        path = self._session_path(session_id)
        path.write_text(json.dumps(asdict(data), indent=2), encoding="utf-8")
        logger.debug("Session saved: %s", path)
        return path

    def load(self, session_id: str) -> SessionData | None:
        """Load a session from disk."""
        path = self._session_path(session_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return SessionData(**raw)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to load session %s: %s", session_id, exc)
            return None

    def list_sessions(self) -> list[SessionData]:
        """List all saved sessions, most recent first."""
        sessions = []
        for p in sorted(
            self.sessions_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        ):
            data = self.load(p.stem)
            if data:
                sessions.append(data)
        return sessions

    def find_by_name(self, name: str) -> SessionData | None:
        """Find a session by name (case-insensitive)."""
        for session in self.list_sessions():
            if session.name.lower() == name.lower():
                return session
        return None

    def find_by_id_or_name(self, identifier: str) -> SessionData | None:
        """Find session by ID prefix or name."""
        # Try exact ID first
        data = self.load(identifier)
        if data:
            return data
        # Try name
        by_name = self.find_by_name(identifier)
        if by_name:
            return by_name
        # Try ID prefix
        for session in self.list_sessions():
            if session.session_id.startswith(identifier):
                return session
        return None

    def delete(self, session_id: str) -> bool:
        """Delete a session and its history file."""
        path = self._session_path(session_id)
        hist = self._history_path(session_id)
        deleted = False
        if path.exists():
            path.unlink()
            deleted = True
        if hist.exists():
            hist.unlink()
        return deleted

    def latest(self) -> SessionData | None:
        """Get the most recently updated session."""
        sessions = self.list_sessions()
        return sessions[0] if sessions else None

    def get_history_path(self, session_id: str) -> Path:
        """Get the FileHistory path for a session."""
        return self._history_path(session_id)


# ---------------------------------------------------------------------------
# Status bar
# ---------------------------------------------------------------------------


def render_status_bar(
    mode: str,
    config: PipelineConfig,
    preset: str = "balanced",
    run_id: str = "",
) -> None:
    """Render the AIP status dashboard panel."""
    model_chain = _build_model_chain(mode, config)

    parts = [
        f"  Mode: [bold]{mode}[/bold]    Model: [cyan]{model_chain}[/cyan]",
        f"  Preset: {preset}  Thinking: {_fmt_thinking(config.thinking_budget)}",
    ]
    if run_id:
        parts[-1] += f"  Run: {run_id[:16]}.."

    body = "\n".join(parts)
    panel = Panel(body, title="[bold green]AIP[/bold green]", width=56, padding=(0, 1))
    console.print(panel)


def render_session_status(
    stats: SessionStats, session_name: str = "", session_id: str = ""
) -> None:
    """Render session stats panel."""
    total_runs = stats.runs_ok + stats.runs_error
    lines = [
        f"  Runs: {total_runs} ({stats.runs_ok} ok, {stats.runs_error} error)",
        f"  Tokens: claude {stats.format_tokens(stats.claude_tokens)}"
        f" | codex {stats.format_tokens(stats.codex_tokens)}",
        f"  Time: {stats.elapsed} total",
    ]
    if session_name:
        lines.append(f"  Session: [bold]{session_name}[/bold] ({session_id[:12]}..)")

    body = "\n".join(lines)
    panel = Panel(body, title="[bold]Session[/bold]", width=56, padding=(0, 1))
    console.print(panel)


def render_interactive_bar(
    mode: str,
    config: PipelineConfig,
    stats: SessionStats,
    session_name: str = "",
) -> None:
    """Render the interactive REPL header."""
    model = _get_active_model(mode, config)
    title_extra = f" | {session_name}" if session_name else ""
    body = "\n".join(
        [
            f"  Active: [bold]{mode}[/bold]     Model: [cyan]{model}[/cyan]",
            f"  Tokens: claude {stats.format_tokens(stats.claude_tokens)}"
            f" | codex {stats.format_tokens(stats.codex_tokens)}",
        ]
    )
    panel = Panel(
        body,
        title=f"[bold green]AIP Interactive[/bold green]{title_extra}",
        width=56,
        padding=(0, 1),
    )
    console.print(panel)


def _build_model_chain(mode: str, config: PipelineConfig) -> str:
    """Build a model chain string based on mode."""
    if mode == "pipeline":
        return f"{config.claude_plan_model} -> codex -> {config.claude_review_model}"
    if mode == "ask":
        return config.claude_ask_model
    if mode == "chat":
        return config.claude_chat_model
    if mode == "plan":
        return f"{config.claude_plan_model} (thinking)"
    if mode in ("explore", "code"):
        return config.codex_model
    if mode == "review":
        return config.claude_review_model
    return config.claude_ask_model


def _get_active_model(mode: str, config: PipelineConfig) -> str:
    """Get the primary active model for a mode."""
    models = {
        "ask": config.claude_ask_model,
        "chat": config.claude_chat_model,
        "plan": config.claude_plan_model,
        "explore": config.codex_model,
        "code": config.codex_model,
        "review": config.claude_review_model,
        "pipeline": config.claude_plan_model,
    }
    return models.get(mode, "sonnet")


def _fmt_thinking(budget: int) -> str:
    """Format thinking budget for display."""
    if budget == 0:
        return "off"
    if budget >= 1000:
        return f"{budget // 1000}k"
    return str(budget)


# ---------------------------------------------------------------------------
# Autocomplete
# ---------------------------------------------------------------------------

# (command, description) pairs -- ordered by frequency of use
_COMMAND_COMPLETIONS: list[tuple[str, str]] = [
    ("/mode", "Trocar modo (ask, chat, plan, code, explore, auto)"),
    ("/preset", "Aplicar preset (fast, balanced, thorough)"),
    ("/model", "Trocar modelo (ex: /model claude sonnet)"),
    ("/session", "Gerenciar sessoes (save, load, list, new, delete)"),
    ("/status", "Ver uso de tokens e tempo da sessao"),
    ("/thinking", "Ajustar thinking budget (0, 5000, 10000, 50000)"),
    ("/last", "Mostrar resumo do ultimo run"),
    ("/context", "Ver historico de tarefas da sessao"),
    ("/help", "Listar todos os comandos"),
    ("/quit", "Sair do REPL (sessao salva automaticamente)"),
]

_MODE_COMPLETIONS: list[tuple[str, str]] = [
    ("auto", "NLU classifica e roteia automaticamente"),
    ("ask", "Pergunta rapida via Claude (Sonnet)"),
    ("chat", "Sessao interativa Claude (Sonnet)"),
    ("plan", "Planejamento profundo (Opus + thinking alto)"),
    ("code", "Implementacao rapida via Codex"),
    ("explore", "Prototipagem via Codex (suggest mode)"),
    ("pipeline", "Ciclo completo: plan -> implement -> review"),
]

_PRESET_COMPLETIONS: list[tuple[str, str]] = [
    ("fast", "Sonnet + Haiku + codex-spark (rapido, barato)"),
    ("balanced", "Opus plan + Sonnet review + codex (padrao)"),
    ("thorough", "Opus + codex-max + thinking 50k (completo)"),
]

_PROVIDER_COMPLETIONS: list[tuple[str, str]] = [
    ("claude", "Modelos Claude (haiku, sonnet, opus)"),
    ("codex", "Modelos Codex (codex-spark, codex, codex-max)"),
]

_CLAUDE_MODEL_COMPLETIONS: list[tuple[str, str]] = [
    ("haiku", "Rapido e barato, bom para Q&A simples"),
    ("sonnet", "Equilibrio velocidade/qualidade (padrao ask/chat)"),
    ("opus", "Melhor qualidade, ideal para planning/review critico"),
]

_CODEX_MODEL_COMPLETIONS: list[tuple[str, str]] = [
    ("gpt-5.3-codex-spark", "Ultra-rapido, baixa latencia, tarefas simples"),
    ("gpt-5.3-codex", "Melhor overall para coding (padrao)"),
    ("gpt-5.1-codex-max", "Tarefas complexas, codebases grandes"),
]

_THINKING_COMPLETIONS: list[tuple[str, str]] = [
    ("0", "Desligado (sem extended thinking)"),
    ("5000", "Leve (tarefas simples)"),
    ("10000", "Padrao (features normais)"),
    ("50000", "Alto (arquitetura, migracoes)"),
    ("128000", "Maximo (analise critica complexa)"),
]

_SESSION_COMPLETIONS: list[tuple[str, str]] = [
    ("list", "Listar todas as sessoes salvas"),
    ("save", "Salvar sessao atual (opcional: /session save nome)"),
    ("load", "Carregar sessao (/session load nome-ou-id)"),
    ("new", "Iniciar nova sessao limpa"),
    ("name", "Renomear sessao atual (/session name novo-nome)"),
    ("delete", "Deletar sessao (/session delete nome-ou-id)"),
]


if HAS_PROMPT_TOOLKIT:

    class AIPCompleter(Completer):
        """Context-aware autocomplete for AIP REPL commands."""

        def get_completions(
            self, document: Document, complete_event: object
        ) -> list[Completion]:
            """Yield completions based on current input context."""
            text = document.text_before_cursor
            words = text.split()
            word_count = len(words)

            if not text:
                return []

            # "/" alone: immediately show all commands
            if text == "/":
                return self._from_pairs(_COMMAND_COMPLETIONS, "/")

            # Typing first word (command)
            if word_count == 1 and not text.endswith(" "):
                return self._from_pairs(_COMMAND_COMPLETIONS, words[0])

            # Second word (subcommand argument)
            cmd = words[0].lower()
            partial = words[1] if word_count >= 2 and not text.endswith(" ") else ""

            if cmd == "/mode":
                return self._from_pairs(_MODE_COMPLETIONS, partial)
            if cmd == "/preset":
                return self._from_pairs(_PRESET_COMPLETIONS, partial)
            if cmd == "/thinking":
                return self._from_pairs(_THINKING_COMPLETIONS, partial)
            if cmd == "/session":
                return self._from_pairs(_SESSION_COMPLETIONS, partial)
            if cmd == "/model":
                if word_count == 2 and not text.endswith(" "):
                    return self._from_pairs(_PROVIDER_COMPLETIONS, partial)
                if word_count == 2 and text.endswith(" "):
                    provider = words[1].lower()
                    if provider == "claude":
                        return self._from_pairs(_CLAUDE_MODEL_COMPLETIONS, "")
                    if provider == "codex":
                        return self._from_pairs(_CODEX_MODEL_COMPLETIONS, "")
                if word_count >= 3:
                    partial3 = words[2] if not text.endswith(" ") else ""
                    provider = words[1].lower()
                    if provider == "claude":
                        return self._from_pairs(_CLAUDE_MODEL_COMPLETIONS, partial3)
                    if provider == "codex":
                        return self._from_pairs(_CODEX_MODEL_COMPLETIONS, partial3)

            return []

        def _from_pairs(
            self, pairs: list[tuple[str, str]], partial: str
        ) -> list[Completion]:
            """Build Completion objects from (text, description) pairs."""
            results = []
            for text, desc in pairs:
                if text.startswith(partial):
                    results.append(
                        Completion(
                            text,
                            start_position=-len(partial),
                            display=text,
                            display_meta=desc,
                        )
                    )
            return results


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

VALID_MODES = ("ask", "chat", "explore", "code", "plan", "pipeline", "auto")

HELP_TEXT = """[bold]AIP REPL Commands:[/bold]

  /mode <mode>              Switch mode (ask|chat|explore|code|plan|pipeline|auto)
  /model <provider> <name>  Set model (e.g. /model claude sonnet)
  /preset <name>            Apply preset (fast|balanced|thorough)
  /thinking <budget>        Set thinking budget (0|5000|10000|50000)
  /status                   Show session stats
  /last                     Show last run summary
  /context                  Show task history for this session

  [bold]Session management:[/bold]
  /session list             List all saved sessions
  /session save [name]      Save current session
  /session load <name|id>   Load a saved session
  /session new              Start a fresh session
  /session name <name>      Rename current session
  /session delete <name|id> Delete a saved session

  /help                     Show this help
  /quit                     Exit (auto-saves session)

  <any text>                Execute in current mode (default: auto)
"""


def _generate_session_id() -> str:
    return (
        datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:6]
    )


@dataclass
class REPLState:
    """Mutable state for the REPL session."""

    mode: str = "auto"
    preset: str = "balanced"
    config: PipelineConfig | None = None
    project: Path = field(default_factory=Path.cwd)
    stats: SessionStats = field(default_factory=SessionStats)
    running: bool = True
    # Session fields
    session_id: str = ""
    session_name: str = ""
    created_at: str = ""
    context: list[ContextEntry] = field(default_factory=list)


def _restore_session(
    data: SessionData, state: REPLState, config: PipelineConfig
) -> None:
    """Restore a saved session into the current REPL state and config."""
    state.session_id = data.session_id
    state.session_name = data.name
    state.created_at = data.created_at

    # Restore config
    cfg = data.config_state
    state.mode = cfg.get("mode", "auto")
    state.preset = cfg.get("preset", "balanced")
    config.claude_ask_model = cfg.get("claude_ask_model", config.claude_ask_model)
    config.claude_chat_model = cfg.get("claude_chat_model", config.claude_chat_model)
    config.claude_plan_model = cfg.get("claude_plan_model", config.claude_plan_model)
    config.claude_review_model = cfg.get(
        "claude_review_model", config.claude_review_model
    )
    config.codex_model = cfg.get("codex_model", config.codex_model)
    config.thinking_budget = cfg.get("thinking_budget", config.thinking_budget)

    # Restore stats (preserving start_time as now)
    st = data.stats
    state.stats.claude_tokens = st.get("claude_tokens", 0)
    state.stats.codex_tokens = st.get("codex_tokens", 0)
    state.stats.runs_ok = st.get("runs_ok", 0)
    state.stats.runs_error = st.get("runs_error", 0)
    state.stats.elapsed_seconds = st.get("elapsed_seconds", 0.0)

    # Restore context
    state.context = [
        ContextEntry(
            task=e.get("task", ""),
            mode=e.get("mode", ""),
            summary=e.get("summary", ""),
            timestamp=e.get("timestamp", ""),
        )
        for e in data.context
    ]


def run_repl(config: PipelineConfig, project: Path) -> int:
    """Run the interactive REPL loop with session management."""
    from ai_pipeline import (
        classify_intent_llm,
        run_ask,
        run_chat,
        run_code,
        run_explore,
        run_plan,
    )

    mgr = SessionManager(project)
    state = REPLState(config=config, project=project)

    # Try to restore the most recent session
    latest = mgr.latest()
    if latest:
        _restore_session(latest, state, config)
        console.print(
            f"  [dim]Sessao restaurada: {state.session_name or state.session_id[:12]}[/dim]"
        )
    else:
        state.session_id = _generate_session_id()
        state.created_at = datetime.now(tz=timezone.utc).isoformat()

    render_interactive_bar(state.mode, config, state.stats, state.session_name)
    console.print()

    # Build prompt with autocomplete and persistent history
    _read_input = _build_input_fn(mgr, state)

    while state.running:
        try:
            user_input = _read_input()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye![/dim]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            _handle_command(user_input, state, config, mgr)
            continue

        # Execute task
        mode = state.mode
        task = user_input

        if mode == "auto":
            console.print("  [dim][auto] Classificando tarefa...[/dim]")
            nlu = classify_intent_llm(task, project)
            mode = nlu.mode
            console.print(
                f"  [dim][auto] Detectado: {nlu.mode}"
                f" (codex={nlu.codex_model}, review={nlu.review_model},"
                f" thinking={nlu.thinking_budget})[/dim]"
            )
            config.codex_model = nlu.codex_model
            config.claude_review_model = nlu.review_model
            config.thinking_budget = nlu.thinking_budget

            chain = _build_model_chain(mode, config)
            console.print(f"  [dim][auto] {chain}[/dim]")
            console.print()

        # Estimate input tokens
        state.stats.add_tokens(
            "claude" if mode in ("ask", "chat", "plan", "review") else "codex",
            len(task),
        )

        # Dispatch
        rc = 1
        if mode == "ask":
            rc = run_ask(task, config, project)
        elif mode == "chat":
            rc = run_chat(project, config)
        elif mode == "plan":
            rc = run_plan(task, config, project)
        elif mode == "explore":
            rc = run_explore(task, project, config)
        elif mode in ("code", "pipeline"):
            rc = run_code(task, project, config)

        state.stats.record_run(success=rc == 0)

        # Record context
        summary = f"{'OK' if rc == 0 else 'ERROR'} via {mode}"
        state.context.append(
            ContextEntry(
                task=task[:200],
                mode=mode,
                summary=summary[:MAX_SUMMARY_CHARS],
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        )
        console.print()

    # Auto-save on exit
    mgr.save(state.session_id, state.session_name, state, config, state.context)
    console.print(
        f"  [dim]Sessao salva: {state.session_name or state.session_id[:12]}[/dim]"
    )

    return 0


def _build_input_fn(mgr: SessionManager, state: REPLState) -> Any:
    """Build the input function with optional autocomplete and history.

    Falls back to simple console.input() when:
    - prompt_toolkit is not installed
    - stdin is not a real terminal (pipe, redirection)
    """
    is_tty = hasattr(sys.stdin, "isatty") and sys.stdin.isatty()

    if HAS_PROMPT_TOOLKIT and is_tty:
        completer = AIPCompleter()
        prompt_msg = HTML("<ansigreen><b>aip&gt;</b></ansigreen> ")
        history_path = mgr.get_history_path(state.session_id)
        history = FileHistory(str(history_path))

        def _read() -> str:
            return pt_prompt(
                prompt_msg,
                completer=completer,
                complete_while_typing=True,
                history=history,
            ).strip()

        return _read

    def _read_fallback() -> str:
        return console.input("[bold green]aip>[/bold green] ").strip()

    return _read_fallback


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


def _handle_command(
    raw: str,
    state: REPLState,
    config: PipelineConfig,
    mgr: SessionManager,
) -> None:
    """Parse and execute a slash command."""
    from ai_pipeline import PRESETS

    parts = raw.split()
    cmd = parts[0].lower()

    if cmd == "/quit":
        state.running = False
        console.print("  [dim]Bye![/dim]")

    elif cmd == "/help":
        console.print(HELP_TEXT)

    elif cmd == "/status":
        render_session_status(state.stats, state.session_name, state.session_id)

    elif cmd == "/last":
        if state.stats.last_summary:
            console.print(state.stats.last_summary)
        else:
            console.print("  [dim]No runs yet.[/dim]")

    elif cmd == "/context":
        _show_context(state)

    elif cmd == "/mode":
        if len(parts) < 2:
            console.print(f"  Mode: [bold]{state.mode}[/bold]")
            return
        new_mode = parts[1].lower()
        if new_mode not in VALID_MODES:
            console.print(f"  [red]Unknown mode: {new_mode}[/red]")
            console.print(f"  Valid: {', '.join(VALID_MODES)}")
            return
        state.mode = new_mode
        model = _get_active_model(new_mode, config)
        console.print(f"  Mode -> [bold]{new_mode}[/bold] ({model})")

    elif cmd == "/model":
        if len(parts) < 3:
            console.print("  Usage: /model <claude|codex> <model_name>")
            return
        provider = parts[1].lower()
        model_name = parts[2]
        if provider == "claude":
            config.claude_ask_model = model_name
            config.claude_chat_model = model_name
            console.print(f"  Claude model -> [cyan]{model_name}[/cyan]")
        elif provider == "codex":
            config.codex_model = model_name
            console.print(f"  Codex model -> [cyan]{model_name}[/cyan]")
        else:
            console.print("  [red]Provider must be 'claude' or 'codex'[/red]")

    elif cmd == "/preset":
        if len(parts) < 2:
            console.print(f"  Preset: [bold]{state.preset}[/bold]")
            return
        name = parts[1].lower()
        if name not in PRESETS:
            console.print(f"  [red]Unknown preset: {name}[/red]")
            return
        config.apply_preset(name)
        state.preset = name
        console.print(f"  Preset -> [bold]{name}[/bold]")

    elif cmd == "/thinking":
        if len(parts) < 2:
            console.print(f"  Thinking: {_fmt_thinking(config.thinking_budget)}")
            return
        try:
            budget = int(parts[1])
        except ValueError:
            console.print("  [red]Budget must be an integer[/red]")
            return
        config.thinking_budget = budget
        console.print(f"  Thinking -> [bold]{_fmt_thinking(budget)}[/bold]")

    elif cmd == "/session":
        _handle_session_command(parts[1:], state, config, mgr)

    else:
        console.print(f"  [red]Unknown command: {cmd}[/red]. Type /help for commands.")


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------


def _handle_session_command(
    args: list[str],
    state: REPLState,
    config: PipelineConfig,
    mgr: SessionManager,
) -> None:
    """Handle /session subcommands."""
    if not args:
        # Default: show current session info
        name_display = state.session_name or "(sem nome)"
        console.print(f"  Session: [bold]{name_display}[/bold]")
        console.print(f"  ID: {state.session_id}")
        console.print(f"  Criada: {state.created_at[:19]}")
        console.print(f"  Contexto: {len(state.context)} entradas")
        return

    subcmd = args[0].lower()

    if subcmd == "list":
        sessions = mgr.list_sessions()
        if not sessions:
            console.print("  [dim]Nenhuma sessao salva.[/dim]")
            return

        table = Table(title="Sessoes salvas", width=60)
        table.add_column("Nome", style="bold")
        table.add_column("ID", style="dim")
        table.add_column("Atualizada")
        table.add_column("Runs")

        for s in sessions:
            name = s.name or "(sem nome)"
            sid = s.session_id[:12]
            updated = s.updated_at[:16] if s.updated_at else "?"
            runs = str(s.stats.get("runs_ok", 0) + s.stats.get("runs_error", 0))
            # Highlight current session
            if s.session_id == state.session_id:
                name = f"[green]* {name}[/green]"
            table.add_row(name, sid, updated, runs)

        console.print(table)

    elif subcmd == "save":
        name = " ".join(args[1:]) if len(args) > 1 else state.session_name
        if name:
            state.session_name = name
        path = mgr.save(
            state.session_id, state.session_name, state, config, state.context
        )
        display = state.session_name or state.session_id[:12]
        console.print(f"  Sessao salva: [bold]{display}[/bold]")
        console.print(f"  [dim]{path}[/dim]")

    elif subcmd == "load":
        if len(args) < 2:
            console.print("  Usage: /session load <nome-ou-id>")
            return
        identifier = " ".join(args[1:])
        data = mgr.find_by_id_or_name(identifier)
        if not data:
            console.print(f"  [red]Sessao nao encontrada: {identifier}[/red]")
            return
        # Save current first
        mgr.save(state.session_id, state.session_name, state, config, state.context)
        # Load the target
        _restore_session(data, state, config)
        display = state.session_name or state.session_id[:12]
        console.print(f"  Sessao carregada: [bold]{display}[/bold]")
        console.print(f"  {len(state.context)} entradas de contexto restauradas")
        render_interactive_bar(state.mode, config, state.stats, state.session_name)

    elif subcmd == "new":
        # Save current, then start fresh
        mgr.save(state.session_id, state.session_name, state, config, state.context)
        state.session_id = _generate_session_id()
        state.session_name = " ".join(args[1:]) if len(args) > 1 else ""
        state.created_at = datetime.now(tz=timezone.utc).isoformat()
        state.stats = SessionStats()
        state.context = []
        state.mode = "auto"
        state.preset = "balanced"
        display = state.session_name or "nova sessao"
        console.print(f"  Nova sessao: [bold]{display}[/bold]")
        render_interactive_bar(state.mode, config, state.stats, state.session_name)

    elif subcmd == "name":
        if len(args) < 2:
            console.print(
                f"  Nome atual: [bold]{state.session_name or '(sem nome)'}[/bold]"
            )
            return
        state.session_name = " ".join(args[1:])
        console.print(f"  Sessao renomeada: [bold]{state.session_name}[/bold]")

    elif subcmd == "delete":
        if len(args) < 2:
            console.print("  Usage: /session delete <nome-ou-id>")
            return
        identifier = " ".join(args[1:])
        data = mgr.find_by_id_or_name(identifier)
        if not data:
            console.print(f"  [red]Sessao nao encontrada: {identifier}[/red]")
            return
        if data.session_id == state.session_id:
            console.print("  [red]Nao pode deletar a sessao ativa.[/red]")
            return
        mgr.delete(data.session_id)
        console.print(f"  Sessao deletada: {data.name or data.session_id[:12]}")

    else:
        console.print(f"  [red]Subcomando desconhecido: {subcmd}[/red]")
        console.print("  Opcoes: list, save, load, new, name, delete")


def _show_context(state: REPLState) -> None:
    """Show task context history for the current session."""
    if not state.context:
        console.print("  [dim]Nenhuma tarefa registrada nesta sessao.[/dim]")
        return

    table = Table(title=f"Contexto ({len(state.context)} entradas)", width=60)
    table.add_column("#", style="dim", width=3)
    table.add_column("Modo", width=8)
    table.add_column("Tarefa")
    table.add_column("Status", width=6)

    for i, entry in enumerate(state.context, 1):
        task_display = entry.task[:40] + "..." if len(entry.task) > 40 else entry.task
        table.add_row(str(i), entry.mode, task_display, entry.summary[:6])

    console.print(table)
