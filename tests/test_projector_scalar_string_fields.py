"""Regression tests for scalar-string handling in behavior semantic fields.

Real-world models (see BEH-26/27/28 in this repo's own model) declare
``goals`` / ``postconditions`` as scalar YAML strings rather than lists.
The parser stores them verbatim into ``list[str]`` fields (no coercion).
Projectors that call ``next(iter(field), "")`` on such a value iterate
the string character-by-character and yield only the first char,
producing outcome/goal labels like ``"a"``, ``"n"``, ``"c"`` instead of
the full sentence.

These tests pin the correct behavior: the first-value helper must
return the full string when given a str, not its first character.
"""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import (
    project_conops,
    project_use_cases,
)
from architecture_model.core.view_context import ArchitectureViewContext


_EXPECTED_OUTCOME = "Agent receives compressed context under budget"
_EXPECTED_GOAL = "Compressed architecture context under agent token budget"


def _write_model_with_scalar_fields(tmp_path: Path) -> Path:
    """Write a minimal model where postconditions/goals are scalar strings."""
    path = tmp_path / ".architecture-model.yaml"
    path.write_text(
        f"""meta: {{project: scalar_fields, schema_version: '2.0'}}
entities:
  actors:
    - {{id: ACT-1, name: Agent, status: ACTIVE}}
  capabilities:
    - {{id: CAP-1, name: Context Broker, status: ACTIVE}}
  behaviors:
    - id: BEH-1
      name: Slice-Scoped Context
      status: ACTIVE
      behavior_type: use_case
      actor_id: ACT-1
      capability_id: CAP-1
      trigger: AI agent invokes architect_slice with a focus target
      goals: {_EXPECTED_GOAL}
      preconditions: A published architecture model exists
      postconditions: {_EXPECTED_OUTCOME}
      interface_refs: [IF-1]
  interfaces:
    - {{id: IF-1, name: Slice API, status: ACTIVE, provider: SYS-1, consumer: ACT-1}}
  systems:
    - {{id: SYS-1, name: Broker, status: ACTIVE}}
relationships:
  - {{from: ACT-1, to: IF-1, type: consumes}}
  - {{from: SYS-1, to: IF-1, type: exposes}}
""",
        encoding="utf-8",
    )
    return path


def _context(tmp_path: Path) -> ArchitectureViewContext:
    path = _write_model_with_scalar_fields(tmp_path)
    return ArchitectureViewContext.load(load_model(path), tmp_path)


def test_conops_outcome_label_uses_full_string_when_postconditions_is_scalar(tmp_path):
    """conops outcome node must show the full postconditions sentence, not char 0."""
    spec = project_conops(_context(tmp_path))
    outcome_nodes = [node for node in spec.nodes if node.kind == "outcome"]
    assert outcome_nodes, "expected an outcome node for BEH-1"
    labels = [node.label for node in outcome_nodes]
    assert _EXPECTED_OUTCOME in labels, (
        f"outcome label should be the full postconditions string, got {labels!r}"
    )
    # Guard against the char-iteration regression specifically.
    assert not any(len(label) == 1 for label in labels), (
        f"single-character outcome label indicates str-iteration bug: {labels!r}"
    )


def test_conops_scenario_subtitle_uses_full_goal_when_goals_is_scalar(tmp_path):
    """conops scenario subtitle must include the full goal string, not char 0."""
    spec = project_conops(_context(tmp_path))
    scenario_nodes = [node for node in spec.nodes if node.kind == "scenario"]
    assert scenario_nodes, "expected a scenario node for BEH-1"
    subtitle = scenario_nodes[0].subtitle or ""
    assert _EXPECTED_GOAL in subtitle, (
        f"scenario subtitle should contain the full goal string, got {subtitle!r}"
    )


def test_use_cases_subtitle_uses_full_strings_when_semantic_fields_are_scalar(tmp_path):
    """use-cases node subtitle must show the full goal + outcome strings, not char 0."""
    spec = project_use_cases(_context(tmp_path))
    use_case_nodes = [node for node in spec.nodes if node.kind == "use-case"]
    assert use_case_nodes, "expected a use-case node for BEH-1"
    subtitle = use_case_nodes[0].subtitle or ""
    assert _EXPECTED_GOAL in subtitle, (
        f"use-case subtitle should contain the full goal string, got {subtitle!r}"
    )
    assert _EXPECTED_OUTCOME in subtitle, (
        f"use-case subtitle should contain the full postconditions string, got {subtitle!r}"
    )
