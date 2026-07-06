"""Tests for hierarchical code generation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
    System,
)
from architecture_model.core.decomposer import DecompositionResult, decompose_model
from architecture_model.training.hierarchical_generator import HierarchicalGenerator


def _make_decomposed_model():
    """Create a DecompositionResult with 1 system + 1 remaining component."""
    # Sub-model for the system
    sub_model = ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test", system="Core Engine"),
        entities=Entities(
            components=[
                Component(id="comp-core", name="core", status=Status.ACTIVE,
                    symbols=[Symbol(name="Context", kind=SymbolKind.CLASS, members=["invoke"])]),
                Component(id="comp-parser", name="parser", status=Status.ACTIVE,
                    symbols=[Symbol(name="OptionParser", kind=SymbolKind.CLASS, members=["parse"])]),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="comp-core", to_id="comp-parser"),
        ],
    )

    # Top-level with system + remaining component
    top_level = ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test"),
        entities=Entities(
            systems=[
                System(id="sys-core-engine", name="Core Engine", status=Status.ACTIVE,
                    f_block="F1", complexity_score=20.0,
                    sub_model_ref="systems/core-engine.yaml",
                    component_ids=["comp-core", "comp-parser"]),
            ],
            components=[
                Component(id="comp-utils", name="utils", status=Status.ACTIVE,
                    functions=["echo", "format_filename"]),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="sys-core-engine", to_id="comp-utils"),
        ],
    )

    return DecompositionResult(
        top_level=top_level,
        sub_models={"sys-core-engine": sub_model},
    )


class TestHierarchicalGenerator:
    @pytest.mark.asyncio
    async def test_generates_code_per_system(self):
        """Each system gets its own generate_code call."""
        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(side_effect=[
            "# core.py\nclass Context:\n    def invoke(self): pass\n\n# parser.py\nclass OptionParser:\n    def parse(self): pass",
            "# utils.py\ndef echo(): pass\ndef format_filename(): pass",
        ])

        gen = HierarchicalGenerator(surrogate)
        decomposition = _make_decomposed_model()
        code = await gen.generate(decomposition)

        # Should have called generate_code twice (1 system + 1 remainder)
        assert surrogate.generate_code.call_count == 2
        assert "Context" in code
        assert "OptionParser" in code
        assert "echo" in code

    @pytest.mark.asyncio
    async def test_includes_system_header(self):
        """Generated code includes system boundary markers."""
        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(return_value="# core.py\nclass X: pass")

        gen = HierarchicalGenerator(surrogate)
        decomposition = _make_decomposed_model()
        # Remove remaining components to simplify
        decomposition.top_level.entities.components = []
        code = await gen.generate(decomposition)

        assert "System: Core Engine" in code

    @pytest.mark.asyncio
    async def test_fallback_for_no_systems(self):
        """generate_from_model falls back to single call when no systems needed."""
        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(return_value="# app.py\nclass App: pass")

        gen = HierarchicalGenerator(surrogate)

        # Simple model — won't trigger decomposition
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(
                components=[Component(id="comp-app", name="app", status=Status.ACTIVE)],
            ),
            relationships=[],
        )
        manifest = {"functional_blocks": {}}

        code = await gen.generate_from_model(model, manifest)

        assert surrogate.generate_code.call_count == 1
        assert "App" in code

    @pytest.mark.asyncio
    async def test_handles_empty_generation(self):
        """If surrogate returns empty, doesn't crash."""
        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(return_value="")

        gen = HierarchicalGenerator(surrogate)
        decomposition = _make_decomposed_model()
        code = await gen.generate(decomposition)

        # Should not crash, may be empty
        assert isinstance(code, str)

    @pytest.mark.asyncio
    async def test_generate_from_model_decomposes_complex(self):
        """generate_from_model triggers decomposition for complex models."""
        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(return_value="# mod.py\nclass X: pass")

        gen = HierarchicalGenerator(surrogate)

        # Complex model that will trigger decomposition
        comps = [
            Component(
                id=f"comp-{i}", name=f"mod{i}", status=Status.ACTIVE,
                f_block="F1",
                symbols=[Symbol(name=f"C{j}", kind=SymbolKind.CLASS,
                         members=[f"m{k}" for k in range(5)]) for j in range(3)],
            )
            for i in range(4)
        ]
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=comps),
            relationships=[],
        )
        manifest = {"functional_blocks": {"F1": {"name": "Core"}}}

        code = await gen.generate_from_model(model, manifest)

        # Should have been decomposed (1 system) → 1 call for system
        assert surrogate.generate_code.call_count == 1
        assert isinstance(code, str)
