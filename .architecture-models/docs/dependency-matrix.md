# Dependency Matrix

| | **Authoring** | **Pipeline** | **Manifest** | **Core** | **Extract** | **Schema** |
|---|---|---|---|---|---|---|
| **Authoring** | · | ← | → | → |  |  |
| **Pipeline** | → | · | → | → | → |  |
| **Manifest** | ← | ← | · | → | ← |  |
| **Core** | ← | ← | → | · | ← | → |
| **Extract** |  | ← | → | → | · |  |
| **Schema** |  |  |  | ← |  | · |

**Legend:** → = requires from column, ← = provides to column, · = self
