"""Tests for architecture_model.walks.meta.walk_coverage.

Exercises the meta-walk that audits WalkSpec-vs-CAP-WK coverage.
Uses both synthetic fixtures (for edge cases) and the real repo
model + walks dir (for integration signal).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.walks.meta import (
    CoverageReport,
    audit_walk_coverage,
    collect_cap_wk_subcaps,
)
from architecture_model.walks.meta.walk_coverage import (
    discover_python_meta_walks,
)

REPO = Path(__file__).resolve().parents[2]
WALKS_DIR = REPO / ".architecture/model/walks"
MODEL_PATH = REPO / ".architecture/model/capabilities.v3.yaml"


@pytest.fixture(scope="module")
def real_model() -> dict:
    with MODEL_PATH.open() as f:
        return yaml.safe_load(f)


# ---------- collect_cap_wk_subcaps -----------------------------------------


def test_collect_from_entities_shape():
    model = {
        "entities": {
            "capabilities": [
                {"id": "CAP-WK"},
                {"id": "CAP-WK.direction-lint"},
                {"id": "CAP-WK.author"},
                {"id": "CAP-PB"},  # non-WK — must be excluded
            ]
        }
    }
    assert collect_cap_wk_subcaps(model) == {
        "CAP-WK.direction-lint",
        "CAP-WK.author",
    }


def test_umbrella_cap_wk_excluded():
    model = {"entities": {"capabilities": [{"id": "CAP-WK"}]}}
    assert collect_cap_wk_subcaps(model) == set()


def test_collect_from_bucket_shape():
    model = {
        "buckets": [
            {"capabilities": [{"id": "CAP-WK.foo"}, {"id": "CAP-WK.bar"}]}
        ]
    }
    assert collect_cap_wk_subcaps(model) == {"CAP-WK.foo", "CAP-WK.bar"}


def test_malformed_entities_returns_empty():
    assert collect_cap_wk_subcaps({}) == set()
    assert collect_cap_wk_subcaps({"entities": None}) == set()
    assert collect_cap_wk_subcaps({"entities": {"capabilities": "not-a-list"}}) == set()


def test_real_model_has_expected_subcaps(real_model):
    """The real capabilities.v3.yaml declares 13 CAP-WK.* sub-caps (post-Part 7)."""
    subcaps = collect_cap_wk_subcaps(real_model)
    assert "CAP-WK.meta-coverage" in subcaps
    assert "CAP-WK.attribute-completeness" in subcaps
    assert "CAP-WK.constraint-impact" in subcaps
    assert "CAP-WK.realization-skip" in subcaps
    assert "CAP-WK" not in subcaps
    # Umbrella + 13 sub-caps expected — assert lower bound to allow future growth.
    assert len(subcaps) >= 13


# ---------- audit_walk_coverage: synthetic scenarios -----------------------


def _write_walk(dir: Path, walk_id: str, audits: list[str]) -> None:
    (dir / f"{walk_id}.v3.yaml").write_text(
        yaml.safe_dump(
            {
                "walk": {
                    "id": f"WALK-{walk_id}",
                    "audits": audits,
                    "scope": {"kind": "capability"},
                }
            }
        )
    )


def _audit_synthetic(walks_dir: Path, model: dict) -> CoverageReport:
    """Wrapper: synthetic tests use an empty python_meta_dir so real repo
    Python meta-walks don't leak into isolated fixtures."""
    empty = walks_dir / "__no_py__"
    empty.mkdir(exist_ok=True)
    return audit_walk_coverage(walks_dir, model, python_meta_dir=empty)


def test_uncovered_subcap_flagged(tmp_path):
    _write_walk(tmp_path, "foo", ["CAP-WK.foo"])
    model = {
        "entities": {
            "capabilities": [
                {"id": "CAP-WK.foo"},
                {"id": "CAP-WK.bar"},  # no walk audits this
            ]
        }
    }
    report = _audit_synthetic(tmp_path, model)
    assert isinstance(report, CoverageReport)
    verdicts = {c.subject: c.verdict for c in report.cards}
    assert verdicts["CAP-WK.foo"] == "covered"
    assert verdicts["CAP-WK.bar"] == "uncovered"
    assert len(report.uncovered) == 1


def test_dangling_ref_flagged(tmp_path):
    _write_walk(tmp_path, "phantom", ["CAP-WK.phantom"])
    model = {"entities": {"capabilities": [{"id": "CAP-WK.real"}]}}
    report = _audit_synthetic(tmp_path, model)
    dangling = report.dangling
    assert len(dangling) == 1
    assert dangling[0].subject == "CAP-WK.phantom"
    assert dangling[0].walks == ("WALK-phantom",)


def test_non_cap_wk_audits_not_dangling(tmp_path):
    """Walks legitimately audit CAP-PB / CAP-SL / CAP-DF; these are not dangling."""
    _write_walk(tmp_path, "cross", ["CAP-WK.foo", "CAP-PB"])
    model = {"entities": {"capabilities": [{"id": "CAP-WK.foo"}]}}
    report = _audit_synthetic(tmp_path, model)
    assert report.dangling == ()


def test_duplicate_walk_flagged(tmp_path):
    _write_walk(tmp_path, "one", ["CAP-WK.shared"])
    _write_walk(tmp_path, "two", ["CAP-WK.shared"])
    model = {"entities": {"capabilities": [{"id": "CAP-WK.shared"}]}}
    report = _audit_synthetic(tmp_path, model)
    dup = [c for c in report.cards if c.verdict == "duplicate-walk"]
    assert len(dup) == 1
    assert dup[0].walks == ("WALK-one", "WALK-two")


def test_cards_sorted_by_severity(tmp_path):
    _write_walk(tmp_path, "phantom", ["CAP-WK.phantom"])  # dangling
    _write_walk(tmp_path, "covers", ["CAP-WK.a"])
    model = {
        "entities": {
            "capabilities": [
                {"id": "CAP-WK.a"},
                {"id": "CAP-WK.b"},  # uncovered
            ]
        }
    }
    report = _audit_synthetic(tmp_path, model)
    verdicts = [c.verdict for c in report.cards]
    # dangling first, then uncovered, then covered.
    assert verdicts.index("dangling-ref") < verdicts.index("uncovered")
    assert verdicts.index("uncovered") < verdicts.index("covered")


# ---------- audit_walk_coverage: integration against real repo -------------


def test_real_repo_no_dangling_refs(real_model):
    """Post-Part 7, every audited CAP-WK.* has a matching sub-cap in the model."""
    report = audit_walk_coverage(WALKS_DIR, real_model)
    assert report.dangling == (), (
        f"unexpected dangling audits: "
        f"{[(c.subject, c.walks) for c in report.dangling]}"
    )


def test_real_repo_covered_subcaps_include_meta(real_model):
    """Post-Part 9, meta-coverage AND attribute-completeness are both covered.

    Part 9 (L22) added Python meta-walk discovery, so
    ``CAP-WK.meta-coverage`` — which is realized by walk_coverage.py
    itself (a Python meta-walk, not a WalkSpec YAML) — now shows up as
    covered via ``META-walk_coverage``.
    """
    report = audit_walk_coverage(WALKS_DIR, real_model)
    covered = {c.subject for c in report.cards if c.verdict == "covered"}
    assert "CAP-WK.meta-coverage" in covered
    assert "CAP-WK.attribute-completeness" in covered


def test_real_repo_report_envelope_shape(real_model):
    report = audit_walk_coverage(WALKS_DIR, real_model)
    d = report.to_dict()
    assert d["walk_id"] == "META-walk-coverage"
    assert d["audits"] == ["CAP-WK.meta-coverage"]
    assert isinstance(d["cards"], list)
    assert all("subject" in c and "verdict" in c for c in d["cards"])


# ---------- Python meta-walk discovery (L22, Part 9) -----------------------


def test_discover_python_meta_walks_finds_marker(tmp_path):
    """A .py file whose docstring contains the marker is discovered."""
    (tmp_path / "example.py").write_text(
        '"""Example meta-walk. Realizes ``CAP-WK.example``."""\n'
    )
    found = discover_python_meta_walks(tmp_path)
    assert len(found) == 1
    assert found[0]["walk_id"] == "META-example"
    assert found[0]["audits"] == ["CAP-WK.example"]


def test_discover_python_meta_walks_multiline_marker(tmp_path):
    """Marker split across lines with whitespace still matches."""
    (tmp_path / "multi.py").write_text(
        '"""Docstring with newline before marker.\n\nRealizes\n``CAP-WK.multi``.\n"""\n'
    )
    found = discover_python_meta_walks(tmp_path)
    assert len(found) == 1
    assert found[0]["audits"] == ["CAP-WK.multi"]


def test_discover_python_meta_walks_skips_dunder(tmp_path):
    """__init__.py and other dunder files are skipped even if they carry a marker."""
    (tmp_path / "__init__.py").write_text(
        '"""Realizes ``CAP-WK.pkg``."""\n'
    )
    (tmp_path / "real.py").write_text(
        '"""Realizes ``CAP-WK.real``."""\n'
    )
    found = discover_python_meta_walks(tmp_path)
    walk_ids = {f["walk_id"] for f in found}
    assert walk_ids == {"META-real"}


def test_discover_python_meta_walks_ignores_missing_marker(tmp_path):
    """A .py file without the Realizes marker is silently ignored."""
    (tmp_path / "plain.py").write_text('"""No marker here."""\n')
    assert discover_python_meta_walks(tmp_path) == []


def test_discover_python_meta_walks_missing_dir_returns_empty(tmp_path):
    """Non-existent directory returns [] rather than raising."""
    assert discover_python_meta_walks(tmp_path / "does-not-exist") == []


def test_discover_python_meta_walks_dedupe_multiple_markers(tmp_path):
    """Duplicate markers within one docstring are deduplicated in-order."""
    (tmp_path / "twin.py").write_text(
        '"""Realizes ``CAP-WK.foo``. Also Realizes ``CAP-WK.foo``.\n'
        'And Realizes ``CAP-WK.bar``."""\n'
    )
    found = discover_python_meta_walks(tmp_path)
    assert found[0]["audits"] == ["CAP-WK.foo", "CAP-WK.bar"]


def test_discover_python_meta_walks_deterministic_order(tmp_path):
    """Discovery iterates files in sorted order."""
    (tmp_path / "zeta.py").write_text('"""Realizes ``CAP-WK.z``."""\n')
    (tmp_path / "alpha.py").write_text('"""Realizes ``CAP-WK.a``."""\n')
    (tmp_path / "mid.py").write_text('"""Realizes ``CAP-WK.m``."""\n')
    walk_ids = [f["walk_id"] for f in discover_python_meta_walks(tmp_path)]
    assert walk_ids == ["META-alpha", "META-mid", "META-zeta"]


def test_audit_with_python_meta_dir(tmp_path):
    """audit_walk_coverage integrates Python meta-walks via python_meta_dir."""
    walks_dir = tmp_path / "walks"
    py_dir = tmp_path / "py"
    walks_dir.mkdir()
    py_dir.mkdir()
    (py_dir / "linter.py").write_text('"""Realizes ``CAP-WK.linter``."""\n')
    model = {
        "entities": {
            "capabilities": [
                {"id": "CAP-WK.linter"},
                {"id": "CAP-WK.other"},
            ]
        }
    }
    report = audit_walk_coverage(walks_dir, model, python_meta_dir=py_dir)
    verdicts = {c.subject: c.verdict for c in report.cards}
    assert verdicts["CAP-WK.linter"] == "covered"
    assert verdicts["CAP-WK.other"] == "uncovered"
    linter_card = next(c for c in report.cards if c.subject == "CAP-WK.linter")
    assert linter_card.walks == ("META-linter",)


def test_real_repo_direction_lint_covered_by_python_meta_walk(real_model):
    """Part 9 covers CAP-WK.direction-lint via META-direction_lint."""
    report = audit_walk_coverage(WALKS_DIR, real_model)
    covered = {c.subject: c for c in report.cards if c.verdict == "covered"}
    assert "CAP-WK.direction-lint" in covered
    assert covered["CAP-WK.direction-lint"].walks == ("META-direction_lint",)


def test_real_repo_promotion_strict_covered(real_model):
    """Part 9's promotion-strict WalkSpec covers CAP-WK.promotion-strict."""
    report = audit_walk_coverage(WALKS_DIR, real_model)
    covered = {c.subject: c for c in report.cards if c.verdict == "covered"}
    assert "CAP-WK.promotion-strict" in covered
    assert covered["CAP-WK.promotion-strict"].walks == ("WALK-promotion-strict",)


def test_python_meta_walks_discovered_in_real_repo():
    """Discovery finds both shipped Python meta-walks in the real package."""
    meta_dir = REPO / "src/architecture_model/walks/meta"
    found = discover_python_meta_walks(meta_dir)
    walk_ids = {f["walk_id"] for f in found}
    assert "META-walk_coverage" in walk_ids
    assert "META-direction_lint" in walk_ids
