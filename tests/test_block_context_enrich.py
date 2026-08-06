"""Test block-context-aware enrichment."""
import pytest
from pathlib import Path
from architecture_model.core.types import Component, Status
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, FunctionInfo, ClassInfo, MetricsResult,
    ScanReport, ModuleStatus, RecursiveManifest,
)
from architecture_model.orchestration.auto_enrich import enrich_with_block_context


def _make_recursive_manifest(block_id, block_name, modules):
    manifest = Manifest(
        generated_at="2026-01-01", project_root="/tmp/test",
        metrics=MetricsResult(values={}), functional_blocks={},
        modules=modules, interfaces=[],
        scan_report=ScanReport(
            files_attempted=len(modules), files_succeeded=len(modules),
            files_failed=0, parse_errors=[], functions_extracted=0,
            classes_extracted=0, constants_extracted=0,
            interfaces_derived=0, blocks_processed=0, unclaimed_files=0,
        ),
    )
    return RecursiveManifest(
        block_id=block_id, block_name=block_name,
        parent_model=".architecture-model.yaml",
        component_id="", manifest=manifest,
        children={}, block_dependencies=[],
    )


def _make_model(components):
    entities_obj = type("Entities", (), {"components": components, "behaviors": []})()
    return type("Model", (), {"entities": entities_obj, "meta": {}, "relationships": []})()


def _make_component(id, name, source_block, files, pattern="", contract=""):
    return Component(
        id=id, name=name, status=Status.ACTIVE,
        source_block=source_block, files=files, pattern=pattern, contract=contract,
    )


class TestBlockPatternPropagation:
    def test_block_pattern_propagates_to_unclassified_components(self):
        """Components without patterns should get the block-level pattern."""
        modules = [
            ModuleInfo(file="plugins/email.py", name="email", docstring=None,
                      functions=[FunctionInfo(name="handle_email", signature="(p) -> dict", calls=[], docstring=None, raises=[])],
                      imports=[], line_count=10, status=ModuleStatus.ACTIVE,
                      classes=[], exports=[], decorated_functions=[], imports_detailed=[],
                      module_constants={}, module_assignments={}),
            ModuleInfo(file="plugins/export.py", name="export", docstring=None,
                      functions=[FunctionInfo(name="handle_export", signature="(p) -> dict", calls=[], docstring=None, raises=[])],
                      imports=[], line_count=10, status=ModuleStatus.ACTIVE,
                      classes=[], exports=[], decorated_functions=[], imports_detailed=[],
                      module_constants={}, module_assignments={}),
            ModuleInfo(file="plugins/cleanup.py", name="cleanup", docstring=None,
                      functions=[FunctionInfo(name="handle_cleanup", signature="(p) -> dict", calls=[], docstring=None, raises=[])],
                      imports=[], line_count=10, status=ModuleStatus.ACTIVE,
                      classes=[], exports=[], decorated_functions=[], imports_detailed=[],
                      module_constants={}, module_assignments={}),
        ]
        rm = _make_recursive_manifest("S5", "Plugins", modules)

        comp1 = _make_component("C1", "EmailPlugin", "S5", ["plugins/email.py"])
        comp2 = _make_component("C2", "ExportPlugin", "S5", ["plugins/export.py"])
        comp3 = _make_component("C3", "CleanupPlugin", "S5", ["plugins/cleanup.py"])
        model = _make_model([comp1, comp2, comp3])

        enrich_with_block_context(model, {"S5": rm})

        assert comp1.pattern == "handler"
        assert comp2.pattern == "handler"
        assert comp3.pattern == "handler"

    def test_does_not_overwrite_existing_pattern(self):
        modules = [
            ModuleInfo(file="core/bus.py", name="bus", docstring=None,
                      functions=[], imports=[], line_count=10, status=ModuleStatus.ACTIVE,
                      classes=[ClassInfo(name="Bus", bases=[], methods=["on", "emit"],
                              is_abstract=False, decorators=[], attributes={})],
                      exports=[], decorated_functions=[], imports_detailed=[],
                      module_constants={}, module_assignments={}),
        ]
        rm = _make_recursive_manifest("S1", "Core", modules)
        comp = _make_component("C1", "Bus", "S1", ["core/bus.py"], pattern="custom")
        model = _make_model([comp])

        enrich_with_block_context(model, {"S1": rm})
        assert comp.pattern == "custom"

    def test_contract_inference_from_block_name(self):
        """Components without contracts get one from block name."""
        modules = [
            ModuleInfo(file="net/proto.py", name="proto", docstring=None,
                      functions=[], imports=[], line_count=10, status=ModuleStatus.ACTIVE,
                      classes=[], exports=[], decorated_functions=[], imports_detailed=[],
                      module_constants={}, module_assignments={}),
        ]
        rm = _make_recursive_manifest("S3", "Network", modules)
        comp = _make_component("C1", "Protocol", "S3", ["net/proto.py"])
        model = _make_model([comp])

        enrich_with_block_context(model, {"S3": rm})
        assert "Network" in comp.contract
