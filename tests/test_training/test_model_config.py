"""Tests for ModelConfig dataclass and MODEL_REGISTRY."""

from __future__ import annotations

import pytest
import yaml

from architecture_model.training.model_config import (
    ModelConfig,
    MODEL_REGISTRY,
    get_model_config,
    resolve_config,
)


# ---------------------------------------------------------------------------
# Registry Tests
# ---------------------------------------------------------------------------


class TestModelRegistry:
    def test_registry_has_three_models(self):
        assert len(MODEL_REGISTRY) == 3

    def test_registry_keys(self):
        expected = {"qwen2.5:7b", "llama3.1:8b", "gemma2:9b"}
        assert set(MODEL_REGISTRY.keys()) == expected

    def test_registry_values_are_model_config(self):
        for cfg in MODEL_REGISTRY.values():
            assert isinstance(cfg, ModelConfig)


# ---------------------------------------------------------------------------
# ModelConfig Field Tests
# ---------------------------------------------------------------------------


class TestModelConfigFields:
    def test_qwen_config(self):
        cfg = MODEL_REGISTRY["qwen2.5:7b"]
        assert cfg.ollama_tag == "qwen2.5:7b"
        assert cfg.hf_model_id == "Qwen/Qwen2.5-7B-Instruct"
        assert cfg.lora_target_modules == ["q_proj", "k_proj", "v_proj", "o_proj"]
        assert cfg.lora_r == 16
        assert cfg.lora_alpha == 32
        assert cfg.context_window == 32768
        assert cfg.wraps_in_fences is True

    def test_llama_config(self):
        cfg = MODEL_REGISTRY["llama3.1:8b"]
        assert cfg.ollama_tag == "llama3.1:8b"
        assert cfg.hf_model_id == "meta-llama/Llama-3.1-8B-Instruct"
        assert cfg.lora_target_modules == ["q_proj", "k_proj", "v_proj", "o_proj"]
        assert cfg.lora_r == 16
        assert cfg.lora_alpha == 32
        assert cfg.context_window == 131072
        assert cfg.wraps_in_fences is True

    def test_gemma_config(self):
        cfg = MODEL_REGISTRY["gemma2:9b"]
        assert cfg.ollama_tag == "gemma2:9b"
        assert cfg.hf_model_id == "google/gemma-2-9b-it"
        assert cfg.lora_target_modules == ["q_proj", "k_proj", "v_proj", "o_proj"]
        assert cfg.lora_r == 16
        assert cfg.lora_alpha == 32
        assert cfg.context_window == 8192
        assert cfg.wraps_in_fences is False

    def test_config_is_frozen(self):
        cfg = MODEL_REGISTRY["qwen2.5:7b"]
        with pytest.raises(Exception):
            cfg.ollama_tag = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_model_config Tests
# ---------------------------------------------------------------------------


class TestGetModelConfig:
    def test_returns_known_model(self):
        cfg = get_model_config("qwen2.5:7b")
        assert cfg.ollama_tag == "qwen2.5:7b"
        assert cfg.hf_model_id == "Qwen/Qwen2.5-7B-Instruct"

    def test_returns_each_known_model(self):
        for tag in MODEL_REGISTRY:
            cfg = get_model_config(tag)
            assert cfg is MODEL_REGISTRY[tag]

    def test_returns_generic_fallback_for_unknown(self):
        cfg = get_model_config("unknown:latest")
        assert cfg.ollama_tag == "unknown:latest"
        assert cfg.hf_model_id == ""
        assert cfg.lora_target_modules == ["q_proj", "v_proj"]
        assert cfg.context_window == 4096

    def test_fallback_has_safe_defaults(self):
        cfg = get_model_config("mystery-model:3b")
        assert cfg.lora_r == 16
        assert cfg.lora_alpha == 32
        assert cfg.wraps_in_fences is False


# ---------------------------------------------------------------------------
# resolve_config Tests
# ---------------------------------------------------------------------------


class TestResolveConfig:
    def test_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("ARCHMODEL_SURROGATE_MODEL", raising=False)
        cfg = resolve_config(default="llama3.1:8b")
        assert cfg.ollama_tag == "llama3.1:8b"

    def test_env_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv("ARCHMODEL_SURROGATE_MODEL", "gemma2:9b")
        cfg = resolve_config(default="qwen2.5:7b")
        assert cfg.ollama_tag == "gemma2:9b"

    def test_reads_from_yaml_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ARCHMODEL_SURROGATE_MODEL", raising=False)
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"surrogate_model": "gemma2:9b"}))
        cfg = resolve_config(default="qwen2.5:7b", config_path=str(config_file))
        assert cfg.ollama_tag == "gemma2:9b"

    def test_env_var_overrides_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ARCHMODEL_SURROGATE_MODEL", "llama3.1:8b")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"surrogate_model": "gemma2:9b"}))
        cfg = resolve_config(default="qwen2.5:7b", config_path=str(config_file))
        assert cfg.ollama_tag == "llama3.1:8b"

    def test_missing_config_file_uses_default(self, monkeypatch):
        monkeypatch.delenv("ARCHMODEL_SURROGATE_MODEL", raising=False)
        cfg = resolve_config(default="qwen2.5:7b", config_path="/nonexistent/path.yaml")
        assert cfg.ollama_tag == "qwen2.5:7b"

    def test_env_var_with_unknown_model_returns_fallback(self, monkeypatch):
        monkeypatch.setenv("ARCHMODEL_SURROGATE_MODEL", "custom:latest")
        cfg = resolve_config(default="qwen2.5:7b")
        assert cfg.ollama_tag == "custom:latest"
        assert cfg.hf_model_id == ""


# ---------------------------------------------------------------------------
# Surrogate + ModelConfig Integration Tests
# ---------------------------------------------------------------------------


class TestSurrogateModelConfig:
    def test_surrogate_accepts_model_config(self):
        from architecture_model.training.surrogate import Surrogate
        from architecture_model.training.model_config import MODEL_REGISTRY
        cfg = MODEL_REGISTRY["llama3.1:8b"]
        s = Surrogate(model_config=cfg)
        assert s.model_name == "llama3.1:8b"
        assert s.model_config.hf_model_id == "meta-llama/Llama-3.1-8B-Instruct"

    def test_surrogate_swap_model_updates_config(self):
        from architecture_model.training.surrogate import Surrogate
        s = Surrogate(model_name="qwen2.5:7b")
        assert s.model_config.ollama_tag == "qwen2.5:7b"
        s.swap_model("llama3.1:8b")
        assert s.model_config.ollama_tag == "llama3.1:8b"
        assert s.model_config.hf_model_id == "meta-llama/Llama-3.1-8B-Instruct"

    def test_surrogate_backward_compat_model_name_string(self):
        from architecture_model.training.surrogate import Surrogate
        s = Surrogate(model_name="qwen2.5:7b")
        assert s.model_name == "qwen2.5:7b"

    def test_surrogate_swap_with_model_config_object(self):
        from architecture_model.training.surrogate import Surrogate
        from architecture_model.training.model_config import MODEL_REGISTRY
        s = Surrogate(model_name="qwen2.5:7b")
        s.swap_model(MODEL_REGISTRY["gemma2:9b"])
        assert s.model_name == "gemma2:9b"


# ---------------------------------------------------------------------------
# LoRATrainer + ModelConfig Integration Tests
# ---------------------------------------------------------------------------


class TestTrainerModelConfig:
    def test_trainer_from_model_config(self):
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        cfg = MODEL_REGISTRY["llama3.1:8b"]
        t = LoRATrainer(model_config=cfg)
        assert t.base_model == "meta-llama/Llama-3.1-8B-Instruct"
        assert "k_proj" in t.lora_target_modules

    def test_trainer_detects_model_change(self):
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        cfg = MODEL_REGISTRY["qwen2.5:7b"]
        t = LoRATrainer(model_config=cfg)
        assert not t.needs_retrain
        t.update_model(MODEL_REGISTRY["llama3.1:8b"])
        assert t.needs_retrain

    def test_trainer_backward_compat(self):
        from architecture_model.training.trainer import LoRATrainer
        t = LoRATrainer(base_model="some/Model-hf", lora_r=8, lora_alpha=16)
        assert t.base_model == "some/Model-hf"
        assert t.lora_r == 8
        assert t.lora_target_modules == ["q_proj", "v_proj"]

    def test_trainer_same_model_no_retrain(self):
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        cfg = MODEL_REGISTRY["qwen2.5:7b"]
        t = LoRATrainer(model_config=cfg)
        t.update_model(MODEL_REGISTRY["qwen2.5:7b"])
        assert not t.needs_retrain


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# resolve_training_targets Tests
# ---------------------------------------------------------------------------


class TestTrainingTargets:
    def test_resolve_targets_from_config(self, tmp_path):
        from architecture_model.training.model_config import resolve_training_targets
        cfg_file = tmp_path / ".architecture-model-training.yaml"
        cfg_file.write_text(
            "surrogate_model: gemma2:9b\n"
            "training_targets:\n"
            "  - gemma2:9b\n"
            "  - llama3.1:8b\n"
        )
        targets = resolve_training_targets(config_path=cfg_file)
        assert len(targets) == 2
        assert targets[0].ollama_tag == "gemma2:9b"
        assert targets[1].ollama_tag == "llama3.1:8b"

    def test_resolve_targets_from_env(self, monkeypatch):
        from architecture_model.training.model_config import resolve_training_targets
        monkeypatch.setenv("ARCHMODEL_TRAINING_TARGETS", "gemma2:9b,llama3.1:8b")
        targets = resolve_training_targets()
        assert len(targets) == 2
        assert targets[0].ollama_tag == "gemma2:9b"
        assert targets[1].ollama_tag == "llama3.1:8b"

    def test_resolve_targets_default_is_surrogate_model(self, monkeypatch):
        from architecture_model.training.model_config import resolve_training_targets
        monkeypatch.delenv("ARCHMODEL_TRAINING_TARGETS", raising=False)
        targets = resolve_training_targets()
        assert len(targets) == 1
        assert targets[0].ollama_tag == "qwen2.5:7b"  # default surrogate

    def test_resolve_targets_unknown_model_gets_generic(self, monkeypatch):
        from architecture_model.training.model_config import resolve_training_targets
        monkeypatch.setenv("ARCHMODEL_TRAINING_TARGETS", "custom:7b")
        targets = resolve_training_targets()
        assert len(targets) == 1
        assert targets[0].ollama_tag == "custom:7b"
        assert targets[0].hf_model_id == ""  # generic fallback


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------


class TestMultiAdapterTraining:
    def test_train_all_calls_train_per_target(self):
        """Verify train_all iterates over targets."""
        from unittest.mock import patch, MagicMock
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        from pathlib import Path

        trainer = LoRATrainer()
        targets = [MODEL_REGISTRY["gemma2:9b"], MODEL_REGISTRY["llama3.1:8b"]]

        with patch.object(trainer, "train", return_value=Path("/tmp/fake")) as mock_train, \
             patch.object(trainer, "export_to_ollama") as mock_export:
            mock_dataset = MagicMock()
            results = trainer.train_all(mock_dataset, targets, output_base=Path("/tmp/adapters"))

        assert mock_train.call_count == 2
        assert mock_export.call_count == 2
        assert "gemma2:9b" in results
        assert "llama3.1:8b" in results

    def test_train_all_names_models_correctly(self):
        """Verify Ollama model naming: {model}-arch."""
        from unittest.mock import patch, MagicMock
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        from pathlib import Path

        trainer = LoRATrainer()
        targets = [MODEL_REGISTRY["gemma2:9b"]]

        with patch.object(trainer, "train", return_value=Path("/tmp/fake")), \
             patch.object(trainer, "export_to_ollama") as mock_export:
            trainer.train_all(MagicMock(), targets, output_base=Path("/tmp/adapters"))

        # export_to_ollama(adapter_path, model_name) — check second positional arg
        mock_export.assert_called_once()
        args = mock_export.call_args[0]
        assert args[1] == "gemma2-9b-arch"

    def test_train_all_adapter_paths(self):
        """Verify adapter directories: output_base/{tag-sanitized}/."""
        from unittest.mock import patch, MagicMock
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        from pathlib import Path

        trainer = LoRATrainer()
        targets = [MODEL_REGISTRY["gemma2:9b"], MODEL_REGISTRY["llama3.1:8b"]]

        train_calls = []
        def fake_train(dataset, output_dir, **kwargs):
            train_calls.append(Path(output_dir))
            return Path(output_dir)

        with patch.object(trainer, "train", side_effect=fake_train), \
             patch.object(trainer, "export_to_ollama"):
            trainer.train_all(MagicMock(), targets, output_base=Path("/tmp/adapters"))

        assert Path("/tmp/adapters/gemma2-9b") in train_calls
        assert Path("/tmp/adapters/llama3.1-8b") in train_calls

    def test_train_all_returns_paths(self):
        """Verify return value maps tag to adapter path."""
        from unittest.mock import patch, MagicMock
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        from pathlib import Path

        trainer = LoRATrainer()
        targets = [MODEL_REGISTRY["gemma2:9b"]]

        with patch.object(trainer, "train", return_value=Path("/tmp/adapters/gemma2-9b")), \
             patch.object(trainer, "export_to_ollama"):
            results = trainer.train_all(MagicMock(), targets, output_base=Path("/tmp/adapters"))

        assert results["gemma2:9b"] == Path("/tmp/adapters/gemma2-9b")


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------


class TestPipelineMultiAdapter:
    def test_pipeline_accepts_training_targets(self):
        """Pipeline can be constructed with training_targets."""
        from unittest.mock import MagicMock
        from architecture_model.training.pipeline import TrainingPipeline
        from architecture_model.training.model_config import MODEL_REGISTRY

        targets = [MODEL_REGISTRY["gemma2:9b"], MODEL_REGISTRY["llama3.1:8b"]]
        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=MagicMock(),
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=MagicMock(),
            repo_fetcher=MagicMock(),
            training_targets=targets,
        )
        assert pipeline.training_targets == targets

    def test_pipeline_trigger_training_calls_train_all(self):
        """When training_targets set, _trigger_training calls train_all."""
        from unittest.mock import MagicMock
        from architecture_model.training.pipeline import TrainingPipeline
        from architecture_model.training.model_config import MODEL_REGISTRY

        targets = [MODEL_REGISTRY["gemma2:9b"], MODEL_REGISTRY["llama3.1:8b"]]
        mock_trainer = MagicMock()
        mock_store = MagicMock()

        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=mock_store,
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=mock_trainer,
            repo_fetcher=MagicMock(),
            training_targets=targets,
        )
        pipeline._trigger_training()

        mock_trainer.prepare_dataset.assert_called_once_with(mock_store)
        mock_trainer.train_all.assert_called_once()
        call_args = mock_trainer.train_all.call_args[0]
        assert call_args[1] == targets  # second positional arg is targets

    def test_pipeline_trigger_training_single_model_fallback(self):
        """Without training_targets, falls back to single train() call."""
        from unittest.mock import MagicMock
        from architecture_model.training.pipeline import TrainingPipeline

        mock_trainer = MagicMock()
        mock_store = MagicMock()

        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=mock_store,
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=mock_trainer,
            repo_fetcher=MagicMock(),
        )
        pipeline._trigger_training()

        mock_trainer.prepare_dataset.assert_called_once()
        mock_trainer.train.assert_called_once()
        mock_trainer.train_all.assert_not_called()


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------


class TestExports:
    def test_model_config_importable_from_training(self):
        from architecture_model.training import (
            ModelConfig, MODEL_REGISTRY, get_model_config, resolve_config,
        )
        assert len(MODEL_REGISTRY) == 3
        assert callable(get_model_config)
        assert callable(resolve_config)
