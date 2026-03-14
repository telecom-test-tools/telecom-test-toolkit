"""TestWatch plugin adapter.

Wraps the testwatch log monitoring tool to work as a TTT plugin.
Calls watch_log() with JSON output mode and converts results
to the shared TestResult model.
"""

import os

from ttt.models import AnalysisResult, PipelineContext, TestResult
from ttt.plugin import TTTPlugin


class TestWatchPlugin(TTTPlugin):
    name = "testwatch"
    description = "Quick pass/fail log scanner with pattern matching"
    plugin_type = "analyzer"

    def run(self, context: PipelineContext) -> AnalysisResult:
        # Inline testwatch's pattern matching logic to avoid import conflicts
        # with Python's built-in 'parser' module
        import re
        fail_patterns = ["FAIL", "FAILED", "ERROR", "CRASH", "TIMEOUT"]

        def parse_line(line, patterns):
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return "FAIL"
            return "PASS"

        all_test_results = []
        total_passed = 0
        total_failed = 0

        for log_file in context.log_files:
            if not os.path.exists(log_file):
                continue

            with open(log_file, "r") as f:
                for i, line in enumerate(f, 1):
                    stripped = line.strip()
                    if not stripped:
                        continue

                    result = parse_line(stripped, fail_patterns)
                    status = "fail" if result == "FAIL" else "pass"

                    if status == "pass":
                        total_passed += 1
                    else:
                        total_failed += 1

                    all_test_results.append(
                        TestResult(
                            test_id=f"{os.path.basename(log_file)}:line_{i}",
                            status=status,
                            source_tool="testwatch",
                            message=stripped,
                            metadata={"file": log_file, "line_number": i},
                        )
                    )

        return AnalysisResult(
            tool_name="testwatch",
            plugin_type="analyzer",
            summary={
                "passed": total_passed,
                "failed": total_failed,
                "total": total_passed + total_failed,
                "files_scanned": len(context.log_files),
            },
            test_results=all_test_results,
        )

    def validate(self, context: PipelineContext) -> bool:
        return len(context.log_files) > 0
