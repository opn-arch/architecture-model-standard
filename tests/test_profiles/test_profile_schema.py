import pytest
from architecture_model.profiles.schema import (
    DomainProfile,
    EnumExtension,
    EntityExtension,
    ConditionalRule,
    load_profile,
    BUILTIN_PROFILES,
)


def test_domain_profile_creation():
    p = DomainProfile(
        domain="controls",
        extends_schema="1.4",
        enum_extensions=[
            EnumExtension(
                enum_name="component_kind",
                values=["sensor", "actuator", "controller"],
            )
        ],
        entity_extensions=[
            EntityExtension(
                entity_type="component",
                properties={"signal_type": {"type": "string"}},
            )
        ],
        validation_rules=[
            ConditionalRule(
                entity_type="component",
                when={"kind": "sensor"},
                require=["signal_type"],
                message="Sensors must declare signal_type",
            )
        ],
    )
    assert p.domain == "controls"
    assert len(p.enum_extensions) == 1
    assert "sensor" in p.enum_extensions[0].values


def test_builtin_profiles_exist():
    assert "software" in BUILTIN_PROFILES
    assert "controls" in BUILTIN_PROFILES
    assert "mechanical" in BUILTIN_PROFILES
    assert "electrical" in BUILTIN_PROFILES


def test_load_custom_profile(tmp_path):
    import yaml

    profile_data = {
        "domain": "custom",
        "extends_schema": "1.4",
        "enum_extensions": [
            {"enum_name": "component_kind", "values": ["widget", "gadget"]}
        ],
        "entity_extensions": [],
        "validation_rules": [],
    }
    pf = tmp_path / "custom.yaml"
    pf.write_text(yaml.dump(profile_data))
    p = load_profile(str(pf))
    assert p.domain == "custom"
    assert "widget" in p.enum_extensions[0].values
