"""Prompt assembly for the `fill_promise` walk (Part 12).

Hand-rolled v3-native projector — takes a v3 model dict, an
`(entity_id, attribute)` promise slot, a human-authored note body, and a
template string, and produces a deterministic LLM prompt.

Deterministic by construction:

- Entities/promises/siblings/relations are all sorted by id.
- Relation section restricted to a fixed 4-type allowlist and sorted by
  `(type, target_id)`.
- Empty sections render as ``_(none)_`` (never blank).
- No timestamps, no random UUIDs.

Same input → same string → same SHA-256 → MockProvider hit.

Realizes helpers consumed by ``CAP-WK.author``.
"""
from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any, Mapping

# v3 entity kinds (mirrors architecture_model.core.v3_loader.ENTITY_KINDS).
_ENTITY_KINDS = (
    "components",
    "capabilities",
    "behaviors",
    "interfaces",
    "actors",
    "constraints",
    "layers",
)

# Kind → singular label used in the prompt output instruction.
_KIND_SINGULAR = {
    "components": "component",
    "capabilities": "capability",
    "behaviors": "behavior",
    "interfaces": "interface",
    "actors": "actor",
    "constraints": "constraint",
    "layers": "layer",
}

# Relation types included in the prompt slice (token discipline).
_RELATION_ALLOWLIST = frozenset(
    {"realizes", "exposes", "consumes", "depends-on"}
)

_NONE = "_(none)_"


def default_template_body(repo_path: Path | None = None) -> str:
    """Return the fill_promise template body.

    If ``repo_path`` is given and a user-editable override exists at
    ``<repo_path>/.architecture/llm/prompts/fill_promise.md``, that is
    returned. Otherwise the package resource shipped with this module
    is returned.
    """
    if repo_path is not None:
        override = (
            Path(repo_path) / ".architecture" / "llm" / "prompts" / "fill_promise.md"
        )
        if override.exists():
            return override.read_text(encoding="utf-8")
    return resources.files("architecture_model.llm.prompts").joinpath(
        "fill_promise.md"
    ).read_text(encoding="utf-8")


def _find_entity(
    v3_model: Mapping[str, Any], entity_id: str
) -> tuple[str, Mapping[str, Any]]:
    """Return ``(kind, entity_dict)`` for ``entity_id`` in a v3 model.

    Raises ``KeyError`` if not found.
    """
    entities = v3_model.get("entities") or {}
    for kind in _ENTITY_KINDS:
        for ent in entities.get(kind, []) or []:
            if isinstance(ent, Mapping) and ent.get("id") == entity_id:
                return kind, ent
    raise KeyError(f"entity {entity_id!r} not found in v3 model")


def _promises_section(
    entity: Mapping[str, Any], marked_attribute: str
) -> str:
    promises = entity.get("promises") or []
    if not promises:
        return _NONE
    lines: list[str] = []
    for p in sorted(promises, key=lambda x: x.get("id", "")):
        pid = p.get("id", "")
        attr = p.get("attribute", "")
        status = p.get("status", "?")
        marker = "→" if attr == marked_attribute else " "
        content = p.get("content") or []
        if isinstance(content, list) and content:
            summary = str(content[0])
            if len(summary) > 80:
                summary = summary[:77] + "..."
        else:
            summary = "(empty)"
        lines.append(f"{marker} `{pid}` — attribute=`{attr}` status=`{status}` — {summary}")
    return "\n".join(lines)


def _index_relationships(
    v3_model: Mapping[str, Any],
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Return ``(outbound_by_source, inbound_by_target)`` dicts."""
    out: dict[str, list[dict]] = {}
    inb: dict[str, list[dict]] = {}
    for rel in v3_model.get("relationships") or []:
        if not isinstance(rel, Mapping):
            continue
        src = rel.get("from")
        tgt = rel.get("to")
        if not src or not tgt:
            continue
        out.setdefault(src, []).append(dict(rel))
        inb.setdefault(tgt, []).append(dict(rel))
    return out, inb


def _entity_name(v3_model: Mapping[str, Any], entity_id: str) -> str:
    """Return the ``name`` of an entity, or the id itself if not found."""
    try:
        _, ent = _find_entity(v3_model, entity_id)
        return str(ent.get("name") or entity_id)
    except KeyError:
        return entity_id


def _parent_chain(
    v3_model: Mapping[str, Any],
    entity_id: str,
    inbound: dict[str, list[dict]],
) -> str:
    """Walk ``contains`` inbound edges to build ``ROOT / A / B / **entity**``."""
    chain: list[str] = [entity_id]
    seen: set[str] = {entity_id}
    current = entity_id
    while True:
        parents = [
            r.get("from")
            for r in inbound.get(current, [])
            if r.get("type") == "contains"
        ]
        parents = [p for p in parents if p and p not in seen]
        if not parents:
            break
        # Deterministic: pick the smallest id if multiple parents.
        current = sorted(parents)[0]
        chain.append(current)
        seen.add(current)
    chain.reverse()
    # Format: ROOT / A — name / B — name / **entity** — name
    parts: list[str] = ["ROOT"]
    for idx, eid in enumerate(chain):
        name = _entity_name(v3_model, eid)
        piece = f"`{eid}` — {name}"
        if idx == len(chain) - 1:
            piece = f"**{piece}**"
        parts.append(piece)
    return " / ".join(parts)


def _siblings_section(
    v3_model: Mapping[str, Any],
    entity_id: str,
    inbound: dict[str, list[dict]],
    outbound: dict[str, list[dict]],
) -> str:
    """Siblings = other entities under the same immediate ``contains`` parent."""
    parents = sorted(
        r.get("from")
        for r in inbound.get(entity_id, [])
        if r.get("type") == "contains" and r.get("from")
    )
    if not parents:
        return _NONE
    parent = parents[0]
    siblings = sorted(
        {
            r.get("to")
            for r in outbound.get(parent, [])
            if r.get("type") == "contains"
            and r.get("to")
            and r.get("to") != entity_id
        }
    )
    if not siblings:
        return _NONE
    lines = [f"- `{sid}` — {_entity_name(v3_model, sid)}" for sid in siblings]
    return "\n".join(lines)


def _relations_section(
    v3_model: Mapping[str, Any],
    entity_id: str,
    outbound: dict[str, list[dict]],
) -> str:
    """Outbound 1-hop relations, filtered to the allowlist and sorted."""
    rels = [
        (str(r.get("type")), str(r.get("to")))
        for r in outbound.get(entity_id, [])
        if r.get("type") in _RELATION_ALLOWLIST and r.get("to")
    ]
    if not rels:
        return _NONE
    seen: set[tuple[str, str]] = set()
    lines: list[str] = []
    for rtype, target in sorted(rels):
        key = (rtype, target)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- `{rtype}` → `{target}` — {_entity_name(v3_model, target)}")
    return "\n".join(lines)


def assemble_promise_prompt(
    v3_model: Mapping[str, Any],
    entity_id: str,
    attribute: str,
    note_body: str,
    template_body: str | None = None,
) -> str:
    """Build the LLM prompt for filling ``(entity_id, attribute)``.

    Deterministic: identical inputs → identical output string.

    Raises
    ------
    KeyError
        If ``entity_id`` is not present in ``v3_model``.
    """
    if template_body is None:
        template_body = default_template_body()

    kind, entity = _find_entity(v3_model, entity_id)
    outbound, inbound = _index_relationships(v3_model)

    fmt_context = {
        "attribute": attribute,
        "entity_id": entity_id,
        "entity_kind": kind,
        "entity_kind_singular": _KIND_SINGULAR.get(kind, kind),
        "entity_name": entity.get("name") or entity_id,
        "entity_description": entity.get("description") or "(no description)",
        "note_body": note_body,
        "promises_block": _promises_section(entity, attribute),
        "parent_chain": _parent_chain(v3_model, entity_id, inbound),
        "siblings_block": _siblings_section(v3_model, entity_id, inbound, outbound),
        "relations_block": _relations_section(v3_model, entity_id, outbound),
    }

    return template_body.format(**fmt_context)


__all__ = [
    "assemble_promise_prompt",
    "default_template_body",
]
