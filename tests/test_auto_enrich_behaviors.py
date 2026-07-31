"""Tests for behavioral auto-enrichment from manifest."""

from dataclasses import dataclass, field

import pytest

from architecture_model.core.types import Behavior, Status
from architecture_model.manifest.types import (
    DecoratedFunction,
    FunctionInfo,
    ModuleInfo,
    ModuleStatus,
    Manifest,
)
from architecture_model.orchestration.auto_enrich import enrich_behaviors_from_manifest


def _make_manifest(modules: list[ModuleInfo]) -> Manifest:
    """Create a minimal Manifest with given modules."""
    return Manifest(
        generated_at="2024-01-01T00:00:00",
        project_root="/tmp/test",
        metrics=None,  # type: ignore
        functional_blocks={},
        modules=modules,
        interfaces=[],
    )


def _make_behavior(name: str, source_file: str, **kwargs) -> Behavior:
    """Create a Behavior with defaults."""
    return Behavior(
        id=f"BEH-{name}",
        name=name,
        status=Status.ACTIVE,
        source_file=source_file,
        **kwargs,
    )


def _make_module(
    file: str,
    functions: list[FunctionInfo] | None = None,
    decorated_functions: list[DecoratedFunction] | None = None,
) -> ModuleInfo:
    return ModuleInfo(
        file=file,
        name=file.replace("/", ".").replace(".py", ""),
        docstring=None,
        functions=functions or [],
        imports=[],
        line_count=50,
        status=ModuleStatus.ACTIVE,
        classes=[],
        decorated_functions=decorated_functions or [],
    )


class _FakeModel:
    def __init__(self, behaviors: list[Behavior]):
        self.entities = {"behaviors": behaviors}


class TestTriggerExtraction:
    def test_extracts_trigger_from_route_decorator(self):
        behavior = _make_behavior("handle_request", "src/api.py")
        module = _make_module(
            "src/api.py",
            functions=[FunctionInfo(name="handle_request", signature="(req)", calls=["validate", "save"])],
            decorated_functions=[
                DecoratedFunction(name="handle_request", decorators=["app.route('/users')"])
            ],
        )
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert behavior.trigger == "app.route('/users')"

    def test_no_overwrite_existing_trigger(self):
        behavior = _make_behavior("handle_request", "src/api.py", trigger="manual trigger")
        module = _make_module(
            "src/api.py",
            functions=[FunctionInfo(name="handle_request", signature="(req)", calls=[])],
            decorated_functions=[
                DecoratedFunction(name="handle_request", decorators=["app.route('/users')"])
            ],
        )
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert behavior.trigger == "manual trigger"

    def test_extracts_event_handler_decorator(self):
        behavior = _make_behavior("on_payment", "src/events.py")
        module = _make_module(
            "src/events.py",
            functions=[FunctionInfo(name="on_payment", signature="(event)", calls=[])],
            decorated_functions=[
                DecoratedFunction(name="on_payment", decorators=["event_handler('payment.created')"])
            ],
        )
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert "event_handler" in behavior.trigger


class TestStepsExtraction:
    def test_extracts_steps_from_call_graph(self):
        behavior = _make_behavior("process_order", "src/orders.py")
        module = _make_module(
            "src/orders.py",
            functions=[
                FunctionInfo(
                    name="process_order",
                    signature="(order)",
                    calls=["validate_order", "charge_payment", "send_confirmation"],
                )
            ],
        )
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert behavior.steps == ["validate_order", "charge_payment", "send_confirmation"]

    def test_no_overwrite_existing_steps(self):
        behavior = _make_behavior("process_order", "src/orders.py", steps=["existing_step"])
        module = _make_module(
            "src/orders.py",
            functions=[
                FunctionInfo(name="process_order", signature="(order)", calls=["new_step"])
            ],
        )
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert behavior.steps == ["existing_step"]


class TestErrorConditions:
    def test_extracts_postconditions_from_raises(self):
        behavior = _make_behavior("process_order", "src/orders.py")
        module = _make_module(
            "src/orders.py",
            functions=[
                FunctionInfo(
                    name="process_order",
                    signature="(order)",
                    calls=[],
                    raises=["ValueError", "PaymentError"],
                )
            ],
        )
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert behavior.postconditions == ["raises ValueError", "raises PaymentError"]

    def test_no_overwrite_existing_postconditions(self):
        behavior = _make_behavior(
            "process_order", "src/orders.py", postconditions=["order is saved"]
        )
        module = _make_module(
            "src/orders.py",
            functions=[
                FunctionInfo(name="process_order", signature="(order)", calls=[], raises=["ValueError"])
            ],
        )
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert behavior.postconditions == ["order is saved"]


class TestNoMatch:
    def test_no_source_file_skips(self):
        behavior = _make_behavior("mystery", "src/unknown.py")
        module = _make_module("src/other.py")
        model = _FakeModel([behavior])
        enrich_behaviors_from_manifest(model, _make_manifest([module]))
        assert behavior.trigger == ""
        assert behavior.steps == []
