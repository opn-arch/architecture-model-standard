"""tiny_pkg — three-module fixture used by the SI&L pipeline tests."""
from tiny_pkg.api import Service
from tiny_pkg.core import compute
from tiny_pkg.storage import Store

__all__ = ["Service", "compute", "Store"]
