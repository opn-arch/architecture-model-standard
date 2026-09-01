"""Tests for v3 viewer features: new diagram generators, click injection, property cards."""

from html.parser import HTMLParser
import json
import subprocess

import pytest
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Relationship, RelationType,
    Component, Capability, Actor, Behavior, Interface, Constraint, Layer,
    System, Requirement, Status, ActorType, Priority, ConstraintType,
    InterfaceType, DecisionEntry,
)
from architecture_model.core.visualize import (
    generate_icd_diagram,
    generate_requirements_allocation_diagram,
    generate_system_decomposition_diagram,
    inject_click_handlers,
    build_entity_properties,
    generate_html_viewer,
)


class _ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.handlers = []
        self.images = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.handlers.extend(value for name, value in attrs.items() if name.startswith("on"))
        if tag == "img":
            self.images.append(attrs)
        if tag == "script":
            self._script = {"type": attrs.get("type"), "text": ""}

    def handle_data(self, data):
        if self._script is not None:
            self._script["text"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append(self._script)
            self._script = None


def _make_model():
    """Build a model with all entity types for testing."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="Developer", status=Status.ACTIVE, type=ActorType.HUMAN)],
            capabilities=[
                Capability(id="CAP-1", name="Parsing", status=Status.ACTIVE, priority=Priority.HIGH),
                Capability(id="CAP-2", name="Validation", status=Status.ACTIVE),
            ],
            components=[
                Component(id="COMP-1", name="Parser", status=Status.ACTIVE),
                Component(id="COMP-2", name="Validator", status=Status.ACTIVE),
                Component(id="COMP-3", name="CLI", status=Status.ACTIVE),
            ],
            behaviors=[Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE)],
            interfaces=[
                Interface(id="IF-1", name="Parse API", status=Status.ACTIVE),
                Interface(id="IF-2", name="Validate API", status=Status.ACTIVE),
            ],
            constraints=[Constraint(id="CON-1", name="Max 100ms", status=Status.ACTIVE)],
            layers=[Layer(id="LAY-1", name="Core", status=Status.ACTIVE)],
            systems=[
                System(id="SYS-1", name="Core System", status=Status.ACTIVE, component_ids=["COMP-1", "COMP-2"]),
            ],
            requirements=[
                Requirement(id="REQ-1", name="Must parse YAML", status=Status.ACTIVE, priority="must"),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.EXPOSES, from_id="COMP-1", to_id="IF-1"),
            Relationship(type=RelationType.EXPOSES, from_id="COMP-2", to_id="IF-2"),
            Relationship(type=RelationType.CONSUMES, from_id="ACT-1", to_id="IF-1"),
            Relationship(type=RelationType.SATISFIES, from_id="COMP-1", to_id="REQ-1"),
            Relationship(type=RelationType.CONSTRAINED_BY, from_id="COMP-1", to_id="CON-1"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-2", to_id="COMP-1"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1"),
        ],
    )


class TestICDDiagram:
    def test_returns_mermaid(self):
        result = generate_icd_diagram(_make_model())
        assert result.startswith("flowchart LR")

    def test_contains_interfaces(self):
        result = generate_icd_diagram(_make_model())
        assert "Parse API" in result
        assert "Validate API" in result

    def test_contains_consumer_edges(self):
        result = generate_icd_diagram(_make_model())
        assert "consumes" in result

    def test_groups_by_provider(self):
        result = generate_icd_diagram(_make_model())
        # COMP-1 exposes IF-1, so Parser should be a subgraph label
        assert "Parser" in result


class TestRequirementsAllocationDiagram:
    def test_returns_mermaid(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert result.startswith("flowchart LR")

    def test_contains_requirements(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert "Must parse YAML" in result

    def test_contains_satisfies_edges(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert "satisfies" in result

    def test_contains_constrained_by_edges(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert "constrained-by" in result

    def test_empty_model_shows_placeholder(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(),
            relationships=[],
        )
        result = generate_requirements_allocation_diagram(model)
        assert "No requirements" in result


class TestSystemDecompositionDiagram:
    def test_returns_mermaid(self):
        result = generate_system_decomposition_diagram(_make_model())
        assert result.startswith("flowchart TB")

    def test_contains_systems(self):
        result = generate_system_decomposition_diagram(_make_model())
        assert "Core System" in result

    def test_contains_components_in_system(self):
        result = generate_system_decomposition_diagram(_make_model())
        assert "Parser" in result
        assert "Validator" in result

    def test_unassigned_components_shown(self):
        result = generate_system_decomposition_diagram(_make_model())
        # COMP-3 (CLI) is not in any system
        assert "CLI" in result


class TestClickInjection:
    def test_injects_click_for_known_ids(self):
        mermaid = "flowchart LR\n    COMP_1[Parser]\n    classDef cls_comp fill:#27AE60"
        result = inject_click_handlers(mermaid, {"COMP-1"})
        assert 'click COMP_1 call showEntity()' in result

    def test_preserves_classdefs(self):
        mermaid = "flowchart LR\n    COMP_1[Parser]\n    classDef cls_comp fill:#27AE60"
        result = inject_click_handlers(mermaid, {"COMP-1"})
        assert "classDef cls_comp" in result

    def test_removes_existing_click_directives(self):
        mermaid = 'flowchart LR\n    COMP_1[Parser]\n    click COMP_1 "old.mmd"'
        result = inject_click_handlers(mermaid, {"COMP-1"})
        assert "old.mmd" not in result
        assert 'click COMP_1 call showEntity()' in result

    def test_ignores_unknown_ids(self):
        mermaid = "flowchart LR\n    COMP_1[Parser]"
        result = inject_click_handlers(mermaid, {"OTHER-1"})
        assert "showEntity" not in result

    def test_handles_empty_diagram(self):
        result = inject_click_handlers("flowchart LR", {"COMP-1"})
        assert "flowchart LR" in result


class TestBuildEntityProperties:
    def test_returns_all_entities(self):
        props = build_entity_properties(_make_model())
        assert "COMP-1" in props
        assert "CAP-1" in props
        assert "ACT-1" in props
        assert "SYS-1" in props
        assert "REQ-1" in props

    def test_component_properties(self):
        props = build_entity_properties(_make_model())
        p = props["COMP-1"]
        assert p["type"] == "component"
        assert p["name"] == "Parser"

    def test_actor_has_type_field(self):
        props = build_entity_properties(_make_model())
        p = props["ACT-1"]
        assert p["properties"]["Actor Type"]

    def test_capability_has_priority(self):
        props = build_entity_properties(_make_model())
        p = props["CAP-1"]
        assert "Priority" in p["properties"]

    def test_requirement_has_priority(self):
        props = build_entity_properties(_make_model())
        p = props["REQ-1"]
        assert p["properties"]["Priority"] == "must"


class TestSystemChildResolution:
    """Test that system decomposition resolves child components when parent ID is missing."""

    def test_resolves_children_when_parent_missing(self):
        """SYS-1 references COMP-1 which doesn't exist, but COMP-1.1 and COMP-1.2 do."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                systems=[System(id="SYS-1", name="Core", status=Status.ACTIVE,
                               component_ids=["COMP-1"])],
                components=[
                    Component(id="COMP-1.1", name="Parser", status=Status.ACTIVE),
                    Component(id="COMP-1.2", name="Validator", status=Status.ACTIVE),
                    Component(id="COMP-2", name="CLI", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        result = generate_system_decomposition_diagram(model)
        # COMP-1 doesn't exist, but its children should be in the system subgraph
        assert "Parser" in result
        assert "Validator" in result
        # COMP-2 is unassigned
        assert "CLI" in result
        assert "Core" in result


class TestHtmlViewerModuleData:
    """Test that viewer includes module data when repo_path is provided."""

    def test_viewer_includes_showModule(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "showModule" in html

    def test_viewer_includes_sid_map(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "sid_map" in html

    def test_viewer_includes_comp_files(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "comp_files" in html

    def test_callback_syntax(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert 'callback' in html


def _make_rich_model():
    """Model with rich fields for property card testing."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="Dev", status=Status.ACTIVE, type=ActorType.HUMAN,
                          intent="Build software", goals=["Ship fast", "Stay sane"])],
            capabilities=[Capability(id="CAP-1", name="Parsing", status=Status.ACTIVE,
                                     priority=Priority.HIGH, intent="Parse YAML files",
                                     moes=["<100ms parse time", ">99% accuracy"])],
            components=[Component(id="COMP-1", name="Parser", status=Status.ACTIVE,
                                  intent="Core parsing engine", goals=["Fast", "Accurate"],
                                  trade_offs=["Speed vs memory"], failure_modes=["OOM on huge files"],
                                  contract="Must accept any valid YAML")],
            behaviors=[Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE,
                                actor="ACT-1", steps=["Open file", "Tokenize", "Build AST"],
                                trigger="User request")],
            interfaces=[Interface(id="IF-1", name="Parse API", status=Status.ACTIVE,
                                  type=InterfaceType.REST, provider="COMP-1", protocol="HTTP")],
            constraints=[Constraint(id="CON-1", name="Max 100ms", status=Status.ACTIVE,
                                    type=ConstraintType.PERFORMANCE, metric="latency",
                                    threshold="100ms", rationale="UX requirement")],
            layers=[Layer(id="LAY-1", name="Core", status=Status.ACTIVE, order=1,
                          technology=["Python"], directories=["src/core"])],
            requirements=[Requirement(id="REQ-1", name="Must parse YAML", status=Status.ACTIVE,
                                      priority="must", text="System shall parse YAML files")],
            systems=[System(id="SYS-1", name="Core", status=Status.ACTIVE,
                            component_ids=["COMP-1"])],
        ),
        relationships=[
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1",
                         description="Parser realizes parsing capability"),
            Relationship(type=RelationType.EXPOSES, from_id="COMP-1", to_id="IF-1"),
        ],
    )


class TestEnrichedPropertyCards:
    """Test that build_entity_properties returns rich fields and relationships."""

    def test_actor_intent_and_goals(self):
        props = build_entity_properties(_make_rich_model())
        p = props["ACT-1"]
        assert p["properties"]["Intent"] == "Build software"
        assert p["properties"]["Goals"] == ["Ship fast", "Stay sane"]

    def test_capability_intent_and_moes(self):
        props = build_entity_properties(_make_rich_model())
        p = props["CAP-1"]
        assert p["properties"]["Intent"] == "Parse YAML files"
        assert p["properties"]["Measures of Effectiveness"] == ["<100ms parse time", ">99% accuracy"]

    def test_component_rich_fields(self):
        props = build_entity_properties(_make_rich_model())
        p = props["COMP-1"]
        assert p["properties"]["Intent"] == "Core parsing engine"
        assert p["properties"]["Goals"] == ["Fast", "Accurate"]
        assert p["properties"]["Trade-offs"] == ["Speed vs memory"]
        assert p["properties"]["Failure Modes"] == ["OOM on huge files"]
        assert p["properties"]["Contract"] == "Must accept any valid YAML"

    def test_behavior_steps_and_trigger(self):
        props = build_entity_properties(_make_rich_model())
        p = props["BEH-1"]
        assert p["properties"]["Steps"] == ["Open file", "Tokenize", "Build AST"]
        assert p["properties"]["Trigger"] == "User request"
        assert p["properties"]["Actor"] == "ACT-1"

    def test_interface_type_and_provider(self):
        props = build_entity_properties(_make_rich_model())
        p = props["IF-1"]
        assert "rest" in p["properties"]["Interface Type"].lower()
        assert p["properties"]["Provider"] == "COMP-1"
        assert p["properties"]["Protocol"] == "HTTP"

    def test_constraint_fields(self):
        props = build_entity_properties(_make_rich_model())
        p = props["CON-1"]
        assert p["properties"]["Constraint Type"] == "performance"
        assert p["properties"]["Metric"] == "latency"
        assert p["properties"]["Threshold"] == "100ms"
        assert p["properties"]["Rationale"] == "UX requirement"

    def test_layer_fields(self):
        props = build_entity_properties(_make_rich_model())
        p = props["LAY-1"]
        assert p["properties"]["Order"] == "1"
        assert p["properties"]["Technology"] == ["Python"]
        assert p["properties"]["Directories"] == ["src/core"]

    def test_requirement_text(self):
        props = build_entity_properties(_make_rich_model())
        p = props["REQ-1"]
        assert p["properties"]["Text"] == "System shall parse YAML files"

    def test_real_decisions_are_json_safe_with_readable_labels(self):
        model = _make_rich_model()
        model.entities.components[0].decisions = [
            DecisionEntry(choice="Use YAML", rationale="Readable", alternatives=["JSON"]),
        ]

        properties = build_entity_properties(model)["COMP-1"]["properties"]

        assert properties["Decisions"] == [{
            "choice": "Use YAML",
            "rationale": "Readable",
            "alternatives": ["JSON"],
        }]
        import json
        json.dumps(properties)

    def test_real_decisions_render_as_structured_rows(self, tmp_path):
        model = _make_rich_model()
        model.entities.components[0].decisions = [DecisionEntry(
            choice="Use YAML",
            date="2026-09-01",
            rationale="Readable",
            alternatives=["JSON", "TOML"],
            context="Model persistence",
        )]

        html = generate_html_viewer(model, tmp_path / "viewer.html").read_text()

        assert 'class="decision-card"' in html
        assert 'class="decision-choice"' in html
        assert "decision.date" in html
        assert "decision.rationale" in html
        assert "decision.alternatives" in html
        assert "decision.context" in html
        assert "[object Object]" not in html

    def test_requirement_value_function_uses_runtime_data_key(self):
        model = _make_rich_model()
        model.entities.requirements[0].value_function = r"J = \sum_t c_t"

        properties = build_entity_properties(model)["REQ-1"]["properties"]

        assert properties["value_function"] == r"J = \sum_t c_t"
        assert "Value Function" not in properties

    def test_outgoing_relationships(self):
        props = build_entity_properties(_make_rich_model())
        rels = props["COMP-1"]["relationships"]
        assert len(rels["outgoing"]) == 2
        realize_rel = [r for r in rels["outgoing"] if r["type"] == "realizes"][0]
        assert realize_rel["target"] == "CAP-1"
        assert realize_rel["description"] == "Parser realizes parsing capability"

    def test_incoming_relationships(self):
        props = build_entity_properties(_make_rich_model())
        rels = props["CAP-1"]["relationships"]
        assert len(rels["incoming"]) == 1
        assert rels["incoming"][0]["source"] == "COMP-1"

    def test_html_viewer_renders_rel_section(self, tmp_path):
        html = generate_html_viewer(_make_rich_model(), tmp_path / "v.html").read_text()
        assert "rel-section" in html
        assert "rel-type" in html
        assert "prop-list" in html

    def test_hostile_model_data_is_safe_and_inline_scripts_are_valid(self, tmp_path):
        hostile = "</script><script>globalThis.pwned=1</script> ' \" & \u2028 \u2029"
        model = _make_model()
        model.meta.project = hostile
        model.entities.components[0].name = hostile
        model.entities.components[0].description = hostile
        model.relationships[0].description = hostile

        html = generate_html_viewer(model, tmp_path / "viewer.html", title=hostile).read_text()
        parser = _ScriptParser()
        parser.feed(html)

        data_script = next(script for script in parser.scripts if script["type"] == "application/json")
        assert json.loads(data_script["text"])["properties"]["COMP-1"]["name"] == hostile
        assert len(parser.scripts) == 2
        assert not parser.images
        assert not parser.handlers
        for index, script in enumerate(parser.scripts):
            if script["type"] == "application/json":
                continue
            path = tmp_path / f"inline-{index}.js"
            path.write_text(script["text"])
            result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            assert result.returncode == 0, result.stderr

    def test_entity_rendering_escapes_hostile_values_when_storage_throws(self, tmp_path):
        hostile = "</textarea><img src=x onerror=globalThis.pwned=1> & ' \""
        model = _make_model()
        model.entities.components[0].name = hostile
        model.entities.components[0].description = hostile
        html = generate_html_viewer(model, tmp_path / "viewer.html").read_text()
        parser = _ScriptParser()
        parser.feed(html)
        data = json.loads(next(s["text"] for s in parser.scripts if s["type"] == "application/json"))
        script = next(s["text"] for s in parser.scripts if s["type"] != "application/json")
        harness = f"""
const vm = require('vm');
const textarea = {{value: '', addEventListener:()=>{{}}, dataset: {{entityId: 'COMP-1'}}}};
const content = {{dataset: {{}}, innerHTML: '', addEventListener:()=>{{}}, querySelectorAll: () => [], querySelector: s => s === '.comment-textarea' ? textarea : null}};
const element = {{addEventListener:()=>{{}}, click:()=>{{}}, value:''}};
const dataElement = {{...element, textContent: {json.dumps(json.dumps(data))}}};
const context = {{console, Blob, URL, alert: () => {{}}, MutationObserver: function(){{this.observe=()=>{{}}}},
  document: {{getElementById: id => id === 'viewer-data' ? dataElement : (id === 'content' ? content : element), querySelectorAll: () => [], querySelector: () => ({{classList: {{remove:()=>{{}}, toggle:()=>{{}}}}, addEventListener:()=>{{}}}}), createElement: () => ({{click:()=>{{}}}})}},
  localStorage: new Proxy({{}}, {{get() {{throw new Error('storage denied')}}}}),
  innerWidth: 1200, atob, btoa, escape, unescape, encodeURIComponent, decodeURIComponent}};
context.window = context;
vm.createContext(context);
vm.runInContext({json.dumps(script)}, context);
context.showEntity('COMP-1');
if (context.pwned) throw new Error('hostile content executed');
if (content.innerHTML.includes('<img')) throw new Error('hostile HTML was not escaped');
if (!content.innerHTML.includes('&lt;/textarea&gt;')) throw new Error('description was not escaped');
if (textarea.value !== '') throw new Error('unexpected textarea value');
"""
        result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    def test_comment_import_accepts_known_entities_and_rejects_unknown_ids(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "viewer.html").read_text()
        parser = _ScriptParser()
        parser.feed(html)
        data = json.loads(next(s["text"] for s in parser.scripts if s["type"] == "application/json"))
        script = next(s["text"] for s in parser.scripts if s["type"] != "application/json")
        imported = "COMP-1:\n  comment: |\n    safe <b>text</b>\nUNKNOWN-9:\n  comment: |\n    rejected"
        harness = f"""
const vm = require('vm');
const writes = [];
const element = {{addEventListener:()=>{{}}, click:()=>{{}}, value:'', files:[{{}}]}};
const content = {{...element, dataset: {{}}, querySelectorAll:()=>[], querySelector:()=>null}};
const context = {{console, Blob, URL, alert:()=>{{}}, MutationObserver:function(){{this.observe=()=>{{}}}},
  FileReader:function(){{this.readAsText=()=>this.onload({{target:{{result:{json.dumps(imported)}}}}})}},
  document:{{getElementById:id=>id==='viewer-data'?{{...element,textContent:{json.dumps(json.dumps(data))}}}:id==='content'?content:element,querySelectorAll:()=>[],querySelector:()=>({{...element,classList:{{remove:()=>{{}},toggle:()=>{{}}}}}}),createElement:()=>element}},
  localStorage:{{length:0,setItem:(key,value)=>writes.push([key,value]),getItem:()=>null,key:()=>null}},
  innerWidth:1200,atob,btoa,escape,unescape,encodeURIComponent,decodeURIComponent}};
context.window=context; vm.createContext(context); vm.runInContext({json.dumps(script)},context);
context.importComments(element);
if (writes.length !== 1 || !writes[0][0].endsWith(':COMP-1') || writes[0][1] !== 'safe <b>text</b>') throw new Error(JSON.stringify(writes));
"""
        result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


class TestDocEmbedding:
    """Test that SE docs and ops artifacts are embedded in the viewer."""

    def test_load_docs_with_se_dir(self, tmp_path):
        from architecture_model.core.visualize import _load_docs
        se_dir = tmp_path / ".architecture-models" / "docs" / "se"
        se_dir.mkdir(parents=True)
        (se_dir / "conops.md").write_text("# ConOps\n\nOperational concept.")
        result = _load_docs(tmp_path)
        assert "conops" in result["se"]
        assert "<h1" in result["se"]["conops"]
        assert "Operational concept" in result["se"]["conops"]

    def test_load_docs_with_component_dir(self, tmp_path):
        from architecture_model.core.visualize import _load_docs
        comp_dir = tmp_path / ".architecture" / "docs" / "components"
        comp_dir.mkdir(parents=True)
        (comp_dir / "COMP-1.md").write_text("# Parser\n\n- Fast\n- Reliable")
        result = _load_docs(tmp_path)
        assert "COMP-1" in result["components"]
        assert "<li>" in result["components"]["COMP-1"]

    def test_load_ops_devlog(self, tmp_path):
        from architecture_model.core.visualize import _load_ops_data
        arch_dir = tmp_path / ".architecture"
        arch_dir.mkdir(parents=True)
        import json
        (arch_dir / "devlog.jsonl").write_text(
            json.dumps({"log_type": "decision", "title": "Chose YAML", "timestamp": "2026-01-01", "content": "YAML is human-readable"}) + "\n"
        )
        result = _load_ops_data(tmp_path)
        assert "devlog" in result
        assert "Chose YAML" in result["devlog"]

    def test_load_ops_validation(self, tmp_path):
        from architecture_model.core.visualize import _load_ops_data
        import json
        arch_dir = tmp_path / ".architecture"
        arch_dir.mkdir(parents=True)
        (arch_dir / "validation.json").write_text(json.dumps({"score": 86, "is_valid": True, "issues": []}))
        result = _load_ops_data(tmp_path)
        assert "validation" in result
        assert "86" in result["validation"]

    def test_viewer_includes_docs_section(self, tmp_path):
        se_dir = tmp_path / ".architecture-models" / "docs" / "se"
        se_dir.mkdir(parents=True)
        (se_dir / "conops.md").write_text("# ConOps")
        html = generate_html_viewer(_make_rich_model(), tmp_path / "v.html", repo_path=tmp_path).read_text()
        assert "showDoc" in html
        assert "Documents" in html
        assert "SE Documents" in html

    def test_viewer_includes_ops_section(self, tmp_path):
        import json
        arch_dir = tmp_path / ".architecture"
        arch_dir.mkdir(parents=True)
        (arch_dir / "devlog.jsonl").write_text(
            json.dumps({"log_type": "decision", "title": "Test", "timestamp": "", "content": ""}) + "\n"
        )
        html = generate_html_viewer(_make_rich_model(), tmp_path / "v.html", repo_path=tmp_path).read_text()
        assert "showOps" in html
        assert "Intelligence" in html

    def test_md_to_html_headings(self):
        from architecture_model.core.visualize import _md_to_html
        result = _md_to_html("# Title\n\n## Subtitle\n\nParagraph text.")
        assert "<h1" in result
        assert "<h2" in result
        assert "<p" in result

    def test_md_to_html_code_block(self):
        from architecture_model.core.visualize import _md_to_html
        result = _md_to_html("```python\nprint('hello')\n```")
        assert "<pre" in result
        assert "print" in result

    def test_markdown_escapes_raw_html_before_formatting(self):
        from architecture_model.core.visualize import _md_to_html

        result = _md_to_html("# Safe\n\n<img src=x onerror=globalThis.pwned=1> **bold**\n\n```\n<script>alert(1)</script>\n```")

        parser = _ScriptParser()
        parser.feed(result)
        assert not parser.images
        assert not parser.scripts
        assert "&lt;img src=x onerror=globalThis.pwned=1&gt;" in result
        assert "<strong>bold</strong>" in result
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in result

    def test_ops_json_values_are_html_escaped(self, tmp_path):
        from architecture_model.core.visualize import _load_ops_data

        arch_dir = tmp_path / ".architecture"
        arch_dir.mkdir()
        payload = "<img src=x onerror=globalThis.pwned=1>"
        (arch_dir / "devlog.jsonl").write_text(json.dumps({
            "log_type": payload, "title": payload, "timestamp": payload, "content": payload,
        }) + "\n")

        result = _load_ops_data(tmp_path)["devlog"]
        parser = _ScriptParser()
        parser.feed(result)

        assert not parser.images
        assert not parser.handlers
        assert result.count("&lt;img") == 4

    @pytest.mark.parametrize("reader_body", [
        "throw new Error('read denied')",
        "this.onerror(new Error('malformed'))",
    ])
    def test_comment_import_contains_filereader_failures(self, tmp_path, reader_body):
        html = generate_html_viewer(_make_model(), tmp_path / "viewer.html").read_text()
        parser = _ScriptParser()
        parser.feed(html)
        data = json.loads(next(s["text"] for s in parser.scripts if s["type"] == "application/json"))
        script = next(s["text"] for s in parser.scripts if s["type"] != "application/json")
        harness = f"""
const vm=require('vm'); const element={{addEventListener:()=>{{}},click:()=>{{}},value:'',files:[{{}}]}};
const content={{...element,dataset:{{}},querySelectorAll:()=>[],querySelector:()=>null}};
const context={{console,Blob,URL,alert:()=>{{}},MutationObserver:function(){{this.observe=()=>{{}}}},
 FileReader:function(){{this.readAsText=()=>{{{reader_body}}}}},
 document:{{getElementById:id=>id==='viewer-data'?{{...element,textContent:{json.dumps(json.dumps(data))}}}:id==='content'?content:element,querySelectorAll:()=>[],querySelector:()=>({{...element,classList:{{remove:()=>{{}},toggle:()=>{{}}}}}}),createElement:()=>element}},
 localStorage:{{length:0,setItem:()=>{{}},getItem:()=>null,key:()=>null}},innerWidth:1200,atob,btoa,escape,unescape,encodeURIComponent,decodeURIComponent}};
context.window=context;vm.createContext(context);vm.runInContext({json.dumps(script)},context);context.importComments(element);
"""
        result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


class TestDepthScoring:
    """Tests for entity depth scoring and viewer depth badge/deepen UI."""

    def test_stub_component(self):
        """Component with only name/status → stub."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                components=[Component(id="COMP-1", name="Bare", status=Status.ACTIVE)],
            ),
            relationships=[],
        )
        props = build_entity_properties(model)
        assert props["COMP-1"]["depth"] == "stub"

    def test_rich_component(self):
        """Component with many fields populated → rich."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                components=[Component(
                    id="COMP-1", name="Rich", status=Status.ACTIVE,
                    description="A rich component",
                    intent="Does everything",
                    goals=["goal1"],
                    files=["f.py"],
                    responsibilities=["resp1"],
                    monitored=True,
                )],
            ),
            relationships=[],
        )
        props = build_entity_properties(model)
        # 6 of 11 fields populated = 0.55 → rich
        assert props["COMP-1"]["depth"] == "rich"

    def test_moderate_behavior(self):
        """Behavior with description + trigger → moderate (2/5 = 0.4)."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                behaviors=[Behavior(
                    id="BEH-1", name="Do Thing", status=Status.ACTIVE,
                    description="Does a thing", trigger="on event",
                )],
            ),
            relationships=[],
        )
        props = build_entity_properties(model)
        assert props["BEH-1"]["depth"] == "moderate"

    def test_viewer_contains_depth_css(self, tmp_path):
        """Generated HTML viewer contains depth badge CSS classes."""
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "depth-badge" in html
        assert "depth-rich" in html
        assert "depth-moderate" in html
        assert "depth-stub" in html
        assert "deepen-section" in html
        assert "deepen-cmd" in html

    def test_viewer_deepen_command_in_js(self, tmp_path):
        """Generated HTML contains deepen CLI command template in JS."""
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "architecture-model deepen --entity" in html

    def test_capability_with_se_fields_scores_higher(self):
        """Capability with goals+failure_modes+monitored scores rich (not stub)."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                capabilities=[Capability(
                    id="CAP-1", name="Rich Cap", status=Status.ACTIVE,
                    description="desc",
                    goals=["g1"],
                    failure_modes=["fm1"],
                    monitored=True,
                    decisions=["d1"],
                    moes=["m1"],
                )],
            ),
            relationships=[],
        )
        props = build_entity_properties(model)
        # 5 of 9 fields populated (description, moes, goals, failure_modes, monitored, decisions) = 6/9 → rich
        assert props["CAP-1"]["depth"] == "rich"

    def test_build_entity_properties_includes_se_fields(self):
        """build_entity_properties extracts new SE fields into property cards."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                capabilities=[Capability(
                    id="CAP-1", name="Cap", status=Status.ACTIVE,
                    goals=["g1"], failure_modes=["fm1"], decisions=["d1"],
                )],
                behaviors=[Behavior(
                    id="BEH-1", name="Beh", status=Status.ACTIVE,
                    goals=["g1"], failure_modes=["fm1"],
                )],
                components=[Component(
                    id="COMP-1", name="Comp", status=Status.ACTIVE,
                    monitored=True, decisions=["d1"],
                )],
            ),
            relationships=[],
        )
        props = build_entity_properties(model)
        assert "Goals" in props["CAP-1"]["properties"]
        assert "Failure Modes" in props["CAP-1"]["properties"]
        assert "Decisions" in props["CAP-1"]["properties"]
        assert "Goals" in props["BEH-1"]["properties"]
        assert "Failure Modes" in props["BEH-1"]["properties"]
        assert "Monitored" in props["COMP-1"]["properties"]
        assert "Decisions" in props["COMP-1"]["properties"]
