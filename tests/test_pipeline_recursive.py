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
from architecture_model.pipeline.protocol import Evidence, LLMCallRecord, PipelineContext
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
    def test_five_file_system_and_two_inline_components_preserve_scoped_architecture(self, tmp_path):
        subsystem = tmp_path / "engine"
        subsystem.mkdir()
        for index in range(5):
            (subsystem / f"worker_{index}.py").write_text(
                f'MIN_BATCH_{index} = {index + 5}\n\ndef process_{index}():\n    return MIN_BATCH_{index}\n'
            )
        (tmp_path / "inline_a.py").write_text(
            "from fastapi import APIRouter\nrouter = APIRouter()\n"
            "INLINE_A_LIMIT = 7\n"
            "@router.get('/inline-a')\ndef inline_a(): return INLINE_A_LIMIT\n"
        )
        (tmp_path / "inline_b.py").write_text(
            "from fastapi import APIRouter\nrouter = APIRouter()\n"
            "INLINE_B_LIMIT = 9\n"
            "@router.get('/inline-b')\ndef inline_b(): return INLINE_B_LIMIT\n"
        )

        class FixedDecompose:
            name = "decompose"
            requires = ["validate"]

            def run(self, _ctx):
                return StageResult(
                    output=DecomposeResult(
                        systems=[SystemBoundary(
                            system_id="SYS-engine", name="Engine", is_full_system=True,
                            files=[f"engine/worker_{index}.py" for index in range(5)],
                        )],
                        inline_components=[
                            SystemBoundary(
                                system_id="COMP-inline-a", name="Inline A",
                                files=["inline_a.py"], is_full_system=False,
                            ),
                            SystemBoundary(
                                system_id="COMP-inline-b", name="Inline B",
                                files=["inline_b.py"], is_full_system=False,
                            ),
                        ],
                    ),
                    quality=QualityMetrics(score=100),
                )

        stages = _make_coordinator()._stages | {
            "decompose": FixedDecompose(),
            "synthesize": SynthesizeStage(),
            "emit": EmitStage(),
        }
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
        resolutions = [
            ("engine", "Engine workflow", "engine/worker_0.py"),
            ("inline-a", "Inline A workflow", "inline_a.py"),
            ("inline-b", "Inline B workflow", "inline_b.py"),
        ]
        ctx.prior_corrections = [
            Evidence(
                source="llm_analysis", confidence=0.95,
                raw=f"validate {name} -> execute {name}", location="complex_behavior",
                metadata={
                    "resolution_id": f"res-{name}", "behavior_name": behavior_name,
                    "source_files": [source_file],
                    "steps": [f"validate {name}", f"execute {name}"],
                    "intent": f"Reliably execute {name}",
                },
            )
            for name, behavior_name, source_file in resolutions
        ]
        ctx.llm_calls = [
            LLMCallRecord(
                stage="infer", purpose=f"resolve {name}", resolution_id=f"res-{name}",
                files_sent=[source_file],
            )
            for name, _behavior_name, source_file in resolutions
        ]

        result = PipelineCoordinator(stages).run_recursive(ctx)

        emit = result["results"]["emit"].output
        errors = [
            issue for issue in emit.final_validation_issues
            if issue.get("severity", "").lower() == "error"
        ]
        assert (tmp_path / ".architecture-model.yaml").exists(), "\n".join(
            f"{issue['code']}: {issue['message']}" for issue in errors
        )
        root = load_model(tmp_path / ".architecture-model.yaml")
        subsystem_model = load_model(tmp_path / root.entities.systems[0].sub_model_ref)
        root_behavior_names = {behavior.name for behavior in root.entities.behaviors}
        subsystem_behavior_names = {behavior.name for behavior in subsystem_model.entities.behaviors}
        assert "Engine workflow" in subsystem_behavior_names
        assert "Engine workflow" not in root_behavior_names
        assert {"Inline A workflow", "Inline B workflow"} <= root_behavior_names
        assert not ({"Inline A workflow", "Inline B workflow"} & subsystem_behavior_names)
        assert len(root.entities.systems) == 1
        assert len(root.entities.components) == 2
        assert all(component.intent and component.goals for component in root.entities.components), [
            (component.name, component.intent, component.goals) for component in root.entities.components
        ] + [
            (capability.name, capability.intent, capability.goals)
            for capability in root.entities.capabilities
        ]
        assert all(component.requirements for component in root.entities.components)
        assert all(component.interface_refs for component in root.entities.components)
        assert all(behavior.steps and behavior.structured_steps for behavior in root.entities.behaviors)
        assert all(step.component_ref for behavior in root.entities.behaviors for step in behavior.structured_steps)
        assert all(requirement.rationale and requirement.moes and requirement.value_function for requirement in root.entities.requirements)
        for model in (root, subsystem_model):
            assert len(model.all_entity_ids) == sum(
                len(group) for group in (
                    model.entities.systems, model.entities.components,
                    model.entities.capabilities, model.entities.behaviors,
                    model.entities.interfaces, model.entities.requirements,
                    model.entities.constraints, model.entities.actors, model.entities.layers,
                )
            )
            assert not [issue for issue in validate_model(model).issues if issue.severity.value == "ERROR"]
            assert all(
                rel.from_id in model.all_entity_ids and rel.to_id in model.all_entity_ids
                for rel in model.relationships
            )
        assert emit.promoted and emit.final_model_score > 0
        viewer = generate_html_viewer(
            root, tmp_path / "viewer.html", repo_path=tmp_path
        ).read_text()
        assert "engine::" in viewer
        assert "Inline A workflow" in viewer and "Inline B workflow" in viewer
        assert all(entity_id in viewer for entity_id in root.all_entity_ids)

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
        assert len(root.entities.components) == 1
        assert root.entities.components[0].files == ["shared.py"]
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
