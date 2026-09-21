# R8 — Requirements Ingestion from Documentation (Design)

**Date:** 2026-09-20
**Author:** OpenCode session (post-R7 landing)
**Parent report:** `docs/reports/2026-09-20-model-quality-evaluation.md` §5 Path 2, §6 R8
**Status:** approved (design questions answered 2026-09-20)

## Goal

Complement R7's LLM inference with grounded content from real docs.
R8 scans authored documentation and attaches doc-sourced requirements
to model entities as promises. Deterministically-bound matches emit
`status=verified` with the doc as `verified_by`; ambiguous matches
emit `status=proposed`. Together with R7 this is Path 2 in the
evaluation report and closes the content-authenticity gap that pure
LLM inference cannot: real design decisions in real docs become
first-class promise content.

## Scope

**In:**
- R8a — deterministic scan of `docs/reports/`, `docs/plans/`,
  `CONTEXT.md`, `README.md` (configurable). Three deterministic
  binding paths: YAML frontmatter `binds_to:`, inline `<!-- binds: ID -->`
  markers, exact-heading-match against entity name.
- R8b — LLM binding classifier for heading text that fuzzy-matches a
  candidate entity but isn't identical. Reuses the R7 LLMProvider
  Protocol with a classification prompt.
- New pipeline stage `ingest_requirements` inserted after R7 (or
  post-`containerize` when R7 off).
- CLI flag `--ingest-requirements`; config knob for doc roots.

**Out:**
- Cross-repo doc ingestion (URL fetching, remote refs)
- `verified_by` URI schema beyond local file paths
- Requirements deduplication across doc revisions
- Requirements diff/history tracking

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Scope | R8a + R8b (deterministic + LLM binding classifier) |
| 2 | Doc roots | `docs/reports/`, `docs/plans/`, `CONTEXT.md`, `README.md` |

## Architecture

### Three-layer binding

```
Doc section (heading + body)
    │
    ├── Layer 1: explicit marker → binds_to: <entity_id>
    │       (YAML frontmatter, HTML comment, {#ID} anchor)
    │       → status=verified
    │
    ├── Layer 2: exact entity-name match in heading
    │       (case-insensitive, punctuation-normalized)
    │       → status=verified
    │
    └── Layer 3: fuzzy heading — LLM classifier
            (only if Layer 1/2 miss and heading contains any
             entity-name substring token; provider called once
             per (section, candidate-entity) pair)
            → status=proposed with confidence embedded in
              provenance
```

### Data flow

```
ingest_requirements(model, doc_roots, provider) -> new_model
    │
    ├── scan_docs(doc_roots) -> list[DocSection]
    │
    ├── for section in sections:
    │     entity_id = _try_explicit_marker(section)
    │                 or _try_exact_heading_match(section, model)
    │                 or (
    │                     _classify_llm(section, candidates, provider)
    │                     if provider else None
    │                 )
    │     if entity_id:
    │         requirements = _extract_requirements(section.body)
    │         status = VERIFIED if layer in {1,2} else PROPOSED
    │         emit Promise(attribute="requirements", content=req,
    │                      owner_entity=entity_id, status=status,
    │                      verified_by=(section.path,))
```

### DocSection dataclass

```python
@dataclass(frozen=True)
class DocSection:
    path: str            # relative to repo root
    heading: str         # e.g. "## Component: FooBar"
    heading_level: int   # 1..6
    body: str            # markdown between this heading and next
    frontmatter: dict    # top-of-file YAML if any
    inline_binds_to: str | None   # from <!-- binds: ID -->
    anchor_id: str | None         # from {#ID}
```

### Requirement extraction

Rough-and-simple for Phase 1: any bullet or numbered list item in the
section body is one requirement. Prose paragraphs are not extracted
(too noisy for Phase 1). Refined extraction is a follow-on.

### LLM binding classifier prompt

```
You are matching a documentation section to an architecture model
entity. Return strict JSON.

Section heading: "{heading}"
Section body (first 800 chars): "{body_excerpt}"

Candidate entities (id | kind | name):
{candidates_block}

Which entity, if any, does this section describe?
Return: {"entity_id": "<id or null>", "confidence": <0.0-1.0>}
```

Confidence threshold for accepting a match: **≥ 0.75**. Below that
the section produces no promises. This is a knob on the stage.

### Idempotency

- Verified promises from R8a are preserved across re-runs (same
  content → same promise id).
- Proposed promises from R8b are refreshed on re-run (same overwrite
  policy as R7).
- R7-emitted proposed promises for `requirements` are DELETED before
  R8 runs (real docs beat LLM guesses).

### Orchestrator wiring

`run_pipeline` gains:
```python
ingest_requirements: bool = False,
doc_roots: tuple[Path, ...] | None = None,   # defaults to standard set
requirements_provider: LLMProvider | None = None,  # Layer 3 only
```

Stage order when both flags on:
`... → containerize → derive_attributes_llm → ingest_requirements → verify → publish`

Placement rationale: R8 runs AFTER R7 so it can overwrite R7's
proposed `requirements` promises with grounded verified/proposed
content from docs.

## Testing strategy

TDD strict.

1. `test_scan_docs.py` — walk doc roots; parse frontmatter, heading
   tree, inline markers; deterministic ordering.
2. `test_binding_layers.py` — three deterministic layers hit their
   expected paths on fixture docs. Layer 3 uses MockProvider.
3. `test_requirement_extraction.py` — bullet/numbered list extraction;
   empty sections produce no promises; nested lists flattened.
4. `test_ingest_requirements.py` — end-to-end: fixture model +
   fixture docs → model with R8-derived promises. Idempotency
   round-trip.
5. `test_orchestrator_r8.py` — flag off = baseline; flag on = new
   promises; R7+R8 interaction (R7 proposed requirements are
   overwritten by R8).

## Determinism

Scan order by `sorted(paths)`; heading order by file position;
candidate order for classifier by entity id. Promise ids
content-derived (existing invariant). Provider input canonicalized
for MockProvider replay.

## Failure modes

| Failure | Handling |
|---------|----------|
| Missing doc root | Silently skipped (log at debug); not an error |
| Malformed frontmatter | Section still parsed; frontmatter=None |
| Unknown entity_id in explicit marker | Warning; section skipped |
| Provider unavailable + Layer 3 needed | Layer 3 skipped; Layers 1-2 still run |
| Classifier low confidence | No promise emitted |

## Non-goals

- Prose-paragraph requirement extraction (Phase 2)
- Cross-doc requirement dedup (Phase 2)
- Requirement change tracking / doc diff invalidation (Phase 3)
- Multi-language docs (English only)

## Metrics (success criteria)

On AMS itself (~40 report files + 100+ plan files):
- `promotion-strict` — expected shift from 509 insufficient toward
  `ready-to-code-strict` for entities that have real design docs
  (target: ≥ 5 entities reach `ready-to-code-strict`).
- Verified promise count — should grow beyond R7's 138 baseline
  (R8 emits `verified` on marker/exact-heading matches; typical
  authored components have named sections in reports).
- Zero regression on R7 tests.

## Follow-ons

- R8b1: retry queue for low-confidence classifications (human review)
- R8c: verified_by URI expansion (line ranges, section anchors)
- R8d: doc drift detector — invalidate verified promises when the
  source section changes
