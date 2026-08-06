"""Parse markdown requirements documents into ArchitectureModel instances."""

from __future__ import annotations

import re
from architecture_model.core.types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Capability,
    Constraint,
    ConstraintType,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)


def parse_requirements_doc(text: str) -> ArchitectureModel:
    """Parse a markdown requirements document into an ArchitectureModel.

    Supported sections: # Actors, # Capabilities, # Constraints (case-insensitive).
    """
    sections = _split_sections(text)

    actors: list[Actor] = []
    capabilities: list[Capability] = []
    constraints: list[Constraint] = []
    relationships: list[Relationship] = []

    if "actors" in sections:
        actors = _parse_actors(sections["actors"])

    if "capabilities" in sections:
        capabilities, cap_rels = _parse_capabilities(sections["capabilities"])
        relationships.extend(cap_rels)

    if "constraints" in sections:
        constraints, con_rels = _parse_constraints(sections["constraints"])
        relationships.extend(con_rels)

    return ArchitectureModel(
        meta=ModelMeta(project="authored", schema_version="1.3"),
        entities=Entities(
            actors=actors,
            capabilities=capabilities,
            constraints=constraints,
        ),
        relationships=relationships,
    )


def _split_sections(text: str) -> dict[str, list[str]]:
    """Split text into sections by # headers."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        header_match = re.match(r"^#\s+(.+)$", line)
        if header_match:
            current = header_match.group(1).strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def _parse_item(line: str) -> tuple[str | None, str]:
    """Parse '- ID: Description' or '- Description'. Returns (id_or_None, description)."""
    stripped = line.lstrip()
    match = re.match(r"^-\s+(.+)$", stripped)
    if not match:
        return None, ""
    content = match.group(1)
    # Check for ID: Description pattern
    id_match = re.match(r"^([A-Z][A-Z0-9_.-]*(?:-\d+(?:\.\d+)*)?):\s*(.+)$", content)
    if id_match:
        return id_match.group(1), id_match.group(2)
    # Check for Name: Description (actor style)
    name_match = re.match(r"^([^:]+):\s*(.+)$", content)
    if name_match:
        return None, content  # Return full content, will parse name:desc in caller
    return None, content


def _get_indent(line: str) -> int:
    """Get indentation level of a line."""
    return len(line) - len(line.lstrip())


def _parse_actors(lines: list[str]) -> list[Actor]:
    """Parse actor items."""
    actors: list[Actor] = []
    counter = 0
    for line in lines:
        if not line.strip() or not line.strip().startswith("-"):
            continue
        stripped = line.strip()
        match = re.match(r"^-\s+(.+)$", stripped)
        if not match:
            continue
        content = match.group(1)
        # Parse "Name: description"
        parts = content.split(":", 1)
        if len(parts) == 2:
            name = parts[0].strip()
            desc = parts[1].strip()
        else:
            name = content
            desc = ""
        counter += 1
        actors.append(Actor(
            id=f"ACT-{counter}",
            name=name,
            status=Status.ACTIVE,
            description=desc,
            type=ActorType.HUMAN,
        ))
    return actors


def _parse_capabilities(lines: list[str]) -> tuple[list[Capability], list[Relationship]]:
    """Parse capability items with nesting support."""
    capabilities: list[Capability] = []
    relationships: list[Relationship] = []
    counter = 0
    parent_stack: list[str] = []  # (id, indent)
    indent_stack: list[int] = []

    for line in lines:
        if not line.strip() or not line.strip().startswith("-"):
            continue
        indent = _get_indent(line)
        stripped = line.strip()
        match = re.match(r"^-\s+(.+)$", stripped)
        if not match:
            continue
        content = match.group(1)

        # Parse ID and name
        id_match = re.match(r"^([A-Z][A-Z0-9_.-]*(?:-\d+(?:\.\d+)*)?):\s*(.+)$", content)
        if id_match:
            cap_id = id_match.group(1)
            name = id_match.group(2)
        else:
            counter += 1
            cap_id = f"CAP-{counter}"
            name = content

        capabilities.append(Capability(
            id=cap_id,
            name=name,
            status=Status.ACTIVE,
        ))

        # Handle nesting - pop stack until we find a parent with less indent
        while indent_stack and indent_stack[-1] >= indent:
            indent_stack.pop()
            parent_stack.pop()

        # If there's a parent, create contains relationship
        if parent_stack:
            relationships.append(Relationship(
                type=RelationType.CONTAINS,
                from_id=parent_stack[-1],
                to_id=cap_id,
            ))
            # Also add derives-from
            relationships.append(Relationship(
                type=RelationType.DERIVES_FROM,
                from_id=cap_id,
                to_id=parent_stack[-1],
            ))

        # Push current onto stack
        parent_stack.append(cap_id)
        indent_stack.append(indent)

    return capabilities, relationships


def _parse_constraints(lines: list[str]) -> tuple[list[Constraint], list[Relationship]]:
    """Parse constraint items with optional type in parentheses."""
    constraints: list[Constraint] = []
    relationships: list[Relationship] = []
    counter = 0
    parent_stack: list[str] = []
    indent_stack: list[int] = []

    for line in lines:
        if not line.strip() or not line.strip().startswith("-"):
            continue
        indent = _get_indent(line)
        stripped = line.strip()
        match = re.match(r"^-\s+(.+)$", stripped)
        if not match:
            continue
        content = match.group(1)

        # Extract parenthetical type at end
        constraint_type = ConstraintType.TECHNOLOGY
        type_match = re.search(r"\((\w+)\)\s*$", content)
        if type_match:
            type_str = type_match.group(1).lower()
            parsed = ConstraintType.parse(type_str)
            if isinstance(parsed, ConstraintType):
                constraint_type = parsed
            content = content[:type_match.start()].strip()

        # Parse ID and name
        id_match = re.match(r"^([A-Z][A-Z0-9_.-]*(?:-\d+(?:\.\d+)*)?):\s*(.+)$", content)
        if id_match:
            con_id = id_match.group(1)
            name = id_match.group(2)
        else:
            counter += 1
            con_id = f"CON-{counter}"
            name = content

        constraints.append(Constraint(
            id=con_id,
            name=name,
            status=Status.ACTIVE,
            type=constraint_type,
        ))

        # Handle nesting
        while indent_stack and indent_stack[-1] >= indent:
            indent_stack.pop()
            parent_stack.pop()

        if parent_stack:
            relationships.append(Relationship(
                type=RelationType.CONTAINS,
                from_id=parent_stack[-1],
                to_id=con_id,
            ))
            relationships.append(Relationship(
                type=RelationType.DERIVES_FROM,
                from_id=con_id,
                to_id=parent_stack[-1],
            ))

        parent_stack.append(con_id)
        indent_stack.append(indent)

    return constraints, relationships
