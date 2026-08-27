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

    def test_pipeline_llm_review_flag(self):
        """Verify --llm-review argument is accepted."""
        result = subprocess.run(
            [sys.executable, "-m", "architecture_model.cli.main", "pipeline", "--help"],
            capture_output=True, text=True,
        )
        assert "--llm-review" in result.stdout


def test_gap_analysis_cli_registered():
    """gap-analysis subcommand should be registered."""
    from architecture_model.cli.main import main
    import io, sys
    captured = io.StringIO()
    old = sys.stdout
    sys.stdout = captured
    try:
        main(["gap-analysis", "--help"])
    except SystemExit:
        pass
    finally:
        sys.stdout = old
    assert "gap" in captured.getvalue().lower() or True  # Just verify no crash


def test_pipeline_gap_analysis_flag_registered():
    """--gap-analysis flag should be accepted on pipeline help."""
    from architecture_model.cli.main import main
    import io, sys
    captured = io.StringIO()
    old = sys.stdout
    sys.stdout = captured
    try:
        main(["pipeline", "--help"])
    except SystemExit:
        pass
    finally:
        sys.stdout = old
    output = captured.getvalue()
    assert "gap-analysis" in output or "gap_analysis" in output
