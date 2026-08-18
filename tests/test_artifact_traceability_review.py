"""Tests for artifact traceability with LLM review and enrichment data."""

import tempfile
from pathlib import Path

import yaml

from architecture_model.core.parser import load_model
from architecture_model.pipeline.protocol import ArtifactReview, EnrichmentRecord

_MINIMAL = {
    "meta": {"schema_version": "1.3", "project": "test"},
    "entities": {
        "capabilities": [{"id": "CAP-1", "name": "Test"}],
        "components": [{"id": "COMP-1", "name": "Core"}],
        "behaviors": [],
        "actors": [],
        "interfaces": [],
        "constraints": [],
        "requirements": [],
    },
    "relationships": [],
}


def _make_model():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        yaml.dump(_MINIMAL, f)
    return load_model(Path(f.name))


def test_traceability_with_reviews():
    from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability

    model = _make_model()
    reviews = [
        ArtifactReview(
            artifact_path="docs/se/conops.md",
            review_summary="Good coverage of ops scenarios.",
            comments=["Missing actors", "Strong capabilities"],
            prompt_sent="Review this...",
            response_received="SUMMARY: Good coverage...",
            timestamp="2026-08-18T10:00:00",
            duration_ms=500,
        )
    ]
    result = generate_artifact_traceability(model, None, reviews=reviews)
    assert "## LLM Review Status" in result
    assert "conops.md" in result
    assert "Good coverage" in result


def test_traceability_with_enrichments():
    from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability

    model = _make_model()
    enrichments = [
        EnrichmentRecord(
            entity_id="CAP-1",
            entity_type="capability",
            stage="infer",
            old_value="Utils",
            new_value="Config Manager",
            prompt="Name this...",
            response="Config Manager",
            timestamp="2026-08-18T10:00:00",
        )
    ]
    result = generate_artifact_traceability(model, None, enrichments=enrichments)
    assert "## LLM Enrichment Provenance" in result
    assert "CAP-1" in result
    assert "Utils" in result
    assert "Config Manager" in result


def test_traceability_with_review_details():
    from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability

    model = _make_model()
    reviews = [
        ArtifactReview(
            artifact_path="docs/se/conops.md",
            review_summary="Good.",
            comments=["Fix actors"],
            prompt_sent="Review prompt here",
            response_received="SUMMARY: Good.\nCOMMENT: Fix actors",
            timestamp="2026-08-18T10:00:00",
        )
    ]
    result = generate_artifact_traceability(model, None, reviews=reviews)
    assert "## Review Details" in result
    assert "Review prompt here" in result
    assert "<details>" in result


def test_traceability_without_reviews():
    from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability

    model = _make_model()
    result = generate_artifact_traceability(model, None)
    assert "No LLM reviews available" in result
    assert "No LLM enrichment records available" in result
