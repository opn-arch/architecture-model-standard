# R7 — LLM Attribute Inference (Design)

**Date:** 2026-09-20
**Author:** OpenCode session (post-R9 checkpoint)
**Parent report:** `docs/reports/2026-09-20-model-quality-evaluation.md` §5 Path 1, §6 R7
**Status:** approved (design questions answered 2026-09-20)

## Goal

Close the substrate→content gap that R9 exposed: 509/522 entities carry
only `intent` promises and fail the promotion-strict five-attribute
Category B gate. R7 adds an optional pipeline_v3 stage that proposes
Category B attributes as `status: proposed` promises using an LLM
provider, so downstream review can validate and promote them.

## Scope

**In:** optional post-`containerize` pipeline stage; new
`derive_attributes_llm` module; CLI flag `--infer-attributes`;
MCPProvider integration for real inference; MockProvider for CI;
tests via TDD.

**Out (explicitly deferred):**
- R8 (requirements ingestion from docs)
- Human-in-the-loop review UI
- Cost tracking / budget enforcement (relies on OCA policy layer)
- Attribute inference for actors, interfaces, constraints entities,
  layers — vocabulary mismatch with Category B gate

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Which attributes? | All five: `goals`, `requirements`, `success_criteria`, `failure_modes`, `constraints` |
| 2 | Which entity kinds? | `behaviors` + `components` + `capabilities` |
| 3 | Idempotency | Skip entities where attribute already has `verified` promises; overwrite `proposed` on re-run |
| 4 | Default provider | MCPProvider (OCA subprocess), lazy-imported |

## Architecture

### Pipeline integration

```
scan → derive_promises → derive_behaviors → derive_triggers →
cluster → link → containerize →
[derive_attributes_llm]  ← NEW, gated by infer_attributes=True
→ verify → publish
```

Placement rationale: post-`containerize` gives the LLM a complete
ContainerizedBehavior + Component tree to reason over; pre-`verify`
means the new proposed promises participate in verification.

### API surface

```python
# src/architecture_model/pipeline_v3/derive_attributes_llm.py

CATEGORY_B_ATTRIBUTES = (
    "goals",
    "requirements",
    "success_criteria",
    "failure_modes",
    "constraints",
)

TARGET_KINDS = ("behaviors", "components", "capabilities")

@dataclass(frozen=True)
class AttributeInferenceRequest:
    entity_id: str
    entity_kind: str          # singular: "behavior" | "component" | "capability"
    entity_name: str
    entity_description: str
    existing_promises: tuple[Promise, ...]   # for context
    target_attribute: str     # one of CATEGORY_B_ATTRIBUTES

@dataclass(frozen=True)
class AttributeInferenceResult:
    entity_id: str
    target_attribute: str
    items: tuple[str, ...]    # each becomes one Promise
    error: str | None = None  # populated on failure; items empty


def derive_attributes(
    model: dict,
    *,
    provider: LLMProvider,
    target_kinds: tuple[str, ...] = TARGET_KINDS,
    target_attributes: tuple[str, ...] = CATEGORY_B_ATTRIBUTES,
    batch_size: int = 10,
) -> dict:
    """Return a new model dict with proposed promises appended.

    Idempotent policy:
        * Entities with ≥1 verified promise for a target attribute are skipped.
        * Existing proposed promises for a target attribute are replaced.
        * intent + typed-gap + open promises are preserved untouched.

    Batching:
        * Requests are grouped by (entity_kind, target_attribute) then
          batched at ``batch_size`` per provider.structured() call.
        * Batches are ordered by (entity_kind, attribute, entity_id) for
          determinism.

    Failure model:
        * Per-batch provider errors are captured on
          AttributeInferenceResult.error; no partial writes into the model.
        * Whole-stage failure raises; caller decides whether to publish.
    """
```

### Orchestrator wiring

`run_pipeline` gains two kwargs:
```python
def run_pipeline(
    repo_path,
    *,
    out_path,
    project_name="",
    cluster_depth=3,
    skip_publish=False,
    infer_attributes: bool = False,          # NEW
    attribute_provider: LLMProvider | None = None,  # NEW
) -> PipelineRunResult:
    ...
    if infer_attributes:
        if attribute_provider is None:
            attribute_provider = _load_default_provider()  # lazy MCPProvider
        stages.insert(<after containerize>, wrap_function(
            "derive_attributes_llm",
            lambda s: {**s, "model": derive_attributes(s["model"], provider=attribute_provider)},
        ))
```

### Default provider loader

```python
# src/architecture_model/pipeline_v3/derive_attributes_llm.py

def _load_default_provider() -> LLMProvider:
    """Lazy-load MCPProvider from opencode_arch. Fail with actionable message."""
    try:
        from opencode_arch.llm.providers.mcp import MCPProvider
    except ImportError as exc:
        raise RuntimeError(
            "R7 --infer-attributes requires either a --provider argument or "
            "`opencode-arch` installed. Install with `pip install opencode-arch` "
            "or pass a custom LLMProvider to run_pipeline(attribute_provider=...)."
        ) from exc
    return MCPProvider.from_config()  # uses OCA's default policy
```

### Prompt

Reuses `src/architecture_model/llm/prompts/fill_promise.md` — already
generic over `{attribute}`. R7 populates `{entity_kind_singular}` = one
of `behavior|component|capability` and `{note_body}` with a stub:

> Propose 1–5 concise items for the `{attribute}` of this
> {entity_kind_singular}. Each item should be a single declarative
> sentence. Return JSON: `{"{attribute}": ["item 1", "item 2", ...]}`.

The `promises_block`, `parent_chain`, `siblings_block`, and
`relations_block` are populated via existing `_prompt_assembly`
helpers — no new prompt code needed.

### Response schema

```python
# JSON schema handed to provider.structured():
{
    "type": "object",
    "properties": {
        "<attribute>": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
            "maxItems": 5,
        }
    },
    "required": ["<attribute>"],
    "additionalProperties": False,
}
```

### Data flow

```
containerize.state.model
    │
    ├── for kind in TARGET_KINDS:
    │   for entity in model["entities"][kind]:
    │     for attribute in CATEGORY_B_ATTRIBUTES:
    │       if has_verified(entity, attribute): skip
    │       else: emit AttributeInferenceRequest
    │
    ├── batch requests by (kind, attribute)
    │
    ├── for batch in batches:
    │     provider.structured(prompt, schema) → list[AttributeInferenceResult]
    │
    └── mutate model:
          entity["promises"] = (
              [p for p in entity["promises"] if not (p.attribute == attr and p.status == PROPOSED)]
              + [Promise(id=..., owner=entity_id, attribute=attr, content=item,
                         status=PROPOSED, verified_by=()) for item in result.items]
          )
```

## Testing strategy

TDD strict — failing tests before implementation. Provider abstraction
allows MockProvider for CI.

**Test cohorts:**
1. `test_derive_attributes.py` — unit tests over `derive_attributes()`
   with a MockProvider that returns canned JSON. Assertions:
   - New proposed promises appear on target entities
   - Verified promises preserved
   - Existing proposed promises replaced (not duplicated)
   - Non-target kinds untouched
   - Deterministic ordering
2. `test_default_provider_loader.py` — ImportError path emits actionable
   message; ImportError caught cleanly.
3. `test_orchestrator_attribute_flag.py` — `run_pipeline(infer_attributes=True,
   attribute_provider=MockProvider())` on a fixture repo produces model
   with proposed attributes; `infer_attributes=False` is byte-identical
   to pre-R7 output.
4. Manual smoke test (not committed): `run_pipeline(..., infer_attributes=True)`
   against AMS itself using MCPProvider → OCA. Verify one entity's
   proposed promises look sensible.

## Determinism

Deterministic ordering per entity + attribute (sort by entity_id).
Batch ordering by (kind, attribute, entity_id). Promise id derivation
via existing `Promise.derive_id(owner, attribute, content, status)`.
Non-deterministic input (LLM output) is scoped to `content`; ids
change if content changes — desired.

## Failure modes

| Failure | Handling |
|---------|----------|
| Provider raises | Batch marked `error`; entity's promises untouched |
| Provider returns malformed JSON | Same as above (validator upstream) |
| Provider returns empty list | Treated as "no proposal"; no promises emitted; not an error |
| OCA not installed + no --provider | Fail-fast in `_load_default_provider` with install instructions |
| infer_attributes=False | Stage skipped; pipeline byte-identical to pre-R7 |

## Non-goals

- Cost/budget tracking (OCA policy layer owns this)
- Prompt refinement based on prompt_refiner walk (out of scope; add later)
- Multi-provider fallback (single provider per run)
- Attribute quality scoring / verified_by inference (that's the human
  review step or a follow-on R7b)
- Recursive re-inference on model diffs (single-shot per run)

## Metrics (success criteria)

After R7 executes on AMS with a working provider:
- `promotion-strict` verdict distribution shifts toward `partial-strict`
  and `ready-to-code-strict`. Target: ≥30% of behaviors reach
  `partial-strict` (some proposed promises for ≥1 attribute).
- Zero regressions on `attribute-completeness` (needs-enrichment stays 0).
- Zero change to verified promise count (138 → 138).
- `total promises` grows by ~N_entities × 5_attributes × ~3_items avg
  ≈ 15,000 (upper bound; real run likely 3–5k after skip logic).

## Follow-ons

- R7b: per-attribute prompt specialization (currently one template).
- R8: requirements ingestion complements R7 by supplying `verified`
  promises from doc scans — the verified/proposed ratio should shift
  toward verified over time.
- OCA integration: expose `architect_infer_attributes(repo_path)` MCP
  tool wrapping this stage.
