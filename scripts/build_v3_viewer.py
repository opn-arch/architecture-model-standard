"""build_v3_viewer — v3-native single-file HTML viewer builder.

Merges the pipeline-generated v3 model (default
``.architecture-model.v3.yaml``) with all hand-authored fragments under
``.architecture/model/*.v3.yaml`` into a single unified payload and
emits ``.architecture/viewers/v3_viewer.html`` — a self-contained HTML
viewer.

Model-first: the viewer subsystem is itself modeled in
``.architecture/model/viewer.v3.yaml`` as ``COMP-VIEWER``.

Satisfied promises (see viewer.v3.yaml):

- D1 overview_landing — landing screen with totals + histograms
- D3 entity_detail_with_promises — promises grouped by attribute
- D4 gap_index_view — flat gap table grouped by gap_type
- D6 inbound_outbound_neighbors_inline — chips inside detail card
- D8 per_entity_notes_save — textarea per entity + Save downloads
  ``notes.yaml`` (option A: browser download, user places manually)
- D9 multi_entity_kind_sidebar — sidebar groups per entity kind
- D10 authored_fragment_merge — merges pipeline + authored fragments;
  same entity id across sources triggers promise-level union (C4);
  kind collisions and conflicting promise content are hard-fails
- P1 single_file_html, P2 offline_deterministic, P3 repo_agnostic

Unrealized-entity detection: any authored capability/behavior with no
outbound ``realizes``/``traces-to`` edge is surfaced under Typed Gaps
with ``gap_type: unrealized`` (dogfooding).

Usage::

    python scripts/build_v3_viewer.py [model_path]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = REPO / ".architecture-model.v3.yaml"
FRAGMENT_DIR = REPO / ".architecture" / "model"
NOTES_PATH = REPO / ".architecture" / "viewers" / "notes.yaml"
OUT_DIR = REPO / ".architecture" / "viewers"
OUT_HTML = OUT_DIR / "v3_viewer.html"
OUT_JSON = OUT_DIR / "v3_viewer_data.json"

# Canonical entity kinds (v3 + schema-compatible extras used by authored fragments).
ENTITY_KINDS = [
    "components",
    "capabilities",
    "behaviors",
    "interfaces",
    "actors",
    "constraints",
    "layers",
]


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _load_sources(model_path: Path) -> list[tuple[str, dict]]:
    """Return [(source_label, doc), ...] pipeline model + all authored fragments."""
    sources: list[tuple[str, dict]] = []
    if model_path.exists():
        sources.append((str(model_path.relative_to(REPO)), _load_yaml(model_path)))
    if FRAGMENT_DIR.exists():
        for frag in sorted(FRAGMENT_DIR.glob("*.v3.yaml")):
            sources.append((str(frag.relative_to(REPO)), _load_yaml(frag)))
    return sources


def _merge_sources(sources: list[tuple[str, dict]]) -> tuple[dict, dict, list, list]:
    """Merge sources → (meta, entities_by_kind, relationships, source_index).

    entities_by_kind: {kind: {id: entity}}
    source_index: [{"id": ..., "source": ..., "kind": ...}] — first source wins
      for the "source" tag; enrichment sources are recorded on collision but
      not shown as primary.
    Merge policy (as of C4, replaces prior hard-fail):
      - Same entity id declared in multiple sources: promise-level union.
        Promises are keyed by promise.id. Same promise.id across sources
        must have identical content (hard-fail otherwise, exit 3).
      - Same entity id across DIFFERENT kinds is a hard-fail.
      - Relationship dedup by (from, to, type) tuple.
    """
    meta: dict = {}
    entities_by_kind: dict[str, dict] = {k: {} for k in ENTITY_KINDS}
    id_kind: dict[str, str] = {}  # id -> kind (kind-collision guard)
    id_source: dict[str, str] = {}  # id -> primary source (first declarer)
    source_index: list[dict] = []
    relationships: list[dict] = []
    rel_seen: set[tuple[str, str, str]] = set()

    for label, doc in sources:
        # First source's meta wins; later sources contribute nothing to meta.
        if not meta and doc.get("meta"):
            meta = dict(doc["meta"])
        for kind in ENTITY_KINDS:
            for ent in doc.get("entities", {}).get(kind, []) or []:
                eid = ent.get("id")
                if not eid:
                    continue
                # Kind-collision guard: same id across different kinds is fatal.
                if eid in id_kind and id_kind[eid] != kind:
                    print(
                        f"error: id {eid!r} declared as {id_kind[eid]!r} in "
                        f"{id_source[eid]!r} and as {kind!r} in {label!r}",
                        file=sys.stderr,
                    )
                    sys.exit(3)
                if eid not in id_kind:
                    # First declaration: keep entity as-is.
                    id_kind[eid] = kind
                    id_source[eid] = label
                    entities_by_kind[kind][eid] = dict(ent)
                    source_index.append(
                        {"id": eid, "source": label, "kind": kind}
                    )
                else:
                    # Enrichment: union promises by id, hard-fail on conflict.
                    existing = entities_by_kind[kind][eid]
                    existing_promises = existing.get("promises", []) or []
                    new_promises = ent.get("promises", []) or []
                    by_pid = {p.get("id"): p for p in existing_promises}
                    for p in new_promises:
                        pid = p.get("id")
                        if not pid:
                            continue
                        if pid in by_pid:
                            # Same promise id: content must match exactly.
                            a, b = by_pid[pid], p
                            if (
                                a.get("attribute") != b.get("attribute")
                                or a.get("content") != b.get("content")
                                or a.get("owner_entity") != b.get("owner_entity")
                            ):
                                print(
                                    f"error: promise id {pid!r} on entity "
                                    f"{eid!r} has conflicting content between "
                                    f"{id_source[eid]!r} and {label!r}",
                                    file=sys.stderr,
                                )
                                sys.exit(3)
                            # Identical: silently accept.
                        else:
                            by_pid[pid] = p
                    # Rebuild promises list in deterministic pid order.
                    existing["promises"] = [by_pid[k] for k in sorted(by_pid)]
                    # Enrichment sources do NOT override name / root_prefix /
                    # module_names — pipeline stays authoritative on those.
                    source_index.append(
                        {"id": eid, "source": label, "kind": kind}
                    )
        for rel in doc.get("relationships", []) or []:
            key = (rel.get("from"), rel.get("to"), rel.get("type", "depends-on"))
            if key in rel_seen:
                continue
            rel_seen.add(key)
            relationships.append(rel)

    return meta, entities_by_kind, relationships, source_index


def _kind_singular(kind: str) -> str:
    if kind.endswith("ies"):
        return kind[:-3] + "y"
    if kind.endswith("s"):
        return kind[:-1]
    return kind


# ---------------------------------------------------------------------------
# SE Views — deterministic Mermaid generation from merged payload.
# ---------------------------------------------------------------------------

# Narrative text is version-controlled here (not derived from model) so the
# viewer surfaces a stable authorial voice. Update in lockstep with walks.
SE_VIEW_NARRATIVES = {
    "conops": (
        "Concept of Operations for the AMS dev workflow. Four actors "
        "(developer, SE, CI, and the Part-3 LLM) drive the three top-level "
        "capabilities. The developer + SE run the day-to-day loop "
        "(view \u2192 note \u2192 walk/author \u2192 validate \u2192 re-extract). "
        "CI enforces byte-determinism on every push. The LLM is declared "
        "as future actor for CAP-DF.4 (Part 3, not yet realized)."
    ),
    "functional": (
        "Functional analysis \u2014 top-down capability tree derived from the "
        "merged model. CAP-PB (extract) contains the 8 pipeline behaviors; "
        "CAP-SL (slice) exposes IF-slicer; CAP-DF (evolve) contains four "
        "sub-capabilities: walk, view, validate, and LLM seams. Behaviors "
        "hang off their owning sub-capability; interfaces are leaves. "
        "Constraint edges (constrained-by) surface non-functional "
        "requirements at the capability level."
    ),
    "logical": (
        "Logical architecture \u2014 layer\u2192component allocation and "
        "layer\u2192layer dependency graph. Five layers separate concerns: "
        "L-standard (schema + core), L-tooling (pipeline_v3), L-view "
        "(viewer + build), L-authoring (fragment YAMLs), L-llm (Part 3). "
        "Each layer subgraphs its owned components; edges between layers "
        "show depends-on / consumes / produces relationships."
    ),
    "use_cases": (
        "Use cases \u2014 actor\u2192behavior triggers grouped per actor. "
        "Each actor's behaviors are the concrete operations they perform. "
        "ACT-llm behaviors (BEH-S1, BEH-S2) are declared open (Part 3). "
        "ACT-developer and ACT-se share BEH-view-browse (both open the "
        "viewer to review the model)."
    ),
}


def _mid(entity_id: str) -> str:
    """Sanitize entity id for Mermaid node id (alnum only, letter-prefixed)."""
    return "n" + "".join(c for c in entity_id if c.isalnum())


def _mesc(label: str) -> str:
    """Escape a Mermaid quoted label."""
    return label.replace('"', "'").replace("\n", " ").strip()


def _mermaid_conops(
    entities_by_kind: dict, relationships: list
) -> tuple[str, list[str]]:
    """Actors on left, top-level capabilities on right; triggers edges between."""
    actors = sorted(entities_by_kind["actors"].keys())
    caps = sorted(entities_by_kind["capabilities"].keys())
    lines = ["flowchart LR"]
    if actors:
        lines.append('  subgraph ACTORS["Actors"]')
        for aid in actors:
            name = entities_by_kind["actors"][aid].get("name", aid)
            lines.append(f'    {_mid(aid)}["{_mesc(aid)}<br/>{_mesc(name)}"]')
        lines.append("  end")
    if caps:
        lines.append('  subgraph CAPS["Capabilities"]')
        for cid in caps:
            name = entities_by_kind["capabilities"][cid].get("name", cid)
            lines.append(f'    {_mid(cid)}["{_mesc(cid)}<br/>{_mesc(name)}"]')
        lines.append("  end")
    # Actor -> Behavior/Capability edges (from actors only).
    refs: set[str] = set(actors) | set(caps)
    edges: list[tuple[str, str, str]] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f in actors and rt == "triggers":
            # Follow behavior -> capability via contains reverse-lookup.
            # If t is a capability, edge directly; else find containing cap.
            if t in caps:
                edges.append((f, t, "triggers"))
                refs.add(t)
            else:
                # Find capability containing t.
                for rr in relationships:
                    if rr.get("to") == t and rr.get("type") == "contains":
                        cap = rr.get("from")
                        if cap in caps:
                            edges.append((f, cap, f"triggers ({t})"))
                            refs.add(cap)
                            break
    edges = sorted(set(edges))
    for f, t, lbl in edges:
        lines.append(f"  {_mid(f)} -->|{_mesc(lbl)}| {_mid(t)}")
    return "\n".join(lines), sorted(refs)


def _mermaid_functional(
    entities_by_kind: dict, relationships: list
) -> tuple[str, list[str]]:
    """Capability tree: CAP-* → sub-caps → behaviors + interfaces."""
    caps = entities_by_kind["capabilities"]
    behs = entities_by_kind["behaviors"]
    ifaces = entities_by_kind["interfaces"]
    cons = entities_by_kind["constraints"]
    lines = ["flowchart TD"]
    refs: set[str] = set()
    for cid in sorted(caps):
        name = caps[cid].get("name", cid)
        lines.append(f'  {_mid(cid)}["{_mesc(cid)}<br/>{_mesc(name)}"]')
        refs.add(cid)
    for bid in sorted(behs):
        name = behs[bid].get("name", bid)
        lines.append(f'  {_mid(bid)}(["{_mesc(bid)}<br/>{_mesc(name)}"])')
    for iid in sorted(ifaces):
        name = ifaces[iid].get("name", iid)
        lines.append(f'  {_mid(iid)}[/"{_mesc(iid)}<br/>{_mesc(name)}"/]')
    for kid in sorted(cons):
        name = cons[kid].get("name", kid)
        lines.append(f'  {_mid(kid)}{{{{"{_mesc(kid)}<br/>{_mesc(name)}"}}}}')
    edges: list[tuple[str, str, str]] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f in caps and rt == "contains" and (t in caps or t in behs):
            edges.append((f, t, "contains"))
            refs.add(t)
        elif f in caps and rt == "exposes" and t in ifaces:
            edges.append((f, t, "exposes"))
            refs.add(t)
        elif f in caps and rt == "constrained-by" and t in cons:
            edges.append((f, t, "constrained-by"))
            refs.add(t)
        elif f in caps and rt == "realizes":
            # Skip capability -> component realizes edges here; those belong
            # to logical view.
            pass
    edges = sorted(set(edges))
    for f, t, rt in edges:
        arrow = "-.->|constrained by|" if rt == "constrained-by" else (
            "==>|exposes|" if rt == "exposes" else "-->"
        )
        lines.append(f"  {_mid(f)} {arrow} {_mid(t)}")
    return "\n".join(lines), sorted(refs)


def _mermaid_logical(
    entities_by_kind: dict, relationships: list
) -> tuple[str, list[str]]:
    """Layer subgraphs with contained components; layer→layer dep edges."""
    layers = entities_by_kind["layers"]
    comps = entities_by_kind["components"]
    lines = ["flowchart TD"]
    refs: set[str] = set()
    # For each layer, subgraph with contained components.
    layer_comps: dict[str, list[str]] = {lid: [] for lid in layers}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f in layers and rt == "contains" and t in comps:
            layer_comps[f].append(t)
    orphan_comps: list[str] = []
    contained_ids: set[str] = set()
    for lid, cs in layer_comps.items():
        for c in cs:
            contained_ids.add(c)
    for cid in comps:
        if cid not in contained_ids:
            orphan_comps.append(cid)
    for lid in sorted(layers):
        name = layers[lid].get("name", lid)
        cs = sorted(layer_comps.get(lid, []))
        lines.append(f'  subgraph {_mid(lid)}["{_mesc(lid)}: {_mesc(name)}"]')
        if cs:
            for cid in cs:
                cname = comps[cid].get("name", cid)
                lines.append(
                    f'    {_mid(cid)}["{_mesc(cid)}<br/>{_mesc(cname)}"]'
                )
                refs.add(cid)
        else:
            # Empty layer placeholder for visual completeness.
            lines.append(f'    {_mid(lid)}_empty([empty])')
        lines.append("  end")
        refs.add(lid)
    # Layer→layer edges.
    edges: list[tuple[str, str, str]] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f in layers and t in layers and rt in (
            "depends-on",
            "consumes",
            "produces",
        ):
            edges.append((f, t, rt))
    edges = sorted(set(edges))
    for f, t, rt in edges:
        arrow = "-.->|produces|" if rt == "produces" else (
            "==>|consumes|" if rt == "consumes" else "-->|depends on|"
        )
        lines.append(f"  {_mid(f)} {arrow} {_mid(t)}")
    return "\n".join(lines), sorted(refs)


def _mermaid_use_cases(
    entities_by_kind: dict, relationships: list
) -> tuple[str, list[str]]:
    """Actor→Behavior triggers, grouped per actor."""
    actors = entities_by_kind["actors"]
    behs = entities_by_kind["behaviors"]
    lines = ["flowchart LR"]
    refs: set[str] = set()
    # Collect triggered behaviors per actor.
    per_actor: dict[str, list[str]] = {aid: [] for aid in sorted(actors)}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f in actors and rt == "triggers" and t in behs:
            per_actor.setdefault(f, []).append(t)
    for aid in sorted(actors):
        name = actors[aid].get("name", aid)
        lines.append(f'  {_mid(aid)}(("{_mesc(aid)}<br/>{_mesc(name)}"))')
        refs.add(aid)
    # Group behaviors in a single subgraph, deduplicated + sorted.
    used_behs = sorted({b for bs in per_actor.values() for b in bs})
    if used_behs:
        lines.append('  subgraph USE_CASES["Use Cases (Behaviors)"]')
        for bid in used_behs:
            name = behs[bid].get("name", bid)
            lines.append(
                f'    {_mid(bid)}["{_mesc(bid)}<br/>{_mesc(name)}"]'
            )
            refs.add(bid)
        lines.append("  end")
    # Edges.
    edges: list[tuple[str, str]] = []
    for aid, bs in per_actor.items():
        for b in bs:
            edges.append((aid, b))
    for f, t in sorted(set(edges)):
        lines.append(f"  {_mid(f)} --> {_mid(t)}")
    return "\n".join(lines), sorted(refs)


def _build_se_views(entities_by_kind: dict, relationships: list) -> dict:
    """Return {view_id: {title, narrative, mermaid, entity_refs}} deterministically."""
    views = {
        "conops": ("Concept of Operations", _mermaid_conops),
        "functional": ("Functional Analysis", _mermaid_functional),
        "logical": ("Logical Architecture", _mermaid_logical),
        "use_cases": ("Use Cases", _mermaid_use_cases),
    }
    out: dict = {}
    for vid, (title, fn) in views.items():
        mmd, refs = fn(entities_by_kind, relationships)
        out[vid] = {
            "title": title,
            "narrative": SE_VIEW_NARRATIVES[vid],
            "mermaid": mmd,
            "entity_refs": refs,
        }
    return out


def _build_payload(model_path: Path) -> dict:
    sources = _load_sources(model_path)
    meta, entities_by_kind, relationships, source_index = _merge_sources(sources)
    source_by_id = {rec["id"]: rec["source"] for rec in source_index}

    # Neighbor + realizes maps (id-agnostic across kinds).
    out_edges: dict[str, list[tuple[str, str]]] = {}  # id -> [(target, rel_type)]
    in_edges: dict[str, list[tuple[str, str]]] = {}  # id -> [(source, rel_type)]
    for kind in ENTITY_KINDS:
        for eid in entities_by_kind[kind]:
            out_edges.setdefault(eid, [])
            in_edges.setdefault(eid, [])
    for r in relationships:
        f, t = r.get("from"), r.get("to")
        rt = r.get("type", "depends-on")
        if f is None or t is None:
            continue
        out_edges.setdefault(f, []).append((t, rt))
        in_edges.setdefault(t, []).append((f, rt))

    # Unrealized detection for authored capabilities and behaviors.
    unrealized_gaps: list[dict] = []
    for kind in ("capabilities", "behaviors"):
        for eid, ent in entities_by_kind[kind].items():
            src = source_by_id.get(eid, "")
            if src.endswith(".architecture-model.v3.yaml"):
                # Pipeline output doesn't emit these today; skip if it ever does.
                continue
            outs = out_edges.get(eid, [])
            has_realize = any(
                rt in ("realizes", "traces-to", "contains") for _, rt in outs
            )
            if not has_realize:
                unrealized_gaps.append(
                    {
                        "owner": eid,
                        "owner_name": ent.get("name", eid),
                        "owner_kind": _kind_singular(kind),
                        "promise_id": "-",
                        "attribute": "-",
                        "gap_type": "unrealized",
                        "content": [
                            f"authored {_kind_singular(kind)} without realizes/traces-to edge"
                        ],
                    }
                )

    # Aggregate promise stats + entity records.
    status_hist: dict[str, int] = {"verified": 0, "open": 0, "typed-gap": 0}
    gap_type_hist: dict[str, int] = {}
    gap_flat: list[dict] = []

    entity_records: dict[str, dict] = {}  # kind -> list

    for kind in ENTITY_KINDS:
        recs = []
        for eid, ent in sorted(entities_by_kind[kind].items()):
            promises = ent.get("promises", []) or []
            by_attr: dict[str, list[dict]] = {}
            gap_count = 0
            for p in promises:
                attr = p.get("attribute", "other")
                status = p.get("status", "open")
                gtype = p.get("gap_type")
                by_attr.setdefault(attr, []).append(
                    {
                        "id": p.get("id", ""),
                        "content": p.get("content", []),
                        "status": status,
                        "gap_type": gtype,
                        "provenance": p.get("provenance", ""),
                    }
                )
                status_hist[status] = status_hist.get(status, 0) + 1
                if status == "typed-gap":
                    gap_count += 1
                if gtype:
                    gap_type_hist[gtype] = gap_type_hist.get(gtype, 0) + 1
                    gap_flat.append(
                        {
                            "owner": eid,
                            "owner_name": ent.get("name", eid),
                            "owner_kind": _kind_singular(kind),
                            "promise_id": p.get("id", ""),
                            "attribute": attr,
                            "gap_type": gtype,
                            "content": p.get("content", []),
                        }
                    )
            outs_typed = sorted({t for t, _ in out_edges.get(eid, [])})
            ins_typed = sorted({s for s, _ in in_edges.get(eid, [])})
            recs.append(
                {
                    "id": eid,
                    "kind": _kind_singular(kind),
                    "name": ent.get("name", eid),
                    "root_prefix": ent.get("root_prefix", ""),
                    "module_count": len(ent.get("module_names", []) or []),
                    "promise_count": len(promises),
                    "gap_count": gap_count,
                    "by_attr": by_attr,
                    "outbound": outs_typed,
                    "inbound": ins_typed,
                    "source": source_by_id.get(eid, ""),
                }
            )
        entity_records[kind] = recs

    # Bump gap-type histogram + gap list with unrealized.
    for g in unrealized_gaps:
        gap_type_hist["unrealized"] = gap_type_hist.get("unrealized", 0) + 1
    gap_flat.extend(unrealized_gaps)
    gap_flat.sort(key=lambda g: (g["gap_type"], g["owner"], g["promise_id"]))

    # Top-N summaries across all entities.
    all_records = [r for kind in ENTITY_KINDS for r in entity_records[kind]]
    top_by_promises = sorted(
        all_records, key=lambda c: (-c["promise_count"], c["id"])
    )[:5]
    top_by_gaps = sorted(all_records, key=lambda c: (-c["gap_count"], c["id"]))[:5]
    top_by_promises = [
        {
            "id": c["id"],
            "name": c["name"],
            "kind": c["kind"],
            "promise_count": c["promise_count"],
        }
        for c in top_by_promises
    ]
    top_by_gaps = [
        {
            "id": c["id"],
            "name": c["name"],
            "kind": c["kind"],
            "gap_count": c["gap_count"],
        }
        for c in top_by_gaps
    ]

    # Load existing notes if any (embedded for prefill).
    notes: dict = {}
    if NOTES_PATH.exists():
        raw = _load_yaml(NOTES_PATH)
        notes = raw.get("notes", {}) or {}

    totals = {
        "components": len(entity_records["components"]),
        "entities": sum(len(entity_records[k]) for k in ENTITY_KINDS),
        "promises": sum(r["promise_count"] for r in all_records),
        "gaps": sum(r["gap_count"] for r in all_records) + len(unrealized_gaps),
        "relationships": len(relationships),
    }
    kinds_present = [k for k in ENTITY_KINDS if entity_records[k]]

    se_views = _build_se_views(entities_by_kind, relationships)

    return {
        "meta": meta,
        "totals": totals,
        "status_hist": status_hist,
        "gap_type_hist": gap_type_hist,
        "top_by_promises": top_by_promises,
        "top_by_gaps": top_by_gaps,
        "gaps": gap_flat,
        "entities_by_kind": entity_records,
        "kinds_present": kinds_present,
        "sources": [s[0] for s in sources],
        "notes": notes,
        "se_views": se_views,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>AMS v3 Viewer</title>
<style>
:root {
  --bg: #1a1a2e; --fg: #e0e0e0; --muted: #a0a0c0;
  --sidebar: #16213e; --panel: #16213e; --border: #2a2a4e;
  --accent: #e94560; --link: #7ec8e3; --ok: #4ade80; --warn: #fbbf24; --error: #e94560;
  --ok-bg: #14532d; --warn-bg: #78350f; --error-bg: #7f1d1d;
}
* { box-sizing: border-box; }
body { margin:0; font:14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--fg); background:var(--bg); }
.layout { display:grid; grid-template-columns: 280px 1fr; min-height:100vh; }
#sidebar { background:var(--sidebar); border-right:1px solid var(--border); overflow-y:auto; padding:16px 0; position:sticky; top:0; height:100vh; }
#sidebar h1 { margin:0 16px 4px; font-size:15px; color:var(--fg); }
#sidebar .frame { margin:0 16px 12px; color:var(--muted); font-size:11px; }
#sidebar .totals { margin:0 16px 14px; font-size:11px; color:var(--muted); border-top:1px solid var(--border); padding-top:10px; }
#sidebar .totals b { color:var(--fg); }
#sidebar .nav-item { display:block; padding:8px 16px; color:var(--link); cursor:pointer; font-size:13px; border-left:3px solid transparent; }
#sidebar .nav-item:hover { background:var(--border); }
#sidebar .nav-item.active { background:var(--border); border-left-color:var(--accent); color:var(--fg); font-weight:600; }
#sidebar details { margin:4px 0; }
#sidebar summary { padding:8px 16px; cursor:pointer; color:var(--fg); font-size:12px; text-transform:uppercase; letter-spacing:0.05em; font-weight:600; user-select:none; }
#sidebar summary:hover { background:var(--border); }
#sidebar .entity-link { display:block; padding:5px 16px 5px 28px; color:var(--link); cursor:pointer; font-size:12px; border-left:3px solid transparent; text-decoration:none; }
#sidebar .entity-link:hover { background:var(--border); }
#sidebar .entity-link.active { background:var(--border); border-left-color:var(--accent); color:var(--fg); }
#sidebar .entity-link .cid { font-family: ui-monospace, "SF Mono", Menlo, monospace; color:var(--muted); font-size:10px; display:block; }
#content { padding:24px 32px; max-width:1000px; }
.breadcrumb { color:var(--muted); font-size:12px; margin-bottom:8px; }
.breadcrumb a { color:var(--link); text-decoration:none; cursor:pointer; }
.breadcrumb a:hover { text-decoration:underline; }
h2.content-header { color:var(--accent); margin:0 0 4px; font-size:24px; }
.subtitle { color:var(--muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; margin-bottom:16px; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px; margin-bottom:14px; }
.card h3 { margin:0 0 10px; font-size:12px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
.grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:14px; }
.bar-row { display:grid; grid-template-columns: 110px 1fr 50px; gap:8px; align-items:center; margin-bottom:6px; font-size:12px; }
.bar-row .label { font-family: ui-monospace, "SF Mono", Menlo, monospace; color:var(--fg); }
.bar-row .bar { height:14px; border-radius:3px; }
.bar-row .num { text-align:right; color:var(--muted); font-variant-numeric: tabular-nums; }
.bar.ok { background:var(--ok); }
.bar.warn { background:var(--warn); }
.bar.error { background:var(--error); }
.bar.neutral { background:var(--link); }
table.tops { width:100%; border-collapse:collapse; font-size:12px; }
table.tops td { padding:5px 6px; border-bottom:1px solid var(--border); color:var(--fg); }
table.tops td.cid { font-family: ui-monospace, "SF Mono", Menlo, monospace; color:var(--muted); width:120px; }
table.tops td.kind { color:var(--muted); font-size:11px; width:80px; }
table.tops td.num { text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; width:50px; }
table.tops tr { cursor:pointer; }
table.tops tr:hover td { background:var(--border); }
.attr-group { margin-top:14px; }
.attr-group h3 { margin:0 0 6px; font-size:12px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
.prom { padding:10px 12px; border:1px solid var(--border); border-radius:6px; margin-bottom:6px; background:var(--panel); position:relative; }
.prom .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.pid { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:11px; color:var(--muted); }
.content-text { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; margin-top:6px; word-break:break-word; color:var(--fg); }
.prov { display:none; font-size:11px; color:var(--muted); margin-top:6px; font-family: ui-monospace, "SF Mono", Menlo, monospace; white-space:pre-wrap; border-top:1px dashed var(--border); padding-top:6px; }
.prom:hover .prov { display:block; }
.chips { display:flex; flex-wrap:wrap; gap:5px; }
.chip { display:inline-block; padding:3px 9px; border-radius:12px; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:11px; cursor:pointer; background:var(--border); border:1px solid var(--border); color:var(--link); }
.chip:hover { background:var(--accent); color:var(--fg); border-color:var(--accent); }
.badge { padding:2px 8px; border-radius:10px; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.03em; }
.badge.ok    { background:var(--ok-bg);    color:var(--ok); }
.badge.warn  { background:var(--warn-bg);  color:var(--warn); }
.badge.error { background:var(--error-bg); color:var(--error); }
.badge.gap   { background:var(--error-bg); color:var(--error); }
.empty { color:var(--muted); font-style:italic; font-size:12px; }
textarea.notes { width:100%; min-height:100px; background:var(--bg); color:var(--fg); border:1px solid var(--border); border-radius:6px; padding:10px; font:inherit; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; resize:vertical; }
button.save { margin-top:8px; padding:8px 16px; background:var(--accent); color:#fff; border:0; border-radius:6px; cursor:pointer; font:inherit; font-weight:600; }
button.save:hover { background:#ff5570; }
button.save:disabled { background:var(--border); cursor:not-allowed; color:var(--muted); }
table.gaps { width:100%; border-collapse:collapse; font-size:12px; background:var(--panel); border:1px solid var(--border); border-radius:6px; overflow:hidden; }
table.gaps th, table.gaps td { padding:7px 10px; text-align:left; border-bottom:1px solid var(--border); color:var(--fg); }
table.gaps th { background:var(--border); font-size:10px; text-transform:uppercase; color:var(--muted); }
table.gaps tr:hover td { background:var(--border); cursor:pointer; }
table.gaps td.cid, table.gaps td.pid { font-family: ui-monospace, "SF Mono", Menlo, monospace; color:var(--muted); }
h3.gap-header { margin:18px 0 8px; font-size:12px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
.source-tag { font-size:10px; color:var(--muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; margin-left:8px; }
</style>
</head>
<body>
<div class="layout">
<aside id="sidebar">
  <h1>AMS v3 Viewer</h1>
  <div class="frame">Modeled by <code>viewer.v3.yaml</code> (COMP-VIEWER).</div>
  <div class="totals">
    <div><b id="t-entities">-</b> entities across <b id="t-kinds">-</b> kinds</div>
    <div><b id="t-proms">-</b> promises &middot; <b id="t-gaps">-</b> gaps</div>
    <div><b id="t-rels">-</b> edges &middot; schema <b id="t-schema">-</b></div>
  </div>
  <a class="nav-item" data-nav="overview">Overview</a>
  <a class="nav-item" data-nav="gaps">Typed Gaps</a>
  <details open><summary style="pointer-events:none">SE Views</summary>
    <a class="entity-link" data-se="conops">Concept of Operations<span class="cid">conops</span></a>
    <a class="entity-link" data-se="functional">Functional Analysis<span class="cid">functional</span></a>
    <a class="entity-link" data-se="logical">Logical Architecture<span class="cid">logical</span></a>
    <a class="entity-link" data-se="use_cases">Use Cases<span class="cid">use_cases</span></a>
  </details>
  <div id="entity-groups"></div>
</aside>
<main id="content"></main>
</div>
<script src="assets/mermaid.min.js"></script>
<script id="v3-data" type="application/json">__PAYLOAD__</script>
<script>
const data = JSON.parse(document.getElementById('v3-data').textContent);
const byId = {};
for (const kind of data.kinds_present) {
  for (const e of data.entities_by_kind[kind]) byId[e.id] = e;
}
// Notes state (in-memory, seeded from embedded notes)
const notes = Object.assign({}, data.notes || {});

document.getElementById('t-entities').textContent = data.totals.entities;
document.getElementById('t-kinds').textContent = data.kinds_present.length;
document.getElementById('t-proms').textContent = data.totals.promises;
document.getElementById('t-gaps').textContent = data.totals.gaps;
document.getElementById('t-rels').textContent = data.totals.relationships;
document.getElementById('t-schema').textContent = (data.meta || {}).schema_version || '-';

// --- Sidebar entity groups ---
function renderSidebar() {
  const host = document.getElementById('entity-groups');
  let html = '';
  for (const kind of data.kinds_present) {
    const items = data.entities_by_kind[kind];
    html += `<details open><summary data-kind="${kind}">${kind} (${items.length})</summary>`;
    for (const e of items) {
      html += `<a class="entity-link" data-id="${e.id}">${escapeHtml(e.name)}<span class="cid">${e.id}</span></a>`;
    }
    html += `</details>`;
  }
  host.innerHTML = html;
  host.querySelectorAll('.entity-link').forEach(a => {
    a.addEventListener('click', (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      if (a.dataset.id) selectEntity(a.dataset.id);
      else if (a.dataset.se) showSEView(a.dataset.se);
    });
  });
  // Also wire the SE Views section (rendered before entity-groups).
  document.querySelectorAll('#sidebar .entity-link[data-se]').forEach(a => {
    a.addEventListener('click', (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      showSEView(a.dataset.se);
    });
  });
  host.querySelectorAll('summary[data-kind]').forEach(s => {
    s.addEventListener('click', () => showKindList(s.dataset.kind));
  });
  document.querySelectorAll('.nav-item').forEach(a => {
    a.addEventListener('click', (ev) => {
      ev.preventDefault();
      const t = a.dataset.nav;
      if (t === 'overview') showOverview();
      else if (t === 'gaps') showGaps();
    });
  });
}

function showKindList(kind) {
  highlightNav(null, null);
  const items = data.entities_by_kind[kind] || [];
  let html = `<div class="breadcrumb"><a data-nav="overview">Overview</a> / ${kind}</div>`;
  html += `<h2 class="content-header">${kind} (${items.length})</h2>`;
  html += `<div class="subtitle">All ${kind} in the merged model. Click a row for entity detail.</div>`;
  html += `<div class="card"><table class="tops"><thead><tr>`;
  html += `<th style="text-align:left;font-size:11px;text-transform:uppercase;color:var(--muted);padding:6px">Id</th>`;
  html += `<th style="text-align:left;font-size:11px;text-transform:uppercase;color:var(--muted);padding:6px">Name</th>`;
  html += `<th style="text-align:right;font-size:11px;text-transform:uppercase;color:var(--muted);padding:6px">Promises</th>`;
  html += `<th style="text-align:right;font-size:11px;text-transform:uppercase;color:var(--muted);padding:6px">Gaps</th>`;
  html += `<th style="text-align:left;font-size:11px;text-transform:uppercase;color:var(--muted);padding:6px">Source</th>`;
  html += `</tr></thead><tbody>`;
  for (const e of items) {
    html += `<tr data-id="${e.id}"><td class="cid">${e.id}</td><td>${escapeHtml(e.name)}</td><td class="num">${e.promise_count}</td><td class="num">${e.gap_count}</td><td class="cid" style="font-size:10px">${escapeHtml(e.source)}</td></tr>`;
  }
  html += `</tbody></table></div>`;
  document.getElementById('content').innerHTML = html;
  document.querySelectorAll('table.tops tr[data-id]').forEach(tr => tr.addEventListener('click', () => selectEntity(tr.dataset.id)));
  document.querySelectorAll('.breadcrumb a').forEach(a => a.addEventListener('click', () => { if (a.dataset.nav === 'overview') showOverview(); }));
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function highlightNav(kind, id) {
  document.querySelectorAll('.nav-item').forEach(a => a.classList.toggle('active', a.dataset.nav === kind));
  document.querySelectorAll('.entity-link').forEach(a => {
    const isEntity = a.dataset.id === id;
    const isSE = a.dataset.se && a.dataset.se === kind;
    a.classList.toggle('active', isEntity || isSE);
  });
}

// --- Overview ---
function showOverview() {
  highlightNav('overview', null);
  const sh = data.status_hist || {};
  const total = Math.max(1, (sh.verified||0) + (sh.open||0) + (sh['typed-gap']||0));
  const rows = [
    ['verified', sh.verified||0, 'ok'],
    ['open', sh.open||0, 'warn'],
    ['typed-gap', sh['typed-gap']||0, 'error'],
  ];
  const statusBars = rows.map(([label, n, cls]) => {
    const pct = (n/total*100).toFixed(1);
    return `<div class="bar-row"><div class="label">${label}</div><div class="bar ${cls}" style="width:${pct}%"></div><div class="num">${n}</div></div>`;
  }).join('');
  const gh = data.gap_type_hist || {};
  const gkeys = Object.keys(gh).sort((a,b) => gh[b]-gh[a] || a.localeCompare(b));
  const gtotal = Math.max(1, gkeys.reduce((s,k) => s+gh[k], 0));
  const gapBars = gkeys.length ? gkeys.map(k => {
    const pct = (gh[k]/gtotal*100).toFixed(1);
    return `<div class="bar-row"><div class="label">${k}</div><div class="bar neutral" style="width:${pct}%"></div><div class="num">${gh[k]}</div></div>`;
  }).join('') : '<span class="empty">No typed gaps.</span>';
  const topProms = (data.top_by_promises || []).map(c =>
    `<tr data-id="${c.id}"><td class="cid">${c.id}</td><td>${escapeHtml(c.name)}</td><td class="kind">${c.kind}</td><td class="num">${c.promise_count}</td></tr>`
  ).join('');
  const topGaps = (data.top_by_gaps || []).map(c =>
    `<tr data-id="${c.id}"><td class="cid">${c.id}</td><td>${escapeHtml(c.name)}</td><td class="kind">${c.kind}</td><td class="num">${c.gap_count}</td></tr>`
  ).join('');
  const kindSummary = data.kinds_present.map(k =>
    `<div class="bar-row"><div class="label">${k}</div><div class="bar neutral" style="width:${(data.entities_by_kind[k].length/data.totals.entities*100).toFixed(1)}%"></div><div class="num">${data.entities_by_kind[k].length}</div></div>`
  ).join('');
  document.getElementById('content').innerHTML = `
    <div class="breadcrumb">Overview</div>
    <h2 class="content-header">Architecture Model</h2>
    <div class="subtitle">${data.sources.length} source(s) &middot; ${data.totals.entities} entities across ${data.kinds_present.length} kinds</div>
    <div class="grid2">
      <div class="card"><h3>Promise status</h3>${statusBars}</div>
      <div class="card"><h3>Typed gap distribution</h3>${gapBars}</div>
      <div class="card"><h3>Entity kinds</h3>${kindSummary}</div>
      <div class="card"><h3>Sources merged</h3><ul style="margin:0;padding-left:18px;font-family:ui-monospace,'SF Mono',Menlo,monospace;font-size:12px">${data.sources.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul></div>
      <div class="card"><h3>Top 5 by promise count</h3><table class="tops">${topProms}</table></div>
      <div class="card"><h3>Top 5 by typed-gap count</h3><table class="tops">${topGaps}</table></div>
    </div>`;
  document.querySelectorAll('table.tops tr').forEach(tr => tr.addEventListener('click', () => selectEntity(tr.dataset.id)));
}

// --- Gaps ---
function showGaps() {
  highlightNav('gaps', null);
  const groups = {};
  for (const g of (data.gaps || [])) {
    (groups[g.gap_type] = groups[g.gap_type] || []).push(g);
  }
  const keys = Object.keys(groups).sort((a,b) => groups[b].length - groups[a].length || a.localeCompare(b));
  let html = `<div class="breadcrumb">Typed Gaps</div><h2 class="content-header">Typed Gaps</h2><div class="subtitle">${data.totals.gaps} total across ${keys.length} type(s)</div>`;
  if (!keys.length) html += '<p class="empty">No typed gaps.</p>';
  for (const k of keys) {
    const rows = groups[k].map(g =>
      `<tr data-id="${g.owner}"><td class="cid">${g.owner}</td><td>${escapeHtml(g.owner_name)}</td><td class="kind">${g.owner_kind}</td><td class="pid">${g.promise_id}</td><td>${g.attribute}</td></tr>`
    ).join('');
    html += `<h3 class="gap-header">${k} (${groups[k].length})</h3>` +
      `<table class="gaps"><thead><tr><th>Owner id</th><th>Owner name</th><th>Kind</th><th>Promise id</th><th>Attribute</th></tr></thead><tbody>${rows}</tbody></table>`;
  }
  document.getElementById('content').innerHTML = html;
  document.querySelectorAll('table.gaps tr[data-id]').forEach(tr => tr.addEventListener('click', () => selectEntity(tr.dataset.id)));
}

// --- Entity detail ---
function badge(status) {
  const cls = ({verified:'ok', open:'warn', 'typed-gap':'error'})[status] || 'warn';
  return `<span class="badge ${cls}">${status}</span>`;
}

function selectEntity(id) {
  const e = byId[id];
  if (!e) return;
  highlightNav(null, id);
  const attrs = ['intent','delivers','provides'];
  let html = `<div class="breadcrumb"><a data-nav="overview">Overview</a> / ${e.kind}s / ${e.id}</div>`;
  html += `<h2 class="content-header">${escapeHtml(e.name)}</h2>`;
  html += `<div class="subtitle">${e.id} &middot; ${e.kind}${e.root_prefix ? ' &middot; '+escapeHtml(e.root_prefix) : ''}<span class="source-tag">from ${escapeHtml(e.source)}</span></div>`;
  html += `<div class="card"><h3>Summary</h3><div style="font-size:13px">${e.module_count} modules &middot; ${e.promise_count} promises &middot; ${e.gap_count} typed gaps</div></div>`;

  const seen = new Set();
  for (const attr of attrs) {
    const rows = (e.by_attr[attr] || []);
    seen.add(attr);
    if (!rows.length) continue;
    html += `<div class="card"><h3>${attr} (${rows.length})</h3>`;
    for (const p of rows) {
      const gap = p.gap_type ? `<span class="badge gap">${p.gap_type}</span>` : '';
      html += `<div class="prom"><div class="row">${badge(p.status)}${gap}<span class="pid">${escapeHtml(p.id)}</span></div>` +
              `<div class="content-text">${escapeHtml((p.content || []).join(', ')) || '<span class="empty">(empty)</span>'}</div>` +
              `<div class="prov">${escapeHtml(p.provenance || '')}</div></div>`;
    }
    html += `</div>`;
  }
  for (const attr of Object.keys(e.by_attr)) {
    if (seen.has(attr)) continue;
    const rows = e.by_attr[attr];
    html += `<div class="card"><h3>${attr} (${rows.length})</h3>`;
    for (const p of rows) {
      html += `<div class="prom"><div class="row">${badge(p.status)}<span class="pid">${escapeHtml(p.id)}</span></div>` +
              `<div class="content-text">${escapeHtml((p.content || []).join(', '))}</div></div>`;
    }
    html += `</div>`;
  }

  html += `<div class="card"><h3>Neighbors</h3>`;
  html += `<div style="margin-bottom:6px;font-size:11px;color:var(--muted);text-transform:uppercase">Depends on (${e.outbound.length})</div><div class="chips" style="margin-bottom:12px">`;
  html += e.outbound.length ? e.outbound.map(id => `<span class="chip" data-id="${id}">${id}</span>`).join('') : '<span class="empty">none</span>';
  html += `</div><div style="margin-bottom:6px;font-size:11px;color:var(--muted);text-transform:uppercase">Depended on by (${e.inbound.length})</div><div class="chips">`;
  html += e.inbound.length ? e.inbound.map(id => `<span class="chip" data-id="${id}">${id}</span>`).join('') : '<span class="empty">none</span>';
  html += `</div></div>`;

  const noteVal = notes[e.id] || '';
  html += `<div class="card"><h3>Notes</h3>` +
    `<textarea class="notes" id="notes-${e.id}" placeholder="Human notes, questions, TODOs — persisted to notes.yaml via Save button.">${escapeHtml(noteVal)}</textarea>` +
    `<button class="save" id="save-btn">Save notes.yaml (download)</button>` +
    `<div style="margin-top:6px;font-size:11px;color:var(--muted)">Option A: browser downloads full notes.yaml. Place in <code>.architecture/viewers/notes.yaml</code> and rebuild.</div></div>`;

  document.getElementById('content').innerHTML = html;
  document.querySelectorAll('.chip').forEach(ch => ch.addEventListener('click', () => selectEntity(ch.dataset.id)));
  document.querySelectorAll('.breadcrumb a').forEach(a => a.addEventListener('click', () => {
    if (a.dataset.nav === 'overview') showOverview();
  }));
  const ta = document.getElementById(`notes-${e.id}`);
  ta.addEventListener('input', () => { notes[e.id] = ta.value; });
  document.getElementById('save-btn').addEventListener('click', () => {
    // Snapshot current textarea before download.
    notes[e.id] = ta.value;
    // Build YAML manually (deterministic, sorted).
    const keys = Object.keys(notes).sort();
    let yaml = "schema_version: '1.0'\\nnotes:\\n";
    if (!keys.length) yaml += '  {}\\n';
    for (const k of keys) {
      const v = notes[k] || '';
      if (!v.trim()) continue;
      // Use YAML block scalar for multi-line safety.
      yaml += `  ${k}: |\\n`;
      for (const line of v.split('\\n')) yaml += `    ${line}\\n`;
    }
    const blob = new Blob([yaml], {type: 'text/yaml'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'notes.yaml';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

renderSidebar();
showOverview();

// --- SE Views (Mermaid diagrams) ---
if (window.mermaid) {
  mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose', flowchart: { htmlLabels: true, curve: 'basis' } });
}

let _seRenderCounter = 0;
async function showSEView(viewId) {
  highlightNav(viewId, null);
  const v = (data.se_views || {})[viewId];
  if (!v) { document.getElementById('content').innerHTML = `<div class="empty">SE view ${escapeHtml(viewId)} not found.</div>`; return; }
  const refs = (v.entity_refs || []).map(id =>
    `<span class="chip" data-id="${id}">${id}</span>`
  ).join('');
  const diagramId = `mmd-${viewId}-${++_seRenderCounter}`;
  document.getElementById('content').innerHTML = `
    <div class="breadcrumb"><a data-nav="overview">Overview</a> / SE Views / ${escapeHtml(v.title)}</div>
    <h2 class="content-header">${escapeHtml(v.title)}</h2>
    <div class="subtitle">Deterministic render from merged model (${v.entity_refs.length} entity refs)</div>
    <div class="card"><h3>Intent</h3><div style="font-size:13px;line-height:1.6">${escapeHtml(v.narrative)}</div></div>
    <div class="card"><h3>Diagram</h3>
      <div class="mermaid-host" style="background:#0f172a;padding:12px;border-radius:6px;overflow-x:auto">
        <div id="${diagramId}" class="mermaid">${escapeHtml(v.mermaid)}</div>
      </div>
    </div>
    <div class="card"><h3>Entities referenced (${v.entity_refs.length})</h3><div class="chips">${refs || '<span class="empty">none</span>'}</div></div>
    <details class="card"><summary style="cursor:pointer;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Mermaid source</summary><pre style="margin:8px 0 0;font-family:ui-monospace,'SF Mono',Menlo,monospace;font-size:11px;color:var(--muted);white-space:pre-wrap">${escapeHtml(v.mermaid)}</pre></details>
  `;
  document.querySelectorAll('.chip').forEach(ch => ch.addEventListener('click', () => selectEntity(ch.dataset.id)));
  document.querySelectorAll('.breadcrumb a').forEach(a => a.addEventListener('click', () => {
    if (a.dataset.nav === 'overview') showOverview();
  }));
  if (window.mermaid) {
    try {
      const el = document.getElementById(diagramId);
      await mermaid.run({ nodes: [el] });
    } catch (err) {
      const el = document.getElementById(diagramId);
      if (el) el.innerHTML = `<div class="empty">Mermaid render failed: ${escapeHtml(err.message || String(err))}</div>`;
    }
  }
}
</script>
</body>
</html>
"""


def build(model_path: Path | None = None) -> None:
    path = model_path or DEFAULT_MODEL
    if not path.exists():
        print(f"error: {path} not found - run pipeline_v3 first", file=sys.stderr)
        sys.exit(2)
    payload = _build_payload(path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8"
    )
    embedded = json.dumps(payload, sort_keys=True)
    html = HTML_TEMPLATE.replace("__PAYLOAD__", embedded)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"wrote {OUT_HTML} ({OUT_HTML.stat().st_size} bytes)")
    print(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size} bytes)")
    print(
        f"totals: {payload['totals']['entities']} entities, "
        f"{payload['totals']['promises']} promises, "
        f"{payload['totals']['gaps']} gaps, "
        f"{payload['totals']['relationships']} edges"
    )
    print(f"kinds present: {payload['kinds_present']}")
    print(f"sources merged: {payload['sources']}")
    print(f"status_hist: {payload['status_hist']}")
    print(f"gap_type_hist: {payload['gap_type_hist']}")
    print(f"open: file://{OUT_HTML}")


if __name__ == "__main__":
    arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    build(arg)
