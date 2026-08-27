"""Artifact Traceability Map document generator."""

from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


# Which entity types feed which SE documents
_ENTITY_DOC_MAP: dict[str, list[str]] = {
    "Components": [
        "Logical Architecture",
        "Maintenance Manual",
        "Operations Manual",
        "Interface Specification",
    ],
    "Capabilities": ["ConOps", "Functional Analysis", "Requirements Analysis"],
    "Behaviors": ["Use Cases", "Functional Analysis", "Verification & Validation"],
    "Interfaces": ["Interface Specification", "Logical Architecture"],
    "Constraints": ["Requirements Analysis", "Risk Assessment"],
    "Requirements": ["Requirements Analysis", "Verification & Validation"],
    "Actors": ["ConOps", "Use Cases"],
    "Layers": ["Logical Architecture"],
}

_ARTIFACT_FILES: list[tuple[str, str, str]] = [
    (
        ".architecture-model.yaml",
        "Canonical architecture model (source of truth)",
        "Pipeline emit stage",
    ),
    (
        ".architecture-models/",
        "Per-system sub-models from decomposition",
        "Pipeline decompose stage",
    ),
    (".architecture/", "Root directory for all architecture artifacts", "Pipeline"),
    (
        ".architecture/derived_requirements.yaml",
        "Requirements derived from model analysis",
        "Pipeline specify stage",
    ),
    (
        ".architecture/test_map.json",
        "Mapping of components to test files",
        "Pipeline specify stage",
    ),
    (
        ".architecture/component_test_map.json",
        "Component-level test coverage map",
        "Pipeline specify stage",
    ),
    (
        ".architecture/pipeline-cache/",
        "Cached intermediate pipeline stage results",
        "Pipeline (all stages)",
    ),
    (".architecture/docs/se/", "Generated SE documents", "SE doc generator"),
    (".architecture/learning/", "Accumulated heuristics and learnings", "Learning subsystem"),
]


def _human_size(size: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


# Artifact category definitions for dynamic scanning
_ARTIFACT_CATEGORIES: list[tuple[str, str, list[str]]] = [
    (
        "Architecture Models",
        "Canonical model and sub-models",
        [
            "**/.architecture-model.yaml",
        ],
    ),
    (
        "System Manifests",
        "Pipeline manifests",
        [
            "**/manifest.json",
        ],
    ),
    (
        "SE Documents",
        "Generated SE docs",
        [
            ".architecture-models/docs/se/*.md",
            "**/docs/se/*.md",
        ],
    ),
    (
        "Pipeline Cache",
        "Cached stage results",
        [
            ".architecture/pipeline-cache/*.json",
        ],
    ),
    (
        "Test Mapping",
        "Source-to-test mappings",
        [
            ".architecture/test_map.json",
            ".architecture/component_test_map.json",
        ],
    ),
    (
        "Requirements",
        "Derived requirements",
        [
            ".architecture/derived_requirements.yaml",
        ],
    ),
    (
        "Learning",
        "Heuristics and learnings",
        [
            ".architecture/learning/*",
        ],
    ),
    (
        "Reviews & Provenance",
        "LLM review and enrichment data",
        [
            ".architecture/pipeline-cache/reviews.json",
            ".architecture/pipeline-cache/enrichment_log.json",
            ".architecture/pipeline-cache/llm_calls.json",
        ],
    ),
]


def _scan_artifacts(repo_root: Path) -> list[tuple[str, list[tuple[str, int]]]]:
    """Scan a repo for architecture artifacts, grouped by category.

    Returns: [(category_name, [(relative_path, size_bytes), ...]), ...]
    """
    results: list[tuple[str, list[tuple[str, int]]]] = []
    seen: set[str] = set()
    for cat_name, _desc, patterns in _ARTIFACT_CATEGORIES:
        files: list[tuple[str, int]] = []
        for pat in patterns:
            for fpath in sorted(repo_root.glob(pat)):
                if fpath.is_file():
                    rel = str(fpath.relative_to(repo_root))
                    if rel not in seen:
                        seen.add(rel)
                        files.append((rel, fpath.stat().st_size))
        if files:
            results.append((cat_name, files))
    return results


def _render_dynamic_inventory(
    repo_root: Path,
    reviews: list | None = None,
) -> list[str]:
    """Render a dynamic categorized artifact inventory."""
    lines: list[str] = []
    lines.append("## 6. Architecture Artifact Inventory")
    lines.append("")

    scanned = _scan_artifacts(repo_root)
    if not scanned:
        lines.append("*No architecture artifacts found. Run the extraction pipeline first.*")
        lines.append("")
        return lines

    # Build reviewed set for status column
    reviewed_paths: set[str] = set()
    if reviews:
        for rev in reviews:
            reviewed_paths.add(getattr(rev, "artifact_path", ""))

    total_files = 0
    total_bytes = 0
    for cat_name, files in scanned:
        lines.append(f"### {cat_name}")
        lines.append("")
        lines.append("| Path | Size | LLM Reviewed |")
        lines.append("|------|------|-------------|")
        for rel_path, size in files:
            reviewed = "Yes" if rel_path in reviewed_paths else "—"
            lines.append(f"| `{rel_path}` | {_human_size(size)} | {reviewed} |")
            total_files += 1
            total_bytes += size
        lines.append("")

    lines.append(f"**Total:** {total_files} files, {_human_size(total_bytes)}")
    lines.append("")
    return lines


def generate_artifact_traceability(
    model: ArchitectureModel,
    manifest: object | None = None,
    *,
    reviews: list | None = None,
    enrichments: list | None = None,
    repo_root: Path | None = None,
) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Artifact Traceability Map: {project}")
    lines.append("")

    # Counts
    counts: dict[str, int] = {
        "Components": len(model.entities.components),
        "Capabilities": len(model.entities.capabilities),
        "Behaviors": len(model.entities.behaviors),
        "Interfaces": len(model.entities.interfaces),
        "Constraints": len(model.entities.constraints),
        "Requirements": len(model.entities.requirements),
        "Actors": len(model.entities.actors),
        "Layers": len(model.entities.layers),
    }

    # --- Section 1: Entity Inventory ---
    lines.append("## 1. Entity Inventory")
    lines.append("")
    lines.append("| Entity Type | Count | Feeds SE Documents |")
    lines.append("|-------------|-------|--------------------|")
    for etype, count in counts.items():
        docs = ", ".join(_ENTITY_DOC_MAP.get(etype, []))
        lines.append(f"| {etype} | {count} | {docs or '—'} |")
    lines.append("")

    # --- Section 2: Artifact Dependency Graph ---
    lines.append("## 2. Artifact Dependency Graph")
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph TD")
    lines.append('    MODEL[".architecture-model.yaml"]')
    lines.append('    SUBMODELS[".architecture-models/"]')
    lines.append('    DERIVED_REQ["derived_requirements.yaml"]')
    lines.append('    TEST_MAP["test_map.json"]')
    lines.append('    COMP_TEST["component_test_map.json"]')
    lines.append('    CACHE["pipeline-cache/"]')
    lines.append('    SE_DOCS[".architecture/docs/se/"]')
    lines.append('    LEARNING["learning/"]')
    lines.append("")
    lines.append("    MODEL -->|decompose| SUBMODELS")
    lines.append("    MODEL -->|specify| DERIVED_REQ")
    lines.append("    MODEL -->|specify| TEST_MAP")
    lines.append("    MODEL -->|specify| COMP_TEST")
    lines.append("    MODEL -->|generate| SE_DOCS")
    lines.append("    MODEL -->|pipeline stages| CACHE")
    lines.append("    CACHE -->|emit| MODEL")
    lines.append("    MODEL -->|feedback| LEARNING")
    lines.append("```")
    lines.append("")

    # --- Section 3: Entity-to-Artifact Traceability Matrix ---
    lines.append("## 3. Entity-to-Artifact Traceability Matrix")
    lines.append("")
    all_docs = sorted({d for docs in _ENTITY_DOC_MAP.values() for d in docs})
    entity_types = list(counts.keys())
    header = "| Artifact | " + " | ".join(entity_types) + " |"
    sep = "|" + "|".join(["---"] * (len(entity_types) + 1)) + "|"
    lines.append(header)
    lines.append(sep)
    for doc in all_docs:
        row = f"| {doc} |"
        for etype in entity_types:
            if doc in _ENTITY_DOC_MAP.get(etype, []):
                c = counts[etype]
                row += f" **{c}** |" if c > 0 else " — |"
            else:
                row += " |"
        lines.append(row)
    lines.append("")

    # --- Section 4: Relationship Distribution ---
    lines.append("## 4. Relationship Distribution")
    lines.append("")
    if model.relationships:
        # Count by type and track endpoints
        rel_counter: Counter[str] = Counter()
        rel_endpoints: dict[str, set[str]] = {}
        entity_map: dict[str, str] = {}
        for c in model.entities.components:
            entity_map[c.id] = "Component"
        for c in model.entities.capabilities:
            entity_map[c.id] = "Capability"
        for b in model.entities.behaviors:
            entity_map[b.id] = "Behavior"
        for i in model.entities.interfaces:
            entity_map[i.id] = "Interface"
        for a in model.entities.actors:
            entity_map[a.id] = "Actor"
        for r in model.entities.requirements:
            entity_map[r.id] = "Requirement"
        for cn in model.entities.constraints:
            entity_map[cn.id] = "Constraint"

        for rel in model.relationships:
            rt = _rel_type_str(rel.type)
            rel_counter[rt] += 1
            from_type = entity_map.get(rel.from_id, "Unknown")
            to_type = entity_map.get(rel.to_id, "Unknown")
            rel_endpoints.setdefault(rt, set()).add(f"{from_type} → {to_type}")

        lines.append("| Relationship Type | Count | Connects |")
        lines.append("|-------------------|-------|----------|")
        for rt, count in rel_counter.most_common():
            connects = ", ".join(sorted(rel_endpoints.get(rt, set())))
            lines.append(f"| {rt} | {count} | {connects} |")
    else:
        lines.append("*No relationships defined.*")
    lines.append("")

    # --- Section 5: Traceability Gaps ---
    lines.append("## 5. Traceability Gaps")
    lines.append("")
    gaps: list[str] = []
    for etype, docs in _ENTITY_DOC_MAP.items():
        if counts.get(etype, 0) == 0:
            gaps.append(f"**{etype}** — 0 entities; leaves gaps in: {', '.join(docs)}")

    if not model.relationships:
        gaps.append("**No relationships** — traceability between entities cannot be established")
    else:
        rel_types_present = {_rel_type_str(r.type) for r in model.relationships}
        important = {"depends-on", "realizes", "allocated-to", "constrained-by"}
        missing = important - rel_types_present
        for m in sorted(missing):
            gaps.append(f"**{m}** relationship type missing — weakens cross-entity traceability")

    if gaps:
        for g in gaps:
            lines.append(f"- {g}")
    else:
        lines.append("All entity types populated. Full traceability achieved.")
    lines.append("")

    # --- Section 5b: Semantic Completeness Gaps ---
    lines.append("### Semantic Completeness Gaps")
    lines.append("")

    # MOE gaps
    caps_without_moes = [c for c in model.entities.capabilities if not getattr(c, 'moes', None)]
    if caps_without_moes:
        lines.append(f"**Capabilities without MOEs:** {len(caps_without_moes)}")
        for c in caps_without_moes:
            lines.append(f"- {c.id}: {c.name} — missing MOE definition")
        lines.append("")

    # Contract gaps
    ifaces_without_contract = [i for i in model.entities.interfaces if not getattr(i, 'contract', None)]
    if ifaces_without_contract:
        lines.append(f"**Interfaces without contract:** {len(ifaces_without_contract)}")
        for i in ifaces_without_contract:
            lines.append(f"- {i.id}: {i.name} — missing contract (pre/post/invariant)")
        lines.append("")

    # Intent gaps
    entities_without_intent: list[str] = []
    for c in model.entities.components:
        if not getattr(c, 'intent', None):
            entities_without_intent.append(f"{c.id}: {c.name} (component)")
    for c in model.entities.capabilities:
        if not getattr(c, 'intent', None):
            entities_without_intent.append(f"{c.id}: {c.name} (capability)")
    if entities_without_intent:
        lines.append(f"**Entities without intent:** {len(entities_without_intent)}")
        for e in entities_without_intent:
            lines.append(f"- {e}")
        lines.append("")

    if not caps_without_moes and not ifaces_without_contract and not entities_without_intent:
        lines.append("All semantic fields populated.")
        lines.append("")

    # --- Section 6: Architecture Artifact Inventory ---
    if repo_root:
        lines.extend(_render_dynamic_inventory(repo_root, reviews=reviews))
    else:
        # Fallback: static file map
        lines.append("## 6. Architecture File Map")
        lines.append("")
        lines.append("| Path | Purpose | Generated By |")
        lines.append("|------|---------|-------------|")
        for path, purpose, gen_by in _ARTIFACT_FILES:
            lines.append(f"| `{path}` | {purpose} | {gen_by} |")
        lines.append("")

    # --- Section 7: LLM Review Status ---
    lines.append("## LLM Review Status")
    lines.append("")
    if reviews:
        lines.append("| Artifact | Reviewed | Summary | Comments Count | Timestamp |")
        lines.append("|----------|----------|---------|----------------|-----------|")
        for rev in reviews:
            lines.append(
                f"| {rev.artifact_path} | Yes | {rev.review_summary} | {len(rev.comments)} | {rev.timestamp} |"
            )
    else:
        lines.append("No LLM reviews available.")
    lines.append("")

    # --- Section 8: LLM Enrichment Provenance ---
    lines.append("## LLM Enrichment Provenance")
    lines.append("")
    if enrichments:
        lines.append("| Entity ID | Type | Stage | Old Value | New Value | Timestamp |")
        lines.append("|-----------|------|-------|-----------|-----------|-----------|")
        for enr in enrichments:
            lines.append(
                f"| {enr.entity_id} | {enr.entity_type} | {enr.stage} | {enr.old_value} | {enr.new_value} | {enr.timestamp} |"
            )
    else:
        lines.append("No LLM enrichment records available.")
    lines.append("")

    # --- Section 9: Review Details ---
    lines.append("## Review Details")
    lines.append("")
    if reviews:
        for rev in reviews:
            lines.append(f"### {rev.artifact_path}")
            lines.append("")
            lines.append(f"**Summary:** {rev.review_summary}")
            lines.append("")
            if rev.comments:
                for c in rev.comments:
                    lines.append(f"- {c}")
                lines.append("")
            lines.append("<details>")
            lines.append("<summary>Prompt and response</summary>")
            lines.append("")
            lines.append("**Prompt sent:**")
            lines.append("```")
            lines.append(rev.prompt_sent)
            lines.append("```")
            lines.append("")
            lines.append("**Response received:**")
            lines.append("```")
            lines.append(rev.response_received)
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")
    else:
        lines.append("No review details available.")
    lines.append("")

    return "\n".join(lines)
