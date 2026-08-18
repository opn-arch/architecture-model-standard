"""Tests for EnrichmentRecord and ArtifactReview dataclasses."""

from architecture_model.pipeline.protocol import EnrichmentRecord, ArtifactReview


def test_enrichment_record_construction():
    r = EnrichmentRecord(
        entity_id="CAP-1",
        entity_type="capability",
        stage="infer",
        old_value="Utils",
        new_value="Data Processing",
        prompt="suggest name",
        response="Data Processing",
        timestamp="2026-01-01T00:00:00",
    )
    assert r.entity_id == "CAP-1"
    assert r.model == ""
    assert r.duration_ms == 0
    assert r.context == {}


def test_enrichment_record_with_optionals():
    r = EnrichmentRecord(
        entity_id="CAP-2",
        entity_type="capability",
        stage="infer",
        old_value="X",
        new_value="Y",
        prompt="p",
        response="r",
        timestamp="t",
        model="gpt-4",
        duration_ms=123,
        context={"key": "val"},
    )
    assert r.model == "gpt-4"
    assert r.duration_ms == 123
    assert r.context == {"key": "val"}


def test_artifact_review_construction():
    r = ArtifactReview(
        artifact_path="/tmp/out.yaml",
        review_summary="Looks good",
        comments=["minor issue"],
        prompt_sent="review this",
        response_received="ok",
        timestamp="2026-01-01T00:00:00",
    )
    assert r.artifact_path == "/tmp/out.yaml"
    assert r.comments == ["minor issue"]
    assert r.model == ""
    assert r.token_count == 0


def test_artifact_review_with_optionals():
    r = ArtifactReview(
        artifact_path="f",
        review_summary="s",
        comments=[],
        prompt_sent="p",
        response_received="r",
        timestamp="t",
        model="claude",
        duration_ms=50,
        token_count=100,
    )
    assert r.model == "claude"
    assert r.duration_ms == 50
    assert r.token_count == 100
