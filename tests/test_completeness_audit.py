"""Completeness audit — verify every operational pipeline is fully modeled."""

from pathlib import Path
import pytest

from architecture_model.core.parser import load_model


MODEL_PATH = Path(__file__).resolve().parents[1] / ".architecture-model.yaml"

PIPELINES = {
    "BEH-P1":  "EXTRACT",
    "BEH-26":  "SLICE",
    "BEH-27":  "SELF-IMPROVEMENT",
    "BEH-28":  "DEV-LOOP",
    "BEH-LLM": "LLM-PROVIDER",
    "BEH-SIL": "SI&L LOGGING",
    "BEH-FBK": "FEEDBACK JOURNALS",
}


@pytest.fixture(scope="module")
def model():
    return load_model(MODEL_PATH)


@pytest.mark.parametrize("anchor,label", list(PIPELINES.items()))
def test_pipeline_has_subbehaviors(model, anchor, label):
    subs = [b for b in model.entities.behaviors
            if b.id == anchor or b.id.startswith(anchor + ".")]
    assert len(subs) >= 1, f"{label} ({anchor}) has no behaviors"


@pytest.mark.parametrize("anchor,label", list(PIPELINES.items()))
def test_pipeline_all_have_descriptions(model, anchor, label):
    subs = [b for b in model.entities.behaviors
            if b.id == anchor or b.id.startswith(anchor + ".")]
    missing = [b.id for b in subs if not (b.description or "").strip()]
    assert not missing, f"{label} sub-behaviors missing description: {missing}"


def _rels_by_type(model, t):
    def gf(r): return getattr(r, "from_id", None) or getattr(r, "from_", None)
    def gt(r): return getattr(r, "to_id", None) or getattr(r, "to_", None)
    def rt(r):
        v = getattr(r, "type", None) or getattr(r, "relation_type", None)
        return v.value if hasattr(v, "value") else str(v)
    return [(gf(r), gt(r)) for r in model.relationships if rt(r) == t]


@pytest.mark.parametrize("anchor,label", list(PIPELINES.items()))
def test_pipeline_root_has_traces_to_component(model, anchor, label):
    traces = _rels_by_type(model, "traces-to")
    trace_targets = {t for _, t in traces}
    assert anchor in trace_targets, f"{label} root {anchor} not traced to any component"


@pytest.mark.parametrize("anchor,label", list(PIPELINES.items()))
def test_pipeline_stages_are_triggered(model, anchor, label):
    subs = [b for b in model.entities.behaviors
            if b.id.startswith(anchor + ".")]
    if not subs:
        pytest.skip(f"{label} has no sub-behaviors")
    triggers = _rels_by_type(model, "triggers")
    trig_from = {a for a, _ in triggers}
    trig_to = {b for _, b in triggers}
    # Every sub except leaves-with-terminal must appear as trigger source OR target
    isolated = [b.id for b in subs
                if b.id not in trig_from and b.id not in trig_to]
    assert not isolated, f"{label} has isolated sub-behaviors (no triggers in or out): {isolated}"
