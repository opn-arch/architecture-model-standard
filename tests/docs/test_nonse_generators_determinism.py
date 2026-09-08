"""Byte-identical output guard for the 9 non-SE doc generators.

Task 4 of Phase 1 substrate-and-liveness plan. The non-SE doc
generators (`architecture_model.docs.{component_spec, icd,
dependency_matrix, health, drift, system_design, integration_flows,
behavior_spec, index}`) each render Markdown from an architecture
model via heterogeneous signatures. Without a determinism guard, a
future dict-ordering or set-iteration regression in any single
generator could silently churn rendered artifacts on every rebuild.
This test locks each generator's output to byte-identical repeat
invocations against the committed sample model.
"""

import copy
from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.docs.behavior_spec import generate_behavior_spec
from architecture_model.docs.component_spec import generate_component_spec
from architecture_model.docs.dependency_matrix import generate_dependency_matrix
from architecture_model.docs.drift import generate_drift_report
from architecture_model.docs.health import generate_health_report
from architecture_model.docs.icd import generate_icd
from architecture_model.docs.index import generate_index
from architecture_model.docs.integration_flows import generate_integration_flows
from architecture_model.docs.system_design import generate_system_design
from architecture_model.manifest.call_graph import FlowTrace
from architecture_model.manifest.types import Manifest, MetricsResult

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


def _make_empty_manifest() -> Manifest:
    return Manifest(
        generated_at="1970-01-01T00:00:00Z",
        project_root=".",
        metrics=MetricsResult(),
        functional_blocks={},
        modules=[],
        interfaces=[],
    )


def _dispatch(name: str, model):
    if name == "generate_icd":
        return generate_icd(model)
    if name == "generate_dependency_matrix":
        return generate_dependency_matrix(model)
    if name == "generate_integration_flows":
        return generate_integration_flows(model)
    if name == "generate_system_design":
        return generate_system_design(model)
    if name == "generate_health_report":
        return generate_health_report(model)
    if name == "generate_component_spec":
        return generate_component_spec(model.entities.components[0], model)
    if name == "generate_drift_report":
        # Force a real diff (not the trivial has_changes=False shortcut)
        # by mutating a copy of the model on one side of the compare.
        mutated = copy.deepcopy(model)
        mutated.entities.components[0].name = "MainModuleV2"
        return generate_drift_report(model, mutated)
    if name == "generate_index":
        # Populate doc_paths so every content section gate opens,
        # exercising the real rendering paths.
        doc_paths = {
            "diagrams": [Path("context.mmd"), Path("components.mmd")],
            "components": [Path("COMP-1.md"), Path("COMP-2.md")],
            "behaviors": [Path("BEH-1.md")],
        }
        return generate_index(model, doc_paths)
    if name == "generate_behavior_spec":
        behavior = model.entities.behaviors[0]
        flow_trace = FlowTrace(
            entry="BEH-1", steps=[], components_crossed=[], depth=0, truncated=False,
        )
        return generate_behavior_spec(
            behavior, flow_trace, _make_empty_manifest(), {},
        )
    raise AssertionError(f"unknown generator: {name}")


GENERATORS = [
    "generate_icd",
    "generate_dependency_matrix",
    "generate_integration_flows",
    "generate_system_design",
    "generate_health_report",
    "generate_component_spec",
    "generate_drift_report",
    "generate_index",
    "generate_behavior_spec",
]


@pytest.mark.parametrize("name", GENERATORS, ids=GENERATORS)
def test_nonse_generator_byte_identical(name, sample_model):
    a = _dispatch(name, sample_model)
    b = _dispatch(name, sample_model)
    assert isinstance(a, str)
    assert len(a) > 0
    assert a == b, f"{name} not byte-identical"
