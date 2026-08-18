import asyncio
from unittest.mock import AsyncMock
from pathlib import Path
from architecture_model.pipeline.protocol import ArtifactReview


def test_run_llm_reviews_creates_reviews(tmp_path):
    """_run_llm_reviews produces ArtifactReview for each artifact."""
    from architecture_model.pipeline.emit import EmitStage

    se_dir = tmp_path / "docs" / "se"
    se_dir.mkdir(parents=True)
    (se_dir / "conops.md").write_text("# ConOps\n\nDetailed content about operations." * 5)
    (se_dir / "index.md").write_text("# Index")  # should be skipped

    callback = AsyncMock(
        return_value=(
            "SUMMARY: Good document with solid coverage.\n"
            "COMMENT: Missing actor definitions\n"
            "COMMENT: Strong capability coverage"
        )
    )

    stage = EmitStage()
    reviews = asyncio.run(stage._run_llm_reviews(tmp_path, callback))

    assert len(reviews) == 1
    rev = reviews[0]
    assert isinstance(rev, ArtifactReview)
    assert "conops" in rev.artifact_path
    assert rev.review_summary == "Good document with solid coverage."
    assert len(rev.comments) == 2
    assert "Missing actor definitions" in rev.comments
    assert rev.prompt_sent  # non-empty
    assert rev.response_received  # non-empty


def test_run_llm_reviews_skips_small_files(tmp_path):
    from architecture_model.pipeline.emit import EmitStage

    (tmp_path / "tiny.md").write_text("Hi")
    callback = AsyncMock()
    stage = EmitStage()
    reviews = asyncio.run(stage._run_llm_reviews(tmp_path, callback))
    assert len(reviews) == 0
    callback.assert_not_called()


def test_inline_reviews_appends_section(tmp_path):
    from architecture_model.pipeline.emit import _inline_reviews

    doc = tmp_path / "conops.md"
    doc.write_text("# ConOps\n\nSome content.\n")

    reviews = [
        ArtifactReview(
            artifact_path="conops.md",
            review_summary="Well-structured.",
            comments=["Missing actors", "Good scenarios"],
            prompt_sent="Review this artifact...",
            response_received="SUMMARY: Well-structured.\nCOMMENT: Missing actors\nCOMMENT: Good scenarios",
            timestamp="2026-08-18T10:00:00",
            duration_ms=500,
        )
    ]

    count = _inline_reviews(tmp_path, reviews)
    assert count == 1

    content = doc.read_text()
    assert "## LLM Review" in content
    assert "Well-structured." in content
    assert "Missing actors" in content
    assert "Good scenarios" in content
    assert "2026-08-18" in content
    assert "<details>" in content


def test_inline_reviews_idempotent(tmp_path):
    from architecture_model.pipeline.emit import _inline_reviews

    doc = tmp_path / "conops.md"
    doc.write_text("# ConOps\n\nContent.\n\n---\n\n## LLM Review\n\nOld review.\n")

    reviews = [
        ArtifactReview(
            artifact_path="conops.md",
            review_summary="New review.",
            comments=[],
            prompt_sent="p",
            response_received="r",
            timestamp="2026-08-18T11:00:00",
            duration_ms=100,
        )
    ]

    _inline_reviews(tmp_path, reviews)
    content = doc.read_text()
    assert content.count("## LLM Review") == 1
    assert "New review." in content
    assert "Old review" not in content


def test_inline_reviews_skips_non_md(tmp_path):
    from architecture_model.pipeline.emit import _inline_reviews

    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text("meta:\n  project: test\n")

    reviews = [
        ArtifactReview(
            artifact_path="model.yaml",
            review_summary="Good model.",
            comments=[],
            prompt_sent="p",
            response_received="r",
            timestamp="2026-08-18T10:00:00",
        )
    ]

    count = _inline_reviews(tmp_path, reviews)
    assert count == 0  # YAML files don't get inline reviews
