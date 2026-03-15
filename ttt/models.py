"""Shared data models used by all TTT plugins.

These models define the contracts between plugins:
- TestResult: A single test outcome
- AnalysisResult: Output from any analyzer/scorer plugin
- PipelineContext: Shared state threaded through the pipeline
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TestResult(BaseModel):
    """Represents a single test execution result."""

    model_config = ConfigDict(extra="allow")

    test_id: str
    status: str  # "pass" | "fail" | "skip" | "error"
    duration: Optional[float] = None
    timestamp: str = ""
    source_tool: str = ""
    message: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "TestResult":
        return cls.model_validate(data)


class AnalysisResult(BaseModel):
    """Output from any plugin execution."""

    model_config = ConfigDict(extra="allow")

    tool_name: str
    plugin_type: str  # "analyzer" | "scorer" | "reporter" | "dashboard"
    summary: Dict[str, Any] = Field(default_factory=dict)
    test_results: List[TestResult] = Field(default_factory=list)
    output_files: List[str] = Field(default_factory=list)
    raw_output: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        return cls.model_validate(data)


class PipelineContext(BaseModel):
    """Shared state passed through the entire pipeline.

    Plugins read from and write to this context. Each plugin appends
    its AnalysisResult to `results`, making data available to downstream plugins.
    """

    model_config = ConfigDict(extra="allow")

    log_files: List[str] = Field(default_factory=list)
    results: List[AnalysisResult] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
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
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineContext":
        return cls.model_validate(data)
