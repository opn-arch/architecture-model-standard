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
        """With 2+ small groups, flat-repo fallback promotes each to its own F-block."""
        groups = [
            ModuleGroup(name="A", modules=["a.py"], primary_file="a.py"),
            ModuleGroup(name="B", modules=["b.py"], primary_file="b.py"),
        ]
        result = auto_fblocks(groups, threshold=3)
        # Flat-repo fallback: each group becomes its own F-block
        assert "F1" in result
        assert "F2" in result
        assert result["F1"]["files"] == ["a.py"]
        assert result["F2"]["files"] == ["b.py"]

    def test_flat_repo_fallback_promotes_groups(self):
        """When all groups are below threshold, promote each to its own F-block."""
        # 6 single-file groups (flat repo scenario)
        groups = [
            ModuleGroup(name="app", modules=["src/app.py"], primary_file="src/app.py"),
            ModuleGroup(name="models", modules=["src/models.py"], primary_file="src/models.py"),
            ModuleGroup(name="views", modules=["src/views.py"], primary_file="src/views.py"),
            ModuleGroup(name="utils", modules=["src/utils.py"], primary_file="src/utils.py"),
            ModuleGroup(name="config", modules=["src/config.py"], primary_file="src/config.py"),
            ModuleGroup(name="auth", modules=["src/auth.py"], primary_file="src/auth.py"),
        ]

        result = auto_fblocks(groups, threshold=3)

        # Should NOT collapse everything to F0
        assert len(result) > 1, f"Expected multiple F-blocks, got: {list(result.keys())}"
        # All files should be assigned somewhere
        all_files = []
        for v in result.values():
            all_files.extend(v["files"])
        assert len(all_files) == 6

    def test_flat_repo_fallback_not_triggered_when_fblocks_exist(self):
        """When some groups meet threshold, normal behavior applies."""
        groups = [
            ModuleGroup(name="core", modules=["a.py", "b.py", "c.py"], primary_file="a.py"),
            ModuleGroup(name="small", modules=["d.py"], primary_file="d.py"),
        ]

        result = auto_fblocks(groups, threshold=3)

        # "core" meets threshold -> F1, "small" -> F0
        assert "F1" in result
        assert "F0" in result

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
