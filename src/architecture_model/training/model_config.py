"""ModelConfig dataclass and MODEL_REGISTRY for surrogate model selection.

Provides a frozen configuration bundle for each supported model, a lookup
function with safe fallback, and a resolution function that checks env vars
and YAML config files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass(frozen=True)
class ModelConfig:
    """Immutable configuration bundle for a surrogate model."""

    ollama_tag: str
    hf_model_id: str = ""
    lora_target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    lora_r: int = 16
    lora_alpha: int = 32
    context_window: int = 4096
    wraps_in_fences: bool = False
    notes: str = ""


MODEL_REGISTRY: Dict[str, ModelConfig] = {
    "qwen2.5:7b": ModelConfig(
        ollama_tag="qwen2.5:7b",
        hf_model_id="Qwen/Qwen2.5-7B-Instruct",
        lora_target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        context_window=32768,
        wraps_in_fences=True,
    ),
    "llama3.1:8b": ModelConfig(
        ollama_tag="llama3.1:8b",
        hf_model_id="meta-llama/Llama-3.1-8B-Instruct",
        lora_target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        context_window=131072,
        wraps_in_fences=True,
    ),
    "gemma2:9b": ModelConfig(
        ollama_tag="gemma2:9b",
        hf_model_id="google/gemma-2-9b-it",
        lora_target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        context_window=8192,
        wraps_in_fences=False,
    ),
}


def get_model_config(ollama_tag: str) -> ModelConfig:
    """Return registry entry for *ollama_tag*, or a generic fallback with safe defaults."""
    if ollama_tag in MODEL_REGISTRY:
        return MODEL_REGISTRY[ollama_tag]
    return ModelConfig(ollama_tag=ollama_tag)


def resolve_config(
    default: str = "gemma2:9b",
    config_path: Optional[str] = None,
) -> ModelConfig:
    """Resolve model config from env var, YAML file, or default (in priority order).

    Priority:
      1. ARCHMODEL_SURROGATE_MODEL environment variable (highest)
      2. YAML config file at *config_path* (key: ``surrogate_model``)
      3. *default* parameter
    """
    # 1. Environment variable (highest priority)
    env_tag = os.environ.get("ARCHMODEL_SURROGATE_MODEL")
    if env_tag:
        return get_model_config(env_tag)

    # 2. YAML config file
    if config_path:
        path = Path(config_path)
        if path.is_file():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            tag = data.get("surrogate_model")
            if tag:
                return get_model_config(tag)

    # 3. Default
    return get_model_config(default)
