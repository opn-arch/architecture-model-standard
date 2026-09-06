"""Test wrapper for the SI&L decorator coverage check (DoD step 6).

Ensures ``scripts/apply_sil_decorators.py --check`` stays green in CI without
requiring a separate step. If any expected instrumentation site loses its
``@instrumented(...)`` decorator or its component_id drifts, this fails.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1].parent / "scripts" / "apply_sil_decorators.py"


def _load_coverage():
    if "apply_sil_decorators" in sys.modules:
        return sys.modules["apply_sil_decorators"]
    spec = importlib.util.spec_from_file_location("apply_sil_decorators", SCRIPT)
    assert spec and spec.loader, f"cannot load {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve its own __module__.
    sys.modules["apply_sil_decorators"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_apply_sil_decorators_check_passes():
    """All 19 expected SI&L sites (10 stages + 6 renderers + 3 validators) must be present."""
    coverage = _load_coverage()
    rc = coverage.run(check_mode=True)
    assert rc == 0, "SI&L decorator coverage regressed — see scripts/apply_sil_decorators.py"


def test_expected_site_count():
    """Regression guard: keep the expected-count anchor from the plan visible."""
    coverage = _load_coverage()
    # 10 pipeline stages + 6 renderers + 3 validators = 19
    assert len(coverage.EXPECTED) == 19
