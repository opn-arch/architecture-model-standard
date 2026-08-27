"""Tests for gap_prompts — per-stage LLM re-inference prompt builders."""
from __future__ import annotations

import pytest


def test_infer_prompt_contains_module_list():
    from architecture_model.pipeline.gap_prompts import build_reinfer_prompt
    modules = [
        {"path": "src/main.py", "functions": ["load", "save"], "classes": []},
        {"path": "src/parser.py", "functions": ["parse"], "classes": ["Parser"]},
    ]
    prompt = build_reinfer_prompt("infer", modules=modules)
    assert "src/main.py" in prompt
    assert "src/parser.py" in prompt
    assert "capabilities" in prompt.lower()


def test_allocate_prompt_contains_capabilities():
    from architecture_model.pipeline.gap_prompts import build_reinfer_prompt
    modules = [{"path": "src/main.py", "functions": ["load"], "classes": []}]
    capabilities = [{"id": "CAP-1", "name": "Loading"}]
    prompt = build_reinfer_prompt("allocate", modules=modules, capabilities=capabilities)
    assert "CAP-1" in prompt
    assert "Loading" in prompt
    assert "component" in prompt.lower()


def test_relate_prompt_contains_components():
    from architecture_model.pipeline.gap_prompts import build_reinfer_prompt
    components = [{"id": "COMP-1", "name": "Loader", "files": ["src/main.py"]}]
    capabilities = [{"id": "CAP-1", "name": "Loading"}]
    imports = [{"source": "src/main.py", "target": "src/parser.py"}]
    prompt = build_reinfer_prompt("relate", components=components, capabilities=capabilities, imports=imports)
    assert "COMP-1" in prompt
    assert "realizes" in prompt.lower() or "relationship" in prompt.lower()


def test_specify_prompt_contains_components_and_routes():
    from architecture_model.pipeline.gap_prompts import build_reinfer_prompt
    components = [{"id": "COMP-1", "name": "Loader", "files": ["src/main.py"]}]
    prompt = build_reinfer_prompt("specify", components=components)
    assert "interface" in prompt.lower()


def test_contract_prompt_contains_test_files():
    from architecture_model.pipeline.gap_prompts import build_reinfer_prompt
    components = [{"id": "COMP-1", "name": "Loader", "files": ["src/main.py"]}]
    test_files = ["tests/test_main.py"]
    prompt = build_reinfer_prompt("contract", components=components, test_files=test_files)
    assert "test_main.py" in prompt


def test_validate_prompt_contains_model_summary():
    from architecture_model.pipeline.gap_prompts import build_reinfer_prompt
    model_summary = {"components": 4, "capabilities": 3, "relationships": 12}
    prompt = build_reinfer_prompt("validate", model_summary=model_summary)
    assert "4" in prompt


def test_unknown_stage_returns_generic():
    from architecture_model.pipeline.gap_prompts import build_reinfer_prompt
    prompt = build_reinfer_prompt("unknown_stage")
    assert prompt


def test_parse_reinfer_response_json():
    from architecture_model.pipeline.gap_prompts import parse_reinfer_response
    response = '```json\n{"capabilities": [{"name": "Loading", "files": ["main.py"]}]}\n```'
    parsed = parse_reinfer_response("infer", response)
    assert "capabilities" in parsed
    assert parsed["capabilities"][0]["name"] == "Loading"


def test_parse_reinfer_response_plain_json():
    from architecture_model.pipeline.gap_prompts import parse_reinfer_response
    response = '{"components": [{"name": "Loader"}]}'
    parsed = parse_reinfer_response("allocate", response)
    assert "components" in parsed


def test_parse_reinfer_response_bad_json():
    from architecture_model.pipeline.gap_prompts import parse_reinfer_response
    parsed = parse_reinfer_response("infer", "not json at all")
    assert parsed == {}
