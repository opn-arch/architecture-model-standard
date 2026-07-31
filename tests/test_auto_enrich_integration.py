"""Integration test: auto-enrichment boosts component confidence."""
from pathlib import Path

from architecture_model.manifest.scanner import scan_file
from architecture_model.manifest.types import Manifest
from architecture_model.core.types import Component
from architecture_model.core.confidence import compute_component_confidence
from architecture_model.orchestration.auto_enrich import enrich_from_manifest


def test_enrichment_boosts_confidence(tmp_path: Path):
    """Create a small documented Python repo, generate manifest, enrich model, verify confidence jumps."""
    # 1. Create a Python file with typed functions, docstrings, constants, a class
    code = '''\
"""Service module for handling user accounts."""

MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30


class UserService:
    """Manages user lifecycle operations."""

    def __init__(self, db):
        self.db = db

    def create_user(self, name: str, email: str) -> dict:
        """Create a new user account."""
        return self.db.insert({"name": name, "email": email})

    def get_user(self, user_id: int) -> dict:
        """Retrieve user by ID."""
        return self.db.find(user_id)

    def delete_user(self, user_id: int) -> bool:
        """Delete a user account."""
        return self.db.delete(user_id)


def validate_email(email: str) -> bool:
    """Check if email format is valid."""
    return "@" in email


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return f"hashed_{password}"
'''
    src_file = tmp_path / "user_service.py"
    src_file.write_text(code)

    # 2. Generate manifest by scanning the file directly
    module_info = scan_file(tmp_path, src_file)
    manifest = Manifest(
        generated_at="2024-01-01",
        project_root=str(tmp_path),
        modules=[module_info],
        functional_blocks={},
        interfaces=[],
        metrics=None,
    )

    # 3. Create a minimal model with one Component pointing to that file
    comp = Component(
        id="COMP-1",
        name="UserService",
        status="ACTIVE",
        files=["user_service.py"],
    )

    class _FakeModel:
        def __init__(self):
            self.entities = {"components": [comp], "behaviors": []}

    model = _FakeModel()

    # 4. Compute confidence before enrichment — should be low (only files)
    before = compute_component_confidence(comp)
    assert before < 0.15, f"Expected low confidence before enrichment, got {before}"

    # 5. Enrich from manifest
    enrich_from_manifest(model, manifest)

    # 6. Compute confidence after enrichment — should be significantly higher
    after = compute_component_confidence(comp)
    assert after > 0.40, f"Expected confidence > 0.40 after enrichment, got {after}"
    assert after > before, "Enrichment should increase confidence"

    # 7. Assert fields are populated
    assert comp.signatures, "signatures should be populated"
    assert comp.symbols, "symbols should be populated"
    assert comp.constants, "constants should be populated"
    assert comp.contract, "contract should be populated"
