"""Test pipeline compact mode."""
import pytest
from pathlib import Path
from architecture_model.orchestration.pipeline import run_pipeline
from architecture_model.core.parser import load_model, load_block_model


@pytest.fixture
def compact_repo(tmp_path):
    (tmp_path / "architecture.yaml").write_text("""
project: test-compact
functional_blocks:
  S1:
    name: Core
    dirs: [core]
  S2:
    name: API
    dirs: [api]
""")
    (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test-compact
  schema_version: '1.3'
functional_blocks:
  S1:
    name: Core
    dirs: [core]
  S2:
    name: API
    dirs: [api]
entities:
  components:
    - id: COMP-1
      name: Engine
      status: ACTIVE
      source_block: S1
      files: [core/engine.py]
    - id: COMP-2
      name: Router
      status: ACTIVE
      source_block: S2
      files: [api/router.py]
relationships: []
""")
    core = tmp_path / "core"
    core.mkdir()
    (core / "engine.py").write_text('''
"""Engine that processes requests."""
MAX_QUEUE = 100
class Engine:
    """Core processing engine."""
    def process(self, request: dict) -> dict:
        return {}
''')
    api = tmp_path / "api"
    api.mkdir()
    (api / "router.py").write_text('''
"""Routes requests to handlers."""
class Router:
    """Request router."""
    def route(self, path: str) -> callable:
        return lambda: None
''')
    return tmp_path


def test_compact_mode_strips_root_detail(compact_repo):
    run_pipeline(compact_repo, compact=True)

    root = load_model(str(compact_repo / ".architecture-model.yaml"))
    comps = root.entities.components if hasattr(root.entities, "components") else root.entities.get("components", [])
    for comp in comps:
        assert comp.signatures == [], f"{comp.name} should have empty signatures in root"
        assert comp.symbols == [], f"{comp.name} should have empty symbols in root"
        assert comp.source_block  # identity preserved


def test_compact_mode_creates_sub_models(compact_repo):
    run_pipeline(compact_repo, compact=True)

    f1 = load_block_model(compact_repo, "S1")
    assert f1 is not None


def test_non_compact_mode_preserves_root(compact_repo):
    """Without compact=True, root model stays as-is."""
    run_pipeline(compact_repo, compact=False)

    root = load_model(str(compact_repo / ".architecture-model.yaml"))
    comps = root.entities.components if hasattr(root.entities, "components") else root.entities.get("components", [])
    assert len(comps) == 2
