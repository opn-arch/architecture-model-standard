# Layer Architecture — architecture-model-standard

## Layer Overview

The system uses a single **Application Layer** (L-APP) containing all 9 top-level components. Two of these — COMP-CORE and COMP-MANIFEST — are decomposed into sub-components, bringing the total to 24 addressable units.

| Layer | ID | Components | Sub-Components | Total |
|-------|----|:----------:|:--------------:|:-----:|
| Application | L-APP | 9 | 15 | 24 |

## Component Catalog

### Top-Level Components

| ID | Name | Description |
|---|---|---|
| COMP-CORE | core | Parser, validator, slicer, differ, merger, decomposer, type system |
| COMP-MANIFEST | manifest | AST scanner, block discovery, metrics, interfaces, body hints, test analyzer |
| COMP-CLI | cli | CLI entry point (9 commands) |
| COMP-CONFIG | config | Configuration loader and schema |
| COMP-SPEC | spec | JSON Schema definitions |
| COMP-EXTRACT | extract | Model extraction from source code |
| COMP-PROFILES | profiles | Domain profile loading, open enums |
| COMP-UTILS | utils | Shared file discovery, exclusion patterns |
| COMP-ENRICH | enrich | Auto-enrichment of models from AST |

### COMP-CORE Sub-Components (7)

| ID | Name | Role |
|---|---|---|
| COMP-CORE-PARSER | parser | Load/save architecture models from YAML |
| COMP-CORE-VALIDATOR | validator | Structural validation, scoring |
| COMP-CORE-SLICER | slicer | Extract sub-models by F-block or layer |
| COMP-CORE-DIFFER | differ | Diff two architecture models |
| COMP-CORE-MERGER | merger | Merge partial models |
| COMP-CORE-DECOMPOSER | decomposer | Decompose monolith into subsystems |
| COMP-CORE-TYPES | types | Shared type definitions (ArchitectureModel, etc.) |

### COMP-MANIFEST Sub-Components (8)

| ID | Name | Role |
|---|---|---|
| COMP-MANIFEST-GENERATOR | generator | Orchestrates manifest generation |
| COMP-MANIFEST-SCANNER | scanner | AST scanning of Python source files |
| COMP-MANIFEST-BLOCKS | blocks | F-block discovery from package structure |
| COMP-MANIFEST-METRICS | metrics | LOC, complexity, function counts |
| COMP-MANIFEST-INTERFACES | interfaces | Public API extraction |
| COMP-MANIFEST-BODY-HINTS | body-hints | Trivial function body extraction |
| COMP-MANIFEST-TEST-ANALYZER | test-analyzer | Test file analysis, contract extraction |
| COMP-MANIFEST-TYPES | types | Manifest-specific type definitions |

## Top-Level Dependency Graph

```
                        ┌──────────┐
                        │ COMP-CLI │
                        └────┬─────┘
               ┌─────────┬──┴──┬───────────┐
               ▼         ▼     ▼           ▼
          ┌────────┐ ┌──────┐ ┌──────────┐ ┌────────┐
          │  CORE  │ │CONFIG│ │ MANIFEST │ │ ENRICH │
          └───┬────┘ └──────┘ └────┬─────┘ └───┬────┘
         ┌────┼────┐          ┌────┘       ┌───┘
         ▼    ▼    ▼          ▼            ▼
     ┌──────┐┌────┐┌────────┐┌─────┐  ┌──────┐┌──────────┐
     │CONFIG││SPEC││PROFILES││UTILS│  │ CORE ││ MANIFEST │
     └──────┘└────┘└────────┘└─────┘  └──────┘└──────────┘

     COMP-EXTRACT ──▶ COMP-CORE
```

**Dependency summary:**

- **COMP-CLI** → CORE, CONFIG, MANIFEST, ENRICH
- **COMP-CORE** → CONFIG, SPEC, PROFILES
- **COMP-MANIFEST** → CONFIG, UTILS
- **COMP-EXTRACT** → CORE
- **COMP-ENRICH** → CORE, MANIFEST

Leaf components (no outgoing dependencies): CONFIG, SPEC, PROFILES, UTILS.

## COMP-CORE Internal Dependency Graph

```
  ┌────────┐  ┌───────────┐  ┌────────┐  ┌────────┐  ┌────────┐
  │ PARSER │  │ VALIDATOR │  │ SLICER │  │ DIFFER │  │ MERGER │
  └───┬────┘  └─────┬─────┘  └───┬────┘  └───┬────┘  └───┬────┘
      │          ┌───┘            │           │        ┌──┘
      │          │                │           │        │
      ▼          ▼                ▼           ▼        ▼
  ┌───────┐  ┌────────┐      ┌───────┐  ┌───────┐ ┌───────┐
  │ TYPES │  │PROFILES│      │ TYPES │  │ TYPES │ │ TYPES │
  └───────┘  │(extern)│      └───────┘  └───────┘ └───────┘
             └────────┘
                              ┌────────────┐
                              │ DECOMPOSER │
                              └──────┬─────┘
                                ┌────┘
                                ▼
                            ┌───────┐  ┌───────┐
                            │ TYPES │  │ UTILS │
                            └───────┘  │(extern)│
                                       └───────┘
```

All six operational sub-components depend on **TYPES**. VALIDATOR also reaches outside to PROFILES. MERGER and DECOMPOSER reach outside to UTILS.

## COMP-MANIFEST Internal Dependency Graph

```
                     ┌───────────┐
                     │ GENERATOR │
                     └─────┬─────┘
            ┌────┬────┬────┼────┐
            ▼    ▼    ▼    ▼    ▼
        ┌──────┐┌──────┐┌───────┐┌──────────┐┌───────┐
        │SCANNER││BLOCKS││METRICS││INTERFACES││ TYPES │
        └──┬───┘└──┬───┘└──┬────┘└────┬─────┘└───────┘
           │    ┌──┘       │          │
           ▼    ▼          ▼          ▼
        ┌─────┐┌──────┐┌───────┐ ┌───────┐
        │TYPES││SCANNER││ TYPES │ │ TYPES │
        └─────┘└──────┘└───────┘ └───────┘
               ┌───────┐
               │ UTILS │  (BLOCKS also depends on external UTILS)
               │(extern)│
               └───────┘

  ┌────────────┐          ┌───────────────┐
  │ BODY-HINTS │          │ TEST-ANALYZER │
  └──────┬─────┘          └───────┬───────┘
         ▼                        ▼
     ┌──────────┐            ┌──────────┐
     │CORE-TYPES│            │CORE-TYPES│
     │ (extern) │            │ (extern) │
     └──────────┘            └──────────┘
```

GENERATOR orchestrates SCANNER, BLOCKS, METRICS, INTERFACES, and TYPES. BODY-HINTS and TEST-ANALYZER depend on CORE-TYPES (cross-component).

## Interface Exposure Mapping

| Component | Interface ID | API Surface |
|---|---|---|
| COMP-CLI | IF-CLI | 9 CLI commands (init, extract, validate, slice, diff, query, context, stats, impact) |
| COMP-CORE-PARSER | IF-PARSE-API | `load_model()`, `save_model()` |
| COMP-CORE-VALIDATOR | IF-VALIDATE-API | `validate_model() → ValidationResult` |
| COMP-CORE-SLICER | IF-SLICER-API | `slice_by_fblock()`, `slice_by_layer()` |
| COMP-MANIFEST-GENERATOR | IF-MANIFEST-API | `generate_manifest() → Manifest` |
| COMP-PROFILES | IF-PROFILE-API | `load_profile() → DomainProfile` |
| COMP-ENRICH | IF-ENRICH-API | `enrich_model() → ArchitectureModel` |

## Dependency Matrix

Rows depend on columns. **●** = direct dependency.

| | CONFIG | SPEC | PROFILES | UTILS | CORE | MANIFEST |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **COMP-CLI** | ● | | | | ● | ● |
| **COMP-CORE** | ● | ● | ● | | | |
| **COMP-MANIFEST** | ● | | | ● | | |
| **COMP-EXTRACT** | | | | | ● | |
| **COMP-ENRICH** | | | | | ● | ● |

COMP-CLI also depends on COMP-ENRICH (omitted from columns for space — it is a transitive consumer of CORE and MANIFEST through ENRICH).

## Technology Stack

| Technology | Role |
|---|---|
| Python 3.10+ | Implementation language |
| YAML | Model serialization format |
| JSON Schema | Model structural validation (COMP-SPEC) |
| Python `ast` module | Source code scanning (COMP-MANIFEST) |
| Click | CLI framework (COMP-CLI) |

## Relationship Summary

| Type | Count |
|---|:---:|
| depends-on | 34 |
| contains | 24 |
| realizes | 10 |
| traces-to | 9 |
| exposes | 7 |
| consumes | 4 |
| constrained-by | 3 |
| **Total** | **91** |
