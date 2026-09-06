import pytest

playwright = pytest.importorskip("playwright.sync_api")


def test_dashboard_renders_and_drilldown_opens(tmp_path):
    """Materialize slice, render HTML, copy assets alongside, load in headless
    chromium, verify DOM contents, click a node, verify drill-down panel opens."""
    import shutil, yaml
    from pathlib import Path
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.model_slice import ModelSlice
    from architecture_model.lifecycle.model_slice_materializer import materialize
    from architecture_model.lifecycle.renderers.pipeline_html import render

    # 1. Materialize fixture slice
    fx = Path("tests/fixtures/lifecycle/pipeline_dashboard_pkg")
    shutil.copytree(fx, tmp_path / "pkg")
    pkg = load_package(tmp_path / "pkg")
    slice_dict = yaml.safe_load(Path("tests/fixtures/lifecycle/pipeline.slice.yaml").read_text())
    ms = materialize(ModelSlice.model_validate(slice_dict), pkg)

    # 2. Render HTML and write to tmp_path along with the static assets tree
    html = render(materialized_slice=ms, sil_store=None)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "pipeline.html").write_text(html)
    src_assets = Path("src/architecture_model/lifecycle/renderers/assets/pipeline_dashboard")
    dest_assets = out_dir / "assets" / "pipeline_dashboard"
    shutil.copytree(src_assets, dest_assets)

    # 3. Launch headless chromium, load pipeline.html via file://, verify DOM
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto((out_dir / "pipeline.html").as_uri())
            # Wait for the deferred badges.js to run
            page.wait_for_selector(".node-card", timeout=5000)

            # Every entity from the fixture should have a card
            expected_ids = {"CAP-INGEST", "CAP-RENDER", "COMP-COLLECTOR",
                             "COMP-BUILDER", "COMP-VIEWER", "CON-LATENCY"}
            card_ids = set(page.eval_on_selector_all(
                ".node-card",
                "els => els.map(e => e.getAttribute('data-node-id'))"))
            assert card_ids == expected_ids

            # Click one node; drill-down panel becomes visible
            page.click(f'.node-card[data-node-id="COMP-COLLECTOR"]')
            page.wait_for_selector("#pipeline-drilldown:not([hidden])", timeout=2000)
            panel_text = page.text_content("#pipeline-drilldown")
            assert "COMP-COLLECTOR" in panel_text
        finally:
            browser.close()
