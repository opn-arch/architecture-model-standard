"""Entity-level deepening via scoped manifest scan.

Given an entity ID, resolves associated source files, runs a manifest scan
on those files, and enriches the entity in the model with richer data
(signatures, body_hints, etc.).
"""

from __future__ import annotations

from pathlib import Path

from architecture_model.core.types import ArchitectureModel, Component


def resolve_entity_files(model: ArchitectureModel, entity_id: str) -> list[str]:
    """Resolve source files associated with an entity.

    Strategy by entity type:
    - Component: return component.files directly
    - Capability: find components that realize it → union of their files
    - Behavior: find components that trace-to it, or via capability_id → realizes
    - Interface: use interface.component_id → component files, or exposes relationships
    - Layer: find components contained in layer → union of their files
    - Other: traverse relationships where entity is to_id, find connected components
    """
    # Build entity lookup
    all_entities = {}
    for etype in ("actors", "capabilities", "components", "behaviors",
                  "interfaces", "constraints", "layers", "systems", "requirements"):
        for e in getattr(model.entities, etype, []) or []:
            all_entities[e.id] = (etype, e)

    if entity_id not in all_entities:
        raise ValueError(f"Entity {entity_id!r} not found in model")

    etype, entity = all_entities[entity_id]

    # Component: direct files
    if etype == "components":
        return list(getattr(entity, "files", None) or [])

    # Build component lookup for file resolution
    comp_map: dict[str, Component] = {
        c.id: c for c in (model.entities.components or [])
    }

    def _files_from_comp_ids(comp_ids: set[str]) -> list[str]:
        files: list[str] = []
        for cid in comp_ids:
            comp = comp_map.get(cid)
            if comp and comp.files:
                files.extend(comp.files)
        return files

    # Relationship-based resolution
    comp_ids: set[str] = set()

    # Check direct field references (interface.provider)
    if etype == "interfaces":
        cid = getattr(entity, "provider", None)
        if cid and cid in comp_map:
            comp_ids.add(cid)

    # Traverse relationships
    for rel in model.relationships or []:
        rtype = rel.type.value if hasattr(rel.type, "value") else str(rel.type)

        if etype == "capabilities" and rtype == "realizes" and rel.to_id == entity_id:
            comp_ids.add(rel.from_id)
        elif etype == "behaviors" and rtype == "traces-to" and rel.to_id == entity_id:
            comp_ids.add(rel.from_id)
        elif etype == "interfaces" and rtype == "exposes" and rel.to_id == entity_id:
            comp_ids.add(rel.from_id)
        elif etype == "layers" and rtype == "contains" and rel.from_id == entity_id:
            if rel.to_id in comp_map:
                comp_ids.add(rel.to_id)
        elif rel.to_id == entity_id and rel.from_id in comp_map:
            comp_ids.add(rel.from_id)
        elif rel.from_id == entity_id and rel.to_id in comp_map:
            comp_ids.add(rel.to_id)

    return _files_from_comp_ids(comp_ids)


def deepen_entity(
    repo_path: Path,
    model: ArchitectureModel,
    entity_id: str,
) -> ArchitectureModel:
    """Deepen an entity by running a scoped manifest scan and enriching the model.

    1. Resolve source files for the entity
    2. Run manifest scan on those files
    3. Enrich the entity's component(s) with signatures, body_hints, etc.
    4. Return the updated model
    """
    files = resolve_entity_files(model, entity_id)
    if not files:
        raise ValueError(
            f"No source files resolved for entity {entity_id!r}. "
            "Only entities linked to components with files can be deepened."
        )

    # Resolve files relative to repo_path, filter to existing
    resolved: list[Path] = []
    for f in files:
        p = Path(repo_path) / f
        if p.exists():
            resolved.append(p)

    if not resolved:
        raise ValueError(
            f"No source files exist on disk for entity {entity_id!r}. "
            f"Expected: {files}"
        )

    # Run manifest scan on the resolved files
    from architecture_model.manifest.generator import generate_manifest

    manifest = generate_manifest(repo_path)

    # Build a lookup of scanned module data by file path
    scanned_by_file: dict[str, dict] = {}
    manifest_dict = manifest.to_dict()
    for mod in manifest_dict.get("modules", []):
        mod_file = mod.get("file", "")
        scanned_by_file[mod_file] = mod

    # Find components to enrich
    all_entities = {}
    for etype in ("actors", "capabilities", "components", "behaviors",
                  "interfaces", "constraints", "layers", "systems", "requirements"):
        for e in getattr(model.entities, etype, []) or []:
            all_entities[e.id] = (etype, e)

    etype, entity = all_entities[entity_id]

    # Determine which components to enrich
    comp_ids_to_enrich: set[str] = set()
    if etype == "components":
        comp_ids_to_enrich.add(entity_id)
    else:
        # Resolve to components via same logic as resolve_entity_files
        comp_map = {c.id: c for c in (model.entities.components or [])}
        for rel in model.relationships or []:
            rtype = rel.type.value if hasattr(rel.type, "value") else str(rel.type)
            if rel.to_id == entity_id and rel.from_id in comp_map:
                comp_ids_to_enrich.add(rel.from_id)
            elif rel.from_id == entity_id and rel.to_id in comp_map:
                comp_ids_to_enrich.add(rel.to_id)
        if etype == "interfaces":
            cid = getattr(entity, "provider", None)
            if cid:
                comp_ids_to_enrich.add(cid)

    # Enrich components with manifest data
    for comp in (model.entities.components or []):
        if comp.id not in comp_ids_to_enrich:
            continue
        comp_files = comp.files or []
        sigs: list[str] = []
        for f in comp_files:
            mod_data = scanned_by_file.get(f, {})
            for fn in mod_data.get("functions", []):
                name = fn if isinstance(fn, str) else fn.get("name", "")
                sig = fn if isinstance(fn, str) else fn.get("signature", name)
                if sig:
                    sigs.append(sig)
            for cls in mod_data.get("classes", []):
                name = cls if isinstance(cls, str) else cls.get("name", "")
                if name:
                    sigs.append(f"class {name}")

        if sigs and not comp.signatures:
            comp.signatures = sigs

    return model
