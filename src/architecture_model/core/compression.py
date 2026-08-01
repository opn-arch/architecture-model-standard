"""Compression statistics for architecture models.

Computes and formats token savings to demonstrate value to users.
"""
from __future__ import annotations

from pathlib import Path

SOURCE_EXTENSIONS = {"*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs", "*.java", "*.kt", "*.swift"}
EXCLUDE_DIRS = {"node_modules", ".git", "vendor", "_vendor", "vendored", "__pycache__", "dist", "build", ".venv", "venv"}
CHARS_PER_TOKEN = 4


def compute_compression_stats(root: Path) -> dict:
    """Compute compression ratio between source code and model representation."""
    source_bytes = _sum_source_size(root)
    model_bytes = _sum_model_size(root)

    source_tokens = source_bytes // CHARS_PER_TOKEN
    model_tokens = model_bytes // CHARS_PER_TOKEN
    tokens_saved = max(0, source_tokens - model_tokens)

    if model_bytes > 0:
        compression_ratio = round(source_bytes / model_bytes, 1)
    else:
        compression_ratio = 0.0

    return {
        "source_bytes": source_bytes,
        "model_bytes": model_bytes,
        "compression_ratio": compression_ratio,
        "source_tokens": source_tokens,
        "model_tokens": model_tokens,
        "tokens_saved": tokens_saved,
    }


def format_compression_summary(stats: dict) -> str:
    """Format stats as human-readable summary string."""
    if stats["compression_ratio"] == 0.0:
        return "No model found — run 'architecture-model init .' to generate."

    lines = [
        "--- Token Savings ---",
        f"  Source code: ~{stats['source_tokens']:,} tokens ({stats['source_bytes']:,} bytes)",
        f"  Model:       ~{stats['model_tokens']:,} tokens ({stats['model_bytes']:,} bytes)",
        f"  Compression: {stats['compression_ratio']}x ({stats['tokens_saved']:,} tokens saved)",
    ]

    ratio = stats["compression_ratio"]
    if ratio >= 50:
        lines.append(f"  Note: High compression ({ratio}x). Consider per-block slicing for accuracy.")
    elif ratio >= 10:
        lines.append(f"  Quality: Good compression range for accurate architecture reasoning.")

    return "\n".join(lines)


def _sum_source_size(root: Path) -> int:
    """Sum all source file sizes, excluding vendor/generated."""
    total = 0
    for ext in SOURCE_EXTENSIONS:
        for f in root.rglob(ext):
            if any(p in f.parts for p in EXCLUDE_DIRS):
                continue
            if ".architecture-models" in f.parts:
                continue
            try:
                total += f.stat().st_size
            except OSError:
                continue
    return total


def _sum_model_size(root: Path) -> int:
    """Sum architecture model file sizes."""
    total = 0
    models_dir = root / ".architecture-models"
    if models_dir.is_dir():
        for f in models_dir.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    continue

    for name in (".architecture-model-extracted.yaml", ".architecture-model.yaml"):
        candidate = root / name
        if candidate.is_file():
            try:
                total += candidate.stat().st_size
            except OSError:
                pass

    return total
