# Close the LLM Loop — Design Document

**Date:** 2026-08-28  
**Status:** Approved  
**Branch:** `feature/model-quality-16wp`

## Problem

The pipeline has all the pieces for LLM-enhanced inference but they're not connected:
- Heuristic stages produce mediocre names, wrong layers, miss capabilities
- `gap_prompts.py` can ask LLM to re-infer from scratch per stage
- `gap_analysis.py` can diff heuristic vs LLM output
- `auto_correct.py` can apply field-level corrections (but blocks names, can't add/remove entities)
- None of these are wired together in the pipeline's main flow

## Solution

Add an LLM refinement step after stages 2-5 (infer, allocate, relate, specify) that:
1. Runs heuristics first (fast, deterministic baseline)
2. Asks LLM to re-infer from scratch (reuses gap_prompts)
3. Diffs the two outputs (reuses gap_analysis diff engine)
4. Applies improvements to the stage output objects directly

## Stage-by-Stage LLM Role

| Stage | LLM Refinement | LLM Review (post-hoc) | Rationale |
|-------|:-:|:-:|-----------|
| observe | No | Keep | AST is ground truth |
| infer | **Yes** | Remove (subsumed) | Names, descriptions, missed capabilities |
| allocate | **Yes** | Remove (subsumed) | Layer assignments, component names |
| relate | **Yes** | Remove (subsumed) | Semantic relationship types |
| specify | **Yes** | Remove (subsumed) | Interface naming and classification |
| contract | No | Keep | Deterministic test matching |
| validate | No | Keep | Rule-based, review adds second opinion |
| decompose | No | Keep | Structural thresholds |

## New Module: `llm_refine.py`

Operates on stage output objects directly (not model dicts like auto_correct.py).

### Refinement operations per stage

**infer:** Rename capabilities/behaviors (sim >= 0.5), add LLM-only ones with origin="llm_inferred"  
**allocate:** Rename components (sim >= 0.5), override layers (always), no add/remove  
**relate:** Add LLM-only relationships, upgrade rel types, no removal of import-based  
**specify:** Rename interfaces (sim >= 0.5), improve type classification  

### Confidence model

- sim >= 0.7: auto-apply ("high confidence")
- sim 0.5-0.7: apply ("llm-suggested")
- sim < 0.5: skip
- Layer corrections: always apply
- LLM additions: tag with origin="llm_inferred"
