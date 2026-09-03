# Viewer Curation Reference

Viewer curation is an optional, presentation-only overlay for the native ConOps,
functional, logical, and use-case views. It selects, orders, labels, groups, and
annotates canonical architecture facts without changing the architecture model.
If no profile exists, curation is disabled, or a view is invalid, the projectors
automatically produce deterministic views from the canonical model.

## Discovery And CLI

By default, both commands discover
`.architecture/viewer-curation.yaml` below the project root:

```text
architecture-model viewer <path>
architecture-model visualize <path>
```

Use an explicit repository-relative profile or disable discovery:

- `architecture-model viewer <path> --curation <path>`
- `architecture-model viewer <path> --no-curation`
- `architecture-model visualize <path> --curation <path>`
- `architecture-model visualize <path> --no-curation`

`--curation` and `--no-curation` are mutually exclusive. The explicit path must
remain inside the project root.

## Python API

Load and validate the optional overlay against a hierarchy-aware context:

```python
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import load_viewer_curation

context = ArchitectureViewContext.from_repo(project_root)
curation = load_viewer_curation(project_root, context, path=None)
for warning in curation.diagnostics:
    print(warning.code, warning.message)
```

`path=None` performs default discovery. `load_viewer_curation()` always returns
a `ViewerCuration`; missing or rejected data is represented by empty
`ViewCuration` values and warning diagnostics rather than an exception. Advanced
callers can use `validate_view_curation()` for constructed overlays and
`merge_ordered()` for deterministic first-seen ordering. Pass each loaded view
to `project_conops()`, `project_functional_architecture()`,
`project_logical_architecture()`, or `project_use_cases()`, or call
`build_curated_views()` to assemble all four projections.

## Version 1 Schema

The root has exactly `version: 1` and a `views` mapping. Supported view names
are `conops`, `functional`, `logical`, and `use_cases`. Every field is optional;
an omitted view uses automatic projection.

### Common View Fields

| Key | Value | Meaning |
|---|---|---|
| `featured` | selector list | Prefer entities in the bounded overview. |
| `hide` | selector list | Omit matching presentation entities. |
| `order` | qualified-ID or presentation-ID list | Stable display priority. |
| `labels` | ID-to-text mapping | Presentation labels for known IDs. |
| `externals` | external list | Evidenced inferred external systems. |
| `scenarios` | scenario list | Evidenced operational groupings. |
| `groups` | group list | Presentation groupings or aggregates. |
| `flows` | flow list | Canonical or evidenced inferred connections. |
| `tiers` | group list | Ordered logical tiers. |
| `aggregate_components` | selector list | Components represented by aggregates. |
| `preferred_capability_root` | selector | Preferred functional root. |
| `mission_root` | selector | Preferred mission root. |
| `drilldowns` | name-to-selector mapping | Named drilldown entry points. |

`ViewCuration` exposes these fields plus `actors`, `associations`, and
`annotations` for use cases. Its `safe_text` value is an internal validation
result, not a YAML key. `ViewerCuration` contains `version`, `views`, and
`diagnostics`; `CuratedViews` contains the four named views.

### Selectors And Namespace

A selector is either a qualified-ID string such as `root::COMP-1`, or a mapping
with exactly one of `qualified_id`, `local_id`, `name`, `source_file`, or `tag`.
Mappings may add `system` to scope any mode except `qualified_id`:

```yaml
- root::COMP-1
- local_id: COMP-1
  system: root
- name: Request Service
- source_file: src/service.py
- tag: domain
```

Hierarchy IDs use the `<system>::<local-id>` namespace. `root` identifies the
top model; subsystem slugs identify loaded child models. Name and local-ID
selectors must resolve uniquely. `Selector.resolved_id` is computed by the
loader and is not accepted in YAML.

### Nested Records

A group or tier supports `id`, `label`, `kind`, `parent`, `order`,
`description`, and `members`. Members are selectors; IDs occupy the same
per-view presentation namespace as canonical entities, scenarios, externals,
and actors. `CuratedGroup` stores the resolved grouping.

A scenario supports all group keys plus `goal`, `outcomes`, `requirements`,
`moes`, and `evidence`. `CuratedScenario` represents it. Semantic additions
require evidence.

An external supports `id`, `name`, `kind`, `description`, `inferred`, and
`evidence`. `inferred` must be `true`. `kind` may be `source-system`,
`ai-service`, `telemetry`, `legacy-adapter`, or `external-service`.
`CuratedExternal` represents it.

A flow supports `source`, `target`, `kind`, `label`, `description`, `inferred`,
and `evidence`. A canonical architecture relationship may use its canonical
relationship kind without inference. A noncanonical flow must set `inferred:
true`, include evidence, and use `exchange`, `operational-flow`, or `data-flow`.
`CuratedFlow` represents it.

Each evidence item is an `EvidenceRecord` with exactly `source` and `claim`.
`source` is an existing file inside the project; `claim` is safe presentation
text explaining what that file supports.

### ConOps

ConOps commonly uses `externals`, `scenarios`, and `flows`. Scenario `goal`,
`outcomes`, `requirements`, and `moes` provide evidenced mission semantics.
External and inferred flow `kind` values communicate presentation roles. These
facts are always visibly marked inferred in rendered nodes, edges, and evidence
panels and never become actors, behaviors, or relationships in the canonical
model.

### Functional Architecture

Functional views use `groups` to organize capabilities and `flows` to show
canonical or evidenced inferred functional/data movement. `featured`, `order`,
`preferred_capability_root`, and `drilldowns` control overview emphasis.

### Logical Architecture

Logical views use `tiers` for lanes and `groups` with `kind: aggregate` for
presentation aggregates. Set each aggregate's `parent` to a tier ID and list
its underlying selectors in `members`; `aggregate_components` suppresses those
components as separate overview nodes.

### Use Cases

Use-case `actors` contain `id`, `name`, `inferred`, and `evidence` and map to
`CuratedUseCaseActor`. Added actors must be inferred and evidenced.

`associations` contain `actor`, nonempty `use_cases`, `inferred`, and `evidence`
and map to `CuratedUseCaseAssociation`. The actor is a canonical actor selector
or a curated actor ID; each use case must select a behavior. Associations must
be inferred and evidenced.

`annotations` contain `use_case`, `goal`, `trigger`, `preconditions`,
`postconditions`, `success_outcome`, `moes`, and `evidence` and map to
`CuratedUseCaseAnnotation`. At least one semantic field is required, the target
must be a behavior, and evidence is mandatory.

## Validation And Security

Loading is fail closed. An unsupported root key, version, or view name rejects
the whole profile. An unknown nested key, malformed value, duplicate semantic
record, unresolved required selector, invalid endpoint, or unsafe text rejects
the affected view and emits structured warnings in `diagnostics`; other valid
views remain usable. Ambiguous optional selectors also warn and cannot influence
projection.

Profile and evidence paths are resolved and confined to the repository. Missing
evidence files, absolute escapes, and `..` path traversal are rejected. YAML is
loaded safely. Presentation text rejects script tags, JavaScript URLs, and HTML
event-handler attributes; all remaining labels, claims, navigation content, and
viewer values are escaped before HTML/SVG insertion to prevent XSS. Curation
cannot inject raw HTML, SVG, JavaScript, or canonical architecture entities.

## Output Behavior

Overview projections are deterministic and bounded to at most 25 nodes and 40
edges per panel. Omitted detail remains available through generated drilldowns;
explicit `drilldowns` may choose entry entities. The self-contained viewer
supports back/forward navigation across overviews, drilldowns, entities,
modules, and embedded pipeline history. Comments are stored locally in the
browser and can be imported/exported as YAML. The generated HTML embeds model,
documents, history, scripts, styles, and offline SVG fallbacks; it requires no
network connection. No generated HTML or SVG belongs in source control.

## Minimal Example

```yaml
version: 1
views:
  functional:
    featured: [root::CAP-1]
    labels:
      root::CAP-1: Accept Requests
```

## Full Example

[`examples/viewer-curation.yaml`](../examples/viewer-curation.yaml) exercises
all four view-specific sections against the minimal model fixture at
[`tests/fixtures/viewer-curation-model.yaml`](../tests/fixtures/viewer-curation-model.yaml).
It demonstrates selectors, hierarchy IDs, scenarios, evidence, inferred
externals and flows, functional groups, logical tiers and aggregates, use-case
actors, associations, and annotations.
