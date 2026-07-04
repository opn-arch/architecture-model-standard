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
