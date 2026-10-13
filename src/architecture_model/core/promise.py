"""Promise dataclass — Phase 1 of T0.14 (v3 bootstrap).

A Promise is the fundamental unit of Plan B's schema 3.0: every semantic
field on a 2.1 entity (intent, goals, verification, ...) becomes a Promise
record with deterministic ID, delivery lineage, and verification evidence.

This module realizes COMP-PB-PROMISE-TYPE (see .architecture-model.plan-b.yaml
line 1655-1697). Round-trip serialization delegates to COMP-PB-PROMISE-PARSER
(TBD in a later task) but the core to_dict/from_dict lives here.

Shape (locked in walk-instance #1 + T0.14 plan):

    Promise(
        id,               # PR-<sha1[:12]> deterministic
        attribute,        # semantic field name (intent, goals, ...)
        content,          # str | list[str], the promised value
        owner_entity,     # entity ID that owns this Promise
        delivered_from,   # parent Promise ID or None
        verified_by,      # tuple[str, ...] verification IDs / evidence refs
        status,           # PromiseStatus enum
        gap_type,         # str | None, only when status=TYPED_GAP
        provenance,       # source of this Promise (turn / walk / plan ref)
    )

Invariants enforced at construction:
    - status=TYPED_GAP  ⇒  gap_type is non-empty
    - status!=TYPED_GAP ⇒  gap_type is None
    - attribute and owner_entity are non-empty
    - id, when supplied, must match compute_promise_id(attribute, content, owner)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

__all__ = ["Promise", "PromiseStatus", "compute_promise_id"]


class PromiseStatus(str, Enum):
    """Lifecycle state of a Promise.

    - OPEN: content asserted but not yet delivered from a parent
    - DELIVERED: content matches (or derives from) a parent's delivery
    - VERIFIED: at least one verified_by evidence record confirms delivery
    - TYPED_GAP: content deliberately empty; gap_type names the category
    - PROPOSED: content authored by an LLM or automated proposer, pending
      human review; promoted to OPEN or VERIFIED after validation
    """

    OPEN = "open"
    DELIVERED = "delivered"
    VERIFIED = "verified"
    TYPED_GAP = "typed-gap"
    PROPOSED = "proposed"


def _canonicalize_content(content: object) -> str:
    """Produce a canonical string form of content for hashing.

    Lists preserve order — ordering carries semantic weight (walk-instance #1
    finding G-WALK-PATH-P-ALREADY-DESIGNED noted that goals[1] ≠ goals[0]).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        return json.dumps(list(content), ensure_ascii=False, separators=(",", ":"))
    if content is None:
        return ""
    # Fallback: JSON with sorted keys for dicts, str() otherwise
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(content)


def compute_promise_id(attribute: str, content: object, owner_entity: str) -> str:
    """Deterministic PR-<sha1[:12]> from the identity triple (attribute, content, owner).

    Deliberately excludes status, gap_type, verified_by, delivered_from, provenance
    — those are lifecycle metadata, not identity. Two Promises with the same
    (attribute, content, owner) are the same Promise regardless of lifecycle stage.
    """
    payload = "|".join([
        attribute,
        _canonicalize_content(content),
        owner_entity,
    ])
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"PR-{digest[:12]}"


@dataclass(frozen=True)
class Promise:
    """A single semantic promise attached to an owning entity.

    Frozen dataclass: Promise identity is content-derived, so mutation
    would break the id-content invariant. Modify by constructing a new
    Promise (e.g. via dataclasses.replace).
    """

    attribute: str
    content: object                                       # str | list[str] | ...
    owner_entity: str
    delivered_from: str | None = None
    verified_by: tuple[str, ...] = field(default_factory=tuple)
    status: PromiseStatus = PromiseStatus.OPEN
    gap_type: str | None = None
    provenance: str = ""
    id: str = ""                                          # auto-derived if empty

    def __post_init__(self) -> None:
        # Field-level invariants
        if not self.attribute:
            raise ValueError("Promise.attribute must be non-empty")
        if not self.owner_entity:
            raise ValueError("Promise.owner_entity must be non-empty")

        # Normalize verified_by → tuple even if caller passed list
        if not isinstance(self.verified_by, tuple):
            object.__setattr__(self, "verified_by", tuple(self.verified_by))

        # Status/gap_type invariant
        if self.status == PromiseStatus.TYPED_GAP:
            if not self.gap_type:
                raise ValueError(
                    "Promise with status=TYPED_GAP must supply gap_type"
                )
        else:
            if self.gap_type is not None:
                raise ValueError(
                    "Promise.gap_type must be None unless status=TYPED_GAP"
                )

        # Compute or verify id
        expected = compute_promise_id(self.attribute, self.content, self.owner_entity)
        if not self.id:
            object.__setattr__(self, "id", expected)
        elif self.id != expected:
            raise ValueError(
                f"Promise.id {self.id!r} does not match computed {expected!r} "
                f"for (attribute={self.attribute!r}, owner={self.owner_entity!r})"
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Emit a canonical dict form suitable for YAML / JSON round-trip."""
        return {
            "id": self.id,
            "attribute": self.attribute,
            "content": self.content,
            "owner_entity": self.owner_entity,
            "delivered_from": self.delivered_from,
            "verified_by": list(self.verified_by),
            "status": self.status.value,
            "gap_type": self.gap_type,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Promise":
        """Round-trip constructor.

        Missing optional fields default to their dataclass defaults.
        Providing id in the dict triggers integrity check against
        the recomputed id.
        """
        try:
            status = PromiseStatus(d.get("status", "open"))
        except ValueError as exc:
            raise ValueError(f"Unknown Promise status: {d.get('status')!r}") from exc

        return cls(
            attribute=d["attribute"],
            content=d["content"],
            owner_entity=d["owner_entity"],
            delivered_from=d.get("delivered_from"),
            verified_by=tuple(d.get("verified_by") or ()),
            status=status,
            gap_type=d.get("gap_type"),
            provenance=d.get("provenance", "") or "",
            id=d.get("id", "") or "",
        )
