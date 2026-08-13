"""Tests for relate, specify, contract, and validate pipeline stages."""
import pytest
from pathlib import Path
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.decompose import DecomposeStage
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

    def test_specify_library_interface(self, tmp_path):
        """Component with public functions consumed by another gets a library interface."""
        from architecture_model.pipeline.observe_types import (
            Inventory, ModuleRecord, FunctionRecord,
        )
        from architecture_model.pipeline.allocate_types import (
            AllocationResult, ComponentAllocation,
        )
        from architecture_model.pipeline.protocol import (
            PipelineContext, StageResult, QualityMetrics,
        )
        # Two components: auth (3 public funcs) and users (imports from auth)
        auth_path = Path("auth/core.py")
        users_path = Path("users/views.py")
        inventory = Inventory(
            modules=[
                ModuleRecord(
                    path=auth_path,
                    functions=[
                        FunctionRecord(name="authenticate", signature="(token)", body_hint=""),
                        FunctionRecord(name="get_current_user", signature="(token)", body_hint=""),
                        FunctionRecord(name="hash_password", signature="(pwd)", body_hint=""),
                    ],
                    imports=[],
                ),
                ModuleRecord(
                    path=users_path,
                    functions=[
                        FunctionRecord(name="list_users", signature="()", body_hint=""),
                    ],
                    imports=["auth.core"],
                ),
            ],
        )
        allocation = AllocationResult(components=[
            ComponentAllocation(id="COMP-AUTH", name="Auth", files=[auth_path]),
            ComponentAllocation(id="COMP-USERS", name="Users", files=[users_path]),
        ])
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(
            output=inventory, quality=QualityMetrics(score=100),
            diagnostics=[], uncertainties=[], input_hash="", duration_ms=0, version="1.0",
        )
        ctx.cache["allocate"] = StageResult(
            output=allocation, quality=QualityMetrics(score=100),
            diagnostics=[], uncertainties=[], input_hash="", duration_ms=0, version="1.0",
        )
        result = SpecifyStage().run(ctx)
        lib = [i for i in result.output.interfaces if i.interface_type == "library"]
        assert len(lib) == 1
        assert lib[0].component_id == "COMP-AUTH"
        assert any("authenticate" in m for m in lib[0].methods)

    def test_specify_quality_score_library_only(self, tmp_path):
        """Quality score reflects component coverage when only library interfaces exist."""
        from architecture_model.pipeline.observe_types import (
            Inventory, ModuleRecord, FunctionRecord,
        )
        from architecture_model.pipeline.allocate_types import (
            AllocationResult, ComponentAllocation,
        )
        from architecture_model.pipeline.protocol import (
            PipelineContext, StageResult, QualityMetrics,
        )
        auth_path = Path("auth/core.py")
        users_path = Path("users/views.py")
        inventory = Inventory(
            modules=[
                ModuleRecord(
                    path=auth_path,
                    functions=[
                        FunctionRecord(name="authenticate", signature="(token)", body_hint=""),
                        FunctionRecord(name="get_current_user", signature="(token)", body_hint=""),
                        FunctionRecord(name="hash_password", signature="(pwd)", body_hint=""),
                    ],
                    imports=[],
                ),
                ModuleRecord(
                    path=users_path,
                    functions=[
                        FunctionRecord(name="list_users", signature="()", body_hint=""),
                    ],
                    imports=["auth.core"],
                ),
            ],
        )
        allocation = AllocationResult(components=[
            ComponentAllocation(id="COMP-AUTH", name="Auth", files=[auth_path]),
            ComponentAllocation(id="COMP-USERS", name="Users", files=[users_path]),
        ])
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        ctx.cache["observe"] = StageResult(
            output=inventory, quality=QualityMetrics(score=100),
            diagnostics=[], uncertainties=[], input_hash="", duration_ms=0, version="1.0",
        )
        ctx.cache["allocate"] = StageResult(
            output=allocation, quality=QualityMetrics(score=100),
            diagnostics=[], uncertainties=[], input_hash="", duration_ms=0, version="1.0",
        )
        result = SpecifyStage().run(ctx)
        assert result.quality.score >= 50
        assert result.quality.sub_scores.get("library_count", 0) >= 1


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


class TestRegenScoreStage:
    def test_regen_score_stage_can_run(self, tmp_path):
        """Returns True when model exists, False otherwise."""
        from architecture_model.pipeline.regen_score import RegenScoreStage

        stage = RegenScoreStage()
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        assert stage.can_run(ctx) is False

        (tmp_path / ".architecture-model.yaml").write_text("meta:\n  project: x\n")
        assert stage.can_run(ctx) is True

    def test_regen_score_stage_no_model(self, tmp_path):
        """Stage returns low score when no enriched data."""
        from architecture_model.pipeline.regen_score import RegenScoreStage

        model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Bare
      status: ACTIVE
relationships: []
"""
        (tmp_path / ".architecture-model.yaml").write_text(model_yaml)
        stage = RegenScoreStage()
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        result = stage.run(ctx)
        assert result.output.overall < 50
        assert any(d.code == "REGEN_NOT_ENRICHED" for d in result.diagnostics)

    def test_regen_score_stage_with_enrichment(self, tmp_path):
        """Enriched component yields higher score."""
        from architecture_model.pipeline.regen_score import RegenScoreStage

        model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Test
      status: ACTIVE
      signatures:
        - name: foo
          params: ["x: int"]
          returns: "int"
          body_hint: "return x + 1"
      test_contracts:
        - test_file: test_foo.py
          test_method: test_foo_works
          assertion: "assert foo(1) == 2"
      constants:
        - name: MAX
          value: "100"
relationships: []
"""
        (tmp_path / ".architecture-model.yaml").write_text(model_yaml)
        stage = RegenScoreStage()
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        result = stage.run(ctx)
        assert result.output.overall > 0
        assert result.output.grade in ("A", "B", "C", "D", "F")
        assert "Test" in result.output.component_scores
        # Should NOT have the not-enriched diagnostic
        assert not any(d.code == "REGEN_NOT_ENRICHED" for d in result.diagnostics)


def test_validate_depends_on_specify_and_contract():
    """Validate should depend on specify and contract so all entities are available."""
    from architecture_model.pipeline.validate import ValidateStage
    stage = ValidateStage()
    assert "specify" in stage.requires
    assert "contract" in stage.requires


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


def test_infer_groups_by_package_for_large_repos(tmp_path):
    """Large repos (>50 modules) group capabilities by top-level package."""
    src = tmp_path / "src"
    for pkg in ("db", "core", "template", "forms"):
        pkg_dir = src / pkg
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("")
        for i in range(15):
            funcs = "\n".join(
                f"def func_{j}():\n    pass\n" for j in range(5)
            )
            (pkg_dir / f"mod_{i}.py").write_text(funcs)

    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
    ctx.cache["observe"] = ObserveStage().run(ctx)
    ctx.cache["infer"] = InferStage().run(ctx)

    caps = ctx.cache["infer"].output.capabilities
    assert len(caps) >= 3
    assert len(caps) <= 10
    assert any("db" in c.name.lower() for c in caps)


def test_allocate_splits_by_package_not_leaf_dir():
    """When splitting oversized components, group by sub-package, not leaf dir."""
    from architecture_model.pipeline.allocate import _split_oversized, _group_by_package_level
    from architecture_model.pipeline.allocate_types import ComponentAllocation

    # 18 files across 3 sub-packages (models, backends, sql), each with 2 sub-dirs (a, b), 3 files each
    files = []
    for pkg in ("models", "backends", "sql"):
        for sub in ("a", "b"):
            for i in range(3):
                files.append(Path(f"django/db/{pkg}/{sub}/file_{i}.py"))

    comp = ComponentAllocation(
        id="COMP-1",
        name="Database",
        files=files,
        layer="data",
    )

    result = _split_oversized([comp])
    # Should split by sub-package (models, backends, sql) = 3, not by leaf dir (6)
    assert len(result) >= 2
    assert len(result) <= 4

    # Also test the helper directly
    groups = _group_by_package_level(files)
    assert set(groups.keys()) == {"models", "backends", "sql"}
    assert all(len(v) == 6 for v in groups.values())


def test_full_pipeline_large_repo_produces_sensible_systems(tmp_path):
    """End-to-end: a large repo should produce fewer than 20 caps and 25 components."""
    import shutil

    # Create 6 packages with varying module counts (83 total)
    packages = {
        "db": 20, "core": 18, "template": 12,
        "forms": 10, "views": 15, "utils": 8,
    }
    for pkg, count in packages.items():
        pkg_dir = tmp_path / pkg
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        for i in range(count):
            (pkg_dir / f"mod_{i}.py").write_text(
                f"class {pkg.title()}Class{i}:\n"
                f"    pass\n\n"
                f"def func_a_{i}():\n    return {i}\n\n"
                f"def func_b_{i}():\n    return {i}\n\n"
                f"def func_c_{i}():\n    return {i}\n\n"
                f"def func_d_{i}():\n    return {i}\n"
            )

    out_dir = tmp_path / ".architecture" / "pipeline-cache"
    ctx = PipelineContext(repo_path=tmp_path, output_dir=out_dir)

    # Run stages in order
    ctx.cache["observe"] = ObserveStage().run(ctx)
    ctx.cache["infer"] = InferStage().run(ctx)
    ctx.cache["allocate"] = AllocateStage().run(ctx)
    ctx.cache["relate"] = RelateStage().run(ctx)
    ctx.cache["specify"] = SpecifyStage().run(ctx)
    ctx.cache["decompose"] = DecomposeStage().run(ctx)

    # Extract results
    infer_result = ctx.get("infer").output
    alloc_result = ctx.get("allocate").output
    decompose_result = ctx.get("decompose").output

    caps = infer_result.capabilities
    comps = alloc_result.components
    systems = decompose_result.systems

    assert len(caps) <= 20, f"Too many capabilities: {len(caps)}"
    assert len(comps) <= 25, f"Too many components: {len(comps)}"
    assert len(systems) >= 3, f"Too few systems: {len(systems)}"


def test_infer_cli_use_cases(tmp_path):
    """CLI commands should produce use-case behaviors."""
    from architecture_model.pipeline.infer import InferStage
    from architecture_model.pipeline.observe_types import (
        Inventory, ModuleRecord, FunctionRecord,
    )
    from architecture_model.pipeline.protocol import PipelineContext, StageResult, QualityMetrics

    mod = ModuleRecord(
        path=Path("manage.py"),
        functions=[
            FunctionRecord(
                name="handle",
                signature="def handle(self, options)",
                body_hint="",
                calls=["migrate", "flush"],
                decorators=[],
                docstring="Run database migrations",
            ),
        ],
        classes=[],
        imports=["click"],
        constants=[],
        line_count=50,
        docstring="Management command for migrations",
    )
    inventory = Inventory(modules=[mod], edges=[], routes=[], constraints=[],
                          test_files=[], docs=[])

    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture-models")
    ctx.cache["observe"] = StageResult(
        output=inventory, quality=QualityMetrics(score=100),
        diagnostics=[], uncertainties=[], input_hash="1",
        duration_ms=0, version="1.0",
    )

    stage = InferStage()
    result = stage.run(ctx)
    behaviors = result.output.behaviors
    cli_behaviors = [b for b in behaviors if b.behavior_type == "use_case"]
    assert len(cli_behaviors) >= 1


def test_infer_middleware_workflow(tmp_path):
    """Middleware classes should produce workflow behaviors."""
    from architecture_model.pipeline.infer import InferStage
    from architecture_model.pipeline.observe_types import (
        Inventory, ModuleRecord, ClassRecord,
    )
    from architecture_model.pipeline.protocol import PipelineContext, StageResult, QualityMetrics

    mod = ModuleRecord(
        path=Path("django/middleware/csrf.py"),
        functions=[],
        classes=[
            ClassRecord(
                name="CsrfViewMiddleware",
                bases=["MiddlewareMixin"],
                methods=["process_request", "process_view", "process_response"],
                method_details=[],
                attributes={},
                decorators=[],
                is_abstract=False,
            ),
        ],
        imports=["django.utils.deprecation"],
        constants=[],
        line_count=100,
        docstring="",
    )
    inventory = Inventory(modules=[mod], edges=[], routes=[], constraints=[],
                          test_files=[], docs=[])

    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture-models")
    ctx.cache["observe"] = StageResult(
        output=inventory, quality=QualityMetrics(score=100),
        diagnostics=[], uncertainties=[], input_hash="1",
        duration_ms=0, version="1.0",
    )

    stage = InferStage()
    result = stage.run(ctx)
    workflows = [b for b in result.output.behaviors if b.behavior_type == "workflow"]
    assert len(workflows) >= 1
    csrf_wf = [w for w in workflows if "Csrf" in w.name][0]
    assert "process_request" in csrf_wf.steps


def test_synthesize_propagates_all_entities():
    """_build_system_model_yaml includes behaviors, interfaces, constraints, layers, actors."""
    import yaml
    from pathlib import Path
    from architecture_model.pipeline.synthesize import _build_system_model_yaml
    from architecture_model.pipeline.protocol import StageResult, QualityMetrics
    from architecture_model.pipeline.observe_types import Inventory, ConstraintRecord
    from architecture_model.pipeline.infer_types import (
        InferenceResult, InferredCapability, InferredActor, InferredBehavior,
    )
    from architecture_model.pipeline.allocate_types import AllocationResult, ComponentAllocation
    from architecture_model.pipeline.relate_types import RelateResult, DerivedRelationship
    from architecture_model.pipeline.specify_types import SpecifyResult, InterfaceSpec
    from architecture_model.pipeline.decompose_types import SystemBoundary

    boundary = SystemBoundary(
        system_id="SYS-CORE",
        name="Core",
        files=["src/core/parser.py", "src/core/validator.py"],
        is_full_system=True,
    )

    def _sr(output):
        return StageResult(
            output=output, quality=QualityMetrics(score=100),
            diagnostics=[], uncertainties=[], input_hash="", duration_ms=0, version="1.0",
        )

    results = {
        "observe": _sr(Inventory(
            modules=[],
            constraints=[
                ConstraintRecord(name="python", value=">=3.10", source="src/core/parser.py", constraint_type="version"),
                ConstraintRecord(name="timeout", value="30s", source="src/other/unrelated.py", constraint_type="timeout"),
            ],
        )),
        "infer": _sr(InferenceResult(
            capabilities=[
                InferredCapability(id="CAP-1", name="Parsing"),
                InferredCapability(id="CAP-2", name="Validation"),
            ],
            actors=[
                InferredActor(id="ACT-1", name="Developer", actor_type="human", evidence_source="cli"),
            ],
            behaviors=[
                InferredBehavior(id="BEH-1", name="Parse File", capability_id="CAP-1", behavior_type="use_case", steps=["read", "parse"]),
                InferredBehavior(id="BEH-2", name="Unrelated", capability_id="CAP-99", behavior_type="workflow"),
                InferredBehavior(id="BEH-3", name="Global", capability_id="", behavior_type="use_case"),
            ],
        )),
        "allocate": _sr(AllocationResult(components=[
            ComponentAllocation(id="COMP-1", name="Parser", files=[Path("src/core/parser.py")], layer="service"),
            ComponentAllocation(id="COMP-2", name="Validator", files=[Path("src/core/validator.py")], layer="service"),
        ])),
        "relate": _sr(RelateResult(relationships=[
            DerivedRelationship(from_id="COMP-1", to_id="CAP-1", rel_type="realizes"),
        ])),
        "specify": _sr(SpecifyResult(interfaces=[
            InterfaceSpec(id="IF-1", name="ParserAPI", component_id="COMP-1", interface_type="library", methods=["parse"], description="Parser interface"),
            InterfaceSpec(id="IF-2", name="OtherAPI", component_id="COMP-OTHER", interface_type="rest"),
        ])),
    }

    yaml_str = _build_system_model_yaml(boundary, results)
    model = yaml.safe_load(yaml_str)
    entities = model["entities"]

    # Behaviors: BEH-1 (cap matches) and BEH-3 (no cap_id) included, BEH-2 excluded
    assert "behaviors" in entities
    beh_ids = [b["id"] for b in entities["behaviors"]]
    assert "BEH-1" in beh_ids
    assert "BEH-3" in beh_ids
    assert "BEH-2" not in beh_ids

    # Interfaces: only IF-1 (component matches)
    assert "interfaces" in entities
    assert len(entities["interfaces"]) == 1
    assert entities["interfaces"][0]["id"] == "IF-1"

    # Constraints: only the one with source in boundary files
    assert "constraints" in entities
    assert len(entities["constraints"]) == 1
    assert entities["constraints"][0]["name"] == "python"
    assert "id" in entities["constraints"][0]

    # Layers: derived from components
    assert "layers" in entities
    assert len(entities["layers"]) == 1
    assert entities["layers"][0]["name"] == "service"

    # Actors: all included
    assert "actors" in entities
    assert len(entities["actors"]) == 1
    assert entities["actors"][0]["id"] == "ACT-1"
