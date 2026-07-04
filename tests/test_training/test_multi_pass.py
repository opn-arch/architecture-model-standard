"""Tests for multi-pass hierarchical extraction."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import yaml

from architecture_model.training.multi_pass import MultiPassExtractor, PassResult
from architecture_model.training.context_builder import ContextSlices
from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta


@pytest.fixture
def context():
    return ContextSlices(
        structure="pkg: api/, models/, tasks/",
        boundaries="class UserAPI(APIView): ...",
        behavior="@task def send_email(): ...",
        relationships="api imports models, tasks imports services",
        constraints="DATABASES = {'default': ...}",
    )


@pytest.fixture
def mock_client():
    """Mock LLM client with _chat method."""
    client = MagicMock()
    client._chat = AsyncMock()
    return client


def _yaml_response(entities_yaml: str) -> dict:
    """Build mock Ollama response."""
    return {"message": {"content": entities_yaml}}


class TestPassResult:
    def test_pass_result_fields(self):
        """PassResult stores pass name, raw YAML, and parsed entities."""
        pr = PassResult(pass_name="structure", raw_yaml="layers: []", entities={})
        assert pr.pass_name == "structure"
        assert pr.raw_yaml == "layers: []"


class TestMultiPassExtractor:
    def test_init(self, mock_client, context):
        """Accepts client and context slices."""
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        assert mpe._client is mock_client

    @pytest.mark.asyncio
    async def test_pass_structure_uses_structure_slice(self, mock_client, context):
        """Pass 1 sends structure slice with structure-specific prompt."""
        mock_client._chat.return_value = _yaml_response(
            "layers:\n  - id: L1\n    name: API\n    status: ACTIVE\n"
            "components:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"
        )
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        result = await mpe._pass_structure()
        # Verify structure slice was sent
        call_args = mock_client._chat.call_args[0][0]
        assert "PACKAGE STRUCTURE" in call_args[1]["content"] or "pkg:" in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_extract_produces_model(self, mock_client, context):
        """Full extract() returns an ArchitectureModel."""
        # Each pass returns a valid YAML fragment
        responses = [
            _yaml_response("layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"),
            _yaml_response("actors:\n  - id: A1\n    name: User\n    status: ACTIVE\n    type: human\ninterfaces:\n  - id: I1\n    name: REST API\n    status: ACTIVE\n    type: REST"),
            _yaml_response("capabilities:\n  - id: CAP1\n    name: Auth\n    status: ACTIVE\nbehaviors:\n  - id: B1\n    name: Login\n    status: ACTIVE"),
            _yaml_response("relationships:\n  - type: depends-on\n    from: C1\n    to: A1"),
            _yaml_response("constraints:\n  - id: CON1\n    name: Rate Limit\n    status: ACTIVE"),
        ]
        mock_client._chat.side_effect = responses
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        model = await mpe.extract()
        assert isinstance(model, ArchitectureModel)
        assert len(model.entities.layers) >= 1
        assert len(model.entities.actors) >= 1
        assert len(model.entities.components) >= 1

    @pytest.mark.asyncio
    async def test_later_passes_include_prior_results(self, mock_client, context):
        """Pass 4 (relationships) receives entities from passes 1-3."""
        responses = [
            _yaml_response("layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"),
            _yaml_response("actors:\n  - id: A1\n    name: User\n    status: ACTIVE\n    type: human\ninterfaces: []"),
            _yaml_response("capabilities: []\nbehaviors: []"),
            _yaml_response("relationships:\n  - type: depends-on\n    from: C1\n    to: A1"),
            _yaml_response("constraints: []"),
        ]
        mock_client._chat.side_effect = responses
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        await mpe.extract()
        # Pass 4 (relationships) should reference prior entities
        fourth_call = mock_client._chat.call_args_list[3][0][0]
        user_msg = fourth_call[1]["content"]
        assert "L1" in user_msg or "C1" in user_msg or "A1" in user_msg

    @pytest.mark.asyncio
    async def test_handles_parse_failure_gracefully(self, mock_client, context):
        """If a pass returns garbage, extraction still produces a partial model."""
        responses = [
            _yaml_response("layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents: []"),
            _yaml_response("NOT VALID YAML {{{"),  # Pass 2 fails
            _yaml_response("capabilities: []\nbehaviors: []"),
            _yaml_response("relationships: []"),
            _yaml_response("constraints: []"),
        ]
        mock_client._chat.side_effect = responses
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        model = await mpe.extract()
        # Should still return a model with pass 1 results
        assert model is not None
        assert len(model.entities.layers) >= 1

    @pytest.mark.asyncio
    async def test_five_passes_called(self, mock_client, context):
        """Extract calls exactly 5 passes."""
        responses = [
            _yaml_response("layers: []\ncomponents: []"),
            _yaml_response("actors: []\ninterfaces: []"),
            _yaml_response("capabilities: []\nbehaviors: []"),
            _yaml_response("relationships: []"),
            _yaml_response("constraints: []"),
        ]
        mock_client._chat.side_effect = responses
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        await mpe.extract()
        assert mock_client._chat.call_count == 5
