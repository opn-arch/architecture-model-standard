# Sitting C Review — Track 3 Completion Verification

**Date:** 2026-09-10
**Scope:** Post-Track-3 state of the 4 SE panels in the viewer's SE tab
(ConOps / Functional Analysis / Logical Architecture / Use Cases).
**Baseline:** Sitting B (all 4 panels FAIL with 11 diagnostics each).

## Result: PASS — Phantom-ID gap closed

All 4 SE panels regenerated after Task 9's `viewer-curation.yaml` update:

| Panel | Phantom refs (was → now) | "Entity not found" (was → now) |
|-------|--------------------------|--------------------------------|
| ConOps | 7 → 0 | 7 → 0 |
| Functional Analysis | 7 → 0 | 7 → 0 |
| Logical Architecture | 7 → 0 | 7 → 0 |
| Use Cases | 7 → 0 | 7 → 0 |

The 7 phantom curation IDs
(`CAP-COMMENT-COLLABORATION`, `CAP-SIL-INSTRUMENTATION`,
`CAP-LLM-ROUTING`, `COMP-COMMENT-SYS`, `COMP-SIL`, `COMP-LLM`,
`COMP-DASHBOARD`) no longer surface in any of the 4 SE panels.
They have been repointed to the canonical numeric IDs added in
Tasks 3-8: `CAP-16..CAP-18`, `COMP-13..COMP-17`, `LAY-6..LAY-7`,
`BEH-26..BEH-29`, `IF-17..IF-22`.

## Diagnostics still present (not Track 3 scope)

**A1 ConOps** — `82 operational paths omitted (limit 15)`.
The projector still buckets pipeline sub-behaviors and Django auth
handlers as "operational scenarios". Track 5 (FIX-A4.2 at
`se_view_projectors.py:1967`) filters by behavior category/role.

**A4 Use Cases** — same underlying projector, same fix in Track 5.

**A2 Functional Analysis / A3 Logical Architecture** — no
diagnostics beyond the ones Track 5 addresses.

## Remaining viewer.html phantoms (out of Track 3 scope)

`grep -cE "COMP-COMMENT-SYS|COMP-DASHBOARD" .architecture/diagrams/viewer.html`
returns `1`. Source: `.architecture/ai/proposals/plan-a.yaml`
(a historical AI proposal artifact rendered as
`plan-a.html`). Track 3 does not touch proposal artifacts — this is
lifecycle-proposal state, not model curation. Deferred to a separate
ticket if the plan-a.html rendering should be repointed at canonical
IDs post-hoc.

## Verification commands (reproducible)

```bash
# Regenerate SE docs and viewer
PYTHONPATH="$PWD/src" python -m architecture_model.cli.main docs . --se-only
PYTHONPATH="$PWD/src" python -m architecture_model.cli.main viewer .

# Verify no phantom IDs or "Entity not found" in 4 SE panels
for f in conops functional-analysis logical-architecture use-cases; do
  cnt=$(grep -cE "CAP-COMMENT-COLLABORATION|CAP-SIL-INSTRUMENTATION|CAP-LLM-ROUTING|COMP-COMMENT-SYS|COMP-SIL[^-]|COMP-LLM[^-]|COMP-DASHBOARD|Entity not found" .architecture-models/docs/se/$f.md)
  echo "$f: $cnt phantom/not-found refs"
done
# Expected: all four show "0 phantom/not-found refs"
```

## Test suite state

Before Track 3: 3638 passed / 104 skipped (baseline with Track 1 fix).
After Track 3 Task 10:
**3646 passed / 104 skipped / 0 failed** (81s).

Deltas:
- +8 new tests total: 8 `tests/test_track3_phase_b_entities.py` (Task 2 RED tests, all now GREEN)
- 2 renamed tests in `tests/test_layer_entities.py`
  (`test_five_layers_exist` → `test_seven_layers_exist`)
- 3 tests in `tests/test_capability_hierarchy.py` normalized to accept
  both `from_id`/`to_id` and `from`/`to` relationship endpoint keys

## Conclusion

Track 3 objective met: canonical model contains the 20 entities
(2 layers + 5 components + 3 capabilities + 6 interfaces + 4 behaviors)
and 25 relationships needed to back the Sitting-B-flagged SE panel
content. Curation now references canonical IDs. Ready for Track 4
(slice anchoring) or Track 5 (FIX-A4.2 projector filter).
