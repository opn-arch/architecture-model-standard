"""Artifact selection and registry for model-driven SE document generation."""

from architecture_model.artifacts.selector import (
    ArtifactSpec,
    ARTIFACT_REGISTRY,
    SUBSYSTEM_ARTIFACTS,
    SubsystemInfo,
    get_artifact_spec,
    select_artifacts,
    select_subsystem_artifacts,
    should_decompose,
)
from architecture_model.artifacts.templates import ArtifactTemplate, TemplateSection, TEMPLATES, get_template
from architecture_model.artifacts.context import assemble_artifact_context

__all__ = [
    "ArtifactSpec",
    "ArtifactTemplate",
    "ARTIFACT_REGISTRY",
    "SUBSYSTEM_ARTIFACTS",
    "SubsystemInfo",
    "TEMPLATES",
    "TemplateSection",
    "assemble_artifact_context",
    "get_artifact_spec",
    "get_template",
    "select_artifacts",
    "select_subsystem_artifacts",
    "should_decompose",
]
