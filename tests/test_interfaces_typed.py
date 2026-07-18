"""Tests for typed derive_interfaces()."""

from pathlib import Path

from architecture_model.manifest.interfaces import derive_interfaces
from architecture_model.manifest.types import InterfaceEdge, ModuleInfo, ModuleStatus


def test_derive_interfaces_returns_typed():
    modules = [
        ModuleInfo(
            file="pkg/a.py", name="A", docstring=None,
            functions=[], imports=["pkg.b"], line_count=10,
            status=ModuleStatus.ACTIVE, classes=[],
        ),
        ModuleInfo(
            file="pkg/b.py", name="B", docstring=None,
            functions=[], imports=[], line_count=10,
            status=ModuleStatus.ACTIVE, classes=[],
        ),
    ]
    result = derive_interfaces(modules, Path("/fake"))
    assert all(isinstance(e, InterfaceEdge) for e in result)
    assert len(result) >= 1
    assert result[0].source == "pkg/a.py"
    assert result[0].target == "pkg/b.py"
    assert result[0].import_path == "pkg.b"


def test_derive_interfaces_no_self_reference():
    modules = [
        ModuleInfo(
            file="pkg/a.py", name="A", docstring=None,
            functions=[], imports=["pkg.a"], line_count=10,
            status=ModuleStatus.ACTIVE, classes=[],
        ),
    ]
    result = derive_interfaces(modules, Path("/fake"))
    assert len(result) == 0


def test_derive_interfaces_deduplicates():
    modules = [
        ModuleInfo(
            file="pkg/a.py", name="A", docstring=None,
            functions=[], imports=["pkg.b", "pkg.b.sub"], line_count=10,
            status=ModuleStatus.ACTIVE, classes=[],
        ),
        ModuleInfo(
            file="pkg/b.py", name="B", docstring=None,
            functions=[], imports=[], line_count=10,
            status=ModuleStatus.ACTIVE, classes=[],
        ),
    ]
    result = derive_interfaces(modules, Path("/fake"))
    # Should deduplicate the (a -> b) edge
    assert len(result) == 1
