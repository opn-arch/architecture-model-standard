"""Tests for stage_tracer."""
from __future__ import annotations
import pytest
from dataclasses import dataclass, field


def test_trace_infer_domain_modules():
    from architecture_model.pipeline.stage_tracer import trace_infer, StageTrace
    
    @dataclass
    class FakePath:
        stem: str = "ansi"
        name: str = "ansi.py"
        parts: tuple = ("colorama", "ansi.py")
        parent: object = None
        def __str__(self): return f"colorama/{self.name}"
        def __post_init__(self):
            if self.parent is None:
                object.__setattr__(self, 'parent', type('P', (), {'stem': 'colorama', 'name': 'colorama'})())
    
    @dataclass
    class FakeFunc:
        name: str = "code_to_chars"
        is_async: bool = False
        decorators: list = field(default_factory=list)
        calls: list = field(default_factory=list)
    
    @dataclass
    class FakeClass:
        name: str = "AnsiCodes"
        bases: list = field(default_factory=list)
        methods: list = field(default_factory=list)
    
    @dataclass
    class FakeMod:
        path: object = None
        functions: list = field(default_factory=list)
        classes: list = field(default_factory=list)
        imports: list = field(default_factory=list)
        line_count: int = 100
        quality_score: float = 50.0
    
    @dataclass
    class FakeInv:
        modules: list = field(default_factory=list)
        routes: list = field(default_factory=list)
        test_files: list = field(default_factory=list)
    
    mod = FakeMod(
        path=FakePath(),
        functions=[FakeFunc(), FakeFunc(name="set_title"), FakeFunc(name="clear_screen")],
        classes=[FakeClass(), FakeClass(name="AnsiFore")],
    )
    inv = FakeInv(modules=[mod])
    
    infer_out = {"capabilities": [{"id": "CAP-1", "name": "Ansi", "source_files": []}], "actors": [], "behaviors": []}
    llm_data = {"capabilities": [{"name": "ANSI Code Generation", "source_file": "colorama/ansi.py"}]}
    
    trace = trace_infer(inv, infer_out, llm_data)
    assert isinstance(trace, StageTrace)
    assert len(trace.decisions) >= 3  # routes, triggers, domain_modules at minimum
    assert len(trace.entities) >= 1
    entity = trace.entities[0]
    assert entity.entity_name == "Ansi"
    assert entity.created_by == "_infer_from_domain_modules"
    assert entity.llm_alternative == "ANSI Code Generation"


def test_trace_infer_route_capability():
    from architecture_model.pipeline.stage_tracer import trace_infer
    
    infer_out = {"capabilities": [{"id": "CAP-1", "name": "Users Management", "source_files": []}], "actors": [], "behaviors": []}
    trace = trace_infer(None, infer_out, {})
    entity = trace.entities[0]
    assert entity.created_by == "_infer_from_routes"


def test_trace_infer_cli_capability():
    from architecture_model.pipeline.stage_tracer import trace_infer
    
    infer_out = {"capabilities": [{"id": "CAP-1", "name": "CLI Deploy", "source_files": []}], "actors": [], "behaviors": []}
    trace = trace_infer(None, infer_out, {})
    entity = trace.entities[0]
    assert entity.created_by == "_infer_from_cli"


def test_trace_infer_behaviors_gap():
    from architecture_model.pipeline.stage_tracer import trace_infer
    
    infer_out = {"capabilities": [], "actors": [], "behaviors": []}
    llm_data = {"behaviors": [{"name": "Init workflow", "type": "workflow"}, {"name": "Load config", "type": "use_case"}]}
    trace = trace_infer(None, infer_out, llm_data)
    # Should have a decision step about behaviors with gap assessment
    behavior_step = [d for d in trace.decisions if "behavior" in d.function_name.lower()]
    assert len(behavior_step) >= 1
    assert "0" in behavior_step[0].result  # pipeline found 0


def test_trace_allocate_seed_from_capabilities():
    from architecture_model.pipeline.stage_tracer import trace_allocate
    
    infer_data = {"capabilities": [{"id": "CAP-1", "name": "Ansi"}]}
    alloc_data = {"components": [{"id": "COMP-1", "name": "Ansi", "files": ["colorama/ansi.py"], "layer": "infra", "capability_id": "CAP-1"}]}
    llm_data = {"components": [{"name": "ANSI Codes", "files": ["colorama/ansi.py"], "layer": "core"}]}
    
    trace = trace_allocate(None, alloc_data, infer_data, llm_data)
    entity = trace.entities[0]
    assert entity.created_by == "_seed_from_capabilities"
    assert entity.llm_alternative == "ANSI Codes"


def test_trace_allocate_all_infra_warning():
    from architecture_model.pipeline.stage_tracer import trace_allocate
    
    alloc_data = {"components": [
        {"id": "COMP-1", "name": "A", "files": ["a.py"], "layer": "infra", "capability_id": "CAP-1"},
        {"id": "COMP-2", "name": "B", "files": ["b.py"], "layer": "infra", "capability_id": "CAP-2"},
    ]}
    trace = trace_allocate(None, alloc_data, {"capabilities": []}, {})
    # Should flag all-infra as warning
    layer_step = [d for d in trace.decisions if "layer" in d.function_name.lower() or "layer" in d.what_it_checks.lower()]
    assert len(layer_step) >= 1


def test_trace_specify_library_api():
    from architecture_model.pipeline.stage_tracer import trace_specify
    
    alloc_data = {"components": [{"id": "COMP-1", "name": "Ansi"}]}
    specify_data = {"interfaces": [{"name": "COMP-1 Library API", "component_id": "COMP-1", "type": None}]}
    llm_data = {"interfaces": [{"name": "ANSI Escape Sequence API", "component_id": "COMP-1"}]}
    
    trace = trace_specify(None, specify_data, alloc_data, llm_data)
    entity = trace.entities[0]
    assert entity.created_by == "library_api_fallback"
    assert entity.llm_alternative == "ANSI Escape Sequence API"


def test_trace_relate_classifies_relationships():
    from architecture_model.pipeline.stage_tracer import trace_relate
    
    relate_data = {"relationships": [
        {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
        {"from": "COMP-1", "to": "COMP-2", "type": "depends-on"},
        {"from": "LAYER-INFRA", "to": "COMP-1", "type": "contains"},
    ]}
    trace = trace_relate(None, relate_data, {}, {}, {})
    assert len(trace.entities) == 3
    types = {e.created_by for e in trace.entities}
    assert "realizes_derivation" in types
    assert "import_edge_analysis" in types
    assert "layer_grouping" in types


def test_trace_stage_dispatches():
    from architecture_model.pipeline.stage_tracer import trace_stage, StageTrace
    for stage in ["infer", "allocate", "relate", "specify", "contract", "validate"]:
        trace = trace_stage(stage, None, {}, {}, {})
        assert isinstance(trace, StageTrace)
        assert trace.stage == stage


def test_trace_stage_unknown():
    from architecture_model.pipeline.stage_tracer import trace_stage, StageTrace
    trace = trace_stage("unknown", None, {}, {}, {})
    assert trace.stage == "unknown"
    assert len(trace.decisions) == 0
