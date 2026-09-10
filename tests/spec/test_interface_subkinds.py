"""Interface.subkind + metadata schema — Phase 4-A Task 11.

Adds ``subkind`` (softly enumerated) and ``metadata`` (freeform dict)
to Interface entities so extracted CLI/HTTP/plugin endpoints (Tasks
8-10) can be promoted into Interface entities and consumed by the
reference-doc projectors (Tasks 13-15).

Validator warns when ``subkind == "cli_command"`` but ``metadata.args``
is missing/empty — the extractor should always populate arg specs, so
an unpopulated cli_command interface is likely a partial model.
"""

from __future__ import annotations

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import Interface
from architecture_model.core.validator import validate_model


def _model_with_interface(interface_dict: dict):
    return _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "iface"},
            "entities": {
                "interfaces": [interface_dict],
            },
        }
    )


def test_interface_dataclass_has_subkind_and_metadata():
    iface = Interface(id="IF-1", name="X", status="ACTIVE")
    assert iface.subkind == ""
    assert iface.metadata == {}


def test_parser_reads_subkind_and_metadata():
    model = _model_with_interface(
        {
            "id": "IF-1",
            "name": "hello",
            "subkind": "cli_command",
            "metadata": {
                "framework": "click",
                "args": [{"name": "--name", "required": False}],
            },
        }
    )
    iface = model.entities.interfaces[0]
    assert iface.subkind == "cli_command"
    assert iface.metadata["framework"] == "click"
    assert isinstance(iface.metadata["args"], list)


def test_parser_default_subkind_is_empty_string():
    model = _model_with_interface({"id": "IF-1", "name": "x"})
    assert model.entities.interfaces[0].subkind == ""


def test_validator_warns_cli_command_without_args():
    model = _model_with_interface(
        {
            "id": "IF-BAD",
            "name": "no-args",
            "subkind": "cli_command",
            "metadata": {"framework": "click"},
        }
    )
    result = validate_model(model)
    codes_or_messages = [
        (i.code or "") + " " + (i.message or "") for i in result.issues
    ]
    joined = " | ".join(codes_or_messages).lower()
    assert "cli_command" in joined and "args" in joined


def test_validator_ok_for_cli_command_with_args():
    model = _model_with_interface(
        {
            "id": "IF-OK",
            "name": "hello",
            "subkind": "cli_command",
            "metadata": {
                "framework": "click",
                "args": [{"name": "--name"}],
            },
        }
    )
    result = validate_model(model)
    joined = " | ".join(
        (i.code or "") + " " + (i.message or "") for i in result.issues
    ).lower()
    # Should NOT flag args-missing for IF-OK specifically.
    assert not (
        "if-ok" in joined and "args" in joined and "cli_command" in joined
    )


def test_schema_accepts_all_documented_subkinds():
    for subkind in [
        "api",
        "cli_command",
        "http_route",
        "plugin_hook",
        "event",
        "data",
        "message",
    ]:
        model = _model_with_interface(
            {
                "id": f"IF-{subkind}",
                "name": subkind,
                "subkind": subkind,
                "metadata": {"args": [{"name": "x"}]} if subkind == "cli_command" else {},
            }
        )
        result = validate_model(model)
        # Schema validation should not reject any of these subkinds.
        schema_errors = [
            i for i in result.issues if (i.code or "").startswith("schema")
        ]
        assert not schema_errors, f"{subkind}: {schema_errors}"
