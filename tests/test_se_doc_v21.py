"""Tests for v2.1 SE field rendering in doc generators."""
from tests.fixtures.se_doc_model import make_model


class TestBaselineGeneration:
    """Verify existing generators don't crash with v2.1 fields."""

    def test_conops_generates(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Test System" in result or "test-project" in result
        assert "Model Validation" in result

    def test_functional_analysis_generates(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "CAP-1" in result

    def test_logical_architecture_generates(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Validator" in result

    def test_use_cases_generates(self):
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = make_model()
        result = generate_use_cases(model, manifest=None)
        assert "Validate Model" in result

    def test_artifact_traceability_generates(self):
        from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability
        model = make_model()
        result = generate_artifact_traceability(model, manifest=None)
        assert "COMP-1" in result or "components" in result.lower()


class TestConopsV21:
    def test_capability_intent_rendered(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Ensure models are structurally correct" in result

    def test_capability_moes_rendered(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Validation score >= 80/100" in result

    def test_actor_intent_rendered(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Primary user of the system" in result

    def test_failure_modes_section(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Silent acceptance of invalid models" in result


class TestFunctionalAnalysisV21:
    def test_capability_intent_in_table(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "Ensure models are structurally correct" in result

    def test_moes_section(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "Measures of Effectiveness" in result
        assert "Validation score >= 80/100" in result

    def test_trade_offs_in_mapping(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "Strict validation vs permissive parsing" in result


class TestLogicalArchitectureV21:
    def test_component_intent_rendered(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Single source of truth" in result

    def test_interface_contract_rendered(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Pre: model is parsed" in result or "idempotent" in result

    def test_trade_offs_rendered(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Strict validation vs permissive parsing" in result


class TestUseCasesV21:
    def test_success_criteria_from_moes(self):
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = make_model()
        result = generate_use_cases(model, manifest=None)
        # BEH-1 traces-to COMP-1, COMP-1 realizes CAP-1, CAP-1 has MOEs
        assert "Success Criteria" in result or "Validation score >= 80/100" in result

    def test_failure_modes_rendered(self):
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = make_model()
        result = generate_use_cases(model, manifest=None)
        # COMP-1 has failure_modes, linked via traces-to from BEH-1
        assert "Failure Modes" in result or "Silent acceptance" in result


class TestArtifactTraceabilityV21:
    def test_moe_gap_detection(self):
        from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability
        model = make_model()
        # Remove MOEs from CAP-2 to create a gap
        model.entities.capabilities[1].moes = []
        result = generate_artifact_traceability(model, manifest=None)
        assert "without moe" in result.lower() or "missing moe" in result.lower()

    def test_contract_gap_detection(self):
        from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability
        model = make_model()
        # Clear contract to create a gap
        model.entities.interfaces[0].contract = ""
        result = generate_artifact_traceability(model, manifest=None)
        assert "without contract" in result.lower() or "missing contract" in result.lower()
