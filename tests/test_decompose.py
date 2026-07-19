"""Tests for model decomposition via relationship tracing."""
import json
import textwrap
from pathlib import Path

import yaml

from architecture_model.core.types import (
    ArchitectureModel, Behavior, Capability, Component, ComponentKind,
    Constraint, ConstraintType, Entities, Interface, InterfaceType,
    ModelMeta, Relationship, RelationType, Status,
)
from architecture_model.core.parser import save_model
from architecture_model.decompose import decompose_model, write_sub_models


def _setup_project(tmp_path):
    """Create a project with parent model that has all entity types + relationships.

    Uses src-layout so discover_config() finds source_root=src/myproject
    and creates F1 for the 'core' subpackage.
    """
    # Source files
    pkg_root = tmp_path / "src" / "myproject"
    pkg_root.mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("")

    pkg = pkg_root / "core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "parser.py").write_text(textwrap.dedent('''
        """Parser module."""
        def parse(data: str) -> dict:
            """Parse input data."""
            return {"raw": data}
    '''))
    (pkg / "validator.py").write_text(textwrap.dedent('''
        """Validator module."""
        def check(model: dict) -> list:
            """Run checks."""
            return []
    '''))

    # Parent model with ALL entity types and rich relationships
    model = ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test", generated_at="2026-01-01"),
        entities=Entities(
            components=[
                Component(id="COMP-CORE", name="Core", status=Status.ACTIVE,
                          kind=ComponentKind.PACKAGE, f_block="F1"),
                Component(id="COMP-CORE-PARSER", name="Parser", status=Status.ACTIVE,
                          files=["src/myproject/core/parser.py"],
                          kind=ComponentKind.MODULE, f_block="F1"),
                Component(id="COMP-CORE-VALIDATOR", name="Validator", status=Status.ACTIVE,
                          files=["src/myproject/core/validator.py"],
                          kind=ComponentKind.MODULE, f_block="F1"),
                Component(id="COMP-EXTERNAL", name="External", status=Status.ACTIVE,
                          files=["src/myproject/external.py"],
                          kind=ComponentKind.MODULE, f_block="F2"),
            ],
            capabilities=[
                Capability(id="CAP-PARSE", name="Parsing", status=Status.ACTIVE,
                           f_block="F1", description="Parse data"),
            ],
            interfaces=[
                Interface(id="IF-PARSE-API", name="Parser API", status=Status.ACTIVE,
                          type=InterfaceType.INTERNAL),
            ],
            behaviors=[
                Behavior(id="BEH-VALIDATE", name="Validation Flow", status=Status.ACTIVE),
            ],
            constraints=[
                Constraint(id="CON-SCHEMA", name="Schema Conformance",
                           status=Status.ACTIVE, type=ConstraintType.TECHNOLOGY),
            ],
        ),
        relationships=[
            # Internal structure
            Relationship(type=RelationType.CONTAINS, from_id="COMP-CORE", to_id="COMP-CORE-PARSER"),
            Relationship(type=RelationType.CONTAINS, from_id="COMP-CORE", to_id="COMP-CORE-VALIDATOR"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-CORE-VALIDATOR", to_id="COMP-CORE-PARSER"),
            # Entity connections (what decompose should trace)
            Relationship(type=RelationType.REALIZES, from_id="COMP-CORE", to_id="CAP-PARSE"),
            Relationship(type=RelationType.EXPOSES, from_id="COMP-CORE-PARSER", to_id="IF-PARSE-API"),
            Relationship(type=RelationType.TRACES_TO, from_id="COMP-CORE-VALIDATOR", to_id="BEH-VALIDATE"),
            Relationship(type=RelationType.CONSTRAINED_BY, from_id="COMP-CORE", to_id="CON-SCHEMA"),
            # Boundary dependency
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-CORE", to_id="COMP-EXTERNAL"),
        ],
    )
    save_model(model, tmp_path / ".architecture-model.yaml")

    block_id = "F1"
    return tmp_path, block_id


def test_decompose_traces_capabilities(tmp_path):
    """Decompose pulls in parent capabilities via realizes relationships."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    cap_ids = {c.id for c in sub.entities.capabilities}
    assert "CAP-PARSE" in cap_ids, f"Should trace CAP-PARSE via realizes. Got: {cap_ids}"


def test_decompose_traces_interfaces(tmp_path):
    """Decompose pulls in parent interfaces via exposes relationships."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    iface_ids = {i.id for i in sub.entities.interfaces}
    assert "IF-PARSE-API" in iface_ids, f"Should trace IF-PARSE-API via exposes. Got: {iface_ids}"


def test_decompose_traces_behaviors(tmp_path):
    """Decompose pulls in parent behaviors via traces-to relationships."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    beh_ids = {b.id for b in sub.entities.behaviors}
    assert "BEH-VALIDATE" in beh_ids, f"Should trace BEH-VALIDATE via traces-to. Got: {beh_ids}"


def test_decompose_traces_constraints(tmp_path):
    """Decompose pulls in parent constraints via constrained-by relationships."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    con_ids = {c.id for c in sub.entities.constraints}
    assert "CON-SCHEMA" in con_ids, f"Should trace CON-SCHEMA via constrained-by. Got: {con_ids}"


def test_decompose_includes_parent_component(tmp_path):
    """Decompose includes the parent component (COMP-CORE) in the sub-model."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    comp_ids = {c.id for c in sub.entities.components}
    assert "COMP-CORE" in comp_ids, f"Should include parent component. Got: {comp_ids}"
    assert "COMP-CORE-PARSER" in comp_ids
    assert "COMP-CORE-VALIDATOR" in comp_ids


def test_decompose_includes_boundary_deps(tmp_path):
    """Decompose includes cross-block depends-on as boundary relationships."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    dep_rels = [r for r in sub.relationships if r.type == RelationType.DEPENDS_ON]
    boundary = [r for r in dep_rels if r.to_id == "COMP-EXTERNAL"]
    assert len(boundary) >= 1, f"Should include boundary dep to COMP-EXTERNAL. Got deps: {[(r.from_id, r.to_id) for r in dep_rels]}"


def test_decompose_includes_internal_relationships(tmp_path):
    """Decompose includes all internal relationships (contains, realizes, exposes, etc.)."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    rel_types = {r.type for r in sub.relationships}
    assert RelationType.CONTAINS in rel_types, "Should include contains"
    assert RelationType.REALIZES in rel_types, "Should include realizes"
    assert RelationType.EXPOSES in rel_types, "Should include exposes"
    assert RelationType.CONSTRAINED_BY in rel_types, "Should include constrained-by"


def test_decompose_excludes_external_components(tmp_path):
    """Decompose should NOT include COMP-EXTERNAL in the sub-model's components."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    comp_ids = {c.id for c in sub.entities.components}
    assert "COMP-EXTERNAL" not in comp_ids, "External components should not be in sub-model"


def test_decompose_meta_links_to_parent(tmp_path):
    """Sub-model meta has parent_model and refines_component."""
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    assert sub.meta.parent_model == "../../.architecture-model.yaml"
    assert sub.meta.refines_component == "COMP-CORE"


def test_write_sub_models(tmp_path):
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    out_dir = tmp_path / ".architecture-models"
    written = write_sub_models(results, out_dir)
    assert len(written) >= 1
    assert (out_dir / block_id / ".architecture-model.yaml").exists()
    data = yaml.safe_load((out_dir / block_id / ".architecture-model.yaml").read_text())
    assert data["meta"]["parent_model"] == "../../.architecture-model.yaml"
    assert "entities" in data
    # Verify traced entities are in YAML
    assert len(data["entities"].get("capabilities", [])) >= 1
    assert len(data["entities"].get("interfaces", [])) >= 1
    assert len(data["entities"].get("behaviors", [])) >= 1
    assert len(data["entities"].get("constraints", [])) >= 1


def test_decompose_cli(tmp_path):
    """Test the CLI decompose command end-to-end."""
    from architecture_model.cli.main import main

    root, block_id = _setup_project(tmp_path)
    out_dir = tmp_path / ".architecture-models"
    ret = main(["decompose", str(root), "-o", str(out_dir)])
    assert ret == 0
    assert (out_dir / block_id / ".architecture-model.yaml").exists()
