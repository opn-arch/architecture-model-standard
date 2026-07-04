"""
MultiPassExtractor: 5-pass hierarchical architecture extraction.

Each pass targets a different architectural aspect using the appropriate
context slice, building the model incrementally. Later passes receive
the partial model from earlier passes to ensure consistency.

Pass 1: Structure    → layers, components (from directory tree)
Pass 2: Boundaries   → actors, interfaces (from API endpoints)
Pass 3: Behavior     → capabilities, behaviors (from tasks/workflows)
Pass 4: Relationships → relationships between all entities
Pass 5: Constraints  → constraints (from configs, decorators)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Relationship,
)
from architecture_model.training.context_builder import ContextSlices
from architecture_model.training.surrogate import _strip_fences


@dataclass
class PassResult:
    """Result from a single extraction pass."""
    pass_name: str
    raw_yaml: str
    entities: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True


# ---------------------------------------------------------------------------
# Pass-specific system prompts
# ---------------------------------------------------------------------------

_PASS_PROMPTS = {
    "structure": """\
You are extracting the STRUCTURAL layer of a software architecture.
From the package structure, import graph, and entry points below, identify:
- layers: architectural tiers (e.g. client, transport, models, utils, config)
- components: modules/packages within each layer

IMPORTANT: Identify MULTIPLE layers even from flat package layouts. Use the import \
graph and naming patterns to infer layering:
- Modules that are imported by many others → lower/foundation layer
- Modules that import many others → higher/application layer
- Modules with no internal imports → utility/support layer
- Modules with "transport", "connection", "pool" → transport/network layer
- Modules with "model", "types", "schema" → data/model layer
- Modules with "client", "api", "app" → application/client layer
- Modules with "auth", "middleware" → cross-cutting/middleware layer
- Modules with "config", "settings" → configuration layer

Output ONLY valid YAML:
layers:
  - id: L<n>
    name: <layer name>
    status: ACTIVE
components:
  - id: C<n>
    name: <component name>
    status: ACTIVE
    layer: L<n>

Output raw YAML only — no markdown fences, no explanation.""",

    "boundaries": """\
You are extracting the BOUNDARY layer of a software architecture.
From the code interfaces, public API, and class definitions below, identify:
- actors: external agents that interact with this system
- interfaces: APIs, protocols, data exchanges exposed or consumed

IMPORTANT for identifying actors — think about WHO or WHAT uses this code:
- If there's a Client/SDK class → there are "Developer" or "Application" actors using it
- If there's HTTP requests → there are "HTTP Server" or "Remote Service" actors
- If there's authentication → there are "User" or "Identity Provider" actors
- If there's file I/O → there's a "Filesystem" actor
- If there's a CLI → there's an "Operator" or "User" actor
- Proxies, load balancers, caches referenced → they are system actors

For interfaces, look at:
- Abstract base classes / Protocols (these DEFINE interfaces)
- Public methods on main classes (these EXPOSE interfaces)
- Type definitions for callbacks/hooks (these are extension interfaces)

Output ONLY valid YAML:
actors:
  - id: A<n>
    name: <actor name>
    status: ACTIVE
    type: human|system|external-service
interfaces:
  - id: I<n>
    name: <interface name>
    status: ACTIVE
    type: rest|grpc|graphql|event|cli

Output raw YAML only — no markdown fences, no explanation.""",

    "behavior": """\
You are extracting the BEHAVIORAL layer of a software architecture.
From the classes, methods, tasks, and workflows below, identify:
- capabilities: functional groups (what the system CAN do as a whole)
- behaviors: specific operational sequences or use cases

IMPORTANT for capabilities — group related functions into broader capabilities:
- HTTP methods (get, post, put, delete) → "HTTP Request Handling" capability
- Auth methods (login, token, refresh) → "Authentication" capability
- Retry/redirect/timeout logic → "Request Resilience" capability
- Encoding/decoding methods → "Content Processing" capability
- Connection pooling → "Connection Management" capability
- Streaming methods → "Streaming" capability

For behaviors, identify specific workflows or sequences:
- "Send HTTP Request" (build → connect → send → receive → decode)
- "Authenticate Request" (check credentials → add headers)
- "Handle Redirect" (detect 3xx → follow location)
- "Retry on Failure" (detect error → backoff → retry)

Output ONLY valid YAML:
capabilities:
  - id: CAP<n>
    name: <capability name>
    status: ACTIVE
behaviors:
  - id: B<n>
    name: <behavior name>
    status: ACTIVE

Output raw YAML only — no markdown fences, no explanation.""",

    "relationships": """\
You are extracting RELATIONSHIPS between architecture entities.
Given the full model so far and the import/dependency information, identify ALL \
relationships between entities.

Valid relationship types:
- contains: layer contains a component
- depends-on: component A depends on component B (A imports/uses B)
- exposes: component exposes an interface
- consumes: actor/component consumes an interface
- realizes: component realizes a capability
- constrained-by: component/capability is constrained by a constraint
- allocated-to: behavior is allocated to a component

IMPORTANT: Be thorough. For EVERY component, identify:
1. Which layer CONTAINS it
2. Which other components it DEPENDS-ON (from imports)
3. Which interfaces it EXPOSES (if it defines abstract APIs)
4. Which capabilities it REALIZES

For EVERY actor, identify which interfaces it CONSUMES.
For EVERY behavior, identify which component it is ALLOCATED-TO.

Generate at minimum one relationship per entity. Aim for 3-5 relationships per component.

Output ONLY valid YAML:
relationships:
  - type: <relationship-type>
    from: <source entity id>
    to: <target entity id>

Output raw YAML only — no markdown fences, no explanation.""",

    "constraints": """\
You are extracting architectural CONSTRAINTS.
From the configurations, type definitions, error handling, and patterns below, identify:
- constraints: non-functional requirements, design rules, architectural decisions

Look for:
- Type safety contracts (Protocol classes, type annotations) → "Type Safety" constraint
- Error handling patterns (custom exceptions hierarchy) → "Error Contract" constraint
- Async/sync duality → "Async Support" constraint
- Connection pooling/timeouts → "Performance" constraint
- TLS/SSL configuration → "Security" constraint
- Retry/backoff patterns → "Reliability" constraint
- Version compatibility → "Compatibility" constraint

Output ONLY valid YAML:
constraints:
  - id: CON<n>
    name: <constraint name>
    status: ACTIVE

Output raw YAML only — no markdown fences, no explanation.""",
}


class MultiPassExtractor:
    """5-pass hierarchical architecture extractor.

    Uses an LLM client (surrogate or oracle) to extract architecture
    incrementally, with each pass focusing on a specific aspect.
    """

    def __init__(
        self,
        client: Any,
        context: ContextSlices,
        project_name: str = "unknown",
    ) -> None:
        self._client = client
        self._context = context
        self._project_name = project_name
        self._pass_results: list[PassResult] = []

    async def extract(self) -> ArchitectureModel:
        """Run all 5 passes and merge into a complete model."""
        # Pass 1: Structure
        await self._pass_structure()
        # Pass 2: Boundaries
        await self._pass_boundaries()
        # Pass 3: Behavior
        await self._pass_behavior()
        # Pass 4: Relationships
        await self._pass_relationships()
        # Pass 5: Constraints
        await self._pass_constraints()

        return self._merge_results()

    async def _pass_structure(self) -> PassResult:
        """Pass 1: Extract layers and components from structure + import graph."""
        # Enrich structure with import graph to help identify layers
        context = (
            f"{self._context.structure}\n\n"
            f"# IMPORT GRAPH (use to identify layering)\n"
            f"{self._context.relationships}"
        )
        result = await self._run_pass("structure", context)
        self._pass_results.append(result)
        return result

    async def _pass_boundaries(self) -> PassResult:
        """Pass 2: Extract actors and interfaces from boundaries + structure."""
        # Enrich boundaries with structure overview and behavior for actor inference
        context = (
            f"# PROJECT OVERVIEW\n{self._context.structure}\n\n"
            f"# INTERFACES AND BOUNDARIES\n{self._context.boundaries}\n\n"
            f"# BEHAVIORAL PATTERNS (for actor inference)\n"
            f"{self._context.behavior[:500]}"
        )
        result = await self._run_pass("boundaries", context)
        self._pass_results.append(result)
        return result

    async def _pass_behavior(self) -> PassResult:
        """Pass 3: Extract capabilities and behaviors."""
        # Enrich behavior with structure for broader capability grouping
        context = (
            f"# PROJECT STRUCTURE\n{self._context.structure}\n\n"
            f"# BEHAVIORS AND METHODS\n{self._context.behavior}"
        )
        result = await self._run_pass("behavior", context)
        self._pass_results.append(result)
        return result

    async def _pass_relationships(self) -> PassResult:
        """Pass 4: Extract relationships (receives full prior model + imports)."""
        # Build rich context with full model and import graph
        prior_entities = self._summarize_prior_entities()
        context = (
            f"# FULL MODEL SO FAR (all entities with IDs and names)\n"
            f"{prior_entities}\n\n"
            f"# IMPORT/DEPENDENCY GRAPH\n{self._context.relationships}\n\n"
            f"# PROJECT STRUCTURE (for contains relationships)\n"
            f"{self._context.structure}"
        )
        result = await self._run_pass("relationships", context)
        self._pass_results.append(result)
        return result

    async def _pass_constraints(self) -> PassResult:
        """Pass 5: Extract constraints from configs + type contracts."""
        # Enrich with behavior patterns (reveal design constraints)
        context = (
            f"{self._context.constraints}\n\n"
            f"# BEHAVIORAL PATTERNS (reveal design constraints)\n"
            f"{self._context.behavior[:500]}\n\n"
            f"# BOUNDARIES (reveal interface contracts)\n"
            f"{self._context.boundaries[:500]}"
        )
        result = await self._run_pass("constraints", context)
        self._pass_results.append(result)
        return result

    async def _run_pass(self, pass_name: str, context_slice: str) -> PassResult:
        """Execute a single extraction pass."""
        system_prompt = _PASS_PROMPTS[pass_name]
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_slice},
        ]

        try:
            response = await self._client._chat(messages)
            content = response.get("message", {}).get("content", "")
            content = _strip_fences(content)

            raw = yaml.safe_load(content)
            if not isinstance(raw, dict):
                return PassResult(pass_name=pass_name, raw_yaml=content, success=False)

            # Extract entities and relationships
            entities = {k: v for k, v in raw.items() if k != "relationships"}
            relationships = raw.get("relationships", [])

            return PassResult(
                pass_name=pass_name,
                raw_yaml=content,
                entities=entities,
                relationships=relationships if isinstance(relationships, list) else [],
            )
        except Exception:
            return PassResult(pass_name=pass_name, raw_yaml="", success=False)

    def _summarize_prior_entities(self) -> str:
        """Build a YAML summary of all entities found in prior passes."""
        combined: dict[str, list] = {}
        for result in self._pass_results:
            if not result.success:
                continue
            for key, value in result.entities.items():
                if isinstance(value, list):
                    combined.setdefault(key, []).extend(value)

        if not combined:
            return "(no entities found yet)"

        try:
            return yaml.dump(combined, default_flow_style=False, sort_keys=False)
        except Exception:
            return str(combined)

    def _merge_results(self) -> ArchitectureModel:
        """Merge all pass results into a single ArchitectureModel."""
        # Combine all entities and relationships into a single dict
        merged: dict[str, Any] = {
            "meta": {
                "schema_version": "1.0",
                "project": self._project_name,
            },
            "entities": {
                "actors": [],
                "capabilities": [],
                "behaviors": [],
                "interfaces": [],
                "constraints": [],
                "layers": [],
                "components": [],
            },
            "relationships": [],
        }

        for result in self._pass_results:
            if not result.success:
                continue

            # Merge entities
            for key, value in result.entities.items():
                if key in merged["entities"] and isinstance(value, list):
                    merged["entities"][key].extend(value)

            # Merge relationships
            if result.relationships:
                merged["relationships"].extend(result.relationships)

        # Normalize LLM output before parsing
        self._normalize_merged(merged)

        # Add deterministic relationships from code analysis
        self._add_deterministic_relationships(merged)

        # Parse into ArchitectureModel using existing parser
        try:
            return _parse_raw(merged)
        except Exception:
            # Fallback: return empty model with whatever we got
            return ArchitectureModel(
                meta=ModelMeta(schema_version="1.0", project=self._project_name),
                entities=Entities(),
                relationships=[],
            )

    def _add_deterministic_relationships(self, merged: dict[str, Any]) -> None:
        """Add mechanically derivable relationships from code structure.

        Generates:
        1. 'contains' — layer contains component (from component.layer field)
        2. 'depends-on' — component depends on component (from import graph)

        These don't need LLM reasoning and fill the gap between LLM-generated
        semantic relationships and the complete picture.
        """
        entities = merged.get("entities", {})
        existing_rels = merged.setdefault("relationships", [])

        # Track existing relationships to avoid duplicates
        existing_set: set[tuple[str, str, str]] = set()
        for rel in existing_rels:
            if isinstance(rel, dict):
                existing_set.add((
                    rel.get("type", ""),
                    rel.get("from", ""),
                    rel.get("to", ""),
                ))

        # 1. Generate 'contains' relationships: layer → component
        layer_ids = {l["id"] for l in entities.get("layers", []) if isinstance(l, dict)}
        for comp in entities.get("components", []):
            if not isinstance(comp, dict):
                continue
            layer_ref = comp.get("layer", "")
            comp_id = comp.get("id", "")
            if layer_ref and comp_id and layer_ref in layer_ids:
                key = ("contains", layer_ref, comp_id)
                if key not in existing_set:
                    existing_rels.append({
                        "type": "contains",
                        "from": layer_ref,
                        "to": comp_id,
                    })
                    existing_set.add(key)

        # 2. Generate 'depends-on' relationships from import graph
        import_map = self._context.import_map
        if not import_map:
            self._add_semantic_relationships(merged, existing_rels, existing_set)
            return

        # Build a mapping: module_name → component_id
        # Match component names to file stems (e.g. component "client" → "_client.py")
        comp_name_to_id: dict[str, str] = {}
        for comp in entities.get("components", []):
            if not isinstance(comp, dict):
                continue
            comp_id = comp.get("id", "")
            comp_name = comp.get("name", "").lower()
            if comp_id and comp_name:
                comp_name_to_id[comp_name] = comp_id
                # Also index by words for multi-word names (e.g. "http client" → "client")
                for word in comp_name.split():
                    if word not in comp_name_to_id:
                        comp_name_to_id[word] = comp_id

        # Build mapping: file_path → component_id (multi-strategy matching)
        file_to_comp: dict[str, str] = {}
        for file_path in import_map:
            # Strategy 1: Match last path segment (file stem)
            stem = file_path.replace("/", ".").rstrip(".py")
            clean_stem = stem.lstrip("_").split(".")[-1]  # Take last part
            # Remove trailing underscores and common suffixes
            clean_stem = clean_stem.rstrip("_")

            if clean_stem in comp_name_to_id:
                file_to_comp[file_path] = comp_name_to_id[clean_stem]
                continue

            # Strategy 2: Match parent directory (e.g. _transports/asgi.py → transport)
            parts = file_path.split("/")
            if len(parts) > 1:
                parent = parts[-2].lstrip("_").rstrip("s")  # "transports" → "transport"
                if parent in comp_name_to_id:
                    file_to_comp[file_path] = comp_name_to_id[parent]
                    continue
                # Also try plural parent
                parent_full = parts[-2].lstrip("_")
                if parent_full in comp_name_to_id:
                    file_to_comp[file_path] = comp_name_to_id[parent_full]
                    continue

            # Strategy 3: Partial/prefix matching
            for comp_name, comp_id in comp_name_to_id.items():
                if (clean_stem.startswith(comp_name) or
                        comp_name.startswith(clean_stem)):
                    file_to_comp[file_path] = comp_id
                    break
            else:
                # Strategy 4: Underscore-separated parts match
                # e.g. "status_codes" → match "status" component
                for part in clean_stem.split("_"):
                    if part in comp_name_to_id:
                        file_to_comp[file_path] = comp_name_to_id[part]
                        break

        # Generate depends-on from import edges
        for file_path, imports in import_map.items():
            src_comp = file_to_comp.get(file_path)
            if not src_comp:
                continue

            for imported_module in imports:
                # Skip stdlib/external imports
                clean_import = imported_module.lstrip("_")

                # Find the target component - multi-strategy
                tgt_comp = comp_name_to_id.get(clean_import)
                if not tgt_comp:
                    # Try singular form (e.g. "transports" → "transport")
                    tgt_comp = comp_name_to_id.get(clean_import.rstrip("s"))
                if not tgt_comp:
                    # Try as parent dir import (e.g. importing "base" from transports)
                    # Skip common non-component imports
                    if clean_import in ("base", "types", "typing", "enum",
                                        "io", "os", "re", "sys", "json"):
                        continue
                    tgt_comp = comp_name_to_id.get(clean_import)

                if tgt_comp and tgt_comp != src_comp:
                    key = ("depends-on", src_comp, tgt_comp)
                    if key not in existing_set:
                        existing_rels.append({
                            "type": "depends-on",
                            "from": src_comp,
                            "to": tgt_comp,
                        })
                        existing_set.add(key)

        # 3. Generate semantic relationships (realizes, exposes)
        self._add_semantic_relationships(merged, existing_rels, existing_set)

    @staticmethod
    def _add_semantic_relationships(
        merged: dict[str, Any],
        existing_rels: list[dict[str, Any]],
        existing_set: set[tuple[str, str, str]],
    ) -> None:
        """Add semantic relationships derivable from entity cross-references.

        Generates:
        - 'realizes': component → capability (name/description overlap)
        - 'exposes': component → interface (if component handles APIs)
        - 'constrained-by': component → constraint (broad application)
        """
        entities = merged.get("entities", {})
        components = [c for c in entities.get("components", []) if isinstance(c, dict)]
        capabilities = [c for c in entities.get("capabilities", []) if isinstance(c, dict)]
        interfaces = [i for i in entities.get("interfaces", []) if isinstance(i, dict)]
        constraints = [c for c in entities.get("constraints", []) if isinstance(c, dict)]

        # Helper: extract keywords from name/description
        _STOP_WORDS = {"the", "a", "an", "and", "or", "for", "of", "to", "in",
                       "is", "it", "on", "at", "by", "with", "from", "as", "be",
                       "this", "that", "all", "are", "was", "were", "will", "can"}

        def _keywords(entity: dict[str, Any]) -> set[str]:
            text = f"{entity.get('name', '')} {entity.get('description', '')}".lower()
            words = set(text.replace("-", " ").replace("_", " ").split())
            return words - _STOP_WORDS

        # Build component keyword index
        comp_kws = [(c, _keywords(c)) for c in components]

        # 'realizes': component → capability
        # A component realizes a capability if their keywords overlap significantly
        for cap in capabilities:
            cap_kws = _keywords(cap)
            cap_id = cap.get("id", "")
            if not cap_id or len(cap_kws) < 2:
                continue

            best_comp = None
            best_score = 0
            for comp, kws in comp_kws:
                overlap = len(cap_kws & kws)
                if overlap > best_score:
                    best_score = overlap
                    best_comp = comp

            if best_comp and best_score >= 2:
                key = ("realizes", best_comp["id"], cap_id)
                if key not in existing_set:
                    existing_rels.append({
                        "type": "realizes",
                        "from": best_comp["id"],
                        "to": cap_id,
                    })
                    existing_set.add(key)

        # 'exposes': component → interface
        # Match by name similarity or if component name appears in interface description
        for iface in interfaces:
            iface_id = iface.get("id", "")
            iface_kws = _keywords(iface)
            if not iface_id:
                continue

            best_comp = None
            best_score = 0
            for comp, kws in comp_kws:
                overlap = len(iface_kws & kws)
                if overlap > best_score:
                    best_score = overlap
                    best_comp = comp

            if best_comp and best_score >= 1:
                key = ("exposes", best_comp["id"], iface_id)
                if key not in existing_set:
                    existing_rels.append({
                        "type": "exposes",
                        "from": best_comp["id"],
                        "to": iface_id,
                    })
                    existing_set.add(key)

        # 'constrained-by': apply each constraint to relevant components
        # Constraints typically apply to multiple components
        for con in constraints:
            con_id = con.get("id", "")
            con_kws = _keywords(con)
            if not con_id:
                continue

            # Apply to components whose keywords overlap, or if no match, to all
            applied = False
            for comp, kws in comp_kws:
                overlap = len(con_kws & kws)
                if overlap >= 1:
                    key = ("constrained-by", comp["id"], con_id)
                    if key not in existing_set:
                        existing_rels.append({
                            "type": "constrained-by",
                            "from": comp["id"],
                            "to": con_id,
                        })
                        existing_set.add(key)
                        applied = True

            # If constraint is broad (e.g. "security"), apply to all components
            if not applied and len(components) <= 20:
                for comp in components:
                    comp_id = comp.get("id", "")
                    key = ("constrained-by", comp_id, con_id)
                    if key not in existing_set:
                        existing_rels.append({
                            "type": "constrained-by",
                            "from": comp_id,
                            "to": con_id,
                        })
                        existing_set.add(key)

        # 'realizes': behavior → capability
        # A behavior realizes a capability if their keywords overlap (≥2 words)
        behaviors = [b for b in entities.get("behaviors", []) if isinstance(b, dict)]
        for cap in capabilities:
            cap_kws = _keywords(cap)
            cap_id = cap.get("id", "")
            if not cap_id or len(cap_kws) < 2:
                continue

            for beh in behaviors:
                beh_id = beh.get("id", "")
                if not beh_id:
                    continue
                beh_kws = _keywords(beh)
                overlap = len(cap_kws & beh_kws)
                if overlap >= 2:
                    key = ("realizes", beh_id, cap_id)
                    if key not in existing_set:
                        existing_rels.append({
                            "type": "realizes",
                            "from": beh_id,
                            "to": cap_id,
                        })
                        existing_set.add(key)

        # 'allocated-to': behavior → component (for orphan behaviors only)
        # If a behavior has NO relationships at all, allocate it to the best-matching component
        for beh in behaviors:
            beh_id = beh.get("id", "")
            if not beh_id:
                continue

            # Check if behavior already participates in any relationship
            has_rel = any(
                beh_id == t[1] or beh_id == t[2] for t in existing_set
            )
            if has_rel:
                continue

            # Find best-matching component by keyword overlap (≥1)
            beh_kws = _keywords(beh)
            best_comp = None
            best_score = 0
            for comp, kws in comp_kws:
                overlap = len(beh_kws & kws)
                if overlap > best_score:
                    best_score = overlap
                    best_comp = comp

            if best_comp and best_score >= 1:
                key = ("allocated-to", beh_id, best_comp["id"])
                if key not in existing_set:
                    existing_rels.append({
                        "type": "allocated-to",
                        "from": beh_id,
                        "to": best_comp["id"],
                    })
                    existing_set.add(key)

    @staticmethod
    def _normalize_merged(merged: dict[str, Any]) -> None:
        """Normalize LLM output to match expected enum values.

        LLMs often produce lowercase enum values that the parser expects
        in specific casing (e.g. 'rest' → 'REST', 'active' → 'ACTIVE').
        """
        # Known interface type mappings (lowercase → canonical)
        _INTERFACE_TYPES = {
            "rest": "REST", "websocket": "WebSocket", "database": "database",
            "file": "file", "message-queue": "message-queue", "message_queue": "message-queue",
            "internal": "internal", "external": "external",
            "grpc": "internal", "graphql": "internal", "event": "internal",
            "cli": "internal", "http": "REST", "api": "REST",
        }

        # Known actor type mappings
        _ACTOR_TYPES = {
            "human": "human", "system": "system",
            "external-service": "external-service", "external_service": "external-service",
            "service": "external-service", "external": "external-service",
        }

        # Known constraint type mappings
        _CONSTRAINT_TYPES = {
            "performance": "performance", "security": "security",
            "reliability": "reliability", "scalability": "scalability",
            "regulatory": "regulatory", "technology": "technology",
            "operational": "operational",
        }

        # Known relationship type mappings
        _REL_TYPES = {
            "realizes": "realizes", "contains": "contains",
            "depends-on": "depends-on", "depends_on": "depends-on",
            "exposes": "exposes", "consumes": "consumes",
            "traces-to": "traces-to", "traces_to": "traces-to",
            "allocated-to": "allocated-to", "allocated_to": "allocated-to",
            "constrained-by": "constrained-by", "constrained_by": "constrained-by",
            "uses": "consumes", "implements": "realizes",
            "triggers": "depends-on",
        }

        entities = merged.get("entities", {})

        # Normalize status fields (must be valid enum: ACTIVE, PLANNED, DORMANT, DEPRECATED)
        _VALID_STATUSES = {"ACTIVE", "PLANNED", "DORMANT", "DEPRECATED"}
        _STATUS_MAP = {
            "INACTIVE": "DORMANT", "DISABLED": "DORMANT", "ARCHIVED": "DEPRECATED",
            "RETIRED": "DEPRECATED", "DRAFT": "PLANNED", "TODO": "PLANNED",
            "WIP": "PLANNED", "EXPERIMENTAL": "PLANNED",
        }
        for etype in entities.values():
            if isinstance(etype, list):
                for entity in etype:
                    if isinstance(entity, dict):
                        if "status" in entity:
                            raw_status = str(entity["status"]).upper()
                            if raw_status in _VALID_STATUSES:
                                entity["status"] = raw_status
                            else:
                                entity["status"] = _STATUS_MAP.get(raw_status, "ACTIVE")

        # Normalize interface types
        for iface in entities.get("interfaces", []):
            if isinstance(iface, dict) and "type" in iface:
                raw_type = str(iface["type"]).lower()
                iface["type"] = _INTERFACE_TYPES.get(raw_type, "internal")

        # Normalize actor types
        for actor in entities.get("actors", []):
            if isinstance(actor, dict) and "type" in actor:
                raw_type = str(actor["type"]).lower()
                actor["type"] = _ACTOR_TYPES.get(raw_type, "human")

        # Normalize constraint types
        for con in entities.get("constraints", []):
            if isinstance(con, dict) and "type" in con:
                raw_type = str(con["type"]).lower()
                con["type"] = _CONSTRAINT_TYPES.get(raw_type, "technology")

        # Normalize relationship types
        for rel in merged.get("relationships", []):
            if isinstance(rel, dict) and "type" in rel:
                raw_type = str(rel["type"]).lower()
                rel["type"] = _REL_TYPES.get(raw_type, "depends-on")
