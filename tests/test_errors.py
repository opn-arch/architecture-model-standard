import pytest

from architecture_model.core.errors import ParseError


def test_parse_error_is_value_error():
    assert issubclass(ParseError, ValueError)


def test_parser_raises_parse_error_on_empty_file(tmp_path):
    from architecture_model.core.parser import load_model
    p = tmp_path / "empty.yaml"
    p.write_text("")
    with pytest.raises(ParseError):
        load_model(p)


def test_package_load_error_is_parse_error():
    from architecture_model.lifecycle.package import PackageLoadError
    assert issubclass(PackageLoadError, ParseError)


def test_serialization_duplicate_key_raises_parse_error():
    from architecture_model.lifecycle.serialization import canonical_yaml_load
    with pytest.raises(ParseError):
        canonical_yaml_load("a: 1\na: 2\n")


def test_proposal_unknown_kind_raises_parse_error():
    from architecture_model.ai.proposals import proposal_from_dict
    with pytest.raises(ParseError):
        proposal_from_dict({"kind": "nonexistent-kind-xyz"})


def test_top_level_reexports_parse_error():
    import architecture_model
    assert architecture_model.ParseError is ParseError


def test_core_reexports_parse_error():
    from architecture_model.core import ParseError as CoreParseError
    assert CoreParseError is ParseError
