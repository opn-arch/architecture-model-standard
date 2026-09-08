"""Architecture model JSON Schema package.

Exposes the canonical ``SCHEMA_VERSION`` string used throughout the code
base (parser fallbacks, decompose emit, tests). Bumping this constant is
part of every schema revision; ``schema.json``'s ``$id`` must match.
"""

SCHEMA_VERSION = "2.1.0"

__all__ = ["SCHEMA_VERSION"]
