"""
Integration test: Enhanced extraction on encode/httpx.

Mid-complexity repo (23 Python files, ~8800 LOC) with clear architecture:
- Client layer (sync/async)
- Transport layer (HTTP/1.1, HTTP/2, mock, ASGI, WSGI)
- Middleware patterns (auth, redirects, decoders)
- URL/Request/Response models

Compares: single-pass vs enhanced vs oracle extraction.
"""

import asyncio
import json
import time
from pathlib import Path

import aiohttp
import yaml

from architecture_model.training.surrogate import Surrogate, _EXTRACT_SYSTEM_PROMPT, _strip_fences
from architecture_model.training.context_builder import ContextBuilder
from architecture_model.training.multi_pass import MultiPassExtractor
from architecture_model.training.refiner import ModelRefiner
from architecture_model.training.evaluator import Evaluator
from architecture_model.core.parser import _parse_raw
from architecture_model.core.validator import validate_model


HTTPX_ROOT = Path("/tmp/test-arch-model/httpx/httpx")


def build_single_pass_context() -> str:
    """Build a simple concatenated context (original approach)."""
    parts = []
    for py_file in sorted(HTTPX_ROOT.rglob("*.py")):
        try:
            content = py_file.read_text(errors="ignore")
            rel = py_file.relative_to(HTTPX_ROOT)
            parts.append(f"# {rel}\n{content}")
        except OSError:
            continue
    # Limit to ~15K chars (similar budget to enhanced)
    combined = "\n\n".join(parts)
    return combined[:15000]


async def call_copilot_relay(system_prompt: str, user_prompt: str) -> str:
    """Call copilot-relay and collect SSE response."""
    url = "http://localhost:8400/chat"
    payload = {
        "content": user_prompt,
        "system_prompt": system_prompt,
    }

    full_response = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=180)) as resp:
            async for line in resp.content:
                text = line.decode("utf-8").strip()
                if text.startswith("data: "):
                    data = json.loads(text[6:])
                    if data.get("type") == "chunk":
                        full_response = data.get("content", "")
                    elif data.get("type") == "done":
                        break
                    elif data.get("type") == "error":
                        print(f"  [relay error] {data.get('detail')}")
                        break
    return full_response


def print_model_summary(label: str, model, val_result):
    """Print a formatted model summary."""
    print(f"    Entities: {model.entity_count}")
    print(f"      Actors: {len(model.entities.actors)}")
    print(f"      Capabilities: {len(model.entities.capabilities)}")
    print(f"      Behaviors: {len(model.entities.behaviors)}")
    print(f"      Interfaces: {len(model.entities.interfaces)}")
    print(f"      Constraints: {len(model.entities.constraints)}")
    print(f"      Layers: {len(model.entities.layers)}")
    print(f"      Components: {len(model.entities.components)}")
    print(f"    Relationships: {model.relationship_count}")
    print(f"    Validator score: {val_result.score}/100")
    if val_result.issues:
        print(f"    Issues: {val_result.error_count} errors, {val_result.warning_count} warnings, {val_result.info_count} info")


async def main():
    print("=" * 60)
    print("INTEGRATION TEST: encode/httpx (mid-complexity)")
    print("=" * 60)
    print(f"Source: {HTTPX_ROOT}")
    print(f"Files: {len(list(HTTPX_ROOT.rglob('*.py')))} Python files")

    surrogate = Surrogate(model_name="qwen2.5:7b")
    results = {}

    # ─────────────────────────────────────────────────────────────
    # 1. SINGLE-PASS EXTRACTION (baseline)
    # ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("[1] SINGLE-PASS extraction (qwen2.5:7b, concatenated context)")
    print("─" * 60)

    code = build_single_pass_context()
    print(f"    Context: {len(code)} chars")

    t0 = time.time()
    sp_model = await surrogate.extract_model(code)
    t1 = time.time()

    if sp_model:
        sp_val = validate_model(sp_model)
        print_model_summary("single-pass", sp_model, sp_val)
        print(f"    Time: {t1-t0:.1f}s")
        results["single_pass"] = (sp_model, sp_val)
    else:
        print("    FAILED - got None")
        results["single_pass"] = None

    # ─────────────────────────────────────────────────────────────
    # 2. ENHANCED EXTRACTION (context builder + multi-pass + refiner)
    # ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("[2] ENHANCED extraction (AST-guided + 5-pass + refiner)")
    print("─" * 60)

    t0 = time.time()

    # Step 2a: Build context slices
    cb = ContextBuilder(HTTPX_ROOT, max_chars=15000)
    slices = cb.build()
    print(f"    Context slices: {len(slices.combined())} chars total")
    print(f"      Structure:     {len(slices.structure)} chars")
    print(f"      Boundaries:    {len(slices.boundaries)} chars")
    print(f"      Behavior:      {len(slices.behavior)} chars")
    print(f"      Relationships: {len(slices.relationships)} chars")
    print(f"      Constraints:   {len(slices.constraints)} chars")

    # Step 2b: Multi-pass extraction
    print("    Running 5-pass extraction...")
    extractor = MultiPassExtractor(surrogate, slices, project_name="httpx")
    enhanced_model = await extractor.extract()

    if enhanced_model:
        mid_val = validate_model(enhanced_model)
        print(f"    [After multi-pass] Entities: {enhanced_model.entity_count}, "
              f"Relationships: {enhanced_model.relationship_count}, "
              f"Score: {mid_val.score}/100")

        # Step 2c: Refine
        print("    Running refiner (max 2 rounds)...")
        refiner = ModelRefiner(surrogate, max_rounds=2)
        enhanced_model = await refiner.refine(enhanced_model, slices.combined())
        t1 = time.time()

        en_val = validate_model(enhanced_model)
        print_model_summary("enhanced", enhanced_model, en_val)
        print(f"    Time: {t1-t0:.1f}s")
        results["enhanced"] = (enhanced_model, en_val)
    else:
        t1 = time.time()
        print(f"    FAILED - got None ({t1-t0:.1f}s)")
        results["enhanced"] = None

    # ─────────────────────────────────────────────────────────────
    # 3. ORACLE EXTRACTION (copilot-relay)
    # ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("[3] ORACLE extraction (copilot-relay → GitHub Copilot)")
    print("─" * 60)

    # Use the enhanced context for oracle too (fairer comparison)
    oracle_context = slices.combined() if slices else code
    print(f"    Context: {len(oracle_context)} chars")

    t0 = time.time()
    oracle_response = await call_copilot_relay(_EXTRACT_SYSTEM_PROMPT, oracle_context)
    t1 = time.time()

    oracle_model = None
    if oracle_response:
        clean = _strip_fences(oracle_response)
        try:
            raw = yaml.safe_load(clean)
            if isinstance(raw, dict):
                oracle_model = _parse_raw(raw)
        except Exception as e:
            print(f"    Parse error: {e}")

    if oracle_model:
        oracle_val = validate_model(oracle_model)
        print_model_summary("oracle", oracle_model, oracle_val)
        print(f"    Time: {t1-t0:.1f}s")
        results["oracle"] = (oracle_model, oracle_val)
    else:
        print(f"    FAILED to parse ({len(oracle_response)} chars, {t1-t0:.1f}s)")
        if oracle_response:
            print(f"    First 300 chars: {oracle_response[:300]}")
        results["oracle"] = None

    # ─────────────────────────────────────────────────────────────
    # 4. COMPARISON TABLE
    # ─────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("COMPARISON TABLE")
    print("═" * 60)

    header = f"    {'Metric':<25} {'Single-pass':<14} {'Enhanced':<14} {'Oracle':<14}"
    print(header)
    print(f"    {'─'*65}")

    def val_or_na(result, attr):
        if result is None:
            return "N/A"
        model, val = result
        if attr == "entities":
            return str(model.entity_count)
        elif attr == "relationships":
            return str(model.relationship_count)
        elif attr == "score":
            return f"{val.score}/100"
        elif attr == "actors":
            return str(len(model.entities.actors))
        elif attr == "capabilities":
            return str(len(model.entities.capabilities))
        elif attr == "behaviors":
            return str(len(model.entities.behaviors))
        elif attr == "interfaces":
            return str(len(model.entities.interfaces))
        elif attr == "constraints":
            return str(len(model.entities.constraints))
        elif attr == "layers":
            return str(len(model.entities.layers))
        elif attr == "components":
            return str(len(model.entities.components))
        return "?"

    for metric in ["entities", "relationships", "score", "actors", "capabilities",
                   "behaviors", "interfaces", "constraints", "layers", "components"]:
        sp = val_or_na(results.get("single_pass"), metric)
        en = val_or_na(results.get("enhanced"), metric)
        oc = val_or_na(results.get("oracle"), metric)
        print(f"    {metric:<25} {sp:<14} {en:<14} {oc:<14}")

    # ─────────────────────────────────────────────────────────────
    # 5. LOSS VECTORS (vs oracle)
    # ─────────────────────────────────────────────────────────────
    if results.get("oracle"):
        oracle_m = results["oracle"][0]
        evaluator = Evaluator()

        print(f"\n    {'─'*65}")
        print(f"    {'LOSS vs Oracle':<25} {'Single-pass':<14} {'Enhanced':<14}")
        print(f"    {'─'*65}")

        if results.get("single_pass"):
            loss_sp = evaluator.compute_loss(local_model=results["single_pass"][0], oracle_model=oracle_m)
        if results.get("enhanced"):
            loss_en = evaluator.compute_loss(local_model=results["enhanced"][0], oracle_model=oracle_m)

        for label, attr in [("L1 (struct accuracy)", "structural_accuracy"),
                            ("L2 (completeness)", "completeness"),
                            ("L3 (validator)", "validator_score")]:
            sp_v = f"{getattr(loss_sp, attr):.3f}" if results.get("single_pass") else "N/A"
            en_v = f"{getattr(loss_en, attr):.3f}" if results.get("enhanced") else "N/A"
            print(f"    {label:<25} {sp_v:<14} {en_v:<14}")

    print("\n" + "═" * 60)
    print("TEST COMPLETE")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(main())
