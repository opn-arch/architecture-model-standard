"""Derive requirements from code signals captured by the observe stage.

Analyzes constants, decorators, routes, abstract classes, imports, and test coverage
to automatically produce functional and non-functional requirements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Patterns that indicate performance/capacity constants
_PERF_PATTERNS = [
    (re.compile(r"(?i)(timeout|ttl|expire|deadline)"), "timing"),
    (re.compile(r"(?i)(max|limit|cap|threshold|ceiling)"), "capacity"),
    (re.compile(r"(?i)(retry|attempts|backoff|max_retries)"), "reliability"),
    (re.compile(r"(?i)(batch|chunk|page|buffer)_?size"), "throughput"),
    (re.compile(r"(?i)(port|host|url|endpoint|base_url)"), "deployment"),
]

# Decorators that indicate requirement categories
_DECORATOR_SIGNALS = {
    "security": [
        "login_required",
        "auth",
        "permission_required",
        "requires_auth",
        "authenticated",
        "permissions",
        "csrf_protect",
    ],
    "reliability": ["retry", "backoff", "circuit_breaker", "timeout", "rate_limit"],
    "performance": ["cache", "lru_cache", "cached", "memoize", "cached_property"],
    "observability": ["trace", "instrument", "monitor", "log_call", "metrics"],
}

# Imports that indicate observability
_OBSERVABILITY_IMPORTS = {
    "logging",
    "structlog",
    "loguru",
    "sentry_sdk",
    "opentelemetry",
    "prometheus_client",
}


@dataclass
class DerivedRequirement:
    """A requirement automatically derived from code analysis."""

    id: str
    name: str
    category: str  # performance|security|reliability|quality|interface|observability|technology|error_handling
    priority: str  # must|should|could
    source_file: str
    source_signal: str
    component_id: str = ""
    evidence: str = ""


def derive_requirements(
    ctx: Any,
    file_component_map: dict[str, str] | None = None,
    test_map: dict[str, list[str]] | None = None,
) -> list[DerivedRequirement]:
    """Derive requirements from observe stage output.

    Args:
        ctx: PipelineContext with cached observe results
        file_component_map: file path → component ID mapping
        test_map: source file → test files mapping

    Returns:
        List of derived requirements, sorted by priority then category.
    """
    observe_result = ctx.get("observe") if ctx.has("observe") else None
    if not observe_result or not observe_result.output:
        return []

    inventory = observe_result.output
    file_map = file_component_map or {}
    reqs: list[DerivedRequirement] = []
    counters: dict[str, int] = {}  # category → count

    def _next_id(category: str) -> str:
        prefix = category[0].upper()
        counters[category] = counters.get(category, 0) + 1
        return f"REQ-{prefix}{counters[category]}"

    def _comp_for_file(filepath: str) -> str:
        return file_map.get(filepath, "")

    # 1. Constants → Performance/Capacity requirements
    for mod in inventory.modules:
        for const in mod.constants or []:
            for pattern, subcategory in _PERF_PATTERNS:
                if pattern.search(const.name):
                    cat = (
                        "performance"
                        if subcategory in ("timing", "throughput")
                        else "reliability"
                        if subcategory == "reliability"
                        else "technology"
                    )
                    reqs.append(
                        DerivedRequirement(
                            id=_next_id(cat),
                            name=f"{const.name} = {const.value}" if const.value else const.name,
                            category=cat,
                            priority="must" if subcategory == "timing" else "should",
                            source_file=str(mod.path),
                            source_signal=f"constant:{const.name}={const.value}",
                            component_id=_comp_for_file(str(mod.path)),
                            evidence=f"UPPER_CASE constant in {mod.path.name}",
                        )
                    )
                    break  # Only match first pattern

    # 2. Decorators → Security/Reliability/Performance requirements
    for mod in inventory.modules:
        for func in mod.functions or []:
            for dec in func.decorators or []:
                dec_name = dec.split("(")[0].split(".")[-1].lower()
                for cat, signals in _DECORATOR_SIGNALS.items():
                    if any(s in dec_name for s in signals):
                        priority = "must" if cat == "security" else "should"
                        reqs.append(
                            DerivedRequirement(
                                id=_next_id(cat),
                                name=f"{func.name} requires {dec_name}",
                                category=cat,
                                priority=priority,
                                source_file=str(mod.path),
                                source_signal=f"decorator:@{dec}",
                                component_id=_comp_for_file(str(mod.path)),
                                evidence=f"@{dec} on {func.name}() in {mod.path.name}",
                            )
                        )
                        break

        # Also check class method decorators
        for cls in mod.classes or []:
            for method in cls.method_details or []:
                method_name = (
                    method.get("name", "")
                    if isinstance(method, dict)
                    else getattr(method, "name", "")
                )
                method_decs = (
                    method.get("decorators", [])
                    if isinstance(method, dict)
                    else getattr(method, "decorators", [])
                )
                for dec in method_decs or []:
                    dec_name = dec.split("(")[0].split(".")[-1].lower()
                    for cat, signals in _DECORATOR_SIGNALS.items():
                        if any(s in dec_name for s in signals):
                            priority = "must" if cat == "security" else "should"
                            reqs.append(
                                DerivedRequirement(
                                    id=_next_id(cat),
                                    name=f"{cls.name}.{method_name} requires {dec_name}",
                                    category=cat,
                                    priority=priority,
                                    source_file=str(mod.path),
                                    source_signal=f"decorator:@{dec}",
                                    component_id=_comp_for_file(str(mod.path)),
                                    evidence=f"@{dec} on {cls.name}.{method_name}()",
                                )
                            )
                            break

    # 3. Routes → Security requirements (authenticated endpoints)
    for route in inventory.routes or []:
        if route.is_authenticated:
            reqs.append(
                DerivedRequirement(
                    id=_next_id("security"),
                    name=f"{route.method} {route.path} requires authentication",
                    category="security",
                    priority="must",
                    source_file=str(route.file),
                    source_signal=f"route:authenticated:{route.method}:{route.path}",
                    component_id=_comp_for_file(str(route.file)),
                    evidence=f"Authenticated route in {route.file.name}",
                )
            )

    # 4. Technology constraints (already captured by observe)
    for constraint in inventory.constraints or []:
        reqs.append(
            DerivedRequirement(
                id=_next_id("technology"),
                name=f"{constraint.name}: {constraint.value}",
                category="technology",
                priority="must" if "python" in constraint.name.lower() else "should",
                source_file=str(constraint.source) if hasattr(constraint, "source") else "",
                source_signal=f"constraint:{constraint.constraint_type}:{constraint.name}",
                component_id="",
                evidence=f"Detected {constraint.constraint_type} constraint",
            )
        )

    # 5. Observability — modules importing logging
    logged_components: set[str] = set()
    for mod in inventory.modules:
        mod_imports = {imp.split(".")[-1] if "." in imp else imp for imp in (mod.imports or [])}
        if mod_imports & _OBSERVABILITY_IMPORTS:
            comp = _comp_for_file(str(mod.path))
            if comp and comp not in logged_components:
                logged_components.add(comp)
                reqs.append(
                    DerivedRequirement(
                        id=_next_id("observability"),
                        name=f"Component {comp} has logging instrumentation",
                        category="observability",
                        priority="could",
                        source_file=str(mod.path),
                        source_signal="import:logging",
                        component_id=comp,
                        evidence=f"Imports logging/structlog in {mod.path.name}",
                    )
                )

    # 6. Abstract/Protocol classes → Interface requirements
    for mod in inventory.modules:
        for cls in mod.classes or []:
            bases = cls.bases or []
            is_protocol = any(b in ("Protocol", "ABC", "ABCMeta") for b in bases) or cls.is_abstract
            if is_protocol:
                methods = []
                for m in cls.method_details or []:
                    mname = m.get("name", "") if isinstance(m, dict) else getattr(m, "name", "")
                    if mname and not mname.startswith("_"):
                        methods.append(mname)
                if methods:
                    reqs.append(
                        DerivedRequirement(
                            id=_next_id("interface"),
                            name=f"{cls.name} protocol requires: {', '.join(methods[:5])}",
                            category="interface",
                            priority="must",
                            source_file=str(mod.path),
                            source_signal=f"abstract_class:{cls.name}",
                            component_id=_comp_for_file(str(mod.path)),
                            evidence=f"Abstract/Protocol class with {len(methods)} required methods",
                        )
                    )

    # 7. Test coverage → Quality requirements
    if test_map:
        comp_test_counts: dict[str, int] = {}
        for src_file, tests in test_map.items():
            comp = _comp_for_file(src_file)
            if comp:
                comp_test_counts[comp] = comp_test_counts.get(comp, 0) + len(tests)

        for comp, count in sorted(comp_test_counts.items(), key=lambda x: -x[1]):
            reqs.append(
                DerivedRequirement(
                    id=_next_id("quality"),
                    name=f"Component {comp} has {count} test file(s) covering its source",
                    category="quality",
                    priority="should",
                    source_file="",
                    source_signal=f"test_coverage:{comp}:{count}",
                    component_id=comp,
                    evidence=f"{count} test files import this component's source",
                )
            )

    # 8. Error handling density
    for mod in inventory.modules:
        # Count functions with significant try/except (heuristic: body_hint mentions "try" or "except")
        error_handlers = 0
        for func in mod.functions or []:
            hint = (func.body_hint or "").lower()
            if "try" in hint or "except" in hint or "raise" in hint:
                error_handlers += 1
        if error_handlers >= 3:
            reqs.append(
                DerivedRequirement(
                    id=_next_id("error_handling"),
                    name=f"{mod.path.name} has {error_handlers} error-handling functions",
                    category="error_handling",
                    priority="could",
                    source_file=str(mod.path),
                    source_signal=f"error_handling:{error_handlers}_functions",
                    component_id=_comp_for_file(str(mod.path)),
                    evidence=f"{error_handlers} functions with try/except/raise patterns",
                )
            )

    # Sort: must first, then should, then could; within priority by category
    priority_order = {"must": 0, "should": 1, "could": 2}
    reqs.sort(key=lambda r: (priority_order.get(r.priority, 9), r.category, r.id))

    return reqs


def select_top_requirements(
    reqs: list[DerivedRequirement], max_count: int = 15
) -> list[DerivedRequirement]:
    """Select the top N requirements for inclusion in the model YAML.

    Strategy: diverse category coverage + highest priority.
    """
    if len(reqs) <= max_count:
        return reqs

    # Ensure at least 1 per category, then fill by priority
    selected: list[DerivedRequirement] = []
    by_category: dict[str, list[DerivedRequirement]] = {}
    for r in reqs:
        by_category.setdefault(r.category, []).append(r)

    # One per category (highest priority first)
    for cat, cat_reqs in sorted(by_category.items()):
        if cat_reqs:
            selected.append(cat_reqs[0])

    # Fill remaining slots from overall priority order
    selected_ids = {r.id for r in selected}
    for r in reqs:
        if len(selected) >= max_count:
            break
        if r.id not in selected_ids:
            selected.append(r)
            selected_ids.add(r.id)

    return selected[:max_count]


def persist_requirements(
    reqs: list[DerivedRequirement],
    output_dir: Path,
) -> Path:
    """Write full derived requirements to YAML artifact.

    Returns path to written file.
    """
    import yaml

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "derived_requirements.yaml"

    data = {
        "derived_requirements": [
            {
                "id": r.id,
                "name": r.name,
                "category": r.category,
                "priority": r.priority,
                "source_file": r.source_file,
                "source_signal": r.source_signal,
                "component_id": r.component_id,
                "evidence": r.evidence,
            }
            for r in reqs
        ],
        "summary": {
            "total": len(reqs),
            "by_priority": {
                "must": sum(1 for r in reqs if r.priority == "must"),
                "should": sum(1 for r in reqs if r.priority == "should"),
                "could": sum(1 for r in reqs if r.priority == "could"),
            },
            "by_category": {
                cat: sum(1 for r in reqs if r.category == cat)
                for cat in sorted(set(r.category for r in reqs))
            },
        },
    }

    output_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return output_path
