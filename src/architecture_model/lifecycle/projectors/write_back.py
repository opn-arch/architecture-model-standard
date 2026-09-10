"""``WriteBackProjector`` base class — Phase 4-A Task 1.

Write-back projectors are the LLM-authoring counterpart to the
deterministic Phase 1-3 projectors. A ``.llm`` variant sits alongside
its deterministic sibling: the deterministic projector renders whatever
semantic content is already on the model; the write-back projector
takes the deterministic base view as input, prompts an
:class:`~architecture_model.llm.provider.LLMProvider` for a structured
authoring payload, and packages the response as an
:class:`~architecture_model.ai.proposals.ModelPatch` proposal ready for
:func:`architect_proposal_apply` to persist.

Contract:

1. ``base_projector_name`` (class attr) names the sibling deterministic
   projector. The base view is dispatched from the provided ``registry``
   (or :data:`DEFAULT_REGISTRY` when unset).
2. Subclasses override three hooks:
   - ``build_prompt(base_view, fragment, config) -> str``
   - ``expected_proposal_schema() -> dict``
   - ``pack_proposal(raw, fragment, config) -> Proposal``
3. ``__call__`` composes: dispatch base → build prompt → provider
   ``structured()`` → pack proposal → wrap in a ``DiagramSpec`` with
   ``content_kind="ai_proposal"``.

No LLM providers are imported at module load — a provider is passed via
DI so tests inject mocks and the module remains offline-safe.
"""

from __future__ import annotations

from typing import Any, ClassVar, TYPE_CHECKING

from architecture_model.core.diagram_spec import DiagramSpec

if TYPE_CHECKING:  # pragma: no cover
    from architecture_model.ai.proposals import Proposal
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.llm.provider import LLMProvider
    from architecture_model.lifecycle.view_projection import ProjectorRegistry


class WriteBackProjector:
    """Base class for LLM-authoring projectors.

    Instances are callable with the same ``(fragment, config)`` signature
    as deterministic projectors so they slot into the existing
    :class:`~architecture_model.lifecycle.view_projection.ProjectorRegistry`.
    """

    base_projector_name: ClassVar[str] = ""
    projector_name: ClassVar[str] = ""

    def __init__(
        self,
        provider: "LLMProvider",
        task_class: str,
        *,
        registry: "ProjectorRegistry | None" = None,
    ) -> None:
        if not self.base_projector_name:
            raise ValueError(
                f"{type(self).__name__}.base_projector_name must be set"
            )
        if not self.projector_name:
            raise ValueError(
                f"{type(self).__name__}.projector_name must be set"
            )
        if not self.projector_name.endswith(".llm"):
            raise ValueError(
                f"{type(self).__name__}.projector_name "
                f"({self.projector_name!r}) must end with '.llm'"
            )
        self.provider = provider
        self.task_class = task_class
        self._registry = registry

    def __call__(
        self, fragment: "ArchitectureModel", config: dict[str, Any]
    ) -> DiagramSpec:
        registry = self._resolve_registry()
        base_fn, _base_version = registry.get(self.base_projector_name)
        base_view = base_fn(fragment, config)
        prompt = self.build_prompt(base_view, fragment, config)
        schema = self.expected_proposal_schema()
        raw = self.provider.structured(prompt, schema=schema)
        proposal = self.pack_proposal(raw, fragment, config)
        return DiagramSpec(
            id=f"prose:{self.projector_name}",
            title=self.projector_name,
            facets={
                "content_kind": "ai_proposal",
                "proposal": proposal.to_dict(),
                "base_view_id": base_view.id,
            },
        )

    # -- Hooks subclasses override ------------------------------------------

    def build_prompt(
        self,
        base_view: DiagramSpec,
        fragment: "ArchitectureModel",
        config: dict[str, Any],
    ) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} must override build_prompt()"
        )

    def expected_proposal_schema(self) -> dict[str, Any]:
        raise NotImplementedError(
            f"{type(self).__name__} must override expected_proposal_schema()"
        )

    def pack_proposal(
        self,
        raw: dict[str, Any],
        fragment: "ArchitectureModel",
        config: dict[str, Any],
    ) -> "Proposal":
        raise NotImplementedError(
            f"{type(self).__name__} must override pack_proposal()"
        )

    # -- Internal helpers ----------------------------------------------------

    def _resolve_registry(self) -> "ProjectorRegistry":
        if self._registry is not None:
            return self._registry
        # Late import — DEFAULT_REGISTRY seeds itself on first access via the
        # view_projection module's helpers; importing at call time avoids a
        # projector-registration import cycle.
        from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

        return DEFAULT_REGISTRY


__all__ = ["WriteBackProjector"]
