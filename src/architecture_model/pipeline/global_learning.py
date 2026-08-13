"""Cross-project global learning persistence.

Stores heuristic rules, archetype patterns, and workflow lessons
that transfer knowledge across different repositories (Loop 3).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import json


@dataclass
class HeuristicRule:
    """A learned heuristic for a pipeline stage."""
    id: str
    stage: str
    condition: str
    action: str
    rationale: str
    learned_from: str
    validated_on: list[str] = field(default_factory=list)
    threshold: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchetypePattern:
    """A recognized codebase archetype pattern."""
    id: str
    name: str
    indicators: list[str]
    problem: str
    solution: str
    applicable_repos: list[str] = field(default_factory=list)


@dataclass
class WorkflowLesson:
    """A lesson learned from a workflow failure/fix cycle."""
    id: str
    trigger: str
    diagnosis: str
    fix_applied: str
    validation: str
    files_changed: list[str] = field(default_factory=list)
    commit: str = ""


class GlobalLearningStore:
    """Persists cross-project learning data."""

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    # --- Heuristics ---

    def add_heuristic(self, rule: HeuristicRule) -> None:
        rules = self._load_json("heuristics.json", [])
        rules = [r for r in rules if r["id"] != rule.id]
        rules.append(asdict(rule))
        self._save_json("heuristics.json", rules)

    def get_heuristics(self, stage: str | None = None) -> list[HeuristicRule]:
        data = self._load_json("heuristics.json", [])
        rules = [HeuristicRule(**d) for d in data]
        if stage:
            rules = [r for r in rules if r.stage == stage]
        return rules

    def validate_heuristic(self, rule_id: str, repo: str) -> None:
        rules = self._load_json("heuristics.json", [])
        for r in rules:
            if r["id"] == rule_id:
                if repo not in r["validated_on"]:
                    r["validated_on"].append(repo)
                break
        self._save_json("heuristics.json", rules)

    # --- Archetypes ---

    def add_archetype(self, pattern: ArchetypePattern) -> None:
        patterns = self._load_json("archetypes.json", [])
        patterns = [p for p in patterns if p["id"] != pattern.id]
        patterns.append(asdict(pattern))
        self._save_json("archetypes.json", patterns)

    def get_archetypes(self) -> list[ArchetypePattern]:
        data = self._load_json("archetypes.json", [])
        return [ArchetypePattern(**d) for d in data]

    def match_archetypes(self, observed_indicators: list[str]) -> list[ArchetypePattern]:
        indicators_set = set(observed_indicators)
        return [
            p for p in self.get_archetypes()
            if indicators_set & set(p.indicators)
        ]

    # --- Workflows ---

    def add_workflow(self, lesson: WorkflowLesson) -> None:
        lessons = self._load_json("workflows.json", [])
        lessons = [l for l in lessons if l["id"] != lesson.id]
        lessons.append(asdict(lesson))
        self._save_json("workflows.json", lessons)

    def get_workflows(self) -> list[WorkflowLesson]:
        data = self._load_json("workflows.json", [])
        return [WorkflowLesson(**d) for d in data]

    # --- Helpers ---

    def _load_json(self, filename: str, default: Any) -> Any:
        path = self.path / filename
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def _save_json(self, filename: str, data: Any) -> None:
        path = self.path / filename
        path.write_text(json.dumps(data, indent=2, default=str))
