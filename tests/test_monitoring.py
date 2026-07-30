"""Test monitoring infrastructure."""
import time
from architecture_model.monitoring import (
    FunctionMetrics,
    MetricsCollector,
    get_collector,
    monitored,
)


def test_function_metrics_dataclass():
    m = FunctionMetrics(
        function="test_fn",
        module="test_module",
        time_ms=42.5,
        quality_scores={"score": 95},
        input_metrics={"count": 10},
        output_metrics={"size": 200},
    )
    assert m.function == "test_fn"
    assert m.time_ms == 42.5
    assert m.quality_scores["score"] == 95


def test_collector_accumulates_metrics():
    collector = MetricsCollector()
    m1 = FunctionMetrics(function="fn1", module="mod", time_ms=10.0)
    m2 = FunctionMetrics(function="fn2", module="mod", time_ms=20.0)
    collector.record(m1)
    collector.record(m2)
    assert len(collector.metrics) == 2
    drained = collector.drain()
    assert len(drained) == 2
    assert len(collector.metrics) == 0


def test_get_collector_returns_thread_local():
    c1 = get_collector()
    c2 = get_collector()
    assert c1 is c2


def test_monitored_decorator_records_timing():
    collector = get_collector()
    collector.drain()

    @monitored(module="test")
    def slow_fn(x):
        time.sleep(0.01)
        return x * 2

    result = slow_fn(5)
    assert result == 10
    metrics = collector.drain()
    assert len(metrics) == 1
    assert metrics[0].function == "slow_fn"
    assert metrics[0].time_ms >= 9


def test_monitored_with_quality_extractor():
    collector = get_collector()
    collector.drain()

    @monitored(module="test", quality=lambda result: {"leaf_count": len(result)})
    def get_items():
        return [1, 2, 3]

    result = get_items()
    assert result == [1, 2, 3]
    metrics = collector.drain()
    assert metrics[0].quality_scores == {"leaf_count": 3}


def test_monitored_with_input_extractor():
    collector = get_collector()
    collector.drain()

    @monitored(module="test", inputs=lambda args, kwargs: {"n": args[0]})
    def square(n):
        return n * n

    assert square(4) == 16
    metrics = collector.drain()
    assert metrics[0].input_metrics == {"n": 4}
