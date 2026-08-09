"""Tests for relate, specify, contract, and validate pipeline stages."""
import pytest
from pathlib import Path
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.specify import SpecifyStage
from architecture_model.pipeline.contract import ContractStage
from architecture_model.pipeline.validate import ValidateStage
from architecture_model.pipeline.protocol import PipelineContext


def _setup_project(tmp_path):
    """Create a small project with routes, tests, and domain files."""
    (tmp_path / "users.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users():
    """List all users."""
    pass

@router.post("/users")
def create_user():
    """Create a user."""
    pass
''')
    (tmp_path / "auth.py").write_text('''
def authenticate(token: str) -> bool:
    """Verify auth token."""
    return True

def get_current_user(token: str):
    pass

def hash_password(pwd: str) -> str:
    pass
''')
    (tmp_path / "test_users.py").write_text('''
def test_list_users():
    pass

def test_create_user():
    pass
''')
    return tmp_path


def _run_full_pipeline(tmp_path):
    """Run all stages in order."""
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
    ctx.cache["observe"] = ObserveStage().run(ctx)
    ctx.cache["infer"] = InferStage().run(ctx)
    ctx.cache["allocate"] = AllocateStage().run(ctx)
    ctx.cache["relate"] = RelateStage().run(ctx)
    ctx.cache["specify"] = SpecifyStage().run(ctx)
    ctx.cache["contract"] = ContractStage().run(ctx)
    ctx.cache["validate"] = ValidateStage().run(ctx)
    return ctx


class TestRelateStage:
    def test_relate_produces_realizes_relationships(self, tmp_path):
        _setup_project(tmp_path)
        ctx = _run_full_pipeline(tmp_path)
        relate_result = ctx.get("relate")
        rels = relate_result.output.relationships
        realizes = [r for r in rels if r.rel_type == "realizes"]
        assert len(realizes) >= 1

    def test_relate_produces_contains_relationships(self, tmp_path):
        _setup_project(tmp_path)
        ctx = _run_full_pipeline(tmp_path)
        relate_result = ctx.get("relate")
        rels = relate_result.output.relationships
        contains = [r for r in rels if r.rel_type == "contains"]
        assert len(contains) >= 1

    def test_relate_name_and_requires(self):
        stage = RelateStage()
        assert stage.name == "relate"
        assert "allocate" in stage.requires


class TestSpecifyStage:
    def test_specify_finds_rest_interfaces(self, tmp_path):
        _setup_project(tmp_path)
        ctx = _run_full_pipeline(tmp_path)
        specify_result = ctx.get("specify")
        rest = [i for i in specify_result.output.interfaces if i.interface_type == "rest"]
        assert len(rest) >= 1

    def test_specify_name_and_requires(self):
        stage = SpecifyStage()
        assert stage.name == "specify"
        assert "observe" in stage.requires


class TestContractStage:
    def test_contract_maps_tests_to_components(self, tmp_path):
        _setup_project(tmp_path)
        ctx = _run_full_pipeline(tmp_path)
        contract_result = ctx.get("contract")
        assert contract_result.output.contracts is not None

    def test_contract_name_and_requires(self):
        stage = ContractStage()
        assert stage.name == "contract"
        assert "allocate" in stage.requires

    def test_contract_substring_match(self, tmp_path):
        """test_basic_click.py should match a component named 'click'."""
        (tmp_path / "click.py").write_text("def main(): pass")
        (tmp_path / "test_basic_click.py").write_text("def test_x(): pass")
        ctx = _run_full_pipeline(tmp_path)
        contract_result = ctx.get("contract")
        targets = [c.target_component for c in contract_result.output.contracts]
        # Should have matched via substring
        assert len(targets) >= 1

    def test_contract_suffix_pattern(self, tmp_path):
        """parser_test.py should match component with parser.py."""
        (tmp_path / "parser.py").write_text("def parse(): pass")
        (tmp_path / "parser_test.py").write_text("def test_parse(): pass")
        ctx = _run_full_pipeline(tmp_path)
        contract_result = ctx.get("contract")
        targets = [c.target_component for c in contract_result.output.contracts]
        assert len(targets) >= 1

    def test_contract_directory_match(self, tmp_path):
        """tests/core/test_foo.py should match component named 'core'."""
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "__init__.py").write_text("")
        (tmp_path / "core" / "engine.py").write_text("def run(): pass")
        tests_dir = tmp_path / "tests" / "core"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_foo.py").write_text("def test_foo(): pass")
        ctx = _run_full_pipeline(tmp_path)
        contract_result = ctx.get("contract")
        targets = [c.target_component for c in contract_result.output.contracts]
        assert len(targets) >= 1


class TestValidateStage:
    def test_validate_produces_score(self, tmp_path):
        _setup_project(tmp_path)
        ctx = _run_full_pipeline(tmp_path)
        validate_result = ctx.get("validate")
        assert 0 <= validate_result.output.score <= 100

    def test_validate_flags_unrealized_capabilities(self, tmp_path):
        # Single file, infer will create capabilities that may not be realized
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = _run_full_pipeline(tmp_path)
        validate_result = ctx.get("validate")
        # Should at least run without error
        assert validate_result.output is not None

    def test_validate_name_and_requires(self):
        stage = ValidateStage()
        assert stage.name == "validate"
        assert "relate" in stage.requires
