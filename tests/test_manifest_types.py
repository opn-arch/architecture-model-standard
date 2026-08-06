from architecture_model.manifest.types import (
    ModuleInfo, ClassInfo, FunctionInfo, ImportDetail, DecoratedFunction,
    InterfaceEdge, BlockManifest, SubFunctionEntry,
    ScanReport, MetricsResult, Manifest, ModuleStatus,
)


def test_module_info_creation():
    m = ModuleInfo(
        file="src/foo.py", name="Foo Module", docstring="Does foo things",
        functions=[FunctionInfo(name="bar", signature="bar(x: int) -> str")],
        imports=["os", "sys"], line_count=100,
        status=ModuleStatus.ACTIVE, classes=[],
        exports=["bar"], decorated_functions=[], imports_detailed=[],
        module_constants={"FOO": "'bar'"}, module_assignments={},
    )
    assert m.file == "src/foo.py"
    assert m.status == ModuleStatus.ACTIVE
    assert len(m.functions) == 1


def test_module_status_values():
    assert ModuleStatus.ACTIVE.value == "active"
    assert ModuleStatus.DORMANT.value == "dormant"
    assert ModuleStatus.MISSING.value == "missing"


def test_scan_report_success_rate():
    r = ScanReport()
    r.files_attempted = 10
    r.files_succeeded = 9
    r.files_failed = 1
    r.parse_errors = ["syntax error in bad.py"]
    assert r.success_rate == 0.9


def test_scan_report_empty():
    r = ScanReport()
    assert r.success_rate == 1.0


def test_interface_edge_creation():
    e = InterfaceEdge(source="a/b.py", target="c/d.py", import_path="c.d")
    assert e.source == "a/b.py"
    assert e.to_dict() == {"source": "a/b.py", "target": "c/d.py", "import_path": "c.d"}


def test_manifest_creation():
    m = Manifest(
        generated_at="2026-07-18T00:00:00", project_root="/tmp/test",
        metrics=MetricsResult(values={"total_python_files": 10}),
        functional_blocks={}, modules=[], interfaces=[],
        scan_report=ScanReport(),
    )
    assert m.metrics.values["total_python_files"] == 10


def test_manifest_to_dict_backward_compat():
    m = Manifest(
        generated_at="2026-07-18T00:00:00", project_root="/tmp/test",
        metrics=MetricsResult(values={"total_python_files": 10}),
        functional_blocks={}, modules=[], interfaces=[],
        scan_report=ScanReport(),
    )
    d = m.to_dict()
    assert "generated_at" in d
    assert "metrics" in d
    assert isinstance(d["metrics"], dict)
    assert "scan_report" not in d


def test_module_info_to_dict():
    m = ModuleInfo(
        file="x.py", name="X", docstring=None,
        functions=[FunctionInfo(name="f", signature="f() -> None")],
        imports=["os"], line_count=50, status=ModuleStatus.ACTIVE, classes=[],
    )
    d = m.to_dict()
    required_keys = {"file", "name", "docstring", "functions", "imports",
                     "line_count", "status", "classes", "exports",
                     "decorated_functions", "imports_detailed",
                     "module_constants", "module_assignments"}
    assert required_keys.issubset(d.keys())
    assert d["status"] == "active"


def test_block_manifest_to_dict():
    b = BlockManifest(name="Core", status="active", description_source="Core module")
    d = b.to_dict()
    assert d["name"] == "Core"
    assert d["sub_functions"] == []


def test_sub_function_entry_to_dict():
    sf = SubFunctionEntry(
        id="S1.1", name="Handler", file="handler.py",
        functions=["handle"], inputs=["request"], outputs=["response"],
        status="active", line_count=100,
    )
    d = sf.to_dict()
    assert d["id"] == "S1.1"
    assert d["functions"] == ["handle"]
