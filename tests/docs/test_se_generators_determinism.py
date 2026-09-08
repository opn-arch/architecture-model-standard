"""Byte-identical output guard for the 17 SE doc generators.

Task 3 of Phase 1 substrate-and-liveness plan. The SE doc suite
(`architecture_model.docs.se.*`) fans out to 11 STANDARD_DOCS +
6 PROJECT_DOCS generators, each producing a Markdown string from
the same input model. Without a determinism guard, a future
dict-ordering or set-iteration regression in any single generator
could silently churn the rendered artifacts on every rebuild
across the entire SE doc suite. This test locks each generator's
output to byte-identical repeat invocations against the committed
sample model.
"""

import importlib
from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.docs.se.generator import PROJECT_DOCS, STANDARD_DOCS

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


_CASES = [(key, mod) for key, mod, _display, _fname in STANDARD_DOCS] + [
    (key, mod) for key, (mod, _display, _fname) in PROJECT_DOCS.items()
]


@pytest.mark.parametrize("key,module_name", _CASES, ids=[k for k, _ in _CASES])
def test_se_generator_byte_identical(key, module_name, sample_model):
    mod = importlib.import_module(f"architecture_model.docs.se.{module_name}")
    gen_fn = getattr(mod, f"generate_{module_name}")
    a = gen_fn(sample_model)
    b = gen_fn(sample_model)
    assert isinstance(a, str)
    assert len(a) > 0
    assert a == b, f"generate_{module_name} not byte-identical"
