"""WP-9: Cross-repo consistency checking."""
from architecture_model.core.cross_repo import check_consistency
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Actor, ActorType, Status,
)


class TestCrossRepoConsistency:
    def test_schema_version_mismatch(self):
        m1 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="a", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        m2 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="b", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        issues = check_consistency([m1, m2])
        assert any("schema_version" in str(i).lower() for i in issues)

    def test_matching_actors_consistent(self):
        actor = Actor(id="ACT-1", name="Developer", status=Status.ACTIVE,
                      type=ActorType.HUMAN)
        m1 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="a", generated_at="2026-01-01"),
            entities=Entities(actors=[actor]), relationships=[],
        )
        m2 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="b", generated_at="2026-01-01"),
            entities=Entities(actors=[actor]), relationships=[],
        )
        issues = check_consistency([m1, m2])
        assert len(issues) == 0
