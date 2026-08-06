"""
Extract an ArchitectureModel directly from source code analysis.

This is the "backward pass" — code → model — bypassing the stage2 markdown
artifact requirement. Derives entities and relationships from AST analysis,
import graphs, and project configuration files.
"""

from __future__ import annotations

import ast
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config.loader import get_config
from ..config.schema import ProjectConfig
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
from .constraint_detector import detect_constraints
from .route_detector import RouteInfo, detect_routes

from architecture_model.monitoring import monitored


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@monitored(
    module="extract.from_code",
    outputs=lambda r: {"component_count": len(r.entities.components), "relationship_count": len(r.relationships)},
)
def extract_from_code(
    project_root: str | Path,
    config: ProjectConfig | None = None,
    manifest: dict | None = None,
) -> ArchitectureModel:
    """Extract an architecture model directly from source code analysis.

    This bypasses the stage2 markdown artifact requirement by deriving
    entities and relationships from AST analysis, import graphs, and
    project configuration files.

    Args:
        project_root: Root directory of the project to analyze.
        config: Optional pre-loaded ProjectConfig. If None, auto-discovered.
        manifest: Optional pre-generated manifest dict. If None, generated fresh.

    Returns:
        Complete ArchitectureModel derived from code analysis.
    """
    root = Path(project_root).resolve()

    if config is None:
        config = get_config(root)

    if manifest is None:
        from ..manifest import generate_manifest

        manifest = generate_manifest(root, config).to_dict()

    # Derive all entities
    capabilities = _derive_capabilities(config)
    routes = detect_routes(root, _get_web_layer_dirs(config))
    actors = _derive_actors(routes, manifest)
    route_behaviors = _derive_route_behaviors(routes, config)
    service_behaviors = _detect_service_behaviors(root, config)
    behaviors = route_behaviors + service_behaviors
    components = _derive_components(manifest, config)
    interfaces = _derive_interfaces(manifest, config)
    layers = _derive_layers(config)
    constraints = detect_constraints(root)

    entities = Entities(
        actors=actors,
        capabilities=capabilities,
        behaviors=behaviors,
        interfaces=interfaces,
        constraints=constraints,
        layers=layers,
        components=components,
    )

    # Derive relationships
    relationships = _derive_relationships(
        capabilities=capabilities,
        behaviors=behaviors,
        components=components,
        interfaces=interfaces,
        constraints=constraints,
        layers=layers,
        config=config,
    )

    meta = ModelMeta(
        schema_version="1.0.0",
        project=config.name or root.name,
        system=config.system or config.name or root.name,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_artifacts=["code-analysis"],
    )

    return ArchitectureModel(meta=meta, entities=entities, relationships=relationships)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert text to a valid entity ID slug.

    Replaces path separators, dots, and special characters with hyphens,
    strips leading/trailing hyphens, and collapses runs of hyphens.
    """
    slug = re.sub(r"[/\\._\s{}]+", "-", text)
    slug = re.sub(r"[^a-zA-Z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-").lower()


def _file_to_source_block(file_path: str, config: ProjectConfig) -> str | None:
    """Determine which F-block a file belongs to based on directory membership."""
    for block in config.functional_blocks:
        for d in block.dirs:
            if file_path.startswith(d + "/") or file_path == d:
                return block.id
        for f in block.files:
            if file_path == f:
                return block.id
    return None


def _file_to_layer(file_path: str, config: ProjectConfig) -> str | None:
    """Determine which layer a file belongs to based on directory membership."""
    for layer in config.layers:
        for d in layer.dirs:
            if file_path.startswith(d + "/") or file_path == d:
                return layer.id
    return None


def _get_web_layer_dirs(config: ProjectConfig) -> list[str] | None:
    """Extract web-layer directories from config for route detection."""
    for layer in config.layers:
        if "web" in layer.id.lower() or "api" in layer.id.lower():
            return layer.dirs
    return None


# ---------------------------------------------------------------------------
# Entity derivation
# ---------------------------------------------------------------------------


def _derive_capabilities(config: ProjectConfig) -> list[Capability]:
    """Derive one capability per F-block in config."""
    capabilities: list[Capability] = []
    for block in config.functional_blocks:
        capabilities.append(
            Capability(
                id=f"CAP-{block.id}",
                name=block.name,
                status=Status.ACTIVE,
                description=block.description_source or f"Capability for {block.name}",
                source_block=block.id,
            )
        )
    return capabilities


def _derive_actors(routes: list[RouteInfo], manifest: dict) -> list[Actor]:
    """Infer actors from entry point types and external dependencies."""
    actors: list[Actor] = []
    seen_ids: set[str] = set()

    has_authenticated = any(r.is_authenticated for r in routes)
    has_anonymous = any(not r.is_authenticated for r in routes)

    if has_authenticated:
        actors.append(
            Actor(
                id="ACT-USER",
                name="Authenticated User",
                status=Status.ACTIVE,
                description="User who has authenticated with the system",
                type=ActorType.HUMAN,
            )
        )
        seen_ids.add("ACT-USER")

    if has_anonymous:
        actors.append(
            Actor(
                id="ACT-ANON",
                name="Anonymous User",
                status=Status.ACTIVE,
                description="Unauthenticated user or public endpoint consumer",
                type=ActorType.HUMAN,
            )
        )
        seen_ids.add("ACT-ANON")

    # Check for database dependencies in manifest modules
    db_indicators = {"asyncpg", "psycopg2", "pymongo", "sqlalchemy", "databases"}
    all_imports: set[str] = set()
    for mod in manifest.get("modules", []):
        for imp in mod.get("imports", []):
            all_imports.add(imp.split(".")[0])

    if all_imports & db_indicators:
        actors.append(
            Actor(
                id="ACT-DB",
                name="Database",
                status=Status.ACTIVE,
                description="External database service",
                type=ActorType.EXTERNAL_SERVICE,
            )
        )
        seen_ids.add("ACT-DB")

    return actors


def _derive_route_behaviors(
    routes: list[RouteInfo], config: ProjectConfig
) -> list[Behavior]:
    """Derive behaviors from route handlers."""
    behaviors: list[Behavior] = []
    seen_ids: set[str] = set()

    for route in routes:
        # Prefer function name for semantic IDs
        name_slug = _slugify(route.function_name) if route.function_name else ""
        if not name_slug:
            name_slug = _slugify(route.path) if route.path else "unknown"

        behavior_id = f"BEH-{route.method}-{name_slug}"

        # Deduplicate
        if behavior_id in seen_ids:
            continue
        seen_ids.add(behavior_id)

        # Determine priority based on HTTP method
        if route.method in ("POST", "PUT", "DELETE"):
            priority = Priority.HIGH
        else:
            priority = Priority.MEDIUM

        # Determine actor
        actor = "ACT-USER" if route.is_authenticated else "ACT-ANON"

        # Determine source_block from file location
        source_block = _file_to_source_block(route.file, config) or ""

        behaviors.append(
            Behavior(
                id=behavior_id,
                name=route.docstring or f"{route.method} {route.path}",
                status=Status.ACTIVE,
                description=route.docstring or f"Route handler: {route.method} {route.path}",
                trigger=f"HTTP {route.method} {route.path}",
                actor=actor,
                priority=priority,
                source_file=route.file,
                tags=[route.framework, source_block] if source_block else [route.framework],
            )
        )

    return behaviors


def _detect_service_behaviors(
    project_root: Path, config: ProjectConfig
) -> list[Behavior]:
    """Scan service-layer files for public functions using AST."""
    behaviors: list[Behavior] = []
    seen_ids: set[str] = set()

    # Find service-layer directories
    service_dirs: list[str] = []
    for layer in config.layers:
        if "service" in layer.id.lower():
            service_dirs.extend(layer.dirs)

    if not service_dirs:
        return behaviors

    for dir_path in service_dirs:
        target = project_root / dir_path
        if not target.is_dir():
            continue

        for py_file in sorted(target.rglob("*.py")):
            if py_file.name == "__init__.py":
                continue
            if "__pycache__" in str(py_file):
                continue

            rel_path = str(py_file.relative_to(project_root))
            module_name = py_file.stem
            source_block = _file_to_source_block(rel_path, config) or ""

            # Parse AST and extract public functions
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue

            for node in ast.iter_child_nodes(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name.startswith("_"):
                    continue

                behavior_id = f"BEH-SVC-{module_name}-{node.name}"
                if behavior_id in seen_ids:
                    continue
                seen_ids.add(behavior_id)

                docstring = ast.get_docstring(node) or ""
                first_line = docstring.split("\n")[0].strip() if docstring else ""

                behaviors.append(
                    Behavior(
                        id=behavior_id,
                        name=first_line or f"{module_name}.{node.name}",
                        status=Status.ACTIVE,
                        description=first_line or f"Service function: {module_name}.{node.name}",
                        source_file=rel_path,
                        source_line=node.lineno,
                        tags=["internal", source_block] if source_block else ["internal"],
                        priority=Priority.MEDIUM,
                    )
                )

    return behaviors


def _derive_components(manifest: dict, config: ProjectConfig) -> list[Component]:
    """Derive components from manifest modules, filtered to F-block directories."""
    components: list[Component] = []
    seen_ids: set[str] = set()

    for mod in manifest.get("modules", []):
        file_path = mod.get("file", "")
        if not file_path:
            continue

        source_block = _file_to_source_block(file_path, config)
        if source_block is None:
            # Skip modules outside F-block directories (tests, scripts, etc.)
            continue

        layer = _file_to_layer(file_path, config) or ""

        # Build component ID from file path
        comp_id = _slugify(file_path.removesuffix(".py"))
        if not comp_id:
            continue

        if comp_id in seen_ids:
            continue
        seen_ids.add(comp_id)

        # Use module docstring as description if available
        description = mod.get("docstring", "") or ""
        name = Path(file_path).stem.replace("_", " ").title()

        components.append(
            Component(
                id=comp_id,
                name=name,
                status=Status.ACTIVE,
                description=description,
                layer=layer,
                source_block=source_block,
                files=[file_path],
                source_file=file_path,
            )
        )

    return components


def _derive_interfaces(manifest: dict, config: ProjectConfig) -> list[Interface]:
    """Derive interfaces from cross-F-block imports in manifest."""
    interfaces: list[Interface] = []
    seen_pairs: set[tuple[str, str]] = set()

    for iface in manifest.get("interfaces", []):
        source_file = iface.get("source", "")
        target_file = iface.get("target", "")

        source_block = _file_to_source_block(source_file, config)
        target_block = _file_to_source_block(target_file, config)

        if source_block and target_block and source_block != target_block:
            # source_block = importer (consumer), target_block = importee (provider)
            pair = (target_block, source_block)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            interfaces.append(
                Interface(
                    id=f"IFC-{target_block}-{source_block}",
                    name=f"{target_block} → {source_block}",
                    status=Status.ACTIVE,
                    description=f"Interface: {target_block} provides to {source_block}",
                    type=InterfaceType.INTERNAL,
                    provider=f"CAP-{target_block}",
                    consumer=f"CAP-{source_block}",
                )
            )

    # External dependencies (imports to things not in any F-block)
    external_targets: set[str] = set()
    for iface in manifest.get("interfaces", []):
        target_file = iface.get("target", "")
        target_block = _file_to_source_block(target_file, config)
        if target_block is None and target_file:
            # This is an import to something outside known F-blocks
            import_path = iface.get("import_path", "")
            top_module = import_path.split(".")[0] if import_path else ""
            if top_module and top_module not in external_targets:
                external_targets.add(top_module)

    for ext in sorted(external_targets):
        ifc_id = f"IFC-EXT-{_slugify(ext)}"
        interfaces.append(
            Interface(
                id=ifc_id,
                name=f"External: {ext}",
                status=Status.ACTIVE,
                description=f"External dependency on {ext}",
                type=InterfaceType.EXTERNAL,
            )
        )

    return interfaces


def _derive_layers(config: ProjectConfig) -> list[Layer]:
    """Derive layers from config."""
    layers: list[Layer] = []
    for idx, layer_config in enumerate(config.layers):
        # Title-case from ID
        name = layer_config.id.replace("-", " ").title()
        layers.append(
            Layer(
                id=layer_config.id,
                name=name,
                status=Status.ACTIVE,
                description=layer_config.description or f"Architecture layer: {name}",
                order=idx,
                directories=layer_config.dirs,
            )
        )
    return layers


# ---------------------------------------------------------------------------
# Helpers for relationship derivation
# ---------------------------------------------------------------------------


def _cap_to_layer(cap_id: str, config: ProjectConfig) -> str | None:
    """Map a capability ID (CAP-F1) back to its layer ID."""
    block_id = cap_id.replace("CAP-", "")
    for block in config.functional_blocks:
        if block.id == block_id:
            for bdir in block.dirs:
                for layer in config.layers:
                    if bdir in layer.dirs or any(
                        bdir.startswith(ld + "/") or ld.startswith(bdir + "/")
                        for ld in layer.dirs
                    ):
                        return layer.id
    return None


# ---------------------------------------------------------------------------
# Relationship derivation
# ---------------------------------------------------------------------------


def _derive_relationships(
    capabilities: list[Capability],
    behaviors: list[Behavior],
    components: list[Component],
    interfaces: list[Interface],
    constraints: list[Constraint],
    layers: list[Layer],
    config: ProjectConfig,
) -> list[Relationship]:
    """Derive all relationships between entities."""
    relationships: list[Relationship] = []

    # Build quick lookup sets
    cap_ids = {c.id for c in capabilities}
    layer_ids = {l.id for l in layers}

    # realizes: behavior → capability of its F-block
    for beh in behaviors:
        source_block = ""
        # Extract source_block from tags
        for tag in beh.tags:
            for block in config.functional_blocks:
                if tag == block.id:
                    source_block = tag
                    break
            if source_block:
                break

        if source_block:
            cap_id = f"CAP-{source_block}"
            if cap_id in cap_ids:
                relationships.append(
                    Relationship(
                        type=RelationType.REALIZES,
                        from_id=beh.id,
                        to_id=cap_id,
                        description=f"{beh.name} realizes {cap_id}",
                    )
                )

    # realizes: component → capability of its F-block
    for comp in components:
        if comp.source_block:
            cap_id = f"CAP-{comp.source_block}"
            if cap_id in cap_ids:
                relationships.append(
                    Relationship(
                        type=RelationType.REALIZES,
                        from_id=comp.id,
                        to_id=cap_id,
                        description=f"{comp.name} realizes {cap_id}",
                    )
                )

    # depends-on: from interface pairs (cross-F-block dependencies)
    for iface in interfaces:
        if iface.type == InterfaceType.INTERNAL and iface.provider and iface.consumer:
            relationships.append(
                Relationship(
                    type=RelationType.DEPENDS_ON,
                    from_id=iface.consumer,
                    to_id=iface.provider,
                    description=f"{iface.consumer} depends on {iface.provider}",
                    strength=Strength.MODERATE,
                )
            )

    # depends-on: layer-to-layer from cross-layer interfaces (import-derived)
    layer_dep_pairs: set[tuple[str, str]] = set()
    for iface in interfaces:
        if iface.type == InterfaceType.INTERNAL and iface.provider and iface.consumer:
            consumer_layer = _cap_to_layer(iface.consumer, config)
            provider_layer = _cap_to_layer(iface.provider, config)
            if consumer_layer and provider_layer and consumer_layer != provider_layer:
                layer_dep_pairs.add((consumer_layer, provider_layer))

    for from_layer, to_layer in sorted(layer_dep_pairs):
        relationships.append(
            Relationship(
                type=RelationType.DEPENDS_ON,
                from_id=from_layer,
                to_id=to_layer,
                description=f"{from_layer} depends on {to_layer}",
                strength=Strength.STRONG,
            )
        )

    # exposes: capability → interface (where capability is provider)
    for iface in interfaces:
        if iface.provider and iface.provider in cap_ids:
            relationships.append(
                Relationship(
                    type=RelationType.EXPOSES,
                    from_id=iface.provider,
                    to_id=iface.id,
                    description=f"{iface.provider} exposes {iface.name}",
                )
            )

    # consumes: capability → interface (where capability is consumer)
    for iface in interfaces:
        if iface.consumer and iface.consumer in cap_ids:
            relationships.append(
                Relationship(
                    type=RelationType.CONSUMES,
                    from_id=iface.consumer,
                    to_id=iface.id,
                    description=f"{iface.consumer} consumes {iface.name}",
                )
            )

    # allocated-to: component → layer
    for comp in components:
        if comp.layer and comp.layer in layer_ids:
            relationships.append(
                Relationship(
                    type=RelationType.ALLOCATED_TO,
                    from_id=comp.id,
                    to_id=comp.layer,
                    description=f"{comp.name} allocated to {comp.layer}",
                )
            )

    # constrained-by: all capabilities → technology constraints
    tech_constraints = [
        c for c in constraints if c.type == ConstraintType.TECHNOLOGY
    ]
    for cap in capabilities:
        for con in tech_constraints:
            relationships.append(
                Relationship(
                    type=RelationType.CONSTRAINED_BY,
                    from_id=cap.id,
                    to_id=con.id,
                    description=f"{cap.name} constrained by {con.name}",
                    strength=Strength.WEAK,
                )
            )

    return relationships
