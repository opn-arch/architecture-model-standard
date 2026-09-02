# Native Diagram Renderer Design

## Architecture

The renderer is a pure `core` module that validates a `DiagramSpec`, computes a deterministic layered layout, and serializes safe SVG with only the Python standard library. It does not invoke Mermaid, load external assets, emit scripts, or assemble HTML.

`render_diagram_svg()` returns standalone SVG. `render_diagram_panel()` returns a frozen value object containing the SVG, toolbar action metadata, dimensions, viewBox, and warnings with JSON-safe serialization. A drilldown helper returns panels keyed by drilldown ID without relying on positional association.

## Layout And Rendering

Nodes and containers are sorted by stable semantic keys before layout. A deterministic graph rank pass supports LR and TB orientations; container membership and semantic tiers influence rank and placement. Fixed minimum gaps, measured wrapped text, expanded group boundaries, and offset orthogonal paths prevent overlap and distinguish parallel edges.

SVG primitives encode semantic node shapes and relationship styles. Classes and `data-*` attributes retain kind, status, inferred state, entity references, and drilldown references. Legends, callouts, diagnostics, and provenance occupy bounded footer regions.

## Safety And Interaction

All text and attribute values pass through XML escaping. Labels, subtitles, and badges are wrapped and clamped before serialization. Clickable nodes receive `role="button"`, `tabindex="0"`, and keyboard-action metadata, but no event attributes or inline JavaScript are emitted. Curation values are represented only as escaped text and known renderer-selected SVG primitives.

## Testing

Tests parse generated SVG with `xml.etree.ElementTree` and assert structural counts, shape/style semantics, non-overlapping node boxes, distinct edge paths, deterministic output under shuffled inputs, hostile text safety, interaction metadata, bounded dimensions, responsive viewBox metadata, diagnostics/footer content, and exact nested drilldown keys. Focused tests are written and observed failing before implementation, then the prescribed full suite is run.
