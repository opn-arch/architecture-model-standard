#!/usr/bin/env python3
"""Build a PDF from authored architecture docs.

Reads selected SE docs, renders Mermaid diagrams to PNG via mmdc,
and produces a combined markdown that pandoc+xelatex turns into a PDF.

Usage:
    python3 build_arch_pdf.py [repo_path]

If repo_path is omitted, uses the parent of this script's directory.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


def get_docs(root: Path):
    """Return list of (source_path, truncate_pattern) for the repo."""
    authored = root / ".architecture" / "authored_docs"
    se_docs = root / ".architecture-models" / "docs" / "se"
    return [
        (authored / "conops.md", None),
        (authored / "functional_analysis.md", None),
        (authored / "logical_architecture.md", None),
        (authored / "use_cases.md", None),
        (se_docs / "artifact-traceability.md", r"^## 6\."),
    ]


def render_mermaid(mmd_content: str, out_png: Path) -> bool:
    """Render a mermaid diagram to PNG via mmdc."""
    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as f:
        f.write(mmd_content)
        mmd_path = f.name
    try:
        env = {**__import__("os").environ}
        env["PUPPETEER_EXECUTABLE_PATH"] = (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        result = subprocess.run(
            ["mmdc", "-i", mmd_path, "-o", str(out_png),
             "-w", "1400", "-b", "white", "--scale", "2"],
            capture_output=True, text=True, timeout=30, env=env,
        )
        if result.returncode != 0:
            print(f"  mmdc error: {result.stderr[:200]}", file=sys.stderr)
            return False
        return out_png.exists()
    except Exception as e:
        print(f"  mmdc exception: {e}", file=sys.stderr)
        return False
    finally:
        Path(mmd_path).unlink(missing_ok=True)


def process_doc(src: Path, truncate_pattern: str | None,
                img_dir: Path, img_counter: list[int]) -> str:
    """Read a doc, optionally truncate, render mermaid to PNG."""
    text = src.read_text()

    # Strip YAML frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            text = text[end + 3:].lstrip("\n")

    # Truncate if pattern given
    if truncate_pattern:
        lines = text.split("\n")
        pat = re.compile(truncate_pattern)
        for i, line in enumerate(lines):
            if pat.match(line):
                text = "\n".join(lines[:i])
                break

    # Render mermaid blocks to PNG
    def replace_mermaid(m):
        img_counter[0] += 1
        png_path = img_dir / f"mermaid_{img_counter[0]}.png"
        if render_mermaid(m.group(1), png_path):
            # Check dimensions — LaTeX can't handle images > ~16000px
            try:
                from struct import unpack
                with open(png_path, "rb") as pf:
                    pf.read(16)
                    w, h = unpack(">II", pf.read(8))
                if h > 16000:
                    # Too tall for LaTeX — skip this diagram
                    png_path.unlink(missing_ok=True)
                    return "*[Diagram omitted — too large for PDF]*"
            except Exception:
                pass
            return f"![Diagram]({png_path}){{ width=100% }}"
        return m.group(0)  # fallback: keep code block

    text = MERMAID_RE.sub(replace_mermaid, text)
    return text


def build_pdf(root: Path):
    """Build architecture-docs.pdf for the given repo root."""
    repo_name = root.name
    print(f"\n{'='*60}")
    print(f"Building PDF for: {repo_name}")
    print(f"{'='*60}")

    img_dir = root / ".architecture" / "_pdf_images"
    img_dir.mkdir(parents=True, exist_ok=True)

    combined_parts = []
    img_counter = [0]

    for src, trunc in get_docs(root):
        if not src.exists():
            print(f"  SKIP (not found): {src.name}", file=sys.stderr)
            continue
        print(f"  Processing: {src.name}")
        content = process_doc(src, trunc, img_dir, img_counter)
        combined_parts.append(content)

    if not combined_parts:
        print(f"  ERROR: No docs found for {repo_name}", file=sys.stderr)
        return

    combined = "\n\n\\newpage\n\n".join(combined_parts)

    combined_md = root / ".architecture" / "_pdf_combined.md"
    combined_md.write_text(combined)

    output_pdf = root / "architecture-docs.pdf"
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

    print(f"  Running pandoc...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  pandoc FAILED:\n{result.stderr}", file=sys.stderr)
        return

    print(f"  PDF: {output_pdf} ({output_pdf.stat().st_size / 1024:.0f} KB)")

    # Cleanup
    combined_md.unlink(missing_ok=True)
    shutil.rmtree(img_dir, ignore_errors=True)


def main():
    if len(sys.argv) > 1:
        roots = [Path(p).resolve() for p in sys.argv[1:]]
    else:
        roots = [Path(__file__).resolve().parent.parent]

    for root in roots:
        build_pdf(root)


if __name__ == "__main__":
    main()
