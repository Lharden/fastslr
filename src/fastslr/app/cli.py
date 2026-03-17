"""FastSLR CLI — batch mode entry point.

This module will be fully implemented in Phase 2.
"""

from __future__ import annotations

import typer

from ..core.constants import VERSION

app = typer.Typer(
    name="fastslr",
    help="FastSLR — Universal deterministic triage for Systematic Literature Reviews.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Show FastSLR version."""
    typer.echo(f"FastSLR v{VERSION}")


if __name__ == "__main__":
    app()
