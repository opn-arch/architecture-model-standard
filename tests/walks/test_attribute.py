"""Tests for the Attribute schema + provenance."""

from __future__ import annotations

from architecture_model.walks.attribute import (
    Attribute,
    AttributeCategory,
    AttributeSource,
    default_category,
)


def test_default_category_authoring() -> None:
    assert default_category("intent") == AttributeCategory.A
    assert default_category("rationale") == AttributeCategory.A


def test_default_category_specification() -> None:
    assert default_category("goals") == AttributeCategory.B
    assert default_category("requirements") == AttributeCategory.B


def test_default_category_promise() -> None:
    assert default_category("promises") == AttributeCategory.C
    assert default_category("slos") == AttributeCategory.C


def test_default_category_unknown_returns_none() -> None:
    assert default_category("unknown_attr") is None


def test_attribute_bare_value_roundtrip() -> None:
    a = Attribute.from_dict("hello")
    assert a.value == "hello"
    assert a.source == AttributeSource.USER
    assert a.confidence == 1.0
    assert a.verified_by == ()


def test_attribute_full_dict_roundtrip() -> None:
    raw = {
        "value": "commit contract",
        "source": "walk",
        "confidence": 0.7,
        "verified_by": ["tests/foo.py"],
        "category": "promise",
    }
    a = Attribute.from_dict(raw)
    assert a.value == "commit contract"
    assert a.source == AttributeSource.WALK
    assert a.confidence == 0.7
    assert a.verified_by == ("tests/foo.py",)
    assert a.category == AttributeCategory.C

    round = a.to_dict()
    assert round["source"] == "walk"
    assert round["confidence"] == 0.7
    assert round["verified_by"] == ["tests/foo.py"]
    assert round["category"] == "promise"


def test_attribute_is_empty() -> None:
    assert Attribute(value=None).is_empty() is True
    assert Attribute(value="").is_empty() is True
    assert Attribute(value=[]).is_empty() is True
    assert Attribute(value="x").is_empty() is False
    assert Attribute(value=[1]).is_empty() is False


def test_attribute_effective_category_inline_override() -> None:
    a = Attribute(value="x", category=AttributeCategory.C)
    assert a.effective_category("intent") == AttributeCategory.C


def test_attribute_effective_category_schema_default() -> None:
    a = Attribute(value="x")
    assert a.effective_category("intent") == AttributeCategory.A
    assert a.effective_category("goals") == AttributeCategory.B
