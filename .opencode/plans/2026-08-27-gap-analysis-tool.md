# Gap Analysis Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a per-stage gap analysis tool that runs the deterministic pipeline, then asks an LLM to re-infer each stage's output from the same inputs, and produces a Markdown report showing deterministic vs LLM results with error propagation traces.

**Architecture:** A new `pipeline/gap_analysis.py` module orchestrates: (1) runs deterministic pipeline stages, (2) builds per-stage LLM prompts containing raw inputs that the deterministic stage received, (3) sends to LLM via `llm_provider.create_llm_callback()`, (4) parses structured JSON responses, (5) diffs deterministic vs LLM, (6) traces naming chains and error propagation forward. Output is `.architecture/gap-analysis.md`. CLI: both `architecture-model gap-analysis <path>` and `architecture-model pipeline <path> --gap-analysis`.

**Tech Stack:** Existing pipeline stages, `llm_provider.py` for LLM access, Markdown output.

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp`
**Branch:** `feature/model-quality-16wp`
**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
**Baseline:** 7 pre-existing failures, 1461 passed, 98 skipped

---

### Task 1: Per-Stage LLM Prompts Module

**Files:**
- Create: `src/architecture_model/pipeline/gap_prompts.py`
- Test: `tests/test_gap_prompts.py`

**Context:** This module builds LLM prompts for each pipeline stage. The prompt gives the LLM the SAME inputs that the deterministic stage received, and asks it to produce equivalent output. The key difference: the LLM uses domain understanding instead of heuristics.

Each prompt builder takes the prior stage outputs (exactly what the deterministic stage had) and returns a prompt string that asks the LLM to produce a JSON response in a specific schema.

**Step 1: Write failing tests**

```python
"""Tests for gap analysis LLM prompts."""
from pathlib import Path
from architecture_model.pipeline.gap_prompts import (
    build_observe_gap_prompt,
    build_infer_gap_prompt,
    build_allocate_gap_prompt,
    build_relate_gap_prompt,
    build_specify_gap_prompt,
    build_contract_gap_prompt,
    build_validate_gap_prompt,
    build_decompose_gap_prompt,
    parse_gap_response,
    GapResponse,
)
from architecture_model.pipeline.observe_types import ModuleRecord, ImportEdge


class TestBuildInferGapPrompt:
    def test_includes_module_details(self):
        mod = ModuleRecord(
            path=Path("src/dotenv/main.py"),
            functions=["load_dotenv", "dotenv_values"],
            classes=["DotEnv"],
            imports=["os", "io"],
            docstring="Module for loading .env files",
            quality_score=63,
        )
        prompt = build_infer_gap_prompt([mod], [])
        assert "main.py" in prompt
        assert "load_dotenv" in prompt
        assert "dotenv_values" in prompt
        assert "DotEnv" in prompt
        assert "capabilities" in prompt.lower()

    def test_requests_json_schema(self):
        prompt = build_infer_gap_prompt([], [])
        assert "capabilities" in prompt
        assert "actors" in prompt
        assert "behaviors" in prompt


class TestBuildAllocateGapPrompt:
    def test_includes_capabilities_and_modules(self):
        mod = ModuleRecord(path=Path("src/foo/bar.py"), functions=["baz"], classes=[], imports=[], quality_score=80)
        prompt = build_allocate_gap_prompt(
            modules=[mod],
            capabilities=[{"id": "CAP-1", "name": "FooBar"}],
            edges=[],
        )
        assert "bar.py" in prompt
        assert "CAP-1" in prompt
        assert "components" in prompt.lower()


class TestParseGapResponse:
    def test_parse_valid(self):
        resp = '{"entities": [{"id": "CAP-1", "name": "Env Loading", "type": "capability"}]}'
        parsed = parse_gap_response(resp)
        assert len(parsed.entities) == 1
        assert parsed.entities[0]["name"] == "Env Loading"

    def test_parse_markdown_wrapped(self):
        resp = '```json\n{"entities": [{"id": "C1", "name": "X", "type": "cap"}]}\n```'
        parsed = parse_gap_response(resp)
        assert len(parsed.entities) == 1

    def test_parse_empty(self):
        parsed = parse_gap_response("")
        assert parsed.entities == []

    def test_parse_invalid(self):
        parsed = parse_gap_response("not json")
        assert parsed.entities == []
```

**Step 2: Run to verify failure**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_prompts.py -v`
Expected: ImportError

**Step 3: Implement `gap_prompts.py`**

```python
"""Per-stage LLM prompts for gap analysis.

Each builder takes the SAME inputs the deterministic stage received
and asks the LLM to produce equivalent output using domain understanding.
"""
from __future__ import annotations

import json as _json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GapResponse:
    """Parsed LLM response for gap analysis."""
    entities: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    assessment: str = ""
    raw: str = ""


def _module_summary(mod: Any) -> str:
    """Format a ModuleRecord for inclusion in a prompt."""
    funcs = ", ".join(getattr(mod, "functions", [])[:15])
    classes = ", ".join(getattr(mod, "classes", [])[:10])
    imports = ", ".join(getattr(mod, "imports", [])[:10])
    doc = (getattr(mod, "docstring", "") or "")[:100]
    q = getattr(mod, "quality_score", "?")
    lines = [f"- **{mod.path}** (quality={q})"]
    if funcs:
        lines.append(f"  Functions: {funcs}")
    if classes:
        lines.append(f"  Classes: {classes}")
    if imports:
        lines.append(f"  Imports: {imports}")
    if doc:
        lines.append(f"  Docstring: {doc}")
    return "\n".join(lines)


def build_observe_gap_prompt(modules: list, edges: list) -> str:
    """Ask LLM to assess observe stage quality anomalies."""
    mod_summaries = "\n".join(_module_summary(m) for m in modules)
    return f"""# Observe Stage Gap Analysis

You have AST scan results for a Python project. Review the module quality scores and identify anomalies.

## Modules
{mod_summaries}

## Import Edges
{len(edges)} edges detected.

Return JSON:
```json
{{
  "entities": [
    {{"id": "module_path", "name": "module_name", "type": "module", "quality_assessment": "your assessment", "expected_quality": 80, "anomaly": true/false, "reason": "why"}}
  ],
  "assessment": "Overall observation assessment"
}}
```

Focus on: quality score anomalies, modules that seem important but score low, test files scored unfairly.
Return ONLY the JSON."""


def build_infer_gap_prompt(modules: list, edges: list) -> str:
    """Ask LLM to infer capabilities, actors, behaviors from raw module data."""
    source_mods = [m for m in modules
                   if not str(m.path).startswith("test") and "tests/" not in str(m.path)
                   and not str(m.path).endswith("conftest.py")]
    test_mods = [m for m in modules if m not in source_mods]

    src_summaries = "\n".join(_module_summary(m) for m in source_mods) or "(none)"
    test_summaries = "\n".join(f"- {m.path}: {len(getattr(m, 'functions', []))} test functions" for m in test_mods) or "(none)"

    return f"""# Infer Stage Gap Analysis

You are given AST-scanned module data for a Python library. Infer the architecture.

## Source Modules
{src_summaries}

## Test Modules
{test_summaries}

## Import Edges
{len(edges)} edges.

Based on the function names, class names, imports, and docstrings, infer:
1. **Capabilities** — What functional capabilities does this library provide? Name them by WHAT they do, not by file name.
2. **Actors** — Who/what interacts with this library?
3. **Behaviors** — What are the key use cases / workflows?

For each entity, provide:
- intent: What is its purpose?
- moes: How do you measure success?
- failure_modes: What can go wrong?

Return JSON:
```json
{{
  "entities": [
    {{"id": "CAP-1", "name": "descriptive name", "type": "capability", "intent": "...", "moes": ["..."], "failure_modes": ["..."]}},
    {{"id": "ACT-1", "name": "actor name", "type": "actor", "actor_type": "human|system"}},
    {{"id": "BHV-1", "name": "behavior name", "type": "behavior", "capability_id": "CAP-1", "steps": ["step1", "step2"]}}
  ],
  "assessment": "Overall inference assessment"
}}
```

IMPORTANT: Name capabilities by their DOMAIN PURPOSE (e.g., "Environment Variable Loading"), not by file name (not "Main").
Return ONLY the JSON."""


def build_allocate_gap_prompt(modules: list, capabilities: list[dict], edges: list) -> str:
    """Ask LLM to allocate modules to components."""
    source_mods = [m for m in modules
                   if not str(m.path).startswith("test") and "tests/" not in str(m.path)
                   and not str(m.path).endswith("conftest.py")]
    mod_list = "\n".join(f"- {m.path}: {', '.join(getattr(m, 'functions', [])[:5])} | {', '.join(getattr(m, 'classes', [])[:5])}"
                         for m in source_mods) or "(none)"
    cap_list = "\n".join(f"- {c['id']}: {c['name']}" for c in capabilities) or "(none)"

    return f"""# Allocate Stage Gap Analysis

Given these source modules and capabilities, group modules into architectural components.

## Source Modules
{mod_list}

## Capabilities (from infer stage)
{cap_list}

## Import Edges
{len(edges)} edges.

For each component:
- Assign a descriptive name (not file name)
- Assign a layer: web (HTTP/API), service (business logic), data (persistence), infra (utilities/config)
- List which files belong to it
- Link to the capability it realizes

Return JSON:
```json
{{
  "entities": [
    {{"id": "COMP-1", "name": "descriptive name", "type": "component", "layer": "service", "files": ["path/to/file.py"], "capability_id": "CAP-1", "intent": "what this component does"}}
  ],
  "assessment": "Overall allocation assessment"
}}
```

IMPORTANT: Choose layers based on FUNCTION, not file location. CLI entry points are 'web' or 'app', core logic is 'service', utilities are 'infra'.
Return ONLY the JSON."""


def build_relate_gap_prompt(components: list[dict], capabilities: list[dict], edges: list) -> str:
    """Ask LLM to derive relationships between entities."""
    comp_list = "\n".join(f"- {c['id']}: {c['name']} (layer={c.get('layer','?')}, files={c.get('files',[])})"
                          for c in components) or "(none)"
    cap_list = "\n".join(f"- {c['id']}: {c['name']}" for c in capabilities) or "(none)"

    edge_str = "\n".join(f"- {e.get('from', '?')} → {e.get('to', '?')}" for e in edges[:30]) if edges else "(none)"

    return f"""# Relate Stage Gap Analysis

Given components and capabilities, derive architectural relationships.

## Components
{comp_list}

## Capabilities
{cap_list}

## Import Edges (file-level, first 30)
{edge_str}

Derive relationships. Types available:
- realizes: component implements a capability
- depends-on: component depends on another component
- uses: component uses a utility component
- contains: layer contains a component
- exposes: component exposes an interface
- constrained-by: component is constrained by a non-functional requirement

Also identify any MISSING relationships or WRONG relationships the deterministic pipeline might produce.

Return JSON:
```json
{{
  "relationships": [
    {{"from_id": "COMP-1", "to_id": "CAP-1", "type": "realizes", "rationale": "why"}},
    {{"from_id": "COMP-1", "to_id": "COMP-2", "type": "depends-on", "rationale": "why"}}
  ],
  "assessment": "Overall relationship assessment"
}}
```

Return ONLY the JSON."""


def build_specify_gap_prompt(components: list[dict], modules: list) -> str:
    """Ask LLM to specify interfaces for components."""
    comp_details = []
    for c in components:
        files = c.get("files", [])
        funcs = []
        for m in modules:
            if str(m.path) in [str(f) for f in files]:
                funcs.extend(getattr(m, "functions", []))
        comp_details.append(f"- {c['id']}: {c['name']} — public functions: {', '.join(funcs[:10])}")

    comp_str = "\n".join(comp_details) or "(none)"

    return f"""# Specify Stage Gap Analysis

Given components and their public functions, specify the interfaces this system exposes.

## Components with Public API
{comp_str}

For each meaningful interface:
- Name it by what it DOES (e.g., "Environment Configuration API"), not by component ID
- Specify the type: rest, cli, library, event
- List the key methods/functions

Return JSON:
```json
{{
  "entities": [
    {{"id": "IF-1", "name": "descriptive name", "type": "interface", "interface_type": "library", "component_id": "COMP-1", "methods": ["func1", "func2"], "description": "what this interface provides"}}
  ],
  "assessment": "Overall interface assessment"
}}
```

Return ONLY the JSON."""


def build_contract_gap_prompt(test_files: list, components: list[dict]) -> str:
    """Ask LLM to map test files to components."""
    test_str = "\n".join(f"- {tf}" for tf in test_files[:20]) or "(none)"
    comp_str = "\n".join(f"- {c['id']}: {c['name']} (files: {c.get('files', [])})" for c in components) or "(none)"

    return f"""# Contract Stage Gap Analysis

Map test files to the components they test.

## Test Files
{test_str}

## Components
{comp_str}

Return JSON:
```json
{{
  "entities": [
    {{"id": "test_file_path", "name": "test name", "type": "contract", "component_id": "COMP-X", "rationale": "why this test tests this component"}}
  ],
  "assessment": "Overall test coverage assessment"
}}
```

Return ONLY the JSON."""


def build_validate_gap_prompt(model_summary: str) -> str:
    """Ask LLM to validate the architecture model."""
    return f"""# Validate Stage Gap Analysis

Review this architecture model for structural issues.

## Model Summary
{model_summary}

Identify:
1. Orphan entities (not connected to anything)
2. Missing relationships
3. Naming quality issues
4. Layer assignment problems
5. Capability coverage gaps

Return JSON:
```json
{{
  "entities": [
    {{"id": "issue_id", "name": "issue title", "type": "issue", "severity": "error|warning|info", "description": "what's wrong", "fix": "how to fix it"}}
  ],
  "assessment": "Overall validation assessment"
}}
```

Return ONLY the JSON."""


def build_decompose_gap_prompt(components: list[dict]) -> str:
    """Ask LLM to decide system boundaries."""
    comp_str = "\n".join(
        f"- {c['id']}: {c['name']} ({len(c.get('files', []))} files, layer={c.get('layer', '?')})"
        for c in components
    ) or "(none)"

    return f"""# Decompose Stage Gap Analysis

Given these components, should any be autonomous subsystems?

## Components
{comp_str}

Criteria for autonomous system: enough files (>=5), distinct bounded context, own lifecycle.
Small libraries typically have 0 autonomous subsystems and all components inline.

Return JSON:
```json
{{
  "entities": [
    {{"id": "comp_id", "name": "comp_name", "type": "system_decision", "decision": "autonomous|inline", "rationale": "why"}}
  ],
  "assessment": "Overall decomposition assessment"
}}
```

Return ONLY the JSON."""


def parse_gap_response(response: str) -> GapResponse:
    """Parse LLM gap analysis response."""
    if not response:
        return GapResponse(raw=response)

    text = response.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return GapResponse(raw=response)

    return GapResponse(
        entities=data.get("entities", []),
        relationships=data.get("relationships", []),
        assessment=data.get("assessment", ""),
        raw=response,
    )
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_prompts.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/gap_prompts.py tests/test_gap_prompts.py
git commit -m "feat(pipeline): per-stage LLM prompts for gap analysis"
```

---

### Task 2: Gap Analysis Engine

**Files:**
- Create: `src/architecture_model/pipeline/gap_analysis.py`
- Test: `tests/test_gap_analysis.py`

**Context:** This is the core engine. It runs the deterministic pipeline, then for each stage sends an LLM prompt and diffs the results. It produces a `GapReport` with per-stage gaps, naming chain comparisons, and error propagation traces.

**Step 1: Write failing tests**

```python
"""Tests for gap analysis engine."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from architecture_model.pipeline.gap_analysis import (
    run_gap_analysis,
    GapReport,
    StageGap,
    NamingChain,
    diff_entities,
    build_naming_chains,
)


class TestDiffEntities:
    def test_detects_name_difference(self):
        det = [{"id": "CAP-1", "name": "Main", "type": "capability"}]
        llm = [{"id": "CAP-1", "name": "Environment Loading", "type": "capability"}]
        gaps = diff_entities(det, llm, "infer")
        assert len(gaps) >= 1
        assert any("name" in g.field for g in gaps)

    def test_detects_missing_entity(self):
        det = [{"id": "CAP-1", "name": "Main", "type": "capability"}]
        llm = [
            {"id": "CAP-1", "name": "Main", "type": "capability"},
            {"id": "BHV-1", "name": "Load Env", "type": "behavior"},
        ]
        gaps = diff_entities(det, llm, "infer")
        assert any(g.category == "missing_in_deterministic" for g in gaps)

    def test_no_gaps_when_same(self):
        det = [{"id": "CAP-1", "name": "Foo", "type": "capability"}]
        llm = [{"id": "CAP-1", "name": "Foo", "type": "capability"}]
        gaps = diff_entities(det, llm, "infer")
        assert len(gaps) == 0


class TestBuildNamingChains:
    def test_traces_module_to_entity(self):
        det_infer = [{"id": "CAP-1", "name": "Main", "type": "capability"}]
        det_alloc = [{"id": "COMP-4", "name": "Main", "type": "component", "capability_id": "CAP-1"}]
        llm_infer = [{"id": "CAP-1", "name": "Environment Loading", "type": "capability"}]
        llm_alloc = [{"id": "COMP-4", "name": "DotenvLoader", "type": "component", "capability_id": "CAP-1"}]
        chains = build_naming_chains(
            det_stages={"infer": det_infer, "allocate": det_alloc},
            llm_stages={"infer": llm_infer, "allocate": llm_alloc},
        )
        assert len(chains) >= 1
        assert chains[0].deterministic_chain != chains[0].llm_chain
```

**Step 2: Run to verify failure**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_analysis.py -v`

**Step 3: Implement `gap_analysis.py`**

```python
"""Gap analysis engine — compares deterministic pipeline vs LLM re-inference.

Runs the deterministic pipeline, sends same inputs to LLM for each stage,
diffs results, traces naming chains and error propagation.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .gap_prompts import (
    build_observe_gap_prompt,
    build_infer_gap_prompt,
    build_allocate_gap_prompt,
    build_relate_gap_prompt,
    build_specify_gap_prompt,
    build_contract_gap_prompt,
    build_validate_gap_prompt,
    build_decompose_gap_prompt,
    parse_gap_response,
)


@dataclass
class EntityGap:
    """A single gap between deterministic and LLM output."""
    stage: str
    entity_id: str
    field: str
    category: str  # "name_mismatch", "missing_in_deterministic", "missing_in_llm", "value_mismatch", "extra_in_deterministic"
    deterministic_value: Any = ""
    llm_value: Any = ""
    severity: str = "important"  # critical, important, minor


@dataclass
class NamingChain:
    """Traces an entity's name through the pipeline stages."""
    entity_id: str
    deterministic_chain: dict[str, str] = field(default_factory=dict)  # stage -> name
    llm_chain: dict[str, str] = field(default_factory=dict)
    divergence_stage: str = ""  # first stage where names differ


@dataclass
class StageGap:
    """Gap analysis for one pipeline stage."""
    stage: str
    deterministic_summary: str = ""
    llm_summary: str = ""
    entity_gaps: list[EntityGap] = field(default_factory=list)
    llm_assessment: str = ""


@dataclass
class GapReport:
    """Full gap analysis report."""
    stage_gaps: list[StageGap] = field(default_factory=list)
    naming_chains: list[NamingChain] = field(default_factory=list)
    propagation_traces: list[str] = field(default_factory=list)
    overall_assessment: str = ""


def diff_entities(
    det_entities: list[dict],
    llm_entities: list[dict],
    stage: str,
) -> list[EntityGap]:
    """Diff deterministic vs LLM entities. Match by type+position, compare fields."""
    gaps: list[EntityGap] = []

    # Group by type
    det_by_type: dict[str, list[dict]] = {}
    llm_by_type: dict[str, list[dict]] = {}
    for e in det_entities:
        det_by_type.setdefault(e.get("type", "unknown"), []).append(e)
    for e in llm_entities:
        llm_by_type.setdefault(e.get("type", "unknown"), []).append(e)

    all_types = set(det_by_type.keys()) | set(llm_by_type.keys())
    for etype in all_types:
        dets = det_by_type.get(etype, [])
        llms = llm_by_type.get(etype, [])

        # Match by ID first, then by position
        det_by_id = {e["id"]: e for e in dets if "id" in e}
        llm_by_id = {e["id"]: e for e in llms if "id" in e}

        # Compare matched pairs
        for eid in det_by_id:
            if eid in llm_by_id:
                d, l = det_by_id[eid], llm_by_id[eid]
                for key in ("name", "intent", "layer", "interface_type"):
                    dv = d.get(key, "")
                    lv = l.get(key, "")
                    if dv and lv and str(dv).lower() != str(lv).lower():
                        gaps.append(EntityGap(
                            stage=stage, entity_id=eid, field=key,
                            category="name_mismatch" if key == "name" else "value_mismatch",
                            deterministic_value=dv, llm_value=lv,
                        ))

        # LLM entities not in deterministic
        for eid in llm_by_id:
            if eid not in det_by_id:
                gaps.append(EntityGap(
                    stage=stage, entity_id=eid, field="existence",
                    category="missing_in_deterministic",
                    llm_value=llm_by_id[eid].get("name", eid),
                    severity="critical" if etype == "behavior" else "important",
                ))

        # Extra LLM entities beyond matched count (for unmatched by ID)
        if len(llms) > len(dets):
            unmatched = [e for e in llms if e.get("id", "") not in det_by_id]
            for e in unmatched:
                if e.get("id", "") not in [g.entity_id for g in gaps]:
                    gaps.append(EntityGap(
                        stage=stage, entity_id=e.get("id", "?"), field="existence",
                        category="missing_in_deterministic",
                        llm_value=e.get("name", "?"),
                    ))

    return gaps


def build_naming_chains(
    det_stages: dict[str, list[dict]],
    llm_stages: dict[str, list[dict]],
) -> list[NamingChain]:
    """Build naming chains tracking entity names through stages."""
    chains: list[NamingChain] = []

    # Track capabilities through infer → allocate
    det_infer = det_stages.get("infer", [])
    llm_infer = llm_stages.get("infer", [])
    det_alloc = det_stages.get("allocate", [])
    llm_alloc = llm_stages.get("allocate", [])

    for i, det_cap in enumerate(det_infer):
        if det_cap.get("type") != "capability":
            continue
        cap_id = det_cap.get("id", f"CAP-{i+1}")
        chain = NamingChain(entity_id=cap_id)

        # Deterministic chain
        chain.deterministic_chain["infer"] = det_cap.get("name", "?")
        # Find matching component
        for comp in det_alloc:
            if comp.get("capability_id") == cap_id:
                chain.deterministic_chain["allocate"] = comp.get("name", "?")
                break

        # LLM chain
        llm_cap = llm_infer[i] if i < len(llm_infer) and llm_infer[i].get("type") == "capability" else None
        if llm_cap:
            chain.llm_chain["infer"] = llm_cap.get("name", "?")
        for comp in llm_alloc:
            if comp.get("capability_id") == cap_id:
                chain.llm_chain["allocate"] = comp.get("name", "?")
                break

        # Find divergence
        for stage in ["infer", "allocate"]:
            if chain.deterministic_chain.get(stage, "") != chain.llm_chain.get(stage, ""):
                chain.divergence_stage = stage
                break

        if chain.deterministic_chain != chain.llm_chain:
            chains.append(chain)

    return chains


async def _run_llm_stage(
    callback: Callable,
    stage_name: str,
    prompt: str,
) -> dict:
    """Run LLM for one stage and parse response."""
    response = await callback(stage_name, prompt, {"purpose": "gap_analysis"})
    parsed = parse_gap_response(response or "")
    return {
        "entities": parsed.entities,
        "relationships": parsed.relationships,
        "assessment": parsed.assessment,
    }


def run_gap_analysis(
    repo_path: Path,
    callback: Callable | None = None,
    stages: list[str] | None = None,
) -> GapReport:
    """Run full gap analysis: deterministic pipeline + LLM re-inference + diff.

    Args:
        repo_path: Path to the project to analyze.
        callback: Async LLM callback. If None, auto-detects.
        stages: Which stages to analyze. Default: all 8 (observe through decompose).

    Returns:
        GapReport with per-stage gaps, naming chains, propagation traces.
    """
    from .observe import ObserveStage
    from .infer import InferStage
    from .allocate import AllocateStage
    from .relate import RelateStage
    from .specify import SpecifyStage
    from .contract import ContractStage
    from .validate import ValidateStage
    from .decompose import DecomposeStage
    from .protocol import PipelineContext

    if callback is None:
        from .llm_provider import create_llm_callback
        callback = create_llm_callback()

    if callback is None:
        return GapReport(overall_assessment="No LLM provider available. Cannot run gap analysis.")

    if stages is None:
        stages = ["observe", "infer", "allocate", "relate", "specify", "contract", "validate", "decompose"]

    # Run deterministic pipeline
    output_dir = repo_path / ".architecture"
    ctx = PipelineContext(repo_path=repo_path, output_dir=output_dir)

    stage_map = {
        "observe": ObserveStage, "infer": InferStage, "allocate": AllocateStage,
        "relate": RelateStage, "specify": SpecifyStage, "contract": ContractStage,
        "validate": ValidateStage, "decompose": DecomposeStage,
    }
    all_stages = ["observe", "infer", "allocate", "relate", "specify", "contract", "validate", "decompose"]
    for name in all_stages:
        ctx.cache[name] = stage_map[name]().run(ctx)

    # Extract deterministic entities per stage
    det_entities: dict[str, list[dict]] = {}
    llm_entities: dict[str, list[dict]] = {}
    stage_gaps: list[StageGap] = []

    loop = asyncio.new_event_loop()

    for stage_name in stages:
        result = ctx.cache[stage_name]
        out = result.output

        # Extract deterministic entities
        det = _extract_det_entities(stage_name, out, ctx)
        det_entities[stage_name] = det

        # Build LLM prompt
        prompt = _build_prompt_for_stage(stage_name, ctx)
        if not prompt:
            continue

        # Call LLM
        llm_result = loop.run_until_complete(_run_llm_stage(callback, stage_name, prompt))
        llm_ents = llm_result["entities"]
        llm_entities[stage_name] = llm_ents

        # Diff
        entity_gaps = diff_entities(det, llm_ents, stage_name)

        # Build stage gap
        sg = StageGap(
            stage=stage_name,
            deterministic_summary=f"{len(det)} entities",
            llm_summary=f"{len(llm_ents)} entities",
            entity_gaps=entity_gaps,
            llm_assessment=llm_result.get("assessment", ""),
        )
        stage_gaps.append(sg)

    loop.close()

    # Build naming chains
    chains = build_naming_chains(det_entities, llm_entities)

    # Build propagation traces
    traces = _build_propagation_traces(stage_gaps)

    return GapReport(
        stage_gaps=stage_gaps,
        naming_chains=chains,
        propagation_traces=traces,
        overall_assessment=f"Analyzed {len(stages)} stages. Found {sum(len(sg.entity_gaps) for sg in stage_gaps)} gaps.",
    )


def _extract_det_entities(stage_name: str, output: Any, ctx: Any) -> list[dict]:
    """Extract entity dicts from deterministic stage output."""
    entities: list[dict] = []

    if stage_name == "observe":
        for m in output.modules:
            entities.append({
                "id": str(m.path), "name": m.path.stem, "type": "module",
                "quality": m.quality_score,
                "functions": list(getattr(m, "functions", [])),
                "classes": list(getattr(m, "classes", [])),
            })
    elif stage_name == "infer":
        for c in output.capabilities:
            entities.append({"id": c.id, "name": c.name, "type": "capability"})
        for a in output.actors:
            entities.append({"id": a.id, "name": a.name, "type": "actor"})
        for b in output.behaviors:
            entities.append({"id": b.id, "name": b.name, "type": "behavior"})
    elif stage_name == "allocate":
        for c in output.components:
            entities.append({
                "id": c.id, "name": c.name, "type": "component",
                "capability_id": c.capability_id, "layer": c.layer,
                "files": [str(f) for f in c.files],
            })
    elif stage_name == "relate":
        for r in output.relationships:
            entities.append({
                "id": f"{r.from_id}->{r.to_id}", "name": f"{r.from_id} {r.rel_type} {r.to_id}",
                "type": "relationship", "rel_type": r.rel_type,
            })
    elif stage_name == "specify":
        for i in output.interfaces:
            entities.append({
                "id": i.id, "name": i.name, "type": "interface",
                "interface_type": i.interface_type, "methods": i.methods,
            })
    elif stage_name == "contract":
        for c in output.contracts:
            entities.append({
                "id": c.test_file if hasattr(c, "test_file") else str(c),
                "name": c.name if hasattr(c, "name") else str(c),
                "type": "contract",
            })
    elif stage_name == "validate":
        # Diagnostics as entities
        for d in ctx.cache["validate"].diagnostics:
            entities.append({
                "id": d.code, "name": d.message, "type": "issue",
                "severity": d.severity,
            })
    elif stage_name == "decompose":
        for s in output.systems:
            entities.append({
                "id": s.id if hasattr(s, "id") else str(s),
                "name": s.name if hasattr(s, "name") else str(s),
                "type": "system",
            })
        for ic in output.inline_components:
            entities.append({"id": str(ic), "name": str(ic), "type": "inline_component"})

    return entities


def _build_prompt_for_stage(stage_name: str, ctx: Any) -> str:
    """Build the LLM re-inference prompt for a stage."""
    obs = ctx.cache["observe"].output

    if stage_name == "observe":
        return build_observe_gap_prompt(obs.modules, obs.edges)
    elif stage_name == "infer":
        return build_infer_gap_prompt(obs.modules, obs.edges)
    elif stage_name == "allocate":
        inf = ctx.cache["infer"].output
        caps = [{"id": c.id, "name": c.name} for c in inf.capabilities]
        return build_allocate_gap_prompt(obs.modules, caps, obs.edges)
    elif stage_name == "relate":
        alloc = ctx.cache["allocate"].output
        inf = ctx.cache["infer"].output
        comps = [{"id": c.id, "name": c.name, "layer": c.layer, "files": [str(f) for f in c.files]}
                 for c in alloc.components]
        caps = [{"id": c.id, "name": c.name} for c in inf.capabilities]
        edges = [{"from": str(e.source), "to": str(e.target)} for e in obs.edges[:30]]
        return build_relate_gap_prompt(comps, caps, edges)
    elif stage_name == "specify":
        alloc = ctx.cache["allocate"].output
        comps = [{"id": c.id, "name": c.name, "layer": c.layer, "files": [str(f) for f in c.files]}
                 for c in alloc.components]
        return build_specify_gap_prompt(comps, obs.modules)
    elif stage_name == "contract":
        alloc = ctx.cache["allocate"].output
        comps = [{"id": c.id, "name": c.name, "files": [str(f) for f in c.files]}
                 for c in alloc.components]
        test_files = [str(tf.path) if hasattr(tf, "path") else str(tf) for tf in obs.test_files]
        return build_contract_gap_prompt(test_files, comps)
    elif stage_name == "validate":
        # Summarize model so far
        inf = ctx.cache["infer"].output
        alloc = ctx.cache["allocate"].output
        rel = ctx.cache["relate"].output
        summary = (
            f"Capabilities: {', '.join(c.name for c in inf.capabilities)}\n"
            f"Components: {', '.join(c.name for c in alloc.components)}\n"
            f"Relationships: {len(rel.relationships)}\n"
            f"Boundary coherence: {alloc.boundary_coherence:.1f}%"
        )
        return build_validate_gap_prompt(summary)
    elif stage_name == "decompose":
        alloc = ctx.cache["allocate"].output
        comps = [{"id": c.id, "name": c.name, "layer": c.layer, "files": [str(f) for f in c.files]}
                 for c in alloc.components]
        return build_decompose_gap_prompt(comps)
    return ""


def _build_propagation_traces(stage_gaps: list[StageGap]) -> list[str]:
    """Build error propagation traces from early-stage gaps."""
    traces: list[str] = []

    # Find naming gaps in infer stage
    for sg in stage_gaps:
        if sg.stage != "infer":
            continue
        for gap in sg.entity_gaps:
            if gap.category == "name_mismatch" and gap.field == "name":
                # Trace forward
                trace = f"INFER: '{gap.deterministic_value}' (det) vs '{gap.llm_value}' (LLM)"
                # Check if same bad name appears in allocate
                for sg2 in stage_gaps:
                    if sg2.stage == "allocate":
                        for g2 in sg2.entity_gaps:
                            if g2.deterministic_value and gap.deterministic_value and \
                               gap.deterministic_value.lower() in str(g2.deterministic_value).lower():
                                trace += f"\n  → ALLOCATE: component also named '{g2.deterministic_value}'"
                traces.append(trace)

    return traces
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_analysis.py -v`

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/gap_analysis.py tests/test_gap_analysis.py
git commit -m "feat(pipeline): gap analysis engine with entity diffing, naming chains, and error propagation"
```

---

### Task 3: Markdown Report Generator

**Files:**
- Create: `src/architecture_model/pipeline/gap_report.py`
- Test: `tests/test_gap_report.py`

**Context:** Takes a `GapReport` and renders it as a readable Markdown document.

**Step 1: Write failing tests**

```python
"""Tests for gap analysis Markdown report."""
from architecture_model.pipeline.gap_report import render_gap_report
from architecture_model.pipeline.gap_analysis import GapReport, StageGap, EntityGap, NamingChain


class TestRenderGapReport:
    def test_includes_stage_headers(self):
        report = GapReport(stage_gaps=[
            StageGap(stage="infer", deterministic_summary="4 entities", llm_summary="6 entities"),
        ])
        md = render_gap_report(report)
        assert "## INFER" in md or "## Infer" in md

    def test_includes_entity_gaps(self):
        gap = EntityGap(
            stage="infer", entity_id="CAP-1", field="name",
            category="name_mismatch",
            deterministic_value="Main", llm_value="Environment Loading",
        )
        report = GapReport(stage_gaps=[
            StageGap(stage="infer", entity_gaps=[gap]),
        ])
        md = render_gap_report(report)
        assert "Main" in md
        assert "Environment Loading" in md

    def test_includes_naming_chains(self):
        chain = NamingChain(
            entity_id="CAP-1",
            deterministic_chain={"infer": "Main", "allocate": "Main"},
            llm_chain={"infer": "Env Loading", "allocate": "DotenvLoader"},
            divergence_stage="infer",
        )
        report = GapReport(naming_chains=[chain])
        md = render_gap_report(report)
        assert "Naming Chain" in md or "naming" in md.lower()

    def test_includes_propagation(self):
        report = GapReport(
            propagation_traces=["INFER: 'Main' → ALLOCATE: component 'Main'"],
        )
        md = render_gap_report(report)
        assert "propagat" in md.lower() or "Propagat" in md
```

**Step 2: Implement `gap_report.py`**

```python
"""Markdown report generator for gap analysis."""
from __future__ import annotations

from .gap_analysis import GapReport, StageGap, EntityGap, NamingChain


def render_gap_report(report: GapReport) -> str:
    """Render a GapReport as Markdown."""
    lines: list[str] = [
        "# Gap Analysis: Deterministic Pipeline vs LLM",
        "",
        f"> {report.overall_assessment}" if report.overall_assessment else "",
        "",
    ]

    # Per-stage sections
    for sg in report.stage_gaps:
        lines.append(f"## {sg.stage.upper()} Stage")
        lines.append("")
        lines.append(f"| | Deterministic | LLM |")
        lines.append(f"|---|---|---|")
        lines.append(f"| **Entities** | {sg.deterministic_summary} | {sg.llm_summary} |")
        lines.append("")

        if sg.llm_assessment:
            lines.append(f"**LLM Assessment:** {sg.llm_assessment}")
            lines.append("")

        if sg.entity_gaps:
            lines.append("### Gaps Found")
            lines.append("")
            lines.append("| Entity | Field | Category | Deterministic | LLM | Severity |")
            lines.append("|---|---|---|---|---|---|")
            for g in sg.entity_gaps:
                det_val = str(g.deterministic_value)[:40] if g.deterministic_value else "—"
                llm_val = str(g.llm_value)[:40] if g.llm_value else "—"
                lines.append(f"| {g.entity_id} | {g.field} | {g.category} | {det_val} | {llm_val} | {g.severity} |")
            lines.append("")
        else:
            lines.append("*No gaps detected.*")
            lines.append("")

    # Naming chains
    if report.naming_chains:
        lines.append("## Naming Chain Analysis")
        lines.append("")
        lines.append("Traces how entity names flow through pipeline stages.")
        lines.append("")
        for chain in report.naming_chains:
            lines.append(f"### {chain.entity_id}")
            lines.append("")
            all_stages = sorted(set(chain.deterministic_chain.keys()) | set(chain.llm_chain.keys()))
            lines.append("| Stage | Deterministic | LLM |")
            lines.append("|---|---|---|")
            for stage in all_stages:
                det = chain.deterministic_chain.get(stage, "—")
                llm = chain.llm_chain.get(stage, "—")
                marker = " **⬅ diverges**" if stage == chain.divergence_stage else ""
                lines.append(f"| {stage} | {det} | {llm}{marker} |")
            lines.append("")

    # Propagation traces
    if report.propagation_traces:
        lines.append("## Error Propagation Traces")
        lines.append("")
        lines.append("How early-stage errors cascade downstream.")
        lines.append("")
        for trace in report.propagation_traces:
            lines.append(f"```")
            lines.append(trace)
            lines.append(f"```")
            lines.append("")

    return "\n".join(lines)
```

**Step 3: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_gap_report.py -v`

**Step 4: Commit**

```bash
git add src/architecture_model/pipeline/gap_report.py tests/test_gap_report.py
git commit -m "feat(pipeline): Markdown report renderer for gap analysis"
```

---

### Task 4: CLI Integration

**Files:**
- Modify: `src/architecture_model/cli/main.py`
- Add test to: `tests/test_review_cli.py`

**Context:** Add two entry points:
1. `architecture-model gap-analysis <path>` — standalone command
2. `architecture-model pipeline <path> --gap-analysis` — pipeline flag

**Step 1: Write failing test**

Add to `tests/test_review_cli.py`:

```python
def test_gap_analysis_command_exists(self):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "architecture_model.cli.main", "gap-analysis", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0

def test_pipeline_gap_analysis_flag(self):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "architecture_model.cli.main", "pipeline", "--help"],
        capture_output=True, text=True,
    )
    assert "--gap-analysis" in result.stdout
```

**Step 2: Implement**

In `cli/main.py`, add a new subparser after the pipeline subparser (around line 113):

```python
# --- gap-analysis ---
p_gap = subparsers.add_parser("gap-analysis", help="Run gap analysis: deterministic vs LLM")
p_gap.add_argument("path", nargs="?", default=".", help="Project root directory")
p_gap.add_argument("-o", "--output", help="Output directory")
p_gap.add_argument("--stages", help="Comma-separated stages to analyze (default: all)")
```

Add `--gap-analysis` flag to pipeline subparser:
```python
p_pipeline.add_argument("--gap-analysis", action="store_true", help="Run gap analysis after pipeline")
```

Add to command dispatch:
```python
"gap-analysis": _cmd_gap_analysis,
```

Add the command function:

```python
def _cmd_gap_analysis(args) -> int:
    """Run gap analysis: deterministic pipeline vs LLM re-inference."""
    from ..pipeline.gap_analysis import run_gap_analysis
    from ..pipeline.gap_report import render_gap_report
    from ..pipeline.llm_provider import create_llm_callback

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    output_dir = Path(args.output).resolve() if args.output else root / ".architecture"
    callback = create_llm_callback()
    if not callback:
        print("ERROR: No LLM provider available (need copilot-relay, OPENAI_API_KEY, or ANTHROPIC_API_KEY)")
        return 1

    stages = args.stages.split(",") if args.stages else None
    print(f"Running gap analysis on {root}...")
    report = run_gap_analysis(root, callback=callback, stages=stages)

    md = render_gap_report(report)
    output_path = output_dir / "gap-analysis.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md)

    print(md)
    print(f"\nReport saved to: {output_path}")
    return 0
```

In `_cmd_pipeline`, after the existing review saving code, add:

```python
if getattr(args, "gap_analysis", False):
    from ..pipeline.gap_analysis import run_gap_analysis
    from ..pipeline.gap_report import render_gap_report
    print("\nRunning gap analysis...")
    gap_report = run_gap_analysis(root, callback=ctx.llm_callback)
    md = render_gap_report(gap_report)
    gap_path = output_dir / "gap-analysis.md"
    gap_path.write_text(md)
    print(md)
    print(f"\nGap analysis saved to: {gap_path}")
```

**Step 3: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_review_cli.py -v`

**Step 4: Commit**

```bash
git add src/architecture_model/cli/main.py tests/test_review_cli.py
git commit -m "feat(cli): add gap-analysis command and --gap-analysis pipeline flag"
```

---

### Task 5: Full Suite Verification + Push

**Step 1: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: 7 pre-existing failures, ~1475+ passed, 0 regressions

**Step 2: E2E test (manual, if copilot-relay available)**

Run: `architecture-model gap-analysis projects/python-dotenv`
Expected: Full gap analysis report printed and saved.

**Step 3: Push**

```bash
git -c http.proxy="" push https://opn-arch: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@github.com/opn-arch/architecture-model-standard.git feature/model-quality-16wp
```
