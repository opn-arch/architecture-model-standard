"""Tests for LLM-driven capability hierarchy."""
from architecture_model.pipeline.gap_prompts import build_reinfer_prompt, _fmt_modules
from architecture_model.pipeline.llm_refine import normalize_llm_output, _flatten_capability_tree


def test_fmt_modules_includes_docstring():
    modules = [{"path": "parser.py", "functions": ["load"], "classes": ["Model"], "docstring": "Parse YAML models"}]
    result = _fmt_modules(modules)
    assert "Parse YAML models" in result


def test_fmt_modules_without_docstring():
    modules = [{"path": "util.py", "functions": ["f"], "classes": []}]
    result = _fmt_modules(modules)
    assert "util.py" in result
    assert "doc=" not in result


def test_infer_prompt_requests_hierarchy():
    prompt = build_reinfer_prompt("infer", modules=[{"path": "a.py", "functions": ["f"], "classes": []}])
    assert "hierarchical" in prompt.lower() or "hierarchy" in prompt.lower()


def test_infer_prompt_requests_descriptions():
    prompt = build_reinfer_prompt("infer", modules=[{"path": "a.py", "functions": ["f"], "classes": []}])
    assert "description" in prompt.lower()


def test_flatten_capability_tree_hierarchical():
    tree = [
        {
            "name": "Understand",
            "description": "Parse and analyze",
            "sub_capabilities": [
                {
                    "name": "Parse YAML",
                    "description": "Load YAML files",
                    "sub_capabilities": [
                        {"name": "Validate syntax", "description": "Check YAML syntax"},
                    ],
                },
            ],
        },
    ]
    flat = _flatten_capability_tree(tree)
    assert len(flat) == 3
    names = [c["name"] for c in flat]
    assert "Understand" in names
    assert "Parse YAML" in names
    assert "Validate syntax" in names


def test_flatten_capability_tree_flat_passthrough():
    """Flat capabilities (no sub_capabilities) should pass through unchanged."""
    tree = [
        {"name": "Cap1", "source_file": "a.py"},
        {"name": "Cap2", "source_file": "b.py"},
    ]
    result = _flatten_capability_tree(tree)
    assert result is tree  # identity — same list object


def test_normalize_infer_hierarchical():
    raw = {
        "capabilities": [
            {
                "name": "Root",
                "description": "The root",
                "sub_capabilities": [
                    {"name": "Child", "description": "A child", "sub_capabilities": []},
                ],
            },
        ],
        "behaviors": [{"name": "Workflow", "type": "use-case"}],
    }
    result = normalize_llm_output("infer", raw)
    caps = result["capabilities"]
    assert len(caps) == 2
    assert any(c["name"] == "Root" for c in caps)
    assert any(c["name"] == "Child" for c in caps)
    # Root should have sub_capability_ids
    root = next(c for c in caps if c["name"] == "Root")
    assert "sub_capability_ids" in root


def test_normalize_infer_flat_backward_compat():
    raw = {
        "capabilities": [
            {"name": "Cap1", "source_file": "a.py"},
            {"name": "Cap2", "source_file": "b.py"},
        ],
        "behaviors": [],
    }
    result = normalize_llm_output("infer", raw)
    caps = result["capabilities"]
    assert len(caps) == 2
    assert caps[0]["source_files"] == ["a.py"]


def test_normalize_infer_preserves_description():
    raw = {
        "capabilities": [
            {
                "name": "Grp",
                "description": "A group",
                "sub_capabilities": [
                    {"name": "Sub", "description": "A sub"},
                ],
            },
        ],
        "behaviors": [],
    }
    result = normalize_llm_output("infer", raw)
    for cap in result["capabilities"]:
        assert "description" in cap
