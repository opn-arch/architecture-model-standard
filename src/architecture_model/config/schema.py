"""Project configuration schema.

Defines the ProjectConfig dataclass tree that replaces all hardcoded
project-specific knowledge in the package. Loaded from .architecture-model.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OutputConfig:
    """Output path templates. Use {project} as placeholder for project name."""

    model: str = "output/{project}/architecture-model.yaml"
    manifest: str = "output/{project}/reality-manifest.json"
    artifacts: str = "output/{project}/artifacts/stage2"

    def resolve(self, project_name: str, root: Path) -> "ResolvedOutputConfig":
        """Resolve path templates with actual project name."""
        return ResolvedOutputConfig(
            model=root / self.model.format(project=project_name),
            manifest=root / self.manifest.format(project=project_name),
            artifacts=root / self.artifacts.format(project=project_name),
        )


@dataclass
class ResolvedOutputConfig:
    """Resolved absolute paths for output locations."""

    model: Path
    manifest: Path
    artifacts: Path


@dataclass
class LayerConfig:
    """A logical architecture layer and its source directories."""

    id: str
    dirs: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class SubBlockConfig:
    """A sub-block within a functional block. Recursive — can contain children."""

    id: str
    name: str
    files: list[str] = field(default_factory=list)
    dirs: list[str] = field(default_factory=list)
    description: str = ""
    sub_blocks: list["SubBlockConfig"] = field(default_factory=list)


@dataclass
class FunctionalBlockConfig:
    """A functional block (capability) and its implementing files/directories."""

    id: str
    name: str
    dirs: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    description_source: str = ""
    sub_blocks: list[SubBlockConfig] = field(default_factory=list)


@dataclass
class MetricConfig:
    """A countable project metric (e.g., routers, models, migrations)."""

    label: str
    path: str
    pattern: str = "*.py"
    exclude: list[str] = field(default_factory=list)
    recursive: bool = False


def _parse_sub_blocks(data: dict[str, Any]) -> list[SubBlockConfig]:
    """Recursively parse sub_blocks from YAML dict."""
    return [
        SubBlockConfig(
            id=sb_id,
            name=sb_def.get("name", ""),
            files=sb_def.get("files", []),
            dirs=sb_def.get("dirs", []),
            description=sb_def.get("description", ""),
            sub_blocks=_parse_sub_blocks(sb_def.get("sub_blocks", {})),
        )
        for sb_id, sb_def in data.items()
    ]


def _serialize_sub_blocks(sbs: list[SubBlockConfig]) -> dict:
    """Recursively serialize sub_blocks to YAML-compatible dict."""
    return {
        sb.id: {
            "name": sb.name,
            **({"files": sb.files} if sb.files else {}),
            **({"dirs": sb.dirs} if sb.dirs else {}),
            **({"description": sb.description} if sb.description else {}),
            **({"sub_blocks": _serialize_sub_blocks(sb.sub_blocks)} if sb.sub_blocks else {}),
        }
        for sb in sbs
    }


@dataclass
class ProjectConfig:
    """Complete project descriptor for the Architecture Model Standard.

    This replaces all hardcoded project-specific knowledge. Loaded from
    .architecture-model.yaml in the project root, or auto-discovered.
    """

    # Project identity
    name: str = ""
    system: str = ""

    # Output paths (with {project} template)
    output: OutputConfig = field(default_factory=OutputConfig)

    # Architecture layers
    layers: list[LayerConfig] = field(default_factory=list)

    # Functional decomposition
    functional_blocks: list[FunctionalBlockConfig] = field(default_factory=list)

    # Countable metrics
    metrics: list[MetricConfig] = field(default_factory=list)

    # Source root (set at load time, not serialized)
    root: Path = field(default_factory=lambda: Path("."))

    # ---------------------------------------------------------------------------
    # Derived lookups (computed on access)
    # ---------------------------------------------------------------------------

    @property
    def layer_dir_map(self) -> dict[str, list[str]]:
        """Map layer IDs to their directories (for merger.py)."""
        return {layer.id: layer.dirs for layer in self.layers if layer.dirs}

    @property
    def fblock_dir_map(self) -> dict[str, str]:
        """Map directory/file prefixes to F-block IDs (for merger.py heuristics).

        Produces entries like: {"scripts/ingestion": "F1", "app/routers": "F4"}
        """
        result: dict[str, str] = {}
        for block in self.functional_blocks:
            for d in block.dirs:
                result[d] = block.id
            for f in block.files:
                # Use file path without .py extension as prefix match key
                prefix = f.rsplit(".py", 1)[0] if f.endswith(".py") else f
                result[prefix] = block.id
        return result

    @property
    def fblock_dict(self) -> dict[str, dict[str, Any]]:
        """FUNCTIONAL_BLOCKS in the legacy dict format (backward compat)."""
        return {
            block.id: {
                "name": block.name,
                "dirs": block.dirs,
                "files": block.files,
                "description_source": block.description_source,
            }
            for block in self.functional_blocks
        }

    @property
    def metrics_paths(self) -> dict[str, Path]:
        """Map metric labels to their resolved paths."""
        return {m.label: self.root / m.path for m in self.metrics}

    def resolved_output(self) -> ResolvedOutputConfig:
        """Get resolved output paths using project name and root."""
        return self.output.resolve(self.name, self.root)

    @classmethod
    def from_dict(cls, data: dict[str, Any], root: Path = Path(".")) -> "ProjectConfig":
        """Construct from parsed YAML dictionary."""
        project = data.get("project", {})
        output_data = data.get("output", {})
        layers_data = data.get("layers", {})
        blocks_data = data.get("functional_blocks", {})
        metrics_data = data.get("metrics", [])

        layers = [
            LayerConfig(
                id=layer_id,
                dirs=layer_def.get("dirs", []) if isinstance(layer_def, dict) else [],
                description=layer_def.get("description", "") if isinstance(layer_def, dict) else "",
            )
            for layer_id, layer_def in layers_data.items()
        ]

        blocks = [
            FunctionalBlockConfig(
                id=block_id,
                name=block_def.get("name", ""),
                dirs=block_def.get("dirs", []),
                files=block_def.get("files", []),
                description_source=block_def.get("description_source", ""),
                sub_blocks=_parse_sub_blocks(block_def.get("sub_blocks", {})),
            )
            for block_id, block_def in blocks_data.items()
        ]

        metrics = [
            MetricConfig(
                label=m.get("label", ""),
                path=m.get("path", ""),
                pattern=m.get("pattern", "*.py"),
                exclude=m.get("exclude", []),
                recursive=m.get("recursive", False),
            )
            for m in metrics_data
        ]

        return cls(
            name=project.get("name", ""),
            system=project.get("system", ""),
            output=OutputConfig(
                model=output_data.get("model", OutputConfig.model),
                manifest=output_data.get("manifest", OutputConfig.manifest),
                artifacts=output_data.get("artifacts", OutputConfig.artifacts),
            ),
            layers=layers,
            functional_blocks=blocks,
            metrics=metrics,
            root=root,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to YAML-compatible dictionary."""
        return {
            "project": {
                "name": self.name,
                "system": self.system,
            },
            "output": {
                "model": self.output.model,
                "manifest": self.output.manifest,
                "artifacts": self.output.artifacts,
            },
            "layers": {layer.id: {"dirs": layer.dirs} for layer in self.layers},
            "functional_blocks": {
                block.id: {
                    "name": block.name,
                    "dirs": block.dirs,
                    "files": block.files,
                    "description_source": block.description_source,
                    **(
                        {"sub_blocks": _serialize_sub_blocks(block.sub_blocks)}
                        if block.sub_blocks
                        else {}
                    ),
                }
                for block in self.functional_blocks
            },
            "metrics": [
                {
                    "label": m.label,
                    "path": m.path,
                    "pattern": m.pattern,
                    **({"exclude": m.exclude} if m.exclude else {}),
                    **({"recursive": True} if m.recursive else {}),
                }
                for m in self.metrics
            ],
        }


@dataclass
class DiscoveryCandidate:
    """A candidate evaluated during config discovery."""

    category: str
    path: str
    accepted: bool
    reason: str


@dataclass
class DiscoveryReport:
    """Observability report for config discovery."""

    layout_detected: str = "unknown"
    blocks_discovered: int = 0
    layers_discovered: int = 0
    metrics_discovered: int = 0
    sub_blocks_discovered: int = 0
    files_total: int = 0
    files_claimed: int = 0
    files_unclaimed: int = 0
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_candidate(
        self, category: str, path: str, accepted: bool, reason: str
    ) -> None:
        self.candidates.append(DiscoveryCandidate(category, path, accepted, reason))

    @property
    def claim_rate(self) -> float:
        if self.files_total == 0:
            return 1.0
        return self.files_claimed / self.files_total

    def summary(self) -> str:
        return (
            f"Layout: {self.layout_detected}, "
            f"{self.blocks_discovered} blocks, {self.layers_discovered} layers, "
            f"{self.metrics_discovered} metrics, "
            f"{self.files_claimed}/{self.files_total} files claimed "
            f"({self.claim_rate:.0%})"
        )
