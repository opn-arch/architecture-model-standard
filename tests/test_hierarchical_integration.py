"""Integration: pipeline produces hierarchical model, slicer loads sub-models."""
import pytest
from pathlib import Path
from architecture_model.core.parser import load_model, load_block_model
from architecture_model.core.slicer import slice_by_fblock
from architecture_model.orchestration.pipeline import run_pipeline


@pytest.fixture
def hierarchical_repo(tmp_path):
    """Create a repo with config, model, and source — run pipeline to produce hierarchy."""
    (tmp_path / "architecture.yaml").write_text("""
project: hierarchy-test
functional_blocks:
  F1:
    name: Core
    dirs: [core]
  F2:
    name: Web
    dirs: [web]
""")
    (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: hierarchy-test
  schema_version: '1.3'
functional_blocks:
  F1:
    name: Core
    dirs: [core]
  F2:
    name: Web
    dirs: [web]
entities:
  components:
    - id: COMP-1
      name: Database
      status: ACTIVE
      f_block: F1
      files: [core/db.py]
    - id: COMP-2
      name: Server
      status: ACTIVE
      f_block: F2
      files: [web/server.py]
  capabilities:
    - id: CAP-1
      name: Data Storage
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
  - from: COMP-2
    to: COMP-1
    type: depends-on
""")
    core = tmp_path / "core"
    core.mkdir()
    (core / "db.py").write_text('''
"""Database connection and query execution."""
MAX_CONNECTIONS = 10

class Database:
    """Manages database connections."""
    def query(self, sql: str) -> list:
        """Execute a SQL query."""
        return []
    def connect(self) -> None:
        """Open a connection."""
        pass
''')
    web = tmp_path / "web"
    web.mkdir()
    (web / "server.py").write_text('''
"""HTTP server handling requests."""

class Server:
    """HTTP request handler."""
    def handle(self, request: dict) -> dict:
        """Handle an HTTP request."""
        return {}
    def start(self, port: int) -> None:
        """Start listening on port."""
        pass
''')
    return tmp_path


def test_pipeline_creates_hierarchy(hierarchical_repo):
    """Pipeline with compact=True produces compact root + sub-models."""
    run_pipeline(hierarchical_repo, compact=True)

    # Root should exist and be compact
    root = load_model(str(hierarchical_repo / ".architecture-model.yaml"))
    root_comps = root.entities.components if hasattr(root.entities, "components") else root.entities.get("components", [])
    assert len(root_comps) == 2
    for comp in root_comps:
        assert comp.signatures == [], f"{comp.name} should have no signatures in root"
        assert comp.symbols == [], f"{comp.name} should have no symbols in root"

    # Sub-models should exist
    f1 = load_block_model(hierarchical_repo, "F1")
    assert f1 is not None


def test_slicer_returns_rich_sub_model(hierarchical_repo):
    """After pipeline with compact, slicer should return sub-model with detail."""
    run_pipeline(hierarchical_repo, compact=True)

    root = load_model(str(hierarchical_repo / ".architecture-model.yaml"))
    sliced = slice_by_fblock(root, "F1", project_root=hierarchical_repo)

    comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
    assert len(comps) >= 1
    # Sub-model should have the Database component
    db = next((c for c in comps if c.name == "Database"), None)
    assert db is not None


def test_root_smaller_than_sub_models(hierarchical_repo):
    """Compact root should be smaller than combined sub-models."""
    run_pipeline(hierarchical_repo, compact=True)

    root_path = hierarchical_repo / ".architecture-model.yaml"
    root_size = root_path.stat().st_size

    sub_paths = list(hierarchical_repo.glob(".architecture-models/*/.architecture-model.yaml"))
    assert len(sub_paths) >= 1
    sub_size = sum(p.stat().st_size for p in sub_paths)

    # Root should be smaller (it's stripped of detail)
    assert root_size < sub_size, f"Root ({root_size}B) should be < sub-models ({sub_size}B)"
