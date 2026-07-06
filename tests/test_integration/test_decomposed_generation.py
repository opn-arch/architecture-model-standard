"""Integration tests for decomposed generation pipeline.

Tests the full decompose → generate → score pipeline with MOCKED surrogate.
Does NOT require Ollama running — pure unit-test with mocks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml as pyyaml

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
)
from architecture_model.core.decomposer import (
    DecompositionResult,
    SystemCandidate,
    SYSTEM_THRESHOLD,
    decompose_model,
    identify_systems,
)
from architecture_model.core.merger import compact_for_generation, enrich_from_manifest
from architecture_model.core.parser import _parse_raw, dump_model
from architecture_model.training.code_structure import (
    StructuralGraph,
    parse_multi_file_code,
)
from architecture_model.training.hierarchical_generator import HierarchicalGenerator


# ---------------------------------------------------------------------------
# Fixtures: click-like model with multiple F-blocks
# ---------------------------------------------------------------------------


def _make_click_like_model() -> ArchitectureModel:
    """Build a model resembling click's architecture with multiple F-block groups.

    Creates 3 complex F-blocks (core, decorators, types) that should each
    become a System, plus 1 simple utilities group that stays top-level.
    """
    # F-block: core (complex — parser, context, commands)
    core_comps = [
        Component(
            id="comp-core", name="core", status=Status.ACTIVE,
            f_block="core",
            symbols=[
                Symbol(name="Context", kind=SymbolKind.CLASS,
                       members=["invoke", "forward", "abort", "exit", "ensure_object"]),
                Symbol(name="BaseCommand", kind=SymbolKind.CLASS,
                       members=["invoke", "main", "make_context", "parse_args"]),
            ],
            functions=["pass_context", "make_pass_decorator"],
        ),
        Component(
            id="comp-commands", name="commands", status=Status.ACTIVE,
            f_block="core",
            symbols=[
                Symbol(name="Command", kind=SymbolKind.CLASS,
                       members=["invoke", "callback", "parse_args", "format_help"]),
                Symbol(name="MultiCommand", kind=SymbolKind.CLASS,
                       members=["list_commands", "get_command", "resolve_command"]),
                Symbol(name="Group", kind=SymbolKind.CLASS,
                       members=["add_command", "command", "group", "result_callback"]),
            ],
            functions=["command", "group"],
        ),
        Component(
            id="comp-parser", name="parser", status=Status.ACTIVE,
            f_block="core",
            symbols=[
                Symbol(name="OptionParser", kind=SymbolKind.CLASS,
                       members=["parse_args", "add_option", "add_argument"]),
                Symbol(name="Option", kind=SymbolKind.CLASS,
                       members=["consume_value", "process_value"]),
                Symbol(name="Argument", kind=SymbolKind.CLASS,
                       members=["consume_value", "process_value"]),
            ],
            functions=["split_arg_string"],
        ),
    ]

    # F-block: decorators (complex — parameter decorators)
    decorator_comps = [
        Component(
            id="comp-decorators", name="decorators", status=Status.ACTIVE,
            f_block="decorators",
            symbols=[
                Symbol(name="ParameterDecorator", kind=SymbolKind.CLASS,
                       members=["__call__", "option", "argument"]),
            ],
            functions=[
                "option", "argument", "password_option", "confirmation_option",
                "version_option", "help_option",
            ],
        ),
        Component(
            id="comp-params", name="params", status=Status.ACTIVE,
            f_block="decorators",
            symbols=[
                Symbol(name="Parameter", kind=SymbolKind.CLASS,
                       members=["resolve_envvar_value", "value_from_envvar",
                                "type_cast_value", "make_metavar", "get_default"]),
                Symbol(name="OptionParam", kind=SymbolKind.CLASS,
                       members=["consume_value", "add_to_parser", "prompt_for_value"]),
                Symbol(name="ArgumentParam", kind=SymbolKind.CLASS,
                       members=["consume_value", "add_to_parser"]),
            ],
            functions=["get_params_from_click"],
        ),
    ]

    # F-block: types (complex — type system)
    type_comps = [
        Component(
            id="comp-types", name="types", status=Status.ACTIVE,
            f_block="types",
            symbols=[
                Symbol(name="ParamType", kind=SymbolKind.CLASS,
                       members=["convert", "get_metavar", "get_missing_message"]),
                Symbol(name="StringParamType", kind=SymbolKind.CLASS, members=["convert"]),
                Symbol(name="IntParamType", kind=SymbolKind.CLASS, members=["convert"]),
                Symbol(name="FloatParamType", kind=SymbolKind.CLASS, members=["convert"]),
                Symbol(name="BoolParamType", kind=SymbolKind.CLASS, members=["convert"]),
                Symbol(name="Choice", kind=SymbolKind.CLASS,
                       members=["convert", "get_metavar", "get_type_repr"]),
                Symbol(name="Path", kind=SymbolKind.CLASS,
                       members=["convert", "resolve_path"]),
                Symbol(name="File", kind=SymbolKind.CLASS,
                       members=["convert", "resolve_lazy"]),
            ],
            functions=["convert_type"],
        ),
    ]

    # F-block: utils (simple — stays top-level)
    util_comp = Component(
        id="comp-utils", name="utils", status=Status.ACTIVE,
        f_block="utils",
        functions=["echo", "secho", "format_filename"],
    )

    all_comps = core_comps + decorator_comps + type_comps + [util_comp]

    rels = [
        Relationship(type=RelationType.DEPENDS_ON, from_id="comp-commands", to_id="comp-core",
                     imports=["Context", "BaseCommand"]),
        Relationship(type=RelationType.DEPENDS_ON, from_id="comp-parser", to_id="comp-core",
                     imports=["Context"]),
        Relationship(type=RelationType.DEPENDS_ON, from_id="comp-decorators", to_id="comp-params",
                     imports=["Parameter"]),
        Relationship(type=RelationType.DEPENDS_ON, from_id="comp-params", to_id="comp-types",
                     imports=["ParamType"]),
        Relationship(type=RelationType.DEPENDS_ON, from_id="comp-core", to_id="comp-utils"),
        Relationship(type=RelationType.DEPENDS_ON, from_id="comp-commands", to_id="comp-utils"),
    ]

    model = ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="click"),
        entities=Entities(components=all_comps),
        relationships=rels,
    )
    return model


def _build_manifest_for_model(model: ArchitectureModel) -> dict:
    """Build synthetic manifest with functional_blocks from model component f_block values."""
    fblocks = {}
    for comp in model.entities.components:
        if comp.f_block and comp.f_block not in fblocks:
            fblocks[comp.f_block] = {"name": comp.f_block}
    return {"modules": [], "interfaces": [], "functional_blocks": fblocks}


# Canned code outputs for each system (simulates surrogate response)
CANNED_CORE_CODE = """\
# core.py
class Context:
    \"\"\"Click execution context.\"\"\"
    def invoke(self, callback, **kwargs): pass
    def forward(self, cmd, **kwargs): pass
    def abort(self): pass
    def exit(self, code=0): pass
    def ensure_object(self, cls): pass

class BaseCommand:
    \"\"\"Base for all commands.\"\"\"
    def invoke(self, ctx): pass
    def main(self, args=None): pass
    def make_context(self, info_name, args): pass
    def parse_args(self, ctx, args): pass

def pass_context(f): pass
def make_pass_decorator(cls): pass

# commands.py
class Command(BaseCommand):
    \"\"\"A single CLI command.\"\"\"
    def invoke(self, ctx): pass
    def callback(self): pass
    def parse_args(self, ctx, args): pass
    def format_help(self, ctx, formatter): pass

class MultiCommand(BaseCommand):
    \"\"\"A command with sub-commands.\"\"\"
    def list_commands(self, ctx): pass
    def get_command(self, ctx, name): pass
    def resolve_command(self, ctx, args): pass

class Group(MultiCommand):
    \"\"\"A group of sub-commands.\"\"\"
    def add_command(self, cmd, name=None): pass
    def command(self, *args, **kwargs): pass
    def group(self, *args, **kwargs): pass
    def result_callback(self): pass

def command(name=None, **attrs): pass
def group(name=None, **attrs): pass

# parser.py
class OptionParser:
    \"\"\"Parses CLI options.\"\"\"
    def parse_args(self, args): pass
    def add_option(self, obj): pass
    def add_argument(self, obj): pass

class Option:
    \"\"\"A CLI option.\"\"\"
    def consume_value(self, ctx, opts): pass
    def process_value(self, ctx, value): pass

class Argument:
    \"\"\"A CLI argument.\"\"\"
    def consume_value(self, ctx, opts): pass
    def process_value(self, ctx, value): pass

def split_arg_string(string): pass
"""

CANNED_DECORATORS_CODE = """\
# decorators.py
class ParameterDecorator:
    \"\"\"Decorator for adding parameters.\"\"\"
    def __call__(self, f): pass
    def option(self, *args, **kwargs): pass
    def argument(self, *args, **kwargs): pass

def option(*args, **kwargs): pass
def argument(*args, **kwargs): pass
def password_option(*args, **kwargs): pass
def confirmation_option(*args, **kwargs): pass
def version_option(*args, **kwargs): pass
def help_option(*args, **kwargs): pass

# params.py
class Parameter:
    \"\"\"Base parameter class.\"\"\"
    def resolve_envvar_value(self, ctx): pass
    def value_from_envvar(self, ctx): pass
    def type_cast_value(self, ctx, value): pass
    def make_metavar(self): pass
    def get_default(self, ctx): pass

class OptionParam(Parameter):
    \"\"\"CLI option parameter.\"\"\"
    def consume_value(self, ctx, opts): pass
    def add_to_parser(self, parser, ctx): pass
    def prompt_for_value(self, ctx): pass

class ArgumentParam(Parameter):
    \"\"\"CLI argument parameter.\"\"\"
    def consume_value(self, ctx, opts): pass
    def add_to_parser(self, parser, ctx): pass

def get_params_from_click(cmd): pass
"""

CANNED_TYPES_CODE = """\
# types.py
class ParamType:
    \"\"\"Base parameter type.\"\"\"
    def convert(self, value, param, ctx): pass
    def get_metavar(self, param): pass
    def get_missing_message(self, param): pass

class StringParamType(ParamType):
    \"\"\"String type.\"\"\"
    def convert(self, value, param, ctx): pass

class IntParamType(ParamType):
    \"\"\"Integer type.\"\"\"
    def convert(self, value, param, ctx): pass

class FloatParamType(ParamType):
    \"\"\"Float type.\"\"\"
    def convert(self, value, param, ctx): pass

class BoolParamType(ParamType):
    \"\"\"Boolean type.\"\"\"
    def convert(self, value, param, ctx): pass

class Choice(ParamType):
    \"\"\"Choice type.\"\"\"
    def convert(self, value, param, ctx): pass
    def get_metavar(self, param): pass
    def get_type_repr(self): pass

class Path(ParamType):
    \"\"\"Path type.\"\"\"
    def convert(self, value, param, ctx): pass
    def resolve_path(self, value): pass

class File(ParamType):
    \"\"\"File type.\"\"\"
    def convert(self, value, param, ctx): pass
    def resolve_lazy(self): pass

def convert_type(value, type_): pass
"""

CANNED_UTILS_CODE = """\
# utils.py
def echo(message=None, **kwargs): pass
def secho(message=None, **kwargs): pass
def format_filename(filename): pass
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDecompositionIdentifiesSystemsForClick:
    """Verify that decomposition correctly identifies systems for a click-like model."""

    def test_identifies_three_systems(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        candidates = identify_systems(model, manifest)

        # core, decorators, types should all exceed threshold
        assert len(candidates) >= 3
        names = {c.name for c in candidates}
        assert "core" in names
        assert "decorators" in names
        assert "types" in names

    def test_utils_stays_top_level(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        candidates = identify_systems(model, manifest)

        # utils is too simple to become a system
        system_fblocks = {c.f_block for c in candidates}
        assert "utils" not in system_fblocks

    def test_decompose_produces_sub_models(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        assert len(result.sub_models) >= 3
        assert len(result.top_level.entities.systems) >= 3

    def test_decompose_top_level_retains_utils(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        top_comp_ids = {c.id for c in result.top_level.entities.components}
        assert "comp-utils" in top_comp_ids

    def test_complexity_scores_above_threshold(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        candidates = identify_systems(model, manifest)

        for candidate in candidates:
            assert candidate.complexity_score > SYSTEM_THRESHOLD, (
                f"System '{candidate.name}' has score {candidate.complexity_score} "
                f"below threshold {SYSTEM_THRESHOLD}"
            )


class TestDecomposedGenerationPipeline:
    """Test the full decompose → generate → score pipeline with mocked surrogate."""

    @pytest.mark.asyncio
    async def test_hierarchical_generate_calls_surrogate_per_system(self):
        """Each system gets its own generate_code call, plus remainder."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        surrogate = MagicMock()
        # Return canned code for each call (systems + remainder)
        call_responses = []
        for sys in result.top_level.entities.systems:
            if "core" in sys.name:
                call_responses.append(CANNED_CORE_CODE)
            elif "decorator" in sys.name:
                call_responses.append(CANNED_DECORATORS_CODE)
            elif "type" in sys.name:
                call_responses.append(CANNED_TYPES_CODE)
            else:
                call_responses.append("# unknown.py\npass")
        # Add remainder (utils)
        call_responses.append(CANNED_UTILS_CODE)

        surrogate.generate_code = AsyncMock(side_effect=call_responses)
        gen = HierarchicalGenerator(surrogate)
        code = await gen.generate(result)

        # Should call generate for each system + remainder
        n_systems = len(result.top_level.entities.systems)
        has_remainder = len(result.top_level.entities.components) > 0
        expected_calls = n_systems + (1 if has_remainder else 0)
        assert surrogate.generate_code.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_stitched_output_contains_all_systems(self):
        """The final stitched code contains code from all systems."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        surrogate = MagicMock()
        call_responses = []
        for sys in result.top_level.entities.systems:
            if "core" in sys.name:
                call_responses.append(CANNED_CORE_CODE)
            elif "decorator" in sys.name:
                call_responses.append(CANNED_DECORATORS_CODE)
            elif "type" in sys.name:
                call_responses.append(CANNED_TYPES_CODE)
            else:
                call_responses.append("# other.py\nclass Other: pass")
        call_responses.append(CANNED_UTILS_CODE)

        surrogate.generate_code = AsyncMock(side_effect=call_responses)
        gen = HierarchicalGenerator(surrogate)
        code = await gen.generate(result)

        # Core system classes
        assert "Context" in code
        assert "BaseCommand" in code
        assert "OptionParser" in code
        # Decorators system
        assert "ParameterDecorator" in code
        assert "Parameter" in code
        # Types system
        assert "ParamType" in code
        assert "Choice" in code
        # Utils (remainder)
        assert "echo" in code
        assert "format_filename" in code

    @pytest.mark.asyncio
    async def test_stitched_output_parseable_as_structural_graph(self):
        """The stitched output can be parsed into a StructuralGraph."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        surrogate = MagicMock()
        call_responses = []
        for sys in result.top_level.entities.systems:
            if "core" in sys.name:
                call_responses.append(CANNED_CORE_CODE)
            elif "decorator" in sys.name:
                call_responses.append(CANNED_DECORATORS_CODE)
            elif "type" in sys.name:
                call_responses.append(CANNED_TYPES_CODE)
            else:
                call_responses.append("# other.py\nclass Other: pass")
        call_responses.append(CANNED_UTILS_CODE)

        surrogate.generate_code = AsyncMock(side_effect=call_responses)
        gen = HierarchicalGenerator(surrogate)
        code = await gen.generate(result)

        graph = parse_multi_file_code(code)
        # Should have parsed classes from all systems
        assert len(graph.classes) > 0
        assert "Context" in graph.class_names
        assert "ParamType" in graph.class_names
        assert len(graph.functions) > 0

    @pytest.mark.asyncio
    async def test_system_headers_in_output(self):
        """Output includes system boundary markers."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(return_value="# mod.py\nclass X: pass")
        gen = HierarchicalGenerator(surrogate)
        code = await gen.generate(result)

        # Each system should have a "System: <name>" header
        for sys in result.top_level.entities.systems:
            assert f"System: {sys.name}" in code

    @pytest.mark.asyncio
    async def test_generate_from_model_triggers_decomposition(self):
        """generate_from_model correctly decomposes and generates."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)

        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(return_value="# mod.py\nclass X: pass")
        gen = HierarchicalGenerator(surrogate)
        code = await gen.generate_from_model(model, manifest)

        # Should have been decomposed — multiple calls
        assert surrogate.generate_code.call_count > 1
        assert isinstance(code, str)
        assert len(code) > 0


class TestSubModelSerialization:
    """Verify sub-models serialize correctly for the surrogate."""

    def test_sub_model_serializes_to_yaml(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        for sys_id, sub_model in result.sub_models.items():
            compacted = compact_for_generation(sub_model)
            sub_dict = dump_model(compacted)
            sub_yaml = pyyaml.dump(
                sub_dict, default_flow_style=False,
                sort_keys=False, allow_unicode=True,
            )
            # Should be valid YAML
            reparsed = pyyaml.safe_load(sub_yaml)
            assert "entities" in reparsed
            assert "components" in reparsed["entities"]
            assert len(reparsed["entities"]["components"]) > 0

    def test_sub_model_preserves_symbols(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        # Find the core system
        core_sys_id = None
        for sys in result.top_level.entities.systems:
            if "core" in sys.name:
                core_sys_id = sys.id
                break

        assert core_sys_id is not None
        sub = result.sub_models[core_sys_id]

        # Sub-model should preserve all symbols from core components
        all_symbol_names = set()
        for comp in sub.entities.components:
            for sym in comp.symbols:
                all_symbol_names.add(sym.name)

        assert "Context" in all_symbol_names
        assert "BaseCommand" in all_symbol_names
        assert "OptionParser" in all_symbol_names

    def test_sub_model_preserves_relationships(self):
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        # Core system should have intra-system relationships
        core_sys_id = None
        for sys in result.top_level.entities.systems:
            if "core" in sys.name:
                core_sys_id = sys.id
                break

        sub = result.sub_models[core_sys_id]
        # comp-commands → comp-core and comp-parser → comp-core are intra-system
        rel_pairs = [(r.from_id, r.to_id) for r in sub.relationships]
        assert ("comp-commands", "comp-core") in rel_pairs
        assert ("comp-parser", "comp-core") in rel_pairs


class TestPipelineProducesValidOutput:
    """Verify the pipeline produces structurally valid output."""

    @pytest.mark.asyncio
    async def test_empty_surrogate_response_handled(self):
        """If surrogate returns empty for a system, pipeline still works."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        surrogate = MagicMock()
        # Return empty for all calls
        surrogate.generate_code = AsyncMock(return_value="")
        gen = HierarchicalGenerator(surrogate)
        code = await gen.generate(result)

        # Should not crash — empty string is valid
        assert isinstance(code, str)

    @pytest.mark.asyncio
    async def test_partial_failure_still_produces_output(self):
        """If one system's generation fails, others still produce code."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        # First call returns code, subsequent return empty
        responses = [CANNED_CORE_CODE] + [""] * (
            len(result.top_level.entities.systems)  # remaining systems
        )
        surrogate = MagicMock()
        surrogate.generate_code = AsyncMock(side_effect=responses)
        gen = HierarchicalGenerator(surrogate)
        code = await gen.generate(result)

        # Should still have output from the first system
        assert "Context" in code or "BaseCommand" in code

    @pytest.mark.asyncio
    async def test_model_round_trips_through_yaml(self):
        """Model can be serialized to YAML and reparsed (for surrogate input)."""
        model = _make_click_like_model()
        manifest = _build_manifest_for_model(model)
        result = decompose_model(model, manifest)

        for sys_id, sub_model in result.sub_models.items():
            compacted = compact_for_generation(sub_model)
            sub_dict = dump_model(compacted)
            sub_yaml = pyyaml.dump(
                sub_dict, default_flow_style=False,
                sort_keys=False, allow_unicode=True,
            )
            # Reparse as raw dict
            reparsed = pyyaml.safe_load(sub_yaml)
            # Should be parseable back to model
            reparsed_model = _parse_raw(reparsed)
            assert len(reparsed_model.entities.components) == len(sub_model.entities.components)
