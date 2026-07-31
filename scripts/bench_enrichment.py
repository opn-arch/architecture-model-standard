#!/usr/bin/env python3
"""Benchmark auto-enrichment on any repository.

Usage: python scripts/bench_enrichment.py /path/to/repo
"""
import sys
from pathlib import Path

from architecture_model.manifest.generator import generate_manifest
from architecture_model.core.parser import load_model
from architecture_model.core.confidence import model_confidence_summary
from architecture_model.orchestration.auto_enrich import enrich_from_manifest


def main():
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    model_path = Path(repo_path) / ".architecture-model.yaml"

    if not model_path.exists():
        print(f"No .architecture-model.yaml found in {repo_path}")
        sys.exit(1)

    print(f"Scanning {repo_path}...")
    manifest = generate_manifest(repo_path)
    print(f"  Found {len(manifest.modules)} modules")

    model = load_model(str(model_path))

    # Before
    before = model_confidence_summary(model)
    print(f"\nBefore enrichment:")
    print(f"  Overall: {before['overall']:.0%}")
    for block in before.get("blocks", []):
        print(f"  {block['name']}: {block['confidence']:.0%}")

    # Enrich
    enrich_from_manifest(model, manifest)

    # After
    after = model_confidence_summary(model)
    print(f"\nAfter enrichment:")
    print(f"  Overall: {after['overall']:.0%}")
    for block in after.get("blocks", []):
        print(f"  {block['name']}: {block['confidence']:.0%}")

    delta = after["overall"] - before["overall"]
    print(f"\n  Δ confidence: +{delta:.0%}")


if __name__ == "__main__":
    main()
