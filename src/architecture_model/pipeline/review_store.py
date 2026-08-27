"""Persistence for pipeline review results."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .protocol import StageQualityReview


def save_reviews(review_dir: Path, reviews: list[StageQualityReview]) -> Path:
    """Save review log to JSON file. Returns path to saved file."""
    review_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = review_dir / f"review_{timestamp}.json"
    data = []
    for r in reviews:
        data.append({
            "stage": r.stage, "score": r.quality.score,
            "sub_scores": r.quality.sub_scores,
            "gate_results": [
                {"passed": gr.passed, "blocks": gr.blocks, "message": gr.message,
                 "metric": gr.metric, "actual": gr.actual, "threshold": gr.threshold}
                for gr in r.gate_results
            ],
            "llm_review": r.llm_review,
            "suggestions": r.suggestions,
            "component_reviews": r.component_reviews,
        })
    filepath.write_text(json.dumps(data, indent=2))
    return filepath


def load_reviews(review_dir: Path) -> list[dict[str, Any]]:
    """Load the most recent review file from directory."""
    if not review_dir.exists():
        return []
    files = sorted(review_dir.glob("review_*.json"), reverse=True)
    if not files:
        return []
    return json.loads(files[0].read_text())
