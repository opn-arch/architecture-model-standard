"""pipeline_v3.publish — Model emit stage (T0.14 Phase 6.7).

Serializes a :class:`ContainerizedModel` to v3 YAML and (optionally)
writes it to disk. The shape matches the Phase 2 v3-poc migration
output so downstream consumers (validator, decompose, docs) get a
uniform schema regardless of whether the model came from migration or
fresh pipeline_v3 extraction.

Two entry points:

    - :func:`serialize_model` — pure, in-memory YAML text.
    - :func:`publish_model` — writes to disk, returns :class:`PublishResult`.

Determinism
-----------

- Components sorted by ``id``.
- Promises within a component sorted by ``(attribute, id)``.
- Relationships sorted by ``(from_cluster, to_cluster)``.
- ``meta.generated_at`` honors ``AMS_DETERMINISTIC_NOW`` (ISO-8601 str)
  when set; otherwise stamps the current UTC instant.
- YAML emit: ``sort_keys=False`` (respects our fixed key order),
  ``default_flow_style=False`` (block style), no aliases.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from architecture_model.pipeline_v3.containerize import (
    ContainerizedBehavior,
    ContainerizedComponent,
    ContainerizedModel,
)
from architecture_model.pipeline_v3.link import Link

__all__ = ["PublishResult", "publish_model", "serialize_model"]


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publish_model call."""

    model_path: Path
    model_yaml: str
    meta: dict[str, Any]


def _now_iso() -> str:
    """Return current UTC ISO timestamp, honoring AMS_DETERMINISTIC_NOW."""
    pinned = os.environ.get("AMS_DETERMINISTIC_NOW")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _component_to_dict(c: ContainerizedComponent) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "root_prefix": c.root_prefix,
        "module_names": list(c.module_names),
        "promises": [p.to_dict() for p in c.promises],
    }


def _behavior_to_dict(b: ContainerizedBehavior) -> dict[str, Any]:
    """Serialize a ContainerizedBehavior to the v3 YAML shape.

    ``class_name`` is omitted when ``None`` so module-level behaviors
    (the common case) do not carry a null field. Field order is fixed
    for stable key ordering under ``sort_keys=False``. ``promises`` list
    (R9) is emitted after class_name (or after function_name when
    class_name is omitted) so behavior entities carry attribute-completeness
    signal even before human/LLM enrichment.
    """
    out: dict[str, Any] = {
        "id": b.id,
        "name": b.name,
        "description": b.description,
        "owner_component": b.owner_component,
        "owner_module": b.owner_module,
        "function_name": b.function_name,
    }
    if b.class_name is not None:
        out["class_name"] = b.class_name
    out["promises"] = [p.to_dict() for p in b.promises]
    return out


def _relationship_to_dict(l: Link) -> dict[str, Any]:
    """Serialize a :class:`Link` to the v3 YAML relationship shape.

    Emits ``sequence`` only when non-``None`` (composite-flow
    metadata from Part 17a3) and ``call_chain`` only when non-``None``
    (composite-flow metadata from Part 17a4). Omission preserves
    byte-identical output for non-composite ``depends-on`` /
    ``traces-to`` / ``triggers`` edges, keeping pre-17a3/17a4
    fixtures digest-stable. ``call_chain`` is emitted as a list
    (YAML block-style sequence) rather than the underlying tuple.
    """
    out: dict[str, Any] = {
        "from": l.from_cluster,
        "to": l.to_cluster,
        "type": l.kind,
        "weight": l.weight,
    }
    if l.sequence is not None:
        out["sequence"] = l.sequence
    if l.call_chain is not None:
        out["call_chain"] = list(l.call_chain)
    return out


def _build_meta(project_name: str, source_root: Path | None) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "schema_version": "3.0",
        "project": project_name or "",
        "generated_by": "pipeline_v3",
        "generated_at": _now_iso(),
    }
    if source_root is not None:
        meta["source_root"] = str(source_root)
    return meta


def _build_doc(
    model: ContainerizedModel,
    *,
    project_name: str,
    source_root: Path | None,
) -> dict[str, Any]:
    components = sorted(
        (_component_to_dict(c) for c in model.components),
        key=lambda d: d["id"],
    )
    relationships = sorted(
        (
            _relationship_to_dict(l)
            for l in model.relationships
        ),
        key=lambda d: (d["from"], d["to"], d["type"]),
    )
    entities: dict[str, Any] = {"components": components}
    # Behaviors block is omitted when empty so pre-17a1 fixtures remain
    # digest-stable. Present when the pipeline produced any behaviors.
    if model.behaviors:
        entities["behaviors"] = sorted(
            (_behavior_to_dict(b) for b in model.behaviors),
            key=lambda d: d["id"],
        )
    return {
        "meta": _build_meta(project_name, source_root),
        "entities": entities,
        "relationships": relationships,
    }


def serialize_model(
    model: ContainerizedModel,
    *,
    project_name: str = "",
    source_root: Path | None = None,
) -> str:
    """Return a v3 YAML string for ``model``.

    Args:
        model: :class:`ContainerizedModel` from :mod:`containerize`.
        project_name: Stamped into ``meta.project``. Empty string is
            allowed for anonymous / test models.
        source_root: If provided, stamped into ``meta.source_root`` for
            audit traceability back to the scanned tree.

    Returns:
        YAML text (block style, stable key order).
    """
    doc = _build_doc(model, project_name=project_name, source_root=source_root)
    return yaml.safe_dump(
        doc,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )


def publish_model(
    model: ContainerizedModel,
    out_path: Path,
    *,
    project_name: str = "",
    source_root: Path | None = None,
) -> PublishResult:
    """Serialize ``model`` and write it atomically to ``out_path``.

    Creates parent directories if needed. Overwrites any existing file.
    Returns a :class:`PublishResult` carrying the YAML text and the meta
    block for programmatic follow-up (e.g. logging, provenance sidecar).
    """
    text = serialize_model(model, project_name=project_name, source_root=source_root)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    # Reparse the meta from doc for the return value (single source of truth)
    doc = _build_doc(model, project_name=project_name, source_root=source_root)
    return PublishResult(model_path=out_path, model_yaml=text, meta=doc["meta"])
