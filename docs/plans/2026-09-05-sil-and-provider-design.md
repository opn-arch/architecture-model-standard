# Plan B — SI&L Instrumentation, LLM Provider Layer, Pipeline Dashboard

**Date:** 2026-09-05
**Status:** Design (approved, pre-implementation plan)
**Branch:** `feat/sil-and-provider`
**Depends on:** `docs/plans/2026-09-05-comment-view-shared-interfaces-design.md`
**Sibling:** `docs/plans/2026-09-05-comment-view-loop-design.md`

## 1. Goal

Give every component — architecture (COMP-*) and runtime (pipeline stage,
MCP tool, renderer, validator) — a persistent, uniform self-improvement +
logging record; formalize an `LLMProvider` protocol with routing/policy so
every LLM call in AMS and OCA becomes reproducible and cost-bounded;
deliver an interactive HTML pipeline dashboard that surfaces the whole
requirements → capabilities → components → modules chain, with live SI&L
badges and drill-down.

Success =

- Every pipeline stage invocation, MCP tool call, renderer run, and
  validator run appears in the SI&L store.
- Every LLM call in the AMS pipeline and the OCA runner is routed via
  `LLMProvider.pick(...)`; every published generation records
  `meta.provider`.
- `pipeline.html` renders from a fixture repo in <2 s, shows badges for
  all COMP-*, and supports click-through to lessons/drift/events/issues.

## 2. Scope

**In scope**

- `LLMProvider` protocol in AMS + three adapters and a routing policy in OCA.
- SI&L schema, decorator, store, snapshot roll-up, `architect_component_health`
  MCP tool.
- Instrumentation of: all pipeline stages, all MCP tools, all
  renderers, all validators.
- Interactive HTML pipeline dashboard rendered by a new `pipeline-html`
  renderer registered in the lifecycle renderer registry.
- Meta-field `meta.provider` added to model schema.

**Out of scope**

- LLM streaming to the dashboard (defined but not consumed in v1).
- Cross-repo SI&L federation (records stay per-repo).
- Cost prediction / spend forecasting (a static budget in the policy is
  enforced; predictions are not).
- Real-time push to the dashboard — v1 dashboard is static (regenerated
  by `architect_artifact_rebuild`).

## 3. Sub-deliverables

### B.1 — LLM Provider Layer (≈1 week)

**Modules to add**

- `src/architecture_model/llm/__init__.py`
- `src/architecture_model/llm/provider.py` — `LLMProvider` Protocol,
  `Completion` TypedDict.
- `src/architecture_model/llm/policy.py` — `TaskClass`, `RoutingRule`,
  `Policy`, `pick`, `spend`. Policy loader from
  `.architecture/llm/policy.yaml`. Retry / backoff / global-budget
  enforcement.
- `src/opencode_arch/llm/providers/mcp.py` — in-process adapter
  wrapping current runner (default).
- `src/opencode_arch/llm/providers/frontier.py` — Anthropic + OpenAI
  clients via env-var config.
- `src/opencode_arch/llm/providers/relay_ext.py` — HTTP relay adapter.
- `src/opencode_arch/llm/registry.py` — resolve `RoutingRule.provider`
  string → `LLMProvider` instance.

**Existing modules to migrate**

- `src/architecture_model/pipeline/{infer,allocate,specify,synthesize,emit}.py`
  — replace direct LLM invocations (currently hard-wired to OpenAI /
  Anthropic SDKs where they appear) with calls to
  `ctx.llm_provider.complete(...)` / `.structured(...)`.
  `PipelineContext` gains an optional `llm_provider: LLMProvider | None`
  field; default remains the OpenCode runner via OCA.
- `src/opencode_arch/runner/opencode.py` — refactor to consume
  `LLMProvider` under the hood; no CLI-visible behavior change.
- `src/architecture_model/spec/schema.json` — add optional
  `meta.provider` field:

  ```json
  "provider": {
    "type": "object",
    "properties": {
      "name":       {"type": "string"},
      "model":      {"type": "string"},
      "policy_ref": {"type": "string"}
    },
    "required": ["name", "model"]
  }
  ```

**Tests**

- Adapter contract tests using recorded fixture responses (each adapter
  round-trips the same fixture and returns identical `Completion`).
- Policy tests: routing selects expected provider per task class; global
  budget triggers `BudgetExceeded`; fallback fires on primary
  `LLMProvider` raising `TransientProviderError`; retry backoff verified.
- Reproducibility: run pipeline twice on the same fixture with
  `meta.provider` pinned; assert byte-identical model output.

### B.2 — SI&L Instrumentation + Store (≈1.5 weeks)

**Modules to add**

- `src/architecture_model/sil/__init__.py`
- `src/architecture_model/sil/record.py` — SI&LRecord Pydantic model
  per §4 of shared-interfaces.
- `src/architecture_model/sil/decorators.py` — `@instrumented(id)`. Emits
  entry/exit events; storage adapter injected. No-op if none injected.
- `src/architecture_model/sil/rollup.py` — walk manifest allocation,
  merge runtime records into architecture-component records.
- `src/opencode_arch/sil/store.py` — SQLite backend (extends existing
  `telemetry/store.py` schema). Ring-buffer maintenance (N=50).
- `src/opencode_arch/sil/snapshot.py` — periodic write of
  `.architecture/sil/<id>.yaml` from SQLite (git-friendly diff).
- `src/opencode_arch/mcp/tools/component_health.py` — new
  `architect_component_health(component_id)` MCP tool.

**Instrumentation edits**

Decorators added at these entry points:

- All pipeline stages: `pipeline/{observe,infer,allocate,relate,specify,
  contract,decompose,synthesize,validate,emit}.py` — top-level `run(...)`
  function.
- All MCP tools: every `src/opencode_arch/mcp/tools/*.py` `_tool(...)`
  handler decorated with `@instrumented("mcp_tool:<name>")`.
- All renderers: `src/architecture_model/lifecycle/renderers/{svg,markdown,
  html,ai_context,zip}.py` — main `render_*` function.
- All validators: `core/validator.validate_model`,
  `core/representativeness.evaluate`, `authoring/gate.evaluate`.

Total decoration surface: ≈40 sites, all one-line changes.

**Tests**

- Decorator emits `{invocation, outcome, duration_ms}` on happy path,
  emits `{outcome: error, ref: exc_class}` on exception (which re-raises).
- Store: ring buffer trimmed to N=50; snapshot YAML matches SQLite row.
- Roll-up: architecture COMP-* aggregates runtime records for its
  allocated modules; weighted average duration.
- `architect_component_health` returns the record + a trend snippet
  (last 7 days delta).

### B.3 — Interactive Pipeline Dashboard (≈1 week)

**Modules to add / extend**

- `src/architecture_model/lifecycle/renderers/pipeline_html.py` (new)
  registered as `"pipeline-html"` in
  `renderers/__init__.py:DEFAULT_RENDERERS`.
- `src/architecture_model/lifecycle/renderers/pipeline_html_data.py`
  (new) — build a `pipeline_state.json` from the resolved model
  package: requirements → capabilities → components → modules edges,
  plus SI&L badge data (pulled via `sil.rollup` at render time),
  plus open-issue counts (from `.architecture/comments/*.yaml`).
- `src/architecture_model/core/visualize.py` — extend to emit
  `pipeline.html` alongside existing diagrams; embed static CSS/JS
  (no external CDN).
- `assets/pipeline_dashboard/` (new) — vanilla-JS drill-down UI:
  - Panel: node info (COMP-id, name, kind, allocated modules).
  - Panel: SI&L record — badges (validation_score, drift_flag_count,
    regen_readiness, failure_rate_7d, avg_duration_ms), sparkline of
    `recent_events`.
  - Panel: Lessons (from `learning/lessons.py`), Drift flags,
    Open Issues (list with `logs-db#<id>` links).

**View / Slice specs**

New named `ViewSpec` and `ModelSlice` in
`.architecture/lifecycle/views/pipeline.view.yaml` +
`.architecture/lifecycle/slices/pipeline.slice.yaml`. Slice selectors
include all `capability`, `component`, `module`, and `constraint` entities.

**Tests**

- Golden snapshot for `pipeline_state.json` on a fixture repo.
- Smoke test: rendered `pipeline.html` opens in headless Chrome
  (playwright), all COMP-* badges present, click-through opens
  the drill-down panel.
- Regeneration test: after a model change, `architect_artifact_rebuild`
  regenerates `pipeline.html` and `pipeline_state.json` deterministically.

## 4. File / directory changes

**New (AMS):**

- `src/architecture_model/llm/{__init__,provider,policy}.py`
- `src/architecture_model/sil/{__init__,record,decorators,rollup}.py`
- `src/architecture_model/lifecycle/renderers/pipeline_html.py`
- `src/architecture_model/lifecycle/renderers/pipeline_html_data.py`
- `assets/pipeline_dashboard/{index.css,drilldown.js,badges.js}`
- `tests/llm/test_provider.py`, `test_policy.py`
- `tests/sil/test_record.py`, `test_decorators.py`, `test_rollup.py`
- `tests/lifecycle/test_renderer_pipeline_html.py`

**New (OCA):**

- `src/opencode_arch/llm/providers/{mcp,frontier,relay_ext}.py`
- `src/opencode_arch/llm/registry.py`
- `src/opencode_arch/sil/{store,snapshot}.py`
- `src/opencode_arch/mcp/tools/component_health.py`
- `tests/llm/test_providers.py`
- `tests/sil/test_store.py`, `test_snapshot.py`
- `tests/mcp/tools/test_component_health.py`

**Extended:**

- `src/architecture_model/pipeline/{observe,infer,allocate,relate,specify,
  contract,decompose,synthesize,validate,emit}.py` — decorators + provider
  routing where LLM calls exist
- `src/architecture_model/lifecycle/renderers/__init__.py` — register
  `pipeline-html`
- `src/architecture_model/lifecycle/renderers/{svg,markdown,html,
  ai_context,zip}.py` — decorators
- `src/architecture_model/core/{validator,representativeness}.py` and
  `authoring/gate.py` — decorators
- `src/architecture_model/spec/schema.json` — add `meta.provider`
- `src/architecture_model/core/visualize.py` — pipeline dashboard emit
- `src/opencode_arch/runner/opencode.py` — consume `LLMProvider`
- `src/opencode_arch/mcp/tools/*.py` — decorators on every handler
- `src/opencode_arch/mcp/server.py` — register `architect_component_health`

## 5. Implementation phases

Roughly 3.5 weeks total, six PRs on this branch (mergeable in order):

**Phase B1.1 (2 days) — LLMProvider protocol**

- Protocol + Completion TypedDict
- `meta.provider` schema field (optional, backward-compatible)
- No adapters yet; pipeline calls stay on their current path but read
  `ctx.llm_provider` if set.

**Phase B1.2 (3 days) — Adapters + policy**

- Three adapters + registry
- Policy loader + tests
- OCA runner refactor onto `LLMProvider`
- Pipeline stages migrated (feature-flagged fallback to current behavior
  for one release)

**Phase B2.1 (3 days) — SI&L schema + decorator + local store**

- Record model + decorator no-op path + rollup
- SQLite backend + snapshot writer
- `architect_component_health` MCP tool

**Phase B2.2 (3 days) — Instrument all sites**

- Pipeline stages, MCP tools, renderers, validators
- Snapshot cron / on-demand
- Roll-up integration into `architect_evaluate` output

**Phase B3.1 (3 days) — Pipeline view/slice/renderer + data JSON**

- `pipeline.slice.yaml`, `pipeline.view.yaml`
- `pipeline-html` renderer + JSON emitter
- Golden-snapshot test

**Phase B3.2 (3 days) — Interactive dashboard + drill-down**

- HTML/CSS/JS assets
- Playwright smoke test
- CONTEXT.md dashboard section

## 6. Risks

- **Instrumentation surface is large (~40 sites).** Mitigation: single
  decorator + a helper script (`scripts/apply_sil_decorators.py`) that
  walks the module tree and reports missing decorations. Enforced by a
  CI check that greps decorator presence on required entry points.
- **Policy misconfiguration silently routes to expensive frontier calls.**
  Mitigation: `Policy.pick(...)` requires `max_cost_usd_per_call` in every
  rule; `spend(...)` is called synchronously and raises `BudgetExceeded`
  before the network call; CI runs on a policy where every rule points
  to the stub provider.
- **Dashboard performance on big models.** Mitigation: `pipeline_state.json`
  is capped at N entities per slice; drill-down data is lazily loaded
  from `.architecture/sil/<id>.yaml`.
- **Roll-up correctness depends on manifest allocation map.** Mitigation:
  golden tests on the fixture with a hand-verified rollup; drift = alert.

## 7. Definition of done

- All new files land; all listed tests pass.
- `pytest tests/ -v --ignore=tests/test_config_loader.py` green on both
  repos.
- A full pipeline run on a fixture repo emits SI&L records for every
  stage, tool, renderer, and validator invoked.
- `architect_component_health COMP-2.1` returns a populated record with
  non-zero `invocations_7d` after the fixture run.
- `.architecture-model.yaml` on the fixture has `meta.provider` populated
  when the pipeline is run with a non-default policy.
- `pipeline.html` renders, badges display, drill-down panel opens on
  click, links to `logs-db#<id>` present for components with open
  comment stubs.
- CONTEXT.md updated with `## SI&L + LLM Provider Layer + Pipeline
  Dashboard` section.
