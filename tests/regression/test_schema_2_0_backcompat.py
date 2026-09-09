"""Task 5 (Phase 2): schema 2.0 back-compat regression gate.

This is the single, load-bearing test that guarantees Phase 2's
schema 2.1 additions did not break existing 2.0 models. When it fails,
STOP — a 2.1 change has become non-additive.

Baseline captured 2026-09-08 against
``tests/fixtures/viewer-curation-model.yaml`` (the only true 2.0
fixture in the tree; ``tests/fixtures/lifecycle/**`` use 2.1.0 already,
and ``se_doc_model`` uses '2.1'):

- ``meta.schema_version`` parses as the string literal ``"2.0"``
- :func:`architecture_model.core.validator.validate_model` returns
  ``score == 94`` and ``is_valid is True``
- 15 issues at that score, no ERROR-severity issue (only WARNING/INFO)

If a new Phase 2 task tightens the parser or validator such that this
fixture's score changes or new ERROR issues appear, the fixture must
either be migrated (via Task 6's ``architecture-model migrate``) or
the Phase 2 change reworked to remain purely additive.
"""

from __future__ import annotations

from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "viewer-curation-model.yaml"


def test_schema_2_0_fixture_still_parses() -> None:
    """load_model succeeds and preserves the 2.0 schema_version literal."""
    model = load_model(FIXTURE)
    assert model.meta.schema_version == "2.0"


def test_schema_2_0_fixture_still_validates_at_baseline_score() -> None:
    """validate_model returns baseline score / validity captured on 2026-09-08.

    Score MUST NOT drop below 94; is_valid MUST remain True. A drop
    means Phase 2 additions leaked into the validator and rejected
    legitimate 2.0 content.
    """
    model = load_model(FIXTURE)
    result = validate_model(model)
    assert result.score == 94, f"score regressed: expected 94, got {result.score}"
    assert result.is_valid is True


def test_schema_2_0_fixture_no_error_severity_issues() -> None:
    """No issue in the 2.0 fixture may be ERROR severity."""
    model = load_model(FIXTURE)
    result = validate_model(model)
    errors = [i for i in result.issues if str(i.severity).upper().endswith("ERROR")]
    assert errors == [], f"unexpected ERROR issues on 2.0 fixture: {errors}"
