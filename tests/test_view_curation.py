from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import Selector, load_viewer_curation, merge_ordered


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
    assert invalid.warnings


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

    assert [item.resolved_id for item in curation.views.conops.featured] == ["root::COMP-1"]
    assert any("Ambiguous selector" in warning for warning in curation.warnings)
    assert any("Duplicate selector" in warning for warning in curation.warnings)
    assert curation.views.conops.labels == {"root::COMP-1": "Primary"}


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
        evidence: [docs/evidence.md]
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
        evidence: [docs/evidence.md]
      - source: root::COMP-1
        target: EXT-GOOD
        kind: realizes
""", encoding="utf-8")

    curation = load_viewer_curation(tmp_path, context, path)

    assert [item.id for item in curation.views.logical.externals] == ["EXT-GOOD"]
    assert len(curation.views.logical.flows) == 1
    assert any("unsafe evidence" in warning.lower() for warning in curation.warnings)
    assert any("canonical relationship" in warning.lower() for warning in curation.warnings)


def test_explicit_config_path_cannot_escape_repo_and_merge_is_deterministic(tmp_path):
    context = _context(tmp_path)
    curation = load_viewer_curation(tmp_path, context, tmp_path / "../outside.yaml")
    assert any("outside repository" in warning for warning in curation.warnings)
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
    assert len(curation.views.functional.flows) == 1
    assert any("Duplicate curated flow" in warning for warning in curation.warnings)
