"""G2 regression: v3 viewer render is deterministic to the merged model.

Guards `scripts/build_v3_viewer.py` against reintroducing nondeterminism
(datetime.now, hash-seeded dict order, unsorted set iteration, etc.).

The build is invoked as a subprocess with varying PYTHONHASHSEED values;
outputs must be byte-identical across seeds.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILDER = REPO_ROOT / "scripts" / "build_v3_viewer.py"
MODEL = REPO_ROOT / ".architecture-model.v3.yaml"
OUT_HTML = REPO_ROOT / ".architecture" / "viewers" / "v3_viewer.html"
OUT_JSON = REPO_ROOT / ".architecture" / "viewers" / "v3_viewer_data.json"


def _build(hashseed: str, out_dir: Path) -> tuple[bytes, bytes]:
    """Run the builder with a given PYTHONHASHSEED, capture outputs."""
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = hashseed
    # Preserve any existing outputs before overwrite.
    saved_html = OUT_HTML.read_bytes() if OUT_HTML.exists() else None
    saved_json = OUT_JSON.read_bytes() if OUT_JSON.exists() else None
    try:
        result = subprocess.run(
            [sys.executable, str(BUILDER)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"builder failed (seed={hashseed}): "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        html = OUT_HTML.read_bytes()
        json_bytes = OUT_JSON.read_bytes()
    finally:
        # Restore any pre-existing outputs so this test never leaves
        # a modified working tree on failure.
        if saved_html is not None:
            OUT_HTML.write_bytes(saved_html)
        if saved_json is not None:
            OUT_JSON.write_bytes(saved_json)
    return html, json_bytes


@pytest.mark.skipif(
    not MODEL.exists(),
    reason="v3 model must exist (run pipeline_v3 first)",
)
def test_v3_viewer_deterministic_across_hashseeds(tmp_path: Path) -> None:
    """Two builds with different PYTHONHASHSEED produce byte-identical outputs."""
    html_a, json_a = _build("1", tmp_path)
    html_b, json_b = _build("42", tmp_path)
    html_c, json_c = _build("999999", tmp_path)

    # Byte-identical.
    assert html_a == html_b == html_c, (
        f"v3_viewer.html varies across hash seeds\n"
        f"  seed=1     sha256={hashlib.sha256(html_a).hexdigest()}\n"
        f"  seed=42    sha256={hashlib.sha256(html_b).hexdigest()}\n"
        f"  seed=99... sha256={hashlib.sha256(html_c).hexdigest()}"
    )
    assert json_a == json_b == json_c, (
        f"v3_viewer_data.json varies across hash seeds\n"
        f"  seed=1     sha256={hashlib.sha256(json_a).hexdigest()}\n"
        f"  seed=42    sha256={hashlib.sha256(json_b).hexdigest()}\n"
        f"  seed=99... sha256={hashlib.sha256(json_c).hexdigest()}"
    )


@pytest.mark.skipif(
    not MODEL.exists(),
    reason="v3 model must exist (run pipeline_v3 first)",
)
def test_v3_viewer_deterministic_across_runs(tmp_path: Path) -> None:
    """Two builds in identical environment produce byte-identical outputs."""
    html_a, json_a = _build("0", tmp_path)
    html_b, json_b = _build("0", tmp_path)
    assert html_a == html_b, "v3_viewer.html not stable across identical runs"
    assert json_a == json_b, (
        "v3_viewer_data.json not stable across identical runs"
    )
