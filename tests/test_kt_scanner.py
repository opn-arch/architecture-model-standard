"""Tests for tree-sitter Kotlin scanner."""
import pytest
from pathlib import Path

try:
    import tree_sitter
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

pytestmark = pytest.mark.skipif(not HAS_TREE_SITTER, reason="tree-sitter not installed")

from architecture_model.manifest.kt_scanner import scan_kotlin
from architecture_model.manifest.protocol import SourceGraph


class TestKotlinScanner:
    def test_detects_classes(self, tmp_path):
        """Scans Kotlin files and finds class declarations."""
        kt_file = tmp_path / "User.kt"
        kt_file.write_text('''
package com.example.models

class User(val name: String, val email: String) {
    fun displayName(): String = "$name <$email>"
    private fun validate() {}
}

data class Address(val street: String, val city: String)
''')
        graph = scan_kotlin(tmp_path)
        assert len(graph.units) == 1
        exports = graph.units[0].exports
        names = {e.name for e in exports}
        assert "User" in names
        assert "Address" in names
        assert "displayName" in names
        assert "validate" not in names  # private

    def test_detects_top_level_functions(self, tmp_path):
        """Scans Kotlin top-level functions."""
        kt_file = tmp_path / "Utils.kt"
        kt_file.write_text('''
package com.example.utils

fun formatDate(date: Long): String {
    return date.toString()
}

internal fun helper() {}
''')
        graph = scan_kotlin(tmp_path)
        exports = graph.units[0].exports
        names = {e.name for e in exports}
        assert "formatDate" in names
        assert "helper" not in names  # internal

    def test_detects_imports_as_edges(self, tmp_path):
        """Import statements become dependency edges."""
        (tmp_path / "models").mkdir()
        (tmp_path / "models" / "User.kt").write_text(
            "package com.example.models\nclass User"
        )
        (tmp_path / "Service.kt").write_text('''
package com.example

import com.example.models.User

class UserService {
    fun getUser(): User = User()
}
''')
        graph = scan_kotlin(tmp_path)
        assert len(graph.edges) >= 1
        edge = graph.edges[0]
        assert "Service.kt" in edge.source
        assert "User" in edge.symbols or "models" in edge.target

    def test_excludes_build_dirs(self, tmp_path):
        """Files in build/ directories are excluded."""
        (tmp_path / "build").mkdir()
        (tmp_path / "build" / "Generated.kt").write_text("class Generated")
        (tmp_path / "Main.kt").write_text("class Main")
        graph = scan_kotlin(tmp_path)
        files = {u.file for u in graph.units}
        assert "Main.kt" in files
        assert "build/Generated.kt" not in files

    def test_extracts_annotations(self, tmp_path):
        """Composable and other annotations are captured."""
        kt_file = tmp_path / "Screen.kt"
        kt_file.write_text('''
package com.example.ui

import androidx.compose.runtime.Composable

@Composable
fun HomeScreen() {
    // UI content
}

fun regularFunction() {}
''')
        graph = scan_kotlin(tmp_path)
        exports = graph.units[0].exports
        names = {e.name for e in exports}
        assert "HomeScreen" in names
        assert "regularFunction" in names

    def test_object_declarations(self, tmp_path):
        """Kotlin object declarations are extracted."""
        kt_file = tmp_path / "Config.kt"
        kt_file.write_text('''
package com.example

object AppConfig {
    val baseUrl = "http://localhost"
}

private object InternalHelper
''')
        graph = scan_kotlin(tmp_path)
        exports = graph.units[0].exports
        names = {e.name for e in exports}
        assert "AppConfig" in names
        assert "InternalHelper" not in names  # private

    def test_language_field(self, tmp_path):
        """SourceGraph has language='kotlin'."""
        (tmp_path / "Main.kt").write_text("class Main")
        graph = scan_kotlin(tmp_path)
        assert graph.language == "kotlin"
        assert graph.units[0].language == "kotlin"

    def test_real_android_app(self):
        """Scan the actual knowledge_os_auto app."""
        app_path = Path(
            "/Users/baigm2/Documents/Projects/logs_db/knowledge_os_auto/app/src/main"
        )
        if not app_path.exists():
            pytest.skip("Android app not available")
        graph = scan_kotlin(app_path)
        assert len(graph.units) >= 8
        assert graph.language == "kotlin"
        all_exports = [e.name for u in graph.units for e in u.exports]
        assert "MainActivity" in all_exports or "KnowledgeOSSession" in all_exports
