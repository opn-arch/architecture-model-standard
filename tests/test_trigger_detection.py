"""Tests for automatic behavior trigger detection."""
import pytest
from architecture_model.orchestration.trigger_detection import (
    detect_behavior_triggers, build_behavior_entry_map
)
from architecture_model.core.types import Behavior, Relationship
from architecture_model.manifest.call_graph import CallGraph


def _make_graph(edges):
    """Build CallGraph from edge dict."""
    graph = CallGraph()
    graph.edges = edges
    for qname in edges:
        file, fname = qname.split(":", 1)
        graph.locations[qname] = file
    for targets in edges.values():
        for t in targets:
            if ":" in t:
                file, fname = t.split(":", 1)
                graph.locations.setdefault(t, file)
                graph.edges.setdefault(t, [])
    return graph


class TestDetectBehaviorTriggers:
    def test_direct_call_creates_trigger(self):
        behaviors = [
            Behavior(id="BEH-1", name="Create log", status="ACTIVE", source_file="routers/logs.py"),
            Behavior(id="BEH-2", name="Parse text", status="ACTIVE", source_file="services/parser.py"),
        ]
        graph = _make_graph({
            "routers/logs.py:create_log": ["services/parser.py:parse_text"],
            "services/parser.py:parse_text": ["services/parser.py:tokenize"],
            "services/parser.py:tokenize": [],
        })
        entries = {"BEH-1": "routers/logs.py:create_log", "BEH-2": "services/parser.py:parse_text"}

        triggers = detect_behavior_triggers(behaviors, graph, entries)
        assert len(triggers) == 1
        assert triggers[0].type.value == "triggers"
        assert triggers[0].from_id == "BEH-1"
        assert triggers[0].to_id == "BEH-2"

    def test_no_cross_call_no_trigger(self):
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
            Behavior(id="BEH-2", name="B", status="ACTIVE", source_file="b.py"),
        ]
        graph = _make_graph({
            "a.py:func_a": ["a.py:helper_a"],
            "a.py:helper_a": [],
            "b.py:func_b": ["b.py:helper_b"],
            "b.py:helper_b": [],
        })
        entries = {"BEH-1": "a.py:func_a", "BEH-2": "b.py:func_b"}

        triggers = detect_behavior_triggers(behaviors, graph, entries)
        assert len(triggers) == 0

    def test_transitive_call_detected(self):
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
            Behavior(id="BEH-2", name="B", status="ACTIVE", source_file="b.py"),
        ]
        graph = _make_graph({
            "a.py:func_a": ["a.py:dispatch"],
            "a.py:dispatch": ["b.py:func_b"],
            "b.py:func_b": [],
        })
        entries = {"BEH-1": "a.py:func_a", "BEH-2": "b.py:func_b"}

        triggers = detect_behavior_triggers(behaviors, graph, entries)
        assert len(triggers) == 1
        assert triggers[0].from_id == "BEH-1"

    def test_no_self_trigger(self):
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
        ]
        graph = _make_graph({"a.py:func_a": ["a.py:func_a"]})
        entries = {"BEH-1": "a.py:func_a"}

        triggers = detect_behavior_triggers(behaviors, graph, entries)
        assert len(triggers) == 0

    def test_chain_detection(self):
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
            Behavior(id="BEH-2", name="B", status="ACTIVE", source_file="b.py"),
            Behavior(id="BEH-3", name="C", status="ACTIVE", source_file="c.py"),
        ]
        graph = _make_graph({
            "a.py:func_a": ["b.py:func_b"],
            "b.py:func_b": ["c.py:func_c"],
            "c.py:func_c": [],
        })
        entries = {"BEH-1": "a.py:func_a", "BEH-2": "b.py:func_b", "BEH-3": "c.py:func_c"}

        triggers = detect_behavior_triggers(behaviors, graph, entries)
        # A->B, A->C (transitive), B->C
        assert len(triggers) == 3

    def test_missing_entry_skipped(self):
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
        ]
        graph = _make_graph({"a.py:func_a": []})
        entries = {}  # No entries mapped

        triggers = detect_behavior_triggers(behaviors, graph, entries)
        assert len(triggers) == 0


class TestBuildBehaviorEntryMap:
    def test_exact_name_match(self):
        behaviors = [
            Behavior(id="BEH-1", name="create_log", status="ACTIVE", source_file="routers/logs.py"),
        ]
        graph = _make_graph({"routers/logs.py:create_log": []})
        entries = build_behavior_entry_map(behaviors, graph)
        assert entries["BEH-1"] == "routers/logs.py:create_log"

    def test_fuzzy_match(self):
        behaviors = [
            Behavior(id="BEH-1", name="entity relationships", status="ACTIVE", source_file="routers/graph.py"),
        ]
        graph = _make_graph({
            "routers/graph.py:get_entity_relationships": [],
            "routers/graph.py:unrelated": [],
        })
        entries = build_behavior_entry_map(behaviors, graph)
        assert entries.get("BEH-1") == "routers/graph.py:get_entity_relationships"

    def test_no_source_file_skipped(self):
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file=""),
        ]
        graph = _make_graph({})
        entries = build_behavior_entry_map(behaviors, graph)
        assert "BEH-1" not in entries
