"""5G Log Analyzer plugin adapter.

Wraps the 5g-log-analyzer tool to work as a TTT plugin.
Re-implements the analysis logic to return structured data
instead of printing to stdout.
"""

import os
import re

from ttt.models import AnalysisResult, PipelineContext, TestResult
from ttt.plugin import TTTPlugin


# Regex rules from the original analyzer.py
RULES = {
    "ATTACH_REQUEST": re.compile(r"ATTACH_REQUEST|Attach Request"),
    "ATTACH_ACCEPT": re.compile(r"ATTACH_ACCEPT|Attach Accept"),
    "ATTACH_REJECT": re.compile(r"ATTACH_REJECT|Attach Reject"),
    "RRC_REJECT": re.compile(r"RRC_REJECT|RRC Reject|RRCConnectionReject"),
    "SETUP_FAILURE": re.compile(r"SETUP_FAILURE|Setup Failure"),
}


class LogAnalyzerPlugin(TTTPlugin):
    name = "log-analyzer"
    description = "gNodeB protocol-level analysis (attach/RRC/setup events)"
    plugin_type = "analyzer"

    def run(self, context: PipelineContext) -> AnalysisResult:
        total_stats = {
            "attach_attempts": 0,
            "attach_successes": 0,
            "attach_failures": 0,
            "rrc_failures": 0,
            "setup_failures": 0,
        }

        test_results = []

        for log_file in context.log_files:
            if not os.path.exists(log_file):
                continue

            with open(log_file, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    event_type = None

                    if RULES["ATTACH_REQUEST"].search(line):
                        total_stats["attach_attempts"] += 1
                        event_type = "ATTACH_REQUEST"
                    elif RULES["ATTACH_ACCEPT"].search(line):
                        total_stats["attach_successes"] += 1
                        event_type = "ATTACH_ACCEPT"
                    elif RULES["ATTACH_REJECT"].search(line):
                        total_stats["attach_failures"] += 1
                        event_type = "ATTACH_REJECT"
                    elif RULES["RRC_REJECT"].search(line):
                        total_stats["rrc_failures"] += 1
                        event_type = "RRC_REJECT"
                    elif RULES["SETUP_FAILURE"].search(line):
                        total_stats["setup_failures"] += 1
                        event_type = "SETUP_FAILURE"

                    if event_type:
                        is_failure = event_type in (
                            "ATTACH_REJECT", "RRC_REJECT", "SETUP_FAILURE"
                        )
                        test_results.append(
                            TestResult(
                                test_id=f"gnb_{event_type}_{i}",
                                status="fail" if is_failure else "pass",
                                source_tool="log-analyzer",
                                message=line.strip(),
                                metadata={
                                    "event_type": event_type,
                                    "file": log_file,
                                    "line": i,
                                },
                            )
                        )

        # Calculate attach success rate
        attach_rate = 0.0
        if total_stats["attach_attempts"] > 0:
            attach_rate = (
                total_stats["attach_successes"] / total_stats["attach_attempts"]
            ) * 100

        summary = {
            **total_stats,
            "attach_success_rate": round(attach_rate, 1),
            "total_events": len(test_results),
        }

        return AnalysisResult(
            tool_name="log-analyzer",
            plugin_type="analyzer",
            summary=summary,
            test_results=test_results,
        )

    def validate(self, context: PipelineContext) -> bool:
        return len(context.log_files) > 0
