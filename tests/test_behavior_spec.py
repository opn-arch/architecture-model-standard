"""Tests for behavior spec doc generator."""

from pathlib import Path

import pytest

from architecture_model.core.types import Behavior, Status
from architecture_model.manifest.call_graph import FlowTrace
from architecture_model.manifest.types import (
    FunctionInfo,
    Manifest,
    MetricsResult,
    ModuleInfo,
)
from architecture_model.orchestration.behavior_flows import (
    BehaviorClassification,
    CrudSummary,
)
from architecture_model.docs.behavior_spec import (
    generate_behavior_spec,
    generate_behavior_index,
)


@pytest.fixture
def behavior():
    return Behavior(
        id="BEH-1",
        name="login",
        status=Status.ACTIVE,
        trigger="POST /auth/login",
        steps=["login", "get_user", "create_session"],
        actor="User",
        preconditions=["User has valid credentials"],
        postconditions=["Session token returned", "User marked active"],
    )


@pytest.fixture
def flow_trace():
    return FlowTrace(
        entry="routers/auth.py:login",
        steps=[
            ("routers/auth.py", "login"),
            ("services/users.py", "get_user"),
            ("services/sessions.py", "create_session"),
        ],
        components_crossed=["COMP-1", "COMP-2", "COMP-3"],
        depth=2,
        truncated=False,
    )


@pytest.fixture
def scoped_manifest():
    return Manifest(
        modules=[
            ModuleInfo(
                file="routers/auth.py",
                name="routers.auth",
                docstring="",
                functions=[
                    FunctionInfo(
                        name="login",
                        signature="(request: LoginRequest) -> TokenResponse",
                        data_in=["request"],
                        data_out="TokenResponse",
                        raises=["ValidationError"],
                    )
                ],
                imports=[],
                line_count=30,
                status="active",
                classes=[],
            ),
            ModuleInfo(
                file="services/users.py",
                name="services.users",
                docstring="",
                functions=[
                    FunctionInfo(
                        name="get_user",
                        signature="(email: str) -> User",
                        data_in=["email"],
                        data_out="User",
                        raises=["NotFoundError"],
                    )
                ],
                imports=[],
                line_count=50,
                status="active",
                classes=[],
            ),
            ModuleInfo(
                file="services/sessions.py",
                name="services.sessions",
                docstring="",
                functions=[
                    FunctionInfo(
                        name="create_session",
                        signature="(user: User) -> str",
                        data_in=["user"],
                        data_out="str",
                        raises=[],
                    )
                ],
                imports=[],
                line_count=40,
                status="active",
                classes=[],
            ),
        ],
        interfaces=[],
        functional_blocks={},
        generated_at="",
        project_root=Path("."),
        metrics=MetricsResult(values={}),
    )


@pytest.fixture
def file_to_comp():
    return {
        "routers/auth.py": "COMP-1",
        "services/users.py": "COMP-2",
        "services/sessions.py": "COMP-3",
    }


def test_generate_spec_has_mermaid(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "```mermaid" in result
    assert "sequenceDiagram" in result


def test_generate_spec_participants(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "participant COMP-1" in result
    assert "participant COMP-2" in result
    assert "participant COMP-3" in result


def test_generate_spec_messages(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "COMP-1->>+COMP-2: get_user()" in result
    assert "COMP-2->>+COMP-3: create_session()" in result


def test_generate_spec_data_flow_table(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "| Step | Function | Input | Output |" in result
    assert "get_user" in result
    assert "email" in result
    assert "User" in result


def test_generate_spec_error_paths(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "login: raises ValidationError" in result
    assert "get_user: raises NotFoundError" in result
    # create_session has no raises, should not appear in error paths
    assert "create_session: raises" not in result


def test_generate_spec_files_touched(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "routers/auth.py" in result
    assert "COMP-1" in result
    assert "services/users.py" in result
    assert "COMP-2" in result


def test_generate_spec_preconditions(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "## Preconditions" in result
    assert "- User has valid credentials" in result


def test_generate_spec_postconditions(behavior, flow_trace, scoped_manifest, file_to_comp):
    result = generate_behavior_spec(behavior, flow_trace, scoped_manifest, file_to_comp)
    assert "## Postconditions" in result
    assert "- Session token returned" in result
    assert "- User marked active" in result


def test_generate_index_cross_component():
    beh = Behavior(
        id="BEH-1",
        name="login",
        status=Status.ACTIVE,
        trigger="POST /auth/login",
        steps=["login", "get_user", "create_session"],
    )
    trace = FlowTrace(
        entry="routers/auth.py:login",
        steps=[
            ("routers/auth.py", "login"),
            ("services/users.py", "get_user"),
            ("services/sessions.py", "create_session"),
        ],
        components_crossed=["COMP-1", "COMP-2", "COMP-3"],
        depth=2,
        truncated=False,
    )
    classification = BehaviorClassification(
        cross_component=[(beh, trace)],
        crud_groups={},
        trivial=[],
    )
    result = generate_behavior_index(classification, {})
    assert "## Cross-Component Flows (1)" in result
    assert "login" in result
    assert "COMP-1, COMP-2, COMP-3" in result
    assert "3" in result  # steps count


def test_generate_index_crud_groups():
    classification = BehaviorClassification(
        cross_component=[],
        crud_groups={"COMP-1": [
            Behavior(id="BEH-2", name="list_users", status=Status.ACTIVE, trigger="GET /users"),
            Behavior(id="BEH-3", name="create_user", status=Status.ACTIVE, trigger="POST /users"),
        ]},
        trivial=[],
    )
    crud_summaries = {
        "COMP-1": CrudSummary(
            component_id="COMP-1",
            count=2,
            verbs={"GET": 1, "POST": 1},
            summary="2 CRUD endpoints (1 GET, 1 POST)",
        ),
    }
    result = generate_behavior_index(classification, crud_summaries)
    assert "## Component CRUD Groups" in result
    assert "COMP-1" in result
    assert "2 CRUD endpoints (1 GET, 1 POST)" in result
    assert "list_users" in result
    assert "create_user" in result
