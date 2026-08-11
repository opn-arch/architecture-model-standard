"""Output types for the emit pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EmitResult:
    """What was written to disk."""

    written_paths: list[str] = field(default_factory=list)
    total_bytes: int = 0
    system_count: int = 0
    doc_count: int = 0
    output_dir: str = ""
