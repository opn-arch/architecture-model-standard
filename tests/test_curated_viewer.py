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
        panel = data["panels"][view["panel_ref"]]
        assert panel["theme"] == "dark"
        assert 'data-theme="dark"' in panel["svg"]
        assert "drilldowns" not in panel
        assert all(item["theme"] == "dark" for ref, item in data["panels"].items() if ref.startswith(key + "::"))
        assert view["spec"]["id"]
        assert "<svg" in panel["svg"]
        ET.fromstring(panel["svg"])
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


def test_model_path_provenance_loads_hierarchy_when_output_is_elsewhere(tmp_path: Path) -> None:
    repo = tmp_path / "logs-db"
    repo.mkdir()
    root_path = _write_model(repo)
    child = repo / ".architecture-models" / "child"
    child.mkdir(parents=True)
    root_path.write_text(root_path.read_text().replace(
        "  actors:",
        "  systems:\n    - {id: SYS-1, name: Child, status: ACTIVE, sub_model_ref: .architecture-models/child/.architecture-model.yaml}\n  actors:",
    ))
    (child / ".architecture-model.yaml").write_text(
        "meta: {project: child, schema_version: '2.0'}\nentities:\n  components:\n    - {id: COMP-CHILD, name: Child, status: ACTIVE}\n",
        encoding="utf-8",
    )
    output = tmp_path / "exports" / "viewer.html"

    data = _viewer_data(generate_html_viewer(load_model(root_path), output, model_path=root_path).read_text())

    assert data["subsystem_entities"]["SYS-1"] == ["child::COMP-CHILD"]
    assert not data["viewer_warnings"]


def test_explicit_wrong_repo_path_reports_unresolved_hierarchy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    wrong = tmp_path / "wrong"
    repo.mkdir()
    wrong.mkdir()
    root_path = _write_model(repo)
    root_path.write_text(root_path.read_text().replace(
        "  actors:",
        "  systems:\n    - {id: SYS-1, name: Child, status: ACTIVE, sub_model_ref: .architecture-models/child/.architecture-model.yaml}\n  actors:",
    ))

    data = _viewer_data(generate_html_viewer(load_model(root_path), tmp_path / "viewer.html", repo_path=wrong).read_text())

    assert data["viewer_warnings"] == [{
        "code": "VIEWER_HIERARCHY_UNAVAILABLE",
        "message": "1 referenced subsystem model could not be resolved from the selected repository root.",
    }]


def test_output_ancestor_is_not_inferred_from_an_unrelated_canonical_model(tmp_path: Path) -> None:
    output_repo = tmp_path / "unrelated"
    output_repo.mkdir()
    _write_model(output_repo)
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    source_path = _write_model(source_repo)
    source_path.write_text(source_path.read_text().replace(
        "  actors:",
        "  systems:\n    - {id: SYS-1, name: Child, status: ACTIVE, sub_model_ref: .architecture-models/child/.architecture-model.yaml}\n  actors:",
    ))

    data = _viewer_data(generate_html_viewer(
        load_model(source_path), output_repo / "exports" / "viewer.html",
    ).read_text())

    assert data["viewer_system_namespaces"] == {}
    assert data["viewer_warnings"][0]["code"] == "VIEWER_HIERARCHY_UNAVAILABLE"


def test_generate_all_diagrams_preserves_mmd_and_adds_native_svg(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    paths = generate_all_diagrams(model, tmp_path / "diagrams", repo_path=tmp_path)

    assert paths["context"].suffix == ".mmd"
    for name in ("conops", "functional-architecture", "logical-architecture", "use-cases"):
        assert paths[name].suffix == ".svg"
        root = ET.parse(paths[name]).getroot()
        assert root.attrib["data-theme"] == "light"


def test_viewer_exports_and_docs_share_curated_spec_identity(tmp_path: Path) -> None:
    from architecture_model.docs.se.generator import generate_se_docs

    model = load_model(_write_model(tmp_path))
    curation = tmp_path / ".architecture" / "viewer-curation.yaml"
    curation.parent.mkdir()
    curation.write_text("""version: 1
views:
  conops:
    labels: {root::BEH-1: Curated operation}
""", encoding="utf-8")
    viewer = _viewer_data(generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text())
    exports = generate_all_diagrams(model, tmp_path / "exports", repo_path=tmp_path)
    docs = tmp_path / "docs"
    generate_se_docs(model, docs, repo_root=tmp_path, doc_filter=["conops"])

    expected = viewer["se_views"]["conops"]["spec"]
    for path in (exports["conops"], docs / "conops.svg"):
        root = ET.parse(path).getroot()
        assert root.attrib["data-diagram-id"] == expected["id"]
        assert {item.attrib["data-node-id"] for item in root.iter() if "data-node-id" in item.attrib} == {
            item["id"] for item in expected["nodes"]
        }


def test_generated_javascript_parses_with_node(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    html = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)
    script = next(value for value in scripts if "var D = JSON.parse" in value)
    js = tmp_path / "viewer.js"
    js.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_navigation_escapes_hostile_repository_values_in_dom_harness(tmp_path: Path, monkeypatch) -> None:
    hostile = '<img src=x onerror="globalThis.pwned=(globalThis.pwned||0)+1">'
    hostile_filename = hostile + ".md"
    model = load_model(_write_model(tmp_path))
    modules = {
        hostile: {
            "canonical_path": hostile,
            "name": hostile,
            "doc": "",
            "funcs": [],
            "classes": [],
            "consts": [],
            "routes": [],
        }
    }
    monkeypatch.setattr("architecture_model.core.visualize._build_module_data", lambda _repo: modules)
    docs = tmp_path / ".architecture-models" / "docs" / "se"
    docs.mkdir(parents=True)
    (docs / hostile_filename).write_text("# Safe\n\n<img src=x onerror=globalThis.bodyPwned=1>", encoding="utf-8")
    html = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    data = _viewer_data(html)
    script = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)[1]
    view_key = "conops"
    panel_ref = data["se_views"][view_key]["panel_ref"]
    panel = data["panels"][panel_ref]
    data["se_views"][view_key].update({
        "label": hostile,
        "subtitle": hostile,
        "warnings": [{"code": "HOSTILE", "message": hostile}],
        "curation": {"status": hostile, "path": hostile},
    })
    data["se_views"][view_key]["spec"]["title"] = hostile
    panel["diagram_id"] = hostile
    panel["provenance"] = {"source": hostile, "entity_refs": []}
    data["pipeline_history"] = [{
        "run_id": "run-1", "started_at": "now", "status": hostile,
        "source": hostile, "invocation": hostile, "stages": [],
    }]
    data["modules"][hostile] = modules[hostile]
    data["properties"]["COMP-1"]["properties"] = {hostile: "safe value"}
    data["properties"]["COMP-1"]["depth"] = hostile
    doc_name = Path(hostile_filename).stem
    harness = f"""
const vm = require('vm');
const noop = () => {{}};
const classList = {{add:noop, remove:noop, toggle:noop, contains:()=>false}};
function element() {{ return {{dataset:{{}}, style:{{}}, classList, value:'', textContent:'',
  addEventListener:noop, querySelectorAll:()=>[], querySelector:()=>null, setAttribute:noop}}; }}
const content = element();
Object.defineProperty(content, 'innerHTML', {{
  set(value) {{
    this.html = value;
    if (/<img\\b[^>]*onerror=/i.test(value)) throw new Error(value);
  }},
  get() {{ return this.html || ''; }}
}});
const diagram = element();
Object.defineProperty(diagram, 'innerHTML', Object.getOwnPropertyDescriptor(content, 'innerHTML'));
const dataElement = Object.assign(element(), {{textContent:{json.dumps(json.dumps(data))}}});
const document = {{getElementById:id=>id==='viewer-data'?dataElement:id==='content'?content:id==='dia-main'?diagram:element(),
  querySelectorAll:()=>[], querySelector:()=>Object.assign(element(), {{classList}}), createElement:element}};
const context = {{console, document, Blob, URL, alert:noop, MutationObserver:function(){{this.observe=noop}},
  localStorage:{{getItem:()=>null,setItem:noop,length:0,key:()=>null}}, innerWidth:1200,
  atob,btoa,escape,unescape,encodeURIComponent,decodeURIComponent}};
context.window=context; vm.createContext(context); vm.runInContext({json.dumps(script)}, context);
context.wireNativePanel=noop;
const routes = [
  () => context.showDoc('se', {json.dumps(doc_name)}, false),
  () => context.showView({json.dumps(view_key)}, false),
  () => context.showCuratedDrilldown({json.dumps(view_key)}, 'overview', '', false),
  () => context.showModule({json.dumps(hostile)}, false),
  () => context.showEntity('COMP-1', false),
  () => context.showPipelineHistory(false),
];
for (const route of routes) route();
if (context.bodyPwned) throw new Error('sanitized Markdown body executed');
if (!content.html.includes('&lt;img')) throw new Error('hostile values were not rendered as text');
"""
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_native_renderer_uses_only_generated_panel_svg(tmp_path: Path) -> None:
    data = _viewer_data(generate_html_viewer(
        load_model(_write_model(tmp_path)), tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text())

    assert all(panel["svg"].startswith("<svg") for panel in data["panels"].values())
    assert all("svg" not in view.get("curation", {}) for view in data["se_views"].values())


def test_drilldown_navigation_matrix_restores_exact_drilldown_then_overview(tmp_path: Path) -> None:
    model = load_model(_write_model(tmp_path))
    html = generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    data = _viewer_data(html)
    data["pipeline_history"] = [{"run_id": "run-1", "started_at": "now", "status": "complete", "stages": []}]
    data["docs"] = {"se": {"sample": "<p>sample</p>"}}
    data["ops"] = {"sample": "<p>sample</p>"}
    data["modules"] = {"sample.py": {"canonical_path": "sample.py", "funcs": [], "classes": [], "consts": [], "routes": []}}
    script = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)[1]
    view_key, drilldown_id = next(
        (key, view["spec"]["drilldowns"][0]["id"])
        for key, view in data["se_views"].items() if view.get("spec", {}).get("drilldowns")
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
const routes = [
  ['view', () => context.showView('icd')],
  ['doc', () => context.showDoc('se', 'sample')],
  ['ops', () => context.showOps('sample')],
  ['module', () => context.showModule('sample.py')],
  ['entity', () => context.showEntity(context.resolveNativeEntity({json.dumps(entity_ref)}))],
  ['history', () => context.showPipelineHistory()],
];
for (const [name, route] of routes) {{
  context.navHistory = [];
  context.showView({json.dumps(view_key)}, false);
  context.showCuratedDrilldown({json.dumps(view_key)}, {json.dumps(drilldown_id)}, {json.dumps(entity_ref)});
  route();
  context.goBack();
  if (content.dataset.currentType !== 'drilldown' || content.dataset.currentViewId !== {json.dumps(view_key)} || content.dataset.currentSpecId !== {json.dumps(drilldown_id)} || content.dataset.currentEntityRef !== {json.dumps(entity_ref)}) throw new Error(name+' did not restore exact drilldown: '+JSON.stringify(content.dataset));
  context.goBack();
  if (content.dataset.currentType !== 'view' || content.dataset.currentId !== {json.dumps(view_key)}) throw new Error(name+' did not restore overview: '+JSON.stringify(content.dataset));
}}
"""
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_actual_logs_db_every_direct_projector_panel_is_bounded_resolved_and_complete(monkeypatch) -> None:
    from architecture_model.core.diagram_renderer import render_diagram_panel
    from architecture_model.core import se_view_projectors
    from architecture_model.core.view_context import ArchitectureViewContext
    from architecture_model.core.view_curation import load_viewer_curation

    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        return
    context = ArchitectureViewContext.from_repo(repo)
    curated = load_viewer_curation(repo, context).views
    projectors = (
        (se_view_projectors.project_conops, curated.conops),
        (se_view_projectors.project_functional_architecture, curated.functional),
        (se_view_projectors.project_logical_architecture, curated.logical),
        (se_view_projectors.project_use_cases, curated.use_cases),
    )
    with monkeypatch.context() as context_patch:
        context_patch.setattr(se_view_projectors, "bound_diagram_spec", lambda spec: spec)
        unbounded = [projector(context, curation) for projector, curation in projectors]
    roots = [
        projector(context, curation) for projector, curation in projectors
    ]
    expected_refs = set()
    raw_stack = list(unbounded)
    while raw_stack:
        raw = raw_stack.pop()
        expected_refs.update(node.entity_ref for node in raw.nodes if node.entity_ref)
        raw_stack.extend(item.spec for item in raw.drilldowns if item.spec)
    actual_refs = set()
    stack = list(roots)
    while stack:
        spec = stack.pop()
        panel = render_diagram_panel(spec)
        drilldown_ids = {item.id for item in spec.drilldowns}
        assert len(spec.nodes) <= 25 and len(spec.edges) <= 40
        assert panel.width <= 2400 and panel.height <= 1800
        assert all(not node.drilldown_ref or node.drilldown_ref in drilldown_ids for node in spec.nodes)
        actual_refs.update(node.entity_ref for node in spec.nodes if node.entity_ref)
        stack.extend(item.spec for item in spec.drilldowns if item.spec)
    assert actual_refs == expected_refs
