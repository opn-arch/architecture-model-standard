# Dependency Matrix

| | **Authoring** | **CLI** | **Config** | **Core** | **Docs** | **Export** | **Extract** | **Integrations** | **Manifest** | **Orchestration** | **Pipeline** | **Utils** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Authoring** | · |  |  | → |  |  |  |  |  |  |  |  |
| **CLI** |  | · | → | → |  |  |  |  | → | → | → |  |
| **Config** |  | ← | · | ← |  |  | ← |  | ← |  | ← |  |
| **Core** | ← | ← | → | · | ← | ← | ← | ← |  | ← | ← |  |
| **Docs** |  |  |  | → | · |  |  |  | → |  |  |  |
| **Export** |  |  |  | → |  | · |  |  |  |  |  |  |
| **Extract** |  |  | → | → |  |  | · |  | → |  |  |  |
| **Integrations** |  |  |  | → |  |  |  | · |  |  |  |  |
| **Manifest** |  | ← | → |  | ← |  | ← |  | · | ← | ← | → |
| **Orchestration** |  | ← |  | → |  |  |  |  | → | · |  |  |
| **Pipeline** |  | ← | → | → |  |  |  |  | → |  | · |  |
| **Utils** |  |  |  |  |  |  |  |  | ← |  |  | · |

**Legend:** → = requires from column, ← = provides to column, · = self
