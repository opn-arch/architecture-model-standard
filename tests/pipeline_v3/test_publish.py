"""Tests for pipeline_v3.publish — T0.14 Phase 6.7.

publish.py serializes a ContainerizedModel to v3 YAML and writes it to
disk. Two entry points:

    serialize_model(model, ...) -> str      # pure, no I/O
    publish_model(model, out_path, ...) -> PublishResult   # writes file

YAML shape mirrors the Phase 2 v3-poc migration output: meta block with
schema_version 3.0, entities.components (each carrying id, name,
root_prefix, module_names, promises), and top-level relationships.

Determinism: writes stable ordering (components sorted by id, promises
sorted by attribute+id, relationships sorted by (from, to)). Respects
AMS_DETERMINISTIC_NOW env var for reproducible timestamps.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from architecture_model.pipeline_v3.cluster import cluster_modules
from architecture_model.pipeline_v3.containerize import containerize
from architecture_model.pipeline_v3.derive_promises import derive_promises
from architecture_model.pipeline_v3.link import link_clusters
from architecture_model.pipeline_v3.publish import (
    PublishResult,
    publish_model,
    serialize_model,
)
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult


_SENTINEL = object()


def _mod(
    name: str,
    docstring: str | None = "d",
    functions=_SENTINEL,
    imports: list[str] | None = None,
) -> ScannedModule:
    if functions is _SENTINEL:
        functions = [{"name": "f"}]
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring=docstring,
        functions=functions,
        classes=[],
        imports=imports or [],
        line_count=1,
    )


def _model(*modules: ScannedModule, depth: int = 2):
    scan = ScanResult(source_root=Path("/tmp"), modules=list(modules))
    clusters = cluster_modules(scan, depth=depth)
    ps = derive_promises(scan)
    links = link_clusters(clusters)
    return containerize(clusters, ps, links)


# ---------------------------------------------------------------------------
# serialize_model
# ---------------------------------------------------------------------------


def test_serialize_returns_yaml_string():
    model = _model(_mod("a.b.x"))
    text = serialize_model(model)
    assert isinstance(text, str)
    doc = yaml.safe_load(text)
    assert isinstance(doc, dict)


def test_serialize_has_v3_schema_version():
    model = _model(_mod("a.b.x"))
    doc = yaml.safe_load(serialize_model(model))
    assert doc["meta"]["schema_version"] == "3.0"


def test_serialize_stamps_generator():
    model = _model(_mod("a.b.x"))
    doc = yaml.safe_load(serialize_model(model))
    assert doc["meta"]["generated_by"] == "pipeline_v3"


def test_serialize_respects_project_name():
    model = _model(_mod("a.b.x"))
    doc = yaml.safe_load(serialize_model(model, project_name="my-proj"))
    assert doc["meta"]["project"] == "my-proj"


def test_serialize_includes_all_components():
    model = _model(_mod("a.b.x"), _mod("a.c.y"))
    doc = yaml.safe_load(serialize_model(model))
    comps = doc["entities"]["components"]
    assert len(comps) == len(model.components)
    assert {c["id"] for c in comps} == {c.id for c in model.components}


def test_serialize_component_carries_promises():
    model = _model(_mod("a.b.x", docstring="hi"))
    doc = yaml.safe_load(serialize_model(model))
    comp = doc["entities"]["components"][0]
    assert "promises" in comp
    assert len(comp["promises"]) == len(model.components[0].promises)
    # each promise dict has core fields
    p0 = comp["promises"][0]
    assert set(p0) >= {"id", "attribute", "content", "owner_entity", "status"}


def test_serialize_promise_owner_matches_component_id():
    model = _model(_mod("a.b.x", docstring="hi"))
    doc = yaml.safe_load(serialize_model(model))
    comp = doc["entities"]["components"][0]
    for p in comp["promises"]:
        assert p["owner_entity"] == comp["id"]


def test_serialize_includes_relationships_block():
    model = _model(
        _mod("a.b.x", imports=["a.c.y"]),
        _mod("a.c.y"),
    )
    doc = yaml.safe_load(serialize_model(model))
    rels = doc["relationships"]
    assert len(rels) == 1
    r = rels[0]
    assert r["type"] == "depends-on"
    assert r["from"] and r["to"] and "weight" in r


def test_serialize_is_deterministic_with_pinned_now(monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-09-14T00:00:00Z")
    model = _model(_mod("a.b.x"))
    a = serialize_model(model)
    b = serialize_model(model)
    assert a == b
    doc = yaml.safe_load(a)
    assert doc["meta"]["generated_at"] == "2026-09-14T00:00:00Z"


def test_serialize_ordering_is_stable():
    """Components sorted by id, promises sorted by (attribute, id),
    relationships sorted by (from, to)."""
    model = _model(_mod("z.q.m"), _mod("a.b.n"), _mod("m.p.o"))
    doc = yaml.safe_load(serialize_model(model))
    comp_ids = [c["id"] for c in doc["entities"]["components"]]
    assert comp_ids == sorted(comp_ids)


def test_serialize_empty_model_produces_valid_yaml():
    doc = yaml.safe_load(serialize_model(_model()))
    assert doc["entities"]["components"] == []
    assert doc["relationships"] == []


def test_serialize_source_root_captured_when_provided():
    model = _model(_mod("a.b.x"))
    doc = yaml.safe_load(serialize_model(model, source_root=Path("/tmp/some/repo")))
    assert doc["meta"]["source_root"] == "/tmp/some/repo"


# ---------------------------------------------------------------------------
# publish_model — I/O
# ---------------------------------------------------------------------------


def test_publish_writes_file_and_returns_result(tmp_path):
    model = _model(_mod("a.b.x"))
    out = tmp_path / "arch.yaml"
    result = publish_model(model, out, project_name="p")
    assert isinstance(result, PublishResult)
    assert result.model_path == out
    assert out.exists()
    doc = yaml.safe_load(out.read_text())
    assert doc["meta"]["project"] == "p"


def test_publish_result_carries_yaml_text(tmp_path):
    model = _model(_mod("a.b.x"))
    out = tmp_path / "arch.yaml"
    result = publish_model(model, out)
    assert result.model_yaml == out.read_text()


def test_publish_creates_parent_directories(tmp_path):
    model = _model(_mod("a.b.x"))
    out = tmp_path / "deep" / "nested" / "arch.yaml"
    publish_model(model, out)
    assert out.exists()


def test_publish_overwrites_existing_file(tmp_path):
    model = _model(_mod("a.b.x"))
    out = tmp_path / "arch.yaml"
    out.write_text("stale content")
    publish_model(model, out)
    assert "stale content" not in out.read_text()
    assert "schema_version" in out.read_text()


# ---------------------------------------------------------------------------
# R9: behavior promises emitted in YAML
# ---------------------------------------------------------------------------


def test_serialize_behavior_carries_promises_list():
    """Each behavior dict in serialized YAML carries a promises list
    with at least one intent promise (from R9 emission)."""
    from architecture_model.pipeline_v3.derive_behaviors import derive_behaviors

    m = _mod(
        "a.b.x",
        docstring="mod",
        functions=[{"name": "scan_repo", "docstring": "Scan a repository."}],
    )
    scan = ScanResult(source_root=Path("/tmp"), modules=[m])
    clusters = cluster_modules(scan, depth=2)
    ps = derive_promises(scan)
    links = link_clusters(clusters)
    behaviors = derive_behaviors(scan)
    model = containerize(clusters, ps, links, behaviors=behaviors)

    text = serialize_model(model)
    data = yaml.safe_load(text)
    behs = data["entities"]["behaviors"]
    assert len(behs) == 1
    assert "promises" in behs[0]
    intents = [p for p in behs[0]["promises"] if p["attribute"] == "intent"]
    assert len(intents) == 1
    assert intents[0]["content"] == "Scan a repository."
