"""LinkedIn quality scoring models."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class LinkedInQualityGateResult(BaseModel):
    """Result for one deterministic LinkedIn quality gate."""

    name: str
    passed: bool
    score: int = Field(ge=0, le=100)
    message: str


class LinkedInQualityScore(BaseModel):
    """Aggregate deterministic quality score for one LinkedIn post."""

    overall_score: int = Field(ge=0, le=100)
    passed: bool
    gate_results: List[LinkedInQualityGateResult]
    issues: List[str]
    warnings: List[str]

    @field_validator("issues", "warnings")
    @classmethod
    def strip_blank_messages(cls, values):
        return [value.strip() for value in values if value.strip()]

    @field_validator("gate_results")
    @classmethod
    def must_have_at_least_one_gate(cls, values):
        if not values:
            raise ValueError("gate_results must contain at least one gate result")
        return values
