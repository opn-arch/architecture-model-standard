"""Tests for the specify pipeline stage — semantic interface naming."""

from architecture_model.pipeline.specify import _name_library_interface


def test_library_interface_uses_component_name():
    name = _name_library_interface(
        comp_id="COMP-1", comp_name="AnsiToWin32",
        public_symbols={"AnsiToWin32": "class AnsiToWin32", "wrap_stream": "wrap_stream(stream)"},
        module_stems=["ansitowin32"],
    )
    assert "COMP-1" not in name
    assert "AnsiToWin32" in name


def test_library_interface_dominant_class():
    name = _name_library_interface(
        comp_id="COMP-1", comp_name="Connections",
        public_symbols={"Connection": "class Connection", "connect": "connect()", "close": "close()"},
        module_stems=["connections"],
    )
    assert "Connection" in name


def test_library_interface_function_module():
    name = _name_library_interface(
        comp_id="COMP-2", comp_name="Ansi",
        public_symbols={"code": "code(n)", "set_title": "set_title(t)", "clear_screen": "clear_screen()"},
        module_stems=["ansi"],
    )
    assert "Ansi" in name or "ANSI" in name
