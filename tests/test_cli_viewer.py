"""Tests for `architecture-model viewer` CLI command."""

import json
import zipfile
from pathlib import Path

import pytest

from architecture_model.cli.main import main


@pytest.fixture
def model_dir(tmp_path):
    """Create a minimal model file for CLI testing."""
    model_yaml = tmp_path / ".architecture-model.yaml"
    model_yaml.write_text("""\
meta:
  project: test-project
  schema_version: '2.0'
entities:
  components:
    - id: COMP-1
      name: Parser
      status: ACTIVE
  capabilities:
    - id: CAP-1
      name: Parsing
      status: ACTIVE
relationships:
  - from_id: COMP-1
    to_id: CAP-1
    type: realizes
""")
    return tmp_path


class TestViewerCLI:
    def test_generates_html_file(self, model_dir):
        out = model_dir / "viewer.html"
        rc = main(["viewer", str(model_dir), "-o", str(out)])
        assert rc == 0
        assert out.exists()
        html = out.read_text()
        assert "<!DOCTYPE html>" in html
        assert "COMP-1" in html

    def test_default_output_path(self, model_dir):
        rc = main(["viewer", str(model_dir)])
        assert rc == 0
        default = model_dir / ".architecture" / "diagrams" / "viewer.html"
        assert default.exists()

    def test_custom_title(self, model_dir):
        out = model_dir / "v.html"
        rc = main(["viewer", str(model_dir), "-o", str(out), "--title", "My System"])
        assert rc == 0
        assert "My System" in out.read_text()

    def test_zip_flag(self, model_dir):
        out = model_dir / "viewer.html"
        rc = main(["viewer", str(model_dir), "-o", str(out), "--zip"])
        assert rc == 0
        zip_path = out.with_suffix(".zip")
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path) as zf:
            assert "viewer.html" in zf.namelist()

    def test_no_docs_flag(self, model_dir):
        # Create SE docs that would normally be embedded
        se_dir = model_dir / ".architecture-models" / "docs" / "se"
        se_dir.mkdir(parents=True)
        (se_dir / "conops.md").write_text("# ConOps\n\nBig document content here.")
        out = model_dir / "v.html"

        # With docs (default)
        main(["viewer", str(model_dir), "-o", str(out)])
        with_docs_size = out.stat().st_size

        # Without docs
        out2 = model_dir / "v2.html"
        main(["viewer", str(model_dir), "-o", str(out2), "--no-docs"])
        without_docs_size = out2.stat().st_size

        # Without docs should be smaller (or at least not contain the doc content)
        html = out2.read_text()
        assert "Big document content here" not in html

    def test_missing_model_returns_error(self, tmp_path):
        rc = main(["viewer", str(tmp_path)])
        assert rc != 0

    def test_auto_title_from_project(self, model_dir):
        out = model_dir / "v.html"
        rc = main(["viewer", str(model_dir), "-o", str(out)])
        assert rc == 0
        assert "test-project" in out.read_text().lower() or "test_project" in out.read_text().lower()
