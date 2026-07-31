"""Tests for auto_fblocks generation."""
import pytest
from architecture_model.manifest.grouping import auto_fblocks, ModuleGroup


class TestAutoFblocks:
    def test_large_groups_become_fblocks(self):
        groups = [
            ModuleGroup(name="Auth", modules=["auth/login.py", "auth/session.py", "auth/tokens.py"],
                       primary_file="auth/login.py"),
            ModuleGroup(name="API", modules=["api/routes.py", "api/models.py", "api/views.py", "api/utils.py"],
                       primary_file="api/routes.py"),
        ]
        result = auto_fblocks(groups, threshold=3)
        assert "F1" in result
        assert "F2" in result
        assert result["F1"]["name"] == "Auth"
        assert result["F2"]["name"] == "API"
        assert len(result["F2"]["files"]) == 4

    def test_small_groups_merged_to_shared(self):
        groups = [
            ModuleGroup(name="Auth", modules=["auth/login.py", "auth/session.py", "auth/tokens.py"],
                       primary_file="auth/login.py"),
            ModuleGroup(name="Utils", modules=["utils.py"], primary_file="utils.py"),
            ModuleGroup(name="Config", modules=["config.py", "settings.py"], primary_file="config.py"),
        ]
        result = auto_fblocks(groups, threshold=3)
        assert "F1" in result  # Auth
        assert "F0" in result  # Shared (Utils + Config merged)
        assert "utils.py" in result["F0"]["files"]
        assert "config.py" in result["F0"]["files"]
        assert len(result["F0"]["files"]) == 3

    def test_common_dir_detected(self):
        groups = [
            ModuleGroup(name="Backend", modules=["src/backend/api.py", "src/backend/models.py", "src/backend/db.py"],
                       primary_file="src/backend/api.py"),
        ]
        result = auto_fblocks(groups)
        assert result["F1"]["dirs"] == ["src/backend"]

    def test_no_common_dir_when_mixed(self):
        groups = [
            ModuleGroup(name="Mixed", modules=["auth/login.py", "api/routes.py", "utils/helpers.py"],
                       primary_file="auth/login.py"),
        ]
        result = auto_fblocks(groups)
        assert result["F1"]["dirs"] == [] or result["F1"]["dirs"] == [""]

    def test_empty_groups(self):
        result = auto_fblocks([])
        assert result == {}

    def test_all_small_groups(self):
        groups = [
            ModuleGroup(name="A", modules=["a.py"], primary_file="a.py"),
            ModuleGroup(name="B", modules=["b.py"], primary_file="b.py"),
        ]
        result = auto_fblocks(groups, threshold=3)
        assert "F0" in result
        assert len(result) == 1  # Only Shared block
        assert set(result["F0"]["files"]) == {"a.py", "b.py"}

    def test_threshold_customizable(self):
        groups = [
            ModuleGroup(name="Small", modules=["a.py", "b.py"], primary_file="a.py"),
        ]
        # With threshold=2, this becomes an F-block
        result = auto_fblocks(groups, threshold=2)
        assert "F1" in result
        # With threshold=3, it goes to Shared
        result2 = auto_fblocks(groups, threshold=3)
        assert "F0" in result2
        assert "F1" not in result2
