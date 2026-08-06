"""Tests for auto-enrichment from manifest."""

from types import SimpleNamespace

import pytest

from architecture_model.core.types import (
    Component,
    Constant,
    FunctionSignature,
    Status,
    Symbol,
    SymbolKind,
)
from architecture_model.manifest.types import ClassInfo, FunctionInfo, ModuleInfo, ModuleStatus
from architecture_model.orchestration.auto_enrich import (
    _classify_pattern,
    _parse_signature,
    create_behaviors_from_manifest,
    enrich_from_manifest,
)


def _make_module(
    file="src/foo.py",
    name="foo",
    docstring="Does amazing things. More details here.",
    functions=None,
    classes=None,
    module_constants=None,
) -> ModuleInfo:
    return ModuleInfo(
        file=file,
        name=name,
        docstring=docstring,
        functions=functions or [],
        imports=[],
        line_count=100,
        status=ModuleStatus.ACTIVE,
        classes=classes or [],
        module_constants=module_constants or {},
    )


def _make_manifest(modules: list[ModuleInfo], interfaces=None):
    """Create a minimal manifest-like object."""
    return SimpleNamespace(modules=modules, interfaces=interfaces or [])


def _make_component(files, **kwargs) -> Component:
    return Component(
        id="COMP-1",
        name="TestComp",
        status=Status.ACTIVE,
        files=files,
        **kwargs,
    )


def _make_model(components):
    return SimpleNamespace(entities={"components": components})


class TestSignatureExtraction:
    def test_basic_params_and_return(self):
        func = FunctionInfo(name="add", signature="(a: int, b: int) -> int")
        sig = _parse_signature("add", func)
        assert sig.name == "add"
        assert sig.params == ["a: int", "b: int"]
        assert sig.returns == "int"

    def test_no_return(self):
        func = FunctionInfo(name="run", signature="(x: str)")
        sig = _parse_signature("run", func)
        assert sig.params == ["x: str"]
        assert sig.returns == ""

    def test_no_params(self):
        func = FunctionInfo(name="get", signature="() -> bool")
        sig = _parse_signature("get", func)
        assert sig.params == []
        assert sig.returns == "bool"


class TestSymbolExtraction:
    def test_basic_class(self):
        mod = _make_module(classes=[ClassInfo(name="Foo", bases=["Bar"], methods=["run", "stop"])])
        comp = _make_component(files=["src/foo.py"])
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod]))
        assert len(comp.symbols) == 1
        assert comp.symbols[0].name == "Foo"
        assert comp.symbols[0].supers == ["Bar"]
        assert comp.symbols[0].members == ["run", "stop"]

    def test_dataclass_detection(self):
        mod = _make_module(classes=[ClassInfo(name="Config", bases=[], methods=[], decorators=["dataclass"])])
        comp = _make_component(files=["src/foo.py"])
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod]))
        assert comp.symbols[0].kind == SymbolKind.DATACLASS

    def test_exception_detection(self):
        mod = _make_module(classes=[ClassInfo(name="MyError", bases=["Exception"], methods=[])])
        comp = _make_component(files=["src/foo.py"])
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod]))
        assert comp.symbols[0].kind == SymbolKind.EXCEPTION


class TestConstantExtraction:
    def test_extracts_constants(self):
        mod = _make_module(module_constants={"MAX_RETRIES": "3", "TIMEOUT": "30"})
        comp = _make_component(files=["src/foo.py"])
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod]))
        assert len(comp.constants) == 2
        names = {c.name for c in comp.constants}
        assert "MAX_RETRIES" in names
        assert "TIMEOUT" in names


class TestContractInference:
    def test_first_sentence_from_docstring(self):
        mod = _make_module(docstring="Manages user sessions. Handles auth and tokens.")
        comp = _make_component(files=["src/foo.py"])
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod]))
        assert comp.contract == "Manages user sessions"


class TestPatternClassification:
    def test_matches_with_two_indicators(self):
        # "data-class" pattern has indicators: @dataclass, TypedDict, NamedTuple
        mod = _make_module(
            classes=[
                ClassInfo(name="MyData", bases=[], methods=[], decorators=["dataclass"]),
                ClassInfo(name="MyTypedDict", bases=["TypedDict"], methods=[]),
            ]
        )
        pattern = _classify_pattern([mod])
        assert pattern == "data-class"

    def test_no_match_with_one_indicator(self):
        mod = _make_module(classes=[ClassInfo(name="Foo", bases=[], methods=[], decorators=["dataclass"])])
        pattern = _classify_pattern([mod])
        assert pattern == ""


class TestNoOverwrite:
    def test_existing_signatures_not_overwritten(self):
        existing_sig = FunctionSignature(name="existing", params=["x: int"], returns="str")
        mod = _make_module(functions=[FunctionInfo(name="new_func", signature="(y: str) -> bool")])
        comp = _make_component(files=["src/foo.py"], signatures=[existing_sig])
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod]))
        assert len(comp.signatures) == 1
        assert comp.signatures[0].name == "existing"

    def test_existing_contract_not_overwritten(self):
        mod = _make_module(docstring="New contract here.")
        comp = _make_component(files=["src/foo.py"], contract="Original contract")
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod]))
        assert comp.contract == "Original contract"


class TestMultiFile:
    def test_merges_data_from_multiple_files(self):
        mod1 = _make_module(
            file="src/a.py",
            name="a",
            functions=[FunctionInfo(name="func_a", signature="(x: int) -> str")],
        )
        mod2 = _make_module(
            file="src/b.py",
            name="b",
            functions=[FunctionInfo(name="func_b", signature="(y: bool) -> int")],
        )
        comp = _make_component(files=["src/a.py", "src/b.py"])
        model = _make_model([comp])
        enrich_from_manifest(model, _make_manifest([mod1, mod2]))
        assert len(comp.signatures) == 2
        names = {s.name for s in comp.signatures}
        assert names == {"func_a", "func_b"}


class TestBehaviorFiltering:
    """Tests for behavior significance filtering and CRUD collapse."""

    def _make_behavior_model(self, comp_files):
        """Create model with a component mapping to given files."""
        comp = _make_component(files=comp_files)
        return _make_model([comp])

    def test_skips_trivial_service_functions(self):
        """Service functions with trivial accessor names and 0-1 calls should not become behaviors."""
        trivial_getter = FunctionInfo(name="get_value", signature="() -> str", calls=[])
        trivial_fetch = FunctionInfo(name="fetch_one", signature="() -> str", calls=["db.get"])
        significant = FunctionInfo(name="process_data", signature="() -> str", calls=["validate", "transform", "enrich", "store", "notify"])
        mod = _make_module(
            file="src/services/data_svc.py",
            name="data_svc",
            functions=[trivial_getter, trivial_fetch, significant],
        )
        model = self._make_behavior_model(["src/services/data_svc.py"])
        manifest = _make_manifest([mod])
        behaviors, rels = create_behaviors_from_manifest(model, manifest)
        names = [b.name for b in behaviors]
        assert "get_value" not in names
        assert "fetch_one" not in names
        assert "process_data" in names

    def test_keeps_all_router_functions(self):
        """Router functions are always kept (they're API endpoints)."""
        trivial = FunctionInfo(name="health_check", signature="() -> str", calls=[])
        mod = _make_module(
            file="src/routers/health.py",
            name="health",
            functions=[trivial],
        )
        model = self._make_behavior_model(["src/routers/health.py"])
        manifest = _make_manifest([mod])
        behaviors, rels = create_behaviors_from_manifest(model, manifest)
        names = [b.name for b in behaviors]
        assert "health_check" in names

    def test_crud_collapse(self):
        """CRUD functions for same resource are collapsed into single behavior."""
        funcs = [
            FunctionInfo(name="create_user", signature="(data) -> User", calls=["validate", "db.insert", "index", "notify", "log"]),
            FunctionInfo(name="get_user", signature="(id) -> User", calls=["db.get", "format", "cache", "validate", "log"]),
            FunctionInfo(name="update_user", signature="(id, data) -> User", calls=["validate", "db.update", "index", "notify", "log"]),
            FunctionInfo(name="delete_user", signature="(id) -> None", calls=["db.delete", "cleanup", "index", "notify", "log"]),
        ]
        mod = _make_module(
            file="src/services/user_svc.py",
            name="user_svc",
            functions=funcs,
        )
        model = self._make_behavior_model(["src/services/user_svc.py"])
        manifest = _make_manifest([mod])
        behaviors, rels = create_behaviors_from_manifest(model, manifest)
        names = [b.name for b in behaviors]
        # Should be collapsed into one "User CRUD" behavior
        assert len(behaviors) == 1
        assert behaviors[0].name == "User CRUD"
        # Steps should list the operations
        assert len(behaviors[0].steps) > 0
