"""Tests for :mod:`architecture_model.feedback.junit_ingest` (Phase 2 Task 17)."""
from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.feedback.junit_ingest import ingest_junit


_SIMPLE_SUITE = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="ams-unit" tests="4" failures="1" errors="0" skipped="1" time="3.25">
  <testcase classname="pkg.test_a" name="test_pass_1" time="0.1"/>
  <testcase classname="pkg.test_a" name="test_pass_2" time="0.2"/>
  <testcase classname="pkg.test_b" name="test_fail_1" time="1.0">
    <failure message="assert 1 == 2" type="AssertionError">Traceback...</failure>
  </testcase>
  <testcase classname="pkg.test_c" name="test_skip_1" time="0.0">
    <skipped/>
  </testcase>
</testsuite>
"""


_WRAPPED_SUITES = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="s1" tests="2" failures="1" errors="0" skipped="0" time="1.0">
    <testcase classname="p" name="ok"/>
    <testcase classname="p" name="bad">
      <failure message="boom"/>
    </testcase>
  </testsuite>
  <testsuite name="s2" tests="1" failures="0" errors="1" skipped="0" time="0.5">
    <testcase classname="q" name="broken">
      <error message="segfault"/>
    </testcase>
  </testsuite>
</testsuites>
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


def test_simple_suite_counters(tmp_path):
    path = _write(tmp_path, "junit.xml", _SIMPLE_SUITE)
    batch = ingest_junit(path)
    assert batch.suite == "ams-unit"
    assert batch.total == 4
    assert batch.failed == 1
    assert batch.skipped == 1
    assert batch.passed == 2  # 4 - 1 - 1
    assert batch.duration_s == pytest.approx(3.25)


def test_simple_suite_failure_extracted(tmp_path):
    path = _write(tmp_path, "junit.xml", _SIMPLE_SUITE)
    batch = ingest_junit(path)
    assert len(batch.failures) == 1
    f = batch.failures[0]
    assert f.nodeid == "pkg.test_b::test_fail_1"
    assert f.message == "assert 1 == 2"


def test_wrapped_testsuites_summed(tmp_path):
    path = _write(tmp_path, "junit.xml", _WRAPPED_SUITES)
    batch = ingest_junit(path)
    assert batch.suite == "s1"  # first testsuite name
    assert batch.total == 3
    assert batch.failed == 2  # 1 failure + 1 error
    assert batch.skipped == 0
    assert batch.passed == 1
    assert len(batch.failures) == 2
    assert batch.failures[0].nodeid == "p::bad"
    assert batch.failures[1].nodeid == "q::broken"


def test_suite_override(tmp_path):
    path = _write(tmp_path, "junit.xml", _SIMPLE_SUITE)
    batch = ingest_junit(path, suite="custom-name")
    assert batch.suite == "custom-name"


def test_timestamp_is_iso_utc(tmp_path):
    path = _write(tmp_path, "junit.xml", _SIMPLE_SUITE)
    batch = ingest_junit(path)
    # ISO-8601 UTC ends with +00:00 or Z.
    assert batch.timestamp
    assert batch.timestamp.endswith("+00:00") or batch.timestamp.endswith("Z")


def test_missing_attributes_default_to_zero(tmp_path):
    minimal = """<?xml version="1.0"?>
<testsuite name="min">
  <testcase classname="p" name="one"/>
</testsuite>
"""
    path = _write(tmp_path, "junit.xml", minimal)
    batch = ingest_junit(path)
    assert batch.total == 0
    assert batch.failed == 0
    assert batch.skipped == 0
    assert batch.passed == 0
    assert batch.duration_s == 0.0


def test_error_child_counted_as_failure(tmp_path):
    xml = """<?xml version="1.0"?>
<testsuite name="s" tests="1" failures="0" errors="1" time="0.1">
  <testcase classname="p" name="bad">
    <error message="import failed"/>
  </testcase>
</testsuite>
"""
    path = _write(tmp_path, "junit.xml", xml)
    batch = ingest_junit(path)
    assert batch.failed == 1
    assert batch.failures[0].message == "import failed"


def test_message_falls_back_to_child_text(tmp_path):
    xml = """<?xml version="1.0"?>
<testsuite name="s" tests="1" failures="1" time="0.1">
  <testcase classname="p" name="bad">
    <failure>First traceback line
Second line</failure>
  </testcase>
</testsuite>
"""
    path = _write(tmp_path, "junit.xml", xml)
    batch = ingest_junit(path)
    assert batch.failures[0].message == "First traceback line"


def test_unrecognized_root_raises(tmp_path):
    xml = """<?xml version="1.0"?>
<something/>
"""
    path = _write(tmp_path, "junit.xml", xml)
    with pytest.raises(ValueError):
        ingest_junit(path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_junit(tmp_path / "does-not-exist.xml")


def test_skipped_child_element_counted(tmp_path):
    """Some dialects report skipped via child element only, no suite-level attr."""
    xml = """<?xml version="1.0"?>
<testsuite name="s" tests="2" time="0.1">
  <testcase classname="p" name="ok"/>
  <testcase classname="p" name="skip"><skipped/></testcase>
</testsuite>
"""
    path = _write(tmp_path, "junit.xml", xml)
    batch = ingest_junit(path)
    assert batch.skipped == 1
    assert batch.passed == 1  # 2 - 0 - 1
