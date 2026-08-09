# Component: Store (COMP-5)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/persistence/store.py` | — | — |

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
| `save_project` | `root: Path, model: Any, manifest: Any, representativeness: Any | None, telemetry: dict | None` | `Path` | Persist model + manifest + metrics to .architecture/ directory.

Args:
    root: Repository root directory
    model: ArchitectureModel instance
    manifest: Manifest instance (has .to_dict())
    representativeness: RepresentativenessResult instance (has .to_dict())
    telemetry: Optional telemetry dict (token_budget, iterations, etc.)

Returns:
    Path to the .architecture/ directory |
| `save_block` | `root: Path, block_id: str, model: Any, manifest: Any, representativeness: Any | None` | `Path` | Persist a hierarchical block's artifacts to .architecture/<block_id>/.

Args:
    root: Repository root directory
    block_id: F-block ID (e.g., "F1")
    model: ArchitectureModel for this block
    manifest: Manifest for this block
    representativeness: Optional RepresentativenessResult for this block

Returns:
    Path to the block directory |
| `load_project` | `root: Path` | `ProjectSnapshot` | Load model + manifest + metrics from .architecture/ directory.

Args:
    root: Repository root directory

Returns:
    ProjectSnapshot with loaded data |

## Interface Dependencies

- **provides** `exposes_to_Core` → COMP-1 (Core) [save_project, save_block, load_project, ProjectSnapshot]
- **requires** `uses_Core` → COMP-1 (Core) [load_block_model, load_model, validate_model_data, dump_model, save_model]

## Patterns

None

## Confidence

82%
