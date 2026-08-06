"""Integration test: pipeline -> iterative decompose -> enrichment prompt."""
from pathlib import Path

from architecture_model.orchestration.pipeline import run_pipeline
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt


def test_full_flow_synthetic_repo(tmp_path):
    """Create a synthetic repo, run pipeline with deep=True, produce enrichment prompt."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    for i in range(20):
        code = f"import myapp.mod_{max(0,i-1)}\nclass Handler{i}:\n    def process(self): pass\n"
        (pkg / f"mod_{i}.py").write_text(code)

    config = tmp_path / ".architecture-model.yaml"
    config.write_text("""\
meta:
  project: test-enrichment
  schema_version: '1.3'
functional_blocks:
  S1:
    name: MyApp
    dirs:
      - myapp
entities:
  components: []
relationships: []
""")

    result = run_pipeline(tmp_path, deep=True)
    assert "S1" in result.manifests
    assert len(result.deep_decompositions) > 0

    prompt = format_enrichment_prompt(list(result.deep_decompositions.values()))
    assert "COMP-" in prompt
    assert "pattern" in prompt.lower()
    assert len(prompt) < 20000
