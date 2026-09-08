# Plan B — SI&L + LLM Provider Layer + Pipeline Dashboard (Implementation Plan)

**Date:** 2026-09-05
**Status:** Implementation plan (executable via superpowers workflow)
**Branch:** `feat/sil-and-provider`
**Design:** `docs/plans/2026-09-05-sil-and-provider-design.md`
**Shared interfaces:** `docs/plans/2026-09-05-comment-view-shared-interfaces-design.md`
**Sibling plan:** `docs/plans/2026-09-05-comment-view-loop.md`

## Preflight

### Repo layout assumed by this plan

- AMS = this repo (`architecture-model-standard`).
- OCA = sibling repo at `../opencode-arch/`.
- Both repos must be on branch `feat/sil-and-provider`. If OCA is on a
  different branch, `git -C ../opencode-arch checkout -B feat/sil-and-provider`
  before starting Phase B1.2.

### Existing surfaces this plan extends

- `src/architecture_model/pipeline/llm_provider.py` — **legacy** provider
  auto-detection (Enum-based). Kept for one release under a compatibility
  shim; new code goes through the Protocol in `architecture_model/llm/`.
- `../opencode-arch/src/opencode_arch/llm/{cache,relay}.py` — existing HTTP
  cache and relay client. `relay.py` is folded into the new `RelayExtProvider`
  adapter; `cache.py` is reused unchanged (Provider adapters delegate to it).
- `../opencode-arch/src/opencode_arch/telemetry/store.py` — SQLite store the
  SI&L backend extends (new tables `sil_records`, `sil_events`; existing
  tables untouched).
- `../opencode-arch/src/opencode_arch/mcp/tools/` — 30 existing MCP tool
  handlers, each gets one decorator line in B2.2.
- `../opencode-arch/src/opencode_arch/runner/opencode.py` — the CLI wrapper
  refactored to consume `LLMProvider` in B1.2.

### Fixtures

- `tests/fixtures/lifecycle/sample_package_tree/` — canonical fixture used by
  Plan A. Reused here for pipeline / dashboard tests.
- `tests/fixtures/sil/tiny_repo/` — **new** in Task B2.1.4; a 3-module
  Python package used as roll-up target.

### Verification commands

Run after every task:

```bash
pytest tests/ -v --ignore=tests/test_config_loader.py -x
```

At OCA-touching tasks, additionally:

```bash
pytest ../opencode-arch/tests/ -v -x
```

Golden-snapshot tasks may need `--snapshot-update` on first run — the task
explicitly calls this out.

### Commit hygiene

- One task = one commit. No batching.
- Commit subject: `<type>(<scope>): <B<phase>.<task>> <what>` e.g.
  `feat(llm): B1.1.2 add Completion TypedDict + LLMProvider Protocol`.
- Body: 1–3 lines describing rationale; reference design-doc section.
- No trailer required on this branch (trailers apply to MCP-generated
  commits in Plan A, not manual ones).

---

## Phase B1 — LLM Provider Layer

### B1.1 — Protocol, TypedDict, meta.provider schema (2 days)

Goal: land the AMS-side contract with **zero runtime impact** — no adapter
switches yet, pipeline still uses its legacy path. This phase is safe to
merge on its own.

#### Task B1.1.1 — Create `architecture_model/llm/` package

**Red.** Create `tests/llm/test_package.py`:

```python
def test_llm_package_importable():
    import architecture_model.llm as llm
    assert hasattr(llm, "__all__")


def test_llm_package_exports_provider_and_completion():
    from architecture_model.llm import LLMProvider, Completion
    assert LLMProvider is not None
    assert Completion is not None
```

Run: `pytest tests/llm/test_package.py -x` → fails with `ModuleNotFoundError`.

**Green.** Create `src/architecture_model/llm/__init__.py`:

```python
"""LLM Provider protocol — see docs/plans/2026-09-05-...-shared-interfaces-design.md §5."""

from architecture_model.llm.provider import Completion, LLMProvider

__all__ = ["Completion", "LLMProvider"]
```

Create empty `src/architecture_model/llm/provider.py` with only a module
docstring for now — the next task fills it. Add temporary stubs to satisfy
the import:

```python
"""LLMProvider Protocol and Completion TypedDict."""
from typing import Protocol, TypedDict


class Completion(TypedDict):
    text: str


class LLMProvider(Protocol):
    name: str
```

Run: `pytest tests/llm/test_package.py -x` → passes.

**Commit.** `feat(llm): B1.1.1 scaffold architecture_model.llm package`

#### Task B1.1.2 — Full `Completion` TypedDict + `LLMProvider` Protocol

**Red.** Extend `tests/llm/test_package.py`:

```python
def test_completion_typed_dict_keys():
    from architecture_model.llm import Completion
    ann = Completion.__annotations__
    assert set(ann) == {
        "text",
        "tokens_prompt",
        "tokens_completion",
        "model",
        "finish_reason",
    }


def test_llm_provider_protocol_surface():
    from architecture_model.llm import LLMProvider
    # Protocol has all 4 methods declared
    for method in ("complete", "stream", "structured", "tokenize"):
        assert hasattr(LLMProvider, method), method


def test_llm_provider_runtime_checkable_by_duck_type():
    from architecture_model.llm import LLMProvider

    class Duck:
        name = "duck"
        def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
            return {"text": "", "tokens_prompt": 0, "tokens_completion": 0,
                    "model": "d", "finish_reason": "stop"}
        def stream(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
            yield ""
        def structured(self, prompt, schema, *, model=None):
            return {}
        def tokenize(self, text):
            return len(text.split())

    d = Duck()
    # runtime_checkable Protocols support isinstance()
    assert isinstance(d, LLMProvider)
```

**Green.** Replace `src/architecture_model/llm/provider.py`:

```python
"""LLMProvider Protocol and Completion TypedDict.

See docs/plans/2026-09-05-comment-view-shared-interfaces-design.md §5.
"""
from __future__ import annotations

from typing import Iterator, Literal, Protocol, TypedDict, runtime_checkable


class Completion(TypedDict):
    text: str
    tokens_prompt: int
    tokens_completion: int
    model: str
    finish_reason: Literal["stop", "length", "content_filter", "tool_use"]


@runtime_checkable
class LLMProvider(Protocol):
    """Uniform LLM interface. Adapters live in opencode-arch."""

    name: str

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

Run: `pytest tests/llm/ -x` → all pass.

**Commit.** `feat(llm): B1.1.2 add Completion TypedDict + LLMProvider Protocol`

#### Task B1.1.3 — Add `meta.provider` to `spec/schema.json`

**Red.** Create `tests/spec/test_meta_provider.py`:

```python
import json
from pathlib import Path


def test_schema_has_meta_provider_definition():
    schema = json.loads(
        Path("src/architecture_model/spec/schema.json").read_text()
    )
    meta_props = schema["properties"]["meta"]["properties"]
    assert "provider" in meta_props
    prov = meta_props["provider"]
    assert prov["type"] == "object"
    assert set(prov["required"]) == {"name", "model"}
    assert prov["properties"]["name"]["type"] == "string"
    assert prov["properties"]["model"]["type"] == "string"
    assert prov["properties"]["policy_ref"]["type"] == "string"


def test_model_without_provider_still_parses():
    from architecture_model.core.parser import _parse_raw
    m = _parse_raw({
        "meta": {"project": "p", "schema_version": "1.3"},
        "entities": {"components": []},
        "relationships": [],
    })
    assert m.meta.project == "p"


def test_model_with_provider_parses_and_round_trips():
    from architecture_model.core.parser import _parse_raw
    m = _parse_raw({
        "meta": {
            "project": "p",
            "schema_version": "1.3",
            "provider": {
                "name": "frontier",
                "model": "claude-4.7",
                "policy_ref": "default",
            },
        },
        "entities": {"components": []},
        "relationships": [],
    })
    assert m.meta.provider is not None
    assert m.meta.provider.name == "frontier"
    assert m.meta.provider.model == "claude-4.7"
```

**Green.** Two edits:

1. `src/architecture_model/spec/schema.json` — inside
   `properties.meta.properties`, add:

   ```json
   "provider": {
     "type": "object",
     "properties": {
       "name":       {"type": "string"},
       "model":      {"type": "string"},
       "policy_ref": {"type": "string"}
     },
     "required": ["name", "model"],
     "additionalProperties": false
   }
   ```

2. `src/architecture_model/core/types.py` — add `ProviderMeta` dataclass and
   optional field on `Meta`:

   ```python
   @dataclass(frozen=True)
   class ProviderMeta:
       name: str
       model: str
       policy_ref: str | None = None


   @dataclass(frozen=True)
   class Meta:
       # ... existing fields ...
       provider: ProviderMeta | None = None
   ```

3. `src/architecture_model/core/parser.py` — extend `_parse_meta` to read
   `raw.get("provider")` and construct `ProviderMeta` when present.

Run: `pytest tests/spec/test_meta_provider.py -x`.

**Commit.** `feat(schema): B1.1.3 add optional meta.provider field`

#### Task B1.1.4 — Wire `PipelineContext.llm_provider` (opt-in)

**Red.** Add to `tests/pipeline/test_context.py`:

```python
def test_pipeline_context_accepts_llm_provider_none_default():
    from architecture_model.pipeline.protocol import PipelineContext
    ctx = PipelineContext(repo_path=Path("/tmp"))
    assert ctx.llm_provider is None


def test_pipeline_context_accepts_llm_provider_when_set():
    from architecture_model.pipeline.protocol import PipelineContext
    from architecture_model.llm import LLMProvider

    class Stub:
        name = "stub"
        def complete(self, *a, **kw): raise NotImplementedError
        def stream(self, *a, **kw):   raise NotImplementedError
        def structured(self, *a, **kw): raise NotImplementedError
        def tokenize(self, t): return 0

    ctx = PipelineContext(repo_path=Path("/tmp"), llm_provider=Stub())
    assert isinstance(ctx.llm_provider, LLMProvider)
```

**Green.** In `src/architecture_model/pipeline/protocol.py`, add optional
field to `PipelineContext`:

```python
llm_provider: "LLMProvider | None" = None
```

Import guarded by `TYPE_CHECKING` to avoid a hard runtime dependency. **No
stage changes yet** — this task only exposes the slot.

**Commit.** `feat(pipeline): B1.1.4 expose optional llm_provider on PipelineContext`

---

### B1.2 — Adapters, policy, migration (3 days)

All work in `../opencode-arch/`. AMS remains unchanged.

#### Task B1.2.1 — Recorded-fixture harness for adapter contract tests

**Red.** Create `../opencode-arch/tests/llm/fixtures/completion_stop.json`:

```json
{
  "prompt": "hello",
  "text": "world",
  "tokens_prompt": 1,
  "tokens_completion": 1,
  "model": "test-model",
  "finish_reason": "stop"
}
```

Create `../opencode-arch/tests/llm/test_adapter_contract.py` with a
parametrized fixture harness that a Provider adapter must satisfy. Assert
each adapter, when fed the fixture, returns a `Completion` byte-identical
to the fixture record. The test file imports adapters not yet written.

**Green.** File the tests as skipped for now with `pytest.mark.skip(
reason="adapters land in B1.2.2/3/4")`. No production code yet.

**Commit (in OCA repo).** `test(llm): B1.2.1 recorded-fixture harness for adapter contracts`

#### Task B1.2.2 — `MCPProvider` (in-process, default)

**Red.** Un-skip the `MCPProvider` parametrization in the contract test.
Add `../opencode-arch/tests/llm/test_mcp_provider.py`:

```python
def test_mcp_provider_name():
    from opencode_arch.llm.providers.mcp import MCPProvider
    assert MCPProvider().name == "mcp"


def test_mcp_provider_tokenize_uses_tiktoken_or_fallback():
    from opencode_arch.llm.providers.mcp import MCPProvider
    n = MCPProvider().tokenize("one two three")
    assert n >= 3
```

**Green.** Create `../opencode-arch/src/opencode_arch/llm/providers/__init__.py`
(empty) and `.../mcp.py`:

```python
"""In-process LLMProvider adapter — default when no policy override."""
from __future__ import annotations

from typing import Iterator

from architecture_model.llm import Completion, LLMProvider


class MCPProvider:
    name = "mcp"

    def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0) -> Completion:
        # Delegates to whatever runner is active in-session; for tests, the
        # fixture harness monkeypatches _invoke().
        return self._invoke(prompt, model, max_tokens, temperature)

    def stream(self, prompt, *, model=None, max_tokens=4096, temperature=0.0) -> Iterator[str]:
        yield self.complete(prompt, model=model, max_tokens=max_tokens,
                            temperature=temperature)["text"]

    def structured(self, prompt, schema, *, model=None) -> dict:
        import json
        c = self.complete(prompt + "\n\nRespond in JSON only.", model=model)
        return json.loads(c["text"])

    def tokenize(self, text: str) -> int:
        try:
            import tiktoken  # type: ignore
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text.split()))

    def _invoke(self, prompt, model, max_tokens, temperature) -> Completion:
        # Real impl: shell out to `opencode run --prompt ...` or wire to
        # the current OpenCode SDK. For test fixture, monkeypatched.
        raise NotImplementedError("wire in B1.2.5 runner refactor")


# runtime-checkable Protocol satisfied by structural typing
assert isinstance(MCPProvider(), LLMProvider)
```

Run: `pytest ../opencode-arch/tests/llm/ -x` → adapter tests pass under
monkeypatch.

**Commit.** `feat(llm): B1.2.2 add MCPProvider adapter`

#### Task B1.2.3 — `FrontierProvider` (Anthropic + OpenAI)

**Red.** `../opencode-arch/tests/llm/test_frontier_provider.py`:

```python
def test_frontier_provider_selects_anthropic_when_only_anthropic_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    from opencode_arch.llm.providers.frontier import FrontierProvider
    p = FrontierProvider()
    assert p.backend == "anthropic"


def test_frontier_provider_raises_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from opencode_arch.llm.providers.frontier import FrontierProvider
    import pytest
    with pytest.raises(RuntimeError, match="no.*API key"):
        FrontierProvider()
```

**Green.** Implement `.../frontier.py`. Uses `urllib` (no new deps) to hit
`https://api.anthropic.com/v1/messages` or `https://api.openai.com/v1/chat/completions`.
Returns `Completion` normalized across backends. Wraps `opencode_arch.llm.cache`
transparently.

**Commit.** `feat(llm): B1.2.3 add FrontierProvider (Anthropic/OpenAI)`

#### Task B1.2.4 — `RelayExtProvider` (folds existing `relay.py`)

**Red.** `../opencode-arch/tests/llm/test_relay_ext_provider.py`:

```python
def test_relay_ext_provider_url_from_env(monkeypatch):
    monkeypatch.setenv("OPENCODE_RELAY_URL", "http://relay.local:8400")
    from opencode_arch.llm.providers.relay_ext import RelayExtProvider
    assert RelayExtProvider().base_url == "http://relay.local:8400"


def test_relay_ext_provider_completion_via_stub_server(httpserver):
    # pytest-httpserver
    httpserver.expect_request("/chat").respond_with_json({
        "text": "ok", "tokens_prompt": 3, "tokens_completion": 1,
        "model": "relay", "finish_reason": "stop",
    })
    from opencode_arch.llm.providers.relay_ext import RelayExtProvider
    p = RelayExtProvider(base_url=httpserver.url_for(""))
    c = p.complete("hi")
    assert c["text"] == "ok"
```

**Green.** Implement `.../relay_ext.py` — refactor of existing `relay.py`
to conform to `LLMProvider`. Delete `relay.py` in the same commit (adapter
supersedes it) after grep confirms no other imports remain.

**Commit.** `feat(llm): B1.2.4 add RelayExtProvider; retire legacy relay.py`

#### Task B1.2.5 — Registry + `Policy` loader

**Red.** `../opencode-arch/tests/llm/test_policy.py`:

```python
def test_policy_loads_yaml_and_picks_provider(tmp_path):
    (tmp_path / ".architecture" / "llm").mkdir(parents=True)
    (tmp_path / ".architecture" / "llm" / "policy.yaml").write_text("""
rules:
  synthesis:
    provider: mcp
    model: opencode-default
    max_cost_usd_per_call: 0.10
    fallback: [frontier]
  classification:
    provider: frontier
    model: claude-4.7
    max_cost_usd_per_call: 0.02
    fallback: []
global_budget_usd: 10.0
retry_backoff: [0.5, 2.0, 8.0]
""")
    from opencode_arch.llm.policy import load_policy, TaskClass
    p = load_policy(tmp_path)
    prov = p.pick(TaskClass("synthesis"))
    assert prov.name == "mcp"


def test_policy_budget_enforced(monkeypatch):
    from opencode_arch.llm.policy import Policy, RoutingRule, TaskClass, BudgetExceeded
    from opencode_arch.llm.providers.mcp import MCPProvider
    import pytest
    p = Policy(
        rules={TaskClass("x"): RoutingRule(TaskClass("x"), "mcp", "m", 0.5, ())},
        global_budget_usd=1.0,
        retry_backoff=(0.0,),
    )
    p.spend("mcp", 0.6)
    p.spend("mcp", 0.5)
    with pytest.raises(BudgetExceeded):
        p.spend("mcp", 0.01)


def test_policy_fallback_on_transient_error(monkeypatch):
    from opencode_arch.llm.policy import Policy, RoutingRule, TaskClass, TransientProviderError
    # primary raises, fallback returns — pick() returns fallback provider
    # (implementation detail: pick returns a wrapper that tries in order)
    ...
```

**Green.** Implement `.../policy.py` + `.../registry.py`. Registry maps
`"mcp" | "frontier" | "relay-ext"` strings → instantiated provider objects,
caching one instance per name.

**Commit.** `feat(llm): B1.2.5 add Policy loader, registry, and fallback wrapping`

#### Task B1.2.6 — Migrate OCA runner onto `LLMProvider`

**Red.** `../opencode-arch/tests/runner/test_opencode.py` (extend):

```python
def test_runner_uses_llm_provider_from_policy(tmp_path, monkeypatch):
    # policy.yaml selects a stub provider; runner completes through it
    # assert monkeypatched stub was invoked, not the real subprocess
    ...
```

**Green.** Refactor `../opencode-arch/src/opencode_arch/runner/opencode.py`
to call `Policy.pick(...).complete(...)` instead of spawning `opencode run`
directly. CLI-visible behavior unchanged (subprocess path still available
under `MCPProvider._invoke`).

**Commit.** `refactor(runner): B1.2.6 route runner calls through LLMProvider`

#### Task B1.2.7 — Migrate AMS pipeline stages that call LLMs

**Red.** `tests/pipeline/test_llm_routing.py`:

```python
def test_infer_uses_ctx_llm_provider_when_set():
    # Build a PipelineContext with a stub LLMProvider that records calls.
    # Run InferStage on a tiny inventory; assert stub.complete was called.
    ...


def test_infer_falls_back_to_legacy_provider_when_ctx_none():
    # ctx.llm_provider is None → legacy pipeline/llm_provider.py path used.
    # Assert no import error, no behavior regression.
    ...
```

**Green.** In each stage that historically called an LLM (`infer.py`,
`allocate.py`, `specify.py`, `synthesize.py`, `emit.py` and helpers
`llm_refine.py`, `gap_prompts.py`, `context_gen.py`), replace direct
provider calls with:

```python
if ctx.llm_provider is not None:
    completion = ctx.llm_provider.complete(prompt, model=None, max_tokens=4096)
    text = completion["text"]
else:
    text = _legacy_call(prompt)  # existing code path
```

Add `Meta.provider` write-back in `emit.py` when `ctx.llm_provider` is set:

```python
if ctx.llm_provider is not None:
    model.meta = replace(
        model.meta,
        provider=ProviderMeta(name=ctx.llm_provider.name,
                              model=getattr(ctx.llm_provider, "default_model", "?"),
                              policy_ref=ctx.policy_ref),
    )
```

**Commit.** `refactor(pipeline): B1.2.7 route stage LLM calls through ctx.llm_provider`

#### Task B1.2.8 — Reproducibility test

**Red.** `tests/e2e/test_reproducibility.py`:

```python
def test_pipeline_reproducible_with_pinned_provider(tmp_path):
    """Run pipeline twice on the fixture with a deterministic stub provider;
    assert byte-identical .architecture-model.yaml."""
    ...
```

Stub provider returns a canned response per prompt-hash.

**Green.** Any determinism gap surfaced (timestamps in meta, dict iteration
order, etc.) fixed here.

**Commit.** `test(e2e): B1.2.8 reproducibility harness with pinned provider`

---

## Phase B2 — SI&L: schema, decorator, store, instrumentation

### B2.1 — Record schema, decorator, no-op path (3 days)

#### Task B2.1.1 — `SI&LRecord` model + `sil/` package scaffold

**Red.** `tests/sil/test_record.py`:

```python
def test_sil_record_arch_kind_minimum():
    from architecture_model.sil.record import SILRecord, Metrics
    r = SILRecord(
        component_id="COMP-2.1",
        kind="architecture-component",
        name="Pipeline Coordination",
        metrics=Metrics(),
    )
    assert r.component_id == "COMP-2.1"
    assert r.kind == "architecture-component"


def test_sil_record_runtime_kind():
    from architecture_model.sil.record import SILRecord, Metrics
    r = SILRecord(
        component_id="stage:observe",
        kind="runtime-component",
        name="ObserveStage",
        metrics=Metrics(invocations_7d=42, failure_rate_7d=0.05, avg_duration_ms=120),
    )
    assert r.metrics.invocations_7d == 42


def test_sil_record_yaml_round_trip(tmp_path):
    from architecture_model.sil.record import SILRecord, Metrics, dump_yaml, load_yaml
    r = SILRecord(component_id="COMP-1", kind="architecture-component",
                  name="Core", metrics=Metrics(validation_score=87))
    p = tmp_path / "COMP-1.yaml"
    p.write_text(dump_yaml(r))
    r2 = load_yaml(p.read_text())
    assert r2 == r


def test_sil_record_rejects_bad_kind():
    from architecture_model.sil.record import SILRecord, Metrics
    import pytest
    with pytest.raises(ValueError):
        SILRecord(component_id="x", kind="bogus", name="n", metrics=Metrics())
```

**Green.** Create:

- `src/architecture_model/sil/__init__.py` exporting `SILRecord`,
  `Metrics`, `Event`, `Rollup`, `instrumented`.
- `src/architecture_model/sil/record.py` — dataclasses matching the schema
  in shared-interfaces §4. `dump_yaml` / `load_yaml` reusing
  `architecture_model.core.parser` YAML helpers. Enum-typed `kind`. Event
  ring buffer trimmed to 50.

**Commit.** `feat(sil): B2.1.1 add SILRecord model + yaml round-trip`

#### Task B2.1.2 — `@instrumented` decorator (no-op path)

**Red.** `tests/sil/test_decorators_noop.py`:

```python
def test_instrumented_is_transparent_when_no_store():
    from architecture_model.sil.decorators import instrumented

    calls = []

    @instrumented("stage:test")
    def add(a, b):
        calls.append((a, b))
        return a + b

    assert add(2, 3) == 5
    assert calls == [(2, 3)]


def test_instrumented_reraises_exceptions_when_no_store():
    from architecture_model.sil.decorators import instrumented
    import pytest

    @instrumented("stage:boom")
    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        boom()


def test_instrumented_works_on_methods():
    from architecture_model.sil.decorators import instrumented

    class Stage:
        @instrumented("stage:x")
        def run(self, ctx):
            return ctx * 2

    assert Stage().run(21) == 42
```

**Green.** `src/architecture_model/sil/decorators.py`:

```python
"""SI&L instrumentation decorator (no-op when no store bound)."""
from __future__ import annotations

import functools
import time
from typing import Any, Callable

_STORE: "Any | None" = None  # OCA injects via bind_store()


def bind_store(store: Any) -> None:
    global _STORE
    _STORE = store


def instrumented(component_id: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _STORE is None:
                return fn(*args, **kwargs)
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                _STORE.emit(component_id, "invocation", "ok",
                            int((time.perf_counter() - t0) * 1000))
                return result
            except BaseException as e:
                _STORE.emit(component_id, "invocation", "error",
                            int((time.perf_counter() - t0) * 1000),
                            ref=type(e).__name__)
                raise
        return wrapper
    return deco
```

**Commit.** `feat(sil): B2.1.2 add @instrumented decorator with no-op path`

#### Task B2.1.3 — `sil.rollup.rollup_component`

**Red.** `tests/sil/test_rollup.py`:

```python
def test_rollup_merges_runtime_records_for_arch_component(tmp_path):
    """COMP-2.1 owns modules pipeline/coordinator.py + protocol.py + cache.py.
    Two runtime records (stage:observe scoped to those modules, mcp_tool:pipeline)
    are aggregated: invocations summed, avg_duration_ms weighted."""
    from architecture_model.sil.record import SILRecord, Metrics
    from architecture_model.sil.rollup import rollup_component

    manifest_allocation = {
        "COMP-2.1": [
            "src/architecture_model/pipeline/coordinator.py",
            "src/architecture_model/pipeline/protocol.py",
        ]
    }
    runtime_records = [
        SILRecord(component_id="stage:observe", kind="runtime-component",
                  name="ObserveStage",
                  metrics=Metrics(invocations_7d=10, avg_duration_ms=100,
                                   failure_rate_7d=0.1)),
        SILRecord(component_id="mcp_tool:pipeline", kind="runtime-component",
                  name="pipeline",
                  metrics=Metrics(invocations_7d=30, avg_duration_ms=200,
                                   failure_rate_7d=0.0)),
    ]
    arch_record = SILRecord(component_id="COMP-2.1",
                            kind="architecture-component",
                            name="Pipeline Coordination",
                            metrics=Metrics(validation_score=88))
    merged = rollup_component(
        arch_record, runtime_records,
        allocation_map=manifest_allocation,
        module_to_runtime={"src/architecture_model/pipeline/coordinator.py":
                           ["stage:observe", "mcp_tool:pipeline"]},
    )
    assert merged.rollup.runtime_components == ["stage:observe", "mcp_tool:pipeline"]
    assert merged.metrics.invocations_7d == 40           # 10 + 30
    assert merged.metrics.avg_duration_ms == 175         # (10·100 + 30·200) / 40
    assert 0.024 < merged.metrics.failure_rate_7d < 0.026  # weighted
```

**Green.** Implement `src/architecture_model/sil/rollup.py` with
`rollup_component(arch, runtime, *, allocation_map, module_to_runtime) -> SILRecord`.

**Commit.** `feat(sil): B2.1.3 add rollup_component`

#### Task B2.1.4 — Fixture repo + OCA SQLite store

**Red.** Create `tests/fixtures/sil/tiny_repo/` with 3 hand-written Python
modules and a corresponding `.architecture-model.yaml` with 2 components
that allocate them.

`../opencode-arch/tests/sil/test_store.py`:

```python
def test_store_emit_writes_row_and_trims_to_50(tmp_path):
    from opencode_arch.sil.store import SILStore
    s = SILStore(tmp_path / "sil.sqlite")
    for i in range(60):
        s.emit("stage:x", "invocation", "ok", 10)
    rows = s.recent("stage:x")
    assert len(rows) == 50


def test_store_error_outcome_recorded():
    from opencode_arch.sil.store import SILStore
    s = SILStore(":memory:")
    s.emit("stage:x", "invocation", "error", 5, ref="ValueError")
    rows = s.recent("stage:x")
    assert rows[0]["outcome"] == "error"
    assert rows[0]["ref"] == "ValueError"
```

**Green.** `../opencode-arch/src/opencode_arch/sil/__init__.py` +
`store.py` — SQLite table `sil_events(id, component_id, ts, kind, outcome,
duration_ms, ref)`. `SILStore.emit(...)` is thread-safe (single writer,
WAL mode). `recent(id, n=50)` newest-first. Also aggregates
`invocations_7d`, `failure_rate_7d`, `avg_duration_ms` on demand.

Also add `bind_ams_decorator()` that calls
`architecture_model.sil.decorators.bind_store(self)`.

**Commit (OCA).** `feat(sil): B2.1.4 add SILStore SQLite backend + AMS binding`

#### Task B2.1.5 — Snapshot writer

**Red.** `../opencode-arch/tests/sil/test_snapshot.py`:

```python
def test_snapshot_writes_yaml_matches_sqlite(tmp_path):
    from opencode_arch.sil.store import SILStore
    from opencode_arch.sil.snapshot import write_snapshot
    s = SILStore(tmp_path / "s.db")
    for _ in range(5): s.emit("stage:observe", "invocation", "ok", 10)
    write_snapshot(s, "stage:observe", tmp_path / "sil" / "stage:observe.yaml")
    text = (tmp_path / "sil" / "stage:observe.yaml").read_text()
    assert "component_id: stage:observe" in text
    assert "recent_events:" in text
```

**Green.** `../opencode-arch/src/opencode_arch/sil/snapshot.py` — reads
`SILStore`, materializes a `SILRecord`, dumps YAML atomically (temp file +
rename) to `.architecture/sil/<id>.yaml`.

**Commit (OCA).** `feat(sil): B2.1.5 add snapshot writer`

#### Task B2.1.6 — `architect_component_health` MCP tool

**Red.** `../opencode-arch/tests/mcp/tools/test_component_health.py`:

```python
def test_component_health_returns_record_and_trend(tmp_path):
    # seed a store, invoke the tool, assert envelope shape.
    ...

def test_component_health_unknown_component_returns_not_found():
    ...
```

**Green.** `../opencode-arch/src/opencode_arch/mcp/tools/component_health.py`
following the envelope conventions of the existing tools. Register in
`../opencode-arch/src/opencode_arch/mcp/server.py`.

**Commit (OCA).** `feat(mcp): B2.1.6 add architect_component_health tool`

---

### B2.2 — Instrument all sites (3 days)

Each subtask is trivially small (one-line decorator + one assertion test).
Batched *by module*, one commit per module. No batching across modules.

#### Task B2.2.1 — Instrument all 10 pipeline stages

**Red.** `tests/sil/test_instrumentation_pipeline.py`:

```python
import pytest

STAGE_MODULES = [
    "architecture_model.pipeline.observe",
    "architecture_model.pipeline.infer",
    "architecture_model.pipeline.allocate",
    "architecture_model.pipeline.relate",
    "architecture_model.pipeline.specify",
    "architecture_model.pipeline.contract",
    "architecture_model.pipeline.decompose",
    "architecture_model.pipeline.synthesize",
    "architecture_model.pipeline.validate",
    "architecture_model.pipeline.emit",
]

@pytest.mark.parametrize("mod", STAGE_MODULES)
def test_stage_run_is_instrumented(mod):
    import importlib
    m = importlib.import_module(mod)
    # find the *Stage class; assert its run() carries the marker attribute
    stage_cls = next(v for k, v in vars(m).items()
                     if k.endswith("Stage") and isinstance(v, type))
    assert getattr(stage_cls.run, "__sil_instrumented__", False)
```

**Green.** Extend `instrumented(...)` to set
`wrapper.__sil_instrumented__ = True` and `wrapper.__sil_component_id__ =
component_id`. Then in each stage module add:

```python
from architecture_model.sil.decorators import instrumented

class ObserveStage:
    @instrumented("stage:observe")
    def run(self, ctx: PipelineContext) -> StageResult[Inventory]:
        ...
```

**Commit.** `feat(sil): B2.2.1 instrument all 10 pipeline stages`

#### Task B2.2.2 — Instrument all 5 renderers

**Red.** Analogous parametrized test for
`architecture_model.lifecycle.renderers.{svg,markdown,html,ai_context,zip}`
and their top-level `render` function.

**Green.** Add `@instrumented("renderer:<name>")` to each `render(...)`.

**Commit.** `feat(sil): B2.2.2 instrument all lifecycle renderers`

#### Task B2.2.3 — Instrument 3 validators

**Red.** Test that `validate_model`, `representativeness.evaluate`, and
`authoring/gate.evaluate` all carry the marker.

**Green.** Add `@instrumented("validator:validate")`,
`"validator:check"`, `"validator:gate"`.

**Commit.** `feat(sil): B2.2.3 instrument three validators`

#### Task B2.2.4 — Instrument all MCP tool handlers (OCA)

**Red.** `../opencode-arch/tests/mcp/test_instrumentation.py`:

```python
def test_every_mcp_tool_handler_is_instrumented():
    import pkgutil, importlib
    import opencode_arch.mcp.tools as pkg
    missing = []
    for info in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        m = importlib.import_module(info.name)
        for name, fn in vars(m).items():
            if name.endswith("_tool") and callable(fn):
                if not getattr(fn, "__sil_instrumented__", False):
                    missing.append(f"{info.name}:{name}")
    assert not missing, f"un-instrumented tools: {missing}"
```

**Green.** Add `@instrumented(f"mcp_tool:{tool_name}")` to each `*_tool`
handler across ~30 modules. This is mechanical — one commit is acceptable
because the CI check enforces coverage.

**Commit (OCA).** `feat(sil): B2.2.4 instrument all MCP tool handlers`

#### Task B2.2.5 — Snapshot cron hook + integration into `architect_evaluate`

**Red.** `../opencode-arch/tests/mcp/tools/test_evaluate_includes_sil.py`
asserts the `evaluate` envelope now includes an `sil_summary` key with
per-component roll-ups.

**Green.** Extend `../opencode-arch/src/opencode_arch/mcp/tools/evaluate.py`
to walk the SILStore and roll up per-COMP records. Wire snapshot writer
to be called at end of every pipeline run (in `pipeline.py` tool).

**Commit (OCA).** `feat(mcp): B2.2.5 include SI&L summary in evaluate; snapshot after pipeline runs`

---

## Phase B3 — Pipeline Dashboard

### B3.1 — View/slice/data JSON + renderer (3 days)

#### Task B3.1.1 — `pipeline.slice.yaml` fixture + materializer contract

**Red.** `tests/lifecycle/test_pipeline_slice.py`:

```python
def test_pipeline_slice_materializes_on_fixture(tmp_path):
    # Copy sample_package_tree; run architect_slice_materialize with
    # spec loaded from tests/fixtures/lifecycle/pipeline.slice.yaml;
    # assert output fragment contains all capabilities, components, and
    # constraint entities and their allocation edges.
    ...
```

Ship the slice YAML file in the fixture location.

**Green.** No production code change needed — slice materializer already
exists. Task just proves the slice spec is correct.

**Commit.** `test(lifecycle): B3.1.1 pipeline slice spec + materialization test`

#### Task B3.1.2 — `pipeline.view.yaml` + `pipeline_html_data.build()`

**Red.** `tests/lifecycle/test_pipeline_html_data.py` — golden snapshot on
the fixture. First run: manually inspect and `pytest --snapshot-update`.

Assertions:
- `nodes[]` includes every COMP-* from the slice.
- `edges[]` includes `requirement → capability`, `capability → component`,
  `component → module` links.
- `badges[<comp_id>]` populated for every COMP-* from a stub SIL store
  seeded in the test.

**Green.** Implement `src/architecture_model/lifecycle/renderers/pipeline_html_data.py`
exporting `build(materialized_slice, sil_store=None) -> dict`.

**Commit.** `feat(lifecycle): B3.1.2 add pipeline_state.json builder`

#### Task B3.1.3 — `pipeline-html` renderer registration + golden

**Red.** `tests/lifecycle/test_renderer_pipeline_html.py`:

```python
def test_pipeline_html_renderer_registered():
    from architecture_model.lifecycle.renderers import DEFAULT_RENDERERS
    assert "pipeline-html" in DEFAULT_RENDERERS


def test_pipeline_html_renderer_emits_expected_shell(tmp_path, snapshot):
    from architecture_model.lifecycle.renderers.pipeline_html import render
    html = render(view_spec=..., slice=..., artifact_spec=...)
    # snapshot the top 200 lines (deterministic structure)
    snapshot.assert_match(html[:5000], "pipeline_html_shell.txt")
```

**Green.** Implement `src/architecture_model/lifecycle/renderers/pipeline_html.py`:

- Reads `pipeline_state.json` from `build()`.
- Renders an HTML shell that embeds the JSON as a `<script id="pipeline-state">`
  tag and links to the static assets from `assets/pipeline_dashboard/`.
- Registers in `renderers/__init__.py:DEFAULT_RENDERERS` under key
  `"pipeline-html"`.
- Emits `content_type = "text/html; charset=utf-8"`.

**Commit.** `feat(lifecycle): B3.1.3 add pipeline-html renderer`

---

### B3.2 — Interactive dashboard + drill-down (3 days)

#### Task B3.2.1 — Static assets (CSS + drill-down JS + badges JS)

**Red.** `tests/lifecycle/test_dashboard_assets.py`:

```python
def test_all_assets_exist_and_have_content():
    from pathlib import Path
    root = Path("src/architecture_model/lifecycle/renderers/assets/pipeline_dashboard")
    for f in ("index.css", "drilldown.js", "badges.js"):
        p = root / f
        assert p.exists() and p.stat().st_size > 100


def test_html_shell_references_all_assets():
    from architecture_model.lifecycle.renderers.pipeline_html import render
    html = render(...)  # minimal fixture
    for f in ("index.css", "drilldown.js", "badges.js"):
        assert f in html
```

**Green.** Ship the three static asset files. Vanilla JS; no external CDN,
no build step. `drilldown.js` opens a right-hand panel with:

- **Node info** (id, name, kind, allocated modules)
- **SI&L badges** (validation_score, drift_flag_count, regen_readiness,
  failure_rate_7d, avg_duration_ms) — colored by threshold
- **Lessons** list (loaded lazily via `<script>` tag pointing at
  `lessons/<comp_id>.json` if present)
- **Open issues** list (from `.architecture/comments/*.yaml` where
  `component_id == <selected>` and `issue_ref.state != closed`)

**Commit.** `feat(dashboard): B3.2.1 add pipeline dashboard assets (CSS + drilldown JS)`

#### Task B3.2.2 — Playwright smoke test

**Red.** `tests/lifecycle/test_dashboard_playwright.py` (skip if `playwright`
not installed):

```python
def test_dashboard_renders_and_drilldown_opens(tmp_path):
    from playwright.sync_api import sync_playwright
    # 1. Materialize slice + project view + render html to tmp_path/pipeline.html
    # 2. Launch headless chromium; navigate to file://.../pipeline.html
    # 3. Assert every COMP-* badge is present in DOM.
    # 4. Click a node; assert drill-down panel visible with node info.
    ...
```

**Green.** No production code — this task validates B3.2.1 works
end-to-end. Add `playwright` to `[dev]` extras in `pyproject.toml`.

**Commit.** `test(dashboard): B3.2.2 playwright smoke test for drill-down UI`

#### Task B3.2.3 — Rebuild integration + CONTEXT.md

**Red.** `tests/lifecycle/test_dashboard_rebuild.py`:

```python
def test_architect_artifact_rebuild_regenerates_pipeline_html_deterministic():
    # Run architect_artifact_rebuild twice with same inputs;
    # assert byte-identical output.
    ...
```

**Green.** No production code expected to change (rebuild goes through
existing DAG). If a non-determinism surfaces (e.g. iteration order in JSON
output), fix here.

Then update `CONTEXT.md`: add a `## SI&L + LLM Provider Layer + Pipeline
Dashboard` section documenting:

- Where SI&L records live and how to inspect them
  (`architect_component_health COMP-<id>`).
- Where the policy file lives and how to pin providers via
  `meta.provider`.
- How to open the dashboard (path to `pipeline.html` inside
  `.architecture/lifecycle/artifacts/`).

**Commit.** `docs(context): B3.2.3 document SI&L, LLM providers, and pipeline dashboard`

---

## Definition of Done (verification checklist)

Run all of the following on a clean checkout of `feat/sil-and-provider`
(AMS) + `feat/sil-and-provider` (OCA):

1. `pytest tests/ -v --ignore=tests/test_config_loader.py` → **green**
   (AMS side).
2. `pytest ../opencode-arch/tests/ -v` → **green** (OCA side).
3. End-to-end fixture run:

   ```bash
   architecture-model pipeline tests/fixtures/sil/tiny_repo/
   ```

   → produces `tests/fixtures/sil/tiny_repo/.architecture-model.yaml` with
   `meta.provider` populated (if policy is set) and populates SIL store.

4. `python -c "from opencode_arch.mcp.tools.component_health import
   component_health_tool; \
   print(component_health_tool('tests/fixtures/sil/tiny_repo', 'COMP-1'))"`
   returns a dict with `invocations_7d > 0` and a populated `recent_events`.

5. Render the dashboard:

   ```bash
   architect artifact rebuild <spec_for_pipeline_html>
   open .architecture/lifecycle/artifacts/pipeline.html
   ```

   → dashboard loads, badges display, drill-down opens on click.

6. Grep for un-instrumented sites:

   ```bash
   python scripts/apply_sil_decorators.py --check
   ```

   → exits 0 (no missing decorations).

7. CONTEXT.md contains the new SI&L / provider / dashboard section
   (Task B3.2.3).

Only when *all seven* pass does the branch become mergeable.

---

## Risks & mitigations (recap of design §6, made concrete)

- **Instrumentation drift.** CI check in Task B2.2.4 + `apply_sil_decorators.py --check`
  in Definition-of-Done step 6 enforces coverage.
- **Policy misconfig routes to expensive frontier calls.** Policy loader
  in B1.2.5 requires `max_cost_usd_per_call` per rule; `spend()` blocks
  synchronously; CI uses a stub-only policy.
- **Dashboard performance.** `pipeline_state.json` cap of N entities per
  slice enforced in `pipeline_html_data.build()`; drill-down data lazy-loaded.
- **Roll-up correctness.** Golden test in B2.1.3 with a hand-verified
  weighted average. Any change to allocation semantics must update the
  golden and be reviewed.

---

## Handoff

At completion of this plan, offer the executing agent a choice per the
writing-plans skill:

- **Subagent-Driven (this session)** — dispatch each task to a fresh
  subagent via `superpowers:subagent-driven-development`. Recommended for
  Phases B1.1 and B2.1 which have tight per-task scopes.
- **Parallel Session** — spawn a separate session that follows
  `superpowers:executing-plans` with checkpoints after each phase.
  Recommended for Phase B2.2 (mechanical, wide-area) and Phase B3
  (asset-heavy, benefits from focused review passes).
