"""Shared model fixture for SE doc generator tests."""
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability,
    Actor, ActorType, Behavior, Interface, InterfaceType, Constraint,
    ConstraintType, Layer, Relationship, Status, Priority,
)


def make_model() -> ArchitectureModel:
    """Create a model with v2.1 fields populated for doc generation tests."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.1", project="test-project",
                       system="Test System", generated_at="2026-08-26"),
        entities=Entities(
            actors=[
                Actor(id="ACT-1", name="Developer", status=Status.ACTIVE,
                      type=ActorType.HUMAN, intent="Primary user of the system",
                      goals=["Ship features fast", "Maintain code quality"]),
            ],
            capabilities=[
                Capability(id="CAP-1", name="Model Validation", status=Status.ACTIVE,
                           description="Validates architecture models against schema",
                           intent="Ensure models are structurally correct before use",
                           priority=Priority.HIGH,
                           moes=["Validation score >= 80/100",
                                 "Zero critical issues on valid models"]),
                Capability(id="CAP-2", name="Context Formatting", status=Status.ACTIVE,
                           description="Compresses models for LLM consumption",
                           intent="Minimize token usage while preserving semantic content",
                           moes=["Compression ratio > 5x for repos > 50K tokens"]),
            ],
            components=[
                Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                          kind="library", layer="core",
                          description="Core validation engine",
                          intent="Single source of truth for model correctness",
                          responsibilities=["Schema validation", "Relationship integrity"],
                          goals=["100% coverage of schema rules"],
                          moes=["All 17 relationship types validated"],
                          trade_offs=["Strict validation vs permissive parsing",
                                      "Performance vs thoroughness"],
                          failure_modes=["Silent acceptance of invalid models",
                                         "False positives blocking valid models"],
                          files=["src/architecture_model/core/validator.py"]),
                Component(id="COMP-2", name="Slicer", status=Status.ACTIVE,
                          kind="library", layer="core",
                          description="Model slicing and filtering",
                          intent="Enable focused views of large models",
                          responsibilities=["F-block slicing", "Layer slicing"],
                          goals=["Sub-second slice operations"],
                          trade_offs=["Completeness vs token budget"],
                          files=["src/architecture_model/core/slicer.py"]),
            ],
            behaviors=[
                Behavior(id="BEH-1", name="Validate Model", status=Status.ACTIVE,
                         actor="ACT-1", trigger="User runs validate command",
                         preconditions=["Model file exists"],
                         steps=["Load model from YAML", "Run structural checks",
                                "Run semantic checks", "Return score"],
                         postconditions=["Validation result returned"]),
            ],
            interfaces=[
                Interface(id="IF-1", name="Validation API", status=Status.ACTIVE,
                           type=InterfaceType.INTERNAL,
                          description="validate_model(model) -> ValidationResult",
                          provider="COMP-1", consumer="COMP-2",
                          contract="Pre: model is parsed ArchitectureModel. Post: result.score in 0..100. Invariant: idempotent."),
            ],
            constraints=[
                Constraint(id="CON-1", name="Schema Compatibility", status=Status.ACTIVE,
                            type=ConstraintType.TECHNOLOGY,
                           description="Must support schema versions 1.0-2.1",
                           rationale="Backward compatibility with existing models"),
            ],
            layers=[
                Layer(id="L-1", name="Core", status=Status.ACTIVE, order=1,
                      technology="Python", directories=["src/architecture_model/core"]),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type="realizes"),
            Relationship(from_id="COMP-2", to_id="CAP-2", type="realizes"),
            Relationship(from_id="COMP-2", to_id="COMP-1", type="depends-on"),
            Relationship(from_id="COMP-1", to_id="IF-1", type="exposes"),
            Relationship(from_id="BEH-1", to_id="COMP-1", type="traces-to"),
        ],
    )
