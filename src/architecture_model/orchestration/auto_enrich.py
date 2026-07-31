"""Auto-enrichment of architecture model components from manifest data.

Populates Component fields (signatures, symbols, constants, contract, pattern,
responsibilities) by matching component files to manifest modules.
"""

from __future__ import annotations

import re
from typing import Any

from architecture_model.core.types import (
    Behavior,
    Component,
    Constant,
    FunctionSignature,
    Symbol,
    SymbolKind,
)
from architecture_model.manifest.types import ClassInfo, FunctionInfo, Manifest, ModuleInfo
from architecture_model.monitoring import monitored
from architecture_model.patterns import load_patterns

# Decorators that indicate a trigger
_TRIGGER_DECORATORS = re.compile(
    r"(route|get|post|put|delete|patch|"
    r"event|signal|handler|listen|subscribe|"
    r"on_event|on_message|webhook|cron|scheduled)",
    re.IGNORECASE,
)


def _parse_signature(name: str, func: FunctionInfo) -> FunctionSignature:
    """Parse a FunctionInfo into a FunctionSignature."""
    sig = func.signature
    params: list[str] = []
    returns = ""

    # Extract params and return type from "(a: int, b: int) -> int"
    m = re.match(r"\((.*?)\)\s*(?:->\s*(.+))?", sig)
    if m:
        param_str = m.group(1).strip()
        if param_str:
            params = [p.strip() for p in param_str.split(",")]
        returns = (m.group(2) or "").strip()

    return FunctionSignature(
        name=name,
        params=params,
        returns=returns,
        decorators=[],
        body_hint=func.docstring or "",
    )


def _detect_symbol_kind(cls: ClassInfo) -> SymbolKind:
    """Detect SymbolKind from class decorators and bases."""
    all_text = " ".join(cls.decorators + cls.bases).lower()
    if "dataclass" in all_text:
        return SymbolKind.DATACLASS
    if "exception" in all_text or "error" in all_text:
        return SymbolKind.EXCEPTION
    if "protocol" in all_text:
        return SymbolKind.PROTOCOL
    if "enum" in all_text:
        return SymbolKind.ENUM
    if "abc" in all_text or cls.is_abstract:
        return SymbolKind.INTERFACE
    return SymbolKind.CLASS


def _class_to_symbol(cls: ClassInfo) -> Symbol:
    """Convert a ClassInfo to a Symbol."""
    return Symbol(
        name=cls.name,
        kind=_detect_symbol_kind(cls),
        members=list(cls.methods),
        supers=list(cls.bases),
    )


def _extract_contract(module: ModuleInfo, classes: list[ClassInfo]) -> str:
    """Infer contract from first sentence of module or class docstring."""
    for source in [module.docstring] + [None]:  # try module first
        pass
    # Try module docstring
    if module.docstring:
        first = module.docstring.strip().split("\n")[0]
        # Get first sentence
        sentence = re.split(r"[.!?]", first)[0].strip()
        if sentence:
            return sentence
    # Try first class docstring (not available in ClassInfo, skip)
    return ""


def _classify_pattern(modules: list[ModuleInfo]) -> str:
    """Classify component pattern using pattern catalog indicators."""
    catalog = load_patterns()

    # Collect all names (functions, classes, methods) from modules
    names: list[str] = []
    for mod in modules:
        for f in mod.functions:
            names.append(f.name.lower())
        for c in mod.classes:
            names.append(c.name.lower())
            for m in c.methods:
                names.append(m.lower())
            for d in c.decorators:
                names.append(d.lower())

    name_text = " ".join(names)

    best_pattern = ""
    best_count = 0

    for pattern_name, pattern_info in catalog.items():
        if not isinstance(pattern_info, dict):
            continue
        indicators = pattern_info.get("indicators", [])
        match_count = 0
        for indicator in indicators:
            # Strip wildcards and lowercase
            clean = indicator.lower().replace("*", "").replace("class ", "").replace("@", "").strip()
            if not clean:
                continue
            if clean in name_text:
                match_count += 1
        if match_count >= 2 and match_count > best_count:
            best_count = match_count
            best_pattern = pattern_name

    return best_pattern


def _extract_responsibilities(classes: list[ClassInfo]) -> list[str]:
    """Extract responsibilities from class method names."""
    responsibilities: list[str] = []
    for cls in classes:
        for method in cls.methods:
            if method.startswith("_"):
                continue
            # Convert method name to readable responsibility
            readable = method.replace("_", " ")
            responsibilities.append(readable)
    return responsibilities


@monitored("orchestration.auto_enrich")
def enrich_from_manifest(model: Any, manifest: Manifest) -> None:
    """Enrich model components in-place from manifest data.

    Populates signatures, symbols, constants, contract, pattern, and
    responsibilities for each component by matching files to manifest modules.
    """
    # Build file -> ModuleInfo lookup
    file_lookup: dict[str, ModuleInfo] = {}
    for mod in manifest.modules:
        file_lookup[mod.file] = mod

    components = model.entities.get("components", [])

    for comp in components:
        if not isinstance(comp, Component):
            continue

        # Gather matching modules for this component's files
        matched_modules: list[ModuleInfo] = []
        for f in comp.files:
            if f in file_lookup:
                matched_modules.append(file_lookup[f])

        if not matched_modules:
            continue

        # Extract signatures
        if not comp.signatures:
            sigs: list[FunctionSignature] = []
            for mod in matched_modules:
                for func in mod.functions:
                    sigs.append(_parse_signature(func.name, func))
            comp.signatures = sigs

        # Extract symbols
        if not comp.symbols:
            symbols: list[Symbol] = []
            for mod in matched_modules:
                for cls in mod.classes:
                    symbols.append(_class_to_symbol(cls))
            comp.symbols = symbols

        # Extract constants
        if not comp.constants:
            consts: list[Constant] = []
            for mod in matched_modules:
                for name, value in mod.module_constants.items():
                    consts.append(Constant(name=name, value=value, context=mod.name))
            comp.constants = consts

        # Infer contract
        if not comp.contract:
            for mod in matched_modules:
                contract = _extract_contract(mod, mod.classes)
                if contract:
                    comp.contract = contract
                    break

        # Classify pattern
        if not comp.pattern:
            pattern = _classify_pattern(matched_modules)
            if pattern:
                comp.pattern = pattern

        # Extract responsibilities
        if not comp.responsibilities:
            all_classes: list[ClassInfo] = []
            for mod in matched_modules:
                all_classes.extend(mod.classes)
            resps = _extract_responsibilities(all_classes)
            if resps:
                comp.responsibilities = resps


def _extract_trigger(decorated_functions: list, func_name: str) -> str:
    """Find trigger decorator for a function."""
    for dec_func in decorated_functions:
        if dec_func.name == func_name:
            for dec in dec_func.decorators:
                if _TRIGGER_DECORATORS.search(dec):
                    return dec
    return ""


def _extract_steps(functions: list[FunctionInfo], entry_name: str) -> list[str]:
    """Extract ordered call steps from the entry point function's call graph."""
    for func in functions:
        if func.name == entry_name:
            return list(func.calls) if func.calls else []
    return []


def _extract_error_conditions(functions: list[FunctionInfo], entry_name: str) -> list[str]:
    """Extract error/post conditions from raises in the entry function."""
    for func in functions:
        if func.name == entry_name:
            return list(func.raises) if func.raises else []
    return []


@monitored("orchestration.auto_enrich_behaviors")
def enrich_behaviors_from_manifest(model: Any, manifest: Manifest) -> None:
    """Enrich model behaviors in-place from manifest data.

    Populates trigger, steps, and postconditions for each behavior by matching
    source_file to manifest modules and using the behavior name as entry point.
    """
    # Build file -> ModuleInfo lookup
    file_lookup: dict[str, ModuleInfo] = {}
    for mod in manifest.modules:
        file_lookup[mod.file] = mod

    behaviors = model.entities.get("behaviors", [])

    for behavior in behaviors:
        if not isinstance(behavior, Behavior):
            continue

        # Match source_file to module
        module = file_lookup.get(behavior.source_file or "")
        if not module:
            continue

        # Use behavior name (snake_case) as entry point function name
        entry_name = behavior.name.lower().replace(" ", "_").replace("-", "_")

        # Extract trigger from decorated functions (don't overwrite)
        if not behavior.trigger:
            trigger = _extract_trigger(module.decorated_functions, entry_name)
            if trigger:
                behavior.trigger = trigger

        # Extract steps from call graph (don't overwrite)
        if not behavior.steps:
            steps = _extract_steps(module.functions, entry_name)
            if steps:
                behavior.steps = steps

        # Extract postconditions from raises (don't overwrite)
        if not behavior.postconditions:
            conditions = _extract_error_conditions(module.functions, entry_name)
            if conditions:
                behavior.postconditions = [f"raises {exc}" for exc in conditions]
