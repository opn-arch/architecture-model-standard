"""Test enrichment context formatter for agent annotation."""
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
from architecture_model.orchestration.deep_decompose import DecomposeResult, SubComponent, InternalRelationship


def _sample_tree() -> list[DecomposeResult]:
    return [DecomposeResult(
        block_id="F6",
        block_name="MQTT",
        sub_components=[
            SubComponent(id="COMP-F6-1", name="", files=["mqtt/client.py", "mqtt/connection.py"], classes=["MQTTClient"], functions=["async_connect"], line_count=200),
            SubComponent(id="COMP-F6-2", name="", files=["mqtt/fan.py"], classes=["MqttFan"], functions=["async_setup_entry"], line_count=80),
            SubComponent(id="COMP-F6-3", name="", files=["mqtt/light.py"], classes=["MqttLight"], functions=["async_setup_entry"], line_count=90),
        ],
        internal_relationships=[
            InternalRelationship(from_id="COMP-F6-2", to_id="COMP-F6-1", edge_count=3),
            InternalRelationship(from_id="COMP-F6-3", to_id="COMP-F6-1", edge_count=2),
        ],
        depth=1,
    )]


def test_format_enrichment_prompt_contains_all_leaves():
    prompt = format_enrichment_prompt(_sample_tree())
    assert "COMP-F6-1" in prompt
    assert "COMP-F6-2" in prompt
    assert "COMP-F6-3" in prompt


def test_format_enrichment_prompt_includes_pattern_catalog():
    prompt = format_enrichment_prompt(_sample_tree())
    assert "entity-platform" in prompt
    assert "reconnecting-client" in prompt


def test_format_enrichment_prompt_includes_instructions():
    prompt = format_enrichment_prompt(_sample_tree())
    assert "pattern" in prompt.lower()
    assert "contract" in prompt.lower()


def test_format_enrichment_prompt_compact():
    """Should be under 2000 tokens (~8000 chars) for 3 leaves."""
    prompt = format_enrichment_prompt(_sample_tree())
    assert len(prompt) < 8000
