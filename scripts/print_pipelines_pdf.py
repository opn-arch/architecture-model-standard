#!/usr/bin/env python
"""Generate a PDF of the 7 pipelines fragment with flow diagrams.

Reads:
    .architecture/model/pipelines.v3.yaml       — behaviors + relationships
    .architecture/model/pipeline-flow-annotations.yaml — rendering hints

Emits Markdown then invokes pandoc (xelatex) to render PDF.

Output:
    docs/reports/pipelines-v3.md
    docs/reports/pipelines-v3.pdf

Flow diagrams:
    - linear layout  → Unicode box-drawing in fenced monospace block
    - fanout layout  → TikZ (raw LaTeX embedded in markdown)

Markers on flow diagrams (from annotations file):
    L, LLM, SI&L                — current sites (solid)
    L*, LLM*, SI&L*             — proposed / design intent
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / ".architecture" / "model" / "pipelines.v3.yaml"
ANNO = REPO / ".architecture" / "model" / "pipeline-flow-annotations.yaml"
OUT_MD = REPO / "docs" / "reports" / "pipelines-v3.md"
OUT_PDF = REPO / "docs" / "reports" / "pipelines-v3.pdf"

TOPS = ["BEH-P1", "BEH-26", "BEH-27", "BEH-28", "BEH-LLM", "BEH-SIL", "BEH-FBK"]


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------
def _escape(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("_", r"\_")
        .replace("<", r"\textless{}")
        .replace(">", r"\textgreater{}")
    )


def _tex_escape(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


def _promise_row(prom: dict) -> str:
    attr = prom.get("attribute", "?")
    status = prom.get("status", "?")
    content = prom.get("content") or []
    if isinstance(content, list) and content:
        body = "; ".join(str(c).strip() for c in content)
    else:
        body = str(content or "")
    if len(body) > 220:
        body = body[:217] + "..."
    return f"- **{_escape(attr)}** *({status})* — {_escape(body)}"


# ---------------------------------------------------------------------------
# Linear ASCII flow renderer (Unicode box-drawing)
# ---------------------------------------------------------------------------
BOX_W = 18            # total width including borders
INNER = BOX_W - 2     # width available for text
GAP_ARROW = " → "     # 3 chars between boxes on the id row
GAP_SPACE = "   "     # 3 chars on other rows


def _linear_box(step: dict, cap: str) -> list[str]:
    inner = INNER
    name = str(step.get("short", "?"))[:inner].center(inner)
    sid = str(step.get("id", "?"))[:inner].center(inner)
    cap_line = cap[:inner].center(inner)
    comp = str(step.get("comp", "?"))[:inner].center(inner)
    return [
        "┌" + "─" * inner + "┐",
        "│" + name + "│",
        "│" + sid + "│",
        "│" + cap_line + "│",
        "│" + comp + "│",
        "└" + "─" * inner + "┘",
    ]


def _marker_cell(step: dict) -> str:
    markers = step.get("markers") or []
    if not markers:
        text = "·"
    else:
        text = ",".join(str(m) for m in markers)
    return text[:BOX_W].center(BOX_W)


def _join_boxes_row(steps: list[dict], cap: str) -> list[str]:
    boxes = [_linear_box(s, cap) for s in steps]
    height = len(boxes[0])
    out = [""] * height
    for i, box in enumerate(boxes):
        for r in range(height):
            out[r] += box[r]
        if i < len(boxes) - 1:
            for r in range(height):
                # id row is index 2 of the 6-row box; put arrow there
                out[r] += GAP_ARROW if r == 2 else GAP_SPACE
    # markers row aligned to each box center
    markers_row = ""
    for i, s in enumerate(steps):
        markers_row += _marker_cell(s)
        if i < len(steps) - 1:
            markers_row += GAP_SPACE
    out.append(markers_row)
    return out


def render_linear(flow: dict) -> str:
    steps = flow.get("steps") or []
    cap = flow.get("cap", "")
    wrap = int(flow.get("wrap", 5))
    lines: list[str] = []
    for chunk_start in range(0, len(steps), wrap):
        chunk = steps[chunk_start : chunk_start + wrap]
        row_lines = _join_boxes_row(chunk, cap)
        lines.extend(row_lines)
        if chunk_start + wrap < len(steps):
            # add continuation arrow row
            lines.append("")
            lines.append("↓".center(len(row_lines[0])))
            lines.append("")
    loop = flow.get("loopback")
    if loop:
        lines.append("")
        lines.append(f"  ⟲ loopback: {loop['from']} → {loop['to']}  ({loop.get('label','')})")
    # wrap in fenced code block
    return "```\n" + "\n".join(lines) + "\n```\n"


# ---------------------------------------------------------------------------
# TikZ fanout renderer (raw LaTeX embedded in markdown)
# ---------------------------------------------------------------------------
def render_fanout(flow: dict) -> str:
    hub_id = flow["pipeline"]
    cap = flow.get("cap", "")
    hub_comp = flow.get("hub_comp", "")
    leaves = flow.get("leaves") or []
    side_boxes = flow.get("side_boxes") or []
    n = len(leaves)
    # angles evenly around 360°
    step = 360.0 / n
    radius = 4.0

    parts: list[str] = []
    parts.append(r"\begin{center}")
    parts.append(
        r"\begin{tikzpicture}["
        r"every node/.style={draw, rounded corners, align=center, "
        r"font=\small, minimum height=1.0cm, minimum width=2.3cm, "
        r"inner sep=2pt}]"
    )
    hub_label = (
        f"{{\\bfseries {_tex_escape(hub_id)}}}\\\\"
        f"{_tex_escape(cap)}\\\\{_tex_escape(hub_comp)}"
    )
    parts.append(rf"  \node[fill=blue!10] (hub) at (0,0) {{{hub_label}}};")
    for i, leaf in enumerate(leaves):
        angle = step * i
        lid = _tex_escape(leaf["id"])
        name = _tex_escape(leaf.get("short", "?"))
        comp = _tex_escape(leaf.get("comp", ""))
        label = f"{{\\bfseries {lid}}}\\\\{name}\\\\{comp}"
        parts.append(
            rf"  \node (l{i}) at ({angle}:{radius}cm) {{{label}}};"
        )
        parts.append(rf"  \draw[-{{Latex}}] (hub) -- (l{i});")
    # side boxes below hub
    for j, sb in enumerate(side_boxes):
        x = -5 + j * 3.2
        y = -5.5
        parts.append(
            rf"  \node[fill=gray!10, font=\ttfamily\footnotesize] "
            rf"(sb{j}) at ({x},{y}) {{{_tex_escape(sb)}}};"
        )
        parts.append(rf"  \draw[dashed, -{{Latex}}] (hub) -- (sb{j});")
    parts.append(r"\end{tikzpicture}")
    parts.append(r"\end{center}")
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Full markdown build
# ---------------------------------------------------------------------------
def build_markdown(model: dict, anno: dict) -> str:
    behaviors = {
        b["id"]: b for b in model.get("entities", {}).get("behaviors", [])
    }
    rels = model.get("relationships", [])
    children: dict[str, list[str]] = {}
    for r in rels:
        if r.get("type") == "contains":
            children.setdefault(r["from"], []).append(r["to"])
    realizes: dict[str, str] = {}
    for r in rels:
        if r.get("type") == "realizes":
            realizes[r["from"]] = r["to"]

    flows_by_pipeline = {f["pipeline"]: f for f in anno.get("flows", [])}
    cap_gloss = anno.get("cap_glossary") or {}
    comp_gloss = anno.get("comp_glossary") or {}

    total = len(behaviors)
    total_prom = sum(len(b.get("promises") or []) for b in behaviors.values())
    verified = sum(
        1
        for b in behaviors.values()
        for p in (b.get("promises") or [])
        if p.get("status") == "verified"
    )

    L: list[str] = []
    # ---------- frontmatter ----------
    L += [
        "---",
        "title: AMS Operational Pipelines (v3 fragment)",
        f"subtitle: {total} behaviors, {len(rels)} relationships, 7 top-level pipelines",
        "author: architecture-model-standard",
        "date: 2026-09-20",
        "geometry: margin=0.7in",
        "fontsize: 10pt",
        "colorlinks: true",
        "header-includes:",
        "  - \\usepackage{tikz}",
        "  - \\usetikzlibrary{positioning,arrows.meta,shapes.geometric}",
        "  - \\usepackage{fancyvrb}",
        "---",
        "",
    ]

    # ---------- overview ----------
    L += [
        "# Overview",
        "",
        "Seven top-level operational pipelines defining AMS as a running system. "
        "Source: `.architecture/model/pipelines.v3.yaml`. "
        "Flow annotations: `.architecture/model/pipeline-flow-annotations.yaml`. "
        "Generated by `scripts/print_pipelines_pdf.py`.",
        "",
        "| Top | Name | Direct subs | Realizes |",
        "|---|---|---:|---|",
    ]
    for tid in TOPS:
        b = behaviors.get(tid)
        if not b:
            continue
        subs = children.get(tid, [])
        cap = realizes.get(tid, "—")
        L.append(
            f"| **{tid}** | `{_escape(b.get('name','?'))}` | {len(subs)} | {cap} |"
        )
    L += [
        "",
        f"**Coverage:** {total} behaviors, {total_prom} promises, "
        f"{verified} verified ({verified*100//max(total_prom,1)}%).",
        "",
    ]

    # ---------- legend ----------
    L += [
        "## Legend",
        "",
        "Flow diagrams overlay three marker kinds at each step. "
        "**Solid** markers (`L`, `LLM`, `SI&L`) indicate sites present in code today. "
        "**Starred** markers (`L*`, `LLM*`, `SI&L*`) are proposed / design intent — "
        "the aggregation view lets one diagram show reality overlaid with where the "
        "model should wire the next integration.",
        "",
        "| Marker | Meaning |",
        "|---|---|",
        "| `L` | Logging site (stdlib logging, journal writes, non-SI&L) |",
        "| `LLM` | LLM provider call site |",
        "| `SI&L` | SI&L instrumented site (`@sil_instrument` or `SILStore.append`) |",
        "| `*` suffix | Proposed / design intent, not yet in code |",
        "| `·` | No marker at this step |",
        "",
    ]

    # ---------- CAP glossary ----------
    if cap_gloss:
        L += ["## Capability glossary (CAP)", "", "| ID | Description |", "|---|---|"]
        for k, v in sorted(cap_gloss.items()):
            L.append(f"| `{k}` | {_escape(v)} |")
        L.append("")

    # ---------- COMP glossary ----------
    if comp_gloss:
        L += ["## Component glossary (COMP)", "", "| ID | Description |", "|---|---|"]
        for k, v in sorted(comp_gloss.items()):
            L.append(f"| `{k}` | {_escape(v)} |")
        L.append("")

    L += ["\\newpage", ""]

    # ---------- per-pipeline pages ----------
    for tid in TOPS:
        b = behaviors.get(tid)
        if not b:
            continue
        L += [f"# {tid} — {_escape(b.get('name',''))}", ""]
        # intent quote
        for p in b.get("promises") or []:
            if p.get("attribute") == "intent":
                content = p.get("content") or []
                if content:
                    L += [f"> {_escape(content[0])}", ""]
                break
        cap = realizes.get(tid)
        if cap:
            L += [f"**Realizes:** `{cap}`", ""]

        # flow diagram (before promises so it's on top of the page)
        flow = flows_by_pipeline.get(tid)
        if flow:
            layout = flow.get("layout")
            L += ["## Flow", ""]
            if layout == "linear":
                L += [render_linear(flow), ""]
            elif layout == "fanout":
                L += [render_fanout(flow), ""]
            else:
                L += [f"*Unknown layout: {layout}*", ""]

        # promises
        L += ["## Promises", ""]
        for p in b.get("promises") or []:
            L.append(_promise_row(p))
        L.append("")

        # subs
        subs = children.get(tid, [])
        if subs:
            L += [f"## Direct sub-behaviors ({len(subs)})", ""]
            L += ["| ID | Name | Intent |", "|---|---|---|"]
            for sid in subs:
                sb = behaviors.get(sid)
                if not sb:
                    L.append(f"| {sid} | *(missing)* | |")
                    continue
                intent = ""
                for p in sb.get("promises") or []:
                    if p.get("attribute") == "intent":
                        c = p.get("content") or []
                        if c:
                            intent = str(c[0])
                        break
                if len(intent) > 130:
                    intent = intent[:127] + "..."
                L.append(
                    f"| `{sid}` | `{_escape(sb.get('name','?'))}` | {_escape(intent)} |"
                )
            L.append("")

        L += ["\\newpage", ""]

    # ---------- appendix ----------
    L += ["# Appendix: Relationships", "", f"Total: {len(rels)} edges", ""]
    types: dict[str, int] = {}
    for r in rels:
        types[r.get("type", "?")] = types.get(r.get("type", "?"), 0) + 1
    for t, n in sorted(types.items()):
        L.append(f"- `{t}`: {n}")
    L.append("")
    return "\n".join(L)


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: {SRC} not found", file=sys.stderr)
        return 1
    if not ANNO.exists():
        print(f"ERROR: {ANNO} not found", file=sys.stderr)
        return 1
    model = yaml.safe_load(SRC.read_text())
    anno = yaml.safe_load(ANNO.read_text())
    md = build_markdown(model, anno)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md)
    print(f"wrote {OUT_MD} ({len(md)} bytes)")

    cmd = [
        "pandoc",
        str(OUT_MD),
        "-o",
        str(OUT_PDF),
        "--pdf-engine=xelatex",
        "-V",
        "monofont=Menlo",
    ]
    print("running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("pandoc stderr:\n" + result.stderr, file=sys.stderr)
        return result.returncode
    print(f"wrote {OUT_PDF} ({OUT_PDF.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
