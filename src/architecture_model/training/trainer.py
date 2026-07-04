"""LoRA Trainer: HF PEFT fine-tuning with Ollama export.

Fine-tunes a local surrogate model using oracle-validated examples
from the DatasetStore, then exports the adapter for Ollama serving.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from architecture_model.training.model_config import ModelConfig, get_model_config

if TYPE_CHECKING:
    from architecture_model.training.dataset import DatasetStore

# ---------------------------------------------------------------------------
# Optional dependency imports (torch, transformers, peft, datasets)
# ---------------------------------------------------------------------------

try:
    import torch  # noqa: F401

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    AutoModelForCausalLM = None  # type: ignore[assignment, misc]
    AutoTokenizer = None  # type: ignore[assignment, misc]
    Trainer = None  # type: ignore[assignment, misc]
    TrainingArguments = None  # type: ignore[assignment, misc]

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


class LoRATrainer:
    """Fine-tunes a base model with LoRA using HF PEFT, exports to Ollama."""

    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
        lora_r: int = 16,
        lora_alpha: int = 32,
        *,
        model_config: Optional[ModelConfig] = None,
    ) -> None:
        if model_config is not None:
            self.base_model = model_config.hf_model_id
            self.lora_r = model_config.lora_r
            self.lora_alpha = model_config.lora_alpha
            self._config: Optional[ModelConfig] = model_config
        else:
            self.base_model = base_model
            self.lora_r = lora_r
            self.lora_alpha = lora_alpha
            self._config = None
        self._needs_retrain = False

    @property
    def needs_retrain(self) -> bool:
        """Whether the model has changed and requires retraining."""
        return self._needs_retrain

    @property
    def lora_target_modules(self) -> list[str]:
        """Return LoRA target modules from config, or default fallback."""
        if self._config is not None:
            return self._config.lora_target_modules
        return ["q_proj", "v_proj"]

    def update_model(self, new_config: ModelConfig) -> None:
        """Update trainer to use a new model config, flagging retrain if needed."""
        if new_config.hf_model_id != self.base_model:
            self._needs_retrain = True
        self.base_model = new_config.hf_model_id
        self.lora_r = new_config.lora_r
        self.lora_alpha = new_config.lora_alpha
        self._config = new_config

    def prepare_dataset(self, store: "DatasetStore") -> "Dataset":
        """Convert store examples to a HuggingFace Dataset.

        Calls store.export_for_training() which returns list[dict] with
        keys: instruction, input, output (instruction-tuning format).
        """
        if not HAS_DATASETS:
            raise RuntimeError(
                "datasets is required for prepare_dataset. "
                "Install with: pip install datasets"
            )

        examples = store.export_for_training()
        return Dataset.from_list(examples)

    def train(self, dataset: "Dataset", output_dir: Path, epochs: int = 3) -> Path:
        """Fine-tune the base model with LoRA on the given dataset.

        Args:
            dataset: HuggingFace Dataset with instruction/input/output columns.
            output_dir: Directory to save the LoRA adapter.
            epochs: Number of training epochs.

        Returns:
            Path to the saved adapter directory.
        """
        if not HAS_TORCH:
            raise RuntimeError(
                "torch is required for training. Install with: pip install torch"
            )
        if not HAS_TRANSFORMERS:
            raise RuntimeError(
                "transformers is required for training. "
                "Install with: pip install transformers"
            )
        if not HAS_PEFT:
            raise RuntimeError(
                "peft is required for training. Install with: pip install peft"
            )

        # Load base model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        model = AutoModelForCausalLM.from_pretrained(self.base_model)

        # Configure LoRA
        lora_config = LoraConfig(
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            target_modules=self.lora_target_modules,
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora_config)

        # Training arguments
        output_dir = Path(output_dir)
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=4,
            save_strategy="epoch",
            logging_steps=10,
        )

        # Train
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer,
        )
        trainer.train()

        # Save adapter
        model.save_pretrained(output_dir)

        return output_dir

    def export_to_ollama(self, adapter_path: Path, model_name: str) -> None:
        """Create a Modelfile and register the model with Ollama.

        Writes a Modelfile with FROM (base model) and ADAPTER (adapter path),
        then runs `ollama create <model_name> -f <Modelfile>`.
        """
        adapter_path = Path(adapter_path)
        modelfile_path = adapter_path / "Modelfile"

        # Write the Modelfile
        modelfile_content = f"FROM {self.base_model}\nADAPTER {adapter_path}\n"
        modelfile_path.write_text(modelfile_content)

        # Run ollama create
        cmd = ["ollama", "create", model_name, "-f", str(modelfile_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"ollama create failed (exit {result.returncode}): {result.stderr}"
            )
