"""Tests for multi-signal system boundary detection."""
import pytest
from architecture_model.core.decomposer import detect_systems, SystemScore
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Relationship
)
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, FunctionInfo, MetricsResult, ModuleStatus
)
from datetime import datetime


def _make_manifest(modules):
    """Helper to build Manifest from module specs."""
    module_infos = []
    for m in modules:
        module_infos.append(ModuleInfo(
            file=m["file"], name=m.get("name", m["file"]),
            docstring="",
            functions=[FunctionInfo(name=f, signature=f"def {f}()") for f in m.get("functions", [])],
            imports=m.get("imports", []), line_count=50,
            status=ModuleStatus.ACTIVE, classes=[]
        ))
    return Manifest(
        modules=module_infos, interfaces=[],
        functional_blocks={}, generated_at=datetime.now().isoformat(),
        project_root="/tmp/test", metrics=MetricsResult(values={})
    )


def _make_model(components, relationships=None):
    """Helper to build model from component specs."""
    comps = [
        Component(id=c["id"], name=c["name"], status="ACTIVE", files=c.get("files", []))
        for c in components
    ]
    rels = [Relationship(type=r["type"], from_id=r["from"], to_id=r["to"]) for r in (relationships or [])]
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=comps),
        relationships=rels
    )


class TestDetectSystems:
    def test_returns_system_scores(self):
        manifest = _make_manifest([
            {"file": "api/users.py", "imports": ["models.user"], "functions": ["get_user"]},
            {"file": "models/user.py", "imports": [], "functions": ["User"]},
            {"file": "api/posts.py", "imports": ["models.post"], "functions": ["get_posts"]},
            {"file": "models/post.py", "imports": [], "functions": ["Post"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Users", "files": ["api/users.py", "models/user.py"]},
            {"id": "COMP-2", "name": "Posts", "files": ["api/posts.py", "models/post.py"]},
        ])
        results = detect_systems(model, manifest)
        assert len(results) >= 1
        assert all(isinstance(r, SystemScore) for r in results)
        assert all(0 <= r.independence <= 1.0 for r in results)

    def test_independent_modules_form_separate_systems(self):
        manifest = _make_manifest([
            {"file": "billing/charge.py", "imports": ["billing.models"], "functions": ["charge"]},
            {"file": "billing/models.py", "imports": [], "functions": ["Invoice"]},
            {"file": "notifications/email.py", "imports": ["notifications.templates"], "functions": ["send"]},
            {"file": "notifications/templates.py", "imports": [], "functions": ["render"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Billing", "files": ["billing/charge.py", "billing/models.py"]},
            {"id": "COMP-2", "name": "Notifications", "files": ["notifications/email.py", "notifications/templates.py"]},
        ])
        results = detect_systems(model, manifest)
        assert len(results) >= 2
        for r in results:
            assert r.independence > 0.5

    def test_tightly_coupled_single_system(self):
        manifest = _make_manifest([
            {"file": "core/engine.py", "imports": ["core.config", "core.state"], "functions": ["run"]},
            {"file": "core/config.py", "imports": ["core.state"], "functions": ["load"]},
            {"file": "core/state.py", "imports": ["core.engine"], "functions": ["save"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Engine", "files": ["core/engine.py"]},
            {"id": "COMP-2", "name": "Config", "files": ["core/config.py"]},
            {"id": "COMP-3", "name": "State", "files": ["core/state.py"]},
        ])
        results = detect_systems(model, manifest, target_systems=1)
        assert any(len(r.component_ids) == 3 for r in results)

    def test_data_affinity_signal(self):
        manifest = _make_manifest([
            {"file": "api/orders.py", "imports": ["models.order", "models.line_item"], "functions": ["create_order"]},
            {"file": "services/shipping.py", "imports": ["models.order", "models.address"], "functions": ["ship"]},
            {"file": "models/order.py", "imports": [], "functions": ["Order"]},
            {"file": "models/line_item.py", "imports": ["models.order"], "functions": ["LineItem"]},
            {"file": "models/address.py", "imports": [], "functions": ["Address"]},
            {"file": "unrelated/analytics.py", "imports": ["unrelated.math"], "functions": ["compute"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Orders", "files": ["api/orders.py", "models/order.py", "models/line_item.py"]},
            {"id": "COMP-2", "name": "Shipping", "files": ["services/shipping.py", "models/address.py"]},
            {"id": "COMP-3", "name": "Analytics", "files": ["unrelated/analytics.py"]},
        ])
        results = detect_systems(model, manifest)
        analytics_systems = [r for r in results if "COMP-3" in r.component_ids and len(r.component_ids) == 1]
        assert len(analytics_systems) >= 1

    def test_empty_model_returns_empty(self):
        manifest = _make_manifest([])
        model = _make_model([])
        results = detect_systems(model, manifest)
        assert results == []

    def test_single_component_returns_one_system(self):
        manifest = _make_manifest([{"file": "main.py", "imports": [], "functions": ["run"]}])
        model = _make_model([{"id": "COMP-1", "name": "Main", "files": ["main.py"]}])
        results = detect_systems(model, manifest)
        assert len(results) == 1
        assert results[0].component_ids == ["COMP-1"]
