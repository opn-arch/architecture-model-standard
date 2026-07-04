# Architecture Decisions

Key design decisions made during development of the Architecture Model Standard.

---

## ADR-001: Standalone Package vs Monorepo Module

**Context:** The architecture model logic lived inside `logs-db/scripts/_architecture_model/`. As more projects needed architectural analysis, coupling to logs-db became a bottleneck.

**Decision:** Extract to a standalone package (`architecture-model-standard`) installed as an editable dependency back into logs-db.

**Consequences:**
- Any project can `pip install` the package and get architecture tooling
- logs-db consumers (`_pipeline_manifest.py`, `_pipeline_artifacts.py`) import from `architecture_model` instead of `scripts._architecture_model`
- Two repos to maintain, but clear separation of concerns
- Import rewrite: all internal imports use absolute `architecture_model.*` paths

---

## ADR-002: Full Architecture Model as Authoritative Source (Option B)

**Context:** Two options for how the architecture model relates to the reality manifest:
- Option A: Model supplements manifest (manifest is source of truth)
- Option B: Model is authoritative (manifest provides ground truth validation)

**Decision:** Option B — the Architecture Model is the authoritative architectural description. The reality manifest supplements it with verified ground truth from code.

**Consequences:**
- When model and manifest disagree, the model defines intent; manifest reveals drift
- Validation checks `[ACTIVE]` claims in the model against manifest evidence
- `[PLANNED]` and `[DORMANT]` claims are not validated against code
- Artifacts are generated FROM the model, not from raw manifest data

---

## ADR-003: Self-Bootstrapping (No Manual Config Prerequisite)

**Context:** Early design required users to manually write `.architecture-model.yaml` before the pipeline could analyze their project. This created a chicken-and-egg problem for new projects.

**Decision:** The pipeline MUST be fully self-bootstrapping. `architecture-model init` auto-generates the config from directory structure. Users can edit AFTER auto-generation, never before.

**Algorithm:**
1. Find source root (src-layout → flat-layout → lib-layout fallback)
2. Each immediate subpackage with `.py` files becomes an F-block
3. Names derived from directory names; descriptions from `__init__.py` docstrings
4. Layers derived from F-block directories when no heuristic layers match
5. Metrics discovered from common directory patterns (routers, models, migrations, templates)

**Consequences:**
- Zero-config pipeline operation for any Python project
- Generated config is a starting point — human editing improves it
- Subsequent `init` runs will NOT overwrite manual changes (requires `--force`)
- The `synthesize` stage can refine the config with LLM-derived groupings (replaces auto-discovered blocks with richer LLM-synthesized ones, but preserves manual blocks)

---

## ADR-004: Configurable Functional Blocks (Not Hard-Coded)

**Context:** Initially, 6 functional blocks were hard-coded in the manifest generator, mapping specific directories to specific F-block IDs. This broke for any project that wasn't logs-db.

**Decision:** F-blocks are defined in `.architecture-model.yaml` and loaded dynamically. The hard-coded mapping was removed.

**Consequences:**
- Any project structure works (not just FastAPI + scripts layout)
- The `fblock_dict` property on `ProjectConfig` provides the runtime mapping
- Manifest generator iterates `config.fblock_dict` instead of a constant
- Block status (`active`/`dormant`) is determined by whether files exist and have content

---

## ADR-005: Status Markers on All Functional Claims

**Context:** Architectural documents describe both what EXISTS and what is PLANNED. Validating planned features against code produces false failures.

**Decision:** All entities carry a status: `[ACTIVE]`, `[PLANNED]`, or `[DORMANT]`. The validator ONLY checks `[ACTIVE]` claims against code evidence.

**Consequences:**
- `[ACTIVE]` = must have code evidence (files exist, functions present)
- `[PLANNED]` = aspirational, no validation against code
- `[DORMANT]` = was active, currently unused (code may exist but isn't exercised)
- Validation failures only count against ACTIVE claims
- Status can be auto-detected: if F-block has 0 active sub-functions → `dormant`

---

## ADR-006: Synthesis Bridge (Auto-Write Config After LLM Synthesis)

**Context:** The `synthesize` pipeline stage produces rich architectural JSON (subsystems, function blocks, interfaces) via LLM. This information was only stored in the DB, never written back to the project's config file.

**Decision:** After successful synthesis, automatically write/refine `.architecture-model.yaml` using `_write_architecture_config()` in `_pipeline_synthesize.py`.

**Merge strategy:**
- If existing blocks are all "auto-discovered" → replace with LLM-synthesized (better quality)
- If existing blocks have manual descriptions → preserve them (don't overwrite human work)
- If no blocks exist → add LLM-synthesized blocks
- Wrapped in try/except — failures are non-fatal (logged as warnings)

**Consequences:**
- Pipeline is fully circular: code → synthesis → config → manifest → artifacts
- First run produces basic config; subsequent runs refine it
- Human edits are respected and preserved
- The config file improves automatically over time as the LLM understands the project better

---

## ADR-007: Metric Labels Must Be Singular

**Context:** Metric keys in the manifest were inconsistently named (`routers` vs `router_count`). Pipeline consumers expected specific key patterns.

**Decision:** All metric labels are SINGULAR (`router`, `model`, `migration`, `template`). The manifest appends `_count` to produce keys like `router_count`.

**Consequences:**
- Consistent key naming: `{label}_count`
- `display.py` uses dynamic metric discovery (doesn't hard-code expected keys)
- Projects without standard metrics (no routers, no migrations) display "(no standard metrics detected)" instead of crashing

---

## ADR-008: PDF Generation via Headless Chrome

**Context:** Artifacts contain PlantUML and Mermaid diagrams. Users need print-quality PDFs with rendered graphics. Node/npm are broken in this environment.

**Decision:** Use headless Chrome (`--print-to-pdf`) with `--virtual-time-budget=10000` to allow Mermaid JS (loaded from CDN) to render before PDF capture.

**Pipeline:**
1. Markdown → HTML (PlantUML rendered to inline SVG via jar, Mermaid as `<pre class="mermaid">` with CDN JS)
2. HTML → PDF (headless Chrome with `--run-all-compositor-stages-before-draw`)

**Consequences:**
- No new Python dependencies (Chrome is already installed)
- Mermaid renders correctly (JS executes in browser context)
- PlantUML renders as crisp SVG (rasterization-free)
- `--no-pdf-header-footer` produces clean output
- Command: `python -m scripts.render_plantuml <files> --out-dir <dir> --pdf`
