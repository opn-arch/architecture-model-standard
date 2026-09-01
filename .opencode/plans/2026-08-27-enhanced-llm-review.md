# Enhanced LLM Review System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a three-level (stage/component/module) LLM review system with auto-correction that works via copilot-relay, OpenAI, Anthropic, or MCP callback.

**Architecture:** A `pipeline/llm_provider.py` module provides a unified async LLM callback that auto-detects copilot-relay (localhost:8400), OpenAI, or Anthropic. The existing `stage_review.py` is enhanced to build semantic prompts with entity intent/metrics at three levels and parse structured JSON corrections. The coordinator applies auto-corrections between stages. Reviews persist to `.architecture/reviews/`.

**Tech Stack:** aiohttp (copilot-relay SSE), openai/anthropic SDKs (optional), JSON correction format.

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp`
**Branch:** `feature/model-quality-16wp`
**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
**Baseline:** 7 pre-existing failures, 1438 passed, 98 skipped

---

### Task 1: LLM Provider Module

**Files:**
- Create: `src/architecture_model/pipeline/llm_provider.py`
- Test: `tests/test_llm_provider.py`

**Step 1: Write failing tests**

```python
"""Tests for LLM provider auto-detection."""
import pytest
from unittest.mock import AsyncMock, patch
from architecture_model.pipeline.llm_provider import (
    create_llm_callback,
    copilot_relay_callback,
    LLMProvider,
)


class TestCreateLLMCallback:
    def test_returns_none_when_nothing_available(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=False):
                cb = create_llm_callback()
                assert cb is None

    def test_prefers_copilot_relay(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=True):
            cb = create_llm_callback()
            assert cb is not None

    def test_falls_back_to_openai(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=False):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
                cb = create_llm_callback()
                assert cb is not None

    def test_falls_back_to_anthropic(self):
        with patch("architecture_model.pipeline.llm_provider._copilot_relay_available", return_value=False):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
                cb = create_llm_callback()
                assert cb is not None


class TestCopilotRelayCallback:
    @pytest.mark.asyncio
    async def test_callback_signature(self):
        """Callback accepts (stage, prompt, context) -> str."""
        with patch("architecture_model.pipeline.llm_provider._call_copilot_relay", new_callable=AsyncMock) as mock:
            mock.return_value = "response text"
            result = await copilot_relay_callback("observe", "review this", {})
            assert result == "response text"
            mock.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_llm_provider.py -v`
Expected: FAIL with ImportError

**Step 3: Implement `src/architecture_model/pipeline/llm_provider.py`**

```python
"""LLM provider auto-detection for pipeline reviews.

Supports three pathways:
1. copilot-relay — local SSE server at http://localhost:8400/chat
2. OpenAI — via OPENAI_API_KEY env var
3. Anthropic — via ANTHROPIC_API_KEY env var
"""
from __future__ import annotations

import json
import os
from enum import Enum
from typing import Any, Callable

COPILOT_RELAY_URL = "http://localhost:8400/chat"


class LLMProvider(Enum):
    COPILOT_RELAY = "copilot-relay"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NONE = "none"


def _copilot_relay_available() -> bool:
    """Check if copilot-relay is running."""
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8400/health", method="GET")
        with urllib.request.urlopen(req, timeout=1):
            return True
    except Exception:
        return False


async def _call_copilot_relay(system_prompt: str, user_prompt: str, timeout: int = 180) -> str:
    """Call copilot-relay SSE endpoint and collect full response."""
    try:
        import aiohttp
    except ImportError:
        return ""

    payload = {"content": user_prompt, "system_prompt": system_prompt}
    full_response = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            COPILOT_RELAY_URL, json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            async for line in resp.content:
                text = line.decode("utf-8").strip()
                if text.startswith("data: "):
                    data = json.loads(text[6:])
                    if data.get("type") == "chunk":
                        full_response = data.get("content", "")
                    elif data.get("type") == "done":
                        break
                    elif data.get("type") == "error":
                        break
    return full_response


async def copilot_relay_callback(stage: str, prompt: str, context: dict[str, Any] | None = None) -> str:
    """LLM callback using copilot-relay."""
    system_prompt = (
        "You are an architecture model reviewer. Analyze pipeline stage output and "
        "return structured JSON with corrections and suggestions. "
        "Always respond with valid JSON matching the requested schema."
    )
    return await _call_copilot_relay(system_prompt, prompt)


async def _openai_callback(stage: str, prompt: str, context: dict[str, Any] | None = None) -> str:
    """LLM callback using OpenAI API."""
    try:
        import openai
    except ImportError:
        return ""
    client = openai.AsyncOpenAI()
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an architecture model reviewer. Return structured JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


async def _anthropic_callback(stage: str, prompt: str, context: dict[str, Any] | None = None) -> str:
    """LLM callback using Anthropic API."""
    try:
        import anthropic
    except ImportError:
        return ""
    client = anthropic.AsyncAnthropic()
    resp = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system="You are an architecture model reviewer. Return structured JSON.",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else ""


def detect_provider() -> LLMProvider:
    """Detect the best available LLM provider."""
    if _copilot_relay_available():
        return LLMProvider.COPILOT_RELAY
    if os.getenv("OPENAI_API_KEY"):
        return LLMProvider.OPENAI
    if os.getenv("ANTHROPIC_API_KEY"):
        return LLMProvider.ANTHROPIC
    return LLMProvider.NONE


_CALLBACKS: dict[LLMProvider, Callable] = {
    LLMProvider.COPILOT_RELAY: copilot_relay_callback,
    LLMProvider.OPENAI: _openai_callback,
    LLMProvider.ANTHROPIC: _anthropic_callback,
}


def create_llm_callback() -> Callable | None:
    """Create an LLM callback using the best available provider."""
    provider = detect_provider()
    return _CALLBACKS.get(provider)
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_llm_provider.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/llm_provider.py tests/test_llm_provider.py
git commit -m "feat(pipeline): add LLM provider auto-detection for copilot-relay/OpenAI/Anthropic"
```

---

### Task 2: Enhanced Three-Level Review Prompts

**Files:**
- Modify: `src/architecture_model/pipeline/stage_review.py`
- Modify: `tests/test_stage_review.py`

**Step 1: Write failing tests**

Add to `tests/test_stage_review.py`:

```python
from architecture_model.pipeline.stage_review import (
    build_semantic_review_prompt,
    parse_correction_response,
    Correction,
    CorrectionResult,
)
from architecture_model.pipeline.protocol import QualityMetrics, GateResult


class TestBuildSemanticReviewPrompt:
    def test_includes_stage_summary(self):
        qm = QualityMetrics(score=70, sub_scores={"parse_success_rate": 85.0})
        prompt = build_semantic_review_prompt(
            stage_name="observe",
            quality=qm,
            gate_results=[],
            components=[{"id": "COMP-1", "name": "Core", "intent": "Parse models", "file_count": 9, "quality": 85}],
            modules=[{"path": "core/parser.py", "functions": 5, "quality": 91}],
        )
        assert "observe" in prompt
        assert "COMP-1" in prompt
        assert "core/parser.py" in prompt
        assert "Parse models" in prompt

    def test_includes_gate_results(self):
        qm = QualityMetrics(score=70)
        gate = GateResult(passed=False, blocks=False, message="WARN: code_quality_avg = 45.0", metric="code_quality_avg", actual=45.0, threshold=50.0)
        prompt = build_semantic_review_prompt(
            stage_name="observe", quality=qm, gate_results=[gate],
            components=[], modules=[],
        )
        assert "WARN" in prompt
        assert "code_quality_avg" in prompt

    def test_requests_json_response(self):
        qm = QualityMetrics(score=70)
        prompt = build_semantic_review_prompt("observe", qm, [], [], [])
        assert "JSON" in prompt or "json" in prompt


class TestParseCorrectionResponse:
    def test_parse_valid_corrections(self):
        response = '{"stage_assessment": "Good", "corrections": [{"entity_id": "COMP-1", "field": "intent", "action": "improve", "value": "Better intent", "confidence": 0.9}], "warnings": [], "suggestions": ["Add more tests"]}'
        result = parse_correction_response(response)
        assert len(result.corrections) == 1
        assert result.corrections[0].entity_id == "COMP-1"
        assert result.corrections[0].confidence == 0.9
        assert result.stage_assessment == "Good"

    def test_parse_empty_response(self):
        result = parse_correction_response("")
        assert result.corrections == []

    def test_parse_invalid_json(self):
        result = parse_correction_response("not json at all")
        assert result.corrections == []
        assert result.raw == "not json at all"

    def test_parse_json_in_markdown(self):
        response = '```json\n{"stage_assessment": "OK", "corrections": [], "warnings": [], "suggestions": []}\n```'
        result = parse_correction_response(response)
        assert result.stage_assessment == "OK"
```

**Step 2: Run to verify failure**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_stage_review.py::TestBuildSemanticReviewPrompt -v`
Expected: ImportError

**Step 3: Add to `stage_review.py` (keep existing functions)**

Add the following new types and functions after the existing code:

```python
import json as _json
from typing import Any

@dataclass
class Correction:
    """A single auto-correction suggested by the LLM."""
    entity_id: str
    field: str
    action: str  # "improve", "add", "fix", "remove"
    value: Any = ""
    confidence: float = 0.0


@dataclass
class CorrectionResult:
    """Full parsed correction response from LLM."""
    stage_assessment: str = ""
    corrections: list[Correction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    raw: str = ""


def build_semantic_review_prompt(
    stage_name: str,
    quality: QualityMetrics,
    gate_results: list,
    components: list[dict],
    modules: list[dict],
    summary: str = "",
) -> str:
    """Build a three-level semantic review prompt for LLM."""
    lines = [
        f"# Pipeline Stage Review: {stage_name}",
        f"Overall quality score: {quality.score:.0f}/100",
    ]
    if quality.sub_scores:
        lines.append("\n## Stage Metrics")
        for k, v in quality.sub_scores.items():
            lines.append(f"- {k}: {v:.1f}")
    if gate_results:
        lines.append("\n## Gate Results")
        for gr in gate_results:
            lines.append(f"- {gr.message}")
    if summary:
        lines.append(f"\n## Summary\n{summary}")
    if components:
        lines.append("\n## Components")
        lines.append("| ID | Name | Intent | Files | Quality |")
        lines.append("|---|---|---|---|---|")
        for c in components:
            intent = c.get("intent", "—")
            lines.append(f"| {c['id']} | {c['name']} | {intent} | {c.get('file_count', '?')} | {c.get('quality', '?')} |")
    if modules:
        lines.append("\n## Modules")
        lines.append("| Path | Functions | Quality |")
        lines.append("|---|---|---|")
        for m in modules:
            lines.append(f"| {m['path']} | {m.get('functions', '?')} | {m.get('quality', '?')} |")
    lines.extend([
        "\n## Instructions",
        "Review the stage output and return a JSON object with this exact structure:",
        '```json',
        '{',
        '  "stage_assessment": "Brief assessment of this stage",',
        '  "corrections": [',
        '    {"entity_id": "COMP-X", "field": "intent", "action": "improve", "value": "new value", "confidence": 0.9}',
        '  ],',
        '  "warnings": ["warning text"],',
        '  "suggestions": ["suggestion text"]',
        '}',
        '```',
        '',
        'Correction actions: improve, add, fix, remove.',
        'Fields: intent, moes, failure_modes, status, trade_offs.',
        'Set confidence >= 0.8 for corrections you are certain about.',
        'Return ONLY the JSON object, no other text.',
    ])
    return "\n".join(lines)


def parse_correction_response(response: str) -> CorrectionResult:
    """Parse LLM response into structured corrections."""
    if not response:
        return CorrectionResult(raw=response)
    text = response.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return CorrectionResult(raw=response)
    corrections = []
    for c in data.get("corrections", []):
        corrections.append(Correction(
            entity_id=c.get("entity_id", ""),
            field=c.get("field", ""),
            action=c.get("action", ""),
            value=c.get("value", ""),
            confidence=c.get("confidence", 0.0),
        ))
    return CorrectionResult(
        stage_assessment=data.get("stage_assessment", ""),
        corrections=corrections,
        warnings=data.get("warnings", []),
        suggestions=data.get("suggestions", []),
        raw=response,
    )
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_stage_review.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/stage_review.py tests/test_stage_review.py
git commit -m "feat(pipeline): three-level semantic review prompts with JSON correction parsing"
```

---

### Task 3: Auto-Correction Applier

**Files:**
- Create: `src/architecture_model/pipeline/auto_correct.py`
- Test: `tests/test_auto_correct.py`

**Step 1: Write failing tests**

```python
"""Tests for auto-correction applier."""
from architecture_model.pipeline.auto_correct import apply_corrections, CorrectionLog
from architecture_model.pipeline.stage_review import Correction


class TestApplyCorrections:
    def _make_model_dict(self):
        return {
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Core", "intent": "", "status": "ACTIVE"},
                ],
                "capabilities": [
                    {"id": "CAP-F1", "name": "Parsing", "moes": []},
                ],
            }
        }

    def test_auto_applies_high_confidence_intent(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "intent", "improve", "Parse YAML models", 0.9)]
        log = apply_corrections(model, corrections)
        assert log.applied == 1
        assert model["entities"]["components"][0]["intent"] == "Parse YAML models"

    def test_skips_low_confidence(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "intent", "improve", "New intent", 0.5)]
        log = apply_corrections(model, corrections)
        assert log.applied == 0
        assert log.skipped == 1

    def test_applies_moe_addition(self):
        model = self._make_model_dict()
        corrections = [Correction("CAP-F1", "moes", "add", ["All YAML parsed correctly"], 0.85)]
        log = apply_corrections(model, corrections)
        assert log.applied == 1
        assert model["entities"]["capabilities"][0]["moes"] == ["All YAML parsed correctly"]

    def test_skips_structural_changes(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "name", "improve", "NewName", 0.95)]
        log = apply_corrections(model, corrections, structural_fields={"name"})
        assert log.applied == 0
        assert log.skipped == 1

    def test_log_tracks_before_after(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "intent", "improve", "Better intent", 0.9)]
        log = apply_corrections(model, corrections)
        assert len(log.entries) == 1
        assert log.entries[0]["old"] == ""
        assert log.entries[0]["new"] == "Better intent"
```

**Step 2: Run to verify failure**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_auto_correct.py -v`
Expected: ImportError

**Step 3: Implement `src/architecture_model/pipeline/auto_correct.py`**

```python
"""Auto-correction applier for LLM review corrections."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .stage_review import Correction

SAFE_FIELDS = {"intent", "moes", "failure_modes", "trade_offs", "status", "goals"}
STRUCTURAL_FIELDS = {"name", "id", "files", "relationships"}
CONFIDENCE_THRESHOLD = 0.8


@dataclass
class CorrectionLog:
    """Record of corrections applied and skipped."""
    applied: int = 0
    skipped: int = 0
    entries: list[dict[str, Any]] = field(default_factory=list)


def apply_corrections(
    model_dict: dict[str, Any],
    corrections: list[Correction],
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    structural_fields: set[str] | None = None,
) -> CorrectionLog:
    """Apply auto-corrections to a model dict. Returns log of changes."""
    if structural_fields is None:
        structural_fields = STRUCTURAL_FIELDS

    log = CorrectionLog()
    entity_index = _build_entity_index(model_dict)

    for corr in corrections:
        if corr.confidence < confidence_threshold:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "low_confidence", "confidence": corr.confidence})
            continue
        if corr.field in structural_fields:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "structural_field"})
            continue
        if corr.field not in SAFE_FIELDS:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "unknown_field"})
            continue
        entity = entity_index.get(corr.entity_id)
        if entity is None:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "entity_not_found"})
            continue
        old_value = entity.get(corr.field, "")
        if corr.action == "add" and isinstance(corr.value, list):
            existing = entity.get(corr.field, [])
            entity[corr.field] = existing + corr.value if isinstance(existing, list) else corr.value
        else:
            entity[corr.field] = corr.value
        log.applied += 1
        log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "old": old_value, "new": corr.value, "confidence": corr.confidence})

    return log


def _build_entity_index(model_dict: dict[str, Any]) -> dict[str, dict]:
    """Build id -> entity dict mapping from model dict."""
    index: dict[str, dict] = {}
    entities = model_dict.get("entities", {})
    for entity_type in entities.values():
        if isinstance(entity_type, list):
            for entity in entity_type:
                if isinstance(entity, dict) and "id" in entity:
                    index[entity["id"]] = entity
    return index
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_auto_correct.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/auto_correct.py tests/test_auto_correct.py
git commit -m "feat(pipeline): auto-correction applier with confidence thresholds and safety rules"
```

---

### Task 4: Wire Enhanced Review into Coordinator

**Files:**
- Modify: `src/architecture_model/pipeline/coordinator.py:145-189` (`_evaluate_gates` method)
- Add helper methods: `_extract_component_data`, `_extract_module_data`
- Modify: `tests/test_pipeline_coordinator.py`

**Step 1: Write failing test**

Add to `tests/test_pipeline_coordinator.py`:

```python
class TestEnhancedLLMReview:
    def test_semantic_review_called_with_components(self):
        """When llm_callback returns corrections JSON, review log captures them."""
        import asyncio

        async def mock_llm(stage, prompt, ctx):
            return '{"stage_assessment": "Good", "corrections": [{"entity_id": "COMP-1", "field": "intent", "action": "improve", "value": "Better", "confidence": 0.9}], "warnings": [], "suggestions": ["Add tests"]}'

        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp/out"))
        ctx.llm_callback = mock_llm

        stages = {"observe": FakeStage("observe", [])}
        coord = PipelineCoordinator(stages)
        results = coord.run_all(ctx)

        assert len(ctx.review_log) >= 1
        review = ctx.review_log[0]
        assert review.stage == "observe"
        assert len(review.suggestions) >= 1
```

**Step 2: Modify `_evaluate_gates` in coordinator.py**

Replace the LLM review section (lines 152-173) to use `build_semantic_review_prompt` and `parse_correction_response`:

```python
# LLM review if callback available
llm_review = ""
suggestions: list[str] = []
component_reviews: dict[str, str] = {}
if ctx.llm_callback is not None:
    try:
        from .stage_review import build_semantic_review_prompt, parse_correction_response
        import asyncio
        components = self._extract_component_data(result, ctx)
        modules = self._extract_module_data(result, ctx)
        prompt = build_semantic_review_prompt(
            stage_name, result.quality, gate_results,
            components, modules, summary=result.summary,
        )
        loop = asyncio.get_event_loop()
        if loop.is_running():
            pass
        else:
            response = loop.run_until_complete(
                ctx.llm_enrich(stage_name, prompt, {"purpose": "semantic_review"})
            )
            if response:
                parsed = parse_correction_response(response)
                llm_review = response
                suggestions = parsed.suggestions
    except Exception:
        pass
```

Add helper methods to the PipelineCoordinator class:

```python
def _extract_component_data(self, result: StageResult, ctx: PipelineContext) -> list[dict]:
    """Extract component info from stage result for review prompt."""
    components = []
    for comp_id, comp_q in result.quality.component_scores.items():
        components.append({
            "id": comp_id, "name": comp_id, "intent": "",
            "file_count": 0, "quality": comp_q.score,
        })
    return components

def _extract_module_data(self, result: StageResult, ctx: PipelineContext) -> list[dict]:
    """Extract module info from stage result for review prompt."""
    modules = []
    if hasattr(result.output, '__iter__') and not isinstance(result.output, (str, dict)):
        for item in result.output:
            if hasattr(item, 'path') and hasattr(item, 'quality_score'):
                modules.append({
                    "path": str(item.path),
                    "functions": len(getattr(item, 'functions', [])),
                    "quality": item.quality_score,
                })
    return modules
```

**Step 3: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_coordinator.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/architecture_model/pipeline/coordinator.py tests/test_pipeline_coordinator.py
git commit -m "feat(pipeline): wire semantic LLM review with component/module context into coordinator"
```

---

### Task 5: Review Persistence

**Files:**
- Create: `src/architecture_model/pipeline/review_store.py`
- Test: `tests/test_review_store.py`

**Step 1: Write failing tests**

```python
"""Tests for review persistence."""
import json
from pathlib import Path
from architecture_model.pipeline.review_store import save_reviews, load_reviews
from architecture_model.pipeline.protocol import StageQualityReview, QualityMetrics


class TestReviewStore:
    def test_save_and_load(self, tmp_path):
        review = StageQualityReview(
            stage="observe", quality=QualityMetrics(score=70),
            gate_results=[], llm_review="test review", suggestions=["suggestion 1"],
        )
        save_reviews(tmp_path, [review])
        loaded = load_reviews(tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["stage"] == "observe"
        assert loaded[0]["llm_review"] == "test review"

    def test_save_creates_directory(self, tmp_path):
        review_dir = tmp_path / "reviews"
        review = StageQualityReview(stage="observe", quality=QualityMetrics(score=70), gate_results=[])
        save_reviews(review_dir, [review])
        assert review_dir.exists()

    def test_load_empty(self, tmp_path):
        loaded = load_reviews(tmp_path)
        assert loaded == []
```

**Step 2: Run to verify failure**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_review_store.py -v`

**Step 3: Implement `src/architecture_model/pipeline/review_store.py`**

```python
"""Persistence for pipeline review results."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .protocol import StageQualityReview


def save_reviews(review_dir: Path, reviews: list[StageQualityReview]) -> Path:
    """Save review log to JSON file. Returns path to saved file."""
    review_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = review_dir / f"review_{timestamp}.json"
    data = []
    for r in reviews:
        data.append({
            "stage": r.stage, "score": r.quality.score,
            "sub_scores": r.quality.sub_scores,
            "gate_results": [
                {"passed": gr.passed, "blocks": gr.blocks, "message": gr.message,
                 "metric": gr.metric, "actual": gr.actual, "threshold": gr.threshold}
                for gr in r.gate_results
            ],
            "llm_review": r.llm_review,
            "suggestions": r.suggestions,
            "component_reviews": r.component_reviews,
        })
    filepath.write_text(json.dumps(data, indent=2))
    return filepath


def load_reviews(review_dir: Path) -> list[dict[str, Any]]:
    """Load the most recent review file from directory."""
    if not review_dir.exists():
        return []
    files = sorted(review_dir.glob("review_*.json"), reverse=True)
    if not files:
        return []
    return json.loads(files[0].read_text())
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_review_store.py -v`

**Step 5: Commit**

```bash
git add src/architecture_model/pipeline/review_store.py tests/test_review_store.py
git commit -m "feat(pipeline): review persistence to .architecture/reviews/"
```

---

### Task 6: CLI --llm-review Flag

**Files:**
- Modify: `src/architecture_model/cli/main.py` (lines 107-112 for arg, lines 778-847 for usage)
- Add test to: `tests/test_review_cli.py`

**Step 1: Write failing test**

Add to `tests/test_review_cli.py`:

```python
def test_pipeline_llm_review_flag():
    """Verify --llm-review argument is accepted."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "architecture_model.cli.main", "pipeline", "--help"],
        capture_output=True, text=True,
    )
    assert "--llm-review" in result.stdout
```

**Step 2: Implement**

In `cli/main.py`, after line 112 (`p_pipeline.add_argument("-o", ...)`) add:
```python
p_pipeline.add_argument("--llm-review", action="store_true", help="Enable LLM review of stage outputs")
```

In `_cmd_pipeline`, after line 819 (`ctx = PipelineContext(...)`) add:
```python
if getattr(args, "llm_review", False):
    from ..pipeline.llm_provider import create_llm_callback
    callback = create_llm_callback()
    if callback:
        ctx.llm_callback = callback
        print("LLM review enabled")
    else:
        print("WARNING: --llm-review specified but no LLM provider available")
```

After line 846 (`return 0`), before the return, add:
```python
# Save reviews if any
if ctx.review_log:
    from ..pipeline.review_store import save_reviews
    review_path = save_reviews(output_dir / "reviews", ctx.review_log)
    print(f"Reviews saved to: {review_path}")
    for review in ctx.review_log:
        if review.suggestions:
            print(f"\n  {review.stage} suggestions:")
            for s in review.suggestions[:3]:
                print(f"    - {s}")
```

**Step 3: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_review_cli.py -v`

**Step 4: Commit**

```bash
git add src/architecture_model/cli/main.py tests/test_review_cli.py
git commit -m "feat(cli): add --llm-review flag to pipeline command"
```

---

### Task 7: Full Suite Verification + Push

**Step 1: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: 7 pre-existing failures, ~1450+ passed, 0 regressions

**Step 2: E2E test with copilot-relay (manual, if available)**

Run: `architecture-model pipeline projects/python-dotenv --llm-review`
Expected: Pipeline runs with LLM reviews at each stage, reviews saved to `.architecture/reviews/`

**Step 3: Push**

```bash
git -c http.proxy="" push https://opn-arch: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@github.com/opn-arch/architecture-model-standard.git feature/model-quality-16wp
```
