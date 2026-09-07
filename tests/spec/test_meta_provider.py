import json
from pathlib import Path


def test_schema_has_meta_provider_definition():
    schema = json.loads(
        Path("src/architecture_model/spec/schema.json").read_text()
    )
    meta_props = schema["properties"]["meta"]["properties"]
    assert "provider" in meta_props
    prov = meta_props["provider"]
    assert prov["type"] == "object"
    assert set(prov["required"]) == {"name", "model"}
    assert prov["properties"]["name"]["type"] == "string"
    assert prov["properties"]["model"]["type"] == "string"
    assert prov["properties"]["policy_ref"]["type"] == "string"


def test_model_without_provider_still_parses():
    from architecture_model.core.parser import _parse_raw
    m = _parse_raw({
        "meta": {"project": "p", "schema_version": "1.3"},
        "entities": {"components": []},
        "relationships": [],
    })
    assert m.meta.project == "p"


def test_model_with_provider_parses_and_round_trips():
    from architecture_model.core.parser import _parse_raw
    m = _parse_raw({
        "meta": {
            "project": "p",
            "schema_version": "1.3",
            "provider": {
                "name": "frontier",
                "model": "claude-4.7",
                "policy_ref": "default",
            },
        },
        "entities": {"components": []},
        "relationships": [],
    })
    assert m.meta.provider is not None
    assert m.meta.provider.name == "frontier"
    assert m.meta.provider.model == "claude-4.7"
