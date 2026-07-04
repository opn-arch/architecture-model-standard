"""Tests for oracle performance tracking store."""

import pytest
from architecture_model.training.oracle_performance import (
    OraclePerformanceStore,
    OracleResult,
)


class TestOraclePerformanceStore:
    def test_record_and_count(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        assert store.count() == 0
        store.record(OracleResult(
            repo_url="https://github.com/test/a",
            prompt_variant="v1",
            coverage_score=0.85,
            validator_score=92.0,
            iteration=1,
        ))
        assert store.count() == 1

    def test_get_poor_extractions(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        store.record(OracleResult("repo-a", "v1", 0.9, 95.0, 1))
        store.record(OracleResult("repo-b", "v1", 0.4, 70.0, 1))
        store.record(OracleResult("repo-c", "v1", 0.3, 60.0, 1))
        store.record(OracleResult("repo-d", "v1", 0.8, 90.0, 1))

        poor = store.get_poor_extractions(threshold=0.7, limit=3)
        assert len(poor) == 2
        assert poor[0].coverage_score <= 0.4  # worst first

    def test_get_average_coverage(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        store.record(OracleResult("a", "v1", 0.8, 90.0, 1))
        store.record(OracleResult("b", "v1", 0.6, 80.0, 1))
        avg = store.get_average_coverage()
        assert avg == pytest.approx(0.7, abs=0.01)

    def test_count_since_iteration(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        store.record(OracleResult("a", "v1", 0.8, 90.0, 1))
        store.record(OracleResult("b", "v1", 0.6, 80.0, 2))
        store.record(OracleResult("c", "v1", 0.7, 85.0, 2))
        assert store.count_since_iteration(2) == 2

    def test_get_high_scoring(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        store.record(OracleResult("a", "v1", 0.9, 95.0, 1))
        store.record(OracleResult("b", "v1", 0.5, 70.0, 1))
        store.record(OracleResult("c", "v1", 0.85, 90.0, 1))

        high = store.get_high_scoring(threshold=0.8, limit=10)
        assert len(high) == 2
        assert all(h["coverage_score"] >= 0.8 for h in high)

    def test_empty_store(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        assert store.get_poor_extractions() == []
        assert store.get_average_coverage() == 0.0
        assert store.get_high_scoring() == []
