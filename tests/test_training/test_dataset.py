"""Tests for training dataset store."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from architecture_model.training.dataset import DatasetStore, TrainingExample


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_dataset.db")


@pytest.fixture
def store(db_path):
    """Provide a DatasetStore instance."""
    s = DatasetStore(db_path)
    yield s
    s.close()


@pytest.fixture
def sample_example():
    """Provide a minimal TrainingExample."""
    return TrainingExample(
        repo_url="https://github.com/example/repo",
        repo_sha="abc123",
        code_context="def hello(): pass",
        local_output="Function hello with no body",
        iteration=1,
        metadata={"source": "test"},
    )


class TestStoreCreation:
    def test_store_creates_db(self, db_path):
        """DB file exists after init."""
        store = DatasetStore(db_path)
        assert os.path.exists(db_path)
        store.close()


class TestSaveAndRetrieve:
    def test_save_and_retrieve_example(self, store, sample_example):
        """Round-trip save/get preserves all fields."""
        example_id = store.save(sample_example)
        assert isinstance(example_id, int)
        assert example_id > 0

        retrieved = store.get(example_id)
        assert retrieved.repo_url == sample_example.repo_url
        assert retrieved.repo_sha == sample_example.repo_sha
        assert retrieved.code_context == sample_example.code_context
        assert retrieved.local_output == sample_example.local_output
        assert retrieved.iteration == sample_example.iteration
        assert retrieved.metadata == sample_example.metadata
        assert retrieved.oracle_output is None
        assert retrieved.loss_vector is None
        assert retrieved.id == example_id
        assert retrieved.created_at is not None

    def test_save_with_oracle_output(self, store):
        """Save with oracle output and loss vector."""
        example = TrainingExample(
            repo_url="https://github.com/example/repo",
            repo_sha="def456",
            code_context="class Foo: pass",
            local_output="Class Foo identified",
            oracle_output="Class Foo: singleton pattern, manages state",
            loss_vector={"accuracy": 0.3, "completeness": 0.5},
            iteration=2,
            metadata={"model": "llama3"},
        )
        example_id = store.save(example)
        retrieved = store.get(example_id)

        assert retrieved.oracle_output == "Class Foo: singleton pattern, manages state"
        assert retrieved.loss_vector == {"accuracy": 0.3, "completeness": 0.5}


class TestUpdateLoss:
    def test_update_loss(self, store, sample_example):
        """Update loss vector after save."""
        example_id = store.save(sample_example)
        loss = {"accuracy": 0.8, "completeness": 0.6, "style": 0.9}
        store.update_loss(example_id, loss)

        retrieved = store.get(example_id)
        assert retrieved.loss_vector == loss


class TestQuery:
    def test_query_by_iteration(self, store):
        """Filter by iteration."""
        for i in range(1, 4):
            ex = TrainingExample(
                repo_url="https://github.com/example/repo",
                repo_sha=f"sha{i}",
                code_context=f"context {i}",
                local_output=f"output {i}",
                iteration=i,
                metadata={},
            )
            store.save(ex)

        results = store.query(iteration=2)
        assert len(results) == 1
        assert results[0].iteration == 2
        assert results[0].repo_sha == "sha2"

    def test_query_has_oracle(self, store):
        """Filter by oracle presence."""
        # Example without oracle
        ex1 = TrainingExample(
            repo_url="https://github.com/example/repo",
            repo_sha="sha1",
            code_context="ctx1",
            local_output="out1",
            iteration=1,
            metadata={},
        )
        # Example with oracle
        ex2 = TrainingExample(
            repo_url="https://github.com/example/repo",
            repo_sha="sha2",
            code_context="ctx2",
            local_output="out2",
            oracle_output="oracle out2",
            iteration=1,
            metadata={},
        )
        store.save(ex1)
        store.save(ex2)

        with_oracle = store.query(has_oracle=True)
        assert len(with_oracle) == 1
        assert with_oracle[0].oracle_output == "oracle out2"

        without_oracle = store.query(has_oracle=False)
        assert len(without_oracle) == 1
        assert without_oracle[0].oracle_output is None


class TestTrainingIntegration:
    def test_count_new_since_last_train(self, store):
        """Counts oracle-validated examples since last training run."""
        # Add oracle-validated examples
        for i in range(3):
            ex = TrainingExample(
                repo_url="https://github.com/example/repo",
                repo_sha=f"sha{i}",
                code_context=f"ctx{i}",
                local_output=f"out{i}",
                oracle_output=f"oracle{i}",
                iteration=1,
                metadata={},
            )
            store.save(ex)

        assert store.new_examples_since_last_train() == 3

        # Record a training run — should reset count
        store.record_training_run(
            base_model="llama3-8b",
            lora_path="/path/to/lora",
            examples_used=3,
        )

        assert store.new_examples_since_last_train() == 0

        # Add more oracle-validated examples
        ex = TrainingExample(
            repo_url="https://github.com/example/repo",
            repo_sha="sha_new",
            code_context="ctx_new",
            local_output="out_new",
            oracle_output="oracle_new",
            iteration=2,
            metadata={},
        )
        store.save(ex)

        assert store.new_examples_since_last_train() == 1

    def test_export_for_training(self, store):
        """Only oracle-validated examples exported, correct format."""
        # Without oracle — should not appear in export
        ex1 = TrainingExample(
            repo_url="https://github.com/example/repo",
            repo_sha="sha1",
            code_context="def foo(): pass",
            local_output="function foo",
            iteration=1,
            metadata={},
        )
        # With oracle — should appear
        ex2 = TrainingExample(
            repo_url="https://github.com/example/repo",
            repo_sha="sha2",
            code_context="class Bar: pass",
            local_output="class Bar",
            oracle_output="class Bar implements observer pattern",
            iteration=1,
            metadata={},
        )
        store.save(ex1)
        store.save(ex2)

        exported = store.export_for_training()
        assert len(exported) == 1
        item = exported[0]
        assert "instruction" in item
        assert "input" in item
        assert "output" in item
        assert item["input"] == "class Bar: pass"
        assert item["output"] == "class Bar implements observer pattern"

    def test_record_training_run(self, store):
        """Logs run and resets new count."""
        # Add oracle examples
        for i in range(5):
            ex = TrainingExample(
                repo_url="https://github.com/example/repo",
                repo_sha=f"sha{i}",
                code_context=f"ctx{i}",
                local_output=f"out{i}",
                oracle_output=f"oracle{i}",
                iteration=1,
                metadata={},
            )
            store.save(ex)

        assert store.new_examples_since_last_train() == 5

        run_id = store.record_training_run(
            base_model="llama3-8b",
            lora_path="/models/lora_v1",
            examples_used=5,
        )

        assert isinstance(run_id, int)
        assert run_id > 0
        # After recording, new count resets
        assert store.new_examples_since_last_train() == 0
