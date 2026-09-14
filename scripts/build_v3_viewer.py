"""build_v3_viewer — v3-native single-file HTML viewer builder (T0.14 follow-up).

Reads ``.architecture-model.v3.yaml`` and emits
``.architecture/viewers/v3_viewer.html`` — a single self-contained
HTML file that renders the v3 Promise-graph model with:

- Top frame line stating what the viewer is showing.
- Left rail: component list (sortable by promise count / by id / by name),
  with search box and "show only components with typed gaps" filter.
- Center: selected component detail — Promises grouped by attribute
  (intent / delivers / provides), each with a status badge and hover
  provenance.
- Right: depends-on neighbors (outbound + inbound) as clickable links.

Vanilla JS, offline, deterministic. Palette copied from the pipeline
dashboard convention (green/yellow/red) so all AMS viewers share a
visual house style.

Usage::

    python scripts/build_v3_viewer.py

Writes both a JSON payload sidecar (for debugging) and the HTML.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MODEL = REPO / ".architecture-model.v3.yaml"
OUT_DIR = REPO / ".architecture" / "viewers"
OUT_HTML = OUT_DIR / "v3_viewer.html"
OUT_JSON = OUT_DIR / "v3_viewer_data.json"


STATUS_CLASS = {
    "verified": "ok",
    "open": "warn",
    "typed-gap": "error",
}


def _build_payload(model: dict) -> dict:
    comps = model.get("entities", {}).get("components", [])
    rels = model.get("relationships", [])

    # Precompute neighbor maps once so client code is trivial.
    out_edges: dict[str, list[str]] = {c["id"]: [] for c in comps}
    in_edges: dict[str, list[str]] = {c["id"]: [] for c in comps}
    for r in rels:
        f, t = r.get("from"), r.get("to")
        if f in out_edges and t is not None:
            out_edges[f].append(t)
        if t in in_edges and f is not None:
            in_edges[t].append(f)

    comp_records = []
    for c in comps:
        promises = c.get("promises", []) or []
        by_attr: dict[str, list[dict]] = {}
        gap_count = 0
        for p in promises:
            attr = p.get("attribute", "other")
            by_attr.setdefault(attr, []).append(
                {
                    "id": p["id"],
                    "content": p.get("content", []),
                    "status": p.get("status", "open"),
                    "gap_type": p.get("gap_type"),
                    "provenance": p.get("provenance", ""),
                }
            )
            if p.get("status") == "typed-gap":
                gap_count += 1
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

    meta = model.get("meta", {})
    totals = {
        "components": len(comp_records),
        "promises": sum(r["promise_count"] for r in comp_records),
        "gaps": sum(r["gap_count"] for r in comp_records),
        "relationships": len(rels),
    }
    return {"meta": meta, "totals": totals, "components": comp_records}


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
  --panel: #ffffff;
}
* { box-sizing: border-box; }
body { margin:0; font:14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--fg); background:var(--bg); }
header { padding:12px 20px; background:var(--panel); border-bottom:1px solid var(--border); }
header h1 { margin:0 0 4px; font-size:16px; }
header .frame { color:var(--muted); font-size:12px; }
header .totals { margin-top:6px; font-size:12px; color:var(--muted); }
header .totals b { color:var(--fg); }
main { display:grid; grid-template-columns: 260px 1fr 240px; height: calc(100vh - 76px); }
#rail { border-right:1px solid var(--border); background:var(--panel); overflow-y:auto; }
#rail .controls { padding:10px; border-bottom:1px solid var(--border); }
#rail input, #rail select { width:100%; margin-bottom:6px; padding:4px 6px; font:inherit; border:1px solid var(--border); border-radius:4px; }
#rail label { font-size:12px; color:var(--muted); display:flex; gap:6px; align-items:center; }
#rail ul { list-style:none; padding:0; margin:0; }
#rail li { padding:8px 12px; border-bottom:1px solid #f0f2f4; cursor:pointer; }
#rail li:hover { background:#f6f8fa; }
#rail li.active { background:#ddf4ff; }
#rail li .cid { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:11px; color:var(--muted); }
#rail li .cname { font-weight:600; }
#rail li .cstats { font-size:11px; color:var(--muted); margin-top:2px; }
#detail { padding:16px 24px; overflow-y:auto; }
#detail h2 { margin:0 0 4px; }
#detail .prefix { color:var(--muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; }
#detail .attr-group { margin-top:14px; }
#detail .attr-group h3 { margin:0 0 6px; font-size:13px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
#detail .prom { padding:8px 10px; border:1px solid var(--border); border-radius:6px; margin-bottom:6px; background:var(--panel); }
#detail .prom .row { display:flex; gap:8px; align-items:center; }
#detail .pid { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:11px; color:var(--muted); }
#detail .content { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; }
.badge { padding:1px 6px; border-radius:10px; font-size:11px; font-weight:600; }
.badge.ok    { background:var(--ok-bg);    color:var(--ok); }
.badge.warn  { background:var(--warn-bg);  color:var(--warn); }
.badge.error { background:var(--error-bg); color:var(--error); }
.badge.gap { background:var(--error-bg); color:var(--error); margin-left:4px; }
#detail .prov { display:none; font-size:11px; color:var(--muted); margin-top:4px; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
#detail .prom:hover .prov { display:block; }
#neighbors { border-left:1px solid var(--border); background:var(--panel); overflow-y:auto; padding:12px; }
#neighbors h3 { margin:0 0 6px; font-size:13px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); }
#neighbors ul { list-style:none; padding:0; margin:0 0 14px 0; }
#neighbors li { padding:4px 6px; cursor:pointer; border-radius:4px; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:12px; }
#neighbors li:hover { background:#f6f8fa; }
.empty { color:var(--muted); font-style:italic; font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>AMS v3 Viewer</h1>
  <div class="frame">What you're looking at: AMS's own architecture, extracted using the v3 standard + pipeline_v3 tooling. Same tooling applies to any Python codebase.</div>
  <div class="totals">
    <b id="t-comps">–</b> components ·
    <b id="t-proms">–</b> promises ·
    <b id="t-gaps">–</b> typed gaps ·
    <b id="t-rels">–</b> depends-on edges ·
    schema <b id="t-schema">–</b>
  </div>
</header>
<main>
  <aside id="rail">
    <div class="controls">
      <input id="q" placeholder="Search id or name…" />
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
  <section id="detail"><p class="empty">Select a component from the left rail.</p></section>
  <aside id="neighbors">
    <h3>Depends-on (outbound)</h3>
    <ul id="out"><li class="empty">–</li></ul>
    <h3>Depended-on by (inbound)</h3>
    <ul id="in"><li class="empty">–</li></ul>
  </aside>
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
document.getElementById('t-schema').textContent = (data.meta || {}).schema_version || '–';

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
      `<div class="cstats">${c.promise_count} promises · ${c.gap_count} gaps · ${c.module_count} modules</div>`;
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
  let html = `<h2>${c.name}</h2><div class="prefix">${c.id} · ${c.root_prefix}</div>`;
  html += `<div class="cstats" style="color:var(--muted);margin-top:6px;font-size:12px">${c.module_count} modules · ${c.promise_count} promises · ${c.gap_count} typed gaps</div>`;
  for (const attr of attrs) {
    const rows = (c.by_attr[attr] || []);
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
  // any other attributes
  for (const attr of Object.keys(c.by_attr)) {
    if (attrs.includes(attr)) continue;
    const rows = c.by_attr[attr];
    html += `<div class="attr-group"><h3>${attr} (${rows.length})</h3>`;
    for (const p of rows) {
      html += `<div class="prom"><div class="row">${badge(p.status)}<span class="pid">${p.id}</span></div>` +
              `<div class="content">${(p.content || []).join(', ')}</div></div>`;
    }
    html += `</div>`;
  }
  el.innerHTML = html;
}

function renderNeighbors(cid) {
  const c = byId[cid];
  const outUl = document.getElementById('out');
  const inUl = document.getElementById('in');
  outUl.innerHTML = '';
  inUl.innerHTML = '';
  const mk = (id) => {
    const li = document.createElement('li');
    const label = (byId[id] || {}).name || id;
    li.textContent = `${id} · ${label}`;
    li.addEventListener('click', () => selectComponent(id));
    return li;
  };
  if (!c || !c.outbound.length) outUl.innerHTML = '<li class="empty">–</li>';
  else c.outbound.forEach(id => outUl.appendChild(mk(id)));
  if (!c || !c.inbound.length) inUl.innerHTML = '<li class="empty">–</li>';
  else c.inbound.forEach(id => inUl.appendChild(mk(id)));
}

function selectComponent(cid) {
  selected = cid;
  renderList();
  renderDetail(cid);
  renderNeighbors(cid);
}

document.getElementById('q').addEventListener('input', renderList);
document.getElementById('sort').addEventListener('change', renderList);
document.getElementById('gaps-only').addEventListener('change', renderList);
renderList();
</script>
</body>
</html>
"""


def build() -> None:
    if not MODEL.exists():
        print(f"error: {MODEL} not found — run pipeline_v3 first", file=sys.stderr)
        sys.exit(2)
    with open(MODEL, "r", encoding="utf-8") as fh:
        model = yaml.safe_load(fh)
    payload = _build_payload(model)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    # Embed as JSON literal; safe because we sort_keys and there are no </script> sequences.
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
    print(f"open: file://{OUT_HTML}")


if __name__ == "__main__":
    build()
