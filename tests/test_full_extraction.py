"""Tests for full extraction pipeline."""
import pytest
from pathlib import Path
from architecture_model.orchestration.full_extraction import full_extraction


class TestFullExtraction:
    def test_produces_model_with_components(self, tmp_path):
        """Pipeline produces a model with components."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "models.py").write_text(
            "class User:\n    pass\n\nclass Order:\n    pass\n"
        )
        (tmp_path / "app" / "services.py").write_text(
            "from app.models import User\n\ndef get_user():\n    return User()\n\ndef process():\n    get_user()\n"
        )
        
        model = full_extraction(tmp_path)
        assert model.meta.project == tmp_path.name
        assert len(model.entities.components) >= 1

    def test_produces_behaviors_from_routers(self, tmp_path):
        """Pipeline detects behaviors from router modules."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "routers").mkdir()
        (tmp_path / "app" / "routers" / "__init__.py").write_text("")
        (tmp_path / "app" / "routers" / "users.py").write_text(
            "def get_user(user_id: int):\n    return {'id': user_id}\n\ndef create_user(name: str):\n    return {'name': name}\n"
        )
        
        model = full_extraction(tmp_path)
        assert len(model.entities.behaviors) >= 1

    def test_detects_systems(self, tmp_path):
        """Pipeline identifies system boundaries."""
        for subdir in ["billing", "notifications"]:
            d = tmp_path / subdir
            d.mkdir()
            (d / "__init__.py").write_text("")
            (d / "main.py").write_text(f"def run_{subdir}():\n    pass\n")
        
        model = full_extraction(tmp_path)
        assert len(model.entities.systems) >= 1

    def test_infers_capabilities(self, tmp_path):
        """Pipeline creates capabilities from behavior triggers."""
        (tmp_path / "routers").mkdir()
        (tmp_path / "routers" / "__init__.py").write_text("")
        (tmp_path / "routers" / "items.py").write_text(
            "def get_items():\n    '''GET /items'''\n    pass\n\ndef create_item():\n    '''POST /items'''\n    pass\n"
        )
        
        model = full_extraction(tmp_path)
        assert model.entities is not None

    def test_empty_repo_returns_empty_model(self, tmp_path):
        """Empty repo produces model with no entities."""
        model = full_extraction(tmp_path)
        assert model.meta.project == tmp_path.name
        assert len(model.entities.components) == 0

    def test_model_has_correct_meta(self, tmp_path):
        """Model meta has correct project name and schema version."""
        (tmp_path / "app.py").write_text("def main(): pass\n")
        model = full_extraction(tmp_path)
        assert model.meta.schema_version == "1.3"
        assert model.meta.project == tmp_path.name
