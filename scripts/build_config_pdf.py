#!/usr/bin/env python3
"""Build PDF for COMP-9 (Configuration) component spec."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_arch_pdf import process_doc

import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
AUTHORED = ROOT / ".architecture" / "authored_docs" / "configuration"
SE_DOCS = ROOT / ".architecture-models" / "configuration" / "docs" / "se"

DOCS = [
    (AUTHORED / "component_spec.md", None),
    (SE_DOCS / "artifact-traceability.md", r"^## 6\."),
]


def main():
    img_dir = ROOT / ".architecture" / "_pdf_images"
    img_dir.mkdir(parents=True, exist_ok=True)

    combined_parts = []
    img_counter = [0]

    for src, trunc in DOCS:
        if not src.exists():
            print(f"SKIP (not found): {src}", file=sys.stderr)
            continue
        print(f"Processing: {src.name}")
        content = process_doc(src, trunc, img_dir, img_counter)
        combined_parts.append(content)

    combined = "\n\n\\newpage\n\n".join(combined_parts)

    combined_md = ROOT / ".architecture" / "_pdf_combined.md"
    combined_md.write_text(combined)

    output_pdf = ROOT / "config-docs.pdf"
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

    print("Running pandoc...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"pandoc FAILED:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"PDF: {output_pdf} ({output_pdf.stat().st_size / 1024:.0f} KB)")

    combined_md.unlink(missing_ok=True)
    shutil.rmtree(img_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
