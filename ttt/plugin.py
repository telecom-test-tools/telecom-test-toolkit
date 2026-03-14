"""Plugin base class and discovery mechanism.

Plugins register themselves via the 'ttt.plugins' entry point group
in their pyproject.toml or setup.py. The discover_plugins() function
finds and loads all registered plugins at runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from importlib.metadata import entry_points
from typing import Any, Dict, Optional

from ttt.models import AnalysisResult, PipelineContext


class TTTPlugin(ABC):
    """Abstract base class that all TTT plugins must implement.

    Attributes:
        name: Human-readable plugin name
        description: Short description of what the plugin does
        plugin_type: Category — "analyzer", "scorer", "reporter", or "dashboard"
    """

    name: str = "unnamed"
    description: str = ""
    plugin_type: str = "analyzer"  # analyzer | scorer | reporter | dashboard

    @abstractmethod
    def run(self, context: PipelineContext) -> AnalysisResult:
        """Execute the plugin with the given pipeline context.

        Args:
            context: Shared pipeline state with log files and upstream results.

        Returns:
            AnalysisResult containing this plugin's output.
        """
        ...

    def get_cli_options(self) -> Dict[str, Any]:
        """Return extra CLI options this plugin accepts.

        Override this to add plugin-specific CLI arguments.

        Returns:
            Dict of option_name -> {type, default, help}
        """
        return {}

    def validate(self, context: PipelineContext) -> bool:
        """Check if this plugin can run given the current context.

        Override to add custom validation (e.g., check that required
        log files exist or upstream results are present).
        """
        return True

    def __repr__(self) -> str:
        return f"<TTTPlugin: {self.name} ({self.plugin_type})>"


def discover_plugins() -> Dict[str, TTTPlugin]:
    """Auto-discover all installed TTT plugins via entry points.

    Scans the 'ttt.plugins' entry point group and instantiates each
    registered plugin class.

    Returns:
        Dict mapping plugin name -> plugin instance
    """
    plugins = {}

    # Python 3.12+ and 3.9+ compatible entry point discovery
    try:
        eps = entry_points(group="ttt.plugins")
    except TypeError:
        # Python 3.9 fallback
        all_eps = entry_points()
        eps = all_eps.get("ttt.plugins", [])

    for ep in eps:
        try:
            plugin_class = ep.load()
            plugin_instance = plugin_class()
            plugins[ep.name] = plugin_instance
        except Exception as e:
            # Don't crash if a plugin fails to load
            print(f"⚠️  Warning: Failed to load plugin '{ep.name}': {e}")

    return plugins


def get_plugin(name: str) -> Optional[TTTPlugin]:
    """Get a specific plugin by name.

    Args:
        name: The registered plugin name (e.g. 'testwatch')

    Returns:
        Plugin instance or None if not found.
    """
    plugins = discover_plugins()
    return plugins.get(name)
