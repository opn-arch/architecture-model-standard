"""Tests for fblock_override parameter in generate_recursive_manifests."""
import tempfile
from pathlib import Path

from architecture_model.manifest.recursive import generate_recursive_manifests


def _make_repo(tmp_path: Path) -> Path:
    """Create a minimal repo with two packages."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("def main(): pass\n")
    (pkg / "utils.py").write_text("def helper(): pass\n")
    sub = pkg / "api"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "views.py").write_text("from myapp.core import main\ndef index(): return main()\n")
    (sub / "routes.py").write_text("def setup(): pass\n")
    return tmp_path


class TestFblockOverride:
    def test_override_produces_block_manifests(self, tmp_path):
        repo = _make_repo(tmp_path)
        override = {
            "F1": {"name": "Core", "dirs": ["myapp"], "files": []},
            "F2": {"name": "API", "dirs": ["myapp/api"], "files": []},
        }
        results = generate_recursive_manifests(repo, fblock_override=override)
        assert "F1" in results
        assert "F2" in results
        assert results["F1"].block_name == "Core"
        assert results["F2"].block_name == "API"

    def test_override_bypasses_config(self, tmp_path):
        """Even without .architecture-model.yaml, override works."""
        repo = _make_repo(tmp_path)
        override = {
            "F1": {"name": "All", "dirs": ["myapp"], "files": []},
        }
        results = generate_recursive_manifests(repo, fblock_override=override)
        assert len(results) == 1
        assert len(results["F1"].manifest.modules) >= 3

    def test_override_empty_dict_returns_empty(self, tmp_path):
        repo = _make_repo(tmp_path)
        results = generate_recursive_manifests(repo, fblock_override={})
        assert results == {}

    def test_override_with_files_list(self, tmp_path):
        repo = _make_repo(tmp_path)
        override = {
            "F1": {"name": "JustCore", "dirs": [], "files": ["myapp/core.py", "myapp/utils.py"]},
        }
        results = generate_recursive_manifests(repo, fblock_override=override)
        assert len(results["F1"].manifest.modules) == 2
