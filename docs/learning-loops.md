# Learning Loops Audit

Audits which learning-and-improvement hooks are wired into each of the
seven operational pipelines the model claims. Every pipeline anchor
below has at least one closed-loop path where signal collected during a
run is persisted and re-consumed on the next run — this is the
precondition for adopting the standard as a **self-improving substrate**.

Sources:

- `src/architecture_model/pipeline/coordinator.py` — orchestrator; injects `LearningStore`
  + `GlobalLearningStore` into every stage context, records stage scores
  after every run, appends per-stage history rows.
- `src/architecture_model/pipeline/history.py` — `append_pipeline_history()` →
  `.architecture/pipeline-history.jsonl`.
- `src/architecture_model/pipeline/learning.py` — per-repo `LearningStore`
  (corrections, calibration, stage-quality history).
- `src/architecture_model/pipeline/global_learning.py` — cross-repo
  `GlobalLearningStore` (heuristic rules, archetype patterns, workflow
  lessons).
- `src/architecture_model/pipeline/lessons.py` — one-shot lesson recorder used
  by the SELF-IMPROVEMENT pipeline.
- `src/architecture_model/feedback/{gates,drift,test_results}.py` — append-only
  JSONL journals under `.architecture/*.jsonl`.
- `src/architecture_model/sil/{record,rollup,decorators}.py` — SI&L event
  store `.architecture/sil.sqlite` + component rollups.

## Coverage Matrix

| Anchor    | Pipeline           | Signal capture                                                                                | Persistence                                                                    | Re-injection on next run                                                                                                | Loop closed |
| --------- | ------------------ | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- | ----------- |
| BEH-P1    | EXTRACT            | Per-stage `stage_quality` scores + validator issues per run (`coordinator.py:406`)            | `.architecture/pipeline-history.jsonl` (`history.py:append_pipeline_history`)  | `LearningStore.get_calibration(stage)` seeds `ctx.calibration` at `coordinator.py:130`                                  | yes         |
| BEH-26    | SLICE              | Slice provenance + `stale.yaml` cache written by `lifecycle/rebuild.py`                       | `.architecture/lifecycle/stale.yaml`; per-artifact `<id>.provenance.json`      | Rebuild plan reads sidecars via `mcp.tools.evaluate._collect_freshness_summary`; skips fresh outputs                    | yes         |
| BEH-27    | SELF-IMPROVEMENT   | Lessons emitted from stage failures + user corrections (`pipeline/lessons.py`)                | `.architecture/learning/history.json`; global store at `~/.architecture-model` | `GlobalLearningStore.get_heuristics/archetypes/workflows()` injected into `ctx.global_learning` at `coordinator.py:134` | yes         |
| BEH-28    | DEV-LOOP           | Comments captured via `cli/comment.py`; work-orders (`ai/work_order.py`); jobs                | `.architecture/comments/`, `.architecture/ai/workorders/`, `.architecture/ai/jobs/`           | `architect_work_issue` resolves stubs on next iteration; job state transitions carry `error` / `result_ref`             | yes         |
| BEH-LLM   | LLM-PROVIDER       | Per-call latency, tokens, cost; policy fallbacks in `llm/*` adapters                          | `meta.provider = {name, model, policy_ref}` stamped on emitted model           | `run_via_policy` reads `.architecture/llm/policy.yaml`; enforces per-call cost caps and remembers failures via fallback | yes         |
| BEH-SIL   | SI&L LOGGING       | `@sil_instrument` decorator captures every architecturally-significant call site              | `.architecture/sil.sqlite` (ring-buffered 50 events/component)                 | `sil/rollup.py` snapshots to `.architecture/sil/<component_id>.yaml`; consumed by `architect_component_health`          | yes         |
| BEH-FBK   | FEEDBACK JOURNALS  | Gate outcomes, drift snapshots, JUnit ingest (`feedback/{gates,drift,junit_ingest}.py`)       | `.architecture/gates.jsonl`, `.architecture/drift.jsonl`, `.architecture/test_results.jsonl`  | `supplementary_loaders.load_gates/drift/test_results()` resolves refs at slice materialization time                     | yes         |

All seven anchors close their loop: signal → persistence → re-injection.

## Cross-Cutting Invariants

- **Every run appends history.** `Pipeline._record_history()` at
  `coordinator.py:148-168` writes per-stage + per-run rows regardless
  of success/failure so the corpus grows monotonically.
- **Calibration is per-stage-per-repo.** `LearningStore.get_calibration()`
  keys on `stage_name`, so seed values improve independently for each
  operational stage.
- **Global lessons are cross-repo.** Heuristic rules (HR-*), archetype
  patterns (AP-*), and workflow lessons (WL-*) live in
  `~/.architecture-model/learnings.yaml` and apply to every subsequent
  project analyzed by the pipeline.
- **All journals are append-only JSONL.** Nothing is silently rewritten;
  every past decision remains inspectable.

## Verifying the Loop Locally

```bash
# 1. Show what's currently in the global lesson store
architecture-model learnings

# 2. Show per-pipeline gap posture
architecture-model audit .architecture-model.yaml

# 3. Confirm every pipeline anchor has zero completeness gaps
python -c "from architecture_model.core.parser import load_model;\
from architecture_model.core.validator import validate_model;\
r = validate_model(load_model('.architecture-model.yaml'));\
print(sum(1 for i in r.issues if (i.code or '').startswith('PIPELINE_')))"

# 4. Inspect the append-only history stream
tail -5 .architecture/pipeline-history.jsonl
```

Expected: audit reports `Total gaps: 0`; the Python one-liner prints
`0`; `pipeline-history.jsonl` shows recent runs with per-stage scores.
