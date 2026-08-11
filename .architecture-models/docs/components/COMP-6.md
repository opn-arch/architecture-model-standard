# Component: Extract (COMP-6)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/extract/constraint_detector.py` | — | — |
| `src/architecture_model/extract/from_artifacts.py` | — | — |
| `src/architecture_model/extract/from_code.py` | — | — |
| `src/architecture_model/extract/route_detector.py` | — | — |
| `src/architecture_model/extract/table_parser.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `detect_constraints` | `project_root: Path` | `list[Constraint]` | Scan project configuration files for derivable constraints.

Args:
    project_root: Root directory of the project.

Returns:
    List of Constraint entities derived from config files. |
| `extract_from_artifacts` | `artifact_dir: str | Path, project: str, system: str` | `ArchitectureModel` | Extract a complete architecture model from Tier 1 artifact markdown files.

Args:
    artifact_dir: Directory containing the stage2 artifact markdown files.
    project: Project name (used in meta).
    system: System identifier.

Returns:
    Populated ArchitectureModel. |
| `main` | `` | `` | CLI: extract architecture model from artifacts. |
| `extract_from_code` | `project_root: str | Path, config: ProjectConfig | None, manifest: dict | None` | `ArchitectureModel` | Extract an architecture model directly from source code analysis.

This bypasses the stage2 markdown artifact requirement by deriving
entities and relationships from AST analysis, import graphs, and
project configuration files.

Args:
    project_root: Root directory of the project to analyze.
    config: Optional pre-loaded ProjectConfig. If None, auto-discovered.
    manifest: Optional pre-generated manifest dict. If None, generated fresh.

Returns:
    Complete ArchitectureModel derived from code analysis. |
| `detect_routes` | `project_root: Path, web_layer_dirs: list[str] | None` | `list[RouteInfo]` | Scan Python files for route handler declarations.

Args:
    project_root: Root directory of the project.
    web_layer_dirs: Optional list of directories to restrict scanning
                   (e.g., ["app/api"]). If None, scans all .py files.

Returns:
    List of RouteInfo for each detected route handler. |
| `parse_tables` | `markdown: str` | `list[list[dict[str, str]]]` | Parse all markdown tables in the text.

Returns a list of tables, where each table is a list of row-dicts
keyed by normalized header names. |
| `find_table_after_heading` | `markdown: str, heading_pattern: str` | `list[dict[str, str]]` | Find the first table that appears after a heading matching the pattern.

Args:
    markdown: Full markdown text
    heading_pattern: Regex pattern to match against heading text (case-insensitive)

Returns:
    List of row dicts, or empty list if no matching table found. |
| `extract_sections` | `markdown: str, level: int` | `dict[str, str]` | Split markdown into sections by heading level.

Returns dict mapping heading text -> section content (including sub-headings). |
| `extract_list_items` | `text: str` | `list[str]` | Extract bullet/numbered list items from text. |

## Interface Dependencies

- **requires** `uses_Core` → COMP-4 (Core) [Status, RelationType, ActorType, InterfaceType, ConstraintType, Priority, Strength, ComponentKind, BehaviorPattern, SymbolKind]
- **requires** `uses_Manifest` → COMP-3 (Manifest) [load_config, discover_config, get_config, write_config]
- **provides** `exposes_to_Pipeline` → COMP-2 (Pipeline) [detect_routes, RouteInfo]

## Patterns

None

## Confidence

82%
