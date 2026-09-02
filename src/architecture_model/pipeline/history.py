"""Append-only structured history for pipeline execution."""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from copy import deepcopy
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
    source: str = "library"
    scope: str = ""
    parent_run_id: str | None = None
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
    source: str = "library"
    scope: str = ""
    parent_run_id: str | None = None
    stage: str = "observe"
    produced_functions: list[str] = field(default_factory=list)
    produced_classes: list[str] = field(default_factory=list)
    produced_routes: list[str] = field(default_factory=list)
    produced_constants: list[str] = field(default_factory=list)
    produced_entity_ids: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


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
    revision: str = "base"
    extraction_score: float | None = None
    final_model_score: float | None = None
    final_model_path: str = ""
    model_promoted: bool = False
    final_validation_issues: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for collection in (data["components"], data["modules"]):
            for item in collection:
                item["parent"] = item.get("parent_run_id")
        data.update({
            "timestamp": self.started_at,
            "invoked_by": self.invocation or self.source,
            "parent": self.parent_run_id,
            "artifacts": list(self.produced_artifacts),
        })
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineRunRecord":
        values = deepcopy(data)
        values.setdefault("started_at", values.get("timestamp", ""))
        values.setdefault("invocation", values.get("invoked_by", ""))
        values.setdefault("parent_run_id", values.get("parent"))
        values.setdefault("produced_artifacts", values.get("artifacts", []))
        for alias in ("timestamp", "invoked_by", "parent", "artifacts"):
            values.pop(alias, None)
        values["stages"] = [StageHistoryRecord(**item) for item in values.get("stages", [])]
        component_values = values.get("components", [])
        module_values = values.get("modules", [])
        for item in [*component_values, *module_values]:
            item.setdefault("parent_run_id", item.get("parent"))
            item.pop("parent", None)
        values["components"] = [ComponentHistoryRecord(**item) for item in component_values]
        values["modules"] = [ModuleHistoryRecord(**item) for item in module_values]
        return cls(**values)


def append_pipeline_history(repo_path: str | Path, record: PipelineRunRecord) -> Path:
    """Atomically append one serialized record under a process-safe file lock."""
    path = Path(repo_path) / ".architecture" / "pipeline-history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record.to_dict(), separators=(",", ":")) + "\n").encode()
    with _locked_history(path) as fd:
        _append_payload(fd, payload)
    return path


def serialize_artifact_path(path: str | Path, repo_path: str | Path) -> str:
    """Return a repo-relative artifact path, or an absolute path when external."""
    resolved_path = Path(path).resolve()
    resolved_repo = Path(repo_path).resolve()
    try:
        return str(resolved_path.relative_to(resolved_repo))
    except ValueError:
        return str(resolved_path)


def load_pipeline_history(repo_path: str | Path, limit: int = 50) -> list[PipelineRunRecord]:
    """Load newest valid records, skipping malformed lines."""
    path = Path(repo_path) / ".architecture" / "pipeline-history.jsonl"
    if limit <= 0:
        return []
    if not path.is_file():
        legacy = _load_legacy_report(Path(repo_path))
        return [legacy] if legacy is not None else []
    records: list[PipelineRunRecord] = []
    seen_run_ids: set[str] = set()
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        try:
            record = PipelineRunRecord.from_dict(json.loads(line))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if record.run_id in seen_run_ids:
            continue
        records.append(record)
        seen_run_ids.add(record.run_id)
        if len(records) >= limit:
            break
    if not records:
        legacy = _load_legacy_report(Path(repo_path))
        return [legacy] if legacy is not None else []
    return records


def finalize_pipeline_history(
    repo_path: str | Path,
    run_id: str,
    artifacts: list[str],
    final_validation: dict[str, Any] | None = None,
) -> PipelineRunRecord | None:
    """Append a final immutable revision using one locked merge transaction."""
    path = Path(repo_path) / ".architecture" / "pipeline-history.jsonl"
    if not path.is_file():
        return None
    with _locked_history(path) as fd:
        base = _latest_matching_record(_read_locked(fd), run_id)
        if base is None:
            return None
        base.produced_artifacts = list(dict.fromkeys([*base.produced_artifacts, *artifacts]))
        if final_validation:
            base.extraction_score = final_validation.get("extraction_score")
            base.final_model_score = final_validation.get("final_model_score")
            base.final_model_path = final_validation.get("final_model_path", "")
            base.model_promoted = bool(final_validation.get("promoted"))
            base.final_validation_issues = list(final_validation.get("issues", []))
        for component in base.components:
            safe_name = component.component_id.lower().replace(" ", "-")
            component.artifacts = list(dict.fromkeys([
                *component.artifacts,
                *(item for item in artifacts if item.endswith((
                    "functional.yaml", "structure.yaml", "relationships.yaml", "validation.json",
                    f"specs/{safe_name}.yaml", f"contracts/{safe_name}.yaml",
                ))),
            ]))
        for module in base.modules:
            module.artifacts = list(dict.fromkeys([
                *module.artifacts,
                *(item for item in artifacts if item.endswith("inventory.json")),
            ]))
        base.revision = "final"
        payload = (json.dumps(base.to_dict(), separators=(",", ":")) + "\n").encode()
        _append_payload(fd, payload)
        return base


@contextmanager
def _locked_history(path: Path):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        except ImportError:
            pass
        yield fd
    finally:
        os.close(fd)


def _append_payload(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        offset += os.write(fd, payload[offset:])
    os.fsync(fd)


def _read_locked(fd: int) -> str:
    size = os.fstat(fd).st_size
    return os.pread(fd, size, 0).decode("utf-8", errors="replace")


def _latest_matching_record(text: str, run_id: str) -> PipelineRunRecord | None:
    for line in reversed(text.splitlines()):
        try:
            record = PipelineRunRecord.from_dict(json.loads(line))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if record.run_id == run_id:
            return record
    return None


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
