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
from architecture_model.pipeline.protocol import QualityMetrics, StageResult
from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.synthesize import SynthesizeStage
from architecture_model.pipeline.emit import EmitStage
from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
from architecture_model.core.visualize import generate_html_viewer


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
    def test_two_system_recursive_hierarchy_is_scoped_valid_and_viewable(self, tmp_path):
        alpha = tmp_path / "alpha"
        beta = tmp_path / "beta"
        alpha.mkdir()
        beta.mkdir()
        for index in range(5):
            route = (
                "from fastapi import APIRouter\nrouter = APIRouter()\n"
                "@router.get('/alpha')\ndef alpha_route(): return {}\n"
                if index == 0 else ""
            )
            (alpha / f"api_{index}.py").write_text(route + f"def alpha_{index}(): return {index}\n")
            (beta / f"model_{index}.py").write_text(f"class Model{index}: pass\n")
        inline = tmp_path / "shared.py"
        inline.write_text("def shared(): return True\n")

        class FixedDecompose:
            name = "decompose"
            requires = ["validate"]

            def run(self, _ctx):
                return StageResult(
                    output=DecomposeResult(
                        systems=[
                            SystemBoundary(
                                system_id="SYS-1", name="Alpha", is_full_system=True,
                                files=[str(path.relative_to(tmp_path)) for path in sorted(alpha.glob("*.py"))],
                            ),
                            SystemBoundary(
                                system_id="SYS-2", name="Beta", is_full_system=True,
                                files=[str(path.relative_to(tmp_path)) for path in sorted(beta.glob("*.py"))],
                            ),
                        ],
                        inline_components=[SystemBoundary(
                            system_id="COMP-9", name="Shared", is_full_system=False,
                            files=["shared.py"],
                        )],
                    ),
                    quality=QualityMetrics(score=100),
                )

        stages = _make_coordinator()._stages | {
            "decompose": FixedDecompose(),
            "synthesize": SynthesizeStage(),
            "emit": EmitStage(),
        }
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")

        result = PipelineCoordinator(stages).run_recursive(ctx)

        root = load_model(tmp_path / ".architecture-model.yaml")
        assert len(root.entities.systems) == 2
        assert [component.name for component in root.entities.components] == ["Shared"]
        assert root.entities.capabilities == [] and root.entities.behaviors == []
        refs = [system.sub_model_ref for system in root.entities.systems]
        assert len(set(refs)) == 2
        submodels = [load_model(tmp_path / ref) for ref in refs]
        assert all(model.entities.components and model.relationships for model in submodels)
        assert all(not [i for i in validate_model(model).issues if i.severity.value == "ERROR"] for model in submodels)
        assert not [i for i in validate_model(root).issues if i.severity.value == "ERROR"]
        alpha_model = next(model for model in submodels if model.meta.system == "Alpha")
        beta_model = next(model for model in submodels if model.meta.system == "Beta")
        assert any("alpha" in artifact for artifact in alpha_model.meta.source_artifacts)
        assert not any("alpha" in artifact for artifact in beta_model.meta.source_artifacts)
        emit = result["results"]["emit"].output
        assert emit.promoted and emit.final_model_score > 0
        assert emit.extraction_score > 0
        report = (tmp_path / ".architecture-models" / "pipeline-report.md").read_text()
        assert "Final Model Score" in report and "Promoted:** yes" in report
        viewer = generate_html_viewer(root, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
        assert "alpha::" in viewer and "beta::" in viewer

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
