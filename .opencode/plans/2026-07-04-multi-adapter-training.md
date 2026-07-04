# Multi-Adapter Training + gemma2:9b Default

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set gemma2:9b as the default surrogate model and add multi-adapter training that fine-tunes LoRA adapters for both gemma2:9b and llama3.1:8b from the same oracle dataset.

**Architecture:** `LoRATrainer.train_all()` iterates over a list of `ModelConfig` targets, training a separate LoRA adapter per model. Adapters saved to `./adapters/{model}/`, exported to Ollama as `{model}-arch`. Config file specifies `training_targets` list.

**Tech Stack:** Existing PEFT/transformers integration, Ollama Modelfile creation, YAML config.

---

### Task 1: Change default model to gemma2:9b

**Files:**
- Modify: `src/architecture_model/training/surrogate.py`
- Modify: `src/architecture_model/training/trainer.py`
- Modify: `src/architecture_model/training/model_config.py`
- Modify: `.architecture-model-training.yaml.example`
- Modify: `tests/test_training/test_model_config.py`

**Step 1: Update surrogate.py default**

Change `model_name: str = "qwen2.5:7b"` to `model_name: str = "gemma2:9b"` in `Surrogate.__init__`.

**Step 2: Update trainer.py default**

Change `base_model: str = "Qwen/Qwen2.5-7B-Instruct"` to `base_model: str = "google/gemma-2-9b-it"` in `LoRATrainer.__init__`.

**Step 3: Update model_config.py resolve_config default**

Change `def resolve_config(default: str = "qwen2.5:7b", ...)` to `def resolve_config(default: str = "gemma2:9b", ...)`.

**Step 4: Update example config**

Change `surrogate_model: qwen2.5:7b` to `surrogate_model: gemma2:9b` in `.architecture-model-training.yaml.example`.

**Step 5: Fix any tests asserting old defaults**

Check `test_model_config.py` for tests like `test_resolve_config_default` and `test_trainer_backward_compat` that may assume the old default. Update assertions to match `gemma2:9b` / `google/gemma-2-9b-it`.

**Step 6: Run tests**

Run: `pytest tests/ --tb=short -q`
Expected: 310 passed

**Step 7: Commit**

```bash
git commit -am "feat(training): set gemma2:9b as default surrogate model"
```

---

### Task 2: Add resolve_training_targets() function

**Files:**
- Modify: `src/architecture_model/training/model_config.py`
- Modify: `tests/test_training/test_model_config.py`

**Step 1: Write failing tests**

```python
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
        assert targets[0].ollama_tag == "gemma2:9b"  # default surrogate

    def test_resolve_targets_unknown_model_gets_generic(self, monkeypatch):
        from architecture_model.training.model_config import resolve_training_targets
        monkeypatch.setenv("ARCHMODEL_TRAINING_TARGETS", "custom:7b")
        targets = resolve_training_targets()
        assert len(targets) == 1
        assert targets[0].ollama_tag == "custom:7b"
        assert targets[0].hf_model_id == ""  # generic fallback
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_training/test_model_config.py::TestTrainingTargets -v`
Expected: ImportError (function doesn't exist yet)

**Step 3: Implement resolve_training_targets**

Add to `model_config.py`:

```python
def resolve_training_targets(
    config_path: Optional[Path] = None,
) -> list[ModelConfig]:
    """Resolve list of models to train LoRA adapters for.

    Priority:
    1. ARCHMODEL_TRAINING_TARGETS env var (comma-separated Ollama tags)
    2. training_targets list in config file
    3. Default: just the resolved surrogate model
    """
    # 1. Environment variable
    env_targets = os.environ.get("ARCHMODEL_TRAINING_TARGETS")
    if env_targets:
        tags = [t.strip() for t in env_targets.split(",") if t.strip()]
        return [get_model_config(tag) for tag in tags]

    # 2. Config file
    if config_path and config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text())
            if isinstance(data, dict) and "training_targets" in data:
                tags = data["training_targets"]
                if isinstance(tags, list):
                    return [get_model_config(str(t)) for t in tags]
        except (yaml.YAMLError, OSError):
            pass

    # 3. Default: just the surrogate model
    default_cfg = resolve_config(config_path=config_path)
    return [default_cfg]
```

**Step 4: Update __init__.py exports**

Add `resolve_training_targets` to imports and `__all__`.

**Step 5: Run tests**

Run: `pytest tests/ --tb=short -q`
Expected: 310+ passed

**Step 6: Commit**

```bash
git add src/architecture_model/training/model_config.py \
        src/architecture_model/training/__init__.py \
        tests/test_training/test_model_config.py
git commit -m "feat(training): add resolve_training_targets() for multi-model config"
```

---

### Task 3: Add train_all() method to LoRATrainer

**Files:**
- Modify: `src/architecture_model/training/trainer.py`
- Modify: `tests/test_training/test_model_config.py`

**Step 1: Write failing tests**

```python
class TestMultiAdapterTraining:
    def test_train_all_calls_train_per_target(self):
        """Verify train_all iterates over targets (mock-based)."""
        from unittest.mock import patch, MagicMock
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        from pathlib import Path

        trainer = LoRATrainer()
        targets = [MODEL_REGISTRY["gemma2:9b"], MODEL_REGISTRY["llama3.1:8b"]]

        # Mock train() and export_to_ollama() since we can't actually run training
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

        # Should be called with "gemma2-9b-arch"
        call_args = mock_export.call_args
        assert call_args[0][1] == "gemma2-9b-arch" or call_args[1].get("model_name") == "gemma2-9b-arch"

    def test_train_all_adapter_paths(self):
        """Verify adapter directories: output_base/{tag}/."""
        from unittest.mock import patch, MagicMock
        from architecture_model.training.trainer import LoRATrainer
        from architecture_model.training.model_config import MODEL_REGISTRY
        from pathlib import Path

        trainer = LoRATrainer()
        targets = [MODEL_REGISTRY["gemma2:9b"], MODEL_REGISTRY["llama3.1:8b"]]

        train_calls = []
        def fake_train(dataset, output_dir, **kwargs):
            train_calls.append(output_dir)
            return Path(output_dir)

        with patch.object(trainer, "train", side_effect=fake_train), \
             patch.object(trainer, "export_to_ollama"):
            trainer.train_all(MagicMock(), targets, output_base=Path("/tmp/adapters"))

        assert Path("/tmp/adapters/gemma2-9b") in [Path(p) for p in train_calls]
        assert Path("/tmp/adapters/llama3.1-8b") in [Path(p) for p in train_calls]
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_training/test_model_config.py::TestMultiAdapterTraining -v`
Expected: AttributeError (train_all doesn't exist)

**Step 3: Implement train_all**

Add to `LoRATrainer` class in `trainer.py`:

```python
def train_all(
    self,
    dataset: "Dataset",
    targets: list["ModelConfig"],
    output_base: Path,
    epochs: int = 3,
) -> dict[str, Path]:
    """Fine-tune LoRA adapters for multiple base models.

    Trains a separate adapter for each target model using the same dataset.
    Exports each to Ollama with naming convention: {model}-arch.

    Args:
        dataset: HuggingFace Dataset (model-independent training data).
        targets: List of ModelConfig to train adapters for.
        output_base: Base directory for adapters (creates subdirs per model).
        epochs: Training epochs per model.

    Returns:
        Mapping of ollama_tag → adapter_path for each successfully trained model.
    """
    output_base = Path(output_base)
    results: dict[str, Path] = {}

    for cfg in targets:
        # Update trainer config for this target
        self.update_model(cfg)

        # Adapter output directory: output_base/{tag-sanitized}/
        safe_tag = cfg.ollama_tag.replace(":", "-")
        adapter_dir = output_base / safe_tag

        # Train
        adapter_path = self.train(dataset, output_dir=adapter_dir, epochs=epochs)

        # Export to Ollama: "{model}-arch"
        # e.g. "gemma2:9b" → "gemma2-9b-arch"
        ollama_name = f"{safe_tag}-arch"
        self.export_to_ollama(adapter_path, ollama_name)

        results[cfg.ollama_tag] = adapter_path

    return results
```

**Step 4: Run tests**

Run: `pytest tests/ --tb=short -q`
Expected: 310+ passed

**Step 5: Commit**

```bash
git add src/architecture_model/training/trainer.py tests/test_training/test_model_config.py
git commit -m "feat(training): add train_all() for multi-adapter LoRA training

Trains separate LoRA adapters for multiple base models from the same dataset.
Adapters stored at ./adapters/{model-tag}/, exported to Ollama as {model}-arch."
```

---

### Task 4: Wire multi-adapter into TrainingPipeline

**Files:**
- Modify: `src/architecture_model/training/pipeline.py`
- Modify: `tests/test_training/test_model_config.py`

**Step 1: Write failing tests**

```python
class TestPipelineMultiAdapter:
    def test_pipeline_trigger_training_uses_targets(self):
        """Pipeline._trigger_training calls train_all with configured targets."""
        from unittest.mock import patch, MagicMock, PropertyMock
        from architecture_model.training.pipeline import TrainingPipeline
        from architecture_model.training.model_config import MODEL_REGISTRY
        from pathlib import Path

        # Create pipeline with mocked components
        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=MagicMock(),
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=MagicMock(),
            repo_fetcher=MagicMock(),
        )
        pipeline.training_targets = [
            MODEL_REGISTRY["gemma2:9b"],
            MODEL_REGISTRY["llama3.1:8b"],
        ]

        pipeline._trigger_training()

        pipeline.trainer.train_all.assert_called_once()
        call_args = pipeline.trainer.train_all.call_args
        targets_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]["targets"]
        assert len(targets_arg) == 2
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_training/test_model_config.py::TestPipelineMultiAdapter -v`
Expected: FAIL (pipeline doesn't have training_targets or call train_all)

**Step 3: Update TrainingPipeline**

In `pipeline.py`:

```python
class TrainingPipeline:
    def __init__(
        self,
        surrogate: Surrogate,
        oracle: Oracle,
        store: DatasetStore,
        evaluator: Evaluator,
        controller: MPCController,
        trainer: LoRATrainer,
        repo_fetcher: RepoFetcher,
        training_targets: list | None = None,
    ) -> None:
        self.surrogate = surrogate
        self.oracle = oracle
        self.store = store
        self.evaluator = evaluator
        self.controller = controller
        self.trainer = trainer
        self.repo_fetcher = repo_fetcher
        # Multi-adapter: list of models to train (default: just the surrogate's model)
        self.training_targets = training_targets

    def _trigger_training(self) -> None:
        """Prepare dataset and run LoRA fine-tuning for all target models."""
        logger.info("Training threshold reached, starting fine-tuning.")
        dataset = self.trainer.prepare_dataset(self.store)

        if self.training_targets and len(self.training_targets) > 0:
            # Multi-adapter training
            from pathlib import Path
            output_base = Path("./adapters")
            self.trainer.train_all(dataset, self.training_targets, output_base=output_base)
        else:
            # Single model training (backward compat)
            from pathlib import Path
            output_dir = Path("./adapters") / "default"
            self.trainer.train(dataset, output_dir=output_dir)
```

**Step 4: Run tests**

Run: `pytest tests/ --tb=short -q`
Expected: 310+ passed

**Step 5: Commit**

```bash
git add src/architecture_model/training/pipeline.py tests/test_training/test_model_config.py
git commit -m "feat(training): wire multi-adapter training into pipeline

TrainingPipeline accepts training_targets list. When set, _trigger_training()
calls train_all() to fine-tune adapters for all target models from same data."
```

---

### Task 5: Update example config and integration test

**Files:**
- Modify: `.architecture-model-training.yaml.example`
- Modify: `scripts/test_model_swap.py`

**Step 1: Update example config to show training_targets**

```yaml
# Training pipeline configuration
# Copy to .architecture-model-training.yaml and customize.
#
# Model options (pre-tested):
#   gemma2:9b    - Best structured YAML output, precise schema adherence (DEFAULT)
#   llama3.1:8b  - Strong instruction following, 128K context
#   qwen2.5:7b   - Good code comprehension, 32K context
#
# Any Ollama model works - unregistered models use safe defaults.

surrogate_model: gemma2:9b
ollama_host: http://localhost:11434

# Train LoRA adapters for multiple models (same oracle data, separate adapters)
# Adapters saved to ./adapters/{model}/, exported to Ollama as {model}-arch
training_targets:
  - gemma2:9b
  - llama3.1:8b

# Oracle (via litellm - set API keys in environment)
# oracle_model: gpt-4o

# Training
# training_threshold: 50
# lora_output_dir: ./adapters/
```

**Step 2: Update benchmark script to show multi-adapter info**

Add a note at the end of `scripts/test_model_swap.py` about multi-adapter training:

```python
print("\nMULTI-ADAPTER TRAINING:")
print("  Configure in .architecture-model-training.yaml:")
print("    training_targets:")
print("      - gemma2:9b")
print("      - llama3.1:8b")
print("  Or via env: ARCHMODEL_TRAINING_TARGETS=gemma2:9b,llama3.1:8b")
```

**Step 3: Run tests**

Run: `pytest tests/ --tb=short -q`
Expected: 310+ passed

**Step 4: Commit**

```bash
git add .architecture-model-training.yaml.example scripts/test_model_swap.py
git commit -m "docs: update config example with multi-adapter training targets"
```

---

## Summary

After all 5 tasks:

| What | Before | After |
|------|--------|-------|
| Default surrogate | qwen2.5:7b | **gemma2:9b** |
| Default HF model | Qwen/Qwen2.5-7B-Instruct | **google/gemma-2-9b-it** |
| Training targets | single model | **[gemma2:9b, llama3.1:8b]** |
| Adapter storage | N/A | **./adapters/{model-tag}/** |
| Ollama export names | N/A | **gemma2-9b-arch, llama3.1-8b-arch** |

**Workflow after implementation:**
```bash
# Pull both models
ollama pull gemma2:9b
ollama pull llama3.1:8b

# Run MPC loop — collects oracle data
architecture-model training run

# When training threshold hit (50 examples):
#   → trains ./adapters/gemma2-9b/  → exports gemma2-9b-arch
#   → trains ./adapters/llama3.1-8b/ → exports llama3.1-8b-arch

# Use fine-tuned model for extraction:
architecture-model extract --model gemma2-9b-arch
```
