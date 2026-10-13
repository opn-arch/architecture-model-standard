# CAP-DF Part 13 — `CAP-WK.llm-endpoint-inventory` walk

**Date:** 2026-09-18
**Author:** JIT plan derived from master design `docs/plans/2026-09-18-cap-df-ceremony-and-llm-coverage-design.md` (`ca8b3c0`).
**Status:** draft — execute after Part 12 (`d0f719b` / OCA `fd9775e`).

## Goal

Audit which LLM integration points exist across the AMS + OCA codebases and cross-reference them against a declared inventory. Emits Cards per endpoint: `covered` (declared + AST-visible), `undeclared` (AST-visible, not in inventory), `stale` (declared, no AST match), `legacy` (uses `llm_callback` instead of `LLMProvider` Protocol). No behavioral change — this is a pure meta-walk (Tier T1, no LLM call).

**Coverage impact:** 12 → **13 covered** (adds `CAP-WK.llm-endpoint-inventory`).

## Scope

**AMS-only work.** OCA endpoints are audited by cross-repo AST scan (path resolved relative to the AMS repo root — `../opencode-arch/` by default, override via arg). No OCA commit needed for Part 13.

## Design decisions (locked)

1. **Detection strategy:** Pure `ast.walk` over each `.py` source file. Detect `Call` nodes whose `.func` matches one of six patterns:
   - `provider.complete(...)`, `provider.structured(...)`, `provider.stream(...)` — new Protocol
   - `ctx.llm_enrich(...)` — pipeline stage entry
   - `llm_callback(...)` — legacy pattern (attribute or bare name)
   - `run_via_policy(...)` — OCA policy router
   Match on attribute name only (not receiver identity) — receiver names vary (`self.provider`, `_prov`, etc.). False-positive risk accepted (a `.complete` call on an unrelated object is caught by declared inventory: undeclared calls become `undeclared` verdicts, not silently covered).

2. **Endpoint identity:** `endpoint_id` = `"<repo_slug>:<posix_relpath>:<lineno>"`. Deterministic, cross-repo-safe. `repo_slug` = last path component of the repo root (`architecture-model-standard` / `opencode-arch`). This makes IDs stable across machines when the two repos sit side-by-side under any parent.

3. **Declared inventory format:** `.architecture/llm/endpoints.yaml` at AMS root. Top-level key `endpoints:` — list of `{id, location, kind, task_class, tier, migration_status}` records. `id` matches the AST-derived form above. `migration_status` ∈ `{"protocol", "legacy", "provenance", "routing"}`. First cut declares all 29 endpoints from the master design's inventory tables.

4. **Card schema:** dataclass `EndpointCard(endpoint_id: str, verdict: str, details: dict, location: str | None = None)`. Verdicts: `covered` | `undeclared` | `stale` | `legacy`. `legacy` overrides `covered` when `migration_status == "legacy"` (a declared+visible legacy endpoint still surfaces as legacy so the audit can drive migration).

5. **Silent-skip on missing OCA:** If the sibling OCA repo path doesn't exist, the walk audits AMS only and emits an informational Card with `endpoint_id="__meta__:oca_missing"`, `verdict="undeclared"`. No exception.

6. **Testing strategy:** Unit-test on synthetic fixture repos (`tmp_path`-hosted directory trees with hand-written Python files containing each call pattern). No dependency on the real AMS/OCA source trees — keeps tests hermetic and fast (target <1s).

7. **Model wire:** Add sub-cap `CAP-WK.llm-endpoint-inventory` under `CAP-WK` in `capabilities.v3.yaml`. Realizing promise flipped `proposed → verified` with 3 `verified_by` entries (walk, endpoints.yaml, tests). Meta-coverage discovery uses the existing docstring marker regex — walk module gets a `Realizes ``CAP-WK.llm-endpoint-inventory``` line.

## Deferred (out of scope for Part 13)

- **Endpoint execution.** Part 13 declares the inventory and audits coverage. Actually routing calls through `Policy.pick` for each declared endpoint lands in Part 14.
- **Task-class enforcement.** The `task_class` field in `endpoints.yaml` is declarative-only until Part 14 wires the bundler.
- **Tier-based cost estimation.** Same — declared but inert.
- **Fixture generation from real repos.** Tests use synthetic fixtures. A follow-up (candidate lesson) could add a snapshot test that runs the walk against the real AMS+OCA trees and gates on regression, but that's not blocking.

## Task list

1. **Create `.architecture/llm/endpoints.yaml`** — declare all 29 endpoints from the master design tables. Use the design doc's `location` strings verbatim; `id` derived as `<repo_slug>:<posix_relpath>:<lineno>` when the location has a `file:line` pattern, else a stable synthetic id.
2. **Write `src/architecture_model/walks/meta/llm_endpoint_inventory.py`** — the meta-walk. Module docstring includes `Realizes ``CAP-WK.llm-endpoint-inventory``` marker.
3. **Write `tests/walks/meta/test_llm_endpoint_inventory.py`** — synthetic fixtures + tests for each verdict (covered / undeclared / stale / legacy / missing-OCA).
4. **Wire `CAP-WK.llm-endpoint-inventory` in `.architecture/model/capabilities.v3.yaml`** — add sub-cap; flip `PR-CAP-WK-llm-endpoint-inventory-intent` to `verified`.
5. **Update `CONTEXT.md`** — Part 13 additions block after the Part 12 block. Note new walk, endpoints.yaml location, coverage bump to 13.
6. **Verification gate** — full AMS pytest (~4316 → ~4324 pass), meta-coverage audit shows 13 covered / 0 uncovered.
7. **Commit** — `feat(model): Part 13 — CAP-WK.llm-endpoint-inventory (LLM endpoint audit walk)`.

## Files created / modified

**New:**
- `.architecture/llm/endpoints.yaml`
- `src/architecture_model/walks/meta/llm_endpoint_inventory.py`
- `tests/walks/meta/test_llm_endpoint_inventory.py`

**Modified:**
- `.architecture/model/capabilities.v3.yaml` (add sub-cap + flip promise)
- `CONTEXT.md` (Part 13 additions block)

## Success criteria

- All AMS tests pass (unchanged count + new tests).
- Meta-coverage audit reports **13 covered, 2 duplicate-walk, 0 uncovered**.
- `endpoints.yaml` parses via `yaml.safe_load`; all 29 endpoints present with all required fields.
- Walk detects both new-protocol (`provider.structured`) and legacy (`llm_callback`) patterns on synthetic fixtures.
- Silent-skip verified: missing OCA sibling directory yields a Card, not an exception.
