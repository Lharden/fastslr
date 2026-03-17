"""CLI entry point, console helpers, and interactive mode."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from .constants import VERSION

# ── Console output helpers ───────────────────────────────────────────────────


class Console:
    """Helpers for colored and formatted terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    CHECK = "[OK]"
    WARN = "[WARN]"
    CROSS = "[ERR]"
    BOX_H = "-"
    BOX_V = "|"
    BOX_TL = "+"
    BOX_TR = "+"
    BOX_BL = "+"
    BOX_BR = "+"
    BOX_TM = "+"
    BOX_ML = "+"
    BOX_MR = "+"

    @staticmethod
    def _supports_color() -> bool:
        if sys.platform == "win32":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    @classmethod
    def disable_colors(cls) -> None:
        """Disable ANSI colors if the terminal does not support them."""
        if not cls._supports_color():
            cls.RESET = cls.BOLD = cls.GREEN = cls.YELLOW = ""
            cls.RED = cls.CYAN = cls.DIM = ""

        # Keep symbols ASCII-only for stable output across Windows code pages.

    @classmethod
    def header(cls, text: str) -> None:
        print(f"\n{cls.BOLD}{cls.CYAN}{'=' * 60}{cls.RESET}")
        print(f"{cls.BOLD}{cls.CYAN}  {text}{cls.RESET}")
        print(f"{cls.BOLD}{cls.CYAN}{'=' * 60}{cls.RESET}\n")

    @classmethod
    def step(cls, num: int, text: str) -> None:
        print(f"{cls.BOLD}[{num}]{cls.RESET} {text}")

    @classmethod
    def success(cls, text: str) -> None:
        print(f"{cls.GREEN}{cls.CHECK}{cls.RESET} {text}")

    @classmethod
    def warning(cls, text: str) -> None:
        print(f"{cls.YELLOW}{cls.WARN}{cls.RESET} {text}")

    @classmethod
    def error(cls, text: str) -> None:
        print(f"{cls.RED}{cls.CROSS}{cls.RESET} {text}")

    @classmethod
    def info(cls, text: str) -> None:
        print(f"{cls.DIM}  {text}{cls.RESET}")

    @classmethod
    def result_box(cls, title: str, items: list[tuple[str, str, str]]) -> None:
        """Display a formatted result box."""
        hline = cls.BOX_H * 58
        print(f"\n{cls.BOLD}{cls.BOX_TL}{hline}{cls.BOX_TR}{cls.RESET}")
        print(f"{cls.BOLD}{cls.BOX_V}  {title:<54}  {cls.BOX_V}{cls.RESET}")
        print(f"{cls.BOLD}{cls.BOX_ML}{hline}{cls.BOX_MR}{cls.RESET}")
        for label, value, color in items:
            color_code = getattr(cls, color.upper(), cls.RESET)
            print(
                f"{cls.BOX_V}  {label:<30} {color_code}{value:>23}{cls.RESET}  {cls.BOX_V}"
            )
        print(f"{cls.BOLD}{cls.BOX_BL}{hline}{cls.BOX_BR}{cls.RESET}")


# ── Progress bar ─────────────────────────────────────────────────────────────


class ProgressBar:
    """Simple terminal progress bar."""

    def __init__(self, total: int, width: int = 40, prefix: str = "") -> None:
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
        self.start_time = time.time()
        self.fill_char = "#"
        self.empty_char = "-"
        self.sep_char = "|"

    def update(self, current: int) -> None:
        self.current = current
        pct = current / self.total if self.total > 0 else 1
        filled = int(self.width * pct)
        bar = self.fill_char * filled + self.empty_char * (self.width - filled)

        elapsed = time.time() - self.start_time
        rate = current / elapsed if elapsed > 0 else 0
        eta = (self.total - current) / rate if rate > 0 else 0

        sys.stdout.write(
            f"\r{self.prefix} {self.sep_char}{bar}{self.sep_char} {current}/{self.total} "
            f"({pct * 100:.0f}%) [{rate:.0f}/s, ETA: {eta:.0f}s]  "
        )
        sys.stdout.flush()

    def finish(self) -> None:
        elapsed = time.time() - self.start_time
        rate = self.total / elapsed if elapsed > 0 else 0
        full_bar = self.fill_char * self.width
        sys.stdout.write(
            f"\r{self.prefix} {self.sep_char}{full_bar}{self.sep_char} "
            f"{self.total}/{self.total} (100%) "
            f"[{rate:.1f}/s, {elapsed:.1f}s total]  \n"
        )
        sys.stdout.flush()


# ── Path resolution ──────────────────────────────────────────────────────────


def _get_default_paths() -> dict:
    """Compute default file paths relative to the package location."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # src/rsl_triage -> src -> project_root

    return {
        "config": script_dir / "default_config.json",
        "terms": project_root / "data" / "terms_final.csv",
        "input_dir": project_root / "data",
        "output_dir": project_root / "output",
    }


# ── Interactive mode ─────────────────────────────────────────────────────────


def run_interactive() -> dict:
    """Interactive step-by-step configuration mode."""
    from .config import auto_detect_input

    default_paths = _get_default_paths()

    Console.header("Interactive Mode - Configuration")

    print("This mode helps you configure the triage step by step.\n")

    # Input file
    print("1. Input file (article corpus)")
    default_input = auto_detect_input(default_paths["input_dir"])
    if default_input:
        print(f"   Detected: {default_input}")
        response = input("   Use this file? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes", "s", "sim"):
            input_path = default_input
        else:
            input_path = Path(input("   File path: ").strip())
    else:
        input_path = Path(input("   CSV file path: ").strip())

    # Config file
    print("\n2. Configuration file")
    if default_paths["config"].exists():
        print(f"   Default found: {default_paths['config']}")
        response = input("   Use default configuration? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes", "s", "sim"):
            config_path = default_paths["config"]
        else:
            config_path = Path(input("   File path: ").strip())
    else:
        config_path = Path(input("   JSON file path: ").strip())

    # Terms file
    print("\n3. Terms file")
    if default_paths["terms"].exists():
        print(f"   Default found: {default_paths['terms']}")
        response = input("   Use default terms? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes", "s", "sim"):
            terms_path = default_paths["terms"]
        else:
            terms_path = Path(input("   File path: ").strip())
    else:
        terms_path = Path(input("   CSV file path: ").strip())

    # Output
    print("\n4. Output file")
    default_output = (
        default_paths["output_dir"]
        / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    print(f"   Suggestion: {default_output}")
    response = input("   Use this path? [Y/n]: ").strip().lower()
    if response in ("", "y", "yes", "s", "sim"):
        output_path = default_output
    else:
        output_path = Path(input("   File path: ").strip())

    return {
        "input": input_path,
        "config": config_path,
        "terms": terms_path,
        "output": output_path,
    }


# ── Main entry point ────────────────────────────────────────────────────────


def _add_common_io_args(parser: argparse.ArgumentParser) -> None:
    """Add the shared -i/-t/-c flags to a subparser."""
    parser.add_argument(
        "-i", "--input", dest="input_file", type=Path,
        help="Path to the article corpus CSV file",
    )
    parser.add_argument(
        "-t", "--terms", dest="terms_file", type=Path,
        help="Path to the terms CSV file",
    )
    parser.add_argument(
        "-c", "--config", dest="config_file", type=Path,
        help="Path to the JSON configuration file",
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="fastslr",
        description=f"FastSLR v{VERSION} - Deterministic article screening",
    )
    parser.add_argument(
        "--version", action="version", version=f"FastSLR {VERSION}",
    )
    parser.add_argument(
        "--log-level", default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: WARNING)",
    )

    # ── Top-level convenience flags (allow legacy `fastslr -i ... -t ...`) ──
    parser.add_argument(
        "-i", "--input", dest="input_file", type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-t", "--terms", dest="terms_file", type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-c", "--config", dest="config_file", type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-o", "--output", dest="output_file", type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-progress", action="store_true", default=False,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--interactive", action="store_true", default=False,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--format", dest="output_format", default=None,
        help=argparse.SUPPRESS,
    )

    subparsers = parser.add_subparsers(dest="command")

    # ── run ──────────────────────────────────────────────────────────────────
    run_parser = subparsers.add_parser(
        "run", help="Execute the full triage pipeline",
    )
    _add_common_io_args(run_parser)
    run_parser.add_argument(
        "-o", "--output", dest="output_file", type=Path,
        help="Path for the output results file",
    )
    run_parser.add_argument(
        "--no-progress", action="store_true", default=False,
        help="Disable the progress bar",
    )
    run_parser.add_argument(
        "--interactive", action="store_true", default=False,
        help="Run in interactive configuration mode",
    )
    run_parser.add_argument(
        "--format", dest="output_format", default=None,
        help="Output format (xlsx, csv)",
    )

    # ── init ─────────────────────────────────────────────────────────────────
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new FastSLR project",
    )
    init_parser.add_argument(
        "--name", default=None,
        help="Project name",
    )
    init_parser.add_argument(
        "--preset", default=None,
        help="Configuration preset to use",
    )
    init_parser.add_argument(
        "--blocks", default=None,
        help="Comma-separated list of domain blocks",
    )
    init_parser.add_argument(
        "--dir", dest="project_dir", type=Path, default=None,
        help="Target directory for the new project",
    )

    # ── pilot ────────────────────────────────────────────────────────────────
    pilot_parser = subparsers.add_parser(
        "pilot", help="Run triage on a random sample for quick validation",
    )
    _add_common_io_args(pilot_parser)
    pilot_parser.add_argument(
        "-n", dest="sample_size", type=int, default=50,
        help="Number of articles to sample (default: 50)",
    )
    pilot_parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible sampling",
    )
    pilot_parser.add_argument(
        "-o", "--output", dest="output_file", type=Path, default=None,
        help="Optional path to export pilot results",
    )

    # ── diff ─────────────────────────────────────────────────────────────────
    diff_parser = subparsers.add_parser(
        "diff", help="Compare two result files",
    )
    diff_parser.add_argument("file1", type=Path, help="First result file")
    diff_parser.add_argument("file2", type=Path, help="Second result file")
    diff_parser.add_argument(
        "--output", dest="output_file", type=Path, default=None,
        help="Output CSV for diff results",
    )
    diff_parser.add_argument(
        "--id-column", default="ID",
        help="Column name used as article identifier (default: ID)",
    )

    # ── report ───────────────────────────────────────────────────────────────
    report_parser = subparsers.add_parser(
        "report", help="Generate a standalone report from existing results",
    )
    _add_common_io_args(report_parser)

    return parser


def _run_pipeline(
    input_path: Path,
    terms_path: Path,
    config_path: Path,
    output_path: Path,
    show_progress: bool = True,
) -> int:
    """Execute the full triage pipeline."""
    from .config import get_domain_blocks, load_config, load_global_params, parse_terms_csv
    from .engine import process_articles
    from .io import (
        compute_config_hash,
        compute_file_hash,
        export_config_audit,
        export_results,
        generate_report,
        load_csv_safe,
    )
    from .normalization import NormalizationEngine
    from .patterns import precompile_patterns

    Console.header(f"FastSLR v{VERSION}")

    # Step 1: Load files
    Console.step(1, "Loading files...")

    if not input_path.exists():
        Console.error(f"Input file not found: {input_path}")
        return 1
    if not terms_path.exists():
        Console.error(f"Terms file not found: {terms_path}")
        return 1
    if not config_path.exists():
        Console.error(f"Config file not found: {config_path}")
        return 1

    base_config = load_config(config_path)
    df = load_csv_safe(input_path)
    Console.success(f"Loaded {len(df)} articles from {input_path.name}")

    # Step 2: Parse terms and compile patterns
    Console.step(2, "Parsing terms and compiling patterns...")

    config = parse_terms_csv(str(terms_path), base_config)
    norm_engine = NormalizationEngine(config.get("normalization_rules", {}))
    global_params = load_global_params(config.get("global", {}))

    domain_blocks = get_domain_blocks(config)
    for block_name in domain_blocks:
        config[block_name] = precompile_patterns(config[block_name], norm_engine, global_params)
    if "T0" in config:
        config["T0"] = precompile_patterns(config["T0"], norm_engine, global_params)

    Console.success(
        f"Compiled patterns for {len(domain_blocks)} block(s): {', '.join(domain_blocks)}"
    )

    # Step 3: Process articles
    Console.step(3, "Processing articles...")

    result_df, stats = process_articles(df, config, show_progress=show_progress)

    Console.success(
        f"Processed {stats['total_articles']} articles "
        f"in {stats['processing_time']:.2f}s "
        f"({stats['articles_per_second']:.1f}/s)"
    )

    # Step 4: Export results
    Console.step(4, "Exporting results...")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_results(result_df, output_path, config)
    Console.success(f"Results exported to {output_path}")

    # Generate supplementary files
    report_path = output_path.with_stem(output_path.stem + "_report").with_suffix(".txt")
    generate_report(result_df, stats, config, report_path)

    config_audit_path = output_path.with_stem(output_path.stem + "_config").with_suffix(".json")
    export_config_audit(config, config_audit_path)

    stats_path = output_path.with_stem(output_path.stem + "_stats").with_suffix(".json")
    stats_path.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # Display summary
    distribution = stats.get("decision_distribution", {})
    items: list[tuple[str, str, str]] = []
    for decision, count in sorted(distribution.items()):
        color = "green" if "APPROVED" in decision else ("yellow" if "FLAGGED" in decision else "red")
        items.append((decision, str(count), color))
    items.append(("Total", str(stats["total_articles"]), "cyan"))

    Console.result_box("Final Decision Distribution", items)

    return 0


def _resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    """Resolve input/terms/config/output paths from args + defaults."""
    default_paths = _get_default_paths()
    return {
        "input": getattr(args, "input_file", None),
        "terms": getattr(args, "terms_file", None) or default_paths["terms"],
        "config": getattr(args, "config_file", None) or default_paths["config"],
        "output": getattr(args, "output_file", None) or (
            default_paths["output_dir"]
            / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        ),
    }


# ── Subcommand handlers ────────────────────────────────────────────────────


def _cmd_run(args: argparse.Namespace) -> int:
    """Handle the ``run`` subcommand (wraps the existing pipeline)."""
    interactive = getattr(args, "interactive", False)
    has_io_args = any([
        getattr(args, "input_file", None),
        getattr(args, "terms_file", None),
        getattr(args, "config_file", None),
    ])

    if interactive or not has_io_args:
        try:
            paths = run_interactive()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return 1
        return _run_pipeline(
            input_path=paths["input"],
            terms_path=paths["terms"],
            config_path=paths["config"],
            output_path=paths["output"],
        )

    resolved = _resolve_paths(args)
    if not resolved["input"]:
        Console.error("Input file is required. Use -i <path> or --interactive.")
        return 1

    return _run_pipeline(
        input_path=resolved["input"],
        terms_path=resolved["terms"],
        config_path=resolved["config"],
        output_path=resolved["output"],
        show_progress=not getattr(args, "no_progress", False),
    )


def _cmd_init(args: argparse.Namespace) -> int:
    """Handle the ``init`` subcommand (stub)."""
    Console.warning("'fastslr init' is coming soon.")
    return 0


def _cmd_pilot(args: argparse.Namespace) -> int:
    """Handle the ``pilot`` subcommand -- run triage on a random sample."""
    from .config import get_domain_blocks, load_config, load_global_params, parse_terms_csv
    from .engine import process_articles, sample_articles
    from .io import export_results, load_csv_safe
    from .normalization import NormalizationEngine
    from .patterns import precompile_patterns

    resolved = _resolve_paths(args)
    input_path = resolved["input"]
    terms_path = resolved["terms"]
    config_path = resolved["config"]
    output_path = getattr(args, "output_file", None)
    sample_size: int = getattr(args, "sample_size", 50)
    seed: int | None = getattr(args, "seed", None)

    if not input_path:
        Console.error("Input file is required. Use -i <path>.")
        return 1

    Console.header(f"FastSLR v{VERSION} -- Pilot Mode")

    # Step 1: Load files
    Console.step(1, "Loading files...")

    if not input_path.exists():
        Console.error(f"Input file not found: {input_path}")
        return 1
    if not terms_path.exists():
        Console.error(f"Terms file not found: {terms_path}")
        return 1
    if not config_path.exists():
        Console.error(f"Config file not found: {config_path}")
        return 1

    base_config = load_config(config_path)
    df = load_csv_safe(input_path)
    Console.success(f"Loaded {len(df)} articles from {input_path.name}")

    # Step 2: Sample
    Console.step(2, f"Sampling {sample_size} articles (seed={seed})...")
    sample_df = sample_articles(df, sample_size, seed)
    Console.success(f"Sampled {len(sample_df)} of {len(df)} articles")

    # Step 3: Parse terms and compile patterns
    Console.step(3, "Parsing terms and compiling patterns...")

    config = parse_terms_csv(str(terms_path), base_config)
    norm_engine = NormalizationEngine(config.get("normalization_rules", {}))
    global_params = load_global_params(config.get("global", {}))

    domain_blocks = get_domain_blocks(config)
    for block_name in domain_blocks:
        config[block_name] = precompile_patterns(
            config[block_name], norm_engine, global_params,
        )
    if "T0" in config:
        config["T0"] = precompile_patterns(config["T0"], norm_engine, global_params)

    Console.success(
        f"Compiled patterns for {len(domain_blocks)} block(s): "
        f"{', '.join(domain_blocks)}"
    )

    # Step 4: Process sample
    Console.step(4, "Processing sample...")

    result_df, stats = process_articles(sample_df, config, show_progress=True)

    # Enrich stats with sampling metadata
    stats["pilot"] = {
        "sample_size": len(sample_df),
        "corpus_size": len(df),
        "seed": seed,
    }

    Console.success(
        f"Processed {stats['total_articles']} articles "
        f"in {stats['processing_time']:.2f}s "
        f"({stats['articles_per_second']:.1f}/s)"
    )

    # Step 5: Optional export
    if output_path:
        Console.step(5, "Exporting pilot results...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        export_results(result_df, output_path, config)
        Console.success(f"Pilot results exported to {output_path}")

    # Display compact summary
    distribution = stats.get("decision_distribution", {})
    items: list[tuple[str, str, str]] = []
    for decision, count in sorted(distribution.items()):
        color = (
            "green" if "APPROVED" in decision
            else ("yellow" if "FLAGGED" in decision else "red")
        )
        items.append((decision, str(count), color))
    items.append(("Sample / Corpus", f"{len(sample_df)} / {len(df)}", "cyan"))

    Console.result_box("Pilot Results", items)

    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    """Handle the ``diff`` subcommand (stub)."""
    Console.warning("'fastslr diff' is coming soon.")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Handle the ``report`` subcommand (stub)."""
    Console.warning("'fastslr report' is coming soon.")
    return 0


_COMMAND_HANDLERS: dict[str, object] = {
    "run": _cmd_run,
    "init": _cmd_init,
    "pilot": _cmd_pilot,
    "diff": _cmd_diff,
    "report": _cmd_report,
}


def main() -> int:
    """Main CLI entry point with subcommand routing."""
    Console.disable_colors()

    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    command = args.command

    # If no subcommand given but -i/-t/-c args are present, default to "run"
    if command is None:
        has_io_args = any([
            getattr(args, "input_file", None),
            getattr(args, "terms_file", None),
            getattr(args, "config_file", None),
        ])
        if has_io_args or getattr(args, "interactive", False):
            command = "run"
        else:
            # No args at all -> default to run (interactive mode)
            command = "run"

    handler = _COMMAND_HANDLERS.get(command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)  # type: ignore[operator]
