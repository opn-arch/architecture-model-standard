"""build_v3_viewer — v3-native single-file HTML viewer builder (T0.14 follow-up).

Reads a v3 model YAML (default ``.architecture-model.v3.yaml``) and
emits ``.architecture/viewers/v3_viewer.html`` — a single self-contained
HTML file that renders the v3 Promise-graph model.

Model-first: the viewer subsystem is itself modeled in
``.architecture/viewers/viewer.v3.yaml`` as ``COMP-VIEWER`` with
declared ``delivers`` promises (D1..D7). This script's job is to
satisfy each promise. Any promise not satisfied should be flipped to
``status: typed-gap`` in that file (dogfooding the standard).

Satisfied promises:

- PR-VIEWER-D1 overview_landing — landing tab with totals, status +
  gap-type histograms, and top-5 tables.
- PR-VIEWER-D2 dependency_graph_visual — inline SVG circular layout
  with clickable nodes and hover edge highlighting.
- PR-VIEWER-D3 component_detail_with_promises — promises grouped by
  attribute (intent / delivers / provides) with badges and provenance.
- PR-VIEWER-D4 gap_index_view — flat gap table grouped by gap_type
  with clickable owner rows.
- PR-VIEWER-D5 se_level_navigation — tab bar (Overview / Graph /
  Components / Gaps) mirrors SE walk levels.
- PR-VIEWER-D6 inbound_outbound_neighbors_inline — neighbors rendered
  as chips inside the component detail card, not in a wasted rail.
- PR-VIEWER-D7 component_search_and_filter — search box + sort +
  gaps-only filter in the Components tab.
- PR-VIEWER-P1 single_file_html — one HTML file, no external assets.
- PR-VIEWER-P2 offline_deterministic — sort_keys=True on embedded
  JSON; deterministic circular layout from sorted order.
- PR-VIEWER-P3 repo_agnostic — optional argv model path.

Palette copied from the pipeline dashboard convention (green/amber/red)
so all AMS viewers share a visual house style.

Usage::

    python scripts/build_v3_viewer.py [model_path]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = REPO / ".architecture-model.v3.yaml"
OUT_DIR = REPO / ".architecture" / "viewers"
OUT_HTML = OUT_DIR / "v3_viewer.html"
OUT_JSON = OUT_DIR / "v3_viewer_data.json"


def _build_payload(model: dict) -> dict:
    comps = model.get("entities", {}).get("components", [])
    rels = model.get("relationships", [])

    # Neighbor maps
    out_edges: dict[str, list[str]] = {c["id"]: [] for c in comps}
    in_edges: dict[str, list[str]] = {c["id"]: [] for c in comps}
    for r in rels:
        f, t = r.get("from"), r.get("to")
        if f in out_edges and t is not None:
            out_edges[f].append(t)
        if t in in_edges and f is not None:
            in_edges[t].append(f)

    status_hist: dict[str, int] = {"verified": 0, "open": 0, "typed-gap": 0}
    gap_type_hist: dict[str, int] = {}
    gap_flat: list[dict] = []

    comp_records = []
    for c in comps:
        promises = c.get("promises", []) or []
        by_attr: dict[str, list[dict]] = {}
        gap_count = 0
        for p in promises:
            attr = p.get("attribute", "other")
            status = p.get("status", "open")
            gtype = p.get("gap_type")
            by_attr.setdefault(attr, []).append(
                {
                    "id": p["id"],
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
                        "owner": c["id"],
                        "owner_name": c.get("name", c["id"]),
                        "promise_id": p["id"],
                        "attribute": attr,
                        "gap_type": gtype,
                        "content": p.get("content", []),
                    }
                )
        comp_records.append(
            {
                "id": c["id"],
                "name": c.get("name", c["id"]),
                "root_prefix": c.get("root_prefix", ""),
                "module_count": len(c.get("module_names", []) or []),
                "promise_count": len(promises),
                "gap_count": gap_count,
                "by_attr": by_attr,
                "outbound": sorted(set(out_edges.get(c["id"], []))),
                "inbound": sorted(set(in_edges.get(c["id"], []))),
            }
        )

    comp_records.sort(key=lambda r: r["id"])

    # Deterministic circular layout for the dependency graph.
    n = len(comp_records)
    cx, cy, r_ = 400.0, 360.0, 300.0
    graph_nodes = []
    for i, c in enumerate(comp_records):
        theta = (2.0 * math.pi * i) / max(n, 1) - math.pi / 2.0
        graph_nodes.append(
            {
                "id": c["id"],
                "name": c["name"],
                "x": round(cx + r_ * math.cos(theta), 2),
                "y": round(cy + r_ * math.sin(theta), 2),
                "promise_count": c["promise_count"],
                "gap_count": c["gap_count"],
            }
        )
    edge_seen = set()
    graph_edges = []
    for r in rels:
        f, t = r.get("from"), r.get("to")
        if f is None or t is None:
            continue
        key = (f, t)
        if key in edge_seen:
            continue
        edge_seen.add(key)
        graph_edges.append({"from": f, "to": t})
    graph_edges.sort(key=lambda e: (e["from"], e["to"]))

    # Top-N summaries for the overview tab.
    top_by_promises = sorted(
        comp_records, key=lambda c: (-c["promise_count"], c["id"])
    )[:5]
    top_by_gaps = sorted(
        comp_records, key=lambda c: (-c["gap_count"], c["id"])
    )[:5]
    top_by_promises = [
        {"id": c["id"], "name": c["name"], "promise_count": c["promise_count"]}
        for c in top_by_promises
    ]
    top_by_gaps = [
        {"id": c["id"], "name": c["name"], "gap_count": c["gap_count"]}
        for c in top_by_gaps
    ]

    gap_flat.sort(key=lambda g: (g["gap_type"], g["owner"], g["promise_id"]))

    meta = model.get("meta", {})
    totals = {
        "components": len(comp_records),
        "promises": sum(r["promise_count"] for r in comp_records),
        "gaps": sum(r["gap_count"] for r in comp_records),
        "relationships": len(rels),
    }
    return {
        "meta": meta,
        "totals": totals,
        "status_hist": status_hist,
        "gap_type_hist": gap_type_hist,
        "top_by_promises": top_by_promises,
        "top_by_gaps": top_by_gaps,
        "graph": {"nodes": graph_nodes, "edges": graph_edges},
        "gaps": gap_flat,
        "components": comp_records,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>AMS v3 Viewer</title>
<style>
:root {
  --bg: #fafbfc; --fg: #1f2328; --muted: #57606a; --border: #d0d7de;
  --ok: #1a7f37; --ok-bg: #dafbe1;
  --warn: #9a6700; --warn-bg: #fff8c5;
  --error: #cf222e; --error-bg: #ffebe9;
  --panel: #ffffff; --accent: #0969da; --accent-bg: #ddf4ff;
}
* { box-sizing: border-box; }
body { margin:0; font:14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--fg); background:var(--bg); }
header { padding:12px 20px; background:var(--panel); border-bottom:1px solid var(--border); }
header h1 { margin:0 0 4px; font-size:16px; }
header .frame { color:var(--muted); font-size:12px; }
header .totals { margin-top:6px; font-size:12px; color:var(--muted); }
header .totals b { color:var(--fg); }
nav.tabs { display:flex; gap:0; background:var(--panel); border-bottom:1px solid var(--border); padding:0 12px; }
nav.tabs button { background:transparent; border:0; border-bottom:2px solid transparent; padding:10px 16px; font:inherit; color:var(--muted); cursor:pointer; }
nav.tabs button.active { color:var(--accent); border-bottom-color:var(--accent); font-weight:600; }
nav.tabs button:hover { color:var(--fg); }
main { height: calc(100vh - 130px); overflow:hidden; }
.tab { display:none; height:100%; overflow-y:auto; }
.tab.active { display:block; }

/* Overview */
#tab-overview { padding:20px 24px; }
.grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:20px; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px; }
.card h3 { margin:0 0 12px; font-size:13px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
.bar-row { display:grid; grid-template-columns: 100px 1fr 50px; gap:8px; align-items:center; margin-bottom:6px; font-size:12px; }
.bar-row .label { font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.bar-row .bar { height:14px; border-radius:3px; }
.bar-row .num { text-align:right; color:var(--muted); font-variant-numeric: tabular-nums; }
.bar.ok { background:var(--ok); }
.bar.warn { background:var(--warn); }
.bar.error { background:var(--error); }
.bar.neutral { background:var(--accent); }
table.tops { width:100%; border-collapse:collapse; font-size:12px; }
table.tops td { padding:4px 6px; border-bottom:1px solid #f0f2f4; }
table.tops td.cid { font-family: ui-monospace, "SF Mono", Menlo, monospace; color:var(--muted); width:130px; }
table.tops td.num { text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; width:50px; }
table.tops tr { cursor:pointer; }
table.tops tr:hover td { background:#f6f8fa; }

/* Graph */
#tab-graph { padding:16px; }
#tab-graph .wrap { display:grid; grid-template-columns: 1fr 260px; gap:16px; height:100%; }
#svg-wrap { background:var(--panel); border:1px solid var(--border); border-radius:8px; overflow:hidden; }
svg { display:block; width:100%; height:100%; }
svg .edge { stroke:#d0d7de; stroke-width:1; fill:none; }
svg .edge.hi { stroke:var(--accent); stroke-width:2; }
svg .node circle { stroke:#24292f; stroke-width:1; cursor:pointer; }
svg .node.g0 circle { fill:#dafbe1; }
svg .node.g1 circle { fill:#fff8c5; }
svg .node.g2 circle { fill:#ffebe9; }
svg .node text { font: 9px ui-monospace, "SF Mono", Menlo, monospace; pointer-events:none; fill:#24292f; }
svg .node.hi circle { stroke:var(--accent); stroke-width:2.5; }
#graph-side .card { margin-bottom:12px; }
#graph-side .legend div { display:flex; align-items:center; gap:8px; font-size:12px; margin-bottom:4px; }
#graph-side .legend span.sw { width:12px; height:12px; border-radius:50%; display:inline-block; border:1px solid #24292f; }
#graph-hover { font-size:12px; color:var(--muted); min-height:60px; }
#graph-hover b { color:var(--fg); }

/* Components */
#tab-components { display:none; grid-template-columns: 300px 1fr; height:100%; }
#tab-components.active { display:grid; }
#rail { border-right:1px solid var(--border); background:var(--panel); overflow-y:auto; }
#rail .controls { padding:10px; border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--panel); }
#rail input, #rail select { width:100%; margin-bottom:6px; padding:4px 6px; font:inherit; border:1px solid var(--border); border-radius:4px; }
#rail label { font-size:12px; color:var(--muted); display:flex; gap:6px; align-items:center; }
#rail ul { list-style:none; padding:0; margin:0; }
#rail li { padding:8px 12px; border-bottom:1px solid #f0f2f4; cursor:pointer; }
#rail li:hover { background:#f6f8fa; }
#rail li.active { background:var(--accent-bg); }
#rail li .cid { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:11px; color:var(--muted); }
#rail li .cname { font-weight:600; }
#rail li .cstats { font-size:11px; color:var(--muted); margin-top:2px; }
#detail { padding:16px 24px; overflow-y:auto; }
#detail h2 { margin:0 0 4px; }
#detail .prefix { color:var(--muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; }
#detail .attr-group { margin-top:14px; }
#detail .attr-group h3 { margin:0 0 6px; font-size:13px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
#detail .prom { padding:8px 10px; border:1px solid var(--border); border-radius:6px; margin-bottom:6px; background:var(--panel); }
#detail .prom .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
#detail .pid { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:11px; color:var(--muted); }
#detail .content { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; margin-top:4px; word-break:break-word; }
#detail .prov { display:none; font-size:11px; color:var(--muted); margin-top:4px; font-family: ui-monospace, "SF Mono", Menlo, monospace; white-space:pre-wrap; }
#detail .prom:hover .prov { display:block; }
#detail .neighbors { margin-top:18px; padding-top:12px; border-top:1px solid var(--border); }
#detail .neighbors h3 { font-size:13px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); margin:0 0 6px; }
#detail .chips { display:flex; flex-wrap:wrap; gap:4px; margin-bottom:10px; }
.chip { display:inline-block; padding:2px 8px; border-radius:12px; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:11px; cursor:pointer; background:#f6f8fa; border:1px solid var(--border); color:var(--fg); }
.chip:hover { background:var(--accent-bg); border-color:var(--accent); }
.chip.neutral { background:#f6f8fa; }

/* Gaps */
#tab-gaps { padding:20px 24px; }
#tab-gaps h3 { margin:16px 0 8px; font-size:13px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
table.gaps { width:100%; border-collapse:collapse; font-size:12px; background:var(--panel); border:1px solid var(--border); border-radius:6px; overflow:hidden; }
table.gaps th, table.gaps td { padding:6px 10px; text-align:left; border-bottom:1px solid #f0f2f4; }
table.gaps th { background:#f6f8fa; font-size:11px; text-transform:uppercase; color:var(--muted); }
table.gaps tr:hover td { background:#f6f8fa; cursor:pointer; }
table.gaps td.cid, table.gaps td.pid { font-family: ui-monospace, "SF Mono", Menlo, monospace; color:var(--muted); }

.badge { padding:1px 6px; border-radius:10px; font-size:11px; font-weight:600; }
.badge.ok    { background:var(--ok-bg);    color:var(--ok); }
.badge.warn  { background:var(--warn-bg);  color:var(--warn); }
.badge.error { background:var(--error-bg); color:var(--error); }
.badge.gap   { background:var(--error-bg); color:var(--error); }
.empty { color:var(--muted); font-style:italic; font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>AMS v3 Viewer</h1>
  <div class="frame">Modeled by <code>.architecture/viewers/viewer.v3.yaml</code> (COMP-VIEWER). Shows AMS's own v3 model — same tooling applies to any Python codebase.</div>
  <div class="totals">
    <b id="t-comps">-</b> components &middot;
    <b id="t-proms">-</b> promises &middot;
    <b id="t-gaps">-</b> typed gaps &middot;
    <b id="t-rels">-</b> depends-on edges &middot;
    schema <b id="t-schema">-</b>
  </div>
</header>
<nav class="tabs">
  <button data-tab="overview" class="active">Overview</button>
  <button data-tab="graph">Graph</button>
  <button data-tab="components">Components</button>
  <button data-tab="gaps">Gaps</button>
</nav>
<main>
  <section id="tab-overview" class="tab active">
    <div class="grid2">
      <div class="card">
        <h3>Promise status distribution</h3>
        <div id="status-bars"></div>
      </div>
      <div class="card">
        <h3>Typed-gap distribution</h3>
        <div id="gaptype-bars"></div>
      </div>
      <div class="card">
        <h3>Top 5 components by promise count</h3>
        <table class="tops" id="top-proms"></table>
      </div>
      <div class="card">
        <h3>Top 5 components by typed-gap count</h3>
        <table class="tops" id="top-gaps"></table>
      </div>
    </div>
  </section>
  <section id="tab-graph" class="tab">
    <div class="wrap">
      <div id="svg-wrap">
        <svg id="graph" viewBox="0 0 800 720" preserveAspectRatio="xMidYMid meet"></svg>
      </div>
      <div id="graph-side">
        <div class="card legend">
          <h3>Legend</h3>
          <div><span class="sw" style="background:#dafbe1"></span> 0 typed gaps</div>
          <div><span class="sw" style="background:#fff8c5"></span> 1-3 typed gaps</div>
          <div><span class="sw" style="background:#ffebe9"></span> 4+ typed gaps</div>
          <div style="margin-top:6px;color:var(--muted);font-size:11px">Hover to highlight edges. Click to open component detail.</div>
        </div>
        <div class="card">
          <h3>Hover</h3>
          <div id="graph-hover"><span class="empty">Hover a node.</span></div>
        </div>
      </div>
    </div>
  </section>
  <section id="tab-components" class="tab">
    <aside id="rail">
      <div class="controls">
        <input id="q" placeholder="Search id or name..." />
        <select id="sort">
          <option value="id">Sort: id</option>
          <option value="name">Sort: name</option>
          <option value="promise_count">Sort: promise count</option>
          <option value="gap_count">Sort: gap count</option>
        </select>
        <label><input type="checkbox" id="gaps-only" /> gaps only</label>
      </div>
      <ul id="comp-list"></ul>
    </aside>
    <section id="detail"><p class="empty">Select a component from the left rail, or click one on the Graph tab.</p></section>
  </section>
  <section id="tab-gaps" class="tab">
    <div id="gap-groups"></div>
  </section>
</main>
<script id="v3-data" type="application/json">__PAYLOAD__</script>
<script>
const data = JSON.parse(document.getElementById('v3-data').textContent);
const byId = Object.fromEntries(data.components.map(c => [c.id, c]));
let selected = null;

document.getElementById('t-comps').textContent = data.totals.components;
document.getElementById('t-proms').textContent = data.totals.promises;
document.getElementById('t-gaps').textContent  = data.totals.gaps;
document.getElementById('t-rels').textContent  = data.totals.relationships;
document.getElementById('t-schema').textContent = (data.meta || {}).schema_version || '-';

// --- Tabs ---
function switchTab(name) {
  document.querySelectorAll('nav.tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.id === 'tab-' + name));
}
document.querySelectorAll('nav.tabs button').forEach(b => {
  b.addEventListener('click', () => switchTab(b.dataset.tab));
});

// --- Overview ---
function renderOverview() {
  const sh = data.status_hist || {};
  const total = Math.max(1, (sh.verified||0) + (sh.open||0) + (sh['typed-gap']||0));
  const rows = [
    ['verified', sh.verified||0, 'ok'],
    ['open', sh.open||0, 'warn'],
    ['typed-gap', sh['typed-gap']||0, 'error'],
  ];
  document.getElementById('status-bars').innerHTML = rows.map(([label, n, cls]) => {
    const pct = (n/total*100).toFixed(1);
    return `<div class="bar-row"><div class="label">${label}</div><div class="bar ${cls}" style="width:${pct}%"></div><div class="num">${n}</div></div>`;
  }).join('');

  const gh = data.gap_type_hist || {};
  const keys = Object.keys(gh).sort((a,b) => gh[b]-gh[a] || a.localeCompare(b));
  const gtotal = Math.max(1, keys.reduce((s,k) => s+gh[k], 0));
  if (!keys.length) {
    document.getElementById('gaptype-bars').innerHTML = '<span class="empty">No typed gaps.</span>';
  } else {
    document.getElementById('gaptype-bars').innerHTML = keys.map(k => {
      const pct = (gh[k]/gtotal*100).toFixed(1);
      return `<div class="bar-row"><div class="label">${k}</div><div class="bar neutral" style="width:${pct}%"></div><div class="num">${gh[k]}</div></div>`;
    }).join('');
  }

  const tp = document.getElementById('top-proms');
  tp.innerHTML = (data.top_by_promises || []).map(c =>
    `<tr data-id="${c.id}"><td class="cid">${c.id}</td><td>${c.name}</td><td class="num">${c.promise_count}</td></tr>`
  ).join('');
  tp.querySelectorAll('tr').forEach(tr => tr.addEventListener('click', () => {
    switchTab('components'); selectComponent(tr.dataset.id);
  }));

  const tg = document.getElementById('top-gaps');
  tg.innerHTML = (data.top_by_gaps || []).map(c =>
    `<tr data-id="${c.id}"><td class="cid">${c.id}</td><td>${c.name}</td><td class="num">${c.gap_count}</td></tr>`
  ).join('');
  tg.querySelectorAll('tr').forEach(tr => tr.addEventListener('click', () => {
    switchTab('components'); selectComponent(tr.dataset.id);
  }));
}

// --- Graph ---
function renderGraph() {
  const svg = document.getElementById('graph');
  const nodes = data.graph.nodes;
  const edges = data.graph.edges;
  const NS = 'http://www.w3.org/2000/svg';
  const posById = Object.fromEntries(nodes.map(n => [n.id, n]));

  // Edges
  const edgeEls = [];
  for (const e of edges) {
    const a = posById[e.from], b = posById[e.to];
    if (!a || !b) continue;
    const line = document.createElementNS(NS, 'line');
    line.setAttribute('x1', a.x); line.setAttribute('y1', a.y);
    line.setAttribute('x2', b.x); line.setAttribute('y2', b.y);
    line.setAttribute('class', 'edge');
    line.dataset.from = e.from; line.dataset.to = e.to;
    svg.appendChild(line);
    edgeEls.push(line);
  }
  // Nodes
  const nodeEls = {};
  for (const n of nodes) {
    const g = document.createElementNS(NS, 'g');
    const gc = n.gap_count >= 4 ? 'g2' : (n.gap_count >= 1 ? 'g1' : 'g0');
    g.setAttribute('class', 'node ' + gc);
    g.setAttribute('transform', `translate(${n.x},${n.y})`);
    const c = document.createElementNS(NS, 'circle');
    c.setAttribute('r', 14);
    g.appendChild(c);
    const t = document.createElementNS(NS, 'text');
    t.setAttribute('text-anchor', 'middle'); t.setAttribute('dy', 3);
    t.textContent = n.name.slice(0, 10);
    g.appendChild(t);
    const title = document.createElementNS(NS, 'title');
    title.textContent = `${n.id} ${n.name}\n${n.promise_count} promises, ${n.gap_count} typed gaps`;
    g.appendChild(title);
    g.addEventListener('mouseenter', () => hoverNode(n.id, edgeEls, nodeEls, true));
    g.addEventListener('mouseleave', () => hoverNode(n.id, edgeEls, nodeEls, false));
    g.addEventListener('click', () => { switchTab('components'); selectComponent(n.id); });
    svg.appendChild(g);
    nodeEls[n.id] = g;
  }
}
function hoverNode(id, edgeEls, nodeEls, on) {
  const hoverBox = document.getElementById('graph-hover');
  const c = byId[id];
  if (on && c) {
    hoverBox.innerHTML = `<b>${c.name}</b> <span style="color:var(--muted)">(${c.id})</span><br>` +
      `${c.promise_count} promises &middot; ${c.gap_count} typed gaps &middot; ${c.module_count} modules<br>` +
      `<span style="color:var(--muted)">${c.outbound.length} out &middot; ${c.inbound.length} in</span>`;
  } else if (!on) {
    hoverBox.innerHTML = '<span class="empty">Hover a node.</span>';
  }
  for (const el of edgeEls) {
    const match = (el.dataset.from === id) || (el.dataset.to === id);
    el.classList.toggle('hi', on && match);
  }
  const g = nodeEls[id];
  if (g) g.classList.toggle('hi', on);
}

// --- Components ---
function renderList() {
  const q = document.getElementById('q').value.toLowerCase();
  const sortKey = document.getElementById('sort').value;
  const gapsOnly = document.getElementById('gaps-only').checked;
  let items = data.components.slice();
  if (q) items = items.filter(c => c.id.toLowerCase().includes(q) || c.name.toLowerCase().includes(q));
  if (gapsOnly) items = items.filter(c => c.gap_count > 0);
  items.sort((a,b) => {
    if (sortKey === 'name') return a.name.localeCompare(b.name);
    if (sortKey === 'promise_count') return b.promise_count - a.promise_count;
    if (sortKey === 'gap_count') return b.gap_count - a.gap_count;
    return a.id.localeCompare(b.id);
  });
  const ul = document.getElementById('comp-list');
  ul.innerHTML = '';
  for (const c of items) {
    const li = document.createElement('li');
    li.dataset.id = c.id;
    if (selected === c.id) li.classList.add('active');
    li.innerHTML =
      `<div class="cname">${c.name}</div>` +
      `<div class="cid">${c.id}</div>` +
      `<div class="cstats">${c.promise_count} promises &middot; ${c.gap_count} gaps &middot; ${c.module_count} modules</div>`;
    li.addEventListener('click', () => selectComponent(c.id));
    ul.appendChild(li);
  }
}
function badge(status) {
  const cls = ({verified:'ok', open:'warn', 'typed-gap':'error'})[status] || 'warn';
  return `<span class="badge ${cls}">${status}</span>`;
}
function renderDetail(cid) {
  const c = byId[cid];
  const el = document.getElementById('detail');
  if (!c) { el.innerHTML = '<p class="empty">Unknown component.</p>'; return; }
  const attrs = ['intent','delivers','provides'];
  let html = `<h2>${c.name}</h2><div class="prefix">${c.id} &middot; ${c.root_prefix}</div>`;
  html += `<div style="color:var(--muted);margin-top:6px;font-size:12px">${c.module_count} modules &middot; ${c.promise_count} promises &middot; ${c.gap_count} typed gaps</div>`;
  const seen = new Set();
  for (const attr of attrs) {
    const rows = (c.by_attr[attr] || []);
    seen.add(attr);
    if (!rows.length) continue;
    html += `<div class="attr-group"><h3>${attr} (${rows.length})</h3>`;
    for (const p of rows) {
      const gap = p.gap_type ? `<span class="badge gap">${p.gap_type}</span>` : '';
      html += `<div class="prom"><div class="row">${badge(p.status)}${gap}<span class="pid">${p.id}</span></div>` +
              `<div class="content">${(p.content || []).join(', ') || '<span class="empty">(empty)</span>'}</div>` +
              `<div class="prov">${p.provenance || ''}</div></div>`;
    }
    html += `</div>`;
  }
  for (const attr of Object.keys(c.by_attr)) {
    if (seen.has(attr)) continue;
    const rows = c.by_attr[attr];
    html += `<div class="attr-group"><h3>${attr} (${rows.length})</h3>`;
    for (const p of rows) {
      html += `<div class="prom"><div class="row">${badge(p.status)}<span class="pid">${p.id}</span></div>` +
              `<div class="content">${(p.content || []).join(', ')}</div></div>`;
    }
    html += `</div>`;
  }
  // Neighbors inline (PR-VIEWER-D6)
  html += `<div class="neighbors"><h3>Depends-on (${c.outbound.length})</h3><div class="chips">`;
  html += c.outbound.length
    ? c.outbound.map(id => `<span class="chip neutral" data-id="${id}">${id}</span>`).join('')
    : '<span class="empty">none</span>';
  html += `</div><h3>Depended-on by (${c.inbound.length})</h3><div class="chips">`;
  html += c.inbound.length
    ? c.inbound.map(id => `<span class="chip neutral" data-id="${id}">${id}</span>`).join('')
    : '<span class="empty">none</span>';
  html += `</div></div>`;
  el.innerHTML = html;
  el.querySelectorAll('.chip').forEach(ch => ch.addEventListener('click', () => selectComponent(ch.dataset.id)));
}
function selectComponent(cid) {
  selected = cid;
  renderList();
  renderDetail(cid);
}

// --- Gaps ---
function renderGaps() {
  const groups = {};
  for (const g of (data.gaps || [])) {
    (groups[g.gap_type] = groups[g.gap_type] || []).push(g);
  }
  const keys = Object.keys(groups).sort((a,b) => groups[b].length - groups[a].length || a.localeCompare(b));
  const host = document.getElementById('gap-groups');
  if (!keys.length) { host.innerHTML = '<p class="empty">No typed gaps.</p>'; return; }
  host.innerHTML = keys.map(k => {
    const rows = groups[k].map(g =>
      `<tr data-id="${g.owner}"><td class="cid">${g.owner}</td><td>${g.owner_name}</td><td class="pid">${g.promise_id}</td><td>${g.attribute}</td></tr>`
    ).join('');
    return `<h3>${k} (${groups[k].length})</h3>` +
      `<table class="gaps"><thead><tr><th>Owner id</th><th>Owner name</th><th>Promise id</th><th>Attribute</th></tr></thead><tbody>${rows}</tbody></table>`;
  }).join('');
  host.querySelectorAll('tr[data-id]').forEach(tr => tr.addEventListener('click', () => {
    switchTab('components'); selectComponent(tr.dataset.id);
  }));
}

document.getElementById('q').addEventListener('input', renderList);
document.getElementById('sort').addEventListener('change', renderList);
document.getElementById('gaps-only').addEventListener('change', renderList);

renderOverview();
renderGraph();
renderList();
renderGaps();
</script>
</body>
</html>
"""


def build(model_path: Path | None = None) -> None:
    path = model_path or DEFAULT_MODEL
    if not path.exists():
        print(f"error: {path} not found - run pipeline_v3 first", file=sys.stderr)
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as fh:
        model = yaml.safe_load(fh)
    payload = _build_payload(model)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    embedded = json.dumps(payload, sort_keys=True)
    html = HTML_TEMPLATE.replace("__PAYLOAD__", embedded)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"wrote {OUT_HTML} ({OUT_HTML.stat().st_size} bytes)")
    print(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size} bytes)")
    print(
        f"totals: {payload['totals']['components']} components, "
        f"{payload['totals']['promises']} promises, "
        f"{payload['totals']['gaps']} gaps, "
        f"{payload['totals']['relationships']} edges"
    )
    print(f"status_hist: {payload['status_hist']}")
    print(f"gap_type_hist: {payload['gap_type_hist']}")
    print(f"open: file://{OUT_HTML}")


if __name__ == "__main__":
    arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    build(arg)
