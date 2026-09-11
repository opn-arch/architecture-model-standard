"""Bug 3: logical projector must surface every model-declared layer as a lane.

Prior behavior hardcoded ``_LOGICAL_TIERS`` (5 canonical tiers: Web,
Application, Domain, Data, Infrastructure) and dropped model layers
that didn't semantically match. A model with 7 explicit layers (e.g.
``Foundation``, ``Domain``, ``Application``, ``Interface``,
``Infrastructure``, ``Observability``, ``AI Integration``) would lose
``Foundation``, ``Observability``, and ``AI Integration``.

The fix iterates ``model.entities.layers`` and turns each into a lane;
the canonical tier list remains a fallback for models that declare no
layers at all.
"""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import project_logical_architecture
from architecture_model.core.view_context import ArchitectureViewContext


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


def test_project_logical_architecture_surfaces_every_model_layer_as_lane(tmp_path):
    context = _seven_layer_context(tmp_path)
    spec = project_logical_architecture(context)
    lane_labels = {group.label for group in spec.lanes if group.kind == "tier"}
    assert {
        "Foundation", "Domain", "Application", "Interface",
        "Infrastructure", "Observability", "AI Integration",
    } <= lane_labels, (
        f"Expected every model-declared layer to appear as a tier lane. "
        f"Got: {sorted(lane_labels)}"
    )


def test_project_logical_architecture_falls_back_to_canonical_tiers_when_no_layers(tmp_path):
    _write(tmp_path / ".architecture-model.yaml", """meta: {project: none, schema_version: '2.0'}
entities:
  components:
    - {id: COMP-1, name: Web Gateway, status: ACTIVE, layer: web, files: [src/web/g.py]}
    - {id: COMP-2, name: Domain Rules, status: ACTIVE, layer: domain, files: [src/domain/r.py]}
relationships: []
""")
    context = ArchitectureViewContext.load(
        load_model(tmp_path / ".architecture-model.yaml"), tmp_path
    )
    spec = project_logical_architecture(context)
    lane_ids = {group.id for group in spec.lanes if group.kind == "tier"}
    assert any("logical-tier:" in identifier for identifier in lane_ids), (
        f"Expected canonical tier fallback when model declares no layers. "
        f"Got: {sorted(lane_ids)}"
    )
