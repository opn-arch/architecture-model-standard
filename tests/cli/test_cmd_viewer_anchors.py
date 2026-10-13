"""Track 4 Pass 1, Task 6: ``_cmd_viewer`` computes slice anchors and
passes them via ``anchors=`` to ``generate_html_viewer``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from architecture_model.cli.main import main
from architecture_model.core.slice_anchor import VIEW_TO_ARTIFACT, SliceAnchor


MODEL_YAML = """meta:
  schema_version: '2.1'
  project: demo
entities:
  components:
    - id: COMP-1
      name: Widget
      status: ACTIVE
  capabilities:
    - id: CAP-F1
      name: DoThing
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
"""


def test_cmd_viewer_passes_anchors_for_each_view(tmp_path, capsys) -> None:
    (tmp_path / ".architecture-model.yaml").write_text(MODEL_YAML, encoding="utf-8")
    out = tmp_path / "viewer.html"

    captured_kwargs: dict = {}

    def _fake_generate(model, output_path, **kwargs):
        captured_kwargs.update(kwargs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("<html></html>", encoding="utf-8")
        return output_path

    with patch(
        "architecture_model.core.visualize.generate_html_viewer",
        side_effect=_fake_generate,
    ):
        exit_code = main(["viewer", str(tmp_path), "-o", str(out), "--no-docs"])

    assert exit_code == 0, capsys.readouterr()
    anchors = captured_kwargs.get("anchors")
    assert anchors is not None, "expected anchors= kwarg on generate_html_viewer"
    assert isinstance(anchors, dict)
    for view_name in VIEW_TO_ARTIFACT:
        assert view_name in anchors, f"missing anchor for view {view_name!r}"
        assert isinstance(anchors[view_name], SliceAnchor)
        assert anchors[view_name].view_name == view_name
