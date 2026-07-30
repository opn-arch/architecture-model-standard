"""Test that confidence is auto-computed on validate and load."""
import tempfile
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel, ModelMeta as Meta, Entities, Component, Status, FunctionSignature,
)
from architecture_model.core.validator import validate_model
from architecture_model.core.parser import load_model


def test_validate_sets_confidence():
    model = ArchitectureModel(
        meta=Meta(project="test", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="C1", name="A", status=Status.ACTIVE,
                      contract="Does X", pattern="adapter",
                      signatures=[FunctionSignature(name="run", params=["x"], returns="str")],
                      files=["a.py"]),
        ]),
        relationships=[],
    )
    assert model.entities.components[0].confidence == 0.0
    validate_model(model)
    assert model.entities.components[0].confidence > 0.5


def test_load_model_sets_confidence():
    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: A
      status: ACTIVE
      contract: Does X
      files: [a.py]
relationships: []
"""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(model_yaml)
        f.flush()
        model = load_model(Path(f.name))
    assert model.entities.components[0].confidence > 0.0
