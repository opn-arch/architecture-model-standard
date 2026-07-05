#!/usr/bin/env python3
"""Multi-repo forward+backward validation with surrogate training.

Runs the full MPC pipeline on 10 repos:
1. Clone (shallow, proxy-cleared)
2. Forward: manifest → oracle extraction ×2 → enforcement
3. Forward: surrogate extraction → loss computation
4. Backward: test mapping, doc coverage, structural, consistency
5. Training: save examples, DPO preferences

Usage: python scripts/test_multi_repo.py [--skip-clone] [--repos N]
"""

import argparse
import asyncio
import json
import subprocess
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
from architecture_model.core.validator import validate_model
from architecture_model.training.backward_validator import BackwardValidator, BackwardResult
from architecture_model.training.dataset import DatasetStore, TrainingExample
from architecture_model.training.evaluator import Evaluator, LossVector
from architecture_model.training.coverage_scorer import CoverageScorer
from architecture_model.training.model_comparison import compare_models
from architecture_model.training.oracle_context import OracleContextBuilder
from architecture_model.training.oracle_coverage import ManifestCoverageComputer
from architecture_model.training.oracle_evolution import _BASE_EXTRACTION_PROMPT
from architecture_model.training.surrogate import Surrogate


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLONE_DIR = Path("/tmp/test-repos")
RESULTS_DIR = Path("results")
COPILOT_RELAY_URL = "http://localhost:8400/chat"
DB_PATH = "data/training.db"

REPOS = [
    # Small (< 5K LOC)
    {"url": "https://github.com/pallets/click", "name": "click", "subdir": "src/click"},
    {"url": "https://github.com/tiangolo/typer", "name": "typer", "subdir": "typer"},
    {"url": "https://github.com/encode/httpcore", "name": "httpcore", "subdir": "httpcore"},
    {"url": "https://github.com/agronholm/anyio", "name": "anyio", "subdir": "src/anyio"},
    {"url": "https://github.com/theskumar/python-dotenv", "name": "python-dotenv", "subdir": "src/dotenv"},
    # Medium (5-50K LOC)
    {"url": "https://github.com/pydantic/pydantic", "name": "pydantic", "subdir": "pydantic"},
    {"url": "https://github.com/tiangolo/fastapi", "name": "fastapi", "subdir": "fastapi"},
    {"url": "https://github.com/Textualize/rich", "name": "rich", "subdir": "rich"},
    {"url": "https://github.com/encode/httpx", "name": "httpx", "subdir": "httpx"},
    {"url": "https://github.com/psf/black", "name": "black", "subdir": "src/black"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def strip_fences(text: str) -> str:
    """Strip markdown code fences from YAML response."""
    if "```yaml" in text:
        text = text.split("```yaml", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return text.strip()


async def call_copilot_relay(content: str, system_prompt: str, timeout: int = 120) -> str:
    """Call copilot-relay SSE endpoint and collect full response."""
    payload = {"content": content, "system_prompt": system_prompt}

    full_response: list[str] = []
    async with aiohttp.ClientSession() as session:
        async with session.post(
            COPILOT_RELAY_URL, json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout)
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


async def oracle_extract(context: str) -> ArchitectureModel | None:
    """Extract architecture model via oracle (copilot-relay)."""
    try:
        raw_response = await call_copilot_relay(context, _BASE_EXTRACTION_PROMPT, timeout=120)
    except (asyncio.TimeoutError, aiohttp.ClientError, RuntimeError) as e:
        print(f"    [Oracle error: {e}]")
        return None

    cleaned = strip_fences(raw_response)

    try:
        raw = yaml.safe_load(cleaned)
    except yaml.YAMLError as e:
        print(f"    [YAML parse error: {e}]")
        return None

    if not isinstance(raw, dict):
        print(f"    [Not a dict, got {type(raw).__name__}]")
        return None

    try:
        return _parse_raw(raw)
    except Exception as e:
        print(f"    [Model parse error: {e}]")
        return None


async def surrogate_extract(context: str, surrogate: Surrogate) -> ArchitectureModel | None:
    """Extract architecture model via surrogate (Ollama qwen2.5:7b)."""
    try:
        model = await asyncio.wait_for(
            surrogate.extract_model(context),
            timeout=180
        )
        return model
    except asyncio.TimeoutError:
        print("    [Surrogate timeout]")
        return None
    except Exception as e:
        print(f"    [Surrogate error: {e}]")
        return None


def clone_repo(repo: dict) -> Path:
    """Shallow clone with proxy clearing. Returns repo root path."""
    target = CLONE_DIR / repo["name"]
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "git",
        "-c", "http.proxy=",
        "-c", "https.proxy=",
        "clone",
        "--depth", "1",
        repo["url"],
        str(target),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Clone failed for {repo['name']}: {result.stderr.strip()}")
    return target


def get_repo_sha(repo_path: Path) -> str:
    """Get the HEAD SHA for a cloned repo."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=repo_path
    )
    return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"


# ---------------------------------------------------------------------------
# Per-repo pipeline
# ---------------------------------------------------------------------------


async def process_repo(
    repo: dict,
    index: int,
    total: int,
    surrogate: Surrogate | None,
    store: DatasetStore,
    evaluator: Evaluator,
) -> dict:
    """Process a single repo through the full pipeline.

    Returns a results dict with all metrics.
    """
    name = repo["name"]
    t0 = time.time()
    result: dict = {
        "name": name,
        "url": repo["url"],
        "status": "ok",
        "error": None,
    }

    print(f"\n[{index}/{total}] {name} ({repo['url'].split('github.com/')[1]})", end="", flush=True)

    # 1. Clone
    try:
        repo_root = clone_repo(repo)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        result["status"] = "clone_failed"
        result["error"] = str(e)
        print(f" CLONE FAILED: {e}")
        return result

    source_path = repo_root / repo["subdir"]
    if not source_path.exists():
        # Fallback to repo root
        source_path = repo_root

    sha = get_repo_sha(repo_root)
    result["sha"] = sha

    # 2. Build manifest + context
    print(" .", end="", flush=True)
    try:
        builder = OracleContextBuilder(source_path, max_chars=40000)
        manifest = builder._generate_manifest()
        context = builder.build(manifest)
    except Exception as e:
        result["status"] = "manifest_failed"
        result["error"] = str(e)
        print(f" MANIFEST FAILED: {e}")
        return result

    result["manifest"] = {
        "modules": len(manifest.get("modules", [])),
        "interfaces": len(manifest.get("interfaces", [])),
        "blocks": len(manifest.get("functional_blocks", {})),
    }

    # 3. Oracle extraction ×2 (for consistency measurement)
    print(".", end="", flush=True)
    oracle_model_1 = await oracle_extract(context)
    if oracle_model_1 is None:
        result["status"] = "oracle_failed"
        result["error"] = "First oracle extraction returned None"
        print(f" ORACLE FAILED (run 1)")
        return result

    print(".", end="", flush=True)
    oracle_model_2 = await oracle_extract(context)
    if oracle_model_2 is None:
        # Use first model only, set consistency to 0
        consistency_score = 0.0
    else:
        # Compute consistency from structural comparison
        sim = compare_models(oracle_model_1, oracle_model_2)
        consistency_score = sim.get("overall", 0.0)

    # Validate oracle model
    val_result = validate_model(oracle_model_1)
    result["validator_score"] = val_result.score

    # 4. Coverage scoring (penalty signal — does NOT modify the model)
    print(".", end="", flush=True)
    scorer = CoverageScorer()
    cov_score = scorer.score(oracle_model_1, manifest)
    oracle_model = oracle_model_1  # No modification — raw oracle output

    # Rejection gate: mark low-quality extractions
    if cov_score.overall < 0.4:
        result["quality_gate"] = "rejected"
    else:
        result["quality_gate"] = "accepted"

    result["coverage_score"] = {
        "edge_coverage": cov_score.edge_coverage,
        "edge_precision": cov_score.edge_precision,
        "cohesion": cov_score.cohesion,
        "directionality": cov_score.directionality,
        "overall": cov_score.overall,
        "missing_edges_count": len(cov_score.missing_edges),
        "spurious_rels_count": len(cov_score.spurious_rels),
        "low_cohesion_components": cov_score.low_cohesion_components,
    }

    # 5. Legacy coverage analysis (manifest module/block/interface coverage)
    coverage_computer = ManifestCoverageComputer()
    coverage = coverage_computer.compute(manifest, oracle_model)
    result["coverage"] = {
        "module": coverage.module_coverage,
        "interface": coverage.interface_coverage,
        "block": coverage.block_coverage,
        "overall": coverage.overall,
    }

    # 6. Surrogate extraction + loss computation
    surrogate_model: ArchitectureModel | None = None
    loss: LossVector | None = None

    if surrogate is not None:
        print(".", end="", flush=True)
        surrogate_model = await surrogate_extract(context, surrogate)

        if surrogate_model is not None:
            loss = evaluator.compute_loss(
                local_model=surrogate_model,
                oracle_model=oracle_model,
            )
            result["loss"] = {
                "structural_accuracy": loss.structural_accuracy,
                "completeness": loss.completeness,
                "validator_score": loss.validator_score,
            }
        else:
            # Surrogate failed — record worst-case loss for training signal
            result["loss"] = {
                "structural_accuracy": 0.0,
                "completeness": 0.0,
                "validator_score": 0.0,
            }
            result["surrogate_failed"] = True
    else:
        result["loss"] = None

    # 7. Backward validation
    print(".", end="", flush=True)
    backward_validator = BackwardValidator()
    backward = backward_validator.validate(
        model=oracle_model,
        manifest=manifest,
        repo_path=repo_root,
        consistency_score=consistency_score,
    )
    result["backward"] = {
        "test_coverage": backward.test_coverage,
        "doc_coverage": backward.doc_coverage,
        "structural_coverage": backward.structural_coverage,
        "consistency": backward.consistency,
        "overall": backward.overall,
    }

    # 8. Save training example + DPO if threshold met
    oracle_yaml = yaml.dump(oracle_model.to_dict(), default_flow_style=False) if hasattr(oracle_model, "to_dict") else ""
    surrogate_yaml = ""
    if surrogate_model is not None:
        surrogate_yaml = yaml.dump(surrogate_model.to_dict(), default_flow_style=False) if hasattr(surrogate_model, "to_dict") else ""

    # Save training example
    example = TrainingExample(
        repo_url=repo["url"],
        repo_sha=sha,
        code_context=context[:50000],  # Cap context size
        local_output=surrogate_yaml if surrogate_yaml else oracle_yaml,
        oracle_output=oracle_yaml if oracle_yaml else None,
        iteration=1,
        loss_vector=result.get("loss"),
        metadata={
            "name": name,
            "backward": result["backward"],
            "coverage": result["coverage"],
        },
    )
    store.save(example)
    result["training_saved"] = True

    # DPO: save preference when surrogate fails or is significantly worse
    dpo_saved = False
    if oracle_yaml:
        should_save_dpo = False
        margin = 0.0
        if surrogate_model is None:
            # Surrogate completely failed — strong preference signal
            should_save_dpo = True
            margin = 1.0
        elif loss is not None and loss.structural_accuracy < 0.6 and surrogate_yaml:
            should_save_dpo = True
            margin = 1.0 - loss.structural_accuracy

        if should_save_dpo:
            # For failed surrogate, use empty string as rejected
            rejected = surrogate_yaml if surrogate_yaml else "# surrogate failed to produce output\n"
            store.save_preference(
                prompt=context[:30000],
                chosen=oracle_yaml,
                rejected=rejected,
                margin=margin,
                iteration=1,
            )
            dpo_saved = True
    result["dpo_saved"] = dpo_saved

    # Timing
    elapsed = time.time() - t0
    result["elapsed_s"] = elapsed

    # Print per-repo summary
    mod_cov = coverage.module_coverage * 100
    iface_cov = coverage.interface_coverage * 100
    block_cov = coverage.block_coverage * 100
    test_cov = backward.test_coverage * 100
    doc_cov = backward.doc_coverage * 100
    struct_cov = backward.structural_coverage * 100
    consist = backward.consistency * 100
    surr_loss_str = f"{loss.structural_accuracy:.2f}" if loss else ("0.00*" if result.get("surrogate_failed") else "N/A")
    dpo_str = f"yes (margin={1.0 - loss.structural_accuracy:.2f})" if dpo_saved and loss else ("yes (fail)" if dpo_saved else "no")
    gate_str = result["quality_gate"]

    dots = "." * max(1, 45 - len(name))
    print(f" {dots} {elapsed:.0f}s")
    print(f"  Forward:  validator={val_result.score}  mod={mod_cov:.0f}%  iface={iface_cov:.0f}%  block={block_cov:.0f}%")
    print(f"  CovScore: edge={cov_score.edge_coverage:.2f}  prec={cov_score.edge_precision:.2f}  coh={cov_score.cohesion:.2f}  dir={cov_score.directionality:.2f}  overall={cov_score.overall:.2f}  gate={gate_str}")
    print(f"  Backward: test={test_cov:.0f}%  doc={doc_cov:.0f}%  struct={struct_cov:.0f}%  consist={consist:.0f}%")
    print(f"  Training: surr_loss={surr_loss_str}  DPO={dpo_str}")

    return result


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


def print_summary_table(results: list[dict]):
    """Print formatted results table."""
    # Filter to successful results
    ok_results = [r for r in results if r["status"] == "ok"]
    failed = [r for r in results if r["status"] != "ok"]

    if not ok_results:
        print("\nNo successful results to display.")
        return

    line = "\u2501" * 90
    print(f"\n{line}")
    print(f" {'Repo':<16} {'Valid':>5}  {'ModCov':>6}  {'Iface':>5}  {'Block':>5}  "
          f"{'TestMap':>7}  {'DocCov':>6}  {'Consist':>7}  {'SurrLoss':>8}")
    print(line)

    # Accumulators for mean
    sums = {
        "valid": 0.0, "mod": 0.0, "iface": 0.0, "block": 0.0,
        "test": 0.0, "doc": 0.0, "consist": 0.0, "surr": 0.0,
    }
    surr_count = 0

    for r in ok_results:
        name = r["name"][:16]
        valid = r.get("validator_score", 0)
        cov = r.get("coverage", {})
        bw = r.get("backward", {})
        loss = r.get("loss")

        mod = cov.get("module", 0) * 100
        iface = cov.get("interface", 0) * 100
        block = cov.get("block", 0) * 100
        test = bw.get("test_coverage", 0) * 100
        doc = bw.get("doc_coverage", 0) * 100
        consist = bw.get("consistency", 0) * 100
        surr = loss["structural_accuracy"] if loss else None

        sums["valid"] += valid
        sums["mod"] += mod
        sums["iface"] += iface
        sums["block"] += block
        sums["test"] += test
        sums["doc"] += doc
        sums["consist"] += consist
        if surr is not None:
            sums["surr"] += surr
            surr_count += 1

        surr_str = f"{surr:.2f}" if surr is not None else "N/A"
        print(f" {name:<16} {valid:>5}  {mod:>5.0f}%  {iface:>4.0f}%  {block:>4.0f}%  "
              f"{test:>6.0f}%  {doc:>5.0f}%  {consist:>6.0f}%  {surr_str:>8}")

    n = len(ok_results)
    print(line)
    mean_surr = f"{sums['surr'] / surr_count:.2f}" if surr_count > 0 else "N/A"
    print(f" {'MEAN':<16} {sums['valid']/n:>5.1f}  {sums['mod']/n:>5.0f}%  "
          f"{sums['iface']/n:>4.0f}%  {sums['block']/n:>4.0f}%  "
          f"{sums['test']/n:>6.0f}%  {sums['doc']/n:>5.0f}%  "
          f"{sums['consist']/n:>6.0f}%  {mean_surr:>8}")
    print(line)

    if failed:
        print(f"\nFailed repos ({len(failed)}):")
        for r in failed:
            print(f"  - {r['name']}: {r['status']} — {r.get('error', 'unknown')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    parser = argparse.ArgumentParser(description="Multi-repo forward+backward validation")
    parser.add_argument("--skip-clone", action="store_true", help="Skip cloning repos that already exist")
    parser.add_argument("--repos", type=int, default=len(REPOS), help="Number of repos to process")
    args = parser.parse_args()

    repos = REPOS[:args.repos]

    print("=" * 70)
    print("  MULTI-REPO FORWARD+BACKWARD VALIDATION")
    print(f"  Repos: {len(repos)} | Oracle: copilot-relay | Surrogate: qwen2.5:7b")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Setup directories
    CLONE_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    # 1. Clone repos (unless --skip-clone and they exist)
    if not args.skip_clone:
        print("\nCloning repos...")
        for repo in repos:
            target = CLONE_DIR / repo["name"]
            if target.exists():
                print(f"  {repo['name']}: already exists, skipping")
                continue
            try:
                clone_repo(repo)
                print(f"  {repo['name']}: cloned")
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                print(f"  {repo['name']}: FAILED ({e})")
    else:
        print("\nSkipping clone (--skip-clone)")

    # 2. Initialize surrogate
    surrogate: Surrogate | None = None
    try:
        surrogate = Surrogate(model_name="qwen2.5:7b", host="http://localhost:11434")
        # Quick availability check via a trivial request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:11434/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    print(f"\nSurrogate: qwen2.5:7b (Ollama available)")
                else:
                    print(f"\nSurrogate: Ollama returned {resp.status}, skipping surrogate steps")
                    surrogate = None
    except Exception:
        print("\nSurrogate: Ollama not reachable, skipping surrogate steps")
        surrogate = None

    # 3. Initialize store + evaluator
    store = DatasetStore(DB_PATH)
    evaluator = Evaluator()

    # 4. Process each repo
    results: list[dict] = []
    total_t0 = time.time()

    for i, repo in enumerate(repos, 1):
        try:
            result = await process_repo(repo, i, len(repos), surrogate, store, evaluator)
            results.append(result)
        except Exception as e:
            print(f"\n  UNEXPECTED ERROR: {e}")
            results.append({
                "name": repo["name"],
                "url": repo["url"],
                "status": "error",
                "error": str(e),
            })

    total_elapsed = time.time() - total_t0

    # 5. Print summary table
    print_summary_table(results)

    # 6. Training stats
    n_examples = store.count()
    n_prefs = store.count_preferences()
    print(f"\nTraining: {n_examples} examples, {n_prefs} DPO prefs saved to {DB_PATH}")
    print(f"Total time: {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")

    # 7. Save JSON results
    output_file = RESULTS_DIR / f"multi_repo_{datetime.now().strftime('%Y-%m-%d')}.json"
    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "oracle": "copilot-relay (localhost:8400)",
            "surrogate": "qwen2.5:7b" if surrogate else "unavailable",
            "repos_processed": len(results),
        },
        "results": results,
        "summary": {
            "total_time_s": total_elapsed,
            "successful": len([r for r in results if r["status"] == "ok"]),
            "failed": len([r for r in results if r["status"] != "ok"]),
            "training_examples": n_examples,
            "dpo_preferences": n_prefs,
        },
    }
    output_file.write_text(json.dumps(output, indent=2, default=str))
    print(f"Results saved to: {output_file}")

    store.close()


if __name__ == "__main__":
    asyncio.run(main())
