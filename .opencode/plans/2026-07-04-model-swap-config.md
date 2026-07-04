# Model Swap & Configuration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the surrogate model configurable with a registry of tested models, automatic LoRA invalidation on model change, and env/config-file support.

**Architecture:** A `ModelConfig` dataclass bundles Ollama tag, HuggingFace model ID, LoRA target modules, and model-specific settings. A `MODEL_REGISTRY` provides pre-configured entries. The `Surrogate` and `LoRATrainer` read from a shared config, and LoRA adapters are invalidated when the base model changes.

**Tech Stack:** Python dataclasses, YAML config file (`.architecture-model-training.yaml`), environment variables, existing Ollama/PEFT integration.

---

### Task 1: Create ModelConfig dataclass and MODEL_REGISTRY

**Files:**
- Create: `src/architecture_model/training/model_config.py`
- Test: `tests/test_training/test_model_config.py`

**Step 1: Write the failing tests**

```python
# tests/test_training/test_model_config.py
"""Tests for ModelConfig and MODEL_REGISTRY."""
import pytest
from architecture_model.training.model_config import (
    ModelConfig, MODEL_REGISTRY, get_model_config, resolve_config,
)


class TestModelConfig:
    def test_registry_has_three_models(self):
        assert len(MODEL_REGISTRY) == 3
        assert "qwen2.5:7b" in MODEL_REGISTRY
        assert "llama3.1:8b" in MODEL_REGISTRY
        assert "gemma2:9b" in MODEL_REGISTRY

    def test_config_fields(self):
        cfg = MODEL_REGISTRY["qwen2.5:7b"]
        assert cfg.ollama_tag == "qwen2.5:7b"
        assert cfg.hf_model_id == "Qwen/Qwen2.5-7B-Instruct"
        assert "q_proj" in cfg.lora_target_modules
        assert cfg.context_window >= 4096

    def test_get_model_config_known(self):
        cfg = get_model_config("qwen2.5:7b")
        assert cfg.ollama_tag == "qwen2.5:7b"

    def test_get_model_config_unknown_returns_generic(self):
        cfg = get_model_config("some-random-model:3b")
        assert cfg.ollama_tag == "some-random-model:3b"
        assert cfg.hf_model_id == ""  # unknown
        assert cfg.lora_target_modules == ["q_proj", "v_proj"]  # safe default

    def test_llama_config(self):
        cfg = MODEL_REGISTRY["llama3.1:8b"]
        assert cfg.hf_model_id == "meta-llama/Llama-3.1-8B-Instruct"
        assert "k_proj" in cfg.lora_target_modules

    def test_gemma_config(self):
        cfg = MODEL_REGISTRY["gemma2:9b"]
        assert cfg.hf_model_id == "google/gemma-2-9b-it"

    def test_resolve_config_from_env(self, monkeypatch):
        monkeypatch.setenv("ARCHMODEL_SURROGATE_MODEL", "llama3.1:8b")
        cfg = resolve_config()
        assert cfg.ollama_tag == "llama3.1:8b"

    def test_resolve_config_default(self, monkeypatch):
        monkeypatch.delenv("ARCHMODEL_SURROGATE_MODEL", raising=False)
        cfg = resolve_config(default="qwen2.5:7b")
        assert cfg.ollama_tag == "qwen2.5:7b"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_training/test_model_config.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/architecture_model/training/model_config.py
"""Model configuration registry for surrogate model swapping.

Provides pre-configured settings for tested models and supports
automatic resolution from environment variables or config files.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class ModelConfig:
    """Complete configuration for a surrogate model."""

    # Ollama model tag (e.g. "qwen2.5:7b")
    ollama_tag: str

    # HuggingFace model ID for LoRA training (e.g. "Qwen/Qwen2.5-7B-Instruct")
    # Empty string means model is not supported for LoRA fine-tuning
    hf_model_id: str = ""

    # LoRA target modules (architecture-specific attention projections)
    lora_target_modules: list[str] = field(default_factory=lambda: ["q_proj", "v_proj"])

    # Recommended LoRA rank for this model size
    lora_r: int = 16

    # LoRA alpha (typically 2x rank)
    lora_alpha: int = 32

    # Context window size (tokens) - affects prompt budgeting
    context_window: int = 8192

    # Whether this model tends to wrap output in markdown fences
    wraps_in_fences: bool = True

    # Notes about model behavior for architecture extraction
    notes: str = ""


# ---------------------------------------------------------------------------
# Pre-configured model registry
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, ModelConfig] = {
    "qwen2.5:7b": ModelConfig(
        ollama_tag="qwen2.5:7b",
        hf_model_id="Qwen/Qwen2.5-7B-Instruct",
        lora_target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_r=16,
        lora_alpha=32,
        context_window=32768,
        wraps_in_fences=True,
        notes="Good code comprehension; occasionally produces lowercase enums",
    ),
    "llama3.1:8b": ModelConfig(
        ollama_tag="llama3.1:8b",
        hf_model_id="meta-llama/Llama-3.1-8B-Instruct",
        lora_target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_r=16,
        lora_alpha=32,
        context_window=131072,
        wraps_in_fences=True,
        notes="Strong instruction following; 128K context; may over-generate entities",
    ),
    "gemma2:9b": ModelConfig(
        ollama_tag="gemma2:9b",
        hf_model_id="google/gemma-2-9b-it",
        lora_target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_r=16,
        lora_alpha=32,
        context_window=8192,
        wraps_in_fences=False,
        notes="Best structured YAML output; precise schema adherence; rarely wraps in fences",
    ),
}


def get_model_config(ollama_tag: str) -> ModelConfig:
    """Get config for a model by Ollama tag.

    Returns a pre-configured entry from the registry if available,
    otherwise returns a generic config with safe defaults.
    """
    if ollama_tag in MODEL_REGISTRY:
        return MODEL_REGISTRY[ollama_tag]

    # Generic fallback for unknown models
    return ModelConfig(
        ollama_tag=ollama_tag,
        hf_model_id="",
        lora_target_modules=["q_proj", "v_proj"],
        context_window=4096,
        wraps_in_fences=True,
        notes="Unknown model - using safe defaults",
    )


def resolve_config(
    default: str = "qwen2.5:7b",
    config_path: Optional[Path] = None,
) -> ModelConfig:
    """Resolve model config from environment, config file, or default.

    Priority order:
    1. ARCHMODEL_SURROGATE_MODEL environment variable
    2. .architecture-model-training.yaml in project root (if config_path given)
    3. default parameter
    """
    # 1. Environment variable
    env_model = os.environ.get("ARCHMODEL_SURROGATE_MODEL")
    if env_model:
        return get_model_config(env_model)

    # 2. Config file
    if config_path and config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text())
            if isinstance(data, dict) and "surrogate_model" in data:
                return get_model_config(data["surrogate_model"])
        except (yaml.YAMLError, OSError):
            pass

    # 3. Default
    return get_model_config(default)
```

**Step 4: Run tests**

Run: `pytest tests/test_training/test_model_config.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/training/model_config.py tests/test_training/test_model_config.py
git commit -m "feat(training): add ModelConfig registry with 3 tested models"
```

---

### Task 2: Wire ModelConfig into Surrogate and LoRATrainer

**Files:**
- Modify: `src/architecture_model/training/surrogate.py`
- Modify: `src/architecture_model/training/trainer.py`
- Test: `tests/test_training/test_model_config.py` (extend)

**Step 1: Write failing tests**

Append to `tests/test_training/test_model_config.py`:

```python
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
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_training/test_model_config.py::TestSurrogateModelConfig -v`
Expected: FAIL (TypeError - unexpected keyword argument)

**Step 3: Update Surrogate**

Replace `__init__`, `model_name` property, and `swap_model` in `surrogate.py`:

```python
from architecture_model.training.model_config import ModelConfig, get_model_config

class Surrogate:
    """Ollama client wrapper for local LLM architecture extraction."""

    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        host: str = "http://localhost:11434",
        model_config: Optional[ModelConfig] = None,
    ) -> None:
        if model_config is not None:
            self._config = model_config
        else:
            self._config = get_model_config(model_name)
        self._host = host

    @property
    def model_name(self) -> str:
        return self._config.ollama_tag

    @property
    def model_config(self) -> ModelConfig:
        return self._config

    def swap_model(self, new_model: str | ModelConfig) -> None:
        """Change the active model. Accepts Ollama tag string or ModelConfig."""
        if isinstance(new_model, ModelConfig):
            self._config = new_model
        else:
            self._config = get_model_config(new_model)
```

Keep `_model_name` references in `_chat()` updated to use `self._config.ollama_tag`.

**Step 4: Update LoRATrainer**

Add `model_config` param, `lora_target_modules` property, `needs_retrain`, `update_model()`:

```python
from architecture_model.training.model_config import ModelConfig, get_model_config

class LoRATrainer:
    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
        lora_r: int = 16,
        lora_alpha: int = 32,
        model_config: Optional[ModelConfig] = None,
    ) -> None:
        if model_config is not None:
            self._config = model_config
            self.base_model = model_config.hf_model_id
            self.lora_r = model_config.lora_r
            self.lora_alpha = model_config.lora_alpha
        else:
            self._config = None
            self.base_model = base_model
            self.lora_r = lora_r
            self.lora_alpha = lora_alpha
        self._needs_retrain = False

    @property
    def needs_retrain(self) -> bool:
        """True if base model changed since last training."""
        return self._needs_retrain

    @property
    def lora_target_modules(self) -> list[str]:
        """LoRA target modules for the current model."""
        if self._config:
            return self._config.lora_target_modules
        return ["q_proj", "v_proj"]

    def update_model(self, new_config: ModelConfig) -> None:
        """Switch base model. Marks existing adapters as stale."""
        if new_config.hf_model_id != self.base_model:
            self._needs_retrain = True
        self._config = new_config
        self.base_model = new_config.hf_model_id
        self.lora_r = new_config.lora_r
        self.lora_alpha = new_config.lora_alpha
```

Update `train()` to use `self.lora_target_modules` in `LoraConfig`.

**Step 5: Run tests**

Run: `pytest tests/test_training/test_model_config.py -v`
Expected: All PASS

**Step 6: Run full suite**

Run: `pytest tests/ --tb=short -q`
Expected: 284+ passed

**Step 7: Commit**

```bash
git add src/architecture_model/training/surrogate.py src/architecture_model/training/trainer.py \
        tests/test_training/test_model_config.py
git commit -m "feat(training): wire ModelConfig into Surrogate and LoRATrainer

Surrogate accepts model_config kwarg; swap_model() updates full config.
LoRATrainer.update_model() marks adapters stale on base model change.
Both maintain full backward compatibility with string model_name args."
```

---

### Task 3: Add config file support and update exports

**Files:**
- Modify: `src/architecture_model/training/__init__.py`
- Create: `.architecture-model-training.yaml.example`
- Test: `tests/test_training/test_model_config.py` (extend)

**Step 1: Write failing tests**

```python
class TestConfigFileResolution:
    def test_resolve_from_yaml_file(self, tmp_path):
        from architecture_model.training.model_config import resolve_config
        cfg_file = tmp_path / ".architecture-model-training.yaml"
        cfg_file.write_text("surrogate_model: gemma2:9b\n")
        result = resolve_config(config_path=cfg_file)
        assert result.ollama_tag == "gemma2:9b"

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        from architecture_model.training.model_config import resolve_config
        cfg_file = tmp_path / ".architecture-model-training.yaml"
        cfg_file.write_text("surrogate_model: gemma2:9b\n")
        monkeypatch.setenv("ARCHMODEL_SURROGATE_MODEL", "llama3.1:8b")
        result = resolve_config(config_path=cfg_file)
        assert result.ollama_tag == "llama3.1:8b"
```

**Step 2: These should pass already (resolve_config handles this)**

Run: `pytest tests/test_training/test_model_config.py::TestConfigFileResolution -v`
Expected: PASS

**Step 3: Update `__init__.py` exports**

Add to imports and `__all__`:
```python
from architecture_model.training.model_config import (
    ModelConfig, MODEL_REGISTRY, get_model_config, resolve_config,
)
```

**Step 4: Create example config file**

```yaml
# .architecture-model-training.yaml.example
# Copy to .architecture-model-training.yaml and customize.
#
# Model options (pre-tested):
#   qwen2.5:7b   — Good code comprehension, 32K context
#   llama3.1:8b  — Strong instruction following, 128K context
#   gemma2:9b    — Best structured YAML output, precise schema adherence
#
# Any Ollama model works — unregistered models use safe defaults.

surrogate_model: qwen2.5:7b
ollama_host: http://localhost:11434

# Oracle (via litellm — set API keys in environment)
# oracle_model: gpt-4o

# Training
# training_threshold: 50
# lora_output_dir: ./adapters/
```

**Step 5: Run full test suite**

Run: `pytest tests/ --tb=short -q`
Expected: 284+ passed

**Step 6: Commit**

```bash
git add src/architecture_model/training/__init__.py .architecture-model-training.yaml.example \
        tests/test_training/test_model_config.py
git commit -m "feat(training): export model config API and add example config file"
```

---

### Task 4: Model swap benchmark script

**Files:**
- Create: `scripts/test_model_swap.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python
"""Benchmark: compare extraction quality across surrogate models.

Usage:
    python scripts/test_model_swap.py

Requires models to be pulled in Ollama first:
    ollama pull qwen2.5:7b
    ollama pull llama3.1:8b
    ollama pull gemma2:9b
"""
import asyncio
import time
from pathlib import Path

from architecture_model.training.model_config import MODEL_REGISTRY
from architecture_model.training.surrogate import Surrogate
from architecture_model.training.context_builder import ContextBuilder
from architecture_model.training.multi_pass import MultiPassExtractor
from architecture_model.training.refiner import ModelRefiner
from architecture_model.core.validator import validate_model

HTTPX_ROOT = Path("/tmp/test-arch-model/httpx/httpx")


async def benchmark_model(ollama_tag: str) -> dict | None:
    """Run enhanced extraction with a specific model."""
    cfg = MODEL_REGISTRY.get(ollama_tag)
    if not cfg:
        print(f"  {ollama_tag}: NOT IN REGISTRY, skipping")
        return None

    surrogate = Surrogate(model_config=cfg)
    cb = ContextBuilder(HTTPX_ROOT)
    slices = cb.build()

    t0 = time.time()
    extractor = MultiPassExtractor(surrogate, slices, project_name="httpx")
    model = await extractor.extract()

    if model is None:
        print(f"  {ollama_tag}: extraction FAILED")
        return None

    refiner = ModelRefiner(surrogate, max_rounds=2)
    model = await refiner.refine(model, slices.combined())
    elapsed = time.time() - t0

    vr = validate_model(model)
    result = {
        "model": ollama_tag,
        "entities": model.entity_count,
        "relationships": len(model.relationships),
        "score": vr.score,
        "time": elapsed,
    }
    return result


async def main():
    print("=" * 60)
    print("MODEL SWAP BENCHMARK (httpx)")
    print("=" * 60)
    print(f"\nSource: {HTTPX_ROOT}")
    print(f"Models in registry: {list(MODEL_REGISTRY.keys())}\n")

    results = []
    for tag in MODEL_REGISTRY:
        print(f"Testing {tag}...")
        try:
            r = await benchmark_model(tag)
            if r:
                results.append(r)
                print(f"  -> {r['entities']} entities, {r['relationships']} rels, "
                      f"score {r['score']}/100, {r['time']:.1f}s\n")
        except Exception as e:
            print(f"  -> ERROR: {e}\n")

    if results:
        print("\n" + "=" * 60)
        print("COMPARISON")
        print("=" * 60)
        print(f"{'Model':<20} {'Entities':<12} {'Rels':<8} {'Score':<10} {'Time':<8}")
        print("-" * 58)
        for r in results:
            print(f"{r['model']:<20} {r['entities']:<12} {r['relationships']:<8} "
                  f"{r['score']}/100    {r['time']:.1f}s")

    print("\nNote: Training data in training.db is model-independent.")
    print("Swap models freely — only LoRA adapters need retraining.")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Commit**

```bash
git add scripts/test_model_swap.py
git commit -m "feat(training): add model swap benchmark script"
```

---

## Transferability Summary

After implementation, here's what transfers when you swap models:

| Asset | Transfers? | Notes |
|-------|-----------|-------|
| Training DB (oracle examples) | YES | Model-independent (input, output) pairs |
| Pipeline code | YES | All logic is model-agnostic |
| Deterministic relationships | YES | No LLM involved |
| Prompt engineering | YES | Works across model families |
| LoRA adapters | NO | Must retrain (cheap: minutes on GPU) |
| Model-specific quirks (fence stripping, enum fixes) | PARTIAL | Registry tracks per-model behavior |

To swap models at runtime:
```python
surrogate.swap_model("llama3.1:8b")  # updates config, LoRA targets, etc.
trainer.update_model(surrogate.model_config)  # marks adapters stale
trainer.needs_retrain  # -> True
```
