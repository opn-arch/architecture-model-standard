"""Test that generate_manifest produces deterministic output across processes."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


def test_manifest_determinism_across_processes(tmp_path: Path):
    """Run generate_manifest in 5 separate subprocesses and assert identical JSON."""
    # Create a minimal project with multiple files and return type annotations
    pkg = tmp_path / "mypackage"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    (pkg / "alpha.py").write_text(textwrap.dedent("""\
        def get_names() -> list:
            return []

        def get_count() -> int:
            return 0

        def get_label() -> str:
            return ""

        def get_flag() -> bool:
            return True

        def get_mapping() -> dict:
            return {}
    """))

    (pkg / "beta.py").write_text(textwrap.dedent("""\
        def fetch_data() -> dict:
            return {}

        def fetch_items() -> list:
            return []

        def fetch_status() -> str:
            return "ok"

        def fetch_count() -> int:
            return 0

        def fetch_flag() -> bool:
            return False
    """))

    script = textwrap.dedent(f"""\
        import json, sys
        sys.path.insert(0, {str(tmp_path)!r})
        from pathlib import Path
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(Path({str(tmp_path)!r}))
        d = manifest.to_dict()
        d.pop("generated_at", None)
        print(json.dumps(d, sort_keys=True))
    """)

    results = []
    for i in range(5):
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env={"PATH": "", "PYTHONHASHSEED": str(i * 12345)},
        )
        assert proc.returncode == 0, f"Run {i} failed: {proc.stderr}"
        results.append(proc.stdout.strip())

    # All 5 runs must produce identical output
    for i, result in enumerate(results[1:], 1):
        assert result == results[0], (
            f"Run {i} differs from run 0.\n"
            f"Run 0: {results[0][:200]}\n"
            f"Run {i}: {result[:200]}"
        )
