"""SI&L (Self-Improvement & Logging) package.

Exports the record schema. The ``instrumented`` decorator will be added
in task B2.1.2 and re-exported here at that time.
"""

from architecture_model.sil.record import (
    Event,
    Metrics,
    Rollup,
    SILRecord,
    dump_yaml,
    load_yaml,
)

__all__ = [
    "Event",
    "Metrics",
    "Rollup",
    "SILRecord",
    "dump_yaml",
    "load_yaml",
]
