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
    from architecture_model.training.model_config import get_model_config

    cfg = get_model_config(ollama_tag)
    surrogate = Surrogate(model_config=cfg)

    if not HTTPX_ROOT.exists():
        print(f"  ERROR: {HTTPX_ROOT} not found. Clone httpx first:")
        print(f"    git clone https://github.com/encode/httpx /tmp/test-arch-model/httpx")
        return None

    cb = ContextBuilder(HTTPX_ROOT)
    slices = cb.build()

    print(f"  Extracting with {ollama_tag}...")
    t0 = time.time()

    try:
        extractor = MultiPassExtractor(surrogate, slices, project_name="httpx")
        model = await extractor.extract()
    except Exception as e:
        print(f"  EXTRACTION FAILED: {e}")
        return None

    if model is None:
        print(f"  Extraction returned None (model may not be available)")
        return None

    # Run refiner
    try:
        refiner = ModelRefiner(surrogate, max_rounds=2)
        model = await refiner.refine(model, slices.combined())
    except Exception as e:
        print(f"  Refiner failed (using unrefined): {e}")

    elapsed = time.time() - t0

    vr = validate_model(model)
    result = {
        "model": ollama_tag,
        "entities": model.entity_count,
        "relationships": len(model.relationships),
        "score": vr.score,
        "time": elapsed,
        "hf_id": cfg.hf_model_id,
        "context_window": cfg.context_window,
    }
    return result


async def main():
    print("=" * 64)
    print("MODEL SWAP BENCHMARK")
    print("=" * 64)
    print(f"\nSource: {HTTPX_ROOT}")
    print(f"Models in registry: {list(MODEL_REGISTRY.keys())}")
    print()

    results = []
    for tag in MODEL_REGISTRY:
        print(f"─── {tag} ───")
        try:
            r = await benchmark_model(tag)
            if r:
                results.append(r)
                print(f"  Entities:      {r['entities']}")
                print(f"  Relationships: {r['relationships']}")
                print(f"  Score:         {r['score']}/100")
                print(f"  Time:          {r['time']:.1f}s")
                print()
        except Exception as e:
            print(f"  ERROR: {e}\n")

    if len(results) > 1:
        print("\n" + "=" * 64)
        print("COMPARISON")
        print("=" * 64)
        print(f"  {'Model':<20} {'Entities':<10} {'Rels':<8} {'Score':<10} {'Time':<8}")
        print(f"  {'─' * 56}")
        for r in results:
            print(f"  {r['model']:<20} {r['entities']:<10} "
                  f"{r['relationships']:<8} {r['score']}/100    {r['time']:.1f}s")

    print("\n" + "─" * 64)
    print("TRANSFERABILITY NOTE:")
    print("  Training data (oracle examples in training.db) is model-independent.")
    print("  LoRA adapters are model-specific and must be retrained after swap.")
    print("  Swap cost: `ollama pull <model>` + re-run LoRA fine-tuning.")
    print("  All deterministic relationships and prompts carry over unchanged.")
    print("─" * 64)

    print("\nMULTI-ADAPTER TRAINING:")
    print("  Configure in .architecture-model-training.yaml:")
    print("    training_targets:")
    print("      - gemma2:9b")
    print("      - llama3.1:8b")
    print("  Or via env: ARCHMODEL_TRAINING_TARGETS=gemma2:9b,llama3.1:8b")
    print("  Adapters saved to: ./adapters/{model-tag}/")
    print("  Exported to Ollama as: {model-tag}-arch")


if __name__ == "__main__":
    asyncio.run(main())
