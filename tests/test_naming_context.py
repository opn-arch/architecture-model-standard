"""Tests for decomposition naming context formatter."""
from architecture_model.orchestration.naming_context import format_naming_context
from architecture_model.orchestration.deep_decompose import DecomposeResult, SubComponent, InternalRelationship


def test_format_naming_context_compact():
    """Naming context is compact and informative."""
    result = DecomposeResult(
        block_id="F6",
        block_name="MQTT Integration",
        sub_components=[
            SubComponent(id="COMP-F6-1", name="temp", files=["mqtt/client.py", "mqtt/transport.py"],
                        classes=["MQTT", "MqttClientSetup", "AsyncTransport"], functions=["connect", "disconnect"], line_count=800),
            SubComponent(id="COMP-F6-2", name="temp", files=["mqtt/discovery.py", "mqtt/models.py"],
                        classes=["MqttDiscovery", "DiscoveryPayload"], functions=["async_start", "process_message"], line_count=600),
        ],
        internal_relationships=[
            InternalRelationship(from_id="COMP-F6-2", to_id="COMP-F6-1", edge_count=5),
        ],
    )

    context = format_naming_context(result)
    assert "COMP-F6-1" in context
    assert "MQTT" in context
    assert "client" in context
    assert len(context) < 2000


def test_format_naming_context_empty():
    """Empty decomposition produces minimal output."""
    result = DecomposeResult(block_id="F1", block_name="Core")
    context = format_naming_context(result)
    assert "no sub-components" in context.lower() or len(context.strip()) < 100
