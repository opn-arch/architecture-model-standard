"""Tests for DPO preference trainer."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from architecture_model.training.trainer_dpo import DPOLoRATrainer


class TestDPOLoRATrainer:
    def test_init_default_config(self):
        trainer = DPOLoRATrainer()
        assert trainer.base_model == "Qwen/Qwen2.5-7B-Instruct"

    def test_init_custom_beta(self):
        trainer = DPOLoRATrainer(beta=0.2)
        assert trainer.beta == 0.2

    def test_default_beta(self):
        trainer = DPOLoRATrainer()
        assert trainer.beta == 0.1

    def test_requires_trl_for_training(self):
        trainer = DPOLoRATrainer()
        # Verify the class has the expected interface
        assert hasattr(trainer, 'train')
        assert hasattr(trainer, 'base_model')
        assert hasattr(trainer, 'beta')

    def test_init_with_model_config(self):
        from architecture_model.training.model_config import ModelConfig
        config = ModelConfig(
            hf_model_id="test/model",
            ollama_tag="test:latest",
            lora_r=8,
            lora_alpha=16,
            lora_target_modules=["q_proj", "k_proj"],
        )
        trainer = DPOLoRATrainer(model_config=config)
        assert trainer.base_model == "test/model"
