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
    "generator",
    [generate_component_diagram, generate_use_case_diagram, generate_system_boundary_diagram],
)
def test_mermaid_generator_byte_identical(generator, sample_model):
    a = generator(sample_model)
    b = generator(sample_model)
    assert a == b, f"{generator.__name__} not byte-identical"
    assert isinstance(a, str)
    assert len(a) > 0
