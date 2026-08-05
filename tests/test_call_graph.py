"""Tests for call graph infrastructure."""

import pytest
from architecture_model.manifest.types import (
    FunctionInfo, ModuleInfo, ModuleStatus, Manifest, MetricsResult,
)
from architecture_model.manifest.call_graph import (
    CallGraph, FlowTrace, build_call_graph, trace_flow, map_flow_to_components,
)


def _make_manifest(modules):
    return Manifest(
        generated_at="2024-01-01",
        project_root="/tmp",
        metrics=MetricsResult(values={}),
        functional_blocks={},
        modules=modules,
        interfaces=[],
    )


def _mod(file, name, functions, imports=None):
    return ModuleInfo(
        file=file, name=name, docstring=None,
        functions=functions, imports=imports or [],
        line_count=10, status=ModuleStatus.ACTIVE, classes=[],
    )


def _func(name, calls=None):
    return FunctionInfo(name=name, signature=f"def {name}()", calls=calls or [])


class TestBuildCallGraph:
    def test_simple_cross_module(self):
        """Module A imports B and calls a function from B."""
        mod_a = _mod("app/api.py", "app.api",
                      [_func("handle_request", calls=["process"])],
                      imports=["from app.service import process"])
        mod_b = _mod("app/service.py", "app.service",
                      [_func("process")])
        manifest = _make_manifest([mod_a, mod_b])
        graph = build_call_graph(manifest)

        key = "app/api.py:handle_request"
        assert "app/service.py:process" in graph.edges[key]

    def test_local_calls(self):
        """Function calls another in same module."""
        mod = _mod("app/utils.py", "app.utils",
                   [_func("main", calls=["helper"]), _func("helper")])
        manifest = _make_manifest([mod])
        graph = build_call_graph(manifest)

        assert "app/utils.py:helper" in graph.edges["app/utils.py:main"]

    def test_ambiguous(self):
        """Same function name in 2 modules, both included."""
        mod_a = _mod("app/a.py", "app.a",
                     [_func("run", calls=["do_work"])],
                     imports=["from app.b import do_work", "from app.c import do_work"])
        mod_b = _mod("app/b.py", "app.b", [_func("do_work")])
        mod_c = _mod("app/c.py", "app.c", [_func("do_work")])
        manifest = _make_manifest([mod_a, mod_b, mod_c])
        graph = build_call_graph(manifest)

        edges = graph.edges["app/a.py:run"]
        assert "app/b.py:do_work" in edges
        assert "app/c.py:do_work" in edges

    def test_unresolved_skipped(self):
        """Calls to stdlib/external are not in edges."""
        mod = _mod("app/main.py", "app.main",
                   [_func("start", calls=["print", "os.path.join"])],
                   imports=["import os"])
        manifest = _make_manifest([mod])
        graph = build_call_graph(manifest)

        assert graph.edges.get("app/main.py:start", []) == []


class TestTraceFlow:
    def test_linear(self):
        """A -> B -> C trace."""
        mod_a = _mod("a.py", "a", [_func("fa", calls=["fb"])], imports=["from b import fb"])
        mod_b = _mod("b.py", "b", [_func("fb", calls=["fc"])], imports=["from c import fc"])
        mod_c = _mod("c.py", "c", [_func("fc")])
        graph = build_call_graph(_make_manifest([mod_a, mod_b, mod_c]))

        flow = trace_flow(graph, "a.py:fa")
        assert flow.steps == [("a.py", "fa"), ("b.py", "fb"), ("c.py", "fc")]
        assert not flow.truncated

    def test_cycle(self):
        """A -> B -> A doesn't infinite loop."""
        mod_a = _mod("a.py", "a", [_func("fa", calls=["fb"])], imports=["from b import fb"])
        mod_b = _mod("b.py", "b", [_func("fb", calls=["fa"])], imports=["from a import fa"])
        graph = build_call_graph(_make_manifest([mod_a, mod_b]))

        flow = trace_flow(graph, "a.py:fa")
        assert flow.steps == [("a.py", "fa"), ("b.py", "fb")]
        assert not flow.truncated

    def test_max_depth(self):
        """Stops at depth limit."""
        # Chain: m0 -> m1 -> m2 -> m3 -> m4 -> m5
        modules = []
        for i in range(6):
            calls = [f"f{i+1}"] if i < 5 else []
            imports = [f"from m{i+1} import f{i+1}"] if i < 5 else []
            modules.append(_mod(f"m{i}.py", f"m{i}", [_func(f"f{i}", calls=calls)], imports=imports))
        graph = build_call_graph(_make_manifest(modules))

        flow = trace_flow(graph, "m0.py:f0", max_depth=3)
        assert flow.depth == 3
        assert flow.truncated
        assert len(flow.steps) == 4  # entry + 3 hops


class TestMapFlowToComponents:
    def test_boundary_crossings(self):
        """Only records when component changes."""
        flow = FlowTrace(
            entry="a.py:fa",
            steps=[("a.py", "fa"), ("a.py", "helper"), ("b.py", "fb"), ("c.py", "fc")],
            components_crossed=[],
            depth=3,
            truncated=False,
        )
        file_to_comp = {"a.py": "COMP-1", "b.py": "COMP-2", "c.py": "COMP-2"}
        result = map_flow_to_components(flow, file_to_comp)
        assert result.components_crossed == ["COMP-1", "COMP-2"]
