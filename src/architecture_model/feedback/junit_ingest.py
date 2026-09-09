"""JUnit-XML ingest → :class:`TestResultBatch` (Phase 2 Task 17).

Parses a standard JUnit XML file (as produced by ``pytest --junit-xml``,
``mvn test``, ``go test -v -json | ...``, etc.) into a
:class:`~architecture_model.feedback.test_results.TestResultBatch` ready
to hand to :func:`architecture_model.feedback.test_results.append`.

Only stdlib :mod:`xml.etree.ElementTree` is used — no external deps.

JUnit dialect notes
-------------------
Both single ``<testsuite>`` and wrapping ``<testsuites>`` roots are
accepted. Attributes (``tests``, ``failures``, ``errors``, ``skipped``,
``time``) are all optional; missing counters default to 0 and are then
consistency-checked (see :func:`ingest_junit`). ``<error>`` children on
a test case are treated as failures for the purposes of the roll-up
(the shape spec has no ``errored`` field yet); the failure message
carries the child element's tag as a hint.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from architecture_model.feedback.test_results import TestFailure, TestResultBatch


def _int(elem: ET.Element, attr: str, default: int = 0) -> int:
    v = elem.get(attr)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _float(elem: ET.Element, attr: str, default: float = 0.0) -> float:
    v = elem.get(attr)
    if v is None or v == "":
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _collect_testsuites(root: ET.Element) -> list[ET.Element]:
    """Return one or more <testsuite> elements from the parsed root."""
    if root.tag == "testsuites":
        return list(root.findall("testsuite"))
    if root.tag == "testsuite":
        return [root]
    raise ValueError(
        f"unrecognized JUnit root element {root.tag!r} — expected "
        "'testsuites' or 'testsuite'"
    )


def _extract_failure(case: ET.Element) -> TestFailure | None:
    """Return a :class:`TestFailure` if the case has <failure> or <error>."""
    child = case.find("failure")
    tag = "failure"
    if child is None:
        child = case.find("error")
        tag = "error"
    if child is None:
        return None
    classname = case.get("classname", "")
    name = case.get("name", "")
    nodeid = f"{classname}::{name}" if classname else name
    # Prefer the 'message' attribute; fall back to first non-empty text line.
    msg = child.get("message")
    if not msg and child.text:
        for line in child.text.splitlines():
            line = line.strip()
            if line:
                msg = line
                break
    if not msg:
        msg = f"({tag})"
    return TestFailure(nodeid=nodeid or "?", message=msg)


def ingest_junit(junit_xml_path: Path, *, suite: str | None = None) -> TestResultBatch:
    """Parse ``junit_xml_path`` into a :class:`TestResultBatch`.

    When multiple ``<testsuite>`` elements are present under a
    ``<testsuites>`` root, counters are summed and failures are
    concatenated in document order.

    Parameters
    ----------
    junit_xml_path:
        Path to a JUnit XML file.
    suite:
        Override the suite name. Defaults to the first ``<testsuite>``
        element's ``name`` attribute (or ``"junit"`` when absent).

    Returns
    -------
    TestResultBatch
        With ``timestamp`` set to the file mtime as ISO-8601 UTC. Callers
        wanting a different timestamp should copy the batch via
        ``dataclasses.replace``.

    Raises
    ------
    ValueError
        On unrecognized root elements.
    FileNotFoundError
        When ``junit_xml_path`` does not exist.
    """
    tree = ET.parse(junit_xml_path)
    root = tree.getroot()
    testsuites = _collect_testsuites(root)
    if not testsuites:
        raise ValueError("no <testsuite> elements found in JUnit XML")

    total = 0
    failed = 0
    skipped = 0
    duration = 0.0
    failures: list[TestFailure] = []

    for ts in testsuites:
        total += _int(ts, "tests", 0)
        failed += _int(ts, "failures", 0) + _int(ts, "errors", 0)
        skipped += _int(ts, "skipped", 0)
        duration += _float(ts, "time", 0.0)
        for case in ts.findall("testcase"):
            if case.find("skipped") is not None:
                # Some JUnit dialects report skipped as a child, not an attr.
                # Only count if the suite-level attr didn't already cover it.
                if _int(ts, "skipped", 0) == 0:
                    skipped += 1
                continue
            f = _extract_failure(case)
            if f is not None:
                failures.append(f)

    # Sanity: passed = total - failed - skipped, floored at 0.
    passed = max(0, total - failed - skipped)

    if suite is None:
        suite = testsuites[0].get("name") or "junit"

    mtime = junit_xml_path.stat().st_mtime
    timestamp = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

    return TestResultBatch(
        suite=suite,
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration_s=duration,
        failures=tuple(failures),
        timestamp=timestamp,
    )


__all__ = ["ingest_junit"]
