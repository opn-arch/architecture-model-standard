#!/usr/bin/env python3
"""Full autoencoder round-trip test v2: model → code → compare with REAL source.

For each repo in the training database:
1. Load oracle-extracted architecture model YAML
2. Generate code from the model via surrogate (qwen2.5:7b) AND copilot-relay
3. Load REAL source code from cloned repos (not DB context)
4. Parse both into StructuralGraphs (AST)
5. Compute RoundTripScore with fixed metrics (NaN-aware, module overlap, fuzzy class)
6. Report per-repo metrics + aggregates

Usage: python scripts/test_round_trip.py [--limit N] [--surrogate-only] [--copilot-only]
"""

import argparse
import asyncio
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import aiohttp
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import ArchitectureModel
from architecture_model.training.code_structure import (
    parse_code_structure,
    parse_multi_file_code,
    StructuralGraph,
)
from architecture_model.training.surrogate import Surrogate, _GENERATE_SYSTEM_PROMPT

# Try importing semantic matcher (needs Ollama with nomic-embed-text)
try:
    from architecture_model.training.semantic_matcher import SemanticMatcher

    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COPILOT_RELAY_URL = "http://localhost:8400/chat"
DB_PATH = "data/training.db"
RESULTS_DIR = Path("results")
CLONE_DIR = Path("/tmp/test-repos")

# Repo subdir mappings (matching test_multi_repo.py config)
REPO_SUBDIRS = {
    "click": "src/click",
    "typer": "typer",
    "httpcore": "httpcore",
    "anyio": "src/anyio",
    "python-dotenv": "src/dotenv",
    "colorama": "colorama",
    "tqdm": "tqdm",
    "attrs": "src",  # Fixed: both src/attr and src/attrs
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
# Helpers
# ---------------------------------------------------------------------------


def strip_fences(text: str) -> str:
    """Strip markdown code fences from response."""
    if "```python" in text:
        text = text.split("```python", 1)[1].split("```", 1)[0]
    elif "```yaml" in text:
        text = text.split("```yaml", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return text.strip()


async def call_copilot_relay(content: str, system_prompt: str, timeout: int = 180) -> str:
    """Call copilot-relay SSE endpoint and collect full response."""
    payload = {"content": content, "system_prompt": system_prompt}

    full_response: list[str] = []
    async with aiohttp.ClientSession() as session:
        async with session.post(
            COPILOT_RELAY_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Copilot-relay returned {resp.status}: {await resp.text()}")

            buffer = ""
            async for line in resp.content:
                decoded = line.decode("utf-8")
                buffer += decoded

                while "\n" in buffer:
                    line_text, buffer = buffer.split("\n", 1)
                    line_text = line_text.strip()

                    if line_text.startswith("data: "):
                        data_str = line_text[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "chunk":
                                chunk = data.get("content", "")
                                if chunk:
                                    full_response.append(chunk)
                            elif "choices" in data:
                                choices = data["choices"]
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    chunk = delta.get("content", "")
                                    if chunk:
                                        full_response.append(chunk)
                        except json.JSONDecodeError:
                            continue

    return "".join(full_response)


# ---------------------------------------------------------------------------
# Fixed Metrics (NaN-aware)
# ---------------------------------------------------------------------------


def jaccard(set_a: set, set_b: set) -> float:
    """Case-insensitive Jaccard similarity.

    Returns NaN if original (set_a) is empty — metric not applicable.
    Returns 0.0 if original non-empty but generated (set_b) is empty.
    """
    if not set_a:
        return float("nan")  # Original has nothing — metric N/A
    if not set_b:
        return 0.0  # Generated failed to produce anything
    a = {s.lower() for s in set_a}
    b = {s.lower() for s in set_b}
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


def fuzzy_class_match(orig_classes: set, gen_classes: set) -> float:
    """Fuzzy class name matching — handles prefix/suffix/substring overlap.

    For each original class name, check if any generated class name is:
    - Exact match (case-insensitive)
    - Substring match (one contains the other, min 4 chars)

    Returns recall: fraction of original classes matched.
    Returns NaN if original is empty.
    """
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
            # Substring: "session" in "securecookiesession"
            if len(orig) >= 4 and orig in gen:
                matched += 1
                break
            if len(gen) >= 4 and gen in orig:
                matched += 1
                break
    return matched / len(orig_lower)


def import_overlap(orig_imports: set, gen_imports: set) -> float:
    """Fraction of original imports found in generated (partial suffix match).

    Returns NaN if original is empty.
    """
    if not orig_imports:
        return float("nan")
    if not gen_imports:
        return 0.0

    matched = 0
    for orig_mod in orig_imports:
        orig_lower = orig_mod.lower()
        for gen_mod in gen_imports:
            gen_lower = gen_mod.lower()
            if (
                orig_lower == gen_lower
                or orig_lower.endswith(f".{gen_lower}")
                or gen_lower.endswith(f".{orig_lower}")
            ):
                matched += 1
                break
    return matched / len(orig_imports)


def module_name_overlap(orig_modules: list, gen_modules: list) -> float:
    """Module-level comparison: fraction of original modules found in generated.

    Uses suffix matching: 'flask.app' matches 'app', 'app.py' markers, etc.
    Returns NaN if original is empty.
    """
    if not orig_modules:
        return float("nan")
    if not gen_modules:
        return 0.0

    def normalize(mod: str) -> set:
        """Return set of possible matching names for a module."""
        mod_l = mod.lower().strip()
        parts = mod_l.split(".")
        names = {mod_l}
        # Last part (e.g., 'app' from 'flask.app')
        if parts:
            names.add(parts[-1])
        # Last two parts
        if len(parts) >= 2:
            names.add(".".join(parts[-2:]))
        return names

    gen_names = set()
    for g in gen_modules:
        gen_names.update(normalize(g))

    matched = 0
    for orig in orig_modules:
        orig_names = normalize(orig)
        if orig_names & gen_names:
            matched += 1

    return matched / len(orig_modules)


def module_count_ratio(orig_modules: list, gen_modules: list) -> float:
    """min(a,b)/max(a,b) for module counts. NaN if original is empty."""
    a, b = len(orig_modules), len(gen_modules)
    if a == 0:
        return float("nan")
    if b == 0:
        return 0.0
    return min(a, b) / max(a, b)


def compute_round_trip_score(
    original: StructuralGraph,
    generated: StructuralGraph,
    semantic_scores: dict | None = None,
) -> dict:
    """Compute full round-trip score with adaptive weighting.

    Metrics that return NaN (because original has no data) are excluded
    and their weight is redistributed proportionally.
    """
    # Raw metrics (may be NaN)
    metrics = {
        "class_overlap": jaccard(original.class_names, generated.class_names),
        "fuzzy_class": fuzzy_class_match(original.class_names, generated.class_names),
        "method_overlap": jaccard(original.method_names, generated.method_names),
        "function_overlap": jaccard(original.function_names, generated.function_names),
        "import_recall": import_overlap(original.import_modules, generated.import_modules),
        "module_name_overlap": module_name_overlap(original.modules, generated.modules),
        "module_count_ratio": module_count_ratio(original.modules, generated.modules),
    }

    # Semantic scores (optional)
    if semantic_scores:
        metrics["semantic_class_match"] = semantic_scores.get("semantic_class_match", float("nan"))
        metrics["intent_coverage"] = semantic_scores.get("intent_coverage", float("nan"))
    else:
        metrics["semantic_class_match"] = float("nan")
        metrics["intent_coverage"] = float("nan")

    # Adaptive composite: weight only non-NaN metrics
    weights = {
        "class_overlap": 0.10,
        "fuzzy_class": 0.10,
        "method_overlap": 0.10,
        "function_overlap": 0.05,
        "import_recall": 0.15,
        "module_name_overlap": 0.20,
        "module_count_ratio": 0.10,
        "semantic_class_match": 0.10,
        "intent_coverage": 0.10,
    }

    total_weight = 0.0
    weighted_sum = 0.0
    for key, weight in weights.items():
        val = metrics.get(key, float("nan"))
        if not math.isnan(val):
            weighted_sum += weight * val
            total_weight += weight

    metrics["overall"] = weighted_sum / total_weight if total_weight > 0 else 0.0
    metrics["active_metrics"] = sum(
        1 for k, v in metrics.items()
        if k not in ("overall", "active_metrics") and isinstance(v, float) and not math.isnan(v)
    )

    return metrics


# ---------------------------------------------------------------------------
# Ground Truth: Load from cloned repos
# ---------------------------------------------------------------------------


def load_repo_source(repo_name: str) -> StructuralGraph:
    """Load actual source files from cloned repo and parse into StructuralGraph."""
    subdir = REPO_SUBDIRS.get(repo_name, repo_name)
    repo_path = CLONE_DIR / repo_name / subdir

    if not repo_path.exists():
        # Fallback to repo root
        repo_path = CLONE_DIR / repo_name
        if not repo_path.exists():
            return StructuralGraph()

    parts = []
    py_files = sorted(repo_path.rglob("*.py"))[:100]  # Cap at 100 files
    for f in py_files:
        try:
            content = f.read_text(errors="ignore")
            rel_path = f.relative_to(repo_path.parent)
            parts.append(f"# {rel_path}\n{content}")
        except (OSError, ValueError):
            continue

    if not parts:
        return StructuralGraph()

    code = "\n\n".join(parts)
    return parse_multi_file_code(code)


def load_training_examples(db_path: str, limit: int | None = None) -> list[dict]:
    """Load training examples from SQLite (deduplicated by repo)."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT repo_url, code_context, oracle_output, local_output
        FROM training_examples
        WHERE oracle_output IS NOT NULL
        AND LENGTH(oracle_output) > 100
        GROUP BY repo_url
        HAVING id = MAX(id)
        ORDER BY id DESC
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "repo": row["repo_url"].split("/")[-1],
            "repo_url": row["repo_url"],
            "code_context": row["code_context"],
            "oracle_output": row["oracle_output"],
            "local_output": row["local_output"],
        })
    return results


# ---------------------------------------------------------------------------
# Per-repo processing
# ---------------------------------------------------------------------------


async def process_repo_round_trip(
    example: dict,
    index: int,
    total: int,
    surrogate: Surrogate | None,
    use_copilot: bool,
    semantic_matcher: object | None = None,
) -> dict:
    """Run the full round-trip test for one repo."""
    name = example["repo"]
    t0 = time.time()

    result = {
        "repo": name,
        "repo_url": example["repo_url"],
        "status": "ok",
    }

    print(f"\n[{index}/{total}] {name}", end="", flush=True)

    # 1. Load REAL source code from cloned repo (not DB context)
    original_graph = load_repo_source(name)
    if not original_graph.classes and not original_graph.functions and not original_graph.modules:
        result["status"] = "no_source"
        result["error"] = f"No source found at {CLONE_DIR / name}"
        print(" NO SOURCE")
        return result

    result["original"] = {
        "classes": len(original_graph.classes),
        "methods": len(original_graph.method_names),
        "functions": len(original_graph.function_names),
        "imports": len(original_graph.import_modules),
        "modules": len(original_graph.modules),
    }
    print(
        f" (C:{len(original_graph.classes)} M:{len(original_graph.method_names)}"
        f" F:{len(original_graph.function_names)} Mod:{len(original_graph.modules)})",
        end="", flush=True,
    )

    # 2. Generate code via surrogate
    surrogate_score = None
    surrogate_graph = None
    if surrogate is not None:
        print(" surr", end="", flush=True)
        try:
            generated_code = await asyncio.wait_for(
                surrogate.generate_code(example["oracle_output"]),
                timeout=120,
            )
            if generated_code:
                surrogate_graph = parse_multi_file_code(generated_code)
                if not surrogate_graph.classes and not surrogate_graph.functions:
                    surrogate_graph = parse_code_structure(generated_code, "generated")

                # Compute semantic scores if available
                sem_scores = None
                if semantic_matcher and original_graph.class_names and surrogate_graph.class_names:
                    try:
                        matches = await semantic_matcher.match_names(
                            list(original_graph.class_names),
                            list(surrogate_graph.class_names),
                        )
                        intent = await semantic_matcher.intent_coverage(
                            list(original_graph.class_names),
                            list(surrogate_graph.class_names),
                        )
                        sem_scores = {
                            "semantic_class_match": sum(m.score for m in matches) / len(matches) if matches else 0.0,
                            "intent_coverage": intent,
                        }
                    except Exception:
                        pass

                surrogate_score = compute_round_trip_score(original_graph, surrogate_graph, sem_scores)
                print(f"={surrogate_score['overall']:.2f}", end="", flush=True)
            else:
                print("=FAIL", end="", flush=True)
                surrogate_score = {"overall": 0.0, "error": "empty output"}
        except asyncio.TimeoutError:
            print("=TIMEOUT", end="", flush=True)
            surrogate_score = {"overall": 0.0, "error": "timeout"}
        except Exception as e:
            print(f"=ERR({e})", end="", flush=True)
            surrogate_score = {"overall": 0.0, "error": str(e)}

    result["surrogate"] = surrogate_score

    # 3. Generate code via copilot-relay
    copilot_score = None
    copilot_graph = None
    if use_copilot:
        print(" cop", end="", flush=True)
        try:
            generated_code = await call_copilot_relay(
                example["oracle_output"],
                _GENERATE_SYSTEM_PROMPT,
                timeout=180,
            )
            generated_code = strip_fences(generated_code)

            if generated_code:
                copilot_graph = parse_multi_file_code(generated_code)
                if not copilot_graph.classes and not copilot_graph.functions:
                    copilot_graph = parse_code_structure(generated_code, "generated")

                # Compute semantic scores if available
                sem_scores = None
                if semantic_matcher and original_graph.class_names and copilot_graph.class_names:
                    try:
                        matches = await semantic_matcher.match_names(
                            list(original_graph.class_names),
                            list(copilot_graph.class_names),
                        )
                        intent = await semantic_matcher.intent_coverage(
                            list(original_graph.class_names),
                            list(copilot_graph.class_names),
                        )
                        sem_scores = {
                            "semantic_class_match": sum(m.score for m in matches) / len(matches) if matches else 0.0,
                            "intent_coverage": intent,
                        }
                    except Exception:
                        pass

                copilot_score = compute_round_trip_score(original_graph, copilot_graph, sem_scores)
                print(f"={copilot_score['overall']:.2f}", end="", flush=True)
            else:
                print("=FAIL", end="", flush=True)
                copilot_score = {"overall": 0.0, "error": "empty output"}
        except asyncio.TimeoutError:
            print("=TIMEOUT", end="", flush=True)
            copilot_score = {"overall": 0.0, "error": "timeout"}
        except Exception as e:
            print(f"=ERR({e})", end="", flush=True)
            copilot_score = {"overall": 0.0, "error": str(e)}

    result["copilot"] = copilot_score

    # 4. Structural details for analysis
    if surrogate_graph:
        result["surrogate_generated"] = {
            "classes": len(surrogate_graph.classes),
            "methods": len(surrogate_graph.method_names),
            "functions": len(surrogate_graph.function_names),
            "imports": len(surrogate_graph.import_modules),
            "modules": len(surrogate_graph.modules),
        }
    if copilot_graph:
        result["copilot_generated"] = {
            "classes": len(copilot_graph.classes),
            "methods": len(copilot_graph.method_names),
            "functions": len(copilot_graph.function_names),
            "imports": len(copilot_graph.import_modules),
            "modules": len(copilot_graph.modules),
        }

    result["elapsed_s"] = time.time() - t0
    return result


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def fmt(val) -> str:
    """Format a metric value — 'N/A' for NaN, otherwise 2 decimal places."""
    if isinstance(val, float) and math.isnan(val):
        return "  -  "
    if isinstance(val, float):
        return f"{val:5.2f}"
    return str(val)


def print_summary(results: list[dict], use_copilot: bool, use_surrogate: bool):
    """Print formatted round-trip results table."""
    ok_results = [r for r in results if r["status"] == "ok"]
    if not ok_results:
        print("\nNo successful results.")
        return

    line = "\u2501" * 145
    print(f"\n{line}")
    print("  ROUND-TRIP FIDELITY v2: Architecture Model \u2192 Code \u2192 Compare with REAL Source")
    print(line)

    # Header
    hdr = (
        f" {'Repo':<14} {'Gen':>4}"
        f" {'ClsJ':>5} {'ClsF':>5} {'Meth':>5} {'Func':>5}"
        f" {'ImpRc':>5} {'ModNm':>5} {'ModCt':>5}"
        f" {'SemCl':>5} {'IntCv':>5}"
        f" {'OVER':>5}"
        f"  {'OrgC':>4}/{'GnC':<3} {'OrgM':>4}/{'GnM':<3}"
    )
    print(hdr)
    print("\u2500" * 145)

    surr_scores = []
    cop_scores = []

    for r in ok_results:
        name = r["repo"][:14]
        orig = r.get("original", {})

        # Surrogate row
        if use_surrogate and r.get("surrogate") and "class_overlap" in r.get("surrogate", {}):
            s = r["surrogate"]
            sg = r.get("surrogate_generated", {})
            print(
                f" {name:<14} {'surr':>4}"
                f" {fmt(s['class_overlap']):>5} {fmt(s['fuzzy_class']):>5}"
                f" {fmt(s['method_overlap']):>5} {fmt(s['function_overlap']):>5}"
                f" {fmt(s['import_recall']):>5} {fmt(s['module_name_overlap']):>5}"
                f" {fmt(s['module_count_ratio']):>5}"
                f" {fmt(s['semantic_class_match']):>5} {fmt(s['intent_coverage']):>5}"
                f" {s['overall']:>5.2f}"
                f"  {orig.get('classes', 0):>4}/{sg.get('classes', 0):<3}"
                f" {orig.get('modules', 0):>4}/{sg.get('modules', 0):<3}"
            )
            surr_scores.append(s)

        # Copilot row
        if use_copilot and r.get("copilot") and "class_overlap" in r.get("copilot", {}):
            c = r["copilot"]
            cg = r.get("copilot_generated", {})
            print(
                f" {'':14} {'cop':>4}"
                f" {fmt(c['class_overlap']):>5} {fmt(c['fuzzy_class']):>5}"
                f" {fmt(c['method_overlap']):>5} {fmt(c['function_overlap']):>5}"
                f" {fmt(c['import_recall']):>5} {fmt(c['module_name_overlap']):>5}"
                f" {fmt(c['module_count_ratio']):>5}"
                f" {fmt(c['semantic_class_match']):>5} {fmt(c['intent_coverage']):>5}"
                f" {c['overall']:>5.2f}"
                f"  {orig.get('classes', 0):>4}/{cg.get('classes', 0):<3}"
                f" {orig.get('modules', 0):>4}/{cg.get('modules', 0):<3}"
            )
            cop_scores.append(c)

        if use_surrogate and use_copilot:
            print()  # spacer

    # Mean rows
    print("\u2500" * 145)

    def mean_metric(scores: list[dict], key: str) -> float:
        """Mean of non-NaN values for a metric."""
        vals = [s[key] for s in scores if key in s and isinstance(s[key], float) and not math.isnan(s[key])]
        return sum(vals) / len(vals) if vals else float("nan")

    if surr_scores:
        print(
            f" {'MEAN':<14} {'surr':>4}"
            f" {fmt(mean_metric(surr_scores, 'class_overlap')):>5}"
            f" {fmt(mean_metric(surr_scores, 'fuzzy_class')):>5}"
            f" {fmt(mean_metric(surr_scores, 'method_overlap')):>5}"
            f" {fmt(mean_metric(surr_scores, 'function_overlap')):>5}"
            f" {fmt(mean_metric(surr_scores, 'import_recall')):>5}"
            f" {fmt(mean_metric(surr_scores, 'module_name_overlap')):>5}"
            f" {fmt(mean_metric(surr_scores, 'module_count_ratio')):>5}"
            f" {fmt(mean_metric(surr_scores, 'semantic_class_match')):>5}"
            f" {fmt(mean_metric(surr_scores, 'intent_coverage')):>5}"
            f" {mean_metric(surr_scores, 'overall'):>5.2f}"
        )
    if cop_scores:
        print(
            f" {'MEAN':<14} {'cop':>4}"
            f" {fmt(mean_metric(cop_scores, 'class_overlap')):>5}"
            f" {fmt(mean_metric(cop_scores, 'fuzzy_class')):>5}"
            f" {fmt(mean_metric(cop_scores, 'method_overlap')):>5}"
            f" {fmt(mean_metric(cop_scores, 'function_overlap')):>5}"
            f" {fmt(mean_metric(cop_scores, 'import_recall')):>5}"
            f" {fmt(mean_metric(cop_scores, 'module_name_overlap')):>5}"
            f" {fmt(mean_metric(cop_scores, 'module_count_ratio')):>5}"
            f" {fmt(mean_metric(cop_scores, 'semantic_class_match')):>5}"
            f" {fmt(mean_metric(cop_scores, 'intent_coverage')):>5}"
            f" {mean_metric(cop_scores, 'overall'):>5.2f}"
        )
    print(line)

    # Failure summary
    failed_surr = [r for r in ok_results if r.get("surrogate") and r["surrogate"].get("error")]
    failed_cop = [r for r in ok_results if r.get("copilot") and r["copilot"].get("error")]
    no_source = [r for r in results if r["status"] == "no_source"]
    if no_source:
        print(f"\nNo source found ({len(no_source)}):")
        for r in no_source:
            print(f"  - {r['repo']}")
    if failed_surr:
        print(f"\nSurrogate failures ({len(failed_surr)}):")
        for r in failed_surr:
            print(f"  - {r['repo']}: {r['surrogate'].get('error')}")
    if failed_cop:
        print(f"\nCopilot failures ({len(failed_cop)}):")
        for r in failed_cop:
            print(f"  - {r['repo']}: {r['copilot'].get('error')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    parser = argparse.ArgumentParser(description="Full autoencoder round-trip test v2")
    parser.add_argument("--limit", type=int, default=None, help="Max repos to process")
    parser.add_argument("--surrogate-only", action="store_true", help="Skip copilot-relay")
    parser.add_argument("--copilot-only", action="store_true", help="Skip surrogate")
    parser.add_argument("--no-semantic", action="store_true", help="Skip semantic embedding matching")
    args = parser.parse_args()

    use_surrogate = not args.copilot_only
    use_copilot = not args.surrogate_only

    print("=" * 80)
    print("  AUTOENCODER ROUND-TRIP TEST v2: Model \u2192 Code \u2192 Compare with REAL Source")
    generators = []
    if use_surrogate:
        generators.append("qwen2.5:7b (Ollama)")
    if use_copilot:
        generators.append("copilot-relay")
    print(f"  Generators: {' + '.join(generators)}")
    print(f"  Ground truth: Real source from {CLONE_DIR}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    # Load examples from DB
    examples = load_training_examples(DB_PATH, limit=args.limit)
    print(f"\nLoaded {len(examples)} repos from {DB_PATH}")

    if not examples:
        print("No training examples found. Run test_multi_repo.py first.")
        return

    # Initialize surrogate
    surrogate: Surrogate | None = None
    if use_surrogate:
        try:
            surrogate = Surrogate(model_name="qwen2.5:7b", host="http://localhost:11434")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:11434/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        print("Surrogate: qwen2.5:7b (Ollama available)")
                    else:
                        print(f"Surrogate: Ollama returned {resp.status}, disabling")
                        surrogate = None
        except Exception:
            print("Surrogate: Ollama not reachable, disabling")
            surrogate = None

    # Initialize semantic matcher
    semantic_matcher = None
    if not args.no_semantic and HAS_SEMANTIC:
        try:
            semantic_matcher = SemanticMatcher()
            print("Semantic matcher: nomic-embed-text (enabled)")
        except Exception:
            print("Semantic matcher: unavailable, using hard metrics only")

    # Check copilot-relay
    if use_copilot:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8400/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        print("Copilot-relay: available")
                    else:
                        print("Copilot-relay: unhealthy, disabling")
                        use_copilot = False
        except Exception:
            print("Copilot-relay: not reachable, disabling")
            use_copilot = False

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Process each repo
    results: list[dict] = []
    total_t0 = time.time()

    for i, example in enumerate(examples, 1):
        try:
            result = await process_repo_round_trip(
                example, i, len(examples),
                surrogate=surrogate,
                use_copilot=use_copilot,
                semantic_matcher=semantic_matcher,
            )
            results.append(result)
        except Exception as e:
            print(f"\n  UNEXPECTED ERROR: {e}")
            results.append({"repo": example["repo"], "status": "error", "error": str(e)})

    total_elapsed = time.time() - total_t0

    # Print summary
    print_summary(results, use_copilot=use_copilot, use_surrogate=use_surrogate)
    print(f"\nTotal time: {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")

    # Save JSON
    output_file = RESULTS_DIR / f"round_trip_v2_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json"
    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "surrogate": "qwen2.5:7b" if surrogate else "disabled",
            "copilot": "copilot-relay" if use_copilot else "disabled",
            "semantic": "nomic-embed-text" if semantic_matcher else "disabled",
            "ground_truth": "real source from /tmp/test-repos/",
            "repos": len(results),
        },
        "results": results,
    }
    output_file.write_text(json.dumps(output, indent=2, default=str))
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
