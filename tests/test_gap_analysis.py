"""Tests for gap_analysis engine."""
from __future__ import annotations
import pytest
from dataclasses import dataclass, field


def test_extract_stage_data_infer():
    from architecture_model.pipeline.gap_analysis import extract_stage_data
    @dataclass
    class FakeCap:
        id: str = "CAP-1"
        name: str = "Main"
        module_sources: list = field(default_factory=list)
    @dataclass
    class FakeInfer:
        capabilities: list = field(default_factory=list)
        actors: list = field(default_factory=list)
        behaviors: list = field(default_factory=list)
    
    output = FakeInfer(capabilities=[FakeCap(module_sources=["main.py"])])
    data = extract_stage_data("infer", output)
    assert "capabilities" in data
    assert data["capabilities"][0]["name"] == "Main"
    assert data["capabilities"][0]["id"] == "CAP-1"


def test_extract_stage_data_allocate():
    from architecture_model.pipeline.gap_analysis import extract_stage_data
    @dataclass
    class FakeComp:
        id: str = "COMP-1"
        name: str = "Main"
        files: list = field(default_factory=lambda: ["main.py"])
        layer: str = "infra"
        capability_id: str = "CAP-1"
    @dataclass
    class FakeAlloc:
        components: list = field(default_factory=list)
    
    output = FakeAlloc(components=[FakeComp()])
    data = extract_stage_data("allocate", output)
    assert "components" in data
    assert data["components"][0]["layer"] == "infra"


def test_extract_stage_data_relate():
    from architecture_model.pipeline.gap_analysis import extract_stage_data
    @dataclass
    class FakeRel:
        from_id: str = "COMP-1"
        to_id: str = "CAP-1"
        type: str = "realizes"
    @dataclass
    class FakeRelResult:
        relationships: list = field(default_factory=list)
    
    output = FakeRelResult(relationships=[FakeRel()])
    data = extract_stage_data("relate", output)
    assert data["relationships"][0]["from"] == "COMP-1"
    assert data["relationships"][0]["type"] == "realizes"


def test_diff_stage_outputs_finds_renamed():
    from architecture_model.pipeline.gap_analysis import diff_stage_outputs
    det = {"capabilities": [{"name": "Main", "id": "CAP-1"}]}
    llm = {"capabilities": [{"name": "Environment Loading", "id": "CAP-1"}]}
    gap = diff_stage_outputs("infer", det, llm)
    assert len(gap.renamed) >= 1
    assert gap.renamed[0]["det"] == "Main"
    assert gap.renamed[0]["llm"] == "Environment Loading"


def test_diff_stage_outputs_finds_added():
    from architecture_model.pipeline.gap_analysis import diff_stage_outputs
    det = {"capabilities": [{"name": "Main", "id": "CAP-1"}]}
    llm = {"capabilities": [
        {"name": "Main", "id": "CAP-1"},
        {"name": "Parsing", "id": "CAP-2"},
    ]}
    gap = diff_stage_outputs("infer", det, llm)
    assert len(gap.added) >= 1


def test_diff_stage_outputs_finds_removed():
    from architecture_model.pipeline.gap_analysis import diff_stage_outputs
    det = {"capabilities": [
        {"name": "Main", "id": "CAP-1"},
        {"name": "Extra", "id": "CAP-2"},
    ]}
    llm = {"capabilities": [{"name": "Main", "id": "CAP-1"}]}
    gap = diff_stage_outputs("infer", det, llm)
    assert len(gap.removed) >= 1


def test_build_naming_chains():
    from architecture_model.pipeline.gap_analysis import build_naming_chains
    det_data = {
        "infer": {"capabilities": [{"name": "Main", "source_file": "main.py", "id": "CAP-1"}]},
        "allocate": {"components": [{"name": "Main", "capability_id": "CAP-1", "id": "COMP-1"}]},
        "specify": {"interfaces": [{"name": "Main Library API", "component_id": "COMP-1"}]},
    }
    llm_data = {
        "infer": {"capabilities": [{"name": "Environment Loading", "source_file": "main.py", "id": "CAP-1"}]},
        "allocate": {"components": [{"name": "DotenvLoader", "capability_id": "CAP-1", "id": "COMP-1"}]},
        "specify": {"interfaces": [{"name": "Environment Config API", "component_id": "COMP-1"}]},
    }
    chains = build_naming_chains(det_data, llm_data)
    assert len(chains) >= 1
    assert chains[0].source == "main.py"
    assert chains[0].is_generic


def test_trace_propagation():
    from architecture_model.pipeline.gap_analysis import trace_propagation
    det_data = {
        "infer": {"capabilities": [{"name": "Main", "id": "CAP-1", "source_file": "main.py"}]},
        "allocate": {"components": [{"name": "Main", "id": "COMP-1", "capability_id": "CAP-1"}]},
        "relate": {"relationships": [{"from": "COMP-1", "to": "CAP-1", "type": "realizes"}]},
        "specify": {"interfaces": [{"name": "Main Library API", "component_id": "COMP-1"}]},
    }
    traces = trace_propagation(det_data)
    assert len(traces) >= 1
    assert traces[0].origin_stage == "infer"
    assert len(traces[0].affected) >= 1


def test_generic_name_detection():
    from architecture_model.pipeline.gap_analysis import is_generic_name
    assert is_generic_name("Main")
    assert is_generic_name("Core")
    assert is_generic_name("Utils")
    assert is_generic_name("Helper")
    assert not is_generic_name("Environment Loading")
    assert not is_generic_name("Dotenv Parser")


def test_extract_stage_data_relate_has_type():
    """Relationship type must be extracted (not None)."""
    from architecture_model.pipeline.gap_analysis import extract_stage_data

    class FakeRel:
        from_id = "COMP-1"
        to_id = "CAP-1"
        rel_type = "realizes"

    class FakeOutput:
        relationships = [FakeRel()]

    data = extract_stage_data("relate", FakeOutput())
    assert data["relationships"][0]["type"] == "realizes"


def test_diff_matches_by_name_similarity():
    """Entities without IDs should match by name similarity."""
    from architecture_model.pipeline.gap_analysis import diff_stage_outputs

    det = {"capabilities": [
        {"id": "CAP-1", "name": "Ansitowin32"},
        {"id": "CAP-2", "name": "Ansi"},
    ]}
    llm = {"capabilities": [
        {"name": "ANSI-to-Win32 Conversion"},
        {"name": "ANSI Code Generation"},
    ]}
    gap = diff_stage_outputs("infer", det, llm)
    assert len(gap.renamed) == 2
    assert len(gap.added) == 0
    assert len(gap.removed) == 0


def test_diff_name_match_threshold():
    """Names below similarity threshold stay as added/removed."""
    from architecture_model.pipeline.gap_analysis import diff_stage_outputs

    det = {"capabilities": [{"id": "CAP-1", "name": "Parser"}]}
    llm = {"capabilities": [{"name": "Completely Unrelated Widget"}]}
    gap = diff_stage_outputs("infer", det, llm)
    assert len(gap.renamed) == 0
    assert len(gap.added) == 1
    assert len(gap.removed) == 1
