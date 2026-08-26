"""WP-2: Detail level scoring — L0 through L4."""
from architecture_model.core.detail_level import compute_detail_level, DetailLevel
from architecture_model.core.types import Component, Capability, Behavior, Interface, Status


class TestDetailLevel:
    def test_skeleton_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert compute_detail_level(c) == DetailLevel.L0_SKELETON

    def test_described_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      description="A test component")
        assert compute_detail_level(c) == DetailLevel.L1_DESCRIBED

    def test_specified_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      description="A test component",
                      intent="Provide testing",
                      responsibilities=["Parse", "Validate"])
        assert compute_detail_level(c) == DetailLevel.L2_SPECIFIED

    def test_enriched_component(self):
        from architecture_model.core.types import FunctionSignature, TestContract
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      description="A test component",
                      intent="Provide testing",
                      responsibilities=["Parse"],
                      signatures=[FunctionSignature(name="parse", params=["path"])],
                      test_contracts=[TestContract(assertion="returns dict",
                                                   contract_type="output",
                                                   test_method="test_parse",
                                                   test_file="test_core.py")])
        assert compute_detail_level(c) == DetailLevel.L3_ENRICHED

    def test_reviewed_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      extensions={"_llm_review": {"timestamp": "2026-01-01"}})
        assert compute_detail_level(c) == DetailLevel.L4_REVIEWED

    def test_capability_skeleton(self):
        c = Capability(id="CAP-1", name="Test", status=Status.ACTIVE)
        assert compute_detail_level(c) == DetailLevel.L0_SKELETON

    def test_capability_specified(self):
        c = Capability(id="CAP-1", name="Test", status=Status.ACTIVE,
                       description="Validates", intent="Ensure correctness",
                       moes=["95% detection"])
        assert compute_detail_level(c) == DetailLevel.L2_SPECIFIED

    def test_behavior_specified(self):
        b = Behavior(id="BEH-1", name="Test", status=Status.ACTIVE,
                     description="Run validation", intent="User triggers validation",
                     steps=["Load model", "Validate"])
        assert compute_detail_level(b) == DetailLevel.L2_SPECIFIED

    def test_interface_specified(self):
        i = Interface(id="IF-1", name="Test", status=Status.ACTIVE,
                      description="API", intent="Entry point",
                      protocol="REST")
        assert compute_detail_level(i) == DetailLevel.L2_SPECIFIED
