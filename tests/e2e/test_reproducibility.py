"""E2E: pipeline reproducibility with a deterministic stub LLMProvider.

Task B1.2.8 — SI&L + Provider plan.

Runs the extraction pipeline twice against an identical fixture repo using a
deterministic stub `LLMProvider` (canned response keyed by SHA-256(prompt)),
and asserts that the emitted `.architecture-model.yaml` bytes are identical
across runs.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from architecture_model.llm.provider import Completion, LLMProvider
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.contract import ContractStage
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.decompose import DecomposeStage
from architecture_model.pipeline.emit import EmitStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import PipelineContext
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.specify import SpecifyStage
from architecture_model.pipeline.synthesize import SynthesizeStage
from architecture_model.pipeline.validate import ValidateStage


class DeterministicStubProvider:
    """LLMProvider that returns canned responses keyed by SHA-256(prompt).

    Identical prompts → identical replies. Unknown prompts → a stable
    generic reply so the pipeline still exercises the provider path without
    injecting entropy.
    """

    name: str = "deterministic-stub"
    default_model: str = "stub-v0"

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def _reply(self, prompt: str) -> str:
        key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if key not in self._cache:
            # Fixed short reply — pipeline treats LLM output as a suggestion,
            # so any stable string is fine. Prefix with 8 hex chars for debuggability.
            self._cache[key] = f"stub:{key[:8]}"
        return self._cache[key]

    def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> Completion:
        text = self._reply(prompt)
        return Completion(
            text=text,
            tokens_prompt=len(prompt) // 4,
            tokens_completion=len(text) // 4,
            model=model or self.default_model,
            finish_reason="stop",
        )

    def stream(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
        yield self._reply(prompt)

    def structured(self, prompt, schema, *, model=None):
        return {"text": self._reply(prompt)}

    def tokenize(self, text: str) -> int:
        return max(1, len(text) // 4)


# Sanity: our stub must satisfy the runtime-checkable protocol.
assert isinstance(DeterministicStubProvider(), LLMProvider)


def _write_fixture(root: Path) -> None:
    """Write a tiny 1-module Python fixture that the pipeline can consume."""
    pkg = root / "src" / "widget"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text(
        '"""Widget core."""\n'
        "from __future__ import annotations\n\n"
        "class Widget:\n"
        '    """A tiny widget."""\n\n'
        "    def __init__(self, name: str) -> None:\n"
        "        self.name = name\n\n"
        "    def greet(self) -> str:\n"
        '        return f"hello {self.name}"\n'
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "widget"\nversion = "0.0.1"\n'
    )


def _make_ctx(repo: Path) -> PipelineContext:
    output_dir = repo / ".architecture"
    output_dir.mkdir(parents=True, exist_ok=True)
    return PipelineContext(
        repo_path=repo,
        output_dir=output_dir,
        llm_provider=DeterministicStubProvider(),
    )


def _stages() -> dict:
    return {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "specify": SpecifyStage(),
        "contract": ContractStage(),
        "validate": ValidateStage(),
        "decompose": DecomposeStage(),
        "synthesize": SynthesizeStage(),
        "emit": EmitStage(),
    }


def _run_pipeline(repo: Path) -> bytes:
    ctx = _make_ctx(repo)
    coord = PipelineCoordinator(_stages())
    coord.run_all(ctx)
    model_path = repo / ".architecture-model.yaml"
    assert model_path.exists(), (
        f".architecture-model.yaml was not emitted at {model_path}"
    )
    return model_path.read_bytes()


@pytest.fixture(autouse=True)
def _pin_clock(monkeypatch):
    """Pin the deterministic clock env var so meta.generated_at is stable."""
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-01-01T00:00:00+00:00")
    yield


def test_pipeline_reproducible_with_pinned_provider(tmp_path):
    """Run the pipeline twice on the fixture with a deterministic stub provider;
    assert byte-identical .architecture-model.yaml."""
    repo = tmp_path / "widget-repo"
    repo.mkdir()
    _write_fixture(repo)

    first = _run_pipeline(repo)
    second = _run_pipeline(repo)

    assert first == second, (
        "Emitted .architecture-model.yaml differs between runs. First 400 bytes:\n"
        f"--- run 1 ---\n{first[:400]!r}\n--- run 2 ---\n{second[:400]!r}"
    )


def test_stub_provider_is_stable():
    """The stub must return identical replies for identical prompts."""
    p = DeterministicStubProvider()
    a = p.complete("hello world")
    b = p.complete("hello world")
    assert a["text"] == b["text"]
    assert a["model"] == b["model"]
