import importlib
import pytest

STAGE_MODULES = [
    "architecture_model.pipeline.observe",
    "architecture_model.pipeline.infer",
    "architecture_model.pipeline.allocate",
    "architecture_model.pipeline.relate",
    "architecture_model.pipeline.specify",
    "architecture_model.pipeline.contract",
    "architecture_model.pipeline.decompose",
    "architecture_model.pipeline.synthesize",
    "architecture_model.pipeline.validate",
    "architecture_model.pipeline.emit",
]


@pytest.mark.parametrize("mod", STAGE_MODULES)
def test_stage_run_is_instrumented(mod):
    m = importlib.import_module(mod)
    stage_cls = next(v for k, v in vars(m).items()
                     if k.endswith("Stage") and isinstance(v, type))
    assert getattr(stage_cls.run, "__sil_instrumented__", False)
