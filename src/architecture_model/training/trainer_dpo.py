"""DPO Preference Trainer using trl.DPOTrainer.

Fine-tunes the surrogate model using preference pairs where:
- chosen = oracle output (higher quality architecture extraction)
- rejected = surrogate output (lower quality)

This teaches the model to prefer outputs similar to oracle quality.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from architecture_model.training.model_config import ModelConfig

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Optional dependency imports
# ---------------------------------------------------------------------------

try:
    from trl import DPOTrainer, DPOConfig  # type: ignore[import-untyped]
    HAS_TRL = True
except ImportError:
    HAS_TRL = False
    DPOTrainer = None  # type: ignore[assignment, misc]
    DPOConfig = None  # type: ignore[assignment, misc]

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    AutoModelForCausalLM = None  # type: ignore[assignment, misc]
    AutoTokenizer = None  # type: ignore[assignment, misc]

try:
    from peft import LoraConfig, get_peft_model  # type: ignore[import-untyped]
    HAS_PEFT = True
except ImportError:
    HAS_PEFT = False
    LoraConfig = None  # type: ignore[assignment, misc]
    get_peft_model = None  # type: ignore[assignment, misc]

try:
    from datasets import Dataset  # type: ignore[import-untyped]
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False
    Dataset = None  # type: ignore[assignment, misc]


class DPOLoRATrainer:
    """DPO fine-tuning for preference learning on architecture extractions.

    Uses trl.DPOTrainer with LoRA adapters. The preference signal teaches
    the surrogate to produce outputs closer to oracle quality.
    """

    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
        model_config: Optional[ModelConfig] = None,
        beta: float = 0.1,
        max_length: int = 4096,
        max_prompt_length: int = 6144,
    ) -> None:
        if model_config:
            self.base_model = model_config.hf_model_id
            self._config = model_config
        else:
            self.base_model = base_model
            self._config = None
        self.beta = beta
        self.max_length = max_length
        self.max_prompt_length = max_prompt_length

    def train(self, preference_dataset: "Dataset", output_dir: Path, epochs: int = 3) -> Path:
        """Run DPO training on preference pairs.

        Args:
            preference_dataset: HF Dataset with 'prompt', 'chosen', 'rejected' columns.
            output_dir: Directory to save the DPO adapter.
            epochs: Number of training epochs.

        Returns:
            Path to saved adapter.

        Raises:
            RuntimeError: If trl or transformers are not installed.
        """
        if not HAS_TRL:
            raise RuntimeError(
                "trl is required for DPO training. Install with: pip install trl"
            )
        if not HAS_TRANSFORMERS:
            raise RuntimeError(
                "transformers + peft required. Install with: pip install transformers peft"
            )

        model = AutoModelForCausalLM.from_pretrained(self.base_model)
        tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=(
                self._config.lora_target_modules
                if self._config
                else ["q_proj", "v_proj"]
            ),
            task_type="CAUSAL_LM",
        )

        output_dir = Path(output_dir)
        dpo_config = DPOConfig(
            output_dir=str(output_dir),
            num_train_epochs=epochs,
            beta=self.beta,
            per_device_train_batch_size=1,
            max_length=self.max_length,
            learning_rate=5e-5,
            logging_steps=1,
            gradient_accumulation_steps=4,
            dataloader_pin_memory=False,
            warmup_steps=2,
        )

        trainer = DPOTrainer(
            model=model,
            args=dpo_config,
            train_dataset=preference_dataset,
            processing_class=tokenizer,
            peft_config=lora_config,
        )
        trainer.train()
        trainer.save_model(str(output_dir))

        return output_dir
