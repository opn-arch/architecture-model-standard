import pytest
from architecture_model.profiles.schema import load_profile, BUILTIN_PROFILES


@pytest.mark.parametrize("name", list(BUILTIN_PROFILES.keys()))
def test_builtin_profile_loads(name):
    p = load_profile(name)
    assert p.domain == name
    assert p.extends_schema == "1.4"


def test_controls_profile_has_sensor_kind():
    p = load_profile("controls")
    kinds = p.get_extended_values("component_kind")
    assert "sensor" in kinds
    assert "actuator" in kinds
    assert "controller" in kinds


def test_mechanical_profile_has_assembly_kind():
    p = load_profile("mechanical")
    kinds = p.get_extended_values("component_kind")
    assert "part" in kinds
    assert "assembly" in kinds


def test_electrical_profile_has_pcb_kind():
    p = load_profile("electrical")
    kinds = p.get_extended_values("component_kind")
    assert "pcb" in kinds
    assert "connector" in kinds


def test_software_profile_is_base():
    p = load_profile("software")
    assert len(p.enum_extensions) == 0
