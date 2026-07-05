"""Tests for ArchitectureModel.to_dict() and to_yaml() serialization methods."""

from __future__ import annotations

import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Constraint,
    ConstraintType,
    Entities,
    Interface,
    InterfaceType,
    Layer,
    ModelMeta,
    Priority,
    Relationship,
    RelationType,
    Status,
    Strength,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_full_model() -> ArchitectureModel:
    """Build a comprehensive model with all entity types and fields populated."""
    meta = ModelMeta(
        schema_version="1.0",
        project="test-project",
        system="Test System",
        generated_at="2025-01-01T00:00:00Z",
        source_artifacts=["manifest.json", "tier1.yaml"],
        manifest_hash="abc123",
    )
    entities = Entities(
        actors=[
            Actor(
                id="actor-1",
                name="Developer",
                status=Status.ACTIVE,
                description="A software developer",
                tags=["human", "internal"],
                source_file="src/actors.py",
                source_line=10,
                type=ActorType.HUMAN,
                goals=["write code", "review PRs"],
            ),
        ],
        capabilities=[
            Capability(
                id="cap-1",
                name="Code Generation",
                status=Status.ACTIVE,
                description="Generate code from specs",
                tags=["core"],
                f_block="FB-CodeGen",
                priority=Priority.HIGH,
                requirements=["LLM access", "Template engine"],
            ),
        ],
        behaviors=[
            Behavior(
                id="beh-1",
                name="Generate Architecture",
                status=Status.ACTIVE,
                description="Generate architecture model from source",
                tags=["pipeline"],
                trigger="New project scan",
                actor="actor-1",
                preconditions=["Source code available"],
                postconditions=["Model file written"],
                steps=["Scan AST", "Extract entities", "Build model"],
                frequency="on-demand",
                priority=Priority.CRITICAL,
            ),
        ],
        interfaces=[
            Interface(
                id="iface-1",
                name="REST API",
                status=Status.ACTIVE,
                description="Main REST interface",
                tags=["api", "public"],
                type=InterfaceType.REST,
                protocol="HTTP/2",
                provider="comp-1",
                consumer="actor-1",
                data_format="JSON",
                endpoints=[{"method": "GET", "path": "/api/models"}],
            ),
        ],
        constraints=[
            Constraint(
                id="con-1",
                name="Response Time",
                status=Status.ACTIVE,
                description="API must respond within 200ms",
                tags=["performance"],
                type=ConstraintType.PERFORMANCE,
                metric="p99_latency_ms",
                threshold="200",
                rationale="User experience requirement",
            ),
        ],
        layers=[
            Layer(
                id="layer-1",
                name="Services",
                status=Status.ACTIVE,
                description="Service layer",
                tags=["backend"],
                order=2,
                technology=["Python", "FastAPI"],
                directories=["src/services/"],
            ),
        ],
        components=[
            Component(
                id="comp-1",
                name="Model Parser",
                status=Status.ACTIVE,
                description="Parses YAML into typed model",
                tags=["core", "parser"],
                layer="layer-1",
                f_block="FB-CodeGen",
                technology="Python",
                files=["src/parser.py", "src/types.py"],
                responsibilities=["Parse YAML", "Validate schema"],
            ),
        ],
    )
    relationships = [
        Relationship(
            type=RelationType.REALIZES,
            from_id="comp-1",
            to_id="cap-1",
            description="Parser realizes code generation",
            strength=Strength.STRONG,
        ),
        Relationship(
            type=RelationType.CONTAINS,
            from_id="layer-1",
            to_id="comp-1",
        ),
    ]
    return ArchitectureModel(meta=meta, entities=entities, relationships=relationships)


def _make_minimal_model() -> ArchitectureModel:
    """Build a minimal model with only required fields (no optional data)."""
    meta = ModelMeta(schema_version="1.0", project="minimal")
    entities = Entities(
        actors=[Actor(id="a1", name="User", status=Status.ACTIVE)],
    )
    return ArchitectureModel(meta=meta, entities=entities, relationships=[])


# ---------------------------------------------------------------------------
# Tests: to_dict() structure
# ---------------------------------------------------------------------------


class TestToDictStructure:
    """Test that to_dict() produces the expected top-level structure."""

    def test_returns_dict(self):
        model = _make_full_model()
        result = model.to_dict()
        assert isinstance(result, dict)

    def test_has_meta_entities_relationships_keys(self):
        model = _make_full_model()
        result = model.to_dict()
        assert "meta" in result
        assert "entities" in result
        assert "relationships" in result

    def test_meta_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        meta = result["meta"]
        assert meta["schema_version"] == "1.0"
        assert meta["project"] == "test-project"
        assert meta["system"] == "Test System"
        assert meta["generated_at"] == "2025-01-01T00:00:00Z"
        assert meta["source_artifacts"] == ["manifest.json", "tier1.yaml"]
        assert meta["manifest_hash"] == "abc123"

    def test_entities_has_all_types(self):
        model = _make_full_model()
        result = model.to_dict()
        ents = result["entities"]
        assert "actors" in ents
        assert "capabilities" in ents
        assert "behaviors" in ents
        assert "interfaces" in ents
        assert "constraints" in ents
        assert "layers" in ents
        assert "components" in ents


# ---------------------------------------------------------------------------
# Tests: Enum serialization
# ---------------------------------------------------------------------------


class TestEnumSerialization:
    """Verify all enum values are serialized as strings, not enum objects."""

    def test_status_is_string(self):
        model = _make_full_model()
        result = model.to_dict()
        actor = result["entities"]["actors"][0]
        assert actor["status"] == "ACTIVE"
        assert isinstance(actor["status"], str)

    def test_actor_type_is_string(self):
        model = _make_full_model()
        result = model.to_dict()
        actor = result["entities"]["actors"][0]
        assert actor["type"] == "human"
        assert isinstance(actor["type"], str)

    def test_interface_type_is_string(self):
        model = _make_full_model()
        result = model.to_dict()
        iface = result["entities"]["interfaces"][0]
        assert iface["type"] == "REST"
        assert isinstance(iface["type"], str)

    def test_constraint_type_is_string(self):
        model = _make_full_model()
        result = model.to_dict()
        con = result["entities"]["constraints"][0]
        assert con["type"] == "performance"
        assert isinstance(con["type"], str)

    def test_priority_is_string(self):
        model = _make_full_model()
        result = model.to_dict()
        cap = result["entities"]["capabilities"][0]
        assert cap["priority"] == "high"
        assert isinstance(cap["priority"], str)

    def test_relationship_type_is_string(self):
        model = _make_full_model()
        result = model.to_dict()
        rel = result["relationships"][0]
        assert rel["type"] == "realizes"
        assert isinstance(rel["type"], str)

    def test_strength_is_string(self):
        model = _make_full_model()
        result = model.to_dict()
        rel = result["relationships"][0]
        assert rel["strength"] == "strong"
        assert isinstance(rel["strength"], str)


# ---------------------------------------------------------------------------
# Tests: Relationship key names
# ---------------------------------------------------------------------------


class TestRelationshipKeys:
    """Verify relationships use 'from'/'to' keys (not 'from_id'/'to_id')."""

    def test_uses_from_key(self):
        model = _make_full_model()
        result = model.to_dict()
        rel = result["relationships"][0]
        assert "from" in rel
        assert "from_id" not in rel

    def test_uses_to_key(self):
        model = _make_full_model()
        result = model.to_dict()
        rel = result["relationships"][0]
        assert "to" in rel
        assert "to_id" not in rel

    def test_from_to_values_correct(self):
        model = _make_full_model()
        result = model.to_dict()
        rel = result["relationships"][0]
        assert rel["from"] == "comp-1"
        assert rel["to"] == "cap-1"


# ---------------------------------------------------------------------------
# Tests: Optional field omission
# ---------------------------------------------------------------------------


class TestOptionalFieldOmission:
    """Verify empty optional fields are omitted for cleanliness."""

    def test_empty_description_omitted(self):
        model = _make_minimal_model()
        result = model.to_dict()
        actor = result["entities"]["actors"][0]
        assert "description" not in actor

    def test_empty_tags_omitted(self):
        model = _make_minimal_model()
        result = model.to_dict()
        actor = result["entities"]["actors"][0]
        assert "tags" not in actor

    def test_none_source_file_omitted(self):
        model = _make_minimal_model()
        result = model.to_dict()
        actor = result["entities"]["actors"][0]
        assert "source_file" not in actor

    def test_none_source_line_omitted(self):
        model = _make_minimal_model()
        result = model.to_dict()
        actor = result["entities"]["actors"][0]
        assert "source_line" not in actor

    def test_empty_meta_system_omitted(self):
        model = _make_minimal_model()
        result = model.to_dict()
        assert "system" not in result["meta"]

    def test_empty_meta_manifest_hash_omitted(self):
        model = _make_minimal_model()
        result = model.to_dict()
        assert "manifest_hash" not in result["meta"]

    def test_default_strength_omitted_in_relationship(self):
        """Relationship with default MODERATE strength omits the field."""
        model = _make_full_model()
        result = model.to_dict()
        # Second relationship has default strength
        rel = result["relationships"][1]
        assert "strength" not in rel

    def test_default_priority_omitted(self):
        """Capability with MEDIUM priority (default) should omit priority."""
        meta = ModelMeta(schema_version="1.0", project="test")
        entities = Entities(
            capabilities=[
                Capability(
                    id="c1", name="Cap", status=Status.ACTIVE, priority=Priority.MEDIUM
                )
            ]
        )
        model = ArchitectureModel(meta=meta, entities=entities)
        result = model.to_dict()
        cap = result["entities"]["capabilities"][0]
        assert "priority" not in cap


# ---------------------------------------------------------------------------
# Tests: Entity-specific fields
# ---------------------------------------------------------------------------


class TestEntitySpecificFields:
    """Verify type-specific fields are serialized correctly."""

    def test_actor_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        actor = result["entities"]["actors"][0]
        assert actor["id"] == "actor-1"
        assert actor["name"] == "Developer"
        assert actor["type"] == "human"
        assert actor["goals"] == ["write code", "review PRs"]
        assert actor["source_file"] == "src/actors.py"
        assert actor["source_line"] == 10

    def test_capability_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        cap = result["entities"]["capabilities"][0]
        assert cap["f_block"] == "FB-CodeGen"
        assert cap["priority"] == "high"
        assert cap["requirements"] == ["LLM access", "Template engine"]

    def test_behavior_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        beh = result["entities"]["behaviors"][0]
        assert beh["trigger"] == "New project scan"
        assert beh["actor"] == "actor-1"
        assert beh["preconditions"] == ["Source code available"]
        assert beh["postconditions"] == ["Model file written"]
        assert beh["steps"] == ["Scan AST", "Extract entities", "Build model"]
        assert beh["frequency"] == "on-demand"
        assert beh["priority"] == "critical"

    def test_interface_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        iface = result["entities"]["interfaces"][0]
        assert iface["type"] == "REST"
        assert iface["protocol"] == "HTTP/2"
        assert iface["provider"] == "comp-1"
        assert iface["consumer"] == "actor-1"
        assert iface["data_format"] == "JSON"
        assert iface["endpoints"] == [{"method": "GET", "path": "/api/models"}]

    def test_constraint_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        con = result["entities"]["constraints"][0]
        assert con["type"] == "performance"
        assert con["metric"] == "p99_latency_ms"
        assert con["threshold"] == "200"
        assert con["rationale"] == "User experience requirement"

    def test_layer_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        layer = result["entities"]["layers"][0]
        assert layer["order"] == 2
        assert layer["technology"] == ["Python", "FastAPI"]
        assert layer["directories"] == ["src/services/"]

    def test_component_fields(self):
        model = _make_full_model()
        result = model.to_dict()
        comp = result["entities"]["components"][0]
        assert comp["layer"] == "layer-1"
        assert comp["f_block"] == "FB-CodeGen"
        assert comp["technology"] == "Python"
        assert comp["files"] == ["src/parser.py", "src/types.py"]
        assert comp["responsibilities"] == ["Parse YAML", "Validate schema"]


# ---------------------------------------------------------------------------
# Tests: to_yaml()
# ---------------------------------------------------------------------------


class TestToYaml:
    """Test that to_yaml() produces valid YAML strings."""

    def test_returns_string(self):
        model = _make_full_model()
        result = model.to_yaml()
        assert isinstance(result, str)

    def test_valid_yaml(self):
        model = _make_full_model()
        result = model.to_yaml()
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)
        assert "meta" in parsed
        assert "entities" in parsed
        assert "relationships" in parsed

    def test_yaml_matches_to_dict(self):
        model = _make_full_model()
        yaml_str = model.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed == model.to_dict()


# ---------------------------------------------------------------------------
# Tests: Round-trip compatibility with _parse_raw
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Verify to_dict() output is compatible with _parse_raw()."""

    def test_round_trip_preserves_entity_ids(self):
        """_parse_raw(model.to_dict()) should produce same entity IDs."""
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        assert original.all_entity_ids == rebuilt.all_entity_ids

    def test_round_trip_preserves_entity_count(self):
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        assert original.entity_count == rebuilt.entity_count

    def test_round_trip_preserves_relationship_count(self):
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        assert original.relationship_count == rebuilt.relationship_count

    def test_round_trip_preserves_meta(self):
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        assert rebuilt.meta.schema_version == original.meta.schema_version
        assert rebuilt.meta.project == original.meta.project
        assert rebuilt.meta.system == original.meta.system
        assert rebuilt.meta.generated_at == original.meta.generated_at
        assert rebuilt.meta.source_artifacts == original.meta.source_artifacts
        assert rebuilt.meta.manifest_hash == original.meta.manifest_hash

    def test_round_trip_preserves_actor_details(self):
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        orig_actor = original.entities.actors[0]
        new_actor = rebuilt.entities.actors[0]
        assert new_actor.id == orig_actor.id
        assert new_actor.name == orig_actor.name
        assert new_actor.status == orig_actor.status
        assert new_actor.type == orig_actor.type
        assert new_actor.goals == orig_actor.goals
        assert new_actor.description == orig_actor.description
        assert new_actor.tags == orig_actor.tags

    def test_round_trip_preserves_relationship_details(self):
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        orig_rel = original.relationships[0]
        new_rel = rebuilt.relationships[0]
        assert new_rel.type == orig_rel.type
        assert new_rel.from_id == orig_rel.from_id
        assert new_rel.to_id == orig_rel.to_id
        assert new_rel.description == orig_rel.description
        assert new_rel.strength == orig_rel.strength

    def test_round_trip_preserves_behavior_details(self):
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        orig = original.entities.behaviors[0]
        new = rebuilt.entities.behaviors[0]
        assert new.trigger == orig.trigger
        assert new.actor == orig.actor
        assert new.preconditions == orig.preconditions
        assert new.postconditions == orig.postconditions
        assert new.steps == orig.steps
        assert new.frequency == orig.frequency
        assert new.priority == orig.priority

    def test_round_trip_preserves_component_details(self):
        original = _make_full_model()
        rebuilt = _parse_raw(original.to_dict())
        orig = original.entities.components[0]
        new = rebuilt.entities.components[0]
        assert new.layer == orig.layer
        assert new.f_block == orig.f_block
        assert new.technology == orig.technology
        assert new.files == orig.files
        assert new.responsibilities == orig.responsibilities

    def test_round_trip_minimal_model(self):
        """Even a minimal model round-trips correctly."""
        original = _make_minimal_model()
        rebuilt = _parse_raw(original.to_dict())
        assert rebuilt.entity_count == original.entity_count
        assert rebuilt.entities.actors[0].id == "a1"
        assert rebuilt.entities.actors[0].name == "User"

    def test_yaml_round_trip(self):
        """to_yaml() → yaml.safe_load → _parse_raw produces equivalent model."""
        original = _make_full_model()
        yaml_str = original.to_yaml()
        raw = yaml.safe_load(yaml_str)
        rebuilt = _parse_raw(raw)
        assert original.all_entity_ids == rebuilt.all_entity_ids
        assert original.relationship_count == rebuilt.relationship_count
