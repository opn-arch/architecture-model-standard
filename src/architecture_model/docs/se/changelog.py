"""Edition changelog tracking for SE documents."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Changelog:
    """Tracks document generation, user edits, and regeneration history."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, Any]:
        if self._path.exists():
            import yaml  # lazy import
            return yaml.safe_load(self._path.read_text()) or {"documents": {}}
        return {"documents": {}}

    def _save(self, data: dict[str, Any]) -> None:
        import yaml
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def record_generation(self, doc_name: str, *, author: str, model_hash: str,
                          section_hashes: dict[str, str] | None = None,
                          summary: str = "Initial generation from model") -> None:
        data = self.load()
        now = _now_iso()
        data["documents"][doc_name] = {
            "created": now,
            "created_by": author,
            "model_version": model_hash,
            "section_hashes": section_hashes or {},
            "editions": [{
                "timestamp": now,
                "author": author,
                "type": "generated",
                "summary": summary,
            }],
        }
        self._save(data)

    def detect_edits(self, doc_name: str, *, current_hashes: dict[str, str]) -> list[str]:
        """Return list of section names that were modified since last generation."""
        data = self.load()
        doc = data.get("documents", {}).get(doc_name)
        if not doc:
            return []
        stored = doc.get("section_hashes", {})
        return [name for name, h in current_hashes.items()
                if name in stored and stored[name] != h]

    def record_regeneration(self, doc_name: str, *, author: str, model_hash: str,
                            preserved_sections: list[str] | None = None,
                            conflicts: list[str] | None = None,
                            section_hashes: dict[str, str] | None = None,
                            summary: str = "Model updated") -> None:
        data = self.load()
        doc = data["documents"].get(doc_name)
        if not doc:
            self.record_generation(doc_name, author=author, model_hash=model_hash,
                                   section_hashes=section_hashes, summary=summary)
            return
        doc["model_version"] = model_hash
        if section_hashes:
            doc["section_hashes"] = section_hashes
        doc["editions"].append({
            "timestamp": _now_iso(),
            "author": author,
            "type": "regenerated",
            "summary": summary,
            "preserved_sections": preserved_sections or [],
            "conflicts": conflicts or [],
        })
        self._save(data)
