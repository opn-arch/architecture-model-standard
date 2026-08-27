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
