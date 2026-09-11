"""Tests for formal layer entities in the architecture model."""
import yaml
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / ".architecture-model.yaml"

def _load_model():
    with open(MODEL_PATH) as f:
        return yaml.safe_load(f)

def _rel_pair(r):
    """Normalize relationship endpoints (schema accepts from/to or from_id/to_id)."""
    return (r.get("from_id") or r.get("from"), r.get("to_id") or r.get("to"))

def test_seven_layers_exist():
    model = _load_model()
    layers = model["entities"].get("layers", [])
    assert len(layers) == 7
    layer_ids = {l["id"] for l in layers}
    assert layer_ids == {"LAY-1", "LAY-2", "LAY-3", "LAY-4", "LAY-5", "LAY-6", "LAY-7"}

def test_layers_have_descriptions():
    model = _load_model()
    for layer in model["entities"]["layers"]:
        assert layer.get("description"), f"{layer['id']} missing description"

def test_layers_contain_components():
    model = _load_model()
    contains_rels = [_rel_pair(r) for r in model["relationships"]
                     if r.get("type") == "contains"
                     and (_rel_pair(r)[0] or "").startswith("LAY-")]
    assert len(contains_rels) >= 5, "Each layer should contain at least one component"

def test_layer_dependencies():
    model = _load_model()
    deps = {_rel_pair(r) for r in model["relationships"]
            if r.get("type") == "depends-on"
            and (_rel_pair(r)[0] or "").startswith("LAY-")}
    assert ("LAY-4", "LAY-3") in deps
    assert ("LAY-3", "LAY-2") in deps
    assert ("LAY-2", "LAY-1") in deps
    assert ("LAY-5", "LAY-1") in deps
