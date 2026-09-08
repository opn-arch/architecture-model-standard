"""B3.2.3 — Determinism guard for pipeline_html renderer.

The OCA-side ``architect_artifact_rebuild`` tool ultimately funnels through
``materialize`` + ``pipeline_html.render``. We exercise that path twice
against identical inputs and require byte-identical output.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from architecture_model.lifecycle.model_slice import ModelSlice
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.renderers.pipeline_html import render


FIXTURE_PKG = Path("tests/fixtures/lifecycle/pipeline_dashboard_pkg")
FIXTURE_SLICE = Path("tests/fixtures/lifecycle/pipeline.slice.yaml")


def _prepare(tmp_path):
    shutil.copytree(FIXTURE_PKG, tmp_path / "pkg")
    pkg = load_package(tmp_path / "pkg")
    slice_dict = yaml.safe_load(FIXTURE_SLICE.read_text())
    return pkg, slice_dict


def test_pipeline_html_render_is_deterministic(tmp_path):
    """Render twice with identical inputs; require byte-identical HTML."""
    pkg, slice_dict = _prepare(tmp_path)

    ms1 = materialize(ModelSlice.model_validate(slice_dict), pkg)
    html1 = render(materialized_slice=ms1, sil_store=None)
    ms2 = materialize(ModelSlice.model_validate(slice_dict), pkg)
    html2 = render(materialized_slice=ms2, sil_store=None)

    assert html1 == html2
    assert html1.encode("utf-8") == html2.encode("utf-8")


def test_pipeline_html_data_stable_across_rebuilds(tmp_path):
    """The embedded JSON payload is stable across runs (order-sensitive)."""
    pkg, slice_dict = _prepare(tmp_path)

    def _payload():
        ms = materialize(ModelSlice.model_validate(slice_dict), pkg)
        html = render(materialized_slice=ms, sil_store=None)
        start = html.index('<script id="pipeline-state"')
        open_end = html.index(">", start) + 1
        close = html.index("</script>", open_end)
        return json.loads(html[open_end:close].strip())

    a, b = _payload(), _payload()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert [n["id"] for n in a["nodes"]] == [n["id"] for n in b["nodes"]]
    assert [(e["from"], e["to"], e["type"]) for e in a["edges"]] == [
        (e["from"], e["to"], e["type"]) for e in b["edges"]
    ]
