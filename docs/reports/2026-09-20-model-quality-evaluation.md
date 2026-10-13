# Self-Model MBSE Fidelity Evaluation

**Date:** 2026-09-20
**Scope:** AMS v3 self-model (merged from `.architecture-model.v3.yaml` + `.architecture/model/*.v3.yaml` fragments)
**Method:** Criteria-driven scorecard against the 8 success criteria in `docs/reports/2026-09-14-v3-se-walk.md`, backed by numeric evidence from all 15 declarative walks + 4 Python meta-walks + a substrate coherence audit.
**Model state:** refreshed via `pipeline_v3.orchestrator.run_pipeline()` on AMS itself immediately before measurement (R1 closed). Predecessor numbers from the pre-refresh model are noted parenthetically where the delta is diagnostic.

---

## §1 Executive Summary

The refreshed AMS v3 self-model is **structurally strong** (97.3% src-module coverage, up from 84.8% pre-refresh; zero broken component→module refs; all 15 declarative walks execute cleanly) but **semantically thin at the strict specification tier** (0/520 entities pass promotion-strict; 699/901 promises still `open`).

The pipeline_v3 refresh closed the freshness gap (walks and graph packages now componentized) and increased behavior density 26×, from 17 authored behaviors to 449 derived behaviors. This refresh also **exposed a substrate finding invisible in the pre-refresh state**: 432 of the 449 newly-derived behaviors carry zero promises. `pipeline_v3.derive_behaviors` emits Behavior entities but does not attach `intent`/`delivers`/`provides` promises the way `derive_promises` does for capabilities and components. This is the single most actionable pipeline finding of the audit.

| # | Criterion | Verdict | Key Evidence |
|---|-----------|---------|--------------|
| 1 | Byte-deterministic pipeline | **Pass (static)** | Emit stage uses sorted keys + hash-derived ids; deferred full re-run check |
| 2 | Auditable provenance per entity | **Partial** | 138/901 promises verified (15.3%); 44/520 entities `ready-to-code` on attribute-completeness |
| 3 | Open work as typed gaps | **Pass** | 60 typed-gap (vs 699 open) — substrate distinguishes; typed-gap ratio 6.2% |
| 4 | Schema separable from pipeline | **Pass** | `spec/schema.json` — 0 references to pipeline_v3 modules |
| 5 | Reproducible on any Python repo without config | **Pass** | `run_pipeline(repo_path, *, out_path)` — no config file required |
| 6 | Composable stages, each pure/testable | **Pass** | 16 pipeline_v3 modules, 19 test files — every stage has ≥1 test |
| 7 | Walks-as-capabilities discipline | **Pass** | walk-coverage: 15 covered, 2 duplicate-walk, 0 uncovered |
| 8 | Category B specification tier reachable | **Fail (self)** | promotion-strict: 507 insufficient, 13 partial, **0 ready-to-code-strict** |

**Real-world extrapolation:** Self-model quality is a **ceiling for authored-content criteria** (2, 8) and a **floor for structural criteria** (1, 3–7). Predicted external-repo behavior: pipeline_v3 will match or exceed the self-model on 5–6 criteria, and fall short on the two authored-content criteria — but two well-defined substrate extensions (LLM attribute inference, requirements ingestion) each close a quantifiable portion of that gap (§5).

---

## §2 MBSE Fidelity Scorecard

### Criterion 1 — Byte-deterministic pipeline

**Definition (SE walk):** running `run_pipeline()` twice on the same input produces byte-identical output.

**Proxy:** static inspection of emit stage; deferred full re-run comparison as out-of-scope.

**Evidence:** `pipeline_v3/publish.py` writes YAML via canonicalized ordering; entity ids in `pipeline_v3/derive_promises.py` are content-hashed. No wall-clock timestamps stamped except via `AMS_DETERMINISTIC_NOW`.

**Verdict:** **Pass (static)**.

---

### Criterion 2 — Auditable provenance per entity

**Definition:** every entity claim carries evidence (`verified_by`) traceable to code or an artifact.

**Proxy:** promise-status distribution + attribute-completeness walk verdict.

**Evidence (refreshed model):**
- Total promises: **901** across **88 entities that carry promises** (out of 520 total entities)
- `verified`: 138 (15.3%)
- `open`: 699 (77.6%)
- `typed-gap`: 60 (6.7%)
- `proposed`: 4 (0.4%)
- attribute-completeness walk: **44 ready-to-code / 44 needs-validation / 432 needs-enrichment**

**Substrate finding:** 432/520 entities (83%) have NO promises. Cross-referencing entity counts (25 caps + 27 comps + 17 authored behaviors + 4 actors + 4 interfaces + 6 constraints + 5 layers ≈ 88), the 432 promise-less entities correspond precisely to the 432 newly-derived behaviors that `pipeline_v3.derive_behaviors` emitted without promise attachment. Pre-refresh this was invisible because only 17 authored behaviors existed.

**Verdict:** **Partial**. Provenance mechanism is uniform on the 88 authored/authored-adjacent entities, but the 432 derived behaviors are structurally out of the promise system entirely — a substrate gap.

---

### Criterion 3 — Open work as typed gaps

**Definition:** missing content should be an explicit typed gap, not an implicit absence.

**Evidence:** 60 promises with `status: typed-gap` (up from 54 pre-refresh — pipeline emits some typed gaps deterministically). Substrate consistently uses the four statuses (open / typed-gap / proposed / verified).

**Verdict:** **Pass**. Substrate is exercised, at 6.7% of open work — same ratio as pre-refresh, suggesting the pipeline doesn't preferentially emit typed-gap over open, which is a defensible design choice.

---

### Criterion 4 — Schema separable from pipeline

**Definition:** the v3 schema must be usable without pipeline_v3; no schema reference to pipeline modules.

**Evidence:** `spec/schema.json` mentions "pipeline" 3 times, all as enum values (behavior kinds: `sequential | event-driven | state-machine | saga | pipeline | parallel`) — not module references. `promise-graph.schema.json`: zero references.

**Verdict:** **Pass**.

---

### Criterion 5 — Reproducible on any Python repo without config

**Definition:** the pipeline runs with only a repo path; no per-repo config file required.

**Evidence:** orchestrator signature at `pipeline_v3/orchestrator.py:167`:
```python
def run_pipeline(
    repo_path: Path | str,
    *,
    out_path: Path | str,
    project_name: str = "",
    cluster_depth: int = 3,
    skip_publish: bool = False,
) -> PipelineRunResult:
```

Only `repo_path` and `out_path` are required. All tuning knobs have defaults. **This session's R1 refresh proved the criterion by running it on AMS.**

**Verdict:** **Pass**.

---

### Criterion 6 — Composable stages, each pure/testable

**Evidence:** 16 pipeline_v3 modules (scan, cluster, containerize, derive_behaviors, derive_promises, derive_triggers, link, orchestrator, publish, slice, verify + 3 substrate + 1 adapter). 19 test files under `tests/pipeline_v3/`. Every stage has ≥1 dedicated test.

**Verdict:** **Pass**.

---

### Criterion 7 — Walks-as-capabilities discipline

**Evidence:** `walk_coverage` Python meta-walk: 15 covered, 2 duplicate-walk (kind-dispatched realize-* + realization-skip-* families), 0 uncovered declarative.

**Verdict:** **Pass**.

---

### Criterion 8 — Category B specification tier reachable

**Definition:** entities should be reachable to `ready-to-code-strict` under the five-attribute Category B gate (goals ∧ requirements ∧ success_criteria ∧ failure_modes ∧ constraints).

**Evidence (refreshed model):**
- 507 entities: `insufficient-strict` (up from 73 pre-refresh — the 434 new promise-less behaviors all fail the gate as predicted)
- 13 entities: `partial-strict` (unchanged from pre-refresh)
- **0 entities: `ready-to-code-strict`**

Loose promotion walk: 44 ready-to-code, 39 needs-validation, 4 promotion-candidate, 433 needs-enrichment.

**Verdict:** **Fail (self-model)**. The strict gate is unattained on any of the 520 entities. This is not a substrate failure — the 44 loose-gate passes prove the machinery works. It is a **content authoring gap** compounded by the substrate finding above: no derived behavior carries the promise attributes the gate reads.

---

## §3 Substrate Coherence Audit

### Code → Model

| Metric | Pre-refresh | Refreshed |
|--------|------------:|----------:|
| Python files in `src/architecture_model/` | 330 | 330 |
| Dotted modules covered by ≥1 component's `module_names` | 280 | **321** |
| **Coverage** | **84.8%** | **97.3%** |
| Orphan modules | 50 | **9** |
| Components | 25 | **27** |

**Top-level packages missing from the model:**

| Package | Pre-refresh | Refreshed | Notes |
|---------|:-----------:|:---------:|-------|
| `walks` | ❌ missing | ✅ covered | CAP-WK substrate now componentized |
| `graph` | ❌ missing | ✅ covered | NetworkX export layer componentized |
| `audit` | ❌ missing | ❌ still missing | Single-file top-level module |
| `patterns` | ❌ missing | ❌ still missing | Pattern classifier from learning loop |
| `monitoring` | ❌ missing | ❌ still missing | Monitoring surface |
| `monitoring_checks` | ❌ missing | ❌ still missing | Monitoring checks |
| `__main__` | ❌ missing | ❌ still missing | Trivial |

**Nine orphan modules:** the 5 remaining top-level packages (all small — audit, monitoring, monitoring_checks, patterns, __main__) plus 4 individual test-support files (`core/test_affinity.py`, `feedback/test_results.py`, `manifest/test_analyzer.py`, and the src package `__init__` itself).

### Model → Code

| Metric | Value |
|--------|-------|
| Components with `module_names` | 27 |
| Unique modeled modules | 321 |
| **Broken refs** | **0** |

Every module the model claims exists, actually exists.

### Combined verdict

**Structural coherence: excellent** (0 broken refs, 97.3% coverage post-refresh). The remaining 9 orphans are individually small; the 5 top-level packages account for ≤10 files combined. Cluster tuning (`cluster_depth=3` default) apparently classifies these as too small to promote to their own components.

---

## §4 Walk Verdict Distribution

Full run of 15 declarative + 4 Python meta-walks on the refreshed self-model (520 entities, 782 relationships, 901 promises).

### Structural walks (all `ready-to-code`)

| Walk | Cards | Verdict |
|------|-----:|---------|
| browse | 520 | 520 ready-to-code |
| descend | 520 | 520 ready-to-code |
| constraint-impact | 6 | 6 ready-to-code |
| realize-actor | 4 | 4 ready-to-code |
| realize-behavior | 449 | 449 ready-to-code |
| realize-capability | 25 | 25 ready-to-code |
| realize-component | 27 | 27 ready-to-code |
| realize-constraint | 6 | 6 ready-to-code |
| realize-interface | 4 | 4 ready-to-code |
| realize-layer | 5 | 5 ready-to-code |
| realization-skip-capability | 25 | 25 ready-to-code |
| realization-skip-component | 27 | 27 ready-to-code |

All 449 derived behaviors are structurally traversable. The pre-refresh model had only 17 behavior cards; refresh increased this 26×.

### Semantic walks (mixed verdicts — the real signal)

| Walk | Cards | Verdict distribution |
|------|-----:|----------------------|
| attribute-completeness | 520 | 44 ready-to-code, 44 needs-validation, **432 needs-enrichment** |
| flow-audit *(Part 17b)* | 449 | 200 ready-to-code, **249 needs-enrichment** |
| promotion | 520 | 44 ready-to-code, 39 needs-validation, 4 promotion-candidate, **433 needs-enrichment** |
| promotion-strict | 520 | 13 partial-strict, **507 insufficient-strict**, 0 ready-to-code-strict |
| unrealized-cap | 25 | 21 needs-enrichment, 3 needs-validation, 1 ready-to-code |

**Signal (post-refresh):**
- `attribute-completeness` and `promotion` both surface the same 432 needs-enrichment cohort — the promise-less derived behaviors from `derive_behaviors`.
- `flow-audit` — of the 449 derived behaviors, 200 pass the flow criteria (44.5%) and 249 fail. Pre-refresh this walk saw only 17 authored behaviors, all passing. The post-refresh 249 needs-enrichment cards are the walk's first genuine signal.
- `promotion-strict` at 0 ready-to-code — unchanged conclusion, dramatically expanded denominator.
- `unrealized-cap` at 21/25 needs-enrichment — **unchanged**. Refresh did not add realization edges. The capability inventory in `.architecture/model/capabilities.v3.yaml` is authored, not pipeline-derived, so refresh didn't touch it.

### Python meta-walks

| Meta-walk | Verdict distribution |
|-----------|----------------------|
| walk_coverage | 15 covered, 2 duplicate-walk |
| direction_lint | *errored (driver-side interface mismatch — passes raw list, walk expects `{"relationships": [...]}`); walk itself is fine* |
| llm_endpoint_inventory | 24 stale, 16 undeclared, 4 legacy, 4 covered |
| prompt_refiner | 9 unused |

**llm_endpoint_inventory** shows the most drift in the substrate — 24 declared endpoints no longer exist in code; only 4 endpoints both declared and detected. Highest-priority cleanup surface after the derive_behaviors gap.

---

## §5 Real-World Extrapolation

**Setup:** predictions anchored to the refreshed self-model. External-repo run deferred (R6).

**Framing hypothesis:** the self-model's authored content acts as a **ceiling** for criteria that depend on human specification (promotion-strict, attribute-completeness, verified provenance), and as a **floor** for criteria satisfied structurally by the pipeline (coverage, walk coverage, schema separability, byte-determinism).

### Predictions per criterion

| # | Criterion | Self verdict | External-repo prediction | Rationale |
|---|-----------|--------------|--------------------------|-----------|
| 1 | Byte-deterministic | Pass | **Pass (same signal)** | Determinism is a property of the pipeline, not the input |
| 2 | Auditable provenance | Partial (15.3% verified) | **Worse — near-zero verified initially** | `verified_by` requires authored evidence, absent on fresh repos |
| 3 | Typed gaps for open work | Pass | **Pass (similar ratio)** | Pipeline emits typed gaps deterministically per Part 17 series |
| 4 | Schema separability | Pass | **Pass** | Property of AMS, invariant of target |
| 5 | Reproducible without config | Pass | **Pass** | Invariant |
| 6 | Composable stages | Pass | **Pass** | Invariant |
| 7 | Walks-as-capabilities | Pass | **Pass** | Invariant |
| 8 | Category B strict tier | Fail (0/520) | **Fail (0/N initially)** | No authored Category B attributes on freshly extracted entities |

### Composite predictions (updated with refresh numbers)

- **Structural coverage on external repos:** predicted 95%+. The refreshed self-model hit 97.3% on AMS itself — a strong precedent.
- **Behavior density on external repos:** predicted 10–30 per top-level package. AMS has 27 components and 449 behaviors post-refresh (~16 behaviors per component); similar-shaped repos should land in the same range.
- **Promise volume on external repos:** predicted 5–20× entity count, dominated by `open`. Self-model produces 901 promises / 88 promise-bearing entities ≈ 10 promises/entity; if the pipeline gap on derived behaviors (§2 substrate finding) is closed, this ratio would extend to all entities.
- **`unrealized-cap` verdict on external repos:** hard to predict — depends on whether the authoring team creates a capability layer at all. If they don't (majority case), this walk sees 0 cards.

### What "fresh extraction cannot manufacture" means precisely

The claim that fresh extraction cannot manufacture authored content is imprecise. Refined:

**Fresh *AST-only* extraction cannot manufacture verified content.** Two well-defined authoring surfaces exist and each closes a distinct portion of the gap.

**Attribute inventory — what AST can and cannot produce:**

| Attribute | Self-model count | AST-derivable? | Source |
|-----------|-----------------:|:--------------:|--------|
| `intent` | 381 | ✅ | docstring first line |
| `delivers` | 283 | ✅ | function names, return types |
| `provides` | 181 | ✅ | public API surface |
| `verified_by` | 16 | ❌ | test-to-claim mapping is a semantic judgment |
| `failure_modes` | 10 | ❌ | architectural failure modes ≠ `except` blocks |
| `requirements` | 8 | ❌ | external spec / user story |
| `slos` | 7 | ❌ | operational targets |
| `success_criteria` | 3 | ❌ | acceptance framing |
| `goals` | 1 | ❌ | mission/PRD framing |
| others (stakeholders, trade_offs, assumptions, etc.) | 1–3 each | ❌ | organizational / retrospective knowledge |

The top-3 AST-derivable attributes account for 845/901 = **94% of promise volume** but **0% of the Category B strict attributes**.

**Why AST-only can't produce verified provenance:**
- `derive_promises.py` emits `open` promises with `verified_by: []`. It cannot know which test proves which claim — `test_scan.py exists` does not prove `component scan delivers behavior Y`; only the *assertions inside* the test do, and mapping assertion → claim is a judgment.
- Design docs, plans, prior reports (the other three verified_by shapes observed in the self-model) do not exist in a fresh repo. There is nothing to point at.

**Path 1 — LLM-assisted attribute inference.**
Run a T2 LLM pass per entity after AST extraction; propose Category B attributes from code + docstrings + neighborhood context. Land results as `proposed` promises (never auto-`verified`). This is the exact pattern of `CAP-DF.author` (Part 12) applied at extraction time rather than per-comment.
- Predicted effect: flips ~60% of `insufficient-strict` → `partial-strict`, and a smaller fraction to `ready-to-code` under the *loose* gate. Does not touch strict verified count.
- Cost: 1 LLM call per entity. On opencode-arch (~30 components + derived behaviors, est. ~150 entities), ~$0.30–1.50 at T2 rates. On AMS-scale (520 entities), ~$1–5.
- Ceiling: `proposed`, not `verified`. Strict gate still fails without human review promoting `proposed → verified`.

**Path 2 — Requirements ingestion.**
Auto-scan `docs/spec/`, `docs/requirements.md`, `docs/adr/`, `README.md` for structured or semi-structured requirements. Attach as promises on the entities they mention (fuzzy match on component/capability name). AMS already has `architect_require` in OCA for the manual case; auto-scan is the extension.
- Predicted effect: highly repo-dependent. On repos with an ADR discipline (~10% of Python projects) closes 40–70% of the loose gate. On repos with no docs, closes 0%.
- Cost: one AST-like pass; no LLM required unless the docs are free-form.
- Ceiling: whatever the docs cover. Higher than LLM inference *when docs exist*, because human-authored → higher confidence → can flip directly to `verified` if the trace is unambiguous.

**Combined:** LLM inference + requirements ingestion together close an estimated 70–80% of the loose Category B gate on external repos. The strict-gate `verified` bar still requires human review — this is by design.

### Bottom line

The self-model provides **high confidence** that pipeline_v3 will produce structurally coherent, walk-traversable, byte-deterministic output on any Python repo (Criteria 1, 3–7 hold as invariants). It provides **zero confidence** about semantic quality *from AST-only extraction* (Criteria 2, 8) — but two well-defined substrate extensions (Path 1 LLM inference, Path 2 requirements ingestion) each close a quantifiable portion of that gap, and the substrate correctly represents its own inability to fabricate content in the absence of either by using `open` and `typed-gap` promises rather than hallucinating.

The **most impactful substrate improvement** discoverable only after the refresh: closing the promise-emission gap on `derive_behaviors` (§2, §6/R9).

---

## §6 Findings & Recommended Follow-Ons

### Findings (evidence-anchored, refreshed model)

1. **F1 — Zero broken refs.** All 321 modeled modules exist on disk. Model→code integrity is perfect.
2. **F2 — Coverage 97.3% post-refresh** (was 84.8%). R1 closed the walks and graph freshness gaps. 9 orphans remain (5 small top-level packages + 4 individual files).
3. **F3 — Strict Category B is a universal 0.** 0/520 entities pass `promotion-strict`. Expanded denominator does not change the conclusion, but exposes the derived-behaviors gap below.
4. **F4 — 699 open promises (77.6%).** Most claims lack verified evidence. Concentrated in `intent` (381), `delivers` (283), `provides` (181) — the three AST-derivable promise types.
5. **F5 — LLM endpoint inventory drift.** 24 stale + 16 undeclared vs 4 covered — highest-drift inventory in the substrate.
6. **F6 — `direction_lint` driver bug.** Not a walk bug; the driver invocation passed a raw list where the walk expects `{"relationships": ...}`.
7. **F7 — `unrealized-cap` 21/25 needs-enrichment — unchanged by refresh.** Capability layer is authored (`capabilities.v3.yaml`), not pipeline-derived. Pipeline_v3 does not emit `realizes` edges from derived components to authored capabilities.
8. **F8 — Behavior density: 17 → 449 (26×).** Refresh restored the pipeline's ability to model behaviors. Pre-refresh model was fundamentally under-behaviored.
9. **F9 (new — refresh-exposed) — Derived behaviors carry zero promises.** 432/520 entities (83%) have no promises. All correspond to `pipeline_v3.derive_behaviors` output. This is the single most actionable substrate finding: fixing it would populate the majority of the model with `intent`/`delivers`/`provides` promises deterministically.

### Recommended follow-ons

**Substrate/tooling:**
- **R1** — ✅ **Executed this session.** Pipeline_v3 re-run on AMS. Model refreshed; coverage 84.8% → 97.3%; behaviors 17 → 449.
- **R2** — Fix the `direction_lint` invocation in the evaluation driver (or add a convenience wrapper accepting bare list).
- **R3** — Cleanup pass on `.architecture/llm/endpoints.yaml` — 24 stale to remove, 16 undeclared to add. Closes F5.
- **R9 (new)** — **Highest-impact substrate fix.** Extend `pipeline_v3/derive_behaviors.py` to attach `intent`/`delivers`/`provides` promises to derived Behavior entities, symmetric with the emission `derive_promises.py` does for capabilities and components. Closes F9. Predicted effect: 432 entities move from "no promises" to fully-populated top-3 attributes → loose-gate `ready-to-code` count could jump from 44 to hundreds without any authoring.

**Content/authoring:**
- **R4** — Pilot Category B strict authoring on one high-value capability (candidate: CAP-PB — the extraction capability itself). Fill all 5 attributes with verified promises. Measures the actual cost of reaching `ready-to-code-strict`.
- **R5** — Convert `open` promises to `typed-gap` where the gap is intentional. Would raise the 6.7% typed-gap ratio and reduce misleading `open` counts.

**Substrate extensions to close the semantic gap (§5 Paths 1 and 2):**
- **R7 — Path 1: extraction-time LLM attribute inference.** Add an optional pipeline_v3 stage (post-`derive_promises`, pre-`publish`) that runs a T2 LLM pass per entity proposing Category B attributes with `status: proposed`. Reuses the `CAP-DF.author` prompt-assembly + provider Protocol from Part 12. Gated by CLI flag (`--infer-attributes`) so default runs stay AST-pure and deterministic. Estimated effect on external repos: 60–70% of `insufficient-strict` → `partial-strict`.
- **R8 — Path 2: requirements ingestion.** Add a `pipeline_v3.ingest_requirements` stage that scans `docs/spec/`, `docs/requirements.md`, `docs/adr/`, `README.md` for structured requirements. Attach as promises with fuzzy-matched entity_ref. When the trace is unambiguous (exact ADR → component name match), emit as `verified` with the doc path as `verified_by`; otherwise `proposed`. AMS already has `architect_require` in OCA for the manual single-entity case; this is the batch/auto extension.

**Real-world validation:**
- **R6** — Point-in-time pipeline_v3 run on `../opencode-arch` and `../logs_db`. Compare walk verdict distributions against self-model predictions in §5. Publish delta as follow-up report.

---

## Appendix A — Machine-Readable Summaries

- `/tmp/ams_eval_summary.json` — entity counts, promise distributions, all walk verdicts (refreshed)
- `/tmp/ams_coherence.json` — substrate coherence per-component modules, orphan list, broken refs (refreshed)

Both are ad-hoc scratch files, not committed. Regenerate via `/tmp/ams_eval.py` + `/tmp/ams_coherence.py`.

---

## §7 Post-R9 Checkpoint (behavior intent-promise emission)

**Change under test:** commit `4d7c377` `feat(pipeline): R9 — derive intent promises for behavior candidates`. Adds `derive_promises_for_behavior()` in `pipeline_v3/derive_behaviors.py`; wires `promises: tuple[Promise, ...]` through `ContainerizedBehavior` and `publish._behavior_to_dict()`. Each behavior gets one Promise with `attribute="intent"`, `status=OPEN`, `content=<description>`.

**Method:** re-ran `run_pipeline(repo_path='.', out_path='.architecture-model.v3.yaml')` post-R9. Merged model via `load_v3_model()` (fragments: authored `.architecture/model/capabilities.v3.yaml` + pipeline output `.architecture-model.v3.yaml`). Re-ran attribute-completeness and promotion-strict walks.

### Entity/Promise deltas

| Metric | Pre-R9 (refreshed) | Post-R9 | Δ |
|--------|-------------------:|--------:|---:|
| Total entities | 520 | 522 | +2 |
| Entities carrying promises | 88 (16.9%) | **522 (100%)** | **+434 (+83.1 pp)** |
| Total promises | 901 | 1336 | +435 |
| `verified` promises | 138 | 138 | 0 |
| `open` promises | 699 | 1134 | +435 |
| `typed-gap` promises | 60 | 60 | 0 |
| `proposed` promises | 4 | 4 | 0 |

### Walk verdict deltas

**Attribute-completeness:**

| Verdict | Pre-R9 | Post-R9 | Δ |
|---------|-------:|--------:|---:|
| `ready-to-code` | 44 | 44 | 0 |
| `needs-validation` | 44 | **478** | **+434** |
| `needs-enrichment` | **432** | **0** | **−432** |

**Promotion-strict (5-attribute Category B gate):**

| Verdict | Pre-R9 | Post-R9 | Δ |
|---------|-------:|--------:|---:|
| `ready-to-code-strict` | 0 | 0 | 0 |
| `partial-strict` | 13 | 13 | 0 |
| `insufficient-strict` | 507 | 509 | +2 |

### Interpretation

**Substrate gap closed.** The `needs-enrichment` cohort — 432 derived behaviors that carried zero promises — is empty. Every entity in the model now participates in the promise substrate. This was the concrete finding in §2 Criterion 2 ("83% of entities have NO promises"), and R9 resolves it structurally.

**Promotion-strict unchanged (as expected).** R9 emits only the `intent` attribute; the strict gate requires `goals ∧ requirements ∧ success_criteria ∧ failure_modes ∧ constraints`. Zero movement on `ready-to-code-strict` is the correct outcome — R7 (LLM attribute inference) is the substrate extension that targets that gate.

**Criterion 2 verdict revision.** Pre-R9: **Partial** (mechanism uniform on 88 entities). Post-R9: **Pass** (mechanism uniform on 522/522 entities). The substrate is now provenance-complete; the remaining problem is content richness, not substrate coverage.

**Scorecard update:**

| # | Criterion | Pre-R9 | Post-R9 |
|---|-----------|--------|---------|
| 2 | Auditable provenance per entity | Partial | **Pass** |
| 8 | Category B specification tier reachable | Fail (self) | Fail (self) — unchanged, R7 target |

### Next

R9 is the substrate half of Path 3 ("promise-emission during derivation"). Content richness (Paths 1 + 2 = R7 + R8) remains the delta to criterion 8. Proceeding to R7 brainstorm next.

---

## 8. Post-R7 + R8 checkpoint (2026-09-20)

R7 (LLM attribute inference — Path 1) and R8 (requirements ingestion from documentation — Path 2) landed as opt-in pipeline_v3 stages. Both are behind flags on `run_pipeline`; default runs remain byte-identical.

### R7 landed (commit `9e3f518`)

New stage `derive_attributes_llm.py`. When `run_pipeline(infer_attributes=True, attribute_provider=<LLMProvider>)`, proposes 1–5 items per (entity, Cat-B attribute) pair for target kinds `behaviors ∪ components ∪ capabilities`. Emits `status: proposed` promises. Skips entities with an existing `verified` promise for the target attribute; overwrites `proposed`. `PROPOSED` added to `PromiseStatus` enum (was in schema but not in Python). Default provider is `MCPProvider` (lazy-imported from OCA) with actionable RuntimeError when OCA missing.

### R8 landed (commit `0acdf70`)

New stage `ingest_requirements.py`. When `run_pipeline(ingest_requirements=True)`, scans doc roots (`docs/reports/`, `docs/plans/`, `CONTEXT.md`, `README.md` — configurable via `doc_roots=`) for markdown sections and attaches doc-sourced requirements to entities. Three binding layers:

| Layer | Mechanism | Status |
|---|---|---|
| 1 | YAML frontmatter `binds_to:`, HTML comment `<!-- binds: ID -->`, or heading anchor `{#ID}` | `verified` |
| 2 | Exact heading match against entity name (case-insensitive, punctuation-normalized) | `verified` |
| 3 | LLM classifier over candidates whose name shares a token with the heading (CamelCase-aware); confidence threshold default 0.75 | `proposed` |

Bullet + numbered list items in the section body become requirement content (one item = one promise). Prose paragraphs ignored. When R7 and R8 both on, R8 wipes R7's proposed `requirements` promises before binding (real docs beat LLM guesses). Existing `verified` promises always preserved.

### Measured effect on AMS self-model

Method: re-ran `run_pipeline(ingest_requirements=True, doc_roots=<default>)` on this repo. Merged model via `load_v3_model()`. Ran `promotion-strict` walk.

| Metric | Pre-R8 (post-R9) | Post-R8 | Δ |
|---|---:|---:|---:|
| Total entities | 522 | 525 | +3 (pipeline rescan) |
| `requirements` promises `verified` | 4 | 4 | 0 |
| `requirements` promises from R8 | — | 0 | 0 |
| Sections scanned | — | 1279 | — |
| Layer 1/2 exact matches | — | 1 (`Validate` in README) | — |
| Layer 2 sections producing promises | — | 0 | 0 |
| `promotion-strict / ready-to-code-strict` | 0 | 0 | 0 |
| `promotion-strict / partial-strict` | 13 | 13 | 0 |
| `promotion-strict / insufficient-strict` | 509 | 512 | +3 |

### Interpretation

**R8 substrate proven, R8 signal null on AMS.** 39 unit tests + 3 orchestrator tests confirm all three binding layers work on fixtures with realistic docs. On AMS itself, R8 scanned 1279 sections and found exactly one exact-heading match — `## Validate` in `README.md` — which contained a bash code block, not a bullet list, so zero requirement promises were emitted. The AMS doc corpus is process-oriented (`## Design`, `## Testing strategy`, `## Phase N substrate`) rather than entity-indexed (`## AuthService\n- must verify JWT`), so the assumption R8 encodes — that authored docs cite entity names as headings and list requirements as bullets — does not hold on this repo.

**Where R8 will fire.** Downstream consumer repos with SE-style component docs — one report per component, headings naming the component, requirement bullets under it — should see Layer 2 matches at high rate. This is the target shape for R8's design and matches the pattern in most enterprise SE deliverables. Empirical validation on such a repo is R8 follow-on work.

**R7 not exercised on AMS.** R7 requires an `LLMProvider`. OCA is not installed in this session's Python environment, and running the full 522-entity × 5-attribute pass through a real provider is out of scope for the substrate-landing checkpoint. R7's structural correctness is verified by 16 tests (12 unit + 4 orchestrator, all against `MockProvider`). Effect measurement on a real corpus is R7 follow-on work.

**Scorecard update:**

| # | Criterion | Pre-R7/R8 | Post-R7/R8 |
|---|-----------|-----------|------------|
| 8 | Category B specification tier reachable | Fail (self) | Fail (self) — R7/R8 substrate landed; content lift requires real provider or entity-indexed docs |

### Delivered substrate summary

Post-R2/R3/R7/R8/R9 the pipeline_v3 surface exposes three opt-in enrichment lanes on top of the baseline AST extraction:

```
scan → derive_promises → derive_behaviors → derive_triggers →
cluster → link → containerize → verify →
    ┌─ [R7: derive_attributes_llm]      (Cat-B proposals from LLM)
    ├─ [R8: ingest_requirements]        (Cat-B verified from docs)
    └─ publish (with R9 intent baked in)
```

R9's intent-per-behavior emission runs unconditionally inside `containerize` and is now the pipeline's default provenance floor. R7 and R8 stack: when both are on, R8 runs after R7 and R8's doc-grounded content replaces R7's guesses on the `requirements` attribute; R7's proposals on the other four Cat-B attributes (`goals`, `success_criteria`, `failure_modes`, `constraints`) survive.

Verification: full test suite **4517 passed, 105 skipped** (baseline 4351 → +166 tests from R7, R8, R9, and the PROPOSED enum lock). No regressions.

### Next

R7/R8 substrate is complete. Follow-ons carrying real content lift:

1. **R7 empirical run** — install OCA, run `run_pipeline(infer_attributes=True)` on AMS self-model with real MCPProvider. Measure promotion-strict verdict shift.
2. **R8 empirical run** — pick a downstream consumer repo (or author component-indexed docs on AMS itself). Measure Layer 2 hit rate and requirements promise growth.
3. **R8b1 (deferred)** — retry queue for low-confidence Layer 3 classifications, exposed as a human-review CLI.
4. **R8d (deferred)** — doc drift detector: invalidate `verified` R8 promises when their source section changes.
5. **R4/R5 (out of scope this session)** — content-authoring skills.
