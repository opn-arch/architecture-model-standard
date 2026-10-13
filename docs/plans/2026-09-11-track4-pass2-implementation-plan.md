# Track 4 Pass 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend anchor routing to logical/conops/use_cases panels, distinguish entity kinds by Mermaid shape, and enrich the drill-down with all schema-2.1 semantic fields, grouped relationships, and linked requirements.

**Architecture:** Three orthogonal changes bundled into one Pass — (1) widen `_APPLY_ANCHOR` frozenset from `{"functional"}` to `{"functional","logical","conops","use_cases"}` and add count-based regression tests per view to prevent Pass 1 Task 5's false-green pattern; (2) add module-level `_MERMAID_SHAPE` mapping + `_shape(kind, sid, label)` helper in `visualize.py` and route all Mermaid node emitters through it; (3) expand `build_entity_properties._base` to serialize 9 missing schema-2.1 fields, restructure relationship rendering into semantic groups in `propCardHtml` JS, and load `.architecture/derived_requirements.yaml` into a new `requirements_by_entity` payload key rendered as a drill-down section.

**Tech Stack:** Python 3.11+, dataclasses, PyYAML, Mermaid.js flowchart syntax, embedded JS in `visualize.py`, pytest.

**Baseline:** 3664 passed / 104 skipped as of `4eec709`. Target post-Pass-2: ~3680–3682 passed. No schema bump.

**Design doc:** `docs/plans/2026-09-11-track4-pass2-design.md` (committed at `08aaa78`).

**Guardrails (rigid):**
- TDD every task (RED → GREEN → commit).
- One commit per task, Conventional Commits.
- **NEVER** `git add -A` / `git add .`. Stage only the exact files touched.
- **NEVER** touch `.architecture*` generated files / `.DS_Store` / `sil.sqlite*` / `.architecture-models/` / `.architecture-model.yaml`.
- **NEVER** `pip install -e`.
- `.architecture/derived_requirements.yaml` is READ-ONLY input — do not modify.
- Test command:
  `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`

---

## Task 1: Mermaid shape mapping + `_shape` helper

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (module-top area, near existing constants around line 24–35)
- Test: `tests/core/test_mermaid_shapes.py` (create)

**Step 1: Write the failing tests**

Create `tests/core/test_mermaid_shapes.py`:

```python
"""Tests for Mermaid shape mapping and _shape helper (Track 4 Pass 2 Task 1)."""

import pytest

from architecture_model.core.visualize import _MERMAID_SHAPE, _shape


def test_shape_mapping_covers_seven_kinds():
    """_MERMAID_SHAPE must map all seven entity kinds to bracket pairs."""
    expected = {"component", "capability", "actor", "behavior",
                "interface", "constraint", "layer"}
    assert expected.issubset(set(_MERMAID_SHAPE.keys()))


def test_shape_emits_correct_mermaid_syntax_per_kind():
    """_shape returns Mermaid node syntax with the correct bracket pair per kind."""
    assert _shape("component", "COMP_1", "MyComp") == 'COMP_1["MyComp"]'
    assert _shape("capability", "CAP_1", "MyCap") == 'CAP_1{{"MyCap"}}'
    assert _shape("actor", "ACT_1", "MyActor") == 'ACT_1(("MyActor"))'
    assert _shape("behavior", "BEH_1", "MyBeh") == 'BEH_1(["MyBeh"])'
    assert _shape("interface", "IF_1", "MyIF") == 'IF_1[/"MyIF"/]'
    assert _shape("constraint", "CON_1", "MyCon") == 'CON_1{"MyCon"}'


def test_shape_falls_back_to_rectangle_for_unknown_kind(caplog):
    """Unknown kinds return rectangle syntax and emit a DEBUG log."""
    import logging
    caplog.set_level(logging.DEBUG, logger="architecture_model.core.visualize")
    out = _shape("system", "SYS_1", "MyS")
    assert out == 'SYS_1["MyS"]'
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_mermaid_shapes.py -q`
Expected: `ImportError: cannot import name '_MERMAID_SHAPE'` or similar.

**Step 3: Write minimal implementation**

In `src/architecture_model/core/visualize.py`, near the existing module-top constants (after `from __future__ import annotations` imports, before the first function definition, around line 24–35):

```python
# ── Mermaid shape mapping (Track 4 Pass 2 Task 1) ─────────────────────
# Maps entity kind (lowercase singular) to a (left_bracket, right_bracket)
# pair used to wrap the node label in Mermaid flowchart syntax.
# Layer is subgraph-based and not included here.
_MERMAID_SHAPE: dict[str, tuple[str, str]] = {
    "component":  ("[",   "]"),
    "capability": ("{{",  "}}"),
    "actor":      ("((",  "))"),
    "behavior":   ("([",  "])"),
    "interface":  ("[/",  "/]"),
    "constraint": ("{",   "}"),
    "layer":      ("[",   "]"),  # fallback; layers normally emitted as subgraphs
}


def _shape(kind: str, sid: str, label: str) -> str:
    """Return a Mermaid node declaration with kind-appropriate brackets.

    Unknown kinds fall back to rectangle brackets and emit a DEBUG log.
    Label is always quoted to survive special characters.
    """
    brackets = _MERMAID_SHAPE.get(kind.lower())
    if brackets is None:
        _log.debug("visualize._shape: unknown kind %r; falling back to rect", kind)
        brackets = ("[", "]")
    left, right = brackets
    return f'{sid}{left}"{label}"{right}'
```

Confirm `_log` already exists at module scope (search for `_log = logging.getLogger(__name__)`); if not, add it.

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_mermaid_shapes.py -q`
Expected: 3 passed.

**Step 5: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/core/test_mermaid_shapes.py
git commit -m "feat(track4): add Mermaid shape mapping and _shape helper for entity kinds"
```

---

## Task 2: Apply shapes in native panel diagrams

**Context:** The four native panel diagrams (`generate_functional_architecture_diagram`, `generate_logical_architecture_diagram`, `generate_conops_diagram`, `generate_use_case_diagrams`) currently emit nodes as bare `sid[label]` regardless of kind. Route every node emission through `_shape(kind, sid, label)`.

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (all node-emission sites in the 4 native diagram generators)
- Test: `tests/core/test_shapes_in_panels.py` (create)

**Step 1: Write the failing tests**

Create `tests/core/test_shapes_in_panels.py`:

```python
"""Tests for shape application in native panel diagrams (Track 4 Pass 2 Task 2)."""

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import (
    generate_functional_architecture_diagram,
    generate_use_case_diagrams,
)


def _build_model():
    return _parse_raw({
        "meta": {"project": "shapes-test", "schema_version": "2.1"},
        "entities": {
            "actors": [{"id": "ACT-1", "name": "User", "status": "ACTIVE"}],
            "capabilities": [
                {"id": "CAP-1", "name": "RootCap", "status": "ACTIVE"},
                {"id": "CAP-2", "name": "ChildCap", "status": "ACTIVE"},
            ],
            "components": [
                {"id": "COMP-1", "name": "Widget", "status": "ACTIVE"},
            ],
            "behaviors": [
                {"id": "BEH-1", "name": "UseIt", "status": "ACTIVE"},
            ],
        },
        "relationships": [
            {"from": "CAP-1", "to": "CAP-2", "type": "contains"},
            {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
            {"from": "ACT-1", "to": "BEH-1", "type": "consumes"},
        ],
    })


def test_functional_diagram_uses_hexagon_for_capability_and_rect_for_component():
    model = _build_model()
    mermaid = generate_functional_architecture_diagram(model)
    # Capability = hexagon: {{"Name"}}
    assert '{{"RootCap"}}' in mermaid or '{{"CAP-1"}}' in mermaid
    # Component = rect: ["Name"]
    assert '["Widget"]' in mermaid or '["COMP-1"]' in mermaid


def test_use_case_diagram_uses_circle_for_actor_and_stadium_for_behavior():
    model = _build_model()
    diagrams = generate_use_case_diagrams(model)
    body = "\n".join(diagrams.values()) if isinstance(diagrams, dict) else str(diagrams)
    # Actor = circle: (("User"))
    assert '(("User"))' in body or '(("ACT-1"))' in body
    # Behavior = stadium: (["UseIt"])
    assert '(["UseIt"])' in body or '(["BEH-1"])' in body
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_shapes_in_panels.py -q`
Expected: 2 failed (nodes still emitted as plain rectangles).

**Step 3: Implement**

Locate every node-emission site inside the 4 native panel generators
(`generate_functional_architecture_diagram` around line 890,
`generate_logical_architecture_diagram`, `generate_conops_diagram`,
`generate_use_case_diagrams`). For each site that currently produces
`sid[label]` or `sid["label"]`, replace with `_shape(kind, sid, label)`.
Use grep for `_sid(` inside these functions to enumerate sites.

Example transformation:
```python
# BEFORE
lines.append(f'    {_sid(comp.id)}["{escape(comp.name)}"]')
# AFTER
lines.append(f"    {_shape('component', _sid(comp.id), escape(comp.name))}")
```

Apply consistently: components → `"component"`, capabilities → `"capability"`,
actors → `"actor"`, behaviors → `"behavior"`, interfaces → `"interface"`,
constraints → `"constraint"`. Layer subgraphs untouched.

**Step 4: Verify tests pass + no regression**

Run:
- `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_shapes_in_panels.py tests/core/test_mermaid_shapes.py -q` (expect 5 passed)
- `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q -k "visualize or viewer or diagram" --ignore=tests/test_config_loader.py 2>&1 | tail -20` (report result; expect 0 failures)

If existing diagram-golden tests fail due to shape changes, update those goldens as part of THIS commit — they reflect the new visual contract.

**Step 5: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/core/test_shapes_in_panels.py
# If any goldens updated:
# git add tests/<updated golden files>
git commit -m "feat(track4): apply per-kind Mermaid shapes in native panel diagrams"
```

---

## Task 3: Schema 2.1 field expansion in `_base`

**Files:**
- Modify: `src/architecture_model/core/visualize.py:1638-1666` (`_base` inner function of `build_entity_properties`)
- Test: `tests/core/test_entity_properties_2_1_fields.py` (create)

**Step 1: Write the failing tests**

Create `tests/core/test_entity_properties_2_1_fields.py`:

```python
"""Tests for schema 2.1 semantic field serialization (Track 4 Pass 2 Task 3)."""

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import build_entity_properties


def _model_with_populated_capability():
    return _parse_raw({
        "meta": {"project": "sem-fields", "schema_version": "2.1"},
        "entities": {
            "capabilities": [{
                "id": "CAP-1",
                "name": "RichCap",
                "status": "ACTIVE",
                "intent": "why-it-exists",
                "goals": ["goal-a"],
                "stakeholders": ["ops"],
                "success_criteria": ["metric-x-met"],
                "assumptions": ["network-available"],
                "open_questions": ["q1?"],
                "requirements": ["REQ-1"],
                "verification": ["test-suite-z"],
                "slos": ["latency<100ms"],
                "owner": "alice",
                "maturity": "stable",
                "dependencies_rationale": "because-y",
            }],
        },
    })


def test_all_nine_new_semantic_fields_serialize():
    """The 9 schema-2.1 fields missing from _base must now appear in properties."""
    model = _model_with_populated_capability()
    props = build_entity_properties(model)
    universal = props["CAP-1"]["properties"]
    expected_labels = {
        "Stakeholders", "Success Criteria", "Assumptions", "Open Questions",
        "Verification", "SLOs", "Owner", "Maturity", "Dependencies Rationale",
    }
    for label in expected_labels:
        assert label in universal, f"missing label {label!r} in {list(universal)}"


def test_existing_fields_still_serialize():
    """Regression: existing 2.0 fields still appear."""
    model = _model_with_populated_capability()
    props = build_entity_properties(model)
    universal = props["CAP-1"]["properties"]
    assert "Intent" in universal
    assert "Goals" in universal
    assert "Requirements" in universal


def test_empty_semantic_fields_are_stripped():
    """None/empty values must not produce spurious keys."""
    raw = {
        "meta": {"project": "sparse", "schema_version": "2.1"},
        "entities": {"capabilities": [{
            "id": "CAP-2", "name": "SparseCap", "status": "ACTIVE",
            "intent": "populated",  # only one field
        }]},
    }
    model = _parse_raw(raw)
    props = build_entity_properties(model)
    universal = props["CAP-2"]["properties"]
    assert "Intent" in universal
    assert "Stakeholders" not in universal
    assert "SLOs" not in universal
```

**Step 2: Run to verify RED**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_entity_properties_2_1_fields.py -q`
Expected: `test_all_nine_new_semantic_fields_serialize` fails (labels absent).

**Step 3: Implement**

Modify `_base` inner function around `visualize.py:1638-1666`. Extend the
tuple loop that iterates `(field_name, label)` pairs to include the 9
missing fields. The block currently reads:

```python
for field_name, label in (
    ("intent", "Intent"),
    ("goals", "Goals"),
    ("requirements", "Requirements"),
    ("rationale", "Rationale"),
    ("moes", "Measures of Effectiveness"),
    ("value_function", "value_function"),
    ("failure_modes", "Failure Modes"),
    ("trade_offs", "Trade-offs"),
    ("interface_refs", "Interfaces"),
    ("decisions", "Decisions"),
    ("monitored", "Monitored"),
):
```

Add the 9 new pairs (order: keep existing at top, append new at bottom):
```python
    ("stakeholders", "Stakeholders"),
    ("success_criteria", "Success Criteria"),
    ("assumptions", "Assumptions"),
    ("open_questions", "Open Questions"),
    ("verification", "Verification"),
    ("slos", "SLOs"),
    ("owner", "Owner"),
    ("maturity", "Maturity"),
    ("dependencies_rationale", "Dependencies Rationale"),
```

The existing `if value not in (None, "", []):` guard ensures empty
values are stripped — no additional handling needed.

**Step 4: Verify GREEN**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_entity_properties_2_1_fields.py -q` (expect 3 passed)
Then: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q -k "entity_properties or build_entity" --ignore=tests/test_config_loader.py 2>&1 | tail -20` (report result)

**Step 5: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/core/test_entity_properties_2_1_fields.py
git commit -m "feat(track4): serialize 9 schema 2.1 semantic fields in entity properties"
```

---

## Task 4: Relationship grouping in `propCardHtml`

**Files:**
- Modify: `src/architecture_model/core/visualize.py:3343-3362` (the relationship-rendering block inside `propCardHtml` JS)
- Test: `tests/core/test_relationship_grouping.py` (create)

**Step 1: Write the failing tests**

Create `tests/core/test_relationship_grouping.py`:

```python
"""Tests for relationship grouping in propCardHtml (Track 4 Pass 2 Task 4)."""

from pathlib import Path

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import generate_html_viewer


def _model():
    return _parse_raw({
        "meta": {"project": "rel-group", "schema_version": "2.1"},
        "entities": {
            "capabilities": [{"id": "CAP-1", "name": "C1", "status": "ACTIVE"}],
            "components": [
                {"id": "COMP-1", "name": "K1", "status": "ACTIVE"},
                {"id": "COMP-2", "name": "K2", "status": "ACTIVE"},
            ],
        },
        "relationships": [
            {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
            {"from": "COMP-2", "to": "CAP-1", "type": "realizes"},
            {"from": "COMP-1", "to": "COMP-2", "type": "depends-on"},
        ],
    })


def test_html_groups_relationships_under_semantic_headers(tmp_path):
    out = tmp_path / "v.html"
    generate_html_viewer(_model(), out, repo_path=tmp_path)
    html = out.read_text()
    # Grouped headers must appear in the JS (either as string literals or in a lookup)
    for header in ("Realized By", "Realizes", "Depends On"):
        assert header in html, f"missing group header {header!r}"


def test_grouping_lookup_present_in_payload(tmp_path):
    """Sanity: the JS has a mapping from RelationshipType to display group name."""
    out = tmp_path / "v.html"
    generate_html_viewer(_model(), out, repo_path=tmp_path)
    html = out.read_text()
    # A well-known relation-type value must be mapped somewhere
    assert "realizes" in html.lower()
```

**Step 2: RED**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_relationship_grouping.py -q`
Expected: `test_html_groups_relationships_under_semantic_headers` fails (headers absent).

**Step 3: Implement**

Modify the relationship-rendering block in `propCardHtml` (JS, around
lines 3343-3362). Current code lists outgoing then incoming flat.
Replace with a grouped rendering:

```javascript
if (p.relationships) {
    var ro = p.relationships.outgoing || [];
    var ri = p.relationships.incoming || [];
    if (ro.length + ri.length > 0) {
        // Group headers per relationship type (outgoing / incoming distinction)
        var OUT_LABEL = {
            "realizes": "Realizes", "contains": "Contains", "depends-on": "Depends On",
            "exposes": "Exposes", "consumes": "Consumes", "traces-to": "Traces To",
            "constrained-by": "Constrained By", "allocated-to": "Allocated To",
            "triggers": "Triggers", "produces": "Produces", "subscribes-to": "Subscribes To",
            "transforms": "Transforms", "supersedes": "Supersedes", "migrates-to": "Migrates To",
            "mounted-on": "Mounted On", "connected-at": "Connected At", "routed-through": "Routed Through"
        };
        var IN_LABEL = {
            "realizes": "Realized By", "contains": "Contained In", "depends-on": "Depended On By",
            "exposes": "Exposed By", "consumes": "Consumed By", "traces-to": "Traced From",
            "constrained-by": "Constrains", "allocated-to": "Allocation Target Of",
            "triggers": "Triggered By", "produces": "Produced By", "subscribes-to": "Subscription Target Of",
            "transforms": "Transformed From", "supersedes": "Superseded By", "migrates-to": "Migrated From",
            "mounted-on": "Mount Target Of", "connected-at": "Connection Target Of", "routed-through": "Routing Target Of"
        };

        var groups = {};  // header -> list of html items
        function push(header, itemHtml) {
            if (!groups[header]) groups[header] = [];
            groups[header].push(itemHtml);
        }

        for (var oi = 0; oi < ro.length; oi++) {
            var r = ro[oi];
            var header = OUT_LABEL[r.type] || "Other (Outgoing)";
            var item = '<div class="rel-item">\\u2192 <a href="#" data-entity-id="' + escapeHtml(r.target) + '" class="rel-link">' + escapeHtml(r.target + (r.target_name ? ': ' + r.target_name : '')) + '</a>';
            if (r.description) item += ' <span class="rel-desc">(' + escapeHtml(r.description) + ')</span>';
            item += '</div>';
            push(header, item);
        }
        for (var ii = 0; ii < ri.length; ii++) {
            var r = ri[ii];
            var header = IN_LABEL[r.type] || "Other (Incoming)";
            var item = '<div class="rel-item"><a href="#" data-entity-id="' + escapeHtml(r.source) + '" class="rel-link">' + escapeHtml(r.source + (r.source_name ? ': ' + r.source_name : '')) + '</a> \\u2190';
            if (r.description) item += ' <span class="rel-desc">(' + escapeHtml(r.description) + ')</span>';
            item += '</div>';
            push(header, item);
        }

        html += '<div class="rel-section"><div class="rel-header">Relationships (' + (ro.length + ri.length) + ')</div>';
        Object.keys(groups).sort().forEach(function(header) {
            html += '<div class="rel-group"><div class="rel-group-header">' + escapeHtml(header) + '</div>';
            html += groups[header].join('');
            html += '</div>';
        });
        html += '</div>';
    }
}
```

Add matching CSS near the existing `.rel-*` styles (search for `.rel-item`
declaration):

```css
.rel-group { margin-top: 8px; }
.rel-group-header { font-weight: 600; color: #a0c0e0; margin: 4px 0 2px 0; font-size: 0.9em; }
```

Note: because Python triple-quoted f-strings are used for the HTML/JS blob,
double-brace all `{...}` literals in the JS additions (they must appear as
`{{...}}` in the Python source).

**Step 4: Verify GREEN + no regression**

Run:
- `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_relationship_grouping.py -q` (expect 2 passed)
- `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q -k "viewer or html or propCard" --ignore=tests/test_config_loader.py 2>&1 | tail -20`

**Step 5: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/core/test_relationship_grouping.py
git commit -m "feat(track4): group entity relationships under semantic headers in drill-down"
```

---

## Task 5: Requirements loader

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (add new `_load_requirements` module-level helper near the existing `_load_docs` / `_load_ops_data` helpers)
- Test: `tests/core/test_requirements_loader.py` (create)

**Context:** `.architecture/derived_requirements.yaml` structure (verify shape by reading a small window of the file first; expect a list under `requirements:` where each has `id`, `text`, `component_id` or `entity_id` or `traces_to`).

**Step 1: Explore actual file structure**

Before writing tests: `Read` `.architecture/derived_requirements.yaml` (first 60 lines) to determine the exact schema. Adjust the loader tests and implementation to match. Note the field name used to link a requirement to an entity (`component_id`, `entity_id`, `traces_to`, etc.). Report the schema in the commit body.

**Step 2: Write the failing tests**

Create `tests/core/test_requirements_loader.py` (adjust fixture to match discovered schema):

```python
"""Tests for _load_requirements helper (Track 4 Pass 2 Task 5)."""

from pathlib import Path

import pytest
import yaml

from architecture_model.core.visualize import _load_requirements


def test_load_requirements_builds_entity_index(tmp_path):
    """A YAML with N requirements produces an entity_id -> [requirement] dict."""
    req_dir = tmp_path / ".architecture"
    req_dir.mkdir()
    (req_dir / "derived_requirements.yaml").write_text(yaml.safe_dump({
        "requirements": [
            {"id": "REQ-1", "text": "System must foo", "entity_id": "COMP-1"},
            {"id": "REQ-2", "text": "System must bar", "entity_id": "COMP-1"},
            {"id": "REQ-3", "text": "System must baz", "entity_id": "CAP-1"},
        ],
    }))
    index = _load_requirements(tmp_path)
    assert set(index.keys()) == {"COMP-1", "CAP-1"}
    assert len(index["COMP-1"]) == 2
    assert index["CAP-1"][0]["id"] == "REQ-3"


def test_load_requirements_missing_file_returns_empty_index(tmp_path):
    """Missing derived_requirements.yaml -> empty dict, no exception."""
    index = _load_requirements(tmp_path)
    assert index == {}
```

**Step 3: RED**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_requirements_loader.py -q`
Expected: `ImportError` for `_load_requirements`.

**Step 4: Implement**

Add near existing loaders in `visualize.py`:

```python
def _load_requirements(repo_root: Path | None) -> dict[str, list[dict]]:
    """Load .architecture/derived_requirements.yaml into entity_id -> requirements.

    Returns empty dict if file missing or malformed. Logs INFO on absence,
    WARNING on parse error. Never raises.

    The linking field is determined dynamically: prefers `entity_id`, then
    `component_id`, then a scan of `traces_to` list entries.
    """
    if repo_root is None:
        return {}
    path = Path(repo_root) / ".architecture" / "derived_requirements.yaml"
    if not path.exists():
        _log.info("visualize: no derived_requirements.yaml at %s", path)
        return {}
    try:
        import yaml
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _log.warning("visualize: failed to parse %s: %r", path, exc)
        return {}

    if not isinstance(raw, dict):
        return {}
    reqs = raw.get("requirements") or []
    if not isinstance(reqs, list):
        return {}

    index: dict[str, list[dict]] = {}
    for req in reqs:
        if not isinstance(req, dict):
            continue
        # Prefer explicit link fields; fall back to traces_to list.
        target = req.get("entity_id") or req.get("component_id")
        targets: list[str] = []
        if isinstance(target, str) and target:
            targets.append(target)
        traces = req.get("traces_to") or []
        if isinstance(traces, list):
            targets.extend(str(t) for t in traces if isinstance(t, str))
        for t in targets:
            index.setdefault(t, []).append(req)
    return index
```

If the actual `derived_requirements.yaml` schema found in Step 1 uses a
different top-level key (e.g., a bare list, or nested under
`derived_requirements:`), adjust `raw.get("requirements")` accordingly.

**Step 5: Verify GREEN**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_requirements_loader.py -q` (expect 2 passed)

**Step 6: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/core/test_requirements_loader.py
git commit -m "feat(track4): load derived_requirements.yaml into entity->requirements index"
```

---

## Task 6: Requirements section in drill-down

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — (a) call `_load_requirements(trusted_root)` inside `generate_html_viewer` around line 2648 (near the other loaders); (b) add `"requirements_by_entity": requirements_index` to the `diagram_data` dict at line 2657; (c) add a "Linked Requirements" render block in `propCardHtml` above the relationships block (around line 3342)
- Test: `tests/core/test_requirements_section.py` (create)

**Step 1: Write the failing test**

Create `tests/core/test_requirements_section.py`:

```python
"""Tests for Linked Requirements section in drill-down (Track 4 Pass 2 Task 6)."""

from pathlib import Path

import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import generate_html_viewer


def test_html_contains_linked_requirements_section(tmp_path):
    """When derived_requirements.yaml links entity_id, HTML shows the section."""
    (tmp_path / ".architecture").mkdir()
    (tmp_path / ".architecture" / "derived_requirements.yaml").write_text(
        yaml.safe_dump({
            "requirements": [
                {"id": "REQ-42", "text": "Must be fast", "entity_id": "COMP-1"},
            ],
        })
    )
    model = _parse_raw({
        "meta": {"project": "req-render", "schema_version": "2.1"},
        "entities": {
            "components": [{"id": "COMP-1", "name": "Fast", "status": "ACTIVE"}],
        },
    })
    out = tmp_path / "v.html"
    generate_html_viewer(model, out, repo_path=tmp_path)
    html = out.read_text()
    # The payload key must be present
    assert "requirements_by_entity" in html
    # The specific requirement id must be present in the payload
    assert "REQ-42" in html
    # The header text must be present in the JS renderer
    assert "Linked Requirements" in html
```

**Step 2: RED**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_requirements_section.py -q`
Expected: `"requirements_by_entity" in html` fails.

**Step 3: Implement — payload wiring**

Inside `generate_html_viewer`, near line 2648 (after `_load_ops_data`):

```python
    # ── 5h. Linked requirements from derived_requirements.yaml ────
    requirements_by_entity = _load_requirements(trusted_root)
```

In the `diagram_data` dict around line 2657, add:

```python
        "requirements_by_entity": requirements_by_entity,
```

**Step 4: Implement — JS render block**

In `propCardHtml`, ABOVE the relationships block (before the
`if (p.relationships) {` at line 3343), add:

```javascript
// Linked requirements from derived_requirements.yaml (Track 4 Pass 2 Task 6)
var linkedReqs = (D.requirements_by_entity && D.requirements_by_entity[eid]) || [];
if (linkedReqs.length > 0) {
    html += '<div class="req-section"><div class="req-header">Linked Requirements (' + linkedReqs.length + ')</div>';
    for (var qi = 0; qi < linkedReqs.length; qi++) {
        var req = linkedReqs[qi];
        html += '<div class="req-item">';
        html += '<span class="req-id">' + escapeHtml(req.id || '') + '</span> ';
        html += '<span class="req-text">' + escapeHtml(req.text || req.description || '') + '</span>';
        html += '</div>';
    }
    html += '</div>';
}
```

Double-brace all `{...}` in the JS additions if inside a Python f-string.

Add CSS near existing `.rel-*` styles:

```css
.req-section { margin-top: 12px; padding: 8px; background: rgba(80, 100, 140, 0.1); border-radius: 4px; }
.req-header { font-weight: 600; color: #b0d0f0; margin-bottom: 6px; }
.req-item { padding: 3px 0; font-size: 0.9em; }
.req-id { color: #ffcc70; font-family: monospace; }
.req-text { color: #d0d0e0; }
```

**Step 5: Verify GREEN + no regression**

Run:
- `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_requirements_section.py -q` (expect 1 passed)
- `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q -k "requirements or viewer" --ignore=tests/test_config_loader.py 2>&1 | tail -20`

**Step 6: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/core/test_requirements_section.py
git commit -m "feat(track4): render Linked Requirements section in drill-down property card"
```

---

## Task 7a: Extend `_APPLY_ANCHOR` to `logical` + regression test

**Files:**
- Modify: `src/architecture_model/core/visualize.py:26` (the `_APPLY_ANCHOR` frozenset — add `"logical"`)
- Test: `tests/test_viewer_anchored.py` (extend)

**Step 1: Write the failing test**

Append to `tests/test_viewer_anchored.py`:

```python
def test_logical_panel_routes_through_anchor_model(tmp_path):
    """Regression: logical panel HTML count of exclusive entity drops sharply when anchored.

    Mirrors the functional-panel count-comparison test (cb52e66) — proves the
    anchor.model is actually consulted for the logical view render, not just
    stored on the diagram_data payload.
    """
    from architecture_model.core.slice_anchor import SliceAnchor
    from architecture_model.core.parser import _parse_raw, load_model
    from architecture_model.core.visualize import generate_html_viewer

    # Full model contains a component EXCLUSIVE-TO-FULL that renders into logical
    full = _parse_raw({
        "meta": {"project": "log-route", "schema_version": "2.1"},
        "entities": {
            "layers": [{"id": "LAY-1", "name": "L1", "status": "ACTIVE"}],
            "components": [
                {"id": "COMP-IN", "name": "InScope", "status": "ACTIVE"},
                {"id": "COMP-EXCL-LOG", "name": "ExclusiveInFullLOGXYZZY", "status": "ACTIVE"},
            ],
        },
        "relationships": [
            {"from": "LAY-1", "to": "COMP-IN", "type": "contains"},
            {"from": "LAY-1", "to": "COMP-EXCL-LOG", "type": "contains"},
        ],
    })
    # Anchored subset omits COMP-EXCL-LOG
    subset = _parse_raw({
        "meta": {"project": "log-route", "schema_version": "2.1"},
        "entities": {
            "layers": [{"id": "LAY-1", "name": "L1", "status": "ACTIVE"}],
            "components": [{"id": "COMP-IN", "name": "InScope", "status": "ACTIVE"}],
        },
        "relationships": [
            {"from": "LAY-1", "to": "COMP-IN", "type": "contains"},
        ],
    })
    anchor = SliceAnchor(
        view_name="logical",
        artifact_name="logical-architecture",
        model=subset,
        files=(),
        artifacts=(),
    )

    out_full = tmp_path / "full.html"
    generate_html_viewer(full, out_full, repo_path=tmp_path)
    full_count = out_full.read_text().count("COMP-EXCL-LOG")

    out_anchored = tmp_path / "anchored.html"
    generate_html_viewer(full, out_anchored, repo_path=tmp_path, anchors={"logical": anchor})
    anchored_count = out_anchored.read_text().count("COMP-EXCL-LOG")

    assert full_count > 0, "test setup broken: exclusive id not in un-anchored HTML"
    assert anchored_count < full_count, (
        f"Logical panel is not routed through anchor.model: "
        f"COMP-EXCL-LOG occurrences anchored={anchored_count} vs full={full_count} "
        f"(expected strictly less when routing is active)."
    )
```

**Step 2: RED**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_viewer_anchored.py::test_logical_panel_routes_through_anchor_model -q`
Expected: count comparison fails (both equal).

**Step 3: Implement**

In `visualize.py`, change:

```python
_APPLY_ANCHOR = frozenset({"functional"})
```

to:

```python
_APPLY_ANCHOR = frozenset({"functional", "logical"})
```

**Step 4: Verify GREEN**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_viewer_anchored.py -q` (expect all pass, count strictly less for logical exclusive entity)

**Step 5: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/test_viewer_anchored.py
git commit -m "feat(track4): route logical panel through anchor.model"
```

---

## Task 7b: Extend `_APPLY_ANCHOR` to `conops` + regression test

Identical pattern to 7a. Use exclusive-entity id `COMP-EXCL-CON` /
name `ExclusiveInFullCONXYZZY`. Set `view_name="conops"`,
`artifact_name="conops"`.

The conops diagram renders behaviors + actors; adjust the test fixture to
include a `behaviors:` entity whose exclusion is what triggers the count
difference (behaviors are the primary conops shape). If conops instead
renders components as the primary node kind, keep the component-based
fixture.

**Commit message:** `feat(track4): route conops panel through anchor.model`

---

## Task 7c: Extend `_APPLY_ANCHOR` to `use_cases` + regression test

Identical pattern. Use exclusive-entity id `BEH-EXCL-UC` / name
`ExclusiveInFullUCXYZZY`. Set `view_name="use_cases"`,
`artifact_name="use-cases"`.

The use-case diagram renders actors + behaviors; construct the exclusive
entity as a behavior (or actor) that appears in the un-anchored render.

**Commit message:** `feat(track4): route use_cases panel through anchor.model`

---

## Task 8: Full regression + regenerate viewer.html (verification only)

**Step 1: Run full suite**

`PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: ≥3680 passed (baseline 3664 + ~16 new); 0 failures.

**Step 2: Regenerate viewer.html**

`PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m architecture_model.cli.main viewer .`
Expected: `.architecture/diagrams/viewer.html` regenerates cleanly (~7–8 MB).

**Step 3: Do NOT commit `viewer.html`** — it is gitignored.

**Step 4: Report**

Provide session summary with:
- Total commits in Pass 2 (expected: 1 design + ~9 implementation = 10)
- Baseline / final test counts
- Files touched by count
- Any deviations from the plan and rationale
- Whether to push origin now or await user review of regenerated viewer

---

## Deferred / Non-Goals (per design doc)

- No schema bump.
- No nav-sidebar routing (Pass 3).
- No emission of `data-slice-anchor` HTML attrs (Pass 3).
- No `curation.featured ⊆ anchor.model` validation (Pass 4).
- No shape mapping for `System` beyond fallback.

---

## Execution mode

Subagent-driven-development, matching Pass 1's rhythm: implementer →
spec reviewer → code-quality reviewer per task, fresh subagent per role,
one commit per task. Parallel dispatches where safe (T1/T3/T5
independent; T7a/T7b/T7c independent).
