"""Lifecycle package: identity, serialization, packages, revisions, slices, views, artifacts, gates."""
from architecture_model.lifecycle.versions import SchemaVersions, ContractKind
from architecture_model.lifecycle.model_slice import (
    ModelSlice,
    Selectors,
    Curation,
    compute_slice_digest,
)
from architecture_model.lifecycle.model_slice_materializer import (
    MaterializationWarning,
    MaterializedSlice,
    materialize,
)
from architecture_model.lifecycle.view_spec import (
    SliceRef,
    ViewCuration,
    ViewSpec,
    compute_view_spec_digest,
)
from architecture_model.lifecycle.view_projection import (
    DEFAULT_REGISTRY,
    ProjectedView,
    ProjectorFn,
    ProjectorNotFound,
    ProjectorRegistry,
    SliceMismatch,
    project,
)
from architecture_model.lifecycle.artifact_spec import (
    ArtifactSpec,
    Renderer,
    SignatureSlot,
    ViewRef,
    compute_artifact_spec_digest,
)
from architecture_model.lifecycle.artifact_dag import (
    ArtifactDAG,
    ArtifactDAGCycle,
    ArtifactDAGError,
    BuildStep,
    MissingArtifactRef,
    RebuildPlan,
    build_artifact_dag,
    rebuild_plan,
)
from architecture_model.lifecycle.renderers import (
    DEFAULT_RENDERERS,
    RendererFn,
    get_renderer,
    render_html,
    render_markdown,
    render_svg,
)

__all__ = [
    "ArtifactDAG",
    "ArtifactDAGCycle",
    "ArtifactDAGError",
    "BuildStep",
    "MissingArtifactRef",
    "RebuildPlan",
    "build_artifact_dag",
    "rebuild_plan",
    "ArtifactSpec",
    "Renderer",
    "SignatureSlot",
    "ViewRef",
    "compute_artifact_spec_digest",
    "DEFAULT_REGISTRY",
    "ProjectedView",
    "ProjectorFn",
    "ProjectorNotFound",
    "ProjectorRegistry",
    "SliceMismatch",
    "project",
    "SchemaVersions",
    "ContractKind",
    "ModelSlice",
    "Selectors",
    "Curation",
    "compute_slice_digest",
    "MaterializationWarning",
    "MaterializedSlice",
    "materialize",
    "ViewSpec",
    "SliceRef",
    "ViewCuration",
    "compute_view_spec_digest",
    "DEFAULT_RENDERERS",
    "RendererFn",
    "get_renderer",
    "render_html",
    "render_markdown",
    "render_svg",
]
