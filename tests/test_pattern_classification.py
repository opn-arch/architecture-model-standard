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


def test_parser_pattern():
    """Parser pattern detected from parse/token/visitor names."""
    mod = ModuleInfo(
        file="parser.py", name="parser", docstring=None,
        functions=[FunctionInfo(name="parse", signature="(text: str) -> Node", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="tokenize", signature="(text: str) -> list", calls=[], docstring=None, raises=[])],
        imports=[], line_count=50, status=ModuleStatus.ACTIVE,
        classes=[], exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "parser"


def test_middleware_pattern():
    """Middleware pattern detected from middleware/intercept names."""
    mod = ModuleInfo(
        file="middleware.py", name="middleware", docstring=None,
        functions=[FunctionInfo(name="before_request", signature="(req) -> req", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="after_request", signature="(resp) -> resp", calls=[], docstring=None, raises=[])],
        imports=[], line_count=30, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="CORSMiddleware", bases=[], methods=["intercept"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "middleware"


def test_serializer_pattern():
    """Serializer pattern detected from to_json/from_json names."""
    mod = ModuleInfo(
        file="serializer.py", name="serializer", docstring=None,
        functions=[],
        imports=[], line_count=40, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="UserSerializer", bases=[], methods=["to_json", "from_json", "to_dict"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "serializer"


def test_cli_pattern():
    """CLI pattern detected from command/argument/option names."""
    mod = ModuleInfo(
        file="cli.py", name="cli", docstring=None,
        functions=[FunctionInfo(name="invoke", signature="(args) -> int", calls=[], docstring=None, raises=[])],
        imports=[], line_count=60, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="Command", bases=[], methods=["param", "argument", "option"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "cli"


def test_router_pattern():
    """Router pattern detected from route/endpoint/add_route names."""
    mod = ModuleInfo(
        file="router.py", name="router", docstring=None,
        functions=[FunctionInfo(name="add_route", signature="(path, handler) -> None", calls=[], docstring=None, raises=[])],
        imports=[], line_count=40, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="APIRouter", bases=[], methods=["include_router", "endpoint"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "router"


def test_validator_pattern():
    """Validator pattern detected from validate/is_valid names."""
    mod = ModuleInfo(
        file="validator.py", name="validator", docstring=None,
        functions=[FunctionInfo(name="validate", signature="(data: dict) -> bool", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="check_value", signature="(v) -> bool", calls=[], docstring=None, raises=[])],
        imports=[], line_count=30, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="SchemaValidator", bases=[], methods=["is_valid"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "validator"


def test_factory_pattern():
    """Factory pattern detected from factory/builder/from_config names."""
    mod = ModuleInfo(
        file="factory.py", name="factory", docstring=None,
        functions=[FunctionInfo(name="from_config", signature="(cfg: dict) -> Client", calls=[], docstring=None, raises=[])],
        imports=[], line_count=25, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="ClientFactory", bases=[], methods=["create_instance", "build_from"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "factory"


def test_decorator_pattern():
    """Decorator pattern detected from decorator/wraps/wrapper names."""
    mod = ModuleInfo(
        file="decorators.py", name="decorators", docstring=None,
        functions=[FunctionInfo(name="decorator", signature="(fn) -> fn", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="wraps", signature="(fn) -> fn", calls=[], docstring=None, raises=[])],
        imports=[], line_count=20, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="Wrapper", bases=[], methods=["before_call", "after_call"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "decorator-pattern"


def test_transport_pattern():
    """Transport pattern detected from transport/connection_pool names."""
    mod = ModuleInfo(
        file="transport.py", name="transport", docstring=None,
        functions=[],
        imports=[], line_count=80, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="AsyncTransport", bases=[], methods=["send_request", "open_connection", "close_connection"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "transport"


def test_plugin_pattern():
    """Plugin pattern detected from plugin/extension/load_plugin names."""
    mod = ModuleInfo(
        file="plugins.py", name="plugins", docstring=None,
        functions=[FunctionInfo(name="load_plugin", signature="(name: str) -> Plugin", calls=[], docstring=None, raises=[])],
        imports=[], line_count=40, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="PluginManager", bases=[], methods=["get_plugin", "hook_impl"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "plugin"


def test_pipeline_pattern():
    """Pipeline pattern detected from pipeline/stage/add_stage names."""
    mod = ModuleInfo(
        file="pipeline.py", name="pipeline", docstring=None,
        functions=[FunctionInfo(name="run_pipeline", signature="(data) -> result", calls=[], docstring=None, raises=[])],
        imports=[], line_count=50, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="Pipeline", bases=[], methods=["add_stage", "process_step"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "pipeline"


def test_formatter_pattern():
    """Formatter pattern detected from format_output/render/pretty_print names."""
    mod = ModuleInfo(
        file="formatter.py", name="formatter", docstring=None,
        functions=[FunctionInfo(name="format_output", signature="(data) -> str", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="pretty_print", signature="(obj) -> None", calls=[], docstring=None, raises=[])],
        imports=[], line_count=30, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="HelpFormatter", bases=[], methods=["render", "format_help"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == "formatter"


def test_no_pattern_for_generic_names():
    """Generic names like 'run', 'init', 'main' should not match any pattern."""
    mod = ModuleInfo(
        file="app.py", name="app", docstring=None,
        functions=[FunctionInfo(name="run", signature="() -> None", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="init", signature="() -> None", calls=[], docstring=None, raises=[]),
                   FunctionInfo(name="main", signature="() -> None", calls=[], docstring=None, raises=[])],
        imports=[], line_count=20, status=ModuleStatus.ACTIVE,
        classes=[ClassInfo(name="App", bases=[], methods=["start", "stop"],
                          is_abstract=False, decorators=[], attributes={})],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )
    assert _classify_pattern([mod]) == ""
