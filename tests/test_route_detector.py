"""Tests for architecture_model.extract.route_detector."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from architecture_model.extract.route_detector import (
    RouteInfo,
    detect_routes,
    _extract_fastapi_routes,
    _extract_flask_routes,
    _extract_django_routes,
)


# ---------------------------------------------------------------------------
# Synthetic sources
# ---------------------------------------------------------------------------

FASTAPI_SOURCE = textwrap.dedent("""\
    from fastapi import APIRouter, Depends, Security
    from app.auth import get_current_user

    router = APIRouter()

    @router.get("/articles/{slug}")
    async def get_article(slug: str):
        \"\"\"Retrieve a single article by slug.\"\"\"
        ...

    @router.post("/articles")
    async def create_article(
        payload: dict,
        user=Depends(get_current_user),
    ):
        \"\"\"Create a new article.\"\"\"
        ...

    @router.delete("/articles/{slug}")
    async def delete_article(
        slug: str,
        user=Security(scopes=["admin"]),
    ):
        \"\"\"Delete an article.\"\"\"
        ...

    @router.get("/health")
    def health_check():
        ...
""")

FLASK_SOURCE = textwrap.dedent("""\
    from flask import Blueprint

    bp = Blueprint("articles", __name__)

    @bp.route("/articles", methods=["GET"])
    def list_articles():
        \"\"\"List all articles.\"\"\"
        ...

    @bp.route("/articles", methods=["POST"])
    @login_required
    def create_article():
        \"\"\"Create an article.\"\"\"
        ...

    @bp.route("/articles/<slug>", methods=["GET", "PUT"])
    def article_detail(slug):
        \"\"\"Get or update article.\"\"\"
        ...
""")

DJANGO_URLS_SOURCE = textwrap.dedent("""\
    from django.urls import path
    from . import views

    urlpatterns = [
        path("articles/", views.article_list),
        path("articles/<slug>/", views.article_detail),
    ]
""")


# ---------------------------------------------------------------------------
# FastAPI tests
# ---------------------------------------------------------------------------


class TestFastAPIDetection:
    """Tests for FastAPI route extraction."""

    @pytest.fixture()
    def routes(self) -> list[RouteInfo]:
        tree = ast.parse(FASTAPI_SOURCE)
        return _extract_fastapi_routes(tree, "app/api/routes.py")

    def test_detects_all_routes(self, routes: list[RouteInfo]):
        assert len(routes) == 4

    def test_get_route_path(self, routes: list[RouteInfo]):
        get_route = next(r for r in routes if r.function_name == "get_article")
        assert get_route.path == "/articles/{slug}"
        assert get_route.method == "GET"

    def test_post_route(self, routes: list[RouteInfo]):
        post_route = next(r for r in routes if r.function_name == "create_article")
        assert post_route.method == "POST"
        assert post_route.path == "/articles"

    def test_docstring_extracted(self, routes: list[RouteInfo]):
        get_route = next(r for r in routes if r.function_name == "get_article")
        assert get_route.docstring == "Retrieve a single article by slug."

    def test_auth_depends_detected(self, routes: list[RouteInfo]):
        post_route = next(r for r in routes if r.function_name == "create_article")
        assert post_route.is_authenticated is True

    def test_security_detected(self, routes: list[RouteInfo]):
        delete_route = next(r for r in routes if r.function_name == "delete_article")
        assert delete_route.is_authenticated is True

    def test_no_auth_not_flagged(self, routes: list[RouteInfo]):
        health = next(r for r in routes if r.function_name == "health_check")
        assert health.is_authenticated is False

    def test_framework_set(self, routes: list[RouteInfo]):
        assert all(r.framework == "fastapi" for r in routes)

    def test_file_path(self, routes: list[RouteInfo]):
        assert all(r.file == "app/api/routes.py" for r in routes)


# ---------------------------------------------------------------------------
# Flask tests
# ---------------------------------------------------------------------------


class TestFlaskDetection:
    """Tests for Flask route extraction."""

    @pytest.fixture()
    def routes(self) -> list[RouteInfo]:
        tree = ast.parse(FLASK_SOURCE)
        return _extract_flask_routes(tree, "app/views.py")

    def test_detects_all_routes(self, routes: list[RouteInfo]):
        # list_articles (GET), create_article (POST),
        # article_detail (GET + PUT) = 4 total
        assert len(routes) == 4

    def test_methods_from_keyword(self, routes: list[RouteInfo]):
        list_route = next(r for r in routes if r.function_name == "list_articles")
        assert list_route.method == "GET"

    def test_multiple_methods_expanded(self, routes: list[RouteInfo]):
        detail_routes = [r for r in routes if r.function_name == "article_detail"]
        methods = sorted(r.method for r in detail_routes)
        assert methods == ["GET", "PUT"]

    def test_flask_auth_decorator(self, routes: list[RouteInfo]):
        create = next(r for r in routes if r.function_name == "create_article")
        assert create.is_authenticated is True

    def test_no_auth_not_flagged(self, routes: list[RouteInfo]):
        list_route = next(r for r in routes if r.function_name == "list_articles")
        assert list_route.is_authenticated is False

    def test_framework_set(self, routes: list[RouteInfo]):
        assert all(r.framework == "flask" for r in routes)

    def test_docstring_extracted(self, routes: list[RouteInfo]):
        list_route = next(r for r in routes if r.function_name == "list_articles")
        assert list_route.docstring == "List all articles."


# ---------------------------------------------------------------------------
# Django tests
# ---------------------------------------------------------------------------


class TestDjangoDetection:
    """Tests for Django urlpatterns extraction."""

    @pytest.fixture()
    def routes(self) -> list[RouteInfo]:
        tree = ast.parse(DJANGO_URLS_SOURCE)
        return _extract_django_routes(tree, "app/urls.py")

    def test_detects_all_routes(self, routes: list[RouteInfo]):
        assert len(routes) == 2

    def test_path_extracted(self, routes: list[RouteInfo]):
        first = routes[0]
        assert first.path == "articles/"
        assert first.function_name == "article_list"

    def test_default_method_is_get(self, routes: list[RouteInfo]):
        assert all(r.method == "GET" for r in routes)

    def test_framework_set(self, routes: list[RouteInfo]):
        assert all(r.framework == "django" for r in routes)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests that files with syntax errors are skipped gracefully."""

    def test_syntax_error_skipped(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        """Files with syntax errors are skipped with a warning."""
        bad_file = tmp_path / "broken.py"
        bad_file.write_text("def foo(\n  this is not valid python", encoding="utf-8")

        good_file = tmp_path / "good.py"
        good_file.write_text(
            textwrap.dedent("""\
                from fastapi import APIRouter
                router = APIRouter()

                @router.get("/ok")
                def ok_route():
                    ...
            """),
            encoding="utf-8",
        )

        routes = detect_routes(tmp_path)

        # Good file was still processed
        assert len(routes) == 1
        assert routes[0].function_name == "ok_route"

        # Warning was printed to stderr
        captured = capsys.readouterr()
        assert "broken.py" in captured.err

    def test_empty_project_returns_empty(self, tmp_path: Path):
        """An empty directory returns an empty route list."""
        routes = detect_routes(tmp_path)
        assert routes == []

    def test_web_layer_dirs_filter(self, tmp_path: Path):
        """Only scans specified directories when web_layer_dirs is set."""
        api_dir = tmp_path / "app" / "api"
        api_dir.mkdir(parents=True)
        other_dir = tmp_path / "other"
        other_dir.mkdir(parents=True)

        (api_dir / "routes.py").write_text(
            textwrap.dedent("""\
                from fastapi import APIRouter
                router = APIRouter()

                @router.get("/included")
                def included():
                    ...
            """),
            encoding="utf-8",
        )
        (other_dir / "routes.py").write_text(
            textwrap.dedent("""\
                from fastapi import APIRouter
                router = APIRouter()

                @router.get("/excluded")
                def excluded():
                    ...
            """),
            encoding="utf-8",
        )

        routes = detect_routes(tmp_path, web_layer_dirs=["app/api"])
        assert len(routes) == 1
        assert routes[0].function_name == "included"


# ---------------------------------------------------------------------------
# Factory auth & route-level dependencies tests
# ---------------------------------------------------------------------------

FASTAPI_FACTORY_AUTH_SOURCE = textwrap.dedent("""\
    from fastapi import APIRouter, Depends
    from app.auth import get_current_user_authorizer

    router = APIRouter()

    @router.get("/me")
    async def get_profile(
        user=Depends(get_current_user_authorizer()),
    ):
        \"\"\"Get current user profile.\"\"\"
        ...

    @router.post("/articles", dependencies=[Depends(get_current_user_authorizer())])
    async def create_article(payload: dict):
        \"\"\"Create article (auth on decorator).\"\"\"
        ...
""")


def test_fastapi_factory_auth_detected():
    """Depends(factory_func()) should be detected as auth."""
    tree = ast.parse(FASTAPI_FACTORY_AUTH_SOURCE)
    routes = _extract_fastapi_routes(tree, "app/api/users.py")
    assert len(routes) == 2
    assert routes[0].is_authenticated is True  # Depends(factory())
    assert routes[1].is_authenticated is True  # dependencies kwarg


def test_fastapi_route_level_dependencies_kwarg():
    """dependencies=[Depends(auth)] on decorator should trigger auth."""
    tree = ast.parse(FASTAPI_FACTORY_AUTH_SOURCE)
    routes = _extract_fastapi_routes(tree, "app/api/users.py")
    article_route = [r for r in routes if r.function_name == "create_article"][0]
    assert article_route.is_authenticated is True
