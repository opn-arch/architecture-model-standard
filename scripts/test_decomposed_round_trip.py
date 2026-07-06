#!/usr/bin/env python3
"""v1.3 Decomposed Round-Trip Test: oracle YAML → enrich → decompose → generate → compare.

Tests the full hierarchical decomposition + generation pipeline on a repo,
comparing decomposed (per-system) generation against baseline (single-call).

Usage:
    python scripts/test_decomposed_round_trip.py [--repo click] [--timeout 300]
    python scripts/test_decomposed_round_trip.py --all
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
from architecture_model.core.merger import enrich_from_manifest, compact_for_generation
from architecture_model.core.decomposer import (
    auto_assign_f_blocks,
    decompose_model,
    identify_systems,
    compute_complexity,
    SYSTEM_THRESHOLD,
)
from architecture_model.manifest.scanner import _scan_file
from architecture_model.training.code_structure import (
    parse_code_structure,
    parse_multi_file_code,
    StructuralGraph,
)
from architecture_model.training.hierarchical_generator import HierarchicalGenerator
from architecture_model.training.surrogate import Surrogate

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
# Metrics (same as test_enriched_round_trip.py)
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
# Helpers
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


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------


async def run_test(repo_name: str, timeout: int = 300):
    """Run the decomposed round-trip test for one repo."""
    print(f"\n{'='*70}")
    print(f"  v1.3 DECOMPOSED ROUND-TRIP TEST: {repo_name}")
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

    # 4. Enrich model with manifest data
    print("[4] Enriching model with manifest data...", end=" ")
    try:
        result = enrich_from_manifest(model, manifest)
        enriched_model = result.model
        naming_acc = result.naming_accuracy
        n_symbols = sum(len(c.symbols) for c in enriched_model.entities.components)
        n_functions = sum(len(c.functions) for c in enriched_model.entities.components)
        print(f"OK (naming_accuracy={naming_acc:.2f}, {n_symbols} symbols, {n_functions} functions)")
    except Exception as e:
        print(f"FAILED — {e}")
        return None

    # 5. Build functional_blocks for decomposition
    #    Auto-assign f_blocks if model doesn't have them (oracle-extracted models)
    enriched_model = auto_assign_f_blocks(enriched_model)
    fblocks = {}
    for comp in enriched_model.entities.components:
        if comp.f_block and comp.f_block not in fblocks:
            fblocks[comp.f_block] = {"name": comp.f_block}
    manifest["functional_blocks"] = fblocks

    # 6. Decompose
    print("[5] Decomposing model (identify systems)...", end=" ")
    try:
        decomposition = decompose_model(enriched_model, manifest)
        n_systems = len(decomposition.top_level.entities.systems)
        n_remaining = len(decomposition.top_level.entities.components)
        print(f"OK ({n_systems} systems, {n_remaining} remaining components)")

        if n_systems > 0:
            print(f"\n    {'System':<30} {'Components':>10} {'Complexity':>10}")
            print(f"    {'─'*50}")
            for sys in decomposition.top_level.entities.systems:
                sub = decomposition.sub_models.get(sys.id)
                n_sub_comps = len(sub.entities.components) if sub else 0
                print(f"    {sys.name:<30} {n_sub_comps:>10} {sys.complexity_score:>10.1f}")
            print()
    except Exception as e:
        print(f"FAILED — {e}")
        import traceback; traceback.print_exc()
        return None

    # 7. Load real source as StructuralGraph (ground truth)
    print("[6] Loading real source as StructuralGraph...", end=" ")
    original_graph = load_repo_source(repo_name)
    print(
        f"OK (C:{len(original_graph.class_names)} M:{len(original_graph.method_names)} "
        f"F:{len(original_graph.function_names)} Mod:{len(original_graph.modules)})"
    )

    surrogate = Surrogate(model_name="qwen2.5:7b")

    # 8. BASELINE: compact single-call generation (non-decomposed)
    print(f"\n[7a] BASELINE: compact single-call generation (timeout={timeout}s)...", end=" ", flush=True)
    baseline_score = None
    baseline_time = 0.0
    try:
        gen_model = compact_for_generation(enriched_model)
        gen_dict = dump_model(gen_model)
        gen_yaml = pyyaml.dump(gen_dict, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)

        t0 = time.time()
        baseline_code = await asyncio.wait_for(
            surrogate.generate_code(gen_yaml),
            timeout=timeout,
        )
        baseline_time = time.time() - t0

        if baseline_code:
            baseline_graph = parse_multi_file_code(baseline_code)
            if not baseline_graph.classes and not baseline_graph.functions:
                baseline_graph = parse_code_structure(baseline_code, "generated")
            baseline_score = compute_score(original_graph, baseline_graph)
            print(f"OK (overall={baseline_score['overall']:.3f}, {baseline_time:.1f}s)")
        else:
            print("EMPTY")
    except asyncio.TimeoutError:
        print("TIMEOUT")
    except Exception as e:
        print(f"ERROR: {e}")

    # 9. DECOMPOSED: per-system hierarchical generation
    print(f"[7b] DECOMPOSED: hierarchical per-system generation (timeout={timeout}s)...", flush=True)
    decomposed_score = None
    decomposed_time = 0.0
    system_times: dict[str, float] = {}

    if n_systems == 0:
        print("     SKIPPED (no systems identified — model too simple for decomposition)")
    else:
        try:
            gen = HierarchicalGenerator(surrogate)
            t0 = time.time()
            decomposed_code = await asyncio.wait_for(
                gen.generate(decomposition),
                timeout=timeout * (n_systems + 1),  # Scale timeout with systems
            )
            decomposed_time = time.time() - t0

            if decomposed_code:
                decomposed_graph = parse_multi_file_code(decomposed_code)
                if not decomposed_graph.classes and not decomposed_graph.functions:
                    decomposed_graph = parse_code_structure(decomposed_code, "generated")
                decomposed_score = compute_score(original_graph, decomposed_graph)
                print(f"     OK (overall={decomposed_score['overall']:.3f}, {decomposed_time:.1f}s total)")
                # Estimate per-system time (uniform split for simplicity)
                avg_per_system = decomposed_time / (n_systems + (1 if n_remaining > 0 else 0))
                for sys in decomposition.top_level.entities.systems:
                    system_times[sys.name] = avg_per_system
            else:
                print("     EMPTY")
        except asyncio.TimeoutError:
            print("     TIMEOUT")
        except Exception as e:
            print(f"     ERROR: {e}")

    # 10. Report comparison
    print(f"\n{'─'*70}")
    print("  RESULTS COMPARISON: BASELINE vs DECOMPOSED")
    print(f"{'─'*70}")

    def fmt(v):
        if v is None:
            return "  N/A "
        if isinstance(v, float) and math.isnan(v):
            return "  -  "
        return f"{v:6.3f}"

    header = f"{'Metric':<22} {'BASELINE':>8} {'DECOMPOSED':>10} {'Delta':>8}"
    print(header)
    print("─" * len(header))

    if baseline_score and decomposed_score:
        for key in ["class_overlap", "fuzzy_class", "method_overlap", "function_overlap",
                    "module_name_overlap", "module_count_ratio", "overall"]:
            bv = baseline_score.get(key, float("nan"))
            dv = decomposed_score.get(key, float("nan"))
            delta = ""
            if not math.isnan(bv) and not math.isnan(dv):
                d = dv - bv
                delta = f"{d:+6.3f}" if d != 0 else "     0"
            print(f"  {key:<20} {fmt(bv):>8} {fmt(dv):>10} {delta:>8}")

        print(f"\n  Baseline time:    {baseline_time:.1f}s")
        print(f"  Decomposed time:  {decomposed_time:.1f}s (across {n_systems} systems)")
        if system_times:
            print(f"  Avg per system:   {sum(system_times.values())/len(system_times):.1f}s")
    elif baseline_score:
        print("  (Decomposed generation failed — baseline only)")
        for key in ["class_overlap", "fuzzy_class", "method_overlap", "function_overlap",
                    "module_name_overlap", "module_count_ratio", "overall"]:
            bv = baseline_score.get(key, float("nan"))
            print(f"  {key:<20} {fmt(bv):>8}       -   ")
    elif decomposed_score:
        print("  (Baseline failed — decomposed only)")
        for key in ["class_overlap", "fuzzy_class", "method_overlap", "function_overlap",
                    "module_name_overlap", "module_count_ratio", "overall"]:
            dv = decomposed_score.get(key, float("nan"))
            print(f"  {key:<20}      -    {fmt(dv):>10}")
    else:
        print("  Both generation attempts failed or timed out.")

    # 11. Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    result_data = {
        "test": "v1.3_decomposed_round_trip",
        "timestamp": ts,
        "repo": repo_name,
        "naming_accuracy": naming_acc,
        "decomposition": {
            "n_systems": n_systems,
            "n_remaining_components": n_remaining,
            "systems": [
                {
                    "name": sys.name,
                    "complexity_score": sys.complexity_score,
                    "n_components": len(sys.component_ids),
                }
                for sys in decomposition.top_level.entities.systems
            ],
        },
        "baseline_score": baseline_score,
        "decomposed_score": decomposed_score,
        "timing": {
            "baseline_seconds": baseline_time,
            "decomposed_seconds": decomposed_time,
            "per_system": system_times,
        },
        "improvement": None,
    }
    if baseline_score and decomposed_score:
        result_data["improvement"] = decomposed_score["overall"] - baseline_score["overall"]

    out_path = RESULTS_DIR / f"decomposed_round_trip_{repo_name}_{ts}.json"
    out_path.write_text(json.dumps(result_data, indent=2, default=str))
    print(f"\nResults saved: {out_path}")

    return result_data


async def main():
    parser = argparse.ArgumentParser(description="v1.3 Decomposed Round-Trip Test")
    parser.add_argument("--repo", default="click", help="Repo to test (default: click)")
    parser.add_argument("--timeout", type=int, default=300, help="Generation timeout per call (seconds)")
    parser.add_argument("--all", action="store_true", help="Run all repos in batch")
    parser.add_argument("--sample", type=int, default=None, help="Random sample of N repos")
    args = parser.parse_args()

    if args.all:
        repos = list(REPO_SUBDIRS.keys())
    elif args.sample:
        import random
        repos = random.sample(list(REPO_SUBDIRS.keys()), min(args.sample, len(REPO_SUBDIRS)))
    else:
        repos = [args.repo]

    all_results = []
    for repo in repos:
        result = await run_test(repo, args.timeout)
        if result:
            all_results.append(result)

    if len(all_results) > 1:
        # Print aggregate summary
        print(f"\n{'='*70}")
        print(f"  AGGREGATE RESULTS ({len(all_results)} repos)")
        print(f"{'='*70}")

        baseline_scores = [
            r["baseline_score"]["overall"]
            for r in all_results
            if r.get("baseline_score") and "overall" in r["baseline_score"]
        ]
        decomposed_scores = [
            r["decomposed_score"]["overall"]
            for r in all_results
            if r.get("decomposed_score") and "overall" in r["decomposed_score"]
        ]
        improvements = [r["improvement"] for r in all_results if r.get("improvement") is not None]

        if baseline_scores:
            print(f"  BASELINE mean:     {sum(baseline_scores)/len(baseline_scores):.3f} (n={len(baseline_scores)})")
        if decomposed_scores:
            print(f"  DECOMPOSED mean:   {sum(decomposed_scores)/len(decomposed_scores):.3f} (n={len(decomposed_scores)})")
        if improvements:
            print(f"  Mean improvement:  {sum(improvements)/len(improvements):+.3f}")
            print(f"  Min improvement:   {min(improvements):+.3f}")
            print(f"  Max improvement:   {max(improvements):+.3f}")

        # Save aggregate
        RESULTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        agg_path = RESULTS_DIR / f"decomposed_batch_{ts}.json"
        agg_path.write_text(json.dumps({
            "test": "v1.3_decomposed_batch",
            "timestamp": ts,
            "n_repos": len(all_results),
            "aggregate": {
                "baseline_mean": sum(baseline_scores)/len(baseline_scores) if baseline_scores else None,
                "decomposed_mean": sum(decomposed_scores)/len(decomposed_scores) if decomposed_scores else None,
                "mean_improvement": sum(improvements)/len(improvements) if improvements else None,
            },
            "results": all_results,
        }, indent=2, default=str))
        print(f"\n  Batch results saved: {agg_path}")


if __name__ == "__main__":
    asyncio.run(main())
