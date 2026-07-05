#!/usr/bin/env python3
"""End-to-end test of oracle self-learning loop on a real repo via copilot-relay.

Tests:
1. Manifest quality (interfaces, blocks detected)
2. Extraction quality (validator score, coverage)
3. Self-critique improvement
4. Reproducibility (extract twice, compare structural similarity)

Usage: python scripts/test_oracle_learning.py [repo_path]
Default: /tmp/test-repos/pydantic/pydantic
"""

import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

import aiohttp
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import ArchitectureModel, RelationType
from architecture_model.core.validator import validate_model
from architecture_model.training.oracle_context import OracleContextBuilder
from architecture_model.training.oracle_coverage import ManifestCoverageComputer
from architecture_model.training.oracle_evolution import _BASE_EXTRACTION_PROMPT
from architecture_model.training.interface_enforcer import InterfaceEnforcer


COPILOT_RELAY_URL = "http://localhost:8400/chat"


def _strip_fences(text: str) -> str:
    """Strip markdown code fences."""
    if "```yaml" in text:
        text = text.split("```yaml", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return text.strip()


async def call_copilot_relay(content: str, system_prompt: str) -> str:
    """Call copilot-relay SSE endpoint and collect full response."""
    payload = {"content": content, "system_prompt": system_prompt}

    full_response = []
    async with aiohttp.ClientSession() as session:
        async with session.post(
            COPILOT_RELAY_URL, json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
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


async def extract_model(context: str, system_prompt: str) -> ArchitectureModel | None:
    """Extract architecture model via copilot-relay."""
    raw_response = await call_copilot_relay(context, system_prompt)

    cleaned = _strip_fences(raw_response)

    try:
        raw = yaml.safe_load(cleaned)
    except yaml.YAMLError as e:
        print(f"  [YAML parse error: {e}]")
        return None

    if not isinstance(raw, dict):
        print(f"  [Not a dict, got {type(raw).__name__}]")
        return None

    try:
        return _parse_raw(raw)
    except Exception as e:
        print(f"  [Model parse error: {e}]")
        return None


# ---------------------------------------------------------------------------
# Structural Comparison
# ---------------------------------------------------------------------------

def compare_models(a: ArchitectureModel, b: ArchitectureModel) -> dict:
    """Compare two architecture models structurally.

    Uses fuzzy matching for names (word overlap) and considers both
    .layer field AND allocated-to/contains relationships for decomposition.

    Returns a dict of similarity scores (0-1) across dimensions.
    """
    # Layer similarity (fuzzy: best bipartite matching on word sets)
    a_layers = [_normalize_name(l.name) for l in a.entities.layers]
    b_layers = [_normalize_name(l.name) for l in b.entities.layers]
    layer_sim = _fuzzy_set_similarity(a_layers, b_layers)

    # Component similarity (fuzzy matching)
    a_comps = [_normalize_name(c.name) for c in a.entities.components]
    b_comps = [_normalize_name(c.name) for c in b.entities.components]
    comp_sim = _fuzzy_set_similarity(a_comps, b_comps)

    # Capability similarity (fuzzy)
    a_caps = [_normalize_name(c.name) for c in a.entities.capabilities]
    b_caps = [_normalize_name(c.name) for c in b.entities.capabilities]
    cap_sim = _fuzzy_set_similarity(a_caps, b_caps)

    # Relationship type distribution (cosine similarity)
    a_rel_types = Counter(r.type.value for r in a.relationships)
    b_rel_types = Counter(r.type.value for r in b.relationships)
    rel_type_sim = _cosine_counters(a_rel_types, b_rel_types)

    # Relationship density ratio
    a_rels = len(a.relationships)
    b_rels = len(b.relationships)
    density_ratio = min(a_rels, b_rels) / max(a_rels, b_rels) if max(a_rels, b_rels) > 0 else 1.0

    # Decomposition: layer→component groupings (using BOTH .layer field and relationships)
    a_decomp = _layer_decomposition(a)
    b_decomp = _layer_decomposition(b)
    decomp_sim = _decomposition_similarity(a_decomp, b_decomp)

    # Entity count stability (are models at similar granularity?)
    a_total = len(a.entities.components) + len(a.entities.capabilities)
    b_total = len(b.entities.components) + len(b.entities.capabilities)
    granularity = min(a_total, b_total) / max(a_total, b_total) if max(a_total, b_total) > 0 else 1.0

    # Overall weighted score
    overall = (
        0.15 * layer_sim +
        0.25 * comp_sim +
        0.15 * cap_sim +
        0.15 * rel_type_sim +
        0.10 * density_ratio +
        0.10 * decomp_sim +
        0.10 * granularity
    )

    return {
        "layer_similarity": layer_sim,
        "component_similarity": comp_sim,
        "capability_similarity": cap_sim,
        "relationship_type_dist": rel_type_sim,
        "relationship_density": density_ratio,
        "decomposition_similarity": decomp_sim,
        "granularity_match": granularity,
        "overall": overall,
    }


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    return name.lower().replace("-", " ").replace("_", " ").strip()


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _cosine_counters(a: Counter, b: Counter) -> float:
    """Cosine similarity between two Counter distributions."""
    all_keys = set(a.keys()) | set(b.keys())
    if not all_keys:
        return 1.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in all_keys)
    mag_a = sum(v**2 for v in a.values()) ** 0.5
    mag_b = sum(v**2 for v in b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _fuzzy_set_similarity(a_names: list[str], b_names: list[str]) -> float:
    """Compute fuzzy set similarity using greedy bipartite word-Jaccard matching.

    For each item in the smaller set, find the best match in the larger set.
    Average the best-match scores.
    """
    if not a_names and not b_names:
        return 1.0
    if not a_names or not b_names:
        return 0.0

    # Always match from smaller to larger
    if len(a_names) > len(b_names):
        a_names, b_names = b_names, a_names

    # Greedy matching: for each in A, find best match in B
    used: set[int] = set()
    total_score = 0.0

    for a_item in a_names:
        a_words = set(a_item.split())
        best_score = 0.0
        best_idx = -1

        for i, b_item in enumerate(b_names):
            if i in used:
                continue
            b_words = set(b_item.split())
            score = _jaccard(a_words, b_words)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0:
            used.add(best_idx)
        total_score += best_score

    # Penalize size mismatch: average over the larger set size
    return total_score / max(len(a_names), len(b_names))


def _layer_decomposition(model: ArchitectureModel) -> dict[str, set[str]]:
    """Map layer names to sets of component names.

    Checks BOTH the .layer field on Component AND allocated-to/contains
    relationships from layers to components.
    """
    layer_id_to_name = {l.id: _normalize_name(l.name) for l in model.entities.layers}
    comp_id_to_name = {c.id: _normalize_name(c.name) for c in model.entities.components}
    layer_ids = set(layer_id_to_name.keys())
    comp_ids = set(comp_id_to_name.keys())

    decomp: dict[str, set[str]] = {}

    # Method 1: .layer field on Component
    for comp in model.entities.components:
        if comp.layer and comp.layer in layer_id_to_name:
            layer_name = layer_id_to_name[comp.layer]
            decomp.setdefault(layer_name, set()).add(_normalize_name(comp.name))

    # Method 2: relationships (contains, allocated-to)
    for rel in model.relationships:
        if rel.type.value in ("contains", "allocated-to"):
            # Layer → Component
            if rel.from_id in layer_ids and rel.to_id in comp_ids:
                layer_name = layer_id_to_name[rel.from_id]
                comp_name = comp_id_to_name[rel.to_id]
                decomp.setdefault(layer_name, set()).add(comp_name)
            # Component → Layer (allocated-to can go either direction)
            elif rel.to_id in layer_ids and rel.from_id in comp_ids:
                layer_name = layer_id_to_name[rel.to_id]
                comp_name = comp_id_to_name[rel.from_id]
                decomp.setdefault(layer_name, set()).add(comp_name)

    return decomp


def _decomposition_similarity(a: dict[str, set[str]], b: dict[str, set[str]]) -> float:
    """Compare layer→component groupings using fuzzy layer matching.

    Layers in A are matched to layers in B via word-Jaccard on their names,
    then we compare the component sets within matched layers.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    # Greedily match layers from A to B by name similarity
    a_layers = list(a.keys())
    b_layers = list(b.keys())
    used_b: set[int] = set()
    total_score = 0.0

    for a_layer in a_layers:
        a_words = set(a_layer.split())
        best_layer_score = 0.0
        best_b_idx = -1

        for i, b_layer in enumerate(b_layers):
            if i in used_b:
                continue
            b_words = set(b_layer.split())
            name_sim = _jaccard(a_words, b_words)
            if name_sim > best_layer_score:
                best_layer_score = name_sim
                best_b_idx = i

        if best_b_idx >= 0 and best_layer_score > 0.3:
            used_b.add(best_b_idx)
            # Compare component sets within matched layers
            a_comps = a[a_layer]
            b_comps = b[b_layers[best_b_idx]]
            # Fuzzy component matching within layers
            comp_sim = _fuzzy_set_similarity(
                [c for c in a_comps], [c for c in b_comps]
            )
            total_score += comp_sim
        # else: unmatched layer contributes 0

    return total_score / max(len(a_layers), len(b_layers))


def print_model_summary(model: ArchitectureModel, label: str):
    """Print a structural summary of a model."""
    print(f"  [{label}]")
    print(f"    Layers: {len(model.entities.layers)}")
    for l in model.entities.layers:
        n_comps = sum(1 for c in model.entities.components if c.layer == l.id)
        print(f"      - {l.name} ({n_comps} components)")
    print(f"    Components: {len(model.entities.components)}")
    print(f"    Capabilities: {len(model.entities.capabilities)}")
    print(f"    Relationships: {len(model.relationships)}")
    rel_types = Counter(r.type.value for r in model.relationships)
    for rt, count in rel_types.most_common():
        print(f"      - {rt}: {count}")
    val = validate_model(model)
    print(f"    Validator: {val.score}/100")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    repo_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/test-repos/pydantic")

    if not repo_path.exists():
        print(f"Error: {repo_path} does not exist")
        sys.exit(1)

    # Use pydantic/pydantic as the source
    source_path = repo_path / "pydantic"
    if not source_path.exists():
        source_path = repo_path

    print(f"{'='*60}")
    print(f"  ORACLE SELF-LEARNING TEST: {repo_path.name}")
    print(f"{'='*60}")
    print()

    # Step 1: Build manifest
    print("1. MANIFEST GENERATION")
    print("-" * 40)
    t0 = time.time()
    builder = OracleContextBuilder(source_path, max_chars=40000)
    manifest = builder._generate_manifest()
    context = builder.build(manifest)
    print(f"   Modules:          {len(manifest['modules'])}")
    print(f"   Interfaces:       {len(manifest['interfaces'])}")
    print(f"   Functional blocks: {len(manifest['functional_blocks'])}")
    for bid, bdata in manifest["functional_blocks"].items():
        print(f"     {bid}: {bdata['name']} ({len(bdata['sub_functions'])} files)")
    print(f"   Context chars:    {len(context)}")
    print(f"   Time:             {time.time() - t0:.1f}s")
    print()

    # Step 2: Extract twice for reproducibility
    print("2. REPRODUCIBILITY TEST (2 extractions, same input)")
    print("-" * 40)

    models = []
    for i in range(2):
        print(f"   Extraction {i+1}...")
        t0 = time.time()
        model = await extract_model(context, _BASE_EXTRACTION_PROMPT)
        elapsed = time.time() - t0

        if model is None:
            print(f"   FAILED — extraction {i+1} returned None")
            sys.exit(1)

        models.append(model)
        print(f"   Time: {elapsed:.1f}s")
        print_model_summary(model, f"Run {i+1}")
        print()

    # Compare (before enforcement, raw LLM output)
    print("   STRUCTURAL COMPARISON (raw LLM output):")
    sim = compare_models(models[0], models[1])
    for key, val in sim.items():
        bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
        print(f"   {key:30s} {bar} {val:.2%}")
    print()

    # Step 3: Interface enforcement
    print("3. INTERFACE ENFORCEMENT (manifest-derived dependencies)")
    print("-" * 40)
    enforcer = InterfaceEnforcer()
    enforced_models = []
    for i, model in enumerate(models):
        rels_before = len(model.relationships)
        enforcement = enforcer.enforce(model, manifest)
        enforced_models.append(enforcement.model)
        print(f"   [Run {i+1}] +{enforcement.added_count} rels, "
              f"{enforcement.skipped_count} skipped, "
              f"{enforcement.internal_count} internal "
              f"({rels_before} → {len(enforcement.model.relationships)} total)")
    print()

    # Step 4: Coverage analysis (after enforcement)
    print("4. MANIFEST COVERAGE (after enforcement)")
    print("-" * 40)
    computer = ManifestCoverageComputer()
    for i, model in enumerate(enforced_models):
        coverage = computer.compute(manifest, model)
        print(f"   [Run {i+1}]")
        print(f"     Module coverage:    {coverage.module_coverage:.2%}")
        print(f"     Interface coverage: {coverage.interface_coverage:.2%}")
        print(f"     Block coverage:     {coverage.block_coverage:.2%}")
        print(f"     Overall:            {coverage.overall:.2%}")
        if i == 0:
            uncov_mods = coverage.uncovered_modules
            uncov_ifaces = coverage.uncovered_interfaces
    print()

    # Step 5: Self-critique (using best enforced model)
    best_model = enforced_models[0]
    best_coverage = computer.compute(manifest, best_model)

    if best_coverage.overall < 0.85:
        print("5. SELF-CRITIQUE REFINEMENT")
        print("-" * 40)
        print(f"   Coverage {best_coverage.overall:.2%} < 85%, running critique...")

        # Build critique
        lines = ["## Self-Critique — Gaps Identified\n"]
        lines.append(f"Coverage score: {best_coverage.overall:.2f} (target: 0.85)\n")
        if uncov_mods:
            lines.append("### Uncovered Modules (must add components for these):")
            for mod in uncov_mods[:15]:
                lines.append(f"- `{mod}`")
        if uncov_ifaces:
            lines.append("\n### Uncovered Dependency Edges (must add relationships):")
            for src, tgt in uncov_ifaces[:15]:
                lines.append(f"- `{src}` → `{tgt}`")
        lines.append("\n**Re-extract ensuring these are represented.**")
        critique = "\n".join(lines)

        augmented = f"{context}\n\n{critique}"
        print(f"   Critique mentions {len(uncov_mods)} uncovered modules, {len(uncov_ifaces)} edges")

        t0 = time.time()
        refined = await extract_model(augmented, _BASE_EXTRACTION_PROMPT)
        elapsed = time.time() - t0

        if refined:
            print(f"   Time: {elapsed:.1f}s")
            print_model_summary(refined, "After Critique")

            cov_after = computer.compute(manifest, refined)
            print(f"\n   Coverage change:")
            print(f"     Module:    {best_coverage.module_coverage:.2%} → {cov_after.module_coverage:.2%}")
            print(f"     Interface: {best_coverage.interface_coverage:.2%} → {cov_after.interface_coverage:.2%}")
            print(f"     Block:     {best_coverage.block_coverage:.2%} → {cov_after.block_coverage:.2%}")
            print(f"     Overall:   {best_coverage.overall:.2%} → {cov_after.overall:.2%}")

            # Also compare structural stability with critique
            print(f"\n   Structural distance (original → critique):")
            sim_critique = compare_models(best_model, refined)
            for key, val in sim_critique.items():
                bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
                print(f"   {key:30s} {bar} {val:.2%}")
        else:
            print("   FAILED — critique extraction returned None")
    else:
        print("5. Self-critique SKIPPED (coverage >= 85%)")

    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
