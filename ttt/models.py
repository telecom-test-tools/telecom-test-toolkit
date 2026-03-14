"""Shared data models used by all TTT plugins.

These dataclasses define the contracts between plugins:
- TestResult: A single test outcome
- AnalysisResult: Output from any analyzer/scorer plugin
- PipelineContext: Shared state threaded through the pipeline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TestResult:
    """Represents a single test execution result."""

    test_id: str
    status: str  # "pass" | "fail" | "skip" | "error"
    duration: Optional[float] = None
    timestamp: str = ""
    source_tool: str = ""
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "status": self.status,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "source_tool": self.source_tool,
            "message": self.message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TestResult":
        return cls(
            test_id=data.get("test_id", ""),
            status=data.get("status", ""),
            duration=data.get("duration"),
            timestamp=data.get("timestamp", ""),
            source_tool=data.get("source_tool", ""),
            message=data.get("message", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AnalysisResult:
    """Output from any plugin execution."""

    tool_name: str
    plugin_type: str  # "analyzer" | "scorer" | "reporter" | "dashboard"
    summary: Dict[str, Any] = field(default_factory=dict)
    test_results: List[TestResult] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    raw_output: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "plugin_type": self.plugin_type,
            "summary": self.summary,
            "test_results": [tr.to_dict() for tr in self.test_results],
            "output_files": self.output_files,
            "raw_output": self.raw_output,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        return cls(
            tool_name=data.get("tool_name", ""),
            plugin_type=data.get("plugin_type", ""),
            summary=data.get("summary", {}),
            test_results=[
                TestResult.from_dict(tr) for tr in data.get("test_results", [])
            ],
            output_files=data.get("output_files", []),
            raw_output=data.get("raw_output"),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class PipelineContext:
    """Shared state passed through the entire pipeline.

    Plugins read from and write to this context. Each plugin appends
    its AnalysisResult to `results`, making data available to downstream plugins.
    """

    log_files: List[str] = field(default_factory=list)
    results: List[AnalysisResult] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    output_dir: str = "./ttt_output"

    def get_all_test_results(self) -> List[TestResult]:
        """Aggregate all TestResults from all plugins that have run so far."""
        all_results = []
        for result in self.results:
            all_results.extend(result.test_results)
        return all_results

    def get_result_by_tool(self, tool_name: str) -> Optional[AnalysisResult]:
        """Get the AnalysisResult from a specific tool."""
        for result in self.results:
            if result.tool_name == tool_name:
                return result
        return None

    def to_dict(self) -> dict:
        return {
            "log_files": self.log_files,
            "results": [r.to_dict() for r in self.results],
            "config": self.config,
            "output_dir": self.output_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineContext":
        return cls(
            log_files=data.get("log_files", []),
            results=[
                AnalysisResult.from_dict(r) for r in data.get("results", [])
            ],
            config=data.get("config", {}),
            output_dir=data.get("output_dir", "./ttt_output"),
        )
