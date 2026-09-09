"""EntityPageProjector base class with kind dispatch (Phase 3 Task 7).

Rather than register ``family1.entity_page.component``,
``family1.entity_page.capability``, ... as separate projectors (14 kinds
* 7 families = 98 names), each family registers a single
``familyN.entity_page`` projector: an instance of a
:class:`EntityPageProjector` subclass that dispatches internally by the
scope entity's kind.

Scope info is injected into the projector config by
:func:`architecture_model.lifecycle.view_projection.project` from the
materialized slice's ``provenance['scope_metadata']`` for entity-scoped
slices. The two keys consumed here are:

* ``__scope_entity_id`` — the id from ``scope=entity(<id>)``.
* ``__scope_entity_kind`` — the singular canonical kind
  (``"component"``, ``"capability"``, ...).

Subclasses set ``family: int`` and implement ``_project_<kind>(model,
config) -> DiagramSpec`` for each supported kind. Unknown kinds raise
``NotImplementedError`` — the base does not silently degrade.

The concrete family renderers land in Tasks 8-14; this file only ships
the dispatch scaffolding + tests.
"""

from __future__ import annotations

from typing import Any

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import ArchitectureModel


class EntityPageProjector:
    """Callable base implementing the ``ProjectorFn`` contract.

    Subclasses set ``family`` and provide ``_project_<kind>`` methods.
    The instance itself is registered against the
    :class:`~architecture_model.lifecycle.view_projection.ProjectorRegistry`
    under the name ``familyN.entity_page``.
    """

    family: int = 0

    def __call__(
        self,
        model: ArchitectureModel,
        config: dict[str, Any],
    ) -> DiagramSpec:
        kind = str(config.get("__scope_entity_kind", "") or "").lower()
        method = getattr(self, f"_project_{kind}", None)
        if method is None:
            raise NotImplementedError(
                f"family{self.family}.entity_page has no rendering for kind={kind!r}"
            )
        return method(model, config)


# ---------------------------------------------------------------------------
# Family 1 — mission / purpose per entity (Phase 3 Task 8)
# ---------------------------------------------------------------------------


_FAMILY1_ENTITY_FIELDS = (
    "actors",
    "capabilities",
    "behaviors",
    "interfaces",
    "constraints",
    "layers",
    "components",
)


def _find_entity_by_id(model: ArchitectureModel, entity_id: str):
    """Return the entity object with ``id == entity_id`` from any of the
    seven family-1 entity kinds, or ``None`` if absent from the fragment.
    """
    for field_name in _FAMILY1_ENTITY_FIELDS:
        for ent in getattr(model.entities, field_name, ()):
            if getattr(ent, "id", None) == entity_id:
                return ent
    return None


def _render_family1_body(entity: Any, inbound_depends_on: tuple[str, ...]) -> str:
    """Render the Markdown body for a family-1 entity page.

    Sections are emitted in canonical order and only when they have
    content. ``inbound_depends_on`` ids are folded into the Stakeholders
    section (unioned with the entity's declared stakeholders, sorted for
    determinism).
    """
    parts: list[str] = []

    intent = (getattr(entity, "intent", "") or "").strip()
    if intent:
        parts.append("## Intent\n\n" + intent)

    goals = tuple(getattr(entity, "goals", ()) or ())
    if goals:
        parts.append("## Goals\n\n" + "\n".join(f"- {g}" for g in goals))

    declared_stakeholders = tuple(getattr(entity, "stakeholders", ()) or ())
    all_stakeholders = tuple(
        sorted(set(declared_stakeholders) | set(inbound_depends_on))
    )
    if all_stakeholders:
        parts.append(
            "## Stakeholders\n\n"
            + "\n".join(f"- {s}" for s in all_stakeholders)
        )

    success = tuple(getattr(entity, "success_criteria", ()) or ())
    if success:
        parts.append(
            "## Success Criteria\n\n" + "\n".join(f"- {s}" for s in success)
        )

    owner = (getattr(entity, "owner", "") or "").strip()
    if owner:
        parts.append("## Ownership\n\nOwner: " + owner)

    maturity = getattr(entity, "maturity", None)
    if maturity is not None:
        # Enum or string; render the value.
        mat_str = getattr(maturity, "value", maturity)
        parts.append(f"## Maturity\n\n{mat_str}")

    return "\n\n".join(parts)


class Family1EntityPage(EntityPageProjector):
    """Family 1: mission / purpose per entity.

    Renders a Markdown ``DiagramSpec`` per Phase-1 prose convention.
    Supported kinds: component, capability, behavior, interface, actor,
    constraint, layer.
    """

    family = 1

    def _build(
        self,
        model: ArchitectureModel,
        config: dict[str, Any],
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        inbound = tuple(config.get("__scope_inbound_depends_on", ()) or ())
        entity = _find_entity_by_id(model, entity_id)
        if entity is None:
            # Degenerate: scope entity not present in fragment. Emit a
            # minimal well-formed DiagramSpec rather than raise — the
            # projector contract requires a DiagramSpec return.
            return DiagramSpec(
                id=f"prose:family1.entity_page:{entity_id}",
                title=f"({entity_id})",
                facets={"content_kind": "markdown", "body": ""},
            )
        name = getattr(entity, "name", "") or entity_id
        body = _render_family1_body(entity, inbound)
        return DiagramSpec(
            id=f"prose:family1.entity_page:{entity_id}",
            title=f"{name} ({entity_id})",
            facets={"content_kind": "markdown", "body": body},
        )

    # All seven supported kinds dispatch to the same shared renderer;
    # semantic fields are uniform across them (Phase 2 schema 2.1).
    _project_component = _build
    _project_capability = _build
    _project_behavior = _build
    _project_interface = _build
    _project_actor = _build
    _project_constraint = _build
    _project_layer = _build


# ---------------------------------------------------------------------------
# Family 2 — functional decomposition per entity (Phase 3 Task 9)
# ---------------------------------------------------------------------------


def _family2_spec(
    entity_id: str,
    model: ArchitectureModel,
    body: str,
) -> DiagramSpec:
    """Build the common family-2 DiagramSpec envelope."""
    entity = _find_entity_by_id(model, entity_id)
    name = getattr(entity, "name", "") if entity is not None else ""
    display_name = name or entity_id
    return DiagramSpec(
        id=f"prose:family2.entity_page:{entity_id}",
        title=f"{display_name} ({entity_id})",
        facets={"content_kind": "markdown", "body": body},
    )


class Family2EntityPage(EntityPageProjector):
    """Family 2: functional decomposition per entity.

    Kinds:

    * **capability**: sub-``contains`` tree, realizing components,
      outbound ``triggers``.
    * **component**: capabilities the component ``realizes``.
    * **behavior**: capability that ``contains`` this behavior.

    Other kinds raise ``NotImplementedError`` per the base contract.
    """

    family = 2

    def _project_capability(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        descendants = tuple(config.get("__scope_contains_descendants", ()) or ())
        inbound_by_type = config.get("__scope_inbound_by_type", {}) or {}
        outbound_by_type = config.get("__scope_outbound_by_type", {}) or {}

        realizing = tuple(inbound_by_type.get("realizes", ()) or ())
        triggers_out = tuple(outbound_by_type.get("triggers", ()) or ())

        parts: list[str] = []
        if descendants:
            parts.append(
                "## Sub-Decomposition\n\n"
                + "\n".join(f"- {d}" for d in descendants)
            )
        if realizing:
            parts.append(
                "## Realizing Components\n\n"
                + "\n".join(f"- {r}" for r in realizing)
            )
        if triggers_out:
            parts.append(
                "## Triggers\n\n" + "\n".join(f"- {t}" for t in triggers_out)
            )
        return _family2_spec(entity_id, model, "\n\n".join(parts))

    def _project_component(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        outbound_by_type = config.get("__scope_outbound_by_type", {}) or {}
        realized = tuple(outbound_by_type.get("realizes", ()) or ())

        parts: list[str] = []
        if realized:
            parts.append(
                "## Realizes\n\n" + "\n".join(f"- {r}" for r in realized)
            )
        return _family2_spec(entity_id, model, "\n\n".join(parts))

    def _project_behavior(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        inbound_by_type = config.get("__scope_inbound_by_type", {}) or {}
        # Behavior is contained BY a capability => inbound contains.
        containers = tuple(inbound_by_type.get("contains", ()) or ())

        parts: list[str] = []
        if containers:
            parts.append(
                "## Belongs To\n\n" + "\n".join(f"- {c}" for c in containers)
            )
        return _family2_spec(entity_id, model, "\n\n".join(parts))


# ---------------------------------------------------------------------------
# Family 3 — structural per entity (Phase 3 Task 10)
# ---------------------------------------------------------------------------


def _family_spec(
    family: int,
    entity_id: str,
    model: ArchitectureModel,
    body: str,
) -> DiagramSpec:
    """Generic family-N DiagramSpec envelope for prose entity pages."""
    entity = _find_entity_by_id(model, entity_id)
    name = getattr(entity, "name", "") if entity is not None else ""
    display_name = name or entity_id
    return DiagramSpec(
        id=f"prose:family{family}.entity_page:{entity_id}",
        title=f"{display_name} ({entity_id})",
        facets={"content_kind": "markdown", "body": body},
    )


class Family3EntityPage(EntityPageProjector):
    """Family 3: structural context per entity.

    Kinds: component, layer. Sections: Internal Parts, Depends On,
    Depended On By, Exposed Interfaces, Consumed Interfaces,
    Dependencies Rationale.
    """

    family = 3

    def _render(
        self,
        model: ArchitectureModel,
        config: dict[str, Any],
        *,
        include_interfaces: bool,
        include_rationale: bool,
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        descendants = tuple(config.get("__scope_contains_descendants", ()) or ())
        outbound = config.get("__scope_outbound_by_type", {}) or {}
        inbound = config.get("__scope_inbound_by_type", {}) or {}

        parts: list[str] = []
        if descendants:
            parts.append(
                "## Internal Parts\n\n"
                + "\n".join(f"- {d}" for d in descendants)
            )
        depends_out = tuple(outbound.get("depends-on", ()) or ())
        if depends_out:
            parts.append(
                "## Depends On\n\n" + "\n".join(f"- {d}" for d in depends_out)
            )
        depends_in = tuple(inbound.get("depends-on", ()) or ())
        if depends_in:
            parts.append(
                "## Depended On By\n\n"
                + "\n".join(f"- {d}" for d in depends_in)
            )
        if include_interfaces:
            exposed = tuple(outbound.get("exposes", ()) or ())
            if exposed:
                parts.append(
                    "## Exposed Interfaces\n\n"
                    + "\n".join(f"- {e}" for e in exposed)
                )
            consumed = tuple(outbound.get("consumes", ()) or ())
            if consumed:
                parts.append(
                    "## Consumed Interfaces\n\n"
                    + "\n".join(f"- {c}" for c in consumed)
                )
        if include_rationale:
            entity = _find_entity_by_id(model, entity_id)
            rationale = getattr(entity, "dependencies_rationale", None) or {}
            if rationale:
                lines = [f"- **{k}**: {v}" for k, v in sorted(rationale.items())]
                parts.append("## Dependencies Rationale\n\n" + "\n".join(lines))
        return _family_spec(3, entity_id, model, "\n\n".join(parts))

    def _project_component(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        return self._render(
            model, config, include_interfaces=True, include_rationale=True
        )

    def _project_layer(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        return self._render(
            model, config, include_interfaces=False, include_rationale=False
        )


# ---------------------------------------------------------------------------
# Family 4 — scenarios / interactions per entity (Phase 3 Task 11)
# ---------------------------------------------------------------------------


class Family4EntityPage(EntityPageProjector):
    """Family 4: scenarios per entity.

    Kinds: behavior, actor. Behavior sections: Triggered By, Triggers,
    Actors (inbound consumers). Actor sections: Consumes (outbound
    consumers of interfaces / behaviors).
    """

    family = 4

    def _project_behavior(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        outbound = config.get("__scope_outbound_by_type", {}) or {}
        inbound = config.get("__scope_inbound_by_type", {}) or {}
        triggered_by = tuple(inbound.get("triggers", ()) or ())
        triggers_out = tuple(outbound.get("triggers", ()) or ())
        consumers = tuple(inbound.get("consumes", ()) or ())

        parts: list[str] = []
        if triggered_by:
            parts.append(
                "## Triggered By\n\n"
                + "\n".join(f"- {t}" for t in triggered_by)
            )
        if triggers_out:
            parts.append(
                "## Triggers\n\n" + "\n".join(f"- {t}" for t in triggers_out)
            )
        if consumers:
            parts.append(
                "## Actors\n\n" + "\n".join(f"- {c}" for c in consumers)
            )
        return _family_spec(4, entity_id, model, "\n\n".join(parts))

    def _project_actor(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        outbound = config.get("__scope_outbound_by_type", {}) or {}
        consumed = tuple(outbound.get("consumes", ()) or ())

        parts: list[str] = []
        if consumed:
            parts.append(
                "## Consumes\n\n" + "\n".join(f"- {c}" for c in consumed)
            )
        return _family_spec(4, entity_id, model, "\n\n".join(parts))


# ---------------------------------------------------------------------------
# Family 6 — interfaces + ICD per entity (Phase 3 Task 12)
# ---------------------------------------------------------------------------


class Family6EntityPage(EntityPageProjector):
    """Family 6: interface / ICD content per entity.

    Kinds:

    * **interface** (primary): type, protocol, provider, consumer,
      data_format, schema, contract.
    * **component**: exposed and consumed interface lists.

    Manifest-fragment-derived signatures / routes are a future extension.
    """

    family = 6

    def _project_interface(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        entity = _find_entity_by_id(model, entity_id)
        parts: list[str] = []
        if entity is not None:
            # ``type`` is always populated (enum default = INTERNAL); we
            # still surface it explicitly. Other fields default to empty
            # strings and are omitted when unset.
            type_val = getattr(entity, "type", None)
            if type_val is not None:
                type_str = getattr(type_val, "value", type_val)
                if type_str:
                    parts.append(f"## Type\n\n{type_str}")
            for section, attr in (
                ("Protocol", "protocol"),
                ("Provider", "provider"),
                ("Consumer", "consumer"),
                ("Data Format", "data_format"),
                ("Schema", "schema"),
                ("Contract", "contract"),
            ):
                val = (getattr(entity, attr, "") or "").strip()
                if val:
                    parts.append(f"## {section}\n\n{val}")
        return _family_spec(6, entity_id, model, "\n\n".join(parts))

    def _project_component(
        self, model: ArchitectureModel, config: dict[str, Any]
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        outbound = config.get("__scope_outbound_by_type", {}) or {}
        exposed = tuple(outbound.get("exposes", ()) or ())
        consumed = tuple(outbound.get("consumes", ()) or ())

        parts: list[str] = []
        if exposed:
            parts.append(
                "## Exposed Interfaces\n\n"
                + "\n".join(f"- {e}" for e in exposed)
            )
        if consumed:
            parts.append(
                "## Consumed Interfaces\n\n"
                + "\n".join(f"- {c}" for c in consumed)
            )
        return _family_spec(6, entity_id, model, "\n\n".join(parts))


# ---------------------------------------------------------------------------
# Family 7 — quality + verification per entity (Phase 3 Task 13)
# ---------------------------------------------------------------------------


def _render_item(item: Any) -> str:
    """Render one list element (str, dict, or object with to_dict) as a
    single-line bullet payload.

    VerificationRef / SLO objects declare ``to_dict`` (Phase 2 schema
    2.1). We surface their ``id`` field when present for a stable
    single-line rendering; otherwise fall back to a compact repr.
    """
    if item is None:
        return ""
    if isinstance(item, str):
        return item
    if hasattr(item, "to_dict"):
        d = item.to_dict()
    elif isinstance(item, dict):
        d = item
    else:
        return str(item)
    if not isinstance(d, dict):
        return str(d)
    if d.get("id"):
        return d["id"]
    if d.get("statement"):
        return d["statement"]
    # SLO shape: metric / target / window
    if "metric" in d and "target" in d:
        window = d.get("window", "")
        base = f"{d['metric']} {d['target']}"
        return f"{base} ({window})" if window else base
    return str(d)


def _render_list_section(header: str, items: Any) -> str:
    """Render a `## Header\\n\\n- item1\\n- item2` block, or '' if empty."""
    seq = tuple(items or ())
    if not seq:
        return ""
    lines = [f"- {_render_item(i)}" for i in seq]
    return f"## {header}\n\n" + "\n".join(lines)


class Family7EntityPage(EntityPageProjector):
    """Family 7: quality + verification per entity.

    Kinds: component, capability, behavior, interface, constraint.
    Sections rendered in canonical order (any empty section omitted):
    Requirements, Verification, Failure Modes, Assumptions, Open
    Questions, SLOs (Interface / Component only).
    """

    family = 7

    def _render(
        self,
        model: ArchitectureModel,
        config: dict[str, Any],
        *,
        include_slos: bool,
    ) -> DiagramSpec:
        entity_id = config.get("__scope_entity_id", "")
        entity = _find_entity_by_id(model, entity_id)

        parts: list[str] = []
        if entity is not None:
            for header, attr in (
                ("Requirements", "requirements"),
                ("Verification", "verification"),
                ("Failure Modes", "failure_modes"),
                ("Assumptions", "assumptions"),
                ("Open Questions", "open_questions"),
            ):
                section = _render_list_section(
                    header, getattr(entity, attr, ()) or ()
                )
                if section:
                    parts.append(section)
            if include_slos:
                section = _render_list_section(
                    "SLOs", getattr(entity, "slos", ()) or ()
                )
                if section:
                    parts.append(section)
        return _family_spec(7, entity_id, model, "\n\n".join(parts))

    def _project_component(self, model, config):
        return self._render(model, config, include_slos=True)

    def _project_capability(self, model, config):
        return self._render(model, config, include_slos=False)

    def _project_behavior(self, model, config):
        return self._render(model, config, include_slos=False)

    def _project_interface(self, model, config):
        return self._render(model, config, include_slos=True)

    def _project_constraint(self, model, config):
        return self._render(model, config, include_slos=False)
