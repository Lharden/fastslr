"""Pre-freeze audit of FastSLR v3.0.0: packaging defect F10.

``config_v8.json`` asks for the ``xlsxwriter`` engine, which v3.0.0 did not
declare (a clean install failed), and no lock file pinned the environment.
"""

from __future__ import annotations

from pathlib import Path

# ── F10: xlsxwriter undeclared; no lock file ─────────────────────────────────


class TestF10Packaging:
    ROOT = Path(__file__).resolve().parent.parent

    def test_xlsxwriter_is_declared(self):
        import tomllib

        data = tomllib.loads((self.ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        deps = data["project"]["dependencies"]
        assert any(d.lower().startswith("xlsxwriter") for d in deps)

    def test_lock_file_pins_xlsxwriter(self):
        lock = self.ROOT / "uv.lock"
        assert lock.is_file()
        assert 'name = "xlsxwriter"' in lock.read_text(encoding="utf-8")
