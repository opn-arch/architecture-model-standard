"""Tests for AST-based route detection."""
from architecture_model.extract.route_detector import detect_routes
from pathlib import Path


def test_detect_routes_empty_dir(tmp_path):
    routes = detect_routes(tmp_path)
    assert routes == []


def test_detect_fastapi_route(tmp_path):
    (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users():
    """List all users."""
    pass
''')
    routes = detect_routes(tmp_path)
    assert len(routes) >= 1
    assert routes[0].method == "GET"
    assert routes[0].path == "/users"


def test_detect_flask_route(tmp_path):
    (tmp_path / "views.py").write_text('''
from flask import Blueprint
bp = Blueprint("main", __name__)

@bp.post("/items")
def create_item():
    """Create an item."""
    pass
''')
    routes = detect_routes(tmp_path)
    assert len(routes) >= 1
    assert routes[0].method == "POST"
    assert routes[0].path == "/items"
