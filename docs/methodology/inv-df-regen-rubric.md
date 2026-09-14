# INV-DF-REGEN — Regenerability Scoring Rubric

**Owning capability:** CAP-DF-GATING (Approval and Regenerability-Gated Autonomy)
**Established:** T0.14.0.5.3 (2026-09-14)
**Applies to:** every Plan-B commit adding one or more entities to `.architecture-model.plan-b.yaml`

## Purpose

Make the "how much autonomy does the assistant retain?" question objective, per-entity, and auditable. The rubric replaces subjective self-assessment with three concrete checks that can be applied by inspection.

The invariant name **INV-DF-REGEN** reflects the underlying question: *can this entity be regenerated (or replaced with an equivalent) from the model + associated source alone, or does regeneration require reading tacit knowledge from the conversation that produced it?*

## Scoring

A commit's regen score is the **minimum score across all entities added or materially modified in that commit.** One MEDIUM entity drops the whole commit to MEDIUM.

### HIGH — autonomous continuation permitted

All three of the following:

1. **Source anchor** — entity has `source_paths:` pointing to a file that exists **OR** a structured `verification:` block with ≥1 verification record having `id`, `method`, `target`.
2. **Relationship anchor** — entity has ≥1 outbound relationship of type `realizes`, `contains`, `produces`, `depends-on`, or `traces-to` linking it into the existing graph.
3. **Provenance anchor** — entity's origin is traceable to one of: (a) a specific conversation turn cited in commit message; (b) an upstream SIO or T-task; (c) a prior walk-instance finding; (d) a plan document under `docs/plans/`.

**Assistant behavior:** continue to the next task without user approval, subject to named gate boundaries (T-task phase boundaries) which are always user-only regardless of score.

### MEDIUM — stop, consult user

Any two of three (missing one anchor):

- Has intent + one anchor + one relationship, but lacks either verification or provenance
- Has source_paths pointing to a file that does not yet exist (planned but not written)
- Has verification block but with only prose targets (no `method:` field)

**Assistant behavior:** stop after the commit lands. Report the missing anchor to user with a proposed remedy. Await explicit direction before continuing.

### LOW — stop, consult user, likely revert

Any single anchor or none:

- Has intent only; no relationships; no verification
- Relationships exist but reference undefined entities (broken graph)
- Verification records lack targets or targets are non-checkable ("looks reasonable")

**Assistant behavior:** stop immediately. Treat the commit as tentative. Propose either strengthening the entity to MEDIUM/HIGH or reverting and re-approaching.

## Commit-message tally format

Every Plan-B commit MUST include a `regen:` line in the trailer:

```
regen: <HIGH|MED|LOW> (<N> entities)
```

Or for combined-unit commits:

```
regen: HIGH (2 entities, coherent unit)
```

Or for doc-only / journal-only commits (no entities changed):

```
regen: HIGH (0 entities, doc-only)
regen: HIGH (0 entities, journal-only)
```

VER-DF-GATING-1 (`Every commit message contains 'regen: HIGH|MED|LOW (N entities)' line`) is satisfied by grep on the git log.

## Applying the rubric — worked example

**Entity: COMP-DF-BASELINE** (T0.14.0.1)

| Check | Evidence | Pass? |
|---|---|---|
| Source anchor | `source_paths: [scripts/plan_b_baseline_report.py]` — file exists (216 lines) | ✅ |
| Relationship anchor | `COMP-DF-BASELINE realizes CAP-DF-VERIFY` | ✅ |
| Provenance anchor | T0.14 plan doc (`docs/plans/2026-09-14-t0.14-v3-bootstrap.md`) references this entity | ✅ |

**Score:** HIGH. Continue autonomously.

## Edge cases

- **Zero-entity commits** (docs, journals, rubric-only): score HIGH by default, note `(0 entities, doc-only)`. Cannot be MEDIUM/LOW because no entities to check.
- **Renames without semantic change:** score HIGH; note `(rename)`.
- **Deletions:** score by the *replacement* entity if any, else HIGH with `(deletion)` note.
- **Batched growth (>3 entities in one commit):** automatically MEDIUM even if each individual entity scores HIGH — batching defeats per-entity granularity per VER-DF-EVOLVE (`Growth spurt (many entities in one commit) obscures per-entity regen-check`). The 2-entity coherent-unit exception (as in T0.14.0.5.1+2) requires explicit "coherent unit" justification in the commit body.

## Rationale for these three anchors specifically

- **Source anchor** ensures the entity has code or verification pinning it to reality. Without this, the entity is aspirational.
- **Relationship anchor** ensures the entity is not orphaned in the graph. An orphan cannot be reached by chain-closure verification and thus cannot participate in CAP-DF-VERIFY's guarantee.
- **Provenance anchor** ensures the entity's *reason for existing* is captured somewhere outside the entity itself, so future maintainers (human or LLM) can trace back to intent.

These three together approximate the SysML requirement-to-verification-to-source traceability triple. They are not novel; the rubric just makes them mandatory and machine-checkable for Plan-B commits.

## Open questions

- Should the rubric become an executable check (lint on commit message + YAML diff) rather than a manual assessment? Currently manual; VER-DF-GATING-2 targets a validator lint but not yet built.
- Should MEDIUM commits be blocked from merge, or merged-with-annotation? Currently: MEDIUM = stop-and-consult, user decides.
- Should the rubric apply to non-Plan-B commits (mainline AMS work)? Currently: Plan-B only. Extending post-T0.14.
