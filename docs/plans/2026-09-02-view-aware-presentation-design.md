# View-Aware Presentation Design

## Goal

Make curated ConOps, functional, logical, and use-case diagrams readable and semantically correct in the native SVG renderer without project-specific rules.

## Architecture

Projectors remain responsible for semantic selection, evidence-backed relationships, aggregation, and omission policy. `DiagramSpec.layout` selects one of four deterministic renderer policies: `operational-lanes`, `functional-flow`, `logical-tiers`, or `use-case-catalog`; unknown layouts retain the generic flowchart fallback.

The renderer owns node placement, lane geometry, orthogonal routing, compact display labels, and collision avoidance. Full edge labels remain available in SVG titles when visible text is compacted.

## View Policies

- ConOps uses left-to-right actor, scenario, boundary, and outcome lanes. Curated scenario membership may create a scenario-to-boundary delivery edge only when system membership or mapped evidence supports it.
- Functional architecture uses compact layered ranks and local routing tracks rather than a global edge-label band.
- Logical architecture defaults to five tier lanes, excludes unrelated actors and primary omission-summary nodes in explicit curation, aggregates dependency labels, and separates reciprocal paths. Hiding dependencies leaves a clean tier map.
- Featured use cases retain all explicitly featured nodes and represent omissions as a footer callout unless curation explicitly requests an omission drilldown.

## Testing

Strict TDD adds projector assertions before implementation, then renderer geometry assertions before each layout implementation. Integration tests parse actual rendered SVG geometry, optionally convert it with `rsvg-convert`, and retain a PNG review harness for the logs-db fixture when available.
