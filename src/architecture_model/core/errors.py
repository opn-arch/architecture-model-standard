"""Canonical parse-error type for architecture_model.

All modules that produce parse-time failures (YAML, JSON, schema shape) should
raise ParseError or a subclass. Subclass of ValueError for backward compatibility
with `except ValueError` sites.
"""
from __future__ import annotations

__all__ = ["ParseError"]


class ParseError(ValueError):
    """Canonical parse error for architecture models, packages, and proposals."""
