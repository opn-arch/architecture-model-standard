"""Tests for load_block_model()."""

import textwrap
from pathlib import Path

from architecture_model.core.parser import load_block_model

MINIMAL_MODEL = textwrap.dedent("""\
    meta:
      project: test-block
      schema_version: '1.3'
    entities:
      components:
        - id: COMP-1
          name: TestComponent
          status: ACTIVE
    relationships: []
""")


def test_loads_existing_block(tmp_path: Path):
    block_dir = tmp_path / ".architecture-models" / "S1"
    block_dir.mkdir(parents=True)
    (block_dir / ".architecture-model.yaml").write_text(MINIMAL_MODEL)

    model = load_block_model(tmp_path, "S1")
    assert model is not None
    assert model.meta.project == "test-block"
    assert len(model.entities.components) == 1


def test_returns_none_for_missing_block(tmp_path: Path):
    result = load_block_model(tmp_path, "S99")
    assert result is None


def test_custom_output_dir(tmp_path: Path):
    block_dir = tmp_path / "custom-models" / "S2"
    block_dir.mkdir(parents=True)
    (block_dir / ".architecture-model.yaml").write_text(MINIMAL_MODEL)

    model = load_block_model(tmp_path, "S2", output_dir="custom-models")
    assert model is not None
    assert model.meta.project == "test-block"
