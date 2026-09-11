"""Track 4 Pass 1 Task 5 — functional panel renders only anchor.model entities."""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_html_viewer
from architecture_model.core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT


def _model_yaml(path: Path) -> Path:
    """Model: CAP-1 realized by COMP-1 (both in-scope for functional). LAY-9 is unrelated."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-1
      name: InScopeCap
  components:
    - id: COMP-1
      name: InScopeComp
      source_files: [src/a.py]
  layers:
    - id: LAY-9
      name: UnrelatedLayerNAME
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
""".lstrip())
    return path


def test_functional_panel_renders_only_anchored_entities(tmp_path):
    model_path = _model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    anchors = {v: build_slice_anchor(model, v, tmp_path) for v in VIEW_TO_ARTIFACT}
    out = tmp_path / "viewer.html"
    generate_html_viewer(model, out, repo_path=tmp_path, anchors=anchors)
    html = out.read_text(encoding="utf-8")

    assert "InScopeCap" in html
    from architecture_model.core.visualize import generate_functional_architecture_diagram
    functional_body = generate_functional_architecture_diagram(anchors["functional"].model)
    assert "UnrelatedLayerNAME" not in functional_body


def test_functional_panel_without_anchors_still_uses_full_model(tmp_path):
    model_path = _model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    out = tmp_path / "viewer.html"
    generate_html_viewer(model, out, repo_path=tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "InScopeCap" in html
