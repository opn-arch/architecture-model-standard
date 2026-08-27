"""Test review CLI command."""
import subprocess
import sys


class TestReviewCLI:
    def test_review_command_exists(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['review', '--help'])"],
            capture_output=True, text=True,
        )
        assert "review" in (result.stdout + result.stderr).lower()

    def test_review_command_has_auto_flag(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['review', '--help'])"],
            capture_output=True, text=True,
        )
        assert "--auto" in (result.stdout + result.stderr)

    def test_review_command_has_compare_flag(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['review', '--help'])"],
            capture_output=True, text=True,
        )
        assert "--compare" in (result.stdout + result.stderr)
