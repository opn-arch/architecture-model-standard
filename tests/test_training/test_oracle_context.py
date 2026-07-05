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
        assert "## Source Code Context" in context

    def test_manifest_summary_shows_key_modules(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "big_module.py").write_text("# big\n" * 100)
        (tmp_path / "tiny.py").write_text("# tiny\n")

        builder = OracleContextBuilder(tmp_path)
        context = builder.build()
        assert "big_module" in context
        # Larger module should appear before smaller in the summary
        assert context.index("big_module") < context.index("tiny")

    def test_max_chars_respected(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "huge.py").write_text("x = 1\n" * 10000)

        builder = OracleContextBuilder(tmp_path, max_chars=5000)
        context = builder.build()
        assert len(context) <= 5000  # hard truncation at max_chars

    def test_block_level_dependencies_in_summary(self, tmp_path):
        """Summary includes block-level dependency matrix when blocks and interfaces exist."""
        # Create two blocks with cross-imports (each needs 2+ files to be a block)
        block_a = tmp_path / "alpha"
        block_b = tmp_path / "beta"
        block_a.mkdir()
        block_b.mkdir()
        (tmp_path / "__init__.py").write_text("")
        (block_a / "__init__.py").write_text("")
        (block_b / "__init__.py").write_text("")
        (block_a / "sender.py").write_text(
            "import beta.receiver\n\ndef send(): pass\n" + "# pad\n" * 15
        )
        (block_a / "helper.py").write_text("def help(): pass\n" + "# pad\n" * 15)
        (block_b / "receiver.py").write_text("def receive(): pass\n" + "# pad\n" * 15)
        (block_b / "utils.py").write_text("def util(): pass\n" + "# pad\n" * 15)

        builder = OracleContextBuilder(tmp_path)
        manifest = builder._generate_manifest()
        summary = builder._format_manifest_summary(manifest)

        # Should have block-level deps section
        assert "Block-Level Dependencies" in summary
        assert "MUST have depends-on/consumes" in summary
