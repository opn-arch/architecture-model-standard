"""Tests for artifact template definitions."""

import pytest

from architecture_model.artifacts.templates import (
    TEMPLATES,
    ArtifactTemplate,
    TemplateSection,
    get_template,
)
from architecture_model.artifacts.selector import ARTIFACT_REGISTRY


# Valid source values that TemplateSection.source can reference
VALID_SOURCES = frozenset(
    {
        "meta",
        "components",
        "interfaces",
        "capabilities",
        "behaviors",
        "constraints",
        "layers",
        "relationships",
        "manifest.tests",
        "manifest.metrics",
    }
)


def test_templates_dict_has_12_entries():
    assert len(TEMPLATES) == 12


def test_all_template_ids_match_registry():
    registry_ids = {spec.id for spec in ARTIFACT_REGISTRY}
    template_ids = set(TEMPLATES.keys())
    assert template_ids == registry_ids


def test_each_template_has_at_least_2_sections():
    for artifact_id, template in TEMPLATES.items():
        assert (
            len(template.sections) >= 2
        ), f"Template '{artifact_id}' has fewer than 2 sections"


def test_template_sections_have_valid_sources():
    for artifact_id, template in TEMPLATES.items():
        for section in template.sections:
            assert section.source in VALID_SOURCES, (
                f"Template '{artifact_id}' section '{section.heading}' "
                f"has invalid source '{section.source}'"
            )


def test_get_template_found():
    result = get_template("system-overview")
    assert result is not None
    assert isinstance(result, ArtifactTemplate)
    assert result.artifact_id == "system-overview"


def test_get_template_not_found():
    result = get_template("nonexistent-artifact")
    assert result is None


def test_template_filenames_are_unique():
    filenames = [t.filename for t in TEMPLATES.values()]
    assert len(filenames) == len(set(filenames)), "Duplicate filenames found"


def test_template_system_prompts_non_empty():
    for artifact_id, template in TEMPLATES.items():
        assert template.system_prompt.strip(), (
            f"Template '{artifact_id}' has empty system_prompt"
        )


def test_template_artifact_id_matches_key():
    """Each template's artifact_id field must match its dict key."""
    for key, template in TEMPLATES.items():
        assert template.artifact_id == key


def test_template_filenames_end_with_md():
    """All output filenames should be markdown files."""
    for artifact_id, template in TEMPLATES.items():
        assert template.filename.endswith(".md"), (
            f"Template '{artifact_id}' filename does not end with .md"
        )


def test_section_headings_non_empty():
    """Every section must have a non-empty heading."""
    for artifact_id, template in TEMPLATES.items():
        for section in template.sections:
            assert section.heading.strip(), (
                f"Template '{artifact_id}' has a section with empty heading"
            )


def test_section_instructions_non_empty():
    """Every section must have non-empty instructions."""
    for artifact_id, template in TEMPLATES.items():
        for section in template.sections:
            assert section.instructions.strip(), (
                f"Template '{artifact_id}' section '{section.heading}' "
                f"has empty instructions"
            )
