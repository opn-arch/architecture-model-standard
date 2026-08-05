"""Call graph infrastructure for multi-hop behavior flow tracing."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from architecture_model.manifest.types import FunctionInfo, Manifest


@dataclass
class CallGraph:
    """Resolved call graph from manifest."""
    edges: dict[str, list[str]] = field(default_factory=dict)
    functions: dict[str, FunctionInfo] = field(default_factory=dict)
    locations: dict[str, str] = field(default_factory=dict)


@dataclass
class FlowTrace:
    """Result of tracing a flow from an entry point."""
    entry: str
    steps: list[tuple[str, str]]
    components_crossed: list[str]
    depth: int
    truncated: bool


def build_call_graph(manifest: Manifest) -> CallGraph:
    """Build a resolved call graph from manifest data."""
    graph = CallGraph()

    # Index: func_name -> list of (module_file, FunctionInfo)
    name_index: dict[str, list[str]] = {}  # name -> [qualified_name, ...]

    # Register all functions
    for mod in manifest.modules:
        for func in mod.functions:
            qname = f"{mod.file}:{func.name}"
            graph.functions[qname] = func
            graph.locations[qname] = mod.file
            name_index.setdefault(func.name, []).append(qname)

    # Build module path -> file mapping for import resolution
    # mod.name is human-readable, so derive Python path from file path
    mod_path_to_file: dict[str, str] = {}
    for mod in manifest.modules:
        # "app/services/graph_service.py" -> "app.services.graph_service"
        py_path = mod.file.replace("/", ".").replace("\\", ".")
        if py_path.endswith(".py"):
            py_path = py_path[:-3]
        if py_path.endswith(".__init__"):
            py_path = py_path[:-9]
        mod_path_to_file[py_path] = mod.file
        # Also register the original name in case it's a dotted path
        mod_path_to_file[mod.name] = mod.file

    # Resolve edges
    for mod in manifest.modules:
        # Extract imported module names from import strings
        # Imports can be bare dotted names ("app.services.foo"),
        # "from X import Y", or "import X" format
        imported_modules: set[str] = set()
        for imp in mod.imports:
            if imp.startswith("from "):
                parts = imp.split()
                if len(parts) >= 2:
                    imported_modules.add(parts[1])
            elif imp.startswith("import "):
                parts = imp.split()
                if len(parts) >= 2:
                    imported_modules.add(parts[1])
            else:
                # Bare dotted name like "app.services.graph_service"
                imported_modules.add(imp)

        # Get files of imported modules
        imported_files: set[str] = set()
        for mname in imported_modules:
            if mname in mod_path_to_file:
                imported_files.add(mod_path_to_file[mname])

        local_funcs = {f.name for f in mod.functions}

        for func in mod.functions:
            qname = f"{mod.file}:{func.name}"
            resolved: list[str] = []

            for callee_name in func.calls:
                # 1. Local call
                if callee_name in local_funcs and callee_name != func.name:
                    resolved.append(f"{mod.file}:{callee_name}")
                    continue

                # 2. Imported module calls
                candidates = [
                    qn for qn in name_index.get(callee_name, [])
                    if graph.locations[qn] in imported_files
                ]
                if candidates:
                    resolved.extend(candidates)
                    continue

                # 3. Unresolved - skip

            graph.edges[qname] = resolved

    return graph


def trace_flow(graph: CallGraph, entry: str, *, max_depth: int = 5) -> FlowTrace:
    """BFS from entry point, following call edges."""
    steps: list[tuple[str, str]] = []
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()
    queue.append((entry, 0))
    truncated = False
    actual_depth = 0

    while queue:
        qname, depth = queue.popleft()
        if qname in visited:
            continue
        visited.add(qname)

        file, fname = qname.split(":", 1)
        steps.append((file, fname))
        actual_depth = depth

        if depth >= max_depth:
            truncated = True
            continue

        for callee in graph.edges.get(qname, []):
            if callee not in visited:
                queue.append((callee, depth + 1))

    return FlowTrace(
        entry=entry,
        steps=steps,
        components_crossed=[],
        depth=actual_depth,
        truncated=truncated,
    )


def map_flow_to_components(flow: FlowTrace, file_to_comp: dict[str, str]) -> FlowTrace:
    """Populate components_crossed on a FlowTrace."""
    crossed: list[str] = []
    prev: str | None = None
    for file, _ in flow.steps:
        comp = file_to_comp.get(file)
        if comp and comp != prev:
            crossed.append(comp)
            prev = comp

    return FlowTrace(
        entry=flow.entry,
        steps=flow.steps,
        components_crossed=crossed,
        depth=flow.depth,
        truncated=flow.truncated,
    )
