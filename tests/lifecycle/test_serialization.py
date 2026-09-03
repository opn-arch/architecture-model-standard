"""Tests for architecture_model.lifecycle.serialization."""

from __future__ import annotations

import re
import subprocess
import sys
from decimal import Decimal

import pytest

from architecture_model.lifecycle.serialization import (
    canonical_json,
    canonical_yaml_load,
    digest,
)
from architecture_model.lifecycle.versions import SchemaVersions


def test_key_order_independence():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_nested_key_order_independence():
    a = {"outer": {"b": 1, "a": 2}, "z": {"y": 1, "x": 2}}
    b = {"z": {"x": 2, "y": 1}, "outer": {"a": 2, "b": 1}}
    assert canonical_json(a) == canonical_json(b)


def test_nfc_normalization():
    # decomposed 'e' + combining acute vs precomposed é
    decomposed_key = "e\u0301"
    composed_key = "\u00e9"
    assert canonical_json({decomposed_key: "x"}) == canonical_json({composed_key: "x"})
    assert canonical_json({"k": decomposed_key}) == canonical_json({"k": composed_key})


def test_float_rejected():
    with pytest.raises(TypeError, match="float"):
        canonical_json({"x": 1.5})


def test_decimal_rejected():
    with pytest.raises(TypeError):
        canonical_json({"x": Decimal("1.5")})


def test_bool_serialized_correctly():
    out = canonical_json({"x": True})
    assert b"true" in out
    assert b'"x":1' not in out


def test_tuple_serialized_as_array():
    assert canonical_json({"x": (1, 2, 3)}) == canonical_json({"x": [1, 2, 3]})


def test_none_serialized_as_null():
    assert b"null" in canonical_json({"x": None})


def test_non_string_key_rejected():
    with pytest.raises(TypeError):
        canonical_json({1: "a"})


def test_exclude_paths_shallow():
    a = {"generated_at": "t1", "x": 1}
    b = {"generated_at": "t2", "x": 1}
    assert canonical_json(a, exclude_paths=[("generated_at",)]) == canonical_json(
        b, exclude_paths=[("generated_at",)]
    )


def test_exclude_paths_nested():
    obj = {"meta": {"signatures": ["sig1"], "name": "foo"}, "x": 1}
    out = canonical_json(obj, exclude_paths=[("meta", "signatures")])
    assert b"signatures" not in out
    assert b"name" in out
    assert b"foo" in out


def test_exclude_paths_missing_ok():
    obj = {"a": 1}
    # excluding non-existent path is a no-op
    assert canonical_json(obj, exclude_paths=[("nope",)]) == canonical_json(obj)


def test_digest_format():
    d = digest({"a": 1})
    assert re.match(r"^sha256-v1:[0-9a-f]{64}$", d)


def test_digest_deterministic_cross_process():
    local = digest({"a": 1, "b": [1, 2, 3]})
    code = (
        "import sys; sys.path.insert(0, 'src');"
        "from architecture_model.lifecycle.serialization import digest;"
        "print(digest({'a': 1, 'b': [1, 2, 3]}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == local


def test_digest_stable_under_key_reorder():
    assert digest({"b": 1, "a": 2}) == digest({"a": 2, "b": 1})


def test_digest_excludes_volatile_fields():
    d1 = digest({"a": 1, "generated_at": "t1"}, exclude_paths=[("generated_at",)])
    d2 = digest({"a": 1, "generated_at": "t2"}, exclude_paths=[("generated_at",)])
    assert d1 == d2


def test_canonical_yaml_load_basic():
    assert canonical_yaml_load("a: 1\nb: 2\n") == {"a": 1, "b": 2}


def test_canonical_yaml_load_rejects_duplicate_key():
    with pytest.raises(ValueError, match="duplicate"):
        canonical_yaml_load("a: 1\na: 2\n")


def test_canonical_yaml_load_rejects_non_string_key():
    with pytest.raises(TypeError):
        canonical_yaml_load("1: a\n")


def test_digest_uses_schema_version_algo_tag():
    d = digest({"a": 1})
    assert d.startswith(SchemaVersions.DIGEST_ALGO + ":")
