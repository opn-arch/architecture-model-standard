"""Tests for formal layer entities in the architecture model."""
import yaml
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / ".architecture-model.yaml"

def _load_model():
    with open(MODEL_PATH) as f:
        return yaml.safe_load(f)

def test_five_layers_exist():
    model = _load_model()
    layers = model["entities"].get("layers", [])
    assert len(layers) == 5
    layer_ids = {l["id"] for l in layers}
    assert layer_ids == {"LAY-1", "LAY-2", "LAY-3", "LAY-4", "LAY-5"}

def test_layers_have_descriptions():
    model = _load_model()
    for layer in model["entities"]["layers"]:
        assert layer.get("description"), f"{layer['id']} missing description"

def test_layers_contain_components():
    model = _load_model()
    contains_rels = [(r["from_id"], r["to_id"]) for r in model["relationships"]
                     if r["type"] == "contains" and r["from_id"].startswith("LAY-")]
    assert len(contains_rels) >= 5, "Each layer should contain at least one component"

def test_layer_dependencies():
    model = _load_model()
    deps = {(r["from_id"], r["to_id"]) for r in model["relationships"]
            if r["type"] == "depends-on" and r["from_id"].startswith("LAY-")}
    assert ("LAY-4", "LAY-3") in deps
    assert ("LAY-3", "LAY-2") in deps
    assert ("LAY-2", "LAY-1") in deps
    assert ("LAY-5", "LAY-1") in deps
