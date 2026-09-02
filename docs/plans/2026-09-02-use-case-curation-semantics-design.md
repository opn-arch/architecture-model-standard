# Use-Case Curation Semantics Design

## Goal

Project all explicitly featured use cases and allow repository-evidenced, presentation-only actor participation and behavior annotations without modifying canonical architecture models.

## Curation Schema

The `use_cases` view alone accepts three new keys:

- `actors`: inferred presentation actors with unique `id`, safe `name`, `inferred: true`, and nonempty repository-file `evidence`.
- `associations`: evidence-backed inferred participation records. `actor` is either a presentation actor ID or a canonical actor selector; `use_cases` is a nonempty list of behavior selectors; `inferred` must be true.
- `annotations`: records keyed by a behavior selector with optional `goal`, `trigger`, `preconditions`, `postconditions`, `success_outcome`, and `moes`, plus required repository-file evidence.

Unknown keys, unresolved or wrong-type selectors, duplicate IDs, unsafe text, absent evidence, and evidence paths outside or missing from the repository fail the entire use-case view closed. These keys are rejected for other views.

## Projection

All visible valid featured behaviors are selected first in curation order, even when there are more than nine. Nonfeatured behaviors fill only remaining case capacity by actor round-robin. Actor and external nodes use the remaining global 15-node budget and never replace featured cases; omitted summaries cover only nonfeatured unselected behaviors and appear only when capacity remains.

Canonical actor, trigger, goals, preconditions, postconditions, and MoEs take precedence. Curated annotations fill only absent canonical fields and carry inferred badges and repository evidence provenance. Inferred associations create dashed `participates` edges and never canonical relationships. Structured steps and lanes remain canonical; high-level failure display remains count-only.

## Verification

Unit tests cover strict parsing, fail-closed validation, canonical precedence, nonmutation, inferred provenance, all-featured budgeting, actor participation, honest canonical links, and drilldowns. A compatibility test loads the actual logs-db profile unchanged, verifies all ten current featured selectors render, and validates a temporary augmented copy using the proposed schema.
