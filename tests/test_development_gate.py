"""Tests for the development gate."""

from architecture_model.authoring.gate import check_development_gate, GateResult
from architecture_model.core.types import (
    ArchitectureModel,
    Capability,
    Component,
    Constraint,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)
from architecture_model.manifest.types import (
    Manifest,
    MetricsResult,
    ModuleInfo,
    ModuleStatus,
    ScanReport,
)


def _make_model(phase="production", capabilities=0, components=0, constraints=0, realize=False, allocate=False, files=None):
    caps = [Capability(id=f"CAP-{i+1}", name=f"Cap {i+1}", status=Status.ACTIVE) for i in range(capabilities)]
    cons = [Constraint(id=f"CON-{i+1}", name=f"Con {i+1}", status=Status.ACTIVE) for i in range(constraints)]
    comps = [Component(id=f"COMP-{i+1}", name=f"Comp {i+1}", status=Status.ACTIVE, files=files or []) for i in range(components)]
    rels = []
    if realize:
        for cap in caps:
            rels.append(Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id=cap.id))
    if allocate:
        for con in cons:
            rels.append(Relationship(type=RelationType.ALLOCATED_TO, from_id=con.id, to_id="COMP-1"))
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(capabilities=caps, constraints=cons, components=comps),
        relationships=rels,
    )


def _make_manifest(modules=0, filenames=None):
    if filenames is None:
        filenames = [f"mod_{i}.py" for i in range(modules)]
    mods = [
        ModuleInfo(file=f, name=f.replace(".py", ""), docstring=None, functions=[], imports=[], line_count=10, status=ModuleStatus.ACTIVE, classes=[])
        for f in filenames
    ]
    return Manifest(
        generated_at="2024-01-01",
        project_root="/tmp",
        metrics=MetricsResult(),
        functional_blocks={},
        modules=mods,
        interfaces=[],
    )


def test_concept_phase_is_lenient():
    model = _make_model(phase="concept", capabilities=3, components=0)
    manifest = _make_manifest(modules=10)
    result = check_development_gate(model, manifest, phase="concept")
    assert result.phase_requirements_met is True


def test_production_phase_is_strict():
    model = _make_model(phase="production", capabilities=3, components=1)
    manifest = _make_manifest(modules=10)
    result = check_development_gate(model, manifest, phase="production")
    assert result.phase_requirements_met is False
    assert len(result.issues) > 0


def test_production_all_passing():
    files = ["a.py", "b.py"]
    model = _make_model(capabilities=1, components=1, constraints=1, realize=True, allocate=True, files=files)
    manifest = _make_manifest(filenames=files)
    result = check_development_gate(model, manifest, phase="production")
    assert result.phase_requirements_met is True
    assert result.file_coverage == 100.0


def test_concept_no_entities_fails():
    model = _make_model(phase="concept", capabilities=0, components=0)
    manifest = _make_manifest(modules=5)
    result = check_development_gate(model, manifest, phase="concept")
    assert result.phase_requirements_met is False
