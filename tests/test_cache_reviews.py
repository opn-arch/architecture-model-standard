"""Tests for cache save/load of enrichment log and reviews."""

from pathlib import Path

from architecture_model.pipeline.cache import PipelineCache
from architecture_model.pipeline.protocol import ArtifactReview, EnrichmentRecord


def test_enrichment_log_round_trip(tmp_path: Path):
    cache = PipelineCache(tmp_path / "cache")
    records = [
        EnrichmentRecord(
            entity_id="CAP-1",
            entity_type="capability",
            stage="infer",
            old_value="Utils",
            new_value="Data Processing",
            prompt="p",
            response="r",
            timestamp="2026-01-01T00:00:00",
        ),
        EnrichmentRecord(
            entity_id="COMP-2",
            entity_type="component",
            stage="allocate",
            old_value="Svc",
            new_value="Auth Service",
            prompt="p2",
            response="r2",
            timestamp="2026-01-01T00:00:01",
            model="gpt-4",
            duration_ms=100,
        ),
    ]
    cache.save_enrichment_log(records)
    loaded = cache.load_enrichment_log()
    assert len(loaded) == 2
    assert loaded[0].entity_id == "CAP-1"
    assert loaded[1].model == "gpt-4"
    assert loaded[1].duration_ms == 100


def test_enrichment_log_empty(tmp_path: Path):
    cache = PipelineCache(tmp_path / "cache")
    assert cache.load_enrichment_log() == []


def test_reviews_round_trip(tmp_path: Path):
    cache = PipelineCache(tmp_path / "cache")
    reviews = [
        ArtifactReview(
            artifact_path="/out.yaml",
            review_summary="Good",
            comments=["a", "b"],
            prompt_sent="p",
            response_received="r",
            timestamp="t",
            model="claude",
            duration_ms=50,
            token_count=200,
        ),
    ]
    cache.save_reviews(reviews)
    loaded = cache.load_reviews()
    assert len(loaded) == 1
    assert loaded[0].comments == ["a", "b"]
    assert loaded[0].token_count == 200


def test_reviews_empty(tmp_path: Path):
    cache = PipelineCache(tmp_path / "cache")
    assert cache.load_reviews() == []
