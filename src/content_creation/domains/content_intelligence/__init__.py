"""Content Intelligence domain."""

from .generator import ContentIntelligenceGenerator
from .model import ContentIntelligence, ContrastPair, EmotionalRegister, Hook, TopicType
from .quality import QualityStatus, evaluate_brief_quality
from .repository import ContentIntelligenceRepository

__all__ = [
    "ContentIntelligence",
    "ContentIntelligenceGenerator",
    "ContentIntelligenceRepository",
    "ContrastPair",
    "EmotionalRegister",
    "Hook",
    "QualityStatus",
    "TopicType",
    "evaluate_brief_quality",
]
