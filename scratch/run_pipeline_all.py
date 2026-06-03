import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load env
env_path = Path("/home/aryan/May-2026/Content-Creation/.env")
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {api_key is not None}")

# Add src to path
sys.path.insert(0, "/home/aryan/May-2026/Content-Creation/src")

from content_creation.models.brief import Brief
from content_creation.models.topic import TopicItem, ScoredTopicItem
from content_creation.domains.content_intelligence.generator import ContentIntelligenceGenerator
from content_creation.domains.storyboard.generator import StoryboardGenerator
from content_creation.generation.thumbnail import ThumbnailGenerator
from content_creation.generation.brief import generate_brief
from content_creation.prompts import PromptRegistry
from content_creation.storage.local import LocalStorage
from content_creation.domains.content_intelligence.repository import ContentIntelligenceRepository
from content_creation.domains.storyboard.repository import StoryboardRepository

base_dir = Path("/home/aryan/May-2026/Content-Creation")
storage = LocalStorage(base_dir)
registry = PromptRegistry(base_dir)

ci_repo = ContentIntelligenceRepository(base_dir / "data" / "content_intelligence")
sb_repo = StoryboardRepository(base_dir / "data" / "storyboards")

# The 10 chosen topics
topic_ids = [
    "468a4a589f8d4a953bda8ae2a95bcf1d563f328b0000660a5ce2437a9d3f16c1", # MobiBench
    "d319a59734a08b0b2658b089bd1a2e69c8d4fddddf6bd24ca1f6e74b099bbafb", # Human-Flow Digital Twin
    "866047e526b8d4d3ab97649120e12abbb7d94e2a4ddd795a29baf2eead7f3625", # SGD linear networks
    "7c26d52278c42475b5df845e869e7cf5b44d54b6dea23456f3605c1244cb5f22", # Customers in distress
    "9c41388712568bdca9f2b26fb3a46b744a8d01f2415f2c9469c5873f3d3d0019", # KamonBench
    "a5ff171e87668b5923fab715ad48943692ba90c192db47a5f4894d40b4905dc4", # ScioMind
    "5d2862b7a56a341ff2878e31a98425f9238296c9454c1b14a4b40d2df3360576", # TMPO
    "ccde3cde2aa9e46761357a6ee5e0382351cff65da3f99ae672c0a1bc15ce1cb2", # BO noise
    "f23a20ac073764cabf8cba6dafe9b21d2cec0b6bf5421a2d48539137fb394046", # Quantum decoder
    "2b20a8623e337127048f0d029f4dfe51230b69a63b20b1f4b48449b61c1b3ff5"  # Elections OpenAI
]

# Instantiate generators
ci_gen = ContentIntelligenceGenerator(api_key=api_key, registry=registry)
sb_gen = StoryboardGenerator(api_key=api_key, registry=registry)
thumb_gen = ThumbnailGenerator(api_key=api_key, prompt_dir=registry)

print(f"Starting pipeline run for {len(topic_ids)} topics...")

for idx, tid in enumerate(topic_ids):
    print(f"\nProcessing {idx+1}/{len(topic_ids)}: ID={tid}")
    
    # 1. Load scored topic item
    try:
        scored_item = storage.get_scored(tid)
        if not scored_item:
            # try staged
            scored_item = storage.get_staged(tid)
    except Exception as e:
        print(f"  Error loading topic: {e}")
        continue
        
    if not scored_item:
        print(f"  Topic not found: {tid}")
        continue
        
    print(f"  Topic Title: {scored_item.title[:60]}")
    
    # 2. Generate/Regenerate Brief
    brief = None
    try:
        # Check if we already have a fully generated non-fallback brief
        existing_brief = storage._brief_repo.get(tid)
        if existing_brief and existing_brief.why_it_matters != "needs_review":
            print("  Using existing Brief")
            brief = existing_brief
        else:
            print("  Generating fresh Brief...")
            # We mock registry or prompt path
            brief = generate_brief(scored_item, registry, api_key)
            storage._brief_repo.save(brief)
            print("  Saved Brief")
    except Exception as e:
        print(f"  Error generating Brief: {e}")
        continue
        
    if not brief:
        print("  Brief generation failed")
        continue

    # 3. Generate CI
    ci = None
    try:
        print("  Generating Content Intelligence...")
        ci = ci_gen.generate(brief, topic_category=scored_item.category, published_at=scored_item.published_at)
        ci_repo.save(ci)
        print(f"  Saved CI (Status={ci.review_status})")
    except Exception as e:
        print(f"  Error generating CI: {e}")
        
    if not ci or ci.review_status.value == "needs_review":
        print("  CI failed or went to fallback")
        continue

    # 4. Generate Storyboard
    sb = None
    try:
        print("  Generating Storyboard...")
        sb = sb_gen.generate(brief, ci)
        sb_repo.save(sb)
        print(f"  Saved Storyboard (Status={sb.review_status})")
    except Exception as e:
        print(f"  Error generating Storyboard: {e}")
        
    if not sb or sb.review_status.value == "needs_review":
        print("  Storyboard failed or went to fallback")
        continue

    # 5. Generate Thumbnail
    try:
        print("  Generating Thumbnail...")
        thumb = thumb_gen.generate(sb, brief)
        storage._thumbnail_repo.save(thumb)
        print(f"  Saved Thumbnail (Status={thumb.review_status})")
    except Exception as e:
        print(f"  Error generating Thumbnail: {e}")

print("\nPipeline execution completed!")
