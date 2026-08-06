"""Tests for hierarchical event chain building."""
import pytest
from dataclasses import dataclass, field
from architecture_model.manifest.chains import EventChain, build_block_chains, build_cross_block_chains
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, FunctionInfo, InterfaceEdge, RecursiveManifest, ModuleStatus,
)
from architecture_model.manifest.grouping import ModuleGroup


def _mod(path, name, functions=None, imports=None, classes=None):
    """Helper to build ModuleInfo with defaults."""
    return ModuleInfo(
        file=path, name=name, docstring=None,
        functions=functions or [], imports=imports or [],
        line_count=10, status=ModuleStatus.ACTIVE, classes=classes or [],
    )


def _make_manifest(modules, interfaces=None):
    """Helper to build a Manifest with minimal required fields."""
    return Manifest(
        modules=modules,
        interfaces=interfaces or [],
        functional_blocks={},
        generated_at="2026-01-01T00:00:00",
        project_root="/tmp/test",
        metrics={"total_modules": len(modules)},
    )


class TestBuildBlockChains:
    def test_simple_intra_chain(self):
        """Call from module A func to module B func within same block."""
        modules = [
            _mod("block/api.py", "api",
                 functions=[FunctionInfo(
                     name="handle_request", signature="(req) -> Response",
                     call_order=["service.process", "repo.save"],
                 )],
                 imports=["block.service", "block.repo"]),
            _mod("block/service.py", "service",
                 functions=[FunctionInfo(
                     name="process", signature="(data) -> Result",
                     call_order=["validator.check"],
                 )],
                 imports=["block.validator"]),
            _mod("block/repo.py", "repo",
                 functions=[FunctionInfo(name="save", signature="(r) -> None")]),
        ]
        groups = [
            ModuleGroup(name="api", modules=["block/api.py"], primary_file="block/api.py"),
            ModuleGroup(name="service", modules=["block/service.py"], primary_file="block/service.py"),
            ModuleGroup(name="repo", modules=["block/repo.py"], primary_file="block/repo.py"),
        ]
        manifest = _make_manifest(modules)
        chains = build_block_chains(manifest, groups, block_id="S1")
        assert len(chains) > 0
        # The chain starting from handle_request should span multiple components
        multi_comp = [c for c in chains if len(c.components_involved) >= 2]
        assert len(multi_comp) > 0
        assert all(c.scope == "intra" for c in chains)
        assert all(c.block_id == "S1" for c in chains)

    def test_single_component_no_chains(self):
        """No cross-component chains if everything is in one group."""
        modules = [
            _mod("pkg/a.py", "a",
                 functions=[FunctionInfo(name="run", signature="()", call_order=["helper"])]),
            _mod("pkg/b.py", "b",
                 functions=[FunctionInfo(name="helper", signature="()")]),
        ]
        groups = [
            ModuleGroup(name="pkg", modules=["pkg/a.py", "pkg/b.py"], primary_file="pkg/a.py"),
        ]
        manifest = _make_manifest(modules)
        chains = build_block_chains(manifest, groups, block_id="S1")
        # All calls within one component - no cross-component chains
        cross_comp = [c for c in chains if len(c.components_involved) >= 2]
        assert cross_comp == []


class TestBuildCrossBlockChains:
    def test_cross_block_chain(self):
        """Call from S1 module that resolves to S2 module creates cross-block chain."""
        f1_modules = [
            _mod("f1/handler.py", "handler",
                 functions=[FunctionInfo(
                     name="handle", signature="()", call_order=["auth.verify"],
                 )],
                 imports=["f2.auth"]),
        ]
        f2_modules = [
            _mod("f2/auth.py", "auth",
                 functions=[FunctionInfo(name="verify", signature="()")]),
        ]
        f1_manifest = _make_manifest(f1_modules)
        f2_manifest = _make_manifest(f2_modules)

        recursive_manifests = {
            "S1": RecursiveManifest(
                block_id="S1", block_name="handlers", parent_model="model.yaml",
                component_id="COMP-1", manifest=f1_manifest,
                block_dependencies=["S2"],
            ),
            "S2": RecursiveManifest(
                block_id="S2", block_name="auth", parent_model="model.yaml",
                component_id="COMP-2", manifest=f2_manifest,
            ),
        }
        block_groups = {
            "S1": [ModuleGroup(name="handler", modules=["f1/handler.py"], primary_file="f1/handler.py")],
            "S2": [ModuleGroup(name="auth", modules=["f2/auth.py"], primary_file="f2/auth.py")],
        }

        chains = build_cross_block_chains(recursive_manifests, block_groups)
        assert len(chains) > 0
        assert all(c.scope == "cross" for c in chains)

    def test_no_cross_block_when_internal(self):
        """No cross-block chains when all calls are internal."""
        modules = [
            _mod("f1/a.py", "a",
                 functions=[FunctionInfo(name="run", signature="()", call_order=["helper"])]),
            _mod("f1/b.py", "b",
                 functions=[FunctionInfo(name="helper", signature="()")]),
        ]
        manifest = _make_manifest(modules)
        recursive_manifests = {
            "S1": RecursiveManifest(
                block_id="S1", block_name="core", parent_model="model.yaml",
                component_id="COMP-1", manifest=manifest,
            ),
        }
        block_groups = {
            "S1": [ModuleGroup(name="core", modules=["f1/a.py", "f1/b.py"], primary_file="f1/a.py")],
        }
        chains = build_cross_block_chains(recursive_manifests, block_groups)
        assert chains == []
