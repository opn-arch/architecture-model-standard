"""End-to-end walk runner tests."""

from __future__ import annotations

from architecture_model.walks import run_walk
from architecture_model.walks.spec.loader import parse_walk_spec


def _model() -> dict:
    return {
        "entities": {
            "capabilities": [
                {
                    "id": "CAP-A",
                    "name": "Cap A",
                    "intent": "do A",
                    "goals": ["achieve X"],
                    "promises": ["will do X"],
                },
                {
                    "id": "CAP-B",
                    "name": "Cap B",
                    "intent": "",
                    "goals": [],
                    "promises": [],
                },
                {
                    "id": "CAP-C",
                    "name": "Cap C",
                    "intent": "compose",
                    "goals": ["a", "b", "c", "d", "e"],
                    "promises": ["will compose"],
                },
            ],
            "components": [
                {"id": "COMP-1", "name": "Comp 1", "intent": "impl A"},
            ],
        },
        "relationships": [
            {"from": "COMP-1", "to": "CAP-A", "type": "realizes"},
            {"from": "CAP-C", "to": "CAP-A", "type": "contains"},
            {"from": "CAP-C", "to": "CAP-B", "type": "contains"},
        ],
    }


def _spec() -> str:
    return """
walk:
  id: WALK-readiness
  audits: [CAP-WK.readiness]
  scope:
    kind: capability
  traverse:
    edges: [contains, realizes]
    direction: outbound
    depth: 1
  classify:
    verdicts:
      - name: contradictory
        when: has:intent and count:goals > 4
      - name: ready-to-code
        when: has:intent and has:goals and has:promises
      - name: needs-enrichment
        when: missing:intent or missing:goals
    on_missing_attributes: needs-enrichment
  evidence:
    tier: structural
    sources: [model]
  emit:
    card_template: default
    severity_from: verdict
""".strip()


def test_run_walk_produces_cards_for_each_entity() -> None:
    import yaml as _yaml

    spec = parse_walk_spec(_yaml.safe_load(_spec()))
    result = run_walk(spec, _model())
    assert result["walk_id"] == "WALK-readiness"
    assert len(result["cards"]) == 3
    verdicts = {c["entity_id"]: c["verdict"] for c in result["cards"]}
    assert verdicts["CAP-A"] == "ready-to-code"
    assert verdicts["CAP-B"] == "needs-enrichment"
    assert verdicts["CAP-C"] == "contradictory"


def test_run_walk_cards_sorted_by_severity_desc_then_id() -> None:
    import yaml as _yaml

    spec = parse_walk_spec(_yaml.safe_load(_spec()))
    result = run_walk(spec, _model())
    severities = [c["severity"] for c in result["cards"]]
    assert severities == sorted(severities, reverse=True)


def test_run_walk_deterministic() -> None:
    import yaml as _yaml

    spec = parse_walk_spec(_yaml.safe_load(_spec()))
    r1 = run_walk(spec, _model())
    r2 = run_walk(spec, _model())
    assert r1 == r2


def test_run_walk_evidence_tier_stamped() -> None:
    import yaml as _yaml

    spec = parse_walk_spec(_yaml.safe_load(_spec()))
    result = run_walk(spec, _model())
    for c in result["cards"]:
        assert c["evidence_tier"] == "structural"


def test_run_walk_rollup_any_child_ok() -> None:
    import yaml as _yaml

    spec_yaml = """
walk:
  id: WALK-rollup
  scope:
    kind: capability
  traverse:
    edges: [contains]
    direction: outbound
    depth: 1
  classify:
    verdicts:
      - name: ready-to-code
        when: has:promises
      - name: needs-enrichment
        when: missing:promises
    on_missing_attributes: needs-enrichment
  rollup:
    via: contains
    category: C
    strategy: any-child-ok
"""
    spec = parse_walk_spec(_yaml.safe_load(spec_yaml.strip()))
    model = _model()
    result = run_walk(spec, model)
    verdicts = {c["entity_id"]: c["verdict"] for c in result["cards"]}
    # CAP-C contains CAP-A (ready) and CAP-B (needs-enrichment).
    # any-child-ok: CAP-A ready → CAP-C ready.
    assert verdicts["CAP-C"] == "ready-to-code"


def test_run_walk_from_walk_composition() -> None:
    """A second walk consumes the first walk's cards via from_walk."""
    import yaml as _yaml

    first = parse_walk_spec(_yaml.safe_load(_spec()))
    r1 = run_walk(first, _model())
    prior = r1["cards"]

    second_yaml = """
walk:
  id: WALK-followup
  scope:
    kind: capability
    from_walk: WALK-readiness
  classify:
    verdicts:
      - name: ready-to-code
        when: has:intent
    on_missing_attributes: needs-enrichment
"""
    second = parse_walk_spec(_yaml.safe_load(second_yaml.strip()))
    r2 = run_walk(second, _model(), prior_walk_output=prior)
    # Should have the same set of entities the first walk emitted.
    assert {c["entity_id"] for c in r2["cards"]} == {"CAP-A", "CAP-B", "CAP-C"}
