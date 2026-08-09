"""Tests for the artifact writer."""
import json
import pytest
from pathlib import Path
from architecture_model.pipeline.artifacts import write_artifacts
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.specify import SpecifyStage
from architecture_model.pipeline.contract import ContractStage
from architecture_model.pipeline.validate import ValidateStage
from architecture_model.pipeline.protocol import PipelineContext


def _run_full(tmp_path):
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
    ctx.cache["observe"] = ObserveStage().run(ctx)
    ctx.cache["infer"] = InferStage().run(ctx)
    ctx.cache["allocate"] = AllocateStage().run(ctx)
    ctx.cache["relate"] = RelateStage().run(ctx)
    ctx.cache["specify"] = SpecifyStage().run(ctx)
    ctx.cache["contract"] = ContractStage().run(ctx)
    ctx.cache["validate"] = ValidateStage().run(ctx)
    return ctx


class TestArtifactWriter:
    def test_write_creates_directory(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = _run_full(tmp_path)
        out = write_artifacts(ctx)
        assert out.exists()
        assert (out / "inventory.json").exists()

    def test_write_inventory_json(self, tmp_path):
        (tmp_path / "app.py").write_text('API = "1.0"\ndef hello(): pass')
        ctx = _run_full(tmp_path)
        write_artifacts(ctx)
        data = json.loads((tmp_path / ".architecture" / "inventory.json").read_text())
        assert "modules" in data
        assert "metrics" in data

    def test_write_functional_yaml(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()
@router.get("/items")
def list_items(): pass
''')
        ctx = _run_full(tmp_path)
        write_artifacts(ctx)
        func_path = tmp_path / ".architecture" / "functional.yaml"
        assert func_path.exists()
        content = func_path.read_text()
        assert "capabilities" in content

    def test_write_validation_json(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        ctx = _run_full(tmp_path)
        write_artifacts(ctx)
        data = json.loads((tmp_path / ".architecture" / "validation.json").read_text())
        assert "score" in data
        assert "is_valid" in data

    def test_write_structure_yaml(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        ctx = _run_full(tmp_path)
        write_artifacts(ctx)
        struct_path = tmp_path / ".architecture" / "structure.yaml"
        assert struct_path.exists()
        content = struct_path.read_text()
        assert "components" in content

    def test_write_relationships_yaml(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()
@router.get("/users")
def list_users(): pass
@router.post("/users")
def create_user(): pass
''')
        ctx = _run_full(tmp_path)
        write_artifacts(ctx)
        rel_path = tmp_path / ".architecture" / "relationships.yaml"
        assert rel_path.exists()
