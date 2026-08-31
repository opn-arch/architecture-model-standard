"""Per-stage LLM re-inference prompt builders for gap analysis.

Builds prompts that give an LLM the same inputs a deterministic pipeline stage
received and asks it to independently produce the output, acting as a second
opinion to identify what the deterministic pipeline gets wrong.
"""
from __future__ import annotations

import json
import re
from typing import Any


def _fmt_modules(modules: list[dict]) -> str:
    lines: list[str] = []
    for m in modules:
        funcs = ", ".join(m.get("functions", []))
        classes = ", ".join(m.get("classes", []))
        doc = m.get("docstring", "")
        doc_part = f'  doc="{doc}"' if doc else ""
        lines.append(f"- {m['path']}{doc_part}  functions=[{funcs}]  classes=[{classes}]")
    return "\n".join(lines)


def _fmt_capabilities(capabilities: list[dict]) -> str:
    return "\n".join(f"- {c['id']}: {c['name']}" for c in capabilities)


def _fmt_components(components: list[dict]) -> str:
    lines: list[str] = []
    for c in components:
        files = ", ".join(c.get("files", []))
        lines.append(f"- {c['id']}: {c['name']} [{files}]")
    return "\n".join(lines)


def _fmt_imports(imports: list[dict]) -> str:
    return "\n".join(f"- {i['source']} -> {i['target']}" for i in imports)


_TEMPLATES: dict[str, str] = {
    "infer": """You are an architecture analyst. Given these source modules, identify the capabilities this codebase provides.

## Modules
{modules}

## Task
Analyze the module names, docstrings, functions, and classes to infer a **hierarchical capability tree**:
1. **Root capability** — one sentence describing the system's overall purpose
2. **L1 capability groups** — 3-5 thematic groups (e.g., "Understand", "Validate", "Generate", "Evolve")
3. **L2 capabilities** — concrete functional blocks within each group
4. **L3 sub-capabilities** — specific functions within each L2 capability

Each capability MUST have a `name` (verb phrase) and `description` (1 sentence, semantic).

Also identify **behaviors** — use cases, workflows, operational sequences.

Respond with JSON only:
```json
{{"capabilities": [{{"name": "...", "description": "...", "sub_capabilities": [{{"name": "...", "description": "...", "sub_capabilities": [...]}}]}}], "behaviors": [{{"name": "...", "type": "..."}}]}}
```""",

    "allocate": """You are an architecture analyst. Given these modules and capabilities, group modules into components with layer assignments.

## Modules
{modules}

## Capabilities
{capabilities}

## Task
Group the modules into logical components. Each component should:
- Have a clear name and purpose
- Be assigned to a layer (e.g., core, cli, api, data)
- Realize one or more capabilities

Respond with JSON only:
```json
{{"components": [{{"name": "...", "files": ["..."], "layer": "...", "capability_id": "..."}}]}}
```""",

    "relate": """You are an architecture analyst. Given these components, capabilities, and import edges, produce the relationships between entities.

## Components
{components}

## Capabilities
{capabilities}

## Import Edges
{imports}

## Task
Identify relationships including: realizes, depends-on, contains, exposes, consumes.
Use the import edges to determine dependency relationships.

Respond with JSON only:
```json
{{"relationships": [{{"from": "...", "to": "...", "type": "..."}}]}}
```""",

    "specify": """You are an architecture analyst. Given these components, identify the interfaces they expose or consume.

## Components
{components}

## Task
For each component, identify its interface surface — APIs, protocols, data exchanges.

Respond with JSON only:
```json
{{"interfaces": [{{"name": "...", "type": "...", "component_id": "..."}}]}}
```""",

    "contract": """You are an architecture analyst. Given these components and test files, match each test file to the component it tests.

## Components
{components}

## Test Files
{test_files}

## Task
Map each test file to the component it validates.

Respond with JSON only:
```json
{{"contracts": [{{"test_file": "...", "component_id": "..."}}]}}
```""",

    "validate": """You are an architecture analyst. Given this model summary, identify structural issues.

## Model Summary
{model_summary}

## Task
Check for: orphan components, missing relationships, capability gaps, naming issues.

Respond with JSON only:
```json
{{"issues": ["..."], "score": 85}}
```""",
}


def build_reinfer_prompt(stage_name: str, **kwargs: Any) -> str:
    """Build an LLM re-inference prompt for the given pipeline stage."""
    template = _TEMPLATES.get(stage_name)
    if template is None:
        return f"Review the output of the '{stage_name}' pipeline stage and identify any issues or improvements. Respond with JSON."

    fmt: dict[str, str] = {}
    if "modules" in kwargs:
        fmt["modules"] = _fmt_modules(kwargs["modules"])
    if "capabilities" in kwargs:
        fmt["capabilities"] = _fmt_capabilities(kwargs["capabilities"])
    if "components" in kwargs:
        fmt["components"] = _fmt_components(kwargs["components"])
    if "imports" in kwargs:
        fmt["imports"] = _fmt_imports(kwargs["imports"])
    if "test_files" in kwargs:
        fmt["test_files"] = "\n".join(f"- {f}" for f in kwargs["test_files"])
    if "model_summary" in kwargs:
        fmt["model_summary"] = json.dumps(kwargs["model_summary"], indent=2)

    return template.format_map(fmt)


def parse_reinfer_response(stage_name: str, response: str) -> dict:
    """Extract JSON from an LLM response (markdown fences or plain). Returns {} on failure."""
    # Try markdown fence first
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
    text = m.group(1) if m else response
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}
