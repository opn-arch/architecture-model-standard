"""SQLite-backed store for MPC training examples."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TrainingExample:
    """A single training example for architecture extraction."""

    repo_url: str
    repo_sha: str
    code_context: str
    local_output: str
    iteration: int
    metadata: dict = field(default_factory=dict)
    oracle_output: Optional[str] = None
    loss_vector: Optional[dict] = None
    id: Optional[int] = None
    created_at: Optional[str] = None


class DatasetStore:
    """SQLite-backed store for training examples and run metadata."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS training_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_url TEXT NOT NULL,
                repo_sha TEXT NOT NULL,
                code_context TEXT NOT NULL,
                local_output TEXT NOT NULL,
                oracle_output TEXT,
                loss_vector TEXT,
                iteration INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS training_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                base_model TEXT NOT NULL,
                lora_path TEXT NOT NULL,
                examples_used INTEGER NOT NULL,
                final_loss REAL,
                pareto_front TEXT
            );

            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                chosen TEXT NOT NULL,
                rejected TEXT NOT NULL,
                margin REAL NOT NULL,
                iteration INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self._conn.commit()

    def save(self, example: TrainingExample) -> int:
        """Insert a training example and return its ID."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """
            INSERT INTO training_examples
                (repo_url, repo_sha, code_context, local_output,
                 oracle_output, loss_vector, iteration, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                example.repo_url,
                example.repo_sha,
                example.code_context,
                example.local_output,
                example.oracle_output,
                json.dumps(example.loss_vector) if example.loss_vector else None,
                example.iteration,
                now,
                json.dumps(example.metadata),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def get(self, example_id: int) -> TrainingExample:
        """Retrieve a training example by ID."""
        row = self._conn.execute(
            "SELECT * FROM training_examples WHERE id = ?", (example_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"No training example with id={example_id}")
        return self._row_to_example(row)

    def update_loss(self, example_id: int, loss_vector: dict) -> None:
        """Update the loss vector for an example."""
        self._conn.execute(
            "UPDATE training_examples SET loss_vector = ? WHERE id = ?",
            (json.dumps(loss_vector), example_id),
        )
        self._conn.commit()

    def query(
        self,
        iteration: Optional[int] = None,
        has_oracle: Optional[bool] = None,
    ) -> list[TrainingExample]:
        """Filter examples by iteration and/or oracle presence."""
        clauses: list[str] = []
        params: list = []

        if iteration is not None:
            clauses.append("iteration = ?")
            params.append(iteration)

        if has_oracle is True:
            clauses.append("oracle_output IS NOT NULL")
        elif has_oracle is False:
            clauses.append("oracle_output IS NULL")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM training_examples {where}", params
        ).fetchall()
        return [self._row_to_example(r) for r in rows]

    def count(self) -> int:
        """Return total number of training examples."""
        row = self._conn.execute("SELECT COUNT(*) FROM training_examples").fetchone()
        return row[0]

    def new_examples_since_last_train(self) -> int:
        """Count oracle-validated examples added since the last training run."""
        last_run = self._conn.execute(
            "SELECT started_at FROM training_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if last_run is None:
            # No training runs yet — count all oracle-validated examples
            row = self._conn.execute(
                "SELECT COUNT(*) FROM training_examples WHERE oracle_output IS NOT NULL"
            ).fetchone()
        else:
            row = self._conn.execute(
                """SELECT COUNT(*) FROM training_examples
                   WHERE oracle_output IS NOT NULL AND created_at > ?""",
                (last_run["started_at"],),
            ).fetchone()
        return row[0]

    def record_training_run(
        self, base_model: str, lora_path: str, examples_used: int
    ) -> int:
        """Log a training run. Returns run ID."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """
            INSERT INTO training_runs (started_at, base_model, lora_path, examples_used)
            VALUES (?, ?, ?, ?)
            """,
            (now, base_model, lora_path, examples_used),
        )
        self._conn.commit()
        return cur.lastrowid

    def export_for_training(self) -> list[dict]:
        """Export oracle-validated examples in instruction-tuning format."""
        rows = self._conn.execute(
            "SELECT * FROM training_examples WHERE oracle_output IS NOT NULL"
        ).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "instruction": "Analyze the following code and describe its architecture.",
                    "input": row["code_context"],
                    "output": row["oracle_output"],
                }
            )
        return results

    def export_weighted(self) -> list[dict]:
        """Export training examples with sample_weight based on inverse loss.

        Weight formula: 1.0 + (1.0 - structural_accuracy) * 2.0
        Range: [1.0, 3.0] — harder examples get more gradient contribution.
        """
        rows = self._conn.execute(
            "SELECT * FROM training_examples WHERE oracle_output IS NOT NULL"
        ).fetchall()
        results = []
        for row in rows:
            loss_raw = row["loss_vector"]
            if loss_raw:
                loss = json.loads(loss_raw)
            else:
                loss = {}
            acc = loss.get("structural_accuracy", 0.5)
            results.append(
                {
                    "instruction": "Analyze the following code and describe its architecture.",
                    "input": row["code_context"],
                    "output": row["oracle_output"],
                    "loss_vector": loss or None,
                    "sample_weight": 1.0 + (1.0 - acc) * 2.0,
                }
            )
        return results

    def save_preference(
        self, prompt: str, chosen: str, rejected: str, margin: float, iteration: int
    ) -> None:
        """Save a DPO preference pair (chosen=oracle output, rejected=surrogate output)."""
        self._conn.execute(
            "INSERT INTO preferences (prompt, chosen, rejected, margin, iteration) VALUES (?, ?, ?, ?, ?)",
            (prompt, chosen, rejected, margin, iteration),
        )
        self._conn.commit()

    def export_preferences(self) -> list[dict]:
        """Export preference pairs for DPO training."""
        rows = self._conn.execute(
            "SELECT prompt, chosen, rejected FROM preferences"
        ).fetchall()
        return [{"prompt": r[0], "chosen": r[1], "rejected": r[2]} for r in rows]

    def count_preferences(self) -> int:
        """Return total number of preference pairs."""
        row = self._conn.execute("SELECT COUNT(*) FROM preferences").fetchone()
        return row[0]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def _row_to_example(self, row: sqlite3.Row) -> TrainingExample:
        """Convert a database row to a TrainingExample."""
        loss_raw = row["loss_vector"]
        return TrainingExample(
            id=row["id"],
            repo_url=row["repo_url"],
            repo_sha=row["repo_sha"],
            code_context=row["code_context"],
            local_output=row["local_output"],
            oracle_output=row["oracle_output"],
            loss_vector=json.loads(loss_raw) if loss_raw else None,
            iteration=row["iteration"],
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
        )
