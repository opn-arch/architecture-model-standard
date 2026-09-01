"""Tests for SE field derivation in the infer pipeline stage.

Tests that infer auto-populates intent, goals, failure_modes, and monitored
fields on InferredCapability from source code patterns.
"""

from pathlib import Path

import pytest

from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.infer_types import InferredCapability
from architecture_model.pipeline.observe_types import (
    FunctionRecord,
    ClassRecord,
    Inventory,
    ModuleRecord,
)
from architecture_model.pipeline.protocol import PipelineContext, StageResult


def _make_context(inventory: Inventory) -> PipelineContext:
    """Create a PipelineContext with a pre-loaded observe result."""
    from architecture_model.pipeline.protocol import QualityMetrics

    ctx = PipelineContext(repo_path=Path("/fake"), output_dir=Path("/fake/out"))
    ctx.cache["observe"] = StageResult(
        output=inventory,
        quality=QualityMetrics(score=100),
    )
    return ctx


def _run_infer(inventory: Inventory) -> list[InferredCapability]:
    """Run the infer stage and return capabilities."""
    ctx = _make_context(inventory)
    result = InferStage().run(ctx)
    return result.output.capabilities


class TestIntent:
    """Intent should be derived from module docstrings or module name."""

    def test_intent_from_module_docstring(self):
        mod = ModuleRecord(
            path=Path("src/myapp/ingestion.py"),
            docstring="Handles data ingestion from external sources.",
            functions=[
                FunctionRecord(name="ingest", signature="(data)", body_hint="..."),
                FunctionRecord(name="validate", signature="(data)", body_hint="..."),
                FunctionRecord(name="transform", signature="(data)", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert hasattr(cap, "intent")
        assert "ingestion" in cap.intent.lower() or "external sources" in cap.intent.lower()

    def test_intent_fallback_from_module_name(self):
        mod = ModuleRecord(
            path=Path("src/myapp/validation.py"),
            docstring=None,
            functions=[
                FunctionRecord(name="check_input", signature="(x)", body_hint="..."),
                FunctionRecord(name="check_output", signature="(x)", body_hint="..."),
                FunctionRecord(name="verify", signature="(x)", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert hasattr(cap, "intent")
        assert cap.intent  # non-empty
        assert "validation" in cap.intent.lower()


class TestGoals:
    """Goals should be derived from public function names."""

    def test_goals_from_function_names(self):
        mod = ModuleRecord(
            path=Path("src/myapp/processor.py"),
            functions=[
                FunctionRecord(name="validate_input", signature="(data)", body_hint="..."),
                FunctionRecord(name="transform_data", signature="(data)", body_hint="..."),
                FunctionRecord(name="export_results", signature="(data)", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert hasattr(cap, "goals")
        assert isinstance(cap.goals, list)
        assert len(cap.goals) >= 3
        goals_lower = [g.lower() for g in cap.goals]
        assert any("validate" in g for g in goals_lower)
        assert any("transform" in g for g in goals_lower)
        assert any("export" in g for g in goals_lower)

    def test_goals_skip_private_functions(self):
        mod = ModuleRecord(
            path=Path("src/myapp/service.py"),
            functions=[
                FunctionRecord(name="process", signature="()", body_hint="..."),
                FunctionRecord(name="_helper", signature="()", body_hint="..."),
                FunctionRecord(name="run", signature="()", body_hint="..."),
                FunctionRecord(name="execute", signature="()", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        goals_lower = [g.lower() for g in cap.goals]
        assert not any("helper" in g for g in goals_lower)


class TestFailureModes:
    """Failure modes from exception types and error-related function names."""

    def test_failure_modes_from_exception_types(self):
        mod = ModuleRecord(
            path=Path("src/myapp/handler.py"),
            functions=[
                FunctionRecord(
                    name="process",
                    signature="(data)",
                    body_hint="raise ValueError('bad input')",
                ),
                FunctionRecord(
                    name="connect",
                    signature="()",
                    body_hint="raise TimeoutError('connection timed out')",
                ),
                FunctionRecord(
                    name="save",
                    signature="(data)",
                    body_hint="raise PermissionError('access denied')",
                ),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert hasattr(cap, "failure_modes")
        assert isinstance(cap.failure_modes, list)
        fm_lower = [f.lower() for f in cap.failure_modes]
        assert any("valueerror" in f or "bad input" in f for f in fm_lower)
        assert any("timeouterror" in f or "timed out" in f for f in fm_lower)

    def test_failure_modes_from_error_function_names(self):
        mod = ModuleRecord(
            path=Path("src/myapp/resilience.py"),
            functions=[
                FunctionRecord(name="retry_operation", signature="()", body_hint="..."),
                FunctionRecord(name="handle_failure", signature="()", body_hint="..."),
                FunctionRecord(name="fallback_handler", signature="()", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert isinstance(cap.failure_modes, list)
        fm_lower = [f.lower() for f in cap.failure_modes]
        assert any("retry" in f for f in fm_lower)


class TestMonitored:
    """Monitored should detect logging and metrics patterns."""

    def test_monitored_from_logging_imports(self):
        mod = ModuleRecord(
            path=Path("src/myapp/worker.py"),
            imports=["logging", "os"],
            functions=[
                FunctionRecord(name="do_work", signature="()", body_hint="..."),
                FunctionRecord(name="process", signature="()", body_hint="..."),
                FunctionRecord(name="run", signature="()", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert hasattr(cap, "monitored")
        assert isinstance(cap.monitored, list)
        assert any("logging" in m.lower() for m in cap.monitored)

    def test_monitored_from_metrics_imports(self):
        mod = ModuleRecord(
            path=Path("src/myapp/metrics_collector.py"),
            imports=["prometheus_client", "time"],
            functions=[
                FunctionRecord(name="collect", signature="()", body_hint="..."),
                FunctionRecord(name="report", signature="()", body_hint="..."),
                FunctionRecord(name="aggregate", signature="()", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert isinstance(cap.monitored, list)
        assert any("prometheus" in m.lower() for m in cap.monitored)

    def test_monitored_from_function_names(self):
        mod = ModuleRecord(
            path=Path("src/myapp/telemetry.py"),
            functions=[
                FunctionRecord(name="log_event", signature="()", body_hint="..."),
                FunctionRecord(name="track_metric", signature="()", body_hint="..."),
                FunctionRecord(name="process", signature="()", body_hint="..."),
            ],
        )
        caps = _run_infer(Inventory(modules=[mod]))
        assert len(caps) >= 1
        cap = caps[0]
        assert isinstance(cap.monitored, list)
        assert len(cap.monitored) >= 1
