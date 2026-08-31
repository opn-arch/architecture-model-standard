#!/usr/bin/env python3
"""Author Component Spec for COMP-9 (Configuration) via copilot-relay."""
import json
import httpx
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".architecture" / "authored_docs" / "configuration"
OUT.mkdir(parents=True, exist_ok=True)

MODEL = (ROOT / ".architecture-models" / "configuration" / ".architecture-model.yaml").read_text()

# Read ALL config source files (small enough to include in full)
CODE_FILES = [
    "src/architecture_model/config/__init__.py",
    "src/architecture_model/config/loader.py",
    "src/architecture_model/config/schema.py",
    "src/architecture_model/profiles/schema.py",
]

code_context = ""
for f in CODE_FILES:
    p = ROOT / f
    if p.exists():
        code_context += f"\n### {f}\n```python\n{p.read_text()}\n```\n"

SYSTEM_PROMPT = """You are an expert systems engineer writing a comprehensive Component Specification document.

CRITICAL FRAMING: Requirements alone are NOT enough. This document must capture three layers:
1. INTENT — WHY this component exists, what problem it solves, the philosophy behind design choices
2. GOALS & MEASURES OF EFFECTIVENESS — optimization targets, trade-off rationale, what "best output" looks like (not just pass/fail)  
3. REQUIREMENTS with RATIONALE — every "shall" statement paired with WHY it exists and the reasoning behind the threshold values

Write substantive, technically accurate documentation grounded in the actual code.
Use markdown formatting. Include mermaid diagrams where they add value.
Reference actual function names, class names, field names, and code patterns.
Do NOT include YAML frontmatter. Start directly with the heading."""

PROMPT = """# Task
Write a comprehensive Component Specification for **COMP-9: Configuration** of the Architecture Model Standard.

## Architecture Model (YAML)
```yaml
{model}
```

## Complete Source Code
{code}

## Document Structure (follow this exactly)

### 1. Purpose & Intent
WHY this component exists. The core problem: architecture tools historically required manual project-specific configuration, creating friction and preventing universal applicability. COMP-9 solves this with a self-bootstrapping, zero-config-required design. Explain the philosophy: "point at any repo and get a valid config."

### 2. Goals & Measures of Effectiveness
Not just requirements — optimization targets and trade-offs:
- **Goal: Universal applicability** — any Python/TS/Kotlin repo should work without config. MoE: % of repos where auto-discovery produces usable config without manual intervention.
- **Goal: Discovery accuracy** — heuristic-based discovery should claim >90% of source files and correctly identify architectural layers. MoE: file claim rate, layer accuracy.
- **Goal: Zero friction** — `get_config()` is the single entry point, always returns valid config. No setup ceremony.
- **Trade-off rationale**: Convention over configuration. Heuristics may produce false positives on non-standard layouts — this is acceptable because the alternative (manual config) has worse failure modes (no config at all).

### 3. Architecture Role & Position
Where COMP-9 sits: infrastructure layer, the "spine" every other component reads. Show the 5 inbound dependencies:
- COMP-3.1 (Scanners) → exclusion patterns
- COMP-6 (Extract) → settings
- COMP-11 (Pipeline Learning) → paths  
- COMP-12 (Utilities) → config
- Pipeline stages → functional block definitions

Include a **mermaid dependency diagram** showing COMP-9 at center with inbound arrows.

### 4. API Surface
Document every public function with signature, parameters, return type, behavior, and usage example:
- `get_config(root: Path) -> ProjectConfig` — the recommended entry point
- `load_config(root: Path) -> ProjectConfig` — from file only
- `discover_config(root: Path) -> tuple[ProjectConfig, DiscoveryReport]` — auto-discovery
- `write_config(config: ProjectConfig, root: Path) -> Path` — serialization
- `load_profile(name_or_path: str) -> DomainProfile` — domain profile loading

Include a **mermaid flowchart** showing the `get_config()` resolution logic (file exists? → load or discover → auto-discover sub_blocks → return).

### 5. Data Model
Document every dataclass with ALL fields, types, defaults, and what each field controls:
- `ProjectConfig` — the root config object (name, system, output, layers, functional_blocks, metrics, root, plus all @property accessors)
- `OutputConfig` / `ResolvedOutputConfig` — path templates with {{project}} placeholder
- `LayerConfig` — architecture tier definition
- `FunctionalBlockConfig` / `SubBlockConfig` — recursive capability decomposition
- `MetricConfig` — countable project metrics
- `DiscoveryReport` / `DiscoveryCandidate` — observability for auto-discovery

### 6. Auto-Discovery Engine
The heuristic logic that makes zero-config work:
- `_discover_layers()` — `_LAYER_HEURISTICS` table (web, services, data, pipeline, scheduling patterns)
- `_discover_metrics()` — `_METRIC_HEURISTICS` table (routers, models, migrations, templates)
- `_discover_functional_blocks()` — directory scanning, layout detection (flat vs nested)
- `_discover_sub_blocks()` — recursive sub-directory scanning within F-blocks
- `_derive_layers_from_blocks()` — fallback when no heuristic layers match

Include a **mermaid sequence diagram** showing the discovery flow.

### 7. Domain Profiles
The cross-domain extensibility system:
- 4 built-in profiles: software (default), controls, mechanical, electrical
- `DomainProfile` dataclass — enum extensions, entity extensions, conditional validation rules
- `EnumExtension` — adds values to ComponentKind, InterfaceType, etc.
- `EntityExtension` — adds properties to entity types (validated via JSON Schema)
- `ConditionalRule` — "when X, require Y" validation (e.g., "sensors must declare signal_type")
- How profiles integrate with the validator

### 8. Design Decisions & Rationale
Key decisions with the WHY:
| Decision | Rationale |
|----------|-----------|
| Typed dataclasses over raw dicts | Type safety, IDE support, validation at construction time |
| Auto-discovery over manual init | Reduces adoption friction from "write config" to "point and scan" |
| Convention-based layer detection | 80/20 rule — covers most Python web projects without configuration |
| Recursive sub-blocks | Mirrors real codebase structure (packages within packages) |
| YAML config format | Human-readable, already used by .architecture-model.yaml, no additional dependency |
| 1-hour manifest cache staleness | Balance between freshness and avoiding redundant full scans |

### 9. Consumers & Integration Patterns
For each consumer, document WHAT they use and HOW:
- **Scanners (COMP-3.1)**: Call `config.functional_blocks` for file discovery scope, use exclusion patterns from `EXCLUDED_DIRS`
- **Generator (COMP-3.3)**: Calls `get_config()` for `source_block_dict`, `layers`, metrics paths
- **Extract (COMP-6)**: Uses config for project settings and scanner parameters  
- **Pipeline (COMP-2)**: Reads `functional_blocks` to determine observation scope
- **CLI (COMP-8)**: Entry point calls `get_config()` before any command

### 10. Constraints & Limitations
Honest assessment of boundaries:
- YAML-only config format (no TOML, JSON, or programmatic config)
- Heuristic false positives on non-standard project layouts (monorepos, unusual naming)
- No hot-reload — config is loaded once per invocation
- Discovery heuristics are Python-web-centric — TypeScript/Kotlin projects get minimal layer detection
- No config validation schema (relies on dataclass construction)
- Sub-block discovery is directory-based only (no import-graph-based grouping at config level)

### 11. Requirements Traceability with Rationale
For each requirement, provide the "shall" statement AND the "why":
- Even though the model has 0 explicit requirements for COMP-9, derive them from code behavior and document with rationale statements
- Include Measures of Effectiveness where applicable
""".format(model=MODEL, code=code_context)


def main():
    print("Authoring COMP-9 component spec... ", end="", flush=True)
    
    full_response = ""
    with httpx.Client(timeout=300) as client:
        with client.stream(
            "POST",
            "http://localhost:8400/chat",
            json={"content": PROMPT, "system_prompt": SYSTEM_PROMPT},
        ) as resp:
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "chunk":
                        full_response += data["content"]
                    elif data.get("type") == "done":
                        break
    
    print(f"{len(full_response)} chars")
    out_path = OUT / "component_spec.md"
    out_path.write_text(full_response)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
