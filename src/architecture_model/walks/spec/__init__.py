"""architecture_model.walks.spec — WalkSpec YAML loader.

WalkSpec is the declarative description of a walk. Six sections match
the six pipeline stages:

    scope → traverse → classify → rollup → evidence → emit

Plus top-level metadata: id, audits, from_walk (composition).
"""
