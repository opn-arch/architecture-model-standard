# Complete Viewer Data Surfacing

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface ALL available data in the HTML viewer — rich entity fields, relationship descriptions, SE documents, component specs, and operational artifacts. Everything embedded inline for self-contained viewing.

**Architecture:** Extend `build_entity_properties()` for rich fields, add relationship descriptions to property cards, embed markdown docs as HTML, add new sidebar sections for documents and operational artifacts.

---

### Task 1: Enrich Property Cards with All Model Fields

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — `build_entity_properties()` (~line 1324)
- Test: `tests/test_viewer_v3.py`

**Changes by entity type:**

**Capabilities** — add:
- `intent` (string)
- `moes` (list → join with newlines)

**Components** — add:
- `intent` (string)
- `goals` (list)
- `trade_offs` (list)
- `failure_modes` (list)
- `contract` (string)
- `kind` (string)

**Actors** — add:
- `intent` (string)

**Requirements** — add:
- `text` (string — the actual requirement statement)

**Constraints** — add:
- `value` (string)

**Interfaces** — add:
- `interface_type` (string)
- `methods` (list of signature strings)
- `component_id` (string)

**Behaviors** — add:
- `steps` (list)
- `actor_id` (string)
- `behavior_type` (string)

**Systems** — add:
- `description` (string)

**Property card display:** Lists render as `<ul>` items. Strings render as `<p>` text.

**Test:** Verify `build_entity_properties` returns `intent` for CAP-1, `text` for REQ-1, `goals` for COMP-1, `methods` for interfaces.

---

### Task 2: Relationship Descriptions on Entity Cards

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — `build_entity_properties()` and `showEntity` JS function
- Test: `tests/test_viewer_v3.py`

**Approach:** Add a `relationships` key to each entity's property dict containing:
```json
{
  "outgoing": [{"type": "realizes", "target": "CAP-1", "description": "..."}],
  "incoming": [{"type": "depends-on", "source": "COMP-2", "description": "..."}]
}
```

In the JS `showEntity` function, render these as a "Relationships" section below the property card, before facet diagrams. Each relationship shown as a clickable link to the target/source entity.

---

### Task 3: Embed SE Documents

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — `generate_html_viewer()` and new `_load_se_docs()` helper
- Test: `tests/test_html_viewer.py`

**Data sources:**
1. `.architecture-models/docs/se/*.md` — 17 SE docs
2. `.architecture/docs/components/*.md` — 29 component specs

**Approach:**
- New helper `_load_docs(repo_path)` reads all .md files, converts to HTML using a simple markdown→HTML converter (just headers, paragraphs, lists, code blocks — no external dependency)
- Embed as `D.docs = {"se": {"conops": "<html>...", ...}, "components": {"COMP-1": "<html>...", ...}}`
- Add "Documents" section to sidebar with two expandable categories: "SE Documents" and "Component Specs"
- Clicking a doc title shows it in the content area with breadcrumbs
- New JS function `showDoc(category, name)` renders the embedded HTML

---

### Task 4: Embed Operational Artifacts

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — `generate_html_viewer()` and new `_load_ops_data()` helper

**Data sources:**
1. `.architecture/devlog.jsonl` — structured decision log
2. `.architecture-models/derived_requirements.yaml` — auto-derived requirements
3. `.architecture/gap-analysis-report.md` — gap analysis
4. `.architecture/validation.json` — validation results

**Approach:**
- New helper `_load_ops_data(repo_path)` reads these files
- Devlog: parse JSONL, embed as structured data, render as timeline cards
- Derived requirements: parse YAML, show as table
- Gap analysis: convert markdown to HTML
- Validation: parse JSON, show score + issues
- Add "Intelligence" section to sidebar
- New JS function `showOps(artifact_name)` renders each artifact

---

### Task 5: Run Full Suite, Regenerate, Push

- Full test suite: expect 7 pre-existing failures, ~1760+ passed
- Regenerate viewer
- Validate JS syntax with `node --check`
- Zip to ~/Desktop/architecture-viewer.zip
- Commit and push

**Expected viewer size:** ~600-800KB HTML (~100-130KB zipped)
