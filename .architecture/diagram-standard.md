# Architecture Diagram Visual Standard

Standardized Mermaid shapes, edges, and colors for architecture entity visualization.

## Shape Standard

| Entity Type | Shape | Mermaid Syntax | CSS Class | Color |
|-------------|-------|----------------|-----------|-------|
| Stage | Subroutine | `ID[[Label]]` | `cls_stage` | Blue #4A90D9 |
| Component | Rectangle | `ID[Label]` | `cls_comp` | Green #27AE60 |
| Capability | Rounded rect | `ID(Label)` | `cls_cap` | Orange #F39C12 |
| Behavior | Hexagon | `ID{{Label}}` | `cls_beh` | Purple #8E44AD |
| Interface | Circle | `ID((Label))` | `cls_iface` | Cyan #1ABC9C |
| Module | Parallelogram | `ID[/Label/]` | `cls_mod` | Gray #95A5A6 |
| Actor | Stadium | `ID([Label])` | `cls_actor` | Pink #E74C8B |
| Constraint | Diamond | `ID{Label}` | `cls_con` | Red #E74C3C |
| Layer | Cylinder | `ID[(Label)]` | `cls_layer` | Teal #16A085 |

## Edge Standard

| Relationship | Arrow | Category |
|-------------|-------|----------|
| realizes | `==>` (thick) | Core |
| contains | `-.->` (dotted) | Core |
| depends-on | `-->` (solid) | Core |
| uses | `-->` (solid) | Core |
| exposes | `-.->` (dotted) | Core |
| consumes | `-->` (solid) | Core |
| traces-to | `-.->` (dotted) | Core |
| allocated-to | `-.->` (dotted) | Core |
| constrained-by | `-.-x` (dotted cross) | Core |
| triggers | `-->` (solid) | Behavioral |
| produces | `==>` (thick) | Data flow |
| subscribes-to | `-.->` (dotted) | Data flow |
| transforms | `==>` (thick) | Data flow |
| satisfies | `-.->` (dotted) | V&V |
| verifies | `-.->` (dotted) | V&V |
| supersedes | `-.-x` (dotted cross) | Lifecycle |
| migrates-to | `-.->` (dotted) | Lifecycle |

## 10 Diagram Types

| # | Name | Type | File | Shows |
|---|------|------|------|-------|
| 1 | Context | Model | `context.mmd` | Actors → interfaces → system boundary |
| 2 | Components | Model | `components.mmd` | Components by layer, realizes → capabilities |
| 3 | Behaviors | Model | `behaviors.mmd` | Behavior flow with triggers/contains |
| 4 | Dependencies | Model | `dependencies.mmd` | Inter-component dependency graph |
| 5 | Pipeline Flow | Static | `pipeline-flow.mmd` | 10 pipeline stages + LLM refinement loop |
| 6 | Entity Lifecycle | Static | `entity-lifecycle.mmd` | Entity evolution across stages |
| 7 | Data Flow | Model | `data-flow.mmd` | produces/subscribes/transforms chains |
| 8 | Constraint Map | Model | `constraint-map.mmd` | Constraint → component allocation |
| 9 | Traceability | Model | `traceability.mmd` | Capabilities → components → behaviors |
| 10 | Decomposition | Model | `decomposition.mmd` | System → layers → components tree |

## Usage

### Python API
```python
from architecture_model.core.visualize import generate_all_diagrams, shape, edge_style
paths = generate_all_diagrams(model, output_dir)
```

### CLI
```bash
architecture-model visualize /path/to/project -o diagrams/
```

### Building custom diagrams
```python
from architecture_model.core.visualize import shape, edge_style, css_classes

lines = ["flowchart TD"]
lines.append(f"    {shape('component', 'COMP-1', 'My Service')}")
lines.append(f"    {shape('interface', 'IF-1', 'REST API')}")
lines.append(f"    COMP_1 {edge_style('exposes')} IF_1")
lines.extend(css_classes())
```
