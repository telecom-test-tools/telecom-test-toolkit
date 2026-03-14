"""5G TestScope plugin adapter.

Wraps the 5gtestscope tool to work as a TTT plugin.
Uses the modular parser, analyzer, and KPI calculator
from the original project.
"""

import os
import sys

from ttt.models import AnalysisResult, PipelineContext, TestResult
from ttt.plugin import TTTPlugin


class TestScopePlugin(TTTPlugin):
    name = "testscope"
    description = "Advanced 5G log analysis with KPIs and failure detection"
    plugin_type = "analyzer"

    def run(self, context: PipelineContext) -> AnalysisResult:
        # Inline 5gtestscope's parsing logic to avoid import conflicts
        # with Python's built-in 'parser' module

        def parse_log(file_path):
            events = []
            with open(file_path, "r") as f:
                for line in f:
                    if "RRC Setup" in line:
                        events.append("RRC_SETUP")
                    elif "Registration Accept" in line:
                        events.append("REGISTRATION_SUCCESS")
                    elif "PDU Session" in line:
                        events.append("PDU_SESSION")
                    elif "FAIL" in line or "ERROR" in line:
                        events.append("FAILURE")
            return events

        def detect_failures(events):
            return ["Generic Failure Detected" for e in events if e == "FAILURE"]

        all_test_results = []
        total_events = 0
        total_failures = 0
        all_issues = []

        for log_file in context.log_files:
            if not os.path.exists(log_file):
                continue

            events = parse_log(log_file)
            failures = detect_failures(events)
            total_events += len(events)
            total_failures += len(failures)
            all_issues.extend(failures)

            # Convert events to TestResult objects
            for i, event in enumerate(events):
                is_failure = event == "FAILURE"
                all_test_results.append(
                    TestResult(
                        test_id=f"5g_{event}_{i}",
                        status="fail" if is_failure else "pass",
                        source_tool="testscope",
                        message=event,
                        metadata={
                            "event_type": event,
                            "file": log_file,
                        },
                    )
                )

        # Calculate KPIs
        success_rate = 0.0
        if total_events > 0:
            success_rate = ((total_events - total_failures) / total_events) * 100

        return AnalysisResult(
            tool_name="testscope",
            plugin_type="analyzer",
            summary={
                "total_events": total_events,
                "failures": total_failures,
                "success_rate": round(success_rate, 2),
                "detected_issues": all_issues,
            },
            test_results=all_test_results,
        )

    def validate(self, context: PipelineContext) -> bool:
        return len(context.log_files) > 0
