"""Phase 10 — 2.1 parser deprecation warnings.

Verifies that ``load_model`` / ``_parse_raw`` (the schema-2.1 parser
path) emit a :class:`DeprecationWarning` pointing callers at the v3
pipeline. Behavior must remain unchanged — the warning is advisory,
not a hard break.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
import yaml

from architecture_model.core.parser import _parse_raw, load_model


V21_RAW = {
    "meta": {"schema_version": "2.1", "project": "t"},
    "entities": {"components": [{"id": "COMP-1", "name": "c"}]},
    "relationships": [],
}


def test_parse_raw_emits_deprecation_warning() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _parse_raw(V21_RAW)
    dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert dep, "expected DeprecationWarning from _parse_raw"
    assert "pipeline_v3" in str(dep[0].message).lower() or "v3" in str(dep[0].message).lower()


def test_load_model_emits_deprecation_warning(tmp_path: Path) -> None:
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(V21_RAW), encoding="utf-8")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        load_model(p)
    dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert dep, "expected DeprecationWarning from load_model"


def test_parse_raw_still_returns_model_despite_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = _parse_raw(V21_RAW)
    assert model.meta.schema_version == "2.1"
    assert len(model.entities.components) == 1
    assert model.entities.components[0].id == "COMP-1"
