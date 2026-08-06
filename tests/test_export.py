"""Tests for architecture_model.export."""
import json
import tempfile
from pathlib import Path

import pytest
import yaml

from architecture_model.export.flatfiles import (
    ExportResult, build_flat_export, concat_submodels, concat_docs,
    derive_prefix, manifests_to_markdown,
)
from architecture_model.export.reference import (
    generate_readme, generate_schema_reference,
    generate_api_reference, generate_custom_instructions,
)


class TestDerivePrefix:
    def test_known_aliases(self):
        assert derive_prefix("architecture-model-standard") == "model-std"
        assert derive_prefix("opencode-arch") == "opencode"
        assert derive_prefix("logs_db") == "logs-db"

    def test_unknown_repo(self):
        assert derive_prefix("my-cool-project") == "my-cool-project"
        assert derive_prefix("Some_App") == "some-app"


class TestBuildFlatExport:
    def test_minimal_repo(self, tmp_path):
        """Repo with only .architecture-model.yaml."""
        model = {"meta": {"project": "test", "schema_version": "1.3"}, "entities": {"components": []}, "relationships": []}
        (tmp_path / ".architecture-model.yaml").write_text(yaml.dump(model))
        
        result = build_flat_export(tmp_path, prefix="test")
        assert isinstance(result, ExportResult)
        assert "test--model.yaml" in result.files
        assert "README.md" in result.files
        assert "SCHEMA.md" in result.files
        assert "API.md" in result.files
        assert "CUSTOM-INSTRUCTIONS.md" in result.files
        assert result.total_size_bytes > 0

    def test_with_context(self, tmp_path):
        (tmp_path / ".architecture-model.yaml").write_text("meta: {}")
        (tmp_path / "CONTEXT.md").write_text("# My Project")
        result = build_flat_export(tmp_path, prefix="test")
        assert "test--CONTEXT.md" in result.files
        assert "# My Project" in result.files["test--CONTEXT.md"]

    def test_with_submodels(self, tmp_path):
        (tmp_path / ".architecture-model.yaml").write_text("meta: {}")
        sub = tmp_path / ".architecture-models" / "S1"
        sub.mkdir(parents=True)
        (sub / ".architecture-model.yaml").write_text("meta: {project: sub}")
        result = build_flat_export(tmp_path, prefix="test")
        assert "test--submodels.yaml" in result.files
        assert "Sub-Model: S1" in result.files["test--submodels.yaml"]

    def test_skips_missing(self, tmp_path):
        """Only includes files that exist."""
        (tmp_path / ".architecture-model.yaml").write_text("meta: {}")
        result = build_flat_export(tmp_path, prefix="test")
        # No behaviors, no manifests, no module specs
        assert "test--behavior-specs.md" not in result.files
        assert "test--manifests.md" not in result.files
        assert "test--module-specs.md" not in result.files

    def test_prefix_auto_derived(self, tmp_path):
        # tmp_path name varies, but prefix should be derived
        (tmp_path / ".architecture-model.yaml").write_text("meta: {}")
        result = build_flat_export(tmp_path)
        assert result.prefix == derive_prefix(tmp_path.name)


class TestManifestsToMarkdown:
    def test_converts_modules(self, tmp_path):
        manifest = {
            "modules": [
                {"file": "src/foo.py", "name": "foo", "functions": [{"name": "bar", "signature": "()"}], "imports": ["app.models"]}
            ]
        }
        (tmp_path / "S1.json").write_text(json.dumps(manifest))
        result = manifests_to_markdown(tmp_path)
        assert result is not None
        assert "S1" in result
        assert "src/foo.py" in result
        assert "bar" in result

    def test_handles_files_format(self, tmp_path):
        manifest = {"files": ["src/a.py", "src/b.py"], "component_id": "COMP-1"}
        (tmp_path / "COMP-1.json").write_text(json.dumps(manifest))
        result = manifests_to_markdown(tmp_path)
        assert result is not None
        assert "COMP-1" in result
        assert "src/a.py" in result

    def test_empty_dir(self, tmp_path):
        assert manifests_to_markdown(tmp_path) is None


class TestConcatSubmodels:
    def test_with_headers(self, tmp_path):
        sub = tmp_path / ".architecture-models" / "S1"
        sub.mkdir(parents=True)
        (sub / ".architecture-model.yaml").write_text("meta: {project: f1}")
        result = concat_submodels(tmp_path)
        assert result is not None
        assert "<!-- FILE:" in result
        assert "Sub-Model: S1" in result


class TestReferenceGenerators:
    def test_readme(self):
        r = generate_readme()
        assert "Architecture Model Export" in r

    def test_schema(self):
        s = generate_schema_reference()
        assert "Component" in s
        assert "Behavior" in s
        assert "Relationship" in s

    def test_api(self):
        a = generate_api_reference()
        assert "architect_scan" in a
        assert "Token Arbitrage" in a

    def test_custom_instructions(self):
        c = generate_custom_instructions("test-repo", {"components": 5, "behaviors": 10, "relationships": 20, "file_count": 8})
        assert "test-repo" in c
        assert "5" in c  # components
        assert "10" in c  # behaviors
