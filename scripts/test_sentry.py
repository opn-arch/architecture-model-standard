"""
Integration test: Full MPC iteration on getsentry/sentry.

Compares single-pass (original) vs enhanced (multi-pass + refine) extraction.

Uses skeleton sampling strategy:
- Package structure (151 top-level modules)
- Key entry points (wsgi, asgi, app)
- Architecture-defining files (silo, consumers, event_manager)
- Layer representatives (api, web, services, tasks, integrations, models)
"""

import asyncio
import json
from pathlib import Path

import aiohttp
import yaml

from architecture_model.training.surrogate import Surrogate, _EXTRACT_SYSTEM_PROMPT, _strip_fences
from architecture_model.training.evaluator import Evaluator
from architecture_model.training.dataset import DatasetStore, TrainingExample
from architecture_model.training.context_builder import ContextBuilder
from architecture_model.training.multi_pass import MultiPassExtractor
from architecture_model.training.refiner import ModelRefiner
from architecture_model.core.parser import _parse_raw
from architecture_model.core.validator import validate_model


SENTRY_ROOT = Path("/tmp/test-arch-model/sentry/src/sentry")


def build_code_context() -> str:
    """Build architectural skeleton context for Sentry (~12K chars).

    Strategy: read the most architecturally informative files that reveal
    the system's structure, layers, and key components.
    """
    sections = []

    # 1. Package structure overview
    top_level = sorted(p.name for p in SENTRY_ROOT.iterdir())
    sections.append(
        "# === PACKAGE STRUCTURE (src/sentry/) ===\n"
        "# 151 top-level modules/packages:\n"
        + "\n".join(f"# - {name}" for name in top_level[:60])
        + "\n# ... (91 more)"
    )

    # 2. Entry points
    for entry in ["wsgi.py", "asgi.py", "app.py"]:
        path = SENTRY_ROOT / entry
        if path.exists():
            content = path.read_text()[:800]
            sections.append(f"# === {entry} ===\n{content}")

    # 3. Silo architecture (Sentry's key architectural pattern)
    silo_base = SENTRY_ROOT / "silo" / "base.py"
    if silo_base.exists():
        sections.append(f"# === silo/base.py (Silo Architecture) ===\n{silo_base.read_text()[:1200]}")

    # 4. API layer
    api_base = SENTRY_ROOT / "api" / "base.py"
    if api_base.exists():
        sections.append(f"# === api/base.py ===\n{api_base.read_text()[:1000]}")

    # 5. Consumers (Kafka event processing)
    consumers_init = SENTRY_ROOT / "consumers" / "__init__.py"
    if consumers_init.exists():
        sections.append(f"# === consumers/__init__.py ===\n{consumers_init.read_text()[:1000]}")

    # 6. Event manager (core event processing)
    event_mgr = SENTRY_ROOT / "event_manager.py"
    if event_mgr.exists():
        sections.append(f"# === event_manager.py ===\n{event_mgr.read_text()[:1200]}")

    # 7. Integrations module docstring
    integ_init = SENTRY_ROOT / "integrations" / "__init__.py"
    if integ_init.exists():
        sections.append(f"# === integrations/__init__.py ===\n{integ_init.read_text()[:1000]}")

    # 8. Tasks layer
    tasks_init = SENTRY_ROOT / "tasks" / "__init__.py"
    if tasks_init.exists():
        sections.append(f"# === tasks/__init__.py ===\n{tasks_init.read_text()[:500]}")

    # 9. Models layer (just the imports to show breadth)
    models_init = SENTRY_ROOT / "models" / "__init__.py"
    if models_init.exists():
        sections.append(f"# === models/__init__.py ===\n{models_init.read_text()[:1500]}")

    # 10. Web layer routing
    web_urls = SENTRY_ROOT / "web" / "urls.py"
    if web_urls.exists():
        sections.append(f"# === web/urls.py ===\n{web_urls.read_text()[:1200]}")

    context = "\n\n".join(sections)
    return context


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


async def main():
    print("=" * 60)
    print("MPC INTEGRATION TEST: getsentry/sentry")
    print("=" * 60)

    # 1. Build code context
    print("\n[1] Building code context (skeleton sampling)...")
    code = build_code_context()
    print(f"    {len(code)} chars")

    # 2. Surrogate extraction — SINGLE-PASS (baseline)
    print("\n[2a] Surrogate extraction - SINGLE PASS (qwen2.5:7b)...")
    surrogate = Surrogate(model_name="qwen2.5:7b")
    local_model = await surrogate.extract_model(code)

    if local_model:
        confidence = surrogate.confidence(local_model)
        val_result = validate_model(local_model)
        print(f"    Entities: {local_model.entity_count}")
        print(f"      Actors: {len(local_model.entities.actors)}")
        print(f"      Capabilities: {len(local_model.entities.capabilities)}")
        print(f"      Behaviors: {len(local_model.entities.behaviors)}")
        print(f"      Interfaces: {len(local_model.entities.interfaces)}")
        print(f"      Constraints: {len(local_model.entities.constraints)}")
        print(f"      Layers: {len(local_model.entities.layers)}")
        print(f"      Components: {len(local_model.entities.components)}")
        print(f"    Relationships: {local_model.relationship_count}")
        print(f"    Confidence: {confidence:.2f}")
        print(f"    Validator score: {val_result.score}/100")
    else:
        print("    FAILED - got None")
        local_model = None

    # 2b. Surrogate extraction — ENHANCED (multi-pass + refine)
    print("\n[2b] Surrogate extraction - ENHANCED (multi-pass + refine)...")
    cb = ContextBuilder(SENTRY_ROOT)
    slices = cb.build()
    print(f"    Context slices built: {len(slices.combined())} chars total")
    print(f"      Structure: {len(slices.structure)} chars")
    print(f"      Boundaries: {len(slices.boundaries)} chars")
    print(f"      Behavior: {len(slices.behavior)} chars")
    print(f"      Relationships: {len(slices.relationships)} chars")
    print(f"      Constraints: {len(slices.constraints)} chars")

    extractor = MultiPassExtractor(surrogate, slices, project_name="sentry")
    enhanced_model = await extractor.extract()

    if enhanced_model:
        print(f"    [After multi-pass] Entities: {enhanced_model.entity_count}")
        print(f"    [After multi-pass] Relationships: {enhanced_model.relationship_count}")

        # Refine
        refiner = ModelRefiner(surrogate, max_rounds=2)
        enhanced_model = await refiner.refine(enhanced_model, slices.combined())
        enhanced_val = validate_model(enhanced_model)

        print(f"    [After refine] Entities: {enhanced_model.entity_count}")
        print(f"      Actors: {len(enhanced_model.entities.actors)}")
        print(f"      Capabilities: {len(enhanced_model.entities.capabilities)}")
        print(f"      Behaviors: {len(enhanced_model.entities.behaviors)}")
        print(f"      Interfaces: {len(enhanced_model.entities.interfaces)}")
        print(f"      Constraints: {len(enhanced_model.entities.constraints)}")
        print(f"      Layers: {len(enhanced_model.entities.layers)}")
        print(f"      Components: {len(enhanced_model.entities.components)}")
        print(f"    Relationships: {enhanced_model.relationship_count}")
        print(f"    Confidence: {surrogate.confidence(enhanced_model):.2f}")
        print(f"    Validator score: {enhanced_val.score}/100")
    else:
        print("    FAILED - got None")

    # 3. Comparison
    if local_model and enhanced_model:
        print("\n[3] COMPARISON: Single-pass vs Enhanced")
        print(f"    {'Metric':<25} {'Single-pass':<15} {'Enhanced':<15} {'Improvement'}")
        print(f"    {'-'*70}")

        sp_ent = local_model.entity_count
        en_ent = enhanced_model.entity_count
        print(f"    {'Entities':<25} {sp_ent:<15} {en_ent:<15} {'+' if en_ent > sp_ent else ''}{en_ent - sp_ent}")

        sp_rel = local_model.relationship_count
        en_rel = enhanced_model.relationship_count
        print(f"    {'Relationships':<25} {sp_rel:<15} {en_rel:<15} {'+' if en_rel > sp_rel else ''}{en_rel - sp_rel}")

        sp_score = validate_model(local_model).score
        en_score = enhanced_val.score
        print(f"    {'Validator score':<25} {sp_score:<15} {en_score:<15} {'+' if en_score > sp_score else ''}{en_score - sp_score}")

    # 4. Oracle extraction (copilot-relay)
    print("\n[4] Oracle extraction (copilot-relay → GitHub Copilot)...")
    oracle_response = await call_copilot_relay(_EXTRACT_SYSTEM_PROMPT, code)

    if not oracle_response:
        print("    FAILED - empty response from relay")
        return

    # Parse oracle response
    clean = _strip_fences(oracle_response)
    oracle_model = None
    try:
        raw = yaml.safe_load(clean)
        if isinstance(raw, dict):
            oracle_model = _parse_raw(raw)
    except Exception as e:
        print(f"    Parse error: {e}")

    if oracle_model:
        oracle_val = validate_model(oracle_model)
        print(f"    Entities: {oracle_model.entity_count}")
        print(f"      Actors: {len(oracle_model.entities.actors)}")
        print(f"      Capabilities: {len(oracle_model.entities.capabilities)}")
        print(f"      Behaviors: {len(oracle_model.entities.behaviors)}")
        print(f"      Interfaces: {len(oracle_model.entities.interfaces)}")
        print(f"      Constraints: {len(oracle_model.entities.constraints)}")
        print(f"      Layers: {len(oracle_model.entities.layers)}")
        print(f"      Components: {len(oracle_model.entities.components)}")
        print(f"    Relationships: {oracle_model.relationship_count}")
        print(f"    Validator score: {oracle_val.score}/100")
    else:
        print(f"    FAILED to parse oracle response ({len(oracle_response)} chars)")
        print(f"    First 500 chars:\n{oracle_response[:500]}")
        return

    # 5. Evaluate loss (both approaches vs oracle)
    print("\n[5] Computing loss (surrogate vs oracle)...")
    evaluator = Evaluator()

    if local_model:
        loss_sp = evaluator.compute_loss(local_model=local_model, oracle_model=oracle_model)
        print(f"    SINGLE-PASS vs Oracle:")
        print(f"      L1 (structural accuracy): {loss_sp.structural_accuracy:.3f}")
        print(f"      L2 (completeness):        {loss_sp.completeness:.3f}")
        print(f"      L3 (validator score):      {loss_sp.validator_score:.1f}")

    if enhanced_model:
        loss_en = evaluator.compute_loss(local_model=enhanced_model, oracle_model=oracle_model)
        print(f"    ENHANCED vs Oracle:")
        print(f"      L1 (structural accuracy): {loss_en.structural_accuracy:.3f}")
        print(f"      L2 (completeness):        {loss_en.completeness:.3f}")
        print(f"      L3 (validator score):      {loss_en.validator_score:.1f}")

    # 6. Save to dataset store
    print("\n[6] Saving to dataset store...")
    store = DatasetStore("/tmp/test-arch-model/training.db")
    example = TrainingExample(
        repo_url="https://github.com/getsentry/sentry",
        repo_sha="HEAD",
        code_context=code[:8000],
        local_output=yaml.dump(
            {"entities": local_model.entity_count if local_model else 0,
             "relationships": local_model.relationship_count if local_model else 0}
        ),
        oracle_output=oracle_response[:8000],
        loss_vector={
            "L1": loss_sp.structural_accuracy if local_model else 0,
            "L2": loss_sp.completeness if local_model else 0,
            "L3": loss_sp.validator_score if local_model else 0,
        },
        iteration=1,
        metadata={
            "model": "qwen2.5:7b",
            "oracle": "copilot-relay",
            "repo": "getsentry/sentry",
            "enhanced_entities": enhanced_model.entity_count if enhanced_model else 0,
            "enhanced_relationships": enhanced_model.relationship_count if enhanced_model else 0,
        },
    )
    eid = store.save(example)
    print(f"    Saved example id={eid}")

    # Summary
    total = store.query()
    print(f"    Total examples in store: {len(total)}")
    store.close()

    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
