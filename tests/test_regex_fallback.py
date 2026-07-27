"""Tests for regex fallback scanner when ast.parse() fails."""

import tempfile
from pathlib import Path

from architecture_model.manifest.scanner import scan_file
from architecture_model.manifest.types import ModuleStatus


# Python 3.13 syntax that fails on 3.12: unparenthesized multi-except
PYTHON_313_SOURCE = '''\
"""Module with Python 3.13+ syntax."""

import asyncio
from typing import Any

SOME_CONSTANT = "hello"
TIMEOUT_SECONDS = 30

class EventBus:
    """Core event bus for dispatching events."""

    def __init__(self, loop):
        self._loop = loop

    async def fire(self, event_type: str, data: dict) -> None:
        """Fire an event."""
        pass

    async def listen(self, event_type: str) -> None:
        pass


class StateMachine(EventBus):
    """Manages entity states."""

    def set_state(self, entity_id: str, state: str) -> None:
        pass


def async_create_task(coro) -> asyncio.Task:
    """Create a task."""
    return asyncio.ensure_future(coro)


def setup_component(hass, config):
    """Set up a component."""
    try:
        result = config.get("key")
    except KeyError, ValueError:
        result = None
    return result
'''


class TestRegexFallback:
    """Tests that scan_file extracts useful info via regex when AST fails."""

    def _write_and_scan(self, source: str) -> "ModuleInfo":
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            filepath = root / "module.py"
            filepath.write_text(source)
            return scan_file(root, filepath)

    def test_extracts_classes_on_syntax_error(self):
        """Regex fallback finds class definitions."""
        result = self._write_and_scan(PYTHON_313_SOURCE)
        class_names = [c.name for c in result.classes]
        assert "EventBus" in class_names
        assert "StateMachine" in class_names

    def test_extracts_functions_on_syntax_error(self):
        """Regex fallback finds function definitions."""
        result = self._write_and_scan(PYTHON_313_SOURCE)
        func_names = [f.name for f in result.functions]
        assert "async_create_task" in func_names
        assert "setup_component" in func_names

    def test_extracts_imports_on_syntax_error(self):
        """Regex fallback finds import statements."""
        result = self._write_and_scan(PYTHON_313_SOURCE)
        assert "asyncio" in result.imports
        assert "typing" in result.imports

    def test_status_is_not_missing(self):
        """Files with syntax errors should NOT be MISSING."""
        result = self._write_and_scan(PYTHON_313_SOURCE)
        assert result.status != ModuleStatus.MISSING

    def test_extracts_bases(self):
        """Regex fallback captures inheritance."""
        result = self._write_and_scan(PYTHON_313_SOURCE)
        sm = next(c for c in result.classes if c.name == "StateMachine")
        assert "EventBus" in sm.bases

    def test_extracts_docstring(self):
        """Regex fallback captures module docstring."""
        result = self._write_and_scan(PYTHON_313_SOURCE)
        assert result.docstring == "Module with Python 3.13+ syntax."
