"""architecture_model.walks.meta — meta-walks that audit the walk substrate.

Meta-walks are walks whose subject is the walk substrate itself (WalkSpec
YAMLs and the CAP-WK.* sub-cap inventory). They complement the declarative
WalkSpec runner: `walk_coverage` is Python because it inspects filesystem
YAML files rather than model entities, while `attribute-completeness` is a
pure declarative WalkSpec (`.architecture/model/walks/attribute-completeness.v3.yaml`)
that exercises the classify DSL on promise arrays.

Realizes CAP-WK.meta-coverage.
"""

from architecture_model.walks.meta.direction_lint import (
    DirectionLintCard,
    DirectionLintReport,
    audit_edge_note_directions,
    lint_edge_note_directions,
)
from architecture_model.walks.meta.walk_coverage import (
    CoverageCard,
    CoverageReport,
    audit_walk_coverage,
    collect_cap_wk_subcaps,
)

__all__ = [
    "CoverageCard",
    "CoverageReport",
    "DirectionLintCard",
    "DirectionLintReport",
    "audit_edge_note_directions",
    "audit_walk_coverage",
    "collect_cap_wk_subcaps",
    "lint_edge_note_directions",
]
