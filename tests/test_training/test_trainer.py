"""Tests for LoRA Trainer (HF PEFT integration + Ollama export)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from architecture_model.training.trainer import LoRATrainer


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestLoRATrainerInit:
    def test_default_params(self):
        """Default base_model, lora_r, lora_alpha are set correctly."""
        trainer = LoRATrainer()
        assert trainer.base_model == "Qwen/Qwen2.5-7B-Instruct"
        assert trainer.lora_r == 16
        assert trainer.lora_alpha == 32

    def test_custom_params(self):
        """Custom params override defaults."""
        trainer = LoRATrainer(
            base_model="meta-llama/Llama-2-7b-hf",
            lora_r=8,
            lora_alpha=16,
        )
        assert trainer.base_model == "meta-llama/Llama-2-7b-hf"
        assert trainer.lora_r == 8
        assert trainer.lora_alpha == 16


# ---------------------------------------------------------------------------
# prepare_dataset Tests
# ---------------------------------------------------------------------------


class TestPrepareDataset:
    @patch("architecture_model.training.trainer.HAS_DATASETS", True)
    @patch("architecture_model.training.trainer.Dataset")
    def test_tries_export_weighted_first(self, MockDataset):
        """prepare_dataset calls store.export_weighted() first."""
        trainer = LoRATrainer()
        store = MagicMock()
        store.export_weighted.return_value = [
            {
                "instruction": "Analyze the code.",
                "input": "def foo(): pass",
                "output": "A function foo.",
                "sample_weight": 2.0,
            }
        ]
        MockDataset.from_list.return_value = MagicMock()

        trainer.prepare_dataset(store)

        store.export_weighted.assert_called_once()
        store.export_for_training.assert_not_called()

    @patch("architecture_model.training.trainer.HAS_DATASETS", True)
    @patch("architecture_model.training.trainer.Dataset")
    def test_falls_back_to_export_for_training(self, MockDataset):
        """prepare_dataset falls back to export_for_training() when export_weighted() returns empty."""
        trainer = LoRATrainer()
        store = MagicMock()
        store.export_weighted.return_value = []
        store.export_for_training.return_value = [
            {
                "instruction": "Analyze the code.",
                "input": "def foo(): pass",
                "output": "A function foo.",
            }
        ]
        MockDataset.from_list.return_value = MagicMock()

        trainer.prepare_dataset(store)

        store.export_weighted.assert_called_once()
        store.export_for_training.assert_called_once()

    @patch("architecture_model.training.trainer.HAS_DATASETS", True)
    @patch("architecture_model.training.trainer.Dataset")
    def test_returns_dataset_with_correct_columns(self, MockDataset):
        """Returned dataset has instruction, input, output columns."""
        trainer = LoRATrainer()
        store = MagicMock()
        examples = [
            {
                "instruction": "Analyze the code.",
                "input": "def foo(): pass",
                "output": "A function foo.",
                "sample_weight": 1.5,
            },
            {
                "instruction": "Analyze the code.",
                "input": "class Bar: pass",
                "output": "A class Bar.",
                "sample_weight": 2.0,
            },
        ]
        store.export_weighted.return_value = examples

        # Mock Dataset.from_list to return an object with column_names
        mock_ds = MagicMock()
        mock_ds.column_names = ["instruction", "input", "output", "sample_weight"]
        MockDataset.from_list.return_value = mock_ds

        dataset = trainer.prepare_dataset(store)

        # Dataset should have the expected columns
        assert "instruction" in dataset.column_names
        assert "input" in dataset.column_names
        assert "output" in dataset.column_names
        assert "sample_weight" in dataset.column_names
        # Verify from_list was called with the correct data
        MockDataset.from_list.assert_called_once_with(examples)

    @patch("architecture_model.training.trainer.HAS_DATASETS", True)
    @patch("architecture_model.training.trainer.Dataset")
    def test_dataset_contains_all_examples(self, MockDataset):
        """Dataset.from_list is called with all exported examples."""
        trainer = LoRATrainer()
        store = MagicMock()
        examples = [
            {
                "instruction": f"Instruction {i}",
                "input": f"code {i}",
                "output": f"output {i}",
                "sample_weight": 1.0 + i * 0.5,
            }
            for i in range(5)
        ]
        store.export_weighted.return_value = examples

        mock_ds = MagicMock()
        mock_ds.__len__ = MagicMock(return_value=5)
        MockDataset.from_list.return_value = mock_ds

        dataset = trainer.prepare_dataset(store)

        # Verify all 5 examples were passed to from_list
        passed_examples = MockDataset.from_list.call_args[0][0]
        assert len(passed_examples) == 5

    @patch("architecture_model.training.trainer.HAS_DATASETS", True)
    @patch("architecture_model.training.trainer.Dataset")
    def test_dataset_preserves_content(self, MockDataset):
        """Data passed to Dataset.from_list matches store export."""
        trainer = LoRATrainer()
        store = MagicMock()
        store.export_weighted.return_value = [
            {
                "instruction": "Analyze the following code and describe its architecture.",
                "input": "class MyService:\n    def run(self): ...",
                "output": "MyService is a service component.",
                "sample_weight": 2.5,
            }
        ]
        MockDataset.from_list.return_value = MagicMock()

        trainer.prepare_dataset(store)

        passed_examples = MockDataset.from_list.call_args[0][0]
        assert passed_examples[0]["input"] == "class MyService:\n    def run(self): ..."
        assert passed_examples[0]["output"] == "MyService is a service component."
        assert passed_examples[0]["sample_weight"] == 2.5

    def test_raises_without_datasets_library(self):
        """prepare_dataset raises RuntimeError if datasets not installed."""
        trainer = LoRATrainer()
        store = MagicMock()

        with patch("architecture_model.training.trainer.HAS_DATASETS", False):
            with pytest.raises(RuntimeError, match="datasets"):
                trainer.prepare_dataset(store)


# ---------------------------------------------------------------------------
# train Tests
# ---------------------------------------------------------------------------


class TestTrain:
    @patch("architecture_model.training.trainer.HAS_PEFT", True)
    @patch("architecture_model.training.trainer.HAS_TRANSFORMERS", True)
    @patch("architecture_model.training.trainer.HAS_TORCH", True)
    def test_creates_lora_config_with_correct_params(self, tmp_path):
        """train() creates LoraConfig with the configured r and alpha."""
        trainer = LoRATrainer(lora_r=16, lora_alpha=32)

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=10)
        mock_dataset.column_names = ["instruction", "input", "output", "sample_weight"]
        mock_dataset.map.return_value = MagicMock()

        with (
            patch("architecture_model.training.trainer.LoraConfig") as MockLoraConfig,
            patch("architecture_model.training.trainer.AutoModelForCausalLM") as MockModel,
            patch("architecture_model.training.trainer.AutoTokenizer") as MockTokenizer,
            patch("architecture_model.training.trainer.get_peft_model") as mock_get_peft,
            patch("architecture_model.training.trainer.WeightedCETrainer") as MockTrainer,
            patch("architecture_model.training.trainer.TrainingArguments") as MockArgs,
            patch("architecture_model.training.trainer.default_data_collator"),
        ):
            mock_model_instance = MagicMock()
            MockModel.from_pretrained.return_value = mock_model_instance
            mock_get_peft.return_value = mock_model_instance
            MockTokenizer.from_pretrained.return_value = MagicMock()
            MockTrainer.return_value = MagicMock()

            trainer.train(mock_dataset, tmp_path / "output", epochs=3)

            MockLoraConfig.assert_called_once()
            config_kwargs = MockLoraConfig.call_args[1]
            assert config_kwargs["r"] == 16
            assert config_kwargs["lora_alpha"] == 32

    @patch("architecture_model.training.trainer.HAS_PEFT", True)
    @patch("architecture_model.training.trainer.HAS_TRANSFORMERS", True)
    @patch("architecture_model.training.trainer.HAS_TORCH", True)
    def test_uses_weighted_ce_trainer(self, tmp_path):
        """train() uses WeightedCETrainer instead of plain Trainer."""
        trainer = LoRATrainer()

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=10)
        mock_dataset.column_names = ["instruction", "input", "output", "sample_weight"]
        mock_dataset.map.return_value = MagicMock()

        with (
            patch("architecture_model.training.trainer.LoraConfig"),
            patch("architecture_model.training.trainer.AutoModelForCausalLM") as MockModel,
            patch("architecture_model.training.trainer.AutoTokenizer") as MockTokenizer,
            patch("architecture_model.training.trainer.get_peft_model") as mock_get_peft,
            patch("architecture_model.training.trainer.WeightedCETrainer") as MockWeightedTrainer,
            patch("architecture_model.training.trainer.Trainer") as MockPlainTrainer,
            patch("architecture_model.training.trainer.TrainingArguments"),
            patch("architecture_model.training.trainer.default_data_collator"),
        ):
            mock_model_instance = MagicMock()
            MockModel.from_pretrained.return_value = mock_model_instance
            mock_get_peft.return_value = mock_model_instance
            MockTokenizer.from_pretrained.return_value = MagicMock()
            mock_trainer_instance = MagicMock()
            MockWeightedTrainer.return_value = mock_trainer_instance

            trainer.train(mock_dataset, tmp_path / "output", epochs=3)

            # WeightedCETrainer should be used, not plain Trainer
            MockWeightedTrainer.assert_called_once()
            MockPlainTrainer.assert_not_called()
            mock_trainer_instance.train.assert_called_once()

    @patch("architecture_model.training.trainer.HAS_PEFT", True)
    @patch("architecture_model.training.trainer.HAS_TRANSFORMERS", True)
    @patch("architecture_model.training.trainer.HAS_TORCH", True)
    def test_tokenizes_dataset_before_training(self, tmp_path):
        """train() tokenizes the dataset via dataset.map() before passing to trainer."""
        trainer = LoRATrainer()

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=10)
        mock_dataset.column_names = ["instruction", "input", "output", "sample_weight"]
        mock_tokenized = MagicMock()
        mock_dataset.map.return_value = mock_tokenized

        with (
            patch("architecture_model.training.trainer.LoraConfig"),
            patch("architecture_model.training.trainer.AutoModelForCausalLM") as MockModel,
            patch("architecture_model.training.trainer.AutoTokenizer") as MockTokenizer,
            patch("architecture_model.training.trainer.get_peft_model") as mock_get_peft,
            patch("architecture_model.training.trainer.WeightedCETrainer") as MockTrainer,
            patch("architecture_model.training.trainer.TrainingArguments"),
            patch("architecture_model.training.trainer.default_data_collator"),
        ):
            mock_model_instance = MagicMock()
            MockModel.from_pretrained.return_value = mock_model_instance
            mock_get_peft.return_value = mock_model_instance
            MockTokenizer.from_pretrained.return_value = MagicMock()
            MockTrainer.return_value = MagicMock()

            trainer.train(mock_dataset, tmp_path / "output", epochs=3)

            # dataset.map should be called for tokenization
            mock_dataset.map.assert_called_once()
            map_kwargs = mock_dataset.map.call_args[1]
            assert map_kwargs["remove_columns"] == mock_dataset.column_names

            # The tokenized dataset should be passed to the trainer
            trainer_kwargs = MockTrainer.call_args[1]
            assert trainer_kwargs["train_dataset"] is mock_tokenized

    @patch("architecture_model.training.trainer.HAS_PEFT", True)
    @patch("architecture_model.training.trainer.HAS_TRANSFORMERS", True)
    @patch("architecture_model.training.trainer.HAS_TORCH", True)
    def test_tokenize_fn_preserves_sample_weight(self, tmp_path):
        """The tokenize function preserves sample_weight from examples."""
        trainer = LoRATrainer()

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=10)
        mock_dataset.column_names = ["instruction", "input", "output", "sample_weight"]
        mock_dataset.map.return_value = MagicMock()

        mock_tokenizer = MagicMock()
        mock_tokenizer.side_effect = lambda *a, **kw: {"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1]}

        with (
            patch("architecture_model.training.trainer.LoraConfig"),
            patch("architecture_model.training.trainer.AutoModelForCausalLM") as MockModel,
            patch("architecture_model.training.trainer.AutoTokenizer") as MockTokenizer,
            patch("architecture_model.training.trainer.get_peft_model") as mock_get_peft,
            patch("architecture_model.training.trainer.WeightedCETrainer") as MockTrainer,
            patch("architecture_model.training.trainer.TrainingArguments"),
            patch("architecture_model.training.trainer.default_data_collator"),
        ):
            mock_model_instance = MagicMock()
            MockModel.from_pretrained.return_value = mock_model_instance
            mock_get_peft.return_value = mock_model_instance
            MockTokenizer.from_pretrained.return_value = mock_tokenizer
            MockTrainer.return_value = MagicMock()

            trainer.train(mock_dataset, tmp_path / "output", epochs=3)

            # Extract the tokenize_fn passed to map
            tokenize_fn = mock_dataset.map.call_args[0][0]

            # Test that it preserves sample_weight
            example_with_weight = {
                "instruction": "Analyze",
                "input": "code",
                "output": "result",
                "sample_weight": 2.5,
            }
            result = tokenize_fn(example_with_weight)
            assert result["sample_weight"] == 2.5

            # Test that it works without sample_weight
            example_without_weight = {
                "instruction": "Analyze",
                "input": "code",
                "output": "result",
            }
            result = tokenize_fn(example_without_weight)
            assert "sample_weight" not in result

    @patch("architecture_model.training.trainer.HAS_PEFT", True)
    @patch("architecture_model.training.trainer.HAS_TRANSFORMERS", True)
    @patch("architecture_model.training.trainer.HAS_TORCH", True)
    def test_returns_output_path(self, tmp_path):
        """train() returns the adapter output path."""
        trainer = LoRATrainer()
        output_dir = tmp_path / "output"

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=10)
        mock_dataset.column_names = ["instruction", "input", "output"]
        mock_dataset.map.return_value = MagicMock()

        with (
            patch("architecture_model.training.trainer.LoraConfig"),
            patch("architecture_model.training.trainer.AutoModelForCausalLM") as MockModel,
            patch("architecture_model.training.trainer.AutoTokenizer") as MockTokenizer,
            patch("architecture_model.training.trainer.get_peft_model") as mock_get_peft,
            patch("architecture_model.training.trainer.WeightedCETrainer") as MockTrainer,
            patch("architecture_model.training.trainer.TrainingArguments"),
            patch("architecture_model.training.trainer.default_data_collator"),
        ):
            mock_model_instance = MagicMock()
            MockModel.from_pretrained.return_value = mock_model_instance
            mock_get_peft.return_value = mock_model_instance
            MockTokenizer.from_pretrained.return_value = MagicMock()
            MockTrainer.return_value = MagicMock()

            result = trainer.train(mock_dataset, output_dir, epochs=3)

            assert result == output_dir

    @patch("architecture_model.training.trainer.HAS_PEFT", True)
    @patch("architecture_model.training.trainer.HAS_TRANSFORMERS", True)
    @patch("architecture_model.training.trainer.HAS_TORCH", True)
    def test_passes_epochs_to_training_args(self, tmp_path):
        """train() passes the epochs parameter to TrainingArguments."""
        trainer = LoRATrainer()

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=10)
        mock_dataset.column_names = ["instruction", "input", "output"]
        mock_dataset.map.return_value = MagicMock()

        with (
            patch("architecture_model.training.trainer.LoraConfig"),
            patch("architecture_model.training.trainer.AutoModelForCausalLM") as MockModel,
            patch("architecture_model.training.trainer.AutoTokenizer") as MockTokenizer,
            patch("architecture_model.training.trainer.get_peft_model") as mock_get_peft,
            patch("architecture_model.training.trainer.WeightedCETrainer") as MockTrainer,
            patch("architecture_model.training.trainer.TrainingArguments") as MockArgs,
            patch("architecture_model.training.trainer.default_data_collator"),
        ):
            mock_model_instance = MagicMock()
            MockModel.from_pretrained.return_value = mock_model_instance
            mock_get_peft.return_value = mock_model_instance
            MockTokenizer.from_pretrained.return_value = MagicMock()
            MockTrainer.return_value = MagicMock()

            trainer.train(mock_dataset, tmp_path / "output", epochs=5)

            MockArgs.assert_called_once()
            args_kwargs = MockArgs.call_args[1]
            assert args_kwargs["num_train_epochs"] == 5

    @patch("architecture_model.training.trainer.HAS_PEFT", True)
    @patch("architecture_model.training.trainer.HAS_TRANSFORMERS", True)
    @patch("architecture_model.training.trainer.HAS_TORCH", True)
    def test_passes_default_data_collator(self, tmp_path):
        """train() passes default_data_collator to preserve sample_weight."""
        trainer = LoRATrainer()

        mock_dataset = MagicMock()
        mock_dataset.__len__ = MagicMock(return_value=10)
        mock_dataset.column_names = ["instruction", "input", "output", "sample_weight"]
        mock_dataset.map.return_value = MagicMock()

        with (
            patch("architecture_model.training.trainer.LoraConfig"),
            patch("architecture_model.training.trainer.AutoModelForCausalLM") as MockModel,
            patch("architecture_model.training.trainer.AutoTokenizer") as MockTokenizer,
            patch("architecture_model.training.trainer.get_peft_model") as mock_get_peft,
            patch("architecture_model.training.trainer.WeightedCETrainer") as MockTrainer,
            patch("architecture_model.training.trainer.TrainingArguments"),
            patch("architecture_model.training.trainer.default_data_collator") as mock_collator,
        ):
            mock_model_instance = MagicMock()
            MockModel.from_pretrained.return_value = mock_model_instance
            mock_get_peft.return_value = mock_model_instance
            MockTokenizer.from_pretrained.return_value = MagicMock()
            MockTrainer.return_value = MagicMock()

            trainer.train(mock_dataset, tmp_path / "output", epochs=3)

            # Verify default_data_collator is passed to trainer
            trainer_kwargs = MockTrainer.call_args[1]
            assert trainer_kwargs["data_collator"] is mock_collator

    def test_train_raises_without_dependencies(self, tmp_path):
        """train() raises RuntimeError if torch/transformers/peft not installed."""
        trainer = LoRATrainer()
        mock_dataset = MagicMock()

        with patch("architecture_model.training.trainer.HAS_TORCH", False):
            with pytest.raises(RuntimeError, match="torch"):
                trainer.train(mock_dataset, tmp_path / "output")


# ---------------------------------------------------------------------------
# export_to_ollama Tests
# ---------------------------------------------------------------------------


class TestExportToOllama:
    def test_writes_modelfile_with_correct_content(self, tmp_path):
        """export_to_ollama writes Modelfile with FROM and ADAPTER lines."""
        trainer = LoRATrainer(base_model="codellama/CodeLlama-13b-hf")
        adapter_path = tmp_path / "adapter"
        adapter_path.mkdir()

        with patch("architecture_model.training.trainer.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = MagicMock(returncode=0)
            trainer.export_to_ollama(adapter_path, "my-arch-model")

        # Verify the Modelfile was written
        modelfile = adapter_path / "Modelfile"
        assert modelfile.exists()
        content = modelfile.read_text()
        assert "FROM codellama/CodeLlama-13b-hf" in content
        assert f"ADAPTER {adapter_path}" in content

    def test_runs_ollama_create_command(self, tmp_path):
        """export_to_ollama runs 'ollama create' with correct args."""
        trainer = LoRATrainer()
        adapter_path = tmp_path / "adapter"
        adapter_path.mkdir()

        with patch("architecture_model.training.trainer.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = MagicMock(returncode=0)
            trainer.export_to_ollama(adapter_path, "my-arch-model")

        # Verify subprocess.run was called with ollama create
        mock_subprocess.run.assert_called_once()
        cmd = mock_subprocess.run.call_args[0][0]
        assert cmd[0] == "ollama"
        assert cmd[1] == "create"
        assert "my-arch-model" in cmd
        assert "-f" in cmd

    def test_raises_on_ollama_failure(self, tmp_path):
        """export_to_ollama raises RuntimeError if ollama create fails."""
        trainer = LoRATrainer()
        adapter_path = tmp_path / "adapter"
        adapter_path.mkdir()

        with patch("architecture_model.training.trainer.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = MagicMock(
                returncode=1, stderr="model not found"
            )
            with pytest.raises(RuntimeError, match="ollama create"):
                trainer.export_to_ollama(adapter_path, "bad-model")

    def test_modelfile_path_passed_to_subprocess(self, tmp_path):
        """The -f flag points to the Modelfile inside adapter_path."""
        trainer = LoRATrainer()
        adapter_path = tmp_path / "adapter"
        adapter_path.mkdir()

        with patch("architecture_model.training.trainer.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = MagicMock(returncode=0)
            trainer.export_to_ollama(adapter_path, "test-model")

        cmd = mock_subprocess.run.call_args[0][0]
        modelfile_path = str(adapter_path / "Modelfile")
        assert modelfile_path in cmd


# ---------------------------------------------------------------------------
# WeightedCETrainer Tests
# ---------------------------------------------------------------------------


class TestWeightedCETrainer:
    def test_weighted_trainer_is_importable(self):
        from architecture_model.training.trainer import WeightedCETrainer
        assert WeightedCETrainer is not None

    def test_weighted_trainer_has_compute_loss(self):
        from architecture_model.training.trainer import WeightedCETrainer
        assert hasattr(WeightedCETrainer, 'compute_loss')
