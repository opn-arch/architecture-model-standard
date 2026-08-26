"""WP-11: Two-tier validation scoring — structural + semantic."""
from architecture_model.core.validator import validate_model, Severity
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability,
    Interface, Status,
)


class TestSemanticScoring:
    def test_missing_intent_flagged(self):
        """Components without intent should get SEMANTIC_MISSING_INTENT info."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Core", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        result = validate_model(model)
        semantic_issues = [i for i in result.issues if i.code and "SEMANTIC" in i.code]
        assert len(semantic_issues) > 0, "Should flag missing intent"
        assert any("intent" in i.message.lower() for i in semantic_issues)

    def test_populated_intent_no_flag(self):
        """Components with intent should not get SEMANTIC_MISSING_INTENT."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Core", status=Status.ACTIVE,
                          intent="Provide validation"),
            ]),
            relationships=[],
        )
        result = validate_model(model)
        intent_issues = [i for i in result.issues
                         if i.code and "SEMANTIC_MISSING_INTENT" in i.code]
        assert len(intent_issues) == 0

    def test_missing_responsibilities_flagged(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Core", status=Status.ACTIVE,
                          intent="Provide validation"),
            ]),
            relationships=[],
        )
        result = validate_model(model)
        resp_issues = [i for i in result.issues
                       if i.code and "SEMANTIC_MISSING_RESPONSIBILITIES" in i.code]
        assert len(resp_issues) > 0

    def test_semantic_issues_are_info_level(self):
        """Semantic issues should be INFO, not WARNING or ERROR."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Core", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        result = validate_model(model)
        semantic_issues = [i for i in result.issues if i.code and "SEMANTIC" in i.code]
        assert all(i.severity == Severity.INFO for i in semantic_issues)

    def test_capability_missing_moes_flagged(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(capabilities=[
                Capability(id="CAP-1", name="Validate", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        result = validate_model(model)
        moe_issues = [i for i in result.issues
                      if i.code and "SEMANTIC_MISSING_MOES" in i.code]
        assert len(moe_issues) > 0
