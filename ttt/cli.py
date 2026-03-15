"""Unified CLI for the Telecom Test Toolkit.

Commands:
    ttt plugins         — List all discovered plugins
    ttt run <plugin>    — Run a single plugin
    ttt pipeline        — Run the full analysis pipeline
    ttt dashboard       — Launch the Streamlit dashboard
"""

import os

import click
from rich.console import Console
from rich.table import Table

from ttt.models import PipelineContext
from ttt.pipeline import print_pipeline_summary, run_pipeline, run_single_plugin
from ttt.plugin import discover_plugins

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="Telecom Test Toolkit")
def cli():
    """🚀 Telecom Test Toolkit — Plugin-based ecosystem for telecom test engineers."""
    pass


@cli.command("plugins")
def list_plugins():
    """List all discovered plugins."""
    plugins = discover_plugins()

    if not plugins:
        console.print(
            "[yellow]No plugins found. Install plugins or run 'pip install -e .'[/yellow]"
        )
        return

    table = Table(title="🧩 Discovered Plugins")
    table.add_column("Name", style="cyan bold")
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="dim")

    for name, plugin in sorted(plugins.items()):
        table.add_row(name, plugin.plugin_type, plugin.description)

    console.print(table)
    console.print(f"\n[dim]Total: {len(plugins)} plugins[/dim]")


@cli.command("run")
@click.argument("plugin_name")
@click.option("--input", "-i", "input_files", multiple=True, help="Input log file(s)")
@click.option(
    "--output", "-o", "output_dir", default="./ttt_output", help="Output directory"
)
def run_plugin(plugin_name, input_files, output_dir):
    """Run a single plugin by name."""
    if not input_files:
        console.print(
            "[red]Error: Please provide at least one input file with --input[/red]"
        )
        return

    # Validate input files exist
    for f in input_files:
        if not os.path.exists(f):
            console.print(f"[red]Error: File not found: {f}[/red]")
            return

    context = PipelineContext(
        log_files=list(input_files),
        output_dir=output_dir,
    )

    context = run_single_plugin(plugin_name, context)
    print_pipeline_summary(context)


@cli.command("pipeline")
@click.option(
    "--logs", "-l", "log_files", multiple=True, required=True, help="Input log file(s)"
)
@click.option(
    "--output", "-o", "output_dir", default="./ttt_output", help="Output directory"
)
@click.option("--only", "only_plugins", multiple=True, help="Run only these plugins")
@click.option(
    "--skip",
    "skip_types",
    multiple=True,
    default=["dashboard"],
    help="Skip plugin types",
)
def pipeline(log_files, output_dir, only_plugins, skip_types):
    """Run the full analysis pipeline on log files."""
    # Validate input files
    for f in log_files:
        if not os.path.exists(f):
            console.print(f"[red]Error: File not found: {f}[/red]")
            return

    context = PipelineContext(
        log_files=list(log_files),
        output_dir=output_dir,
    )

    plugin_names = list(only_plugins) if only_plugins else None
    context = run_pipeline(
        context, plugin_names=plugin_names, skip_types=list(skip_types)
    )
    print_pipeline_summary(context)


@cli.command("dashboard")
@click.option(
    "--data-dir", "-d", default="./ttt_output", help="Directory with pipeline results"
)
@click.option("--port", "-p", default=8501, help="Streamlit port")
def dashboard(data_dir, port):
    """Launch the Test Monitor Dashboard."""
    console.print("[bold cyan]🖥️  Launching Test Monitor Dashboard...[/bold cyan]")

    # Check if streamlit is available
    try:
    except ImportError:
        console.print("[red]Error: streamlit is not installed.[/red]")
        console.print(
            "[dim]Install with: pip install 'telecom-test-toolkit[dashboard]'[/dim]"
        )
        return

    dashboard_app = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "test-monitor-dashboard", "app.py"
    )

    if not os.path.exists(dashboard_app):
        console.print(f"[red]Error: Dashboard app not found at {dashboard_app}[/red]")
        return

    os.environ["TTT_DATA_DIR"] = os.path.abspath(data_dir)
    os.system(f"streamlit run {dashboard_app} --server.port {port}")


def main():
    cli()


if __name__ == "__main__":
    main()
