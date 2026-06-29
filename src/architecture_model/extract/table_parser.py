"""
Markdown table parser — extracts structured data from pipe-delimited tables.

Used by the artifact extractors to pull entity data from Tier 1 markdown docs.
"""

from __future__ import annotations

import re
from typing import Any


def parse_tables(markdown: str) -> list[list[dict[str, str]]]:
    """
    Parse all markdown tables in the text.

    Returns a list of tables, where each table is a list of row-dicts
    keyed by normalized header names.
    """
    tables: list[list[dict[str, str]]] = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        # Look for a header row (contains pipes)
        if "|" in lines[i]:
            header_line = lines[i].strip()
            # Check next line is separator (dashes)
            if i + 1 < len(lines) and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[i + 1]):
                headers = _parse_row(header_line)
                if headers:
                    table_rows: list[dict[str, str]] = []
                    i += 2  # skip header + separator

                    while i < len(lines) and "|" in lines[i]:
                        row_line = lines[i].strip()
                        if re.match(r"^\s*\|[\s\-:|]+\|\s*$", row_line):
                            i += 1
                            continue
                        values = _parse_row(row_line)
                        if values:
                            row_dict = {}
                            for idx, h in enumerate(headers):
                                key = _normalize_header(h)
                                row_dict[key] = values[idx] if idx < len(values) else ""
                            table_rows.append(row_dict)
                        i += 1

                    if table_rows:
                        tables.append(table_rows)
                    continue
        i += 1

    return tables


def find_table_after_heading(markdown: str, heading_pattern: str) -> list[dict[str, str]]:
    """
    Find the first table that appears after a heading matching the pattern.

    Args:
        markdown: Full markdown text
        heading_pattern: Regex pattern to match against heading text (case-insensitive)

    Returns:
        List of row dicts, or empty list if no matching table found.
    """
    lines = markdown.split("\n")
    heading_re = re.compile(heading_pattern, re.IGNORECASE)
    found_heading = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check for heading (only match ## or deeper, skip # document titles)
        if line.startswith("##"):
            heading_text = re.sub(r"^#+\s*", "", line)
            if heading_re.search(heading_text):
                found_heading = True
                i += 1
                continue
            elif found_heading:
                # Hit next heading without finding a table
                return []

        # If we've found the heading, look for a table
        if found_heading and "|" in line:
            if i + 1 < len(lines) and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[i + 1]):
                headers = _parse_row(line)
                if headers:
                    table_rows: list[dict[str, str]] = []
                    i += 2

                    while i < len(lines) and "|" in lines[i]:
                        row_line = lines[i].strip()
                        if re.match(r"^\s*\|[\s\-:|]+\|\s*$", row_line):
                            i += 1
                            continue
                        values = _parse_row(row_line)
                        if values:
                            row_dict = {}
                            for idx, h in enumerate(headers):
                                key = _normalize_header(h)
                                row_dict[key] = values[idx] if idx < len(values) else ""
                            table_rows.append(row_dict)
                        i += 1

                    return table_rows
        i += 1

    return []


def extract_sections(markdown: str, level: int = 2) -> dict[str, str]:
    """
    Split markdown into sections by heading level.

    Returns dict mapping heading text -> section content (including sub-headings).
    """
    sections: dict[str, str] = {}
    prefix = "#" * level
    lines = markdown.split("\n")
    current_heading = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith(prefix + " ") and not line.startswith(prefix + "# "):
            # Save previous section
            if current_heading:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = re.sub(r"^#+\s*", "", line.strip())
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_heading:
        sections[current_heading] = "\n".join(current_lines).strip()

    return sections


def extract_list_items(text: str) -> list[str]:
    """Extract bullet/numbered list items from text."""
    items: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        # Match: - item, * item, 1. item, 1) item
        m = re.match(r"^(?:[-*]|\d+[.)]) \s*(.*)", line)
        if m:
            items.append(m.group(1).strip())
    return items


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _parse_row(line: str) -> list[str]:
    """Parse a pipe-delimited row into cell values."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells = [cell.strip() for cell in line.split("|")]
    return cells


def _normalize_header(header: str) -> str:
    """Normalize header to snake_case key."""
    h = header.strip().lower()
    h = re.sub(r"[^a-z0-9]+", "_", h)
    h = h.strip("_")
    return h
