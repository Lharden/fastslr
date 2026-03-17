"""FastSLR CLI — batch mode entry point.

Usage:
    fastslr run <input> --config <config.json> --terms <terms.csv>
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

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from ..core.constants import VERSION

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


def _rich_progress_callback(progress: Progress, task_id: int):
    """Return a callback that updates a rich progress bar."""

    def _on_progress(current: int, total: int) -> None:
        progress.update(task_id, completed=current, total=total)

    return _on_progress


def _print_stats(stats: dict) -> None:
    """Print triage statistics as a rich table."""
    table = Table(title="Triage Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")

    table.add_row("Total articles", str(stats.get("total_articles", 0)))
    table.add_row(
        "Processing time",
        f"{stats.get('processing_time', 0):.2f}s",
    )
    table.add_row(
        "Speed",
        f"{stats.get('articles_per_second', 0):.1f} articles/s",
    )

    dist = stats.get("decision_distribution", {})
    for decision, count in sorted(dist.items()):
        style = (
            "green" if "APPROVED" in decision
            else "yellow" if "FLAGGED" in decision
            else "red"
        )
        table.add_row(f"  {decision}", f"[{style}]{count}[/{style}]")

    if stats.get("error_count", 0) > 0:
        table.add_row("Errors", f"[red]{stats['error_count']}[/red]")

    console.print(table)


# ── Commands ─────────────────────────────────────────────────────────────────


@app.command()
def version() -> None:
    """Show FastSLR version."""
    console.print(f"FastSLR v{VERSION}")


@app.command()
def run(
    input_file: Path = typer.Argument(..., help="Path to articles CSV/XLSX file."),
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Optional[Path] = typer.Option(None, "--terms", "-t", help="Path to terms CSV."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory."),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Interface language."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output."),
) -> None:
    """Run triage on an articles file."""
    from . import controller

    if not input_file.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        raise typer.Exit(1)

    if not config.exists():
        console.print(f"[red]Config not found: {config}[/red]")
        raise typer.Exit(1)

    # Validate config first
    prepared = controller._prepare_config(config, terms)
    issues = controller.validate_config(prepared)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        for issue in errors:
            console.print(f"[red]Config error: {issue.message}[/red]")
        raise typer.Exit(1)

    warnings = [i for i in issues if i.level == "warning"]
    if warnings and not quiet:
        for issue in warnings:
            console.print(f"[yellow]Warning: {issue.message}[/yellow]")

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
        console.print(f"\n[green]Results saved to: {result.output_dir}[/green]")


@app.command()
def preview(
    input_file: Path = typer.Argument(..., help="Path to articles CSV/XLSX file."),
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Optional[Path] = typer.Option(None, "--terms", "-t", help="Path to terms CSV."),
    sample: int = typer.Option(50, "--sample", "-s", help="Number of articles to sample."),
) -> None:
    """Preview triage results on a sample of articles."""
    from . import controller

    if not input_file.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        raise typer.Exit(1)

    result = controller.preview_triage(
        input_path=input_file,
        config_path=config,
        terms_path=terms,
        sample_size=sample,
    )

    _print_stats(result.stats)
    console.print(f"\n[dim]Preview based on {result.sample_size} sampled articles.[/dim]")


@app.command()
def coverage(
    input_file: Path = typer.Argument(..., help="Path to articles CSV/XLSX file."),
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Optional[Path] = typer.Option(None, "--terms", "-t", help="Path to terms CSV."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Export coverage CSV."),
) -> None:
    """Analyze term coverage across all articles."""
    from . import controller
    from ..core.coverage import format_coverage_report

    report = controller.analyze_coverage(
        input_path=input_file,
        config_path=config,
        terms_path=terms,
        output_path=output,
    )

    console.print(format_coverage_report(report))


@app.command()
def diff(
    result_a: Path = typer.Argument(..., help="First result file (CSV/XLSX)."),
    result_b: Path = typer.Argument(..., help="Second result file (CSV/XLSX)."),
) -> None:
    """Compare two triage result files."""
    from . import controller

    report = controller.diff_results(result_a, result_b)

    table = Table(title="Triage Diff", show_header=True)
    table.add_column("Article ID", style="cyan")
    table.add_column("Old Decision", style="red")
    table.add_column("New Decision", style="green")

    for entry in report.changed[:50]:
        table.add_row(entry.article_id, entry.old_decision, entry.new_decision)

    console.print(table)

    if len(report.changed) > 50:
        console.print(f"[dim]... and {len(report.changed) - 50} more changes[/dim]")

    console.print(f"\nTotal changes: [bold]{len(report.changed)}[/bold]")
    console.print(f"Articles in A: {report.total_a}, in B: {report.total_b}")

    if report.summary:
        console.print("\nTransitions:")
        for transition, count in sorted(report.summary.items()):
            console.print(f"  {transition}: {count}")


@app.command(name="new-project")
def new_project(
    name: str = typer.Argument(..., help="Project name."),
    blocks: str = typer.Option(
        ..., "--blocks", "-b",
        help="Comma-separated block names (e.g., 'CTX,TECH,SCM').",
    ),
    preset: str = typer.Option(
        "standard", "--preset", "-p",
        help="Level preset: binary, simple, standard.",
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory."),
) -> None:
    """Create a new triage project with config and terms template."""
    from . import controller

    block_list = [
        {"name": b.strip().upper(), "label": b.strip()}
        for b in blocks.split(",")
        if b.strip()
    ]

    if not block_list:
        console.print("[red]At least one block name is required.[/red]")
        raise typer.Exit(1)

    project_dir = controller.create_project(
        name=name,
        blocks=block_list,
        preset=preset,
        output_dir=output,
    )

    console.print(f"[green]Project created: {project_dir}[/green]")
    console.print(f"  config.json  — edit thresholds and parameters")
    console.print(f"  terms.csv    — add your search terms here")


@app.command(name="export")
def export_cmd(
    result_file: Path = typer.Argument(..., help="Path to triage results file."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory."),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file to include."),
) -> None:
    """Export an academic package (ZIP) from triage results."""
    from . import controller

    if not result_file.exists():
        console.print(f"[red]File not found: {result_file}[/red]")
        raise typer.Exit(1)

    out_dir = output or result_file.parent
    zip_path = controller.export_academic_package(
        result_path=result_file,
        output_dir=out_dir,
        config_path=config,
    )

    console.print(f"[green]Academic package exported: {zip_path}[/green]")


@app.command(name="terms")
def terms_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to config.json."),
    terms: Optional[Path] = typer.Option(None, "--terms", "-t", help="Path to terms CSV."),
    block: Optional[str] = typer.Option(None, "--block", "-b", help="Filter by block name."),
    kind: Optional[str] = typer.Option(None, "--kind", "-k", help="Filter by kind (pos/anti/flag)."),
) -> None:
    """Browse configured terms."""
    from . import controller

    view = controller.browse_terms(
        config_path=config,
        terms_path=terms,
        block_filter=block,
        kind_filter=kind,
    )

    table = Table(title=f"Terms ({view.total} total)", show_header=True)
    table.add_column("Block", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Term")
    table.add_column("Level", justify="center")
    table.add_column("Scope")

    for entry in view.terms[:200]:
        kind_style = (
            "green" if entry["kind"] == "pos"
            else "red" if entry["kind"] == "anti"
            else "yellow"
        )
        table.add_row(
            entry["block"],
            f"[{kind_style}]{entry['kind']}[/{kind_style}]",
            entry["term"],
            str(entry["level"] or ""),
            entry["scope"],
        )

    if view.total > 200:
        console.print(f"[dim]Showing first 200 of {view.total} terms.[/dim]")

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
) -> None:
    """Save a configuration as a named profile."""
    from . import profiles
    from ..core.config import load_config

    cfg = load_config(config)
    path = profiles.save_profile(name, cfg, description)
    console.print(f"[green]Profile '{name}' saved: {path}[/green]")


@profile_app.command("load")
def profile_load(
    name: str = typer.Argument(..., help="Profile name."),
    output: Path = typer.Option(
        "config.json", "--output", "-o", help="Output config file path."
    ),
) -> None:
    """Load a named profile to a config file."""
    from . import profiles
    import json

    cfg = profiles.load_profile(name)
    output.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    console.print(f"[green]Profile '{name}' loaded to: {output}[/green]")


@profile_app.command("list")
def profile_list() -> None:
    """List all saved profiles."""
    from . import profiles

    all_profiles = profiles.list_profiles()

    if not all_profiles:
        console.print("[dim]No profiles saved yet.[/dim]")
        return

    table = Table(title="Saved Profiles", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Path", style="dim")

    for p in all_profiles:
        table.add_row(p.name, p.description, str(p.path))

    console.print(table)


if __name__ == "__main__":
    app()
