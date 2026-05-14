"""Scoring configuration loader and validation."""

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo

logger = logging.getLogger(__name__)


class RuleConfig(BaseModel):
    """Generic configuration for a scoring rule."""
    enabled: bool = True
    weight: float = Field(..., ge=0.0, le=1.0)


class ValidationConfig(BaseModel):
    """Configuration for scoring validation and quality checks."""
    suspiciously_high_score: float = Field(default=95.0, ge=0.0, le=100.0)
    suspiciously_low_score: float = Field(default=10.0, ge=0.0, le=100.0)
    require_published_at: bool = True
    require_author: bool = False
    check_consistency: bool = True


class ScoringConfig(BaseModel):
    """Main scoring configuration matching scoring.yaml categories."""
    student_usefulness: RuleConfig
    novelty: RuleConfig
    credibility: RuleConfig
    explainability: RuleConfig
    hook_potential: RuleConfig
    validation: ValidationConfig = Field(default_factory=ValidationConfig)

    @field_validator("student_usefulness", "novelty", "credibility", "explainability", "hook_potential", "validation", mode="before")
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
        rules = [
            self.student_usefulness,
            self.novelty,
            self.credibility,
            self.explainability,
            self.hook_potential,
        ]
        for rule in rules:
            if rule.enabled:
                total += rule.weight
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
        logger.error(f"Scoring config not found at {config_path}")
        raise FileNotFoundError(f"Scoring config not found at {config_path}")

    try:
        from content_creation.utils.config import load_yaml_config
        data = load_yaml_config(config_path)
        scoring_data = data.get("scoring_rules", {})
        return ScoringConfig(**scoring_data)
    except Exception as e:
        logger.error(f"Failed to load scoring config from {config_path}: {e}")
        raise ValueError(f"Invalid scoring configuration: {e}")
