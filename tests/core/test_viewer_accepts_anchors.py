"""Track 4 Pass 1 Task 4 — generate_html_viewer accepts optional anchors kwarg."""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_html_viewer
from architecture_model.core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT


def _minimal_model_yaml(path: Path) -> Path:
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-1
      name: c1
  components:
    - id: COMP-1
      name: k1
      source_files: [src/a.py]
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
""".lstrip())
    return path


def test_generate_html_viewer_accepts_anchors_kwarg(tmp_path):
    model_path = _minimal_model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    anchors = {v: build_slice_anchor(model, v, tmp_path) for v in VIEW_TO_ARTIFACT}
    output = tmp_path / "viewer.html"
    result = generate_html_viewer(model, output, repo_path=tmp_path, anchors=anchors)
    assert result.is_file()


def test_generate_html_viewer_still_works_without_anchors(tmp_path):
    model_path = _minimal_model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    output = tmp_path / "viewer.html"
    result = generate_html_viewer(model, output, repo_path=tmp_path)
    assert result.is_file()
