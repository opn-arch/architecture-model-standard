"""Registry supports insertion-order listing and duplicate-guard.

Task 5 of Phase 1 substrate-and-liveness plan. Extends ProjectorRegistry
with list_names() (insertion order) and a duplicate-registration guard,
supporting the .llm variant naming convention (family.name + family.name.llm
side-by-side).
"""
import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.view_projection import ProjectorRegistry


def _det(fragment, config):
    return DiagramSpec(nodes=(), edges=(), groups=(), metadata={"kind": "det"})


def _llm(fragment, config):
    return DiagramSpec(nodes=(), edges=(), groups=(), metadata={"kind": "llm"})


def test_llm_variant_registers_and_resolves():
    reg = ProjectorRegistry()
    reg.register("family2.functional", _det)
    reg.register("family2.functional.llm", _llm)

    det_fn, _ = reg.get("family2.functional")
    llm_fn, _ = reg.get("family2.functional.llm")
    assert det_fn.__name__ == "_det"
    assert llm_fn.__name__ == "_llm"


def test_registry_list_names_is_insertion_order():
    reg = ProjectorRegistry()
    reg.register("family1.mission", _det)
    reg.register("family1.mission.llm", _llm)
    reg.register("family2.functional", _det)
    assert reg.list_names() == [
        "family1.mission",
        "family1.mission.llm",
        "family2.functional",
    ]


def test_registry_duplicate_register_raises():
    reg = ProjectorRegistry()
    reg.register("x", _det)
    with pytest.raises(ValueError, match="already registered"):
        reg.register("x", _det)


def test_default_registry_list_names_contains_seeded_projectors():
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY
    names = DEFAULT_REGISTRY.list_names()
    for expected in ("se.conops", "se.functional", "se.logical", "se.use_cases"):
        assert expected in names
