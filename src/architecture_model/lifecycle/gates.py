"""Recursive lifecycle gates for architecture packages.

Purpose
-------
Provides a small, composable gate system that answers the question
"is this architecture package (and every descendant) fit to publish?"
Each :class:`Gate` inspects a single :class:`ArchitecturePackage` and
returns a :class:`GateResult`. :func:`evaluate_tree` recurses the
package tree, collects per-package results, and lifts any blocking
child finding up to the root with breadcrumbs so callers can locate
the failure site in a hierarchy.

Invariants
----------
* Gates never mutate the package or filesystem — they read only.
* Output is fully deterministic: ``per_package`` is keyed by
  ``architecture_id`` with insertion order matching a depth-first walk
  sorted by child ``slug`` (as :func:`iter_descendants` already
  guarantees), and findings inside every :class:`GateResult` are
  sorted by ``(severity, code, path)``.
* ``blocking`` is true iff at least one ``severity == "error"`` finding
  is present. ``passed`` is true iff ``blocking`` is false.
* Only the string values in :data:`GATE_KINDS` may appear on a gate;
  the frozen-set is intentionally open — later tasks may add kinds by
  redefining it locally, but this module never mutates it.

Thread-safety
-------------
All public types are frozen dataclasses; all functions are pure with
respect to their inputs. Concurrent evaluation of independent
package trees is safe. Concurrent evaluation of the SAME tree while
its underlying files are being written is not safe (caller must hold
an appropriate lifecycle lock).

Error taxonomy
--------------
Gates do not raise for policy failures — they return findings with
``severity="error"``. Programmer errors (e.g. a package whose
``root`` is unset because it was not loaded via
:func:`load_package`) propagate as their native exceptions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Protocol

from architecture_model.lifecycle.package import (
    ArchitecturePackage,
    iter_descendants,
)

__all__ = [
    "GATE_KINDS",
    "SEVERITY_ORDER",
    "GateFinding",
    "GateResult",
    "Gate",
    "PackageGate",
    "SliceGate",
    "ViewGate",
    "ArtifactGate",
    "EvolutionGate",
    "DEFAULT_GATES",
    "TreeGateReport",
    "evaluate_tree",
]

GATE_KINDS: frozenset[str] = frozenset(
    {"package", "slice", "view", "artifact", "evolution"}
)

# Deterministic severity ordering: errors first, then warnings, then info.
SEVERITY_ORDER: dict[str, int] = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class GateFinding:
    """A single gate observation."""

    code: str
    message: str
    severity: str  # "error" | "warning" | "info"
    path: str = ""
    breadcrumbs: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateResult:
    """The outcome of one gate applied to one package."""

    kind: str
    package_id: str
    passed: bool
    blocking: bool
    findings: tuple[GateFinding, ...] = ()


class Gate(Protocol):
    """Structural protocol every gate implements."""

    kind: str

    def evaluate(self, pkg: ArchitecturePackage) -> GateResult:  # pragma: no cover
        ...


def _sort_findings(findings: Iterable[GateFinding]) -> tuple[GateFinding, ...]:
    return tuple(
        sorted(
            findings,
            key=lambda f: (
                SEVERITY_ORDER.get(f.severity, 99),
                f.code,
                f.path,
            ),
        )
    )


def _finalize(
    kind: str, package_id: str, findings: Iterable[GateFinding]
) -> GateResult:
    sorted_findings = _sort_findings(findings)
    blocking = any(f.severity == "error" for f in sorted_findings)
    return GateResult(
        kind=kind,
        package_id=package_id,
        passed=not blocking,
        blocking=blocking,
        findings=sorted_findings,
    )


class PackageGate:
    """Validate the package descriptor itself.

    Checks the declared ``model_ref`` and ``manifest_ref`` files exist
    on disk, and that ``root`` is set (i.e., the package was loaded
    via :func:`load_package`). Uniqueness of ``architecture_id`` in
    the tree is enforced by :func:`iter_descendants` — this gate
    only surfaces per-package issues.
    """

    kind = "package"

    def evaluate(self, pkg: ArchitecturePackage) -> GateResult:
        findings: list[GateFinding] = []
        if pkg.root is None:
            findings.append(
                GateFinding(
                    code="PACKAGE.NOT_LOADED",
                    message=(
                        f"package {pkg.architecture_id!r} has no root "
                        "set; construct via load_package()"
                    ),
                    severity="error",
                )
            )
            return _finalize(self.kind, pkg.architecture_id, findings)

        root: Path = pkg.root
        for attr, code in (
            ("model_ref", "PACKAGE.MISSING_MODEL"),
            ("manifest_ref", "PACKAGE.MISSING_MANIFEST"),
        ):
            rel = getattr(pkg, attr)
            target = (root / rel).resolve()
            root_resolved = root.resolve()
            if not target.is_relative_to(root_resolved):
                findings.append(
                    GateFinding(
                        code="PACKAGE.PATH_TRAVERSAL",
                        message=(
                            f"{attr}={rel!r} resolves outside package root"
                        ),
                        severity="error",
                        path=str(target),
                    )
                )
                continue
            if not target.exists():
                findings.append(
                    GateFinding(
                        code=code,
                        message=(
                            f"declared {attr}={rel!r} does not exist"
                        ),
                        severity="error",
                        path=str(target),
                    )
                )
        if not findings:
            findings.append(
                GateFinding(
                    code="PACKAGE.OK",
                    message=(
                        f"package descriptor for {pkg.architecture_id!r} "
                        "is well-formed"
                    ),
                    severity="info",
                )
            )
        return _finalize(self.kind, pkg.architecture_id, findings)


# TODO(T13/T14): implement slice validation using the ModelSlice type
# introduced by the curated-view tasks. Phase-1 is intentionally a
# no-op passer so the recursive gate infrastructure can land first.
class SliceGate:
    """Phase-1 placeholder — returns a single info finding."""

    kind = "slice"

    def evaluate(self, pkg: ArchitecturePackage) -> GateResult:
        return _finalize(
            self.kind,
            pkg.architecture_id,
            [
                GateFinding(
                    code="SLICE.NONE_DEFINED",
                    message=(
                        f"no slices defined for {pkg.architecture_id!r} "
                        "(phase-1 no-op)"
                    ),
                    severity="info",
                )
            ],
        )


# TODO(T15/T16): implement view validation once ViewSpec lands.
class ViewGate:
    """Phase-1 placeholder — returns a single info finding."""

    kind = "view"

    def evaluate(self, pkg: ArchitecturePackage) -> GateResult:
        return _finalize(
            self.kind,
            pkg.architecture_id,
            [
                GateFinding(
                    code="VIEW.NONE_DEFINED",
                    message=(
                        f"no views defined for {pkg.architecture_id!r} "
                        "(phase-1 no-op)"
                    ),
                    severity="info",
                )
            ],
        )


# TODO(T17/T18): implement artifact validation once ArtifactSpec lands.
class ArtifactGate:
    """Phase-1 placeholder — returns a single info finding."""

    kind = "artifact"

    def evaluate(self, pkg: ArchitecturePackage) -> GateResult:
        return _finalize(
            self.kind,
            pkg.architecture_id,
            [
                GateFinding(
                    code="ARTIFACT.NONE_DEFINED",
                    message=(
                        f"no artifacts defined for "
                        f"{pkg.architecture_id!r} (phase-1 no-op)"
                    ),
                    severity="info",
                )
            ],
        )


class EvolutionGate:
    """Check evolution metadata on the package.

    In phase-1 the package descriptor's ``contract_version`` field is
    the schema version for the package contract itself. A future
    ``migration_chain`` field (see terminology.md) will list applied
    migrations; if present it must be a list, otherwise the gate
    emits an info finding indicating no evolution history is
    recorded yet.
    """

    kind = "evolution"

    def evaluate(self, pkg: ArchitecturePackage) -> GateResult:
        findings: list[GateFinding] = []
        if not pkg.contract_version:
            findings.append(
                GateFinding(
                    code="EVOLUTION.MISSING_VERSION",
                    message=(
                        f"package {pkg.architecture_id!r} has no "
                        "contract_version"
                    ),
                    severity="error",
                )
            )
        migration_chain = getattr(pkg, "migration_chain", None)
        if migration_chain is not None and not isinstance(
            migration_chain, list
        ):
            findings.append(
                GateFinding(
                    code="EVOLUTION.BAD_CHAIN",
                    message=(
                        "migration_chain must be a list, got "
                        f"{type(migration_chain).__name__}"
                    ),
                    severity="error",
                )
            )
        if not findings:
            findings.append(
                GateFinding(
                    code="EVOLUTION.OK",
                    message=(
                        f"package {pkg.architecture_id!r} declares "
                        f"contract_version={pkg.contract_version!r}"
                    ),
                    severity="info",
                )
            )
        return _finalize(self.kind, pkg.architecture_id, findings)


DEFAULT_GATES: tuple[Gate, ...] = (
    PackageGate(),
    SliceGate(),
    ViewGate(),
    ArtifactGate(),
    EvolutionGate(),
)


@dataclass(frozen=True)
class TreeGateReport:
    """Aggregate gate report over an entire package tree."""

    overall_passed: bool
    overall_blocking: bool
    per_package: dict[str, tuple[GateResult, ...]] = field(default_factory=dict)
    breadcrumb_findings: tuple[GateFinding, ...] = ()


def _iter_with_root(
    root_pkg: ArchitecturePackage,
) -> list[ArchitecturePackage]:
    """Return root and all descendants in deterministic DFS order."""
    return list(iter_descendants(root_pkg, include_self=True))


def evaluate_tree(
    root_pkg: ArchitecturePackage,
    *,
    gates: Iterable[Gate] = DEFAULT_GATES,
) -> TreeGateReport:
    """Recursively evaluate gates for every descendant package.

    Any error-severity finding from a descendant is lifted into
    :attr:`TreeGateReport.breadcrumb_findings` with ``breadcrumbs``
    tracing from the root package's ``architecture_id`` down to the
    failure site.
    """
    gate_tuple = tuple(gates)
    ordered = _iter_with_root(root_pkg)
    # Build parent-chain map keyed by architecture_id.
    parent_chain: dict[str, tuple[str, ...]] = {
        root_pkg.architecture_id: (root_pkg.architecture_id,)
    }
    # Recompute chains by walking children explicitly, since
    # iter_descendants does not expose parents.
    def _build_chains(
        current: ArchitecturePackage, chain: tuple[str, ...]
    ) -> None:
        parent_chain[current.architecture_id] = chain
        assert current.root is not None
        # Reload children in the same lexical order used by
        # iter_descendants for consistency.
        from architecture_model.lifecycle.package import load_package

        loaded = [load_package(current.root / rel) for rel in current.children]
        loaded.sort(key=lambda c: c.slug)
        for child in loaded:
            _build_chains(child, chain + (child.architecture_id,))

    _build_chains(root_pkg, (root_pkg.architecture_id,))

    per_package_unsorted: dict[str, list[GateResult]] = {}
    breadcrumb_findings: list[GateFinding] = []
    overall_blocking = False

    for pkg in ordered:
        results: list[GateResult] = []
        chain = parent_chain.get(
            pkg.architecture_id, (pkg.architecture_id,)
        )
        for gate in gate_tuple:
            result = gate.evaluate(pkg)
            results.append(result)
            if result.blocking:
                overall_blocking = True
                for f in result.findings:
                    if f.severity != "error":
                        continue
                    breadcrumb_findings.append(
                        GateFinding(
                            code=f.code,
                            message=f.message,
                            severity=f.severity,
                            path=f.path,
                            breadcrumbs=chain,
                        )
                    )
        per_package_unsorted[pkg.architecture_id] = results

    # Deterministic key order.
    per_package: dict[str, tuple[GateResult, ...]] = {
        aid: tuple(per_package_unsorted[aid])
        for aid in sorted(per_package_unsorted)
    }
    breadcrumb_sorted = tuple(
        sorted(
            breadcrumb_findings,
            key=lambda f: (
                f.breadcrumbs,
                SEVERITY_ORDER.get(f.severity, 99),
                f.code,
                f.path,
            ),
        )
    )
    return TreeGateReport(
        overall_passed=not overall_blocking,
        overall_blocking=overall_blocking,
        per_package=per_package,
        breadcrumb_findings=breadcrumb_sorted,
    )
