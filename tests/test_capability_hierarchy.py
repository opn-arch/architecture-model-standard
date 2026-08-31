"""Tests for capability hierarchy in the architecture model."""
import pytest
import yaml
from pathlib import Path
from architecture_model.orchestration.capability_inference import (
    infer_capabilities, build_capability_hierarchy
)
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Capability, Relationship, RelationType
)

MODEL_PATH = Path(__file__).parent.parent / ".architecture-model.yaml"


def _load_model():
    with open(MODEL_PATH) as f:
        return yaml.safe_load(f)


# --- Model YAML hierarchy tests ---

class TestModelCapabilityHierarchy:
    def test_root_capability_exists(self):
        model = _load_model()
        caps = {c["id"]: c for c in model["entities"]["capabilities"]}
        assert "CAP-0" in caps
        assert caps["CAP-0"]["name"] == "Provide Architecture-as-Code Standard"

    def test_l1_group_capabilities_exist(self):
        model = _load_model()
        caps = {c["id"] for c in model["entities"]["capabilities"]}
        for cap_id in ["CAP-0.1", "CAP-0.2", "CAP-0.3", "CAP-0.4"]:
            assert cap_id in caps, f"Missing L1 group capability {cap_id}"

    def test_l2_sub_capabilities_count(self):
        """At least 70 L2 sub-capabilities should exist."""
        model = _load_model()
        caps = model["entities"]["capabilities"]
        l2_caps = [c for c in caps if "." in c["id"] and not c["id"].startswith("CAP-0.")]
        assert len(l2_caps) >= 70, f"Only {len(l2_caps)} L2 sub-capabilities"

    def test_all_capabilities_have_descriptions(self):
        """Every capability should have a description."""
        model = _load_model()
        for cap in model["entities"]["capabilities"]:
            assert cap.get("description"), f"{cap['id']} missing description"

    def test_hierarchy_contains_relationships(self):
        """Every sub-capability should have a contains relationship from its parent."""
        model = _load_model()
        contains_rels = {(r["from_id"], r["to_id"]) for r in model["relationships"]
                         if r["type"] == "contains"}
        caps = model["entities"]["capabilities"]
        for cap in caps:
            cid = cap["id"]
            if "." in cid:
                parent = cid.rsplit(".", 1)[0]
                assert (parent, cid) in contains_rels, f"Missing contains: {parent} -> {cid}"

    def test_all_existing_caps_have_parent(self):
        """CAP-1 through CAP-15 should be contained by a CAP-0.x parent."""
        model = _load_model()
        contains_rels = {r["to_id"] for r in model["relationships"]
                         if r["type"] == "contains" and r["from_id"].startswith("CAP-0.")}
        for i in range(1, 16):
            assert f"CAP-{i}" in contains_rels, f"CAP-{i} not contained by any L1 group"


# --- Inference unit tests (pre-existing) ---

class TestCapabilityInference:
    def test_nested_urls_create_hierarchy(self):
        """Deeper URL paths create parent-child capability relationships."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                behaviors=[
                    Behavior(id="BEH-1", name="List logs", status="ACTIVE", trigger="GET /logs"),
                    Behavior(id="BEH-2", name="Parse log", status="ACTIVE", trigger="POST /logs/parse"),
                    Behavior(id="BEH-3", name="Search logs", status="ACTIVE", trigger="GET /logs/search"),
                    Behavior(id="BEH-4", name="Get orders", status="ACTIVE", trigger="GET /orders"),
                ],
                capabilities=[
                    Capability(id="CAP-1", name="Log Management", status="ACTIVE"),
                    Capability(id="CAP-2", name="Log Parsing", status="ACTIVE"),
                    Capability(id="CAP-3", name="Log Search", status="ACTIVE"),
                    Capability(id="CAP-4", name="Order Management", status="ACTIVE"),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="BEH-1", to_id="CAP-1"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-2", to_id="CAP-2"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-3", to_id="CAP-3"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-4", to_id="CAP-4"),
            ]
        )
        result = build_capability_hierarchy(model)
        contains = [r for r in result.relationships if r.type == RelationType.CONTAINS]
        assert len(contains) == 2
        parent_ids = {r.from_id for r in contains}
        child_ids = {r.to_id for r in contains}
        assert "CAP-1" in parent_ids
        assert "CAP-2" in child_ids
        assert "CAP-3" in child_ids

    def test_flat_urls_no_hierarchy(self):
        """All same-depth paths produce no hierarchy."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                behaviors=[
                    Behavior(id="BEH-1", name="A", status="ACTIVE", trigger="GET /users"),
                    Behavior(id="BEH-2", name="B", status="ACTIVE", trigger="GET /orders"),
                ],
                capabilities=[
                    Capability(id="CAP-1", name="Users", status="ACTIVE"),
                    Capability(id="CAP-2", name="Orders", status="ACTIVE"),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="BEH-1", to_id="CAP-1"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-2", to_id="CAP-2"),
            ]
        )
        result = build_capability_hierarchy(model)
        contains = [r for r in result.relationships if r.type == RelationType.CONTAINS]
        assert len(contains) == 0

    def test_no_capabilities_returns_unchanged(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(capabilities=[]),
            relationships=[]
        )
        result = build_capability_hierarchy(model)
        assert result == model

    def test_preserves_existing_relationships(self):
        """Existing relationships are not removed."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                behaviors=[
                    Behavior(id="BEH-1", name="A", status="ACTIVE", trigger="GET /x"),
                ],
                capabilities=[
                    Capability(id="CAP-1", name="X", status="ACTIVE"),
                    Capability(id="CAP-2", name="Y", status="ACTIVE"),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="BEH-1", to_id="CAP-1"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-1", to_id="COMP-2"),
            ]
        )
        result = build_capability_hierarchy(model)
        assert len(result.relationships) >= 2
