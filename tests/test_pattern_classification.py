"""Tests for generic pattern classification."""

from architecture_model.manifest.types import ModuleInfo, FunctionInfo, ClassInfo, ModuleStatus
from architecture_model.orchestration.auto_enrich import _classify_pattern


def test_generic_patterns_classify_correctly():
    """Generic code patterns should be detected by expanded catalog."""
    # Event bus pattern
    mod = ModuleInfo(
        file="events.py", name="events", docstring=None,
        functions=[], imports=[], line_count=30, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="EventBus", bases=[], methods=["on", "emit", "subscribe"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    pattern = _classify_pattern([mod])
    assert pattern == "event-handler", f"Got: {pattern}"

    # Worker pattern
    mod2 = ModuleInfo(
        file="worker.py", name="worker", docstring=None,
        functions=[], imports=[], line_count=30, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="Worker", bases=[], methods=["execute", "idle"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    pattern2 = _classify_pattern([mod2])
    assert pattern2 == "worker", f"Got: {pattern2}"

    # Handler pattern
    mod3 = ModuleInfo(
        file="plugin.py", name="plugin", docstring=None,
        functions=[FunctionInfo(name="handle_cleanup", signature="(payload: dict) -> dict", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="dispatch", signature="(cmd: str) -> None", calls=[], docstring=None, raises=[])],
        imports=[], line_count=20, status=ModuleStatus.ACTIVE,
        classes=[], exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    pattern3 = _classify_pattern([mod3])
    assert pattern3 == "handler", f"Got: {pattern3}"

    # Queue pattern
    mod4 = ModuleInfo(
        file="queue.py", name="queue", docstring=None,
        functions=[], imports=[], line_count=30, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="TaskQueue", bases=[], methods=["push", "pop", "peek"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    pattern4 = _classify_pattern([mod4])
    assert pattern4 == "queue", f"Got: {pattern4}"
