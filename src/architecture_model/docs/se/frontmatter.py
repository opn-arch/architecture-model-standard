"""Document frontmatter generation and parsing."""
from __future__ import annotations
import hashlib
import re
from typing import Any


def generate_frontmatter(*, document: str, system: str, system_id: str,
                         model_hash: str, edition: int = 1,
                         generator_version: str = "0.3.0") -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"document: {document}",
        f"system: {system}",
        f"system_id: {system_id}",
        f"generated_at: {now}",
        f"generator_version: {generator_version}",
        f"model_hash: {model_hash}",
        f"edition: {edition}",
        "---",
    ]
    return "\n".join(lines)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from a document. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    import yaml
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body


def extract_section_hashes(text: str) -> dict[str, str]:
    """Extract md5 hashes for each ## section in a markdown document."""
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_name is not None:
                content = "\n".join(current_lines).strip()
                sections[current_name] = hashlib.md5(content.encode()).hexdigest()
            current_name = line[3:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        content = "\n".join(current_lines).strip()
        sections[current_name] = hashlib.md5(content.encode()).hexdigest()

    return sections
