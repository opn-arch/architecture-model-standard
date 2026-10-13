"""R8 — Requirements ingestion from documentation.

Scans authored documentation (reports, plans, top-level CONTEXT/README)
and attaches doc-sourced requirements to model entities as promises.

Three binding layers:
    * Layer 1 (deterministic, verified): YAML frontmatter ``binds_to:``,
      inline HTML comment ``<!-- binds: ID -->``, or heading anchor
      ``{#ID}``.
    * Layer 2 (deterministic, verified): exact match between the
      section heading (case-insensitive, punctuation-normalized) and
      an entity name.
    * Layer 3 (LLM, proposed): fuzzy heading matched via an
      ``LLMProvider.structured`` call; only fires when the heading
      shares at least one token with a candidate entity's name.
      Confidence threshold configurable (default 0.75).

Design: ``docs/plans/2026-09-20-r8-requirements-ingestion-design.md``.

Idempotency:
    * ``verified`` promises for ``requirements`` are preserved.
    * ``proposed`` promises for ``requirements`` are wiped before
      re-ingest (both R7 guesses and prior R8 Layer-3 output).
    * ``open`` / ``typed-gap`` / other-attribute promises untouched.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.llm.provider import LLMProvider

__all__ = [
    "DEFAULT_DOC_ROOTS",
    "DocSection",
    "ingest_requirements",
    "scan_docs",
]


DEFAULT_DOC_ROOTS: tuple[str, ...] = (
    "docs/reports",
    "docs/plans",
    "CONTEXT.md",
    "README.md",
)

_TARGET_KINDS: tuple[str, ...] = (
    "components",
    "capabilities",
    "behaviors",
)

_KIND_SINGULAR = {
    "components": "component",
    "capabilities": "capability",
    "behaviors": "behavior",
}

_PROVENANCE = "pipeline_v3.ingest_requirements"


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DocSection:
    path: str
    heading: str
    heading_level: int
    body: str
    frontmatter: dict
    inline_binds_to: str | None
    anchor_id: str | None


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter block; return (dict, remaining_text).

    Malformed frontmatter is silently downgraded to ``{}`` and the body
    is left intact.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}, text
    if not isinstance(data, dict):
        return {}, text
    return data, text[m.end():]


# --------------------------------------------------------------------------
# Section splitting
# --------------------------------------------------------------------------


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_INLINE_BIND_RE = re.compile(r"<!--\s*binds:\s*([\w.\-]+)\s*-->")
_ANCHOR_RE = re.compile(r"\{#([\w.\-]+)\}")


def _clean_heading(heading: str) -> tuple[str, str | None, str | None]:
    """Strip inline markers off a heading. Return (clean_text, inline_bind, anchor)."""
    inline = None
    anchor = None

    m = _INLINE_BIND_RE.search(heading)
    if m:
        inline = m.group(1)
        heading = heading[: m.start()] + heading[m.end():]

    m = _ANCHOR_RE.search(heading)
    if m:
        anchor = m.group(1)
        heading = heading[: m.start()] + heading[m.end():]

    return heading.strip(), inline, anchor


def _parse_sections(text: str, *, frontmatter: dict, path: str) -> list[DocSection]:
    """Split markdown text into sections by ATX headings.

    Each section spans from its heading to the next heading (or EOF).
    Frontmatter is attached to every section from the same file so the
    binding layers can look it up.
    """
    matches = list(_HEADING_RE.finditer(text))
    sections: list[DocSection] = []
    for i, m in enumerate(matches):
        level = len(m.group(1))
        raw = m.group(2)
        clean, inline, anchor = _clean_heading(raw)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip("\n")
        sections.append(
            DocSection(
                path=path,
                heading=clean,
                heading_level=level,
                body=body,
                frontmatter=dict(frontmatter),
                inline_binds_to=inline,
                anchor_id=anchor,
            )
        )
    return sections


# --------------------------------------------------------------------------
# scan_docs
# --------------------------------------------------------------------------


def scan_docs(
    repo_path: Path, doc_roots: Iterable[str] = DEFAULT_DOC_ROOTS
) -> list[DocSection]:
    """Walk configured doc roots and return a flat list of DocSections.

    ``doc_roots`` entries may be either directories (recursively walked
    for ``.md`` files) or single files. Missing paths are silently
    skipped. Output is deterministically sorted by (path, heading order).
    """
    repo_path = Path(repo_path)
    all_files: list[Path] = []
    for root in doc_roots:
        p = repo_path / root
        if not p.exists():
            continue
        if p.is_file():
            if p.suffix.lower() == ".md":
                all_files.append(p)
        else:
            all_files.extend(sorted(p.rglob("*.md")))

    all_files = sorted(set(all_files))
    sections: list[DocSection] = []
    for f in all_files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = f.relative_to(repo_path).as_posix()
        fm, body = _parse_frontmatter(text)
        sections.extend(_parse_sections(body, frontmatter=fm, path=rel))
    return sections


# --------------------------------------------------------------------------
# Requirement extraction
# --------------------------------------------------------------------------


_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$", re.MULTILINE)


def _extract_requirements(body: str) -> list[str]:
    """Extract bullet and numbered list items as requirement strings.

    Nested items are flattened. Prose paragraphs are ignored.
    Order-preserving: bullets and numbered items are captured in
    document order.
    """
    items: list[tuple[int, str]] = []
    for m in _BULLET_RE.finditer(body):
        items.append((m.start(), m.group(1).strip()))
    for m in _NUMBERED_RE.finditer(body):
        items.append((m.start(), m.group(1).strip()))
    items.sort(key=lambda t: t[0])
    return [text for _, text in items if text]


# --------------------------------------------------------------------------
# Entity index + binding
# --------------------------------------------------------------------------


def _iter_entities(model: dict) -> list[tuple[str, dict]]:
    """Yield (kind, entity_dict) for every promotable entity in the model."""
    out: list[tuple[str, dict]] = []
    entities = model.get("entities", {})
    for kind in _TARGET_KINDS:
        for e in entities.get(kind, []):
            out.append((kind, e))
    return out


def _all_entity_ids(model: dict) -> set[str]:
    ids: set[str] = set()
    for entities in model.get("entities", {}).values():
        for e in entities:
            eid = e.get("id")
            if eid:
                ids.add(eid)
    return ids


_PUNCT_RE = re.compile(r"[^\w\s]")
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _normalize_name(s: str) -> str:
    """Case-fold + strip punctuation + collapse whitespace."""
    s = _PUNCT_RE.sub(" ", s).lower()
    return " ".join(s.split())


def _tokens_for_prefilter(s: str) -> set[str]:
    """Tokens for Layer-3 prefilter; splits CamelCase and snake_case."""
    if not s:
        return set()
    # Split CamelCase before lowercasing.
    parts = _CAMEL_SPLIT_RE.split(s)
    joined = " ".join(parts)
    return set(_normalize_name(joined).split())


def _try_explicit_marker(section: DocSection, model: dict) -> str | None:
    """Layer 1: frontmatter / inline comment / anchor → entity_id.

    Returns None if none present, or if the referenced id does not exist
    in the model. Precedence: frontmatter > inline > anchor.
    """
    candidates: list[str] = []
    fm_bind = section.frontmatter.get("binds_to") if section.frontmatter else None
    if isinstance(fm_bind, str) and fm_bind:
        candidates.append(fm_bind)
    if section.inline_binds_to:
        candidates.append(section.inline_binds_to)
    if section.anchor_id:
        candidates.append(section.anchor_id)

    known = _all_entity_ids(model)
    for c in candidates:
        if c in known:
            return c
    return None


def _try_exact_heading_match(section: DocSection, model: dict) -> str | None:
    """Layer 2: exact (normalized) match against any entity name."""
    if not section.heading:
        return None
    norm_heading = _normalize_name(section.heading)
    if not norm_heading:
        return None
    for _kind, e in _iter_entities(model):
        name = e.get("name") or ""
        if _normalize_name(name) == norm_heading:
            return e.get("id")
    return None


def _classify_llm(
    section: DocSection,
    model: dict,
    provider: LLMProvider | None,
    *,
    threshold: float = 0.75,
) -> str | None:
    """Layer 3: LLM classifier over candidate entities.

    Optimizations:
        * No-op if ``provider`` is None.
        * Skip the LLM call if the heading shares no token with any
          candidate entity name.
        * Any provider exception is swallowed and returns None (fail-soft).
    """
    if provider is None:
        return None
    if not section.heading:
        return None

    entities = _iter_entities(model)
    if not entities:
        return None

    # Cheap prefilter: any shared token? Splits CamelCase in entity names.
    heading_tokens = _tokens_for_prefilter(section.heading)
    candidates: list[tuple[str, dict]] = []
    for kind, e in entities:
        name = e.get("name") or ""
        name_tokens = _tokens_for_prefilter(name)
        if heading_tokens & name_tokens:
            candidates.append((kind, e))
    if not candidates:
        return None

    prompt = _build_classify_prompt(section, candidates)
    schema = {
        "type": "object",
        "properties": {
            "entity_id": {"type": ["string", "null"]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["entity_id", "confidence"],
        "additionalProperties": False,
    }
    try:
        raw = provider.structured(prompt, schema)
    except Exception:
        return None

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, dict):
        return None

    entity_id = raw.get("entity_id")
    confidence = raw.get("confidence", 0.0)
    if not isinstance(entity_id, str) or not entity_id:
        return None
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return None
    if confidence < threshold:
        return None

    known = _all_entity_ids(model)
    if entity_id not in known:
        return None
    return entity_id


def _build_classify_prompt(
    section: DocSection, candidates: list[tuple[str, dict]]
) -> str:
    lines = [
        "You are matching a documentation section to an architecture model entity.",
        "Return strict JSON.",
        "",
        f'Section heading: "{section.heading}"',
        f'Section body (first 800 chars): "{section.body[:800]}"',
        "",
        "Candidate entities (id | kind | name):",
    ]
    for kind, e in sorted(candidates, key=lambda t: t[1].get("id", "")):
        singular = _KIND_SINGULAR.get(kind, kind)
        lines.append(f"  {e.get('id', '')} | {singular} | {e.get('name', '')}")
    lines.append("")
    lines.append("Which entity, if any, does this section describe?")
    lines.append('Return: {"entity_id": "<id or null>", "confidence": <0.0-1.0>}')
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Main entry
# --------------------------------------------------------------------------


def ingest_requirements(
    model: dict,
    *,
    repo_path: Path,
    doc_roots: Iterable[str] = DEFAULT_DOC_ROOTS,
    provider: LLMProvider | None = None,
    threshold: float = 0.75,
) -> dict:
    """Scan docs and attach doc-sourced requirement promises to entities.

    Args:
        model: v3 model dict (as returned by ``load_v3_model``).
        repo_path: Repo root — doc_roots are resolved relative to this.
        doc_roots: Iterable of relative paths (files or directories) to
            scan. Missing paths are silently skipped.
        provider: Optional LLMProvider for Layer 3 fuzzy classification.
            When None, only Layers 1 and 2 fire.
        threshold: Minimum confidence (0..1) for accepting a Layer 3
            match. Default 0.75.

    Returns:
        A deep-copied model dict with requirements promises appended
        to matched entities. Input model is not mutated.
    """
    out = copy.deepcopy(model)
    repo_path = Path(repo_path)

    # Wipe existing proposed `requirements` promises (from R7 or prior R8).
    # Verified/open/typed-gap promises for `requirements` are preserved.
    for _kind, e in _iter_entities(out):
        e["promises"] = [
            p
            for p in e.get("promises", [])
            if not (
                p.get("attribute") == "requirements"
                and p.get("status") == PromiseStatus.PROPOSED.value
            )
        ]

    # Index entities by id for fast append.
    entity_by_id: dict[str, dict] = {}
    for _kind, e in _iter_entities(out):
        eid = e.get("id")
        if eid:
            entity_by_id[eid] = e

    sections = scan_docs(repo_path, doc_roots)

    # Sort deterministically before matching so promise emission order
    # is stable for repeated runs.
    sections.sort(key=lambda s: (s.path, s.heading))

    for section in sections:
        entity_id, verified = _resolve_binding(section, out, provider, threshold)
        if not entity_id:
            continue
        entity = entity_by_id.get(entity_id)
        if entity is None:
            continue

        requirements = _extract_requirements(section.body)
        if not requirements:
            continue

        _append_requirements(entity, requirements, section.path, verified=verified)

    return out


def _resolve_binding(
    section: DocSection,
    model: dict,
    provider: LLMProvider | None,
    threshold: float,
) -> tuple[str | None, bool]:
    """Try each layer in order. Return (entity_id, verified_flag)."""
    hit = _try_explicit_marker(section, model)
    if hit:
        return hit, True
    hit = _try_exact_heading_match(section, model)
    if hit:
        return hit, True
    hit = _classify_llm(section, model, provider, threshold=threshold)
    if hit:
        return hit, False
    return None, False


def _append_requirements(
    entity: dict, requirements: list[str], doc_path: str, *, verified: bool
) -> None:
    """Append requirement promises to an entity, skipping duplicates.

    Duplicates are detected by content-derived promise id (Promise
    identity is (attribute, content, owner)).
    """
    existing_ids = {p.get("id") for p in entity.get("promises", [])}
    status = PromiseStatus.VERIFIED if verified else PromiseStatus.PROPOSED
    for req in requirements:
        promise = Promise(
            attribute="requirements",
            content=req,
            owner_entity=entity["id"],
            status=status,
            verified_by=(doc_path,) if verified else (),
            provenance=_PROVENANCE,
        )
        if promise.id in existing_ids:
            continue
        entity.setdefault("promises", []).append(promise.to_dict())
        existing_ids.add(promise.id)
