from pydantic import BaseModel
from typing import Dict, List, Literal, Optional


class AssetEntry(BaseModel):
    path: str
    status: Literal["draft", "needs_review", "missing", "skipped"]
    generated_at: Optional[str] = None


class TopicManifest(BaseModel):
    topic_id: str
    topic_title: str
    source_url: str
    assets: Dict[str, AssetEntry]
    overall_status: Literal["complete", "partial", "blocked"]
    blocking_reasons: List[str]
    ready_for_planner: bool
    generated_at: str