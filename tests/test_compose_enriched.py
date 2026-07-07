"""Tests for compose_enriched_model."""
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
    def test_basic_composition(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        assert len(model.entities.components) > 0

    def test_component_has_module_constants(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower() and c.name != "__init__"),
            None
        )
        assert ansi_comp is not None
        const_names = {c.name for c in ansi_comp.constants}
        assert "CSI" in const_names

    def test_component_has_class_attribute_constants(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower() and c.name != "__init__"),
            None
        )
        const_names = {c.name for c in ansi_comp.constants}
        assert "BLACK" in const_names
        assert "RED" in const_names

    def test_component_has_module_assignments(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower() and c.name != "__init__"),
            None
        )
        const_names = {c.name for c in ansi_comp.constants}
        assert "Fore" in const_names

    def test_component_has_signatures_with_body_hints(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower() and c.name != "__init__"),
            None
        )
        sig_names = {s.name for s in ansi_comp.signatures}
        assert "code_to_chars" in sig_names
        code_sig = next(s for s in ansi_comp.signatures if s.name == "code_to_chars")
        assert code_sig.body_hint != ""
        assert "CSI" in code_sig.body_hint

    def test_component_has_test_contracts(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        ansi_comp = next(
            (c for c in model.entities.components if "ansi" in c.name.lower() and c.name != "__init__"),
            None
        )
        assert len(ansi_comp.test_contracts) > 0

    def test_model_is_valid_and_saveable(self, colorama_like, tmp_path):
        from architecture_model.core.parser import save_model, load_model
        model = compose_enriched_model(colorama_like)
        out = tmp_path / "output" / "model.yaml"
        out.parent.mkdir()
        save_model(model, out)
        loaded = load_model(out)
        assert len(loaded.entities.components) == len(model.entities.components)

    def test_excludes_test_files_from_components(self, colorama_like):
        model = compose_enriched_model(colorama_like)
        for comp in model.entities.components:
            assert "test" not in comp.id.lower() or comp.name == "__init__"
            for f in comp.files:
                assert "test_" not in f and "_test.py" not in f
