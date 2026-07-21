"""CLI visualization — delegates to core.visualize.

Also re-exports legacy functions for backward compatibility.
"""

from ..core.visualize import (
    generate_all_diagrams,
    generate_behaviors_diagram,
    generate_components_diagram,
    generate_context_diagram,
    generate_dependencies_diagram,
)

__all__ = [
    "generate_context_diagram",
    "generate_components_diagram",
    "generate_behaviors_diagram",
    "generate_dependencies_diagram",
    "generate_all_diagrams",
]
