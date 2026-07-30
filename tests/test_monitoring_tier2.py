"""Test that Tier 2/3 functions emit metrics."""
from architecture_model.monitoring import get_collector


def test_cluster_modules_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.core.cluster import cluster_modules
    modules = ["a", "b", "c", "d", "e", "f"]
    edges = [("a", "b"), ("b", "c"), ("d", "e"), ("e", "f")]
    cluster_modules(modules, edges, target_k=2, min_cluster_size=2)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "cluster_modules" in fn_names
    m = next(x for x in metrics if x.function == "cluster_modules")
    assert "cluster_count" in m.output_metrics
    assert "max_size" in m.output_metrics


def test_format_enrichment_prompt_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
    from architecture_model.orchestration.deep_decompose import DecomposeResult, SubComponent

    decomps = [DecomposeResult(
        block_id="F1", block_name="Test",
        sub_components=[SubComponent(id="C1", name="", files=["a.py"], classes=[], functions=[], line_count=10)],
        internal_relationships=[], depth=1,
    )]
    format_enrichment_prompt(decomps)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "format_enrichment_prompt" in fn_names
    m = next(x for x in metrics if x.function == "format_enrichment_prompt")
    assert "token_estimate" in m.output_metrics


def test_diff_models_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.core.types import ArchitectureModel, ModelMeta, Entities
    from architecture_model.core.differ import diff_models

    model = ArchitectureModel(meta=ModelMeta(project="t", schema_version="1.3"), entities=Entities(), relationships=[])
    diff_models(model, model)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "diff_models" in fn_names
