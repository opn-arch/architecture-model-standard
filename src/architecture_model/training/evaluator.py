"""
Multi-objective loss evaluator with Pareto front computation.

Computes how well a local LLM's extraction matches a frontier model's
ground truth across 4 objectives:
- Structural accuracy (entity/relationship F1)
- Completeness (entity recall)
- Reconstruction fidelity (code similarity)
- Validator score (schema/integrity validation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from architecture_model.core.types import ArchitectureModel
from architecture_model.core.validator import validate_model


# ---------------------------------------------------------------------------
# LossVector
# ---------------------------------------------------------------------------


@dataclass
class LossVector:
    """Multi-objective loss vector with 4 objectives."""

    structural_accuracy: float  # entity/relationship F1 vs oracle (0-1)
    completeness: float  # recall of oracle entities (0-1)
    reconstruction_fidelity: float  # code→model→code AST similarity (0-1)
    validator_score: float  # existing 0-100 validator score

    def dominates(self, other: LossVector) -> bool:
        """Pareto dominance: better or equal on ALL, strictly better on at least one."""
        self_vals = (
            self.structural_accuracy,
            self.completeness,
            self.reconstruction_fidelity,
            self.validator_score,
        )
        other_vals = (
            other.structural_accuracy,
            other.completeness,
            other.reconstruction_fidelity,
            other.validator_score,
        )

        at_least_one_strictly_better = False
        for s, o in zip(self_vals, other_vals):
            if s < o:
                return False  # worse on at least one objective
            if s > o:
                at_least_one_strictly_better = True

        return at_least_one_strictly_better


# ---------------------------------------------------------------------------
# Entity F1 computation
# ---------------------------------------------------------------------------


def _collect_typed_entities(model: ArchitectureModel) -> list[tuple[str, str, str]]:
    """Collect all entities as (type, id, name_lower) tuples."""
    entities: list[tuple[str, str, str]] = []
    type_lists = [
        ("actor", model.entities.actors),
        ("capability", model.entities.capabilities),
        ("behavior", model.entities.behaviors),
        ("interface", model.entities.interfaces),
        ("constraint", model.entities.constraints),
        ("layer", model.entities.layers),
        ("component", model.entities.components),
    ]
    for type_name, entity_list in type_lists:
        for entity in entity_list:
            entities.append((type_name, entity.id, entity.name.lower()))
    return entities


def compute_entity_f1(local_model: ArchitectureModel, oracle_model: ArchitectureModel) -> float:
    """
    Match entities by type + ID (exact), falling back to type + name (lowercase).
    Compute precision, recall, and F1.
    """
    local_entities = _collect_typed_entities(local_model)
    oracle_entities = _collect_typed_entities(oracle_model)

    if not local_entities and not oracle_entities:
        return 1.0  # vacuously true

    if not local_entities or not oracle_entities:
        return 0.0

    # Match local entities against oracle
    oracle_matched: set[int] = set()  # indices of matched oracle entities
    local_matched: set[int] = set()  # indices of matched local entities

    # Pass 1: match by type + ID (exact)
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_id == o_id:
                local_matched.add(li)
                oracle_matched.add(oi)
                break

    # Pass 2: match unmatched by type + name (lowercase)
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        if li in local_matched:
            continue
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_name == o_name:
                local_matched.add(li)
                oracle_matched.add(oi)
                break

    true_positives = len(local_matched)
    precision = true_positives / len(local_entities) if local_entities else 0.0
    recall = true_positives / len(oracle_entities) if oracle_entities else 0.0

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


# ---------------------------------------------------------------------------
# Relationship F1 computation
# ---------------------------------------------------------------------------


def compute_relationship_f1(local_model: ArchitectureModel, oracle_model: ArchitectureModel) -> float:
    """
    Match relationships by type + from_id + to_id.
    Compute precision, recall, and F1.
    """
    local_rels = {(r.type, r.from_id, r.to_id) for r in local_model.relationships}
    oracle_rels = {(r.type, r.from_id, r.to_id) for r in oracle_model.relationships}

    if not local_rels and not oracle_rels:
        return 1.0  # vacuously true

    if not local_rels or not oracle_rels:
        return 0.0

    true_positives = len(local_rels & oracle_rels)
    precision = true_positives / len(local_rels)
    recall = true_positives / len(oracle_rels)

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


# ---------------------------------------------------------------------------
# Reconstruction fidelity (line-overlap Jaccard)
# ---------------------------------------------------------------------------


def _compute_line_jaccard(original_code: str, reconstructed_code: str) -> float:
    """Jaccard similarity on normalized (stripped, non-empty) lines."""
    def normalize_lines(code: str) -> set[str]:
        return {line.strip() for line in code.splitlines() if line.strip()}

    orig_lines = normalize_lines(original_code)
    recon_lines = normalize_lines(reconstructed_code)

    if not orig_lines and not recon_lines:
        return 1.0

    if not orig_lines or not recon_lines:
        return 0.0

    intersection = len(orig_lines & recon_lines)
    union = len(orig_lines | recon_lines)

    return intersection / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# Evaluator class
# ---------------------------------------------------------------------------


class Evaluator:
    """Multi-objective loss evaluator for architecture model quality."""

    def compute_loss(
        self,
        local_model: ArchitectureModel,
        oracle_model: Optional[ArchitectureModel] = None,
        original_code: Optional[str] = None,
        reconstructed_code: Optional[str] = None,
    ) -> LossVector:
        """
        Compute multi-objective loss vector.

        L1: structural_accuracy — average of entity F1 and relationship F1
        L2: completeness — entity recall vs oracle
        L3: reconstruction_fidelity — Jaccard on normalized lines
        L4: validator_score — existing validator score (0-100)
        """
        # L4: always computable
        result = validate_model(local_model)
        validator_score = float(result.score)

        # L1 & L2: require oracle
        if oracle_model is not None:
            entity_f1 = compute_entity_f1(local_model, oracle_model)
            rel_f1 = compute_relationship_f1(local_model, oracle_model)
            structural_accuracy = (entity_f1 + rel_f1) / 2.0

            # Compute entity recall directly for completeness
            completeness = _compute_entity_recall(local_model, oracle_model)
        else:
            structural_accuracy = 0.0
            completeness = 0.0

        # L3: requires both code args
        if original_code is not None and reconstructed_code is not None:
            reconstruction_fidelity = _compute_line_jaccard(original_code, reconstructed_code)
        else:
            reconstruction_fidelity = 0.0

        return LossVector(
            structural_accuracy=structural_accuracy,
            completeness=completeness,
            reconstruction_fidelity=reconstruction_fidelity,
            validator_score=validator_score,
        )

    def compute_pareto_front(self, points: list[LossVector]) -> list[LossVector]:
        """Return non-dominated points from the input set."""
        if not points:
            return []

        front: list[LossVector] = []
        for candidate in points:
            # Check if any existing front member dominates candidate
            dominated = False
            for other in points:
                if other is candidate:
                    continue
                if other.dominates(candidate):
                    dominated = True
                    break
            if not dominated:
                front.append(candidate)

        return front


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_entity_recall(local_model: ArchitectureModel, oracle_model: ArchitectureModel) -> float:
    """Compute recall of oracle entities found in local model."""
    local_entities = _collect_typed_entities(local_model)
    oracle_entities = _collect_typed_entities(oracle_model)

    if not oracle_entities:
        return 1.0  # nothing to recall

    if not local_entities:
        return 0.0

    oracle_matched: set[int] = set()
    matched_local: set[int] = set()

    # Pass 1: match by type + ID
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_id == o_id:
                oracle_matched.add(oi)
                matched_local.add(li)
                break

    # Pass 2: match by type + name
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        if li in matched_local:
            continue
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_name == o_name:
                oracle_matched.add(oi)
                matched_local.add(li)
                break

    return len(oracle_matched) / len(oracle_entities)
