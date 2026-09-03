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
    def test_curation_and_no_curation_are_mutually_exclusive(self, model_dir):
        curation = model_dir / "curation.yaml"
        curation.write_text("version: 1\nviews: {}\n")
        with pytest.raises(SystemExit):
            main(["viewer", str(model_dir), "--curation", str(curation), "--no-curation"])

    def test_explicit_invalid_curation_warns_and_exits_zero(self, model_dir, capsys):
        out = model_dir / "viewer.html"
        missing = model_dir / "missing.yaml"
        rc = main(["viewer", str(model_dir), "-o", str(out), "--curation", str(missing)])
        assert rc == 0
        assert "warning" in capsys.readouterr().out.lower()
        assert out.exists()

    def test_no_curation_disables_default_discovery(self, model_dir):
        curation = model_dir / ".architecture" / "viewer-curation.yaml"
        curation.parent.mkdir()
        curation.write_text("version: nope\n")
        out = model_dir / "viewer.html"
        assert main(["viewer", str(model_dir), "-o", str(out), "--no-curation"]) == 0
        assert "CURATION_ROOT_INVALID" not in out.read_text()

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
        architecture = model_dir / ".architecture"
        architecture.mkdir(exist_ok=True)
        (architecture / "devlog.jsonl").write_text(
            '{"log_type":"decision","title":"HISTORY-MARKER","content":"' + "history " * 20000 + '"}\n'
        )
        (architecture / "pipeline-history.jsonl").write_text(
            '{"run_id":"PIPELINE-HISTORY-MARKER","started_at":"now","status":"complete","stages":[]}\n'
        )
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
        assert "HISTORY-MARKER" not in html
        assert "PIPELINE-HISTORY-MARKER" not in html
        assert without_docs_size < with_docs_size * 0.7
        assert '"docs": false' in html
        assert '"operations": false' in html
        assert '"history": false' in html
        assert "Documentation unavailable in this viewer." in html
        assert "Operational artifacts unavailable in this viewer." in html
        assert "Pipeline history unavailable in this viewer." in html
        assert "if (historyLink) historyLink.addEventListener" in html
        assert ".architecture/viewer-curation.yaml" in html

    def test_missing_model_returns_error(self, tmp_path):
        rc = main(["viewer", str(tmp_path)])
        assert rc != 0

    def test_auto_title_from_project(self, model_dir):
        out = model_dir / "v.html"
        rc = main(["viewer", str(model_dir), "-o", str(out)])
        assert rc == 0
        assert "test-project" in out.read_text().lower() or "test_project" in out.read_text().lower()
