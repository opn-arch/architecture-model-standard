# Sub-Model Assessment Report

## Parent Model Summary

- **Validation Score:** 100/100
- **Components:** 25
- **Capabilities:** 10
- **Interfaces:** 7
- **Behaviors:** 5
- **Constraints:** 2
- **Relationships:** 93
- **Signatures:** 85 (100% with body_hint)
- **Constants:** 26
- **Test Contracts:** 266

## Regen Accuracy Prediction

- **Regen-ready components:** 18/25 (72%)
- **Regen-ready by source lines:** 8,492/9,989 (85%)
- **Gap:** 7 components (cli, core-init, core.differ, extract, manifest-init, profiles, spec) = 1,497 lines

## Sub-Model Coverage

| Block | System | Comps | Caps | IFaces | Behav | Const | Rels | Score |
|-------|--------|:-----:|:----:|:------:|:-----:|:-----:|:----:|:-----:|
| F1 | Cli | 1 | 1 | 1 | 4 | 0 | 10 | 90 |
| F2 | Config | 1 | 1 | 0 | 0 | 0 | 5 | 90 |
| F3 | Core | 8 | 2 | 3 | 1 | 2 | 34 | 74 |
| F4 | Extract | 1 | 1 | 0 | 1 | 0 | 3 | 96 |
| F5 | Manifest | 9 | 1 | 1 | 1 | 0 | 28 | 84 |
| F6 | Orchestration | 2 | 1 | 1 | 1 | 0 | 8 | 88 |
| F7 | Profiles | 1 | 1 | 1 | 0 | 0 | 4 | 94 |
| F8 | Spec | 1 | 1 | 0 | 0 | 1 | 3 | 96 |
| F9 | Utils | 1 | 1 | 0 | 0 | 0 | 5 | 90 |

## Union Coverage

- Components: 25/25 (0 missing)
- Capabilities: 10/10 (0 missing)
- Interfaces: 7/7 (0 missing)

**Result: 100% entity coverage across all sub-models.**

## Changes From Prior Assessment

| Metric | Before | After | Delta |
|--------|:------:|:-----:|:-----:|
| Validation score | 70/100 | 100/100 | +30 |
| Test contracts | 109 | 266 | +157 |
| Constants | 11 | 26 | +15 |
| Regen-ready (comps) | 10/25 (40%) | 18/25 (72%) | +8 |
| Regen-ready (lines) | 5,260 (52%) | 8,492 (85%) | +33pp |
| Sub-model blocks | 8 | 9 | +1 (F9 Orchestration) |
| F-block alignment | Misaligned | Aligned | Fixed |
