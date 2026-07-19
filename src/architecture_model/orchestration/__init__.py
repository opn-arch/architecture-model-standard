"""Orchestration — enrich and decompose workflows for architecture models."""

from architecture_model.orchestration.enrich import enrich_model
from architecture_model.orchestration.decompose import decompose_model, write_sub_models

__all__ = ["enrich_model", "decompose_model", "write_sub_models"]
