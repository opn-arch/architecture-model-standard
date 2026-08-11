"""File-based pipeline cache for stage-by-stage MCP execution.

Serializes StageResult objects to JSON files in .architecture/pipeline-cache/
so the MCP orchestrator can resume between stage invocations.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

from architecture_model.pipeline.protocol import (
    Diagnostic,
    Evidence,
    LLMCallRecord,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)


def _serialize(obj: Any) -> Any:
    """Recursively serialize dataclasses and Path objects to JSON-safe dicts."""
    if obj is None:
        return None
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        result["__dataclass__"] = type(obj).__qualname__
        result["__module__"] = type(obj).__module__
        for f in fields(obj):
            result[f.name] = _serialize(getattr(obj, f.name))
        return result
    # Fallback: try str
    return str(obj)


def _get_output_class(stage_name: str) -> type | None:
    """Get the output dataclass for a given stage name."""
    _stage_output_types: dict[str, tuple[str, str]] = {
        "observe": ("architecture_model.pipeline.observe_types", "Inventory"),
        "infer": ("architecture_model.pipeline.infer_types", "InferResult"),
        "allocate": ("architecture_model.pipeline.allocate_types", "AllocateResult"),
        "relate": ("architecture_model.pipeline.relate_types", "RelateResult"),
        "specify": ("architecture_model.pipeline.specify_types", "SpecifyResult"),
        "contract": ("architecture_model.pipeline.contract_types", "ContractResult"),
        "validate": ("architecture_model.pipeline.validate_types", "ValidateResult"),
        "decompose": ("architecture_model.pipeline.decompose_types", "DecomposeResult"),
        "synthesize": ("architecture_model.pipeline.synthesize_types", "SynthesizeResult"),
        "emit": ("architecture_model.pipeline.emit_types", "EmitResult"),
    }
    entry = _stage_output_types.get(stage_name)
    if not entry:
        return None
    import importlib
    mod = importlib.import_module(entry[0])
    return getattr(mod, entry[1], None)


def _deserialize(data: Any, target_type: type | None = None) -> Any:
    """Recursively deserialize JSON data back into dataclasses."""
    if data is None:
        return None
    if isinstance(data, (str, int, float, bool)):
        return data
    if isinstance(data, list):
        return [_deserialize(item) for item in data]
    if isinstance(data, dict):
        if "__dataclass__" in data:
            return _reconstruct_dataclass(data)
        return {k: _deserialize(v) for k, v in data.items()}
    return data


def _reconstruct_dataclass(data: dict) -> Any:
    """Reconstruct a dataclass from serialized dict with __dataclass__ marker."""
    import importlib

    cls_name = data["__dataclass__"]
    mod_name = data["__module__"]

    try:
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
    except (ImportError, AttributeError):
        # Can't reconstruct — return as plain dict
        return {k: _deserialize(v) for k, v in data.items() if not k.startswith("__")}

    if not is_dataclass(cls):
        return {k: _deserialize(v) for k, v in data.items() if not k.startswith("__")}

    kwargs = {}
    for f in fields(cls):
        if f.name in data:
            val = data[f.name]
            # Handle Path fields
            if f.type in ("Path", "Path | None") and isinstance(val, str):
                kwargs[f.name] = Path(val)
            else:
                kwargs[f.name] = _deserialize(val)
    return cls(**kwargs)


def _deserialize_stage_result(data: dict, stage_name: str) -> StageResult:
    """Deserialize a StageResult from JSON dict."""
    # Reconstruct quality
    q_data = data.get("quality", {})
    quality = QualityMetrics(
        score=q_data.get("score", 0.0),
        sub_scores=q_data.get("sub_scores", {}),
        thresholds=q_data.get("thresholds", {}),
        llm_prompt=q_data.get("llm_prompt", ""),
    )

    # Reconstruct diagnostics
    diagnostics = [
        Diagnostic(**d) if isinstance(d, dict) and "__dataclass__" not in d
        else _deserialize(d)
        for d in data.get("diagnostics", [])
    ]

    # Reconstruct uncertainties
    uncertainties = [
        Uncertainty(**u) if isinstance(u, dict) and "__dataclass__" not in u
        else _deserialize(u)
        for u in data.get("uncertainties", [])
    ]

    # Reconstruct output
    output_data = data.get("output")
    if isinstance(output_data, dict) and "__dataclass__" in output_data:
        output = _reconstruct_dataclass(output_data)
    else:
        output = _deserialize(output_data)

    return StageResult(
        output=output,
        quality=quality,
        diagnostics=diagnostics,
        uncertainties=uncertainties,
        input_hash=data.get("input_hash", ""),
        duration_ms=data.get("duration_ms", 0),
        version=data.get("version", "1.0"),
    )


class PipelineCache:
    """File-based cache for pipeline stage results.

    Layout:
        .architecture/pipeline-cache/
            meta.json          — run metadata (timestamp, repo, stages completed)
            observe.json       — serialized StageResult for observe
            infer.json         — serialized StageResult for infer
            ...
            llm_calls.json     — accumulated LLM call records
    """

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def exists(self) -> bool:
        return self.cache_dir.exists() and (self.cache_dir / "meta.json").exists()

    def save_stage(self, stage_name: str, result: StageResult) -> None:
        """Persist a single stage result to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / f"{stage_name}.json"
        data = _serialize(result)
        path.write_text(json.dumps(data, indent=2, default=str))
        self._update_meta(stage_name)

    def load_stage(self, stage_name: str) -> StageResult | None:
        """Load a cached stage result from disk."""
        path = self.cache_dir / f"{stage_name}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return _deserialize_stage_result(data, stage_name)

    def load_all(self) -> dict[str, StageResult]:
        """Load all cached stage results."""
        results: dict[str, StageResult] = {}
        if not self.exists():
            return results
        meta = self._read_meta()
        for stage_name in meta.get("stages_completed", []):
            result = self.load_stage(stage_name)
            if result is not None:
                results[stage_name] = result
        return results

    def save_llm_calls(self, calls: list[LLMCallRecord]) -> None:
        """Persist LLM call records."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / "llm_calls.json"
        data = [_serialize(c) for c in calls]
        path.write_text(json.dumps(data, indent=2))

    def load_llm_calls(self) -> list[LLMCallRecord]:
        """Load persisted LLM call records."""
        path = self.cache_dir / "llm_calls.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text())
        calls = []
        for item in data:
            if isinstance(item, dict):
                # Strip dataclass markers for simple reconstruction
                clean = {k: v for k, v in item.items() if not k.startswith("__")}
                calls.append(LLMCallRecord(**clean))
        return calls

    def clear(self) -> None:
        """Remove all cached data."""
        if self.cache_dir.exists():
            import shutil
            shutil.rmtree(self.cache_dir)

    def _update_meta(self, stage_name: str) -> None:
        """Update meta.json with completed stage."""
        meta = self._read_meta()
        stages = meta.get("stages_completed", [])
        if stage_name not in stages:
            stages.append(stage_name)
        meta["stages_completed"] = stages
        meta["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        (self.cache_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    def _read_meta(self) -> dict:
        meta_path = self.cache_dir / "meta.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())
        return {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "stages_completed": []}

    def hydrate_context(self, ctx: PipelineContext) -> list[str]:
        """Load all cached results into a PipelineContext. Returns stage names loaded."""
        results = self.load_all()
        for name, result in results.items():
            ctx.cache[name] = result
        ctx.llm_calls = self.load_llm_calls()
        return list(results.keys())
