# Auto-Enrichment Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete auto-enrichment pipeline that bridges manifest data → model entities, enabling 80%+ confidence scores without agent involvement for well-documented code.

**Architecture:** Five features implemented sequentially. Feature 1 (structural enrichment) is the core — it reads manifest data and populates Component fields. Feature 2 extends to behaviors. Features 3-5 validate the pipeline at scale.

**Tech Stack:** Python 3.12, pytest, architecture-model-standard APIs, opencode-arch CLI

**Test command:** `pytest tests/ -v --ignore=tests/test_config_loader.py` (in arch-std repo)

**Repo:** `/Users/baigm2/Documents/Projects/architecture-model-standard/`

---

## Task 1: Auto-Enrichment — Structural (Core Function)

**Files:**
- Create: `src/architecture_model/orchestration/auto_enrich.py`
- Test: `tests/test_auto_enrich.py`
- Modify: `src/architecture_model/orchestration/__init__.py`
- Modify: `src/architecture_model/__init__.py`

**Step 1: Write the failing tests**

```python
# tests/test_auto_enrich.py
"""Tests for auto-enrichment from manifest."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, Component, FunctionSignature, Symbol, Constant,
    SymbolKind, ComponentKind,
)
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, FunctionInfo, ClassInfo, MetricsResult,
    ScanReport, ModuleStatus,
)
from architecture_model.orchestration.auto_enrich import enrich_from_manifest


def _make_manifest(modules: list[ModuleInfo]) -> Manifest:
    return Manifest(
        generated_at="2026-01-01",
        project_root="/tmp/test",
        metrics=MetricsResult(values={}),
        functional_blocks={},
        modules=modules,
        interfaces=[],
        scan_report=ScanReport(
            files_attempted=len(modules),
            files_succeeded=len(modules),
            files_failed=0,
            parse_errors=[],
            functions_extracted=0,
            classes_extracted=0,
            constants_extracted=0,
            interfaces_derived=0,
            blocks_processed=0,
            unclaimed_files=0,
        ),
    )


def _make_model(components: list[Component]) -> ArchitectureModel:
    return ArchitectureModel(
        meta={"project": "test", "schema_version": "1.3"},
        entities={"components": components},
        relationships=[],
    )


class TestSignatureExtraction:
    def test_extracts_function_signatures(self):
        module = ModuleInfo(
            file="src/calculator.py",
            name="calculator",
            docstring="Calculator module.",
            functions=[
                FunctionInfo(name="add", signature="(a: int, b: int) -> int", calls=[], docstring="Add two numbers.", raises=[]),
                FunctionInfo(name="divide", signature="(a: float, b: float) -> float", calls=[], docstring=None, raises=["ZeroDivisionError"]),
            ],
            imports=[], line_count=50, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="Calculator", files=["src/calculator.py"])
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        assert len(comp.signatures) == 2
        assert comp.signatures[0].name == "add"
        assert comp.signatures[0].params == ["a: int", "b: int"]
        assert comp.signatures[0].returns == "int"

    def test_does_not_overwrite_existing_signatures(self):
        module = ModuleInfo(
            file="src/calc.py", name="calc", docstring=None,
            functions=[FunctionInfo(name="add", signature="(a, b) -> int", calls=[], docstring=None, raises=[])],
            imports=[], line_count=10, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        existing_sig = FunctionSignature(name="add", params=["a: int", "b: int"], returns="int")
        comp = Component(id="COMP-1", name="Calc", files=["src/calc.py"], signatures=[existing_sig])
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        # Should keep existing, not overwrite
        assert len(comp.signatures) == 1
        assert comp.signatures[0].params == ["a: int", "b: int"]


class TestSymbolExtraction:
    def test_extracts_classes_as_symbols(self):
        module = ModuleInfo(
            file="src/models.py", name="models", docstring=None,
            functions=[],
            imports=[], line_count=100, status=ModuleStatus.ACTIVE,
            classes=[
                ClassInfo(name="User", bases=["BaseModel"], methods=["validate", "save"], is_abstract=False, decorators=[], attributes={"name": "str", "email": "str"}),
                ClassInfo(name="Admin", bases=["User"], methods=["grant_access"], is_abstract=False, decorators=[], attributes={}),
            ],
            exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="Models", files=["src/models.py"])
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        assert len(comp.symbols) == 2
        assert comp.symbols[0].name == "User"
        assert comp.symbols[0].supers == ["BaseModel"]
        assert comp.symbols[0].members == ["validate", "save"]
        assert comp.symbols[0].kind == SymbolKind.CLASS


class TestConstantExtraction:
    def test_extracts_module_constants(self):
        module = ModuleInfo(
            file="src/config.py", name="config", docstring=None,
            functions=[], imports=[], line_count=20, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[],
            module_constants={"MAX_RETRIES": "3", "TIMEOUT": "30"},
            module_assignments={},
        )
        comp = Component(id="COMP-1", name="Config", files=["src/config.py"])
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        assert len(comp.constants) == 2
        names = {c.name for c in comp.constants}
        assert "MAX_RETRIES" in names
        assert "TIMEOUT" in names


class TestContractInference:
    def test_infers_contract_from_docstring(self):
        module = ModuleInfo(
            file="src/auth.py", name="auth",
            docstring="Authentication service that validates user credentials and issues tokens.",
            functions=[], imports=[], line_count=80, status=ModuleStatus.ACTIVE,
            classes=[
                ClassInfo(name="AuthService", bases=[], methods=["login", "logout"],
                         is_abstract=False, decorators=[], attributes={}),
            ],
            exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="AuthService", files=["src/auth.py"])
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        assert comp.contract == "Authentication service that validates user credentials and issues tokens."

    def test_does_not_overwrite_existing_contract(self):
        module = ModuleInfo(
            file="src/auth.py", name="auth",
            docstring="New docstring.",
            functions=[], imports=[], line_count=10, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="Auth", files=["src/auth.py"], contract="Existing contract.")
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        assert comp.contract == "Existing contract."


class TestPatternClassification:
    def test_classifies_pattern_from_indicators(self):
        module = ModuleInfo(
            file="src/repo.py", name="repo", docstring=None,
            functions=[
                FunctionInfo(name="get_by_id", signature="(id: str) -> Optional[Entity]", calls=[], docstring=None, raises=[]),
                FunctionInfo(name="save", signature="(entity: Entity) -> None", calls=[], docstring=None, raises=[]),
                FunctionInfo(name="delete", signature="(id: str) -> None", calls=[], docstring=None, raises=[]),
            ],
            imports=[], line_count=60, status=ModuleStatus.ACTIVE,
            classes=[ClassInfo(name="UserRepository", bases=[], methods=["get_by_id", "save", "delete", "list_all"],
                             is_abstract=False, decorators=[], attributes={})],
            exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="UserRepo", files=["src/repo.py"])
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        # Should detect repository pattern from CRUD method names
        assert comp.pattern != ""

    def test_does_not_overwrite_existing_pattern(self):
        module = ModuleInfo(
            file="src/svc.py", name="svc", docstring=None,
            functions=[FunctionInfo(name="handle", signature="(cmd) -> None", calls=[], docstring=None, raises=[])],
            imports=[], line_count=20, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="Svc", files=["src/svc.py"], pattern="custom-pattern")
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        assert comp.pattern == "custom-pattern"


class TestResponsibilities:
    def test_extracts_responsibilities_from_methods(self):
        module = ModuleInfo(
            file="src/user_service.py", name="user_service", docstring=None,
            functions=[], imports=[], line_count=100, status=ModuleStatus.ACTIVE,
            classes=[ClassInfo(name="UserService", bases=[], methods=["create_user", "update_user", "delete_user", "list_users"],
                             is_abstract=False, decorators=[], attributes={})],
            exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="UserService", files=["src/user_service.py"])
        model = _make_model([comp])
        manifest = _make_manifest([module])

        enrich_from_manifest(model, manifest)

        assert len(comp.responsibilities) > 0


class TestMultiFileComponent:
    def test_merges_data_from_multiple_files(self):
        mod1 = ModuleInfo(
            file="src/api/routes.py", name="routes", docstring="API routing.",
            functions=[FunctionInfo(name="get_users", signature="() -> list", calls=[], docstring=None, raises=[])],
            imports=[], line_count=30, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={"API_VERSION": "'v1'"}, module_assignments={},
        )
        mod2 = ModuleInfo(
            file="src/api/middleware.py", name="middleware", docstring=None,
            functions=[FunctionInfo(name="auth_middleware", signature="(request) -> Response", calls=[], docstring=None, raises=[])],
            imports=[], line_count=20, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        comp = Component(id="COMP-1", name="API", files=["src/api/routes.py", "src/api/middleware.py"])
        model = _make_model([comp])
        manifest = _make_manifest([mod1, mod2])

        enrich_from_manifest(model, manifest)

        assert len(comp.signatures) == 2
        assert len(comp.constants) == 1
        assert comp.contract == "API routing."
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auto_enrich.py -v --ignore=tests/test_config_loader.py`
Expected: ImportError (module doesn't exist yet)

**Step 3: Write the implementation**

```python
# src/architecture_model/orchestration/auto_enrich.py
"""Auto-enrichment: bridge manifest data → model entities without agent involvement."""
from __future__ import annotations

import re
from typing import Any

from ..core.types import (
    ArchitectureModel,
    Component,
    Constant,
    FunctionSignature,
    Symbol,
    SymbolKind,
)
from ..manifest.types import ClassInfo, FunctionInfo, Manifest, ModuleInfo
from ..monitoring import monitored
from ..patterns import load_patterns


def _parse_signature(func: FunctionInfo) -> FunctionSignature:
    """Parse a FunctionInfo.signature string into a FunctionSignature object."""
    sig = func.signature  # e.g. "(a: int, b: int) -> int"
    returns = ""
    params_str = sig

    # Extract return type
    if "->" in sig:
        parts = sig.rsplit("->", 1)
        params_str = parts[0].strip()
        returns = parts[1].strip()

    # Extract params (strip parens)
    params_str = params_str.strip()
    if params_str.startswith("("):
        params_str = params_str[1:]
    if params_str.endswith(")"):
        params_str = params_str[:-1]

    params = [p.strip() for p in params_str.split(",") if p.strip()] if params_str.strip() else []

    return FunctionSignature(
        name=func.name,
        params=params,
        returns=returns,
        decorators=[],
        body_hint="",
    )


def _class_to_symbol(cls: ClassInfo) -> Symbol:
    """Convert a ClassInfo to a Symbol."""
    # Determine kind from decorators/bases
    kind = SymbolKind.CLASS
    if "dataclass" in " ".join(cls.decorators):
        kind = SymbolKind.DATACLASS
    elif cls.is_abstract:
        kind = SymbolKind.PROTOCOL
    elif any("Enum" in b for b in cls.bases):
        kind = SymbolKind.ENUM

    return Symbol(
        name=cls.name,
        kind=kind,
        members=list(cls.methods),
        supers=list(cls.bases),
    )


def _extract_contract(modules: list[ModuleInfo]) -> str:
    """Extract first-sentence contract from module/class docstrings."""
    # Prefer class docstring if there's a primary class, else module docstring
    for mod in modules:
        if mod.docstring:
            # Take first sentence
            first = mod.docstring.split(". ")[0].split(".\n")[0]
            if not first.endswith("."):
                first += "."
            return first
    return ""


def _classify_pattern(modules: list[ModuleInfo]) -> str:
    """Score each pattern by indicator matches in code symbols."""
    patterns = load_patterns()

    # Collect all names from the modules
    all_names: list[str] = []
    for mod in modules:
        all_names.append(mod.name)
        for func in mod.functions:
            all_names.append(func.name)
        for cls in mod.classes:
            all_names.append(cls.name)
            all_names.extend(cls.methods)
            all_names.extend(cls.decorators)

    all_text = " ".join(all_names).lower()

    best_pattern = ""
    best_score = 0

    for pattern_name, pattern_data in patterns.items():
        indicators = pattern_data.get("indicators", [])
        score = 0
        for indicator in indicators:
            # Strip glob wildcards for matching
            clean = indicator.lower().replace("*", "").replace("class ", "").strip()
            if clean and clean in all_text:
                score += 1
        if score >= 2 and score > best_score:
            best_score = score
            best_pattern = pattern_name

    return best_pattern


def _extract_responsibilities(modules: list[ModuleInfo]) -> list[str]:
    """Extract responsibilities from class methods."""
    responsibilities: list[str] = []
    for mod in modules:
        for cls in mod.classes:
            for method in cls.methods:
                if not method.startswith("_"):
                    # Convert method_name to readable form
                    readable = method.replace("_", " ")
                    responsibilities.append(readable)
    return responsibilities[:10]  # Cap at 10


@monitored
def enrich_from_manifest(model: ArchitectureModel, manifest: Manifest) -> None:
    """Populate model components with data extractable from manifest. Mutates in-place.

    Never overwrites fields that are already populated (respects agent-provided data).
    """
    # Build file → module lookup
    file_to_module: dict[str, ModuleInfo] = {}
    for mod in manifest.modules:
        file_to_module[mod.file] = mod

    # Get components
    components = model.entities.get("components", [])

    for comp in components:
        if not isinstance(comp, Component):
            continue

        # Find matching modules
        matched_modules: list[ModuleInfo] = []
        for f in comp.files:
            if f in file_to_module:
                matched_modules.append(file_to_module[f])
            else:
                # Try partial match (file might be relative vs absolute)
                for key, mod in file_to_module.items():
                    if key.endswith(f) or f.endswith(key):
                        matched_modules.append(mod)
                        break

        if not matched_modules:
            continue

        # Signatures (don't overwrite)
        if not comp.signatures:
            sigs = []
            for mod in matched_modules:
                for func in mod.functions:
                    if func.signature:
                        sigs.append(_parse_signature(func))
            comp.signatures = sigs

        # Symbols (don't overwrite)
        if not comp.symbols:
            symbols = []
            for mod in matched_modules:
                for cls in mod.classes:
                    symbols.append(_class_to_symbol(cls))
            comp.symbols = symbols

        # Constants (don't overwrite)
        if not comp.constants:
            constants = []
            for mod in matched_modules:
                for name, value in mod.module_constants.items():
                    constants.append(Constant(name=name, value=value))
            comp.constants = constants

        # Contract (don't overwrite)
        if not comp.contract:
            contract = _extract_contract(matched_modules)
            if contract:
                comp.contract = contract

        # Pattern (don't overwrite)
        if not comp.pattern:
            pattern = _classify_pattern(matched_modules)
            if pattern:
                comp.pattern = pattern

        # Responsibilities (don't overwrite)
        if not comp.responsibilities:
            resps = _extract_responsibilities(matched_modules)
            if resps:
                comp.responsibilities = resps
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_auto_enrich.py -v --ignore=tests/test_config_loader.py`
Expected: All pass

**Step 5: Export from orchestration and top-level**

Add to `src/architecture_model/orchestration/__init__.py`:
```python
from .auto_enrich import enrich_from_manifest
```

Add to `__all__` in both orchestration/__init__.py and the top-level __init__.py.

**Step 6: Commit**

```bash
git add src/architecture_model/orchestration/auto_enrich.py tests/test_auto_enrich.py
git add src/architecture_model/orchestration/__init__.py src/architecture_model/__init__.py
git commit -m "feat: auto-enrichment from manifest (structural Layer A)"
```

---

## Task 2: Behavioral Auto-Enrichment (Layer C)

**Files:**
- Modify: `src/architecture_model/orchestration/auto_enrich.py`
- Test: `tests/test_auto_enrich_behaviors.py`

**Step 1: Write the failing tests**

```python
# tests/test_auto_enrich_behaviors.py
"""Tests for behavioral auto-enrichment from manifest."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, Component, Behavior, BehaviorStep,
)
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, FunctionInfo, ClassInfo, MetricsResult,
    ScanReport, ModuleStatus, DecoratedFunction,
)
from architecture_model.orchestration.auto_enrich import enrich_behaviors_from_manifest


def _make_manifest(modules):
    return Manifest(
        generated_at="2026-01-01", project_root="/tmp/test",
        metrics=MetricsResult(values={}), functional_blocks={},
        modules=modules, interfaces=[],
        scan_report=ScanReport(
            files_attempted=len(modules), files_succeeded=len(modules),
            files_failed=0, parse_errors=[], functions_extracted=0,
            classes_extracted=0, constants_extracted=0,
            interfaces_derived=0, blocks_processed=0, unclaimed_files=0,
        ),
    )


def _make_model(components=None, behaviors=None):
    entities = {}
    if components:
        entities["components"] = components
    if behaviors:
        entities["behaviors"] = behaviors
    return ArchitectureModel(
        meta={"project": "test", "schema_version": "1.3"},
        entities=entities, relationships=[],
    )


class TestTriggerExtraction:
    def test_extracts_trigger_from_decorators(self):
        module = ModuleInfo(
            file="src/handlers.py", name="handlers", docstring=None,
            functions=[
                FunctionInfo(name="handle_login", signature="(request) -> Response", calls=["validate", "create_session"], docstring=None, raises=[]),
            ],
            imports=[], line_count=50, status=ModuleStatus.ACTIVE,
            classes=[], exports=[],
            decorated_functions=[
                DecoratedFunction(name="handle_login", decorators=["app.route('/login', methods=['POST'])"], is_method=False, class_name=None),
            ],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        behavior = Behavior(id="BHV-1", name="Login Flow", source_files=["src/handlers.py"])
        model = _make_model(behaviors=[behavior])
        manifest = _make_manifest([module])

        enrich_behaviors_from_manifest(model, manifest)

        assert behavior.trigger != ""

    def test_does_not_overwrite_existing_trigger(self):
        module = ModuleInfo(
            file="src/h.py", name="h", docstring=None, functions=[],
            imports=[], line_count=10, status=ModuleStatus.ACTIVE,
            classes=[], exports=[],
            decorated_functions=[DecoratedFunction(name="x", decorators=["on_event('start')"], is_method=False, class_name=None)],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        behavior = Behavior(id="BHV-1", name="Startup", source_files=["src/h.py"], trigger="Manual trigger")
        model = _make_model(behaviors=[behavior])
        manifest = _make_manifest([module])

        enrich_behaviors_from_manifest(model, manifest)

        assert behavior.trigger == "Manual trigger"


class TestStepsExtraction:
    def test_extracts_steps_from_call_graph(self):
        module = ModuleInfo(
            file="src/pipeline.py", name="pipeline", docstring=None,
            functions=[
                FunctionInfo(name="run_pipeline", signature="(data) -> Result", calls=["validate_input", "transform", "persist", "notify"], docstring="Run the full pipeline.", raises=[]),
                FunctionInfo(name="validate_input", signature="(data) -> bool", calls=[], docstring=None, raises=["ValidationError"]),
                FunctionInfo(name="transform", signature="(data) -> Data", calls=[], docstring=None, raises=[]),
                FunctionInfo(name="persist", signature="(data) -> None", calls=[], docstring=None, raises=["IOError"]),
                FunctionInfo(name="notify", signature="() -> None", calls=[], docstring=None, raises=[]),
            ],
            imports=[], line_count=100, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        behavior = Behavior(id="BHV-1", name="Data Pipeline", source_files=["src/pipeline.py"], entry_point="run_pipeline")
        model = _make_model(behaviors=[behavior])
        manifest = _make_manifest([module])

        enrich_behaviors_from_manifest(model, manifest)

        assert len(behavior.steps) >= 3


class TestPrePostConditions:
    def test_extracts_raises_as_error_conditions(self):
        module = ModuleInfo(
            file="src/service.py", name="service", docstring=None,
            functions=[
                FunctionInfo(name="process", signature="(item) -> None", calls=["validate"], docstring=None, raises=["ValueError", "TimeoutError"]),
            ],
            imports=[], line_count=30, status=ModuleStatus.ACTIVE,
            classes=[], exports=[], decorated_functions=[],
            imports_detailed=[], module_constants={}, module_assignments={},
        )
        behavior = Behavior(id="BHV-1", name="Processing", source_files=["src/service.py"], entry_point="process")
        model = _make_model(behaviors=[behavior])
        manifest = _make_manifest([module])

        enrich_behaviors_from_manifest(model, manifest)

        # Should have error/post conditions from raises
        assert len(behavior.post_conditions) > 0 or len(behavior.error_conditions) > 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auto_enrich_behaviors.py -v --ignore=tests/test_config_loader.py`
Expected: ImportError

**Step 3: Implement**

Add to `src/architecture_model/orchestration/auto_enrich.py`:

```python
@monitored
def enrich_behaviors_from_manifest(model: ArchitectureModel, manifest: Manifest) -> None:
    """Populate behavior entities with data extractable from manifest control flow.

    Extracts: triggers (from decorators), steps (from call graphs),
    pre/post conditions (from raises/assertions).
    """
    file_to_module: dict[str, ModuleInfo] = {}
    for mod in manifest.modules:
        file_to_module[mod.file] = mod

    behaviors = model.entities.get("behaviors", [])

    for bhv in behaviors:
        if not isinstance(bhv, Behavior):
            continue

        source_files = getattr(bhv, "source_files", [])
        matched_modules: list[ModuleInfo] = []
        for f in source_files:
            if f in file_to_module:
                matched_modules.append(file_to_module[f])
            else:
                for key, mod in file_to_module.items():
                    if key.endswith(f) or f.endswith(key):
                        matched_modules.append(mod)
                        break

        if not matched_modules:
            continue

        # Trigger from decorators
        if not getattr(bhv, "trigger", ""):
            trigger = _extract_trigger(matched_modules)
            if trigger:
                bhv.trigger = trigger

        # Steps from call graph
        if not getattr(bhv, "steps", []):
            entry = getattr(bhv, "entry_point", "")
            steps = _extract_steps(matched_modules, entry)
            if steps:
                bhv.steps = steps

        # Post/error conditions from raises
        if not getattr(bhv, "post_conditions", []):
            conditions = _extract_conditions(matched_modules, getattr(bhv, "entry_point", ""))
            if conditions:
                bhv.post_conditions = conditions


def _extract_trigger(modules: list[ModuleInfo]) -> str:
    """Extract trigger from decorated functions."""
    for mod in modules:
        for dec_func in mod.decorated_functions:
            for dec in dec_func.decorators:
                # Route decorators, event handlers, signals
                if any(kw in dec.lower() for kw in ["route", "on_event", "signal", "handler", "listen", "subscribe"]):
                    return dec
    return ""


def _extract_steps(modules: list[ModuleInfo], entry_point: str) -> list:
    """Extract ordered steps from the call graph of the entry point function."""
    from ..core.types import BehaviorStep

    # Find the entry point function
    for mod in modules:
        for func in mod.functions:
            if func.name == entry_point and func.calls:
                steps = []
                for i, call in enumerate(func.calls, 1):
                    steps.append(BehaviorStep(
                        order=i,
                        action=call.replace("_", " "),
                        component_ref="",
                    ))
                return steps

    # If no entry point specified, look for the function with most calls
    best_func = None
    best_calls = 0
    for mod in modules:
        for func in mod.functions:
            if len(func.calls) > best_calls:
                best_calls = len(func.calls)
                best_func = func

    if best_func and best_calls >= 2:
        steps = []
        for i, call in enumerate(best_func.calls, 1):
            steps.append(BehaviorStep(
                order=i,
                action=call.replace("_", " "),
                component_ref="",
            ))
        return steps

    return []


def _extract_conditions(modules: list[ModuleInfo], entry_point: str) -> list[str]:
    """Extract error/post conditions from raises in the entry function or all functions."""
    conditions: list[str] = []
    for mod in modules:
        for func in mod.functions:
            if entry_point and func.name != entry_point:
                continue
            for exc in func.raises:
                conditions.append(f"May raise {exc}")
    if not conditions and not entry_point:
        # Gather from all functions
        for mod in modules:
            for func in mod.functions:
                for exc in func.raises:
                    conditions.append(f"May raise {exc}")
    return list(set(conditions))
```

**Step 4: Run tests**

Run: `pytest tests/test_auto_enrich_behaviors.py -v --ignore=tests/test_config_loader.py`
Expected: All pass

**Step 5: Commit**

```bash
git add tests/test_auto_enrich_behaviors.py src/architecture_model/orchestration/auto_enrich.py
git commit -m "feat: behavioral auto-enrichment from manifest (Layer C)"
```

---

## Task 3: Integration — Wire into Pipeline + Test on Hard Repo

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py`
- Test: `tests/test_auto_enrich_integration.py`

**Step 1: Write integration test**

```python
# tests/test_auto_enrich_integration.py
"""Integration test: enrich_from_manifest on a real-ish model."""
import pytest
from pathlib import Path
from architecture_model.core.types import ArchitectureModel, Component
from architecture_model.manifest.generator import generate_manifest
from architecture_model.orchestration.auto_enrich import enrich_from_manifest
from architecture_model.core.confidence import compute_component_confidence


@pytest.fixture
def hard_repo(tmp_path):
    """Create a small but representative multi-file repo."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "scheduler.py").write_text('''
"""Task scheduler that manages job execution across worker nodes."""

MAX_WORKERS = 8
DEFAULT_TIMEOUT = 30

class TaskScheduler:
    """Coordinates task distribution to available workers."""

    def __init__(self, workers: list):
        self.workers = workers

    def schedule(self, task: "Task") -> str:
        """Schedule a task for execution. Returns task ID."""
        ...

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        ...

    def get_status(self, task_id: str) -> str:
        """Get current task status."""
        ...

def create_scheduler(config: dict) -> TaskScheduler:
    """Factory function for scheduler creation."""
    ...
''')

    (src / "worker.py").write_text('''
"""Worker node that executes assigned tasks."""

class Worker:
    """Executes tasks in isolation with resource limits."""

    def __init__(self, worker_id: str, capacity: int = 4):
        self.worker_id = worker_id
        self.capacity = capacity

    def execute(self, task: "Task") -> "Result":
        """Execute a single task and return result."""
        ...

    def heartbeat(self) -> dict:
        """Report worker health status."""
        ...
''')
    return tmp_path


def test_enrichment_boosts_confidence(hard_repo):
    """Auto-enrichment should significantly boost confidence for documented code."""
    manifest = generate_manifest(str(hard_repo))

    comp = Component(
        id="COMP-1",
        name="TaskScheduler",
        files=["src/scheduler.py"],
    )
    model = ArchitectureModel(
        meta={"project": "test", "schema_version": "1.3"},
        entities={"components": [comp]},
        relationships=[],
    )

    # Before enrichment
    before = compute_component_confidence(comp)
    assert before <= 0.10  # Only has files

    # Enrich
    enrich_from_manifest(model, manifest)

    # After enrichment
    after = compute_component_confidence(comp)
    assert after >= 0.60  # Should have signatures, symbols, constants, contract
    assert comp.signatures  # Should have schedule, cancel, get_status, create_scheduler
    assert comp.symbols  # Should have TaskScheduler
    assert comp.contract  # From docstring
```

**Step 2: Run to verify fails, implement, verify passes**

Run: `pytest tests/test_auto_enrich_integration.py -v --ignore=tests/test_config_loader.py`

**Step 3: Wire into pipeline.py**

In `run_pipeline()`, after decomposition and before confidence computation, call:
```python
from .auto_enrich import enrich_from_manifest
# After manifest is generated and model exists:
enrich_from_manifest(model, manifest)
```

**Step 4: Commit**

```bash
git add tests/test_auto_enrich_integration.py src/architecture_model/orchestration/pipeline.py
git commit -m "feat: wire auto-enrichment into pipeline + integration test"
```

---

## Task 4: Real Repo Benchmark Script

**Files:**
- Create: `scripts/bench_enrichment.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Benchmark auto-enrichment on any repository.

Usage: python scripts/bench_enrichment.py /path/to/repo
"""
import sys
import json
from pathlib import Path

from architecture_model.manifest.generator import generate_manifest
from architecture_model.core.parser import load_model
from architecture_model.core.confidence import compute_component_confidence, model_confidence_summary
from architecture_model.orchestration.auto_enrich import enrich_from_manifest


def main():
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    model_path = Path(repo_path) / ".architecture-model.yaml"

    if not model_path.exists():
        print(f"No .architecture-model.yaml found in {repo_path}")
        sys.exit(1)

    print(f"Scanning {repo_path}...")
    manifest = generate_manifest(repo_path)
    print(f"  Found {len(manifest.modules)} modules")

    model = load_model(str(model_path))

    # Before
    before = model_confidence_summary(model)
    print(f"\nBefore enrichment:")
    print(f"  Overall: {before['overall']:.0%}")
    for block in before.get("blocks", []):
        print(f"  {block['name']}: {block['confidence']:.0%}")

    # Enrich
    enrich_from_manifest(model, manifest)

    # After
    after = model_confidence_summary(model)
    print(f"\nAfter enrichment:")
    print(f"  Overall: {after['overall']:.0%}")
    for block in after.get("blocks", []):
        print(f"  {block['name']}: {block['confidence']:.0%}")

    delta = after["overall"] - before["overall"]
    print(f"\n  Δ confidence: +{delta:.0%}")


if __name__ == "__main__":
    main()
```

**Step 2: Test on /tmp/test-hard/ (if it exists)**

Run: `python scripts/bench_enrichment.py /tmp/test-hard/`

**Step 3: Commit**

```bash
git add scripts/bench_enrichment.py
git commit -m "feat: add enrichment benchmark script"
```

---

## Task 5: Regeneration Proof (opencode-arch)

**Repo:** `/Users/baigm2/Documents/Projects/opencode-arch/`

**Files:**
- Modify: `src/opencode_arch/cli/calibrate.py`
- Test: `tests/test_regeneration_proof.py`

**Step 1: Write the failing test**

```python
# tests/test_regeneration_proof.py
"""Tests for regeneration proof functionality."""
import pytest
from unittest.mock import AsyncMock, patch
from opencode_arch.cli.calibrate import (
    format_regeneration_prompt,
    compare_regeneration,
)


def test_format_regeneration_prompt_includes_model_context():
    """Prompt should include all enriched fields for a component."""
    component_context = {
        "id": "COMP-1",
        "name": "TaskScheduler",
        "contract": "Coordinates task distribution to available workers.",
        "pattern": "service-layer",
        "signatures": [{"name": "schedule", "params": ["task: Task"], "returns": "str"}],
        "symbols": [{"name": "TaskScheduler", "kind": "CLASS", "members": ["schedule", "cancel"]}],
        "constants": [{"name": "MAX_WORKERS", "value": "8"}],
        "responsibilities": ["schedule tasks", "cancel tasks", "get status"],
    }

    prompt = format_regeneration_prompt(component_context)

    assert "TaskScheduler" in prompt
    assert "schedule" in prompt
    assert "MAX_WORKERS" in prompt
    assert "service-layer" in prompt
    assert "DO NOT" in prompt or "without" in prompt.lower()  # Should say don't read source


def test_compare_regeneration_measures_api_compatibility():
    """Comparison should check function signature compatibility."""
    original = '''
class TaskScheduler:
    def schedule(self, task: "Task") -> str: ...
    def cancel(self, task_id: str) -> bool: ...
'''
    generated = '''
class TaskScheduler:
    def schedule(self, task: "Task") -> str: ...
    def cancel(self, task_id: str) -> bool: ...
    def status(self, task_id: str) -> str: ...
'''
    result = compare_regeneration(original, generated)
    assert result["api_coverage"] >= 0.8  # All original APIs present in generated
    assert "missing_apis" in result


def test_compare_regeneration_detects_missing_apis():
    original = '''
class Foo:
    def bar(self) -> int: ...
    def baz(self, x: str) -> None: ...
'''
    generated = '''
class Foo:
    def bar(self) -> int: ...
'''
    result = compare_regeneration(original, generated)
    assert result["api_coverage"] < 1.0
    assert "baz" in result["missing_apis"]
```

**Step 2: Implement in calibrate.py**

Add `format_regeneration_prompt` and `compare_regeneration` functions.

```python
def format_regeneration_prompt(component_context: dict) -> str:
    """Format a prompt asking agent to regenerate a component from model data only."""
    lines = [
        "# Regeneration Task",
        "",
        f"Regenerate the implementation for component **{component_context['name']}**",
        "using ONLY the information below. Do NOT read the source files.",
        "",
        f"## Contract",
        f"{component_context.get('contract', 'N/A')}",
        "",
        f"## Pattern: {component_context.get('pattern', 'N/A')}",
        "",
        "## Signatures",
    ]
    for sig in component_context.get("signatures", []):
        params = ", ".join(sig.get("params", []))
        ret = sig.get("returns", "")
        lines.append(f"- {sig['name']}({params}) -> {ret}")

    lines.append("")
    lines.append("## Symbols")
    for sym in component_context.get("symbols", []):
        lines.append(f"- {sym['kind']} {sym['name']}: members={sym.get('members', [])}")

    lines.append("")
    lines.append("## Constants")
    for const in component_context.get("constants", []):
        lines.append(f"- {const['name']} = {const['value']}")

    lines.append("")
    lines.append("## Responsibilities")
    for r in component_context.get("responsibilities", []):
        lines.append(f"- {r}")

    lines.append("")
    lines.append("Generate a complete Python module implementing this component.")
    return "\n".join(lines)


def compare_regeneration(original: str, generated: str) -> dict:
    """Compare original source to regenerated code for API compatibility."""
    import ast

    def _extract_apis(source: str) -> set[str]:
        """Extract function/method names from source."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return set()
        apis = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    apis.add(node.name)
        return apis

    original_apis = _extract_apis(original)
    generated_apis = _extract_apis(generated)

    if not original_apis:
        return {"api_coverage": 1.0, "missing_apis": [], "extra_apis": []}

    covered = original_apis & generated_apis
    missing = original_apis - generated_apis
    extra = generated_apis - original_apis

    return {
        "api_coverage": len(covered) / len(original_apis) if original_apis else 1.0,
        "missing_apis": sorted(missing),
        "extra_apis": sorted(extra),
    }
```

**Step 3: Run tests**

Run: `pytest tests/test_regeneration_proof.py -v`

**Step 4: Commit**

```bash
git add src/opencode_arch/cli/calibrate.py tests/test_regeneration_proof.py
git commit -m "feat: regeneration proof - format prompt + compare APIs"
```

---

## Task 6: Calibration Suite (opencode-arch)

**Repo:** `/Users/baigm2/Documents/Projects/opencode-arch/`

**Files:**
- Modify: `src/opencode_arch/cli/calibrate.py`
- Test: `tests/test_calibration_suite.py`

**Step 1: Write the failing test**

```python
# tests/test_calibration_suite.py
"""Tests for calibration suite."""
import pytest
from opencode_arch.cli.calibrate import (
    select_calibration_targets,
    CalibrationReport,
    compute_correlation,
)


def test_select_calibration_targets_picks_diverse_confidence():
    """Should select components across confidence bands."""
    components = [
        {"id": "C1", "confidence": 0.10},
        {"id": "C2", "confidence": 0.25},
        {"id": "C3", "confidence": 0.45},
        {"id": "C4", "confidence": 0.55},
        {"id": "C5", "confidence": 0.70},
        {"id": "C6", "confidence": 0.85},
        {"id": "C7", "confidence": 0.95},
    ]
    targets = select_calibration_targets(components, count=4)
    assert len(targets) == 4
    # Should span low to high
    confidences = [t["confidence"] for t in targets]
    assert min(confidences) < 0.3
    assert max(confidences) > 0.7


def test_compute_correlation():
    """Correlation between confidence and regen quality."""
    # Perfect positive correlation
    data = [
        {"confidence": 0.2, "regen_quality": 0.25},
        {"confidence": 0.5, "regen_quality": 0.55},
        {"confidence": 0.8, "regen_quality": 0.85},
    ]
    r = compute_correlation(data)
    assert r > 0.9

    # No data
    assert compute_correlation([]) == 0.0
```

**Step 2: Implement**

```python
# In calibrate.py

from dataclasses import dataclass


@dataclass
class CalibrationReport:
    components_tested: int
    correlation: float
    bands: dict  # confidence_band → regen_success_rate
    threshold: float  # recommended confidence for safe regeneration


def select_calibration_targets(components: list[dict], count: int = 6) -> list[dict]:
    """Select components spanning confidence bands for calibration."""
    sorted_comps = sorted(components, key=lambda c: c["confidence"])
    if len(sorted_comps) <= count:
        return sorted_comps

    # Pick evenly spaced across the range
    step = len(sorted_comps) / count
    targets = []
    for i in range(count):
        idx = int(i * step)
        targets.append(sorted_comps[idx])
    return targets


def compute_correlation(data: list[dict]) -> float:
    """Compute Pearson correlation between confidence and regen_quality."""
    if len(data) < 2:
        return 0.0
    n = len(data)
    xs = [d["confidence"] for d in data]
    ys = [d["regen_quality"] for d in data]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)
```

**Step 3: Run tests**

Run: `pytest tests/test_calibration_suite.py -v`

**Step 4: Commit**

```bash
git add src/opencode_arch/cli/calibrate.py tests/test_calibration_suite.py
git commit -m "feat: calibration suite - target selection + correlation"
```

---

## Task 7: Full Test Suite Verification

**Step 1: Run all arch-std tests**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: All existing + new tests pass

**Step 2: Run all opencode-arch tests**

Run: `pytest tests/ -v` (in opencode-arch)
Expected: New tests pass (pre-existing failures in test_scan.py unchanged)

**Step 3: Final commit if any fixups needed**

---

## Summary

| Task | Feature | New Tests | Repo |
|------|---------|-----------|------|
| 1 | Structural auto-enrichment | 9 | arch-std |
| 2 | Behavioral auto-enrichment | 4 | arch-std |
| 3 | Pipeline integration + integration test | 1 | arch-std |
| 4 | Benchmark script | 0 (manual) | arch-std |
| 5 | Regeneration proof | 3 | opencode-arch |
| 6 | Calibration suite | 2 | opencode-arch |
| 7 | Full verification | 0 | both |

**Total: ~19 new tests across both repos**
