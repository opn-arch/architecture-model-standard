"""Test quality CLI command."""
import subprocess
import sys


class TestQualityCLI:
    def test_quality_command_exists(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['quality', '--help'])"],
            capture_output=True, text=True,
        )
        assert "quality" in (result.stdout + result.stderr).lower()
