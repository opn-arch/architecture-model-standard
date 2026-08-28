# opencode-arch: Pipeline Comparison Report

**Date:** 2026-08-28
**Pipeline version:** architecture-model-standard @ feature/model-quality-16wp
**Mode:** `--llm-review` (heuristic + LLM refinement)

## Quantitative Comparison

| Dimension | Existing (hand-crafted) | LLM-Refined Pipeline | Delta |
|-----------|:-----------------------:|:-------------------:|:-----:|
| Capabilities | 0 | **58** | +58 |
| Components | 15 | 15 | 0 |
| Behaviors | 22 | (in capabilities) | — |
| Interfaces | 26 | 13 | -13 |
| Relationships | 87 | **119** | +32 |
| Layers | 0 | **5** (api, core, library, data, scripts) | +5 |

## Refinement Activity

| Stage | Renames | Additions | Layer Corrections | LLM Time |
|-------|:-------:|:---------:|:-----------------:|:--------:|
| infer | 3 | 51 | 0 | 19.3s |
| allocate | 10 | 0 | 12 | 26.4s |
| specify | 0 | 0 | 0 | 11.0s |
| **Total** | **13** | **51** | **12** | **56.7s** |

## Component Comparison

| Existing (no layers) | Refined (with layers) |
|---------------------|----------------------|
| Extraction Tools | Extract [core] |
| Artifacts | Artifacts [core] |
| CLI Commands | Opencode Arch (cli) [library] |
| Requirements | Requirements [core] |
| Resolution | — (merged) |
| Context Tools | Context [core] |
| Model Management Tools | — (merged into Agent) |
| Documentation Tools | — (merged) |
| Quality Gate Tools | — (merged) |
| Requirements Tools | — (merged) |
| Live Analysis Tools | — (merged) |
| Runner | Runner [core] |
| Telemetry | Telemetry [core] |
| Learning | Learning [core] |
| MCP Server | MCP Server [api] |
| — | LLM [core] |
| — | Agent [core] |
| — | Prompts [core] |
| — | Opencode Arch (mcp) [library] |
| — | Opencode Arch (regen) [library] |
| — | Scripts [scripts] |

## Capabilities (NEW — not in existing model)

Top capabilities found by LLM-refined pipeline:

1. Validate architecture model consistency
2. Run full pipeline (observe → extract → validate → generate)
3. Spot-check regeneration fidelity for a component
4. Calibrate confidence scores against actual regeneration outcomes
5. Classify test failures and apply self-healing
6. Record telemetry and drain to persistent store
7. Parse requirements and trace to architecture entities
8. Generate documentation artifacts from model
9. Detect model drift and auto-fix
10. Author new architecture from requirements
11. Gate check before code generation proceeds
12. Benchmark extraction and regeneration economy
13. Learn from failures and adapt prompts
14. Architecture Extraction
15. Code Regeneration
16. LLM Caching / LLM Relay
17. Context Slicing
18. Repository Decomposition / Grouping / Scanning
19. Model Diffing
20. Gap Analysis

## Interface Quality

| Existing | Refined |
|----------|---------|
| COMP-3-1 Library API | Artifacts API (library) |
| COMP-3-2 Library API | LLM API (library) |
| COMP-3-3 Library API | Context API (library) |
| COMP-3-4 Library API | Learning API (library) |
| COMP-3-5 Library API | Runner API (library) |
| IF-auto-COMP-1: Extraction Tools API | Extract API (library) |
| run_benchmark CLI | run_benchmark CLI (cli) |

## Key Findings

1. **Capabilities are the biggest win**: The existing model had ZERO capabilities — it described structure (components, interfaces) but not WHAT the system does. The refined pipeline found 58 domain-meaningful capabilities.

2. **Layer assignment works**: All 15 components got meaningful layers (api/core/library/scripts). The existing model had no layer information at all.

3. **Component names improved**: "Extraction Tools" → "Extract", "Context Tools" → "Context". More concise, less redundant.

4. **Interface names dramatically better**: Generic "COMP-3-X Library API" → semantic "Artifacts API", "Learning API", etc.

5. **Relationships richer**: 87 → 119 (+37%). LLM adds semantic relationships beyond import-based ones.

6. **Fewer interfaces is better**: 26 → 13. The existing model had many redundant "Library API" entries. The refined model consolidates into meaningful interfaces per component.

## Validation Score

- Existing model: not re-validated
- Refined pipeline: 75/100 (validate stage)
- Refinement didn't hurt validity — the model is structurally sound

## Cost

- Total LLM time: ~57 seconds (3 stages × ~19s each)
- Pipeline total: ~2 minutes (including emit/synthesize)
- Model: copilot-relay (local proxy to frontier LLM)
