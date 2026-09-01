"""Tests for requirements derivation from source code patterns."""
from pathlib import Path

from architecture_model.pipeline.observe_types import (
    ClassRecord,
    ConstantRecord,
    FunctionRecord,
    Inventory,
    ModuleRecord,
)
from architecture_model.pipeline.specify import _derive_requirements
from architecture_model.pipeline.specify_types import DerivedRequirement


def _make_inventory(**kwargs) -> Inventory:
    return Inventory(**kwargs)


# --- Constants ---

class TestConstantRequirements:
    def test_timeout_constant(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/config.py"),
                constants=[ConstantRecord(name="TIMEOUT", value="30", type="int")],
            ),
        ])
        reqs = _derive_requirements(inv)
        const_reqs = [r for r in reqs if r.source_type == "constant"]
        assert len(const_reqs) == 1
        assert "timeout" in const_reqs[0].text.lower()
        assert "30" in const_reqs[0].text
        assert "src/config.py" in const_reqs[0].rationale
        assert const_reqs[0].moe.startswith("Verify TIMEOUT")

    def test_max_retries_constant(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/client.py"),
                constants=[ConstantRecord(name="MAX_RETRIES", value="3", type="int")],
            ),
        ])
        reqs = _derive_requirements(inv)
        const_reqs = [r for r in reqs if r.source_type == "constant"]
        assert len(const_reqs) == 1
        assert "MAX_RETRIES" in const_reqs[0].moe
        assert const_reqs[0].id.startswith("REQ-C")

    def test_batch_size_constant(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/loader.py"),
                constants=[ConstantRecord(name="BATCH_SIZE", value="100", type="int")],
            ),
        ])
        reqs = _derive_requirements(inv)
        const_reqs = [r for r in reqs if r.source_type == "constant"]
        assert len(const_reqs) == 1
        assert "batch size" in const_reqs[0].text.lower()

    def test_non_requirement_constant_ignored(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/app.py"),
                constants=[ConstantRecord(name="VERSION", value="1.0", type="str")],
            ),
        ])
        reqs = _derive_requirements(inv)
        const_reqs = [r for r in reqs if r.source_type == "constant"]
        assert len(const_reqs) == 0

    def test_multiple_constants(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/config.py"),
                constants=[
                    ConstantRecord(name="TIMEOUT", value="30", type="int"),
                    ConstantRecord(name="MAX_RETRIES", value="5", type="int"),
                    ConstantRecord(name="APP_NAME", value="myapp", type="str"),
                ],
            ),
        ])
        reqs = _derive_requirements(inv)
        const_reqs = [r for r in reqs if r.source_type == "constant"]
        assert len(const_reqs) == 2  # TIMEOUT and MAX_RETRIES, not APP_NAME


# --- Test function names ---

class TestTestRequirements:
    def test_basic_test_function(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("tests/test_auth.py"),
                functions=[FunctionRecord(name="test_validates_input", signature="()", body_hint="")],
            ),
        ])
        reqs = _derive_requirements(inv)
        test_reqs = [r for r in reqs if r.source_type == "test"]
        assert len(test_reqs) == 1
        assert "validates input" in test_reqs[0].text
        assert test_reqs[0].id.startswith("REQ-T")
        assert "test_validates_input passes" in test_reqs[0].moe

    def test_multiple_test_functions(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("tests/test_api.py"),
                functions=[
                    FunctionRecord(name="test_returns_404_for_missing", signature="()", body_hint=""),
                    FunctionRecord(name="test_handles_empty_input", signature="()", body_hint=""),
                    FunctionRecord(name="helper_setup", signature="()", body_hint=""),
                ],
            ),
        ])
        reqs = _derive_requirements(inv)
        test_reqs = [r for r in reqs if r.source_type == "test"]
        assert len(test_reqs) == 2  # helper_setup is not a test

    def test_non_test_file_ignored(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/utils.py"),
                functions=[FunctionRecord(name="test_connection", signature="()", body_hint="")],
            ),
        ])
        reqs = _derive_requirements(inv)
        test_reqs = [r for r in reqs if r.source_type == "test"]
        assert len(test_reqs) == 0


# --- Docstring constraints ---

class TestDocstringRequirements:
    def test_must_constraint(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/validator.py"),
                functions=[FunctionRecord(
                    name="validate",
                    signature="(data)",
                    body_hint="",
                    docstring="Must be called before save.",
                )],
            ),
        ])
        reqs = _derive_requirements(inv)
        doc_reqs = [r for r in reqs if r.source_type == "docstring"]
        assert len(doc_reqs) >= 1
        assert any("must be called before save" in r.text.lower() for r in doc_reqs)

    def test_should_not_constraint(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/cache.py"),
                functions=[FunctionRecord(
                    name="evict",
                    signature="(key)",
                    body_hint="",
                    docstring="Should not block the caller.",
                )],
            ),
        ])
        reqs = _derive_requirements(inv)
        doc_reqs = [r for r in reqs if r.source_type == "docstring"]
        assert len(doc_reqs) >= 1
        assert any("should not block" in r.text.lower() for r in doc_reqs)

    def test_at_most_constraint(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/pool.py"),
                functions=[FunctionRecord(
                    name="acquire",
                    signature="()",
                    body_hint="",
                    docstring="Waits at most 5 seconds for a connection.",
                )],
            ),
        ])
        reqs = _derive_requirements(inv)
        doc_reqs = [r for r in reqs if r.source_type == "docstring"]
        assert len(doc_reqs) >= 1
        assert any("at most 5 seconds" in r.text.lower() for r in doc_reqs)

    def test_requires_constraint(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/auth.py"),
                functions=[FunctionRecord(
                    name="login",
                    signature="(user, pw)",
                    body_hint="",
                    docstring="Requires a valid API key.",
                )],
            ),
        ])
        reqs = _derive_requirements(inv)
        doc_reqs = [r for r in reqs if r.source_type == "docstring"]
        assert len(doc_reqs) >= 1
        assert any("requires a valid api key" in r.text.lower() for r in doc_reqs)

    def test_no_constraint_in_docstring(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/utils.py"),
                functions=[FunctionRecord(
                    name="format",
                    signature="(s)",
                    body_hint="",
                    docstring="Formats a string for display.",
                )],
            ),
        ])
        reqs = _derive_requirements(inv)
        doc_reqs = [r for r in reqs if r.source_type == "docstring"]
        assert len(doc_reqs) == 0

    def test_class_method_docstring(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/service.py"),
                classes=[ClassRecord(
                    name="Service",
                    method_details=[FunctionRecord(
                        name="start",
                        signature="(self)",
                        body_hint="",
                        docstring="Must be initialized before use.",
                    )],
                )],
            ),
        ])
        reqs = _derive_requirements(inv)
        doc_reqs = [r for r in reqs if r.source_type == "docstring"]
        assert len(doc_reqs) >= 1
        assert any("Service.start" in r.name for r in doc_reqs)


# --- Integration ---

class TestMixedSources:
    def test_all_sources_combined(self):
        inv = _make_inventory(modules=[
            ModuleRecord(
                path=Path("src/config.py"),
                constants=[ConstantRecord(name="TIMEOUT", value="30", type="int")],
                functions=[FunctionRecord(
                    name="load",
                    signature="()",
                    body_hint="",
                    docstring="Must return a valid config dict.",
                )],
            ),
            ModuleRecord(
                path=Path("tests/test_config.py"),
                functions=[FunctionRecord(name="test_loads_defaults", signature="()", body_hint="")],
            ),
        ])
        reqs = _derive_requirements(inv)
        types = {r.source_type for r in reqs}
        assert "constant" in types
        assert "test" in types
        assert "docstring" in types
        # All reqs have required fields
        for r in reqs:
            assert r.id
            assert r.text
            assert r.rationale
            assert r.moe
            assert r.source_file
            assert r.source_type

    def test_empty_inventory(self):
        inv = _make_inventory()
        reqs = _derive_requirements(inv)
        assert reqs == []
