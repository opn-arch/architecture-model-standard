# Executive Architecture Backbones Design

## Goal

Produce compact, evidence-backed curated ConOps and logical executive views whose overview geometry is readable while every omitted semantic detail remains available through drilldowns, facets, titles, and provenance.

## Curation Schema

Curated scenarios become a dedicated typed record rather than generic groups. A scenario retains its ID, label, order, kind, parent, and resolved members, and may add `goal`, `outcomes`, `requirements`, and `moes`. Every scenario with any nonempty presentation annotation must carry nonempty structured evidence whose source resolves to a file inside the repository. Unknown keys, malformed string lists, unsafe text, duplicate IDs, unresolved members, missing evidence, or escaping evidence paths invalidate only that view. Curation remains presentation-only and never mutates canonical entities.

## Curated ConOps

The projector uses canonical behavior goals and postconditions first, then evidence-backed scenario annotations only when canonical values are absent. Inferred values are marked on nodes and retained with their evidence and provenance. One shared `Operational Outcomes` overview node contains badges for total and scenario counts; its drilldown lists outcomes grouped by scenario and preserves whether each value is canonical or inferred.

External nodes are grouped only when their curated flows converge on the same scenario and compatible kind. Deterministic semantic naming recognizes source-like externals as `Knowledge Sources` and AI-like externals as `AI Services`; otherwise a stable generic label is used. Each aggregate drilldown contains every original external with evidence. Scenario participation combines direct system members with systems owning member behavior components. More than three systems become one connected `Operational System Boundary`; its drilldown lists all participating systems. Every participating scenario connects to the boundary with canonical/member provenance.

## Logical Backbone

Explicit curated logical mode computes all canonical aggregated system/aggregate dependency and interface edges, then selects at most nine overview edges. Selection is deterministic: explicit cross-system interface/exchange edges, adjacent-tier edges, aggregate count, criticality, cycle representation, and connectivity gain determine priority. A maximum-spanning forest connects every canonically connectable displayed node before a small number of critical or cycle extras are admitted. Reciprocal dependencies collapse to one paired cycle edge in the overview while both directions remain in system drilldowns and a hidden full-dependency facet.

`DiagramSpec` gains JSON-safe facet metadata. Logical overview provenance and a callout report displayed and full edge counts. Relevant system/aggregate drilldowns receive the complete edges touching their members. Truly disconnected nodes receive an isolated badge rather than fabricated links.

## Renderer

Lane members use deterministic adjacent-rank median/barycentric sweeps before placement. Operational routes use shared buses for convergent source flows, monotonic tracks for scenario chains, and shared boundary trunks. Logical paths use lane-local tracks selected to minimize intersections and labels remain near unique source segments. The standalone SVG stays transparent but sets explicit theme-safe foreground variables and contrasting text/label halos so footer and source text remain readable on white and dark hosts.

## Verification

Strict TDD adds failing tests before each implementation slice. Tests cover schema fail-closed behavior, curated ConOps counts and semantic preservation, a shuffled 19-edge logical fixture with deterministic connectivity and cycle handling, serialization of hidden full dependency facets, geometry edge-edge and edge-label crossing analysis, `1800x1200` bounds, and optional `rsvg-convert`. Focused tests run after each slice; the repository-required full command runs before commit. The logs-db profile is read only by optional integration tests and is not edited.
