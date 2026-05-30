"""I/O operations: CSV/XLSX loading, export, report generation, and audit."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pandas as pd

from .constants import SECTION_NAMES, VERSION

chardet: ModuleType | None
try:
    import chardet as _chardet  # type: ignore[import-not-found]
except ModuleNotFoundError:
    chardet = None
else:
    chardet = _chardet

logger = logging.getLogger(__name__)

PROTOCOL_VERSION_CURRENT = "2.1"
PROTOCOL_SCHEMA_ID = "rsl-triage-protocol-v2.1"

_PROTOCOL_ROOT_KEYS = frozenset(
    {
        "protocol_version",
        "schema_id",
        "execution_id",
        "generated_at",
        "triage_version",
        "inputs",
        "configuration",
        "processing",
        "artifacts",
        "reproducibility",
    }
)

SPREADSHEET_EXTENSIONS = frozenset({".xlsx", ".xlsm", ".xls"})
DELIMITED_EXTENSIONS = frozenset({".csv", ".tsv", ".txt"})


# ── hashing ──────────────────────────────────────────────────────────────────


def _sanitize_config_for_serialization(config: dict) -> dict:
    """Remove non-serializable elements from the configuration."""
    config_clean = deepcopy(config)

    for key in list(config_clean.keys()):
        if isinstance(config_clean.get(key), dict):
            block = config_clean[key]
            if isinstance(block, dict):
                block.pop("normalization_engine", None)
                for term_list_key in (
                    "positives",
                    "proximity_positives",
                    "anti_exclude",
                    "anti_flag",
                ):
                    term_list = block.get(term_list_key)
                    if isinstance(term_list, list):
                        for term in term_list:
                            if isinstance(term, dict):
                                term.pop("pattern", None)
                                term.pop("highlight_patterns", None)

    return config_clean


def compute_config_hash(config: dict) -> str:
    """Generate a SHA-256 hash (truncated to 16 hex chars) of the configuration."""
    config_clean = _sanitize_config_for_serialization(config)
    config_str = json.dumps(config_clean, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]


def compute_file_hash(file_path: str) -> str:
    """Compute a SHA-256 hash (truncated to 16 hex chars) of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


# ── Table loading ────────────────────────────────────────────────────────────


# Deterministic fallback chain. ``latin-1`` is last and never fails on decode
# (every byte maps to a code point), so it guarantees a successful read.
_ENCODING_FALLBACK_CHAIN = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def _candidate_encodings(path: Path, preferred: str | None = None) -> list[str]:
    """Return an ordered, de-duplicated list of encodings to try.

    Order: caller-provided ``preferred`` (e.g. from config), then an optional
    chardet guess (kept only as an optimization when the dependency is present),
    then the deterministic fallback chain that ends with ``latin-1``.
    """
    ordered: list[str] = []
    if preferred:
        ordered.append(preferred)

    if chardet is not None:
        try:
            with open(path, "rb") as f:
                raw_data = f.read(10000)
            guess = chardet.detect(raw_data).get("encoding")
        except (OSError, ValueError):
            guess = None
        if guess:
            ordered.append(guess)

    ordered.extend(_ENCODING_FALLBACK_CHAIN)

    seen: set[str] = set()
    deduped: list[str] = []
    for enc in ordered:
        key = enc.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(enc)
    return deduped


def _header_score(columns: list[object]) -> int:
    known_headers = {
        "id",
        "key",
        "eid",
        "ut",
        "title",
        "articletitle",
        "abstract",
        "abstractnote",
        "manualtags",
        "authorkeywords",
        "keywords",
        "block",
        "kind",
        "term",
        "level",
        "sectionscope",
        "isregex",
        "finaldecision",
    }
    score = 0
    for col in columns:
        normalized = re.sub(r"[^a-z0-9]+", "", str(col).lower())
        if normalized in known_headers:
            score += 1
    return score


def _load_delimited_table(
    path: Path, min_columns: int, encoding: str | None = None
) -> pd.DataFrame:
    separators = ("\t", ";", ",") if path.suffix.lower() == ".tsv" else (";", ",", "\t")
    encodings = _candidate_encodings(path, preferred=encoding)
    tried_encodings: list[str] = []

    for enc in encodings:
        candidates: list[tuple[int, int, pd.DataFrame]] = []
        decode_failed = False
        for sep in separators:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, dtype=str, keep_default_na=False)
            except UnicodeDecodeError:
                # This encoding cannot decode the bytes; advance to the next one.
                decode_failed = True
                break
            except Exception:
                # Parsing/separator issue specific to this separator; try the next sep.
                continue
            if len(df.columns) >= min_columns:
                candidates.append((_header_score(list(df.columns)), len(df.columns), df))

        tried_encodings.append(enc)

        if candidates:
            if enc != encodings[0]:
                logger.debug("Loaded delimited table %s using fallback encoding %r", path, enc)
            return max(candidates, key=lambda item: (item[0], item[1]))[2]

        if decode_failed:
            continue

    raise ValueError(
        f"Unable to load delimited table: {path} (tried encodings: {', '.join(tried_encodings)})"
    )


def _load_spreadsheet_table(path: Path, min_columns: int) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, dtype=str, keep_default_na=False)
    except ImportError as exc:
        raise ValueError(
            "Reading Excel files requires the spreadsheet dependencies installed with FastSLR."
        ) from exc
    except Exception as exc:
        raise ValueError(f"Unable to load spreadsheet: {path}") from exc

    if len(df.columns) < min_columns:
        raise ValueError(f"Spreadsheet has fewer than {min_columns} column(s): {path}")

    return df


def load_table_safe(path: Path, min_columns: int = 3, encoding: str | None = None) -> pd.DataFrame:
    """Load a CSV/TSV or Excel table with conservative format detection.

    When ``encoding`` is provided (e.g. from configuration), it is tried first
    for delimited files before the deterministic fallback chain.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix in SPREADSHEET_EXTENSIONS:
        return _load_spreadsheet_table(path, min_columns)
    if suffix in DELIMITED_EXTENSIONS or not suffix:
        return _load_delimited_table(path, min_columns, encoding=encoding)

    raise ValueError(f"Unsupported table format: {path.suffix}. Use CSV, TSV, XLSX, XLSM, or XLS.")


def load_csv_safe(path: Path, encoding: str | None = None) -> pd.DataFrame:
    """Load an input table.

    Kept for backward compatibility; despite the name, XLSX/XLSM/XLS are accepted.
    """
    return load_table_safe(path, encoding=encoding)


def read_result_table(path: Path, encoding: str | None = None) -> pd.DataFrame:
    """Read a result file exported by FastSLR."""
    return load_table_safe(path, min_columns=1, encoding=encoding)


# ── export helpers ───────────────────────────────────────────────────────────


def get_export_opts(cfg: dict) -> dict:
    """Extract export options from the configuration dict."""
    root = cfg or {}
    out = root.get("output") or {}
    # Defaults aligned with the shipped template / generate_config and
    # default_config.json (csv:false, xlsx:true). A minimal hand-written config
    # without an ``output`` block therefore behaves like the documented default
    # instead of silently producing CSV-only output.
    return {
        "export_csv": bool(out.get("csv", False)),
        "export_xlsx": bool(out.get("xlsx", True)),
        "csv_sep": out.get("csv_sep", root.get("sep", ";")),
        "csv_decimal": out.get("csv_decimal", root.get("decimal", ",")),
        "csv_float_fmt": out.get("csv_float_format", "%.2f"),
        "xlsx_engine": out.get("xlsx_engine", "openpyxl"),
        "xlsx_sheet": out.get("xlsx_sheet_name", "resultados"),
        "encoding": root.get("encoding", "utf-8-sig"),
        "academic_package": bool(out.get("academic_package", True)),
    }


def _result_base_path(output_path: Path) -> Path:
    if output_path.suffix.lower() in {".csv", ".xlsx"}:
        return output_path.with_suffix("")
    return output_path


def export_results(df: pd.DataFrame, output_path: Path, cfg: dict) -> dict[str, Path]:
    """Export the result DataFrame to CSV and/or XLSX.

    ``output_path`` is treated as a base path. Passing ``triage_results.xlsx``
    still produces ``triage_results.csv`` when CSV export is enabled.
    """
    opts = get_export_opts(cfg)
    base_path = _result_base_path(output_path)
    exported: dict[str, Path] = {}

    if not opts["export_csv"] and not opts["export_xlsx"]:
        opts["export_xlsx"] = True

    if opts["export_csv"]:
        csv_path = base_path.with_suffix(".csv")
        df.to_csv(
            csv_path,
            index=False,
            encoding=opts["encoding"],
            sep=opts["csv_sep"],
            float_format=opts["csv_float_fmt"],
            decimal=opts["csv_decimal"],
        )
        exported["csv"] = csv_path

    if opts["export_xlsx"]:
        xlsx_path = base_path.with_suffix(".xlsx")
        df.to_excel(
            xlsx_path,
            index=False,
            engine=opts["xlsx_engine"],
            sheet_name=opts["xlsx_sheet"],
        )
        exported["xlsx"] = xlsx_path

    return exported


# ── highlighting ─────────────────────────────────────────────────────────────


def highlight_text(original_text: str, all_terms: list[dict], section_name: str) -> str:
    """Mark matched terms in the original text with ***TERM*** markers."""
    if not original_text or not all_terms:
        return original_text

    spans: list[tuple[int, int]] = []

    for term in all_terms:
        if term.get("scope", "any") not in ("any", section_name):
            continue

        patterns = term.get("highlight_patterns") or [term.get("pattern")]

        for pattern in patterns:
            if not pattern:
                continue

            try:
                for match in pattern.finditer(original_text):
                    spans.append(match.span())
            except re.error:
                continue

    if not spans:
        return original_text

    spans = sorted(set(spans))
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    result = original_text
    for start, end in reversed(merged):
        result = f"{result[:start]}***{result[start:end].upper()}***{result[end:]}"

    return result


def pack_highlights(evaluation) -> str:
    """Serialize all positive matches of a block evaluation to a compact string."""
    items: list[str] = []
    for sec_name in SECTION_NAMES:
        for m in evaluation.matches.get(sec_name, []):
            comp_str = f" comps={'+'.join(m.components)}" if m.components else ""
            # json.dumps escapes embedded double quotes/backslashes so a term such
            # as 'pipe 5" diameter' stays parseable by the coverage regex and does
            # not get mis-classified as a dead-term.
            term_field = json.dumps(m.term)
            items.append(
                f"term={term_field} sec={sec_name} L={m.level} "
                f"row={m.source_row} type={m.match_type}{comp_str}"
            )
    return " | ".join(items)


def pack_anti_hits(hits: list) -> str:
    """Serialize anti-term hits to a compact string."""
    return "|".join(f"{h.term}:{h.section}:{h.source_row}" for h in hits if h.term and h.section)


# ── reports ──────────────────────────────────────────────────────────────────


def generate_report(df: pd.DataFrame, stats: dict, config: dict, output_path: Path) -> None:
    """Write a human-readable triage report to a text file."""
    from .config import get_domain_blocks

    total = len(df)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== TRIAGE REPORT ===\n")
        f.write(f"VERSION: {VERSION}\n")
        f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"TOTAL ARTICLES: {total}\n")
        f.write(f"PROCESSING TIME: {stats.get('processing_time', 0):.2f}s\n")
        f.write(f"RATE: {stats.get('articles_per_second', 0):.1f} articles/s\n\n")

        f.write(f"CONFIG HASH: {compute_config_hash(config)}\n\n")

        if "Final_Decision" in df.columns:
            f.write("== FINAL DECISIONS ==\n")
            for decision, count in df["Final_Decision"].value_counts().items():
                f.write(f"{decision}: {count} ({(count / total) * 100:.1f}%)\n")
            f.write("\n")

        f.write("== BLOCK PERFORMANCE ==\n")

        blocks_to_report = ["T0"] if "Status_T0" in df.columns else []
        blocks_to_report.extend(get_domain_blocks(config))

        for block in blocks_to_report:
            f.write(f"\n{block}:\n")
            block_stats = stats.get("block_performance", {}).get(block, {})

            for status, count in block_stats.get("status_distribution", {}).items():
                f.write(f"  {status}: {count} ({(count / total) * 100:.1f}%)\n")

            if block != "T0":
                f.write(f"  Avg score: {block_stats.get('avg_score', 0):.2f}\n")
                f.write(f"  Max score: {block_stats.get('max_score', 0):.2f}\n")


def export_config_audit(config: dict, output_path: Path) -> None:
    """Export sanitized configuration for audit trail."""
    config_clean = _sanitize_config_for_serialization(config)

    config_clean["_metadata"] = {
        "export_timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "config_hash": compute_config_hash(config),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config_clean, f, indent=2, ensure_ascii=False, default=str)


# ── protocol snapshot ────────────────────────────────────────────────────────


def build_protocol_snapshot(
    config: dict,
    stats: dict,
    input_path: Path,
    terms_path: Path,
    result_path: Path,
    input_hash: str,
    terms_hash: str,
    config_hash: str,
) -> dict:
    """Build a protocol snapshot dict for reproducibility."""
    from .config import get_domain_blocks

    domain_blocks = get_domain_blocks(config)
    block_labels = config.get("_block_labels", {})
    global_cfg = config.get("global", {})

    snapshot = {
        "protocol_version": PROTOCOL_VERSION_CURRENT,
        "schema_id": PROTOCOL_SCHEMA_ID,
        "execution_id": f"run_{uuid.uuid4().hex[:12]}",
        "generated_at": datetime.now().isoformat(),
        "triage_version": VERSION,
        "inputs": {
            "input_file": str(input_path),
            "input_hash": input_hash,
            "terms_file": str(terms_path),
            "terms_hash": terms_hash,
            "config_hash": config_hash,
        },
        "configuration": {
            "decision_policy": global_cfg.get("DECISION_POLICY", "special"),
            "domain_blocks": [{"id": b, "label": block_labels.get(b, b)} for b in domain_blocks],
            "fail_fast": global_cfg.get("FAIL_FAST_GLOBAL", True),
            "enable_special_approval": global_cfg.get("ENABLE_SPECIAL_APPROVAL_RULE", True),
            "level_scores": global_cfg.get("PONTUACAO_NIVEIS", {}),
            "section_weights": global_cfg.get("WEIGHTS", {}),
            "approval_thresholds": global_cfg.get("LIMITES_APROVADO", {}),
            "flagging_thresholds": global_cfg.get("LIMITES_SINALIZADO", {}),
        },
        "processing": {
            "total_articles": stats.get("total_articles", 0),
            "processing_time_seconds": stats.get("processing_time", 0),
            "articles_per_second": stats.get("articles_per_second", 0),
        },
        "artifacts": {
            "results_path": str(result_path),
        },
        "reproducibility": {
            "deterministic_engine": True,
        },
        "methodology": {
            "scoring": "weighted section scores with level-based thresholds",
            "normalization": "rule-based with LRU cache",
        },
    }

    # Sampling metadata
    if stats.get("sample_mode"):
        snapshot["processing"]["sample_mode"] = True
        snapshot["processing"]["sample_size"] = stats.get("sample_size")
        snapshot["processing"]["population_size"] = stats.get("population_size")
        snapshot["processing"]["sample_seed"] = stats.get("sample_seed")

    return snapshot


def validate_protocol_snapshot(snapshot: dict) -> list[str]:
    """Validate a protocol snapshot, returning a list of error strings."""
    errors: list[str] = []

    for key in _PROTOCOL_ROOT_KEYS:
        if key not in snapshot:
            errors.append(f"Missing root key: '{key}'")

    if snapshot.get("protocol_version") != PROTOCOL_VERSION_CURRENT:
        errors.append(
            f"Version mismatch: expected {PROTOCOL_VERSION_CURRENT}, "
            f"got {snapshot.get('protocol_version')}"
        )

    return errors


# Source protocol versions that ``migrate_protocol_snapshot`` knows how to
# upgrade to ``PROTOCOL_VERSION_CURRENT``. The current version is accepted as a
# no-op upgrade target so re-migrating an already-current snapshot is safe.
_MIGRATABLE_SOURCE_VERSIONS = frozenset({"1.0", "2.0", PROTOCOL_VERSION_CURRENT})


def _default_root_value(key: str) -> object:
    """Return a safe placeholder for a missing required root key."""
    if key == "protocol_version":
        return PROTOCOL_VERSION_CURRENT
    if key == "schema_id":
        return PROTOCOL_SCHEMA_ID
    if key == "execution_id":
        return f"run_migrated_{uuid.uuid4().hex[:12]}"
    if key == "generated_at":
        return datetime.now().isoformat()
    if key == "triage_version":
        return VERSION
    # Remaining structural keys (inputs/configuration/processing/artifacts/
    # reproducibility) are objects.
    return {}


def migrate_protocol_snapshot(old_snapshot: dict) -> dict:
    """Migrate a protocol snapshot from a known older version to the current one.

    Refuses unknown/future source versions (raises ``ValueError``), fills any
    missing required root keys with safe defaults, and validates the result so
    the returned snapshot is guaranteed to pass ``validate_protocol_snapshot``.
    """
    source_version = old_snapshot.get("protocol_version")
    if source_version not in _MIGRATABLE_SOURCE_VERSIONS:
        raise ValueError(
            f"Cannot migrate protocol snapshot: unknown source version "
            f"{source_version!r}. Known versions: "
            f"{', '.join(sorted(_MIGRATABLE_SOURCE_VERSIONS))}."
        )

    migrated = deepcopy(old_snapshot)
    migrated["protocol_version"] = PROTOCOL_VERSION_CURRENT
    migrated["schema_id"] = PROTOCOL_SCHEMA_ID

    # Backfill required root keys that an older/minimal snapshot may omit so the
    # migrated snapshot is self-consistent rather than merely re-tagged as 2.1.
    for key in _PROTOCOL_ROOT_KEYS:
        if key not in migrated:
            migrated[key] = _default_root_value(key)

    if "methodology" not in migrated:
        migrated["methodology"] = {
            "scoring": "weighted section scores with level-based thresholds",
            "normalization": "rule-based with LRU cache",
        }

    errors = validate_protocol_snapshot(migrated)
    if errors:
        raise ValueError("Migrated protocol snapshot failed validation: " + "; ".join(errors))

    return migrated


def export_protocol_snapshot(snapshot: dict, output_path: Path) -> None:
    """Write a protocol snapshot to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)


def generate_academic_report(snapshot: dict, output_path: Path) -> None:
    """Generate an academic compliance report in Markdown format."""
    config = snapshot.get("configuration", {})
    processing = snapshot.get("processing", {})
    inputs = snapshot.get("inputs", {})

    lines = [
        "# Academic Compliance Report",
        "",
        f"**Triage version:** {snapshot.get('triage_version', 'N/A')}",
        f"**Generated at:** {snapshot.get('generated_at', 'N/A')}",
        f"**Execution ID:** {snapshot.get('execution_id', 'N/A')}",
        "",
        "## Configuration",
        "",
        f"- Decision policy: {config.get('decision_policy', 'N/A')}",
        f"- Domain blocks: {len(config.get('domain_blocks', []))}",
        f"- Fail-fast: {config.get('fail_fast', 'N/A')}",
        "",
        "## Scoring Criteria",
        "",
        f"- Level scores: {config.get('level_scores', {})}",
        f"- Section weights: {config.get('section_weights', {})}",
        f"- Approval thresholds: {config.get('approval_thresholds', {})}",
        f"- Flagging thresholds: {config.get('flagging_thresholds', {})}",
        "",
        "## Processing",
        "",
        f"- Total articles: {processing.get('total_articles', 0)}",
        f"- Processing time: {processing.get('processing_time_seconds', 0):.2f}s",
        f"- Rate: {processing.get('articles_per_second', 0):.1f} articles/s",
        "",
        "## Inputs",
        "",
        f"- Input file: {inputs.get('input_file', 'N/A')}",
        f"- Input hash: {inputs.get('input_hash', 'N/A')}",
        f"- Terms file: {inputs.get('terms_file', 'N/A')}",
        f"- Terms hash: {inputs.get('terms_hash', 'N/A')}",
        f"- Config hash: {inputs.get('config_hash', 'N/A')}",
        "",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_compliance_manifest(
    artifacts: dict[str, Path], output_path: Path, execution_id: str
) -> None:
    """Export a compliance manifest linking all run artifacts."""
    manifest = {
        "execution_id": execution_id,
        "generated_at": datetime.now().isoformat(),
        "artifacts": {name: str(path) for name, path in artifacts.items()},
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def export_appendix_pack(artifacts: dict[str, Path], zip_path: Path, execution_id: str) -> None:
    """Create a ZIP appendix pack with all available artifacts."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    seen_paths: set[str] = set()
    entries: list[tuple[str, Path]] = []

    for _label, path in artifacts.items():
        if not path.exists():
            continue
        resolved = str(path.resolve())
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        entries.append((path.name, path))

    index_lines = [
        f"# Appendix Pack: {execution_id}",
        "",
        f"Generated at: {datetime.now().isoformat()}",
        "",
        "## Contents",
        "",
    ]

    manifest_items: dict[str, str] = {}

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in entries:
            zf.write(path, name)
            index_lines.append(f"- {name}")
            manifest_items[name] = str(path)

        index_text = "\n".join(index_lines) + "\n"
        zf.writestr("APPENDIX_INDEX.md", index_text)

        manifest = {
            "execution_id": execution_id,
            "generated_at": datetime.now().isoformat(),
            "files": manifest_items,
        }
        zf.writestr("appendix_manifest.json", json.dumps(manifest, indent=2))


__all__ = [
    "PROTOCOL_SCHEMA_ID",
    "PROTOCOL_VERSION_CURRENT",
    "compute_config_hash",
    "compute_file_hash",
    "load_table_safe",
    "load_csv_safe",
    "read_result_table",
    "get_export_opts",
    "export_results",
    "highlight_text",
    "pack_highlights",
    "pack_anti_hits",
    "generate_report",
    "export_config_audit",
    "build_protocol_snapshot",
    "validate_protocol_snapshot",
    "migrate_protocol_snapshot",
    "export_protocol_snapshot",
    "generate_academic_report",
    "export_compliance_manifest",
    "export_appendix_pack",
]
