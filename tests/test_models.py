import pytest

from ttt.models import AnalysisResult, PipelineContext, TestResult


def test_test_result_parsing():
    data = {
        "test_id": "test_001",
        "status": "pass",
        "duration": 1.5,
        "metadata": {"key": "value"},
    }
    result = TestResult.from_dict(data)
    assert result.test_id == "test_001"
    assert result.status == "pass"
    assert result.duration == 1.5
    assert result.metadata["key"] == "value"


def test_analysis_result_initialization():
    result = AnalysisResult(
        tool_name="test_tool", plugin_type="analyzer", summary={"events": 5}
    )
    assert result.tool_name == "test_tool"
    assert result.plugin_type == "analyzer"
    assert result.summary["events"] == 5


def test_pipeline_context_serialization():
    ctx = PipelineContext(
        log_files=["log1.txt", "log2.txt"], results=[], config={"env": "prod"}
    )
    data = ctx.to_dict()
    assert data["log_files"] == ["log1.txt", "log2.txt"]
    assert data["config"]["env"] == "prod"

    # Test deserialization
    ctx2 = PipelineContext.from_dict(data)
    assert ctx2.log_files == ctx.log_files
    assert ctx2.config == ctx.config
