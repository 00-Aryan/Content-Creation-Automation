"""Scoring configuration loader and validation."""

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo

logger = logging.getLogger(__name__)


class RecencyConfig(BaseModel):
    """Configuration for recency scoring rule."""
    enabled: bool = True
    weight: float = Field(default=0.3, ge=0.0, le=1.0)
    half_life_days: int = Field(default=30, gt=0)
    max_age_days: int = Field(default=365, gt=0)

    @field_validator("max_age_days")
    @classmethod
    def validate_age_bounds(cls, v: int, info: ValidationInfo) -> int:
        """Ensure max_age_days >= half_life_days."""
        if "half_life_days" in info.data and v < info.data["half_life_days"]:
            raise ValueError("max_age_days must be >= half_life_days")
        return v


class SourceQualityConfig(BaseModel):
    """Configuration for source quality scoring rule."""
    enabled: bool = True
    weight: float = Field(default=0.25, ge=0.0, le=1.0)
    sources: Dict[str, float] = Field(default_factory=dict)
    default: float = Field(default=50.0, ge=0.0, le=100.0)


class KeywordConfig(BaseModel):
    """Configuration for keyword relevance scoring rule."""
    enabled: bool = True
    weight: float = Field(default=0.25, ge=0.0, le=1.0)
    topic_areas: Dict[str, List[str]] = Field(default_factory=dict)


class QualityConfig(BaseModel):
    """Configuration for quality heuristics scoring rule."""
    enabled: bool = True
    weight: float = Field(default=0.2, ge=0.0, le=1.0)
    min_title_length: int = Field(default=10, gt=0)
    max_title_length: int = Field(default=200, gt=0)
    has_description_bonus: float = Field(default=10.0, ge=0.0)
    has_tags_bonus: float = Field(default=5.0, ge=0.0)


class ValidationConfig(BaseModel):
    """Configuration for scoring validation and quality checks."""
    suspiciously_high_score: float = Field(default=95.0, ge=0.0, le=100.0)
    suspiciously_low_score: float = Field(default=10.0, ge=0.0, le=100.0)
    require_published_at: bool = True
    require_author: bool = False
    check_consistency: bool = True


class ScoringConfig(BaseModel):
    """Main scoring configuration."""
    recency: RecencyConfig = Field(default_factory=RecencyConfig)
    source_quality: SourceQualityConfig = Field(default_factory=SourceQualityConfig)
    keywords: KeywordConfig = Field(default_factory=KeywordConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

    @field_validator("recency", "source_quality", "keywords", "quality", "validation", mode="before")
    @classmethod
    def handle_none(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle None values for sub-configs."""
        return v or {}

    @model_validator(mode="after")
    def validate_total_weight(self) -> "ScoringConfig":
        """Ensure total weight of enabled rules is 1.0."""
        total = self.get_total_weight()
        if not math.isclose(total, 1.0, rel_tol=1e-9):
            raise ValueError(f"Total enabled weights must sum to 1.0, got {total:.4f}")
        return self

    def get_total_weight(self) -> float:
        """Calculate total weight of all enabled rules."""
        total = 0.0
        if self.recency.enabled:
            total += self.recency.weight
        if self.source_quality.enabled:
            total += self.source_quality.weight
        if self.keywords.enabled:
            total += self.keywords.weight
        if self.quality.enabled:
            total += self.quality.weight
        return total


def load_scoring_config(config_path: Path) -> ScoringConfig:
    """Load scoring configuration from YAML file.

    Args:
        config_path: Path to the scoring configuration YAML file.

    Returns:
        ScoringConfig instance.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid.
    """
    if not config_path.exists():
        logger.warning(f"Scoring config not found at {config_path}, using defaults")
        return ScoringConfig()

    try:
        from content_creation.utils.config import load_yaml_config
        data = load_yaml_config(config_path)
        scoring_data = data.get("scoring", {})
        return ScoringConfig(**scoring_data)
    except Exception as e:
        logger.error(f"Failed to load scoring config from {config_path}: {e}")
        raise ValueError(f"Invalid scoring configuration: {e}")
