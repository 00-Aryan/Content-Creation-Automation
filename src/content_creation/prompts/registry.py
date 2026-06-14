"""Prompt registry — single source of truth for prompt path resolution."""

from pathlib import Path
from typing import Dict, Tuple

# Registry mapping: (domain, prompt_name) -> relative path from base_dir
_REGISTRY: Dict[Tuple[str, str], str] = {
    ("brief", "summarize"): "prompts/summarize.md",
    ("script", "short_video"): "prompts/short_video.md",
    ("carousel", "carousel"): "prompts/carousel.md",
    ("newsletter", "newsletter"): "prompts/newsletter.md",
    ("thumbnail", "thumbnail"): "prompts/thumbnail.md",
    ("content_intelligence", "generate"): "prompts/content_intelligence.md",
    ("storyboard", "generate"): "prompts/storyboard.md",
    ("linkedin", "post"): "prompts/linkedin_post.md",
}


class PromptRegistry:
    """Resolves prompt paths by domain and name."""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir

    def get_path(self, domain: str, prompt_name: str) -> Path:
        """Return the resolved path for a domain prompt."""
        key = (domain, prompt_name)
        if key not in _REGISTRY:
            raise KeyError(
                f"Unknown prompt: domain={domain!r}, name={prompt_name!r}. "
                f"Registered: {sorted(_REGISTRY.keys())}"
            )
        return self._base_dir / _REGISTRY[key]

    def get(self, domain: str, prompt_name: str) -> str:
        """Return prompt content by domain and name."""
        path = self.get_path(domain, prompt_name)
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text()
