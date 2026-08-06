"""Tests for the `architecture-model author` CLI command."""

import yaml
from architecture_model.cli.main import main


def test_author_command_produces_model(tmp_path):
    req_file = tmp_path / "requirements.md"
    req_file.write_text("# Actors\n- User: uses app\n# Capabilities\n- CAP-1: Login")

    output = tmp_path / "model.yaml"
    result = main(["author", str(req_file), "--output", str(output)])

    assert result == 0
    assert output.exists()
    data = yaml.safe_load(output.read_text())
    assert data["meta"]["project"] == "authored"
    assert len(data["entities"]["actors"]) == 1
    assert len(data["entities"]["capabilities"]) == 1


def test_author_command_default_output(tmp_path, monkeypatch):
    req_file = tmp_path / "requirements.md"
    req_file.write_text("# Constraints\n- CON-1: Fast (performance)")

    monkeypatch.chdir(tmp_path)
    result = main(["author", str(req_file)])

    assert result == 0
    default_output = tmp_path / ".architecture-model.yaml"
    assert default_output.exists()
