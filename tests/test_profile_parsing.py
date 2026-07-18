import yaml
from architecture_model.core.parser import _parse_raw


def test_meta_includes_domain_profile():
    raw = yaml.safe_load("""
    meta:
      project: factory
      schema_version: '1.4'
      domain_profile: controls
    entities:
      components: []
    relationships: []
    """)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "controls"


def test_meta_domain_profile_defaults_to_software():
    raw = yaml.safe_load("""
    meta:
      project: webapp
      schema_version: '1.4'
    entities:
      components: []
    relationships: []
    """)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "software"
