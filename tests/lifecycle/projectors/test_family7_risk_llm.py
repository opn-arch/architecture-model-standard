"""Family7RiskLLM write-back projector — Phase 4-A Task 5.

Authors ``failure_modes`` + ``assumptions`` on Components, Behaviors, and
Interfaces from a deterministic risk-assessment base view. LLM output:

    {"authored": [
        {"entity_id": "COMP-1",
         "failure_modes": ["...", "..."],
         "assumptions": ["...", "..."]},
        ...
    ]}

Unknown ids and non-target kinds (e.g. Actors, Capabilities) are dropped.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.write_back_variants import (
    Family7RiskLLM,
)
from architecture_model.lifecycle.view_projection import ProjectorRegistry


class _MockProvider:
    name = "mock"

    def __init__(self, response):
        self._response = response

    def structured(self, prompt, schema, *, model=None):
        return dict(self._response)

    def complete(self, *_a, **_kw):  # pragma: no cover
        raise NotImplementedError

    def stream(self, *_a, **_kw):  # pragma: no cover
        raise NotImplementedError

    def tokenize(self, text):  # pragma: no cover
        return len(text)


def _base(fragment, config):
    del fragment, config
    return DiagramSpec(
        id="prose:family7.risk",
        title="family7.risk",
        facets={"content_kind": "markdown", "body": "# Risk Assessment"},
    )


@pytest.fixture
def registry():
    reg = ProjectorRegistry()
    reg.register("family7.risk", _base)
    return reg


@pytest.fixture
def fragment():
    return _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "wb7"},
            "entities": {
                "components": [{"id": "COMP-1", "name": "Core"}],
                "behaviors": [{"id": "BEH-1", "name": "Login"}],
                "interfaces": [{"id": "IF-1", "name": "AuthAPI"}],
                "capabilities": [{"id": "CAP-F1", "name": "Alpha"}],
                "actors": [{"id": "ACT-1", "name": "User"}],
            },
        }
    )


def test_family7_risk_llm_emits_failure_modes_and_assumptions(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {
                    "entity_id": "COMP-1",
                    "failure_modes": ["DB unreachable", "OOM"],
                    "assumptions": ["Single region"],
                },
                {
                    "entity_id": "BEH-1",
                    "failure_modes": ["Wrong password"],
                    "assumptions": ["Cookies enabled"],
                },
                {
                    "entity_id": "IF-1",
                    "failure_modes": ["Rate limited"],
                    "assumptions": ["HTTPS only"],
                },
            ]
        }
    )
    projector = Family7RiskLLM(
        provider=provider, task_class="risk.author", registry=registry
    )
    result = projector(fragment, {})
    payload = result.facets["proposal"]
    assert payload["kind"] == "model-patch"
    ops = payload["operations"]
    # 3 targets × 2 fields = 6 operations
    assert len(ops) == 6
    fm_ops = [o for o in ops if o["field"] == "failure_modes"]
    as_ops = [o for o in ops if o["field"] == "assumptions"]
    assert {o["target_id"] for o in fm_ops} == {"COMP-1", "BEH-1", "IF-1"}
    assert {o["target_id"] for o in as_ops} == {"COMP-1", "BEH-1", "IF-1"}
    comp_fm = next(o for o in fm_ops if o["target_id"] == "COMP-1")
    assert comp_fm["value"] == ["DB unreachable", "OOM"]


def test_family7_risk_llm_skips_non_target_kinds(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {
                    "entity_id": "COMP-1",
                    "failure_modes": ["ok"],
                    "assumptions": ["ok"],
                },
                # Capability and Actor exist but are NOT valid targets.
                {
                    "entity_id": "CAP-F1",
                    "failure_modes": ["no"],
                    "assumptions": ["no"],
                },
                {
                    "entity_id": "ACT-1",
                    "failure_modes": ["no"],
                    "assumptions": ["no"],
                },
                # Unknown id.
                {
                    "entity_id": "GHOST-9",
                    "failure_modes": ["no"],
                    "assumptions": ["no"],
                },
            ]
        }
    )
    projector = Family7RiskLLM(
        provider=provider, task_class="risk.author", registry=registry
    )
    result = projector(fragment, {})
    ops = result.facets["proposal"]["operations"]
    assert {o["target_id"] for o in ops} == {"COMP-1"}


def test_family7_risk_llm_schema_shape():
    provider = _MockProvider({"authored": []})
    projector = Family7RiskLLM(provider=provider, task_class="t")
    schema = projector.expected_proposal_schema()
    item = schema["properties"]["authored"]["items"]
    assert set(item["required"]) >= {"entity_id"}
    assert "failure_modes" in item["properties"]
    assert "assumptions" in item["properties"]


def test_family7_risk_llm_prompt_mentions_fields(fragment, registry):
    captured = {}

    class _Recorder(_MockProvider):
        def structured(self, prompt, schema, *, model=None):
            captured["prompt"] = prompt
            return {"authored": []}

    projector = Family7RiskLLM(
        provider=_Recorder({"authored": []}),
        task_class="risk.author",
        registry=registry,
    )
    projector(fragment, {})
    assert "failure_modes" in captured["prompt"]
    assert "assumptions" in captured["prompt"]
    assert "# Risk Assessment" in captured["prompt"]
