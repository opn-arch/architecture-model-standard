"""Integration test for enhanced extraction pipeline."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from architecture_model.training.context_builder import ContextBuilder, ContextSlices
from architecture_model.training.multi_pass import MultiPassExtractor
from architecture_model.training.refiner import ModelRefiner


@pytest.fixture
def sample_repo(tmp_path):
    """Minimal repo for integration testing."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "api.py").write_text(
        "from rest_framework.views import APIView\n"
        "class UserView(APIView):\n"
        "    def get(self, request): pass\n"
    )
    (pkg / "models.py").write_text(
        "from django.db import models\n"
        "class User(models.Model):\n"
        "    name = models.CharField(max_length=100)\n"
    )
    (pkg / "tasks.py").write_text(
        "from celery import shared_task\n"
        "@shared_task\n"
        "def notify(user_id): pass\n"
    )
    return pkg


class TestEnhancedExtraction:
    def test_context_builder_produces_slices(self, sample_repo):
        """ContextBuilder produces non-empty slices for a real repo."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert len(slices.structure) > 0
        assert len(slices.combined()) > 100

    @pytest.mark.asyncio
    async def test_full_pipeline_context_to_model(self, sample_repo):
        """End-to-end: context → multi-pass → model."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()

        mock_client = MagicMock()
        mock_client._chat = AsyncMock(side_effect=[
            {"message": {"content": "layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"}},
            {"message": {"content": "actors:\n  - id: A1\n    name: User\n    status: ACTIVE\n    type: human\ninterfaces: []"}},
            {"message": {"content": "capabilities:\n  - id: CAP1\n    name: CRUD\n    status: ACTIVE\nbehaviors: []"}},
            {"message": {"content": "relationships:\n  - type: contains\n    from: L1\n    to: C1"}},
            {"message": {"content": "constraints: []"}},
        ])

        extractor = MultiPassExtractor(mock_client, slices, project_name="test")
        model = await extractor.extract()
        assert model is not None
        assert model.entity_count >= 3  # At least layer + component + actor

    @pytest.mark.asyncio
    async def test_refiner_after_extraction(self, sample_repo):
        """Refiner doesn't crash when applied to a well-formed extracted model."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()

        mock_client = MagicMock()
        mock_client._chat = AsyncMock(side_effect=[
            {"message": {"content": "layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"}},
            {"message": {"content": "actors:\n  - id: A1\n    name: User\n    status: ACTIVE\n    type: human\ninterfaces: []"}},
            {"message": {"content": "capabilities: []\nbehaviors: []"}},
            {"message": {"content": "relationships:\n  - type: contains\n    from: L1\n    to: C1"}},
            {"message": {"content": "constraints: []"}},
        ])

        extractor = MultiPassExtractor(mock_client, slices, project_name="test")
        model = await extractor.extract()

        # Refiner should not crash on this model
        refiner = ModelRefiner(mock_client, max_rounds=1)
        result = await refiner.refine(model, slices.combined())
        assert result is not None
        assert result.entity_count >= model.entity_count
