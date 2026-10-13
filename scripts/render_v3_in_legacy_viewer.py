"""render_v3_in_legacy_viewer — v3 → adapter → 2.x HTML viewer.

Feeds the v3 model through the Phase 11 adapter
(:func:`architecture_model.pipeline_v3.adapters.legacy_pipeline.v3_to_legacy_model`)
and hands the result to the existing 2.x HTML viewer at
:func:`architecture_model.core.visualize.generate_html_viewer`.

The 2.x viewer drops v3-specific data (Promises, gap_type,
delivered_from) but gives the familiar box-and-arrow SE lens as a
comparison to the v3-native viewer at
``.architecture/viewers/v3_viewer.html``.

Usage::

    python scripts/render_v3_in_legacy_viewer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MODEL = REPO / ".architecture-model.v3.yaml"
OUT = REPO / ".architecture" / "viewers" / "legacy_viewer.html"


def main() -> None:
    if not MODEL.exists():
        print(f"error: {MODEL} not found — run pipeline_v3 first", file=sys.stderr)
        sys.exit(2)
    with open(MODEL, "r", encoding="utf-8") as fh:
        v3 = yaml.safe_load(fh)

    from architecture_model.pipeline_v3.adapters.legacy_pipeline import (
        v3_to_legacy_model,
    )
    from architecture_model.core.visualize import generate_html_viewer

    legacy = v3_to_legacy_model(v3)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    generate_html_viewer(
        legacy,
        OUT,
        title="AMS v3 (2.x-adapter lens)",
        repo_path=REPO,
        use_curation=False,
        include_docs=False,
        include_history=False,
    )
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(
        f"legacy shape: {len(legacy.entities.components)} components, "
        f"{len(legacy.relationships)} relationships (v3-native data dropped)"
    )
    print(f"open: file://{OUT}")


if __name__ == "__main__":
    main()
