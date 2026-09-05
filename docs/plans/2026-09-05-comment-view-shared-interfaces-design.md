# Shared Interfaces — Comment→View Loop and SI&L / LLM Provider Layer

**Date:** 2026-09-05
**Status:** Design (approved, pre-implementation)
**Source:** `docs/plans/work packages/comment-view.md`
**Depends on:** Phase-1 lifecycle stack (`origin/main` @ `27458c0`)
**Consumed by:**

- `docs/plans/2026-09-05-comment-view-loop-design.md` (Plan A)
- `docs/plans/2026-09-05-sil-and-provider-design.md` (Plan B)

## 1. Purpose

Two sibling initiatives are being planned:

- **Plan A — Comment→View→Issue→MCP-Dev loop.** A user comment on a
  lifecycle-rendered view creates a logs-db Issue; MCP resolves the coordinate,
  runs slice → requirements → dev → validate → apply → publish → rebuild →
  commit → close.
- **Plan B — Self-Improvement & Logging (SI&L) + LLM Provider Layer +
  Pipeline-as-a-View.** Instrument every runtime component; roll up per
  architecture component; formalize an `LLMProvider` protocol with routing
  policy; deliver an interactive HTML pipeline dashboard.

Both plans consume the same handful of contracts. This document freezes those
contracts so the two plans can be executed in parallel worktrees without
integration drift.

Each contract below identifies **owner repo**, **on-disk location**, **schema**,
and the **journal/event vocabulary** the contract introduces.

## 2. Comment stub

**Owner:** `architecture-model-standard` (AMS)
**Location:** `.architecture/comments/<comment_id>.yaml`
**Purpose:** Local, authoritative record of a comment captured against a
lifecycle-rendered artifact. Enough to reconstruct exactly what the commenter
saw; logs-db is the source of truth for **Issue state** but the comment stub is
the source of truth for **comment content and coordinate**.

### Schema

```yaml
comment_id: <uuid-v4>          # generated at capture time; also used as
                               # logs-db external_key
artifact_id: <str>             # ArtifactSpec.id under lifecycle/artifacts/
view_id: <str>                 # ViewSpec.id (referenced by the ArtifactSpec)
slice_id: <str>                # ModelSlice.id (referenced by the ViewSpec)
package_id: <str>              # root ArchitecturePackage.id
revision: "0000042"            # 7-digit generation of the artifact
target_entity_id: <str|null>   # optional; e.g. "COMP-2.1" if the commenter
                               # anchored on a specific node
body: <str>                    # free text; UTF-8; length ≤ 8 kB
author: <str>                  # opaque identifier (email / handle)
created_at: <ISO-8601 UTC>
issue_ref:                     # populated after architect_sync push
  system: "logs-db"            # constant for v1
  issue_id: <str|int|null>     # returned by logs-db POST
  synced_at: <ISO-8601 UTC|null>
```

### Invariants

- `comment_id` is stable and deterministic once assigned; never re-used.
- `artifact_id + view_id + slice_id + package_id + revision` must resolve
  against a *published* generation. Un-published (draft) artifacts cannot be
  commented on in v1.
- `body` and `author` are immutable after write. Anything editable belongs on
  the logs-db Issue, not on the stub.
- `issue_ref.issue_id` starts null; the first successful sync sets it and
  bumps `issue_ref.synced_at`. Subsequent syncs update `synced_at` only.

### Rationale

Storing the coordinate + body locally (rather than only in logs-db) means the
comment survives logs-db outages and lets `architect_work_issue` reconstruct
the exact slice/view/artifact without a network round-trip beyond the initial
Issue fetch.

## 3. Journal event vocabulary

**Owner:** AMS (schema); opencode-arch (writes)
**Location:** existing `.architecture/lifecycle/journal.jsonl`
**Extends:** `architecture_model.lifecycle.journal.JournalEntry`

Five new event kinds:

| Kind                    | Written by                    | Payload keys                                                             |
|-------------------------|-------------------------------|--------------------------------------------------------------------------|
| `comment.capture`       | comment-capture CLI/UI        | `comment_id, artifact_id, view_id, slice_id, revision, author`           |
| `comment.sync`          | `architect_sync`              | `comment_id, issue_ref, direction: "push"|"push-update"`                 |
| `issue.pull`            | `architect_work_issue`        | `issue_id, comment_id, package_revision`                                 |
| `workorder.from_issue`  | `architect_work_issue`        | `issue_id, comment_id, work_order_id, provenance_digest`                 |
| `issue.close`           | `architect_work_issue`        | `issue_id, commit_sha, model_diff_digest, model_revision_from/to`        |

All entries follow existing `JournalEntry` conventions (`ts`, `kind`, `payload`,
`actor`, `digest`).

### Rationale

Reusing the existing journal keeps ordering, atomicity, and replay semantics
consistent with all other lifecycle events. No new store.

## 4. SI&L record

**Owner:** AMS (schema, decorators); opencode-arch (store, MCP surface)
**Location (per-record snapshot):** `.architecture/sil/<component_id>.yaml`
**Location (rolling data):** SQLite table in existing
`opencode_arch/telemetry/store.py`
**Purpose:** One schema for both **architecture components** (COMP-* in the
model) and **runtime components** (pipeline stages, MCP tools, renderers,
validators), distinguished by `kind`.

### Schema

```yaml
component_id: <str>            # COMP-2.1 | stage:observe | mcp_tool:validate
                               # renderer:svg | validator:check
kind: architecture-component | runtime-component
name: <str>
last_touched_revision: "0000042" | null
last_touched_at: <ISO-8601 UTC|null>

metrics:
  validation_score: <int 0-100|null>        # from architect_validate on the
                                            # allocated sub-model
  drift_flag_count: <int>                    # from learning/maintainer
  regen_readiness: <int 0-100|null>          # from core/regen_readiness
  lesson_count: <int>                        # from learning/lessons
  invocations_7d: <int>                      # runtime only; 0 for arch
  failure_rate_7d: <float 0.0-1.0>           # runtime only
  avg_duration_ms: <int>                     # runtime only

recent_events:                               # ring buffer, N = 50, newest first
  - event_id: <uuid>
    ts: <ISO-8601 UTC>
    kind: invocation | outcome | lesson | drift | validation
    outcome: ok | error | timeout | skipped | null
    ref: <str|null>                          # journal digest, lesson id, etc.

rollup:                                      # arch-component only
  runtime_components: [<runtime component_id>, ...]
  aggregated_at: <ISO-8601 UTC>
```

### Instrumentation contract

A single decorator in AMS (`architecture_model.sil.decorators.instrumented`)
wraps target callables with entry/exit event emission:

```python
@instrumented("stage:observe")
def run(ctx: PipelineContext) -> ObserveResult: ...
```

The decorator emits `{ts, component_id, kind: "invocation", outcome, duration_ms}`
on exit and appends to the ring buffer. Storage adapter is injected from OCA;
if absent, the decorator is a no-op (AMS remains dependency-light).

### Roll-up rule

For every architecture COMP-* with allocated modules, the aggregation walks
the manifest allocation map and merges runtime records for modules owned by
that COMP into `rollup.runtime_components`. `metrics.invocations_7d` etc. are
summed; `avg_duration_ms` is weighted by invocation count. Roll-up runs on
demand (`architect_component_health <id>`) and lazily during dashboard render.

### Rationale

One schema, one store, one query surface. The `kind` discriminator lets the
badge renderer treat both uniformly (color by validation_score for arch,
by failure_rate_7d for runtime). Roll-up is cheap because the manifest already
maps modules → COMP-* IDs.

## 5. LLMProvider protocol

**Owner:** AMS (protocol only); opencode-arch (adapters, policy)
**Location (protocol):** `src/architecture_model/llm/provider.py` (new module)
**Location (adapters):** `src/opencode_arch/llm/providers/{mcp,frontier,relay_ext}.py`
**Location (policy):** `src/opencode_arch/llm/policy.py`

### Protocol

```python
class Completion(TypedDict):
    text: str
    tokens_prompt: int
    tokens_completion: int
    model: str
    finish_reason: Literal["stop", "length", "content_filter", "tool_use"]

class LLMProvider(Protocol):
    name: str                                        # "mcp" | "frontier" | "relay-ext"

    def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Completion: ...

    def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Iterator[str]: ...

    def structured(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str | None = None,
    ) -> dict: ...

    def tokenize(self, text: str) -> int: ...
```

### Adapters

- `MCPProvider` — in-process, current default. Wraps whatever runner an
  OpenCode session already provides.
- `FrontierProvider` — direct HTTP to Claude or GPT with `ANTHROPIC_API_KEY`
  or `OPENAI_API_KEY`. Chosen when reproducibility from outside a session
  matters.
- `RelayExtProvider` — external HTTP relay (URL + auth from env). For
  centralized caching, budget control, or air-gapped deployments.

### Routing policy

```python
@dataclass(frozen=True)
class TaskClass:
    name: str                  # "classification" | "synthesis" | "review"

@dataclass(frozen=True)
class RoutingRule:
    task_class: TaskClass
    provider: str              # matches LLMProvider.name
    model: str
    max_cost_usd_per_call: float
    fallback: tuple[str, ...]  # ordered provider names

class Policy:
    rules: dict[TaskClass, RoutingRule]
    global_budget_usd: float
    retry_backoff: tuple[float, ...]   # e.g. (0.5, 2.0, 8.0)

    def pick(self, task_class: TaskClass) -> LLMProvider: ...
    def spend(self, provider: str, cost_usd: float) -> None: ...
```

Policy files live at `.architecture/llm/policy.yaml` (per-repo default) and
are overridable per run.

### Model-meta field

```yaml
meta:
  provider:
    name: frontier
    model: claude-4.7
    policy_ref: default        # references .architecture/llm/policy.yaml
```

Optional; older models parse unchanged. Presence pins the run for
reproducibility.

### Rationale

Keeping the *protocol* in AMS lets pipeline stages call LLMs through it without
depending on OCA. Keeping the *adapters* and *policy* in OCA keeps the AMS
package free of API-client dependencies and per-cloud config.

## 6. Git commit trailers

**Owner:** opencode-arch (writer); AMS (spec doc — this file)
**Purpose:** Every commit produced by the MCP dev loop links back to its
originating comment, issue, session, and model diff.

### Format

Trailers are RFC-standard `Key: value` lines at the end of the commit message,
separated from the body by a blank line:

```
<subject line, imperative mood>

<optional body, wrapped to 72 cols>

Issue: logs-db#<issue_id>
Comment: <comment_id>
Session: <opencode_session_id>
Model-Revision-From: 0000042
Model-Revision-To: 0000043
Model-Diff-Digest: <sha256-hex>
Provider: frontier/claude-4.7
```

Required trailers: `Issue`, `Comment`, `Session`, `Model-Revision-From`,
`Model-Revision-To`, `Model-Diff-Digest`.
Optional trailer: `Provider` (present only when `meta.provider` is set on the
resulting model).

### Rationale

Git-native, greppable (`git log --grep 'Issue: logs-db#42'`), works with
existing tooling (`git interpret-trailers`), and doesn't duplicate what's
already in the journal. Reading a commit tells you everything needed to
reconstruct the change and validate its provenance.

## 7. logs-db API surface (consumed contract)

**Owner:** logs-db (implements); opencode-arch (consumes)
**Base URL:** configured via existing `architect_sync` machinery
(default `http://localhost:8000`).

Plan A depends on three endpoints. logs-db must expose them before the
`architect_work_issue` MCP tool can operate end-to-end. Plan A includes a
`FakeLogsDB` test fixture that implements this surface for CI.

| Method | Path                          | Body                                        | Returns                                    |
|--------|-------------------------------|---------------------------------------------|--------------------------------------------|
| POST   | `/issues`                     | `{external_key, title, body, tags[], meta}` | `{issue_id, url, created_at}`              |
| GET    | `/issues/{id}`                | —                                           | full Issue (state, external_key, comments) |
| POST   | `/issues/{id}/comments`       | `{author, body}`                            | `{comment_id, created_at}`                 |
| POST   | `/issues/{id}/close`          | `{commit_sha, model_diff_digest, note}`     | `{issue_id, state: "closed"}`              |

`external_key` MUST equal the AMS `comment_id`. logs-db is responsible for
idempotency: a second `POST /issues` with the same `external_key` returns the
existing issue rather than creating a duplicate.

## 8. Ownership summary

| Contract               | Schema/API in | Data/state in                          | Written by                       |
|------------------------|---------------|----------------------------------------|----------------------------------|
| Comment stub           | AMS           | `.architecture/comments/*.yaml`        | comment-capture CLI, MCP         |
| Journal events (new)   | AMS           | `.architecture/lifecycle/journal.jsonl`| OCA lifecycle_exec, MCP tools    |
| SI&L record            | AMS           | `.architecture/sil/*.yaml` + SQLite    | AMS decorator (via injected store)|
| LLMProvider protocol   | AMS           | —                                      | AMS (definition)                 |
| LLM adapters + policy  | OCA           | `.architecture/llm/policy.yaml`        | OCA `llm/` subpackage            |
| Commit trailers        | this doc      | git object DB                          | OCA `architect_work_issue`       |
| logs-db API            | logs-db       | logs-db DB                             | logs-db (Plan A consumer only)   |

## 9. Non-goals for these contracts

- **Threading / reply chains on comments.** v1 is one-way (comment → issue).
  Replies happen on the logs-db Issue itself. If a follow-up requires a
  second MCP run, a *new* comment is captured against the new (post-fix)
  revision.
- **Multi-tenant logs-db.** `system: "logs-db"` is a constant. A future
  version can add a `systems` map; the stub schema is forward-compatible
  because `issue_ref` is a struct, not a string.
- **Provider streaming to the dashboard.** `LLMProvider.stream` is defined
  but Plan B's dashboard only consumes finalized SI&L records; live streaming
  is deferred.

## 10. Sequencing

1. This document commits to `main`.
2. Two worktrees branched from `main`:
   - `feat/comment-view-loop` (Plan A)
   - `feat/sil-and-provider` (Plan B)
3. Plan A stubs `LLMProvider` for its proposer; swaps to Plan B's real
   protocol + adapters at the single sync-point (B.1 landed).
4. Plan B's dashboard (B.3) consumes Plan A's comment stubs to show
   per-component open-issue counts. B.3 is the final piece.

## 11. Open questions (do not block this doc)

- **Comment-capture UI.** No decision on whether the initial capture surface
  is a CLI (`architect_comment <artifact_id> --body ...`), an OpenCode slash
  command, or a small browser bookmarklet against the rendered HTML. Any of
  the three writes the same stub schema. Punt to Plan A implementation phase.
- **Session ID source.** OpenCode sessions expose an ID at runtime;
  non-OpenCode invocations (direct CLI) will fall back to
  `session:<uuid4>-cli`. Formalized in Plan A.
- **Policy hot-reload.** Whether `Policy` reloads mid-run when
  `.architecture/llm/policy.yaml` changes. Defer to Plan B; conservative
  default is per-run snapshot.
