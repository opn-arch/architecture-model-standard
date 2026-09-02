# Hierarchy Ownership Hardening Design

## Goal

Make hierarchical synthesis deterministic and evidence-local under overlapping boundaries, ambiguous provenance, and namespace collisions.

## Design

Synthesis first computes stable ownership indexes. Every source file has one allocated component owner and one primary boundary owner; stable IDs break overlaps. Explicitly shared corrections and entities remain top-level rather than being copied into child boundaries.

Projection selects components, capabilities, behaviors, interfaces, requirements, constraints, and relationships only through exclusive source ownership or direct graph evidence. Requirement and interface references remain local to the entity supported by direct relationships or its own source file. Component intent comes from one deterministic primary realized capability selected by source overlap, confidence, then stable ID.

Correction scoping understands allocation maps as target-to-files groups and trims each group to the scoped boundary. Structured workflows accept `source_files` or `files_sent`. Duplicate resolution IDs are treated as ambiguous by the library and rejected at the MCP bridge.

All registered IDs and embedded references are remapped consistently. Promotion checks relationships plus embedded component, capability, actor, interface, requirement, and structured-step references before canonical installation.

## Verification

Strict red-green tests cover each rule, followed by an adversarial five-file subsystem and two-inline fixture with overlapping/shared files. Focused and full suites run in both changed repositories. Architecture-model-standard and opencode-arch changes are committed separately.
