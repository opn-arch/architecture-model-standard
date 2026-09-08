import asyncio
import pytest
from architecture_model.sil.decorators import instrumented, bind_store


class RecordingStore:
    def __init__(self):
        self.events = []
    def emit(self, component_id, kind, outcome, duration_ms, ref=None):
        self.events.append({
            "component_id": component_id,
            "kind": kind,
            "outcome": outcome,
            "duration_ms": duration_ms,
            "ref": ref,
        })


@pytest.fixture
def store():
    s = RecordingStore()
    bind_store(s)
    yield s
    bind_store(None)


def test_async_ok_records_after_await(store):
    @instrumented("stage:async_ok")
    async def work():
        await asyncio.sleep(0.02)
        return 42

    result = asyncio.run(work())
    assert result == 42
    assert len(store.events) == 1
    e = store.events[0]
    assert e["component_id"] == "stage:async_ok"
    assert e["outcome"] == "ok"
    # Recorded latency reflects the actual awaited execution, not near-zero.
    assert e["duration_ms"] >= 15


def test_async_error_records_error_and_reraises(store):
    @instrumented("stage:async_boom")
    async def boom():
        await asyncio.sleep(0.005)
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        asyncio.run(boom())
    assert len(store.events) == 1
    e = store.events[0]
    assert e["outcome"] == "error"
    assert e["ref"] == "ValueError"


def test_async_wrapper_preserves_coroutine_semantics():
    """The decorated function must still be recognized as a coroutine function
    so that async frameworks (asyncio, anyio, MCP async dispatch) treat it
    correctly."""
    import inspect

    @instrumented("stage:asyncish")
    async def work():
        return 1

    assert inspect.iscoroutinefunction(work)
    assert getattr(work, "__sil_instrumented__", False)
    assert getattr(work, "__sil_component_id__", None) == "stage:asyncish"


def test_sync_no_store_still_transparent():
    """Regression: no-op path (no store) still works for sync functions."""
    bind_store(None)
    @instrumented("stage:sync_x")
    def add(a, b): return a + b
    assert add(2, 3) == 5
