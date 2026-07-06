#!/usr/bin/env python3
"""v1.2 Enriched Round-Trip Test: oracle YAML → enrich → generate → compare.

Tests the Schema v1.2 enrichment pipeline end-to-end on a single repo (python-dotenv)
to validate that enriched models produce better code generation than raw models.

Usage: python scripts/test_enriched_round_trip.py [--repo REPO] [--timeout SECS]
"""

import argparse
import asyncio
import json
import math
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml as pyyaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from architecture_model.core.parser import _parse_raw, dump_model
from architecture_model.core.merger import enrich_from_manifest
from architecture_model.manifest.scanner import _scan_file, _extract_classes
from architecture_model.training.code_structure import (
    parse_code_structure,
    parse_multi_file_code,
    StructuralGraph,
)
from architecture_model.training.surrogate import Surrogate, _GENERATE_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = Path("data/training.db")
CLONE_DIR = Path("/tmp/test-repos")
RESULTS_DIR = Path("results")

REPO_SUBDIRS = {
    "click": "src/click",
    "typer": "typer",
    "httpcore": "httpcore",
    "anyio": "src/anyio",
    "python-dotenv": "src/dotenv",
    "colorama": "colorama",
    "tqdm": "tqdm",
    "attrs": "src",
    "structlog": "src/structlog",
    "pydantic": "pydantic",
    "fastapi": "fastapi",
    "rich": "rich",
    "httpx": "httpx",
    "black": "src/black",
    "marshmallow": "src/marshmallow",
    "flask": "src/flask",
    "jinja": "src/jinja2",
    "starlette": "starlette",
    "arrow": "arrow",
}


# ---------------------------------------------------------------------------
# Manifest builder (lightweight — no config needed)
# ---------------------------------------------------------------------------


def build_manifest_for_repo(repo_name: str) -> dict:
    """Build a manifest-like dict by scanning repo source files directly."""
    subdir = REPO_SUBDIRS.get(repo_name, repo_name)
    repo_root = CLONE_DIR / repo_name
    src_dir = repo_root / subdir

    if not src_dir.exists():
        src_dir = repo_root
    if not src_dir.exists():
        raise FileNotFoundError(f"Repo source not found: {src_dir}")

    modules = []
    py_files = sorted(src_dir.rglob("*.py"))[:100]

    for f in py_files:
        try:
            meta = _scan_file(repo_root, f)
            modules.append(meta)
        except Exception:
            continue

    return {"modules": modules, "interfaces": []}


# ---------------------------------------------------------------------------
# Metrics (same as test_round_trip.py)
# ---------------------------------------------------------------------------


def jaccard(set_a: set, set_b: set) -> float:
    if not set_a:
        return float("nan")
    if not set_b:
        return 0.0
    a = {s.lower() for s in set_a}
    b = {s.lower() for s in set_b}
    return len(a & b) / len(a | b) if (a | b) else 0.0


def fuzzy_class_match(orig_classes: set, gen_classes: set) -> float:
    if not orig_classes:
        return float("nan")
    if not gen_classes:
        return 0.0
    orig_lower = {s.lower() for s in orig_classes}
    gen_lower = {s.lower() for s in gen_classes}
    matched = 0
    for orig in orig_lower:
        for gen in gen_lower:
            if orig == gen:
                matched += 1
                break
            if len(orig) >= 4 and orig in gen:
                matched += 1
                break
            if len(gen) >= 4 and gen in orig:
                matched += 1
                break
    return matched / len(orig_lower)


def module_count_ratio(orig: list, gen: list) -> float:
    a, b = len(orig), len(gen)
    if a == 0:
        return float("nan")
    if b == 0:
        return 0.0
    return min(a, b) / max(a, b)


def module_name_overlap(orig_modules: list, gen_modules: list) -> float:
    if not orig_modules:
        return float("nan")
    if not gen_modules:
        return 0.0

    def normalize(mod: str) -> set:
        mod_l = mod.lower().strip()
        parts = mod_l.split(".")
        names = {mod_l}
        if parts:
            names.add(parts[-1])
        if len(parts) >= 2:
            names.add(".".join(parts[-2:]))
        return names

    gen_names = set()
    for g in gen_modules:
        gen_names.update(normalize(g))

    matched = 0
    for orig in orig_modules:
        if normalize(orig) & gen_names:
            matched += 1
    return matched / len(orig_modules)


def compute_score(original: StructuralGraph, generated: StructuralGraph) -> dict:
    metrics = {
        "class_overlap": jaccard(original.class_names, generated.class_names),
        "fuzzy_class": fuzzy_class_match(original.class_names, generated.class_names),
        "method_overlap": jaccard(original.method_names, generated.method_names),
        "function_overlap": jaccard(original.function_names, generated.function_names),
        "module_name_overlap": module_name_overlap(original.modules, generated.modules),
        "module_count_ratio": module_count_ratio(original.modules, generated.modules),
    }

    weights = {
        "class_overlap": 0.15,
        "fuzzy_class": 0.15,
        "method_overlap": 0.15,
        "function_overlap": 0.10,
        "module_name_overlap": 0.25,
        "module_count_ratio": 0.20,
    }

    total_w = 0.0
    weighted_sum = 0.0
    for key, w in weights.items():
        val = metrics[key]
        if not math.isnan(val):
            weighted_sum += w * val
            total_w += w
    metrics["overall"] = weighted_sum / total_w if total_w > 0 else 0.0
    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_oracle_yaml(repo_name: str) -> str | None:
    """Load oracle-extracted YAML from training DB."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """SELECT oracle_output FROM training_examples
           WHERE repo_url LIKE ? AND oracle_output IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (f"%{repo_name}%",),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def strip_fences(text: str) -> str:
    if "```python" in text:
        text = text.split("```python", 1)[1].split("```", 1)[0]
    elif "```yaml" in text:
        text = text.split("```yaml", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return text.strip()


def load_repo_source(repo_name: str) -> StructuralGraph:
    """Load real source from cloned repo into a StructuralGraph."""
    subdir = REPO_SUBDIRS.get(repo_name, repo_name)
    repo_path = CLONE_DIR / repo_name / subdir

    if not repo_path.exists():
        repo_path = CLONE_DIR / repo_name
    if not repo_path.exists():
        return StructuralGraph()

    parts = []
    for f in sorted(repo_path.rglob("*.py"))[:100]:
        try:
            content = f.read_text(errors="ignore")
            rel_path = f.relative_to(repo_path.parent)
            parts.append(f"# {rel_path}\n{content}")
        except (OSError, ValueError):
            continue
    if not parts:
        return StructuralGraph()
    return parse_multi_file_code("\n\n".join(parts))


async def run_test(repo_name: str, timeout: int = 300):
    """Run the enriched round-trip test for one repo."""
    print(f"\n{'='*70}")
    print(f"  v1.2 ENRICHED ROUND-TRIP TEST: {repo_name}")
    print(f"{'='*70}")

    # 1. Load oracle YAML
    print("\n[1] Loading oracle YAML from DB...", end=" ")
    oracle_yaml = load_oracle_yaml(repo_name)
    if not oracle_yaml:
        print("FAILED — no oracle output found")
        return None
    print(f"OK ({len(oracle_yaml)} chars)")

    # 2. Parse into ArchitectureModel
    print("[2] Parsing into ArchitectureModel...", end=" ")
    try:
        raw_dict = pyyaml.safe_load(oracle_yaml)
        model = _parse_raw(raw_dict)
        n_comp = len(model.entities.components)
        n_rel = len(model.relationships)
        print(f"OK ({n_comp} components, {n_rel} relationships)")
    except Exception as e:
        print(f"FAILED — {e}")
        import traceback; traceback.print_exc()
        return None

    # 3. Build manifest from real source
    print("[3] Building manifest from source (AST scan)...", end=" ")
    try:
        manifest = build_manifest_for_repo(repo_name)
        n_mods = len(manifest["modules"])
        total_classes = sum(len(m.get("classes", [])) for m in manifest["modules"])
        print(f"OK ({n_mods} modules, {total_classes} classes)")
    except Exception as e:
        print(f"FAILED — {e}")
        return None

    # 4. Enrich model
    print("[4] Enriching model with manifest data...", end=" ")
    try:
        result = enrich_from_manifest(model, manifest)
        enriched_model = result.model
        naming_acc = result.naming_accuracy

        # Count enriched fields
        n_symbols = sum(len(c.symbols) for c in enriched_model.entities.components)
        n_functions = sum(len(c.functions) for c in enriched_model.entities.components)
        n_imports = sum(len(r.imports) for r in enriched_model.relationships if r.imports)
        print(f"OK (naming_accuracy={naming_acc:.2f}, {n_symbols} symbols, {n_functions} functions, {n_imports} import entries)")
    except Exception as e:
        print(f"FAILED — {e}")
        import traceback; traceback.print_exc()
        return None

    # 5. Dump enriched YAML
    print("[5] Serializing enriched model to YAML...", end=" ")
    try:
        enriched_dict = dump_model(enriched_model)
        enriched_yaml = pyyaml.dump(enriched_dict, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)
        print(f"OK ({len(enriched_yaml)} chars)")
    except Exception as e:
        print(f"FAILED — {e}")
        import traceback; traceback.print_exc()
        return None

    # 6. Load real source as StructuralGraph (ground truth)
    print("[6] Loading real source as StructuralGraph...", end=" ")
    original_graph = load_repo_source(repo_name)
    print(
        f"OK (C:{len(original_graph.class_names)} M:{len(original_graph.method_names)} "
        f"F:{len(original_graph.function_names)} Mod:{len(original_graph.modules)})"
    )

    # 7a. Generate code from RAW oracle YAML (baseline)
    print(f"[7a] Generating code from RAW YAML (qwen2.5:7b, timeout={timeout}s)...", end=" ", flush=True)
    surrogate = Surrogate(model_name="qwen2.5:7b")
    raw_score = None
    try:
        raw_code = await asyncio.wait_for(
            surrogate.generate_code(oracle_yaml),
            timeout=timeout,
        )
        if raw_code:
            raw_graph = parse_multi_file_code(raw_code)
            if not raw_graph.classes and not raw_graph.functions:
                raw_graph = parse_code_structure(raw_code, "generated")
            raw_score = compute_score(original_graph, raw_graph)
            print(f"OK (overall={raw_score['overall']:.3f})")
        else:
            print("EMPTY")
    except asyncio.TimeoutError:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")

    # 7b. Generate code from ENRICHED YAML
    print(f"[7b] Generating code from ENRICHED YAML (qwen2.5:7b, timeout={timeout}s)...", end=" ", flush=True)
    enriched_score = None
    try:
        enriched_code = await asyncio.wait_for(
            surrogate.generate_code(enriched_yaml),
            timeout=timeout,
        )
        if enriched_code:
            enriched_graph = parse_multi_file_code(enriched_code)
            if not enriched_graph.classes and not enriched_graph.functions:
                enriched_graph = parse_code_structure(enriched_code, "generated")
            enriched_score = compute_score(original_graph, enriched_graph)
            print(f"OK (overall={enriched_score['overall']:.3f})")
        else:
            print("EMPTY")
    except asyncio.TimeoutError:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")

    # 8. Report comparison
    print(f"\n{'─'*70}")
    print("  RESULTS COMPARISON")
    print(f"{'─'*70}")

    def fmt(v):
        if v is None:
            return "  N/A "
        if isinstance(v, float) and math.isnan(v):
            return "  -  "
        return f"{v:6.3f}"

    header = f"{'Metric':<22} {'RAW':>8} {'ENRICHED':>8} {'Delta':>8}"
    print(header)
    print("─" * len(header))

    if raw_score and enriched_score:
        for key in ["class_overlap", "fuzzy_class", "method_overlap", "function_overlap",
                    "module_name_overlap", "module_count_ratio", "overall"]:
            rv = raw_score.get(key, float("nan"))
            ev = enriched_score.get(key, float("nan"))
            delta = ""
            if not math.isnan(rv) and not math.isnan(ev):
                d = ev - rv
                delta = f"{d:+6.3f}" if d != 0 else "     0"
            print(f"  {key:<20} {fmt(rv):>8} {fmt(ev):>8} {delta:>8}")
    elif enriched_score:
        print("  (RAW baseline unavailable — enriched only)")
        for key in ["class_overlap", "fuzzy_class", "method_overlap", "function_overlap",
                    "module_name_overlap", "module_count_ratio", "overall"]:
            ev = enriched_score.get(key, float("nan"))
            print(f"  {key:<20}    -    {fmt(ev):>8}")
    else:
        print("  Both generation attempts failed or timed out.")

    # 9. Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    result_data = {
        "test": "v1.2_enriched_round_trip",
        "timestamp": ts,
        "repo": repo_name,
        "naming_accuracy": naming_acc,
        "enrichment_stats": {
            "symbols": n_symbols,
            "functions": n_functions,
            "import_entries": n_imports,
        },
        "raw_score": raw_score,
        "enriched_score": enriched_score,
        "improvement": None,
    }
    if raw_score and enriched_score:
        result_data["improvement"] = enriched_score["overall"] - raw_score["overall"]

    out_path = RESULTS_DIR / f"enriched_round_trip_{repo_name}_{ts}.json"
    out_path.write_text(json.dumps(result_data, indent=2, default=str))
    print(f"\nResults saved: {out_path}")

    return result_data


async def main():
    parser = argparse.ArgumentParser(description="v1.2 Enriched Round-Trip Test")
    parser.add_argument("--repo", default="python-dotenv", help="Repo to test")
    parser.add_argument("--timeout", type=int, default=300, help="Generation timeout (seconds)")
    args = parser.parse_args()

    await run_test(args.repo, args.timeout)


if __name__ == "__main__":
    asyncio.run(main())
