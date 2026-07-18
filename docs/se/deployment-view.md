---
artifact_id: deployment-view
generated_at: 2026-07-11T16:11:16.660938+00:00
generator: opencode-arch-docs
---
# Deployment View

## Deployment Units

All components in architecture-model-standard are deployed as a single Python package. There is no layer separation defined in the model — all components share the same deployment boundary.

### Single Package Unit

| Component | Kind | Status |
|-----------|------|--------|
| COMP-CORE | service | ACTIVE |
| COMP-MANIFEST | service | ACTIVE |
| COMP-CONFIG | config | ACTIVE |
| COMP-SPEC | service | ACTIVE |
| COMP-CLI | cli | ACTIVE |

These components are co-deployed as one installable Python distribution. The CLI serves as the user-facing entry point, while core, manifest, config, and spec provide library functionality consumed both by the CLI and by external callers (LLM agents via programmatic API).

### Dependency Structure Within the Unit

- **cli** depends on core, config, and manifest
- **core** depends on config and spec
- **manifest** depends on config

Config and spec have no internal dependencies, forming the foundation of the package.

## Operational Requirements

### Technology Constraints

| ID | Constraint | Type |
|----|-----------|------|
| CON-SCHEMA | Schema Compliance | technology |
| CON-NO-ORPHANS | No Orphaned Entities | technology |

### Constraint Descriptions

**Schema Compliance (CON-SCHEMA)**
All architecture model YAML files processed by the system must conform to the defined JSON Schema in the spec component. The validation engine enforces structural correctness at parse time.

**No Orphaned Entities (CON-NO-ORPHANS)**
Every entity defined in the model must participate in at least one relationship. The validator flags entities that exist in isolation, ensuring the architectural graph remains connected and meaningful.

### Operational Considerations

- **Stateless execution** — All components operate statelessly against the filesystem. No database or persistent process is required.
- **Single-process deployment** — The package runs within a single Python process; no inter-service communication or network configuration is needed.
- **Filesystem access** — The manifest generator requires read access to the target project's source tree for AST scanning. The CLI requires write access to emit generated YAML files.
