"""pipeline_v3.verify — Chain-closure verification stage (T0.14 Phase 6.6).

Runs :func:`architecture_model.quality.chain_closure.analyze_chain_closure`
over a :class:`ContainerizedModel`. Two entry points:

    - :func:`verify_model` — flat chain-closure report over the whole model.
    - :func:`verify_per_component` — per-component reports for drill-down.

Root-owner convention
---------------------

After :mod:`containerize`, every Promise's ``owner_entity`` is a
component id — there is no higher-level entity for a component-scoped
Promise to be "delivered from". If callers do not supply an explicit
``root_owner_ids`` set, verify treats every component id in the model
as a root. This prevents the entire graph from spuriously flagging
``G-DELIVERY`` when what we actually want to inspect is verification
coverage (``G-VERIFY``) and open-question closure (``G-OPEN-Q``).

Callers who *do* want strict delivery-lineage checking (e.g. when
inter-component delivery edges are expected) can pass
``root_owner_ids=frozenset()`` or a specific subset.
"""

from __future__ import annotations

from architecture_model.pipeline_v3.containerize import ContainerizedModel
from architecture_model.quality.chain_closure import (
    ChainClosureReport,
    analyze_chain_closure,
)

__all__ = ["verify_model", "verify_per_component"]


def _default_roots(model: ContainerizedModel) -> frozenset[str]:
    """Every component id is a delivery root by default (see module docstring)."""
    return frozenset(c.id for c in model.components)


def verify_model(
    model: ContainerizedModel,
    *,
    root_owner_ids: frozenset[str] | set[str] | None = None,
) -> ChainClosureReport:
    """Chain-closure report over all Promises in ``model``.

    Args:
        model: :class:`ContainerizedModel` from :mod:`containerize`.
        root_owner_ids: Owner ids exempt from ``G-DELIVERY``. Defaults to
            every component id in the model (see module docstring).
    """
    roots = (
        frozenset(root_owner_ids)
        if root_owner_ids is not None
        else _default_roots(model)
    )
    all_promises = [p for c in model.components for p in c.promises]
    return analyze_chain_closure(all_promises, root_owner_ids=roots)


def verify_per_component(
    model: ContainerizedModel,
    *,
    root_owner_ids: frozenset[str] | set[str] | None = None,
) -> dict[str, ChainClosureReport]:
    """Return {component_id: ChainClosureReport} for each component.

    Each component's report is computed against ONLY that component's
    Promises. Root owners default to the component's own id.
    """
    out: dict[str, ChainClosureReport] = {}
    for comp in model.components:
        roots = (
            frozenset(root_owner_ids)
            if root_owner_ids is not None
            else frozenset({comp.id})
        )
        out[comp.id] = analyze_chain_closure(
            list(comp.promises),
            root_owner_ids=roots,
        )
    return out
