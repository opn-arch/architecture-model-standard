# Functional Block Accuracy, Multi-Language Generalization & Requirements Traceability

**Status:** Design proposal
**Scope:** architecture-model-standard (deterministic core) + opencode-arch (LLM-assisted layer)
**Core principle:** The deterministic pipeline must remain fully deterministic and language-agnostic. All LLM involvement is additive, cached, non-default, and never mutates or feeds back into the deterministic model.

---

## 1. Background / Problem Statement

Functional blocks (F-blocks) are currently produced by two independent mechanisms:

1. **Directory-based discovery** (`discover_config`, `_discover_functional_blocks`, `_discover_sub_blocks`) — one directory = one F-block, purely spatial, no awareness of actual coupling. This is the default path and assumes a Python package-layout convention.
2. **Dependency clustering** (`auto_assign_f_blocks`) — greedy graph clustering by `depends-on` edges, only invoked as a fallback when a component has no `f_block` at all.

Neither mechanism validates itself against the other, and directory-based discovery — the primary path — has no way to detect when it's wrong. This is a particular problem for **multi-language generalization**: Python's package-layout convention (subdirectory = module boundary) does not hold uniformly across languages, so directory discovery may produce meaningless F-blocks for non-Python codebases produced by a tree-sitter or LLM-based scanner.

Separately, there is no traceability from individual functions back to product/system requirements — capabilities have a loose free-text `requirements: list[str]` field, but nothing connects a specific function to a specific, citable requirement.

This document captures the agreed design for closing both gaps while preserving full determinism in the core pipeline.

---

## 2. F-Block Accuracy Metrics (deterministic, language-agnostic)

All metrics operate on the `depends-on` graph and file layout only — no language-specific parsing required beyond having components and edges, which any scanner (AST, tree-sitter, or LLM-derived) already produces.

| Metric | What it measures | Method |
|---|---|---|
| **Modularity (Q)** | Internal-cluster edge density vs. expected random-graph density | `Q = (1/2m) Σ (A_ij − k_i·k_j/2m)·δ(c_i,c_j)` over `depends-on` edges |
| **Conductance per block** | How "leaky" a block boundary is | `edges_out / (edges_out + edges_in)` |
| **Intra/inter edge ratio** | Cheap proxy for modularity | `intra_edges / total_edges` |
| **Directory/clustering agreement rate** | % of components where directory-assigned and clustering-assigned F-block match | `count(agree) / total_components` |
| **Orphan rate** | % of components with zero `depends-on` edges (unclusterable regardless of language) | `count(degree=0) / total_components` |
| **Cluster balance** | Detects degenerate decomposition (one giant block + singletons) | variance / Gini coefficient of cluster sizes |
| **Cross-block cycle ratio** | Bidirectional edges between two F-blocks — signals a wrong boundary, since a clean decomposition should be roughly a DAG at block level | `cyclic_block_pairs / total_block_pairs_with_edges` |

**Primary metrics:** Modularity and conductance — standard literature metrics, language-agnostic, single global score + per-block score, trackable over time via the existing `learning_curve` telemetry table.

**Determinism requirement:** `auto_assign_f_blocks` currently sorts components by degree with no documented tie-break. Add a fixed secondary sort key (component ID, lexicographic) so identical repo state always produces identical clustering.

---

## 3. Storage & Tagging Scheme

Extend the manifest with a per-component scoring block, stored **alongside**, not inside, the existing `f_block` field, so nothing downstream that reads `f_block` breaks.

```json
{
  "component_id": "COMP-3",
  "f_block": "F3",
  "fblock_provenance": {
    "source": "directory",
    "confidence": 0.82,
    "metrics": {
      "modularity_contribution": 0.34,
      "conductance": 0.12,
      "directory_clustering_agree": true,
      "orphan": false
    },
    "content_hash": "sha256:...",
    "computed_at": "2026-08-03T..."
  }
}
```

`confidence` is a fixed formula over the metrics above — deterministic given the graph, no LLM involved at this stage.

### LLM review layer (additive, never overwrites deterministic fields)

Only triggered when `fblock_provenance.confidence` falls below a configurable threshold (default 0.5) — i.e., only where the deterministic signal is weakest.

```json
{
  "fblock_llm_review": {
    "triggered_because": "confidence_below_threshold",
    "language": "typescript",
    "suggested_f_block": "F4",
    "model": "claude-sonnet-5",
    "prompt_hash": "sha256:...",
    "temperature": 0,
    "self_reported_confidence": 0.7,
    "cached": true
  }
}
```

The LLM's `self_reported_confidence` is treated as **untrusted input, not fact**. Reconciliation (which value wins) is itself a deterministic rule — e.g. "LLM suggestion adopted only if it agrees with directory assignment, otherwise flagged for manual review." The LLM layer never feeds back into `auto_assign_f_blocks`'s graph computation — it annotates after the deterministic pass is complete.

---

## 4. Determinism Discipline for Any LLM-Involved Step

Applies uniformly to F-block review, the audit pass (§5), and requirements traceability (§6):

- **Cache key:** `(content_hash of input, prompt_template_hash, model_id)` — identical inputs always return the cached output; unchanged code never re-queries the model.
- **`temperature=0`** on all calls, to minimize (not eliminate) run-to-run variance on genuinely new inputs.
- **Prompt templates are version-hashed** and stored in output artifacts, so changing a prompt correctly invalidates old cached results rather than silently going stale.
- **LLM output never mutates the deterministic model or manifest.** It is always a separate, additive artifact.
- **LLM calls live in opencode-arch, not architecture-model-standard.** The core library has zero LLM dependency; invocation is gated by language + confidence score.

---

## 5. LLM Functional-Decomposition Audit (opencode-arch, flag-gated)

An independent, full second opinion on functional decomposition — not a per-component tag, a top-down re-derivation. Used to catch domain-specific decomposition errors that graph metrics structurally cannot see (e.g., a documented subsystem boundary that the dependency graph doesn't capture, or a framework convention like "fat model, thin controller").

**Tool:** `architect_llm_audit(repo_path, model_yaml)` — explicit flag, never part of the default `architect_extract` pipeline. Output: `.architecture-models/llm-audit.json`, purely additive.

### Two-stage process (prevents agreement bias)

1. **Blind decomposition:** LLM sees only source code + existing docs (README, CONTEXT.md). The tool's `f_block` assignments and manifest are explicitly withheld. LLM proposes its own functional grouping with rationale.
2. **Comparison:** LLM is now shown the tool's `f_block` assignments and modularity/conductance scores, and asked to reconcile — citing specific evidence for any disagreement (naming conventions, documented boundaries, misplaced files).

### Output schema

```json
{
  "audit_id": "sha256(repo_content_hash + prompt_version)",
  "model": "claude-sonnet-5",
  "temperature": 0,
  "llm_decomposition": {
    "blocks": [
      {"id": "LLM-A", "name": "Manifest scanning", "components": ["scanner.py", "body_hints.py"], "rationale": "..."}
    ]
  },
  "comparison": {
    "agreement_rate": 0.71,
    "matched_pairs": [
      {"tool_fblock": "F5", "llm_block": "LLM-A", "overlap": 0.9, "verdict": "agree"}
    ],
    "disagreements": [
      {
        "tool_fblock": "F3",
        "llm_block": "LLM-C",
        "overlap": 0.4,
        "llm_rationale": "merger.py is grouped by directory under core, but is functionally part of the enrichment pipeline per README.md#L42.",
        "cites_doc": "README.md#L42",
        "deterministic_signal": {"conductance": 0.31, "modularity_contribution": 0.02},
        "recommendation": "flag_for_review"
      }
    ]
  }
}
```

Every disagreement carries `deterministic_signal` alongside the LLM's rationale — a disagreement backed by both a documented rationale *and* a weak conductance score is much higher-confidence evidence of a real problem than LLM opinion alone.

---

## 6. Requirements Traceability

### 6.1 Schema extension

**New entity type: `Requirement`**

| Field | Type | Required | Description |
|---|---|---|---|
| id | str | yes | `REQ-042` |
| text | str | yes | The requirement statement |
| source_doc | str | yes | Path to the requirements document |
| source_anchor | str | yes | Line number, heading, or ID within that doc — the actual citation |
| status | enum | yes | ACTIVE, PLANNED, DEPRECATED |
| content_hash | str | yes | Hash of `source_doc` at extraction time — staleness detection |

**Function addressability:** Add `id: str` to `FunctionSignature` (currently unaddressed), formatted as `{component_id}::{function_name}` (e.g. `COMP-3::compute_complexity`) — stable, derivable, no new counter needed.

**New relationship type: `satisfies`** — `from: COMP-3::compute_complexity, to: REQ-042, type: satisfies`. Kept distinct from the existing `traces-to` (component→behavior, component-granular) since `satisfies` is function-granular.

### 6.2 Extraction — deterministic where possible, LLM-assisted where not

**Tier 1 — deterministic (opencode-arch, no LLM):**
Requirements docs with recognizable structure (`REQ-\d+` IDs, `### Requirement:` headings, checkbox lists) are parsed with regex/structural rules. `source_anchor` is exact; `content_hash` pins the doc; zero ambiguity.

**Tier 2 — LLM-assisted, cached (opencode-arch):**
Freeform prose docs (a PRD without formal IDs) need semantic segmentation. Same cache/determinism discipline as §4. Output tagged `extraction_method: "llm_segmented"` vs. `"structural"` so downstream consumers know which requirements are exact citations vs. inferred boundaries. `source_anchor` is best-effort (paragraph offset) in this tier, not guaranteed line-exact.

### 6.3 Function → Requirement matching (`satisfies` edges)

This is a semantic match with no graph signal available (no dependency edge exists between a docstring and a requirement doc) — necessarily LLM-assisted, but grounded in deterministic evidence wherever possible.

```json
{
  "function_id": "COMP-3::compute_complexity",
  "satisfies": [
    {
      "requirement_id": "REQ-042",
      "confidence": 0.81,
      "evidence": "Function name and body_hint match REQ-042's 'weighted complexity scoring' language; test_contracts test_symbols_contribute/test_deps_contribute directly assert the weighting formula described in REQ-042.",
      "extraction_method": "llm_matched",
      "model": "claude-sonnet-5",
      "prompt_hash": "sha256:...",
      "cache_key": "sha256(function_id + requirement_id + prompt_hash)"
    }
  ]
}
```

Critically, the LLM is given **`test_contracts` and `body_hints` as evidence**, not just function names — this grounds the matching decision in AST-derived ground truth the manifest already produces (a test asserting a specific weighted formula is real, checkable evidence a requirement is satisfied, not an LLM guess from a name alone).

### 6.4 Coverage: 8th dimension

`_check_requirement_traceability`, added to `coverage_report` (currently 5 checks; §7 proposes a 6th and 7th):

- **Orphan functions:** % of ACTIVE, non-trivial functions (excluding `__init__`/trivial getters) with zero `satisfies` edges
- **Orphan requirements:** % of `Requirement` entities with zero incoming `satisfies` edges — arguably the more actionable finding
- **Low-confidence coverage:** % of `satisfies` edges below a confidence threshold, flagged for human review

Reports `null`/`not_run` when no requirements doc is configured — opt-in feature, does not penalize repos without one.

### 6.5 Pipeline placement

New MCP tool `architect_trace_requirements(repo_path, model_yaml, requirements_doc)` — explicit flag, not part of default `architect_extract`. Output: `.architecture-models/requirements-trace.json`, additive, never overwrites the model.

### 6.6 Open question — not yet decided

Does `satisfies` require a **complete requirements doc up front** (doc exists before code, waterfall-style), or must it also work **retroactively** on codebases with no requirements doc (which would require reverse-deriving a requirements doc from behavior/capability descriptions before tracing back to it)? The retroactive case is a fundamentally riskier LLM task — there's no ground-truth doc to anchor against. **Needs a decision before implementation begins.**

---

## 7. Coverage Report — Full Dimension List (proposed)

| # | Check | Status |
|---|---|---|
| 1 | Component coverage | Existing |
| 2 | Relationship accuracy | Existing |
| 3 | Capability coverage | Existing |
| 4 | Interface coverage | Existing |
| 5 | Staleness | Existing |
| 6 | F-block quality (modularity, conductance, agreement rate) | Proposed, §2/§3 |
| 7 | LLM audit agreement (optional, `null` if not run) | Proposed, §5 |
| 8 | Requirement traceability (optional, `null` if not run) | Proposed, §6.4 |

---

## 8. Multi-Language Generalization — Summary of Decisions

- **Core scanner seam** (`scan_file` equivalent) should generalize via **tree-sitter**, not LLM — deterministic, multi-language, preserves exact-text body-hint fidelity that drove 100% blind-regeneration fidelity in the Python benchmark.
- **LLM calls live only in opencode-arch**, gated by **language + confidence score**, never in architecture-model-standard.
- **Directory-based F-block discovery should not be trusted uniformly across languages.** For languages where directory-layout conventions don't map cleanly to modules, dependency clustering (§2) should be the primary signal, with directory discovery demoted to a secondary/validation signal — inverse of the current Python-oriented default.
- **Redundant scanning problem:** the same file is currently scanned 2–4x across independent code paths (`process_block`, the module-level pass in `generate_manifest`, `generate_block_manifest`, `compose_enriched_model`). A **per-file scan cache** keyed on `(absolute_path, content_hash)`, scoped to one pipeline run, must be added before wiring in any LLM fallback per file — otherwise LLM cost multiplies 2–4x unnecessarily.

---

## 9. Non-Negotiable Constraints (recap)

1. architecture-model-standard remains 100% deterministic, zero LLM dependency.
2. All LLM calls live in opencode-arch, gated by language + confidence, cached by content hash, `temperature=0`.
3. LLM output is always additive — separate artifacts, never overwrites or mutates the deterministic model/manifest.
4. LLM audit/review features are explicit, flag-gated tools — never part of the default pipeline.
5. Every LLM judgment is paired with the deterministic signal it agrees or disagrees with, so downstream consumers can weight LLM output against real evidence rather than trusting it standalone.
