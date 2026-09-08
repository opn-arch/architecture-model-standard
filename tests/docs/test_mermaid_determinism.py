"""Byte-identical round-trip guard for Mermaid diagram generators.

Task 2 of Phase 1 substrate-and-liveness plan. `generate_all_diagrams()` fans
out to three per-model Mermaid generators; without a determinism guard, a
future dict-ordering or set-iteration regression could silently churn the
rendered artifacts on every rebuild. This test locks their output to
byte-identical repeat invocations against the committed sample model.
"""

from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.docs.diagrams import (
    generate_component_diagram,
    generate_system_boundary_diagram,
    generate_use_case_diagram,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


@pytest.mark.parametrize(
    "generator, required_substrings",
    [
        (generate_component_diagram, ("```mermaid", "graph TD", "COMP-1", "COMP-2")),
        (generate_use_case_diagram, ("```mermaid", "sequenceDiagram", "UC-1", "EndUser")),
        (generate_system_boundary_diagram, ("```mermaid", "graph TD", "COMP-1", "COMP-2")),
    ],
    ids=lambda v: v.__name__ if callable(v) else "-",
)
def test_mermaid_generator_byte_identical(generator, required_substrings, sample_model):
    a = generator(sample_model)
    b = generator(sample_model)
    # Byte-identity across two invocations on the same input.
    assert a == b, f"{generator.__name__} not byte-identical"
    assert isinstance(a, str)
    assert len(a) > 0
    # Positive-content guard: prevents a degenerate regression where a
    # generator silently short-circuits to a header-only string (e.g., an
    # empty-collection early return) — which would trivially satisfy `a == b`.
    for needle in required_substrings:
        assert needle in a, (
            f"{generator.__name__} output missing required substring "
            f"{needle!r}; got:\n{a}"
        )
