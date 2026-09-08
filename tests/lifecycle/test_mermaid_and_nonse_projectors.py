"""Mermaid + non-SE doc generators are registered under family<N>.<name> names.

Task 7 of Phase 1 substrate-and-liveness plan.
"""
from pathlib import Path

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import load_model
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"

MERMAID_PROJECTORS = [
    "family3.component_diagram",
    "family4.use_case_diagram",
    "family1.system_boundary_diagram",
]

NONSE_PROJECTORS = [
    "family3.component_spec",
    "family6.icd",
    "family3.dependency_matrix",
    "family8.health",
    "family8.drift",
    "family3.system_design",
    "family4.integration_flows",
    "family4.behavior_spec",
    "family8.index",
]

ALL_PROJECTORS = MERMAID_PROJECTORS + NONSE_PROJECTORS


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


def test_all_registered():
    names = set(DEFAULT_REGISTRY.list_names())
    missing = [n for n in ALL_PROJECTORS if n not in names]
    assert not missing, f"missing projectors: {missing}"


@pytest.mark.parametrize("projector_name", MERMAID_PROJECTORS)
def test_mermaid_projector_shape(projector_name, sample_model):
    fn, _ = DEFAULT_REGISTRY.get(projector_name)
    result = fn(sample_model, {})
    assert isinstance(result, DiagramSpec)
    assert result.facets.get("content_kind") == "mermaid"
    body = result.facets.get("body")
    assert isinstance(body, str) and len(body) > 0


@pytest.mark.parametrize("projector_name", NONSE_PROJECTORS)
def test_nonse_projector_shape(projector_name, sample_model):
    fn, _ = DEFAULT_REGISTRY.get(projector_name)
    result = fn(sample_model, {})
    assert isinstance(result, DiagramSpec)
    assert result.facets.get("content_kind") == "markdown"
    body = result.facets.get("body")
    assert isinstance(body, str) and len(body) > 0


@pytest.mark.parametrize("projector_name", ALL_PROJECTORS)
def test_projector_body_byte_identical(projector_name, sample_model):
    fn, _ = DEFAULT_REGISTRY.get(projector_name)
    a = fn(sample_model, {}).facets["body"]
    b = fn(sample_model, {}).facets["body"]
    assert a == b, f"{projector_name} body not byte-identical"
