"""Test that slicer loads sub-models when available."""
import pytest
from pathlib import Path
from architecture_model.core.slicer import slice_by_fblock
from architecture_model.core.parser import load_model
from architecture_model.core.types import ArchitectureModel, Component, Entities, ModelMeta


class TestSlicerSubModels:
    def test_loads_sub_model_when_project_root_provided(self, tmp_path):
        """When sub-model exists, return it instead of filtering root."""
        (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Stub contract
    - id: COMP-2
      name: Monitor
      status: ACTIVE
      f_block: F2
relationships: []
""")
        sub_dir = tmp_path / ".architecture-models" / "F1"
        sub_dir.mkdir(parents=True)
        (sub_dir / ".architecture-model.yaml").write_text("""
meta:
  project: test/F1
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Rich detail from sub-model
      pattern: service-layer
relationships: []
""")
        root = load_model(str(tmp_path / ".architecture-model.yaml"))
        sliced = slice_by_fblock(root, "F1", project_root=tmp_path)

        comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
        assert len(comps) == 1
        assert comps[0].contract == "Rich detail from sub-model"
        assert comps[0].pattern == "service-layer"

    def test_falls_back_when_no_sub_model(self, tmp_path):
        (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
relationships: []
""")
        root = load_model(str(tmp_path / ".architecture-model.yaml"))
        sliced = slice_by_fblock(root, "F1", project_root=tmp_path)

        comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
        assert len(comps) == 1
        assert comps[0].name == "Scheduler"

    def test_works_without_project_root(self):
        """Existing API still works."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(components=[
                Component(id="C1", name="A", f_block="F1", status="ACTIVE"),
                Component(id="C2", name="B", f_block="F2", status="ACTIVE"),
            ]),
            relationships=[],
        )
        sliced = slice_by_fblock(model, "F1")
        comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
        assert len(comps) == 1
        assert comps[0].name == "A"
