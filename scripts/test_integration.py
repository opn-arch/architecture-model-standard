"""
Integration test: Full MPC iteration on a real repo.

Uses:
- Surrogate: Ollama (qwen2.5:7b) for local extraction
- Oracle: copilot-relay (GitHub Copilot via VS Code) for ground truth
- Evaluator: multi-objective loss comparison
- DatasetStore: saves training example
"""

import asyncio
import json
from pathlib import Path

import aiohttp
import yaml

from architecture_model.training.surrogate import Surrogate, _EXTRACT_SYSTEM_PROMPT
from architecture_model.training.evaluator import Evaluator
from architecture_model.training.dataset import DatasetStore, TrainingExample
from architecture_model.core.parser import _parse_raw
from architecture_model.core.validator import validate_model


def read_code_context(repo_path: Path, max_files: int = 15, max_chars: int = 8000) -> str:
    """Read Python files from repo as code context."""
    py_files = sorted(repo_path.rglob("*.py"))[:max_files]
    parts = []
    total = 0
    for f in py_files:
        if total > max_chars:
            break
        try:
            content = f.read_text()[:2000]
            rel = f.relative_to(repo_path)
            parts.append(f"# --- {rel} ---\n{content}")
            total += len(content)
        except Exception:
            pass
    return "\n\n".join(parts)


async def call_copilot_relay(system_prompt: str, user_prompt: str) -> str:
    """Call copilot-relay and collect SSE response."""
    url = "http://localhost:8400/chat"
    payload = {
        "content": user_prompt,
        "system_prompt": system_prompt,
    }

    full_response = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
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


def parse_yaml_response(response: str):
    """Parse YAML from LLM response, stripping markdown fences if present."""
    clean = response
    if "```yaml" in clean:
        clean = clean.split("```yaml", 1)[1].split("```", 1)[0]
    elif "```" in clean:
        clean = clean.split("```", 1)[1].split("```", 1)[0]

    try:
        raw = yaml.safe_load(clean)
        if isinstance(raw, dict):
            return _parse_raw(raw)
    except Exception as e:
        print(f"    Parse error: {e}")
    return None


async def main():
    repo_path = Path("/tmp/test-arch-model/fastapi-realworld")

    print("=" * 60)
    print("MPC TRAINING LOOP - INTEGRATION TEST")
    print("=" * 60)

    # 1. Read code context
    print("\n[1] Reading code context from repo...")
    code = read_code_context(repo_path)
    print(f"    {len(code)} chars from {code.count('# ---')} files")

    # 2. Surrogate extraction (Ollama)
    print("\n[2] Surrogate extraction (qwen2.5:7b via Ollama)...")
    surrogate = Surrogate(model_name="qwen2.5:7b")
    local_model = await surrogate.extract_model(code)

    if local_model:
        confidence = surrogate.confidence(local_model)
        val_result = validate_model(local_model)
        print(f"    Entities: {local_model.entity_count}")
        print(f"    Relationships: {local_model.relationship_count}")
        print(f"    Confidence: {confidence:.2f}")
        print(f"    Validator score: {val_result.score}/100")
    else:
        print("    FAILED - got None (model could not be parsed from Ollama response)")
        return

    # 3. Oracle extraction (copilot-relay)
    print("\n[3] Oracle extraction (copilot-relay → GitHub Copilot)...")
    oracle_response = await call_copilot_relay(_EXTRACT_SYSTEM_PROMPT, code)

    if not oracle_response:
        print("    FAILED - empty response from relay")
        return

    oracle_model = parse_yaml_response(oracle_response)

    if oracle_model:
        oracle_val = validate_model(oracle_model)
        print(f"    Entities: {oracle_model.entity_count}")
        print(f"    Relationships: {oracle_model.relationship_count}")
        print(f"    Validator score: {oracle_val.score}/100")
    else:
        print(f"    FAILED to parse oracle response ({len(oracle_response)} chars)")
        print(f"    First 300 chars: {oracle_response[:300]}")
        return

    # 4. Evaluate loss
    print("\n[4] Computing loss (surrogate vs oracle)...")
    evaluator = Evaluator()
    loss = evaluator.compute_loss(local_model=local_model, oracle_model=oracle_model)
    print(f"    L1 (structural accuracy): {loss.structural_accuracy:.3f}")
    print(f"    L2 (completeness):        {loss.completeness:.3f}")
    print(f"    L3 (validator score):      {loss.validator_score:.1f}")

    # 5. Save to dataset store
    print("\n[5] Saving to dataset store...")
    store = DatasetStore("/tmp/test-arch-model/training.db")
    example = TrainingExample(
        repo_url="https://github.com/nsidnev/fastapi-realworld-example-app",
        repo_sha="HEAD",
        code_context=code[:5000],
        local_output=yaml.dump(
            {"entities": local_model.entity_count, "relationships": local_model.relationship_count}
        ),
        oracle_output=oracle_response[:5000],
        loss_vector={
            "L1": loss.structural_accuracy,
            "L2": loss.completeness,
            "L3": loss.validator_score,
        },
        iteration=1,
        metadata={"model": "qwen2.5:7b", "oracle": "copilot-relay"},
    )
    eid = store.save(example)
    print(f"    Saved example id={eid}")
    store.close()

    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
