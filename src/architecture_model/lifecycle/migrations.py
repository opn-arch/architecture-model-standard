"""Deterministic schema migration framework for lifecycle contracts.

Purpose
-------
Provide a deterministic, auditable mechanism to bump a persisted
lifecycle payload from an older ``contract_version`` to the current
schema version declared in
:mod:`architecture_model.lifecycle.versions`.

Invariants
----------
* Exactly one migration may be registered per ``(kind, from_version)``.
  This guarantees a single, deterministic forward path.
* Every migration step MUST update ``contract_version`` to its declared
  ``to_version``. Steps that forget to bump the version are rejected.
* Migration provenance is APPENDED to ``payload["meta"]["migration_chain"]``
  and is NEVER overwritten. Prior chain entries are preserved verbatim.

Non-goal
--------
This module is the framework only. Phase 1 ships with an empty registry:
concrete migrations are added when a schema version actually bumps.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from architecture_model.lifecycle.versions import ContractKind, SchemaVersions

MigrationFn = Callable[[dict], dict]


@dataclass(frozen=True)
class Migration:
    """A single deterministic version bump for one contract kind."""

    kind: ContractKind
    from_version: str
    to_version: str
    apply: MigrationFn

    @property
    def id(self) -> str:
        return f"{self.kind.value}:{self.from_version}->{self.to_version}"


class MigrationError(ValueError):
    """Base class for migration failures."""


class MigrationPathNotFound(MigrationError):
    """No forward path from a payload's version to the current schema version."""


class MigrationCycle(MigrationError):
    """Cycle detected while resolving a migration path."""


class MigrationRegistry:
    """Registry of migrations, keyed by ``(kind, from_version)``."""

    def __init__(self) -> None:
        # Phase 1: registry starts EMPTY. No auto-registration.
        self._by_key: dict[tuple[ContractKind, str], Migration] = {}

    def register(self, migration: Migration) -> None:
        key = (migration.kind, migration.from_version)
        if key in self._by_key:
            raise MigrationError(
                f"duplicate migration registered for {migration.kind.value} "
                f"from {migration.from_version}"
            )
        self._by_key[key] = migration

    def path(
        self,
        kind: ContractKind,
        from_version: str,
        to_version: str,
    ) -> list[Migration]:
        if from_version == to_version:
            return []
        chain: list[Migration] = []
        seen: set[str] = {from_version}
        current = from_version
        while current != to_version:
            step = self._by_key.get((kind, current))
            if step is None:
                raise MigrationPathNotFound(
                    f"no migration registered for {kind.value} from {current} "
                    f"toward {to_version}"
                )
            if step.to_version in seen:
                raise MigrationCycle(
                    f"cycle detected while migrating {kind.value}: "
                    f"revisits {step.to_version}"
                )
            chain.append(step)
            seen.add(step.to_version)
            current = step.to_version
        return chain

    def migrate(
        self,
        kind: ContractKind,
        payload: Mapping[str, Any],
    ) -> tuple[dict, list[str]]:
        if "contract_version" not in payload:
            raise MigrationError("payload missing contract_version")
        target = SchemaVersions.for_kind(kind)
        current = payload["contract_version"]
        chain = self.path(kind, current, target)
        # Always return a deep copy to preserve the caller's payload.
        result: dict = copy.deepcopy(dict(payload))
        chain_ids: list[str] = []
        for step in chain:
            result = step.apply(result)
            if not isinstance(result, dict):
                raise MigrationError(
                    f"migration {step.id} did not return a dict"
                )
            if result.get("contract_version") != step.to_version:
                raise MigrationError(
                    f"migration {step.id} did not set contract_version to "
                    f"{step.to_version}"
                )
            chain_ids.append(step.id)
        # Provenance: append to meta.migration_chain, never overwrite.
        if chain_ids:
            meta = result.get("meta")
            if not isinstance(meta, dict):
                meta = {}
                result["meta"] = meta
            existing = meta.get("migration_chain")
            if not isinstance(existing, list):
                existing = []
            meta["migration_chain"] = list(existing) + chain_ids
        return result, chain_ids


# Module-level default registry — starts EMPTY for Phase 1.
DEFAULT_REGISTRY: MigrationRegistry = MigrationRegistry()


def migrate(
    kind: ContractKind,
    payload: Mapping[str, Any],
) -> tuple[dict, list[str]]:
    """Delegate to :data:`DEFAULT_REGISTRY`."""
    return DEFAULT_REGISTRY.migrate(kind, payload)


__all__ = [
    "DEFAULT_REGISTRY",
    "Migration",
    "MigrationCycle",
    "MigrationError",
    "MigrationFn",
    "MigrationPathNotFound",
    "MigrationRegistry",
    "migrate",
]
