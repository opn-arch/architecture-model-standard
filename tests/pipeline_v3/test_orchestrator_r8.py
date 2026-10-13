"""Orchestrator wiring for R8 requirements ingestion."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.pipeline_v3.orchestrator import run_pipeline


class _StubProvider:
    """Deterministic Layer-3 classifier."""

    name = "stub"

    def structured(self, prompt: str, schema: dict, *, model=None) -> dict:
        # High confidence — trigger a Layer 3 hit if prefilter passes.
        return {"entity_id": None, "confidence": 0.0}  # default: no match

    def complete(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError

    def stream(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError

    def tokenize(self, text):  # pragma: no cover
        return len(text.split())


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    """One-module repo + one doc file."""
    src = tmp_path / "src" / "tiny"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "mod.py").write_text(
        '"""Tiny module for R8 orchestrator tests."""\n'
        "\n"
        "def do_thing():\n"
        '    """Do the thing."""\n'
        "    return 1\n"
    )
    return tmp_path


def test_run_pipeline_ingest_requirements_off_matches_baseline(tiny_repo, tmp_path):
    """ingest_requirements=False must be byte-identical to no-flag run."""
    out_a = tmp_path / "a.yaml"
    out_b = tmp_path / "b.yaml"
    run_pipeline(tiny_repo, out_path=out_a, project_name="p")
    run_pipeline(
        tiny_repo, out_path=out_b, project_name="p", ingest_requirements=False
    )
    assert out_a.read_text() == out_b.read_text()


def test_run_pipeline_ingest_requirements_layer2_verified(tiny_repo, tmp_path):
    """Layer-2 exact heading match on a real cluster name emits verified promise."""
    # Discover which cluster/component names the pipeline will produce by
    # doing a dry run first.
    dry = tmp_path / "dry.yaml"
    run_pipeline(tiny_repo, out_path=dry, project_name="p")
    doc = yaml.safe_load(dry.read_text())
    components = doc["entities"]["components"]
    assert components, "pipeline produced no components"
    target_name = components[0]["name"]

    # Now author a docs file whose heading exactly matches that name.
    (tiny_repo / "docs" / "reports").mkdir(parents=True)
    (tiny_repo / "docs" / "reports" / "spec.md").write_text(
        f"## {target_name}\n\n- must do the thing\n- must exit cleanly\n"
    )

    out = tmp_path / "with_r8.yaml"
    run_pipeline(
        tiny_repo,
        out_path=out,
        project_name="p",
        ingest_requirements=True,
        doc_roots=("docs/reports",),
    )
    doc2 = yaml.safe_load(out.read_text())
    comp = next(
        c for c in doc2["entities"]["components"] if c["name"] == target_name
    )
    reqs = [p for p in comp["promises"] if p["attribute"] == "requirements"]
    assert len(reqs) == 2
    assert all(p["status"] == "verified" for p in reqs)


def test_run_pipeline_r7_and_r8_together_r8_wins_for_requirements(
    tiny_repo, tmp_path
):
    """R8 must overwrite R7's proposed requirements when both flags on."""
    dry = tmp_path / "dry.yaml"
    run_pipeline(tiny_repo, out_path=dry, project_name="p")
    doc = yaml.safe_load(dry.read_text())
    target_name = doc["entities"]["components"][0]["name"]

    (tiny_repo / "docs" / "reports").mkdir(parents=True)
    (tiny_repo / "docs" / "reports" / "spec.md").write_text(
        f"## {target_name}\n\n- doc-grounded requirement\n"
    )

    class _AttrProvider:
        name = "attr"

        def structured(self, prompt, schema, *, model=None):
            attr = next(iter(schema["properties"].keys()))
            return {attr: [f"R7 guess for {attr}"]}

        def complete(self, *a, **kw):  # pragma: no cover
            raise NotImplementedError

        def stream(self, *a, **kw):  # pragma: no cover
            raise NotImplementedError

        def tokenize(self, text):  # pragma: no cover
            return len(text.split())

    out = tmp_path / "combined.yaml"
    run_pipeline(
        tiny_repo,
        out_path=out,
        project_name="p",
        infer_attributes=True,
        attribute_provider=_AttrProvider(),
        ingest_requirements=True,
        doc_roots=("docs/reports",),
    )
    doc2 = yaml.safe_load(out.read_text())
    comp = next(
        c for c in doc2["entities"]["components"] if c["name"] == target_name
    )
    reqs = [p for p in comp["promises"] if p["attribute"] == "requirements"]
    # Only the doc-grounded requirement survives; R7 proposed guess wiped.
    contents = {p["content"] for p in reqs}
    assert contents == {"doc-grounded requirement"}
    assert reqs[0]["status"] == "verified"

    # Other Category-B attributes still carry R7 proposals.
    goals = [p for p in comp["promises"] if p["attribute"] == "goals"]
    assert any(p["status"] == "proposed" for p in goals)
