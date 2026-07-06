"""
Validator: Check architecture model invariants.

Validates:
1. Referential integrity — all relationship from/to IDs exist as entities
2. Orphan detection — entities with no relationships
3. Status consistency — PLANNED entities shouldn't be depended on by ACTIVE ones
4. ID uniqueness — no duplicate entity IDs across types
5. Completeness — all capabilities have at least one realizing behavior
6. Meta completeness — project and schema_version are set
7. v1.1 semantics — data-model fields, state-machine reachability
8. Regen readiness — constant/signature coverage for code regeneration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .types import ArchitectureModel, RelationType, Status


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    entity_id: Optional[str] = None
    context: Optional[str] = None

    def __str__(self) -> str:
        loc = f" [{self.entity_id}]" if self.entity_id else ""
        ctx = f" ({self.context})" if self.context else ""
        return f"[{self.severity.value}] {self.code}{loc}: {self.message}{ctx}"


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.INFO)

    @property
    def is_valid(self) -> bool:
        """Model is valid if there are no errors (warnings are acceptable)."""
        return self.error_count == 0

    @property
    def score(self) -> int:
        """Score 0-100. Deduct 10 per error, 2 per warning."""
        penalty = (self.error_count * 10) + (self.warning_count * 2)
        return max(0, 100 - penalty)

    def summary(self) -> str:
        return (
            f"Score: {self.score}/100 | "
            f"Errors: {self.error_count}, Warnings: {self.warning_count}, Info: {self.info_count}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_model(
    model: ArchitectureModel,
    strict: bool = False,
) -> ValidationResult:
    """
    Run all validation checks on the architecture model.

    Args:
        model: The model to validate.
        strict: If True, promote warnings to errors.

    Returns:
        ValidationResult with all issues found.
    """
    result = ValidationResult()

    _check_id_uniqueness(model, result)
    _check_referential_integrity(model, result)
    _check_orphan_entities(model, result)
    _check_status_consistency(model, result)
    _check_capability_realization(model, result)
    _check_meta_completeness(model, result)
    _check_v11_semantics(model, result)
    _check_regen_readiness(model, result)

    if strict:
        # Promote warnings to errors
        for issue in result.issues:
            if issue.severity == Severity.WARNING:
                issue.severity = Severity.ERROR

    return result


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _check_id_uniqueness(model: ArchitectureModel, result: ValidationResult) -> None:
    """Ensure no duplicate IDs across all entity types."""
    seen: dict[str, str] = {}  # id -> entity type

    type_entities = [
        ("actor", model.entities.actors),
        ("capability", model.entities.capabilities),
        ("behavior", model.entities.behaviors),
        ("interface", model.entities.interfaces),
        ("constraint", model.entities.constraints),
        ("layer", model.entities.layers),
        ("component", model.entities.components),
    ]

    for type_name, entities in type_entities:
        for entity in entities:
            if entity.id in seen:
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        code="DUPLICATE_ID",
                        message=f"ID '{entity.id}' duplicated across {seen[entity.id]} and {type_name}",
                        entity_id=entity.id,
                    )
                )
            else:
                seen[entity.id] = type_name


def _check_referential_integrity(model: ArchitectureModel, result: ValidationResult) -> None:
    """Ensure all relationship endpoints reference existing entities."""
    all_ids = model.all_entity_ids

    # Also include layer IDs that might be slugified differently
    layer_ids = {layer.id for layer in model.entities.layers}

    for rel in model.relationships:
        if rel.from_id not in all_ids:
            # Check if it's a slugified reference to a known concept
            if not _is_known_external(rel.from_id):
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="DANGLING_REF",
                        message=f"Relationship 'from' references unknown entity '{rel.from_id}'",
                        entity_id=rel.from_id,
                        context=f"{rel.type.value} -> {rel.to_id}",
                    )
                )

        if rel.to_id not in all_ids:
            if not _is_known_external(rel.to_id):
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="DANGLING_REF",
                        message=f"Relationship 'to' references unknown entity '{rel.to_id}'",
                        entity_id=rel.to_id,
                        context=f"{rel.from_id} {rel.type.value} ->",
                    )
                )


def _check_orphan_entities(model: ArchitectureModel, result: ValidationResult) -> None:
    """Find entities that participate in zero relationships."""
    referenced_ids: set[str] = set()
    for rel in model.relationships:
        referenced_ids.add(rel.from_id)
        referenced_ids.add(rel.to_id)

    # Only check behaviors and components for orphans (actors, layers, constraints may be standalone)
    for beh in model.entities.behaviors:
        if beh.id not in referenced_ids and beh.status == Status.ACTIVE:
            result.issues.append(
                ValidationIssue(
                    severity=Severity.INFO,
                    code="ORPHAN_BEHAVIOR",
                    message=f"Behavior '{beh.name}' has no relationships",
                    entity_id=beh.id,
                )
            )

    for comp in model.entities.components:
        if comp.id not in referenced_ids and comp.status == Status.ACTIVE:
            result.issues.append(
                ValidationIssue(
                    severity=Severity.INFO,
                    code="ORPHAN_COMPONENT",
                    message=f"Component '{comp.name}' has no relationships",
                    entity_id=comp.id,
                )
            )


def _check_status_consistency(model: ArchitectureModel, result: ValidationResult) -> None:
    """Warn if ACTIVE entities depend on PLANNED entities."""
    # Build status lookup
    status_map: dict[str, Status] = {}
    for actor in model.entities.actors:
        status_map[actor.id] = actor.status
    for cap in model.entities.capabilities:
        status_map[cap.id] = cap.status
    for beh in model.entities.behaviors:
        status_map[beh.id] = beh.status
    for iface in model.entities.interfaces:
        status_map[iface.id] = iface.status
    for con in model.entities.constraints:
        status_map[con.id] = con.status
    for layer in model.entities.layers:
        status_map[layer.id] = layer.status
    for comp in model.entities.components:
        status_map[comp.id] = comp.status

    for rel in model.relationships:
        from_status = status_map.get(rel.from_id)
        to_status = status_map.get(rel.to_id)

        if from_status == Status.ACTIVE and to_status == Status.PLANNED:
            if rel.type in (RelationType.DEPENDS_ON, RelationType.CONSUMES):
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="STATUS_MISMATCH",
                        message=f"ACTIVE entity depends on PLANNED entity",
                        entity_id=rel.from_id,
                        context=f"{rel.from_id} {rel.type.value} {rel.to_id}",
                    )
                )


def _check_capability_realization(model: ArchitectureModel, result: ValidationResult) -> None:
    """Ensure each ACTIVE capability has at least one realizing behavior."""
    realized_caps: set[str] = set()
    for rel in model.relationships:
        if rel.type == RelationType.REALIZES:
            realized_caps.add(rel.to_id)

    for cap in model.entities.capabilities:
        if cap.status == Status.ACTIVE and cap.id not in realized_caps:
            result.issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="UNREALIZED_CAPABILITY",
                    message=f"Capability '{cap.name}' has no realizing behaviors",
                    entity_id=cap.id,
                )
            )


def _check_meta_completeness(model: ArchitectureModel, result: ValidationResult) -> None:
    """Check that meta fields are properly filled."""
    if not model.meta.project:
        result.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="MISSING_META",
                message="Model meta.project is empty",
            )
        )
    if not model.meta.schema_version:
        result.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="MISSING_META",
                message="Model meta.schema_version is empty",
            )
        )
    if not model.meta.source_artifacts:
        result.issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="MISSING_META",
                message="Model meta.source_artifacts is empty",
            )
        )


def _check_regen_readiness(model: ArchitectureModel, result: ValidationResult) -> None:
    """Rule 8: Assess whether components have enough detail for code regeneration.

    Only applies to components that have test_contracts defined. Checks:
    1. Constant coverage — referenced constants in assertions vs defined constants
    2. Signature coverage — called functions in assertions vs defined signatures
    """
    import re

    for comp in model.entities.components:
        if not comp.test_contracts:
            continue

        # --- Constant coverage ---
        # Parse assertions for patterns like Obj.ATTR == literal → ATTR is a referenced constant
        referenced_constants: set[str] = set()
        for tc in comp.test_contracts:
            # Match patterns: Identifier.CONSTANT_NAME (uppercase with underscores)
            matches = re.findall(r'\b\w+\.([A-Z][A-Z0-9_]+)\b', tc.assertion)
            referenced_constants.update(matches)

        if referenced_constants:
            defined_names = {c.name for c in comp.constants}
            covered = len(referenced_constants & defined_names)
            coverage = covered / len(referenced_constants)

            if coverage < 0.3:
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        code="REGEN_UNREADY",
                        message=(
                            f"Component '{comp.name}' has {coverage:.0%} constant coverage "
                            f"({covered}/{len(referenced_constants)} referenced constants defined)"
                        ),
                        entity_id=comp.id,
                        context="regen_readiness",
                    )
                )
            elif coverage < 0.7:
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="REGEN_PARTIAL",
                        message=(
                            f"Component '{comp.name}' has {coverage:.0%} constant coverage "
                            f"({covered}/{len(referenced_constants)} referenced constants defined)"
                        ),
                        entity_id=comp.id,
                        context="regen_readiness",
                    )
                )

        # --- Signature coverage ---
        # Parse assertions for function calls: identifier(args)
        called_functions: set[str] = set()
        for tc in comp.test_contracts:
            # Match function calls: name(...) — excluding assert, common builtins
            matches = re.findall(r'\b([a-z_]\w*)\s*\(', tc.assertion)
            # Filter out Python keywords/builtins that aren't component functions
            excluded = {"assert", "len", "str", "int", "float", "bool", "list",
                        "dict", "set", "tuple", "type", "isinstance", "print",
                        "repr", "sorted", "reversed", "enumerate", "range", "zip",
                        "map", "filter", "hasattr", "getattr", "setattr"}
            called_functions.update(m for m in matches if m not in excluded)

        if called_functions:
            defined_sigs = {s.name for s in comp.signatures}
            covered = len(called_functions & defined_sigs)
            coverage = covered / len(called_functions)

            if coverage < 0.5:
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="REGEN_LOW_SIG_COVERAGE",
                        message=(
                            f"Component '{comp.name}' has {coverage:.0%} signature coverage "
                            f"({covered}/{len(called_functions)} called functions have signatures)"
                        ),
                        entity_id=comp.id,
                        context="regen_readiness",
                    )
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_known_external(entity_id: str) -> bool:
    """Check if an ID refers to a known external/synthetic reference.

    Layer IDs are always considered known. External service references
    (prefixed with 'external-') are valid targets. Other externals are
    discovered from config.
    """
    # Layer slugs are always valid relationship targets
    if entity_id.endswith("-layer"):
        return True

    # External service convention (e.g., external-llm, external-onedrive)
    if entity_id.startswith("external-"):
        return True

    # Short layer names (web, services, data, pipeline, scheduling)
    short_layers = {"web", "services", "data", "pipeline", "scheduling"}
    if entity_id in short_layers:
        return True

    # Try loading config-derived layers
    try:
        from architecture_model.config.loader import get_config
        from pathlib import Path

        config = get_config(Path("."))
        for layer in config.layers:
            if entity_id == layer.id:
                return True
    except Exception:
        pass

    return False


def _check_v11_semantics(model: ArchitectureModel, result: ValidationResult) -> None:
    """v1.1 semantic checks: data-model completeness, state-machine integrity."""
    from .types import ComponentKind, BehaviorPattern

    # Data-model components without fields: INFO hint
    for comp in model.entities.components:
        if hasattr(comp, 'kind') and comp.kind == ComponentKind.DATA_MODEL and not comp.fields:
            result.issues.append(ValidationIssue(
                severity=Severity.INFO,
                code="DATA_MODEL_NO_FIELDS",
                message="Data-model component has no fields defined",
                entity_id=comp.id,
            ))

    # State-machine: check for unreachable states
    for beh in model.entities.behaviors:
        if hasattr(beh, 'pattern') and beh.pattern == BehaviorPattern.STATE_MACHINE and beh.states:
            all_targets = set()
            for state in beh.states:
                for t in state.transitions:
                    all_targets.add(t.get("to", ""))
            reachable = {beh.states[0].name} | all_targets
            for state in beh.states:
                if state.name not in reachable:
                    result.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        code="STATE_UNREACHABLE",
                        message=f"Orphan state '{state.name}' has no incoming transitions",
                        entity_id=beh.id,
                    ))
