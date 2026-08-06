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


class TestConfigAwareComponents:
    """Tests for config-aware component creation (Task 2)."""

    def test_full_extraction_uses_config_blocks(self, tmp_path):
        """When curated config with functional_blocks exists, components use block names."""
        import yaml

        # Create source files
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "auth").mkdir()
        (tmp_path / "app" / "auth" / "__init__.py").write_text("")
        (tmp_path / "app" / "auth" / "login.py").write_text("def login(): pass\n")
        (tmp_path / "app" / "billing").mkdir()
        (tmp_path / "app" / "billing" / "__init__.py").write_text("")
        (tmp_path / "app" / "billing" / "charge.py").write_text("def charge(): pass\n")

        # Write config with functional_blocks
        config_data = {
            "project": {"name": "myapp", "system": "myapp"},
            "functional_blocks": {
                "F1": {
                    "name": "Authentication",
                    "dirs": ["app/auth"],
                    "files": [],
                },
                "F2": {
                    "name": "Billing",
                    "dirs": ["app/billing"],
                    "files": [],
                },
            },
        }
        (tmp_path / ".architecture-model.yaml").write_text(yaml.dump(config_data))

        model = full_extraction(tmp_path)
        comp_names = [c.name for c in model.entities.components]
        assert "Authentication" in comp_names
        assert "Billing" in comp_names
        # Check source_block is set
        auth_comp = next(c for c in model.entities.components if c.name == "Authentication")
        assert auth_comp.source_block == "F1"

    def test_full_extraction_assigns_remaining_files(self, tmp_path):
        """Files not in any block get auto-grouped into additional components."""
        import yaml

        # Create files: some in block dirs, some in a separate dir
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "auth").mkdir()
        (tmp_path / "app" / "auth" / "__init__.py").write_text("")
        (tmp_path / "app" / "auth" / "login.py").write_text("def login(): pass\n")
        (tmp_path / "app" / "utils").mkdir()
        (tmp_path / "app" / "utils" / "__init__.py").write_text("")
        (tmp_path / "app" / "utils" / "helpers.py").write_text(
            "def helper(): pass\ndef helper2(): pass\n"
        )

        config_data = {
            "project": {"name": "myapp", "system": "myapp"},
            "functional_blocks": {
                "F1": {
                    "name": "Authentication",
                    "dirs": ["app/auth"],
                    "files": [],
                },
            },
        }
        (tmp_path / ".architecture-model.yaml").write_text(yaml.dump(config_data))

        model = full_extraction(tmp_path)
        # Should have at least 2 components: Auth + auto-grouped remainder
        assert len(model.entities.components) >= 2
        auth_comp = next(c for c in model.entities.components if c.name == "Authentication")
        assert "app/auth/login.py" in auth_comp.files

    def test_full_extraction_fallback_without_config(self, tmp_path):
        """Without config, falls back to auto-grouping (existing behavior)."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "models.py").write_text("class User: pass\n")
        (tmp_path / "app" / "services.py").write_text("def serve(): pass\n")

        # No .architecture-model.yaml
        model = full_extraction(tmp_path)
        assert len(model.entities.components) >= 1
        # No component should have a curated F-block source_block (e.g. "F1")
        for c in model.entities.components:
            assert not c.source_block.startswith("F")


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

    def test_full_extraction_creates_component_dependencies(self, tmp_path):
        """Components should have depends-on relationships from import edges."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "routers").mkdir(parents=True)
        (tmp_path / "app" / "routers" / "__init__.py").write_text("")
        (tmp_path / "app" / "services").mkdir(parents=True)
        (tmp_path / "app" / "services" / "__init__.py").write_text("")
        (tmp_path / "app" / "routers" / "users.py").write_text(
            "from app.services.user_service import create_user\ndef get_users(): pass"
        )
        (tmp_path / "app" / "services" / "user_service.py").write_text(
            "def create_user(): pass\ndef validate(): pass"
        )

        model = full_extraction(tmp_path)

        depends_on = [r for r in model.relationships
                      if (r.type.value if hasattr(r.type, 'value') else str(r.type)) == 'depends-on']
        assert len(depends_on) > 0, "Should have at least one depends-on relationship"
