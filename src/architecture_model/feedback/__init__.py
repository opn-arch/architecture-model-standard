"""Append-only feedback journals for lifecycle events.

The ``feedback`` subpackage owns three JSONL journals under
``<repo>/.architecture/``:

* ``gates.jsonl`` — one line per :class:`~architecture_model.feedback.gates.GateEvent`
  (Task 15).
* ``drift.jsonl`` — one line per :class:`~architecture_model.feedback.drift.DriftSnapshot`
  (Task 16).
* ``test_results.jsonl`` — one line per :class:`~architecture_model.feedback.test_results.TestResultBatch`
  (Task 17).

All writers are append-only and atomic-safe (write to a temp file in the
same directory, then rename over the target — POSIX rename is atomic on
the same filesystem). Journals are diagnostic, not authoritative: callers
must not fail user-visible operations if a journal write raises.
"""

__all__: list[str] = []
