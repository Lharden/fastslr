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
    format_coverage_report,
)
from ..core.engine import process_articles, resolve_field_columns, sample_articles
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
    get_export_opts,
    load_table_safe,
    read_result_table,
)
from ..core.normalization import NormalizationEngine
from ..core.patterns import precompile_patterns
from ..core.presets import generate_config

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Return the application version."""
    return VERSION


def format_coverage(report: TermCoverageReport) -> str:
    """Format a coverage report for CLI/TUI display."""
    return format_coverage_report(report)


def read_results_table(path: Path) -> pd.DataFrame:
    """Read a result table using the same rules as diff/export workflows."""
    return read_result_table(path)


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
    artifact_paths: dict[str, Path] = field(default_factory=dict)
    academic_package_path: Path | None = None


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


@dataclass
class SetupInspection:
    """Human-readable setup inspection for a planned triage run."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    input_rows: int | None = None
    input_columns: list[str] = field(default_factory=list)
    field_mapping: dict[str, str | None] = field(default_factory=dict)
    domain_blocks: list[str] = field(default_factory=list)
    terms_count: int | None = None
    output_dir: Path | None = None
    run_command: str | None = None


# ── Configuration & Validation ───────────────────────────────────────────────


def validate_config(config: dict) -> list[ValidationIssue]:
    """Check configuration for common issues."""
    issues: list[ValidationIssue] = []

    if "global" not in config:
        issues.append(ValidationIssue("error", "Missing 'global' section"))

    domain_blocks = get_domain_blocks(config)
    if not domain_blocks:
        issues.append(
            ValidationIssue(
                "error",
                "No domain blocks defined. Add BLOCK_ORDER in config.json or provide a terms file "
                "with at least one non-GLOBAL block.",
            )
        )

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

    # Surface parse errors from terms table (logic contradictions — block run)
    for msg in config.get("_parse_errors", []):
        issues.append(ValidationIssue("error", msg))

    # Surface parse warnings from terms table
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
                config[block_name],
                norm_engine,
                global_params,
                block_name=block_name,
                warnings=compile_warnings,
            )
            config[block_name]["normalization_engine"] = norm_engine

    if "T0" in config:
        config["T0"] = precompile_patterns(
            config["T0"],
            norm_engine,
            global_params,
            block_name="T0",
            warnings=compile_warnings,
        )

    config["_parse_warnings"] = compile_warnings

    return config


def _cmd_path(path: Path) -> str:
    text = str(path)
    if " " in text:
        return f'"{text}"'
    return text


def inspect_run_setup(
    input_path: Path | None = None,
    config_path: Path | None = None,
    terms_path: Path | None = None,
    output_dir: Path | None = None,
) -> SetupInspection:
    """Inspect files and configuration before a run and return actionable guidance."""
    inspection = SetupInspection(ok=True, output_dir=output_dir)

    if input_path is None and config_path is None and terms_path is None:
        inspection.messages.extend(
            [
                "Create a project: fastslr new-project my-review --blocks CTX,TECH,SCM",
                "Fill terms.xlsx with block, kind, term, level, section_scope and is_regex.",
                "Check files: fastslr doctor --input articles.csv -c config.json -t terms.xlsx",
                "Run triage: fastslr run articles.csv -c config.json -t terms.xlsx",
            ]
        )
        return inspection

    config: dict = {}
    if config_path is not None:
        if not config_path.exists():
            inspection.errors.append(f"Config file not found: {config_path}")
        else:
            try:
                config = _prepare_config(config_path, terms_path)
                for issue in validate_config(config):
                    if issue.level == "error":
                        inspection.errors.append(issue.message)
                    else:
                        inspection.warnings.append(issue.message)
                inspection.domain_blocks = get_domain_blocks(config)
                inspection.terms_count = config.get("_valid_terms_count")
            except Exception as exc:
                inspection.errors.append(f"Could not load config/terms: {exc}")

    if input_path is not None:
        if not input_path.exists():
            inspection.errors.append(f"Input file not found: {input_path}")
        else:
            try:
                df = load_table_safe(input_path)
                inspection.input_rows = len(df)
                inspection.input_columns = [str(c) for c in df.columns]
                fields = config.get("fields", {}) if config else {}
                inspection.field_mapping = resolve_field_columns(df, fields)

                for required in ("id", "title", "abstract"):
                    if inspection.field_mapping.get(required) is None:
                        inspection.warnings.append(
                            f"Could not identify the '{required}' column. "
                            f"Set fields.{required} in config.json."
                        )
            except Exception as exc:
                inspection.errors.append(f"Could not load input table: {exc}")

    if terms_path is not None and not terms_path.exists():
        inspection.errors.append(f"Terms file not found: {terms_path}")

    if output_dir is None and input_path is not None:
        inspection.output_dir = input_path.parent / "output"

    if input_path is not None and config_path is not None:
        parts = ["fastslr", "run", _cmd_path(input_path), "-c", _cmd_path(config_path)]
        if terms_path is not None:
            parts.extend(["-t", _cmd_path(terms_path)])
        if output_dir is not None:
            parts.extend(["-o", _cmd_path(output_dir)])
        inspection.run_command = " ".join(parts)

    inspection.ok = not inspection.errors
    return inspection


# ── Triage ───────────────────────────────────────────────────────────────────


def run_triage(
    input_path: Path,
    config_path: Path,
    terms_path: Path | None = None,
    output_dir: Path | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> TriageResult:
    """Execute a full triage run.

    Raises ``ValueError`` when the input corpus has zero data rows (e.g. a
    header-only CSV). Producing an empty academic package / report with
    ``TOTAL ARTICLES: 0`` while reporting success silently misleads a user who
    exported the wrong corpus, so the run is aborted with a clear message
    before any artifact is written.
    """
    config = _prepare_config(config_path, terms_path)
    df = load_table_safe(input_path)

    if len(df) == 0:
        raise ValueError(
            f"O corpus de entrada nao contem nenhum artigo (0 linhas): "
            f"{input_path}. Verifique se o arquivo exportado esta correto."
        )

    if output_dir is None:
        output_dir = input_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    result_df, stats = process_articles(df, config, on_progress=on_progress)

    # Export results
    exported_results = export_results(result_df, output_dir / "triage_results", config)
    result_path = exported_results.get("xlsx") or exported_results.get("csv")
    if result_path is None:
        raise RuntimeError("No result file was exported.")

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

    artifact_paths: dict[str, Path] = {
        **{f"results_{fmt}": path for fmt, path in exported_results.items()},
        "report": report_path,
        "audit": audit_path,
        "protocol": protocol_path,
        "academic_report": academic_path,
    }

    academic_package_path: Path | None = None
    if get_export_opts(config)["academic_package"]:
        academic_package_path = output_dir / "academic_package.zip"
        export_appendix_pack(artifact_paths, academic_package_path, snapshot["execution_id"])
        artifact_paths["academic_package"] = academic_package_path

    return TriageResult(
        result_df=result_df,
        stats=stats,
        config=config,
        output_dir=output_dir,
        result_path=result_path,
        artifact_paths=artifact_paths,
        academic_package_path=academic_package_path,
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
    df = load_table_safe(input_path)
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
    df = load_table_safe(input_path)
    result_df, _ = process_articles(df, config)
    report = analyze_term_coverage(result_df, config)

    if output_path:
        export_coverage_csv(report, output_path)

    return report


# ── Diff ─────────────────────────────────────────────────────────────────────


def diff_results(path_a: Path, path_b: Path) -> DiffReport:
    """Compare two triage result files and find changed decisions."""
    df_a = read_result_table(path_a)
    df_b = read_result_table(path_b)

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
        # No shared canonical ID column. Fall back to the first column of A,
        # but only if it also exists in B; otherwise the merge would raise a
        # raw KeyError on a column missing from B.
        fallback = df_a.columns[0] if len(df_a.columns) else None
        if fallback is not None and fallback in df_b.columns:
            id_col = fallback
        else:
            raise ValueError(
                "Nenhuma coluna de ID comum encontrada entre os dois arquivos "
                "(esperado uma de: ID, id, Key, key). "
                f"Colunas de A: {list(df_a.columns)}; colunas de B: {list(df_b.columns)}."
            )

    report = DiffReport(total_a=len(df_a), total_b=len(df_b))

    merged = pd.merge(
        df_a[[id_col, "Final_Decision"]],
        df_b[[id_col, "Final_Decision"]],
        on=id_col,
        suffixes=("_a", "_b"),
        how="outer",
    )

    # An outer merge introduces NaN for IDs that exist in only one file. The
    # decision columns always exist after the merge, so `.get(..., "MISSING")`
    # never triggers its default; fill the NaNs explicitly so exclusive rows
    # report "MISSING" instead of the string "nan".
    merged = merged.fillna("MISSING")

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
    force: bool = False,
) -> Path:
    """Create a new project with config.json and terms template.

    Refuses to overwrite an existing project (a directory already containing
    ``config.json`` or a ``terms`` template) unless ``force=True`` is passed.
    """
    if output_dir is None:
        output_dir = Path.cwd() / name

    # Guard against silently clobbering an existing project. The previous
    # behavior (``mkdir(exist_ok=True)`` + unconditional writes) overwrote any
    # config/terms files already present in the target directory.
    if not force:
        existing = [
            candidate
            for candidate in (
                output_dir / "config.json",
                output_dir / "terms.xlsx",
                output_dir / "terms.csv",
            )
            if candidate.exists()
        ]
        if existing:
            names = ", ".join(sorted(p.name for p in existing))
            raise FileExistsError(
                f"O diretorio de projeto '{output_dir}' ja contem arquivos de "
                f"projeto ({names}). Use force=True para sobrescrever."
            )

    output_dir.mkdir(parents=True, exist_ok=True)

    config = generate_config(preset_name=preset, blocks=blocks)

    config_path = output_dir / "config.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Generate terms templates. XLSX is the primary editing format; CSV is kept
    # as a lightweight fallback for scripts and version control.
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
    terms_xlsx_path = output_dir / "terms.xlsx"
    terms_csv_path = output_dir / "terms.csv"
    terms_df.to_excel(terms_xlsx_path, index=False, engine="openpyxl")
    terms_df.to_csv(terms_csv_path, sep=";", index=False, encoding="utf-8-sig")

    return output_dir


def save_profile_config(name: str, config_path: Path, description: str = "") -> Path:
    """Save a config file as a named profile."""
    from . import profiles

    cfg = load_config(config_path)
    return profiles.save_profile(name, cfg, description)


# ── Export ───────────────────────────────────────────────────────────────────


def export_academic_package(
    result_path: Path,
    output_dir: Path,
    config_path: Path | None = None,
) -> Path:
    """Create an academic package ZIP from existing results.

    Raises ``ValueError`` when ``result_path`` is not a FastSLR result table
    (i.e. it lacks the ``Final_Decision`` column). Without this guard, pointing
    at any arbitrary CSV produced a ZIP "successfully", yielding an invalid
    academic package that contains raw data instead of triage decisions.
    """
    result_df = read_result_table(result_path)
    if "Final_Decision" not in result_df.columns:
        raise ValueError(
            f"O arquivo '{result_path}' nao parece ser um resultado do FastSLR: "
            f"falta a coluna 'Final_Decision'. Rode 'fastslr run' primeiro para "
            f"gerar um resultado de triagem antes de exportar o pacote academico."
        )

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
    parse_warnings: list[str] = field(default_factory=list)


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

    # Propagate parse warnings (invalid kind, empty term, out-of-range level,
    # skipped rows) so callers can surface which CSV rows were not accepted.
    # Without this, the user assumes every row was loaded.
    parse_warnings: list[str] = list(config.get("_parse_warnings", []))

    return TermsView(
        terms=all_terms,
        total=len(all_terms),
        blocks=domain_blocks,
        parse_warnings=parse_warnings,
    )


__all__ = [
    "ValidationIssue",
    "TriageResult",
    "PreviewResult",
    "DiffEntry",
    "DiffReport",
    "ProfileInfo",
    "SetupInspection",
    "TermsView",
    "get_version",
    "format_coverage",
    "read_results_table",
    "validate_config",
    "inspect_run_setup",
    "run_triage",
    "preview_triage",
    "analyze_coverage",
    "diff_results",
    "create_project",
    "save_profile_config",
    "export_academic_package",
    "browse_terms",
]
