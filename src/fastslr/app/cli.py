"""FastSLR CLI — batch mode entry point.

Usage:
    fastslr doctor --input <input> --config <config.json> --terms <terms.xlsx>
    fastslr run <input> --config <config.json> --terms <terms.xlsx>
    fastslr preview <input> --config <config.json> --sample 50
    fastslr new-project
    fastslr coverage <input> --config <config.json>
    fastslr diff <result1> <result2>
    fastslr export <result> --output <dir>
    fastslr profile save <name> --config <config.json>
    fastslr profile load <name>
    fastslr profile list
    fastslr version
    fastslr tui
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from ..i18n import _ as t
from ..i18n import set_locale

app = typer.Typer(
    name="fastslr",
    help="FastSLR — Universal deterministic triage for Systematic Literature Reviews.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

profile_app = typer.Typer(help="Manage configuration profiles.", no_args_is_help=True)
app.add_typer(profile_app, name="profile")

console = Console()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _setup_lang(lang: str | None) -> None:
    """Configure locale from --lang flag if provided."""
    if lang:
        set_locale(lang)


def _require_input(input_file: Path) -> None:
    """Abort with a friendly message if the input articles file is missing."""
    if not input_file.exists():
        console.print(f"[red]{t('file_not_found', path=input_file)}[/red]")
        raise typer.Exit(1)


def _require_config(config: Path) -> None:
    """Abort with a friendly message if the config file is missing."""
    if not config.exists():
        console.print(f"[red]{t('config_not_found', path=config)}[/red]")
        raise typer.Exit(1)


def _require_terms(terms: Path | None) -> None:
    """Abort with a friendly message if a provided terms file is missing.

    ``terms`` is optional, so ``None`` is accepted silently; only a non-existent
    path triggers the error.
    """
    if terms is not None and not terms.exists():
        console.print(f"[red]{t('file_not_found', path=terms)}[/red]")
        raise typer.Exit(1)


def _rich_progress_callback(progress: Progress, task_id: object):
    """Return a callback that updates a rich progress bar."""

    def _on_progress(current: int, total: int) -> None:
        progress.update(task_id, completed=current, total=total)  # type: ignore[arg-type]

    return _on_progress


def _print_stats(stats: dict) -> None:
    """Print triage statistics as a rich table."""
    table = Table(title=t("table_triage_results"), show_header=True)
    table.add_column(t("table_metric"), style="cyan")
    table.add_column(t("table_value"), style="bold")

    table.add_row(
        t("table_total_articles"),
        str(stats.get("total_articles", 0)),
    )
    table.add_row(
        t("table_processing_time"),
        t("time_unit", value=stats.get("processing_time", 0)),
    )
    table.add_row(
        t("table_speed"),
        t("speed_unit", value=stats.get("articles_per_second", 0)),
    )

    dist = stats.get("decision_distribution", {})
    for decision, count in sorted(dist.items()):
        style = "green" if "APPROVED" in decision else "yellow" if "FLAGGED" in decision else "red"
        table.add_row(f"  {decision}", f"[{style}]{count}[/{style}]")

    if stats.get("error_count", 0) > 0:
        table.add_row(
            t("table_errors"),
            f"[red]{stats['error_count']}[/red]",
        )

    console.print(table)


def _print_setup_inspection(inspection) -> None:
    """Print a setup inspection returned by the controller."""
    if inspection.messages:
        console.print(f"\n[bold]{t('doctor_quick_start')}[/bold]")
        for msg in inspection.messages:
            console.print(f"  - {msg}")

    if inspection.errors:
        console.print(f"\n[red bold]{t('doctor_setup_errors')}[/red bold]")
        for msg in inspection.errors:
            console.print(f"  [red]- {msg}[/red]")

    if inspection.warnings:
        console.print(f"\n[yellow bold]{t('doctor_setup_warnings')}[/yellow bold]")
        for msg in inspection.warnings:
            console.print(f"  [yellow]- {msg}[/yellow]")

    if inspection.input_rows is not None:
        console.print(f"\n[bold]{t('doctor_input_articles')}[/bold]: {inspection.input_rows}")
        if inspection.input_columns:
            console.print(t("doctor_columns") + ": " + ", ".join(inspection.input_columns[:20]))

    if inspection.field_mapping:
        table = Table(title=t("doctor_field_mapping"), show_header=True)
        table.add_column(t("doctor_field"), style="cyan")
        table.add_column(t("doctor_column"))
        for field, column in inspection.field_mapping.items():
            table.add_row(field, column or f"[yellow]{t('doctor_not_found')}[/yellow]")
        console.print(table)

    if inspection.domain_blocks:
        console.print(
            f"\n[bold]{t('doctor_domain_blocks')}[/bold]: " + ", ".join(inspection.domain_blocks)
        )

    if inspection.terms_count is not None:
        console.print(f"[bold]{t('doctor_valid_terms')}[/bold]: {inspection.terms_count}")

    if inspection.output_dir is not None:
        console.print(f"[bold]{t('doctor_output_directory')}[/bold]: {inspection.output_dir}")

    if inspection.run_command:
        console.print(f"\n[bold green]{t('doctor_run_command')}[/bold green]")
        console.print(f"  {inspection.run_command}")


# ── Commands ─────────────────────────────────────────────────────────────────


@app.command()
def version(
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Show FastSLR version."""
    _setup_lang(lang)
    from . import controller

    console.print(t("version_info", version=controller.get_version()))


@app.command()
def doctor(
    input_file: Path | None = typer.Option(
        None, "--input", "-i", help="Path to articles CSV/XLSX file."
    ),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to config.json."),
    terms: Path | None = typer.Option(None, "--terms", "-t", help="Path to terms XLSX/CSV."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output directory."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Check setup files and show the exact run command."""
    _setup_lang(lang)
    from . import controller

    inspection = controller.inspect_run_setup(
        input_path=input_file,
        config_path=config,
        terms_path=terms,
        output_dir=output,
    )
    _print_setup_inspection(inspection)

    if not inspection.ok:
        raise typer.Exit(1)


@app.command()
def run(
    input_file: Path = typer.Argument(..., help="Path to articles CSV/XLSX file."),
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Path | None = typer.Option(None, "--terms", "-t", help="Path to terms XLSX/CSV."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output directory."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Proceed past configuration warnings without prompting."
    ),
) -> None:
    """Run triage on an articles file."""
    _setup_lang(lang)
    from . import controller

    _require_input(input_file)
    _require_config(config)
    _require_terms(terms)

    # Validate config first
    prepared = controller._prepare_config(config, terms)
    issues = controller.validate_config(prepared)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        for issue in errors:
            console.print(f"[red]{t('config_error', message=issue.message)}[/red]")
        raise typer.Exit(1)

    warnings = [i for i in issues if i.level == "warning"]
    if warnings and not quiet:
        console.print(f"\n[yellow bold]{t('warnings_found', count=len(warnings))}[/yellow bold]")
        for i, issue in enumerate(warnings, 1):
            console.print(f"  [yellow]{i}. {issue.message}[/yellow]")
        console.print()
        # Only prompt when running interactively. In a pipe/CI context (no TTY)
        # or with --yes there is nobody to answer [y/N]; aborting there would
        # silently fail the run, so proceed by default instead.
        interactive = sys.stdin.isatty()
        if interactive and not yes:
            if not typer.confirm(t("continue_with_warnings"), default=False):
                raise typer.Exit(0)
        else:
            console.print(f"[dim]{t('proceeding_with_warnings')}[/dim]")
        console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        task_id = progress.add_task("Triage", total=None)
        callback = _rich_progress_callback(progress, task_id)

        result = controller.run_triage(
            input_path=input_file,
            config_path=config,
            terms_path=terms,
            output_dir=output,
            on_progress=callback,
        )

    if not quiet:
        _print_stats(result.stats)
        console.print(f"\n[green]{t('triage_complete', path=result.output_dir)}[/green]")


@app.command()
def preview(
    input_file: Path = typer.Argument(..., help="Path to articles CSV/XLSX file."),
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Path | None = typer.Option(None, "--terms", "-t", help="Path to terms XLSX/CSV."),
    sample: int = typer.Option(50, "--sample", "-s", help="Number of articles to sample."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Preview triage results on a sample of articles."""
    _setup_lang(lang)
    from . import controller

    if sample < 1:
        console.print(f"[red]{t('sample_must_be_positive', value=sample)}[/red]")
        raise typer.Exit(1)

    _require_input(input_file)
    _require_config(config)
    _require_terms(terms)

    result = controller.preview_triage(
        input_path=input_file,
        config_path=config,
        terms_path=terms,
        sample_size=sample,
    )

    _print_stats(result.stats)
    console.print(f"\n[dim]{t('preview_note', count=result.sample_size)}[/dim]")


@app.command()
def coverage(
    input_file: Path = typer.Argument(..., help="Path to articles CSV/XLSX file."),
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Path | None = typer.Option(None, "--terms", "-t", help="Path to terms XLSX/CSV."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Export coverage CSV."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Analyze term coverage across all articles."""
    _setup_lang(lang)
    from . import controller

    _require_input(input_file)
    _require_config(config)
    _require_terms(terms)

    report = controller.analyze_coverage(
        input_path=input_file,
        config_path=config,
        terms_path=terms,
        output_path=output,
    )

    console.print(controller.format_coverage(report))


@app.command()
def diff(
    result_a: Path = typer.Argument(..., help="First result file (CSV/XLSX)."),
    result_b: Path = typer.Argument(..., help="Second result file (CSV/XLSX)."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Compare two triage result files."""
    _setup_lang(lang)
    from . import controller

    for result_file in (result_a, result_b):
        if not result_file.exists():
            console.print(f"[red]{t('file_not_found', path=result_file)}[/red]")
            raise typer.Exit(1)

    report = controller.diff_results(result_a, result_b)

    table = Table(title=t("table_diff_title"), show_header=True)
    table.add_column(t("table_article_id"), style="cyan")
    table.add_column(t("table_old_decision"), style="red")
    table.add_column(t("table_new_decision"), style="green")

    for entry in report.changed[:50]:
        table.add_row(entry.article_id, entry.old_decision, entry.new_decision)

    console.print(table)

    if len(report.changed) > 50:
        console.print(f"[dim]{t('diff_more_changes', count=len(report.changed) - 50)}[/dim]")

    console.print(f"\n{t('diff_total_changes', count=len(report.changed))}")
    console.print(t("diff_article_counts", a=report.total_a, b=report.total_b))

    if report.summary:
        console.print(f"\n{t('diff_transitions')}")
        for transition, count in sorted(report.summary.items()):
            console.print(f"  {transition}: {count}")


@app.command(name="new-project")
def new_project(
    name: str = typer.Argument(..., help="Project name."),
    blocks: str = typer.Option(
        ...,
        "--blocks",
        "-b",
        help="Comma-separated block names (e.g., 'CTX,TECH,SCM').",
    ),
    preset: str = typer.Option(
        "standard",
        "--preset",
        "-p",
        help="Level preset: binary, simple, standard.",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output directory."),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite an existing project directory instead of refusing.",
    ),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Create a new triage project with config and terms template."""
    _setup_lang(lang)
    from . import controller

    block_list = [
        {"name": b.strip().upper(), "label": b.strip()} for b in blocks.split(",") if b.strip()
    ]

    if not block_list:
        console.print(f"[red]{t('blocks_required')}[/red]")
        raise typer.Exit(1)

    try:
        project_dir = controller.create_project(
            name=name,
            blocks=block_list,
            preset=preset,
            output_dir=output,
            force=force,
        )
    except FileExistsError as exc:
        console.print(f"[red]{t('project_exists', message=exc)}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"[green]{t('project_created', path=project_dir)}[/green]")
    console.print(t("project_config_hint"))
    console.print(t("project_terms_hint"))


@app.command(name="export")
def export_cmd(
    result_file: Path = typer.Argument(..., help="Path to triage results file."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output directory."),
    config: Path | None = typer.Option(None, "--config", "-c", help="Config file to include."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Export an academic package (ZIP) from triage results."""
    _setup_lang(lang)
    from . import controller

    if not result_file.exists():
        console.print(f"[red]{t('file_not_found', path=result_file)}[/red]")
        raise typer.Exit(1)

    out_dir = output or result_file.parent
    zip_path = controller.export_academic_package(
        result_path=result_file,
        output_dir=out_dir,
        config_path=config,
    )

    console.print(f"[green]{t('academic_exported', path=zip_path)}[/green]")


@app.command(name="terms")
def terms_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Path | None = typer.Option(None, "--terms", "-t", help="Path to terms XLSX/CSV."),
    block: str | None = typer.Option(None, "--block", "-b", help="Filter by block name."),
    kind: str | None = typer.Option(None, "--kind", "-k", help="Filter by kind (pos/anti/flag)."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Browse configured terms."""
    _setup_lang(lang)
    from . import controller

    _require_config(config)
    _require_terms(terms)

    view = controller.browse_terms(
        config_path=config,
        terms_path=terms,
        block_filter=block,
        kind_filter=kind,
    )

    table = Table(title=t("table_terms_title", count=view.total), show_header=True)
    table.add_column(t("table_block"), style="cyan")
    table.add_column(t("table_kind"), style="magenta")
    table.add_column(t("table_term"))
    table.add_column(t("table_level"), justify="center")
    table.add_column(t("table_scope"))

    for entry in view.terms[:200]:
        kind_style = (
            "green" if entry["kind"] == "pos" else "red" if entry["kind"] == "anti" else "yellow"
        )
        table.add_row(
            entry["block"],
            f"[{kind_style}]{entry['kind']}[/{kind_style}]",
            entry["term"],
            str(entry["level"] or ""),
            entry["scope"],
        )

    if view.total > 200:
        console.print(f"[dim]{t('terms_truncated', shown=200, total=view.total)}[/dim]")

    console.print(table)


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    from .tui import main as tui_main

    tui_main()


# ── Profile subcommands ──────────────────────────────────────────────────────


@profile_app.command("save")
def profile_save(
    name: str = typer.Argument(..., help="Profile name."),
    config: Path = typer.Option(..., "--config", "-c", help="Config file to save as profile."),
    description: str = typer.Option("", "--desc", "-d", help="Profile description."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Save a configuration as a named profile."""
    _setup_lang(lang)
    from . import controller

    _require_config(config)

    path = controller.save_profile_config(name, config, description)
    console.print(f"[green]{t('profile_saved', name=name, path=path)}[/green]")


@profile_app.command("load")
def profile_load(
    name: str = typer.Argument(..., help="Profile name."),
    output: Path = typer.Option("config.json", "--output", "-o", help="Output config file path."),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """Load a named profile to a config file."""
    _setup_lang(lang)
    import json

    from . import profiles

    try:
        cfg = profiles.load_profile(name)
    except FileNotFoundError:
        console.print(f"[red]{t('file_not_found', path=name)}[/red]")
        raise typer.Exit(1)

    output.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    console.print(f"[green]{t('profile_loaded', name=name, path=output)}[/green]")


@profile_app.command("list")
def profile_list(
    lang: str | None = typer.Option(None, "--lang", "-l", help="Interface language."),
) -> None:
    """List all saved profiles."""
    _setup_lang(lang)
    from . import profiles

    all_profiles = profiles.list_profiles()

    if not all_profiles:
        console.print(f"[dim]{t('no_profiles')}[/dim]")
        return

    table = Table(title=t("table_profiles_title"), show_header=True)
    table.add_column(t("table_name"), style="cyan")
    table.add_column(t("table_description"))
    table.add_column(t("table_path"), style="dim")

    for p in all_profiles:
        table.add_row(p.name, p.description, str(p.path))

    console.print(table)


def main() -> None:
    """Entry point that wraps the Typer app with a friendly error handler.

    Commands raise plain exceptions (``FileNotFoundError``, ``ValueError``,
    ``json.JSONDecodeError``) deep in the core engine. Without this wrapper they
    surface as raw tracebacks. Here we translate the common ones into a localized
    one-line message and exit with status 1, while letting ``typer.Exit`` /
    ``SystemExit`` (and ``KeyboardInterrupt``) propagate untouched.
    """
    try:
        app()
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]{t('error_generic', message=exc)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
