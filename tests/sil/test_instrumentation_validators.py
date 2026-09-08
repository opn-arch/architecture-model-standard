"""B2.2.3 — instrument three validator entry points."""


def test_validate_model_is_instrumented():
    from architecture_model.core.validator import validate_model
    assert getattr(validate_model, "__sil_instrumented__", False)
    assert validate_model.__sil_component_id__ == "validator:validate"


def test_representativeness_is_instrumented():
    # Actual entry point is `compute_representativeness`
    # (no `evaluate` symbol exists in this module).
    from architecture_model.core.representativeness import compute_representativeness
    assert getattr(compute_representativeness, "__sil_instrumented__", False)
    assert compute_representativeness.__sil_component_id__ == "validator:check"


def test_authoring_gate_is_instrumented():
    # Actual entry point is `check_development_gate`
    # (no `evaluate` symbol exists in this module).
    from architecture_model.authoring.gate import check_development_gate
    assert getattr(check_development_gate, "__sil_instrumented__", False)
    assert check_development_gate.__sil_component_id__ == "validator:gate"
