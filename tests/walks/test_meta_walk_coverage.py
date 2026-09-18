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
    report = audit_walk_coverage(tmp_path, model)
    assert isinstance(report, CoverageReport)
    verdicts = {c.subject: c.verdict for c in report.cards}
    assert verdicts["CAP-WK.foo"] == "covered"
    assert verdicts["CAP-WK.bar"] == "uncovered"
    assert len(report.uncovered) == 1


def test_dangling_ref_flagged(tmp_path):
    _write_walk(tmp_path, "phantom", ["CAP-WK.phantom"])
    model = {"entities": {"capabilities": [{"id": "CAP-WK.real"}]}}
    report = audit_walk_coverage(tmp_path, model)
    dangling = report.dangling
    assert len(dangling) == 1
    assert dangling[0].subject == "CAP-WK.phantom"
    assert dangling[0].walks == ("WALK-phantom",)


def test_non_cap_wk_audits_not_dangling(tmp_path):
    """Walks legitimately audit CAP-PB / CAP-SL / CAP-DF; these are not dangling."""
    _write_walk(tmp_path, "cross", ["CAP-WK.foo", "CAP-PB"])
    model = {"entities": {"capabilities": [{"id": "CAP-WK.foo"}]}}
    report = audit_walk_coverage(tmp_path, model)
    assert report.dangling == ()


def test_duplicate_walk_flagged(tmp_path):
    _write_walk(tmp_path, "one", ["CAP-WK.shared"])
    _write_walk(tmp_path, "two", ["CAP-WK.shared"])
    model = {"entities": {"capabilities": [{"id": "CAP-WK.shared"}]}}
    report = audit_walk_coverage(tmp_path, model)
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
    report = audit_walk_coverage(tmp_path, model)
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
    """The two Part-7 additions must both find matching walks."""
    report = audit_walk_coverage(WALKS_DIR, real_model)
    covered = {c.subject for c in report.cards if c.verdict == "covered"}
    assert "CAP-WK.meta-coverage" not in covered  # scanner is Python-only, no walk file
    assert "CAP-WK.attribute-completeness" in covered


def test_real_repo_report_envelope_shape(real_model):
    report = audit_walk_coverage(WALKS_DIR, real_model)
    d = report.to_dict()
    assert d["walk_id"] == "META-walk-coverage"
    assert d["audits"] == ["CAP-WK.meta-coverage"]
    assert isinstance(d["cards"], list)
    assert all("subject" in c and "verdict" in c for c in d["cards"])
