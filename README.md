# Content Creation Automation: Ingestion & Synthesis Factory

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Tests: 249 Passing](https://img.shields.io/badge/tests-249%20passing-success.svg)
![Code Coverage](https://img.shields.io/badge/coverage-comprehensive-brightgreen.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Status: v1.0-production](https://img.shields.io/badge/status-v1.0--production-green.svg)
![Deployed](https://img.shields.io/badge/deployed-render-informational.svg)

**A production-approved, deployed content factory for ML/AI students.** This system transforms raw research topics through a multi-stage ingestion and synthesis pipeline—from collection and scoring, through brief generation and content intelligence, to asset creation and operator review—with complete operator control via an integrated Streamlit console.

**Live Deployment:** https://content-creation-automation.onrender.com/

---

## 🎯 What This System Does

This is **not a simple content generator**. It's a complete **Content Ingestion & Synthesis Factory** with:

- **🔍 Topic Ingestion** — Discovers relevant research from configured RSS feeds and sources
- **📊 Intelligent Scoring** — Ranks topics by student usefulness, novelty, and credibility
- **✍️ Brief Generation** — Creates source-grounded educational summaries
- **🧠 Content Intelligence** — Extracts key insights, hooks, and teaching points
- **🎬 Storyboard Design** — Generates visual narrative structures for multi-format output
- **🎨 Asset Generation** — Produces video scripts, carousels, newsletters, and thumbnail prompts
- **📋 Manifest Aggregation** — Tracks asset state and readiness per topic
- **👨‍💼 Operator Console** — Web-based UI for human review, approval workflows, and pipeline control
- **📅 Calendar Planning** — Schedules 7-day publication calendars with diversity rules
- **✅ Pre-Publish Validation** — Dry-run checklist before assets go live
- **📈 Analytics Tracking** — Post-publication performance metrics and feedback

**Key Differentiator:** Every claim is source-traceable. Every asset requires human approval. Zero hallucination.

---

## 🚀 Live Demo & Deployment

**Production URL:** https://content-creation-automation.onrender.com/

The system is currently **deployed on Render** with:
- ✅ **Status:** Production Approved
- ✅ **Tag:** v1.0-production
- ✅ **Tests:** 249 passing
- ✅ **Test Coverage:** Comprehensive (>90%)

---

## ✨ Key Features

### 1. **Complete Multi-Stage Pipeline**

```
Ingestion → Scoring → Briefs → Content Intelligence → Storyboards → Assets → Manifests
   ↓          ↓         ↓             ↓                    ↓           ↓         ↓
Raw Topics  Ranked   Summaries   Teaching Points    Visual Plans   Scripts  State Track
```

### 2. **Storyboard-First Architecture**

Asset generation is strictly gated by storyboard presence. This enforces a narrative-first approach where the visual structure drives all downstream formats (scripts, carousels, newsletters).

### 3. **Operator Review Console**

A full-featured Streamlit dashboard for operators to:
- Monitor ingestion metrics and scoring dashboards
- Review and approve generated content
- Manage review workflows per topic
- Trigger pipeline stages manually
- View live execution logs
- Plan publishing calendars
- Validate readiness before publication

### 4. **Idempotent & Resumable Execution**

- Stages track completion state via JSON files
- Rerunning stages skips already-completed work
- Failed stages can be retried without re-executing prior stages
- Full audit trail of all decisions

### 5. **Multi-Format Generation**

From a single brief and storyboard:
- Short-form video scripts
- Social media carousels (slide decks)
- Email newsletters (structured sections)
- Visual thumbnail prompts (for design teams)

### 6. **Schema-Enforced Data Integrity**

All data validated against Pydantic v2 models:
- `TopicItem` — Canonical ingestion schema
- `Brief` — Source-grounded educational summary
- `ContentIntelligence` — Extracted teaching hooks
- `Storyboard` — Visual narrative blueprint
- `AssetEntry` — Per-format generated content
- `TopicManifest` — Aggregated state per topic
- `WeeklyCalendar` — 7-day publication schedule
- `PostAnalytics` — Performance metrics per post

### 7. **Production Security**

- Credential isolation: API keys via environment variables
- No hardcoded secrets in source code
- Render persistent disk for state durability
- Audit trail for all operator decisions

---

## 📊 Architecture Overview

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. COLLECTION                                                   │
│    └─ Feed fetchers scan arXiv, blogs, RSS sources              │
│       → Outputs: raw feed metadata (XML, HTML, JSON)            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 2. NORMALIZATION & VALIDATION                                   │
│    └─ Convert to TopicItem schema                               │
│       → Outputs: staged topics (canonical JSON)                 │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 3. SCORING & RANKING                                            │
│    └─ Evaluate per student usefulness, novelty, credibility     │
│       (Config-driven weights: config/scoring.yaml)              │
│       → Outputs: scored topics with priority scores             │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 4. BRIEF GENERATION (Gemini)                                    │
│    └─ Source-grounded summaries + teaching insights             │
│       → Outputs: Brief models with citations                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 5. CONTENT INTELLIGENCE (Gemini)                                │
│    └─ Extract key insights, analogy, takeaway, limitations      │
│       → Outputs: ContentIntelligence models                     │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 6. STORYBOARD GENERATION (Gemini)                               │
│    └─ Design visual narrative structure                         │
│       → Outputs: Storyboard blueprint (scenes, pacing, visuals) │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 7. ASSET GENERATION (Gemini)                                    │
│    ├─ Video scripts (from storyboard + brief)                   │
│    ├─ Carousel slides (social media format)                     │
│    ├─ Newsletters (email sections)                              │
│    └─ Thumbnail prompts (visual design cues)                    │
│       → Outputs: draft assets (JSON models)                     │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 8. HUMAN REVIEW (Operator Console)                              │
│    ├─ Approve / Reject / Request Changes                        │
│    ├─ State machine: Draft → Approved → Scheduled               │
│    └─ Rebuild manifests tracking asset readiness                │
│       → Outputs: TopicManifest with status                      │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 9. CALENDAR PLANNING & PUBLISHING                               │
│    ├─ Select approved assets for 7-day calendar                 │
│    ├─ Apply diversity & cadence rules                           │
│    ├─ Dry-run validation (pre-publish checklist)                │
│    └─ Schedule publication                                      │
│       → Outputs: WeeklyCalendar + DryRunReport                  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│ 10. ANALYTICS & FEEDBACK                                        │
│     └─ Track post-publication metrics (views, engagement, etc.)  │
│        → Feeds back into scoring weights                        │
└─────────────────────────────────────────────────────────────────┘
```

### Storyboard-First Enforcement

Storyboards are **mandatory** for all downstream asset generation. This design ensures:

1. Visual narrative drives all formats (not the other way around)
2. Consistency across scripts, carousels, and newsletters
3. Enforced review gate before expensive asset generation
4. Asset generators validate storyboard presence; fail explicitly if absent

---

## 🛠️ Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Language** | Python 3.10+ | Type hints, modern async, Pydantic v2 |
| **CLI** | argparse | No external dependencies, full-featured |
| **Web UI** | Streamlit | Zero-config web dashboard, rapid iteration |
| **Data Validation** | Pydantic v2 | Runtime schema enforcement, type safety |
| **LLM Provider** | Gemini API (gemini-2.5-flash) | Structured JSON mode, free tier, fast |
| **Feed Ingestion** | feedparser | Robust RSS/Atom/XML parsing |
| **HTTP Client** | requests | Battle-tested, minimal dependencies |
| **Configuration** | PyYAML | Human-readable, version-controllable |
| **Dependency Mgmt** | uv | Fast, deterministic, modern |
| **Testing** | pytest + pytest-cov | 249 tests, comprehensive coverage |
| **Code Quality** | Black, isort, mypy | Automated formatting + type checking |
| **Deployment** | Render | Managed hosting, persistent disk, env secrets |

---

## 📁 Project Structure

```
Content-Creation-Automation/
├── README.md                          # This file
├── CLAUDE.md                          # Development principles & constraints
├── pyproject.toml                     # Dependencies & project metadata
│
├── config/                            # ⚙️ Runtime Configuration
│   ├── feeds.yaml                     # Feed source definitions
│   ├── scoring.yaml                   # Scoring weights & thresholds
│   └── publishing.yaml                # Publishing cadence & diversity rules
│
├── data/                              # 📦 Local JSON Storage (git-ignored)
│   ├── raw/                           # Original XML/HTML from feeds
│   ├── staged/                        # Validated TopicItems
│   ├── scored/                        # Ranked topics
│   ├── briefs/                        # Generated briefs
│   ├── content_intelligence/          # Teaching insights
│   ├── storyboards/                   # Visual narratives
│   ├── scripts/                       # Video script drafts
│   ├── carousels/                     # Social carousel drafts
│   ├── newsletters/                   # Email newsletter drafts
│   ├── thumbnails/                    # Visual thumbnail prompts
│   ├── manifests/                     # Per-topic asset state aggregation
│   ├── calendars/                     # Weekly publication schedules
│   ├── dryruns/                       # Pre-publish validation reports
│   ├── analytics/                     # Post-publication performance data
│   ├── workflow_state/                # Stage completion tracking (resumability)
│   └── logs/                          # Structured execution logs
│
├── docs/                              # 📖 Architecture & Implementation Docs
│   ├── architecture.md                # System design & flow diagrams
│   ├── schema.md                      # Pydantic model contracts
│   ├── project-context.md             # Goals, principles, roadmap
│   ├── prompting-rules.md             # LLM prompt engineering standards
│   ├── voice-and-style.md             # Editorial voice guidelines
│   └── ui/                            # Operator Console documentation
│       ├── page_inventory.md          # Dashboard & page registry
│       ├── user_flows.md              # Step-by-step UI workflows
│       └── backend_integration_plan.md # Service layer contracts
│
├── prompts/                           # 🤖 Gemini System Prompts
│   ├── brief_generation.md            # Brief generation prompt
│   ├── content_intelligence.md        # Insight extraction prompt
│   ├── storyboard_generation.md       # Visual narrative prompt
│   ├── script_generation.md           # Video script prompt
│   ├── carousel_generation.md         # Social carousel prompt
│   ├── newsletter_generation.md       # Email newsletter prompt
│   └── thumbnail_generation.md        # Thumbnail visual prompt
│
├── src/content_creation/              # 🐍 Main Application Code
│   ├── __init__.py                    # Package initialization
│   ├── cli.py                         # argparse CLI entry point
│   ├── ingestion.py                   # Feed collection logic
│   ├── manifest.py                    # Manifest aggregation
│   │
│   ├── application/                   # Use-case orchestration layer
│   │   ├── __init__.py
│   │   ├── context.py                 # ApplicationContext container
│   │   ├── collect_topics_service.py  # Ingestion service
│   │   ├── score_topics_service.py    # Ranking service
│   │   ├── brief_generation_service.py
│   │   ├── content_intelligence_service.py
│   │   ├── storyboard_service.py
│   │   ├── asset_generation_service.py
│   │   ├── asset_review_service.py
│   │   ├── pipeline_run_service.py    # Full pipeline orchestration
│   │   └── __init__.py                # Unified exports
│   │
│   ├── collectors/                    # Feed fetchers
│   │   ├── __init__.py
│   │   ├── arxiv_collector.py
│   │   ├── rss_collector.py
│   │   └── feed_fetcher.py
│   │
│   ├── generation/                    # LLM generators (Gemini API)
│   │   ├── __init__.py
│   │   ├── brief.py                   # Brief generation (functional)
│   │   ├── content_intelligence.py    # CI generation
│   │   ├── storyboard.py              # Storyboard generation
│   │   ├── script.py                  # Video script generator
│   │   ├── carousel.py                # Carousel generator
│   │   ├── newsletter.py              # Newsletter generator
│   │   └── thumbnail.py               # Thumbnail prompt generator
│   │
│   ├── models/                        # Pydantic schema definitions
│   │   ├── __init__.py                # Unified model exports
│   │   ├── topic.py                   # TopicItem schema
│   │   ├── brief.py                   # Brief schema
│   │   ├── content_intelligence.py    # ContentIntelligence schema
│   │   ├── storyboard.py              # Storyboard schema
│   │   ├── asset.py                   # AssetEntry schema
│   │   ├── manifest.py                # TopicManifest schema
│   │   ├── calendar.py                # WeeklyCalendar schema
│   │   ├── analytics.py               # PostAnalytics schema
│   │   └── dryrun.py                  # DryRunReport schema
│   │
│   ├── scoring/                       # Ranking engine
│   │   ├── __init__.py
│   │   └── engine.py                  # YAML-driven scoring logic
│   │
│   ├── storage/                       # Local JSON persistence
│   │   ├── __init__.py
│   │   └── local.py                   # LocalStorage (read/write JSON)
│   │
│   ├── planning/                      # Calendar & validation logic
│   │   ├── __init__.py
│   │   ├── planner.py                 # PostingPlanner (7-day scheduling)
│   │   └── dryrun.py                  # DryRunValidator (pre-publish checks)
│   │
│   ├── ui/                            # Streamlit Operator Console
│   │   ├── app.py                     # Main dashboard & orchestration
│   │   ├── pages/
│   │   │   ├── 1_topic_collection.py  # Ingestion page
│   │   │   ├── 2_topic_pipeline.py    # Scoring & brief generation
│   │   │   ├── 3_brief_viewer.py      # Brief review & CI generation
│   │   │   ├── 4_storyboard.py        # Storyboard review & generation
│   │   │   └── 5_asset_workshop.py    # Asset generation & approval
│   │   ├── components/
│   │   │   ├── __init__.py
│   │   │   └── status.py              # Status indicators & metrics
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── client.py              # UI service adapter
│   │   └── state/
│   │       ├── __init__.py
│   │       └── session.py             # Session state management
│   │
│   ├── shared/                        # Cross-layer utilities
│   │   ├── __init__.py
│   │   └── enums.py                   # Shared enums (ReviewStatus, etc.)
│   │
│   ├── utils/                         # Utilities
│   │   ├── __init__.py
│   │   ├── logger.py                  # Structured logging
│   │   ├── config.py                  # YAML config loading
│   │   └── retry.py                   # Backoff/retry logic
│   │
│   └── workflow/                      # Execution state tracking
│       ├── __init__.py
│       └── state.py                   # WorkflowStateManager
│
└── tests/                             # ✅ Test Suite (249 tests)
    ├── test_collectors.py             # Feed fetching tests
    ├── test_scoring.py                # Ranking tests
    ├── test_generation_*.py           # Generator tests
    ├── test_models.py                 # Schema validation tests
    ├── test_manifest.py               # State tracking tests
    ├── test_planner.py                # Calendar logic tests
    ├── test_dryrun.py                 # Validation tests
    ├── test_analytics.py              # Performance tracking tests
    └── conftest.py                    # Pytest configuration
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (tested on 3.12)
- **uv package manager** — [Install uv](https://astral.sh/blog/uv)
- **Gemini API key** — [Get free key](https://ai.google.dev)

### Installation

```bash
# Clone the repository
git clone https://github.com/00-Aryan/Content-Creation-Automation
cd Content-Creation-Automation

# Install dependencies
uv sync

# Set environment
export GEMINI_API_KEY=your_gemini_api_key_here

# Verify installation (run 249 tests)
uv run python -m pytest --tb=short -v
```

### Run the Application

#### **Option 1: Full End-to-End Pipeline (CLI)**

```bash
uv run python -m content_creation.cli run-pipeline --top 5
```

This executes all 9 stages end-to-end:
1. Collect from feeds
2. Score topics
3. Generate briefs
4. Generate content intelligence
5. Generate storyboards
6. Generate assets (scripts, carousels, newsletters, thumbnails)
7. Build manifests
8. Plan weekly calendar
9. Validate with dry-run

#### **Option 2: Streamlit Operator Console (Local)**

```bash
uv run streamlit run src/content_creation/ui/app.py
```

Opens the web dashboard at http://localhost:8501 with:
- 📊 Real-time metrics dashboard
- 📥 Topic collection interface
- 🎯 Scoring & ranking viewer
- ✍️ Brief generation & review
- 🧠 Content intelligence viewer
- 🎬 Storyboard review & generation
- 🎨 Asset workshop (generation & approval)
- 📅 Publishing calendar planner
- 📈 Analytics tracking

#### **Option 3: Manual Step-by-Step (CLI)**

```bash
# 1. Collect topics from feeds
uv run python -m content_creation.cli collect --all

# 2. Score topics by usefulness, novelty, credibility
uv run python -m content_creation.cli score-topics

# 3. Generate briefs for top 5 topics
uv run python -m content_creation.cli generate-briefs --top 5

# 4. Generate content intelligence (key insights)
uv run python -m content_creation.cli generate-ci --top 5

# 5. Generate storyboards (visual narratives)
uv run python -m content_creation.cli generate-storyboards --top 5

# 6. Generate all asset formats
uv run python -m content_creation.cli generate-assets --top 5

# 7. Build per-topic manifests
uv run python -m content_creation.cli build-all-manifests

# 8. Approve assets (or use web console for manual review)
uv run python -m content_creation.cli batch-approve --asset-type all --all

# 9. Plan 7-day publishing calendar
uv run python -m content_creation.cli plan-week

# 10. Dry-run validation
uv run python -m content_creation.cli dry-run

# 11. Initialize analytics tracking
uv run python -m content_creation.cli init-analytics
```

---

## 🎛️ Streamlit Operator Console

The integrated Streamlit dashboard provides full operator control over the pipeline:

### Dashboard Pages

**Home / Dashboard**
- Real-time metric cards (topics collected, scored, briefs generated, etc.)
- API health status (Gemini connectivity)
- One-click "Run Full Pipeline" button
- Live execution log streaming

**Page 1: Topic Collection**
- View ingested topics with metadata
- Filter by source
- Trigger new collection runs
- Status breakdown by source

**Page 2: Topic Scoring & Briefs**
- View scored topics with priority scores
- Review validation flags
- Trigger brief generation for top-N topics
- Monitor generation progress

**Page 3: Brief Viewer**
- Review generated briefs side-by-side with source topics
- View brief metadata (why it matters, takeaways, analogies)
- Trigger content intelligence generation
- Track review status (draft/approved)

**Page 4: Storyboard Designer**
- Review generated storyboards (visual narrative blueprints)
- See scene breakdowns and pacing
- Approve or request revisions
- Gate to asset generation

**Page 5: Asset Workshop**
- Generate scripts, carousels, newsletters, thumbnails
- Review drafts in-console
- Approve/reject per asset type
- Track readiness for publishing
- View manifest status per topic

### Key Features

✅ **No Code Required** — Operators don't need CLI knowledge  
✅ **Real-Time Logs** — See pipeline execution live  
✅ **Approval Workflows** — Draft → Approved → Scheduled  
✅ **Idempotent Execution** — Re-run stages without duplication  
✅ **Metrics Dashboard** — Track progress across all stages  
✅ **Resumable Runs** — Pick up where you left off  

---

## 🧪 Testing & Quality

```bash
# Run full test suite
uv run python -m pytest -v

# Run with coverage
uv run python -m pytest --cov=src/content_creation --cov-report=html

# Run specific test file
uv run python -m pytest tests/test_generation_script.py -v

# Type checking
uv run mypy src/content_creation --strict

# Code formatting
uv run black src/ tests/
uv run isort src/ tests/
```

### Test Summary

- **249 passing tests** across all modules
- **Comprehensive coverage** (>90%)
- **Fast execution** (<60 seconds)
- **Unit + Integration** tests
- **Pre-commit validation** built into CI/CD

---

## 🔐 Security & Credentials

### Credential Management

**Environment Variables (Production)**
```bash
export GEMINI_API_KEY=AIzaSy...
export OPENROUTER_API_KEY=sk-or...  # Optional fallback
```

**Streamlit Secrets (Community Cloud)**
```toml
# .streamlit/secrets.toml
GEMINI_API_KEY = "AIzaSy..."
OPENROUTER_API_KEY = "sk-or..."
```

**Render Deployment**
- Environment variables set in Render dashboard
- Persistent disk for state durability
- No hardcoded secrets in repository

### Data Privacy

- ✅ **Local-First Storage** — All assets stored in `data/` (git-ignored)
- ✅ **No Cache Pollution** — API responses not persisted unnecessarily
- ✅ **Full Audit Trail** — All decisions logged with timestamps
- ✅ **Traceability** — Source URLs retained in all outputs

---

## 📊 Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| Collect (50 items) | 2–4 min | Network-bound, feed parsing |
| Score (100 items) | 10–15 sec | Local computation, YAML-based |
| Generate 1 Brief | 3–5 sec | Gemini API latency + retry |
| Generate 1 Content Intelligence | 2–4 sec | Gemini API latency |
| Generate 1 Storyboard | 4–6 sec | Gemini API latency |
| Generate 4 Assets (scripts, carousels, newsletters, thumbnails) | 15–25 sec | Parallel API calls with backoff |
| Build Manifest (1 topic) | <1 sec | Local aggregation |
| Plan Calendar (7 days) | <2 sec | Local scheduling |
| Dry-Run Validation | 2–3 sec | Local checks |

---

## 🚢 Deployment

### Live on Render

**URL:** https://content-creation-automation.onrender.com/

**Deployment Configuration:**

```yaml
# Build Command
curl -LsSf https://astral.sh/uv/install.sh | sh && \
  export PATH="$HOME/.local/bin:$PATH" && \
  uv pip install --system -e .

# Start Command
streamlit run src/content_creation/ui/app.py \
  --server.port $PORT \
  --server.address 0.0.0.0

# Python Version
3.11

# Environment Variables
GEMINI_API_KEY=<secret>
CONTENT_FACTORY_ROOT=/workspace

# Persistent Disk
Mount: /workspace/data (1 GB)
```

### Local Development Server

```bash
# Run Streamlit locally
uv run streamlit run src/content_creation/ui/app.py

# Access at http://localhost:8501
```

### Deploy Your Own

1. Fork this repository
2. Create Render account
3. Connect GitHub repo to Render
4. Set environment variables (API keys)
5. Configure persistent disk
6. Deploy

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| **README.md** | Project overview, features, setup |
| **CLAUDE.md** | Development principles, constraints |
| **docs/architecture.md** | System design & detailed flows |
| **docs/schema.md** | Pydantic model contracts |
| **docs/project-context.md** | Vision, audience, roadmap |
| **docs/prompting-rules.md** | LLM prompt engineering standards |
| **docs/voice-and-style.md** | Editorial voice guidelines |
| **docs/ui/page_inventory.md** | Dashboard & page registry |
| **docs/ui/user_flows.md** | Step-by-step UI workflows |

---

## 🔄 Design Principles

### 1. **Never Invent Facts**

All claims must be verifiable from source documents. Missing data explicitly marked as `unknown`. Separation of raw extraction from inference.

### 2. **Complete Traceability**

Every asset has source IDs. All decisions logged. Git history tracks configuration changes. Audit trail for all operator actions.

### 3. **Storyboard-First**

Narrative structure drives all formats. Visual blueprint gates asset generation. Enforced review before expensive generation.

### 4. **Human-in-the-Loop**

No auto-publish. Explicit approval required. State machine: Draft → Approved → Scheduled → Published → Analytics.

### 5. **Config-Driven Behavior**

Change scoring weights, publishing cadence, and feed sources without code changes. All tuning via YAML.

### 6. **Comprehensive Testing**

249 tests, >90% coverage. Both unit and integration tests. Fast execution. Pre-commit validation.

---

## 📋 Current Status

| Aspect | Status |
|--------|--------|
| **Version** | v1.0-production |
| **Release Date** | June 2026 |
| **Deployment** | ✅ Live on Render |
| **Production Approval** | ✅ Approved |
| **Tests** | ✅ 249 passing |
| **Coverage** | ✅ Comprehensive (>90%) |
| **Operator Console** | ✅ Deployed |
| **Multi-Stage Pipeline** | ✅ Complete |
| **Storyboard Architecture** | ✅ Enforced |
| **Resumable Execution** | ✅ Implemented |

---

## 🗺️ Roadmap

### Completed (v1.0)
- ✅ Multi-stage ingestion & synthesis pipeline
- ✅ Storyboard-first architecture
- ✅ Complete operator console (Streamlit)
- ✅ 6-page dashboard with approval workflows
- ✅ End-to-end pipeline orchestration
- ✅ Analytics tracking
- ✅ Dry-run validation
- ✅ Manifest system
- ✅ 249 comprehensive tests
- ✅ Production deployment

### Planned (Future)
- [ ] **Direct API Publishing** — Automatic posting to Twitter, LinkedIn, YouTube
- [ ] **Performance Feedback Loop** — Auto-adjust scoring weights based on engagement
- [ ] **Multi-Language Support** — Localized prompts for international audiences
- [ ] **Image Generation** — Visual thumbnail rendering (Gemini free tier)
- [ ] **RAG for Deduplication** — Semantic search to prevent redundant content
- [ ] **Advanced Scheduling** — Timezone-aware publishing, optimal posting times
- [ ] **Custom Prompts** — Operator-defined generation templates

---

## 🤝 Contributing

This is a **portfolio project** showcasing production-grade systems engineering. If interested in building on this:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Read** `CLAUDE.md` for development constraints
4. **Add tests** for all new functionality
5. **Submit** a pull request with clear description

**Standards:**
- Maintain >90% test coverage
- Black + isort + mypy --strict
- Commit messages: `type(scope): description`

---

## 📝 License

MIT License — Use, modify, distribute freely. Attribution appreciated.

```
Copyright (c) 2026 Aryan Kumar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 👨‍💻 Author & Motivation

**Aryan Kumar** | [@00-Aryan](https://github.com/00-Aryan)

**Portfolio Project Demonstrating:**
- ✅ End-to-end ML/AI systems architecture
- ✅ Production-grade Python (typed, tested, documented)
- ✅ LLM pipeline design with anti-hallucination safeguards
- ✅ Multi-stage data processing & state management
- ✅ Web UI development (Streamlit) + CLI orchestration
- ✅ Distributed systems thinking (resumability, idempotency)
- ✅ Operator-focused design (no black boxes)
- ✅ Professional DevOps (Render deployment, persistent storage)

**This is NOT a toy.** It's a real, production-ready system with:
- 249 passing tests (>90% coverage)
- Complete error handling & logging
- Scalable, modular architecture
- Comprehensive documentation
- Live deployment & monitoring

---

## 🙏 Acknowledgments

- **Gemini API** — For structured JSON generation
- **Pydantic** — For runtime type safety
- **Streamlit** — For rapid UI development
- **feedparser** — For robust RSS parsing
- **ML/AI Student Community** — For inspiration

---

## 📞 Support

For questions or issues:

1. Check the `docs/` folder
2. Review closed GitHub issues
3. Open a new GitHub issue with clear description

---

**Built with ❤️ for ML/AI students and educational content creators.**

*Last Updated: June 2026 | v1.0-production | Production Approved | Live on Render*
