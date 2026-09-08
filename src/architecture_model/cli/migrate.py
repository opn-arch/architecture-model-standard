"""``architecture-model migrate`` subcommand.

Minimal 2.0 → 2.1 upgrade. Reads ``.architecture-model.yaml``, bumps
``meta.schema_version`` to the requested target, preserves every other
byte via targeted regex substitution on the meta block (no full YAML
round-trip, no key reordering, no re-quoting).

Deferred to a follow-up: skeleton-field discovery (report which
components/capabilities/etc. would benefit from Phase 2 semantic fields).

Design deviation from plan text (2026-09-08, execution):
- Plan uses Click (``CliRunner.invoke(cli, [...])``); this CLI is
  argparse-based (``main(argv)``). Test file was adapted to invoke
  ``main`` directly with ``capsys``. Behaviour and exit codes match
  the plan spec.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SUPPORTED_TARGETS = ("2.1",)

# Match a ``schema_version`` line under ``meta:`` in either quoted or
# unquoted form. Group 1 is the whitespace prefix, group 2 the current
# version literal (with or without surrounding quotes).
_SCHEMA_VERSION_LINE = re.compile(
    r"(?m)^(\s+)schema_version:\s*(['\"]?[\d.]+['\"]?)\s*$"
)


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "migrate",
        help="Migrate an architecture model to a newer schema version",
    )
    p.add_argument("model", help="Path to .architecture-model.yaml")
    p.add_argument(
        "--to",
        required=True,
        choices=_SUPPORTED_TARGETS,
        help="Target schema version (e.g. '2.1')",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing the file",
    )


def run(args: argparse.Namespace) -> int:
    """Execute the migration. Returns process exit code."""
    return _run(Path(args.model), args.to, args.dry_run)


def _run(model_path: Path, target: str, dry_run: bool) -> int:
    if not model_path.is_file():
        print(f"error: model file not found: {model_path}", file=sys.stderr)
        return 2

    original = model_path.read_text(encoding="utf-8")
    match = _SCHEMA_VERSION_LINE.search(original)
    if match is None:
        print(
            "error: no meta.schema_version line found; run the pipeline "
            "to (re)generate the model first",
            file=sys.stderr,
        )
        return 3

    current_raw = match.group(2)
    current = current_raw.strip("'\"")

    if current == target:
        print(f"error: model already at {target}", file=sys.stderr)
        return 4

    if dry_run:
        print(
            f"would set schema_version to {target} "
            f"(currently {current_raw}) in {model_path}"
        )
        return 0

    new_line = f"{match.group(1)}schema_version: '{target}'"
    updated = _SCHEMA_VERSION_LINE.sub(new_line, original, count=1)
    model_path.write_text(updated, encoding="utf-8")
    print(f"migrated {model_path} from {current} to {target}")
    return 0
