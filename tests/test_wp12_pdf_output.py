"""WP-12: PDF as standard CLI output."""
import subprocess
import sys


class TestPDFCommand:
    def test_docs_command_has_pdf_option(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from architecture_model.cli.main import main; main(['docs', '--help'])"],
            capture_output=True, text=True,
        )
        assert "--pdf" in (result.stdout + result.stderr)
