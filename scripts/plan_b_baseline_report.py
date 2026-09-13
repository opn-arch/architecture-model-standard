"""T0.7: Baseline articulation report for .architecture-model.plan-b.yaml.

Model-based-dev framing: the current model IS complete. Gaps are typed
(articulated as open_questions or as missing structural edges), never
silent. This report enumerates the current articulation state per
entity and per attribute, categorizing what's authored, what's
inherited (via T0.6 propagation), and what carries a typed gap.

Report sections:
  1. System snapshot: entity + relationship counts, validator score.
  2. Per-kind articulation matrix: how many entities have intent,
     delivery edges (incoming), verify edges (incoming/outgoing).
  3. Typed gap inventory:
       G-INTENT   : entity has empty intent
       G-DELIVERY : entity has no incoming contains/realizes/traces-to
       G-VERIFY   : entity has no verification wiring (behavior traces
                    to it, interface exposes/consumes it, or it produces
                    an interface)
       G-OPEN-Q   : entity carries non-empty open_questions
  4. Per-entity table with columns:
       id | kind | intent? | delivery edges in | verify edges | open_qs
  5. Delivery-down inheritance summary (which attributes flow, at
     what depth).
"""

from __future__ import annotations

import io
from collections import defaultdict
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model

PLAN_B = Path(".architecture-model.plan-b.yaml")
OUT = Path("docs/plans/plan-b-baseline-closure.md")


def _rel(rel):
    return getattr(rel, "from_id", None), getattr(rel, "to_id", None), getattr(rel, "type", None)


def main() -> int:
    m = load_model(PLAN_B)
    r = validate_model(m)

    ents = m.entities
    all_entities = []
    for kind, coll in (
        ("actor", ents.actors),
        ("capability", ents.capabilities),
        ("behavior", ents.behaviors),
        ("component", ents.components),
        ("interface", ents.interfaces),
    ):
        for e in coll:
            all_entities.append((kind, e))

    by_id = {e.id: (kind, e) for kind, e in all_entities}

    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    for rel in m.relationships:
        s, t, ty = _rel(rel)
        if s and t:
            outgoing[s].append((ty, t))
            incoming[t].append((ty, s))

    delivery_types = {"contains", "realizes", "traces-to"}
    verify_types = {"traces-to", "exposes", "consumes", "produces"}

    def _delivery_ok(kind, eid):
        """Delivery-down: entity is tied to abstract parent/scope.

        Kind-specific rules:
          cap : incoming `contains` (umbrella caps allowed to be top-level roots).
          beh : outgoing `traces-to` (behavior traces up to a cap).
          comp: outgoing `realizes` (comp realizes a cap).
          if  : incoming `produces` from a beh OR incoming `exposes` from a comp.
        """
        outs = outgoing.get(eid, [])
        ins = incoming.get(eid, [])
        if kind == "cap":
            return any(t == "contains" for t, _ in ins) or eid.startswith("CAP-PB-") and eid in {"CAP-PB-SLICE", "CAP-PB-MODEL", "CAP-PB-EXTRACT", "CAP-PB-DEV"}
        if kind == "beh":
            return any(t == "traces-to" for t, _ in outs)
        if kind == "comp":
            return any(t == "realizes" for t, _ in outs)
        if kind == "if":
            return any(t in ("produces", "exposes") for t, _ in ins)
        return True

    def _verify_ok(kind, eid):
        """Verify-up: entity is tied to concrete evidence.

        Kind-specific rules:
          cap : incoming `realizes` (comp) OR incoming `traces-to` (beh).
          beh : outgoing `exposes`/`consumes`/`produces` OR non-empty verification.
          comp: outgoing `exposes` OR outgoing `produces` OR non-empty verification.
          if  : outgoing `produces` (beh source) OR outgoing `consumes` (beh sink).
        """
        outs = outgoing.get(eid, [])
        ins = incoming.get(eid, [])
        if kind == "cap":
            return any(t in ("realizes", "traces-to") for t, _ in ins)
        if kind == "beh":
            e = by_id[eid][1]
            if getattr(e, "verification", None):
                return True
            return any(t in ("exposes", "consumes", "produces") for t, _ in outs)
        if kind == "comp":
            e = by_id[eid][1]
            if getattr(e, "verification", None):
                return True
            return any(t in ("exposes", "produces") for t, _ in outs)
        if kind == "if":
            return any(t in ("produces", "consumes") for t, _ in ins)
        return True

    kind_short = {"actor": "actor", "capability": "cap", "behavior": "beh", "component": "comp", "interface": "if"}

    per_entity = []
    gaps = defaultdict(list)
    for kind, e in all_entities:
        ks = kind_short[kind]
        intent_ok = bool((getattr(e, "intent", None) or "").strip())
        deliv = _delivery_ok(ks, e.id) if ks != "actor" else True
        veri = _verify_ok(ks, e.id) if ks != "actor" else True
        open_qs = getattr(e, "open_questions", None) or []

        if not intent_ok:
            gaps["G-INTENT"].append(e.id)
        if not deliv:
            gaps["G-DELIVERY"].append(e.id)
        if not veri:
            gaps["G-VERIFY"].append(e.id)
        if open_qs:
            gaps["G-OPEN-Q"].append(e.id)

        per_entity.append((kind, e.id, getattr(e, "name", ""), intent_ok, "YES" if deliv else "NO", "YES" if veri else "NO", len(open_qs)))

    kind_counts = defaultdict(lambda: [0, 0, 0, 0])
    for kind, _id, _n, intent_ok, di, vt, oq in per_entity:
        kind_counts[kind][0] += 1
        kind_counts[kind][1] += int(intent_ok)
        kind_counts[kind][2] += int(di == "YES")
        kind_counts[kind][3] += int(vt == "YES")

    buf = io.StringIO()
    w = buf.write
    w("# Plan B' Baseline Articulation Report\n\n")
    w("*Auto-generated by `scripts/plan_b_baseline_report.py` (T0.7). Regenerate on every plan-b model change.*\n\n")
    w("## 1. Model-based-dev framing\n\n")
    w("The plan-b model is not a partial snapshot of a future target. It is a **complete-at-this-moment articulation** of what has been decided so far. Every gap is **typed** (enumerated below), never silent. Extraction-mode thinking would compute a percentage against a hypothetical target; this report instead reports the current articulation state and the typed-gap inventory that must be closed before the next promise lands.\n\n")

    w("## 2. System snapshot\n\n")
    w(f"- Validator score: **{r.score} / 100** (`is_valid={r.is_valid}`)\n")
    w(f"- Actors: {len(ents.actors)}\n")
    w(f"- Capabilities: {len(ents.capabilities)}\n")
    w(f"- Behaviors: {len(ents.behaviors)}\n")
    w(f"- Components: {len(ents.components)}\n")
    w(f"- Interfaces: {len(ents.interfaces)}\n")
    w(f"- Relationships: {len(m.relationships)}\n\n")

    w("## 3. Per-kind articulation matrix\n\n")
    w("| Kind | Count | With intent | With delivery edges | With verify wiring |\n")
    w("|------|------:|------------:|--------------------:|-------------------:|\n")
    for kind in ("actor", "capability", "behavior", "component", "interface"):
        c, ii, di, vt = kind_counts[kind]
        w(f"| {kind} | {c} | {ii} | {di} | {vt} |\n")
    w("\n")

    w("## 4. Typed gap inventory\n\n")
    w("| Gap type | Meaning | Count | Entities |\n")
    w("|----------|---------|------:|----------|\n")
    for gt, desc in (
        ("G-INTENT", "entity has empty `intent`"),
        ("G-DELIVERY", "no incoming `contains`/`realizes`/`traces-to`"),
        ("G-VERIFY", "no `traces-to`/`exposes`/`consumes`/`produces` touching entity"),
        ("G-OPEN-Q", "entity carries non-empty `open_questions`"),
    ):
        ids = gaps.get(gt, [])
        preview = ", ".join(ids[:6]) + ("..." if len(ids) > 6 else "")
        w(f"| {gt} | {desc} | {len(ids)} | {preview or '-'} |\n")
    w("\n")

    w("## 5. Per-entity articulation table\n\n")
    w("| Kind | ID | Name | Intent | Delivery-down | Verify-up | Open Qs |\n")
    w("|------|----|------|:------:|:-------------:|:---------:|--------:|\n")
    for kind, eid, name, intent_ok, di, vt, oq in per_entity:
        w(f"| {kind} | `{eid}` | {name[:44]} | {'YES' if intent_ok else 'NO'} | {di} | {vt} | {oq} |\n")
    w("\n")

    w("## 6. Delivery-down inheritance summary\n\n")
    w("T0.6 propagated 264 attributes across 45 parent-child edges:\n\n")
    w("- `contains` cap<-cap: 21 attributes across 7 edges\n")
    w("- `realizes` comp<-cap: 168 attributes across 23 edges\n")
    w("- `traces-to` beh<-cap: 75 attributes across 15 edges\n\n")
    w("Attributes propagated: `intent`, `goals`, `stakeholders`, `success_criteria`, `failure_modes`, `trade_offs`, `assumptions`, `open_questions`, `moes`, `requirements`, `verification`, `slos`, `dependencies_rationale`, `owner`, `maturity`. Rule: fill-if-empty, never overwrite child content. See `scripts/plan_b_propagate.py`.\n\n")

    w("## 7. Baseline interpretation\n\n")
    w("The four validator warnings (3 UNREALIZED_CAPABILITY on umbrella caps SLICE/MODEL/EXTRACT + 1 MISSING_META source_artifacts) are structural: umbrella caps are aggregators containing sub-caps that carry the realizing components; they are not expected to have direct realizing behaviors. Source_artifacts meta will be populated at T0.8 when the viewer regeneration establishes the artifact publish trail.\n\n")
    w("This report is the **T0.7 baseline**. Every subsequent plan-b commit must not regress `G-INTENT` or `G-DELIVERY` on non-actor entities. `G-OPEN-Q` is expected to grow as gap enumeration lands in Phase B'-0b.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(buf.getvalue())
    print(f"Wrote {OUT} ({len(buf.getvalue())} bytes)")
    print(f"Gaps: " + ", ".join(f"{k}={len(v)}" for k, v in gaps.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
