"""
Extract Architecture Model from Tier 1 markdown artifacts.

Parses the 5 Tier 1 artifacts:
  - functional-architecture.md → capabilities (F-blocks), actor hints
  - use-cases.md → actors, behaviors (UCs), relationships
  - logical-architecture.md → layers, components
  - requirements-analysis.md → constraints
  - icd.md → interfaces

Produces an ArchitectureModel instance (and optionally writes YAML).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Constraint,
    ConstraintType,
    Entities,
    Interface,
    InterfaceType,
    Layer,
    ModelMeta,
    Priority,
    Relationship,
    RelationType,
    Status,
    Strength,
)
from ..core.parser import save_model
from .table_parser import extract_sections, find_table_after_heading, parse_tables


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_from_artifacts(
    artifact_dir: str | Path,
    project: str = "",
    system: str = "",
) -> ArchitectureModel:
    """
    Extract a complete architecture model from Tier 1 artifact markdown files.

    Args:
        artifact_dir: Directory containing the stage2 artifact markdown files.
        project: Project name (used in meta).
        system: System identifier.

    Returns:
        Populated ArchitectureModel.
    """
    artifact_dir = Path(artifact_dir)

    # Load artifact texts
    texts: dict[str, str] = {}
    for name in [
        "functional-architecture",
        "use-cases",
        "logical-architecture",
        "requirements-analysis",
        "icd",
    ]:
        path = artifact_dir / f"{name}.md"
        if path.exists():
            texts[name] = path.read_text(encoding="utf-8")
        else:
            texts[name] = ""

    # Extract entities from each artifact
    actors = _extract_actors(texts["use-cases"])
    capabilities = _extract_capabilities(texts["functional-architecture"])
    behaviors = _extract_behaviors(texts["use-cases"])
    interfaces = _extract_interfaces(texts["icd"])
    constraints = _extract_constraints(texts["requirements-analysis"])
    layers = _extract_layers(texts["logical-architecture"])
    components = _extract_components(texts["logical-architecture"])

    # Extract relationships
    relationships = []
    relationships.extend(_extract_uc_relationships(texts["use-cases"]))
    relationships.extend(_extract_layer_relationships(texts["logical-architecture"]))
    relationships.extend(_extract_capability_relationships(capabilities, behaviors))
    relationships.extend(_extract_component_capability_relationships(components, capabilities))

    iface_rels, discovered_actors = _extract_interface_relationships(interfaces)
    relationships.extend(iface_rels)

    # Merge auto-discovered external actors (avoid duplicates across ALL entity types)
    all_entity_ids: set[str] = set()
    all_entity_ids.update(a.id for a in actors)
    all_entity_ids.update(c.id for c in capabilities)
    all_entity_ids.update(b.id for b in behaviors)
    all_entity_ids.update(i.id for i in interfaces)
    all_entity_ids.update(c.id for c in constraints)
    all_entity_ids.update(l.id for l in layers)
    all_entity_ids.update(c.id for c in components)
    for actor in discovered_actors:
        if actor.id not in all_entity_ids:
            actors.append(actor)
            all_entity_ids.add(actor.id)

    # Determine source artifacts used
    source_artifacts = [name for name, text in texts.items() if text]

    meta = ModelMeta(
        schema_version="0.1.0",
        project=project or _guess_project(texts),
        system=system or "logs-db",
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_artifacts=source_artifacts,
    )

    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            actors=actors,
            capabilities=capabilities,
            behaviors=behaviors,
            interfaces=interfaces,
            constraints=constraints,
            layers=layers,
            components=components,
        ),
        relationships=relationships,
    )


# ---------------------------------------------------------------------------
# Actors (from use-cases.md)
# ---------------------------------------------------------------------------

_ACTOR_TYPE_MAP = {
    "human": ActorType.HUMAN,
    "human (primary)": ActorType.HUMAN,
    "system": ActorType.SYSTEM,
    "external source": ActorType.EXTERNAL_SERVICE,
    "external": ActorType.EXTERNAL_SERVICE,
}


def _extract_actors(text: str) -> list[Actor]:
    """Parse actors table from use-cases.md §1."""
    if not text:
        return []

    rows = find_table_after_heading(text, r"Actors?\s*[&+]\s*Goals?")
    actors: list[Actor] = []

    for row in rows:
        actor_id = row.get("actor_id", "").strip()
        name = row.get("name", "").strip()
        type_str = row.get("type", "human").strip().lower()
        goals_str = row.get("goals", "")

        if not actor_id or not name:
            continue

        actor_type = _ACTOR_TYPE_MAP.get(type_str, ActorType.HUMAN)
        goals = [g.strip() for g in goals_str.split(",") if g.strip()]

        actors.append(
            Actor(
                id=actor_id,
                name=name,
                status=Status.ACTIVE,
                type=actor_type,
                goals=goals,
            )
        )

    return actors


# ---------------------------------------------------------------------------
# Capabilities (from functional-architecture.md)
# ---------------------------------------------------------------------------

_FBLOCK_RE = re.compile(
    r'class\s+"(F\d+):\s+(.+?)"\s+as\s+\w+\s+<<block>>',
    re.MULTILINE,
)

_STATUS_RE = re.compile(r"\[(\w+)\]")


def _extract_capabilities(text: str) -> list[Capability]:
    """Parse F-block definitions from functional-architecture.md PlantUML BDD."""
    if not text:
        return []

    capabilities: list[Capability] = []

    # Parse from PlantUML class diagrams
    for match in _FBLOCK_RE.finditer(text):
        fblock_id = match.group(1)  # e.g., "F1"
        fblock_name = match.group(2).strip()  # e.g., "Ingest Source Data"

        # Find status for this block (search region after match)
        region = text[match.start() : match.start() + 500]
        status_match = _STATUS_RE.search(region)
        status = Status.ACTIVE
        if status_match:
            try:
                status = Status(status_match.group(1).upper())
            except ValueError:
                pass

        cap_id = f"CAP-{fblock_id}"
        capabilities.append(
            Capability(
                id=cap_id,
                name=fblock_name,
                status=status,
                f_block=fblock_id,
                description=f"Functional block {fblock_id}: {fblock_name}",
                priority=Priority.HIGH,
            )
        )

    # Deduplicate by id (PlantUML may define same block multiple times)
    seen: set[str] = set()
    unique: list[Capability] = []
    for cap in capabilities:
        if cap.id not in seen:
            seen.add(cap.id)
            unique.append(cap)

    return unique


# ---------------------------------------------------------------------------
# Behaviors (from use-cases.md)
# ---------------------------------------------------------------------------

_PRIORITY_MAP = {
    "critical": Priority.CRITICAL,
    "high": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low": Priority.LOW,
}


def _extract_behaviors(text: str) -> list[Behavior]:
    """Parse UC catalog table from use-cases.md §2."""
    if not text:
        return []

    rows = find_table_after_heading(text, r"Use Case Catalog|UC Catalog")
    behaviors: list[Behavior] = []

    for row in rows:
        uc_id = row.get("uc_id", row.get("uc-id", "")).strip()
        title = row.get("title", "").strip()
        actor_str = row.get("actor_s", row.get("actor_s_", row.get("actors", ""))).strip()
        status_str = row.get("status", "ACTIVE").strip()
        priority_str = row.get("priority", "medium").strip().lower()
        frequency = row.get("frequency", "").strip()
        acceptance = row.get("acceptance_criteria", "").strip()
        reqs = row.get(
            "requirement_s", row.get("requirement_s_", row.get("requirements", ""))
        ).strip()
        f_block = row.get("f_block", row.get("f-block", "")).strip()

        if not uc_id:
            continue

        # Parse status from [ACTIVE] format
        status = _parse_status_bracket(status_str)
        priority = _PRIORITY_MAP.get(priority_str, Priority.MEDIUM)

        # Build postconditions from acceptance criteria
        postconditions = [acceptance] if acceptance else []

        # Build requirement traces
        req_list = [r.strip() for r in reqs.split(",") if r.strip()] if reqs else []

        behaviors.append(
            Behavior(
                id=uc_id,
                name=title,
                status=status,
                description=f"{title} (F-block: {f_block})",
                trigger=f"Actor: {actor_str}",
                actor=actor_str,
                frequency=frequency,
                priority=priority,
                postconditions=postconditions,
                tags=[f_block] if f_block else [],
            )
        )

    return behaviors


# ---------------------------------------------------------------------------
# Interfaces (from icd.md)
# ---------------------------------------------------------------------------

_IFACE_TYPE_MAP = {
    "rest": InterfaceType.REST,
    "external/rest": InterfaceType.REST,
    "websocket": InterfaceType.WEBSOCKET,
    "db": InterfaceType.DATABASE,
    "external/db": InterfaceType.DATABASE,
    "database": InterfaceType.DATABASE,
    "file": InterfaceType.FILE,
    "pipeline": InterfaceType.INTERNAL,
    "internal": InterfaceType.INTERNAL,
    "external": InterfaceType.EXTERNAL,
    "external/ml": InterfaceType.EXTERNAL,
    "message-queue": InterfaceType.MESSAGE_QUEUE,
}


def _extract_interfaces(text: str) -> list[Interface]:
    """Parse interface inventory matrix from icd.md §1."""
    if not text:
        return []

    rows = find_table_after_heading(text, r"Interface Inventory Matrix")
    interfaces: list[Interface] = []

    for row in rows:
        ifc_id = row.get("interface_id", "").strip()
        type_str = row.get("type", "internal").strip().lower()
        provider = row.get("provider_f_block", row.get("provider", "")).strip()
        consumer = row.get(
            "consumer_f_block_s", row.get("consumer_f_block_s_", row.get("consumer", ""))
        ).strip()
        protocol = row.get("protocol", "").strip()
        status_str = row.get("status", "ACTIVE").strip()

        if not ifc_id:
            continue

        iface_type = _IFACE_TYPE_MAP.get(type_str, InterfaceType.INTERNAL)
        status = _parse_status_bracket(status_str)

        interfaces.append(
            Interface(
                id=ifc_id,
                name=f"{provider} -> {consumer}",
                status=status,
                type=iface_type,
                protocol=protocol,
                provider=provider,
                consumer=consumer,
                description=f"{type_str} interface: {provider} -> {consumer} via {protocol}",
            )
        )

    return interfaces


# ---------------------------------------------------------------------------
# Constraints (from requirements-analysis.md)
# ---------------------------------------------------------------------------

_CONSTRAINT_TYPE_MAP = {
    "performance": ConstraintType.PERFORMANCE,
    "security": ConstraintType.SECURITY,
    "reliability": ConstraintType.RELIABILITY,
    "scalability": ConstraintType.SCALABILITY,
    "regulatory": ConstraintType.REGULATORY,
    "technology": ConstraintType.TECHNOLOGY,
    "operational": ConstraintType.OPERATIONAL,
    "maintainability": ConstraintType.OPERATIONAL,
    "usability": ConstraintType.OPERATIONAL,
}


def _extract_constraints(text: str) -> list[Constraint]:
    """Parse constraints + NFRs from requirements-analysis.md."""
    if not text:
        return []

    constraints: list[Constraint] = []

    # Extract from "Constraints" section — Technical + Organizational tables
    tc_rows = find_table_after_heading(text, r"Technical Constraints")
    for row in tc_rows:
        c_id = row.get("id", "").strip()
        desc = row.get("constraint", "").strip()
        rationale = row.get("rationale", "").strip()
        impact = row.get("impact", "").strip()
        if not c_id:
            continue
        constraints.append(
            Constraint(
                id=c_id,
                name=desc[:60] if desc else c_id,
                status=Status.ACTIVE,
                type=ConstraintType.TECHNOLOGY,
                rationale=rationale,
                description=f"{desc}. Impact: {impact}" if impact else desc,
            )
        )

    oc_rows = find_table_after_heading(text, r"Organizational Constraints")
    for row in oc_rows:
        c_id = row.get("id", "").strip()
        desc = row.get("constraint", "").strip()
        rationale = row.get("rationale", "").strip()
        impact = row.get("impact", "").strip()
        if not c_id:
            continue
        constraints.append(
            Constraint(
                id=c_id,
                name=desc[:60] if desc else c_id,
                status=Status.ACTIVE,
                type=ConstraintType.OPERATIONAL,
                rationale=rationale,
                description=f"{desc}. Impact: {impact}" if impact else desc,
            )
        )

    # Extract NFRs as constraints
    nfr_rows = find_table_after_heading(text, r"Non-Functional Requirements")
    for row in nfr_rows:
        req_id = row.get("req_id", "").strip()
        desc = row.get("description", "").strip()
        category = row.get("category", "").strip().lower()
        target = row.get("target", "").strip()
        verification = row.get("verification", "").strip()
        if not req_id:
            continue

        c_type = _CONSTRAINT_TYPE_MAP.get(category, ConstraintType.OPERATIONAL)
        constraints.append(
            Constraint(
                id=req_id,
                name=desc[:60] if desc else req_id,
                status=Status.ACTIVE,
                type=c_type,
                metric=category,
                threshold=target,
                rationale=f"Verification: {verification}" if verification else "",
                description=desc,
            )
        )

    return constraints


# ---------------------------------------------------------------------------
# Layers (from logical-architecture.md)
# ---------------------------------------------------------------------------


def _extract_layers(text: str) -> list[Layer]:
    """Parse layer inventory table from logical-architecture.md."""
    if not text:
        return []

    rows = find_table_after_heading(text, r"Layer Inventory")
    layers: list[Layer] = []

    for idx, row in enumerate(rows):
        layer_name = row.get("layer", "").strip().strip("*")
        responsibility = row.get("responsibility", "").strip()
        realizes = row.get("realizes", "").strip()
        file_count = row.get("file_count", "").strip()
        status_str = row.get("status", "ACTIVE").strip()

        if not layer_name:
            continue

        # Generate a clean ID
        layer_id = _slugify(layer_name)
        status = _parse_status_bracket(status_str)

        layers.append(
            Layer(
                id=layer_id,
                name=layer_name,
                status=status,
                order=idx,
                description=f"{responsibility}. Realizes: {realizes}. Files: {file_count}",
            )
        )

    return layers


# ---------------------------------------------------------------------------
# Components (from logical-architecture.md)
# ---------------------------------------------------------------------------

_COMPONENT_RE = re.compile(
    r"[-*]\s+\*\*(.+?)\*\*\s*(?:\(([^)]+)\))?\s*:?\s*(.*?)(?:\[(\w+)\])?$",
    re.MULTILINE,
)


def _extract_components(text: str) -> list[Component]:
    """Parse component listings from logical-architecture.md layer descriptions."""
    if not text:
        return []

    components: list[Component] = []
    seen_ids: set[str] = set()

    # Parse the traceability table for key components
    rows = find_table_after_heading(text, r"Component-to-Function Traceability")
    for row in rows:
        function = row.get("function", "").strip().strip("*")
        layer_str = row.get("realizing_layer_s_", row.get("realizing_layers", "")).strip()
        key_comp_str = row.get("key_components", "").strip()

        if not function or not key_comp_str:
            continue

        # Extract F-block from function name
        fblock_match = re.match(r"(F\d+)", function)
        f_block = fblock_match.group(1) if fblock_match else ""

        # Parse key components (backtick-delimited)
        comp_files = re.findall(r"`([^`]+)`", key_comp_str)
        for comp_file in comp_files:
            comp_id = _slugify(comp_file.replace(".py", ""))
            if comp_id in seen_ids:
                continue
            seen_ids.add(comp_id)

            components.append(
                Component(
                    id=comp_id,
                    name=comp_file,
                    status=Status.ACTIVE,
                    layer=layer_str.split(",")[0].strip() if layer_str else "",
                    f_block=f_block,
                    files=[comp_file],
                )
            )

    return components


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def _extract_uc_relationships(text: str) -> list[Relationship]:
    """Extract UC relationships (<<includes>>, <<extends>>) from use-cases.md §3."""
    if not text:
        return []

    relationships: list[Relationship] = []
    sections = extract_sections(text, level=3)

    # Look for includes/extends patterns
    includes_re = re.compile(r"(UC-\d+)\s*.*?<<includes?>>\s*.*?(UC-\d+)", re.IGNORECASE)
    extends_re = re.compile(r"(UC-\d+)\s*.*?<<extends?>>\s*.*?(UC-\d+)", re.IGNORECASE)

    for section_name, section_text in sections.items():
        for m in includes_re.finditer(section_text):
            relationships.append(
                Relationship(
                    type=RelationType.DEPENDS_ON,
                    from_id=m.group(1),
                    to_id=m.group(2),
                    description="<<includes>>",
                )
            )
        for m in extends_re.finditer(section_text):
            relationships.append(
                Relationship(
                    type=RelationType.DEPENDS_ON,
                    from_id=m.group(1),
                    to_id=m.group(2),
                    description="<<extends>>",
                    strength=Strength.WEAK,
                )
            )

    # Also parse list-based relationships
    # Pattern: "- UC-01, UC-02 → UC-06 (shared enrichment trigger)"
    arrow_re = re.compile(r"(UC-\d+(?:,\s*UC-\d+)*)\s*→\s*(UC-\d+)")
    for section_name, section_text in sections.items():
        for m in arrow_re.finditer(section_text):
            sources = re.findall(r"UC-\d+", m.group(1))
            target = m.group(2)
            for src in sources:
                if src != target:
                    relationships.append(
                        Relationship(
                            type=RelationType.DEPENDS_ON,
                            from_id=src,
                            to_id=target,
                            description="includes",
                        )
                    )

    return relationships


def _extract_layer_relationships(text: str) -> list[Relationship]:
    """Extract inter-layer dependency relationships from logical-architecture.md."""
    if not text:
        return []

    relationships: list[Relationship] = []

    # Parse communication mechanisms table
    rows = find_table_after_heading(text, r"Communication Mechanisms")
    for row in rows:
        source = row.get("source_layer", "").strip()
        target = row.get("target_layer", "").strip()
        mechanism = row.get("mechanism", "").strip()

        if not source or not target:
            continue

        # Extract layer names from "X → Y" format
        parts = re.split(r"\s*→\s*", source)
        if len(parts) == 2:
            source_layer = _slugify(parts[0])
            target_layer = _slugify(parts[1])
        else:
            source_layer = _slugify(source)
            target_layer = _slugify(target)

        relationships.append(
            Relationship(
                type=RelationType.DEPENDS_ON,
                from_id=source_layer,
                to_id=target_layer,
                description=mechanism,
            )
        )

    return relationships


def _extract_capability_relationships(
    capabilities: list[Capability],
    behaviors: list[Behavior],
) -> list[Relationship]:
    """Link behaviors (UCs) to capabilities (F-blocks) via realizes relationship."""
    relationships: list[Relationship] = []

    # Map F-block tag to capability ID
    fblock_to_cap = {cap.f_block: cap.id for cap in capabilities}

    for beh in behaviors:
        # Behaviors have f_block in tags
        for tag in beh.tags:
            if tag in fblock_to_cap:
                relationships.append(
                    Relationship(
                        type=RelationType.REALIZES,
                        from_id=beh.id,
                        to_id=fblock_to_cap[tag],
                        description=f"{beh.name} realizes {tag}",
                    )
                )

    return relationships


def _extract_component_capability_relationships(
    components: list[Component],
    capabilities: list[Capability],
) -> list[Relationship]:
    """Link components to capabilities (F-blocks) via realizes relationship."""
    relationships: list[Relationship] = []
    fblock_to_cap = {cap.f_block: cap.id for cap in capabilities}

    for comp in components:
        if comp.f_block and comp.f_block in fblock_to_cap:
            relationships.append(
                Relationship(
                    type=RelationType.REALIZES,
                    from_id=comp.id,
                    to_id=fblock_to_cap[comp.f_block],
                    description=f"{comp.name} realizes {comp.f_block}",
                )
            )

    return relationships


def _extract_interface_relationships(
    interfaces: list[Interface],
) -> tuple[list[Relationship], list[Actor]]:
    """Generate exposes/consumes relationships from interfaces.

    Returns:
        Tuple of (relationships, auto-discovered external actors).
    """
    relationships: list[Relationship] = []
    discovered_actors: dict[str, Actor] = {}

    for iface in interfaces:
        if iface.provider:
            provider_id = _resolve_fblock_ref(iface.provider)
            relationships.append(
                Relationship(
                    type=RelationType.EXPOSES,
                    from_id=provider_id,
                    to_id=iface.id,
                    description=f"{iface.provider} exposes {iface.id}",
                )
            )
        if iface.consumer:
            # Consumer may be comma-separated (multiple consumers)
            first_consumer = iface.consumer.split(",")[0].strip()
            consumer_id = _resolve_fblock_ref(first_consumer)
            relationships.append(
                Relationship(
                    type=RelationType.CONSUMES,
                    from_id=consumer_id,
                    to_id=iface.id,
                    description=f"{iface.consumer} consumes {iface.id}",
                )
            )
            # Auto-register non-F-block consumers as external actors
            if not re.match(r"CAP-F\d+", consumer_id) and consumer_id not in discovered_actors:
                discovered_actors[consumer_id] = Actor(
                    id=consumer_id,
                    name=first_consumer,
                    type=ActorType.EXTERNAL_SERVICE,
                    status=Status.ACTIVE,
                    description=f"External system (auto-discovered from ICD consumer: {iface.id})",
                )

    return relationships, list(discovered_actors.values())


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _parse_status_bracket(s: str) -> Status:
    """Parse status from [ACTIVE] format."""
    m = re.search(r"\[(\w+)\]", s)
    if m:
        try:
            return Status(m.group(1).upper())
        except ValueError:
            pass
    return Status.ACTIVE


def _slugify(text: str) -> str:
    """Convert text to a slug ID."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def _resolve_fblock_ref(text: str) -> str:
    """
    Resolve a text reference to an F-block into a CAP-Fx ID.

    Handles: "F2 Enrichment", "F1 Ingestion", "F4", etc.
    """
    # Try to extract Fx pattern
    m = re.match(r"(F\d+)", text.strip())
    if m:
        return f"CAP-{m.group(1)}"
    return _slugify(text)


def _guess_project(texts: dict[str, str]) -> str:
    """Try to extract project name from artifact headers."""
    for text in texts.values():
        m = re.search(r"\|\s*Project\s*\|\s*(.+?)\s*\|", text)
        if m:
            return m.group(1).strip()
    return "unknown"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    """CLI: extract architecture model from artifacts."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract architecture model from Tier 1 artifacts")
    parser.add_argument(
        "artifact_dir",
        help="Path to directory containing stage2 artifact markdown files",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output YAML path (default: <artifact_dir>/../architecture-model.yaml)",
    )
    parser.add_argument("--project", default="", help="Project name")
    parser.add_argument("--system", default="", help="System identifier")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    output_path = args.output or (artifact_dir.parent / "architecture-model.yaml")

    print(f"Extracting architecture model from: {artifact_dir}")
    model = extract_from_artifacts(artifact_dir, project=args.project, system=args.system)

    print(f"  Entities: {model.entity_count}")
    print(f"    Actors: {len(model.entities.actors)}")
    print(f"    Capabilities: {len(model.entities.capabilities)}")
    print(f"    Behaviors: {len(model.entities.behaviors)}")
    print(f"    Interfaces: {len(model.entities.interfaces)}")
    print(f"    Constraints: {len(model.entities.constraints)}")
    print(f"    Layers: {len(model.entities.layers)}")
    print(f"    Components: {len(model.entities.components)}")
    print(f"  Relationships: {model.relationship_count}")

    save_model(model, output_path)
    print(f"\nModel saved to: {output_path}")


if __name__ == "__main__":
    main()
