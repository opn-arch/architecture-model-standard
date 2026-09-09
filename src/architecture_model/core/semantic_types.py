"""Nested semantic types used across entities.

All types are frozen dataclasses with explicit ``to_dict`` / ``from_dict``
so YAML round-trip is deterministic. Optional fields are omitted from
serialization when ``None`` (never emitted as ``null``) so byte-identical
guards pass across writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Likelihood(str, Enum):
    RARE = "rare"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    CERTAIN = "certain"


class Severity(str, Enum):
    NEGLIGIBLE = "negligible"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CATASTROPHIC = "catastrophic"


class TradeOffStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVISITED = "revisited"


@dataclass(frozen=True)
class FailureMode:
    id: str
    cause: str
    effect: str
    likelihood: Likelihood
    severity: Severity
    detection: str
    mitigation: str
    mitigated_by: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cause": self.cause,
            "effect": self.effect,
            "likelihood": self.likelihood.value,
            "severity": self.severity.value,
            "detection": self.detection,
            "mitigation": self.mitigation,
            **({"mitigated_by": list(self.mitigated_by)} if self.mitigated_by else {}),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FailureMode":
        return cls(
            id=d["id"],
            cause=d["cause"],
            effect=d["effect"],
            likelihood=Likelihood(d["likelihood"]),
            severity=Severity(d["severity"]),
            detection=d["detection"],
            mitigation=d["mitigation"],
            mitigated_by=tuple(d.get("mitigated_by", [])),
        )


@dataclass(frozen=True)
class TradeOff:
    id: str
    decision: str
    alternatives: tuple[str, ...]
    rationale: str
    consequences: tuple[str, ...]
    revisit_when: str
    status: TradeOffStatus = TradeOffStatus.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "decision": self.decision,
            "alternatives": list(self.alternatives),
            "rationale": self.rationale,
            "consequences": list(self.consequences),
            "revisit_when": self.revisit_when,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TradeOff":
        return cls(
            id=d["id"],
            decision=d["decision"],
            alternatives=tuple(d["alternatives"]),
            rationale=d["rationale"],
            consequences=tuple(d["consequences"]),
            revisit_when=d["revisit_when"],
            status=TradeOffStatus(d.get("status", "active")),
        )


@dataclass(frozen=True)
class SLO:
    metric: str
    target: str
    window: str
    current: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"metric": self.metric, "target": self.target, "window": self.window}
        if self.current is not None:
            d["current"] = self.current
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SLO":
        return cls(metric=d["metric"], target=d["target"], window=d["window"], current=d.get("current"))


@dataclass(frozen=True)
class RequirementRef:
    id: str
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id}
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RequirementRef":
        return cls(id=d["id"], note=d.get("note"))


@dataclass(frozen=True)
class VerificationRef:
    id: str
    method: str | None = None
    target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id}
        if self.method is not None:
            d["method"] = self.method
        if self.target is not None:
            d["target"] = self.target
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VerificationRef":
        return cls(id=d["id"], method=d.get("method"), target=d.get("target"))
