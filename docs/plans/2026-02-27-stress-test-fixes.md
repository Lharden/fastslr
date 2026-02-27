# AI Pipeline v2.1 Stress Test Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir todos os 11 findings do stress test (4 bugs + 7 categorias de falha) no ai_pipeline.py

**Architecture:** Todas as correcoes sao no ai_pipeline.py (~1638 linhas). As mudancas sao independentes entre si e seguem a ordem de severidade. Prompts longos serao passados via stdin pipe em vez de args CLI. Logging sera centralizado. Funcoes standalone ganham timeout e error handling.

**Tech Stack:** Python 3.12+ stdlib (subprocess, tempfile, logging, json, hashlib)

---

### Task 1: BUG-1 — Fix auto mode re-parse crash

**Files:**
- Modify: `ai_pipeline.py:1630`

**Step 1: Write the failing test**

```python
# tests/test_aip_bugs.py
import subprocess
import sys

def test_auto_pipeline_fallback_does_not_crash():
    """BUG-1: auto mode passing None to main() causes argparse crash."""
    result = subprocess.run(
        [sys.executable, "ai_pipeline.py", "auto", "--dry-run", "fix typo"],
        capture_output=True, text=True, timeout=30,
        cwd="C:/Users/Leonardo",
    )
    # Should not crash with 'unrecognized arguments'
    assert "unrecognized arguments" not in result.stderr
    assert result.returncode == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_aip_bugs.py::test_auto_pipeline_fallback_does_not_crash -v`
Expected: FAIL (argparse error: unrecognized arguments)

**Step 3: Write minimal fix**

In `ai_pipeline.py` line 1630, change:
```python
# BEFORE (broken):
return main(argv=None if argv is None else [task])

# AFTER (fixed):
return main([task])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_aip_bugs.py::test_auto_pipeline_fallback_does_not_crash -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ai_pipeline.py tests/test_aip_bugs.py
git commit -m "fix(auto): always pass [task] to main() instead of re-parsing sys.argv"
```

---

### Task 2: BUG-4 — Centralize logging setup

**Files:**
- Modify: `ai_pipeline.py:1007`, `ai_pipeline.py:1529`

**Step 1: Write the failing test**

```python
# tests/test_aip_bugs.py (append)
def test_verbose_flag_enables_debug_logging():
    """BUG-4: double basicConfig silences verbose mode."""
    result = subprocess.run(
        [sys.executable, "ai_pipeline.py", "--dry-run", "-v", "test task"],
        capture_output=True, text=True, timeout=30,
        cwd="C:/Users/Leonardo",
    )
    # With -v, should see DEBUG-level output
    assert "[DEBUG]" in result.stderr or result.returncode == 0
```

**Step 2: Run test to verify current behavior**

Run: `pytest tests/test_aip_bugs.py::test_verbose_flag_enables_debug_logging -v`

**Step 3: Write fix**

Add helper function before `main()`:
```python
_logging_configured = False

def _setup_logging(verbose: bool = False) -> None:
    """Configure logging once. Subsequent calls update level only."""
    global _logging_configured
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
```

Replace in `main()` lines 1006-1011:
```python
# BEFORE:
log_level = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(level=log_level, format=..., datefmt=...)

# AFTER:
_setup_logging(args.verbose)
```

Replace in `entry_point()` lines 1528-1533:
```python
# BEFORE:
log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
logging.basicConfig(level=log_level, format=..., datefmt=...)

# AFTER:
_setup_logging(getattr(args, "verbose", False))
```

**Step 4: Run test**

Run: `pytest tests/test_aip_bugs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(logging): centralize setup to prevent double basicConfig"
```

---

### Task 3: BUG-3 — Fix Windows 32k command line limit via stdin pipe

**Files:**
- Modify: `ai_pipeline.py` — `_execute_stage()`, `_compact_plan_output()`

**Step 1: Write the failing test**

```python
# tests/test_aip_bugs.py (append)
def test_long_prompt_does_not_exceed_cmdline_limit():
    """BUG-3: prompts > 32k chars crash on Windows."""
    import sys
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import Pipeline, PipelineConfig
    from pathlib import Path
    import tempfile

    config = PipelineConfig()
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".pipeline" / "runs").mkdir(parents=True)
        (p / ".pipeline" / "prompts").mkdir(parents=True)
        (p / ".pipeline" / "schemas").mkdir(parents=True)
        pipeline = Pipeline("x" * 40000, p, config, dry_run=True)
        # Should not raise OSError even with 40k char task
        result = pipeline.run(only_stage="plan")
        assert result["plan"].status == "skipped"  # dry run
```

**Step 2: Run test**

Run: `pytest tests/test_aip_bugs.py::test_long_prompt_does_not_exceed_cmdline_limit -v`

**Step 3: Write fix**

Add constant and helper after `_claude_env()`:
```python
_STDIN_PROMPT_THRESHOLD = 20000  # chars — switch to stdin pipe above this
```

Modify `_execute_stage()` to detect long prompts and pipe via stdin:
```python
def _execute_stage(self, stage_name, cmd, timeout):
    start = time.monotonic()
    if self.dry_run:
        ...  # unchanged

    tool_name = cmd[0]
    if not shutil.which(tool_name):
        ...  # unchanged

    # If prompt arg is too long, pipe via stdin instead
    stdin_data = None
    if len(" ".join(cmd)) > _STDIN_PROMPT_THRESHOLD:
        # Find the -p arg and extract the prompt
        try:
            p_idx = cmd.index("-p")
            prompt_text = cmd[p_idx + 1]
            cmd = cmd[:p_idx] + ["-p", "-"] + cmd[p_idx + 2:]
            stdin_data = prompt_text
        except (ValueError, IndexError):
            pass  # no -p flag, proceed normally

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
        ...  # unchanged
```

Apply same pattern to `_compact_plan_output()` and standalone functions.

**Step 4: Run tests**

Run: `pytest tests/test_aip_bugs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(subprocess): pipe long prompts via stdin to avoid Win32k limit"
```

---

### Task 4: BUG-2 — Fix `_extract_json()` for nested JSON

**Files:**
- Modify: `ai_pipeline.py:1162-1178`

**Step 1: Write the failing test**

```python
# tests/test_aip_bugs.py (append)
def test_extract_json_handles_nested_objects():
    """BUG-2: _extract_json regex fails on nested JSON."""
    import sys
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import _extract_json

    # Flat JSON — should work
    flat = '{"mode":"ask","reasoning":"simple"}'
    assert _extract_json(flat)["mode"] == "ask"

    # Nested JSON — was broken
    nested = '{"mode":"pipeline","meta":{"k":"v"},"reasoning":"complex"}'
    result = _extract_json(nested)
    assert result is not None
    assert result["mode"] == "pipeline"

    # JSON inside markdown code block
    md = 'Here is the result:\n```json\n{"mode":"code","reasoning":"quick"}\n```'
    assert _extract_json(md)["mode"] == "code"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_aip_bugs.py::test_extract_json_handles_nested_objects -v`
Expected: FAIL (nested case returns wrong object)

**Step 3: Write fix**

Replace `_extract_json()`:
```python
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
```

**Step 4: Run test**

Run: `pytest tests/test_aip_bugs.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(json): use raw_decode for robust nested JSON extraction"
```

---

### Task 5: Cat-1 — Add timeout + error handling to standalone modes

**Files:**
- Modify: `ai_pipeline.py` — `run_ask()`, `run_chat()`, `run_plan()`, `run_explore()`

**Step 1: Write test**

```python
# tests/test_aip_bugs.py (append)
def test_standalone_modes_have_timeout():
    """Cat-1: standalone modes should not hang forever."""
    import sys, inspect
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import run_ask, run_plan, run_explore
    # Check source code contains 'timeout' for each function
    for fn in (run_ask, run_plan, run_explore):
        src = inspect.getsource(fn)
        assert "timeout" in src, f"{fn.__name__} missing timeout"
        assert "TimeoutExpired" in src or "except" in src, f"{fn.__name__} missing error handling"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_aip_bugs.py::test_standalone_modes_have_timeout -v`
Expected: FAIL

**Step 3: Write fix for each function**

`run_ask()`:
```python
def run_ask(task: str, config: PipelineConfig, project: Path) -> int:
    model = config.claude_ask_model
    cmd = ["claude", "-p", task, "--output-format", "text", "--model", model]
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
```

`run_plan()`:
```python
def run_plan(task: str, config: PipelineConfig, project: Path) -> int:
    model = config.claude_plan_model
    thinking = max(config.thinking_budget, 50000)
    cmd = [
        "claude", "-p", task, "--output-format", "text",
        "--model", model, "--thinking-budget-tokens", str(thinking),
        "--allowedTools", *_PLAN_ALLOWED_TOOLS,
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
```

`run_explore()`:
```python
def run_explore(task: str, project: Path, config: PipelineConfig) -> int:
    cmd = ["codex", "--model", config.codex_model]
    if task:
        cmd.append(task)
    logger.info("[explore] Starting Codex suggest mode (%s)", config.codex_model)
    try:
        result = subprocess.run(
            cmd, cwd=str(project), timeout=config.implement_timeout,
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        logger.error("[explore] Timeout after %ds", config.implement_timeout)
        return 1
```

Note: `run_chat()` is interactive (stdin) — timeout doesn't apply. Keep as-is.

**Step 4: Run tests**

Run: `pytest tests/test_aip_bugs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(modes): add timeout and error handling to standalone run functions"
```

---

### Task 6: Cat-2 — Git repo existence check

**Files:**
- Modify: `ai_pipeline.py` — `Pipeline.__init__()` or `Pipeline.run()`

**Step 1: Write test**

```python
# tests/test_aip_bugs.py (append)
def test_pipeline_warns_on_no_git_repo(tmp_path, caplog):
    """Cat-2: pipeline should warn if not in a git repo."""
    import sys
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import Pipeline, PipelineConfig
    import logging

    config = PipelineConfig(auto_branch=True, auto_commit=True)
    (tmp_path / ".pipeline" / "runs").mkdir(parents=True)
    (tmp_path / ".pipeline" / "prompts").mkdir(parents=True)
    (tmp_path / ".pipeline" / "schemas").mkdir(parents=True)

    pipeline = Pipeline("test task", tmp_path, config, dry_run=True)
    with caplog.at_level(logging.WARNING):
        pipeline.run(only_stage="plan")
    assert any("git" in r.message.lower() for r in caplog.records)
```

**Step 2: Run test**

Run: `pytest tests/test_aip_bugs.py::test_pipeline_warns_on_no_git_repo -v`

**Step 3: Write fix**

Add method to Pipeline and call it in `run()`:
```python
def _check_git_repo(self) -> None:
    """Warn if project is not a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(self.project),
            capture_output=True, check=True, timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.SubprocessError):
        logger.warning(
            "Project %s is not a git repository. "
            "Git features (branch, commit, diff, doom loop) will be skipped.",
            self.project,
        )
        self.config.auto_branch = False
        self.config.auto_commit = False
```

Call at start of `run()`:
```python
def run(self, from_stage=1, only_stage=None):
    self.run_dir.mkdir(parents=True, exist_ok=True)
    self._check_git_repo()
    self._save_metadata()
    ...
```

**Step 4: Run tests**

Run: `pytest tests/test_aip_bugs.py -v`

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(git): check repo existence and disable git features gracefully"
```

---

### Task 7: Cat-3 — Replace `git add -A` with `git add -u`

**Files:**
- Modify: `ai_pipeline.py:686`

**Step 1: Write test**

```python
# tests/test_aip_bugs.py (append)
def test_commit_uses_git_add_u_not_A():
    """Cat-3: git add -A can stage secrets, use -u instead."""
    import sys, inspect
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import Pipeline
    src = inspect.getsource(Pipeline._commit_changes)
    assert "git\", \"add\", \"-u\"" in src or '"-u"' in src
    assert '"-A"' not in src
```

**Step 2: Run test — expected FAIL**

**Step 3: Write fix**

```python
# Line 686: change "-A" to "-u"
["git", "add", "-u"],
```

**Step 4: Run test — expected PASS**

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(git): use git add -u to avoid staging untracked/secret files"
```

---

### Task 8: Cat-4 — Auto-detect base branch

**Files:**
- Modify: `ai_pipeline.py` — add `_detect_base_branch()`, use in `__init__`

**Step 1: Write test**

```python
# tests/test_aip_bugs.py (append)
def test_detect_base_branch(tmp_path):
    """Cat-4: auto-detect main vs master."""
    import subprocess, sys
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import _detect_base_branch

    # Create repo with 'master' branch
    subprocess.run(["git", "init", "-b", "master"], cwd=str(tmp_path),
                    capture_output=True, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                    cwd=str(tmp_path), capture_output=True,
                    env={**__import__("os").environ, "GIT_AUTHOR_NAME": "t",
                         "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                         "GIT_COMMITTER_EMAIL": "t@t"})
    assert _detect_base_branch(tmp_path) == "master"
```

**Step 2: Run test — expected FAIL (function doesn't exist)**

**Step 3: Write fix**

Add module-level function:
```python
def _detect_base_branch(project: Path) -> str:
    """Detect the default branch name (main or master)."""
    for candidate in ("main", "master"):
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=str(project), capture_output=True,
                check=True, timeout=10,
            )
            return candidate
        except (subprocess.CalledProcessError, subprocess.SubprocessError):
            continue
    return "main"  # fallback
```

Modify `Pipeline.__init__`:
```python
# BEFORE:
self.base_branch = base_branch

# AFTER:
self.base_branch = base_branch if base_branch != "main" else _detect_base_branch(self.project)
```

**Step 4: Run tests**

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(git): auto-detect main vs master as base branch"
```

---

### Task 9: Cat-5 — Handle lists in env var substitution

**Files:**
- Modify: `ai_pipeline.py:66-79`

**Step 1: Write test**

```python
# tests/test_aip_bugs.py (append)
def test_env_substitution_handles_lists():
    """Cat-5: _substitute_env_vars should recurse into lists."""
    import sys, os
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import _substitute_env_vars

    os.environ["TEST_ITEM"] = "resolved"
    data = {"tools": ["{env:TEST_ITEM}", "static", "{env:MISSING:fallback}"]}
    result = _substitute_env_vars(data)
    assert result["tools"] == ["resolved", "static", "fallback"]
```

**Step 2: Run test — expected FAIL**

**Step 3: Write fix**

Add list handling to `_substitute_env_vars`:
```python
def _substitute_env_vars(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _substitute_env_vars(value)
        elif isinstance(value, list):
            result[key] = [
                _ENV_VAR_PATTERN.sub(
                    lambda m: os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else m.group(0)),
                    item,
                ) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, str):
            result[key] = _ENV_VAR_PATTERN.sub(
                lambda m: os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else m.group(0)),
                value,
            )
        else:
            result[key] = value
    return result
```

**Step 4: Run tests — expected PASS**

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(config): handle list values in env var substitution"
```

---

### Task 10: Cat-6 — Error on missing prompt templates

**Files:**
- Modify: `ai_pipeline.py:884-890`

**Step 1: Write test**

```python
# tests/test_aip_bugs.py (append)
def test_missing_prompt_raises_error(tmp_path):
    """Cat-6: missing prompt template should not silently return empty string."""
    import sys
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import Pipeline, PipelineConfig
    import pytest

    config = PipelineConfig()
    (tmp_path / ".pipeline" / "runs").mkdir(parents=True)
    (tmp_path / ".pipeline" / "prompts").mkdir(parents=True)
    (tmp_path / ".pipeline" / "schemas").mkdir(parents=True)
    # Don't create plan.txt — it should error

    pipeline = Pipeline("test", tmp_path, config, dry_run=True)
    # Should warn loudly, not silently return ""
    result = pipeline.run(only_stage="plan")
    # At minimum, the prompt should contain a fallback
    assert result["plan"].command  # should still have a valid command
```

**Step 2: Run test**

**Step 3: Write fix**

Add fallback prompts and warning:
```python
_FALLBACK_PROMPTS: dict[str, str] = {
    "plan.txt": "Analyze the codebase and create an implementation plan for the following task.",
    "implement.txt": "Implement the following plan exactly as specified.",
    "review.txt": "Review the implementation against the original plan.",
    "classify.txt": "",
}


def _load_prompt(self, filename: str) -> str:
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
```

**Step 4: Run tests**

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "fix(prompts): add fallback prompts when templates are missing"
```

---

### Task 11: Cat-7 — Add runs cleanup

**Files:**
- Modify: `ai_pipeline.py` — add `--cleanup` arg and `_cleanup_old_runs()`

**Step 1: Write test**

```python
# tests/test_aip_bugs.py (append)
def test_cleanup_old_runs(tmp_path):
    """Cat-7: cleanup should keep only N most recent runs."""
    import sys
    sys.path.insert(0, "C:/Users/Leonardo")
    from ai_pipeline import _cleanup_old_runs

    runs_dir = tmp_path / ".pipeline" / "runs"
    runs_dir.mkdir(parents=True)
    # Create 5 fake run directories
    import time
    for i in range(5):
        d = runs_dir / f"run-{i:03d}"
        d.mkdir()
        (d / "metadata.json").write_text("{}")
        time.sleep(0.05)  # ensure different mtime

    _cleanup_old_runs(runs_dir, keep=3)
    remaining = sorted(runs_dir.iterdir())
    assert len(remaining) == 3
    # Should keep the 3 most recent (002, 003, 004)
    assert remaining[-1].name == "run-004"
```

**Step 2: Run test — expected FAIL**

**Step 3: Write fix**

Add function:
```python
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
```

Add CLI argument in `build_root_parser()`:
```python
root.add_argument("--cleanup", type=int, metavar="N",
                  help="Remove old runs, keeping N most recent")
```

Handle in `entry_point()` before mode routing:
```python
cleanup = getattr(args, "cleanup", None)
if cleanup is not None:
    _cleanup_old_runs(project / RUNS_DIR, keep=cleanup)
    if not task and not mode:
        return 0
```

Also add auto-cleanup at end of `Pipeline.run()`:
```python
# Auto-cleanup: keep last 20 runs
_cleanup_old_runs(self.project / RUNS_DIR, keep=20)
```

**Step 4: Run tests**

Run: `pytest tests/test_aip_bugs.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add ai_pipeline.py
git commit -m "feat(cleanup): add --cleanup flag and auto-prune old pipeline runs"
```

---

### Task 12: Final verification

**Step 1: Run all tests**

```bash
pytest tests/test_aip_bugs.py -v
```

**Step 2: Run syntax check**

```bash
python -c "import py_compile; py_compile.compile('ai_pipeline.py', doraise=True)"
```

**Step 3: Run dry-run smoke test**

```bash
python ai_pipeline.py --dry-run --preset fast -v "test task"
python ai_pipeline.py auto --dry-run "fix typo"
```

**Step 4: Commit final state**

```bash
git add -A
git commit -m "test: add stress test validation suite for all 11 findings"
```
