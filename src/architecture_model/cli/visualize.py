"""CLI visualization — delegates to core.visualize.

Also re-exports legacy functions for backward compatibility.
"""

from ..core.visualize import (
    # Helpers
    shape,
    edge_style,
    css_classes,
    inject_click_handlers,
    build_entity_properties,
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
    generate_component_detail_diagram,
    generate_use_case_diagram,
    generate_html_viewer,
    # SE overview diagrams
    generate_conops_diagram,
    generate_functional_architecture_diagram,
    generate_logical_architecture_diagram,
    generate_behavior_overview_diagram,
    generate_entity_explorer,
    # New SE views (v3)
    generate_icd_diagram,
    generate_requirements_allocation_diagram,
    generate_system_decomposition_diagram,
    # Behavior detail diagrams
    generate_behavior_sequence_diagram,
    generate_behavior_flow_diagram,
)

__all__ = [
    "shape", "edge_style", "css_classes",
    "inject_click_handlers", "build_entity_properties",
    "generate_context_diagram", "generate_components_diagram",
    "generate_behaviors_diagram", "generate_dependencies_diagram",
    "generate_pipeline_flow_diagram", "generate_entity_lifecycle_diagram",
    "generate_data_flow_diagram", "generate_constraint_map_diagram",
    "generate_traceability_diagram", "generate_decomposition_diagram",
    "generate_component_detail_diagram", "generate_use_case_diagram",
    "generate_html_viewer",
    "generate_conops_diagram", "generate_functional_architecture_diagram",
    "generate_logical_architecture_diagram", "generate_behavior_overview_diagram",
    "generate_entity_explorer",
    "generate_icd_diagram", "generate_requirements_allocation_diagram",
    "generate_system_decomposition_diagram",
    "generate_behavior_sequence_diagram",
    "generate_behavior_flow_diagram",
    "generate_all_diagrams",
]
