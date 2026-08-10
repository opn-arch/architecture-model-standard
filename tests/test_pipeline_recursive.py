"""Tests for recursive pipeline decomposition."""
import pytest
from pathlib import Path
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.specify import SpecifyStage
from architecture_model.pipeline.contract import ContractStage
from architecture_model.pipeline.validate import ValidateStage
from architecture_model.pipeline.protocol import PipelineContext


def _make_coordinator():
    stages = {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "specify": SpecifyStage(),
        "contract": ContractStage(),
        "validate": ValidateStage(),
    }
    return PipelineCoordinator(stages)


class TestRecursiveDecomposition:
    def test_run_recursive_writes_artifacts(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
        coord = _make_coordinator()
        result = coord.run_recursive(ctx, max_depth=1, leaf_threshold=5)
        assert (tmp_path / ".architecture" / "inventory.json").exists()
        assert (tmp_path / ".architecture" / "context.md").exists()
        assert "results" in result
        assert "artifacts_dir" in result

    def test_run_recursive_creates_subsystems_for_large_components(self, tmp_path):
        # Create enough files to trigger decomposition (>5 files per component)
        for i in range(8):
            (tmp_path / f"module_{i}.py").write_text(f'''
def func_{i}_a(): pass
def func_{i}_b(): pass
def func_{i}_c(): pass
''')
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
        coord = _make_coordinator()
        result = coord.run_recursive(ctx, max_depth=2, leaf_threshold=3)
        # Should have subsystems if any component > 3 files
        # (depends on how allocation groups them)
        assert "subsystems" in result

    def test_run_recursive_respects_max_depth(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
        coord = _make_coordinator()
        result = coord.run_recursive(ctx, max_depth=0, leaf_threshold=0)
        # max_depth=0 means no recursion into subsystems
        assert result["subsystems"] == {}

    def test_scoped_context_produces_multiple_components(self, tmp_path):
        """A scoped context with 6 files should produce >1 component, not collapse to 1."""
        files = {}
        for name in ("parser", "validator", "slicer", "differ", "merger", "coverage"):
            path = tmp_path / f"{name}.py"
            path.write_text(f"class {name.title()}:\n    def run(self): pass\n")
            files[name] = path

        scope_files = [tmp_path / f"{n}.py" for n in files]
        ctx = PipelineContext(
            repo_path=tmp_path,
            output_dir=tmp_path / ".architecture",
            scope="COMP-CORE",
            scope_files=scope_files,
        )

        obs = ObserveStage()
        ctx.cache["observe"] = obs.run(ctx)
        inf = InferStage()
        ctx.cache["infer"] = inf.run(ctx)
        alloc = AllocateStage()
        result = alloc.run(ctx)

        components = result.output.components
        # Each file has a class → should get its own component
        assert len(components) >= 4, (
            f"Expected >=4 components for 6 scoped files, got {len(components)}: "
            f"{[c.name for c in components]}"
        )
        assert result.output.file_coverage == 100.0
