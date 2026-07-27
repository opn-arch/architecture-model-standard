"""Tests for auto-enrichment."""
import pytest
from pathlib import Path
from architecture_model.core.types import (
    ArchitectureModel, Component, ModelMeta, FunctionSignature, Constant, TestContract
)
from architecture_model.orchestration.enrich import enrich_model


def _make_model(*comps):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.5"),
        entities={"components": list(comps)},
        relationships=[]
    )


def test_enrich_populates_signatures(tmp_path):
    """Extract function signatures from source files."""
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text('''
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"

def _private():
    pass

MAX_RETRIES = 3
''')
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/mymod.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    sig_names = [s.name for s in c.signatures]
    assert "greet" in sig_names
    assert "_private" not in sig_names  # private functions excluded


def test_enrich_populates_constants(tmp_path):
    """Extract module-level constants."""
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text('''
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0
_internal = "hidden"
''')
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/mymod.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    const_names = [co.name for co in c.constants]
    assert "MAX_RETRIES" in const_names
    assert "DEFAULT_TIMEOUT" in const_names


def test_enrich_finds_test_contracts(tmp_path):
    """Discover test files and extract contracts."""
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text("def add(a, b): return a + b\n")
    test_file = tmp_path / "tests" / "test_mymod.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text('''
def test_add():
    assert add(1, 2) == 3

def test_add_negative():
    assert add(-1, 1) == 0
''')
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/mymod.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    test_methods = [t.test_method for t in c.test_contracts]
    assert "test_add" in test_methods


def test_enrich_preserves_existing(tmp_path):
    """Don't overwrite manually-authored signatures."""
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text("def foo(): pass\ndef bar(): pass\n")
    existing_sig = FunctionSignature(name="manual_fn", params=["x: int"], returns="int", body_hint="return x * 2")
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/mymod.py"],
                     signatures=[existing_sig])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    sig_names = [s.name for s in c.signatures]
    assert "manual_fn" in sig_names  # preserved
    assert "foo" in sig_names        # added


def test_enrich_skips_planned_components(tmp_path):
    """PLANNED components should not be enriched."""
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text("def foo(): pass\n")
    comp = Component(id="C1", name="mymod", status="PLANNED", files=["src/mymod.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    assert len(c.signatures) == 0


def test_enrich_handles_missing_files(tmp_path):
    """Components pointing to non-existent files should be skipped gracefully."""
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/nonexistent.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)  # should not crash
    c = enriched.entities["components"][0]
    assert len(c.signatures) == 0


def test_enrich_multiple_files(tmp_path):
    """Component with multiple source files gets signatures from all."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def func_a(): pass\n")
    (tmp_path / "src" / "b.py").write_text("def func_b(): pass\n")
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/a.py", "src/b.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    sig_names = [s.name for s in c.signatures]
    assert "func_a" in sig_names
    assert "func_b" in sig_names


def test_enrich_class_methods_no_name_collision(tmp_path):
    """Multiple classes with same method name should all be included."""
    src = tmp_path / "src" / "tags.py"
    src.parent.mkdir(parents=True)
    src.write_text('''
class TagA:
    def to_json(self, value):
        """Convert to JSON."""
        return str(value)

class TagB:
    def to_json(self, value):
        """Convert to JSON."""
        return repr(value)
''')
    comp = Component(id="C1", name="tags", status="ACTIVE", files=["src/tags.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    # Both should be present with qualified names
    sig_names = [s.name for s in c.signatures]
    assert "TagA.to_json" in sig_names
    assert "TagB.to_json" in sig_names


def test_enrich_class_level_constants(tmp_path):
    """Class-level constants (non-uppercase) should be extracted."""
    src = tmp_path / "src" / "tags.py"
    src.parent.mkdir(parents=True)
    src.write_text('''
class MarkupTag:
    key = " m"
    ensure_ascii = False

class IntTag:
    key = " di"
''')
    comp = Component(id="C1", name="tags", status="ACTIVE", files=["src/tags.py"])
    model = _make_model(comp)
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    const_names = [co.name for co in c.constants]
    assert "MarkupTag.key" in const_names
    assert "MarkupTag.ensure_ascii" in const_names
    assert "IntTag.key" in const_names
