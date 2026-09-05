"""AI :class:`WorkOrder` contract.

A ``WorkOrder`` is a bounded, content-addressable request submitted to an
AI agent. It nominates:

* a set of :class:`SliceRef` inputs (at least one) — the agent MUST NOT
  read anything outside these slices;
* the set of :class:`ProposalKind` outputs the requester will accept;
* a hard :class:`Budget` (tokens + wall time);
* provenance (``requested_by``, ``created_at``).

The contract is versioned by :data:`SchemaVersions.WORK_ORDER` and
validated by ``spec/ai-work-order.schema.json`` (Draft 2020-12).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from importlib import resources
from typing import Any, Mapping, Sequence

from architecture_model.lifecycle.serialization import digest as _digest
from architecture_model.lifecycle.versions import SchemaVersions


class ProposalKind(str, Enum):
    """Every proposal type an AI work order may request."""

    MODEL_PATCH = "model-patch"
    DECOMPOSITION_PROPOSAL = "decomposition-proposal"
    SLICE_PROPOSAL = "slice-proposal"
    VIEW_CURATION_PROPOSAL = "view-curation-proposal"
    ARTIFACT_CANDIDATE = "artifact-candidate"
    IMPACT_ASSESSMENT = "impact-assessment"


@dataclass(frozen=True)
class SliceRef:
    """Reference to an input model slice at a specific model revision."""

    slice_id: str
    model_revision: str

    def to_dict(self) -> dict[str, str]:
        return {"slice_id": self.slice_id, "model_revision": self.model_revision}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SliceRef":
        return cls(slice_id=data["slice_id"], model_revision=data["model_revision"])


@dataclass(frozen=True)
class Budget:
    """Hard resource cap for the agent."""

    max_tokens: int
    max_wall_seconds: int

    def to_dict(self) -> dict[str, int]:
        return {
            "max_tokens": self.max_tokens,
            "max_wall_seconds": self.max_wall_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Budget":
        return cls(
            max_tokens=int(data["max_tokens"]),
            max_wall_seconds=int(data["max_wall_seconds"]),
        )


def _validate_iso8601(value: str) -> None:
    if not isinstance(value, str) or "T" not in value:
        raise ValueError(f"created_at must be ISO-8601 with 'T' separator: {value!r}")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"created_at is not ISO-8601: {value!r} ({exc})") from exc


_SCHEMA_CACHE: dict[str, Any] = {}


def _load_schema() -> dict[str, Any]:
    if "schema" not in _SCHEMA_CACHE:
        text = resources.files("architecture_model.spec").joinpath(
            "ai-work-order.schema.json"
        ).read_text(encoding="utf-8")
        _SCHEMA_CACHE["schema"] = json.loads(text)
    return _SCHEMA_CACHE["schema"]


@dataclass(frozen=True)
class WorkOrder:
    """Bounded AI work order.

    Invariants (enforced in ``__post_init__``):

    * ``input_slice_refs`` non-empty, no duplicate ``slice_id``.
    * ``expected_proposal_kinds`` non-empty.
    * ``budget.max_tokens`` and ``budget.max_wall_seconds`` positive.
    * ``created_at`` is ISO-8601 with a ``T`` separator.
    """

    id: str
    intent: str
    input_slice_refs: list[SliceRef]
    expected_proposal_kinds: list[ProposalKind]
    budget: Budget
    requested_by: str
    created_at: str
    parameters: dict[str, Any] = field(default_factory=dict)
    contract_version: str = SchemaVersions.WORK_ORDER

    def __post_init__(self) -> None:
        if not self.input_slice_refs:
            raise ValueError("input_slice_refs must be non-empty (bounded-input rule)")
        seen: set[str] = set()
        for ref in self.input_slice_refs:
            if ref.slice_id in seen:
                raise ValueError(f"duplicate slice_id in input_slice_refs: {ref.slice_id!r}")
            seen.add(ref.slice_id)
        if not self.expected_proposal_kinds:
            raise ValueError("expected_proposal_kinds must be non-empty")
        if self.budget.max_tokens <= 0:
            raise ValueError(
                f"budget.max_tokens must be positive: {self.budget.max_tokens}"
            )
        if self.budget.max_wall_seconds <= 0:
            raise ValueError(
                f"budget.max_wall_seconds must be positive: {self.budget.max_wall_seconds}"
            )
        _validate_iso8601(self.created_at)

    # ---- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic-key-order dict representation."""
        return {
            "id": self.id,
            "contract_version": self.contract_version,
            "intent": self.intent,
            "input_slice_refs": [r.to_dict() for r in self.input_slice_refs],
            "expected_proposal_kinds": [k.value for k in self.expected_proposal_kinds],
            "parameters": dict(self.parameters),
            "budget": self.budget.to_dict(),
            "requested_by": self.requested_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkOrder":
        return cls(
            id=data["id"],
            contract_version=data.get("contract_version", SchemaVersions.WORK_ORDER),
            intent=data["intent"],
            input_slice_refs=[SliceRef.from_dict(r) for r in data["input_slice_refs"]],
            expected_proposal_kinds=[
                ProposalKind(k) for k in data["expected_proposal_kinds"]
            ],
            parameters=dict(data.get("parameters", {})),
            budget=Budget.from_dict(data["budget"]),
            requested_by=data["requested_by"],
            created_at=data["created_at"],
        )

    def digest(self) -> str:
        """Content digest across all fields (see lifecycle.serialization)."""
        return _digest(self.to_dict())

    # ---- schema validation ------------------------------------------------

    @staticmethod
    def _validate_dict_against_schema(data: dict[str, Any]) -> list[str]:
        import jsonschema

        schema = _load_schema()
        validator = jsonschema.Draft202012Validator(schema)
        errors: list[str] = []
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
            path = "/".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"{path}: {err.message}")
        return errors

    def validate_schema(self) -> list[str]:
        """Validate ``self`` against the JSON Schema. Empty list == valid."""
        return self._validate_dict_against_schema(self.to_dict())

    # ---- convenience factory ---------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        intent: str,
        slices: Sequence[Any],
        accepts: Sequence[Any],
        requested_by: str,
        max_tokens: int,
        max_wall_seconds: int,
        parameters: Mapping[str, Any] | None = None,
        id: str | None = None,
        created_at: str | datetime | None = None,
    ) -> "WorkOrder":
        """Build a WorkOrder from natural Python types with auto-derived id/created_at."""
        normalized_slices: list[SliceRef] = []
        for item in slices:
            if isinstance(item, SliceRef):
                normalized_slices.append(item)
            elif isinstance(item, tuple):
                slice_id, revision = item
                normalized_slices.append(
                    SliceRef(slice_id=slice_id, model_revision=revision)
                )
            elif isinstance(item, Mapping):
                normalized_slices.append(SliceRef(**dict(item)))
            else:
                raise TypeError(f"Unsupported slice entry: {item!r}")

        normalized_accepts: list[ProposalKind] = [
            k if isinstance(k, ProposalKind) else ProposalKind(k) for k in accepts
        ]

        budget = Budget(max_tokens=max_tokens, max_wall_seconds=max_wall_seconds)

        if created_at is None:
            created_at_str = datetime.now(timezone.utc).isoformat()
        elif isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = created_at

        params = dict(parameters) if parameters else {}

        if id is None:
            payload = json.dumps(
                {
                    "intent": intent,
                    "slices": [(s.slice_id, s.model_revision) for s in normalized_slices],
                    "accepts": [k.value for k in normalized_accepts],
                    "requested_by": requested_by,
                    "budget": [max_tokens, max_wall_seconds],
                    "created_at": created_at_str,
                    "parameters": params,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            id = "sha256-v1:" + hashlib.sha256(payload.encode()).hexdigest()

        return cls(
            id=id,
            intent=intent,
            input_slice_refs=normalized_slices,
            expected_proposal_kinds=normalized_accepts,
            budget=budget,
            requested_by=requested_by,
            created_at=created_at_str,
            parameters=params,
        )
