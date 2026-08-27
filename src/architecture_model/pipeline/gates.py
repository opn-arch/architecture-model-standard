"""Default quality gates per pipeline stage."""

from __future__ import annotations

from .protocol import GateSeverity, QualityGate

DEFAULT_GATES: dict[str, list[QualityGate]] = {
    "observe": [
        QualityGate("parse_success_rate", 90.0, GateSeverity.HARD),
        QualityGate("code_quality_avg", 30.0, GateSeverity.SOFT),
    ],
    "infer": [
        QualityGate("capability_coverage", 60.0, GateSeverity.SOFT),
    ],
    "allocate": [
        QualityGate("file_coverage", 95.0, GateSeverity.HARD),
        QualityGate("boundary_coherence", 50.0, GateSeverity.SOFT),
    ],
    "contract": [
        QualityGate("test_coverage_ratio", 50.0, GateSeverity.SOFT),
    ],
    "validate": [
        QualityGate("error_count", 0.0, GateSeverity.HARD, direction="lte"),
    ],
}


def get_gates_for_stage(stage_name: str) -> list[QualityGate]:
    """Return quality gates for a given stage, or empty list for unknown stages."""
    return DEFAULT_GATES.get(stage_name, [])
