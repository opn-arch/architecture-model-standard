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

__all__ = [
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
]
