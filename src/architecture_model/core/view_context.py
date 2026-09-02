"""Hierarchy-aware query context for architecture presentation views."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from architecture_model.core.hierarchy import load_model_hierarchy
from architecture_model.core.types import ArchitectureModel, BaseEntity, Relationship
from architecture_model.core.diagram_spec import Diagnostic


@dataclass(frozen=True)
class IndexedEntity:
    key: str
    local_id: str
    entity_type: str
    model: str
    value: BaseEntity
    source_path: str

    def __getattr__(self, name: str) -> Any:
        return getattr(self.value, name)


@dataclass(frozen=True)
class IndexedRelationship:
    source: str
    target: str
    kind: str
    model: str
    value: Relationship


def _normalized_file(value: str) -> str:
    path = PurePosixPath(str(value).replace("\\", "/"))
    parts = [part for part in path.parts if part not in ("", ".")]
    return "/".join(parts)


def _namespace(path: Path, root: Path) -> str:
    if path == (root / ".architecture-model.yaml").resolve():
        return "root"
    relative = path.relative_to(root)
    parts = list(relative.parent.parts)
    if parts and parts[0] == ".architecture-models":
        parts = parts[1:]
    return "/".join(parts) or relative.stem


class ArchitectureViewContext:
    """Indexed canonical hierarchy with stable, model-qualified entity keys."""

    def __init__(self, root: Path, models: dict[str, ArchitectureModel], warnings: list[str], histories: Any = None):
        self.root = root
        self.models = models
        self.diagnostics: list[Diagnostic] = []
        self._diagnostic_keys: set[tuple[str, str, str, str]] = set()
        for warning in warnings:
            self._add_diagnostic("warning", "HIERARCHY_WARNING", warning)
        self.warnings = self.diagnostics
        self.histories = histories
        self._entities: dict[str, IndexedEntity] = {}
        self._relationships: list[IndexedRelationship] = []
        self._files: dict[str, set[str]] = {}
        self._outgoing: dict[str, list[IndexedRelationship]] = {}
        self._incoming: dict[str, list[IndexedRelationship]] = {}
        self._system_aliases: dict[str, set[str]] = {namespace: {namespace} for namespace in models}
        self._parents: dict[str, str] = {}
        self._index()

    @classmethod
    def load(
        cls, model: ArchitectureModel, project_root: str | Path, histories: Any = None,
    ) -> "ArchitectureViewContext":
        root = Path(project_root).resolve()
        hierarchy, warnings = load_model_hierarchy(model, root)
        indexed: dict[str, ArchitectureModel] = {}
        for item in hierarchy:
            source = Path(getattr(item, "_source_path", root / ".architecture-model.yaml")).resolve()
            try:
                namespace = _namespace(source, root)
            except ValueError:
                warnings.append(f"Model source is outside project root: {source}")
                continue
            if namespace in indexed:
                warnings.append(f"Duplicate model namespace rejected: {namespace}")
                continue
            indexed[namespace] = item
        return cls(root, indexed, warnings, histories)

    @classmethod
    def from_repo(cls, project_root: str | Path, histories: Any = None) -> "ArchitectureViewContext":
        from architecture_model.core.parser import load_model

        root = Path(project_root).resolve()
        return cls.load(load_model(root / ".architecture-model.yaml"), root, histories)

    def _index(self) -> None:
        for namespace, model in sorted(self.models.items()):
            source = str(Path(getattr(model, "_source_path", self.root / ".architecture-model.yaml")))
            for entity_type, values in vars(model.entities).items():
                if not isinstance(values, list):
                    continue
                singular = "capability" if entity_type == "capabilities" else entity_type[:-1] if entity_type.endswith("s") else entity_type
                for entity in values:
                    if not hasattr(entity, "id"):
                        continue
                    key = f"{namespace}::{entity.id}"
                    if key in self._entities:
                        self._add_diagnostic("warning", "DUPLICATE_ENTITY", f"Duplicate entity ID rejected in {namespace}: {entity.id}")
                        continue
                    record = IndexedEntity(key, entity.id, singular, namespace, entity, source)
                    self._entities[key] = record
                    for file_path in getattr(entity, "files", []) or []:
                        self._files.setdefault(_normalized_file(file_path), set()).add(key)
                    source_file = getattr(entity, "source_file", None)
                    if source_file:
                        self._files.setdefault(_normalized_file(source_file), set()).add(key)
        for namespace, model in self.models.items():
            source = Path(getattr(model, "_source_path", self.root / ".architecture-model.yaml")).resolve()
            for parent_namespace, parent in self.models.items():
                parent_source = Path(getattr(parent, "_source_path", self.root / ".architecture-model.yaml")).resolve()
                for system in parent.entities.systems:
                    if not system.sub_model_ref:
                        continue
                    local = (parent_source.parent / system.sub_model_ref).resolve()
                    fallback = (self.root / system.sub_model_ref).resolve()
                    if source in {local, fallback}:
                        self._system_aliases[namespace].update({system.id, system.name, system.source_block})
                        self._parents[namespace] = parent_namespace

        for namespace, model in sorted(self.models.items()):
            for relationship in model.relationships:
                source_key = self._relationship_key(namespace, relationship.from_id)
                target_key = self._relationship_key(namespace, relationship.to_id)
                if source_key not in self._entities or target_key not in self._entities:
                    self._add_diagnostic("warning", "RELATIONSHIP_UNRESOLVED", f"Unresolved relationship in {namespace}: {source_key} -> {target_key}")
                    continue
                kind = getattr(relationship.type, "value", str(relationship.type))
                record = IndexedRelationship(source_key, target_key, kind, namespace, relationship)
                self._relationships.append(record)
                self._outgoing.setdefault(source_key, []).append(record)
                self._incoming.setdefault(target_key, []).append(record)
        self.warnings = self.diagnostics

    def _add_diagnostic(self, severity: str, code: str, message: str, source: str = "", **context: Any) -> None:
        key = (severity, code, message, source)
        if key not in self._diagnostic_keys:
            self._diagnostic_keys.add(key)
            self.diagnostics.append(Diagnostic(severity, code, message, source=source, context=context))

    @staticmethod
    def _relationship_key(namespace: str, reference: str) -> str:
        return reference if "::" in reference else f"{namespace}::{reference}"

    def entity(self, key: str, *, diagnose: bool = True) -> IndexedEntity | None:
        value = self._entities.get(key)
        if value is None and diagnose:
            self._add_diagnostic("warning", "ENTITY_NOT_FOUND", f"Entity not found: {key}", key=key)
        return value

    def qualified_entity(self, model: str, local_id: str) -> IndexedEntity | None:
        if "::" in local_id:
            if not local_id.startswith(f"{model}::"):
                self._add_diagnostic("warning", "QUALIFIED_SCOPE_MISMATCH", f"Qualified entity {local_id} is outside model {model}")
                return None
            return self.entity(local_id)
        return self.entity(f"{model}::{local_id}")

    def parent_model(self, model: str) -> str | None:
        return self._parents.get(model)

    def parent(self, model: str) -> str | None:
        return self.parent_model(model)

    def child_models(self, model: str) -> list[str]:
        return sorted(child for child, parent in self._parents.items() if parent == model)

    def child_models_for_system(self, system_key: str) -> list[str]:
        system = self.entity(system_key)
        if not system or system.entity_type != "system":
            return []
        return sorted(
            model for model in self.child_models(system.model)
            if system.local_id in self._system_aliases.get(model, set())
        )

    def children(self, model: str) -> list[str]:
        return self.child_models(model)

    def ancestors(self, model: str) -> list[str]:
        result: list[str] = []
        current = self.parent_model(model)
        while current is not None and current not in result:
            result.append(current)
            current = self.parent_model(current)
        return result

    def entity_parents(self, key: str) -> list[str]:
        return sorted(relationship.source for relationship in self.incoming(key, "contains"))

    def entity_children(self, key: str) -> list[str]:
        return sorted(relationship.target for relationship in self.outgoing(key, "contains"))

    def entity_ancestors(self, key: str) -> list[str]:
        result: list[str] = []
        seen = {key}
        frontier = self.entity_parents(key)
        while frontier:
            current = frontier.pop(0)
            if current in seen:
                continue
            seen.add(current)
            result.append(current)
            frontier.extend(parent for parent in self.entity_parents(current) if parent not in seen)
        return result

    def entities(self, entity_type: str | None = None, model: str | None = None) -> list[IndexedEntity]:
        return [
            item for item in sorted(self._entities.values(), key=lambda value: value.key)
            if (entity_type is None or item.entity_type == entity_type.rstrip("s"))
            and (model is None or item.model == model)
        ]

    def outgoing(self, key: str, kind: str | None = None) -> list[IndexedRelationship]:
        return self._filtered_relationships(self._outgoing.get(key, []), kind)

    def incoming(self, key: str, kind: str | None = None) -> list[IndexedRelationship]:
        return self._filtered_relationships(self._incoming.get(key, []), kind)

    def relationships(self, kind: str | None = None) -> list[IndexedRelationship]:
        return self._filtered_relationships(self._relationships, kind)

    @staticmethod
    def _filtered_relationships(values: Iterable[IndexedRelationship], kind: str | None) -> list[IndexedRelationship]:
        return sorted(
            (value for value in values if kind is None or value.kind == kind),
            key=lambda value: (value.source, value.target, value.kind),
        )

    def resolve(self, *, qualified_id: str = "", local_id: str = "", system: str = "") -> IndexedEntity | None:
        if qualified_id:
            return self.entity(qualified_id)
        matches = self.select(local_id=local_id, system=system)
        return matches[0] if len(matches) == 1 else None

    def select(
        self, *, qualified_id: str = "", local_id: str = "", name: str = "",
        system: str = "", source_file: str = "", tag: str = "",
    ) -> list[IndexedEntity]:
        if qualified_id:
            value = self.entity(qualified_id)
            return [value] if value else []
        namespaces = {
            namespace for namespace, aliases in self._system_aliases.items() if not system or system in aliases
        }
        values = [value for value in self.entities() if value.model in namespaces]
        if local_id:
            values = [value for value in values if value.local_id == local_id]
        if name:
            values = [value for value in values if value.name == name]
        if source_file:
            keys = self._files.get(_normalized_file(source_file), set())
            values = [value for value in values if value.key in keys]
        if tag:
            values = [value for value in values if tag in (value.tags or [])]
        if len(values) > 1:
            description = qualified_id or local_id or name or source_file or tag
            self._add_diagnostic("warning", "SELECTOR_AMBIGUOUS", f"Selector is ambiguous: {description}", selector=description)
            return []
        if not values:
            description = qualified_id or local_id or name or source_file or tag
            self._add_diagnostic("warning", "SELECTOR_NOT_FOUND", f"Selector did not match: {description}", selector=description)
        return values

    def components_owning_file(self, path: str) -> list[str]:
        return sorted(
            key for key in self._files.get(_normalized_file(path), set())
            if self._entities[key].entity_type == "component"
        )

    def behaviors_owning_file(self, path: str) -> list[str]:
        direct = {
            key for key in self._files.get(_normalized_file(path), set())
            if self._entities[key].entity_type == "behavior"
        }
        for component in self.components_owning_file(path):
            for relationship in self.outgoing(component) + self.incoming(component):
                other = relationship.target if relationship.source == component else relationship.source
                if self._entities[other].entity_type == "behavior":
                    direct.add(other)
        return sorted(direct)

    def systems_realizing_capability(self, capability_key: str) -> list[str]:
        owners = {
            self._entities[relationship.source].model
            for relationship in self.incoming(capability_key, "realizes")
            if self._entities[relationship.source].entity_type in {"component", "system"}
        }
        return sorted(owners)

    def provenance(self, key: str) -> dict[str, str]:
        entity = self.entity(key)
        if not entity:
            return {}
        return {"model": entity.model, "source_path": entity.source_path, "entity_id": entity.local_id}

    def linked_entities(self, key: str) -> list[str]:
        entity = self.entity(key)
        if not entity:
            return []
        local_ids: list[str] = []
        for field_name in ("actor_id", "capability_id", "provider", "consumer", "owner"):
            value = getattr(entity.value, field_name, "")
            if value:
                local_ids.append(value)
        local_ids.extend(getattr(entity.value, "requirements", []) or [])
        linked = {
            qualified for local_id in local_ids
            if (qualified := f"{entity.model}::{local_id}") in self._entities
        }
        return sorted(linked)
