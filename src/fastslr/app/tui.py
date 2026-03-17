"""FastSLR TUI — interactive terminal interface built with Textual.

Designed for researchers who are not programmers. Every screen uses
plain language, contextual help, and visible navigation.
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    ProgressBar,
    RadioButton,
    RadioSet,
    Select,
    Static,
    TextArea,
)

from ..core.constants import VERSION
from ..i18n import _ as t
from ..i18n import SUPPORTED_LOCALES, set_locale


# ── Dashboard ────────────────────────────────────────────────────────────────


MENU_ITEMS = [
    ("new_project", "1", "New Project", "Create a new systematic review project"),
    ("load_profile", "2", "Load Profile", "Load a saved configuration profile"),
    ("edit_config", "3", "Edit Configuration", "View and edit triage parameters"),
    ("browse_terms", "4", "Browse Terms", "View search terms by block and type"),
    ("run_triage", "5", "Run Triage", "Execute triage on your articles"),
    ("results", "6", "Results Explorer", "Browse and filter triage results"),
    ("coverage", "7", "Coverage Analysis", "Check which terms matched"),
    ("diff_runs", "8", "Compare Runs", "Compare two triage results"),
    ("export", "9", "Export Academic Package", "Generate publication-ready ZIP"),
    ("settings", "0", "Settings & Language", "Change language and preferences"),
]


class DashboardScreen(Screen):
    """Main menu — the entry point for all TUI workflows."""

    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
        Binding("1", "menu_1", "", show=False),
        Binding("2", "menu_2", "", show=False),
        Binding("3", "menu_3", "", show=False),
        Binding("4", "menu_4", "", show=False),
        Binding("5", "menu_5", "", show=False),
        Binding("6", "menu_6", "", show=False),
        Binding("7", "menu_7", "", show=False),
        Binding("8", "menu_8", "", show=False),
        Binding("9", "menu_9", "", show=False),
        Binding("0", "menu_0", "", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static(
                f"\n  [bold cyan]FastSLR v{VERSION}[/bold cyan]"
                f" — Systematic Review Triage Engine\n",
                id="title",
            )
            with Container(id="menu"):
                for action_id, key, label, desc in MENU_ITEMS:
                    yield Button(
                        f"[{key}]  {label}",
                        id=action_id,
                        classes="menu-btn",
                    )
            yield Static(
                "\n  [dim]Press a number key or click a button. Press Q to quit.[/dim]\n",
                id="hint",
            )
        yield Footer()

    def _navigate(self, action_id: str) -> None:
        screen_map = {
            "run_triage": RunTriageScreen,
            "new_project": NewProjectScreen,
            "browse_terms": BrowseTermsScreen,
            "results": ResultsScreen,
            "coverage": CoverageScreen,
            "settings": SettingsScreen,
            "load_profile": ProfilesScreen,
            "export": ExportScreen,
            "edit_config": EditConfigScreen,
            "diff_runs": DiffScreen,
        }
        screen_class = screen_map.get(action_id)
        if screen_class:
            self.app.push_screen(screen_class())

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        self._navigate(event.button.id or "")

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_menu_1(self) -> None:
        self._navigate("new_project")

    def action_menu_2(self) -> None:
        self._navigate("load_profile")

    def action_menu_3(self) -> None:
        self._navigate("edit_config")

    def action_menu_4(self) -> None:
        self._navigate("browse_terms")

    def action_menu_5(self) -> None:
        self._navigate("run_triage")

    def action_menu_6(self) -> None:
        self._navigate("results")

    def action_menu_7(self) -> None:
        self._navigate("coverage")

    def action_menu_8(self) -> None:
        self._navigate("diff_runs")

    def action_menu_9(self) -> None:
        self._navigate("export")

    def action_menu_0(self) -> None:
        self._navigate("settings")


# ── Run Triage ───────────────────────────────────────────────────────────────


class RunTriageScreen(Screen):
    """Execute triage on articles — the core workflow."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Run Triage[/bold]\n")
            yield Static("  Choose your articles file (CSV or XLSX):")
            yield Input(placeholder="Path to articles file...", id="input_file")
            yield Static("\n  Configuration file (config.json):")
            yield Input(placeholder="Path to config.json...", id="config_file")
            yield Static("\n  Terms file (optional, CSV):")
            yield Input(placeholder="Path to terms CSV (leave empty to skip)...", id="terms_file")
            yield Static("\n  Output directory (optional):")
            yield Input(placeholder="Output directory (leave empty for default)...", id="output_dir")
            yield Static("")
            with Horizontal():
                yield Button("Run Triage", variant="primary", id="btn_run")
                yield Button("Cancel", variant="default", id="btn_cancel")
            yield Static("", id="status")
            yield ProgressBar(total=100, show_eta=True, id="progress")
            yield Static("", id="results")
        yield Footer()

    @on(Button.Pressed, "#btn_cancel")
    def cancel(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn_run")
    def start_triage(self) -> None:
        self._run_triage()

    @work(thread=True)
    def _run_triage(self) -> None:
        from . import controller

        input_path = self.query_one("#input_file", Input).value.strip()
        config_path = self.query_one("#config_file", Input).value.strip()
        terms_path = self.query_one("#terms_file", Input).value.strip()
        output_dir = self.query_one("#output_dir", Input).value.strip()

        status = self.query_one("#status", Static)
        progress = self.query_one("#progress", ProgressBar)
        results = self.query_one("#results", Static)

        if not input_path or not config_path:
            self.app.call_from_thread(
                status.update, "  [red]Please provide both articles file and config file.[/red]"
            )
            return

        input_p = Path(input_path)
        config_p = Path(config_path)

        if not input_p.exists():
            self.app.call_from_thread(
                status.update, f"  [red]{t('file_not_found', path=input_path)}[/red]"
            )
            return

        if not config_p.exists():
            self.app.call_from_thread(
                status.update, f"  [red]{t('config_not_found', path=config_path)}[/red]"
            )
            return

        self.app.call_from_thread(status.update, "  [cyan]Running triage...[/cyan]")
        self.app.call_from_thread(progress.update, total=100, progress=0)

        def on_progress(current: int, total: int) -> None:
            pct = int(current / max(total, 1) * 100)
            self.app.call_from_thread(progress.update, total=100, progress=pct)

        try:
            result = controller.run_triage(
                input_path=input_p,
                config_path=config_p,
                terms_path=Path(terms_path) if terms_path else None,
                output_dir=Path(output_dir) if output_dir else None,
                on_progress=on_progress,
            )

            self.app.call_from_thread(progress.update, total=100, progress=100)

            stats = result.stats
            dist = stats.get("decision_distribution", {})
            approved = dist.get("APPROVED_FINAL", 0)
            flagged = dist.get("FLAGGED_FINAL", 0)
            rejected = dist.get("REJECTED_FINAL", 0)
            total = stats.get("total_articles", 0)
            time_s = stats.get("processing_time", 0)

            summary = (
                f"\n  [bold green]Triage complete![/bold green]\n\n"
                f"  {t('table_total_articles')}: {total}\n"
                f"  {t('table_processing_time')}: {time_s:.2f}s\n\n"
                f"  [green]APPROVED: {approved}[/green]  "
                f"[yellow]FLAGGED: {flagged}[/yellow]  "
                f"[red]REJECTED: {rejected}[/red]\n\n"
                f"  {t('triage_complete', path=result.output_dir)}\n"
            )
            self.app.call_from_thread(results.update, summary)
            self.app.call_from_thread(status.update, "  [green]Done.[/green]")

        except Exception as e:
            self.app.call_from_thread(
                status.update, f"  [red]Error: {e}[/red]"
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── New Project Wizard ───────────────────────────────────────────────────────


class NewProjectScreen(Screen):
    """Guided project creation — step by step."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]New Project — Step 1 of 3[/bold]\n")
            yield Static("  What is your review about?\n")
            yield Static("  Project name:")
            yield Input(placeholder="e.g., AI_in_Healthcare", id="project_name")
            yield Static("\n  How many thematic areas does your review cover?")
            yield Static(
                "  [dim]For example, a review about 'AI in Education' might have\n"
                "  two areas: Artificial Intelligence and Education.[/dim]\n"
            )
            yield Static("  Block names (comma-separated):")
            yield Input(placeholder="e.g., AI, HEALTH, METHODS", id="blocks")
            yield Static(
                "\n  How strict should the screening be?\n"
            )
            with RadioSet(id="preset"):
                yield RadioButton("Recommended — Balanced (5 levels)", value=True, id="standard")
                yield RadioButton("Sensitive — Keeps more articles (3 levels)", id="simple")
                yield RadioButton("Quick — Binary include/exclude (1 level)", id="binary")
            yield Static("\n  Output directory (leave empty for current folder):")
            yield Input(placeholder="Optional output path...", id="output_dir")
            yield Static("")
            with Horizontal():
                yield Button("Create Project", variant="primary", id="btn_create")
                yield Button("Cancel", variant="default", id="btn_cancel")
            yield Static("", id="result_msg")
        yield Footer()

    @on(Button.Pressed, "#btn_cancel")
    def cancel(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn_create")
    def create(self) -> None:
        from . import controller

        name = self.query_one("#project_name", Input).value.strip()
        blocks_raw = self.query_one("#blocks", Input).value.strip()
        output_raw = self.query_one("#output_dir", Input).value.strip()
        result_msg = self.query_one("#result_msg", Static)

        if not name:
            result_msg.update("  [red]Please enter a project name.[/red]")
            return

        if not blocks_raw:
            result_msg.update("  [red]Please enter at least one block name.[/red]")
            return

        # Determine preset from radio selection
        preset = "standard"
        radio_set = self.query_one("#preset", RadioSet)
        if radio_set.pressed_button:
            preset_map = {"standard": "standard", "simple": "simple", "binary": "binary"}
            preset = preset_map.get(radio_set.pressed_button.id or "", "standard")

        block_list = [
            {"name": b.strip().upper(), "label": b.strip()}
            for b in blocks_raw.split(",")
            if b.strip()
        ]

        try:
            output_dir = Path(output_raw) if output_raw else None
            project_dir = controller.create_project(
                name=name,
                blocks=block_list,
                preset=preset,
                output_dir=output_dir,
            )
            result_msg.update(
                f"\n  [bold green]{t('project_created', path=project_dir)}[/bold green]\n"
                f"  {t('project_config_hint')}\n"
                f"  {t('project_terms_hint')}\n"
            )
        except Exception as e:
            result_msg.update(f"  [red]Error: {e}[/red]")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Browse Terms ─────────────────────────────────────────────────────────────


class BrowseTermsScreen(Screen):
    """View all configured search terms."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Browse Terms[/bold]\n")
            yield Static("  Config file:")
            yield Input(placeholder="Path to config.json...", id="config_path")
            yield Static("  Terms CSV:")
            yield Input(placeholder="Path to terms.csv...", id="terms_path")
            yield Static("")
            yield Button("Load Terms", variant="primary", id="btn_load")
            yield Static("")
            yield DataTable(id="terms_table")
        yield Footer()

    @on(Button.Pressed, "#btn_load")
    def load_terms(self) -> None:
        from . import controller

        config_path = self.query_one("#config_path", Input).value.strip()
        terms_path = self.query_one("#terms_path", Input).value.strip()

        if not config_path:
            return

        try:
            view = controller.browse_terms(
                config_path=Path(config_path),
                terms_path=Path(terms_path) if terms_path else None,
            )

            table = self.query_one("#terms_table", DataTable)
            table.clear(columns=True)
            table.add_columns(
                t("table_block"), t("table_kind"), t("table_term"),
                t("table_level"), t("table_scope"),
            )

            for entry in view.terms[:500]:
                table.add_row(
                    entry["block"],
                    entry["kind"],
                    entry["term"],
                    str(entry["level"] or ""),
                    entry["scope"],
                )
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Results Explorer ─────────────────────────────────────────────────────────


class ResultsScreen(Screen):
    """Browse triage results with filtering."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Results Explorer[/bold]\n")
            yield Static("  Results file (XLSX or CSV):")
            yield Input(placeholder="Path to triage_results.xlsx...", id="results_path")
            yield Static("  Filter by decision:")
            yield Select(
                [
                    ("All", "all"),
                    ("Approved", "APPROVED_FINAL"),
                    ("Flagged", "FLAGGED_FINAL"),
                    ("Rejected", "REJECTED_FINAL"),
                ],
                value="all",
                id="filter_decision",
            )
            yield Button("Load Results", variant="primary", id="btn_load")
            yield Static("", id="summary")
            yield DataTable(id="results_table")
        yield Footer()

    @on(Button.Pressed, "#btn_load")
    def load_results(self) -> None:
        import pandas as pd

        results_path = self.query_one("#results_path", Input).value.strip()
        filter_val = self.query_one("#filter_decision", Select).value

        if not results_path:
            return

        try:
            path = Path(results_path)
            df = pd.read_excel(path) if path.suffix == ".xlsx" else pd.read_csv(path)

            if filter_val != "all" and "Final_Decision" in df.columns:
                df = df[df["Final_Decision"] == filter_val]

            summary = self.query_one("#summary", Static)
            summary.update(f"\n  Showing {len(df)} articles\n")

            table = self.query_one("#results_table", DataTable)
            table.clear(columns=True)

            # Show key columns
            show_cols = []
            for col in df.columns:
                if col in ("ID", "key", "Key") or col.startswith("Final_") or col.startswith("Status_") or col.startswith("FinalScore_"):
                    show_cols.append(col)

            if not show_cols:
                show_cols = list(df.columns[:6])

            table.add_columns(*show_cols)
            for _, row in df.head(200).iterrows():
                table.add_row(*[str(row.get(c, "")) for c in show_cols])

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Coverage ─────────────────────────────────────────────────────────────────


class CoverageScreen(Screen):
    """Analyze which terms matched and which didn't."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Coverage Analysis[/bold]\n")
            yield Static("  Articles file:")
            yield Input(placeholder="Path to articles CSV...", id="input_file")
            yield Static("  Config file:")
            yield Input(placeholder="Path to config.json...", id="config_file")
            yield Static("  Terms CSV:")
            yield Input(placeholder="Path to terms.csv...", id="terms_file")
            yield Static("")
            yield Button("Analyze Coverage", variant="primary", id="btn_analyze")
            yield Static("", id="report_output")
        yield Footer()

    @on(Button.Pressed, "#btn_analyze")
    def analyze(self) -> None:
        from . import controller
        from ..core.coverage import format_coverage_report

        input_path = self.query_one("#input_file", Input).value.strip()
        config_path = self.query_one("#config_file", Input).value.strip()
        terms_path = self.query_one("#terms_file", Input).value.strip()

        if not input_path or not config_path:
            self.notify("Please provide articles file and config file.", severity="warning")
            return

        try:
            report = controller.analyze_coverage(
                input_path=Path(input_path),
                config_path=Path(config_path),
                terms_path=Path(terms_path) if terms_path else None,
            )
            output = self.query_one("#report_output", Static)
            output.update(f"\n{format_coverage_report(report)}\n")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Diff ─────────────────────────────────────────────────────────────────────


class DiffScreen(Screen):
    """Compare two triage runs."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Compare Runs[/bold]\n")
            yield Static("  First result file:")
            yield Input(placeholder="Path to first results file...", id="file_a")
            yield Static("  Second result file:")
            yield Input(placeholder="Path to second results file...", id="file_b")
            yield Static("")
            yield Button("Compare", variant="primary", id="btn_compare")
            yield Static("", id="diff_output")
            yield DataTable(id="diff_table")
        yield Footer()

    @on(Button.Pressed, "#btn_compare")
    def compare(self) -> None:
        from . import controller

        file_a = self.query_one("#file_a", Input).value.strip()
        file_b = self.query_one("#file_b", Input).value.strip()

        if not file_a or not file_b:
            self.notify("Please provide both result files.", severity="warning")
            return

        try:
            report = controller.diff_results(Path(file_a), Path(file_b))

            output = self.query_one("#diff_output", Static)
            output.update(
                f"\n  {t('diff_total_changes', count=len(report.changed))}\n"
                f"  {t('diff_article_counts', a=report.total_a, b=report.total_b)}\n"
            )

            table = self.query_one("#diff_table", DataTable)
            table.clear(columns=True)
            table.add_columns(
                t("table_article_id"), t("table_old_decision"), t("table_new_decision"),
            )
            for entry in report.changed[:200]:
                table.add_row(entry.article_id, entry.old_decision, entry.new_decision)

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Export ───────────────────────────────────────────────────────────────────


class ExportScreen(Screen):
    """Export academic package."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Export Academic Package[/bold]\n")
            yield Static("  Results file:")
            yield Input(placeholder="Path to triage_results.xlsx...", id="result_file")
            yield Static("  Output directory:")
            yield Input(placeholder="Output directory...", id="output_dir")
            yield Static("  Config file (optional, to include in package):")
            yield Input(placeholder="Path to config.json...", id="config_file")
            yield Static("")
            yield Button("Export", variant="primary", id="btn_export")
            yield Static("", id="export_msg")
        yield Footer()

    @on(Button.Pressed, "#btn_export")
    def do_export(self) -> None:
        from . import controller

        result_file = self.query_one("#result_file", Input).value.strip()
        output_dir = self.query_one("#output_dir", Input).value.strip()
        config_file = self.query_one("#config_file", Input).value.strip()

        if not result_file:
            self.notify("Please provide a results file.", severity="warning")
            return

        try:
            zip_path = controller.export_academic_package(
                result_path=Path(result_file),
                output_dir=Path(output_dir) if output_dir else Path(result_file).parent,
                config_path=Path(config_file) if config_file else None,
            )
            msg = self.query_one("#export_msg", Static)
            msg.update(f"\n  [green]{t('academic_exported', path=zip_path)}[/green]\n")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Edit Config ──────────────────────────────────────────────────────────────


class EditConfigScreen(Screen):
    """View and edit configuration parameters."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Edit Configuration[/bold]\n")
            yield Static("  Config file:")
            yield Input(placeholder="Path to config.json...", id="config_path")
            yield Static("")
            yield Button("Load", variant="primary", id="btn_load")
            yield Button("Save Changes", variant="warning", id="btn_save")
            yield Static("")
            yield TextArea(id="config_editor", language="json")
        yield Footer()

    @on(Button.Pressed, "#btn_load")
    def load_config(self) -> None:
        config_path = self.query_one("#config_path", Input).value.strip()
        if not config_path:
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            editor = self.query_one("#config_editor", TextArea)
            editor.load_text(content)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn_save")
    def save_config(self) -> None:
        config_path = self.query_one("#config_path", Input).value.strip()
        if not config_path:
            self.notify("No config file path specified.", severity="warning")
            return

        try:
            editor = self.query_one("#config_editor", TextArea)
            content = editor.text
            # Validate JSON
            json.loads(content)
            Path(config_path).write_text(content, encoding="utf-8")
            self.notify("Configuration saved.", severity="information")
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON: {e}", severity="error")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Profiles ─────────────────────────────────────────────────────────────────


class ProfilesScreen(Screen):
    """Load and manage saved profiles."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Saved Profiles[/bold]\n")
            yield DataTable(id="profiles_table")
            yield Static("")
            yield Button("Refresh", variant="primary", id="btn_refresh")
        yield Footer()

    def on_mount(self) -> None:
        self._load_profiles()

    @on(Button.Pressed, "#btn_refresh")
    def refresh(self) -> None:
        self._load_profiles()

    def _load_profiles(self) -> None:
        from . import profiles

        all_profiles = profiles.list_profiles()
        table = self.query_one("#profiles_table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("table_name"), t("table_description"), t("table_path"))

        if not all_profiles:
            table.add_row(t("no_profiles"), "", "")
        else:
            for p in all_profiles:
                table.add_row(p.name, p.description, str(p.path))

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Settings ─────────────────────────────────────────────────────────────────


class SettingsScreen(Screen):
    """Change language and preferences."""

    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("\n  [bold]Settings & Language[/bold]\n")
            yield Static("  Interface language:")
            yield Select(
                [
                    ("English", "en"),
                    ("Portugues (Brasil)", "pt_BR"),
                    ("Espanol", "es"),
                ],
                value="en",
                id="lang_select",
            )
            yield Static("")
            yield Button("Apply", variant="primary", id="btn_apply")
            yield Static("", id="settings_msg")
            yield Static(
                "\n  [dim]Language changes take effect on new screens.\n"
                "  Tip: Set FASTSLR_LANG environment variable for permanent setting.[/dim]\n"
            )
        yield Footer()

    @on(Button.Pressed, "#btn_apply")
    def apply_settings(self) -> None:
        lang = self.query_one("#lang_select", Select).value
        if lang:
            set_locale(str(lang))
            msg = self.query_one("#settings_msg", Static)
            msg.update(f"\n  [green]Language set to: {lang}[/green]\n")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ── Main App ─────────────────────────────────────────────────────────────────


class FastSLRApp(App):
    """FastSLR — Interactive TUI for Systematic Literature Review triage."""

    TITLE = f"FastSLR v{VERSION}"
    CSS = """
    Screen {
        background: $surface;
    }

    #menu {
        padding: 1 2;
    }

    .menu-btn {
        width: 100%;
        margin: 0 0 0 0;
    }

    #title {
        text-align: center;
    }

    #hint {
        text-align: center;
    }

    DataTable {
        height: auto;
        max-height: 30;
        margin: 1 2;
    }

    TextArea {
        height: 25;
        margin: 0 2;
    }

    Input {
        margin: 0 2;
    }

    Button {
        margin: 0 1;
    }

    ProgressBar {
        margin: 1 2;
    }

    Horizontal {
        height: auto;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        self.push_screen(DashboardScreen())


def main() -> None:
    """Launch the FastSLR interactive TUI."""
    app = FastSLRApp()
    app.run()


if __name__ == "__main__":
    main()
