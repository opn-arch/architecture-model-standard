"""Append-only structured history for pipeline execution."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StageHistoryRecord:
    name: str
    started_at: str = ""
    completed_at: str = ""
    duration_ms: int | None = None
    score: float | None = None
    confidence: float | None = None
    status: str = "completed"
    invoked_by: str = "pipeline"
    dependencies: list[str] = field(default_factory=list)
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)


@dataclass
class ComponentHistoryRecord:
    component_id: str
    name: str
    files: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    timestamp: str = ""
    duration_ms: int | None = None
    invoked_by: str = "pipeline"
    produced_entity_ids: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


@dataclass
class ModuleHistoryRecord:
    path: str
    module: str
    component_id: str = ""
    timestamp: str = ""
    duration_ms: int | None = None
    invoked_by: str = "pipeline"
    stage: str = "observe"
    produced_functions: list[str] = field(default_factory=list)
    produced_classes: list[str] = field(default_factory=list)
    produced_routes: list[str] = field(default_factory=list)
    produced_constants: list[str] = field(default_factory=list)
    produced_entity_ids: list[str] = field(default_factory=list)


@dataclass
class PipelineRunRecord:
    run_id: str
    started_at: str
    completed_at: str
    duration_ms: int
    source: str
    status: str
    history_type: str = "pipeline"
    invocation: str = ""
    scope: str = ""
    parent_run_id: str | None = None
    stages: list[StageHistoryRecord] = field(default_factory=list)
    components: list[ComponentHistoryRecord] = field(default_factory=list)
    modules: list[ModuleHistoryRecord] = field(default_factory=list)
    produced_artifacts: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineRunRecord":
        values = dict(data)
        values["stages"] = [StageHistoryRecord(**item) for item in values.get("stages", [])]
        values["components"] = [ComponentHistoryRecord(**item) for item in values.get("components", [])]
        values["modules"] = [ModuleHistoryRecord(**item) for item in values.get("modules", [])]
        return cls(**values)


def append_pipeline_history(repo_path: str | Path, record: PipelineRunRecord) -> Path:
    """Atomically append one serialized record under a process-safe file lock."""
    path = Path(repo_path) / ".architecture" / "pipeline-history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record.to_dict(), separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        except ImportError:
            pass
        offset = 0
        while offset < len(payload):
            offset += os.write(fd, payload[offset:])
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def load_pipeline_history(repo_path: str | Path, limit: int = 50) -> list[PipelineRunRecord]:
    """Load newest valid records, skipping malformed lines."""
    path = Path(repo_path) / ".architecture" / "pipeline-history.jsonl"
    if limit <= 0:
        return []
    if not path.is_file():
        legacy = _load_legacy_report(Path(repo_path))
        return [legacy] if legacy is not None else []
    records: list[PipelineRunRecord] = []
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        try:
            records.append(PipelineRunRecord.from_dict(json.loads(line)))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if len(records) >= limit:
            break
    return records


def _load_legacy_report(repo_path: Path) -> PipelineRunRecord | None:
    report_path = repo_path / ".architecture-models" / "pipeline-report.md"
    if not report_path.is_file():
        return None
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError:
        return None
    timestamp = _match(text, r"\*\*Generated:\*\*\s*(.+)")
    duration_ms = _parse_duration(_match(text, r"\*\*Total Duration:\*\*\s*(\S+)"))
    stages = []
    for match in re.finditer(
        r"^\|\s*(\w+)\s*\|\s*([\d.]+)\s*\|\s*(\d+\w*)\s*\|", text, re.MULTILINE
    ):
        stages.append(StageHistoryRecord(
            name=match.group(1), score=float(match.group(2)),
            duration_ms=_parse_duration(match.group(3)), invoked_by="legacy-report",
        ))
    return PipelineRunRecord(
        run_id="legacy-pipeline-report",
        started_at=timestamp,
        completed_at=timestamp,
        duration_ms=duration_ms,
        source="legacy-report",
        status="completed",
        invocation="pipeline-report.md",
        stages=stages,
        produced_artifacts=[str(report_path.relative_to(repo_path))],
    )


def _match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _parse_duration(value: str) -> int:
    match = re.match(r"([\d.]+)\s*(ms|s)?", value)
    if not match:
        return 0
    amount = float(match.group(1))
    return int(amount * 1000) if match.group(2) == "s" else int(amount)
