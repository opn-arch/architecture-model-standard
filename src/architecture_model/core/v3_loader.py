"""v3 model loader — merges pipeline model + authored fragments.

Extracted from ``scripts/build_v3_viewer.py`` for reuse by CLI commands
(``export-graph``) and other tooling. Preserves the exact merge policy
originally documented in the viewer builder.

Public API:
    load_v3_model(model_path=None, fragment_dir=None) -> dict

Returns a model dict of shape::

    {
        "meta": {...},
        "entities": {
            "capabilities": [...],
            "components": [...],
            ...
        },
        "relationships": [...],
        "_source_index": [...],  # provenance sidecar (per-entity source)
    }
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import yaml

# Canonical v3 entity kinds. Order matches build_v3_viewer.ENTITY_KINDS.
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


def load_sources(
    model_path: Path,
    fragment_dir: Optional[Path] = None,
) -> list[tuple[str, dict]]:
    """Return [(source_label, doc), ...] pipeline model + authored fragments."""
    sources: list[tuple[str, dict]] = []
    base = model_path.parent if model_path.parent.exists() else Path.cwd()
    if model_path.exists():
        try:
            label = str(model_path.relative_to(base))
        except ValueError:
            label = str(model_path)
        sources.append((label, _load_yaml(model_path)))
    if fragment_dir and fragment_dir.exists():
        for frag in sorted(fragment_dir.glob("*.v3.yaml")):
            try:
                label = str(frag.relative_to(base))
            except ValueError:
                label = str(frag)
            sources.append((label, _load_yaml(frag)))
    return sources


def merge_sources(
    sources: list[tuple[str, dict]],
) -> tuple[dict, dict, list, list]:
    """Merge sources → (meta, entities_by_kind, relationships, source_index).

    Merge policy (verbatim from viewer builder):
      - First source's meta wins.
      - Same entity id declared in multiple sources: promise-level union.
        Promises keyed by promise.id. Identical content required across
        sources; conflicting content is a hard-fail (sys.exit(3)).
      - Same entity id across different kinds is a hard-fail (sys.exit(3)).
      - Relationship dedup by (from, to, type) tuple.
    """
    meta: dict = {}
    entities_by_kind: dict[str, dict] = {k: {} for k in ENTITY_KINDS}
    id_kind: dict[str, str] = {}
    id_source: dict[str, str] = {}
    source_index: list[dict] = []
    relationships: list[dict] = []
    rel_seen: set[tuple[str, str, str]] = set()

    for label, doc in sources:
        if not meta and doc.get("meta"):
            meta = dict(doc["meta"])
        for kind in ENTITY_KINDS:
            for ent in doc.get("entities", {}).get(kind, []) or []:
                eid = ent.get("id")
                if not eid:
                    continue
                if eid in id_kind and id_kind[eid] != kind:
                    print(
                        f"error: id {eid!r} declared as {id_kind[eid]!r} in "
                        f"{id_source[eid]!r} and as {kind!r} in {label!r}",
                        file=sys.stderr,
                    )
                    sys.exit(3)
                if eid not in id_kind:
                    id_kind[eid] = kind
                    id_source[eid] = label
                    entities_by_kind[kind][eid] = dict(ent)
                    source_index.append(
                        {"id": eid, "source": label, "kind": kind}
                    )
                else:
                    existing = entities_by_kind[kind][eid]
                    existing_promises = existing.get("promises", []) or []
                    new_promises = ent.get("promises", []) or []
                    by_pid = {p.get("id"): p for p in existing_promises}
                    for p in new_promises:
                        pid = p.get("id")
                        if not pid:
                            continue
                        if pid in by_pid:
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
                        else:
                            by_pid[pid] = p
                    existing["promises"] = [by_pid[k] for k in sorted(by_pid)]
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


def load_v3_model(
    model_path: Optional[Path] = None,
    fragment_dir: Optional[Path] = None,
) -> dict:
    """Load and merge a v3 model + fragments into a single model dict.

    Args:
        model_path: Root model YAML. Defaults to
            ``.architecture-model.v3.yaml`` under CWD, falling back to
            ``.architecture-model.yaml``.
        fragment_dir: Directory containing ``*.v3.yaml`` fragments.
            Defaults to ``.architecture/model/`` under CWD.

    Returns:
        Model dict with keys ``meta``, ``entities`` (list-shaped per kind),
        ``relationships``, and provenance sidecar ``_source_index``.
    """
    cwd = Path.cwd()
    if model_path is None:
        candidates = [
            cwd / ".architecture-model.v3.yaml",
            cwd / ".architecture-model.yaml",
        ]
        for c in candidates:
            if c.exists():
                model_path = c
                break
        else:
            raise FileNotFoundError(
                "No model found. Tried: "
                + ", ".join(str(c) for c in candidates)
            )
    if fragment_dir is None:
        fragment_dir = cwd / ".architecture" / "model"

    sources = load_sources(Path(model_path), Path(fragment_dir))
    meta, entities_by_kind, relationships, source_index = merge_sources(sources)

    # Convert entities_by_kind dict-of-dicts → dict-of-lists (canonical shape).
    entities = {kind: list(by_id.values()) for kind, by_id in entities_by_kind.items()}

    return {
        "meta": meta,
        "entities": entities,
        "relationships": relationships,
        "_source_index": source_index,
    }
