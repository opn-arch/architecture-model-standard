"""Endpoint dataclasses shared by the endpoint extractors.

An ``Endpoint`` is a callable surface that outside actors invoke:
Click/argparse subcommands, HTTP routes, or plugin hooks. The pipeline
promotes them into Interface entities (Phase 4-A Task 12); reference-doc
projectors (Tasks 13-15) render them as CLI reference / API reference /
plugin guide docs.

Frozen dataclasses: no field reassignment. Instances are not hashable
(``metadata`` is a dict) — extractor output is de-duplicated by
``(kind, name, file, lineno)`` tuples externally when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EndpointKind = Literal["cli_command", "http_route", "plugin_hook"]

__all__ = ["Endpoint", "EndpointArg", "EndpointKind"]


@dataclass(frozen=True)
class EndpointArg:
    """A single argument / option of a CLI command or HTTP route.

    ``type`` is a best-effort string (``"str"``, ``"int"``, Click type
    name, or ``""`` when unknown). ``default`` is the literal Python
    default (parsed from AST) or ``None`` when absent.
    """

    name: str
    type: str = ""
    required: bool = True
    default: Any = None


@dataclass(frozen=True)
class Endpoint:
    """A CLI / HTTP / plugin endpoint discovered by AST scan.

    ``file`` is the source-file path as a string. ``lineno`` is the
    line of the decorator or call site. ``metadata`` carries
    framework-specific extras (``"framework"``, ``"http_method"``,
    ``"path"``, ``"entry_point_group"``, ...).
    """

    kind: EndpointKind
    name: str
    file: str
    lineno: int
    args: tuple[EndpointArg, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
