"""Orchestration — enrich and decompose workflows for architecture models."""

from architecture_model.orchestration.enrich import enrich_model
from architecture_model.orchestration.decompose import decompose_model, write_sub_models

from architecture_model.orchestration.deep_decompose import iterative_decompose
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
from architecture_model.orchestration.auto_enrich import enrich_from_manifest, enrich_behaviors_from_manifest

__all__ = ["enrich_model", "decompose_model", "write_sub_models", "iterative_decompose", "format_enrichment_prompt", "enrich_from_manifest", "enrich_behaviors_from_manifest"]
