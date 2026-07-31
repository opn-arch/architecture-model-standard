"""Test that manifest scanner extracts typed method signatures."""
from architecture_model.manifest.generator import generate_manifest
from architecture_model.manifest.types import ClassInfo, FunctionInfo


def test_class_method_details_extracted(tmp_path):
    """ClassInfo.method_details should contain FunctionInfo with typed signatures."""
    pkg = tmp_path / "src" / "myapp"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "service.py").write_text('''
class UserService:
    """Manages user operations."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, name: str, email: str) -> User:
        """Create a new user."""
        ...

    def delete(self, user_id: int) -> bool:
        """Delete a user by ID."""
        ...

    def _internal(self) -> None:
        ...
''')
    manifest = generate_manifest(tmp_path)
    assert len(manifest.modules) >= 1

    mod = next(m for m in manifest.modules if "service" in m.file)
    assert len(mod.classes) == 1
    cls = mod.classes[0]

    assert cls.name == "UserService"
    # Old field still works
    assert "create" in cls.methods
    assert "delete" in cls.methods

    # New field has full details
    assert len(cls.method_details) >= 2
    create_info = next(m for m in cls.method_details if m.name == "create")
    assert "name: str" in create_info.signature
    assert "User" in create_info.signature
    assert create_info.docstring == "Create a new user."


def test_method_details_empty_by_default():
    """ClassInfo without method_details should default to empty list."""
    ci = ClassInfo(name="Foo", bases=[], methods=["bar"], is_abstract=False, decorators=[], attributes={})
    assert ci.method_details == []
