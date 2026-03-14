"""Regression Flakiness Heatmap Scorer plugin adapter.

Inlines the heatmap scoring logic from the original
Regression-Flakiness-Heatmap-Scorer tool. Converts upstream
TestResult data into a pivot table, evaluates flakiness,
and generates an HTML heatmap report.
"""

from __future__ import annotations

import os
import warnings
from typing import List

from ttt.models import AnalysisResult, PipelineContext, TestResult
from ttt.plugin import TTTPlugin


# ---------------------------------------------------------------------------
# Inlined heatmap logic (from Regression-Flakiness-Heatmap-Scorer)
# ---------------------------------------------------------------------------

def _load_and_merge_data(input_file: str, history_file: str, window: int):
    """Load daily CSV, merge with historical data, enforce rolling window."""
    import pandas as pd

    try:
        daily_df = pd.read_csv(input_file)
    except Exception:
        return pd.DataFrame()

    required = {"TestCase_ID", "gNB_Build", "Status"}
    if not required.issubset(daily_df.columns):
        return pd.DataFrame()

    daily_pivot = daily_df.pivot(
        index="TestCase_ID", columns="gNB_Build", values="Status"
    )

    if os.path.exists(history_file):
        try:
            history_df = pd.read_csv(history_file, index_col="TestCase_ID")
        except Exception:
            history_df = pd.DataFrame()
    else:
        history_df = pd.DataFrame()

    if not history_df.empty:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            merged_df = history_df.combine_first(daily_pivot)
    else:
        merged_df = daily_pivot

    sorted_columns = sorted(merged_df.columns.astype(str))
    merged_df = merged_df[sorted_columns[-window:]]
    merged_df.to_csv(history_file)

    return merged_df


def _evaluate_flakiness(row) -> str:
    """Diagnose a single test row: Stable / High (Flaky) / etc."""
    runs = row.dropna()
    if runs.empty:
        return "No Data"

    statuses = runs.unique()

    if len(statuses) == 1:
        return "Stable" if statuses[0] == "Pass" else "Persistent Fail"

    transitions = (runs != runs.shift()).sum() - 1
    last_status = runs.iloc[-1]

    if transitions >= 2:
        return "High (Flaky)"
    elif transitions == 1:
        return "Recent Hard Fail" if last_status == "Fail" else "Fixed (Recent Pass)"

    return "Stable"


def _generate_heatmap_html(heatmap_df, output_file: str) -> None:
    """Render a styled HTML heatmap report with diagnosis column."""

    def color_cells(val):
        colors = {
            "Pass": "#c8e6c9",
            "Fail": "#ffcdd2",
            "High (Flaky)": "#fff9c4",
            "Recent Hard Fail": "#ff8a80",
            "Persistent Fail": "#ff8a80",
            "Stable": "#e2f0cb",
            "Fixed (Recent Pass)": "#c8e6c9",
        }
        c = colors.get(val, "")
        return (
            f"background-color: {c}; color: black; text-align: center; "
            f"border: 1px solid #ddd;"
            if c
            else ""
        )

    diagnosis_df = heatmap_df.copy()
    diagnosis_df["Diagnosis"] = diagnosis_df.apply(_evaluate_flakiness, axis=1)

    try:
        styled = diagnosis_df.style.map(color_cells)
    except AttributeError:
        styled = diagnosis_df.style.applymap(color_cells)

    html = f"""<html>
<head><style>
  body {{ font-family: Arial, sans-serif; padding: 20px; background: #0f172a; color: #e2e8f0; }}
  h2 {{ color: #38bdf8; }} table {{ border-collapse: collapse; width: 100%; }}
  th {{ background-color: #1e293b; padding: 10px; text-align: center; border: 1px solid #334155; color: #94a3b8; }}
  td {{ padding: 10px; font-weight: bold; }}
</style></head>
<body>
  <h2>gNB Regression — Flakiness Heatmap</h2>
  <p>Highlights real bugs vs simulator flakiness. Data merged with historical runs.</p>
  {styled.to_html()}
</body></html>"""

    with open(output_file, "w") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------

class FlakinessPlugin(TTTPlugin):
    name = "flakiness-scorer"
    description = "Detect flaky tests using failure heatmaps and historical patterns"
    plugin_type = "scorer"

    def run(self, context: PipelineContext) -> AnalysisResult:
        try:
            import pandas as pd
        except ImportError:
            return AnalysisResult(
                tool_name="flakiness-scorer",
                plugin_type="scorer",
                summary={"status": "error", "error": "pandas is required: pip install ttt[all]"},
            )

        upstream_results = context.get_all_test_results()
        output_dir = context.output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Resolve input CSV
        input_csv = context.config.get("flakiness_input_csv")

        if not input_csv and upstream_results:
            input_csv = self._generate_csv_from_results(upstream_results, output_dir)

        if not input_csv:
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

        # Run analysis
        history_file = os.path.join(output_dir, "historical_data.csv")
        output_html = os.path.join(output_dir, "regression_heatmap.html")
        window = context.config.get("flakiness_window", 14)

        try:
            merged = _load_and_merge_data(input_csv, history_file, window)

            if merged.empty:
                return AnalysisResult(
                    tool_name="flakiness-scorer",
                    plugin_type="scorer",
                    summary={"status": "no_data"},
                )

            _generate_heatmap_html(merged, output_html)

            # Diagnose each test
            diagnoses = {}
            for idx, row in merged.iterrows():
                diagnoses[str(idx)] = _evaluate_flakiness(row)

            diagnosis_counts = {}
            for diag in diagnoses.values():
                diagnosis_counts[diag] = diagnosis_counts.get(diag, 0) + 1

            test_results = []
            for test_id, diagnosis in diagnoses.items():
                is_flaky = diagnosis in (
                    "High (Flaky)", "Recent Hard Fail", "Persistent Fail"
                )
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
        """Convert upstream TestResult objects into a CSV for the heatmap."""
        import pandas as pd

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
        has_upstream = any(r.test_results for r in context.results)
        has_csv = any(f.endswith(".csv") for f in context.log_files)
        has_config_csv = "flakiness_input_csv" in context.config
        return has_upstream or has_csv or has_config_csv
