"""Tests for few-shot example retrieval."""

import pytest
from unittest.mock import MagicMock
from architecture_model.training.oracle_few_shot import FewShotRetriever


class TestFewShotRetriever:
    def test_retrieve_returns_empty_when_no_examples(self, tmp_path):
        store = MagicMock()
        store.get_high_scoring = MagicMock(return_value=[])
        retriever = FewShotRetriever(store)
        examples = retriever.retrieve(manifest={}, k=3)
        assert examples == []

    def test_retrieve_returns_k_examples(self, tmp_path):
        store = MagicMock()
        store.get_high_scoring = MagicMock(return_value=[
            {"repo_url": "a", "code_context": "# a", "oracle_output": "model: a",
             "coverage_score": 0.9, "modules": 5},
            {"repo_url": "b", "code_context": "# b", "oracle_output": "model: b",
             "coverage_score": 0.85, "modules": 10},
            {"repo_url": "c", "code_context": "# c", "oracle_output": "model: c",
             "coverage_score": 0.95, "modules": 3},
        ])
        retriever = FewShotRetriever(store)
        examples = retriever.retrieve(manifest={"modules": [{}] * 5}, k=2)
        assert len(examples) <= 2

    def test_format_few_shot_section(self):
        store = MagicMock()
        store.get_high_scoring = MagicMock(return_value=[
            {"repo_url": "https://github.com/test/repo", "code_context": "class Foo: pass",
             "oracle_output": "entities:\n  components: []", "coverage_score": 0.9, "modules": 5},
        ])
        retriever = FewShotRetriever(store)
        section = retriever.format_section(manifest={"modules": [{}] * 5}, k=1)
        assert "Few-Shot" in section
        assert "entities:" in section
