#!/usr/bin/env python3
"""Author SE docs for Manifest subsystem via copilot-relay."""
import json
import sys
import httpx
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".architecture" / "authored_docs" / "manifest"
OUT.mkdir(parents=True, exist_ok=True)

MODEL = (ROOT / ".architecture-models" / "manifest" / ".architecture-model.yaml").read_text()

# Read key source files for code context
CODE_FILES = [
    "src/architecture_model/manifest/types.py",
    "src/architecture_model/manifest/generator.py",
    "src/architecture_model/manifest/scanner.py",
    "src/architecture_model/manifest/call_graph.py",
    "src/architecture_model/manifest/interfaces.py",
    "src/architecture_model/manifest/grouping.py",
    "src/architecture_model/manifest/behavior.py",
    "src/architecture_model/manifest/multi_scanner.py",
    "src/architecture_model/manifest/recursive.py",
]

code_context = ""
for f in CODE_FILES:
    p = ROOT / f
    if p.exists():
        # First 80 lines for API surface
        lines = p.read_text().split("\n")[:80]
        code_context += f"\n### {f}\n```python\n" + "\n".join(lines) + "\n```\n"

SYSTEM_PROMPT = """You are an expert systems engineer writing architecture documentation.
Write substantive, technically accurate documentation based on the architecture model and code context provided.
Use markdown formatting. Include mermaid diagrams where they add value.
Be specific — reference actual component names, function signatures, data types, and relationships from the model.
Do NOT include YAML frontmatter. Start directly with the heading."""

DOCS = {
    "conops": """# Task
Write a Concept of Operations (ConOps) document for the **Manifest** subsystem of the Architecture Model Standard.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The ConOps should cover:
1. **System Overview** — what the Manifest subsystem does, its purpose in the larger architecture pipeline
2. **Stakeholders & Actors** — who/what uses the manifest (pipeline stages, CLI, MCP tools, developers)
3. **Operational Scenarios** — at least 4 concrete scenarios showing how manifest generation is triggered and consumed:
   - Full project scan for initial architecture extraction
   - Incremental scan with caching
   - Multi-language scanning (Python + TypeScript + Kotlin)
   - Recursive manifest generation for subsystem decomposition
4. **System Context** — external interfaces, dependencies on config, utils
5. **Operational Constraints** — performance, file exclusions, AST parsing limitations
6. **Data Flow** — from source files through scanning, analysis, grouping, to final Manifest dataclass

Include a mermaid diagram showing the data flow through the manifest pipeline.""",

    "functional_analysis": """# Task
Write a Functional Analysis document for the **Manifest** subsystem of the Architecture Model Standard.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The Functional Analysis should cover:
1. **Capability Inventory** — CAP-4 (Generate Reality Manifest) broken down into sub-capabilities
2. **Functional Decomposition** — how the capability is realized by the 4 components:
   - COMP-3 (Manifest core + types)
   - COMP-3.1 (Scanners — Python, TypeScript, Kotlin, body hints, metrics, caching)
   - COMP-3.2 (Graph & Analysis — call graphs, interfaces, behavior extraction, test analysis)
   - COMP-3.3 (Grouping & Generation — module grouping, manifest generation, recursive scanning, blocks)
3. **Capability-Component Mapping** — which component realizes which sub-capability
4. **Behavioral Flows** — key processing sequences:
   - The `generate_manifest()` flow: config → blocks → scan → derive interfaces → build manifest
   - The `scan_file()` flow: AST parse → extract functions/classes/imports → behavior extraction
   - The `group_modules()` flow: affinity scoring → merging → group formation
   - The `build_call_graph()` flow: index functions → resolve imports → build edges → trace flows
5. **Requirements Satisfaction** — how REQ-8 through REQ-19 are satisfied

Include mermaid sequence diagrams for the generate_manifest and scan_file flows.""",

    "logical_architecture": """# Task
Write a Logical Architecture document for the **Manifest** subsystem of the Architecture Model Standard.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The Logical Architecture should cover:
1. **Component Structure** — COMP-3 containing COMP-3.1, COMP-3.2, COMP-3.3 with their files and responsibilities
2. **Layer Allocation** — all components are in the `domain` layer
3. **Dependency Graph** — internal dependencies (3.2→3.1, 3.3→3.2) and external dependencies (from pipeline, orchestration, extract, CLI, authoring)
4. **Interface Specification** — the 5 interfaces (IF-2 runner CLI, IF-4 Library API, IF-auto-COMP-3.1/3.2/3.3)
5. **Key Data Types** — Manifest, ModuleInfo, FunctionInfo, ClassInfo, InterfaceEdge, CallGraph, ModuleGroup, BlockManifest, RecursiveManifest
6. **Design Decisions** — typed dataclasses over raw dicts, scan caching, regex fallback scanning, multi-signal grouping

Include a mermaid component diagram showing the internal structure and dependency flow.""",

    "use_cases": """# Task
Write a Use Cases document for the **Manifest** subsystem of the Architecture Model Standard.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The Use Cases should cover at least 6 use cases:
1. **UC-1: Generate Full Project Manifest** — actor: Pipeline Coordinator, trigger: observe stage, steps through generate_manifest()
2. **UC-2: Scan Individual Source File** — actor: Generator, trigger: per-file scan loop, steps through scan_file() AST extraction
3. **UC-3: Resolve Import Dependencies** — actor: Generator, trigger: post-scan, steps through derive_interfaces()
4. **UC-4: Build Call Graph** — actor: Pipeline/Analysis, trigger: behavioral analysis needed, steps through build_call_graph() + trace_flow()
5. **UC-5: Group Modules into Components** — actor: Pipeline (allocate stage), trigger: component boundary detection, steps through group_modules() with multi-signal affinity
6. **UC-6: Multi-Language Scanning** — actor: Pipeline, trigger: non-Python files detected, steps through multi_scanner dispatch
7. **UC-7: Recursive Manifest Generation** — actor: Pipeline (decompose stage), trigger: subsystem decomposition, steps through recursive.py

For each use case include: Actor, Preconditions, Main Flow (numbered steps referencing actual functions), Postconditions, Error Handling.

Include a mermaid use case diagram showing actors and use cases.""",
}


def author_doc(name: str, prompt_template: str) -> str:
    """Send prompt to copilot-relay and collect SSE response."""
    prompt = prompt_template.format(model=MODEL, code=code_context)
    
    print(f"  Authoring {name}... ", end="", flush=True)
    
    full_response = ""
    with httpx.Client(timeout=300) as client:
        with client.stream(
            "POST",
            "http://localhost:8400/chat",
            json={"content": prompt, "system_prompt": SYSTEM_PROMPT},
        ) as resp:
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "chunk":
                        full_response += data["content"]
                    elif data.get("type") == "done":
                        break
    
    print(f"{len(full_response)} chars")
    return full_response


def main():
    for name, prompt_template in DOCS.items():
        content = author_doc(name, prompt_template)
        out_path = OUT / f"{name}.md"
        out_path.write_text(content)
        print(f"  Saved: {out_path}")
    
    print(f"\nAll 4 docs authored in {OUT}")


if __name__ == "__main__":
    main()
