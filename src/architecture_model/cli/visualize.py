"""CLI visualization — delegates to core.visualize.

Also re-exports legacy functions for backward compatibility.
"""

from ..core.visualize import (
    # Helpers
    shape,
    edge_style,
    css_classes,
    # Existing generators
    generate_all_diagrams,
    generate_behaviors_diagram,
    generate_components_diagram,
    generate_context_diagram,
    generate_dependencies_diagram,
    # New generators
    generate_pipeline_flow_diagram,
    generate_entity_lifecycle_diagram,
    generate_data_flow_diagram,
    generate_constraint_map_diagram,
    generate_traceability_diagram,
    generate_decomposition_diagram,
)

__all__ = [
    "shape", "edge_style", "css_classes",
    "generate_context_diagram", "generate_components_diagram",
    "generate_behaviors_diagram", "generate_dependencies_diagram",
    "generate_pipeline_flow_diagram", "generate_entity_lifecycle_diagram",
    "generate_data_flow_diagram", "generate_constraint_map_diagram",
    "generate_traceability_diagram", "generate_decomposition_diagram",
    "generate_all_diagrams",
]
