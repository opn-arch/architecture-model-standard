"""17 SE doc generators are registered under family<N>.<name> names.

Task 6 of Phase 1 substrate-and-liveness plan. Verifies:
- All 17 expected names appear in DEFAULT_REGISTRY.list_names().
- Each projector, when invoked on the sample model, returns a
  DiagramSpec with facets["content_kind"] == "markdown" and a non-empty
  facets["body"].
- Two invocations against the same model return byte-identical body
  (round-trip determinism carried through the wrapper).
"""
from pathlib import Path

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import load_model
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"

EXPECTED_SE_PROJECTORS = [
    "family1.conops",
    "family2.functional_analysis",
    "family3.logical_architecture",
    "family4.operations_manual",
    "family4.maintenance_manual",
    "family4.use_cases",
    "family5.deployment_guide",
    "family6.interface_spec",
    "family6.api_reference",
    "family6.cli_reference",
    "family6.plugin_guide",
    "family6.data_model",
    "family7.requirements_analysis",
    "family7.verification_validation",
    "family7.risk_assessment",
    "family7.security_analysis",
    "family7.artifact_traceability",
]


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


def test_all_se_doc_projectors_registered():
    names = set(DEFAULT_REGISTRY.list_names())
    missing = [n for n in EXPECTED_SE_PROJECTORS if n not in names]
    assert not missing, f"missing SE doc projectors: {missing}"


@pytest.mark.parametrize("projector_name", EXPECTED_SE_PROJECTORS)
def test_se_doc_projector_renders_markdown(projector_name, sample_model):
    fn, _version = DEFAULT_REGISTRY.get(projector_name)
    result = fn(sample_model, {})
    assert isinstance(result, DiagramSpec)
    assert result.facets.get("content_kind") == "markdown"
    body = result.facets.get("body")
    assert isinstance(body, str) and len(body) > 0


@pytest.mark.parametrize("projector_name", EXPECTED_SE_PROJECTORS)
def test_se_doc_projector_body_byte_identical(projector_name, sample_model):
    fn, _version = DEFAULT_REGISTRY.get(projector_name)
    a = fn(sample_model, {}).facets["body"]
    b = fn(sample_model, {}).facets["body"]
    assert a == b, f"{projector_name} body not byte-identical"
