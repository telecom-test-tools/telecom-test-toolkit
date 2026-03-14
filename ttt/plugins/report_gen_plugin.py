"""Test Report Generator plugin adapter.

Wraps test-report-gen to work as a TTT plugin.
Can operate in two modes:
1. Direct mode: parse raw log files using the original parsers
2. Pipeline mode: generate reports from upstream AnalysisResult data
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional

from ttt.models import AnalysisResult, PipelineContext, TestResult
from ttt.plugin import TTTPlugin


class ReportGenPlugin(TTTPlugin):
    name = "report-generator"
    description = "Generate rich HTML test reports from analysis results"
    plugin_type = "reporter"

    def run(self, context: PipelineContext) -> AnalysisResult:
        output_dir = context.output_dir
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(
            output_dir,
            f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        )

        # Aggregate data from all upstream results
        combined_data = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        # Mode 1: Use upstream pipeline results
        if context.results:
            for result in context.results:
                for tr in result.test_results:
                    combined_data["total"] += 1
                    if tr.status == "pass":
                        combined_data["passed"] += 1
                    else:
                        combined_data["failed"] += 1

                    combined_data["details"].append({
                        "name": tr.test_id,
                        "status": "passed" if tr.status == "pass" else "failed",
                        "duration": str(tr.duration or "-"),
                        "message": tr.message,
                    })

        # Mode 2: Also parse raw log files using original parsers
        if context.log_files:
            report_gen_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "test-report-gen",
            )
            sys.path.insert(0, report_gen_dir)
            try:
                from src.parsers import get_parser

                for log_file in context.log_files:
                    if not os.path.exists(log_file):
                        continue

                    # Try to detect log type from filename
                    log_type = self._detect_log_type(log_file)
                    if not log_type:
                        continue

                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        parser = get_parser(log_type)
                        result = parser.parse(content)
                        self._merge_results(combined_data, result)
                    except (ValueError, Exception):
                        pass
            except ImportError:
                pass
            finally:
                if report_gen_dir in sys.path:
                    sys.path.remove(report_gen_dir)

        # Generate the HTML report
        html_content = self._generate_html(combined_data)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return AnalysisResult(
            tool_name="report-generator",
            plugin_type="reporter",
            summary={
                "total": combined_data["total"],
                "passed": combined_data["passed"],
                "failed": combined_data["failed"],
                "report_file": output_file,
            },
            output_files=[output_file],
        )

    def _detect_log_type(self, filepath: str) -> Optional[str]:
        """Guess the log type from filename."""
        name = os.path.basename(filepath).lower()
        if "pytest" in name:
            return "pytest"
        elif "network" in name:
            return "network"
        elif "automation" in name:
            return "automation"
        return None

    def _merge_results(self, main: dict, new: dict) -> None:
        main["total"] += new.get("total", 0)
        main["passed"] += new.get("passed", 0)
        main["failed"] += new.get("failed", 0)
        main["details"].extend(new.get("details", []))

    def _generate_html(self, data: dict) -> str:
        """Generate a standalone HTML report with Chart.js."""
        passed = data["passed"]
        failed = data["failed"]
        total = data["total"]
        pass_rate = (passed / total * 100) if total > 0 else 0

        details_rows = ""
        for d in data["details"]:
            status_class = "pass" if d["status"] == "passed" else "fail"
            status_icon = "✔" if d["status"] == "passed" else "✗"
            details_rows += f"""
            <tr class="{status_class}">
                <td>{d['name']}</td>
                <td><span class="badge {status_class}">{status_icon} {d['status']}</span></td>
                <td>{d['duration']}</td>
                <td>{d.get('message', '')}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TTT Test Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
        .header {{ text-align: center; margin-bottom: 2rem; }}
        .header h1 {{ font-size: 2rem; color: #38bdf8; }}
        .header p {{ color: #94a3b8; margin-top: 0.5rem; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
        .metric-card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; text-align: center; }}
        .metric-card h3 {{ font-size: 2rem; }}
        .metric-card p {{ color: #94a3b8; font-size: 0.9rem; margin-top: 0.5rem; }}
        .metric-card.passed h3 {{ color: #22c55e; }}
        .metric-card.failed h3 {{ color: #ef4444; }}
        .metric-card.rate h3 {{ color: #38bdf8; }}
        .chart-container {{ background: #1e293b; border-radius: 12px; padding: 2rem; margin-bottom: 2rem; max-width: 400px; margin-left: auto; margin-right: auto; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }}
        th {{ background: #334155; padding: 1rem; text-align: left; color: #94a3b8; text-transform: uppercase; font-size: 0.8rem; }}
        td {{ padding: 0.8rem 1rem; border-bottom: 1px solid #334155; }}
        .badge {{ padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }}
        .badge.pass {{ background: #052e16; color: #22c55e; }}
        .badge.fail {{ background: #450a0a; color: #ef4444; }}
        tr.fail {{ background: #1a0505; }}
        .footer {{ text-align: center; color: #475569; margin-top: 2rem; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Telecom Test Toolkit — Report</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="metrics">
        <div class="metric-card"><h3>{total}</h3><p>Total Tests</p></div>
        <div class="metric-card passed"><h3>{passed}</h3><p>Passed</p></div>
        <div class="metric-card failed"><h3>{failed}</h3><p>Failed</p></div>
        <div class="metric-card rate"><h3>{pass_rate:.1f}%</h3><p>Pass Rate</p></div>
    </div>
    <div class="chart-container">
        <canvas id="chart"></canvas>
    </div>
    <table>
        <thead><tr><th>Test</th><th>Status</th><th>Duration</th><th>Message</th></tr></thead>
        <tbody>{details_rows}</tbody>
    </table>
    <div class="footer">
        <p>Telecom Test Toolkit v0.1.0 | Plugin: report-generator</p>
    </div>
    <script>
        new Chart(document.getElementById('chart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed'],
                datasets: [{{ data: [{passed}, {failed}], backgroundColor: ['#22c55e', '#ef4444'], borderWidth: 0 }}]
            }},
            options: {{
                plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }},
                cutout: '60%'
            }}
        }});
    </script>
</body>
</html>"""

    def validate(self, context: PipelineContext) -> bool:
        # Can run if there are upstream results or log files
        return bool(context.results) or bool(context.log_files)
