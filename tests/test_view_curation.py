from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import (
    EvidenceRecord,
    Selector,
    load_viewer_curation,
    merge_ordered,
    validate_view_curation,
)
from architecture_model.core.diagram_spec import Diagnostic


def _context(tmp_path: Path) -> ArchitectureViewContext:
    model_path = tmp_path / ".architecture-model.yaml"
    model_path.write_text("""meta:
  project: curation
  schema_version: '2.0'
entities:
  components:
    - id: COMP-1
      name: Shared
      status: ACTIVE
      tags: [core]
      files: [src/a.py]
    - id: COMP-2
      name: Shared
      status: ACTIVE
relationships: []
""", encoding="utf-8")
    return ArchitectureViewContext.load(load_model(model_path), tmp_path)


def test_missing_and_invalid_curation_fall_back_without_crashing(tmp_path):
    context = _context(tmp_path)
    missing = load_viewer_curation(tmp_path, context)
    assert missing.version == 1 and missing.views.conops.featured == [] and missing.warnings == []

    path = tmp_path / "bad.yaml"
    path.write_text("version: 2\nviews: nope", encoding="utf-8")
    invalid = load_viewer_curation(tmp_path, context, path)
    assert invalid.views.logical.featured == []
    assert invalid.diagnostics


def test_loader_resolves_selectors_and_rejects_ambiguity(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / ".architecture/viewer-curation.yaml"
    path.parent.mkdir()
    path.write_text("""version: 1
views:
  conops:
    featured:
      - qualified_id: root::COMP-1
      - name: Shared
        system: root
      - source_file: src/a.py
    labels:
      root::COMP-1: Primary
""", encoding="utf-8")

    curation = load_viewer_curation(tmp_path, context)

    assert curation.views.conops.featured == []
    assert any("ambiguous" in warning.message.lower() for warning in curation.diagnostics)
    assert any("Duplicate selector" in warning.message for warning in curation.diagnostics)
    assert curation.views.conops.labels == {}


def test_external_and_flow_evidence_must_be_safe_and_present(tmp_path):
    context = _context(tmp_path)
    evidence = tmp_path / "docs/evidence.md"
    evidence.parent.mkdir()
    evidence.write_text("evidence", encoding="utf-8")
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  logical:
    externals:
      - id: EXT-GOOD
        name: Provider
        inferred: true
        evidence:
          - source: docs/evidence.md
            claim: Provider is used by the logical architecture
      - id: EXT-BAD
        name: Bad
        inferred: true
        evidence: [../outside.md]
    groups:
      - id: clients
        label: Clients
    flows:
      - source: clients
        target: EXT-GOOD
        inferred: true
        evidence:
          - source: docs/evidence.md
            claim: Clients exchange requests with Provider
        kind: exchange
      - source: root::COMP-1
        target: EXT-GOOD
        kind: realizes
""", encoding="utf-8")

    curation = load_viewer_curation(tmp_path, context, path)

    assert curation.views.logical == type(curation.views.logical)()
    assert any("unsafe evidence" in warning.message.lower() for warning in curation.diagnostics)


def test_explicit_config_path_cannot_escape_repo_and_merge_is_deterministic(tmp_path):
    context = _context(tmp_path)
    curation = load_viewer_curation(tmp_path, context, tmp_path / "../outside.yaml")
    assert any("outside repository" in warning.message for warning in curation.diagnostics)
    assert merge_ordered(["b", "a"], ["a", "c"]) == ["b", "a", "c"]
    assert Selector(local_id="COMP-1", system="root").resolve(context) == "root::COMP-1"


def test_duplicate_curated_flows_are_warned_and_ignored(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  functional:
    groups:
      - {id: a, label: A}
      - {id: b, label: B}
    flows:
      - {source: a, target: b}
      - {source: a, target: b}
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.functional.flows == []
    assert any("Duplicate curated flow" in warning.message for warning in curation.diagnostics)
    assert any(item.code == "CURATION_SEMANTIC_FLOW_EVIDENCE" for item in curation.diagnostics)


def test_malformed_collections_and_orders_warn_and_fall_back(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  logical:
    featured: nope
    labels: nope
    order: nope
    groups:
      - {id: g, label: Group, order: not-a-number}
    flows: nope
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.logical.groups == []
    assert curation.diagnostics


def test_unknown_top_level_and_view_keys_warn(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
unexpected: true
views:
  conops:
    mystery: true
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert any("Unknown top-level key" in warning.message for warning in curation.diagnostics)
    assert curation.views.conops == type(curation.views.conops)()


def test_file_only_evidence_and_non_presentation_edge_kinds_are_rejected(tmp_path):
    context = _context(tmp_path)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  conops:
    externals:
      - {id: EXT-1, name: External, inferred: true, evidence: [evidence.md]}
    groups:
      - {id: a, label: A}
      - {id: b, label: B}
    flows:
      - source: a
        target: b
        kind: triggers
        inferred: true
        evidence: [{source: evidence.md, claim: A triggers B}]
      - source: a
        target: b
        kind: custom-flow
        inferred: true
        evidence: [{source: evidence.md, claim: A custom B}]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.conops.externals == []
    assert curation.views.conops.flows == []
    assert any("evidence record" in warning.message for warning in curation.diagnostics)


def test_global_presentation_ids_and_deferred_endpoint_validation(tmp_path):
    context = _context(tmp_path)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  functional:
    groups:
      - {id: shared, label: Group}
    tiers:
      - {id: shared, label: Tier}
    externals:
      - id: root::COMP-1
        name: Collision
        inferred: true
        evidence: [{source: evidence.md, claim: collision}]
    flows:
      - source: shared
        target: missing
        kind: exchange
        inferred: true
        evidence: [{source: evidence.md, claim: missing endpoint}]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.functional.tiers == []
    assert curation.views.functional.externals == []
    assert any("unknown target" in warning.message for warning in curation.diagnostics)


def test_invalid_view_fails_closed_while_other_view_survives(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  conops:
    unsupported: true
    featured: [root::COMP-1]
  logical:
    featured: [root::COMP-1]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.conops == type(curation.views.conops)()
    assert [item.resolved_id for item in curation.views.logical.featured] == ["root::COMP-1"]
    assert all(isinstance(item, Diagnostic) for item in curation.diagnostics)


def test_invalid_top_level_key_fails_closed_for_entire_profile(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
unsupported: true
views:
  logical:
    featured: [root::COMP-1]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.logical.featured == []
    assert any(item.code == "CURATION_ROOT_INVALID" for item in curation.diagnostics)


def test_preferred_roots_and_drilldowns_are_typed_and_resolved(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  functional:
    preferred_capability_root: root::COMP-1
    mission_root: {local_id: COMP-1, system: root}
    drilldowns:
      overview: root::COMP-1
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    view = curation.views.functional
    assert view.preferred_capability_root.resolved_id == "root::COMP-1"
    assert view.mission_root.resolved_id == "root::COMP-1"
    assert view.drilldowns["overview"].resolved_id == "root::COMP-1"


def test_unsafe_label_invalidates_only_its_view_and_math_text_survives(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  conops:
    labels: {root::COMP-1: '<script>alert(1)</script>'}
  logical:
    labels: {root::COMP-1: 'Latency < 10ms'}
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.conops.labels == {}
    assert curation.views.logical.labels["root::COMP-1"] == "Latency < 10ms"
    assert curation.views.logical.safe_text is True


def test_unknown_raw_svg_key_in_single_selector_invalidates_view(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  conops:
    featured:
      - qualified_id: root::COMP-1
        raw_svg: '<circle />'
  logical:
    featured: [root::COMP-1]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.conops == type(curation.views.conops)()
    assert curation.views.logical.featured
    assert any(item.code == "CURATION_KEY_UNSUPPORTED" and item.view == "conops" for item in curation.diagnostics)


def test_script_group_label_invalidates_view_but_math_group_label_survives(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  conops:
    groups:
      - {id: bad, label: '<script>alert(1)</script>'}
  logical:
    groups:
      - {id: latency, label: 'Latency < 10ms'}
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.conops.groups == []
    assert curation.views.logical.groups[0].label == "Latency < 10ms"
    assert any(item.code == "CURATION_TEXT_UNSAFE" and item.view == "conops" for item in curation.diagnostics)


def test_unknown_keys_in_all_nested_record_types_fail_view_closed(tmp_path):
    context = _context(tmp_path)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    records = {
        "groups": "groups: [{id: g, label: G, raw_svg: x}]",
        "externals": "externals: [{id: e, name: E, inferred: true, evidence: [{source: evidence.md, claim: c}], raw_svg: x}]",
        "evidence": "externals: [{id: e, name: E, inferred: true, evidence: [{source: evidence.md, claim: c, raw_svg: x}]}]",
        "flows": "groups: [{id: a, label: A}, {id: b, label: B}]\n    flows: [{source: a, target: b, raw_svg: x}]",
    }
    for name, body in records.items():
        path = tmp_path / f"{name}.yaml"
        path.write_text(f"version: 1\nviews:\n  logical:\n    {body}\n", encoding="utf-8")
        curation = load_viewer_curation(tmp_path, context, path)
        assert curation.views.logical == type(curation.views.logical)(), name
        assert any(item.code == "CURATION_KEY_UNSUPPORTED" for item in curation.diagnostics), name


def test_nested_flow_and_evidence_text_validation_preserves_math(tmp_path):
    context = _context(tmp_path)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  logical:
    groups: [{id: a, label: 'A < B'}, {id: b, label: B}]
    flows:
      - source: a
        target: b
        kind: exchange
        inferred: true
        label: 'Latency < 10ms'
        description: 'Plain < comparison'
        evidence: [{source: evidence.md, claim: 'Observed p < 0.05'}]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.logical.flows[0].label == "Latency < 10ms"
    assert curation.views.logical.flows[0].evidence[0].claim == "Observed p < 0.05"


def test_empty_or_multi_mode_selector_invalidates_view(tmp_path):
    context = _context(tmp_path)
    for name, selector in (("empty", "{}"), ("multi", "{qualified_id: root::COMP-1, name: Shared}"), ("system-only", "{system: root}")):
        path = tmp_path / f"{name}.yaml"
        path.write_text(f"version: 1\nviews:\n  conops:\n    featured: [{selector}]\n", encoding="utf-8")
        curation = load_viewer_curation(tmp_path, context, path)
        assert curation.views.conops == type(curation.views.conops)(), name
        assert any(item.code == "CURATION_SELECTOR_INVALID" for item in curation.diagnostics), name


def test_semantic_validation_invalidates_view_for_unknown_references(tmp_path):
    context = _context(tmp_path)
    cases = {
        "label": "labels: {root::MISSING: Label}",
        "parent": "groups: [{id: child, label: Child, parent: missing}]",
        "root": "preferred_capability_root: root::MISSING",
        "flow": "groups: [{id: a, label: A}]\n    flows: [{source: a, target: missing}]",
    }
    for name, body in cases.items():
        path = tmp_path / f"semantic-{name}.yaml"
        path.write_text(f"version: 1\nviews:\n  functional:\n    {body}\n", encoding="utf-8")
        curation = load_viewer_curation(tmp_path, context, path)
        assert curation.views.functional == type(curation.views.functional)(), name
        assert any(item.code.startswith("CURATION_SEMANTIC") for item in curation.diagnostics), name


def test_flow_can_reference_resolved_aggregate_selector(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "aggregate-flow.yaml"
    path.write_text("""version: 1
views:
  logical:
    aggregate_components: [root::COMP-1]
    groups: [{id: clients, label: Clients}]
    flows: [{source: clients, target: root::COMP-1}]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.logical.flows == []
    assert any(item.code == "CURATION_SEMANTIC_FLOW_EVIDENCE" for item in curation.diagnostics)


def test_noncanonical_flow_requires_inferred_structured_evidence(tmp_path):
    context = _context(tmp_path)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    cases = {
        "no-evidence": "groups: [{id: a, label: A}, {id: b, label: B}]\n    flows: [{source: a, target: b}]",
        "not-inferred": "groups: [{id: a, label: A}, {id: b, label: B}]\n    flows: [{source: a, target: b, evidence: [{source: evidence.md, claim: observed}]}]",
        "bad-path": "groups: [{id: a, label: A}, {id: b, label: B}]\n    flows: [{source: a, target: b, inferred: true, kind: exchange, evidence: [{source: ../outside.md, claim: observed}]}]",
    }
    for name, body in cases.items():
        path = tmp_path / f"flow-{name}.yaml"
        path.write_text(f"version: 1\nviews:\n  logical:\n    {body}\n", encoding="utf-8")
        curation = load_viewer_curation(tmp_path, context, path)
        assert curation.views.logical == type(curation.views.logical)(), name
        assert curation.diagnostics, name


def test_canonical_context_relationship_can_back_evidence_free_flow(tmp_path):
    model_path = tmp_path / ".architecture-model.yaml"
    model_path.write_text("""meta: {project: canonical, schema_version: '2.0'}
entities:
  components:
    - {id: A, name: A, status: ACTIVE}
    - {id: B, name: B, status: ACTIVE}
relationships:
  - {from: A, to: B, type: depends-on}
""", encoding="utf-8")
    context = ArchitectureViewContext.from_repo(tmp_path)
    path = tmp_path / "curation.yaml"
    path.write_text("""version: 1
views:
  logical:
    flows: [{source: 'root::A', target: 'root::B', kind: depends-on}]
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert len(curation.views.logical.flows) == 1


def test_external_requires_inferred_true_and_structured_repo_evidence(tmp_path):
    context = _context(tmp_path)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    for inferred, record in (("false", "{source: evidence.md, claim: observed}"), ("true", "evidence.md"), ("true", "{source: ../outside.md, claim: observed}")):
        path = tmp_path / f"external-{inferred}-{len(record)}.yaml"
        path.write_text(f"version: 1\nviews:\n  conops:\n    externals: [{{id: EXT, name: External, inferred: {inferred}, evidence: [{record}]}}]\n", encoding="utf-8")
        curation = load_viewer_curation(tmp_path, context, path)
        assert curation.views.conops.externals == []
        assert curation.diagnostics


def test_group_members_are_qualified_resolved_presentation_selectors(tmp_path):
    context = _context(tmp_path)
    path = tmp_path / "groups.yaml"
    path.write_text("""version: 1
views:
  functional:
    groups:
      - {id: core, label: Core, members: [root::COMP-1]}
""", encoding="utf-8")
    curation = load_viewer_curation(tmp_path, context, path)
    assert curation.views.functional.groups[0].members == ["root::COMP-1"]
