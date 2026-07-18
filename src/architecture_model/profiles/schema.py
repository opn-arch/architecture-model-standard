"""Domain profile schema and loading logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)
PROFILES_DIR = Path(__file__).parent / "builtins"


@dataclass
class EnumExtension:
    enum_name: str
    values: list[str] = field(default_factory=list)


@dataclass
class EntityExtension:
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConditionalRule:
    entity_type: str
    when: dict[str, str] = field(default_factory=dict)
    require: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class DomainProfile:
    domain: str
    extends_schema: str = "1.4"
    enum_extensions: list[EnumExtension] = field(default_factory=list)
    entity_extensions: list[EntityExtension] = field(default_factory=list)
    validation_rules: list[ConditionalRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainProfile:
        return cls(
            domain=data["domain"],
            extends_schema=data.get("extends_schema", "1.4"),
            enum_extensions=[
                EnumExtension(**e) for e in data.get("enum_extensions", [])
            ],
            entity_extensions=[
                EntityExtension(**e) for e in data.get("entity_extensions", [])
            ],
            validation_rules=[
                ConditionalRule(**r) for r in data.get("validation_rules", [])
            ],
        )

    def get_extended_values(self, enum_name: str) -> list[str]:
        for ext in self.enum_extensions:
            if ext.enum_name == enum_name:
                return ext.values
        return []


BUILTIN_PROFILES: dict[str, str] = {
    "software": "software.yaml",
    "controls": "controls.yaml",
    "mechanical": "mechanical.yaml",
    "electrical": "electrical.yaml",
}


def load_profile(name_or_path: str) -> DomainProfile:
    if name_or_path in BUILTIN_PROFILES:
        path = PROFILES_DIR / BUILTIN_PROFILES[name_or_path]
    else:
        path = Path(name_or_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    profile = DomainProfile.from_dict(data)
    logger.info("Loaded domain profile: %s", profile.domain)
    return profile
