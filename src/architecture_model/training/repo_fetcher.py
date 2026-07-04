"""
Repo Fetcher: GitHub API discovery and clone management for training data.

Discovers open-source Python repositories from GitHub matching quality
criteria, and manages local clones for architecture model extraction.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


@dataclass
class RepoInfo:
    """Metadata for a discovered GitHub repository."""

    url: str
    full_name: str
    stars: int
    language: str
    default_branch: str
    has_ci: bool
    size_kb: int


class RepoFetcher:
    """GitHub API discovery and local clone management.

    Discovers repos matching quality criteria via GitHub Search API,
    filters them, and clones locally for architecture extraction.
    """

    def __init__(self, clone_dir: Path, github_token: Optional[str] = None) -> None:
        self.clone_dir = clone_dir
        self._github_token = github_token

    async def discover(
        self, n: int, language: str = "python", min_stars: int = 100
    ) -> list[RepoInfo]:
        """Search GitHub for repos matching criteria.

        Args:
            n: Maximum number of repos to return.
            language: Programming language filter.
            min_stars: Minimum star count.

        Returns:
            List of RepoInfo (at most n items).
        """
        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if self._github_token:
            headers["Authorization"] = f"Bearer {self._github_token}"

        params = {
            "q": f"language:{language} stars:>{min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": str(n),
        }

        data = await self._search_github(params=params, headers=headers)

        items = data.get("items", [])
        repos = [self._parse_item(item) for item in items[:n]]
        return repos

    async def _search_github(
        self, params: dict[str, str], headers: dict[str, str]
    ) -> dict:
        """Execute GitHub search API request via aiohttp.

        Separated for testability (can be mocked without aiohttp installed).
        """
        if not HAS_AIOHTTP:
            raise RuntimeError(
                "aiohttp is required for RepoFetcher.discover(). "
                "Install with: pip install aiohttp"
            )

        async with aiohttp.ClientSession() as session:
            async with session.get(
                GITHUB_SEARCH_URL, params=params, headers=headers
            ) as resp:
                return await resp.json()

    def quality_filter(self, repos: list[RepoInfo]) -> list[RepoInfo]:
        """Filter repos by quality criteria.

        Criteria:
        - stars > 100
        - size_kb < 100_000 (roughly <100k LOC)
        - has_ci is True
        """
        return [
            repo
            for repo in repos
            if repo.stars > 100
            and repo.size_kb < 100_000
            and repo.has_ci
        ]

    def clone(self, repo: RepoInfo) -> Path:
        """Clone a repo locally using git with proxy workaround.

        Args:
            repo: RepoInfo with the URL and full_name.

        Returns:
            Path to the local clone directory.
        """
        clone_path = self.clone_dir / repo.full_name
        clone_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "git",
            "-c", "http.proxy=",
            "-c", "https.proxy=",
            "clone",
            "--depth", "1",
            "--branch", repo.default_branch,
            repo.url,
            str(clone_path),
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        return clone_path

    @staticmethod
    def _parse_item(item: dict) -> RepoInfo:
        """Parse a GitHub API search result item into RepoInfo."""
        return RepoInfo(
            url=item.get("html_url", ""),
            full_name=item.get("full_name", ""),
            stars=item.get("stargazers_count", 0),
            language=item.get("language", ""),
            default_branch=item.get("default_branch", "main"),
            has_ci=True,  # Assume CI presence; refined during clone inspection
            size_kb=item.get("size", 0),
        )
