"""WP-5: Stage summaries — qualitative narrative on StageResult."""
from architecture_model.pipeline.protocol import StageResult, QualityMetrics


class TestStageSummary:
    def test_summary_field_exists(self):
        result = StageResult(
            output={},
            quality=QualityMetrics(score=85.0),
            summary="Discovered 14 capabilities across 6 functional blocks",
        )
        assert result.summary == "Discovered 14 capabilities across 6 functional blocks"

    def test_summary_defaults_empty(self):
        result = StageResult(output={}, quality=QualityMetrics(score=85.0))
        assert result.summary == ""
