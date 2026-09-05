"""Canonical serialization and content digest for lifecycle artifacts.

Purpose
-------
Provide deterministic, byte-identical serialization of Python objects so
they can be content-addressed via cryptographic digest. This is the
foundation for revision identity, semantic diff, and signature slots in
the architecture lifecycle.

Invariants
----------
* **Determinism.** ``canonical_json(x) == canonical_json(x)`` byte-for-byte
  across processes, machines, Python versions, and dict insertion orders.
* **NFC normalization.** All Unicode strings (both dict keys and string
  values) are normalized to Unicode Normal Form C before encoding, so
  visually identical strings hash to the same digest.
* **Sorted keys.** Object keys are sorted lexicographically at every
  nesting level.
* **Compact.** No insignificant whitespace; separators are ``(",", ":")``.
* **UTF-8, no BOM.** ``ensure_ascii=False`` — Unicode passes through.

Forbidden types
---------------
* ``float`` — floating point representation is not stable across
  platforms. Use ``int`` for exact integers.
* ``decimal.Decimal`` — rejected in Phase 1 to keep the numeric surface
  strictly integral. A future phase may add a canonical decimal encoding.
* Non-string mapping keys — raise ``TypeError``.

Accepted types
--------------
``int``, ``str``, ``bool``, ``None``, ``list``, ``tuple`` (encoded as
JSON array), ``dict`` (string keys only).

Key-path exclusion semantics
----------------------------
``exclude_paths`` is a sequence of tuples. Each tuple is a path of
string keys applied at successive nesting levels of ``dict`` values. For
example, ``exclude_paths=[("generated_at",), ("meta", "signatures")]``
strips the top-level ``generated_at`` key AND the nested
``meta.signatures`` key before serialization. Missing paths are silent
no-ops. List/tuple traversal is not supported in Phase 1.

Thread safety
-------------
All functions in this module are pure and thread-safe. They do not
mutate their inputs.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any, Sequence

import yaml

from architecture_model.lifecycle.versions import SchemaVersions


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _strip_paths(obj: Any, paths: Sequence[tuple[str, ...]]) -> Any:
    """Return a copy of ``obj`` with the given key-paths removed.

    Only traverses ``dict`` nodes. Missing paths are ignored.
    """
    if not paths:
        return obj
    # Group paths by first key
    if not isinstance(obj, dict):
        return obj
    # Collect top-level keys to drop entirely and nested paths per key
    drop_keys: set[str] = set()
    nested: dict[str, list[tuple[str, ...]]] = {}
    for p in paths:
        if not p:
            continue
        if len(p) == 1:
            drop_keys.add(p[0])
        else:
            nested.setdefault(p[0], []).append(p[1:])
    result: dict[str, Any] = {}
    for k, v in obj.items():
        if k in drop_keys:
            continue
        if k in nested and isinstance(v, dict):
            result[k] = _strip_paths(v, nested[k])
        else:
            result[k] = v
    return result


def _prepare(obj: Any) -> Any:
    """Recursively validate and normalize ``obj`` for canonical encoding."""
    # bool must be checked BEFORE int (bool is subclass of int) — both are fine
    if isinstance(obj, bool):
        return obj
    if obj is None or isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        raise TypeError(
            "floats are not permitted in canonical JSON; use Decimal or int"
        )
    # Reject Decimal explicitly (imported lazily to avoid hard dep on symbol)
    from decimal import Decimal

    if isinstance(obj, Decimal):
        raise TypeError(
            "Decimal is not permitted in canonical JSON (Phase 1); use int"
        )
    if isinstance(obj, str):
        return _nfc(obj)
    if isinstance(obj, (list, tuple)):
        return [_prepare(v) for v in obj]
    if isinstance(obj, dict):
        prepared: dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"canonical JSON requires string mapping keys, got {type(k).__name__}"
                )
            prepared[_nfc(k)] = _prepare(v)
        return prepared
    raise TypeError(
        f"canonical JSON does not support type {type(obj).__name__}"
    )


def canonical_json(
    obj: Any, *, exclude_paths: Sequence[tuple[str, ...]] = ()
) -> bytes:
    """Serialize ``obj`` to canonical UTF-8 JSON bytes.

    See module docstring for full invariants. Duplicate dict keys are
    impossible in Python dicts, so no explicit check is performed.
    """
    stripped = _strip_paths(obj, tuple(exclude_paths))
    prepared = _prepare(stripped)
    text = json.dumps(
        prepared,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8")


def digest(
    obj: Any, *, exclude_paths: Sequence[tuple[str, ...]] = ()
) -> str:
    """Return ``"<algo>:<hex>"`` content digest of ``obj``.

    The algorithm tag comes from :data:`SchemaVersions.DIGEST_ALGO`.
    """
    data = canonical_json(obj, exclude_paths=exclude_paths)
    hexdigest = hashlib.sha256(data).hexdigest()
    return f"{SchemaVersions.DIGEST_ALGO}:{hexdigest}"


class _NoDuplicateSafeLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate and non-string mapping keys."""


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False):
    if not isinstance(node, yaml.MappingNode):
        from architecture_model.core.errors import ParseError
        raise ParseError(
            f"expected a mapping node, but found {node.id}"
        )
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise TypeError(
                f"canonical YAML requires string mapping keys, got {type(key).__name__}"
            )
        if key in mapping:
            from architecture_model.core.errors import ParseError
            raise ParseError(f"duplicate key {key!r} in YAML mapping")
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


_NoDuplicateSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def canonical_yaml_load(text: str) -> Any:
    """Load YAML with strict mapping rules.

    * Rejects duplicate keys with :class:`ValueError`.
    * Rejects non-string mapping keys with :class:`TypeError`.
    """
    return yaml.load(text, Loader=_NoDuplicateSafeLoader)
