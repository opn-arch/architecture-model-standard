"""SI&L instrumentation decorator (no-op when no store bound)."""
from __future__ import annotations

import functools
import time
from typing import Any, Callable

_STORE: "Any | None" = None  # OCA injects via bind_store()


def bind_store(store: Any) -> None:
    global _STORE
    _STORE = store


def instrumented(component_id: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _STORE is None:
                return fn(*args, **kwargs)
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                _STORE.emit(component_id, "invocation", "ok",
                            int((time.perf_counter() - t0) * 1000))
                return result
            except BaseException as e:
                _STORE.emit(component_id, "invocation", "error",
                            int((time.perf_counter() - t0) * 1000),
                            ref=type(e).__name__)
                raise
        wrapper.__sil_instrumented__ = True
        wrapper.__sil_component_id__ = component_id
        return wrapper
    return deco
