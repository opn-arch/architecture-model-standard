def test_all_assets_exist_and_have_content():
    from pathlib import Path
    root = Path("src/architecture_model/lifecycle/renderers/assets/pipeline_dashboard")
    for f in ("index.css", "drilldown.js", "badges.js"):
        p = root / f
        assert p.exists(), f"missing asset: {f}"
        assert p.stat().st_size > 100, f"asset too small: {f}"


def test_html_shell_references_all_assets(tmp_path):
    """Render minimal HTML; verify all three asset filenames appear."""
    import shutil, yaml
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
    for f in ("index.css", "drilldown.js", "badges.js"):
        assert f in html
