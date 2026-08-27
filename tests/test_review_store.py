"""Tests for review persistence."""
from architecture_model.pipeline.review_store import save_reviews, load_reviews
from architecture_model.pipeline.protocol import StageQualityReview, QualityMetrics


class TestReviewStore:
    def test_save_and_load(self, tmp_path):
        review = StageQualityReview(
            stage="observe", quality=QualityMetrics(score=70),
            gate_results=[], llm_review="test review", suggestions=["suggestion 1"],
        )
        save_reviews(tmp_path, [review])
        loaded = load_reviews(tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["stage"] == "observe"
        assert loaded[0]["llm_review"] == "test review"

    def test_save_creates_directory(self, tmp_path):
        review_dir = tmp_path / "reviews"
        review = StageQualityReview(stage="observe", quality=QualityMetrics(score=70), gate_results=[])
        save_reviews(review_dir, [review])
        assert review_dir.exists()

    def test_load_empty(self, tmp_path):
        loaded = load_reviews(tmp_path)
        assert loaded == []
