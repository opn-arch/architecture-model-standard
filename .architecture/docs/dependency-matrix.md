# Dependency Matrix

| | **Core** | **Type System** | **Validation** | **Parser & Persistence** | **Quality Metrics** | **Export** | **Pipeline Learning** | **Utilities** | **Pipeline** | **Pipeline Coordination** | **Observation Stages** | **Allocation & Relation Stages** | **Specification & Contract Stages** | **Synthesis & Emit Stages** | **Manifest** | **Scanners** | **Graph & Analysis** | **Grouping & Generation** | **Documentation** | **Core Doc Generators** | **SE Document Suite** | **Orchestration** | **Enrichment** | **Decomposition** | **Extract** | **Authoring** | **CLI** | **Configuration** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Core** | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ← |  |
| **Type System** |  | · |  |  |  |  |  |  |  | ← |  | ← |  |  |  |  |  |  |  | ← |  |  | ← |  |  | ← |  |  |
| **Validation** |  |  | · |  |  |  |  |  |  |  |  |  | ← |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Parser & Persistence** |  |  |  | · |  | ← |  |  |  |  |  |  |  | ← |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Quality Metrics** |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ← |  |  |  |  |
| **Export** |  |  |  | → |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Pipeline Learning** |  |  |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | → |
| **Utilities** |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | → |
| **Pipeline** |  |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ← |  |
| **Pipeline Coordination** |  | → |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Observation Stages** |  |  |  |  |  |  |  |  |  |  | · |  |  |  |  | → |  |  |  |  |  |  |  |  |  |  |  |  |
| **Allocation & Relation Stages** |  | → |  |  |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Specification & Contract Stages** |  |  | → |  |  |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Synthesis & Emit Stages** |  |  |  | → |  |  |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| **Manifest** |  |  |  |  |  |  |  |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  | ← |  |  | ← | ← |  |
| **Scanners** |  |  |  |  |  |  |  |  |  |  | ← |  |  |  |  | · | ← |  |  |  |  |  |  |  | ← |  |  | → |
| **Graph & Analysis** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | → | · | ← |  |  |  |  |  |  |  |  |  |  |
| **Grouping & Generation** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | → | · |  |  |  |  |  |  |  |  |  |  |
| **Documentation** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | · |  |  |  |  |  |  |  | ← |  |
| **Core Doc Generators** |  | → |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | · | ← |  |  |  |  |  |  |  |
| **SE Document Suite** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | → | · |  |  |  |  |  |  |  |
| **Orchestration** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | · |  |  |  |  | ← |  |
| **Enrichment** |  | → |  |  |  |  |  |  |  |  |  |  |  |  | → |  |  |  |  |  |  |  | · |  |  |  |  |  |
| **Decomposition** |  |  |  |  | → |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | · |  |  |  |  |
| **Extract** |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | → |  |  |  |  |  |  |  |  | · |  |  | → |
| **Authoring** |  | → |  |  |  |  |  |  |  |  |  |  |  |  | → |  |  |  |  |  |  |  |  |  |  | · | ← |  |
| **CLI** | → |  |  |  |  |  |  |  | → |  |  |  |  |  | → |  |  |  | → |  |  | → |  |  |  | → | · |  |
| **Configuration** |  |  |  |  |  |  | ← | ← |  |  |  |  |  |  |  | ← |  |  |  |  |  |  |  |  | ← |  |  | · |

**Legend:** → = requires from column, ← = provides to column, · = self
