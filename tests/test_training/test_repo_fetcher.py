"""Tests for RepoFetcher (GitHub API discovery and clone management)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from architecture_model.training.repo_fetcher import RepoFetcher, RepoInfo


# ---------------------------------------------------------------------------
# RepoInfo Dataclass Tests
# ---------------------------------------------------------------------------


class TestRepoInfo:
    def test_repo_info_creation(self):
        """RepoInfo stores all expected fields."""
        info = RepoInfo(
            url="https://github.com/owner/repo",
            full_name="owner/repo",
            stars=500,
            language="Python",
            default_branch="main",
            has_ci=True,
            size_kb=5000,
        )
        assert info.url == "https://github.com/owner/repo"
        assert info.full_name == "owner/repo"
        assert info.stars == 500
        assert info.language == "Python"
        assert info.default_branch == "main"
        assert info.has_ci is True
        assert info.size_kb == 5000


# ---------------------------------------------------------------------------
# RepoFetcher Init Tests
# ---------------------------------------------------------------------------


class TestRepoFetcherInit:
    def test_init_with_clone_dir(self, tmp_path):
        """RepoFetcher stores clone directory."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        assert fetcher.clone_dir == tmp_path

    def test_init_with_token(self, tmp_path):
        """RepoFetcher stores optional GitHub token."""
        fetcher = RepoFetcher(clone_dir=tmp_path, github_token="ghp_test123")
        assert fetcher._github_token == "ghp_test123"

    def test_init_without_token(self, tmp_path):
        """RepoFetcher works without a token (None)."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        assert fetcher._github_token is None


# ---------------------------------------------------------------------------
# discover() Tests
# ---------------------------------------------------------------------------


class TestDiscover:
    @pytest.mark.asyncio
    async def test_discover_builds_correct_query(self, tmp_path):
        """discover() passes correct language and stars params to _search_github."""
        fetcher = RepoFetcher(clone_dir=tmp_path, github_token="ghp_test")
        fetcher._search_github = AsyncMock(return_value={"items": []})

        await fetcher.discover(n=5, language="python", min_stars=100)

        fetcher._search_github.assert_called_once()
        call_kwargs = fetcher._search_github.call_args[1]
        params = call_kwargs["params"]
        assert "language:python" in params["q"]
        assert "stars:>100" in params["q"]
        assert params["per_page"] == "5"

    @pytest.mark.asyncio
    async def test_discover_parses_github_response(self, tmp_path):
        """discover() converts GitHub API items into RepoInfo list."""
        fetcher = RepoFetcher(clone_dir=tmp_path)

        github_items = [
            {
                "html_url": "https://github.com/owner/repo1",
                "full_name": "owner/repo1",
                "stargazers_count": 500,
                "language": "Python",
                "default_branch": "main",
                "size": 8000,
            },
            {
                "html_url": "https://github.com/owner/repo2",
                "full_name": "owner/repo2",
                "stargazers_count": 1200,
                "language": "Python",
                "default_branch": "develop",
                "size": 15000,
            },
        ]
        fetcher._search_github = AsyncMock(return_value={"items": github_items})

        repos = await fetcher.discover(n=5)

        assert len(repos) == 2
        assert repos[0].full_name == "owner/repo1"
        assert repos[0].stars == 500
        assert repos[1].default_branch == "develop"
        assert repos[1].size_kb == 15000

    @pytest.mark.asyncio
    async def test_discover_uses_auth_header_when_token_set(self, tmp_path):
        """discover() passes Bearer token in headers to _search_github."""
        fetcher = RepoFetcher(clone_dir=tmp_path, github_token="ghp_secret")
        fetcher._search_github = AsyncMock(return_value={"items": []})

        await fetcher.discover(n=5)

        call_kwargs = fetcher._search_github.call_args[1]
        headers = call_kwargs["headers"]
        assert headers["Authorization"] == "Bearer ghp_secret"

    @pytest.mark.asyncio
    async def test_discover_no_auth_header_without_token(self, tmp_path):
        """discover() does not include Authorization header when no token."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        fetcher._search_github = AsyncMock(return_value={"items": []})

        await fetcher.discover(n=5)

        call_kwargs = fetcher._search_github.call_args[1]
        headers = call_kwargs["headers"]
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_discover_limits_results_to_n(self, tmp_path):
        """discover() returns at most n repos."""
        fetcher = RepoFetcher(clone_dir=tmp_path)

        github_items = [
            {
                "html_url": f"https://github.com/owner/repo{i}",
                "full_name": f"owner/repo{i}",
                "stargazers_count": 200 + i,
                "language": "Python",
                "default_branch": "main",
                "size": 5000,
            }
            for i in range(10)
        ]
        fetcher._search_github = AsyncMock(return_value={"items": github_items})

        repos = await fetcher.discover(n=3)

        assert len(repos) == 3


# ---------------------------------------------------------------------------
# quality_filter() Tests
# ---------------------------------------------------------------------------


class TestQualityFilter:
    def test_quality_filter_removes_low_stars(self, tmp_path):
        """Repos with <= 100 stars are filtered out."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repos = [
            RepoInfo(
                url="https://github.com/a/b",
                full_name="a/b",
                stars=50,
                language="Python",
                default_branch="main",
                has_ci=True,
                size_kb=5000,
            ),
        ]
        result = fetcher.quality_filter(repos)
        assert len(result) == 0

    def test_quality_filter_removes_too_large(self, tmp_path):
        """Repos with size_kb >= 100_000 are filtered out."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repos = [
            RepoInfo(
                url="https://github.com/a/b",
                full_name="a/b",
                stars=500,
                language="Python",
                default_branch="main",
                has_ci=True,
                size_kb=150_000,
            ),
        ]
        result = fetcher.quality_filter(repos)
        assert len(result) == 0

    def test_quality_filter_removes_no_ci(self, tmp_path):
        """Repos without CI are filtered out."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repos = [
            RepoInfo(
                url="https://github.com/a/b",
                full_name="a/b",
                stars=500,
                language="Python",
                default_branch="main",
                has_ci=False,
                size_kb=5000,
            ),
        ]
        result = fetcher.quality_filter(repos)
        assert len(result) == 0

    def test_quality_filter_keeps_good_repos(self, tmp_path):
        """Repos meeting all criteria pass the filter."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repos = [
            RepoInfo(
                url="https://github.com/good/repo",
                full_name="good/repo",
                stars=500,
                language="Python",
                default_branch="main",
                has_ci=True,
                size_kb=10_000,
            ),
        ]
        result = fetcher.quality_filter(repos)
        assert len(result) == 1
        assert result[0].full_name == "good/repo"

    def test_quality_filter_mixed(self, tmp_path):
        """Filter correctly separates good from bad repos."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repos = [
            RepoInfo(url="u1", full_name="good/one", stars=200, language="Python", default_branch="main", has_ci=True, size_kb=5000),
            RepoInfo(url="u2", full_name="bad/low-stars", stars=50, language="Python", default_branch="main", has_ci=True, size_kb=5000),
            RepoInfo(url="u3", full_name="bad/no-ci", stars=300, language="Python", default_branch="main", has_ci=False, size_kb=5000),
            RepoInfo(url="u4", full_name="bad/too-big", stars=400, language="Python", default_branch="main", has_ci=True, size_kb=200_000),
            RepoInfo(url="u5", full_name="good/two", stars=1000, language="Python", default_branch="main", has_ci=True, size_kb=50_000),
        ]
        result = fetcher.quality_filter(repos)
        assert len(result) == 2
        names = [r.full_name for r in result]
        assert "good/one" in names
        assert "good/two" in names


# ---------------------------------------------------------------------------
# clone() Tests
# ---------------------------------------------------------------------------


class TestClone:
    def test_clone_returns_correct_path(self, tmp_path):
        """clone() returns clone_dir / full_name as the local path."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repo = RepoInfo(
            url="https://github.com/owner/repo",
            full_name="owner/repo",
            stars=500,
            language="Python",
            default_branch="main",
            has_ci=True,
            size_kb=5000,
        )

        with patch("architecture_model.training.repo_fetcher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = fetcher.clone(repo)

        assert result == tmp_path / "owner" / "repo"

    def test_clone_runs_git_with_proxy_workaround(self, tmp_path):
        """clone() invokes git clone with proxy-clearing config flags."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repo = RepoInfo(
            url="https://github.com/owner/repo.git",
            full_name="owner/repo",
            stars=500,
            language="Python",
            default_branch="main",
            has_ci=True,
            size_kb=5000,
        )

        with patch("architecture_model.training.repo_fetcher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            fetcher.clone(repo)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Should contain git -c http.proxy="" -c https.proxy="" clone
        assert "git" in cmd
        assert "-c" in cmd
        assert 'http.proxy=' in " ".join(cmd)
        assert 'https.proxy=' in " ".join(cmd)
        assert "clone" in cmd
        assert repo.url in cmd

    def test_clone_creates_parent_directory(self, tmp_path):
        """clone() creates the parent directory structure for the clone."""
        fetcher = RepoFetcher(clone_dir=tmp_path)
        repo = RepoInfo(
            url="https://github.com/deep/nested",
            full_name="deep/nested",
            stars=500,
            language="Python",
            default_branch="main",
            has_ci=True,
            size_kb=5000,
        )

        with patch("architecture_model.training.repo_fetcher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            fetcher.clone(repo)

        # Parent directory should be created
        assert (tmp_path / "deep").exists()
