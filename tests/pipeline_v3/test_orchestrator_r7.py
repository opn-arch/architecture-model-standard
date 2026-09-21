"""Orchestrator wiring for R7 attribute inference."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.pipeline_v3.orchestrator import run_pipeline


class _StubProvider:
    """Deterministic provider — returns 2 items per attribute."""

    name = "stub"

    def structured(self, prompt: str, schema: dict, *, model=None) -> dict:
        attr = next(iter(schema["properties"].keys()))
        return {attr: [f"stub {attr} A", f"stub {attr} B"]}

    def complete(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError

    def stream(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError

    def tokenize(self, text):  # pragma: no cover
        return len(text.split())


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    """One-module repo for a fast pipeline_v3 e2e."""
    src = tmp_path / "src" / "tiny"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "mod.py").write_text(
        '"""Tiny module for R7 orchestrator tests."""\n'
        "\n"
        "def do_thing():\n"
        '    """Do the thing."""\n'
        "    return 1\n"
    )
    return tmp_path


def test_run_pipeline_infer_attributes_off_matches_baseline(tiny_repo, tmp_path):
    """infer_attributes=False must be byte-identical to no-flag run."""
    out_a = tmp_path / "a.yaml"
    out_b = tmp_path / "b.yaml"
    run_pipeline(tiny_repo, out_path=out_a, project_name="p")
    run_pipeline(tiny_repo, out_path=out_b, project_name="p", infer_attributes=False)
    assert out_a.read_text() == out_b.read_text()


def test_run_pipeline_infer_attributes_on_adds_proposed_promises(tiny_repo, tmp_path):
    out_path = tmp_path / "with_r7.yaml"
    run_pipeline(
        tiny_repo,
        out_path=out_path,
        project_name="p",
        infer_attributes=True,
        attribute_provider=_StubProvider(),
    )
    doc = yaml.safe_load(out_path.read_text())
    entities = doc.get("entities", {})

    # At least one behavior should carry proposed promises now.
    behaviors = entities.get("behaviors", [])
    proposed_count = sum(
        1
        for b in behaviors
        for p in b.get("promises", [])
        if p.get("status") == "proposed"
    )
    assert proposed_count > 0, "R7 with provider must emit proposed promises"


def test_run_pipeline_infer_attributes_on_requires_provider(tiny_repo, tmp_path, monkeypatch):
    """Flag on + no provider + no OCA → RuntimeError with actionable message."""
    # Simulate opencode_arch not being installed
    import architecture_model.pipeline_v3.orchestrator as orch

    def _fail_load():
        raise RuntimeError(
            "run_pipeline(infer_attributes=True) requires either an "
            "explicit `attribute_provider=...` argument or the "
            "`opencode-arch` package. Install with "
            "`pip install opencode-arch` or pass a custom LLMProvider."
        )

    monkeypatch.setattr(orch, "_load_default_provider", _fail_load)

    with pytest.raises(RuntimeError, match=r"opencode-arch|attribute_provider"):
        run_pipeline(
            tiny_repo,
            out_path=tmp_path / "should_fail.yaml",
            project_name="p",
            infer_attributes=True,
            attribute_provider=None,
        )


def test_load_default_provider_raises_when_oca_missing(monkeypatch):
    """Directly test the loader's ImportError → RuntimeError translation."""
    import architecture_model.pipeline_v3.orchestrator as orch
    import sys

    # Hide opencode_arch temporarily so the import in _load_default_provider fails.
    monkeypatch.setitem(sys.modules, "opencode_arch.llm.providers.mcp", None)

    with pytest.raises(RuntimeError, match=r"opencode-arch"):
        orch._load_default_provider()
