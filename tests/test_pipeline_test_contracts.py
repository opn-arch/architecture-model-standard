"""Tests for test_contracts enrichment in the pipeline."""
from pathlib import Path


def _create_repo(tmp_path: Path, *, with_tests: bool = True) -> Path:
    """Create a minimal repo with source (and optionally test) files."""
    # Source file
    src_dir = tmp_path / "mylib"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("")
    (src_dir / "calculator.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
    )

    if with_tests:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_calculator.py").write_text(
            "from mylib.calculator import add, subtract\n\n"
            "def test_add():\n    assert add(1, 2) == 3\n\n"
            "def test_subtract():\n    assert subtract(5, 3) == 2\n"
        )

    return tmp_path


def test_pipeline_populates_test_contracts(tmp_path):
    """Pipeline should populate test_contracts when matching test files exist."""
    from architecture_model.orchestration.pipeline import run_pipeline

    repo = _create_repo(tmp_path, with_tests=True)
    result = run_pipeline(repo, from_scratch=True)

    model = result.sub_models.get("model") if hasattr(result, "sub_models") else None
    # run_pipeline returns PipelineResult; get the model from the written file
    from architecture_model.core.parser import load_model

    model_path = repo / ".architecture-model-extracted.yaml"
    assert model_path.exists(), "Pipeline should create extracted model"
    model = load_model(model_path)

    # Find the component that has calculator.py
    comps_with_tests = [
        c for c in model.entities.components
        if any("calculator" in f for f in c.files) and c.test_contracts
    ]
    assert comps_with_tests, (
        f"Expected at least one component with test_contracts populated. "
        f"Components: {[(c.name, c.files, c.test_contracts) for c in model.entities.components]}"
    )


def test_pipeline_no_test_contracts_when_no_tests(tmp_path):
    """Pipeline should leave test_contracts empty when no test files exist."""
    from architecture_model.orchestration.pipeline import run_pipeline
    from architecture_model.core.parser import load_model

    repo = _create_repo(tmp_path, with_tests=False)
    result = run_pipeline(repo, from_scratch=True)

    model_path = repo / ".architecture-model-extracted.yaml"
    assert model_path.exists(), "Pipeline should create extracted model"
    model = load_model(model_path)

    for comp in model.entities.components:
        assert not comp.test_contracts, (
            f"Component {comp.name} should have no test_contracts but has {comp.test_contracts}"
        )
