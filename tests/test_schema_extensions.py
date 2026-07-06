"""Tests for Phase 1.1 schema extensions: Constant, FunctionSignature, TestContract."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from architecture_model.core.parser import _parse_raw, dump_model, load_model, save_model
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    Constant,
    FunctionSignature,
    Status,
    TestContract,
)


# ---------------------------------------------------------------------------
# Unit tests: dataclass construction
# ---------------------------------------------------------------------------


class TestConstantDataclass:
    """Tests for the Constant dataclass."""

    def test_create_with_required_fields(self):
        c = Constant(name="BLACK", value="30")
        assert c.name == "BLACK"
        assert c.value == "30"
        assert c.context == ""

    def test_create_with_context(self):
        c = Constant(name="BLACK", value="30", context="class attribute of AnsiFore")
        assert c.context == "class attribute of AnsiFore"


class TestFunctionSignatureDataclass:
    """Tests for the FunctionSignature dataclass."""

    def test_create_with_required_fields(self):
        sig = FunctionSignature(name="code_to_chars")
        assert sig.name == "code_to_chars"
        assert sig.params == []
        assert sig.returns == ""
        assert sig.decorators == []
        assert sig.body_hint == ""

    def test_create_with_all_fields(self):
        sig = FunctionSignature(
            name="code_to_chars",
            params=["code: int"],
            returns="str",
            decorators=["staticmethod"],
            body_hint="Convert ANSI code integer to escape sequence string",
        )
        assert sig.params == ["code: int"]
        assert sig.returns == "str"
        assert sig.decorators == ["staticmethod"]
        assert sig.body_hint == "Convert ANSI code integer to escape sequence string"


class TestTestContractDataclass:
    """Tests for the TestContract dataclass."""

    def test_create_with_required_fields(self):
        tc = TestContract(
            test_file="ansi_test.py",
            test_method="testForeAttributes",
            assertion="Fore.BLACK == '\\033[30m'",
        )
        assert tc.test_file == "ansi_test.py"
        assert tc.test_method == "testForeAttributes"
        assert tc.assertion == "Fore.BLACK == '\\033[30m'"
        assert tc.contract_type == ""

    def test_create_with_contract_type(self):
        tc = TestContract(
            test_file="ansi_test.py",
            test_method="testForeAttributes",
            assertion="Fore.BLACK == '\\033[30m'",
            contract_type="value_equality",
        )
        assert tc.contract_type == "value_equality"


# ---------------------------------------------------------------------------
# Unit tests: Component with new fields
# ---------------------------------------------------------------------------


class TestComponentWithNewFields:
    """Tests for Component with constants/signatures/test_contracts."""

    def test_component_default_empty_lists(self):
        comp = Component(
            id="COMP-1",
            name="Test",
            status=Status.ACTIVE,
        )
        assert comp.constants == []
        assert comp.signatures == []
        assert comp.test_contracts == []

    def test_component_with_constants(self):
        comp = Component(
            id="COMP-1",
            name="Test",
            status=Status.ACTIVE,
            constants=[Constant(name="BLACK", value="30", context="AnsiFore")],
        )
        assert len(comp.constants) == 1
        assert comp.constants[0].name == "BLACK"

    def test_component_with_signatures(self):
        comp = Component(
            id="COMP-1",
            name="Test",
            status=Status.ACTIVE,
            signatures=[
                FunctionSignature(
                    name="code_to_chars",
                    params=["code: int"],
                    returns="str",
                )
            ],
        )
        assert len(comp.signatures) == 1
        assert comp.signatures[0].name == "code_to_chars"

    def test_component_with_test_contracts(self):
        comp = Component(
            id="COMP-1",
            name="Test",
            status=Status.ACTIVE,
            test_contracts=[
                TestContract(
                    test_file="test_ansi.py",
                    test_method="test_fore",
                    assertion="Fore.BLACK == '\\033[30m'",
                    contract_type="value_equality",
                )
            ],
        )
        assert len(comp.test_contracts) == 1
        assert comp.test_contracts[0].contract_type == "value_equality"


# ---------------------------------------------------------------------------
# Parser tests: YAML → dataclasses
# ---------------------------------------------------------------------------


SAMPLE_YAML_DICT = {
    "meta": {"schema_version": "1.3", "project": "test-project"},
    "entities": {
        "components": [
            {
                "id": "COMP-ANSI",
                "name": "ANSI Module",
                "status": "ACTIVE",
                "constants": [
                    {"name": "BLACK", "value": "30", "context": "AnsiFore"},
                    {"name": "RED", "value": "31"},
                ],
                "signatures": [
                    {
                        "name": "code_to_chars",
                        "params": ["code: int"],
                        "returns": "str",
                        "decorators": ["staticmethod"],
                        "body_hint": "Convert code to escape sequence",
                    },
                    {
                        "name": "init",
                        "params": [],
                        "returns": "None",
                    },
                ],
                "test_contracts": [
                    {
                        "test_file": "ansi_test.py",
                        "test_method": "testForeAttributes",
                        "assertion": "Fore.BLACK == '\\033[30m'",
                        "contract_type": "value_equality",
                    },
                    {
                        "test_file": "ansi_test.py",
                        "test_method": "testRaises",
                        "assertion": "raises ValueError on invalid code",
                        "contract_type": "raises",
                    },
                ],
            }
        ]
    },
    "relationships": [],
}


class TestParseNewFields:
    """Tests for parsing constants/signatures/test_contracts from YAML dicts."""

    def test_parse_constants(self):
        model = _parse_raw(SAMPLE_YAML_DICT)
        comp = model.entities.components[0]
        assert len(comp.constants) == 2
        assert comp.constants[0].name == "BLACK"
        assert comp.constants[0].value == "30"
        assert comp.constants[0].context == "AnsiFore"
        assert comp.constants[1].name == "RED"
        assert comp.constants[1].value == "31"
        assert comp.constants[1].context == ""

    def test_parse_signatures(self):
        model = _parse_raw(SAMPLE_YAML_DICT)
        comp = model.entities.components[0]
        assert len(comp.signatures) == 2
        sig = comp.signatures[0]
        assert sig.name == "code_to_chars"
        assert sig.params == ["code: int"]
        assert sig.returns == "str"
        assert sig.decorators == ["staticmethod"]
        assert sig.body_hint == "Convert code to escape sequence"
        # Second signature with defaults
        sig2 = comp.signatures[1]
        assert sig2.decorators == []
        assert sig2.body_hint == ""

    def test_parse_test_contracts(self):
        model = _parse_raw(SAMPLE_YAML_DICT)
        comp = model.entities.components[0]
        assert len(comp.test_contracts) == 2
        tc = comp.test_contracts[0]
        assert tc.test_file == "ansi_test.py"
        assert tc.test_method == "testForeAttributes"
        assert tc.assertion == "Fore.BLACK == '\\033[30m'"
        assert tc.contract_type == "value_equality"

    def test_parse_missing_new_fields_defaults_empty(self):
        """Components without the new fields should get empty lists."""
        raw = {
            "meta": {"schema_version": "1.3", "project": "test"},
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Simple", "status": "ACTIVE"}
                ]
            },
            "relationships": [],
        }
        model = _parse_raw(raw)
        comp = model.entities.components[0]
        assert comp.constants == []
        assert comp.signatures == []
        assert comp.test_contracts == []


# ---------------------------------------------------------------------------
# Serializer tests: dataclasses → dict
# ---------------------------------------------------------------------------


class TestSerializeNewFields:
    """Tests for serializing constants/signatures/test_contracts to dicts."""

    def test_dump_constants(self):
        model = _parse_raw(SAMPLE_YAML_DICT)
        data = dump_model(model)
        comp_data = data["entities"]["components"][0]
        assert "constants" in comp_data
        assert len(comp_data["constants"]) == 2
        assert comp_data["constants"][0] == {
            "name": "BLACK",
            "value": "30",
            "context": "AnsiFore",
        }
        # context="" should be omitted
        assert comp_data["constants"][1] == {"name": "RED", "value": "31"}

    def test_dump_signatures(self):
        model = _parse_raw(SAMPLE_YAML_DICT)
        data = dump_model(model)
        comp_data = data["entities"]["components"][0]
        assert "signatures" in comp_data
        assert len(comp_data["signatures"]) == 2
        assert comp_data["signatures"][0] == {
            "name": "code_to_chars",
            "params": ["code: int"],
            "returns": "str",
            "decorators": ["staticmethod"],
            "body_hint": "Convert code to escape sequence",
        }
        # Second signature: empty params/decorators/body_hint omitted
        assert comp_data["signatures"][1] == {
            "name": "init",
            "returns": "None",
        }

    def test_dump_test_contracts(self):
        model = _parse_raw(SAMPLE_YAML_DICT)
        data = dump_model(model)
        comp_data = data["entities"]["components"][0]
        assert "test_contracts" in comp_data
        assert len(comp_data["test_contracts"]) == 2
        assert comp_data["test_contracts"][0] == {
            "test_file": "ansi_test.py",
            "test_method": "testForeAttributes",
            "assertion": "Fore.BLACK == '\\033[30m'",
            "contract_type": "value_equality",
        }

    def test_dump_empty_fields_omitted(self):
        """Empty constants/signatures/test_contracts should not appear in output."""
        raw = {
            "meta": {"schema_version": "1.3", "project": "test"},
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Simple", "status": "ACTIVE"}
                ]
            },
            "relationships": [],
        }
        model = _parse_raw(raw)
        data = dump_model(model)
        comp_data = data["entities"]["components"][0]
        assert "constants" not in comp_data
        assert "signatures" not in comp_data
        assert "test_contracts" not in comp_data

    def test_to_dict_method_includes_new_fields(self):
        """ArchitectureModel.to_dict() also serializes the new fields."""
        model = _parse_raw(SAMPLE_YAML_DICT)
        data = model.to_dict()
        comp_data = data["entities"]["components"][0]
        assert "constants" in comp_data
        assert "signatures" in comp_data
        assert "test_contracts" in comp_data


# ---------------------------------------------------------------------------
# Round-trip tests: parse → serialize → parse
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Round-trip fidelity for new fields."""

    def test_round_trip_via_dump_model(self):
        """parse → dump_model → parse produces identical data."""
        model1 = _parse_raw(SAMPLE_YAML_DICT)
        data = dump_model(model1)
        model2 = _parse_raw(data)

        comp1 = model1.entities.components[0]
        comp2 = model2.entities.components[0]

        # Constants
        assert len(comp1.constants) == len(comp2.constants)
        for c1, c2 in zip(comp1.constants, comp2.constants):
            assert c1.name == c2.name
            assert c1.value == c2.value
            assert c1.context == c2.context

        # Signatures
        assert len(comp1.signatures) == len(comp2.signatures)
        for s1, s2 in zip(comp1.signatures, comp2.signatures):
            assert s1.name == s2.name
            assert s1.params == s2.params
            assert s1.returns == s2.returns
            assert s1.decorators == s2.decorators
            assert s1.body_hint == s2.body_hint

        # Test contracts
        assert len(comp1.test_contracts) == len(comp2.test_contracts)
        for t1, t2 in zip(comp1.test_contracts, comp2.test_contracts):
            assert t1.test_file == t2.test_file
            assert t1.test_method == t2.test_method
            assert t1.assertion == t2.assertion
            assert t1.contract_type == t2.contract_type

    def test_round_trip_via_yaml_file(self, tmp_path: Path):
        """parse → save_model → load_model produces identical data."""
        model1 = _parse_raw(SAMPLE_YAML_DICT)
        out_path = tmp_path / "test_model.yaml"
        save_model(model1, out_path)
        model2 = load_model(out_path)

        comp1 = model1.entities.components[0]
        comp2 = model2.entities.components[0]

        assert len(comp1.constants) == len(comp2.constants)
        assert len(comp1.signatures) == len(comp2.signatures)
        assert len(comp1.test_contracts) == len(comp2.test_contracts)

        # Spot check
        assert comp2.constants[0].name == "BLACK"
        assert comp2.signatures[0].returns == "str"
        assert comp2.test_contracts[0].contract_type == "value_equality"

    def test_round_trip_via_to_dict(self):
        """parse → to_dict() → parse produces identical data."""
        model1 = _parse_raw(SAMPLE_YAML_DICT)
        data = model1.to_dict()
        model2 = _parse_raw(data)

        comp1 = model1.entities.components[0]
        comp2 = model2.entities.components[0]

        assert len(comp1.constants) == len(comp2.constants)
        assert len(comp1.signatures) == len(comp2.signatures)
        assert len(comp1.test_contracts) == len(comp2.test_contracts)
