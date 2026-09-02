# Final Executive View Review Design

## Architecture

Keep semantic fixes in curation/projectors and geometry/theme fixes in the renderer. No canonical model mutation and no logs-db profile edit occur. Unknown external roles remain separate until profiles add explicit allowlisted kinds.

## ConOps

`CuratedExternal.kind` accepts only `source-system`, `ai-service`, `telemetry`, `legacy-adapter`, or `external-service`; omission is valid and conservative. Bundling keys include explicit role, target, and flow kind, while each omitted role receives a unique key. Explicit scenario outcomes are primary; canonical postconditions supplement without replacing them. Goals and MoEs remain scenario metadata. Every scenario with outcomes connects to the shared outcomes aggregate, whose drilldown maps scenario nodes to outcome children. The boundary contains only systems reached through scenario members, behavior component ownership, or member interface endpoints.

## Use Cases

The catalog layout places actors in a dedicated left column and use cases in bounded right columns. Actor memberships determine stable barycentric ordering, with multi-actor cases centered between memberships and single-actor cases kept contiguous. Participation edges use one vertical bus per actor and horizontal branches to cases, avoiding edge-edge, node, and label crossings.

## Theme

`DiagramRenderOptions.theme` is `light` by default and validates `light|dark`. SVG embeds an opaque palette background and fixed colors, independent of host media queries. `DiagramPanel.theme` serializes the chosen value and propagates it to drilldowns. Tests calculate WCAG contrast and optionally inspect rendered PNG pixels with librsvg.

## Logical

Canonical isolates retain drilldowns and receive `No cross-system dependency`. Backbone routing is adjusted only where deterministic local tracks can reduce crossings without changing selected edges.

## Testing

Each behavior begins with a failing focused test, followed by minimal implementation and regression runs. Final optional logs-db geometry requires ConOps connected outcomes and exact six participants, Functional zero crossings, Logical at most one, and Use Cases zero, all within `1800x1200`.
