# Part 17a — pipeline_v3 Behavior Emission (multi-part buildout)

**Date:** 2026-09-20
**Status:** 17a1 executing
**Parent plan:** `docs/plans/2026-09-20-flow-modeling-substrate.md`

## Motivation

`pipeline_v3` currently emits **one entity kind (component)** and **one
relationship kind (depends-on)**. Composite behaviors (BEH-run-pipeline,
BEH-mcp-dev-loop) are hand-authored in `capabilities.v3.yaml`. To close
the loop between AST reality and the flow substrate landed in Parts
16a-c, pipeline_v3 needs to emit Behaviors, `traces-to`, `triggers`,
and eventually composite call-chain enrichment.

## Sub-parts

### Part 17a1 — Behavior derivation + `traces-to` emission

**Scope (this commit):**

- New stage `pipeline_v3/derive_behaviors.py` between `derive_promises`
  and `cluster` producing `BehaviorCandidate` per public
  module-level function or class method with a non-empty docstring.
- `BehaviorCandidate(id, name, description, owner_module, function_name)`.
- Deterministic id: `BEH-<sha1(owner_module + ":" + function_name)[:8]>`.
- Deterministic order: `(owner_module, function_name)`.
- `containerize.py`: accept `behaviors` param, rebind to owning cluster,
  emit `ContainerizedBehavior(id, name, description, owner_component,
  owner_module, function_name)` and one `traces-to` Link per behavior
  (component → behavior).
- `orchestrator.py`: wire new stage; `PipelineRunResult.behaviors`.
- `publish.py`: emit `entities.behaviors` (omitted when empty for
  digest stability); relationships block already generic.

**Non-scope:**

- Class-level behaviors (per-method only via `method_details` — deferred
  to 17a2 if needed).
- Behavior promises (`preconditions`, `postconditions`, `trigger`).
- Capability derivation.

**Verification gate:** `python -m pytest tests/
--ignore=tests/test_config_loader.py -q` → 4376 baseline → expect
~4395 passed, 0 regressions.

### Part 17a2 — `triggers` relationship emission

Cluster-adjacent behaviors linked via imports on the same call site
become `triggers` edges. Defer until 17a1 lands.

### Part 17a3 — Composite behavior detection

Heuristic: a Behavior whose owning module is a pipeline orchestrator
(imports and calls ≥3 other behaviors in fixed order) is composite.
Emit `sequence:` on outgoing `triggers`.

### Part 17a4 — Call-chain enrichment on composite `traces-to`

Wire `manifest/call_graph.py`. For each composite behavior's
`traces-to` edge, use `trace_flow` from the behavior's function
across imported behavior functions. Attach `call_chain: list[str]`
on the edge (schema field addition mirroring 16a's `sequence:`).

## Backward-compat

- No schema version bump.
- Empty `entities.behaviors` omitted from YAML (existing publish
  fixtures digest-stable).
- `Link.kind` already generic — `traces-to` flows through unchanged.
- `containerize()` signature extended with optional `behaviors=None`
  default = `[]`.
