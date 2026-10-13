# CAP-DF Part 12 JIT Plan — `CAP-WK.author` (LLM-authored promise-content walk)

**Date:** 2026-09-18
**Prev:** Part 11 (`CAP-WK.save`)
**Next:** Part 13 (per-attribute prompt bundling)
**Terminal state after Part 12:** 12 covered / 0–1 uncovered / 2 duplicate-walk

## Purpose

Implement the third verb in the CAP-DF ceremony flow
(`note → save → author → apply`). Given a queued Job produced by
`architect_promise_save`, run an LLM against a hand-rolled v3-native
prompt slice and return a reviewable `ModelPatch` proposal. Do NOT
auto-apply — `architect_proposal_apply` remains a separate user act
(respects L13 self-improvement loop).

## Locked design decisions

| Aspect | Decision |
|---|---|
| Prompt template location | Default: `src/architecture_model/llm/prompts/fill_promise.md` (package resource). Override: `.architecture/llm/prompts/fill_promise.md`. |
| Template strategy | One generic template with `{attribute}` interpolation. |
| Prompt slice | Hand-rolled v3-native projector `assemble_promise_prompt(...)`. |
| Provider layer | `provider_name: str` MCP arg + registry. Default `"none"` → `PRECONDITION_FAILED reason=no_provider`. |
| Apply semantics | Return proposal envelope; do NOT auto-apply. |
| JobState split | Part 11 amended: save auto-advances `draft → approved → queued`. Part 12 walks `queued → running → validating → completed`. |
| Note provenance | Agent-authored from conversation. |

## Tasks

### Task 0 — Part 11 addendum (JobState auto-advance) [OCA]

Modify `src/opencode_arch/mcp/tools/promise_save.py`: after
`JobStore.create(...)`, transition `draft → approved → queued`
with `actor="promise_save"` and reasons documenting auto-approval.

Update `tests/mcp/test_promise_save_tool.py` happy-path to assert
`job.state == "queued"` and history length == 3.

Commit: `feat(mcp): amend architect_promise_save to auto-approve+queue Job (Part 12 prep)`

### Task 1 — Prompt template resource [AMS]

Create `src/architecture_model/llm/prompts/__init__.py` (empty package)
and `src/architecture_model/llm/prompts/fill_promise.md` with sections:
task line, human intent, target entity, existing promises, parent chain,
siblings, 1-hop relations, output instruction.

### Task 2 — `_prompt_assembly.py` helper [AMS]

Create `src/architecture_model/walks/meta/_prompt_assembly.py` exposing:

```python
def default_template_body(repo_path: Path | None = None) -> str
def assemble_promise_prompt(
    v3_model: Mapping[str, Any],
    entity_id: str,
    attribute: str,
    note_body: str,
    template_body: str | None = None,
) -> str
```

Behavior: deterministic (sorted lists + fixed section order); marks
target promise; walks `contains` for parent chain + siblings; filters
outbound relations to `realizes | exposes | consumes | depends-on`.
Empty sections render as `_(none)_`. Raises `KeyError` on unknown entity.

Tests: `tests/walks/meta/test_prompt_assembly.py` (~8).

### Task 3 — `author_promise_note.py` walk [AMS]

Create `src/architecture_model/walks/meta/author_promise_note.py`
with module docstring `Realizes ``CAP-WK.author``` (meta-coverage marker).

Signature:

```python
def author_promise_note(
    *,
    repo_path: Path,
    job_id: str,
    provider: LLMProvider,
    v3_model: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> ModelPatch
```

Pure — no Job state mutation, no persistence. Loads Job (must be
`queued`), WorkOrder, CommentStub. Assembles prompt. Calls
`provider.structured(prompt, schema)`. Returns a `ModelPatch` with a
single `add` operation at
`entities.<kind>[id=<entity_id>].<attribute>`.

Error types: `AuthorPromiseError` (base), `JobNotQueuedError`,
`WorkOrderMissingError`, `CommentMissingError`, `NotAPromiseNoteError`,
`EntityNotFoundError`.

Tests: `tests/walks/meta/test_author_promise_note.py` (~10).

### Task 4 — `architect_promise_author` MCP tool [OCA]

Create `src/opencode_arch/mcp/tools/promise_author.py` with a
`_PROVIDER_REGISTRY = {"none": lambda: None}` (Mock injected via
monkeypatch in tests).

Envelope: `{repo_path, job_id, provider_name="none"}`.

Flow:
1. Validate args.
2. Resolve provider factory; if `None` → `PRECONDITION_FAILED no_provider`.
3. Transition Job `queued → running` (catch InvalidTransitionError → PRECONDITION_FAILED job_not_queued).
4. Call `author_promise_note(...)` — on error transition Job → failed, return PRECONDITION_FAILED.
5. Transition Job `running → validating`.
6. Persist Proposal atomically under `.architecture/ai/proposals/<proposal_id>.yaml`.
7. Transition Job `validating → completed(result_ref=<path>)`.
8. Journal `ai.proposal.author` event.
9. Return `{ok: True, proposal: <dict>, job_id, proposal_ref}`.

Register in `src/opencode_arch/mcp/server.py` alongside
`architect_promise_save`.

Tests: `tests/mcp/test_promise_author_tool.py` (~6).

### Task 5 — Flip promise + CONTEXT.md update [AMS]

- `.architecture/model/capabilities.v3.yaml`: flip
  `PR-CAP-WK-author-intent` → `verified`; add `verified_by` entries.
- `CONTEXT.md`: add **Part 12 additions** block after Part 11 block.

### Task 6 — Verification

Run AMS test suite (expect ~4314 pass), OCA test suite
(expect ~345 pass), then re-run `audit_walk_coverage` and confirm
`author` moved to covered.

## Commits

1. OCA: `feat(mcp): amend architect_promise_save to auto-approve+queue Job (Part 12 prep)`
2. AMS: `feat(model): Part 12 — CAP-WK.author (LLM-authored promise-content walk)`
3. OCA: `feat(mcp): architect_promise_author tool (CAP-DF Part 12)`
