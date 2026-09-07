"""HTML shell renderer for the interactive pipeline dashboard."""
from __future__ import annotations

import json

from architecture_model.sil.decorators import instrumented

from .pipeline_html_data import build

CONTENT_TYPE = "text/html; charset=utf-8"

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pipeline Dashboard</title>
  <link rel="stylesheet" href="assets/pipeline_dashboard/index.css">
</head>
<body>
  <main id="pipeline-root" data-view="pipeline-html"></main>
  <aside id="pipeline-drilldown" hidden></aside>
  <script id="pipeline-state" type="application/json">
{state}
  </script>
  <script src="assets/pipeline_dashboard/badges.js" defer></script>
  <script src="assets/pipeline_dashboard/drilldown.js" defer></script>
</body>
</html>
"""


@instrumented("renderer:pipeline-html")
def render_pipeline_html(*, materialized_slice, sil_store=None, **_ignored) -> str:
    """Render the HTML shell embedding the pipeline_state JSON."""
    data = build(materialized_slice, sil_store=sil_store)
    return _TEMPLATE.format(state=json.dumps(data, sort_keys=True, indent=2))


render = render_pipeline_html
__all__ = ["render", "render_pipeline_html", "CONTENT_TYPE"]
