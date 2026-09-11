"""Curation ``labels`` must override lane names in the logical view.

The prior projector behavior in ``project_logical_architecture`` only
consumed ``curation.labels`` via ``_label(entity, curation)`` for entity
nodes. Model layers become tier **lanes** (``DiagramGroup``), not
nodes, so lane captions ignored the curation.labels overrides entirely.

The fix (this test guards) honors ``curation.labels[layer.key]`` in the
``elif model_layers:`` branch — the branch introduced by the Bug 3 fix
that surfaces every model-declared layer as a lane. Also guards the
curated-tiers branch against a regression by verifying
``curation.labels[tier.id]`` is honored when a tier id has a label
override.
"""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import project_logical_architecture
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import (
    CuratedGroup,
    Selector,
    ViewCuration,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seven_layer_context(tmp_path: Path) -> ArchitectureViewContext:
    _write(tmp_path / ".architecture-model.yaml", """meta: {project: seven, schema_version: '2.0'}
entities:
  layers:
    - {id: LAY-1, name: Foundation, status: ACTIVE, order: 1}
    - {id: LAY-2, name: Domain, status: ACTIVE, order: 2}
    - {id: LAY-3, name: Application, status: ACTIVE, order: 3}
    - {id: LAY-4, name: Interface, status: ACTIVE, order: 4}
    - {id: LAY-5, name: Infrastructure, status: ACTIVE, order: 5}
    - {id: LAY-6, name: Observability, status: ACTIVE, order: 6}
    - {id: LAY-7, name: AI Integration, status: ACTIVE, order: 7}
  components:
    - {id: COMP-1, name: Types, status: ACTIVE, layer: LAY-1, files: [src/foundation/types.py]}
    - {id: COMP-2, name: Domain Model, status: ACTIVE, layer: LAY-2, files: [src/domain/model.py]}
    - {id: COMP-3, name: Orchestrator, status: ACTIVE, layer: LAY-3, files: [src/application/orch.py]}
    - {id: COMP-4, name: HTTP API, status: ACTIVE, layer: LAY-4, files: [src/interface/http.py]}
    - {id: COMP-5, name: Kafka Adapter, status: ACTIVE, layer: LAY-5, files: [src/infra/kafka.py]}
    - {id: COMP-6, name: Tracer, status: ACTIVE, layer: LAY-6, files: [src/observability/tracer.py]}
    - {id: COMP-7, name: LLM Gateway, status: ACTIVE, layer: LAY-7, files: [src/ai/gateway.py]}
relationships: []
""")
    return ArchitectureViewContext.load(load_model(tmp_path / ".architecture-model.yaml"), tmp_path)


def _resolved(context: ArchitectureViewContext, key: str) -> str:
    """Return the fully-qualified entity key for a bare local id like LAY-1."""
    matches = context.select(local_id=key)
    assert len(matches) == 1, f"Expected exactly one match for {key}, got {matches}"
    return matches[0].key


def test_curation_labels_override_model_layer_lane_names(tmp_path):
    context = _seven_layer_context(tmp_path)
    labels = {
        _resolved(context, "LAY-1"): "Foundation (schema, types, parser)",
        _resolved(context, "LAY-6"): "Observability (SI&L, monitoring)",
        _resolved(context, "LAY-7"): "AI Integration (LLM providers, proposals)",
    }
    curation = ViewCuration(labels=labels)
    spec = project_logical_architecture(context, curation)
    lane_labels = {group.label for group in spec.lanes if group.kind == "tier"}
    # Overridden lanes:
    assert "Foundation (schema, types, parser)" in lane_labels
    assert "Observability (SI&L, monitoring)" in lane_labels
    assert "AI Integration (LLM providers, proposals)" in lane_labels
    # Non-overridden lanes fall back to layer.name:
    assert "Domain" in lane_labels
    assert "Application" in lane_labels


def test_curation_labels_override_curated_tier_lane_names(tmp_path):
    context = _seven_layer_context(tmp_path)
    tiers = [
        CuratedGroup(
            id="tier-platform",
            label="Cross-cutting Platform",
            kind="tier",
            members=[_resolved(context, "LAY-1"), _resolved(context, "LAY-5")],
        ),
        CuratedGroup(
            id="tier-core",
            label="Core Modeling",
            kind="tier",
            members=[_resolved(context, "LAY-2"), _resolved(context, "LAY-3")],
        ),
    ]
    labels = {"tier-platform": "Cross-cutting Platform (relabeled)"}
    curation = ViewCuration(tiers=tiers, labels=labels)
    spec = project_logical_architecture(context, curation)
    lane_labels = {group.label for group in spec.lanes if group.kind == "tier"}
    assert "Cross-cutting Platform (relabeled)" in lane_labels
    # tier-core has no label override; falls back to its curated label.
    assert "Core Modeling" in lane_labels
