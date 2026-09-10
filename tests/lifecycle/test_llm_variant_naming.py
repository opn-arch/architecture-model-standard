"""Registry .llm-variant naming enforcement — Phase 4-A Task 7.

`.llm` projectors are write-back variants that require a deterministic
sibling (same prefix, no `.llm` suffix) to be registered first. This
prevents accidental promotion of LLM-only outputs into artifact pipelines
without a determinism guarantor.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.view_projection import (
    ProjectorRegistry,
    is_llm_projector,
)


def _stub(fragment, config):
    del fragment, config
    return DiagramSpec(
        id="prose:stub", title="stub", facets={"content_kind": "markdown", "body": ""}
    )


def test_is_llm_projector_predicate():
    assert is_llm_projector("family1.mission.llm") is True
    assert is_llm_projector("family1.mission") is False
    assert is_llm_projector("") is False


def test_llm_variant_requires_deterministic_sibling():
    reg = ProjectorRegistry()
    with pytest.raises(ValueError, match="requires deterministic sibling"):
        reg.register("family1.mission.llm", _stub)


def test_llm_variant_registers_when_sibling_present():
    reg = ProjectorRegistry()
    reg.register("family1.mission", _stub)
    reg.register("family1.mission.llm", _stub)  # no raise
    assert "family1.mission.llm" in reg


def test_list_names_filters_by_family_and_variant():
    reg = ProjectorRegistry()
    reg.register("family1.mission", _stub)
    reg.register("family1.mission.llm", _stub)
    reg.register("family3.component_spec", _stub)
    assert reg.list_names(family=1, llm=False) == ["family1.mission"]
    assert reg.list_names(family=1, llm=True) == ["family1.mission.llm"]
    assert reg.list_names(family=1) == ["family1.mission", "family1.mission.llm"]
    assert reg.list_names(family=3, llm=False) == ["family3.component_spec"]
    assert reg.list_names(family=3, llm=True) == []


def test_list_names_without_filters_unchanged():
    reg = ProjectorRegistry()
    reg.register("family1.mission", _stub)
    reg.register("family3.component_spec", _stub)
    assert reg.list_names() == ["family1.mission", "family3.component_spec"]
