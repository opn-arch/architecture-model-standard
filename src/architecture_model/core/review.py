"""LLM entity review loop — prepare prompts and apply review results."""
import copy
from datetime import datetime, timezone
from architecture_model.core.types import BaseEntity, Component, Capability
from architecture_model.core.detail_level import compute_detail_level
from architecture_model.monitoring import monitored


@monitored("core.review")
def prepare_review_prompt(entity: BaseEntity) -> str:
    """Generate a prompt asking LLM to review and fill missing fields."""
    level = compute_detail_level(entity)
    missing = []
    if not entity.intent:
        missing.append("intent")
    if not entity.description:
        missing.append("description")
    if isinstance(entity, Component):
        if not entity.responsibilities:
            missing.append("responsibilities")
        if not entity.goals:
            missing.append("goals")
        if not entity.moes:
            missing.append("moes")

    prompt = f"Review entity {entity.id} ({entity.name}).\n"
    prompt += f"Current detail level: L{level}\n"
    prompt += f"Description: {entity.description or '(none)'}\n"
    if missing:
        prompt += f"Missing fields to fill: {', '.join(missing)}\n"
    prompt += "Provide values for missing fields as JSON."
    return prompt


@monitored("core.review")
def apply_review(entity: BaseEntity, review_data: dict) -> BaseEntity:
    """Apply LLM review results back to entity."""
    updated = copy.deepcopy(entity)
    for field_name, value in review_data.items():
        if field_name == "review_notes":
            continue
        if hasattr(updated, field_name) and not getattr(updated, field_name):
            setattr(updated, field_name, value)
    updated.extensions["_llm_review"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": review_data.get("review_notes", ""),
    }
    return updated
