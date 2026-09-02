from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_all_diagrams, generate_html_viewer


def _write_model(root: Path) -> Path:
    path = root / ".architecture-model.yaml"
    path.write_text(
        """meta:
  project: curated-viewer
  schema_version: '2.0'
entities:
  actors:
    - {id: ACT-1, name: Operator, status: ACTIVE}
  capabilities:
    - {id: CAP-1, name: Operate, status: ACTIVE}
  components:
    - {id: COMP-1, name: Controller, status: ACTIVE}
  behaviors:
    - {id: BEH-1, name: Run operation, status: ACTIVE, actor_id: ACT-1}
  requirements:
    - {id: REQ-1, name: Reliable operation, status: ACTIVE}
relationships:
  - {from_id: COMP-1, to_id: CAP-1, type: realizes}
  - {from_id: BEH-1, to_id: CAP-1, type: realizes}
""",
        encoding="utf-8",
    )
    return path


def _viewer_data(html: str) -> dict:
    match = re.search(r'<script id="viewer-data" type="application/json">(.*?)</script>', html, re.S)
    assert match
    return json.loads(match.group(1))


def test_viewer_embeds_four_native_specs_panels_and_drilldowns(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    output = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path)
    html = output.read_text(encoding="utf-8")
    data = _viewer_data(html)

    assert [(key, data["se_views"][key]["label"]) for key in ("conops", "functional", "logical", "use-cases")] == [
        ("conops", "ConOps"),
        ("functional", "Functional Architecture"),
        ("logical", "Logical Architecture"),
        ("use-cases", "Use Cases"),
    ]
    for key in ("conops", "functional", "logical", "use-cases"):
        view = data["se_views"][key]
        assert view["renderer"] == "native"
        assert view["spec"]["id"]
        assert "<svg" in view["panel"]["svg"]
        ET.fromstring(view["panel"]["svg"])
        assert "mermaid" not in view
        assert view["curation"]["status"] in {"auto", "curated", "partial"}
    assert data["se_views"]["icd"]["renderer"] == "mermaid"
    assert "Behavior Model" not in html
    assert "https://" not in html and "http://" not in html.replace("http://www.w3.org/2000/svg", "")


def test_viewer_contains_accessible_navigation_facets_comments_and_zoom(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    html = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text(encoding="utf-8")

    assert "data-drilldown-ref" in html
    assert "data-entity-ref" in html
    assert "showCuratedDrilldown" in html
    assert "[['zoom-in','Zoom in'],['zoom-out','Zoom out'],['fit','Fit diagram'],['reset','Reset diagram']]" in html
    assert "pointerdown" in html and "touch-action" in html
    assert "ev.key === 'Enter' || ev.key === ' '" in html
    assert "view:' + viewKey + ':' + specId" in html
    assert "view:.+" in html
    assert "data-facet" in html and "updateDiagramVisibility" in html
    assert "data-legend-facet" in html
    assert "@media print" in html
    assert "onclick=" not in html.lower()


def test_hostile_and_invalid_curation_falls_back_without_script_breakout(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    curation = tmp_path / ".architecture" / "viewer-curation.yaml"
    curation.parent.mkdir()
    curation.write_text(
        """version: 1
views:
  conops:
    labels:
      root::CAP-1: "</script><script>alert(1)</script>"
  functional:
    featured: [{qualified_id: root::MISSING}]
""",
        encoding="utf-8",
    )

    html = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text(encoding="utf-8")
    data = _viewer_data(html)

    assert "</script><script>alert(1)</script>" not in html
    assert data["se_views"]["conops"]["curation"]["status"] == "partial"
    assert data["se_views"]["functional"]["curation"]["status"] == "partial"
    assert any(item["code"].startswith("CURATION_") for item in data["se_views"]["conops"]["warnings"])


def test_hierarchical_duplicate_ids_remain_qualified(tmp_path: Path) -> None:
    root_path = _write_model(tmp_path)
    subdir = tmp_path / ".architecture-models" / "child"
    subdir.mkdir(parents=True)
    root_path.write_text(root_path.read_text().replace("  actors:", "  systems:\n    - {id: SYS-1, name: Child, status: ACTIVE, sub_model_ref: .architecture-models/child/.architecture-model.yaml}\n  actors:"))
    (subdir / ".architecture-model.yaml").write_text(
        """meta: {project: child, schema_version: '2.0'}
entities:
  components:
    - {id: COMP-1, name: Child Controller, status: ACTIVE}
""",
        encoding="utf-8",
    )
    model = load_model(root_path)
    data = _viewer_data(generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text())
    def entity_refs(spec: dict) -> set[str]:
        refs = {node.get("entity_ref") for node in spec["nodes"]}
        for drilldown in spec.get("drilldowns", []):
            if drilldown.get("spec"):
                refs.update(entity_refs(drilldown["spec"]))
        return refs

    refs = set().union(*(entity_refs(view["spec"]) for view in data["se_views"].values() if view.get("spec")))
    assert "root::COMP-1" in refs
    assert "child::COMP-1" in refs


def test_generate_all_diagrams_preserves_mmd_and_adds_native_svg(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    paths = generate_all_diagrams(model, tmp_path / "diagrams", repo_path=tmp_path)

    assert paths["context"].suffix == ".mmd"
    for name in ("conops", "functional-architecture", "logical-architecture", "use-cases"):
        assert paths[name].suffix == ".svg"
        ET.parse(paths[name])


def test_generated_javascript_parses_with_node(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    html = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)
    script = next(value for value in scripts if "var D = JSON.parse" in value)
    js = tmp_path / "viewer.js"
    js.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_drilldown_entity_back_restores_exact_drilldown_then_overview(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    html = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    data = _viewer_data(html)
    data["pipeline_history"] = [{"run_id": "run-1", "started_at": "now", "status": "complete", "stages": []}]
    script = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)[1]
    view_key, drilldown_id = next(
        (key, next(iter(view["panel"]["drilldowns"])))
        for key, view in data["se_views"].items() if view.get("panel", {}).get("drilldowns")
    )
    entity_ref = next(
        node["entity_ref"] for node in data["se_views"][view_key]["spec"]["nodes"]
        if node.get("drilldown_ref") == drilldown_id and node.get("entity_ref")
    )
    harness = f"""
const vm = require('vm');
const noop = () => {{}};
const classList = {{add:noop, remove:noop, toggle:noop, contains:()=>false}};
const element = {{dataset:{{}}, style:{{}}, classList, value:'', textContent:'', innerHTML:'',
  addEventListener:noop, querySelectorAll:()=>[], querySelector:()=>null, setAttribute:noop}};
const content = Object.assign({{}}, element, {{dataset:{{}}, querySelector:()=>null}});
const dataElement = Object.assign({{}}, element, {{textContent:{json.dumps(json.dumps(data))}}});
const document = {{getElementById:id=>id==='viewer-data'?dataElement:id==='content'?content:element,
  querySelectorAll:()=>[], querySelector:()=>Object.assign({{}},element), createElement:()=>Object.assign({{}},element)}};
const context = {{console, document, Blob, URL, alert:noop, MutationObserver:function(){{this.observe=noop}},
  localStorage:{{getItem:()=>null,setItem:noop,length:0,key:()=>null}}, innerWidth:1200,
  atob,btoa,escape,unescape,encodeURIComponent,decodeURIComponent}};
context.window=context; vm.createContext(context); vm.runInContext({json.dumps(script)}, context);
context.wireNativePanel=noop;
context.showView({json.dumps(view_key)}, false);
context.showCuratedDrilldown({json.dumps(view_key)}, {json.dumps(drilldown_id)}, {json.dumps(entity_ref)});
context.showEntity(context.resolveNativeEntity({json.dumps(entity_ref)}));
context.goBack();
if (content.dataset.currentType !== 'drilldown' || content.dataset.currentViewId !== {json.dumps(view_key)} || content.dataset.currentSpecId !== {json.dumps(drilldown_id)}) throw new Error('did not restore exact drilldown: '+JSON.stringify(content.dataset));
context.goBack();
if (content.dataset.currentType !== 'view' || content.dataset.currentId !== {json.dumps(view_key)}) throw new Error('did not restore overview: '+JSON.stringify(content.dataset));
context.navHistory.push({{type:'history', id:'pipeline-history', label:'Pipeline History'}});
context.goBack();
if (content.dataset.currentType !== 'history') throw new Error('did not restore pipeline history: '+JSON.stringify(content.dataset));
"""
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
