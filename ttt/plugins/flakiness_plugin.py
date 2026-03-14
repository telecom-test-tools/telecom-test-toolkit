"""Regression Flakiness Heatmap Scorer plugin adapter.

Wraps the flakiness scorer to work as a TTT plugin.
Converts upstream TestResult data into CSV format for the heatmap
generator, or uses a provided CSV directly.
"""

from __future__ import annotations

import os
import sys
import tempfile
from typing import List

from ttt.models import AnalysisResult, PipelineContext, TestResult
from ttt.plugin import TTTPlugin


class FlakinessPlugin(TTTPlugin):
    name = "flakiness-scorer"
    description = "Detect flaky tests using failure heatmaps and historical patterns"
    plugin_type = "scorer"

    def run(self, context: PipelineContext) -> AnalysisResult:
        # Add the scorer to the Python path
        scorer_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "Regression-Flakiness-Heatmap-Scorer",
        )

        sys.path.insert(0, scorer_dir)
        try:
            from generate_heatmap import (
                load_and_merge_data,
                generate_report,
                evaluate_flakiness,
            )
        finally:
            if scorer_dir in sys.path:
                sys.path.remove(scorer_dir)

        # Check if upstream results have test data we can convert to CSV
        upstream_results = context.get_all_test_results()
        output_dir = context.output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Generate a CSV from upstream data if available
        input_csv = context.config.get("flakiness_input_csv")

        if not input_csv and upstream_results:
            input_csv = self._generate_csv_from_results(
                upstream_results, output_dir
            )

        if not input_csv:
            # Check if any log files are CSVs
            for f in context.log_files:
                if f.endswith(".csv"):
                    input_csv = f
                    break

        if not input_csv:
            return AnalysisResult(
                tool_name="flakiness-scorer",
                plugin_type="scorer",
                summary={"status": "skipped", "reason": "No CSV data available"},
            )

        # Run the heatmap generator
        history_file = os.path.join(output_dir, "historical_data.csv")
        output_html = os.path.join(output_dir, "regression_heatmap.html")
        window = context.config.get("flakiness_window", 14)

        try:
            merged = load_and_merge_data(input_csv, history_file, window)

            if merged.empty:
                return AnalysisResult(
                    tool_name="flakiness-scorer",
                    plugin_type="scorer",
                    summary={"status": "no_data"},
                )

            generate_report(merged, output_html)

            # Calculate flakiness diagnoses
            diagnoses = {}
            for idx, row in merged.iterrows():
                diagnoses[str(idx)] = evaluate_flakiness(row)

            # Count diagnosis categories
            diagnosis_counts = {}
            for diag in diagnoses.values():
                diagnosis_counts[diag] = diagnosis_counts.get(diag, 0) + 1

            test_results = []
            for test_id, diagnosis in diagnoses.items():
                is_flaky = diagnosis in ("High (Flaky)", "Recent Hard Fail", "Persistent Fail")
                test_results.append(
                    TestResult(
                        test_id=test_id,
                        status="fail" if is_flaky else "pass",
                        source_tool="flakiness-scorer",
                        message=diagnosis,
                        metadata={"diagnosis": diagnosis},
                    )
                )

            return AnalysisResult(
                tool_name="flakiness-scorer",
                plugin_type="scorer",
                summary={
                    "total_tests_analyzed": len(diagnoses),
                    "diagnosis_counts": diagnosis_counts,
                    "heatmap_file": output_html,
                },
                test_results=test_results,
                output_files=[output_html],
            )

        except Exception as e:
            return AnalysisResult(
                tool_name="flakiness-scorer",
                plugin_type="scorer",
                summary={"status": "error", "error": str(e)},
            )

    def _generate_csv_from_results(
        self, results: List[TestResult], output_dir: str
    ) -> str:
        """Convert upstream TestResult objects into a CSV for the heatmap.

        The heatmap expects: TestCase_ID, gNB_Build, Status
        """
        try:
            import pandas as pd
        except ImportError:
            return ""

        rows = []
        build_label = "Build_latest"

        for tr in results:
            rows.append({
                "TestCase_ID": tr.test_id,
                "gNB_Build": build_label,
                "Status": "Pass" if tr.status == "pass" else "Fail",
            })

        if not rows:
            return ""

        df = pd.DataFrame(rows)
        csv_path = os.path.join(output_dir, "latest_run.csv")
        df.to_csv(csv_path, index=False)
        return csv_path

    def validate(self, context: PipelineContext) -> bool:
        # Can run if there's upstream data or CSV files
        has_upstream = any(r.test_results for r in context.results)
        has_csv = any(f.endswith(".csv") for f in context.log_files)
        has_config_csv = "flakiness_input_csv" in context.config
        return has_upstream or has_csv or has_config_csv
