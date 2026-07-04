"""Tests for oracle context building."""

import pytest
from architecture_model.training.oracle_context import OracleContextBuilder


class TestOracleContextBuilder:
    def test_build_includes_manifest_summary(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "client.py").write_text("class Client:\n    def get(self): pass\n" * 20)
        (tmp_path / "pool.py").write_text("class Pool:\n    def acquire(self): pass\n" * 10)

        builder = OracleContextBuilder(tmp_path)
        context = builder.build()
        assert "Reality Manifest Summary" in context
        assert "client" in context.lower()

    def test_build_includes_code_context(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "main.py").write_text("def main():\n    print('hello')\n")

        builder = OracleContextBuilder(tmp_path)
        context = builder.build()
        assert "Source Code Context" in context or "main" in context

    def test_manifest_summary_shows_key_modules(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "big_module.py").write_text("# big\n" * 100)
        (tmp_path / "tiny.py").write_text("# tiny\n")

        builder = OracleContextBuilder(tmp_path)
        context = builder.build()
        assert "big_module" in context

    def test_max_chars_respected(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "huge.py").write_text("x = 1\n" * 10000)

        builder = OracleContextBuilder(tmp_path, max_chars=5000)
        context = builder.build()
        assert len(context) <= 6000  # some tolerance for headers
