def test_sil_record_arch_kind_minimum():
    from architecture_model.sil.record import SILRecord, Metrics
    r = SILRecord(
        component_id="COMP-2.1",
        kind="architecture-component",
        name="Pipeline Coordination",
        metrics=Metrics(),
    )
    assert r.component_id == "COMP-2.1"
    assert r.kind == "architecture-component"


def test_sil_record_runtime_kind():
    from architecture_model.sil.record import SILRecord, Metrics
    r = SILRecord(
        component_id="stage:observe",
        kind="runtime-component",
        name="ObserveStage",
        metrics=Metrics(invocations_7d=42, failure_rate_7d=0.05, avg_duration_ms=120),
    )
    assert r.metrics.invocations_7d == 42


def test_sil_record_yaml_round_trip(tmp_path):
    from architecture_model.sil.record import SILRecord, Metrics, dump_yaml, load_yaml
    r = SILRecord(component_id="COMP-1", kind="architecture-component",
                  name="Core", metrics=Metrics(validation_score=87))
    p = tmp_path / "COMP-1.yaml"
    p.write_text(dump_yaml(r))
    r2 = load_yaml(p.read_text())
    assert r2 == r


def test_sil_record_rejects_bad_kind():
    from architecture_model.sil.record import SILRecord, Metrics
    import pytest
    with pytest.raises(ValueError):
        SILRecord(component_id="x", kind="bogus", name="n", metrics=Metrics())
