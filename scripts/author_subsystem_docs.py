#!/usr/bin/env python3
"""Author SE documentation for any subsystem via copilot-relay.

Usage:
    python3 author_subsystem_docs.py <view_slug> [--spec]
    
Examples:
    python3 author_subsystem_docs.py pipeline          # 5-doc SE suite
    python3 author_subsystem_docs.py configuration --spec  # Single component spec
    python3 author_subsystem_docs.py manifest          # 5-doc SE suite

The script:
1. Reads the subsystem view model from .architecture-models/<slug>/
2. Reads source files listed in the model components
3. Sends prompts to copilot-relay with the SE-manifesto system prompt
4. Saves authored docs to .architecture/authored_docs/<slug>/
5. Compiles a PDF via pandoc+xelatex with mermaid rendering

Requires: copilot-relay at localhost:8400, mmdc, pandoc, xelatex
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# SE Manifesto System Prompt (shared across all doc types)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert systems engineer writing architecture documentation.

CRITICAL FRAMING — Requirements alone are NOT enough. Every document must capture three layers:

1. **INTENT** — WHY this subsystem/component exists, what problem it solves, the philosophy behind design choices. Not just "what it does" but "why it matters" and "what would break without it."

2. **GOALS & MEASURES OF EFFECTIVENESS** — Optimization targets and trade-offs, not just pass/fail criteria. What does "best output" look like? What are the MoEs (Measures of Effectiveness) that tell us if the subsystem is achieving its purpose, not just meeting minimum requirements?

3. **REQUIREMENTS WITH RATIONALE** — Every "shall" statement paired with WHY it exists. Include the reasoning behind threshold values. A requirement without rationale is a mandate without justification — it invites malicious compliance.

Additionally:
- **Trade-off rationale**: Document what was traded and why. Every design decision is a trade-off; make the reasoning explicit.
- **Value functions**: Where relevant, describe how much MORE valuable the system becomes when it exceeds a requirement, not just whether it passes.
- **Failure modes**: What happens when this subsystem fails? What degrades gracefully, what fails hard?

Write substantive, technically accurate documentation grounded in the actual code.
Use markdown formatting. Include mermaid diagrams where they add clear value.
Reference actual function names, class names, field names, data types, and code patterns from the model and source code.
Do NOT include YAML frontmatter. Start directly with the heading."""


# ---------------------------------------------------------------------------
# Doc-type prompt templates
# ---------------------------------------------------------------------------

def _conops_prompt(name: str, model: str, code: str) -> str:
    return f"""# Task
Write a Concept of Operations (ConOps) document for the **{name}** subsystem.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The ConOps must cover:
1. **System Overview** — what this subsystem does, its purpose in the larger architecture. State the INTENT: why does this exist? What problem does it solve that nothing else can?
2. **Stakeholders & Actors** — who/what uses this subsystem (other components, external tools, humans). What are their goals?
3. **Operational Scenarios** — at least 4 concrete scenarios showing how this subsystem is triggered and consumed. For each scenario, explain the INTENT (what the user/system is trying to achieve), not just the steps.
4. **System Context** — external interfaces, dependencies. Why these dependencies exist (not just that they exist).
5. **Operational Constraints** — performance, resource limits, failure modes. For each constraint, explain the RATIONALE (why this threshold, what happens if violated).
6. **Data Flow** — from inputs through processing to outputs.
7. **Measures of Effectiveness** — how do we know this subsystem is performing WELL (not just "working")? What metrics would tell us it's achieving its goals optimally?

Include a mermaid diagram showing the data flow through this subsystem."""


def _functional_analysis_prompt(name: str, model: str, code: str) -> str:
    return f"""# Task
Write a Functional Analysis document for the **{name}** subsystem.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The Functional Analysis must cover:
1. **Capability Inventory** — all capabilities this subsystem provides, decomposed into sub-capabilities where appropriate. For each capability, state the INTENT (why it exists) and the GOAL (what optimal delivery looks like).
2. **Functional Decomposition** — how capabilities are realized by components. Show the hierarchy.
3. **Capability-Component Mapping** — which component realizes which capability, with rationale for the allocation.
4. **Behavioral Flows** — key processing sequences as mermaid sequence diagrams. For each flow, explain what the system is TRYING TO ACHIEVE (intent), not just the steps.
5. **Requirements Satisfaction** — how each requirement is satisfied, with RATIONALE for each requirement (why it exists, why that threshold, what the consequences of violation are).
6. **Trade-offs & Design Decisions** — what was considered, what was chosen, WHY. What would change if constraints changed?
7. **Measures of Effectiveness** — for each capability, what metrics indicate it's performing optimally (not just meeting minimum)?

Include mermaid sequence diagrams for the 2-3 most important behavioral flows."""


def _logical_architecture_prompt(name: str, model: str, code: str) -> str:
    return f"""# Task
Write a Logical Architecture document for the **{name}** subsystem.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The Logical Architecture must cover:
1. **Component Structure** — all components with their files, responsibilities, and purpose. For each component, state the INTENT (why this boundary exists here).
2. **Layer Allocation** — which layer each component belongs to and WHY (not just "it's in domain layer" but "it's in domain because...").
3. **Dependency Graph** — internal and external dependencies with mermaid diagram. For each dependency, explain WHY it exists (what would break without it).
4. **Interface Specification** — all interfaces with their type and purpose. What contract does each interface enforce?
5. **Key Data Types** — important dataclasses, protocols, enums. Why these abstractions exist.
6. **Design Decisions & Rationale** — key architectural choices with the TRADE-OFFS explicitly documented:
   | Decision | Alternatives Considered | Chosen | Rationale | What Would Change If... |
7. **Failure Modes** — what happens when each component fails? What degrades gracefully vs. fails hard?

Include a mermaid component diagram showing the internal structure and dependency flow."""


def _use_cases_prompt(name: str, model: str, code: str) -> str:
    return f"""# Task
Write a Use Cases document for the **{name}** subsystem.

## Architecture Model (YAML)
```yaml
{model}
```

## Code Context
{code}

## Requirements
The Use Cases must cover at least 5-7 use cases derived from the capabilities and behaviors in the model.

For each use case include:
- **Actor** — who initiates this
- **Intent** — WHY the actor is doing this (their goal, not just the action)
- **Preconditions** — what must be true before
- **Main Flow** — numbered steps referencing actual function names and classes from the code
- **Postconditions** — what is true after success
- **Error Handling** — what happens on failure, how the system degrades
- **Quality Attributes** — performance expectations, reliability guarantees
- **Measures of Effectiveness** — how do we know this use case executed OPTIMALLY (not just "completed")?

Include a mermaid use case or flow diagram showing actors and use cases."""


def _component_spec_prompt(name: str, model: str, code: str) -> str:
    return f"""# Task
Write a comprehensive Component Specification for the **{name}** subsystem.

## Architecture Model (YAML)
```yaml
{model}
```

## Complete Source Code
{code}

## Document Structure

### 1. Purpose & Intent
WHY this component exists. What problem does it solve? What would break without it? The philosophy behind its design.

### 2. Goals & Measures of Effectiveness
Optimization targets and trade-offs — not just pass/fail:
- What does "best output" look like for this component?
- What MoEs tell us it's achieving its purpose optimally?
- What trade-offs were made and why?

### 3. Architecture Role & Position
Where it sits in the system, who depends on it, who it depends on. Include a mermaid dependency diagram.

### 4. API Surface
Every public function with signature, parameters, return type, behavior, and usage example.

### 5. Data Model
Every dataclass with ALL fields, types, defaults, and what each field controls.

### 6. Key Algorithms & Logic
The core processing logic — not line-by-line but the conceptual approach. Why this algorithm, what alternatives exist.

### 7. Design Decisions & Rationale
| Decision | Alternatives | Chosen | Rationale | What Would Change If... |

### 8. Consumers & Integration Patterns
For each consumer: WHAT they use, HOW, and WHY.

### 9. Constraints & Limitations
Honest assessment with rationale for each constraint.

### 10. Requirements Traceability with Rationale
Every requirement with the "shall" statement AND the "why." Include MoEs."""


# ---------------------------------------------------------------------------
# Core authoring logic
# ---------------------------------------------------------------------------

def read_model(slug: str) -> str:
    """Read subsystem view model YAML."""
    model_path = ROOT / ".architecture-models" / slug / ".architecture-model.yaml"
    if not model_path.exists():
        print(f"ERROR: No model at {model_path}", file=sys.stderr)
        sys.exit(1)
    return model_path.read_text()


def read_code_context(model_yaml: str, max_lines_per_file: int = 80) -> str:
    """Extract code context from files listed in the model."""
    import yaml
    model = yaml.safe_load(model_yaml)
    
    files: list[str] = []
    for comp in (model.get("entities", {}).get("components", []) or []):
        files.extend(comp.get("files", []))
    
    code = ""
    for f in files:
        p = ROOT / f
        if p.exists():
            lines = p.read_text().split("\n")[:max_lines_per_file]
            code += f"\n### {f}\n```python\n" + "\n".join(lines) + "\n```\n"
    return code


def author_doc(prompt: str, name: str) -> str:
    """Send prompt to copilot-relay and collect SSE response."""
    print(f"  Authoring {name}... ", end="", flush=True)
    
    full_response = ""
    with httpx.Client(timeout=600) as client:
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


def build_pdf(slug: str, doc_files: list[Path], output_name: str) -> None:
    """Compile authored docs + artifact traceability into PDF."""
    import re
    import tempfile
    
    MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
    
    img_dir = ROOT / ".architecture" / "_pdf_images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_counter = [0]
    
    def render_mermaid(mmd_content: str, out_png: Path) -> bool:
        with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as f:
            f.write(mmd_content)
            mmd_path = f.name
        try:
            import os
            env = {**os.environ}
            env["PUPPETEER_EXECUTABLE_PATH"] = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            result = subprocess.run(
                ["mmdc", "-i", mmd_path, "-o", str(out_png), "-w", "1400", "-b", "white", "--scale", "2"],
                capture_output=True, text=True, timeout=30, env=env,
            )
            return result.returncode == 0 and out_png.exists()
        except Exception:
            return False
        finally:
            Path(mmd_path).unlink(missing_ok=True)
    
    def process_doc(src: Path, truncate_pattern: str | None = None) -> str:
        text = src.read_text()
        # Strip YAML frontmatter
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                text = text[end + 3:].lstrip("\n")
        # Truncate if pattern
        if truncate_pattern:
            pat = re.compile(truncate_pattern)
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if pat.match(line):
                    text = "\n".join(lines[:i])
                    break
        # Render mermaid
        def replace_mermaid(m):
            img_counter[0] += 1
            png_path = img_dir / f"mermaid_{img_counter[0]}.png"
            if render_mermaid(m.group(1), png_path):
                try:
                    from struct import unpack
                    with open(png_path, "rb") as pf:
                        pf.read(16)
                        w, h = unpack(">II", pf.read(8))
                    if h > 16000:
                        png_path.unlink(missing_ok=True)
                        return "*[Diagram omitted — too large for PDF]*"
                except Exception:
                    pass
                return f"![Diagram]({png_path}){{ width=100% }}"
            return m.group(0)
        text = MERMAID_RE.sub(replace_mermaid, text)
        return text
    
    combined_parts = []
    for src in doc_files:
        if not src.exists():
            print(f"  SKIP (not found): {src}", file=sys.stderr)
            continue
        trunc = r"^## 6\." if "artifact-traceability" in src.name else None
        print(f"  Processing: {src.name}")
        combined_parts.append(process_doc(src, trunc))
    
    combined = "\n\n\\newpage\n\n".join(combined_parts)
    combined_md = ROOT / ".architecture" / "_pdf_combined.md"
    combined_md.write_text(combined)
    
    output_pdf = ROOT / output_name
    cmd = [
        "pandoc", str(combined_md), "-o", str(output_pdf),
        "--pdf-engine=xelatex",
        "-V", "geometry:margin=1in",
        "-V", "documentclass=article",
        "-V", "fontsize=11pt",
        "-V", "colorlinks=true",
        "-V", "linkcolor=blue",
        "--syntax-highlighting=none",
    ]
    
    print("  Running pandoc...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  pandoc FAILED:\n{result.stderr}", file=sys.stderr)
    else:
        print(f"  PDF: {output_pdf} ({output_pdf.stat().st_size / 1024:.0f} KB)")
    
    combined_md.unlink(missing_ok=True)
    shutil.rmtree(img_dir, ignore_errors=True)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 author_subsystem_docs.py <view_slug> [--spec]")
        print("  view_slug: directory name under .architecture-models/ (e.g., pipeline, manifest, configuration)")
        print("  --spec: generate single component spec instead of 5-doc SE suite")
        sys.exit(1)
    
    slug = sys.argv[1]
    spec_mode = "--spec" in sys.argv
    
    # Resolve subsystem name from model
    model_yaml = read_model(slug)
    import yaml
    model_data = yaml.safe_load(model_yaml)
    subsystem_name = model_data.get("meta", {}).get("system", slug.title())
    
    print(f"\n{'='*60}")
    print(f"Authoring docs for: {subsystem_name} ({slug})")
    print(f"Mode: {'Component Spec' if spec_mode else '5-Doc SE Suite'}")
    print(f"{'='*60}\n")
    
    # Read code context
    max_lines = 200 if spec_mode else 80  # more code for spec, less for SE suite
    code = read_code_context(model_yaml, max_lines_per_file=max_lines)
    
    # Output directory
    out_dir = ROOT / ".architecture" / "authored_docs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if spec_mode:
        # Single component spec
        prompt = _component_spec_prompt(subsystem_name, model_yaml, code)
        content = author_doc(prompt, "component_spec")
        (out_dir / "component_spec.md").write_text(content)
        
        # Build PDF
        se_traceability = ROOT / ".architecture-models" / slug / "docs" / "se" / "artifact-traceability.md"
        doc_files = [out_dir / "component_spec.md"]
        if se_traceability.exists():
            doc_files.append(se_traceability)
        build_pdf(slug, doc_files, f"{slug}-docs.pdf")
    else:
        # 5-doc SE suite
        doc_types = {
            "conops": _conops_prompt,
            "functional_analysis": _functional_analysis_prompt,
            "logical_architecture": _logical_architecture_prompt,
            "use_cases": _use_cases_prompt,
        }
        
        for doc_name, prompt_fn in doc_types.items():
            prompt = prompt_fn(subsystem_name, model_yaml, code)
            content = author_doc(prompt, doc_name)
            (out_dir / f"{doc_name}.md").write_text(content)
        
        # Build PDF
        se_traceability = ROOT / ".architecture-models" / slug / "docs" / "se" / "artifact-traceability.md"
        doc_files = [
            out_dir / "conops.md",
            out_dir / "functional_analysis.md",
            out_dir / "logical_architecture.md",
            out_dir / "use_cases.md",
        ]
        if se_traceability.exists():
            doc_files.append(se_traceability)
        build_pdf(slug, doc_files, f"{slug}-docs.pdf")
    
    print(f"\nDone! Authored docs in: {out_dir}")


if __name__ == "__main__":
    main()
