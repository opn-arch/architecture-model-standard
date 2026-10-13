"""Regression tests for the operational-use-case filter in projectors.

The viewer's conops and use_cases panels historically iterated ALL
behaviors, letting two categories leak in:

1. Non-root behaviors that are ``contains``-children of an aggregation
   root (e.g. BEH-P1.1..P1.11 pipeline stages under BEH-P1). These are
   sub-steps, not top-level use cases.

2. Auto-derived root behaviors that have no narrative content (no
   trigger, no goals, no postconditions) and don't aggregate any
   children (e.g. CLI-argparse and CLI-test behaviors auto-scraped
   from source files).

The filter must yield exactly:
- Roots WITH narrative (real use cases), AND
- Roots that own ``contains`` children (aggregation roots like the
  pipeline root, which is a legitimate use-case parent even when its
  own narrative fields are sparse).
"""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import (
    project_conops,
    project_use_cases,
)
from architecture_model.core.view_context import ArchitectureViewContext


def _write_mixed_model(tmp_path: Path) -> Path:
    """Write a model with all four behavior categories present."""
    path = tmp_path / ".architecture-model.yaml"
    path.write_text(
        """meta: {project: mixed, schema_version: '2.0'}
entities:
  actors:
    - {id: ACT-1, name: Developer, status: ACTIVE}
  capabilities:
    - {id: CAP-1, name: Mission, status: ACTIVE}
  behaviors:
    # Real use case: narrative root, no children -> INCLUDE
    - id: BEH-REAL
      name: Real Use Case
      status: ACTIVE
      actor_id: ACT-1
      capability_id: CAP-1
      trigger: User invokes the workflow
      goals: [Compress context under budget]
      postconditions: [Workflow completes successfully]
      interface_refs: [IF-1]
    # Aggregation root: no narrative but owns children -> INCLUDE
    - id: BEH-AGG
      name: Aggregation Root
      status: ACTIVE
      actor_id: ACT-1
      capability_id: CAP-1
      interface_refs: [IF-1]
    # Sub-behavior: child of BEH-AGG -> EXCLUDE
    - id: BEH-AGG.1
      name: Sub Step 1
      status: ACTIVE
      description: Auto-generated sub-step of the aggregation root
    # CLI-scraped noise: root, no narrative, no children -> EXCLUDE
    - id: BEH-NOISE
      name: 'CLI: Test Something'
      status: ACTIVE
      actor_id: ACT-1
      steps: [ArgumentParser, add_argument, parse_args]
  interfaces:
    - {id: IF-1, name: API, status: ACTIVE, provider: SYS-1, consumer: ACT-1}
  systems:
    - {id: SYS-1, name: System, status: ACTIVE}
relationships:
  - {from: ACT-1, to: IF-1, type: consumes}
  - {from: SYS-1, to: IF-1, type: exposes}
  - {from: BEH-AGG, to: BEH-AGG.1, type: contains}
""",
        encoding="utf-8",
    )
    return path


def _context(tmp_path: Path) -> ArchitectureViewContext:
    path = _write_mixed_model(tmp_path)
    return ArchitectureViewContext.load(load_model(path), tmp_path)


def _entity_refs(spec, kind: str) -> set[str]:
    return {node.entity_ref for node in spec.nodes if node.kind == kind and node.entity_ref}


def test_conops_scenarios_include_only_operational_use_cases(tmp_path):
    """Real use case + aggregation root appear as scenarios; sub-behavior and CLI-noise are hidden."""
    spec = project_conops(_context(tmp_path))
    scenario_refs = _entity_refs(spec, "scenario")
    assert "root::BEH-REAL" in scenario_refs, "real use case must appear as a conops scenario"
    assert "root::BEH-AGG" in scenario_refs, "aggregation root must appear as a conops scenario"
    assert "root::BEH-AGG.1" not in scenario_refs, "sub-behavior must NOT appear as a conops scenario"
    assert "root::BEH-NOISE" not in scenario_refs, "CLI-test noise must NOT appear as a conops scenario"


def test_use_cases_panel_includes_only_operational_use_cases(tmp_path):
    """Same filter must apply to the use_cases panel."""
    spec = project_use_cases(_context(tmp_path))
    use_case_refs = _entity_refs(spec, "use-case")
    assert "root::BEH-REAL" in use_case_refs, "real use case must appear in use_cases panel"
    assert "root::BEH-AGG" in use_case_refs, "aggregation root must appear in use_cases panel"
    assert "root::BEH-AGG.1" not in use_case_refs, "sub-behavior must NOT appear in use_cases panel"
    assert "root::BEH-NOISE" not in use_case_refs, "CLI-test noise must NOT appear in use_cases panel"


def test_contained_behavior_with_narrative_is_still_a_use_case(tmp_path):
    """A behavior contained by another but carrying its own narrative is a legit sub-use-case.

    Discriminates the two ``contains`` taxonomies: pipeline sub-step
    (no narrative -> hide) vs. use-case decomposition (has narrative
    -> show). The filter must use narrative-or-aggregation, not
    is-root.
    """
    path = tmp_path / ".architecture-model.yaml"
    path.write_text(
        """meta: {project: decomposed, schema_version: '2.0'}
entities:
  actors:
    - {id: ACT-1, name: User, status: ACTIVE}
  capabilities:
    - {id: CAP-1, name: Mission, status: ACTIVE}
  behaviors:
    - id: BEH-PARENT
      name: Parent Use Case
      status: ACTIVE
      actor_id: ACT-1
      capability_id: CAP-1
      trigger: User starts the flow
      goals: [Complete parent]
      postconditions: [Parent flow done]
      interface_refs: [IF-1]
    - id: BEH-CHILD
      name: Sub Use Case
      status: ACTIVE
      actor_id: ACT-1
      capability_id: CAP-1
      trigger: Sub-flow triggered by parent
      goals: [Complete sub-flow]
      postconditions: [Sub-flow done]
      interface_refs: [IF-1]
  interfaces:
    - {id: IF-1, name: API, status: ACTIVE, provider: SYS-1, consumer: ACT-1}
  systems:
    - {id: SYS-1, name: System, status: ACTIVE}
relationships:
  - {from: ACT-1, to: IF-1, type: consumes}
  - {from: SYS-1, to: IF-1, type: exposes}
  - {from: BEH-PARENT, to: BEH-CHILD, type: contains}
""",
        encoding="utf-8",
    )
    context = ArchitectureViewContext.load(load_model(path), tmp_path)
    spec = project_use_cases(context)
    use_case_refs = _entity_refs(spec, "use-case")
    assert "root::BEH-PARENT" in use_case_refs, "parent (aggregation root with narrative) must show"
    assert "root::BEH-CHILD" in use_case_refs, (
        "child WITH narrative must still show — 'contains' between behaviors "
        "with narrative encodes use-case decomposition, not sub-step noise"
    )
