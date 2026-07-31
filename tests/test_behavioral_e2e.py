"""End-to-end behavioral capture integration tests.

Tests that behavioral data flows through the full pipeline:
scan → manifest → recursive manifests → chains.
"""
import pytest
from pathlib import Path

from architecture_model.manifest.generator import generate_manifest
from architecture_model.manifest.recursive import generate_recursive_manifests

SELF_ROOT = Path(__file__).parent.parent


class TestBehavioralEndToEnd:
    def test_scan_produces_behavioral_data_on_self(self):
        """architecture-model-standard scan includes call_order/control_flow."""
        manifest = generate_manifest(SELF_ROOT)
        funcs_with_calls = sum(1 for m in manifest.modules for f in m.functions if f.call_order)
        funcs_with_flow = sum(1 for m in manifest.modules for f in m.functions if f.control_flow)
        funcs_with_guards = sum(1 for m in manifest.modules for f in m.functions if f.guards)
        assert funcs_with_calls > 20, f"Expected >20 functions with call_order, got {funcs_with_calls}"
        assert funcs_with_flow > 10, f"Expected >10 functions with control_flow, got {funcs_with_flow}"
        assert funcs_with_guards > 5, f"Expected >5 functions with guards, got {funcs_with_guards}"

    def test_recursive_manifests_have_chains(self):
        """Per-block recursive manifests include intra-block chains."""
        manifests = generate_recursive_manifests(SELF_ROOT)
        total_chains = sum(len(rm.intra_chains) for rm in manifests.values())
        assert total_chains > 0, "Expected at least some intra-block chains"

    def test_behavioral_data_in_class_methods(self):
        """Class method_details also get behavioral fields."""
        manifest = generate_manifest(SELF_ROOT)
        methods_with_calls = 0
        for m in manifest.modules:
            for cls in m.classes:
                for method in cls.method_details:
                    if method.call_order:
                        methods_with_calls += 1
        assert methods_with_calls > 5, f"Expected >5 methods with call_order, got {methods_with_calls}"

    def test_data_in_out_populated(self):
        """data_in and data_out fields get populated from type annotations."""
        manifest = generate_manifest(SELF_ROOT)
        funcs_with_data_in = sum(1 for m in manifest.modules for f in m.functions if f.data_in)
        funcs_with_data_out = sum(1 for m in manifest.modules for f in m.functions if f.data_out)
        assert funcs_with_data_in > 10, f"Expected >10 functions with data_in, got {funcs_with_data_in}"
        assert funcs_with_data_out > 10, f"Expected >10 functions with data_out, got {funcs_with_data_out}"
