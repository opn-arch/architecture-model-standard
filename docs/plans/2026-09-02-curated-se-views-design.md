# Curated SE Architecture Views Design

## Purpose

Replace large, syntax-oriented Mermaid views with curated systems-engineering views that preserve model truth, expose why each visual element exists, and remain useful in a fully offline HTML viewer. The architecture model remains authoritative; curation affects presentation only.

## Design Principles

- Project model semantics into a renderer-neutral `DiagramSpec` before producing SVG.
- Build every projection from a hierarchy-aware `ArchitectureViewContext`, not a flattened model.
- Infer useful external evidence when the model supports it, but label inference and retain provenance.
- Use optional `.architecture/viewer-curation.yaml` only to select, group, order, label, or hide presentation elements.
- Prefer deterministic output, bounded overview size, and explicit drilldown over exhaustive overview graphs.
- Degrade to a useful partial view with diagnostics rather than silently inventing relationships.

## Semantic DiagramSpec

`DiagramSpec` is the contract between SE projectors and renderers. It contains stable view and element IDs, title and description, layout intent, semantic nodes, typed edges, groups, drilldown targets, provenance references, and diagnostics. Nodes retain architecture entity IDs and kinds; edges retain architecture relationship types or an `inferred` marker with evidence. Styling is expressed as semantic roles such as `actor`, `system`, `capability`, `behavior`, `external`, and `warning`, never renderer-specific SVG fragments.

The projector owns meaning and reduction. The renderer owns geometry, SVG escaping, visual tokens, and hit targets. This separation supports snapshot-like projector tests without coupling them to coordinates and lets the viewer render native SVG without Mermaid or a network dependency.

## ArchitectureViewContext

`ArchitectureViewContext` loads the root model and referenced subsystem models through the existing hierarchy APIs while preserving model boundaries. It indexes entities by qualified identity, records each entity's owning model and containment ancestry, resolves cross-model references, and exposes deterministic queries for parents, children, relationships, evidence, and display labels.

Unqualified IDs may resolve only when unique. Ambiguous or missing references become diagnostics and are omitted from asserted semantic edges. The context also loads optional curation and records source provenance for model files, manifest evidence, inferred facts, and curation decisions.

## Presentation Curation

`.architecture/viewer-curation.yaml` is an optional, repository-local presentation profile. It may define aliases, ordering, overview inclusion or exclusion, visual groups, promoted external systems, preferred roots, and per-view drilldown choices. Selectors use qualified architecture identities where ambiguity is possible.

Curation cannot create or mutate architecture entities or relationships. A configured item that cannot be resolved emits a visible diagnostic. Invalid YAML or unsupported keys do not block viewer generation: generation falls back to uncurated projections and reports the profile error. The effective profile and its source location are included in viewer provenance.

## External Evidence Inference

Projectors may add an external node or connection only from concrete evidence already available to the context:

- An `ExternalSystem` entity is authoritative model evidence.
- An interface provider or consumer outside the current system boundary supports an inferred external participant.
- A behavior actor, trigger, or structured step supports an inferred actor interaction when it names a stable participant.
- Manifest routes, protocols, import boundaries, or endpoints support an inferred external dependency only when a stable target can be identified.
- Curation may promote or relabel evidenced external items but cannot supply the evidence itself.

Inferred elements receive deterministic IDs, an `inferred` status, confidence/evidence text, and links to their source facts. Weak strings, duplicate aliases, and ambiguous targets are omitted with diagnostics. Explicit model entities always win over equivalent inferred evidence.

## Overview And Drilldown Structures

### ConOps

The overview shows actors and evidenced external systems around the system boundary, then a small set of operational capability groups inside it. Edges describe operational interactions rather than implementation dependencies. Selecting an actor, external system, or capability opens a drilldown containing relevant behaviors, interfaces, systems, and evidence.

### Functional Architecture

The overview shows the configured or inferred capability roots and one bounded child level, preserving capability containment and important functional flows. A capability drilldown expands its descendants, realizing systems/components, incoming actors or triggers, and related requirements. It does not mix module dependencies into the functional hierarchy.

### Logical Architecture

The overview shows systems grouped by architectural layer or curated logical domain, including evidenced external dependencies and only important inter-system relationships. A system drilldown shows owned components, exposed/consumed interfaces, dependencies, and relevant constraints. Component detail remains a further viewer navigation target rather than crowding the overview.

### Use Cases

The overview groups top-level behaviors by actor or curated operational theme and shows only cross-use-case trigger flow. A use-case drilldown presents trigger, participating actors/systems/components, ordered steps, outcomes, and linked requirements/interfaces. Sequence or flow detail is derived from structured steps when present and marked incomplete otherwise.

Every overview is bounded deterministically. Omitted detail is represented by an explicit count and drilldown affordance, not silently discarded.

## Native Offline SVG

A deterministic Python renderer converts `DiagramSpec` to accessible inline SVG using simple layered layouts. It emits no scripts, remote assets, Mermaid runtime, fonts, or browser layout dependency. SVG nodes carry stable `data-entity-id`, `data-view-id`, semantic classes, keyboard focus, titles, and ARIA labels. Text and attributes are escaped; long labels wrap or truncate predictably; empty and diagnostic states are valid SVG.

## Viewer Interaction

The existing generated HTML viewer embeds overview and drilldown specs/SVG. Clicking or keyboard-activating a node updates the selected entity, opens the appropriate drilldown, and preserves back/forward navigation. Filters and search operate on semantic IDs, not rendered text. A provenance panel explains whether the selection is modeled, inferred, or curated and lists its evidence. Existing entity details remain available from every semantic node.

## Provenance, Errors, And Security

Each node and edge carries zero or more provenance records identifying model entity, relationship, model file, manifest fact, inference rule, and curation selector. Projectors never represent inference as an authored model fact.

Diagnostics have severity, code, message, view, and related source. Missing hierarchy files, dangling or ambiguous IDs, malformed curation, unsupported inference evidence, and layout omissions remain visible in the viewer and testable in `DiagramSpec`. Repository paths are normalized, untrusted labels are escaped, and curation cannot inject HTML, JavaScript, CSS, or raw SVG.

## Testing Strategy

- Unit-test `DiagramSpec` invariants, serialization, escaping boundaries, and deterministic ordering.
- Unit-test hierarchy loading, qualified resolution, curation validation/fallback, evidence precedence, and inference deduplication.
- Test each projector against compact hierarchical fixtures, asserting semantic nodes, edges, drilldowns, provenance, bounded reduction, and diagnostics.
- Test SVG structure with XML parsing, accessibility attributes, stable hit targets, hostile labels, empty views, and byte-for-byte determinism.
- Test viewer integration for offline assets, click/keyboard navigation, history, provenance display, and curation errors.
- Test each SE Markdown generator embeds or links the same curated overview semantics rather than maintaining a second projection algorithm.
- Add a logs-db curation profile regression test and run the focused visualization/SE tests plus the repository test command.

## Non-Goals

- Changing the architecture model schema or model facts.
- Providing a general-purpose graph editor or manual diagram DSL.
- Supporting arbitrary curation-provided entities, relationships, HTML, or SVG.
- Replacing detailed entity inspection, generated SE prose, or model validation.
