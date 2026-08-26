"""WP-15: Propagate sub-model enrichment to root model."""
from architecture_model.core.propagation import propagate_enrichment
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Status,
    FunctionSignature, TestContract,
)


class TestEnrichmentPropagation:
    def test_signatures_propagate_to_root(self):
        root = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Core", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        sub = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01",
                           refines_component="COMP-1"),
            entities=Entities(components=[
                Component(id="COMP-1.1", name="Parser", status=Status.ACTIVE,
                          signatures=[FunctionSignature(name="parse", params=["path"])],
                          test_contracts=[TestContract(test_file="test_parser.py",
                                                       assertion="returns model",
                                                       contract_type="output",
                                                       test_method="test_parse")]),
            ]),
            relationships=[],
        )
        updated = propagate_enrichment(root, [sub])
        root_comp = updated.entities.components[0]
        assert len(root_comp.signatures) >= 1
        assert len(root_comp.test_contracts) >= 1
