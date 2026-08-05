# Dependency Matrix

| | **CLI** | **Config** | **Core** | **Extract** | **Manifest** | **Orchestration** | **Profiles** | **Spec** | **Utils** |
|---|---|---|---|---|---|---|---|---|---|
| **CLI** | · | → | → |  | → | → |  |  |  |
| **Config** | ← | · | ← | ← | ← | ← |  |  | → |
| **Core** | ← | → | · | ← | → | ← | → | → | → |
| **Extract** |  | → | → | · | → |  |  |  |  |
| **Manifest** | ← | → | → | ← | · | ← |  |  | → |
| **Orchestration** | ← | → | → |  | → | · |  |  |  |
| **Profiles** |  |  | ← |  |  |  | · |  |  |
| **Spec** |  |  | ← |  |  |  |  | · |  |
| **Utils** |  | ← | ← |  | ← |  |  |  | · |

**Legend:** → = requires from column, ← = provides to column, · = self
