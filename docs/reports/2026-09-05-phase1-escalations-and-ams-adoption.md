# Session report: Phase 1 escalations + opencode-arch adaptation

**Date:** 2026-09-05
**Author:** OpenCode (interactive session, user-driven)
**Scope:** Two coordinated development branches across two repos, driven by nits surfaced during earlier Phase 2 opencode-arch work.

---

## Executive summary

Nine escalated nits (N50, N52, N53, N64, N73, N74, N81, N100, N105) were fixed on the primary `architecture-model-standard` repo. A companion adaptation branch on `opencode-arch` then consumed the two APIs that clearly fit, evaluated the rest, and documented the outcomes. Both branches are merged and pushed to `opn-arch`.

- **architecture-model-standard:** 2885 → **2918 tests passing** (+33 new tests, 0 regressions), same 6 pre-existing failures.
- **opencode-arch:** **917 tests passing** (unchanged), same 2 pre-existing failures. Behavior-preserving refactor.

All API additions on ams are **additive** (new symbols, subclass exceptions, aliased renames). No breaking changes.

---

## Repo 1: architecture-model-standard — Phase 1 escalations

### Branch

- Name: `feat/phase1-escalations` (short-lived, now deleted)
- Base: `feat/curated-se-views` @ `7f0c7dc`
- Final tip: merge commit `27458c0` on `feat/curated-se-views`
- Pushed to: `origin/feat/curated-se-views` on `opn-arch/architecture-model-standard.git` (via new SSH alias `github-opnarch`)

### Task ledger (10 tasks, all reviewer-approved)

| # | Nit | Commit | Change | Tests added |
|:-:|:---:|:------:|:-------|:-----------:|
| Plan | — | `918fb15` | 10-task plan committed | — |
| T1 | N73 | `24d6751` | Removed clock injection from `_parse_meta` | +1 |
| T2 | N81 | `1583efe` | Added `.id` alias on `ArchitecturePackage` | +1 |
| T3 | N50 | `3feff3b` | Canonical `ParseError` (new `core/errors.py`, 4 raise sites wired, re-exports) | +7 |
| T4 | N74 | `787dd20` | Publicized `generation_dir`, kept `_generation_dir` alias | +3 |
| T5 | N53 | `78d1f82` | Added `current_root_digest(pkg)` helper | +2 |
| T6 | N64 | `69c2160` | Added `Provenance.proposal_id` (auto-derived SHA-256) | +4 |
| T7 | N100 | `67f9b72` | Added `WorkOrder.build(...)` factory classmethod | +6 |
| T8 | N52 | `78c743e` | Added `apply_model_patch` at `ai/patch.py` (add/remove/replace; move→ParseError) | +6 |
| T9 | N105 | `915a33a` | Added `MaterializedSlice.to_dict()` emitting `fragment` key | +3 |
| T10 | — | `9e06d3a` | Completion report + CONTEXT.md API inventory | — |

**Merge commit:** `27458c0` (`--no-ff` into `feat/curated-se-views`, preserves history).

### New public APIs shipped

```python
from architecture_model.core import ParseError                                   # canonical parse error
from architecture_model.lifecycle import generation_dir, current_root_digest
from architecture_model.lifecycle.package import ArchitecturePackage             # now has .id property
from architecture_model.lifecycle.model_slice_materializer import MaterializedSlice
                                                                                 # .to_dict() emits fragment key
from architecture_model.ai import apply_model_patch
from architecture_model.ai.work_order import WorkOrder                           # .build(...) factory
from architecture_model.ai.proposals import Provenance                           # auto-derived proposal_id
```

### Test delta

| | Baseline | Final | Delta |
|:-|:-:|:-:|:-:|
| Passed | 2885 | **2918** | **+33** |
| Pre-existing failures | 6 | 6 | 0 |
| Regressions | — | **0** | — |

### Follow-up nits (deferred, non-blocking)

1. **N73-followup** — `types.py:780` writes `generated_at` unconditionally on emit; add emit-side guard for byte-identical round-trip.
2. **N50-ripple** — `ai/proposals.py:30/32/34` `Provenance.__post_init__` still raises bare `ValueError`; migrate to `ParseError`. `serialization.py:171` lost yaml `node.start_mark` (line/col); restore.
3. **N53-nit** — malformed `digest.json` still raises raw `json.JSONDecodeError`/`KeyError` in some readers; wrap in `ParseError`.
4. **N64-nit** — `proposal_id` payload uses unescaped `|` delimiter — collision-prone if fields accept free-form text.
5. **N100-nits** — `id` shadows builtin (consider `work_order_id`); slice tuple `(id, rev)` positional in hash schema.
6. **N52-nits** — `move` op deferred as `ParseError`; `_apply_add` depends on private `_parse_raw`; silent no-op on missing `target_id` for `remove`/`replace` (undocumented policy).

---

## Repo 2: opencode-arch — AMS API adoption

### Branch

- Name: `feat/ams-api-adoption` (short-lived, now deleted)
- Base: `main` @ `531b845`
- Final tip: merge commit `4aadf39` on `main`
- Pushed to: `origin/main` on `opn-arch/opencode-arch.git`

### Task ledger (Scope B per user)

| # | Task | Commit | Outcome |
|:-:|:-----|:------:|:--------|
| Plan | AMS API adoption plan (Scope B) | `31aa5d9` | Committed |
| T1 | Adopt `generation_dir` (N74) | `3fa8f2a` | **Adopted** at 4 sites (`mcp/tools/lifecycle/{package_load,package_merge,package_diff}.py`, `cli/lifecycle.py`) |
| T2 | Delegate to public `apply_model_patch` (N52) | `a72c913` | **Documented + retained** — contracts diverge (dict vs dataclass, `InvalidProposalError` vs `ParseError`, dry-run wrapper). Docstring pointer added. |
| T3 | Adopt `current_root_digest` (N53) | `7f17b62` | **Adopted** in `lifecycle_exec/apply.py` (−8 / +2) |
| T4 | Adopt `MaterializedSlice.to_dict` (N105) | — | **Skipped** — MCP response shape adds `digest`/`persisted_path`, omits `provenance`. Adoption would break the response contract. |
| T5 | Adopt `WorkOrder.build` + `Provenance.proposal_id` auto-derive (N100/N64) | — | **N/A** — opencode-arch never uses `WorkOrder(...)` directly (only `.from_dict`); all 5 `Provenance(...)` sites already omit `proposal_id`. |
| T6 | Completion report + CONTEXT | `97251b2` | Committed |

**Merge commit:** `4aadf39` (`--no-ff` into `main`).

### Adoption breakdown

- **Adopted:** 2 APIs (`generation_dir`, `current_root_digest`)
- **Evaluated + retained** (contract divergence, documented): 1 API (`apply_model_patch`)
- **Evaluated + skipped** (shape divergence): 1 API (`MaterializedSlice.to_dict`)
- **Already in use** (no work needed): 1 API (`Provenance.proposal_id` auto-derive)
- **Not applicable** (no callsites): 1 API (`WorkOrder.build`)

**Honest scope B outcome:** opencode-arch was already in reasonably good shape. Private→public renames landed cleanly; contract-mismatched adoptions were correctly left alone rather than forced.

### Test delta

| | Baseline | Final | Delta |
|:-|:-:|:-:|:-:|
| Passed | 917 | **917** | 0 |
| Pre-existing failures | 2 | 2 | 0 |
| Regressions | — | **0** | — |

Zero test-count change is the expected outcome for a behavior-preserving refactor.

### Follow-up notes

1. **`apply_model_patch` contract convergence** — if opencode-arch's `_apply_ops` is ever migrated to `ArchitectureModel` dataclass mutation (rather than raw yaml dict), delegate to the public helper. Requires test-error-type migration.
2. **`MaterializedSlice.to_dict` extension** — if the ams library grows `**extra` merge support or the opencode-arch response contract drops `digest`/`persisted_path`, adoption becomes viable.
3. **Scope C (ParseError migration)** — deferred; migrate opencode-arch error handling in parser-adjacent paths to catch the canonical `ParseError`.

---

## Infrastructure work performed en route

1. **SSH config for opn-arch push access** — user's `baigm2_cat` account had no write on opn-arch. User provided the `opnarch` private key at `~/.ssh/opnarch`. Configured `~/.ssh/config` with `Host github-opnarch` alias routing github.com through that key. Origin remotes on both repos switched to `git@github-opnarch:opn-arch/<repo>.git`.
2. **GitHub secret-scanning unblock** — push of `feat/curated-se-views` was blocked by push protection on a pre-existing commit (`9d7e3b3`) containing what GitHub flagged in `.opencode/plans/*.md`. User approved via GitHub's unblock URL; push then succeeded.
3. **Worktree hygiene** — both feature worktrees created under `.worktrees/`, both cleaned up after merge; both feature branches deleted.

---

## Environment reference (for future sessions)

**architecture-model-standard tests:**
```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py
```
Baseline: 2918 passed, 6 pre-existing failures.

**opencode-arch tests (requires ams `feat/curated-se-views` on path):**
```
PYTHONPATH="$PWD/src:/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/curated-se-views/src" \
  /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/e2e
```
Baseline: 917 passed, 2 pre-existing failures.

**Push access:** SSH alias `github-opnarch` via `~/.ssh/opnarch` key; both `origin` remotes updated.

---

## What was NOT done (explicit non-goals)

- No changes to `.architecture*` telemetry directories (per constraint).
- No `pip install -e` invocations (breaks fastmcp per CONTEXT).
- No history rewrite to remove the flagged secret in `9d7e3b3` — user approved the unblock URL instead.
- No `feat/curated-se-views` → `main` merge on ams — that's a separate decision the user did not request in this session.
- Scope C (opencode-arch `ParseError` migration) deferred by user's Scope B selection.
- Deferred follow-up nits (documented above) were not implemented — they represent low-risk maintenance items surfaced during this session, to be picked up in a future pass.

---

## Deliverables index

- `architecture-model-standard/docs/plans/2026-09-05-phase1-escalations.md` — full 10-task plan + completion report
- `architecture-model-standard/CONTEXT.md` — updated API inventory + test count
- `opencode-arch/docs/plans/2026-09-05-ams-api-adoption.md` — 6-task adoption plan + completion report
- `opencode-arch/CONTEXT.md` — updated with AMS API adoption summary
- This session report — `architecture-model-standard/docs/reports/2026-09-05-phase1-escalations-and-ams-adoption.md`
