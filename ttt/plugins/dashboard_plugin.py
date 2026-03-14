"""Test Monitor Dashboard plugin adapter.

Launches the Streamlit dashboard with an option to read from
the TTT data store instead of using mock data.
"""

import os

from ttt.models import AnalysisResult, PipelineContext
from ttt.plugin import TTTPlugin


class DashboardPlugin(TTTPlugin):
    name = "dashboard"
    description = "Real-time Streamlit dashboard for test monitoring"
    plugin_type = "dashboard"

    def run(self, context: PipelineContext) -> AnalysisResult:
        """Launch the Streamlit dashboard.

        Sets TTT_DATA_DIR environment variable so the dashboard
        can read from the shared data store.
        """
        dashboard_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "test-monitor-dashboard",
        )
        app_path = os.path.join(dashboard_dir, "app.py")

        if not os.path.exists(app_path):
            return AnalysisResult(
                tool_name="dashboard",
                plugin_type="dashboard",
                summary={"status": "error", "reason": f"Dashboard not found at {app_path}"},
            )

        # Set env var for data directory
        os.environ["TTT_DATA_DIR"] = os.path.abspath(context.output_dir)

        port = context.config.get("dashboard_port", 8501)

        # Launch streamlit
        try:
            os.system(f"streamlit run {app_path} --server.port {port}")
        except KeyboardInterrupt:
            pass

        return AnalysisResult(
            tool_name="dashboard",
            plugin_type="dashboard",
            summary={"status": "launched", "port": port},
        )

    def validate(self, context: PipelineContext) -> bool:
        dashboard_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "test-monitor-dashboard",
        )
        return os.path.exists(os.path.join(dashboard_dir, "app.py"))
