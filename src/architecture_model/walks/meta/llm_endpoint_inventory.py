"""LLM endpoint inventory audit walk.

Realizes ``CAP-WK.llm-endpoint-inventory``. Pure meta-walk (Tier T1) —
scans AMS + OCA source trees via ``ast.walk`` for LLM call-site
patterns, cross-references against a declared inventory at
``.architecture/llm/endpoints.yaml``, and emits :class:`EndpointCard`
records with verdicts ``covered`` | ``undeclared`` | ``stale`` |
``legacy``.

Detection is attribute-name-only (receiver identity is ignored) so
call sites like ``self.provider.structured(...)`` and
``_prov.structured(...)`` both match. False positives — genuine
``.complete`` calls on unrelated objects — become ``undeclared``
verdicts, not silent covers.

Cross-repo: OCA is discovered as a sibling directory
(``../opencode-arch`` by default; override via ``oca_root``). When the
sibling is missing the walk audits AMS only and emits an informational
``__meta__:oca_missing`` card — never raises.

Design decisions locked in
``docs/plans/2026-09-18-cap-df-part-13-llm-endpoint-inventory-plan.md``.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

# ---- constants -------------------------------------------------------

#: Attribute-name-based patterns. Bare-name patterns are listed separately.
_ATTR_PATTERNS: frozenset[str] = frozenset(
    {"complete", "structured", "stream", "llm_enrich", "run_via_policy"}
)

#: Bare-name (unqualified) call patterns, e.g. ``llm_callback(...)``.
_BARE_PATTERNS: frozenset[str] = frozenset({"llm_callback"})

#: Verdict labels.
COVERED = "covered"
UNDECLARED = "undeclared"
STALE = "stale"
LEGACY = "legacy"


# ---- data model ------------------------------------------------------


@dataclass(frozen=True)
class EndpointCard:
    """One audit finding per endpoint / call site."""

    endpoint_id: str
    verdict: str
    details: dict = field(default_factory=dict)
    location: str | None = None


@dataclass(frozen=True)
class InventoryReport:
    """Aggregate audit result."""

    cards: list[EndpointCard]
    declared_count: int
    ast_hit_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cards": [asdict(c) for c in self.cards],
            "declared_count": self.declared_count,
            "ast_hit_count": self.ast_hit_count,
        }


# ---- helpers ---------------------------------------------------------


def _repo_slug(repo: Path) -> str:
    """Last path component of the repo root."""
    return repo.resolve().name


def _iter_py_files(root: Path) -> list[Path]:
    """All ``*.py`` under ``root/src`` (deterministic, sorted).

    Restricted to ``src/`` to keep the audit surface bounded to
    production code. Test files, tools, and docs are out of scope.
    """
    src = root / "src"
    if not src.exists():
        return []
    return sorted(src.rglob("*.py"))


def _endpoint_id(repo: Path, py_file: Path, lineno: int) -> str:
    """``<repo_slug>:<posix_relpath_from_repo>:<lineno>``."""
    slug = _repo_slug(repo)
    rel = py_file.resolve().relative_to(repo.resolve()).as_posix()
    return f"{slug}:{rel}:{lineno}"


def _scan_file(py_file: Path) -> list[tuple[str, int]]:
    """Return list of ``(pattern_name, lineno)`` for LLM call sites."""
    try:
        source = py_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(py_file))
    except SyntaxError:
        return []

    hits: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _ATTR_PATTERNS:
            hits.append((func.attr, node.lineno))
        elif isinstance(func, ast.Name) and func.id in _BARE_PATTERNS:
            hits.append((func.id, node.lineno))
    return hits


def scan_repo(repo: Path) -> list[tuple[str, str, int]]:
    """Return list of ``(endpoint_id, pattern, lineno)`` for one repo.

    Deterministic ordering: sorted by ``(posix_relpath, lineno,
    pattern)`` since ``_iter_py_files`` already sorts by path.
    """
    results: list[tuple[str, str, int]] = []
    for py_file in _iter_py_files(repo):
        for pattern, lineno in _scan_file(py_file):
            eid = _endpoint_id(repo, py_file, lineno)
            results.append((eid, pattern, lineno))
    return results


def load_declared_inventory(ams_root: Path) -> list[dict]:
    """Parse ``.architecture/llm/endpoints.yaml`` from AMS.

    Returns the ``endpoints:`` list. Empty list if the file is missing
    or empty. Never raises on parse errors (silent-skip discipline).
    """
    path = ams_root / ".architecture" / "llm" / "endpoints.yaml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return []
    endpoints = data.get("endpoints") if isinstance(data, dict) else None
    return endpoints if isinstance(endpoints, list) else []


# ---- audit -----------------------------------------------------------


def audit_llm_endpoints(
    ams_root: Path,
    *,
    oca_root: Path | None = None,
) -> InventoryReport:
    """Audit LLM endpoint coverage across AMS + OCA.

    Parameters
    ----------
    ams_root
        Path to the AMS repo root (contains ``src/architecture_model``).
    oca_root
        Path to the OCA repo root. When ``None``, defaults to
        ``ams_root.parent / "opencode-arch"``. When the resolved path
        does not exist, the walk emits an informational
        ``__meta__:oca_missing`` card and audits AMS only.

    Returns
    -------
    InventoryReport with per-endpoint cards. Cards are sorted by
    endpoint_id for determinism.
    """
    ams_root = Path(ams_root).resolve()
    if oca_root is None:
        oca_root = ams_root.parent / "opencode-arch"
    else:
        oca_root = Path(oca_root).resolve()

    declared = load_declared_inventory(ams_root)
    declared_by_id: dict[str, dict] = {}
    for record in declared:
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            declared_by_id[record["id"]] = record

    # AST scan: always AMS; OCA only if present.
    ast_hits: dict[str, tuple[str, int]] = {}  # endpoint_id -> (pattern, lineno)
    for eid, pattern, lineno in scan_repo(ams_root):
        ast_hits[eid] = (pattern, lineno)

    cards: list[EndpointCard] = []
    if not oca_root.exists():
        cards.append(
            EndpointCard(
                endpoint_id="__meta__:oca_missing",
                verdict=UNDECLARED,
                details={
                    "reason": "OCA sibling directory not found",
                    "expected_path": str(oca_root),
                },
            )
        )
    else:
        for eid, pattern, lineno in scan_repo(oca_root):
            ast_hits[eid] = (pattern, lineno)

    # Merge declared + AST-visible into per-endpoint cards.
    all_ids = set(declared_by_id.keys()) | set(ast_hits.keys())
    for eid in sorted(all_ids):
        declared_rec = declared_by_id.get(eid)
        ast_hit = ast_hits.get(eid)
        migration_status = (
            declared_rec.get("migration_status") if declared_rec else None
        )

        if declared_rec and ast_hit:
            # Legacy overrides covered — declared+visible legacy endpoints
            # still surface as legacy so the audit drives migration.
            verdict = LEGACY if migration_status == "legacy" else COVERED
            details = {
                "pattern": ast_hit[0],
                "migration_status": migration_status,
                "kind": declared_rec.get("kind"),
                "task_class": declared_rec.get("task_class"),
                "tier": declared_rec.get("tier"),
            }
            location = declared_rec.get("location")
        elif declared_rec and not ast_hit:
            verdict = STALE
            details = {
                "reason": "declared inventory entry has no AST match",
                "migration_status": migration_status,
                "kind": declared_rec.get("kind"),
            }
            location = declared_rec.get("location")
        else:  # AST hit, not declared
            verdict = UNDECLARED
            details = {
                "pattern": ast_hit[0] if ast_hit else None,
                "lineno": ast_hit[1] if ast_hit else None,
            }
            location = eid.split(":", 1)[1] if ":" in eid else None

        cards.append(
            EndpointCard(
                endpoint_id=eid,
                verdict=verdict,
                details=details,
                location=location,
            )
        )

    # Preserve the __meta__ card at the top when present.
    meta = [c for c in cards if c.endpoint_id.startswith("__meta__:")]
    rest = [c for c in cards if not c.endpoint_id.startswith("__meta__:")]
    ordered = meta + rest

    return InventoryReport(
        cards=ordered,
        declared_count=len(declared_by_id),
        ast_hit_count=len(ast_hits),
    )


__all__ = [
    "COVERED",
    "UNDECLARED",
    "STALE",
    "LEGACY",
    "EndpointCard",
    "InventoryReport",
    "audit_llm_endpoints",
    "scan_repo",
    "load_declared_inventory",
]
