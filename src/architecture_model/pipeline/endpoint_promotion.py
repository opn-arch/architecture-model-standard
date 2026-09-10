"""Promote extracted endpoints to Interface entities — Phase 4-A Task 12.

Given an :class:`ArchitectureModel` and a repo root, run the three
endpoint extractors (CLI / HTTP / plugin_hook) and emit Interface
entities with appropriate ``subkind`` + ``metadata``. Auto-create
``exposes`` relationships from each endpoint's owning Component
(determined by matching the endpoint's file against ``component.files``).

Idempotent by construction: Interface ids are deterministic hashes of
``(subkind, file, name, lineno)``. Re-running over the same repo
updates existing Interfaces in place and skips duplicate ``exposes``
edges rather than compounding output.

The helper is a pure data-in / data-out transformation — the caller
(pipeline stage, MCP tool, CLI) decides when to invoke it. Keeping the
promotion decoupled from the observe stage means it can also run on
partially-loaded models (e.g. an OCA-side pipeline stitching data from
multiple repos).
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Iterable

from architecture_model.core.types import (
    ArchitectureModel,
    Interface,
    RelationType,
    Relationship,
    Status,
    Strength,
)
from architecture_model.pipeline.endpoint_extract import (
    extract_cli_endpoints,
    extract_http_endpoints,
    extract_plugin_hook_endpoints,
)
from architecture_model.pipeline.endpoint_types import Endpoint

__all__ = ["promote_endpoints_to_interfaces"]


def _endpoint_id(subkind: str, endpoint: Endpoint) -> str:
    """Deterministic Interface id for an extracted endpoint.

    Hashes ``(subkind, file, name, lineno)`` so re-running produces the
    same id and the promotion is idempotent.
    """
    payload = f"{subkind}|{endpoint.file}|{endpoint.name}|{endpoint.lineno}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8]
    return f"IF-{subkind.replace('_', '-')}-{digest}"


def _endpoint_metadata(endpoint: Endpoint) -> dict:
    """Serialize Endpoint into an Interface-metadata dict."""
    meta = dict(endpoint.metadata)
    # Always include an args list so validators can distinguish
    # unpopulated cli_command interfaces from populated ones with no args.
    meta["args"] = [
        {
            "name": arg.name,
            "type": arg.type,
            "required": arg.required,
            "default": arg.default,
        }
        for arg in endpoint.args
    ]
    return meta


def _python_files(repo_root: Path) -> list[Path]:
    """Return Python source files under ``repo_root`` excluding ignore dirs."""
    exclude = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build"}
    return sorted(
        p
        for p in repo_root.rglob("*.py")
        if not any(part in exclude for part in p.parts)
    )


def _collect_endpoints(
    repo_root: Path,
) -> list[tuple[str, Endpoint]]:
    """Run all three extractors and tag with subkind."""
    py_files = _python_files(repo_root)
    tagged: list[tuple[str, Endpoint]] = []
    tagged.extend(("cli_command", ep) for ep in extract_cli_endpoints(py_files))
    tagged.extend(("http_route", ep) for ep in extract_http_endpoints(py_files))
    tagged.extend(
        ("plugin_hook", ep) for ep in extract_plugin_hook_endpoints(repo_root)
    )
    return tagged


def promote_endpoints_to_interfaces(
    model: ArchitectureModel,
    repo_root: Path,
) -> ArchitectureModel:
    """Return a copy of ``model`` with extracted endpoints promoted.

    Behavior:

    * For every extracted endpoint, ensure an Interface exists with a
      deterministic id (updates existing in place — no duplicates).
    * For each endpoint whose ``file`` matches a component's ``files``,
      ensure an ``exposes`` relationship from that component to the
      Interface.
    * Pre-existing Interfaces / relationships not produced by this
      helper are preserved untouched.

    The returned model is a deep copy — the input is not mutated.
    """
    result = copy.deepcopy(model)
    tagged_endpoints = _collect_endpoints(repo_root)

    # File → owning component id (first match wins).
    file_to_component: dict[str, str] = {}
    for comp in result.entities.components:
        for f in getattr(comp, "files", []) or []:
            key = str(f)
            file_to_component.setdefault(key, comp.id)

    existing_ifaces: dict[str, Interface] = {
        i.id: i for i in result.entities.interfaces
    }
    existing_exposes: set[tuple[str, str]] = {
        (r.from_id, r.to_id)
        for r in result.relationships
        if r.type == RelationType.EXPOSES
    }

    for subkind, endpoint in tagged_endpoints:
        iface_id = _endpoint_id(subkind, endpoint)
        metadata = _endpoint_metadata(endpoint)
        if iface_id in existing_ifaces:
            iface = existing_ifaces[iface_id]
            iface.name = endpoint.name
            iface.subkind = subkind
            iface.metadata = metadata
            iface.source_file = endpoint.file
            iface.source_line = endpoint.lineno
        else:
            iface = Interface(
                id=iface_id,
                name=endpoint.name,
                status=Status.ACTIVE,
                source_file=endpoint.file,
                source_line=endpoint.lineno,
                subkind=subkind,
                metadata=metadata,
            )
            result.entities.interfaces.append(iface)
            existing_ifaces[iface_id] = iface

        comp_id = file_to_component.get(endpoint.file)
        if comp_id is None:
            continue
        edge_key = (comp_id, iface_id)
        if edge_key in existing_exposes:
            continue
        result.relationships.append(
            Relationship(
                type=RelationType.EXPOSES,
                from_id=comp_id,
                to_id=iface_id,
                strength=Strength.STRONG,
            )
        )
        existing_exposes.add(edge_key)

    return result
