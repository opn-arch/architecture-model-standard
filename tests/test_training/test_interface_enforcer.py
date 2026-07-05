"""Tests for InterfaceEnforcer — manifest-derived dependency injection."""

import pytest
from architecture_model.training.interface_enforcer import (
    InterfaceEnforcer,
    EnforcementResult,
)
from architecture_model.core.types import (
    ArchitectureModel, Entities, Component,
    Relationship, RelationType, Strength, Status, ModelMeta,
)


def _meta():
    return ModelMeta(schema_version="1.0", project="test")


def _model(components, relationships=None):
    return ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            actors=[], behaviors=[], interfaces=[], constraints=[],
            capabilities=[], layers=[],
            components=components,
        ),
        relationships=relationships or [],
    )


class TestInterfaceEnforcer:
    def test_injects_missing_relationships(self):
        """3 components, no existing rels, 2 import edges -> 2 new depends-on added."""
        model = _model([
            Component(id="C1", name="Client", status=Status.ACTIVE,
                      files=["src/client.py"]),
            Component(id="C2", name="Pool", status=Status.ACTIVE,
                      files=["src/pool.py"]),
            Component(id="C3", name="Utils", status=Status.ACTIVE,
                      files=["src/utils.py"]),
        ])
        manifest = {
            "modules": [
                {"file": "src/client.py", "name": "Client", "line_count": 100,
                 "functions": ["run"], "imports": ["src/pool.py"], "status": "active"},
                {"file": "src/pool.py", "name": "Pool", "line_count": 80,
                 "functions": ["acquire"], "imports": ["src/utils.py"], "status": "active"},
                {"file": "src/utils.py", "name": "Utils", "line_count": 50,
                 "functions": ["format"], "imports": [], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client.py", "target": "src/pool.py", "import_path": "pool"},
                {"source": "src/pool.py", "target": "src/utils.py", "import_path": "utils"},
            ],
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        assert result.added_count == 2
        # Original model untouched
        assert len(model.relationships) == 0
        # New model has 2 relationships
        assert len(result.model.relationships) == 2
        pairs = {(r.from_id, r.to_id) for r in result.model.relationships}
        assert ("C1", "C2") in pairs
        assert ("C2", "C3") in pairs

    def test_skips_existing_relationships(self):
        """1 existing consumes, 1 missing -> only 1 added, original preserved."""
        model = _model(
            components=[
                Component(id="C1", name="Client", status=Status.ACTIVE,
                          files=["src/client.py"]),
                Component(id="C2", name="Pool", status=Status.ACTIVE,
                          files=["src/pool.py"]),
                Component(id="C3", name="Utils", status=Status.ACTIVE,
                          files=["src/utils.py"]),
            ],
            relationships=[
                Relationship(type=RelationType.CONSUMES, from_id="C1", to_id="C2",
                             description="existing"),
            ],
        )
        manifest = {
            "modules": [
                {"file": "src/client.py", "name": "Client", "line_count": 100,
                 "functions": ["run"], "imports": ["src/pool.py"], "status": "active"},
                {"file": "src/pool.py", "name": "Pool", "line_count": 80,
                 "functions": ["acquire"], "imports": ["src/utils.py"], "status": "active"},
                {"file": "src/utils.py", "name": "Utils", "line_count": 50,
                 "functions": ["format"], "imports": [], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client.py", "target": "src/pool.py", "import_path": "pool"},
                {"source": "src/pool.py", "target": "src/utils.py", "import_path": "utils"},
            ],
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        assert result.added_count == 1
        assert result.skipped_count == 1
        # Total rels = 1 existing + 1 new
        assert len(result.model.relationships) == 2
        # Original relationship preserved
        existing = [r for r in result.model.relationships if r.description == "existing"]
        assert len(existing) == 1

    def test_infers_consumes_for_api_functions(self):
        """Target has get(), post(), subscribe() -> CONSUMES type."""
        model = _model([
            Component(id="C1", name="Client", status=Status.ACTIVE,
                      files=["src/client.py"]),
            Component(id="C2", name="API", status=Status.ACTIVE,
                      files=["src/api.py"]),
        ])
        manifest = {
            "modules": [
                {"file": "src/client.py", "name": "Client", "line_count": 100,
                 "functions": ["run"], "imports": ["src/api.py"], "status": "active"},
                {"file": "src/api.py", "name": "API", "line_count": 100,
                 "functions": ["get(url)", "post(url, data)", "subscribe(topic)"],
                 "imports": [], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client.py", "target": "src/api.py", "import_path": "api"},
            ],
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        assert result.added_count == 1
        added = result.model.relationships[-1]
        assert added.type == RelationType.CONSUMES

    def test_strength_from_edge_count(self):
        """6 files in comp A all import 6 files in comp B -> STRONG."""
        files_a = [f"src/a/mod{i}.py" for i in range(6)]
        files_b = [f"src/b/mod{i}.py" for i in range(6)]
        model = _model([
            Component(id="C1", name="CompA", status=Status.ACTIVE, files=files_a),
            Component(id="C2", name="CompB", status=Status.ACTIVE, files=files_b),
        ])
        # Each file in A imports a different file in B = 6 edges
        modules = []
        for i, f in enumerate(files_a):
            modules.append({
                "file": f, "name": f"ModA{i}", "line_count": 50,
                "functions": ["work"], "imports": [files_b[i]], "status": "active",
            })
        for i, f in enumerate(files_b):
            modules.append({
                "file": f, "name": f"ModB{i}", "line_count": 50,
                "functions": ["process"], "imports": [], "status": "active",
            })
        interfaces = [
            {"source": files_a[i], "target": files_b[i], "import_path": f"b.mod{i}"}
            for i in range(6)
        ]
        manifest = {
            "modules": modules,
            "interfaces": interfaces,
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        assert result.added_count == 1
        added = result.model.relationships[0]
        assert added.strength == Strength.STRONG

    def test_internal_edges_not_injected(self):
        """Both files in same component -> no rels added."""
        model = _model([
            Component(id="C1", name="Client", status=Status.ACTIVE,
                      files=["src/client.py", "src/helper.py"]),
        ])
        manifest = {
            "modules": [
                {"file": "src/client.py", "name": "Client", "line_count": 100,
                 "functions": ["run"], "imports": ["src/helper.py"], "status": "active"},
                {"file": "src/helper.py", "name": "Helper", "line_count": 50,
                 "functions": ["help"], "imports": [], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client.py", "target": "src/helper.py", "import_path": "helper"},
            ],
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        assert result.added_count == 0
        assert result.internal_count == 1
        assert len(result.model.relationships) == 0

    def test_empty_manifest_no_change(self):
        """Empty interfaces -> nothing added."""
        model = _model([
            Component(id="C1", name="Client", status=Status.ACTIVE,
                      files=["src/client.py"]),
        ])
        manifest = {
            "modules": [],
            "interfaces": [],
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        assert result.added_count == 0
        assert result.skipped_count == 0
        assert result.internal_count == 0
        assert len(result.model.relationships) == 0

    def test_bidirectional_imports_become_depends_on(self):
        """A imports B AND B imports A -> DEPENDS_ON (mutual coupling)."""
        model = _model([
            Component(id="C1", name="Client", status=Status.ACTIVE,
                      files=["src/client.py"]),
            Component(id="C2", name="API", status=Status.ACTIVE,
                      files=["src/api.py"]),
        ])
        manifest = {
            "modules": [
                {"file": "src/client.py", "name": "Client", "line_count": 100,
                 "functions": ["run"], "imports": ["src/api.py"], "status": "active"},
                {"file": "src/api.py", "name": "API", "line_count": 100,
                 "functions": ["get(url)", "post(url, data)"],
                 "imports": ["src/client.py"], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client.py", "target": "src/api.py", "import_path": "api"},
                {"source": "src/api.py", "target": "src/client.py", "import_path": "client"},
            ],
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        # Both directions should be DEPENDS_ON (bidirectional overrides CONSUMES)
        for rel in result.model.relationships:
            assert rel.type == RelationType.DEPENDS_ON

    def test_enforce_returns_summary(self):
        """EnforcementResult has correct counts."""
        model = _model(
            components=[
                Component(id="C1", name="Client", status=Status.ACTIVE,
                          files=["src/client.py"]),
                Component(id="C2", name="Pool", status=Status.ACTIVE,
                          files=["src/pool.py"]),
                Component(id="C3", name="Utils", status=Status.ACTIVE,
                          files=["src/utils.py"]),
                Component(id="C4", name="Internals", status=Status.ACTIVE,
                          files=["src/int_a.py", "src/int_b.py"]),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="C2"),
            ],
        )
        manifest = {
            "modules": [
                {"file": "src/client.py", "name": "Client", "line_count": 100,
                 "functions": ["run"], "imports": ["src/pool.py"], "status": "active"},
                {"file": "src/pool.py", "name": "Pool", "line_count": 80,
                 "functions": ["acquire"], "imports": ["src/utils.py"], "status": "active"},
                {"file": "src/utils.py", "name": "Utils", "line_count": 50,
                 "functions": ["format"], "imports": [], "status": "active"},
                {"file": "src/int_a.py", "name": "IntA", "line_count": 30,
                 "functions": ["a"], "imports": ["src/int_b.py"], "status": "active"},
                {"file": "src/int_b.py", "name": "IntB", "line_count": 30,
                 "functions": ["b"], "imports": [], "status": "active"},
            ],
            "interfaces": [
                {"source": "src/client.py", "target": "src/pool.py", "import_path": "pool"},
                {"source": "src/pool.py", "target": "src/utils.py", "import_path": "utils"},
                {"source": "src/int_a.py", "target": "src/int_b.py", "import_path": "int_b"},
            ],
            "functional_blocks": {},
        }

        enforcer = InterfaceEnforcer()
        result = enforcer.enforce(model, manifest)

        assert isinstance(result, EnforcementResult)
        assert result.added_count == 1       # C2->C3 is new
        assert result.skipped_count == 1     # C1->C2 already exists
        assert result.internal_count == 1    # int_a->int_b same component
