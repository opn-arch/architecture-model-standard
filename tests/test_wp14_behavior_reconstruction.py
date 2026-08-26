"""WP-14: Behavior reconstruction from call graph and capability mapping."""
from architecture_model.pipeline.reconstruct_behaviors import reconstruct_behaviors
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Capability, Component,
    Relationship, RelationType, Status,
)


class TestBehaviorReconstruction:
    def test_generates_behavior_per_capability(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                capabilities=[
                    Capability(id="CAP-1", name="Validate Model", status=Status.ACTIVE,
                               description="Validates architecture models"),
                ],
                components=[
                    Component(id="COMP-1", name="Validator", status=Status.ACTIVE),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1"),
            ],
        )
        behaviors, rels = reconstruct_behaviors(model)
        assert len(behaviors) >= 1
        assert any("Validate" in b.name for b in behaviors)
        assert all(b.intent for b in behaviors), "All behaviors should have intent"
        assert all(b.steps for b in behaviors), "All behaviors should have steps"
        assert len(rels) >= 1

    def test_skips_capabilities_with_existing_behaviors(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                capabilities=[
                    Capability(id="CAP-1", name="Validate", status=Status.ACTIVE),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.TRACES_TO, from_id="BEH-1", to_id="CAP-1"),
            ],
        )
        behaviors, rels = reconstruct_behaviors(model)
        assert len(behaviors) == 0

    def test_steps_from_realizing_components(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                capabilities=[
                    Capability(id="CAP-1", name="Parse", status=Status.ACTIVE,
                               description="Parse YAML models"),
                ],
                components=[
                    Component(id="COMP-1", name="YAML Parser", status=Status.ACTIVE),
                    Component(id="COMP-2", name="Schema Checker", status=Status.ACTIVE),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1"),
                Relationship(type=RelationType.REALIZES, from_id="COMP-2", to_id="CAP-1"),
            ],
        )
        behaviors, rels = reconstruct_behaviors(model)
        assert len(behaviors) == 1
        assert "YAML Parser" in behaviors[0].steps[0]
        assert "Schema Checker" in behaviors[0].steps[1]
