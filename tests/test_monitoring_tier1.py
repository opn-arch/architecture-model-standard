"""Test that Tier 1 functions emit metrics."""
from pathlib import Path
from architecture_model.monitoring import get_collector


def test_generate_manifest_emits_metrics(tmp_path):
    collector = get_collector()
    collector.drain()

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("def hello(): pass\n")

    from architecture_model.manifest.generator import generate_manifest
    generate_manifest(tmp_path)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "generate_manifest" in fn_names
    m = next(x for x in metrics if x.function == "generate_manifest")
    assert m.time_ms > 0
    assert "module_count" in m.output_metrics


def test_validate_model_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.core.types import ArchitectureModel, ModelMeta, Entities
    from architecture_model.core.validator import validate_model

    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(),
        relationships=[],
    )
    validate_model(model)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "validate_model" in fn_names
    m = next(x for x in metrics if x.function == "validate_model")
    assert "score" in m.quality_scores


def test_run_pipeline_emits_metrics(tmp_path):
    collector = get_collector()
    collector.drain()

    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(5):
        (pkg / f"m{i}.py").write_text(f"def fn{i}(): pass\n")

    config = tmp_path / ".architecture-model.yaml"
    config.write_text("""meta:
  project: test
  schema_version: '1.3'
functional_blocks:
  F1:
    name: App
    dirs:
      - app
entities:
  components: []
relationships: []
""")

    from architecture_model.orchestration.pipeline import run_pipeline
    run_pipeline(tmp_path)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "run_pipeline" in fn_names
    assert "generate_recursive_manifests" in fn_names
