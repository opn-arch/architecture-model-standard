"""Per-function monitoring infrastructure.

Provides a @monitored decorator that collects timing, input/output metrics,
and quality scores into a thread-local collector. The collector is drained
by the caller (e.g., opencode-arch MCP tools) after each operation.

Usage:
    from architecture_model.monitoring import monitored, get_collector

    @monitored(module="orchestration.pipeline",
               quality=lambda r: {"blocks": len(r.manifests)})
    def run_pipeline(project_root, *, deep=False):
        ...

    # After calling:
    metrics = get_collector().drain()
"""
from __future__ import annotations

import functools
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class FunctionMetrics:
    """Metrics collected from a single function invocation."""
    function: str
    module: str
    time_ms: float = 0.0
    quality_scores: dict[str, Any] = field(default_factory=dict)
    input_metrics: dict[str, Any] = field(default_factory=dict)
    output_metrics: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Thread-safe accumulator for function metrics."""

    def __init__(self):
        self.metrics: list[FunctionMetrics] = []
        self._lock = threading.Lock()

    def record(self, m: FunctionMetrics) -> None:
        with self._lock:
            self.metrics.append(m)

    def drain(self) -> list[FunctionMetrics]:
        """Return all collected metrics and clear the buffer."""
        with self._lock:
            result = self.metrics[:]
            self.metrics.clear()
            return result


_thread_local = threading.local()


def get_collector() -> MetricsCollector:
    """Get the thread-local metrics collector."""
    if not hasattr(_thread_local, "collector"):
        _thread_local.collector = MetricsCollector()
    return _thread_local.collector


def monitored(
    module: str,
    *,
    quality: Callable[[Any], dict[str, Any]] | None = None,
    inputs: Callable[[tuple, dict], dict[str, Any]] | None = None,
    outputs: Callable[[Any], dict[str, Any]] | None = None,
) -> Callable:
    """Decorator that records function metrics to the thread-local collector.

    Args:
        module: Dotted module path (e.g., "orchestration.pipeline")
        quality: Extracts quality scores from the return value
        inputs: Extracts input metrics from (args, kwargs)
        outputs: Extracts output metrics from the return value
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            input_m = {}
            if inputs:
                try:
                    input_m = inputs(args, kwargs)
                except Exception:
                    pass

            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            quality_m = {}
            if quality:
                try:
                    quality_m = quality(result)
                except Exception:
                    pass

            output_m = {}
            if outputs:
                try:
                    output_m = outputs(result)
                except Exception:
                    pass

            m = FunctionMetrics(
                function=fn.__name__,
                module=module,
                time_ms=elapsed_ms,
                quality_scores=quality_m,
                input_metrics=input_m,
                output_metrics=output_m,
            )
            get_collector().record(m)
            return result

        return wrapper
    return decorator
