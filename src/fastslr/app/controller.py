"""FastSLR App Controller — shared orchestration for CLI and TUI.

This is the single point of contact between the application layer (CLI/TUI)
and the core engine. Neither CLI nor TUI should import from core directly.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..core.config import (
    get_domain_blocks,
    load_config,
    load_global_params,
    parse_terms_csv,
)
from ..core.constants import VERSION
from ..core.coverage import (
    TermCoverageReport,
    analyze_term_coverage,
    export_coverage_csv,
)
from ..core.engine import process_articles, sample_articles
from ..core.io import (
    build_protocol_snapshot,
    compute_config_hash,
    compute_file_hash,
    export_appendix_pack,
    export_config_audit,
    export_protocol_snapshot,
    export_results,
    generate_academic_report,
    generate_report,
    load_csv_safe,
)
from ..core.normalization import NormalizationEngine
from ..core.patterns import precompile_patterns
from ..core.presets import generate_config

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ValidationIssue:
    """A configuration validation issue."""

    level: str  # "error", "warning"
    message: str


@dataclass
class TriageResult:
    """Result of a triage run."""

    result_df: pd.DataFrame
    stats: dict
    config: dict
    output_dir: Path
    result_path: Path | None = None


@dataclass
class PreviewResult:
    """Result of a preview/dry-run."""

    result_df: pd.DataFrame
    stats: dict
    sample_size: int


@dataclass
class DiffEntry:
    """A single article that changed between two runs."""

    article_id: str
    old_decision: str
    new_decision: str
    old_score: float | None = None
    new_score: float | None = None


@dataclass
class DiffReport:
    """Comparison between two triage runs."""

    changed: list[DiffEntry] = field(default_factory=list)
    total_a: int = 0
    total_b: int = 0
    summary: dict[str, int] = field(default_factory=dict)


@dataclass
class ProfileInfo:
    """Metadata about a saved profile."""

    name: str
    path: Path
    description: str = ""


# ── Configuration & Validation ───────────────────────────────────────────────


def validate_config(config: dict) -> list[ValidationIssue]:
    """Check configuration for common issues."""
    issues: list[ValidationIssue] = []

    if "global" not in config:
        issues.append(ValidationIssue("error", "Missing 'global' section"))

    domain_blocks = get_domain_blocks(config)
    if not domain_blocks:
        issues.append(ValidationIssue("warning", "No domain blocks defined"))

    for block_name in domain_blocks:
        if block_name not in config:
            issues.append(ValidationIssue("error", f"Block '{block_name}' listed but not defined"))
            continue
        block = config[block_name]
        positives = block.get("positives", [])
        if not positives:
            issues.append(ValidationIssue("warning", f"Block '{block_name}' has no positive terms"))

    global_cfg = config.get("global", {})
    policy = global_cfg.get("DECISION_POLICY", "special")
    if policy not in ("special", "strict", "k_of_n"):
        issues.append(ValidationIssue("error", f"Unknown decision policy: '{policy}'"))

    # Warn about nonsensical threshold values
    for key in ("LIMITES_APROVADO", "LIMITES_SINALIZADO"):
        thresholds = global_cfg.get(key, {})
        for level, value in thresholds.items():
            if value is not None and isinstance(value, (int, float)) and value < 0:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"Negative threshold in {key}[{level}]: {value}",
                    )
                )

    # Surface parse errors from terms CSV (logic contradictions — block run)
    for msg in config.get("_parse_errors", []):
        issues.append(ValidationIssue("error", msg))

    # Surface parse warnings from terms CSV
    for msg in config.get("_parse_warnings", []):
        issues.append(ValidationIssue("warning", msg))

    return issues


def _prepare_config(config_path: Path, terms_path: Path | None = None) -> dict:
    """Load and prepare a full configuration (config + terms + patterns)."""
    config = load_config(config_path)

    if terms_path is not None:
        config = parse_terms_csv(terms_path, config)

    norm_rules = config.get("normalization_rules", {})
    norm_engine = NormalizationEngine(norm_rules)
    global_params = load_global_params(config.get("global", {}))

    compile_warnings: list[str] = config.get("_parse_warnings", [])

    for block_name in get_domain_blocks(config):
        if block_name in config:
            config[block_name] = precompile_patterns(
                config[block_name], norm_engine, global_params,
                block_name=block_name, warnings=compile_warnings,
            )
            config[block_name]["normalization_engine"] = norm_engine

    if "T0" in config:
        config["T0"] = precompile_patterns(
            config["T0"], norm_engine, global_params,
            block_name="T0", warnings=compile_warnings,
        )

    config["_parse_warnings"] = compile_warnings

    return config


# ── Triage ───────────────────────────────────────────────────────────────────


def run_triage(
    input_path: Path,
    config_path: Path,
    terms_path: Path | None = None,
    output_dir: Path | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> TriageResult:
    """Execute a full triage run."""
    config = _prepare_config(config_path, terms_path)
    df = load_csv_safe(input_path)

    if output_dir is None:
        output_dir = input_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    result_df, stats = process_articles(df, config, on_progress=on_progress)

    # Export results
    result_path = output_dir / "triage_results.xlsx"
    export_results(result_df, result_path, config)

    # Export report
    report_path = output_dir / "triage_report.txt"
    generate_report(result_df, stats, config, report_path)

    # Export config audit
    audit_path = output_dir / "config_audit.json"
    export_config_audit(config, audit_path)

    # Protocol snapshot
    config_hash = compute_config_hash(config)
    input_hash = compute_file_hash(str(input_path))
    terms_hash = compute_file_hash(str(terms_path)) if terms_path else "n/a"

    snapshot = build_protocol_snapshot(
        config=config,
        stats=stats,
        input_path=input_path,
        terms_path=terms_path or Path("n/a"),
        result_path=result_path,
        input_hash=input_hash,
        terms_hash=terms_hash,
        config_hash=config_hash,
    )

    protocol_path = output_dir / "protocol.json"
    export_protocol_snapshot(snapshot, protocol_path)

    # Academic report
    academic_path = output_dir / "academic_report.md"
    generate_academic_report(snapshot, academic_path)

    return TriageResult(
        result_df=result_df,
        stats=stats,
        config=config,
        output_dir=output_dir,
        result_path=result_path,
    )


def preview_triage(
    input_path: Path,
    config_path: Path,
    terms_path: Path | None = None,
    sample_size: int = 50,
    seed: int | None = 42,
) -> PreviewResult:
    """Run triage on a sample for validation."""
    config = _prepare_config(config_path, terms_path)
    df = load_csv_safe(input_path)
    sample_df = sample_articles(df, sample_size, seed=seed)
    result_df, stats = process_articles(sample_df, config)
    return PreviewResult(
        result_df=result_df,
        stats=stats,
        sample_size=len(sample_df),
    )


# ── Coverage ─────────────────────────────────────────────────────────────────


def analyze_coverage(
    input_path: Path,
    config_path: Path,
    terms_path: Path | None = None,
    output_path: Path | None = None,
) -> TermCoverageReport:
    """Run triage and analyze term coverage."""
    config = _prepare_config(config_path, terms_path)
    df = load_csv_safe(input_path)
    result_df, _ = process_articles(df, config)
    report = analyze_term_coverage(result_df, config)

    if output_path:
        export_coverage_csv(report, output_path)

    return report


# ── Diff ─────────────────────────────────────────────────────────────────────


def diff_results(path_a: Path, path_b: Path) -> DiffReport:
    """Compare two triage result files and find changed decisions."""
    df_a = pd.read_excel(path_a) if path_a.suffix == ".xlsx" else pd.read_csv(path_a)
    df_b = pd.read_excel(path_b) if path_b.suffix == ".xlsx" else pd.read_csv(path_b)

    # Validate that both files have Final_Decision
    if "Final_Decision" not in df_a.columns:
        raise ValueError(f"File A is missing 'Final_Decision' column: {path_a}")
    if "Final_Decision" not in df_b.columns:
        raise ValueError(f"File B is missing 'Final_Decision' column: {path_b}")

    # Find the ID column
    id_col = None
    for candidate in ("ID", "id", "Key", "key"):
        if candidate in df_a.columns and candidate in df_b.columns:
            id_col = candidate
            break

    if id_col is None:
        id_col = df_a.columns[0]

    report = DiffReport(total_a=len(df_a), total_b=len(df_b))

    merged = pd.merge(
        df_a[[id_col, "Final_Decision"]],
        df_b[[id_col, "Final_Decision"]],
        on=id_col,
        suffixes=("_a", "_b"),
        how="outer",
    )

    for _, row in merged.iterrows():
        old = str(row.get("Final_Decision_a", "MISSING"))
        new = str(row.get("Final_Decision_b", "MISSING"))
        if old != new:
            report.changed.append(
                DiffEntry(
                    article_id=str(row[id_col]),
                    old_decision=old,
                    new_decision=new,
                )
            )

    # Summarize transitions
    transitions: dict[str, int] = {}
    for entry in report.changed:
        key = f"{entry.old_decision} -> {entry.new_decision}"
        transitions[key] = transitions.get(key, 0) + 1
    report.summary = transitions

    return report


# ── Project ──────────────────────────────────────────────────────────────────


def create_project(
    name: str,
    blocks: list[dict],
    preset: str = "standard",
    output_dir: Path | None = None,
) -> Path:
    """Create a new project with config.json and terms template."""
    if output_dir is None:
        output_dir = Path.cwd() / name

    output_dir.mkdir(parents=True, exist_ok=True)

    config = generate_config(preset_name=preset, blocks=blocks)

    config_path = output_dir / "config.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Generate terms CSV template
    terms_rows: list[dict] = []
    for block in blocks:
        block_name = block["name"]
        terms_rows.append(
            {
                "block": block_name,
                "kind": "pos",
                "term": f"example term for {block_name}",
                "level": "1",
                "section_scope": "any",
                "is_regex": "0",
                "normalization_type": "",
                "normalization_target": "",
            }
        )

    # Add example with abbreviation normalization
    if blocks:
        terms_rows.append(
            {
                "block": blocks[0]["name"],
                "kind": "pos",
                "term": "example abbreviation",
                "level": "2",
                "section_scope": "any",
                "is_regex": "0",
                "normalization_type": "abbreviation",
                "normalization_target": "example expanded form",
            }
        )

    # Add a GLOBAL anti-term example
    terms_rows.append(
        {
            "block": "GLOBAL",
            "kind": "anti",
            "term": "systematic review",
            "level": "",
            "section_scope": "any",
            "is_regex": "0",
            "normalization_type": "",
            "normalization_target": "",
        }
    )

    terms_df = pd.DataFrame(terms_rows)
    terms_path = output_dir / "terms.csv"
    terms_df.to_csv(terms_path, sep=";", index=False, encoding="utf-8-sig")

    return output_dir


# ── Export ───────────────────────────────────────────────────────────────────


def export_academic_package(
    result_path: Path,
    output_dir: Path,
    config_path: Path | None = None,
) -> Path:
    """Create an academic package ZIP from existing results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, Path] = {"results": result_path}

    # Collect protocol and report if they exist alongside results
    result_dir = result_path.parent
    for name, filename in (
        ("protocol", "protocol.json"),
        ("report", "triage_report.txt"),
        ("academic", "academic_report.md"),
        ("audit", "config_audit.json"),
    ):
        candidate = result_dir / filename
        if candidate.exists():
            artifacts[name] = candidate

    if config_path and config_path.exists():
        artifacts["config"] = config_path

    zip_path = output_dir / "academic_package.zip"
    execution_id = f"fastslr_v{VERSION}"

    export_appendix_pack(artifacts, zip_path, execution_id)

    return zip_path


# ── Browse Terms ─────────────────────────────────────────────────────────────


@dataclass
class TermsView:
    """Structured view of all configured terms."""

    terms: list[dict] = field(default_factory=list)
    total: int = 0
    blocks: list[str] = field(default_factory=list)


def browse_terms(
    config_path: Path,
    terms_path: Path | None = None,
    block_filter: str | None = None,
    kind_filter: str | None = None,
) -> TermsView:
    """Load and return a structured view of all configured terms."""
    config = load_config(config_path)
    if terms_path:
        config = parse_terms_csv(terms_path, config)

    domain_blocks = get_domain_blocks(config)
    all_terms: list[dict] = []

    target_blocks = [block_filter] if block_filter else domain_blocks
    if not block_filter and "T0" in config:
        target_blocks.append("T0")

    for block_name in target_blocks:
        if block_name not in config:
            continue
        block = config[block_name]

        for entry in block.get("positives", []):
            if kind_filter and kind_filter != "pos":
                continue
            all_terms.append(
                {
                    "block": block_name,
                    "kind": "pos",
                    "term": entry.get("term", ""),
                    "level": entry.get("level"),
                    "scope": entry.get("scope", "any"),
                }
            )

        anti = block.get("anti", {})
        for entry in anti.get("exclude", []):
            if kind_filter and kind_filter != "anti":
                continue
            all_terms.append(
                {
                    "block": block_name,
                    "kind": "anti",
                    "term": entry.get("term", ""),
                    "level": None,
                    "scope": entry.get("scope", "any"),
                }
            )

        for entry in anti.get("flag", []):
            if kind_filter and kind_filter != "flag":
                continue
            all_terms.append(
                {
                    "block": block_name,
                    "kind": "flag",
                    "term": entry.get("term", ""),
                    "level": None,
                    "scope": entry.get("scope", "any"),
                }
            )

    return TermsView(terms=all_terms, total=len(all_terms), blocks=domain_blocks)


__all__ = [
    "ValidationIssue",
    "TriageResult",
    "PreviewResult",
    "DiffEntry",
    "DiffReport",
    "ProfileInfo",
    "TermsView",
    "validate_config",
    "run_triage",
    "preview_triage",
    "analyze_coverage",
    "diff_results",
    "create_project",
    "export_academic_package",
    "browse_terms",
]
