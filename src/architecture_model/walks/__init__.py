"""architecture_model.walks — Walk-as-capability substrate.

Walks are declarative audits over the architecture-model graph. Each
walk is a WalkSpec YAML file that runs on the shared substrate
(pipeline_v3.substrate) through six stages:

    select → traverse → classify → rollup → evidence → emit

Each walk is modeled as an AMS capability (CAP-WK.<slug>) with full v3
attributes (intent, goals, requirements, promises). Walks self-model:
CAP-WK is the umbrella capability, sub-caps are individual walks.

See docs/plans/2026-09-16-walk-substrate.md for the design.
"""

from architecture_model.walks.attribute import (
    Attribute,
    AttributeCategory,
    AttributeSource,
    default_category,
)
from architecture_model.walks.runner import build_walk_pipeline, run_walk
from architecture_model.walks.spec.loader import (
    WalkSpec,
    load_walk_spec,
    load_walk_specs_from_dir,
)
from architecture_model.walks.verdict import Verdict

__all__ = [
    "Attribute",
    "AttributeCategory",
    "AttributeSource",
    "Verdict",
    "WalkSpec",
    "build_walk_pipeline",
    "default_category",
    "load_walk_spec",
    "load_walk_specs_from_dir",
    "run_walk",
]
