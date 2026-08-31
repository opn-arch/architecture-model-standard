"""Tests for the infer pipeline stage."""
import pytest
from pathlib import Path
from architecture_model.pipeline.infer import InferStage, _infer_library_behaviors, _infer_capabilities_by_package
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.observe_types import ModuleRecord, FunctionRecord, ClassRecord
from architecture_model.pipeline.infer_types import InferredCapability, InferredBehavior
from architecture_model.pipeline.protocol import PipelineContext, StageResult, QualityMetrics


def _run_observe_then_infer(tmp_path):
    """Helper: run observe, cache result, then run infer."""
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
    observe = ObserveStage()
    obs_result = observe.run(ctx)
    ctx.cache["observe"] = obs_result
    infer = InferStage()
    return infer.run(ctx)


class TestInferStage:
    def test_infer_name_and_requires(self):
        stage = InferStage()
        assert stage.name == "infer"
        assert stage.requires == ["observe"]

    def test_infer_routes_grouped_by_prefix(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users():
    """List users."""
    pass

@router.post("/users")
def create_user():
    """Create user."""
    pass

@router.get("/articles")
def list_articles():
    """List articles."""
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        caps = result.output.capabilities
        # Should have at least 2 capabilities (users, articles)
        cap_names = [c.name.lower() for c in caps]
        assert any("user" in n for n in cap_names)
        assert any("article" in n for n in cap_names)

    def test_infer_actors_from_routes(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/items")
def get_items():
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        assert len(result.output.actors) >= 1
        assert result.output.actors[0].name == "API Consumer"

    def test_infer_behaviors_from_routes(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}
''')
        result = _run_observe_then_infer(tmp_path)
        assert len(result.output.behaviors) >= 1
        assert result.output.behaviors[0].name == "GET /health"

    def test_infer_quality_metrics(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        result = _run_observe_then_infer(tmp_path)
        assert "capability_coverage" in result.quality.sub_scores
        assert "actor_completeness" in result.quality.sub_scores

    def test_infer_emits_uncertainties_for_ambiguous_modules(self, tmp_path):
        # Module with few functions — not enough to trigger domain cap inference
        (tmp_path / "mystery.py").write_text('''
def do_something():
    pass

def do_another():
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        categories = [u.category for u in result.uncertainties]
        assert "ambiguous_module" in categories

    def test_infer_description_uses_docstrings(self, tmp_path):
        """Capability descriptions should incorporate module/function docstrings."""
        (tmp_path / "parser.py").write_text('''
"""Parse architecture model files into typed objects."""

def load_model(path: str) -> dict:
    """Load and validate an architecture model from YAML."""
    pass

def validate_refs(model: dict) -> list:
    """Check all entity references for integrity."""
    pass

def dump_model(model: dict) -> str:
    """Serialize a model back to YAML format."""
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        caps = result.output.capabilities
        assert len(caps) >= 1
        desc = caps[0].description.lower()
        # Should mention parsing or architecture or model — not just "domain logic in parser.py"
        assert any(word in desc for word in ["parse", "architecture", "model", "validate"]), \
            f"Description should be semantic, got: {caps[0].description}"

    def test_infer_domain_modules_as_capabilities(self, tmp_path):
        (tmp_path / "payments.py").write_text('''
def process_payment():
    pass

def refund_payment():
    pass

def validate_card():
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        cap_names = [c.name.lower() for c in result.output.capabilities]
        assert any("payment" in n for n in cap_names)


class TestInferLibraryBehaviors:
    """Tests for _infer_library_behaviors() — detecting behaviors in pure libraries."""

    def test_infer_library_behaviors_from_public_api(self):
        """Module with init/deinit/reinit → at least 1 behavior with 'init' in name."""
        modules = [
            ModuleRecord(
                path=Path("mylib/core.py"),
                functions=[
                    FunctionRecord(name="init", signature="def init()", body_hint=""),
                    FunctionRecord(name="deinit", signature="def deinit()", body_hint=""),
                    FunctionRecord(name="reinit", signature="def reinit()", body_hint=""),
                    FunctionRecord(name="_private", signature="def _private()", body_hint=""),
                ],
            ),
        ]
        caps = [InferredCapability(id="CAP-1", name="Core", description="Domain logic in mylib/core.py")]
        behaviors = _infer_library_behaviors(modules, caps, [])
        assert len(behaviors) >= 1
        names_lower = [b.name.lower() for b in behaviors]
        assert any("init" in n for n in names_lower)
        assert all(b.id.startswith("BEH-LIB-") for b in behaviors)

    def test_infer_library_behaviors_context_manager(self):
        """Class with __enter__/__exit__ → behavior with 'context' in name."""
        modules = [
            ModuleRecord(
                path=Path("mylib/resource.py"),
                classes=[
                    ClassRecord(
                        name="Connection",
                        methods=["__enter__", "__exit__", "query"],
                    ),
                ],
            ),
        ]
        caps = [InferredCapability(id="CAP-1", name="Resource", description="Domain logic in mylib/resource.py")]
        behaviors = _infer_library_behaviors(modules, caps, [])
        assert len(behaviors) >= 1
        names_lower = [b.name.lower() for b in behaviors]
        assert any("context" in n for n in names_lower)

    def test_infer_library_behaviors_lifecycle(self):
        """Class with open/close → behavior with 'lifecycle' in name."""
        modules = [
            ModuleRecord(
                path=Path("mylib/client.py"),
                classes=[
                    ClassRecord(
                        name="Client",
                        methods=["open", "close", "send", "receive"],
                    ),
                ],
            ),
        ]
        caps = [InferredCapability(id="CAP-1", name="Client", description="Domain logic in mylib/client.py")]
        behaviors = _infer_library_behaviors(modules, caps, [])
        assert len(behaviors) >= 1
        names_lower = [b.name.lower() for b in behaviors]
        assert any("lifecycle" in n for n in names_lower)

    def test_infer_library_behaviors_processing_chain(self):
        """Module with parse/validate/apply → at least 1 behavior."""
        modules = [
            ModuleRecord(
                path=Path("mylib/processor.py"),
                functions=[
                    FunctionRecord(name="parse", signature="def parse(data)", body_hint=""),
                    FunctionRecord(name="validate", signature="def validate(parsed)", body_hint=""),
                    FunctionRecord(name="apply", signature="def apply(validated)", body_hint=""),
                ],
            ),
        ]
        caps = [InferredCapability(id="CAP-1", name="Processor", description="Domain logic in mylib/processor.py")]
        behaviors = _infer_library_behaviors(modules, caps, [])
        assert len(behaviors) >= 1
        names_lower = [b.name.lower() for b in behaviors]
        assert any("pipeline" in n or "processing" in n for n in names_lower)

    def test_infer_library_behaviors_factory(self):
        """Functions named create_* or classes with Factory → behavior."""
        modules = [
            ModuleRecord(
                path=Path("mylib/factory.py"),
                functions=[
                    FunctionRecord(name="create_widget", signature="def create_widget()", body_hint=""),
                    FunctionRecord(name="create_gadget", signature="def create_gadget()", body_hint=""),
                ],
                classes=[
                    ClassRecord(name="ConnectionFactory", methods=["build"]),
                ],
            ),
        ]
        caps = [InferredCapability(id="CAP-1", name="Factory", description="Domain logic in mylib/factory.py")]
        behaviors = _infer_library_behaviors(modules, caps, [])
        assert len(behaviors) >= 1
        names_lower = [b.name.lower() for b in behaviors]
        assert any("create" in n for n in names_lower)

    def test_infer_library_behaviors_skips_non_source(self):
        """Test/init modules should be skipped."""
        modules = [
            ModuleRecord(
                path=Path("tests/test_core.py"),
                functions=[
                    FunctionRecord(name="setup", signature="def setup()", body_hint=""),
                ],
            ),
        ]
        behaviors = _infer_library_behaviors(modules, [], [])
        assert len(behaviors) == 0

    def test_library_behaviors_integrated(self, tmp_path):
        """Integration: pure library with init/close gets behaviors via full pipeline."""
        (tmp_path / "mylib.py").write_text('''
def init():
    """Initialize the library."""
    pass

def configure(options):
    """Configure settings."""
    pass

def shutdown():
    """Shut down cleanly."""
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        assert len(result.output.behaviors) >= 1


def _make_module(path: str, funcs: list[str] | None = None) -> ModuleRecord:
    """Create a minimal ModuleRecord for testing."""
    fn_records = [FunctionRecord(name=f, signature="", body_hint="") for f in (funcs or [])]
    return ModuleRecord(path=Path(path), functions=fn_records)


class TestInferCapabilitiesByPackageNaming:
    """Tests for meaningful capability naming in large repos."""

    def test_subpackage_names_used_over_toplevel(self):
        """Sub-package names should be preferred over generic top-level."""
        modules = []
        for i in range(4):
            modules.append(_make_module(
                f"src/myapp/core/mod{i}.py",
                funcs=[f"func{j}" for j in range(3)],
            ))
        for i in range(4):
            modules.append(_make_module(
                f"src/myapp/api/mod{i}.py",
                funcs=[f"func{j}" for j in range(3)],
            ))
        result = _infer_capabilities_by_package(modules, set())
        names = {cap.name for cap in result}
        assert "Src" not in names
        assert "Myapp" not in names
        assert any("Core" in n for n in names)
        assert any("Api" in n for n in names)

    def test_single_package_falls_back_to_module_stems(self):
        """When all modules are in one package, use module stem themes."""
        modules = [
            _make_module("src/myapp/parser.py", funcs=["parse_a", "parse_b", "parse_c"]),
            _make_module("src/myapp/tokenizer.py", funcs=["tokenize_a", "tokenize_b"]),
            _make_module("src/myapp/formatter.py", funcs=["format_a", "format_b"]),
        ]
        result = _infer_capabilities_by_package(modules, set())
        assert len(result) >= 1
        names = {cap.name for cap in result}
        assert "Myapp" not in names
