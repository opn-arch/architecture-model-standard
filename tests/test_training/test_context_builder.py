"""Tests for AST-guided context builder."""
import pytest
from pathlib import Path
from architecture_model.training.context_builder import ContextBuilder, ContextSlices


@pytest.fixture
def sample_repo(tmp_path):
    """Create a minimal repo structure for testing."""
    # Create package structure
    (tmp_path / "src" / "myapp").mkdir(parents=True)
    (tmp_path / "src" / "myapp" / "__init__.py").write_text("")
    (tmp_path / "src" / "myapp" / "api").mkdir()
    (tmp_path / "src" / "myapp" / "api" / "__init__.py").write_text(
        "from django.urls import path\n"
    )
    (tmp_path / "src" / "myapp" / "api" / "views.py").write_text(
        "from rest_framework.views import APIView\n\n"
        "class UserEndpoint(APIView):\n"
        "    def get(self, request): pass\n"
    )
    (tmp_path / "src" / "myapp" / "models").mkdir()
    (tmp_path / "src" / "myapp" / "models" / "__init__.py").write_text("")
    (tmp_path / "src" / "myapp" / "models" / "user.py").write_text(
        "from django.db import models\n\n"
        "class User(models.Model):\n"
        "    name = models.CharField(max_length=100)\n"
    )
    (tmp_path / "src" / "myapp" / "tasks.py").write_text(
        "from celery import shared_task\n\n"
        "@shared_task\n"
        "def send_email(user_id: int): pass\n"
    )
    (tmp_path / "src" / "myapp" / "services").mkdir()
    (tmp_path / "src" / "myapp" / "services" / "__init__.py").write_text("")
    (tmp_path / "src" / "myapp" / "services" / "email.py").write_text(
        "class EmailService:\n"
        "    def send(self, to: str, body: str): pass\n"
    )
    (tmp_path / "src" / "myapp" / "wsgi.py").write_text(
        "from django.core.wsgi import get_wsgi_application\n"
        "application = get_wsgi_application()\n"
    )
    (tmp_path / "src" / "myapp" / "settings.py").write_text(
        "DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql'}}\n"
        "CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache'}}\n"
        "CELERY_BROKER_URL = 'redis://localhost:6379'\n"
    )
    return tmp_path / "src" / "myapp"


class TestContextSlices:
    def test_slices_has_required_fields(self):
        """ContextSlices has all 5 pass-specific slices."""
        slices = ContextSlices(
            structure="dir tree",
            boundaries="api endpoints",
            behavior="tasks and workflows",
            relationships="import graph",
            constraints="configs",
        )
        assert slices.structure
        assert slices.boundaries
        assert slices.behavior
        assert slices.relationships
        assert slices.constraints

    def test_slices_combined(self):
        """combined() returns all slices joined."""
        slices = ContextSlices(
            structure="A", boundaries="B", behavior="C",
            relationships="D", constraints="E",
        )
        combined = slices.combined()
        assert "A" in combined and "E" in combined


class TestContextBuilder:
    def test_init(self, sample_repo):
        """ContextBuilder accepts repo path and max_chars."""
        cb = ContextBuilder(sample_repo, max_chars=10000)
        assert cb.repo_path == sample_repo

    def test_build_returns_slices(self, sample_repo):
        """build() returns a ContextSlices object."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert isinstance(slices, ContextSlices)

    def test_structure_slice_contains_dir_tree(self, sample_repo):
        """Structure slice includes directory listing."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "api" in slices.structure
        assert "models" in slices.structure
        assert "services" in slices.structure

    def test_boundaries_slice_finds_api_classes(self, sample_repo):
        """Boundaries slice identifies API endpoint classes."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "UserEndpoint" in slices.boundaries or "APIView" in slices.boundaries

    def test_behavior_slice_finds_tasks(self, sample_repo):
        """Behavior slice identifies async tasks."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "send_email" in slices.behavior or "shared_task" in slices.behavior

    def test_constraints_slice_finds_config(self, sample_repo):
        """Constraints slice identifies infrastructure from config."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "postgresql" in slices.constraints.lower() or "DATABASES" in slices.constraints

    def test_relationships_slice_has_imports(self, sample_repo):
        """Relationships slice includes import graph info."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "import" in slices.relationships.lower() or "depends" in slices.relationships.lower()

    def test_respects_max_chars(self, sample_repo):
        """Total context respects max_chars limit."""
        cb = ContextBuilder(sample_repo, max_chars=500)
        slices = cb.build()
        total = len(slices.combined())
        # Allow some overflow for headers but should be reasonable
        assert total < 2000  # 4x max_chars as upper bound

    def test_large_repo_prioritizes_significant_files(self, tmp_path):
        """Context builder should prioritize architecturally significant files in large repos."""
        # Create architecturally significant files at root
        (tmp_path / "__init__.py").write_text("from .core import *\nfrom .client import *")
        (tmp_path / "core.py").write_text("class CoreEngine:\n    def run(self): pass\n    def stop(self): pass\n    def process(self): pass\n" * 5)
        (tmp_path / "base.py").write_text("class BaseHandler:\n    def handle(self): pass\n" * 5)
        (tmp_path / "client.py").write_text("class HTTPClient:\n    def get(self): pass\n    def post(self): pass\n" * 3)

        # Create 150 filler files in a directory that sorts BEFORE the important files
        # alphabetically ("aaa_plugins" < "base", "client", "core")
        sub = tmp_path / "aaa_plugins" / "contrib"
        sub.mkdir(parents=True)
        (sub / "__init__.py").write_text("")
        for i in range(150):
            (sub / f"plugin_{i:03d}.py").write_text(f"# plugin {i}\nclass P{i}: pass\n")

        cb = ContextBuilder(tmp_path)
        files = cb._iter_py_files(max_files=50)

        # Core files should be in the top 50 despite 150+ total files
        file_names = [f.name for f in files]
        assert "core.py" in file_names
        assert "base.py" in file_names
        assert "client.py" in file_names
