"""Pipeline engine that chains plugins together.

Execution order:
1. Analyzers (testwatch, log-analyzer, testscope) — process raw logs
2. Scorers (flakiness-scorer) — analyze patterns in results
3. Reporters (report-generator) — generate output reports
4. Dashboard (optional) — launch live visualization

Each plugin appends its AnalysisResult to the shared PipelineContext,
making data available to downstream plugins.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

from ttt.models import PipelineContext
from ttt.plugin import TTTPlugin, discover_plugins
from ttt.store import save_context

console = Console()

# Execution order by plugin type
EXECUTION_ORDER = ["analyzer", "scorer", "reporter"]


def run_pipeline(
    context: PipelineContext,
    plugin_names: Optional[List[str]] = None,
    skip_types: Optional[List[str]] = None,
) -> PipelineContext:
    """Run the full pipeline or a subset of plugins.

    Args:
        context: Pipeline context with log files and config.
        plugin_names: If provided, only run these specific plugins.
            If None, run all discovered plugins in order.
        skip_types: Plugin types to skip (e.g. ["dashboard"]).

    Returns:
        Updated PipelineContext with all results.
    """
    skip_types = skip_types or ["dashboard"]
    all_plugins = discover_plugins()

    if plugin_names:
        # Run only the requested plugins
        plugins_to_run = {
            name: p for name, p in all_plugins.items() if name in plugin_names
        }
    else:
        plugins_to_run = all_plugins

    # Group by type for ordered execution
    grouped: Dict[str, List[Tuple[str, TTTPlugin]]] = {
        t: [] for t in EXECUTION_ORDER
    }
    for name, plugin in plugins_to_run.items():
        ptype = plugin.plugin_type
        if ptype in skip_types:
            continue
        if ptype in grouped:
            grouped[ptype].append((name, plugin))
        else:
            grouped[ptype] = [(name, plugin)]

    # Execute in order
    total_run = 0
    for ptype in EXECUTION_ORDER:
        plugins_of_type = grouped.get(ptype, [])
        if not plugins_of_type:
            continue

        console.print(f"\n[bold cyan]▶ Running {ptype}s...[/bold cyan]")

        for name, plugin in plugins_of_type:
            console.print(f"  [dim]→ {name}:[/dim] {plugin.description}")

            if not plugin.validate(context):
                console.print(
                    f"  [yellow]⏭  Skipped {name} (validation failed)[/yellow]"
                )
                continue

            try:
                result = plugin.run(context)
                context.results.append(result)
                total_run += 1
                console.print(f"  [green]✓ {name} completed[/green]")
            except Exception as e:
                console.print(f"  [red]✗ {name} failed: {e}[/red]")

    # Save results to data store
    if context.results:
        filepath = save_context(context)
        console.print(f"\n[bold green]✅ Pipeline complete![/bold green]")
        console.print(f"   Plugins run: {total_run}")
        console.print(f"   Results saved to: {filepath}")
    else:
        console.print("\n[yellow]No results generated.[/yellow]")

    return context


def run_single_plugin(
    plugin_name: str,
    context: PipelineContext,
) -> PipelineContext:
    """Run a single plugin by name.

    Args:
        plugin_name: Registered name of the plugin.
        context: Pipeline context.

    Returns:
        Updated PipelineContext.
    """
    all_plugins = discover_plugins()

    if plugin_name not in all_plugins:
        console.print(f"[red]Error: Plugin '{plugin_name}' not found.[/red]")
        available = ", ".join(all_plugins.keys())
        console.print(f"[dim]Available plugins: {available}[/dim]")
        return context

    plugin = all_plugins[plugin_name]
    console.print(
        f"\n[bold cyan]▶ Running {plugin_name}[/bold cyan] — {plugin.description}"
    )

    if not plugin.validate(context):
        console.print(f"[yellow]Validation failed for {plugin_name}[/yellow]")
        return context

    try:
        result = plugin.run(context)
        context.results.append(result)
        filepath = save_context(context)
        console.print(f"[green]✓ {plugin_name} completed[/green]")
        console.print(f"   Results saved to: {filepath}")
    except Exception as e:
        console.print(f"[red]✗ {plugin_name} failed: {e}[/red]")

    return context


def print_pipeline_summary(context: PipelineContext) -> None:
    """Print a rich summary table of pipeline results."""
    if not context.results:
        console.print("[yellow]No results to summarize.[/yellow]")
        return

    table = Table(title="Pipeline Results Summary")
    table.add_column("Plugin", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Tests Found", justify="right")
    table.add_column("Summary", style="dim")

    for result in context.results:
        test_count = str(len(result.test_results))
        summary_keys = ", ".join(
            f"{k}: {v}" for k, v in list(result.summary.items())[:3]
        )
        table.add_row(
            result.tool_name, result.plugin_type, test_count, summary_keys
        )

    console.print(table)
