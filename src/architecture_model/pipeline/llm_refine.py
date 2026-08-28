"""LLM refinement appliers: normalize LLM output and apply diffs to stage results."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from architecture_model.pipeline.infer_types import (
    InferenceResult,
    InferredBehavior,
    InferredCapability,
)
from architecture_model.pipeline.allocate_types import ComponentAllocation
from architecture_model.pipeline.relate_types import DerivedRelationship, RelateResult


# ---------------------------------------------------------------------------
# 1. Normalization — convert raw LLM JSON to extract_stage_data format
# ---------------------------------------------------------------------------

def normalize_llm_output(stage: str, raw: dict) -> dict:
    """Normalize LLM re-inference output to match extract_stage_data format."""
    if stage == "infer":
        return _normalize_infer(raw)
    if stage == "allocate":
        return _normalize_allocate(raw)
    if stage == "relate":
        return _normalize_relate(raw)
    if stage == "specify":
        return _normalize_specify(raw)
    return raw


def _normalize_infer(raw: dict) -> dict:
    caps = []
    for i, c in enumerate(raw.get("capabilities", [])):
        d: dict[str, Any] = {
            "id": c.get("id", f"CAP-F{i + 1}"),
            "name": c.get("name", ""),
        }
        # LLM uses source_file (singular); extract_stage_data uses source_files (plural list)
        sf = c.get("source_file") or c.get("source_files")
        if isinstance(sf, str):
            d["source_files"] = [sf]
        elif isinstance(sf, list):
            d["source_files"] = [str(s) for s in sf]
        else:
            d["source_files"] = []
        caps.append(d)

    behaviors = []
    for i, b in enumerate(raw.get("behaviors", [])):
        behaviors.append({
            "id": b.get("id", f"BEH-{i + 1}"),
            "name": b.get("name", ""),
        })

    actors = []
    for i, a in enumerate(raw.get("actors", [])):
        actors.append({
            "id": a.get("id", f"ACT-{i + 1}"),
            "name": a.get("name", ""),
        })

    return {"capabilities": caps, "actors": actors, "behaviors": behaviors}


def _normalize_allocate(raw: dict) -> dict:
    comps = []
    for i, c in enumerate(raw.get("components", [])):
        files = c.get("files", [])
        if isinstance(files, str):
            files = [files]
        comps.append({
            "id": c.get("id", f"COMP-{i + 1}"),
            "name": c.get("name", ""),
            "layer": c.get("layer", ""),
            "capability_id": c.get("capability_id", ""),
            "files": [str(f) for f in files],
        })
    return {"components": comps}


def _normalize_relate(raw: dict) -> dict:
    rels = []
    for r in raw.get("relationships", []):
        rels.append({
            "from_id": r.get("from") or r.get("from_id", ""),
            "to_id": r.get("to") or r.get("to_id", ""),
            "rel_type": r.get("type") or r.get("rel_type", ""),
        })
    return {"relationships": rels}


def _normalize_specify(raw: dict) -> dict:
    ifaces = []
    for i in raw.get("interfaces", []):
        ifaces.append({
            "name": i.get("name", ""),
            "interface_type": i.get("type") or i.get("interface_type", ""),
            "component_id": i.get("component_id", ""),
        })
    return {"interfaces": ifaces}


# ---------------------------------------------------------------------------
# 2. Apply functions — mutate stage outputs using diff results
# ---------------------------------------------------------------------------

def apply_renames(
    entities: list,
    renames: list[dict],
    threshold: float = 0.5,
) -> list[dict]:
    """Apply name improvements from diff renames to stage output entities.

    *entities*: list of dataclass instances with `.id` and `.name`.
    *renames*: from ``StageGap.renamed`` — each has keys ``det``, ``llm``,
               ``similarity``, ``id``.
    *threshold*: minimum similarity to apply.

    Returns list of ``{entity_id, old_name, new_name, confidence}`` for logging.
    Mutates entity ``.name`` in-place.
    """
    log: list[dict] = []
    id_to_rename = {r["id"]: r for r in renames if r.get("similarity", 0) >= threshold}
    for entity in entities:
        eid = getattr(entity, "id", None)
        if eid in id_to_rename:
            r = id_to_rename[eid]
            old = entity.name
            entity.name = r["llm"]
            log.append({
                "entity_id": eid,
                "old_name": old,
                "new_name": r["llm"],
                "confidence": r["similarity"],
            })
    return log


def apply_layer_corrections(
    components: list[ComponentAllocation],
    llm_components: list[dict],
) -> list[dict]:
    """Override layer assignments from LLM output.

    Matches by name similarity (best match above 0.4).
    Returns list of ``{component_id, old_layer, new_layer}`` for logging.
    """
    log: list[dict] = []
    for comp in components:
        best_sim = 0.0
        best_layer = ""
        for lc in llm_components:
            llm_name = lc.get("name", "")
            if not llm_name:
                continue
            sim = SequenceMatcher(None, comp.name.lower(), llm_name.lower()).ratio()
            if sim > best_sim:
                best_sim = sim
                best_layer = lc.get("layer", "")
        if best_sim >= 0.4 and best_layer and best_layer != comp.layer:
            old = comp.layer
            comp.layer = best_layer
            log.append({
                "component_id": comp.id,
                "old_layer": old,
                "new_layer": best_layer,
            })
    return log


def apply_additions_infer(
    result: InferenceResult,
    added: list[dict],
    id_counter: int,
) -> list[dict]:
    """Add LLM-only capabilities/behaviors to inference result.

    Returns list of ``{entity_type, name, new_id}`` for logging.
    """
    log: list[dict] = []
    counter = id_counter
    for item in added:
        name = item.get("name", "")
        if not name:
            continue
        # Determine type from item content or default to capability
        beh_type = item.get("type") or item.get("behavior_type")
        if beh_type:
            new_id = f"BEH-{counter}"
            result.behaviors.append(InferredBehavior(
                id=new_id,
                name=name,
                behavior_type=beh_type,
            ))
            log.append({"entity_type": "behavior", "name": name, "new_id": new_id})
        else:
            new_id = f"CAP-F{counter}"
            result.capabilities.append(InferredCapability(
                id=new_id,
                name=name,
                evidence_source="llm",
            ))
            log.append({"entity_type": "capability", "name": name, "new_id": new_id})
        counter += 1
    return log


def apply_additions_relate(
    result: RelateResult,
    added: list[dict],
) -> list[dict]:
    """Add LLM-only relationships to relate result.

    Only adds if no existing relationship has same from_id + to_id.
    Returns list of ``{from_id, to_id, rel_type}`` for logging.
    """
    existing = {
        (r.from_id, r.to_id) for r in result.relationships
    }
    log: list[dict] = []
    for item in added:
        from_id = item.get("from") or item.get("from_id", "")
        to_id = item.get("to") or item.get("to_id", "")
        rel_type = item.get("type") or item.get("rel_type", "")
        if not from_id or not to_id:
            continue
        if (from_id, to_id) in existing:
            continue
        result.relationships.append(DerivedRelationship(
            from_id=from_id,
            to_id=to_id,
            rel_type=rel_type,
            evidence_source="llm",
            confidence=0.7,
        ))
        existing.add((from_id, to_id))
        log.append({"from_id": from_id, "to_id": to_id, "rel_type": rel_type})
    return log
