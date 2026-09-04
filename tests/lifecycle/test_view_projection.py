"""Tests for the ViewSpec projector registry (T16)."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.model_slice import Curation, ModelSlice, Selectors
from architecture_model.lifecycle.model_slice_materializer import (
    MaterializationWarning,
    MaterializedSlice,
    materialize,
)
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.view_projection import (
    DEFAULT_REGISTRY,
    ProjectedView,
    ProjectorNotFound,
    ProjectorRegistry,
    SliceMismatch,
    project,
)
from architecture_model.lifecycle.view_spec import SliceRef, ViewSpec


ROOT_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: root
    entities:
      capabilities:
        - id: CAP-1
          name: Cap One
          status: ACTIVE
          source_block: F1
      components:
        - id: COMP-A
          name: Alpha
          status: ACTIVE
          layer: core
          source_block: F1
      layers:
        - id: core
          name: Core Layer
          status: ACTIVE
    relationships:
      - from: COMP-A
        to: CAP-1
        type: realizes
    """
)

ROOT_PKG_YAML = dedent(
    """\
    architecture_id: root-pkg
    name: Root
    slug: root-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)


@pytest.fixture
def pkg(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(ROOT_PKG_YAML)
    (root / ".architecture-model.yaml").write_text(ROOT_MODEL)
    (root / "manifest.json").write_text("{}")
    return load_package(root)


@pytest.fixture
def mslice(pkg) -> MaterializedSlice:
    s = ModelSlice(
        id="s1",
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-A", "CAP-1"]),
        curation=Curation(),
        parameters={},
    )
    return materialize(s, pkg)


def _view(*, slice_id="s1", model_revision="rev-1", projector="stub", config=None) -> ViewSpec:
    return ViewSpec(
        id="v1",
        slice_ref=SliceRef(slice_id=slice_id, model_revision=model_revision),
        projector=projector,
        projector_config=config or {},
        output_content_kind="diagram",
    )


def _stub_spec() -> DiagramSpec:
    return DiagramSpec(id="stub", title="Stub")


# --- ProjectorRegistry ---------------------------------------------------


def test_registry_register_and_get():
    reg = ProjectorRegistry()
    fn = lambda frag, cfg: _stub_spec()
    reg.register("p", fn, version="2.0.0")
    got_fn, got_version = reg.get("p")
    assert got_fn is fn
    assert got_version == "2.0.0"


def test_registry_default_version():
    reg = ProjectorRegistry()
    reg.register("p", lambda f, c: _stub_spec())
    _, version = reg.get("p")
    assert version == "1.0.0"


def test_registry_names_sorted():
    reg = ProjectorRegistry()
    reg.register("b", lambda f, c: _stub_spec())
    reg.register("a", lambda f, c: _stub_spec())
    assert reg.names() == ("a", "b")


def test_registry_contains():
    reg = ProjectorRegistry()
    reg.register("p", lambda f, c: _stub_spec())
    assert "p" in reg
    assert "q" not in reg


def test_registry_unregister():
    reg = ProjectorRegistry()
    reg.register("p", lambda f, c: _stub_spec())
    reg.unregister("p")
    assert "p" not in reg


def test_registry_get_missing_raises_projector_not_found():
    reg = ProjectorRegistry()
    with pytest.raises(ProjectorNotFound):
        reg.get("nope")


def test_projector_not_found_is_key_error():
    assert issubclass(ProjectorNotFound, KeyError)


def test_slice_mismatch_is_value_error():
    assert issubclass(SliceMismatch, ValueError)


# --- project() -----------------------------------------------------------


def test_project_returns_projected_view_with_stub(mslice):
    reg = ProjectorRegistry()
    spec = _stub_spec()
    reg.register("stub", lambda frag, cfg: spec, version="1.2.3")
    view = _view(projector="stub")
    result = project(view, mslice, registry=reg)
    assert isinstance(result, ProjectedView)
    assert result.view_id == "v1"
    assert result.slice_id == "s1"
    assert result.model_revision == "rev-1"
    assert result.diagram_spec is spec
    assert result.provenance["projector"] == "stub"
    assert result.provenance["projector_version"] == "1.2.3"
    assert result.provenance["slice_digest"] == "rev-1"
    # RFC3339 UTC Z
    assert result.provenance["produced_at"].endswith("Z")


def test_project_uses_default_registry_when_none(mslice):
    view = _view(projector="se.conops")
    result = project(view, mslice)
    assert isinstance(result.diagram_spec, DiagramSpec)


def test_project_missing_projector_raises(mslice):
    reg = ProjectorRegistry()
    view = _view(projector="missing")
    with pytest.raises(ProjectorNotFound):
        project(view, mslice, registry=reg)


def test_project_slice_id_mismatch_raises(mslice):
    reg = ProjectorRegistry()
    reg.register("stub", lambda f, c: _stub_spec())
    view = _view(slice_id="other", projector="stub")
    with pytest.raises(SliceMismatch):
        project(view, mslice, registry=reg)


def test_project_model_revision_mismatch_raises(mslice):
    reg = ProjectorRegistry()
    reg.register("stub", lambda f, c: _stub_spec())
    view = _view(model_revision="rev-other", projector="stub")
    with pytest.raises(SliceMismatch):
        project(view, mslice, registry=reg)


def test_project_bad_return_type_raises(mslice):
    reg = ProjectorRegistry()
    reg.register("bad", lambda f, c: {"not": "a spec"})
    view = _view(projector="bad")
    with pytest.raises(TypeError):
        project(view, mslice, registry=reg)


def test_project_propagates_warnings(pkg):
    s = ModelSlice(
        id="s1",
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-A"]),
        curation=Curation(),
        parameters={},
    )
    mat = materialize(s, pkg)
    # Force a synthetic warning to test pass-through
    mat = MaterializedSlice(
        slice_id=mat.slice_id,
        architecture_id=mat.architecture_id,
        model_revision=mat.model_revision,
        model_fragment=mat.model_fragment,
        stub_entity_ids=mat.stub_entity_ids,
        provenance=mat.provenance,
        warnings=(MaterializationWarning(code="SLICE.DANGLING_STRIPPED", message="danglers gone", entity_id="X"),),
    )
    reg = ProjectorRegistry()
    reg.register("stub", lambda f, c: _stub_spec())
    result = project(_view(projector="stub"), mat, registry=reg)
    assert result.warnings and "SLICE.DANGLING_STRIPPED" in result.warnings[0]
    assert "danglers gone" in result.warnings[0]


def test_project_config_is_shallow_copied(mslice):
    reg = ProjectorRegistry()

    def mutator(frag, cfg):
        cfg["injected"] = True
        return _stub_spec()

    reg.register("mut", mutator)
    original = {"a": 1}
    view = _view(projector="mut", config=original)
    project(view, mslice, registry=reg)
    # ViewSpec is frozen; check the ViewSpec's dict is untouched
    assert view.projector_config == {"a": 1}
    assert "injected" not in view.projector_config


def test_project_determinism(mslice):
    reg = ProjectorRegistry()
    reg.register("stub", lambda f, c: DiagramSpec(id="s", title="T"))
    view = _view(projector="stub")
    r1 = project(view, mslice, registry=reg)
    r2 = project(view, mslice, registry=reg)
    assert r1.diagram_spec.to_dict() == r2.diagram_spec.to_dict()
    # Provenance modulo produced_at
    p1 = {k: v for k, v in r1.provenance.items() if k != "produced_at"}
    p2 = {k: v for k, v in r2.provenance.items() if k != "produced_at"}
    assert p1 == p2


# --- DEFAULT_REGISTRY seeded SE projectors -------------------------------


def test_default_registry_has_four_se_projectors():
    names = DEFAULT_REGISTRY.names()
    for expected in ("se.conops", "se.functional", "se.logical", "se.use_cases"):
        assert expected in names


@pytest.mark.parametrize("name", ["se.conops", "se.functional", "se.logical", "se.use_cases"])
def test_default_se_adapter_returns_diagram_spec(mslice, name):
    view = _view(projector=name)
    result = project(view, mslice)
    assert isinstance(result.diagram_spec, DiagramSpec)
    _, ver = DEFAULT_REGISTRY.get(name)
    assert ver == "1.0.0"
