"""Tests for the content-addressed cache."""

from __future__ import annotations

from architecture_model.pipeline_v3.substrate import ContentCache


def test_cache_miss_returns_none() -> None:
    c = ContentCache()
    assert c.get("stage_a", [1, 2, 3]) is None


def test_cache_hit_returns_stored() -> None:
    c = ContentCache()
    c.put("stage_a", [1, 2, 3], "result")
    assert c.get("stage_a", [1, 2, 3]) == "result"


def test_cache_scoped_by_stage_name() -> None:
    c = ContentCache()
    c.put("stage_a", 42, "A")
    c.put("stage_b", 42, "B")
    assert c.get("stage_a", 42) == "A"
    assert c.get("stage_b", 42) == "B"


def test_cache_content_addressed_by_input_shape() -> None:
    c = ContentCache()
    c.put("s", {"k": "v"}, "one")
    # Same content, same hit
    assert c.get("s", {"k": "v"}) == "one"
    # Different content, miss
    assert c.get("s", {"k": "w"}) is None


def test_cache_len_reports_entry_count() -> None:
    c = ContentCache()
    assert len(c) == 0
    c.put("s", 1, "a")
    c.put("s", 2, "b")
    assert len(c) == 2


def test_cache_non_json_input_falls_back_to_repr() -> None:
    c = ContentCache()

    class Opaque:
        def __repr__(self) -> str:
            return "Opaque()"

    c.put("s", Opaque(), "hit")
    # Same repr → same digest → hit
    assert c.get("s", Opaque()) == "hit"
