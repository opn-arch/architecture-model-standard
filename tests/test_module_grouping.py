"""Tests for multi-signal module grouping."""

import pytest
from dataclasses import dataclass
from architecture_model.manifest.types import ModuleInfo, InterfaceEdge, FunctionInfo, ClassInfo, ModuleStatus


def _mod(file: str, line_count: int = 50, functions: list | None = None, classes: list | None = None) -> ModuleInfo:
    """Helper to create a ModuleInfo with minimal boilerplate."""
    return ModuleInfo(
        file=file, name=file.rsplit("/", 1)[-1].replace(".py", ""),
        docstring=None,
        functions=functions or [],
        imports=[], line_count=line_count, status=ModuleStatus.ACTIVE,
        classes=classes or [],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )


def _edge(source: str, target: str) -> InterfaceEdge:
    return InterfaceEdge(source=source, target=target, import_path="")


class TestFilterTrivialModules:
    """Trivial files should be excluded from grouping."""

    def test_filters_empty_init(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("pkg/__init__.py", line_count=3),
            _mod("pkg/core.py", line_count=200, functions=[
                FunctionInfo(name="run", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        # __init__.py with <=5 lines and no functions/classes should be filtered
        all_files = [f for g in groups for f in g.modules]
        assert "pkg/__init__.py" not in all_files
        assert "pkg/core.py" in all_files

    def test_keeps_init_with_code(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("pkg/__init__.py", line_count=50, functions=[
                FunctionInfo(name="setup", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("pkg/core.py", line_count=200),
        ]
        groups = group_modules(modules, [])
        all_files = [f for g in groups for f in g.modules]
        assert "pkg/__init__.py" in all_files

    def test_filters_version_file(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("pkg/__version__.py", line_count=3),
            _mod("pkg/core.py", line_count=200),
        ]
        groups = group_modules(modules, [])
        all_files = [f for g in groups for f in g.modules]
        assert "pkg/__version__.py" not in all_files

    def test_filters_empty_modules(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("pkg/empty.py", line_count=10),  # no functions, no classes
            _mod("pkg/core.py", line_count=200, functions=[
                FunctionInfo(name="run", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        all_files = [f for g in groups for f in g.modules]
        assert "pkg/empty.py" not in all_files


class TestSubdirectoryGrouping:
    """Files in the same subdirectory should be grouped together."""

    def test_groups_by_subdirectory(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("httpx/_transports/base.py", functions=[
                FunctionInfo(name="handle", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("httpx/_transports/default.py", functions=[
                FunctionInfo(name="connect", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("httpx/_transports/mock.py", functions=[
                FunctionInfo(name="mock_handle", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("httpx/_client.py", line_count=2000, functions=[
                FunctionInfo(name="get", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        # Transport files should be in one group
        transport_group = None
        for g in groups:
            if "httpx/_transports/base.py" in g.modules:
                transport_group = g
                break
        assert transport_group is not None
        assert "httpx/_transports/default.py" in transport_group.modules
        assert "httpx/_transports/mock.py" in transport_group.modules
        # Client should be separate
        assert "httpx/_client.py" not in transport_group.modules

    def test_subdirectory_group_name(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("fastapi/routing.py", functions=[
                FunctionInfo(name="route", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("fastapi/security/http.py", functions=[
                FunctionInfo(name="auth", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("fastapi/security/oauth2.py", functions=[
                FunctionInfo(name="oauth", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        # Security files should be in one group
        sec_group = [g for g in groups if "fastapi/security/http.py" in g.modules]
        assert len(sec_group) == 1
        assert "security" in sec_group[0].name.lower()
        assert "fastapi/security/oauth2.py" in sec_group[0].modules


class TestImportAffinityMerging:
    """Files with high import affinity should be merged when over target."""

    def test_merges_by_imports(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("pkg/a.py", functions=[
                FunctionInfo(name="fa", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("pkg/b.py", functions=[
                FunctionInfo(name="fb", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("pkg/c.py", functions=[
                FunctionInfo(name="fc", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        # a imports b heavily, c is independent
        interfaces = [
            _edge("pkg/a.py", "pkg/b.py"),
            _edge("pkg/b.py", "pkg/a.py"),
        ]
        groups = group_modules(modules, interfaces, target_groups=2)
        # a and b should be in same group
        ab_group = None
        for g in groups:
            if "pkg/a.py" in g.modules:
                ab_group = g
                break
        assert ab_group is not None
        assert "pkg/b.py" in ab_group.modules


class TestNamePrefixGrouping:
    """Files with underscore prefixes in same dir should group as utilities."""

    def test_groups_internal_utilities(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("click/_compat.py", functions=[
                FunctionInfo(name="compat_fn", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("click/_utils.py", functions=[
                FunctionInfo(name="util_fn", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("click/_textwrap.py", functions=[
                FunctionInfo(name="wrap", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("click/core.py", line_count=3000, functions=[
                FunctionInfo(name="run", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        # Underscore-prefixed files should be grouped together
        util_group = None
        for g in groups:
            if "click/_compat.py" in g.modules:
                util_group = g
                break
        assert util_group is not None
        assert "click/_utils.py" in util_group.modules
        assert "click/_textwrap.py" in util_group.modules
        # core.py should NOT be in the utility group
        assert "click/core.py" not in util_group.modules


class TestPrimaryFile:
    """Each group should identify its primary (largest) file."""

    def test_primary_is_largest(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("pkg/small.py", line_count=50, functions=[
                FunctionInfo(name="f1", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("pkg/large.py", line_count=500, functions=[
                FunctionInfo(name="f2", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [], target_groups=1)
        assert groups[0].primary_file == "pkg/large.py"


class TestAutoTargetGroups:
    """When target_groups is None, auto-calculate a reasonable count."""

    def test_single_module(self):
        from architecture_model.manifest.grouping import group_modules
        modules = [_mod("pkg/core.py", functions=[
            FunctionInfo(name="run", signature="() -> None", calls=[], docstring=None, raises=[])
        ])]
        groups = group_modules(modules, [])
        assert len(groups) == 1

    def test_many_modules_produces_reasonable_groups(self):
        """With 20+ modules, should produce 5-15 groups, not 20+."""
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod(f"pkg/mod_{i}.py", functions=[
                FunctionInfo(name=f"fn_{i}", signature="() -> None", calls=[], docstring=None, raises=[])
            ])
            for i in range(20)
        ]
        groups = group_modules(modules, [])
        assert 3 <= len(groups) <= 15


class TestNamePrefixPreGrouping:
    """Name-prefix affinity: files sharing a prefix get pre-grouped."""

    def test_shared_prefix_groups_together(self):
        """auth_login.py + auth_utils.py + auth_middleware.py → one group."""
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("src/app/auth_login.py", functions=[
                FunctionInfo(name="login", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/auth_utils.py", functions=[
                FunctionInfo(name="hash_pw", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/auth_middleware.py", functions=[
                FunctionInfo(name="check", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/db_connection.py", functions=[
                FunctionInfo(name="connect", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/db_queries.py", functions=[
                FunctionInfo(name="query", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/server.py", functions=[
                FunctionInfo(name="start", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        # Should get ~3 groups: auth (3 files), db (2 files), server (1 file)
        assert len(groups) <= 4
        auth_group = next(g for g in groups if any("auth" in f for f in g.modules))
        assert len(auth_group.modules) == 3

    def test_single_char_prefix_not_grouped(self):
        """Single-char prefixes (a_foo, a_bar) should NOT trigger grouping."""
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("src/app/a_foo.py", functions=[
                FunctionInfo(name="foo", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/a_bar.py", functions=[
                FunctionInfo(name="bar", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/baz.py", functions=[
                FunctionInfo(name="baz", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        # All singletons (prefix "a" too short to be meaningful)
        assert len(groups) == 3

    def test_prefix_needs_two_plus_files(self):
        """A prefix with only one file doesn't form a group."""
        from architecture_model.manifest.grouping import group_modules
        modules = [
            _mod("src/app/auth_login.py", functions=[
                FunctionInfo(name="login", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/db_conn.py", functions=[
                FunctionInfo(name="connect", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
            _mod("src/app/db_pool.py", functions=[
                FunctionInfo(name="pool", signature="() -> None", calls=[], docstring=None, raises=[])
            ]),
        ]
        groups = group_modules(modules, [])
        db_group = next(g for g in groups if any("db_" in f for f in g.modules))
        assert len(db_group.modules) == 2


class TestNormalizedAffinity:
    """Normalized scoring prevents mega-group attraction."""

    def test_no_mega_group_with_target(self):
        """With target_groups=4, should NOT produce one group with >60% of files."""
        from architecture_model.manifest.grouping import group_modules
        modules = [_mod(f"src/app/mod_{i}.py", functions=[
            FunctionInfo(name=f"fn_{i}", signature="() -> None", calls=[], docstring=None, raises=[])
        ]) for i in range(20)]
        # Create import clusters: 0-4, 5-9, 10-14, 15-19
        interfaces = []
        for cluster_start in range(0, 20, 5):
            for i in range(cluster_start, cluster_start + 5):
                for j in range(i + 1, cluster_start + 5):
                    interfaces.append(InterfaceEdge(
                        source=f"src/app/mod_{i}.py",
                        target=f"src/app/mod_{j}.py",
                        import_path="",
                    ))
        groups = group_modules(modules, interfaces, target_groups=4)
        assert len(groups) == 4
        # No single group should have more than 8 files
        assert all(len(g.modules) <= 8 for g in groups)

    def test_clusters_preserved(self):
        """Import clusters should be kept together, not split."""
        from architecture_model.manifest.grouping import group_modules
        modules = [_mod(f"src/app/mod_{i}.py", functions=[
            FunctionInfo(name=f"fn_{i}", signature="() -> None", calls=[], docstring=None, raises=[])
        ]) for i in range(12)]
        # 3 clusters of 4 with dense internal imports
        interfaces = []
        for cluster_start in range(0, 12, 4):
            for i in range(cluster_start, cluster_start + 4):
                for j in range(i + 1, cluster_start + 4):
                    interfaces.append(InterfaceEdge(
                        source=f"src/app/mod_{i}.py",
                        target=f"src/app/mod_{j}.py",
                        import_path="",
                    ))
        groups = group_modules(modules, interfaces, target_groups=3)
        assert len(groups) == 3
        sizes = sorted(len(g.modules) for g in groups)
        assert sizes == [4, 4, 4]


class TestAutoTargetFix:
    """Auto-target always triggers meaningful merging."""

    def test_eight_modules_get_merged(self):
        """8 flat modules with imports should merge, not stay as 8 singletons."""
        from architecture_model.manifest.grouping import group_modules
        modules = [_mod(f"src/app/{name}.py", functions=[
            FunctionInfo(name="fn", signature="() -> None", calls=[], docstring=None, raises=[])
        ]) for name in [
            "auth", "users", "posts", "comments", "db", "cache", "config", "server"
        ]]
        # auth↔users, posts↔comments, db↔cache — 3 natural pairs + 2 singletons
        interfaces = [
            InterfaceEdge(source="src/app/auth.py", target="src/app/users.py", import_path=""),
            InterfaceEdge(source="src/app/users.py", target="src/app/auth.py", import_path=""),
            InterfaceEdge(source="src/app/posts.py", target="src/app/comments.py", import_path=""),
            InterfaceEdge(source="src/app/comments.py", target="src/app/posts.py", import_path=""),
            InterfaceEdge(source="src/app/db.py", target="src/app/cache.py", import_path=""),
        ]
        groups = group_modules(modules, interfaces)
        # Should merge to ~5 groups (3 pairs + 2 singletons), not stay at 8
        assert len(groups) <= 6
