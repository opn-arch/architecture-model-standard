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
        "Concept of Operations for the AMS dev workflow \u2014 actor "
        "\u2192 top-level-capability roll-up. Behavior-level triggers are "
        "aggregated upward through the contains-graph until they reach one "
        "of the three top capabilities (CAP-PB extract, CAP-SL slice, "
        "CAP-DF evolve). Actor\u2192behavior detail is available on each "
        "actor's entity page and in the Use Cases view. The LLM is "
        "declared as future actor for CAP-DF.4 (Part 3, not yet realized)."
    ),
    "functional": (
        "Functional analysis \u2014 capability hierarchy only. Shows the "
        "three top-level capabilities (CAP-PB extract, CAP-SL slice, "
        "CAP-DF evolve) and the four CAP-DF sub-capabilities (walk, view, "
        "validate, LLM seams). Behaviors, interfaces, and constraints are "
        "accessible via the sidebar and each capability's entity page "
        "(constrained-by targets appear as neighbor chips)."
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
    """Actors on left, top-level capabilities on right; roll-up edges.

    Actor\u2192behavior\u2192capability chains are walked upward through
    ``contains``-edges until a top-level capability (no inbound ``contains``
    from another capability) is reached. Edges are deduplicated on
    ``(actor, top_cap)`` and rendered unlabeled to sidestep the Mermaid
    paren-in-pipe-label parser bug and match the Use Cases aesthetic.
    """
    actors = sorted(entities_by_kind["actors"].keys())
    caps_dict = entities_by_kind["capabilities"]
    caps = sorted(caps_dict.keys())
    # Top-level caps = capabilities with no inbound `contains` edge from
    # another capability.
    contained_by_cap: set[str] = set()
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if rt == "contains" and f in caps_dict and t in caps_dict:
            contained_by_cap.add(t)
    top_caps = {cid for cid in caps if cid not in contained_by_cap}

    # Build reverse lookup: child_cap -> parent_cap via `contains`.
    parent_of: dict[str, str] = {}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if rt == "contains" and f in caps_dict and t in caps_dict:
            parent_of[t] = f

    # Owning cap for an arbitrary entity (behavior or otherwise): first
    # capability that `contains` it.
    owning_cap: dict[str, str] = {}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if rt == "contains" and f in caps_dict and t not in caps_dict:
            owning_cap.setdefault(t, f)

    def _roll_up(cap_id: str) -> str | None:
        """Walk contains-edges upward until a top-cap is reached (max 5 hops)."""
        cur = cap_id
        for _ in range(5):
            if cur in top_caps:
                return cur
            nxt = parent_of.get(cur)
            if nxt is None or nxt == cur:
                return None
            cur = nxt
        return None

    # Emit dedupe'd (actor, top_cap) pairs.
    pairs: set[tuple[str, str]] = set()
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f not in actors or rt != "triggers":
            continue
        if t in caps_dict:
            start = t
        else:
            start = owning_cap.get(t)
            if start is None:
                # No capability owns this behavior; skip with warning.
                print(
                    f"[conops] warn: cannot roll up trigger {f}->{t}: "
                    "no owning capability",
                    file=sys.stderr,
                )
                continue
        top = _roll_up(start)
        if top is None:
            print(
                f"[conops] warn: cannot roll up trigger {f}->{t}: "
                f"no top-cap ancestor within 5 hops (started at {start})",
                file=sys.stderr,
            )
            continue
        pairs.add((f, top))

    used_actors = sorted({a for a, _ in pairs})
    used_tops = sorted({c for _, c in pairs})

    lines = ["flowchart LR"]
    if used_actors:
        lines.append('  subgraph ACTORS["Actors"]')
        for aid in used_actors:
            name = entities_by_kind["actors"][aid].get("name", aid)
            lines.append(f'    {_mid(aid)}(("{_mesc(aid)}<br/>{_mesc(name)}"))')
        lines.append("  end")
    if used_tops:
        lines.append('  subgraph CAPS["Top-level Capabilities"]')
        for cid in used_tops:
            name = caps_dict[cid].get("name", cid)
            lines.append(f'    {_mid(cid)}["{_mesc(cid)}<br/>{_mesc(name)}"]')
        lines.append("  end")
    for f, t in sorted(pairs):
        lines.append(f"  {_mid(f)} --> {_mid(t)}")
    refs = set(used_actors) | set(used_tops)
    return "\n".join(lines), sorted(refs)


def _mermaid_functional(
    entities_by_kind: dict, relationships: list
) -> tuple[str, list[str]]:
    """Capability hierarchy only: caps as nodes, contains-edges between caps.

    Behaviors, interfaces, and constraints are intentionally omitted from
    the diagram to keep the functional view high-level. They remain
    browsable in the sidebar and appear as neighbor chips on each
    capability's entity page (constrained-by targets included).
    """
    caps = entities_by_kind["capabilities"]
    lines = ["flowchart TD"]
    refs: set[str] = set()
    for cid in sorted(caps):
        name = caps[cid].get("name", cid)
        lines.append(f'  {_mid(cid)}["{_mesc(cid)}<br/>{_mesc(name)}"]')
        refs.add(cid)
    edges: list[tuple[str, str]] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f in caps and rt == "contains" and t in caps:
            edges.append((f, t))
    for f, t in sorted(set(edges)):
        lines.append(f"  {_mid(f)} --> {_mid(t)}")
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


def _mermaid_pipeline(
    entities_by_kind: dict, relationships: list, cap_id: str = "CAP-PB"
) -> tuple[str, list[str]] | None:
    """Capability-scoped flow diagram — actors, entry behaviors, stages, outputs.

    Generalized principle: any capability whose contained behaviors have
    internal ``triggers`` edges gets an inline Mermaid flow card. Returns
    ``None`` when the capability has no such edges (no flow to render).

    Layout: flowchart LR with per-kind color coding (v2 dashboard palette).
    Actors (round) → entry behaviors (rect emphasized, inbound triggers
    from actors) → stages (rect grouped in subgraph, topologically sorted)
    → produced interfaces (parallelogram). Deterministic tiebreak by id.
    """
    behs = entities_by_kind["behaviors"]
    acts = entities_by_kind["actors"]
    ifs = entities_by_kind["interfaces"]
    caps = entities_by_kind["capabilities"]
    refs: set[str] = set()

    if cap_id not in caps:
        return None

    # Contained behaviors of this capability.
    contained: list[str] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if f == cap_id and rt == "contains" and t in behs:
            contained.append(t)
    if not contained:
        return None
    contained_set = set(contained)

    # Internal triggers edges (both endpoints in contained_set).
    internal_edges: list[tuple[str, str]] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type", "")
        if rt == "triggers" and f in contained_set and t in contained_set:
            internal_edges.append((f, t))
    if not internal_edges:
        return None

    # Entry behaviors: contained behaviors triggered by any actor.
    entry_behs = sorted({
        r["to"] for r in relationships
        if r.get("type") == "triggers"
        and r.get("to") in contained_set
        and r.get("from") in acts
    })
    entry_set = set(entry_behs)
    stages_only = [s for s in contained if s not in entry_set]

    # Topological sort stages by `triggers` edges (deterministic tiebreak by id).
    trig: dict[str, list[str]] = {s: [] for s in stages_only}
    indeg: dict[str, int] = {s: 0 for s in stages_only}
    for f, t in internal_edges:
        if f in trig and t in indeg:
            trig[f].append(t)
            indeg[t] += 1
    ordered: list[str] = []
    frontier = sorted([s for s, d in indeg.items() if d == 0])
    while frontier:
        n = frontier.pop(0)
        ordered.append(n)
        for m in sorted(trig.get(n, [])):
            indeg[m] -= 1
            if indeg[m] == 0:
                frontier.append(m)
        frontier.sort()
    # Append any stages left (cyclic / disconnected) to keep output stable.
    for s in sorted(stages_only):
        if s not in ordered:
            ordered.append(s)

    # Actors that trigger any entry behavior.
    trig_actors = sorted({
        r["from"] for r in relationships
        if r.get("type") == "triggers"
        and r.get("to") in entry_set
        and r.get("from") in acts
    })

    # Output interfaces produced by any contained behavior.
    out_ifs_pairs = sorted({
        (r["from"], r["to"]) for r in relationships
        if r.get("type") == "produces"
        and r.get("from") in contained_set
        and r.get("to") in ifs
    })
    out_ifs = sorted({t for _, t in out_ifs_pairs})

    lines = ["flowchart LR"]
    # Actors subgraph.
    if trig_actors:
        lines.append('  subgraph ACTORS["Actors"]')
        for aid in trig_actors:
            name = acts[aid].get("name", aid)
            lines.append(f'    {_mid(aid)}(("{_mesc(aid)}<br/>{_mesc(name)}"))')
            refs.add(aid)
        lines.append("  end")
    # Entry behaviors (emphasized).
    for eid in entry_behs:
        ename = behs[eid].get("name", eid)
        lines.append(
            f'  {_mid(eid)}[["{_mesc(eid)}<br/>{_mesc(ename)}"]]'
        )
        refs.add(eid)
    # Stage subgraph.
    if ordered:
        lines.append(
            f'  subgraph STAGES["{_mesc(cap_id)} stages (triggers)"]'
        )
        lines.append("    direction LR")
        for sid in ordered:
            sname = behs[sid].get("name", sid)
            lines.append(
                f'    {_mid(sid)}["{_mesc(sid)}<br/>{_mesc(sname)}"]'
            )
            refs.add(sid)
        # Chain triggers within subgraph (stage-to-stage internal edges).
        for i in range(len(ordered) - 1):
            a, b = ordered[i], ordered[i + 1]
            if b in trig.get(a, []):
                lines.append(f"    {_mid(a)} --> {_mid(b)}")
        lines.append("  end")
    # Output interface nodes.
    for iid in out_ifs:
        iname = ifs[iid].get("name", iid)
        lines.append(f'  {_mid(iid)}[/"{_mesc(iid)}<br/>{_mesc(iname)}"/]')
        refs.add(iid)
    # Cross-subgraph edges: actor -> each entry.
    for aid in trig_actors:
        for eid in entry_behs:
            # Only emit if the model asserts this triggers edge.
            if any(
                r.get("type") == "triggers"
                and r.get("from") == aid and r.get("to") == eid
                for r in relationships
            ):
                lines.append(f"  {_mid(aid)} --> {_mid(eid)}")
    # Entry -> first stage triggered by it (per model triggers).
    for eid in entry_behs:
        for tgt in sorted(t for f, t in internal_edges if f == eid):
            lines.append(f"  {_mid(eid)} --> {_mid(tgt)}")
    # Produced-by edges: each behavior -> its produced interface(s).
    for f, t in out_ifs_pairs:
        lines.append(f"  {_mid(f)} --> {_mid(t)}")

    # Style classes (v2 dashboard palette).
    lines.append(
        "  classDef actor fill:#1e293b,stroke:#0969da,color:#e6edf3;"
    )
    lines.append(
        "  classDef orch fill:#3b1e5a,stroke:#a855f7,color:#f3e8ff,"
        "stroke-width:2px;"
    )
    lines.append(
        "  classDef stage fill:#1e293b,stroke:#6639ba,color:#e6edf3;"
    )
    lines.append(
        "  classDef iface fill:#0f2e1e,stroke:#1a7f37,color:#dafbe1;"
    )
    if trig_actors:
        lines.append(
            "  class " + ",".join(_mid(a) for a in trig_actors) + " actor;"
        )
    if entry_behs:
        lines.append(
            "  class " + ",".join(_mid(e) for e in entry_behs) + " orch;"
        )
    if ordered:
        lines.append("  class " + ",".join(_mid(s) for s in ordered) + " stage;")
    if out_ifs:
        lines.append(
            "  class " + ",".join(_mid(i) for i in out_ifs) + " iface;"
        )

    return "\n".join(lines), sorted(refs)


def _all_entities_flat(entities_by_kind: dict) -> dict:
    """Return {entity_id: (kind_singular, entity_dict)} across all kinds."""
    flat: dict = {}
    for kind in ENTITY_KINDS:
        ksing = _kind_singular(kind)
        for eid, ent in entities_by_kind[kind].items():
            flat[eid] = (ksing, ent)
    return flat


# Per-kind Mermaid node shape (deterministic, matches SE view aesthetic).
_KIND_SHAPE = {
    "component": ('[', ']'),
    "capability": ('(', ')'),
    "behavior": ('[[', ']]'),
    "interface": ('[/', '/]'),
    "actor": ('((', '))'),
    "constraint": ('{{', '}}'),
    "layer": ('[(', ')]'),
}


def _mnode(eid: str, name: str, kind: str) -> str:
    """Emit a Mermaid node line with kind-appropriate shape + label."""
    lo, hi = _KIND_SHAPE.get(kind, ('[', ']'))
    return f'  {_mid(eid)}{lo}"{_mesc(eid)}<br/>{_mesc(name)}"{hi}'


def _emit_class_defs(lines: list) -> None:
    """Append v2-palette classDef lines used across walk diagrams."""
    lines.append("  classDef component fill:#1e293b,stroke:#6639ba,color:#e6edf3;")
    lines.append("  classDef capability fill:#3b1e5a,stroke:#a855f7,color:#f3e8ff,stroke-width:2px;")
    lines.append("  classDef behavior fill:#1e293b,stroke:#0969da,color:#e6edf3;")
    lines.append("  classDef interface fill:#0f2e1e,stroke:#1a7f37,color:#dafbe1;")
    lines.append("  classDef actor fill:#1e293b,stroke:#0969da,color:#e6edf3;")
    lines.append("  classDef constraint fill:#3b1e1e,stroke:#f97316,color:#fed7aa;")
    lines.append("  classDef layer fill:#1a2f4a,stroke:#38bdf8,color:#e0f2fe;")
    lines.append("  classDef root fill:#7f1d1d,stroke:#e94560,color:#ffe4e6,stroke-width:3px;")


def _apply_classes(lines: list, by_kind: dict, root_id: str | None = None) -> None:
    """Emit `class <ids> <kind>;` lines for grouped nodes; root gets `root` class."""
    for kind, ids in by_kind.items():
        clean = [i for i in ids if i != root_id]
        if clean:
            lines.append(f"  class {','.join(_mid(i) for i in clean)} {kind};")
    if root_id:
        lines.append(f"  class {_mid(root_id)} root;")


def _mermaid_decomposition(
    entities_by_kind: dict, relationships: list, entity_id: str
) -> tuple[str, list[str]] | None:
    """BFS ≤2 hops of outbound `contains` edges. Cap 30 nodes; overflow as
    ``...N more`` sink. Returns ``None`` when the root has no outbound
    ``contains`` edges (silent skip)."""
    flat = _all_entities_flat(entities_by_kind)
    if entity_id not in flat:
        return None

    # Outbound contains map (only from entities we know about).
    contains_out: dict[str, list[str]] = {}
    for r in relationships:
        if r.get("type") != "contains":
            continue
        f, t = r.get("from"), r.get("to")
        if f in flat and t in flat:
            contains_out.setdefault(f, []).append(t)

    if not contains_out.get(entity_id):
        return None

    CAP = 30
    visited = {entity_id}
    edges: list[tuple[str, str]] = []
    overflow = 0

    def _expand(node: str) -> list[str]:
        return sorted(set(contains_out.get(node, [])))

    # Depth 1.
    for child in _expand(entity_id):
        if len(visited) >= CAP:
            overflow += 1
            continue
        visited.add(child)
        edges.append((entity_id, child))
    # Depth 2.
    depth1 = [c for c in _expand(entity_id) if c in visited]
    for parent in depth1:
        for child in _expand(parent):
            if child in visited:
                edges.append((parent, child))
                continue
            if len(visited) >= CAP:
                overflow += 1
                continue
            visited.add(child)
            edges.append((parent, child))

    lines = ["flowchart TD"]
    by_kind: dict[str, list[str]] = {}
    for eid in sorted(visited):
        ksing, ent = flat[eid]
        lines.append(_mnode(eid, ent.get("name", eid), ksing))
        by_kind.setdefault(ksing, []).append(eid)
    for f, t in sorted(set(edges)):
        lines.append(f"  {_mid(f)} --> {_mid(t)}")
    if overflow:
        lines.append(f'  overflow["...{overflow} more"]')
        lines.append(f"  {_mid(entity_id)} -.-> overflow")
    _emit_class_defs(lines)
    _apply_classes(lines, by_kind, root_id=entity_id)
    return "\n".join(lines), sorted(visited)


def _mermaid_neighbors(
    entities_by_kind: dict,
    relationships: list,
    entity_id: str,
    out_edges: dict,
    in_edges: dict,
    threshold: int = 20,
) -> tuple[str, list[str]] | None:
    """1-hop typed-edge neighborhood. Skip when total 1-hop neighbors is 0
    or > ``threshold``. Uses ``out_edges``/``in_edges`` (with rel_type),
    NOT the deduplicated ``outbound``/``inbound`` lists on the record."""
    flat = _all_entities_flat(entities_by_kind)
    if entity_id not in flat:
        return None

    outs = [(t, rt) for t, rt in out_edges.get(entity_id, []) if t in flat]
    ins = [(s, rt) for s, rt in in_edges.get(entity_id, []) if s in flat]
    total = len(outs) + len(ins)
    if total == 0 or total > threshold:
        return None

    refs = {entity_id}
    lines = ["flowchart LR"]
    by_kind: dict[str, list[str]] = {}

    # Root node.
    ksing, ent = flat[entity_id]
    lines.append(_mnode(entity_id, ent.get("name", entity_id), ksing))
    by_kind.setdefault(ksing, []).append(entity_id)

    # Nodes for all neighbors (dedup by id).
    neighbor_ids = sorted(set([t for t, _ in outs] + [s for s, _ in ins]))
    for nid in neighbor_ids:
        if nid == entity_id:
            continue
        nksing, nent = flat[nid]
        lines.append(_mnode(nid, nent.get("name", nid), nksing))
        by_kind.setdefault(nksing, []).append(nid)
        refs.add(nid)

    # Edges (deterministic order, typed labels).
    for src, tgt, rt in sorted({(entity_id, t, rt) for t, rt in outs}):
        lines.append(f'  {_mid(src)} -->|{_mesc(rt)}| {_mid(tgt)}')
    for src, tgt, rt in sorted({(s, entity_id, rt) for s, rt in ins}):
        lines.append(f'  {_mid(src)} -->|{_mesc(rt)}| {_mid(tgt)}')

    _emit_class_defs(lines)
    _apply_classes(lines, by_kind, root_id=entity_id)
    return "\n".join(lines), sorted(refs)


def _mermaid_realization(
    entities_by_kind: dict,
    relationships: list,
    entity_id: str,
    kind: str,
    out_edges: dict,
    in_edges: dict,
) -> tuple[str, list[str]] | None:
    """Kind-dispatched 2-hop realization chain. See CONTEXT plan decision 5
    for the exact walks. Returns ``None`` when hop 1 is empty."""
    flat = _all_entities_flat(entities_by_kind)
    if entity_id not in flat:
        return None

    def outs_by(eid: str, rtype: str) -> list[str]:
        return sorted({t for t, rt in out_edges.get(eid, []) if rt == rtype and t in flat})

    def ins_by(eid: str, rtype: str) -> list[str]:
        return sorted({s for s, rt in in_edges.get(eid, []) if rt == rtype and s in flat})

    edges: list[tuple[str, str, str]] = []  # (from, to, label)
    hop1: list[str] = []
    hop2: list[str] = []

    if kind == "capability":
        # cap <-- realizes <-- components --> contains --> sub-components
        hop1 = ins_by(entity_id, "realizes")
        for c in hop1:
            edges.append((c, entity_id, "realizes"))
        for c in hop1:
            for sub in outs_by(c, "contains"):
                edges.append((c, sub, "contains"))
                hop2.append(sub)
    elif kind == "component":
        # comp --> realizes --> capabilities <-- contains <-- parent caps
        hop1 = outs_by(entity_id, "realizes")
        for cap in hop1:
            edges.append((entity_id, cap, "realizes"))
        for cap in hop1:
            for parent in ins_by(cap, "contains"):
                edges.append((parent, cap, "contains"))
                hop2.append(parent)
    elif kind == "behavior":
        # beh <-- traces-to <-- components --> realizes --> capabilities
        hop1 = ins_by(entity_id, "traces-to")
        for c in hop1:
            edges.append((c, entity_id, "traces-to"))
        for c in hop1:
            for cap in outs_by(c, "realizes"):
                edges.append((c, cap, "realizes"))
                hop2.append(cap)
    elif kind == "interface":
        # if <-- exposes <-- components --> realizes --> capabilities
        hop1 = ins_by(entity_id, "exposes")
        for c in hop1:
            edges.append((c, entity_id, "exposes"))
        for c in hop1:
            for cap in outs_by(c, "realizes"):
                edges.append((c, cap, "realizes"))
                hop2.append(cap)
    elif kind == "layer":
        # layer --> contains --> components --> realizes --> capabilities
        hop1 = outs_by(entity_id, "contains")
        for c in hop1:
            edges.append((entity_id, c, "contains"))
        for c in hop1:
            for cap in outs_by(c, "realizes"):
                edges.append((c, cap, "realizes"))
                hop2.append(cap)
    elif kind == "actor":
        # actor --> triggers --> behaviors <-- traces-to <-- components
        hop1 = outs_by(entity_id, "triggers")
        for b in hop1:
            edges.append((entity_id, b, "triggers"))
        for b in hop1:
            for c in ins_by(b, "traces-to"):
                edges.append((c, b, "traces-to"))
                hop2.append(c)
    elif kind == "constraint":
        # constraint <-- constrained-by (1-hop only)
        hop1 = ins_by(entity_id, "constrained-by")
        for c in hop1:
            edges.append((c, entity_id, "constrained-by"))
    else:
        return None

    if not hop1:
        return None

    # Dedup edges deterministically.
    edges = sorted(set(edges))
    node_ids = {entity_id} | set(hop1) | set(hop2)

    lines = ["flowchart LR"]
    by_kind: dict[str, list[str]] = {}
    for nid in sorted(node_ids):
        nksing, nent = flat[nid]
        lines.append(_mnode(nid, nent.get("name", nid), nksing))
        by_kind.setdefault(nksing, []).append(nid)
    for f, t, lbl in edges:
        lines.append(f'  {_mid(f)} -->|{_mesc(lbl)}| {_mid(t)}')
    _emit_class_defs(lines)
    _apply_classes(lines, by_kind, root_id=entity_id)
    return "\n".join(lines), sorted(node_ids)


def _mermaid_cross_capability_flow(
    entities_by_kind: dict, relationships: list, cap_id: str
) -> tuple[str, list[str]] | None:
    """Cross-capability behavior-flow diagram.

    Extends ``_mermaid_pipeline`` beyond a single capability: collects
    TRANSITIVELY-contained behaviors of ``cap_id`` (walking ``contains``
    through any sub-capabilities), then renders every ``triggers`` edge
    where AT LEAST ONE endpoint is in that descendant set. External
    endpoints (behaviors owned by another capability) are drawn in an
    ``External`` subgraph so the boundary crossings are visible.

    Returns ``None`` when the descendant set has no triggers touching it,
    OR when all triggers are already fully-internal (``_mermaid_pipeline``
    handles that case). This yields non-empty output specifically for
    capabilities like CAP-DF whose flow crosses sub-capability boundaries.
    """
    behs = entities_by_kind["behaviors"]
    caps = entities_by_kind["capabilities"]
    if cap_id not in caps:
        return None

    # Transitively walk `contains` from cap_id, collecting behaviors.
    contains_out: dict[str, list[str]] = {}
    for r in relationships:
        if r.get("type") == "contains":
            f, t = r.get("from"), r.get("to")
            if f is not None and t is not None:
                contains_out.setdefault(f, []).append(t)

    seen: set[str] = set()
    stack = [cap_id]
    behaviors_in: set[str] = set()
    caps_in: set[str] = {cap_id}
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for child in contains_out.get(n, []):
            if child in behs:
                behaviors_in.add(child)
            elif child in caps:
                caps_in.add(child)
                stack.append(child)

    if not behaviors_in:
        return None

    # Collect all triggers edges where at least one endpoint is in behaviors_in.
    trig_edges: list[tuple[str, str]] = []
    external: set[str] = set()
    for r in relationships:
        if r.get("type") != "triggers":
            continue
        f, t = r.get("from"), r.get("to")
        if f not in behs or t not in behs:
            continue  # only behavior->behavior triggers on this diagram
        if f in behaviors_in or t in behaviors_in:
            trig_edges.append((f, t))
            if f not in behaviors_in:
                external.add(f)
            if t not in behaviors_in:
                external.add(t)

    if not trig_edges:
        return None
    # Silent-skip when every triggers edge is fully internal (single-cap
    # flow — already covered by _mermaid_pipeline).
    if not external and all(
        f in behaviors_in and t in behaviors_in for f, t in trig_edges
    ):
        # Only skip if the standard flow diagram would fire; when the
        # capability doesn't have any actor entries, _mermaid_pipeline
        # returns None (see line ~494) even for a valid internal chain.
        # In that case, still emit the cross_flow diagram so the entity
        # isn't empty.
        pass  # fall through to render

    # Sub-capability owner map (for grouping internal behaviors).
    owner_of: dict[str, str] = {}
    for parent, kids in contains_out.items():
        if parent in caps_in:
            for k in kids:
                if k in behaviors_in:
                    owner_of[k] = parent

    refs: set[str] = set()
    lines = ["flowchart LR"]
    by_kind: dict[str, list[str]] = {}

    # External subgraph.
    if external:
        lines.append('  subgraph EXT["External (other capabilities)"]')
        lines.append("    direction TB")
        for eid in sorted(external):
            name = behs[eid].get("name", eid)
            lines.append(f'    {_mnode(eid, name, "behavior").strip()}')
            by_kind.setdefault("behavior", []).append(eid)
            refs.add(eid)
        lines.append("  end")

    # Per-sub-capability subgraph for internal behaviors.
    subcap_ids = sorted({owner_of.get(b, cap_id) for b in behaviors_in})
    for sc in subcap_ids:
        members = sorted(b for b in behaviors_in if owner_of.get(b, cap_id) == sc)
        if not members:
            continue
        sc_name = caps.get(sc, {}).get("name", sc)
        lines.append(f'  subgraph SC_{_mid(sc)}["{_mesc(sc)}: {_mesc(sc_name)}"]')
        lines.append("    direction TB")
        for bid in members:
            name = behs[bid].get("name", bid)
            lines.append(f'    {_mnode(bid, name, "behavior").strip()}')
            by_kind.setdefault("behavior", []).append(bid)
            refs.add(bid)
        lines.append("  end")

    # Edges (deterministic order).
    for f, t in sorted(set(trig_edges)):
        lines.append(f"  {_mid(f)} --> {_mid(t)}")

    _emit_class_defs(lines)
    _apply_classes(lines, by_kind, root_id=None)
    return "\n".join(lines), sorted(refs)


def _mermaid_constraint_impact(
    entities_by_kind: dict, relationships: list, cons_id: str
) -> tuple[str, list[str]] | None:
    """Constraint impact graph (2-hop walk).

    Extends the 1-hop constraint case in ``_mermaid_realization`` to show
    downstream impact: what specifically inside each constrained entity
    has to uphold the constraint. Walk:

    hop 1: ``ins_by(cons_id, "constrained-by")``
      \u2014 entities directly declaring they are constrained.
    hop 2 per hop-1 kind:
      capability   -> outbound ``contains`` (sub-caps / behaviors affected)
      component    -> outbound ``contains`` (sub-components affected)
      behavior     -> inbound ``traces-to``  (components that implement it)
      interface    -> inbound ``exposes``     (components exposing it)

    Returns ``None`` when hop 1 is empty. Silent-skip when hop 2 adds no
    new nodes (identical to what the 1-hop realization already shows).
    """
    flat = _all_entities_flat(entities_by_kind)
    if cons_id not in flat:
        return None
    ck, _ = flat[cons_id]
    if ck != "constraint":
        return None

    # Local edge maps.
    out_edges: dict[str, list[tuple[str, str]]] = {}
    in_edges: dict[str, list[tuple[str, str]]] = {}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type")
        if f is None or t is None or rt is None:
            continue
        out_edges.setdefault(f, []).append((t, rt))
        in_edges.setdefault(t, []).append((f, rt))

    def outs_by(eid: str, rtype: str) -> list[str]:
        return sorted({t for t, rt in out_edges.get(eid, []) if rt == rtype and t in flat})

    def ins_by(eid: str, rtype: str) -> list[str]:
        return sorted({s for s, rt in in_edges.get(eid, []) if rt == rtype and s in flat})

    hop1 = ins_by(cons_id, "constrained-by")
    if not hop1:
        return None

    edges: list[tuple[str, str, str]] = []
    for c in hop1:
        edges.append((c, cons_id, "constrained-by"))

    hop2_ids: list[str] = []
    for h in hop1:
        hk, _ = flat[h]
        if hk in ("capability", "component"):
            for kid in outs_by(h, "contains"):
                edges.append((h, kid, "contains"))
                hop2_ids.append(kid)
        elif hk == "behavior":
            for comp in ins_by(h, "traces-to"):
                edges.append((comp, h, "traces-to"))
                hop2_ids.append(comp)
        elif hk == "interface":
            for comp in ins_by(h, "exposes"):
                edges.append((comp, h, "exposes"))
                hop2_ids.append(comp)

    # Silent-skip: no hop2 nodes means this is identical to the 1-hop
    # realization view already rendered. Avoid duplicate cards.
    if not hop2_ids:
        return None

    edges = sorted(set(edges))
    node_ids = {cons_id} | set(hop1) | set(hop2_ids)

    lines = ["flowchart LR"]
    by_kind: dict[str, list[str]] = {}
    for nid in sorted(node_ids):
        nksing, nent = flat[nid]
        lines.append(_mnode(nid, nent.get("name", nid), nksing))
        by_kind.setdefault(nksing, []).append(nid)
    for f, t, lbl in edges:
        lines.append(f'  {_mid(f)} -->|{_mesc(lbl)}| {_mid(t)}')
    _emit_class_defs(lines)
    _apply_classes(lines, by_kind, root_id=cons_id)
    return "\n".join(lines), sorted(node_ids)


def _lint_edge_note_directions(relationships: list) -> list[dict]:
    """Direction-vs-note linter (L2 lesson from realizes-direction-fix).

    Scans every relationship for note-text patterns that describe the
    opposite direction of the stored edge. Returns a deterministic list
    of ``{from, to, type, note, warning}`` dicts. Empty list = clean.

    Patterns caught (case-insensitive on lowercased note):
      "<X> is realized by <Y>"    on edge X -> realizes -> Y   (expects Y -> X)
      "<X> depends on <Y>"        on edge Y -> depends-on -> X (expects X -> Y)
      "<X> is contained in <Y>"   on edge X -> contains -> Y   (expects Y -> X)
      "<X> exposes <Y>"           on edge Y -> exposes -> X    (expects X -> Y)

    IDs in the note are matched by substring on the stored ``from``/``to``
    ids, so both bare ids ("CAP-PB") and qualified references
    ("CAP-PB Extract") trigger the same rule.
    """
    warnings: list[dict] = []
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type")
        note = (r.get("note") or "").lower()
        if not (f and t and rt and note):
            continue
        f_l, t_l = str(f).lower(), str(t).lower()

        rules = [
            ("realizes",     f"{f_l} is realized by",  f"{t_l} realizes"),
            ("depends-on",   f"{t_l} depends on",       f"{f_l} depends on"),
            ("contains",     f"{f_l} is contained",     f"{t_l} contains"),
            ("exposes",      f"{t_l} exposes",          f"{f_l} exposes"),
        ]
        for rule_type, wrong_pattern, right_pattern in rules:
            if rt != rule_type:
                continue
            if wrong_pattern in note and right_pattern not in note:
                warnings.append({
                    "from": f, "to": t, "type": rt, "note": r.get("note", ""),
                    "warning": (
                        f"note text suggests {rule_type} direction is "
                        f"reversed (expected {t}->{f})"
                    ),
                })
                break
    return sorted(warnings, key=lambda w: (w["type"], w["from"], w["to"]))


def _realization_skip_reasons(
    entities_by_kind: dict,
    out_edges: dict,
    in_edges: dict,
) -> dict[str, str]:
    """Strict-realiz diagnostic: for every entity that has NO
    ``realization_mermaid`` populated but DOES have adjacent edges of the
    kind the walker examines, record a one-line reason. Used to surface
    systemic direction bugs (like the L9 realizes-direction fix) early.

    Returns ``{entity_id: reason}`` for skipped-with-signal entities. An
    entity truly disconnected from realization (no relevant edges at all)
    is NOT included \u2014 the walker's silent-skip is correct for those.
    """
    flat = _all_entities_flat(entities_by_kind)
    reasons: dict[str, str] = {}
    for eid, (kind, _) in flat.items():
        # Emulate the walker's hop-1 lookup without rendering.
        if kind == "capability":
            hop1 = [s for s, rt in in_edges.get(eid, []) if rt == "realizes"]
            if not hop1:
                # Signal case: capability has *outbound* realizes edges
                # (direction inverted, matches L9 bug shape).
                out_realizes = [t for t, rt in out_edges.get(eid, []) if rt == "realizes"]
                if out_realizes:
                    reasons[eid] = (
                        f"has outbound realizes to {sorted(out_realizes)} "
                        f"but walker expects inbound (see L9)"
                    )
        elif kind == "component":
            hop1 = [t for t, rt in out_edges.get(eid, []) if rt == "realizes"]
            if not hop1:
                in_realizes = [s for s, rt in in_edges.get(eid, []) if rt == "realizes"]
                if in_realizes:
                    reasons[eid] = (
                        f"has inbound realizes from {sorted(in_realizes)} "
                        f"but walker expects outbound"
                    )
    return dict(sorted(reasons.items()))


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
                # Normalize content to list[str] regardless of source shape.
                # Pipeline-emitted intent promises store docstrings as raw
                # strings; authored fragments use lists. Coercing here keeps
                # downstream JS shape-safe (no `.join()` on string errors).
                raw_c = p.get("content", [])
                if raw_c is None:
                    norm_c: list[str] = []
                elif isinstance(raw_c, str):
                    norm_c = [raw_c] if raw_c.strip() else []
                elif isinstance(raw_c, list):
                    norm_c = [str(x) for x in raw_c]
                else:
                    norm_c = [str(raw_c)]
                by_attr.setdefault(attr, []).append(
                    {
                        "id": p.get("id", ""),
                        "content": norm_c,
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
                            "content": norm_c,
                        }
                    )
            outs_typed = sorted({t for t, _ in out_edges.get(eid, [])})
            ins_typed = sorted({s for s, _ in in_edges.get(eid, [])})
            rec = {
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
            # Capability-scoped flow diagram (design principle: any
            # capability whose contained behaviors carry triggers edges
            # gets an inline Mermaid flow card in its entity page).
            if kind == "capabilities":
                flow = _mermaid_pipeline(entities_by_kind, relationships, eid)
                if flow is not None:
                    mmd, flow_refs = flow
                    rec["flow_mermaid"] = mmd
                    rec["flow_refs"] = flow_refs
                # Cross-capability flow (lifts _mermaid_pipeline beyond
                # a single containing capability). Populates CAP-DF-shaped
                # capabilities whose flow spans sub-capability boundaries.
                # Skip when identical to _mermaid_pipeline output.
                xflow = _mermaid_cross_capability_flow(
                    entities_by_kind, relationships, eid
                )
                if xflow is not None:
                    xmmd, xrefs = xflow
                    if rec.get("flow_mermaid") != xmmd:
                        rec["cross_flow_mermaid"] = xmmd
                        rec["cross_flow_refs"] = xrefs
            # Graph-walk-as-capability: three additional inline diagrams
            # stamped on every entity kind (silent skip when N/A).
            decomp = _mermaid_decomposition(entities_by_kind, relationships, eid)
            if decomp is not None:
                rec["decomposition_mermaid"], rec["decomposition_refs"] = decomp
            realiz = _mermaid_realization(
                entities_by_kind, relationships, eid, rec["kind"],
                out_edges, in_edges,
            )
            if realiz is not None:
                rec["realization_mermaid"], rec["realization_refs"] = realiz
            neigh = _mermaid_neighbors(
                entities_by_kind, relationships, eid,
                out_edges, in_edges,
            )
            if neigh is not None:
                rec["neighbors_mermaid"], rec["neighbors_refs"] = neigh
            # 6th walk: constraint impact (2-hop; extends the 1-hop
            # constraint case in _mermaid_realization). Silent-skip when
            # hop2 is empty (identical to realization view).
            if kind == "constraints":
                cimp = _mermaid_constraint_impact(
                    entities_by_kind, relationships, eid
                )
                if cimp is not None:
                    rec["constraint_impact_mermaid"], rec["constraint_impact_refs"] = cimp
            recs.append(rec)
        entity_records[kind] = recs

    # Build-time diagnostics (surface silent-skips + note-vs-edge
    # direction issues so systemic bugs like L9 fire early).
    direction_warnings = _lint_edge_note_directions(relationships)
    skip_reasons = _realization_skip_reasons(entities_by_kind, out_edges, in_edges)
    diagnostics = {
        "direction_warnings": direction_warnings,
        "realization_skip_reasons": skip_reasons,
    }
    # Print a one-line summary at build time (fail-soft; never blocks build).
    if direction_warnings:
        print(f"WARN: {len(direction_warnings)} note-vs-edge direction mismatch(es):")
        for w in direction_warnings:
            print(f"  [{w['type']}] {w['from']} -> {w['to']}: {w['warning']}")
    if skip_reasons:
        print(f"WARN: {len(skip_reasons)} entities silently skipped by realization walker:")
        for eid, reason in skip_reasons.items():
            print(f"  {eid}: {reason}")

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
        "diagnostics": diagnostics,
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
.content-text { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; margin-top:6px; word-break:break-word; color:var(--fg); white-space:pre-wrap; }
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
  // Event delegation: single listener survives re-renders and guarantees
  // every entity-link responds. Replaces per-element attachment which was
  // suspected of failing intermittently on component rows.
  host.addEventListener('click', (ev) => {
    const a = ev.target.closest('a.entity-link');
    if (a && host.contains(a)) {
      ev.preventDefault(); ev.stopPropagation();
      if (a.dataset.id) selectEntity(a.dataset.id);
      else if (a.dataset.se) showSEView(a.dataset.se);
      return;
    }
    const s = ev.target.closest('summary[data-kind]');
    if (s && host.contains(s)) {
      // Don't preventDefault — let <details> toggle naturally.
      showKindList(s.dataset.kind);
    }
  });
  // SE Views section lives OUTSIDE #entity-groups; wire separately.
  document.querySelectorAll('#sidebar .entity-link[data-se]').forEach(a => {
    a.addEventListener('click', (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      showSEView(a.dataset.se);
    });
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
  const diag = data.diagnostics || {};
  const dw = diag.direction_warnings || [];
  const sr = diag.realization_skip_reasons || {};
  const srKeys = Object.keys(sr);
  let diagBanner = '';
  if (dw.length || srKeys.length) {
    const dwRows = dw.map(w => `<li><code>[${w.type}] ${w.from} -> ${w.to}</code>: ${escapeHtml(w.warning)}</li>`).join('');
    const srRows = srKeys.map(k => `<li><code>${k}</code>: ${escapeHtml(sr[k])}</li>`).join('');
    diagBanner = `<div class="card" style="border-color:var(--warn,#c93);background:#3b2a10">` +
      `<h3>Build diagnostics (${dw.length + srKeys.length})</h3>` +
      (dw.length ? `<div style="font-size:11px;color:var(--muted);text-transform:uppercase;margin-top:6px">Note-vs-edge direction (${dw.length})</div><ul style="margin:4px 0 0 0;padding-left:20px;font-size:12px">${dwRows}</ul>` : '') +
      (srKeys.length ? `<div style="font-size:11px;color:var(--muted);text-transform:uppercase;margin-top:8px">Realization silent-skips (${srKeys.length})</div><ul style="margin:4px 0 0 0;padding-left:20px;font-size:12px">${srRows}</ul>` : '') +
      `</div>`;
  }
  document.getElementById('content').innerHTML = `
    <div class="breadcrumb">Overview</div>
    <h2 class="content-header">Architecture Model</h2>
    <div class="subtitle">${data.sources.length} source(s) &middot; ${data.totals.entities} entities across ${data.kinds_present.length} kinds</div>
    ${diagBanner}
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
  if (!e) {
    console.warn('selectEntity miss:', id, 'byId size:', Object.keys(byId).length);
    return;
  }
  try {
    highlightNav(null, id);
    const attrs = ['intent','delivers','provides'];
    let html = `<div class="breadcrumb"><a data-nav="overview">Overview</a> / ${e.kind}s / ${e.id}</div>`;
    html += `<h2 class="content-header">${escapeHtml(e.name)}</h2>`;
    html += `<div class="subtitle">${e.id} &middot; ${e.kind}${e.root_prefix ? ' &middot; '+escapeHtml(e.root_prefix) : ''}<span class="source-tag">from ${escapeHtml(e.source)}</span></div>`;
    html += `<div class="card"><h3>Summary</h3><div style="font-size:13px">${e.module_count} modules &middot; ${e.promise_count} promises &middot; ${e.gap_count} typed gaps</div></div>`;

    // Inline capability-scoped flow diagram (design principle: any
    // capability whose contained behaviors have triggers edges gets an
    // inline Mermaid flow card here). Rendered ABOVE promises because
    // the flow is the primary insight for pipeline-shaped capabilities.
    let flowDiagramId = null;
    if (e.kind === 'capability' && e.flow_mermaid) {
      flowDiagramId = `mmd-flow-${e.id}-${++_seRenderCounter}`;
      html += `<div class="card"><h3>Flow (contained behaviors)</h3>` +
              `<div class="mermaid-host" style="background:#0f172a;padding:12px;border-radius:6px;overflow-x:auto">` +
              `<div id="${flowDiagramId}" class="mermaid">${escapeHtml(e.flow_mermaid)}</div>` +
              `</div></div>`;
    }

    // Additional graph-walk cards (silent skip when field absent).
    function _walkCard(title, mmd, refs, slug) {
      if (!mmd) return { id: null, html: '' };
      const did = `mmd-${slug}-${e.id}-${++_seRenderCounter}`;
      const chips = (refs || []).map(id =>
        `<span class="chip" data-id="${id}">${id}</span>`
      ).join('');
      const html = `<div class="card"><h3>${title}</h3>` +
        `<div class="mermaid-host" style="background:#0f172a;padding:12px;border-radius:6px;overflow-x:auto">` +
        `<div id="${did}" class="mermaid">${escapeHtml(mmd)}</div></div>` +
        (chips ? `<div style="margin-top:8px;font-size:11px;color:var(--muted);text-transform:uppercase">Entities referenced (${(refs||[]).length})</div><div class="chips" style="margin-top:4px">${chips}</div>` : '') +
        `</div>`;
      return { id: did, html };
    }
    const decompCard = _walkCard('Decomposition (contains, ≤2 hops)', e.decomposition_mermaid, e.decomposition_refs, 'decomp');
    const realizCard = _walkCard('Realization chain', e.realization_mermaid, e.realization_refs, 'realiz');
    const xflowCard = _walkCard('Cross-capability flow (triggers)', e.cross_flow_mermaid, e.cross_flow_refs, 'xflow');
    const cimpCard = _walkCard('Constraint impact (2-hop)', e.constraint_impact_mermaid, e.constraint_impact_refs, 'cimp');
    html += xflowCard.html + cimpCard.html + decompCard.html + realizCard.html;

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

    const neighCard = _walkCard('Neighbors (1-hop, typed)', e.neighbors_mermaid, e.neighbors_refs, 'neigh');
    html += neighCard.html;

    html += `<div class="card"><h3>Neighbors</h3>`;
    html += `<div style="margin-bottom:6px;font-size:11px;color:var(--muted);text-transform:uppercase">Depends on (${e.outbound.length})</div><div class="chips" style="margin-bottom:12px">`;
    html += e.outbound.length ? e.outbound.map(id => `<span class="chip" data-id="${id}">${id}</span>`).join('') : '<span class="empty">none</span>';
    html += `</div><div style="margin-bottom:6px;font-size:11px;color:var(--muted);text-transform:uppercase">Depended on by (${e.inbound.length})</div><div class="chips">`;
    html += e.inbound.length ? e.inbound.map(id => `<span class="chip" data-id="${id}">${id}</span>`).join('') : '<span class="empty">none</span>';
    html += `</div></div>`;

    const noteVal = notes[e.id] || '';
    html += `<div class="card"><h3>Notes</h3>` +
      `<textarea class="notes" id="notes-${e.id}" placeholder="Human notes, questions, TODOs \u2014 persisted to notes.yaml via Save button.">${escapeHtml(noteVal)}</textarea>` +
      `<button class="save" id="save-btn">Save notes.yaml (download)</button>` +
      `<div style="margin-top:6px;font-size:11px;color:var(--muted)">Option A: browser downloads full notes.yaml. Place in <code>.architecture/viewers/notes.yaml</code> and rebuild.</div></div>`;

    document.getElementById('content').innerHTML = html;
    document.querySelectorAll('.chip').forEach(ch => ch.addEventListener('click', () => selectEntity(ch.dataset.id)));
    document.querySelectorAll('.breadcrumb a').forEach(a => a.addEventListener('click', () => {
      if (a.dataset.nav === 'overview') showOverview();
    }));
    const ta = document.getElementById(`notes-${e.id}`);
    if (ta) {
      ta.addEventListener('input', () => { notes[e.id] = ta.value; });
    }
    const saveBtn = document.getElementById('save-btn');
    if (saveBtn && ta) {
      saveBtn.addEventListener('click', () => {
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

    // Render inline Mermaid flow (after content injection so element exists).
    if (window.mermaid) {
      const targets = [
        [flowDiagramId, 'flow'],
        [xflowCard.id, 'cross_flow'],
        [cimpCard.id, 'constraint_impact'],
        [decompCard.id, 'decomposition'],
        [realizCard.id, 'realization'],
        [neighCard.id, 'neighbors'],
      ];
      for (const [did, tag] of targets) {
        if (!did) continue;
        const el = document.getElementById(did);
        if (!el) continue;
        mermaid.run({ nodes: [el] }).catch(err => {
          console.error(tag + ' mermaid render failed for', e.id, err);
          el.innerHTML = `<pre style="color:var(--muted);font-size:11px">Mermaid error: ${escapeHtml(String(err))}</pre>`;
        });
      }
    }
  } catch (err) {
    console.error('selectEntity render failed for', id, err);
    document.getElementById('content').innerHTML =
      `<div class="card"><h2>Render error</h2><div class="subtitle">${escapeHtml(id)}</div>` +
      `<pre style="color:var(--muted);white-space:pre-wrap">${escapeHtml(String(err && err.stack || err))}</pre></div>`;
  }
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
