# Architecture Model Standard

## Origin

Extracted from the `scripts/_architecture_model/` package within the [logs-db](../logs_db/) Knowledge OS project. Became a standalone installable package to enable reuse across multiple projects without coupling to the logs-db codebase.

## Purpose

A universal, machine-readable **Architecture-as-Code** standard that serves as the architectural spine for LLM-driven system engineering. It provides:

- A **YAML schema** describing any software system's architecture (entities, relationships, constraints)
- A **Reality Manifest** generator that produces ground-truth inventories via AST scanning
- A **validation engine** that checks architectural claims against code reality
- An **LLM integration protocol** enabling AI agents to load, query, and update architectural models
- **Self-bootstrapping** configuration — no manual setup required; `architecture-model init` auto-generates the project descriptor from directory structure

## Role in the Three-Repo Architecture

This package is the **schema + library layer** in a three-repo system:

```
architecture-model-standard (this repo)     — Schema, validator, CLI, manifest generator
        ↑ dependency
opencode-arch (../opencode-arch/)           — MCP extension wrapping these APIs
        ↑ used by
OpenCode agent (frontier model)             — Consumes compressed context, produces models

arch-agent (../arch-agent/)                 — Training pipeline + surrogate (future)
        ↑ dependency
architecture-model-standard (this repo)
```

**Core flow:**
```
Code → [AST Scan] → Reality Manifest → [Context Formatter] → Agent → [Validator] → .architecture-model.yaml
```

The `opencode-arch` MCP server wraps this package's APIs:
- `generate_manifest()` → `architect_scan` tool
- `format_model_context()` / slicer → `architect_slice` tool
- `validate_model()` → `architect_validate` tool
- `_parse_raw()` → used by `architect_extract` for storage

## Key Capabilities

### Schema (7 Entity Types)
- **Actors** — external agents that interact with the system
- **Capabilities** — functional blocks (F-blocks) the system provides
- **Behaviors** — use cases, workflows, operational sequences
- **Interfaces** — APIs, protocols, data exchanges between components
- **Constraints** — non-functional requirements, design rules
- **Layers** — architectural tiers (web, services, data, pipeline)
- **Components** — deployable units, modules, packages

### Relationships (17 Types)
- `realizes` — component realizes a capability
- `contains` — layer/component/capability/behavior contains sub-entity
- `depends-on` — component depends on another
- `exposes` — component exposes an interface
- `consumes` — actor consumes an interface
- `traces-to` — component traces to a behavior
- `allocated-to` — entity allocated to a target
- `constrained-by` — entity constrained by a constraint
- `triggers` — behavior triggers another behavior (cross-block flow)
- `mounted-on` / `connected-at` / `routed-through` — spatial
- `produces` / `subscribes-to` / `transforms` — data/event flow
- `supersedes` / `migrates-to` — lifecycle

### LLM Protocol (6 Verbs)
- **LOAD** — parse and internalize the architecture model
- **QUERY** — answer structural questions about the system
- **IMPACT** — trace change impact through relationships
- **VALIDATE** — check claims against the model
- **UPDATE** — propose model modifications
- **PROJECT** — forecast effects of planned changes

### Self-Bootstrapping
The 10-stage pipeline requires no manual configuration to analyze a new project:
1. `architect_pipeline(repo_path, stage="observe")` — AST-scans all source files
2. Discovers modules, imports, routes, constraints, tests, docs
3. Subsequent stages (infer → allocate → relate → specify → contract → validate) build the model
4. `decompose` detects system boundaries (components with ≥5 files become autonomous systems)
5. `synthesize` runs scoped sub-pipelines for each detected system
6. `emit` writes all artifacts to `.architecture-models/`

**Entry point:** `architect_pipeline` MCP tool (stage-by-stage) or `architecture-model pipeline <path>` CLI.
The `init` command has been removed — the pipeline is the single entry point.

### Domain Profiles
The standard supports cross-domain architecture modeling via domain profiles:
- **software** (default) — standard software architecture entities
- **controls** — sensors, actuators, PLCs, fieldbus, SIL levels
- **mechanical** — parts, assemblies, materials, tolerances
- **electrical** — PCBs, connectors, power supplies, voltage/current ratings

Profiles extend the base schema with:
- Additional enum values (ComponentKind, InterfaceType, etc.)
- Additional entity properties (validated via JSON Schema fragments)
- Conditional validation rules (e.g., "sensors must declare signal_type")

Usage: Set `domain_profile: controls` in the model meta section.

## Package Structure

```
src/architecture_model/
├── cli/          — CLI commands (validate, slice, diff, stats, impact, manifest, pipeline, etc.)
├── config/       — Configuration loading, auto-discovery, schema definition
├── core/         — Parser, validator, slicer, differ, merger, decomposer, type system
├── extract/      — Extract model from generated Tier 1 artifacts
├── integrations/ — LLM context formatting, pipeline bridge
├── manifest/     — Reality Manifest generator (AST scanning, metrics, blocks, interfaces)
├── pipeline/     — 10-stage modular extraction pipeline (observe→emit) + cache + report + lessons
├── profiles/     — Domain profile system (software, controls, mechanical, electrical)
├── spec/         — JSON Schema for model validation
└── utils/        — Shared utilities (file discovery, exclusion patterns)
```

## Key APIs (used by opencode-arch)

### Manifest Generation
```python
from architecture_model.manifest.generator import generate_manifest
manifest = generate_manifest(project_root: Path) -> Manifest
# Returns: Manifest dataclass with typed fields
# Use manifest.to_dict() for JSON serialization
```

### Model Parsing
```python
from architecture_model.core.parser import load_model, _parse_raw
from architecture_model.core import ParseError   # canonical parse error (also re-exported at package root)
model = load_model(path: Path) -> ArchitectureModel  # from file
model = _parse_raw(raw: dict) -> ArchitectureModel   # from dict (no public string parser)
# ParseError is the canonical exception raised by parser / serialization / package load paths.
```

### Validation
```python
from architecture_model.core.validator import validate_model
result = validate_model(model: ArchitectureModel) -> ValidationResult
# result.score: int (0-100)
# result.issues: list[ValidationIssue]
# result.is_valid: bool
```

### Context Formatting (the token compressor)
```python
from architecture_model.integrations.llm_context import format_model_context, format_fblock_context
context = format_model_context(model, max_tokens=4000, detail_level="standard") -> str
context = format_fblock_context(model, f_block="F1", max_tokens=4000) -> str
```

### Slicing
```python
from architecture_model.core.slicer import slice_by_fblock, slice_by_layer
sliced = slice_by_fblock(model, fblock_id="F1") -> ArchitectureModel
sliced = slice_by_layer(model, layer_id="web") -> ArchitectureModel
```

### Lifecycle (Phase 1 additions, 2026-09-05)
```python
from architecture_model.lifecycle import generation_dir, current_root_digest
# generation_dir(pkg, generation_id) -> Path            # public replacement for _generation_dir (alias preserved)
# current_root_digest(pkg) -> str | None                # reads current generation's digest.json.root_digest

from architecture_model.lifecycle.package import ArchitecturePackage
pkg.id                                                  # property alias exposing package identifier

from architecture_model.lifecycle.model_slice_materializer import MaterializedSlice
mslice.to_dict()                                        # emits {"fragment": {...}, "slice_id": ..., ...}
```

### AI / Proposal APIs (Phase 1 additions, 2026-09-05)
```python
from architecture_model.ai import apply_model_patch
patched = apply_model_patch(model, proposal)            # add / remove / replace (move → ParseError)

from architecture_model.ai.work_order import WorkOrder
wo = WorkOrder.build(intent=..., input_slice_refs=..., expected_proposal_kinds=..., budget=..., requested_by=...)

from architecture_model.ai.proposals import Provenance
prov = Provenance(...)                                  # proposal_id auto-derived (SHA-256) when omitted
prov.proposal_id                                        # stable identifier for dedup / traceability
```

## Model YAML Format

**Important:** Entities must be nested under the `entities:` key:
```yaml
meta:
  project: my-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: MyComponent
      status: ACTIVE
  capabilities:
    - id: CAP-F1
      name: MyCapability
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
```

## Status

- Schema version: 2.0
- Package version: 0.3.0
- Test suite: 2918 passed (6 pre-existing failures documented)
- CLI entry point: `architecture-model`
- Install: `pip install -e .` (editable) or `pip install architecture-model-standard`

## Phase 1 substrate (model → view mapping)

The Lifecycle spec-driven pipeline
`ModelSlice → materialize → project → render → rebuild_artifacts`
is the single substrate for every doc, diagram, and derived artifact.
Every legacy generator becomes a **registered projector** consumed via
this pipeline; no direct `format_*` calls survive in the artifact path.

Phase 1 lands the substrate + liveness metadata:

- **Projector registry** — `architecture_model.lifecycle.view_projection.projectors` exposes
  a stable `register(name, callable)` / `resolve(name)` API. Adapters wrap existing
  generators (component/use-case/system-boundary diagrams, component spec, ICD,
  SE docs family) so they emit `DiagramSpec` values.
- **DiagramSpec content-kind convention** — Mermaid outputs use
  `id=f"diagram:{name}"`, `facets={"content_kind": "mermaid", "body": body}`;
  prose outputs use `id=f"prose:{name}"`,
  `facets={"content_kind": "markdown", "body": body}`. Multi-entity outputs
  join with `"\n\n---\n\n"`. Phase 2 introduces a proper `ProseSpec` type;
  the facet overload is intentional for Phase 1.
- **Freshness stamping** — `project()` stamps `freshness: "fresh"` and
  `revision: <slice.model_revision>` onto every returned `DiagramSpec`
  (`view_projection.py:189-194`). Provenance is in-memory only for
  Phase 1; per-artifact `<id>.provenance.json` sidecars are deferred to
  Phase 2 Task 28.
- **Descendants coverage** — `materialize()` merges root ∪ descendants
  into a single fragment when the slice's scope includes descendants.
  Per-subsystem **fan-out** (N artifacts, one per descendant with a
  subsystem-slug output path) is deferred to Phase 2 Task 27.

Design + plan docs:

- `docs/plans/2026-09-08-model-view-mapping-design.md` — full design
- `docs/plans/2026-09-08-phase-1-substrate-and-liveness.md` — active plan
- `docs/plans/2026-09-08-phase-2-schema-and-semantic-content.md` — Phase 2 (includes Tasks 27 fan-out + 28 provenance-persistence)
- `docs/plans/2026-09-08-phase-3-*.md`, `docs/plans/2026-09-08-phase-4-*.md` — deferred

## Phase 2 substrate (schema 2.1 + semantic content + feedback)

Phase 2 extends the substrate with semantic fields, supplementary
references, temporal slicing, overlays, and feedback journals. All
additions are **backward-compatible**: every 2.0 fixture continues to
parse and validate unchanged, and empty/None fields are stripped from
digest payloads so pre-Phase-2 hashes stay byte-stable.

**Schema 2.1 (additive).** `meta.schema_version` accepts `'2.0'` and
`'2.1'`. Every entity kind (Component, Capability, Behavior, Interface,
Actor, Constraint, Layer) gains a common bag of optional semantic
fields: `intent`, `goals`, `stakeholders`, `success_criteria`,
`failure_modes`, `trade_offs`, `assumptions`, `open_questions`,
`requirements`, `verification`, `slos`, `owner`, `maturity`,
`dependencies_rationale`. JSON Schema fragments live under `$defs` in
`src/architecture_model/spec/architecture-model.schema.json`.

**Migration CLI.** `architecture-model migrate --to 2.1 <path>` bumps
`meta.schema_version` in-place; no field-level edits required.
`Component.intent` is auto-seeded during pipeline emit from module
docstrings (first non-empty stripped line, capped at 200 chars) when
synthesize left it empty — capability-derived intents from synthesize
(`"Handles queue 0"`, etc.) are preserved.

**Semantic-field rendering.** Projectors surface semantic fields in
component specs, ICDs, and SE docs. Diffs on semantic-only fields
trigger **surgical per-entity invalidation** via
`architecture_model.lifecycle.invalidation.stale_entity_view_ids(diff,
all_view_ids)`, driven by `SEMANTIC_FIELD_RULES` (field name → list of
view prefixes such as `family1.entity_page`, `family1.mission`).
Family-scoped views without an entity suffix are never invalidated by
this path.

**SupplementaryRef + MaterializedSlice.manifest_fragment.**
`SupplementaryRef(kind, uri, digest)` (`SupplementaryKind` = `sil` |
`gates` | `drift` | `test_results`) attaches out-of-model evidence to
a materialized slice. `MaterializedSlice.manifest_fragment` carries a
canonicalized copy of the referenced manifest slice; loaders in
`architecture_model.lifecycle.supplementary_loaders` (`sil`, `gates`,
`drift`, `test_results`) resolve refs at project time.

**Temporal slicing.** `RevisionRange(from_rev, to_rev)` and
`TimeWindow(since, until)` filter supplementary evidence.
`revision_series` and `time_window` slice-spec fields flow through
`materialize()` → `project()` and constrain which journal events end
up in the projected view.

**Overlays.** `ViewCuration.overlays: list[str]` names overlay slots
applied in list order by
`architecture_model.lifecycle.overlays.apply_overlays(view, mslice,
names) -> ProjectedView`. Recognized names live in
`RECOGNIZED_OVERLAYS` (`gates`, `drift`, `sil`, ...). Unknown names
are skipped silently. Output is byte-identical under fixed order
(guarded by `tests/lifecycle/test_overlay_determinism.py`).

**Feedback journals.** Three append-only JSONL streams live under
`.architecture/` in the consuming repo:

- `.architecture/gates.jsonl` — `GateEvent(gate_id, outcome, findings,
  model_revision, ts)`; auto-appended by the OCA `architect_gate` MCP
  tool (fail-soft).
- `.architecture/drift.jsonl` — drift snapshots (`broken_ref`,
  `unrealized_capability`, `orphan`, `missing_impl`); auto-appended
  after every OCA `architect_pipeline` run (fail-soft).
- `.architecture/test_results.jsonl` — `TestResult` batches ingested
  via `architecture_model.feedback.junit_ingest.ingest_junit(path,
  suite=...)` and appended via `test_results.append(repo, batch)`;
  fed by the OCA CLI `opencode-arch feedback ingest-junit <xml>`.

### Hierarchical Model Architecture

Each system has its own complete, self-contained model. The top-level model references subsystem models — it does not contain slices or reduced views.

```
.architecture-model.yaml                    ← top-level system model
.architecture-models/
├── manifest.json                           ← top-level manifest
├── component_test_map.json                 ← test → component allocation
├── derived_requirements.yaml               ← requirements derived from model
├── lessons.md                              ← accumulated pipeline lessons
├── core/                                   ← named subsystem (Core)
│   ├── .architecture-model.yaml
│   └── manifest.json
├── manifest/                               ← named subsystem (Manifest)
├── configuration/                          ← named subsystem
├── cli/                                    ← named subsystem
├── orchestration/                          ← named subsystem
├── extract/                                ← named subsystem
├── pipeline/                               ← named subsystem
├── docs/                                   ← named subsystem
├── documentation/                          ← named subsystem
├── authoring/                              ← named subsystem
├── export/                                 ← named subsystem
├── S0/                                     ← auto-decomposed system (0..15)
├── S1/
├── ...
└── S15/
```

**~27 subsystems total** — 11 named subsystems (Core, Manifest, Configuration, CLI, Orchestration, Extract, Pipeline, Docs, Documentation, Authoring, Export) plus 16 auto-decomposed `S0`..`S15` systems produced by the `decompose` stage when components exceed the ≥5-file threshold.

### Standard Modeling Process

1. **Scan** — `architect_scan` produces AST-based reality manifest (ground truth)
2. **Model** — Build complete, self-contained model per system (capabilities, behaviors, components, interfaces, constraints, relationships)
3. **Manifest** — Generate per-system manifest from AST scan
4. **Enrich** — `architecture-model enrich` copies signatures, constants, test_contracts from manifest onto model components
5. **Visualize** — `generate_all_diagrams()` (in `architecture_model.docs.diagrams`) produces 3 Markdown diagram files per model:
   - `component-diagram.md` — components grouped by layer, `realizes` edges to capabilities
   - `use-case-diagrams.md` — actor → behavior use-case flow
   - `system-boundary-diagram.md` — C4-style system boundary with external actors and interfaces

   (An older `core/visualize.py:generate_all_diagrams()` producing four `.mmd` files still exists but is not the current entry point.)
6. **Validate** — `architecture-model validate` checks structural correctness (score 0-100)

**Understanding levels after each step:**
- Model alone: WHY (capabilities, constraints) + WHAT (behaviors, relationships)
- \+ Manifest: HOW (signatures, classes, imports, call graphs)
- \+ Enrichment: REGEN-READY (body_hints, test_contracts, constants on components)

### Current Model Metrics

| Component | Validate | Regen Score | Sigs | Hints | Consts | Test Contracts |
|-----------|:--------:|:-----------:|:----:|:-----:|:------:|:--------------:|
| Core | 86/100 | 76/100 C | 85 | 85 | — | 131 |
| Manifest | — | 74/100 C | 51 | 51 | — | 76 |
| Pipeline | — | 73/100 C | 40 | 40 | — | 16 |
| Orchestration | — | 70/100 C | 31 | 31 | — | 62 |
| Authoring | — | 70/100 C | 2 | 2 | — | 11 |
| Profiles | — | 70/100 C | 3 | 3 | — | 0 |
| Regen Readiness | — | 68/100 D | 3 | 3 | — | 9 |
| Monitoring | — | 66/100 D | 5 | 5 | — | 5 |
| Persistence | — | 66/100 D | 3 | 3 | — | 8 |
| Extract | — | 65/100 D | 1 | 1 | — | 0 |
| Utils | — | 64/100 D | 4 | 4 | — | 7 |
| Export | — | 62/100 D | 15 | 15 | — | 4 |
| Config | — | 60/100 D | 15 | 15 | — | 1 |
| Docs | — | 58/100 F | 15 | 15 | — | 4 |
| CLI | — | 52/100 F | 1 | 1 | — | 1 |
| Spec | — | 40/100 F | 0 | 0 | — | 0 |
| **TOTAL** | **86/100** | **70/100 C** | **274** | **274** | **156** | **335** |

Previous (2026-07-07): 94 sigs, 11 constants, 339 contracts, no regen scoring.
Current (2026-08-10): 274 sigs (+191%), 156 constants, 335 contracts, Pipeline module covered.

## Phase 3 substrate (recursion + entity views)

Phase 3 extends the substrate with **entity-scoped slicing**, **recursion
controls** on views, **per-entity prose pages** across every doc family,
**drill-down link plumbing** between root-family and entity views, and
**parent+peers invalidation** on entity change. Backward-compatible: no
schema bump (still 2.1); no field changes; existing Phase-2 fixtures parse
and render byte-identically.

**Entity-scoped slicing.** `architecture_model.core.slicer.slice_by_entity(
model, entity_id, *, include_hops=1)` returns the sub-model rooted at
`entity_id`: the entity itself, its transitive `contains` descendants,
and the 1-hop `realizes`/`exposes`/`consumes`/`depends-on` neighborhood.
Unknown ids raise `KeyError`. Wire-level slice YAML gains a new scope
form: `scope: "entity(COMP-3)"` — the materializer parses this via
`parse_entity_scope()`, reduces the base model via `slice_by_entity`
before selectors/closure run, and stamps `scope_metadata` onto the
resulting `MaterializedSlice.provenance`.

**Recursion controls on ViewSpec.** Two new fields:
- `ViewSpec.depth: int | None` — max `contains` hops from the scope root
  when the slice is entity-scoped. `None` = unbounded.
- `ViewSpec.expand_kinds: tuple[str, ...]` — restrict which entity kinds
  are allowed to recurse. Empty tuple = all kinds allowed.

The materializer's `_prune_by_depth()` walks the `contains` graph BFS
from the scope root and drops nodes past `depth`; the parent's kind
must be in `expand_kinds` for recursion to continue past that node.
Ignored for non-entity scopes.

**scope_metadata on MaterializedSlice.provenance.** Populated only for
entity-scoped slices. Computed by
`_compute_entity_scope_metadata(base_model, entity_id)` against the
ORIGINAL model (has ancestors) before slicing. Fields:
`scope_chain: tuple[str, ...]` = `("ROOT", <topmost ancestor>, ..., <entity_id>)`;
`parent: str | None`; `peers: tuple[str, ...]` (sorted);
`roll_up: bool` (False for Phase 3, aggregation projectors flip later);
`scope_entity_id: str`; `scope_entity_kind: str` (singular, e.g.
`"component"`); `inbound_depends_on: tuple[str, ...]`;
`outbound_by_type` / `inbound_by_type: dict[str, tuple[str, ...]]`;
`contains_descendants: tuple[str, ...]` (transitive, sorted).

**ProjectedView carries scope metadata.** `project()` propagates
`scope_chain`, `parent`, `peers`, `roll_up` from the MaterializedSlice
onto the returned `ProjectedView`. Renderers surface these as
breadcrumb navigation — the Markdown renderer emits
`> **Path:** ROOT / A / B / **C**`; the HTML renderer emits
`<nav class="scope-chain">…</nav>` with parent+ancestor links to
`family1.entity_page:<id>` and comma-separated peer links.

**EntityPageProjector convention.** A single projector per family
(`family{1,2,3,4,6,7,8}.entity_page`) dispatches on
`config["__scope_entity_kind"]` via `_project_<kind>` methods. Each
`DiagramSpec` uses `id = f"prose:family{N}.entity_page:{entity_id}"`,
`title = f"{name} ({entity_id})"`, `facets = {"content_kind":
"markdown", "body": <str>}`. Sections use `## Header\n\n<content>`
joined by `\n\n`; empty sections are omitted; order is canonical per
family. `project()` injects `__scope_*` config keys from
`scope_metadata` (entity_id, kind, inbound_depends_on,
outbound_by_type, inbound_by_type, contains_descendants) so
projectors can render roll-ups without re-walking the model.
Family 5 landed in Phase 5 (deployment topology for environments, resources, components).

**Supplementary fragments plumbing.** `project()` unconditionally
injects `__scope_supplementary_fragments = dict(mat.supplementary_fragments)`
when non-empty. `family8.entity_page` reads the `"sil"` key to render
its rollup section; other projectors are unaffected.

**Drill-down metadata on root-family views.** Root-family adapters
(`family3.component_diagram`, `family6.icd`, ...) attach
`facets["drill_to"] = {entity_id: "familyN.entity_page:entity_id"}`
as a sibling of `facets["body"]`. Coverage per family mirrors
`architecture_model.lifecycle.projectors.drill._FAMILY_KINDS`:
`family1` = all seven kinds; `family2` = capabilities/components/behaviors;
`family3` = components/layers; `family4` = behaviors/actors;
`family6` = interfaces/components;
`family7` = components/capabilities/behaviors/interfaces/constraints;
`family8` = components/capabilities/interfaces. Renderers may use
`drill_to` to emit hyperlinks or hover targets; it has no effect on
the rendered body itself.

**Invalidation on entity change.**
`architecture_model.lifecycle.invalidation.entity_change_stale_set(
entity_id, family, model_context)` returns
`{f"family{N}.entity_page:{entity_id}"}` plus the entity's direct
parent, all peers, and `f"family{N}.root"`. Ids use the **colon form**
(`family{N}.entity_page:{entity_id}`) matching `DiagramSpec.id` —
DELIBERATELY DIFFERENT from `stale_entity_view_ids`'s dot form. Do
not mix the two.

Design + plan docs:
- `docs/plans/2026-09-08-phase-3-recursion-and-entity-views.md` — 24-task plan
- `docs/plans/2026-09-08-phase-2-schema-and-semantic-content.md` — Phase 2 (merged)
- `docs/plans/2026-09-08-phase-1-substrate-and-liveness.md` — Phase 1 (merged)
- `docs/plans/2026-09-08-model-view-mapping-design.md` — overall design

## Phase 4 substrate (write-back + endpoints + federated M3)

Phase 4 extends the substrate along three orthogonal axes:
LLM-authored write-back projectors, endpoint-aware Interface subkinds,
and federated (multi-package) slice materialization. All additions are
**backward-compatible**: no schema bump (still 2.1), all existing
fixtures parse/render byte-identically, and the deterministic base
projectors remain the default path.

**Write-back projectors (`.llm` naming enforcement).** A new base class
`architecture_model.lifecycle.projectors.write_back.WriteBackProjector`
wraps a deterministic base projector with an
`architecture_model.llm.LLMProvider`. Concrete variants live in
`architecture_model.lifecycle.projectors.write_back_variants` — one
per family: `Family1MissionLLM`, `Family2FunctionalAnalysisLLM`,
`Family3ComponentSpecLLM`, `Family4UseCasesLLM`, `Family6ICDLLM`,
`Family7RequirementsAnalysisLLM`, `Family8HealthLLM`. Each variant sets
`projector_name = "<base>.llm"` and returns a proposal-shaped `dict`
via `pack_proposal(diagram_spec, config)`. The suffix `.llm` is
**contractual**: the OCA `architect_propose` MCP tool rejects any
projector name without it as `INVALID_ARGUMENT`. Variant classes are
NOT auto-registered in `DEFAULT_REGISTRY` — callers instantiate them
with a provider and dispatch via the tool.

**Endpoint extractors + Interface subkinds.**
`architecture_model.manifest.endpoint_extractor` provides pure-AST
extractors that discover architecturally-significant endpoints in
source: HTTP handlers (Flask/FastAPI/Django), CLI commands (Click,
argparse), message consumers (Celery, Kafka), and RPC entry points.
Output is deterministic (sorted by `(file, lineno, name)`). The
Interface schema gains a `subkind` field via the software domain
profile — recognized values: `http`, `cli`, `message`, `rpc`,
`library`. `Interface.subkind` is **software-profile-scoped** — other
profiles (controls, mechanical, electrical) leave it unset. Endpoint
promotion generates deterministic Interface ids of the form
`IF-{subkind-dashed}-{sha1("subkind|file|name|lineno")[:8]}`.

**Federated (M3) materialization.**
`ModelSlice.child_refs: list[ChildRef]` where
`ChildRef(child_arch_id, revision, ref)` names a child package's
published generation via one of two URI schemes:
* `file://<abs-path>/<child_arch_id>@<revision>`
* `repo://<child_arch_id>@<revision>`
The materializer's new `resolve_ref(ref, root_dir)` helper resolves
both schemes to a `PackageBundle`. Federated slices walk the resulting
child graph, merging descendants into the projected fragment.
`SemanticDiff.children: list[ChildDiffEntry]` (flat list, sort key
`(kind, child_arch_id)`) reports added/removed/revised child packages.
`architecture_model.lifecycle.invalidation.stale_from_federated_children(
children_diff, all_view_ids)` marks M1 roots (`family1.mission`,
`family3.component_diagram`) stale in the parent when a referenced
child publishes a new generation.

**Cross-repo triggers.** Two production-ready templates enable
federated workflows without shared orchestration:
* `docs/templates/child-publish-watcher.sh` — POSIX shell watcher
  using `fswatch` (macOS) / `inotifywait` (Linux) for monorepos.
* `docs/templates/child-publish-webhook.yml` — GitHub Actions workflow
  firing `repository_dispatch` on the parent for multi-repo setups.

**Reference-doc projectors default-on.** The three reference-doc
formats (`cli_reference`, `api_reference`, `plugin_guide`) are wired
into OCA's `architect_docs` `formats='all'` expansion via
`family6.cli_reference`, `family6.api_reference`,
`family6.plugin_guide`. No opt-in flag required.

Design + plan docs:
- `docs/plans/2026-09-08-phase-4-writeback-endpoints-federated.md` — 28-task plan
- `docs/plans/2026-09-08-phase-3-recursion-and-entity-views.md` — Phase 3 (merged)
- `docs/plans/2026-09-08-model-view-mapping-design.md` — overall design

## Phase 5 substrate (deferred completion — deployment views, fan-out, provenance)

Phase 5 closes three deferred sub-tasks from Phases 2 and 3 without
changing any wire-level contracts. Fully backward-compatible: no schema
bump (still 2.1), no digest perturbation, no new required fields.

**Family 5 entity page.** ``Family5EntityPage`` in
``architecture_model.lifecycle.projectors.entity_pages`` renders
deployment topology per entity. Supported kinds:

* ``environment``: kind, region, infrastructure list, constraints list,
  and Deployed Components (inbound ``allocated-to``).
* ``resource``: kind, provider, location, SLA, and Consumed By (inbound
  ``consumes`` ∪ ``depends-on``, deduplicated, sorted).
* ``component``: Deployed To (outbound ``allocated-to``).

The enum-backed ``kind`` field is always emitted (it carries a default);
all other sections are omitted when empty. Closes the latent gap
referenced by ``invalidation.py:146`` which already routes SLO field
edits to ``family5.entity_page``. A private
``_find_deployment_entity`` helper walks ``components``,
``environments``, and ``resources`` — distinct from
``_find_entity_by_id`` which only covers the seven family-1 kinds.

**Drill-down coverage extended.**
``architecture_model.lifecycle.projectors.drill._FAMILY_KINDS`` now
includes ``5: ("components", "environments", "resources")``. Renderers
that read ``facets["drill_to"]`` can emit hyperlinks from root-family
deployment views into family5 entity pages.

**Per-subsystem fan-out (Phase 2 Task 27, shipped in OCA).** The
``Scope`` literal ``"descendants:each"`` (already accepted by
``ModelSlice`` since Phase 3) is honored by
``opencode_arch.lifecycle_exec.rebuild.rebuild_artifacts``. When a
slice carries this scope, the executor enumerates
``iter_descendants(pkg, include_self=True)`` and materializes a
per-descendant local slice, namespacing each artifact's ``spec_id``
as ``<spec_id>.<subsystem_slug>`` so outputs like
``conops.core.md`` / ``conops.manifest.md`` never collide. The merged-
fragment ``"descendants"`` scope from Phase 1 is unchanged.

**Provenance persistence (Phase 2 Task 28, shipped in OCA).** After
every successful atomic body write, ``rebuild_artifacts`` also writes
``<id>.<ext>.provenance.json`` next to the rendered artifact containing
``{freshness, revision, produced_at, projector}`` sourced from
``ProjectedView.provenance``. The ``pipeline-html`` renderer bypasses
``project()``; those artifacts receive a synthesized provenance stub
(``freshness="fresh"``, ``revision`` from the materialized slice) so
they participate in the same freshness summary. Sidecar writes are
best-effort — a failure never fails the artifact itself.
``opencode_arch.mcp.tools.evaluate._collect_freshness_summary`` reads
the sidecars to bucket artifacts as ``fresh``/``stale``/``pending``,
falling back to ``unknown`` when the sidecar is absent (pre-Phase-5
artifacts). Sidecar files are excluded from the artifact total count.

Design + plan docs:
- `docs/plans/2026-09-08-phase-2-schema-and-semantic-content.md` — Tasks 27, 28
- `docs/plans/2026-09-08-phase-3-recursion-and-entity-views.md` — Family 5 note
- `docs/plans/2026-09-08-model-view-mapping-design.md` — overall design


## E2E Benchmark Results (2026-07-07)

### Extraction (architecture model from source code)
| Repo | Score | Entities | Relationships | Time |
|------|-------|----------|---------------|------|
| python-dotenv | 98/100 | 13 | 15 | 82s |
| colorama | 98/100 | 10 | 15 | 94s |
| tqdm | 98/100 | 30 | 48 | 108s |
| structlog | 98/100 | 20 | 24 | 132s |

**Average: 98/100, 100% success rate** — the system reliably produces valid architecture models from arbitrary Python repos.

### Regeneration (code from architecture model)
All repos: **0% test pass rate** — abstract architecture models (capabilities, components, relationships) are insufficient for faithful code regeneration. The models describe WHAT the system does structurally, not HOW it implements specific behavior (function signatures, constants, algorithms). This validates the need for enriched models with AST-level detail.

### Regeneration with Test-Oracle Loop (Normal Mode)
| Repo | Grade | Fidelity | Avg Compression | Subsystems Converged | Avg Iterations |
|------|:-----:|:--------:|:---------------:|:--------------------:|:--------------:|
| colorama | B | 80% | 7.4x | 4/5 | 1 |
| structlog | A | 93% | 17.9x | 13/14 | 1 |
| tqdm | B | 82% | 67.9x | 9/11 | 1 |
| click | B | 89% | 45.9x | 8/9 | 1 |

Note: Non-100% fidelity in normal mode is due to "root" subsystems (decomposer artifacts with 0 test files) and external dependency issues (e.g., tqdm.keras requires TensorFlow).

### Blind Regeneration (model-only, no source/test file access) — FINAL RESULTS

| Repo | Testable Subsystems | Converged | Fidelity | Avg Iterations | Time |
|------|:-------------------:|:---------:|:--------:|:--------------:|:----:|
| colorama | 4 | **4/4** | **100%** | 1.0 | ~5m |
| structlog | 13 | **13/13** | **100%** | 1.0 | ~25m |
| tqdm | 10 | **10/10** | **100%** | 1.0 | ~20m |
| click | 8 | **8/8** | **100%** | 1.0 | ~30m |
| **TOTAL** | **35** | **35/35** | **100%** | **1.0** | **~80m** |

**Key breakthrough:** The enriched architecture model ALONE (body_hints + constants + test_contracts) contains enough information to regenerate code that passes ALL tests for ALL testable subsystems — WITHOUT the agent reading any source or test files. The agent works in an empty temp directory with only the model data in its prompt.

**What this proves:**
- The architecture model is a **lossless behavioral representation** for 35/35 subsystems
- 34/35 converge on **first attempt** (97% first-iteration success)
- Zero fidelity gap for 33/35 subsystems (blind score = normal score)
- Blind mode can even BEAT normal mode (structlog.processors: 91% normal → 100% blind)

**What made it work:**
1. `body_hint` on trivial functions = exact implementation (`return CSI + str(code) + 'm'`)
2. Module-level constants extracted (CSI, OSC, BEL)
3. Class attributes with values (BLACK=30, RED=31, ...)
4. Module-level instances (Fore=AnsiFore(), Back=AnsiBack(), ...)
5. Test contracts specifying exact expected outputs
6. Dependency context expansion for cross-module subsystems
7. Adaptive contract cap increase for under-specified subsystems

### Key Findings
- MCP server works end-to-end with `opencode run` (headless mode)
- `--dangerously-skip-permissions` required for cross-directory access
- `--dir` should point to `architecture-model-standard` (where MCP tools are configured)
- Root cause of earlier MCP failure: broken editable install of `python-dotenv` (pointed to deleted temp dir) caused `mcp` package import to fail silently

### Token Economics (Value Proposition)

**Compression ratio improves with repo size/connectivity:**

| Repo | Source (tokens) | Blind Prompt (tokens) | Compression | Fidelity |
|------|----------------:|---------------------:|:-----------:|:--------:|
| colorama | 10,012 | ~1,800 | 2.8x | 100% |
| structlog | 60,174 | ~3,000 | 6.0x | 100% |
| tqdm | 46,151 | ~2,800 | 7.9x | 100% |
| click | 105,694 | ~4,000 | 26.4x | 100% |

**Per-subsystem analysis (highest compression wins):**
- click.arguments: 97,940 vs 1,141 = **85.8x** compression (100% fidelity)
- click.parser: 74,346 vs 949 = **78.3x** (100% fidelity)
- click.utils: 96,185 vs 2,157 = **44.6x** (100% fidelity)
- click.testing: 91,902 vs 2,731 = **33.7x** (100% fidelity)
- tqdm.contrib: 41,508 vs 819 = **50.7x** compression (100% fidelity)
- tqdm.concurrent: 33,575 vs 780 = **43.0x** (100% fidelity)
- structlog.generic: 9,092 vs 444 = **20.5x** (100% fidelity)

The compression benefit is DEPENDENCY-DRIVEN: subsystems with many large upstream dependencies benefit most because the model provides their API surface in ~50 tokens vs reading full source files.

**Scaling law:** Compression ratio correlates with total source tokens:
- 10K source → 2.8x
- 46-60K source → 6-8x
- 105K source → 26x average (up to 86x per subsystem)

### Learning Loop (COMPLETE - 2026-07-07)

The learning loop is fully integrated into the regen-loop orchestrator:

**Pattern Classifier** (7 pattern types, 14 regex rules + structured analysis):
- CROSS_DEP, MISSING_IMPL, WRONG_CONSTANT, API_MISMATCH, COMPLEX_BEHAVIOR, TEST_INFRA, UNKNOWN
- Dual-level: raw regex on pytest output + structured analysis of pass rates

**Adaptive Prompt Optimizer** (4 heuristic rules + historical pattern lookup):
- Rule 1: High dep count (>=3) → expand dep context proactively
- Rule 2: Low contracts (<10) → increase contract cap to 200
- Rule 3: Low body_hint coverage (<50%) → flag for source excerpts
- Rule 4: Historical patterns → apply learned strategies

**Report Cards** (self-assessment after each run):
- Grading: A (>90% fidelity, >5x compression, 0 novel) through F (<40%)
- Trend detection vs previous runs (fidelity, compression)
- Actionable improvement suggestions

**Lessons** (automatic insight extraction):
- Contract count thresholds, signature correlations
- Dominant pattern detection, systemic issue flagging
- Stored with deduplication (content-hashed IDs)

**Doc Drift Maintainer** (4 checks + auto-fix):
- Test count, version sync, schema version, Python version
- Auto-fixes simple cases (version numbers, test counts)

**CLI Commands:**
- `opencode-arch report` — Display report cards with grades and actions
- `opencode-arch metrics --learning-curve` — Show learning curve trends
- `opencode-arch metrics --drift` — Show unresolved drift flags

### Learning Curve Tracking

The `learning_curve` table in telemetry tracks improvement over successive repos:
- `avg_compression_ratio`: 2.8x → 6.0x → 7.9x → 26.4x (UP with repo size)
- `converged/total`: Should improve as pipeline matures
- `avg_iterations`: Should stay at 1 (good model = first-attempt success)
- Fidelity gap (normal - blind): Target <10% across all repos

## Development Instructions

- Always run tests with: `pytest tests/ -v --ignore=tests/test_config_loader.py` (pre-existing failure)
- Training module has been moved to `arch-agent` repo — do not add training code here
- This is the schema-only open standard — keep it focused on parse/validate/slice/format
- The `opencode-arch` package depends on this — API changes need coordination
- MCP server venv: ensure `python-dotenv` is a proper wheel install (not editable) — `pip install --force-reinstall python-dotenv` if FastMCP import fails

## Related Repos

| Repo | Path | Purpose | Tests |
|------|------|---------|-------|
| architecture-model-standard | (this repo) | Schema, validator, CLI, manifest | 1171 passed |
| opencode-arch | `../opencode-arch/` | MCP extension (token broker) + CLI + E2E benchmarks | 157 passed |
| arch-agent | `../arch-agent/` | Training pipeline + surrogate | 574 passed |

## SI&L + LLM Provider Layer + Pipeline Dashboard

Phase B of the SI&L + Provider initiative added three cross-cutting concerns
that together turn the pipeline from an opaque batch process into an
observable, provider-agnostic, deterministically-rebuildable system. The
AMS side owns the schema, storage, and rendering primitives; the OCA side
owns the runtime adapters and MCP surface.

### SI&L (Structural Interface Layer)

SI&L is a component-scoped telemetry log for architecturally-significant
call sites. Records live in the consuming repo under
`.architecture/sil.sqlite` — a SQLite-backed ring buffer that retains the
50 most recent events per `component_id`. Rollup snapshots are written to
`.architecture/sil/<component_id>.yaml` and carry pre-aggregated 7-day
metrics (invocations, failure rate, average duration).

To inspect a single component: the OCA MCP tool
`architect_component_health COMP-<id>` returns an envelope of shape
`{ok, record: {component_id, kind, name, metrics, recent_events}, trend}`.
For a system-wide view, `architect_evaluate` merges an `sil_summary` key
of shape `{component_id: {invocations_7d, failure_rate_7d, avg_duration_ms}}`
into its regular report.

Instrumented sites currently cover: 10 pipeline stages (`stage:*`), 5
lifecycle renderers (`renderer:*`), 3 validators (`validator:*`), and all
19 MCP `*_tool` handlers (`mcp_tool:*`). Instrumentation is applied via the
`@sil_instrument` decorator in `architecture_model.sil.decorators`, which
is a no-op when no `SILStore` is bound to the current context.

### LLM Provider Layer

Providers are abstracted behind a runtime-checkable `LLMProvider` Protocol
at `architecture_model.llm.provider`, exposing `complete`, `stream`,
`structured`, and `tokenize`. Three concrete adapters live in OCA:
`MCPProvider` (subprocess invocation via `OpencodeRunner`),
`FrontierProvider` (direct Anthropic/OpenAI HTTPS via urllib), and
`RelayExtProvider` (opencode-relay JSON POST).

Routing is policy-driven. `.architecture/llm/policy.yaml` maps
`TaskClass` names to `RoutingRule(provider, model, max_cost_usd_per_call,
fallback)` under a `global_budget_usd`. Callers invoke
`OpencodeRunner.run_via_policy(prompt, task_class_name=...)` and the
runner picks the provider/model, enforces per-call cost caps, and falls
back on error.

Model outputs record their generator via `meta.provider = {name, model,
policy_ref}` inside `.architecture-model.yaml`. The pipeline stamps this
at emit time — see `_stamp_provider` in `pipeline/emit.py`. For fully
reproducible runs, set `AMS_DETERMINISTIC_NOW=<iso8601>` to pin every
timestamp the pipeline consumes (used by `synthesize._now_iso` and
`sil.rollup._now_iso`).

### Pipeline Dashboard

The pipeline dashboard is a single, self-contained interactive HTML file
that visualizes a pipeline architecture slice with live SI&L badges.
Running `architect_artifact_rebuild <spec>` (OCA MCP) writes the artifact
to `.architecture/lifecycle/artifacts/pipeline.html` (or wherever the
rebuild spec targets).

The rebuild is a three-step pipeline. First, a slice YAML (example at
`tests/fixtures/lifecycle/pipeline.slice.yaml`) selects capabilities,
components, and constraints from the model. Second, a view YAML with
projector `pipeline_html_data` runs `build()` to produce a
`{nodes, edges, badges}` JSON payload. Third, the `pipeline-html`
renderer embeds that JSON in an HTML shell and links to vanilla-JS
assets under `assets/pipeline_dashboard/{index.css,badges.js,drilldown.js}`.

Open the file in any browser (`file://.../pipeline.html`). Clicking a node
opens a drill-down panel showing id, name, kind, and colored badges
(validation_score, invocations, failure_rate, latency) using green/yellow/
red thresholds.

The renderer is deterministic: identical inputs produce byte-identical
HTML output. This is guarded by
`tests/lifecycle/test_dashboard_rebuild.py`, which round-trips the
materialize→render path twice and asserts both string equality and
node/edge ordering stability.

<!-- opencode-arch:start -->
# Architecture (auto-managed by opencode-arch)

**Model:** 29 components | 438 relationships
**Score:** 59.4% (FC=75% RA=46% BC=17% BV=100%)
**Codebase:** 189 modules | 442 import edges
**Requirements:** 122 tracked

## Component Map

## Architecture: 29 components
- **Core** (COMP-1): src/architecture_model/core/__init__.py
- **Type System** (COMP-1.1): src/architecture_model/core/types.py
- **Validation** (COMP-1.2): src/architecture_model/core/validator.py, src/architecture_model/spec/__init__.py
- **Parser & Persistence** (COMP-1.3): src/architecture_model/core/parser.py, src/architecture_model/core/compression.py, src/architecture_model/core/merger.py
- **Model Operations** (COMP-1.4): src/architecture_model/core/slicer.py, src/architecture_model/core/differ.py, src/architecture_model/core/coverage.py
- **Quality Metrics** (COMP-1.5): src/architecture_model/core/confidence.py, src/architecture_model/core/regen_readiness.py, src/architecture_model/core/corrections.py
- **Pipeline** (COMP-2): src/architecture_model/pipeline/__init__.py
- **Pipeline Coordination** (COMP-2.1): src/architecture_model/pipeline/coordinator.py, src/architecture_model/pipeline/protocol.py, src/architecture_model/pipeline/cache.py
- **Observation Stages** (COMP-2.2): src/architecture_model/pipeline/observe.py, src/architecture_model/pipeline/observe_types.py, src/architecture_model/pipeline/infer.py
- **Allocation & Relation Stages** (COMP-2.3): src/architecture_model/pipeline/allocate.py, src/architecture_model/pipeline/allocate_types.py, src/architecture_model/pipeline/relate.py
- **Specification & Contract Stages** (COMP-2.4): src/architecture_model/pipeline/specify.py, src/architecture_model/pipeline/specify_types.py, src/architecture_model/pipeline/contract.py
- **Synthesis & Emit Stages** (COMP-2.5): src/architecture_model/pipeline/decompose.py, src/architecture_model/pipeline/decompose_types.py, src/architecture_model/pipeline/synthesize.py
- **Manifest** (COMP-3): src/architecture_model/manifest/__init__.py, src/architecture_model/manifest/types.py
- **Scanners** (COMP-3.1): src/architecture_model/manifest/scanner.py, src/architecture_model/manifest/multi_scanner.py, src/architecture_model/manifest/ts_scanner.py
- **Graph & Analysis** (COMP-3.2): src/architecture_model/manifest/call_graph.py, src/architecture_model/manifest/interfaces.py, src/architecture_model/manifest/behavior.py
- **Grouping & Generation** (COMP-3.3): src/architecture_model/manifest/grouping.py, src/architecture_model/manifest/generator.py, src/architecture_model/manifest/recursive.py
- **Documentation** (COMP-4): src/architecture_model/docs/__init__.py
- **Core Doc Generators** (COMP-4.1): src/architecture_model/docs/generator.py, src/architecture_model/docs/component_spec.py, src/architecture_model/docs/icd.py
- **SE Document Suite** (COMP-4.2): src/architecture_model/docs/se/__init__.py, src/architecture_model/docs/se/generator.py, src/architecture_model/docs/se/frontmatter.py
- **Orchestration** (COMP-5): src/architecture_model/orchestration/__init__.py

## Development Guidelines

- Use `architect_slice` for focused context on specific components
- Use `architect_check` after significant changes to verify model accuracy
- Use `architect_require` to capture functional requirements from discussion
- Use `architect_feedback` to record corrections or rate tool quality
- Components are auto-grouped by import affinity — respect boundaries
<!-- opencode-arch:end -->

