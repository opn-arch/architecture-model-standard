# Lifecycle Terminology

Single source of truth for terms used across the architecture lifecycle
(identity, packaging, revisions, slicing, views, artifacts, gates).
All persisted artifacts declare a `schema_version` frozen in
`architecture_model.lifecycle.versions`.

## Core terms

### ArchitecturePackage
Recursive descriptor for a unit of ownership within an architecture.
The root package and every child package use the **identical** contract —
no special casing for the root. A package owns a set of source paths,
declares its dependencies, and may contain child packages recursively.

### ModelSlice
A bounded, **immutable** projection of a model taken at a specific
model `Revision`. A slice is defined by three orthogonal dimensions:

- **scope**: `local` | `descendants` | `federated`
  (this package, this package plus its children, or a set of peer
  packages joined at declared boundaries).
- **closure**: `strict` | `boundary-stubs` | `transitive`
  (drop out-of-scope refs, replace them with typed stubs, or pull in
  their full definitions transitively).
- **shared_refs**: `none` | `explicit` | `transitive`
  (how references into `shared_paths` are materialized).

A ModelSlice is content-addressed by its own `Digest`; two slices with
identical inputs produce identical revisions.

### ViewSpec
A declarative wrapper that binds three things together: element
**selectors** (which entities from a slice participate), **curation**
rules (grouping, hiding, decorations, ordering), and **projector**
configuration (which projection algorithm and its parameters). A
ViewSpec **consumes** a `ModelSlice` at a pinned revision and
**produces** a `DiagramSpec` as its content payload.

### DiagramSpec
Renderer-neutral content description of a diagram — the existing type
defined in `core/diagram_spec.py`. It is the payload produced by a
ViewSpec and consumed by renderers. **Do not rename**; treat as a
stable interior type.

### ArtifactSpec
Specification of a materialized output: SVG, Markdown, HTML,
AI-context bundle, or a ZIP of other artifacts. An ArtifactSpec
references a `ViewSpec` at a pinned revision, or bundles other
ArtifactSpecs by reference. Rendering an ArtifactSpec is deterministic
given its pinned inputs.

### Revision
Content-addressed, immutable version identifier of a model or spec.
Computed as `Digest` over the canonical payload. Revisions are the
identity handle used everywhere pinning is needed (slice → model,
view → slice, artifact → view). **Distinct** from the pipeline
history's `base` / `final` markers — those describe stage-run status
of a pipeline execution, not artifact identity.

### Generation
A numbered publication of a package under
`generations/<N>/`. Previous generations remain **immutable** and
addressable forever; publishing produces a new generation directory
and never rewrites an old one.

### CURRENT
An atomically-switched symlink alongside the `generations/` directory
that points at the active generation of a package. Readers follow
`CURRENT`; publishers switch it in a single filesystem operation
after the new generation has been fully written and verified.

### Digest
`sha256-v1(canonical_json(payload, exclude=[generated_at, signatures]))`.
Canonical JSON with sorted keys, no insignificant whitespace, and the
non-content fields `generated_at` and `signatures` excluded so that
identical content always yields identical digests. Encoded as a
prefixed hex string; the algorithm tag is frozen as
`SchemaVersions.DIGEST_ALGO`.

### Qualified ID
The tuple `(architecture_id, model_revision, local_id)`. Entities
are **always** referenced by qualified id — never by filesystem path,
never by position, never by unqualified `local_id` outside of its
owning model revision.

### Ownership
Every source file has **exactly one** owner package. The only
exception is files declared under `shared_paths`, which are
explicitly co-owned and referenced across package boundaries via
declared `shared_refs` policy on slices. Any file matched by two
packages without a `shared_paths` declaration is a lifecycle error.
