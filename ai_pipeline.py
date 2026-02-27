"""AI Pipeline v2: NLU Router + TUI + Sequential Pipeline.

Modes:
  (no args)   -> Interactive REPL with status dashboard
  (default)   -> Full pipeline: Plan -> Implement -> Review -> Consolidate
  ask         -> Single-shot question via Claude (Sonnet)
  chat        -> Interactive Claude session (Sonnet)
  plan        -> Deep planning via Claude (Opus + high thinking)
  explore     -> Codex suggest mode for prototyping
  code        -> Direct Codex full-auto for quick implementation
  auto        -> NLU classification via Sonnet, routes to best mode/model
  review      -> Code review via Claude (model chosen by classifier)

Tools:
  Claude Code -> claude -p (headless) / claude (interactive)
  Codex CLI   -> codex exec (headless) / codex (interactive)

Both support OAuth: Claude via 'claude login', Codex via 'codex auth login'.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

logger = logging.getLogger("ai_pipeline")

PIPELINE_DIR = ".pipeline"
RUNS_DIR = f"{PIPELINE_DIR}/runs"
SCHEMAS_DIR = f"{PIPELINE_DIR}/schemas"
PROMPTS_DIR = f"{PIPELINE_DIR}/prompts"

STAGES = ("plan", "implement", "review", "consolidate")

_PLAN_ALLOWED_TOOLS: tuple[str, ...] = (
    "Read",
    "Glob",
    "Grep",
    "Bash(git:*)",
    "WebSearch",
    "WebFetch",
    "LS",
)

_ENV_VAR_PATTERN = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}")


def _substitute_env_vars(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively substitute {env:VAR} and {env:VAR:default} in string values."""

    def _sub_str(s: str) -> str:
        return _ENV_VAR_PATTERN.sub(
            lambda m: os.environ.get(
                m.group(1), m.group(2) if m.group(2) is not None else m.group(0)
            ),
            s,
        )

    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _substitute_env_vars(value)
        elif isinstance(value, list):
            result[key] = [_sub_str(item) if isinstance(item, str) else item for item in value]
        elif isinstance(value, str):
            result[key] = _sub_str(value)
        else:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StageResult:
    """Result of a single pipeline stage."""

    stage: str
    status: str  # "success", "error", "skipped"
    output: Any = None
    error: str | None = None
    duration: float = 0.0
    command: list[str] = field(default_factory=list)


PRESETS: dict[str, dict[str, Any]] = {
    "fast": {
        "claude_plan_model": "sonnet",
        "claude_ask_model": "haiku",
        "claude_chat_model": "haiku",
        "claude_review_model": "haiku",
        "codex_model": "gpt-5.3-codex-spark",
        "thinking_budget": 0,
        "reasoning_effort": "",  # not used for codex models
        "plan_timeout": 90,
        "implement_timeout": 300,
        "review_timeout": 120,
    },
    "balanced": {
        "claude_plan_model": "opus",
        "claude_ask_model": "sonnet",
        "claude_chat_model": "sonnet",
        "claude_review_model": "sonnet",
        "codex_model": "gpt-5.3-codex",
        "thinking_budget": 10000,
        "reasoning_effort": "",
        "plan_timeout": 180,
        "implement_timeout": 600,
        "review_timeout": 300,
    },
    "thorough": {
        "claude_plan_model": "opus",
        "claude_ask_model": "sonnet",
        "claude_chat_model": "opus",
        "claude_review_model": "opus",
        "codex_model": "gpt-5.1-codex-max",
        "thinking_budget": 50000,
        "reasoning_effort": "",
        "plan_timeout": 300,
        "implement_timeout": 900,
        "review_timeout": 600,
    },
}


@dataclass
class PipelineConfig:
    """Pipeline configuration loaded from config.toml."""

    # models
    claude_plan_model: str = "opus"
    claude_ask_model: str = "sonnet"
    claude_chat_model: str = "sonnet"
    claude_review_model: str = "sonnet"
    codex_model: str = "gpt-5.3-codex"

    # thinking / reasoning
    thinking_budget: int = 10000  # Claude extended thinking (0 = off)
    reasoning_effort: str = (
        ""  # Only for o-series models (low/medium/high), empty = skip
    )

    # timeouts (seconds)
    plan_timeout: int = 180
    implement_timeout: int = 600
    review_timeout: int = 300

    # git
    auto_branch: bool = True
    auto_commit: bool = True
    branch_prefix: str = "pipeline"

    # retry
    max_retries: int = 1
    retry_delay: int = 5

    # doom loop detection
    doom_loop_detection: bool = True

    # pipeline compaction
    compact_threshold: int = 30000

    @classmethod
    def from_toml(cls, path: Path) -> PipelineConfig:
        """Load configuration from a TOML file."""
        if not path.exists():
            logger.warning("Config not found at %s, using defaults", path)
            return cls()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        data = _substitute_env_vars(data)

        models = data.get("models", {})
        thinking = data.get("thinking", {})
        timeouts = data.get("timeouts", {})
        git = data.get("git", {})
        retry = data.get("retry", {})
        pipeline_sect = data.get("pipeline", {})

        return cls(
            claude_plan_model=models.get("claude_plan", cls.claude_plan_model),
            claude_ask_model=models.get("claude_ask", cls.claude_ask_model),
            claude_chat_model=models.get("claude_chat", cls.claude_chat_model),
            claude_review_model=models.get("claude_review", cls.claude_review_model),
            codex_model=models.get("codex", cls.codex_model),
            thinking_budget=thinking.get("budget", cls.thinking_budget),
            reasoning_effort=thinking.get("reasoning_effort", cls.reasoning_effort),
            plan_timeout=timeouts.get("plan", cls.plan_timeout),
            implement_timeout=timeouts.get("implement", cls.implement_timeout),
            review_timeout=timeouts.get("review", cls.review_timeout),
            auto_branch=git.get("auto_branch", cls.auto_branch),
            auto_commit=git.get("auto_commit", cls.auto_commit),
            branch_prefix=git.get("branch_prefix", cls.branch_prefix),
            max_retries=retry.get("max_retries", cls.max_retries),
            retry_delay=retry.get("retry_delay", cls.retry_delay),
            doom_loop_detection=retry.get(
                "doom_loop_detection", cls.doom_loop_detection
            ),
            compact_threshold=pipeline_sect.get(
                "compact_threshold", cls.compact_threshold
            ),
        )

    def apply_preset(self, name: str) -> None:
        """Override config values from a named preset."""
        preset = PRESETS.get(name)
        if not preset:
            logger.warning("Unknown preset '%s', ignoring", name)
            return
        for key, value in preset.items():
            if hasattr(self, key):
                setattr(self, key, value)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _detect_base_branch(project: Path) -> str:
    """Detect the default branch name (main or master)."""
    for candidate in ("main", "master"):
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=str(project),
                capture_output=True,
                check=True,
                timeout=10,
            )
            return candidate
        except (subprocess.CalledProcessError, subprocess.SubprocessError):
            continue
    return "main"


_FALLBACK_PROMPTS: dict[str, str] = {
    "plan.txt": (
        "Analyze the codebase and create a detailed implementation plan "
        "for the following task. Output structured JSON."
    ),
    "implement.txt": (
        "Implement the following plan exactly as specified. "
        "Write complete, production-ready code."
    ),
    "review.txt": (
        "Review this implementation against the original plan. "
        "List issues by severity. End with VERDICT: APPROVE or REQUEST_CHANGES."
    ),
}


class PipelineError(Exception):
    """Raised when a pipeline stage fails irrecoverably."""


class Pipeline:
    """Multi-agent sequential pipeline orchestrator."""

    def __init__(
        self,
        task: str,
        project: Path,
        config: PipelineConfig,
        *,
        run_id: str | None = None,
        dry_run: bool = False,
        base_branch: str = "main",
    ) -> None:
        self.task = task
        self.project = project.resolve()
        self.config = config
        self.run_id = (
            run_id
            or datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            + "-"
            + uuid.uuid4().hex[:6]
        )
        self.dry_run = dry_run
        self.base_branch = (
            base_branch
            if base_branch != "main"
            else _detect_base_branch(self.project)
        )

        self.run_dir = self.project / RUNS_DIR / self.run_id
        self.results: dict[str, StageResult] = {}

        self._prompts_dir = self.project / PROMPTS_DIR
        self._schemas_dir = self.project / SCHEMAS_DIR

    def _check_git_repo(self) -> None:
        """Warn if project is not a git repository and disable git features."""
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.project),
                capture_output=True,
                check=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.SubprocessError):
            logger.warning(
                "Project %s is not a git repository. "
                "Git features (branch, commit, diff, doom loop) will be skipped.",
                self.project,
            )
            self.config.auto_branch = False
            self.config.auto_commit = False

    # -- public API ---------------------------------------------------------

    def run(
        self,
        from_stage: int = 1,
        only_stage: str | None = None,
    ) -> dict[str, StageResult]:
        """Execute the pipeline stages sequentially.

        Args:
            from_stage: 1-based index to resume from.
            only_stage: Run only this stage name, then stop.

        Returns:
            Dict mapping stage name to its result.
        """
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._check_git_repo()
        self._save_metadata()

        stage_methods = {
            "plan": self._stage_plan,
            "implement": self._stage_implement,
            "review": self._stage_review,
            "consolidate": self._stage_consolidate,
        }

        stages_to_run = STAGES
        if only_stage:
            if only_stage not in stage_methods:
                raise PipelineError(f"Unknown stage: {only_stage}")
            stages_to_run = (only_stage,)
        else:
            stages_to_run = STAGES[from_stage - 1 :]

        for stage_name in stages_to_run:
            logger.info("=" * 60)
            logger.info("STAGE: %s", stage_name.upper())
            logger.info("=" * 60)

            method = stage_methods[stage_name]
            result = self._run_with_retry(stage_name, method)
            self.results[stage_name] = result
            self._save_result(stage_name, result)

            if result.status == "error":
                logger.error("Stage %s failed: %s", stage_name, result.error)
                logger.error(
                    "Resume with: python ai_pipeline.py --resume %s --from-stage %d",
                    self.run_id,
                    STAGES.index(stage_name) + 1,
                )
                break

            logger.info("Stage %s completed in %.1fs", stage_name, result.duration)

        # Auto-cleanup: keep last 20 runs
        _cleanup_old_runs(self.project / RUNS_DIR, keep=20)

        return self.results

    # -- stage implementations ----------------------------------------------

    def _stage_plan(self) -> StageResult:
        """Stage 1: Generate implementation plan via Claude Code."""
        prompt_template = self._load_prompt("plan.txt")
        schema_path = self._schemas_dir / "plan_schema.json"

        full_prompt = f"{prompt_template}\n\nTask: {self.task}"

        cmd = [
            "claude",
            "-p",
            full_prompt,
            "--output-format",
            "json",
            "--model",
            self.config.claude_plan_model,
        ]

        if self.config.thinking_budget > 0:
            cmd.extend(["--thinking-budget-tokens", str(self.config.thinking_budget)])

        if schema_path.exists():
            cmd.extend(["--json-schema", str(schema_path)])

        cmd.extend(["--allowedTools", *_PLAN_ALLOWED_TOOLS])

        return self._execute_stage("plan", cmd, self.config.plan_timeout)

    def _stage_implement(self) -> StageResult:
        """Stage 2: Implement the plan via Codex CLI."""
        plan_data = self._load_previous_result("plan")
        if plan_data is None:
            return StageResult(
                stage="implement",
                status="error",
                error="No plan found. Run stage 1 first.",
            )

        if self.config.auto_branch:
            self._create_branch()

        prompt_template = self._load_prompt("implement.txt")
        plan_text = (
            json.dumps(plan_data, indent=2)
            if isinstance(plan_data, dict)
            else str(plan_data)
        )
        full_prompt = f"{prompt_template}\n{plan_text}"

        output_file = self.run_dir / "02_implement_output.txt"

        cmd = [
            "codex",
            "exec",
            full_prompt,
            "--full-auto",
            "--json",
            "-o",
            str(output_file),
            "--model",
            self.config.codex_model,
        ]

        # --reasoning-effort only applies to o-series models, not gpt-5.x-codex
        if self.config.reasoning_effort and self.config.codex_model.startswith(
            ("o1", "o3", "o4")
        ):
            cmd.extend(["--reasoning-effort", self.config.reasoning_effort])

        result = self._execute_stage("implement", cmd, self.config.implement_timeout)

        if result.status == "success" and self.config.auto_commit:
            self._commit_changes(f"pipeline({self.run_id}): implement stage")

        return result

    def _stage_review(self) -> StageResult:
        """Stage 3: Review implementation via Claude Code (different model)."""
        plan_data = self._load_previous_result("plan")
        plan_data = self._compact_plan_output(plan_data)

        diff = self._get_git_diff()
        if not diff:
            logger.warning("No git diff found; reviewing current state")
            diff = "(no diff available -- review current codebase state)"

        prompt_template = self._load_prompt("review.txt")
        plan_text = (
            json.dumps(plan_data, indent=2)
            if isinstance(plan_data, dict)
            else str(plan_data or "N/A")
        )
        full_prompt = (
            f"{prompt_template}\n{plan_text}\n\nImplementation diff:\n```\n{diff}\n```"
        )

        cmd = [
            "claude",
            "-p",
            full_prompt,
            "--output-format",
            "json",
            "--model",
            self.config.claude_review_model,
        ]

        return self._execute_stage("review", cmd, self.config.review_timeout)

    def _stage_consolidate(self) -> StageResult:
        """Stage 4: Generate summary (local, no API calls)."""
        start = time.monotonic()

        summary_parts = [
            f"# Pipeline Run: {self.run_id}",
            f"**Task:** {self.task}",
            f"**Project:** {self.project}",
            f"**Date:** {datetime.now(tz=timezone.utc).isoformat()}",
            "",
        ]

        for stage_name in ("plan", "implement", "review"):
            result = self.results.get(stage_name) or self._load_saved_result(stage_name)
            status_icon = {
                "success": "[OK]",
                "error": "[FAIL]",
                "skipped": "[SKIP]",
            }.get(result.status if result else "skipped", "[?]")
            duration = f"{result.duration:.1f}s" if result else "N/A"
            summary_parts.append(
                f"## Stage: {stage_name.upper()} {status_icon} ({duration})"
            )
            summary_parts.append("")

            if result and result.status == "error":
                summary_parts.append(f"**Error:** {result.error}")
            elif result and result.output:
                output_text = (
                    json.dumps(result.output, indent=2)
                    if isinstance(result.output, dict)
                    else str(result.output)
                )
                # Truncate very long outputs
                if len(output_text) > 2000:
                    output_text = output_text[:2000] + "\n... (truncated)"
                summary_parts.append(f"```\n{output_text}\n```")

            summary_parts.append("")

        # Extract verdict from review
        review_result = self.results.get("review") or self._load_saved_result("review")
        if review_result and review_result.output:
            output_str = str(review_result.output)
            verdict_match = re.search(
                r"VERDICT:\s*(APPROVE|REQUEST_CHANGES|NEEDS_DISCUSSION)", output_str
            )
            if verdict_match:
                summary_parts.append(f"## Final Verdict: {verdict_match.group(1)}")
                summary_parts.append("")

        summary_text = "\n".join(summary_parts)
        summary_path = self.run_dir / "summary.md"
        summary_path.write_text(summary_text, encoding="utf-8")

        elapsed = time.monotonic() - start
        logger.info("Summary written to %s", summary_path)

        return StageResult(
            stage="consolidate",
            status="success",
            output=str(summary_path),
            duration=elapsed,
        )

    # -- subprocess execution -----------------------------------------------

    def _execute_stage(
        self, stage_name: str, cmd: list[str], timeout: int
    ) -> StageResult:
        """Run a subprocess command for a pipeline stage."""
        start = time.monotonic()

        if self.dry_run:
            logger.info("[DRY RUN] Would execute: %s", " ".join(cmd))
            return StageResult(
                stage=stage_name,
                status="skipped",
                output="(dry run)",
                duration=time.monotonic() - start,
                command=cmd,
            )

        # Check that the CLI tool exists
        tool_name = cmd[0]
        if not shutil.which(tool_name):
            return StageResult(
                stage=stage_name,
                status="error",
                error=f"CLI tool '{tool_name}' not found in PATH",
                duration=time.monotonic() - start,
                command=cmd,
            )

        logger.info("Executing: %s", " ".join(cmd))
        logger.info("Timeout: %ds", timeout)

        # If prompt arg is too long, pipe via stdin to avoid OS arg limits
        stdin_data = None
        if len(" ".join(cmd)) > _STDIN_PROMPT_THRESHOLD:
            try:
                p_idx = cmd.index("-p")
                prompt_text = cmd[p_idx + 1]
                cmd = cmd[:p_idx] + ["-p", "-"] + cmd[p_idx + 2:]
                stdin_data = prompt_text
                logger.debug("Prompt too long (%d chars), piping via stdin", len(prompt_text))
            except (ValueError, IndexError):
                pass

        # Strip ANTHROPIC_API_KEY for Claude CLI calls to force OAuth
        env = _claude_env() if cmd[0] == "claude" else None
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.project),
                env=env,
            )
        except subprocess.TimeoutExpired:
            return StageResult(
                stage=stage_name,
                status="error",
                error=f"Timeout after {timeout}s",
                duration=time.monotonic() - start,
                command=cmd,
            )

        elapsed = time.monotonic() - start

        if proc.returncode != 0:
            stderr = proc.stderr.strip() if proc.stderr else "(no stderr)"
            return StageResult(
                stage=stage_name,
                status="error",
                error=f"Exit code {proc.returncode}: {stderr[:500]}",
                duration=elapsed,
                command=cmd,
            )

        output = self._parse_output(stage_name, proc.stdout)

        return StageResult(
            stage=stage_name,
            status="success",
            output=output,
            duration=elapsed,
            command=cmd,
        )

    def _parse_output(self, stage_name: str, raw: str) -> Any:
        """Parse CLI output based on the stage and tool format."""
        if stage_name in ("plan", "review"):
            return self._parse_claude_output(raw)
        if stage_name == "implement":
            return self._parse_codex_output(raw)
        return raw

    def _parse_claude_output(self, raw: str) -> Any:
        """Parse Claude Code JSON output.

        Claude Code with --output-format json returns a JSON envelope
        with a `result` field containing the model's response.
        """
        try:
            data = json.loads(raw)
            result_text = data.get("result", raw)
            # The result itself might be JSON (from --json-schema)
            if isinstance(result_text, str):
                try:
                    return json.loads(result_text)
                except (json.JSONDecodeError, ValueError):
                    return result_text
            return result_text
        except (json.JSONDecodeError, ValueError):
            logger.warning("Could not parse Claude output as JSON, returning raw")
            return raw

    def _parse_codex_output(self, raw: str) -> Any:
        """Parse Codex CLI JSONL output.

        Codex outputs one JSON object per line (JSONL).
        We collect all events and return them as a list.
        """
        events = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                events.append({"raw": line})
        return events if events else raw

    # -- retry logic --------------------------------------------------------

    def _run_with_retry(self, stage_name: str, method: Any) -> StageResult:
        """Execute a stage method with configurable retry and doom loop detection."""
        last_result = StageResult(
            stage=stage_name, status="error", error="No attempts made"
        )
        previous_hash = ""

        for attempt in range(1 + self.config.max_retries):
            if attempt > 0:
                # Doom loop detection: compare git state hash before retrying
                if self.config.doom_loop_detection:
                    current_hash = self._get_state_hash()
                    if current_hash == previous_hash:
                        logger.warning(
                            "Doom loop detected in stage %s — "
                            "no changes between attempt %d and %d, aborting retry",
                            stage_name,
                            attempt - 1,
                            attempt,
                        )
                        last_result.error = (
                            f"{last_result.error or 'Failed'} "
                            f"(doom loop: identical state after {attempt} attempts)"
                        )
                        return last_result

                logger.info(
                    "Retry %d/%d for stage %s (waiting %ds)",
                    attempt,
                    self.config.max_retries,
                    stage_name,
                    self.config.retry_delay,
                )
                time.sleep(self.config.retry_delay)

            previous_hash = self._get_state_hash()
            last_result = method()
            if last_result.status in ("success", "skipped"):
                return last_result

        return last_result

    # -- git helpers --------------------------------------------------------

    def _create_branch(self) -> None:
        """Create and checkout a pipeline-specific git branch."""
        branch_name = f"{self.config.branch_prefix}/{self.run_id}"
        logger.info("Creating branch: %s", branch_name)
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=str(self.project),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            logger.warning("Failed to create branch: %s", exc.stderr.strip())

    def _commit_changes(self, message: str) -> None:
        """Stage all changes and commit."""
        logger.info("Committing: %s", message)
        try:
            subprocess.run(
                ["git", "add", "-u"],
                cwd=str(self.project),
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", message, "--allow-empty"],
                cwd=str(self.project),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Commit failed: %s", exc.stderr.strip() if exc.stderr else str(exc)
            )

    def _get_git_diff(self) -> str:
        """Get git diff against the base branch."""
        try:
            proc = subprocess.run(
                ["git", "diff", f"{self.base_branch}...HEAD"],
                cwd=str(self.project),
                capture_output=True,
                text=True,
                check=True,
            )
            return proc.stdout.strip()
        except subprocess.CalledProcessError:
            # Fallback: diff against last commit
            try:
                proc = subprocess.run(
                    ["git", "diff", "HEAD~1"],
                    cwd=str(self.project),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return proc.stdout.strip()
            except subprocess.CalledProcessError:
                return ""

    def _get_state_hash(self) -> str:
        """Get SHA-256 hash of current git state (unstaged + staged diffs).

        Returns a unique-per-call UUID if git fails, so legitimate retries
        are never blocked.
        """
        try:
            unstaged = subprocess.run(
                ["git", "diff"],
                cwd=str(self.project),
                capture_output=True,
                text=True,
                timeout=30,
            )
            staged = subprocess.run(
                ["git", "diff", "--staged"],
                cwd=str(self.project),
                capture_output=True,
                text=True,
                timeout=30,
            )
            combined = (unstaged.stdout or "") + (staged.stdout or "")
            return hashlib.sha256(combined.encode()).hexdigest()
        except (subprocess.SubprocessError, OSError):
            return uuid.uuid4().hex

    def _compact_plan_output(self, plan_data: Any) -> Any:
        """Compact plan output if it exceeds the token threshold.

        Estimates tokens as len(text) // 4. If above config.compact_threshold,
        calls Claude Sonnet to produce a concise summary. Falls back to the
        original plan data on any failure.
        """
        plan_text = (
            json.dumps(plan_data, indent=2)
            if isinstance(plan_data, dict)
            else str(plan_data or "")
        )
        estimated_tokens = len(plan_text) // 4
        if estimated_tokens <= self.config.compact_threshold:
            return plan_data

        logger.info(
            "Plan output ~%d tokens exceeds threshold %d — compacting via Claude",
            estimated_tokens,
            self.config.compact_threshold,
        )

        # Save the full plan for reference
        full_path = self.run_dir / "01_plan_full.json"
        full_path.write_text(
            json.dumps(plan_data, indent=2, default=str), encoding="utf-8"
        )

        compact_prompt = (
            "Summarize the following implementation plan concisely. "
            "Keep all key decisions, file paths, and action items. "
            "Remove verbose explanations and examples.\n\n"
            f"{plan_text}"
        )
        cmd = [
            "claude",
            "-p",
            compact_prompt,
            "--output-format",
            "text",
            "--model",
            "sonnet",
        ]
        # Pipe prompt via stdin if too long for command line
        stdin_data = None
        if len(compact_prompt) > _STDIN_PROMPT_THRESHOLD:
            cmd = [
                "claude",
                "-p", "-",
                "--output-format", "text",
                "--model", "sonnet",
            ]
            stdin_data = compact_prompt
        try:
            result = subprocess.run(
                cmd,
                input=stdin_data,
                cwd=str(self.project),
                capture_output=True,
                text=True,
                timeout=120,
                env=_claude_env(),
            )
            if result.returncode == 0 and result.stdout.strip():
                compacted = result.stdout.strip()
                compact_path = self.run_dir / "01_plan_compacted.txt"
                compact_path.write_text(compacted, encoding="utf-8")
                logger.info(
                    "Plan compacted: %d -> %d chars",
                    len(plan_text),
                    len(compacted),
                )
                return compacted
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("Plan compaction failed, using original: %s", exc)

        return plan_data

    # -- file I/O -----------------------------------------------------------

    def _save_metadata(self) -> None:
        """Save run metadata to disk."""
        meta = {
            "run_id": self.run_id,
            "task": self.task,
            "project": str(self.project),
            "config": asdict(self.config),
            "started_at": datetime.now(tz=timezone.utc).isoformat(),
            "dry_run": self.dry_run,
        }
        meta_path = self.run_dir / "metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _save_result(self, stage_name: str, result: StageResult) -> None:
        """Persist a stage result to disk."""
        stage_num = {
            "plan": "01",
            "implement": "02",
            "review": "03",
            "consolidate": "04",
        }
        filename = f"{stage_num.get(stage_name, '00')}_{stage_name}.json"
        path = self.run_dir / filename

        data = asdict(result)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Result saved: %s", path)

    def _load_previous_result(self, stage_name: str) -> Any:
        """Load a previously saved stage result's output."""
        result = self._load_saved_result(stage_name)
        return result.output if result else None

    def _load_saved_result(self, stage_name: str) -> StageResult | None:
        """Load a saved StageResult from disk."""
        stage_num = {
            "plan": "01",
            "implement": "02",
            "review": "03",
            "consolidate": "04",
        }
        filename = f"{stage_num.get(stage_name, '00')}_{stage_name}.json"
        path = self.run_dir / filename

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return StageResult(
                stage=data.get("stage", stage_name),
                status=data.get("status", "unknown"),
                output=data.get("output"),
                error=data.get("error"),
                duration=data.get("duration", 0.0),
                command=data.get("command", []),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to load %s: %s", path, exc)
            return None

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template, falling back to embedded defaults."""
        path = self._prompts_dir / filename
        if not path.exists():
            fallback = _FALLBACK_PROMPTS.get(filename, "")
            if fallback:
                logger.warning(
                    "Prompt template not found: %s — using fallback", path
                )
                return fallback
            logger.warning("Prompt template not found: %s", path)
            return ""
        return path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _find_latest_run(project: Path) -> str | None:
    """Find the most recent run ID by directory modification time."""
    runs_path = project / RUNS_DIR
    if not runs_path.exists():
        return None
    runs = sorted(runs_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0].name if runs else None


def _cleanup_old_runs(runs_dir: Path, keep: int = 20) -> None:
    """Remove oldest run directories, keeping the N most recent."""
    if not runs_dir.exists():
        return
    runs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime)
    to_remove = runs[:-keep] if len(runs) > keep else []
    for run_dir in to_remove:
        logger.info("Cleaning up old run: %s", run_dir.name)
        shutil.rmtree(run_dir, ignore_errors=True)
    if to_remove:
        logger.info("Removed %d old runs, keeping %d", len(to_remove), keep)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ai_pipeline",
        description="Multi-agent sequential pipeline: Plan -> Implement -> Review",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python ai_pipeline.py "Add health check endpoint"\n'
            '  python ai_pipeline.py --preset thorough "Refactor auth system"\n'
            '  python ai_pipeline.py --preset fast "Fix typo in README"\n'
            '  python ai_pipeline.py --project ~/myapp "Add caching"\n'
            '  python ai_pipeline.py --stage plan "Design new API"\n'
            "  python ai_pipeline.py --resume <run_id> --from-stage 2\n"
            '  python ai_pipeline.py --thinking-budget 50000 "Complex refactor"\n'
        ),
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="Task description for the pipeline",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--stage",
        choices=STAGES,
        help="Run only a specific stage",
    )
    parser.add_argument(
        "--resume",
        metavar="RUN_ID",
        help="Resume a previous run by its ID",
    )
    parser.add_argument(
        "--from-stage",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="Resume from this stage number (1-4)",
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch for review diffs (default: main)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing",
    )
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        help="Use a preset config (fast, balanced, thorough)",
    )
    parser.add_argument(
        "--claude-plan-model",
        help="Override Claude model for planning (e.g., sonnet)",
    )
    parser.add_argument(
        "--claude-review-model",
        help="Override Claude model for review (e.g., opus)",
    )
    parser.add_argument(
        "--codex-model",
        help="Override Codex model (e.g., o3, gpt-4.1)",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        help="Claude extended thinking token budget (0=off, max 128000)",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high"],
        help="Codex reasoning effort for o-series models",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


_logging_configured = False


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging once. Subsequent calls update level only."""
    global _logging_configured  # noqa: PLW0603
    level = logging.DEBUG if verbose else logging.INFO
    if not _logging_configured:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        _logging_configured = True
    else:
        logging.getLogger().setLevel(level)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Logging setup
    _setup_logging(args.verbose)

    project = args.project.resolve()

    # Load config
    config_path = project / PIPELINE_DIR / "config.toml"
    config = PipelineConfig.from_toml(config_path)

    # Apply preset first, then individual overrides
    if args.preset:
        config.apply_preset(args.preset)
    if args.claude_plan_model:
        config.claude_plan_model = args.claude_plan_model
    if args.claude_review_model:
        config.claude_review_model = args.claude_review_model
    if args.codex_model:
        config.codex_model = args.codex_model
    if args.thinking_budget is not None:
        config.thinking_budget = args.thinking_budget
    if args.reasoning_effort:
        config.reasoning_effort = args.reasoning_effort

    # Determine run_id
    run_id = args.resume
    if run_id and not (project / RUNS_DIR / run_id).exists():
        logger.error("Run ID not found: %s", run_id)
        return 1

    # Require task unless resuming
    task = args.task
    if not task and run_id:
        # Load task from metadata
        meta_path = project / RUNS_DIR / run_id / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            task = meta.get("task", "")
    if not task:
        parser.error("task is required (unless resuming with --resume)")

    pipeline = Pipeline(
        task=task,
        project=project,
        config=config,
        run_id=run_id,
        dry_run=args.dry_run,
        base_branch=args.base,
    )

    logger.info("Pipeline run: %s", pipeline.run_id)
    logger.info("Project: %s", project)
    logger.info("Task: %s", task)

    if args.dry_run:
        logger.info("[DRY RUN MODE]")

    results = pipeline.run(
        from_stage=args.from_stage,
        only_stage=args.stage,
    )

    # Print summary
    _print_summary(results, pipeline.run_id)

    # Return non-zero if any stage failed
    if any(r.status == "error" for r in results.values()):
        return 1
    return 0


def _print_summary(results: dict[str, StageResult], run_id: str) -> None:
    """Print a final summary table to the console."""
    print()  # noqa: T201
    print(f"{'=' * 50}")  # noqa: T201
    print(f"  Pipeline Run: {run_id}")  # noqa: T201
    print(f"{'=' * 50}")  # noqa: T201

    status_symbols = {"success": "+", "error": "!", "skipped": "-"}

    for stage_name, result in results.items():
        symbol = status_symbols.get(result.status, "?")
        line = (
            f"  [{symbol}] {stage_name:<15} {result.duration:>6.1f}s  {result.status}"
        )
        if result.status == "error" and result.error:
            line += f"  ({result.error[:60]})"
        print(line)  # noqa: T201

    total_time = sum(r.duration for r in results.values())
    print(f"{'-' * 50}")  # noqa: T201
    print(f"  Total: {total_time:.1f}s")  # noqa: T201
    print()  # noqa: T201


# ---------------------------------------------------------------------------
# Router: intelligent mode dispatch
# ---------------------------------------------------------------------------

# Keywords that hint at intent (lowercase)
_ASK_HINTS = (
    "como",
    "how",
    "what",
    "why",
    "quando",
    "where",
    "explique",
    "explain",
    "o que e",
    "qual a diferenca",
    "por que",
    "what is",
    "diferenca entre",
)
_REVIEW_HINTS = (
    "review",
    "revisar",
    "checar",
    "verificar",
    "code review",
    "analise",
)
_EXPLORE_HINTS = (
    "explorar",
    "explore",
    "prototipo",
    "prototype",
    "testar ideia",
    "experimentar",
    "vibe",
    "playground",
)


@dataclass
class ClassifyResult:
    """Result from NLU classifier."""

    mode: str = "pipeline"
    codex_model: str = "gpt-5.3-codex"
    review_model: str = "sonnet"
    thinking_budget: int = 10000
    reasoning: str = ""


def _claude_env() -> dict[str, str]:
    """Build env for Claude CLI subprocess, stripping API key to force OAuth."""
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    return env


_STDIN_PROMPT_THRESHOLD = 20000  # chars — switch to stdin pipe above this


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract first JSON object from text, handling nested objects."""
    text = text.strip()
    decoder = json.JSONDecoder()
    # Try the whole string first
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    # Scan for first '{' and try to decode from there
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return None


def classify_intent_llm(
    task: str,
    project: Path,
    *,
    dry_run: bool = False,
) -> ClassifyResult:
    """Classify task intent using Claude Sonnet NLU.

    Uses --output-format text (fast) instead of --json-schema (slow).
    Falls back to keyword heuristics if the LLM call fails.
    """
    prompt_path = project / PROMPTS_DIR / "classify.txt"

    if not prompt_path.exists():
        logger.warning("Classify prompt not found, falling back to keywords")
        return ClassifyResult(mode=classify_intent(task))

    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    full_prompt = f"{prompt_text}\n\nTask: {task}"

    cmd = [
        "claude",
        "-p",
        full_prompt,
        "--output-format",
        "text",
        "--model",
        "sonnet",
    ]

    if dry_run:
        logger.info("[classify] Would execute: %s", " ".join(cmd[:6]))
        return ClassifyResult(mode=classify_intent(task))

    if not shutil.which("claude"):
        logger.warning("Claude CLI not found, falling back to keywords")
        return ClassifyResult(mode=classify_intent(task))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project),
            env=_claude_env(),
        )
    except subprocess.TimeoutExpired:
        logger.warning("NLU classify timed out (60s), falling back to keywords")
        return ClassifyResult(mode=classify_intent(task))

    if proc.returncode != 0:
        logger.warning(
            "NLU classify failed (exit %d), falling back to keywords", proc.returncode
        )
        return ClassifyResult(mode=classify_intent(task))

    result_data = _extract_json(proc.stdout)
    if result_data is None:
        logger.warning("NLU classify: no JSON in response, falling back to keywords")
        return ClassifyResult(mode=classify_intent(task))

    valid_modes = {"pipeline", "ask", "explore", "code", "review", "plan"}
    mode = result_data.get("mode", "pipeline")
    if mode not in valid_modes:
        mode = "pipeline"

    return ClassifyResult(
        mode=mode,
        codex_model=result_data.get("codex_model", "gpt-5.3-codex"),
        review_model=result_data.get("review_model", "sonnet"),
        thinking_budget=result_data.get("thinking_budget", 10000),
        reasoning=result_data.get("reasoning", ""),
    )


def classify_intent(task: str) -> str:
    """Classify task intent into a mode using keyword heuristics (fallback)."""
    lower = task.lower().strip()

    # Question patterns
    if lower.endswith("?") or any(lower.startswith(h) for h in _ASK_HINTS):
        return "ask"

    # Review patterns
    if any(h in lower for h in _REVIEW_HINTS):
        return "review"

    # Explore patterns
    if any(h in lower for h in _EXPLORE_HINTS):
        return "explore"

    # Short tasks (< 8 words, no "criar/adicionar/implementar") -> likely quick code
    words = lower.split()
    action_verbs = (
        "criar",
        "adicionar",
        "implementar",
        "migrar",
        "refatorar",
        "create",
        "add",
        "implement",
        "migrate",
        "refactor",
        "build",
    )
    if len(words) <= 7 and not any(v in lower for v in action_verbs):
        return "code"

    # Default: full pipeline
    return "pipeline"


def run_ask(task: str, config: PipelineConfig, project: Path) -> int:
    """Single-shot question via Claude (Sonnet by default)."""
    model = config.claude_ask_model
    cmd = [
        "claude",
        "-p",
        task,
        "--output-format",
        "text",
        "--model",
        model,
    ]
    logger.info("[ask] Sending to Claude (%s)", model)
    try:
        result = subprocess.run(
            cmd, cwd=str(project), text=True,
            env=_claude_env(), timeout=config.review_timeout,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        logger.error("[ask] Timeout after %ds", config.review_timeout)
        return 1


def run_chat(project: Path, config: PipelineConfig) -> int:
    """Launch interactive Claude session (Sonnet by default)."""
    model = config.claude_chat_model
    cmd = ["claude", "--model", model]
    logger.info("[chat] Starting interactive Claude (%s)", model)
    result = subprocess.run(cmd, cwd=str(project), env=_claude_env())
    return result.returncode


def run_plan(task: str, config: PipelineConfig, project: Path) -> int:
    """Deep planning via Claude Opus with high thinking budget."""
    model = config.claude_plan_model
    thinking = max(config.thinking_budget, 50000)
    cmd = [
        "claude",
        "-p",
        task,
        "--output-format",
        "text",
        "--model",
        model,
        "--thinking-budget-tokens",
        str(thinking),
        "--allowedTools",
        *_PLAN_ALLOWED_TOOLS,
    ]
    logger.info("[plan] Deep planning with Claude (%s, thinking=%d)", model, thinking)
    try:
        result = subprocess.run(
            cmd, cwd=str(project), text=True,
            env=_claude_env(), timeout=config.plan_timeout,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        logger.error("[plan] Timeout after %ds", config.plan_timeout)
        return 1


def run_explore(task: str, project: Path, config: PipelineConfig) -> int:
    """Launch Codex in suggest mode for prototyping."""
    cmd = ["codex", "--model", config.codex_model]
    if task:
        cmd.append(task)
    logger.info("[explore] Starting Codex suggest mode (%s)", config.codex_model)
    try:
        result = subprocess.run(cmd, cwd=str(project), timeout=config.implement_timeout)
        return result.returncode
    except subprocess.TimeoutExpired:
        logger.error("[explore] Timeout after %ds", config.implement_timeout)
        return 1


def _get_project_state_hash(project: Path) -> str:
    """Get SHA-256 of git state for a project directory (standalone helper)."""
    try:
        unstaged = subprocess.run(
            ["git", "diff"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=30,
        )
        staged = subprocess.run(
            ["git", "diff", "--staged"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = (unstaged.stdout or "") + (staged.stdout or "")
        return hashlib.sha256(combined.encode()).hexdigest()
    except (subprocess.SubprocessError, OSError):
        return uuid.uuid4().hex


def run_code(task: str, project: Path, config: PipelineConfig) -> int:
    """Direct Codex full-auto for quick implementation."""
    cmd = [
        "codex",
        "exec",
        task,
        "--full-auto",
        "--model",
        config.codex_model,
    ]
    logger.info("[code] Direct Codex exec (%s)", config.codex_model)

    pre_hash = _get_project_state_hash(project) if config.doom_loop_detection else ""

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project),
            text=True,
            timeout=config.implement_timeout,
        )

        if config.doom_loop_detection and pre_hash:
            post_hash = _get_project_state_hash(project)
            if pre_hash == post_hash:
                logger.warning(
                    "[code] No changes detected — possible stuck agent"
                )

        return result.returncode
    except subprocess.TimeoutExpired:
        logger.error("[code] Timeout after %ds", config.implement_timeout)
        return 1


# ---------------------------------------------------------------------------
# Unified CLI with subcommands
# ---------------------------------------------------------------------------


def build_root_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser with subcommands."""
    root = argparse.ArgumentParser(
        prog="aip",
        description="AI Pipeline: intelligent multi-model router",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            '  aip "task"                  Full pipeline (plan->implement->review)\n'
            '  aip ask "question"          Single-shot question via Claude (Sonnet)\n'
            "  aip chat                    Interactive Claude session (Sonnet)\n"
            '  aip plan "complex task"     Deep planning via Claude (Opus + thinking)\n'
            '  aip explore "idea"          Codex suggest mode (prototyping)\n'
            '  aip code "quick task"       Direct Codex full-auto\n'
            '  aip auto "anything"         NLU auto-classify intent and route\n'
            "\n"
            "Pipeline options:\n"
            '  aip --preset fast "task"    Use fast preset\n'
            "  aip --resume <id> --from-stage 2   Resume previous run\n"
        ),
    )

    sub = root.add_subparsers(dest="mode")

    # -- ask
    ask_p = sub.add_parser("ask", help="Single-shot question via Claude")
    ask_p.add_argument("task", help="Question to ask")
    ask_p.add_argument("--model", help="Claude model override")

    # -- chat
    chat_p = sub.add_parser("chat", help="Interactive Claude session")
    chat_p.add_argument("--model", help="Claude model override")

    # -- explore
    exp_p = sub.add_parser("explore", help="Codex suggest mode (prototyping)")
    exp_p.add_argument("task", nargs="?", default="", help="Optional starting prompt")
    exp_p.add_argument("--model", help="Codex model override")

    # -- code
    code_p = sub.add_parser("code", help="Direct Codex full-auto")
    code_p.add_argument("task", help="Task for Codex to implement")
    code_p.add_argument("--model", help="Codex model override")

    # -- plan
    plan_p = sub.add_parser("plan", help="Deep planning via Claude Opus")
    plan_p.add_argument("task", help="Task to plan")
    plan_p.add_argument("--model", help="Claude model override")

    # -- auto
    auto_p = sub.add_parser("auto", help="Auto-classify intent and route")
    auto_p.add_argument("task", help="Task description (auto-classified)")
    auto_p.add_argument("--dry-run", action="store_true", dest="auto_dry_run")

    # -- pipeline args (on root parser for backwards compat)
    root.add_argument("task", nargs="?", help="Task for pipeline")
    root.add_argument("--project", type=Path, default=Path.cwd())
    root.add_argument("--stage", choices=STAGES)
    root.add_argument("--resume", metavar="RUN_ID")
    root.add_argument("--from-stage", type=int, choices=[1, 2, 3, 4], default=1)
    root.add_argument("--base", default="main")
    root.add_argument("--dry-run", action="store_true")
    root.add_argument("--preset", choices=list(PRESETS.keys()))
    root.add_argument("--claude-plan-model")
    root.add_argument("--claude-review-model")
    root.add_argument("--codex-model")
    root.add_argument("--thinking-budget", type=int)
    root.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    root.add_argument("-v", "--verbose", action="store_true")
    root.add_argument(
        "--cleanup",
        type=int,
        metavar="N",
        help="Remove old runs, keeping N most recent",
    )

    return root


def _apply_model_override(mode: str, model: str, config: PipelineConfig) -> None:
    """Apply a --model override to the correct config field based on mode."""
    if mode in ("ask",):
        config.claude_ask_model = model
    elif mode in ("chat",):
        config.claude_chat_model = model
    elif mode in ("plan",):
        config.claude_plan_model = model
    elif mode in ("explore", "code"):
        config.codex_model = model
    elif mode in ("review",):
        config.claude_review_model = model


_KNOWN_MODES = {"ask", "chat", "explore", "code", "plan", "auto"}


def entry_point(argv: list[str] | None = None) -> int:
    """Unified entry point: routes to mode or pipeline.

    Handles the argparse subparser conflict: if the first positional arg
    is not a known mode, we bypass the root parser and go straight to
    the pipeline's main() function.
    """
    raw_args = argv if argv is not None else sys.argv[1:]

    # Detect if first non-flag arg is a known mode
    first_positional = next((a for a in raw_args if not a.startswith("-")), None)
    if first_positional and first_positional not in _KNOWN_MODES:
        # Not a subcommand → treat as pipeline task (original behavior)
        return main(raw_args)

    parser = build_root_parser()
    args = parser.parse_args(raw_args)

    # Logging
    _setup_logging(getattr(args, "verbose", False))

    project = getattr(args, "project", Path.cwd())
    if isinstance(project, Path):
        project = project.resolve()
    else:
        project = Path.cwd().resolve()

    # Load config
    config_path = project / PIPELINE_DIR / "config.toml"
    config = PipelineConfig.from_toml(config_path)

    # Apply model overrides from subcommands
    model_override = getattr(args, "model", None)
    preset = getattr(args, "preset", None)
    if preset:
        config.apply_preset(preset)
    if getattr(args, "claude_plan_model", None):
        config.claude_plan_model = args.claude_plan_model
    if getattr(args, "claude_review_model", None):
        config.claude_review_model = args.claude_review_model
    codex_override = getattr(args, "codex_model", None) or model_override
    if codex_override:
        config.codex_model = codex_override
    if getattr(args, "thinking_budget", None) is not None:
        config.thinking_budget = args.thinking_budget
    if getattr(args, "reasoning_effort", None):
        config.reasoning_effort = args.reasoning_effort

    mode = args.mode
    task = getattr(args, "task", None) or ""
    dry_run = getattr(args, "dry_run", False)
    cleanup = getattr(args, "cleanup", None)
    if cleanup is not None:
        _cleanup_old_runs(project / RUNS_DIR, keep=cleanup)
        if not mode and not task:
            return 0
    active_preset = preset or "balanced"

    # No mode and no task → launch interactive REPL
    if not mode and not task:
        from ai_pipeline_tui import run_repl

        return run_repl(config, project)

    # Apply --model override to the correct config field before status bar
    if model_override and mode:
        _apply_model_override(mode, model_override, config)

    # Render status bar for all non-REPL modes
    try:
        from ai_pipeline_tui import render_status_bar

        effective_mode = mode or "pipeline"
        render_status_bar(effective_mode, config, preset=active_preset)
    except ImportError:
        pass  # TUI module not available, continue without it

    # Route by explicit mode
    if mode == "ask":
        return run_ask(task, config, project)

    if mode == "chat":
        return run_chat(project, config)

    if mode == "plan":
        return run_plan(task, config, project)

    if mode == "explore":
        return run_explore(task, project, config)

    if mode == "code":
        return run_code(task, project, config)

    if mode == "auto":
        auto_dry = getattr(args, "auto_dry_run", False) or dry_run
        nlu = classify_intent_llm(task, project, dry_run=auto_dry)
        logger.info(
            "[auto] NLU → mode=%s codex=%s review=%s thinking=%d | %s",
            nlu.mode,
            nlu.codex_model,
            nlu.review_model,
            nlu.thinking_budget,
            nlu.reasoning,
        )

        # Apply NLU recommendations to config
        config.codex_model = nlu.codex_model
        config.claude_review_model = nlu.review_model
        config.thinking_budget = nlu.thinking_budget

        if nlu.mode == "ask":
            return run_ask(task, config, project)
        if nlu.mode == "plan":
            return run_plan(task, config, project)
        if nlu.mode == "explore":
            return run_explore(task, project, config)
        if nlu.mode == "review":
            return main(["--stage", "review", "--base", "main", task])
        if nlu.mode == "code":
            return run_code(task, project, config)
        # Default: full pipeline
        return main([task])

    # No subcommand with task -> original pipeline behavior
    return main(argv)


if __name__ == "__main__":
    sys.exit(entry_point())
