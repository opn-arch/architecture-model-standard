def test_pipeline_html_renderer_registered():
    from architecture_model.lifecycle.renderers import DEFAULT_RENDERERS
    assert "pipeline-html" in DEFAULT_RENDERERS


def test_pipeline_html_renderer_emits_shell(tmp_path):
    """Render on the B3.1.1 fixture; assert HTML shell contains a
    <script id="pipeline-state" type="application/json"> block with the
    builder JSON, and <link>/<script> tags referencing the 3 static assets
    (which don't need to exist yet — B3.2.1 ships them)."""
    import shutil, yaml, json
    from pathlib import Path
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.model_slice import ModelSlice
    from architecture_model.lifecycle.model_slice_materializer import materialize
    from architecture_model.lifecycle.renderers.pipeline_html import render

    fx = Path("tests/fixtures/lifecycle/pipeline_dashboard_pkg")
    shutil.copytree(fx, tmp_path / "pkg")
    pkg = load_package(tmp_path / "pkg")
    slice_dict = yaml.safe_load(Path("tests/fixtures/lifecycle/pipeline.slice.yaml").read_text())
    ms = materialize(ModelSlice.model_validate(slice_dict), pkg)

    html = render(materialized_slice=ms, sil_store=None)

    assert isinstance(html, str)
    assert "<script id=\"pipeline-state\"" in html
    # The JSON payload must be parseable
    start = html.index("<script id=\"pipeline-state\"")
    open_tag_end = html.index(">", start) + 1
    close = html.index("</script>", open_tag_end)
    payload = json.loads(html[open_tag_end:close].strip())
    assert "nodes" in payload and "edges" in payload and "badges" in payload

    for asset in ("index.css", "drilldown.js", "badges.js"):
        assert asset in html


def test_pipeline_html_renderer_returns_bytes_and_content_type():
    """The renderer's public contract exposes bytes + content-type for the
    lifecycle rebuild pipeline. Content type should be text/html; charset=utf-8."""
    from architecture_model.lifecycle.renderers.pipeline_html import CONTENT_TYPE, render
    assert CONTENT_TYPE == "text/html; charset=utf-8"
