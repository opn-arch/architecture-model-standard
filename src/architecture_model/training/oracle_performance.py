"""SQLite store tracking oracle extraction performance over time."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OracleResult:
    """A single oracle extraction result."""

    repo_url: str
    prompt_variant: str
    coverage_score: float
    validator_score: float
    iteration: int
    uncovered_modules: Optional[str] = None
    uncovered_interfaces: Optional[str] = None
    created_at: Optional[str] = None


class OraclePerformanceStore:
    """SQLite store for oracle performance tracking."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS oracle_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_url TEXT NOT NULL,
                prompt_variant TEXT NOT NULL,
                coverage_score REAL NOT NULL,
                validator_score REAL NOT NULL,
                iteration INTEGER NOT NULL,
                uncovered_modules TEXT,
                uncovered_interfaces TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def record(self, result: OracleResult) -> None:
        """Record an oracle extraction result."""
        created_at = result.created_at or datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO oracle_results
               (repo_url, prompt_variant, coverage_score, validator_score,
                iteration, uncovered_modules, uncovered_interfaces, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.repo_url, result.prompt_variant, result.coverage_score,
             result.validator_score, result.iteration,
             result.uncovered_modules, result.uncovered_interfaces, created_at),
        )
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM oracle_results").fetchone()
        return row[0]

    def count_since_iteration(self, iteration: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM oracle_results WHERE iteration >= ?", (iteration,)
        ).fetchone()
        return row[0]

    def get_poor_extractions(self, threshold: float = 0.7, limit: int = 5) -> list[OracleResult]:
        """Get extractions with coverage below threshold, worst first."""
        rows = self._conn.execute(
            """SELECT * FROM oracle_results
               WHERE coverage_score < ?
               ORDER BY coverage_score ASC LIMIT ?""",
            (threshold, limit),
        ).fetchall()
        return [self._row_to_result(r) for r in rows]

    def get_high_scoring(self, threshold: float = 0.8, limit: int = 20) -> list[dict]:
        """Get high-scoring results for few-shot retrieval."""
        rows = self._conn.execute(
            """SELECT repo_url, coverage_score, validator_score FROM oracle_results
               WHERE coverage_score >= ?
               ORDER BY coverage_score DESC LIMIT ?""",
            (threshold, limit),
        ).fetchall()
        return [{"repo_url": r["repo_url"], "coverage_score": r["coverage_score"],
                 "validator_score": r["validator_score"]} for r in rows]

    def get_average_coverage(self) -> float:
        row = self._conn.execute("SELECT AVG(coverage_score) FROM oracle_results").fetchone()
        return row[0] or 0.0

    def _row_to_result(self, row) -> OracleResult:
        return OracleResult(
            repo_url=row["repo_url"],
            prompt_variant=row["prompt_variant"],
            coverage_score=row["coverage_score"],
            validator_score=row["validator_score"],
            iteration=row["iteration"],
            uncovered_modules=row["uncovered_modules"],
            uncovered_interfaces=row["uncovered_interfaces"],
            created_at=row["created_at"],
        )
