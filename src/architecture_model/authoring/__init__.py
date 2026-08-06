"""Forward-authoring: parse requirements documents into architecture models."""

from architecture_model.authoring.parser import parse_requirements_doc
from architecture_model.authoring.gate import check_development_gate, GateResult

__all__ = ["parse_requirements_doc", "check_development_gate", "GateResult"]
