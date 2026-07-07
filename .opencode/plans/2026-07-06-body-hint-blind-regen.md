# Body Hint Extractor + Blind Regen Mode

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an AST-based body_hint extractor that captures function implementation intent at tiered detail levels, enrich the manifest scanner to extract class attributes and module-level assignments, compose all extracted data into the architecture model, then validate via blind regen on colorama's ansi subsystem.

**Architecture:** New `manifest/body_hints.py` module performs AST analysis on function bodies (classifying as trivial/short/complex, producing appropriate hints). The existing scanner gains class-attribute and module-assignment extraction. A new `compose_enriched_model()` function combines manifest + test_analyzer + body_hints into a fully-populated `.architecture-model.yaml`. The `opencode-arch` regen-loop gains a `--blind` flag that prevents the agent from reading source/test files.

**Tech Stack:** Python 3.11+, `ast` stdlib, pytest, existing architecture_model types (FunctionSignature, Constant, Component)

---

## Task 1: Body Hint Extractor — Core Module

**Files:**
- Create: `src/architecture_model/manifest/body_hints.py`
- Test: `tests/test_body_hints.py`

### Step 1: Write failing tests

```python
"""Tests for body_hints module — AST-based function body classification and hint generation."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from architecture_model.manifest.body_hints import (
    BodyComplexity,
    classify_function,
    extract_body_hint,
    extract_file_hints,
)
from architecture_model.core.types import FunctionSignature


class TestClassifyFunction:
    """Test body complexity classification."""

    def test_trivial_one_liner(self):
        code = "def f(x):\n    return x + 1\n"
        assert classify_function(code, "f") == BodyComplexity.TRIVIAL

    def test_trivial_single_expression(self):
        code = "def greet(name):\n    return 'hello ' + name\n"
        assert classify_function(code, "greet") == BodyComplexity.TRIVIAL

    def test_short_two_to_five_lines(self):
        code = textwrap.dedent("""\
            def process(x):
                result = x * 2
                result += 1
                return result
        """)
        assert classify_function(code, "process") == BodyComplexity.SHORT

    def test_complex_six_plus_lines(self):
        code = textwrap.dedent("""\
            def big_func(data):
                result = []
                for item in data:
                    if item > 0:
                        result.append(item)
                    else:
                        result.append(-item)
                return result
        """)
        assert classify_function(code, "big_func") == BodyComplexity.COMPLEX

    def test_docstring_not_counted_as_body(self):
        code = textwrap.dedent("""\
            def f(x):
                \"\"\"A docstring.\"\"\"
                return x + 1
        """)
        assert classify_function(code, "f") == BodyComplexity.TRIVIAL


class TestExtractBodyHint:
    """Test body hint extraction at each tier."""

    def test_trivial_returns_exact_body(self):
        code = "def code_to_chars(code):\n    return CSI + str(code) + 'm'\n"
        hint = extract_body_hint(code, "code_to_chars")
        assert hint == "return CSI + str(code) + 'm'"

    def test_short_returns_semicolon_joined(self):
        code = textwrap.dedent("""\
            def process(x):
                result = x * 2
                result += 1
                return result
        """)
        hint = extract_body_hint(code, "process")
        assert "result = x * 2" in hint
        assert ";" in hint  # semicolons joining lines

    def test_complex_returns_summary(self):
        code = textwrap.dedent("""\
            def big_func(data):
                result = []
                for item in data:
                    if item > 0:
                        result.append(item)
                    else:
                        result.append(-item)
                return result
        """)
        hint = extract_body_hint(code, "big_func")
        # Complex: should be much shorter than original
        assert len(hint) < len(code)
        # Should mention key constructs
        assert "for" in hint.lower() or "loop" in hint.lower() or "iterate" in hint.lower()

    def test_init_method_special_handling(self):
        code = textwrap.dedent("""\
            class Foo:
                def __init__(self):
                    for name in dir(self):
                        if not name.startswith('_'):
                            value = getattr(self, name)
                            setattr(self, name, code_to_chars(value))
        """)
        hint = extract_body_hint(code, "__init__", class_name="Foo")
        assert hint  # Should produce something meaningful


class TestExtractFileHints:
    """Test file-level extraction producing FunctionSignature objects."""

    def test_extracts_all_functions(self, tmp_path):
        source = textwrap.dedent("""\
            CSI = '\\033['

            def code_to_chars(code):
                return CSI + str(code) + 'm'

            def set_title(title):
                return OSC + '2;' + title + BEL
        """)
        f = tmp_path / "ansi.py"
        f.write_text(source)

        sigs = extract_file_hints(f)
        assert len(sigs) == 2
        assert all(isinstance(s, FunctionSignature) for s in sigs)
        names = {s.name for s in sigs}
        assert "code_to_chars" in names
        assert "set_title" in names

    def test_includes_class_methods(self, tmp_path):
        source = textwrap.dedent("""\
            class AnsiCursor:
                def UP(self, n=1):
                    return CSI + str(n) + 'A'
                def DOWN(self, n=1):
                    return CSI + str(n) + 'B'
        """)
        f = tmp_path / "cursor.py"
        f.write_text(source)

        sigs = extract_file_hints(f)
        names = {s.name for s in sigs}
        assert "UP" in names
        assert "DOWN" in names

    def test_body_hint_populated(self, tmp_path):
        source = "def f(x):\n    return x + 1\n"
        f = tmp_path / "simple.py"
        f.write_text(source)

        sigs = extract_file_hints(f)
        assert sigs[0].body_hint == "return x + 1"

    def test_params_and_returns_populated(self, tmp_path):
        source = "def add(a: int, b: int) -> int:\n    return a + b\n"
        f = tmp_path / "typed.py"
        f.write_text(source)

        sig = extract_file_hints(f)[0]
        assert sig.params == ["a: int", "b: int"]
        assert sig.returns == "int"

    def test_private_functions_excluded(self, tmp_path):
        source = textwrap.dedent("""\
            def public_func():
                return 1

            def _private_func():
                return 2
        """)
        f = tmp_path / "mixed.py"
        f.write_text(source)

        sigs = extract_file_hints(f)
        names = {s.name for s in sigs}
        assert "public_func" in names
        assert "_private_func" not in names

    def test_include_init(self, tmp_path):
        source = textwrap.dedent("""\
            class Foo:
                def __init__(self, x):
                    self.x = x
        """)
        f = tmp_path / "cls.py"
        f.write_text(source)

        sigs = extract_file_hints(f)
        assert any(s.name == "__init__" for s in sigs)
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_body_hints.py -v`
Expected: FAIL (ImportError — module doesn't exist yet)

### Step 3: Implement `body_hints.py`

Create `src/architecture_model/manifest/body_hints.py` with:
- `BodyComplexity` enum (TRIVIAL, SHORT, COMPLEX)
- `classify_function(source, func_name)` — count body statements after stripping docstring
- `extract_body_hint(source, func_name, class_name=None)` — produce tiered hint
- `extract_file_hints(filepath, include_private=False)` — produce list[FunctionSignature]
- `_find_function()`, `_strip_docstring()`, `_node_to_signature()`, `_summarize_complex_body()` helpers

Tiering logic:
- TRIVIAL (1 statement): `ast.unparse(body[0])` — exact body text
- SHORT (2-5 statements): `"; ".join(ast.unparse(s) for s in body)` — semicolons
- COMPLEX (6+ statements): structural summary (loops, ifs, returns, assignments condensed)

### Step 4: Run tests

Run: `pytest tests/test_body_hints.py -v`
Expected: All PASS

### Step 5: Commit

```bash
git add src/architecture_model/manifest/body_hints.py tests/test_body_hints.py
git commit -m "feat: add AST-based body_hint extractor with tiered complexity"
```

---

## Task 2: Enriched Scanner — Class Attributes + Module Assignments

**Files:**
- Modify: `src/architecture_model/manifest/scanner.py:165-350`
- Test: `tests/test_enriched_scanner.py`

### Step 1: Write failing tests

```python
"""Tests for enriched scanner — class attributes, module constants, module assignments."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from architecture_model.manifest.scanner import (
    _extract_class_attributes,
    _extract_module_constants,
    _extract_module_assignments,
    _scan_file,
)


class TestExtractClassAttributes:
    """Test extraction of class-level attribute assignments (e.g., BLACK=30)."""

    def test_simple_int_attributes(self):
        source = textwrap.dedent("""\
            class AnsiFore:
                BLACK = 30
                RED = 31
                GREEN = 32
        """)
        tree = ast.parse(source)
        cls_node = tree.body[0]
        attrs = _extract_class_attributes(cls_node)
        assert {"BLACK": "30", "RED": "31", "GREEN": "32"} == attrs

    def test_string_attributes(self):
        source = textwrap.dedent("""\
            class Config:
                NAME = "hello"
                VERSION = "1.0"
        """)
        tree = ast.parse(source)
        cls_node = tree.body[0]
        attrs = _extract_class_attributes(cls_node)
        assert attrs["NAME"] == "'hello'"
        assert attrs["VERSION"] == "'1.0'"

    def test_ignores_methods(self):
        source = textwrap.dedent("""\
            class Foo:
                X = 1
                def method(self):
                    pass
        """)
        tree = ast.parse(source)
        cls_node = tree.body[0]
        attrs = _extract_class_attributes(cls_node)
        assert "X" in attrs
        assert "method" not in attrs


class TestExtractModuleConstants:
    """Test extraction of module-level constant assignments (UPPER_CASE = literal)."""

    def test_basic_constants(self):
        source = textwrap.dedent("""\
            CSI = '\\033['
            OSC = '\\033]'
            BEL = '\\a'
            some_var = 42
        """)
        tree = ast.parse(source)
        consts = _extract_module_constants(tree)
        assert "CSI" in consts
        assert "OSC" in consts
        assert "BEL" in consts
        assert "some_var" not in consts

    def test_non_literal_excluded(self):
        source = textwrap.dedent("""\
            CONST = 42
            COMPUTED = some_func()
        """)
        tree = ast.parse(source)
        consts = _extract_module_constants(tree)
        assert "CONST" in consts
        assert "COMPUTED" not in consts


class TestExtractModuleAssignments:
    """Test extraction of module-level instance assignments (e.g., Fore = AnsiFore())."""

    def test_instance_assignments(self):
        source = textwrap.dedent("""\
            Fore = AnsiFore()
            Back = AnsiBack()
            Style = AnsiStyle()
        """)
        tree = ast.parse(source)
        assigns = _extract_module_assignments(tree)
        assert assigns["Fore"] == "AnsiFore()"
        assert assigns["Back"] == "AnsiBack()"
        assert assigns["Style"] == "AnsiStyle()"

    def test_excludes_constants(self):
        source = textwrap.dedent("""\
            CSI = '\\033['
            Fore = AnsiFore()
        """)
        tree = ast.parse(source)
        assigns = _extract_module_assignments(tree)
        assert "CSI" not in assigns
        assert "Fore" in assigns


class TestScanFileEnriched:
    """Test that _scan_file now includes enriched fields."""

    def test_scan_includes_class_attributes(self, tmp_path):
        source = textwrap.dedent("""\
            class AnsiFore:
                BLACK = 30
                RED = 31
        """)
        f = tmp_path / "ansi.py"
        f.write_text(source)
        result = _scan_file(tmp_path, f)
        assert result["classes"][0]["attributes"] == {"BLACK": "30", "RED": "31"}

    def test_scan_includes_module_constants(self, tmp_path):
        source = "CSI = '\\\\033['\n"
        f = tmp_path / "const.py"
        f.write_text(source)
        result = _scan_file(tmp_path, f)
        assert "CSI" in result["module_constants"]

    def test_scan_includes_module_assignments(self, tmp_path):
        source = "Fore = AnsiFore()\n"
        f = tmp_path / "inst.py"
        f.write_text(source)
        result = _scan_file(tmp_path, f)
        assert "Fore" in result["module_assignments"]
```

### Step 2: Run tests, verify failure

Run: `pytest tests/test_enriched_scanner.py -v`
Expected: FAIL (ImportError — new functions don't exist)

### Step 3: Implement

Add to `scanner.py`:
- `_extract_class_attributes(cls_node: ast.ClassDef) -> dict[str, str]` — simple Name=Constant assignments
- `_extract_module_constants(tree: ast.Module) -> dict[str, str]` — UPPER_CASE = literal
- `_extract_module_assignments(tree: ast.Module) -> dict[str, str]` — non-constant, non-literal assignments
- Modify `_extract_classes()` to include `"attributes"` field in each class dict
- Modify `_scan_file()` to include `"module_constants"` and `"module_assignments"` in return dict

### Step 4: Run tests

Run: `pytest tests/test_enriched_scanner.py -v`
Expected: All PASS

### Step 5: Run full suite for regressions

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: No regressions

### Step 6: Commit

```bash
git add src/architecture_model/manifest/scanner.py tests/test_enriched_scanner.py
git commit -m "feat: extract class attributes, module constants, module assignments in scanner"
```

---

## Task 3: Compose Enriched Model — Manifest + Body Hints + Test Analyzer → Model

**Files:**
- Modify: `src/architecture_model/core/merger.py` (add `compose_enriched_model()`)
- Test: `tests/test_compose_enriched.py`

### Step 1: Write failing tests

```python
"""Tests for compose_enriched_model — combines manifest + body_hints + test_analyzer into model."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from architecture_model.core.merger import compose_enriched_model
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Constant,
    FunctionSignature,
    TestContract,
)


@pytest.fixture
def colorama_like(tmp_path):
    """Create a minimal colorama-like source structure."""
    pkg = tmp_path / "colorama"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .ansi import Fore, Back, Style\n")
    (pkg / "ansi.py").write_text(textwrap.dedent("""\
        CSI = '\\033['

        def code_to_chars(code):
            return CSI + str(code) + 'm'

        class AnsiCodes:
            def __init__(self):
                for name in dir(self):
                    if not name.startswith('_'):
                        value = getattr(self, name)
                        setattr(self, name, code_to_chars(value))

        class AnsiFore(AnsiCodes):
            BLACK = 30
            RED = 31

        Fore = AnsiFore()
    """))

    tests = tmp_path / "colorama" / "tests"
    tests.mkdir(parents=True)
    (tests / "__init__.py").write_text("")
    (tests / "ansi_test.py").write_text(textwrap.dedent("""\
        from colorama.ansi import code_to_chars, Fore
        import unittest

        class TestAnsi(unittest.TestCase):
            def test_code_to_chars(self):
                self.assertEqual(code_to_chars(0), '\\033[0m')

            def test_fore_black(self):
                self.assertEqual(Fore.BLACK, '\\033[30m')
    """))
    return tmp_path


class TestComposeEnrichedModel:
    """Test that compose_enriched_model produces a fully-populated model."""

    def test_basic_composition(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        assert len(model.entities.components) > 0

    def test_component_has_module_constants(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower()),
            None
        )
        assert ansi_comp is not None
        const_names = {c.name for c in ansi_comp.constants}
        assert "CSI" in const_names

    def test_component_has_class_attribute_constants(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower()),
            None
        )
        const_names = {c.name for c in ansi_comp.constants}
        assert "BLACK" in const_names
        assert "RED" in const_names

    def test_component_has_signatures_with_body_hints(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower()),
            None
        )
        sig_names = {s.name for s in ansi_comp.signatures}
        assert "code_to_chars" in sig_names
        code_sig = next(s for s in ansi_comp.signatures if s.name == "code_to_chars")
        assert "CSI" in code_sig.body_hint

    def test_component_has_test_contracts(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower()),
            None
        )
        assert len(ansi_comp.test_contracts) > 0

    def test_model_is_saveable(self, colorama_like, tmp_path):
        from architecture_model.core.parser import save_model, load_model
        model = compose_enriched_model(colorama_like)
        out = tmp_path / "model.yaml"
        save_model(model, out)
        loaded = load_model(out)
        assert len(loaded.entities.components) == len(model.entities.components)
```

### Step 2: Run tests, verify failure

Run: `pytest tests/test_compose_enriched.py -v`
Expected: FAIL (ImportError)

### Step 3: Implement `compose_enriched_model()`

Add to `merger.py`. Key logic:
1. `_discover_source_files(project_root)` — find all `.py` excluding tests/*, __pycache__, setup.py
2. `_discover_test_files(project_root)` — find all test_*.py and *_test.py files
3. `_map_tests_to_sources(test_files, source_files, project_root)` — parse test imports to determine which source files each test covers
4. For each source file: extract module_constants, class_attributes, module_assignments (via scanner), extract body_hints (via body_hints module), map test_contracts from associated test files
5. Build Component per source file, assemble into ArchitectureModel

### Step 4: Run tests

Run: `pytest tests/test_compose_enriched.py -v`
Expected: All PASS

### Step 5: Full suite

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: No regressions

### Step 6: Commit

```bash
git add src/architecture_model/core/merger.py tests/test_compose_enriched.py
git commit -m "feat: compose_enriched_model combines manifest+body_hints+test_analyzer"
```

---

## Task 4: Verify Manifest Init on Colorama

**Files:**
- Possibly modify: init command if needed
- This is primarily a verification step

### Step 1: Run init

Run: `architecture-model init /tmp/test-repos/colorama`

### Step 2: Verify output

Check that `.architecture-model.yaml` includes F-blocks for source package (not just tests).

### Step 3: Generate manifest

Run: `architecture-model generate /tmp/test-repos/colorama`
Verify source modules appear in manifest.

### Step 4: Fix if needed, commit

---

## Task 5: `--blind` Flag in Regen-Loop (opencode-arch repo)

**Files:**
- Modify: `src/opencode_arch/cli/regen_loop.py`
- Modify: `src/opencode_arch/cli/main.py`
- Test: `tests/test_regen_loop.py`

### Step 1: Write failing test

Test that in blind mode, runner gets a temp dir (not repo_path) and that source files are deleted before agent runs.

### Step 2: Implement

Add `blind: bool = False` to `run_regen_loop()`. When blind:
- Create temp workdir
- Copy test files into it (agent needs to run tests)
- Set `runner.run(repo_path=temp_dir)` instead of actual repo
- All source context passed exclusively via prompt slots
- After agent generates, tests run in the temp dir

### Step 3: Add CLI arg

`@click.option("--blind", is_flag=True, ...)`

### Step 4: Run tests, commit

---

## Task 6: Fix Telemetry Feature Counts (opencode-arch repo)

**Files:**
- Modify: `src/opencode_arch/cli/regen_loop.py:370-388`

### Step 1: Pass actual counts from `_process_subsystem` into the result dict

### Step 2: Update `_record_outcome` to read from result

### Step 3: Test, commit

---

## Task 7: E2E Blind Regen on Colorama Ansi

### Step 1: Run `compose_enriched_model()` on colorama, save model
### Step 2: Verify model has expected constants, signatures, contracts
### Step 3: Run regen-loop with `--blind --subsystem ansi`
### Step 4: Record pass rate as baseline
### Step 5: Compute gap: `100% - blind_score`

---

## Dependency Graph

```
Task 1 (body_hints.py)  ──┐
                          ├──→ Task 3 (compose_enriched_model) ──→ Task 4 (init verify) ──→ Task 7 (e2e)
Task 2 (enriched scanner) ┘                                                                  ↑
                                                              Task 5 (--blind flag) ──────────┘
                                                              Task 6 (telemetry fix) ─────────┘
```

Tasks 1 and 2 are **independent** (parallel).
Task 3 depends on both 1 and 2.
Tasks 5 and 6 are **independent** (parallel, in opencode-arch repo).
Task 7 depends on 3, 4, 5, 6.
