"""Tests for schema.json sync with Python RelationType enum."""

import json
from pathlib import Path

from architecture_model.core.types import RelationType


def test_schema_json_has_all_relationship_types():
    """schema.json relationship type enum must match Python RelationType."""
    schema_path = Path(__file__).parent.parent / "src" / "architecture_model" / "spec" / "schema.json"
    schema = json.loads(schema_path.read_text())
    schema_types = set(schema["$defs"]["relationship"]["properties"]["type"]["enum"])
    python_types = {rt.value for rt in RelationType}
    assert python_types.issubset(schema_types), f"Missing from schema: {python_types - schema_types}"
