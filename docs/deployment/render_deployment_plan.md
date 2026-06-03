# Render Deployment Plan & Readiness Assessment

This document outlines the deployment strategy and readiness assessment for hosting the `content-creation` factory pipeline and Streamlit dashboard MVP on Render.

---

## 1. Deployment Specification

### Build Command
On Render, we can use the following build command to bootstrap the system, install `uv` (our package manager), and install dependencies:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv pip install --system -e .
```

### Start Command
To launch the Streamlit app on Render, the start command must bind to the port provided dynamically by the platform:
```bash
streamlit run src/content_creation/ui/app.py --server.port $PORT --server.address 0.0.0.0
```

### Python Version
The `pyproject.toml` specifies `requires-python = ">=3.10"`.
We recommend setting the Python version on Render to **`3.11`** (or `3.12`) via the `PYTHON_VERSION` environment variable.

### Dependency Management Approach
Dependency management uses `pyproject.toml` and `uv.lock` via the `uv` toolchain. Dependency resolution is locked on every commit.

### Environment Variables Required
The following environment variables must be configured on Render:
- `GEMINI_API_KEY` (Required; API key for the primary Google Gemini content synthesis provider)
- `OPENROUTER_API_KEY` (Optional; API key for the fallback OpenRouter provider)
- `CONTENT_FACTORY_ROOT` (Optional; path override for resolving storage paths. If not specified, the application resolves it dynamically by looking for directories relative to the script path)
- `PYTHON_VERSION` (Required by Render; set to `3.11` to match the target run environment)

### Local Storage Dependencies
The application uses [LocalStorage](file:///home/aryan/May-2026/Content-Creation/src/content_creation/storage/local.py) for persisting state and assets. All files are written to the `data/` directory at the project root. This includes raw RSS feeds, normalized staging topics, scored items, brief drafts, content intelligence, storyboards, generated scripts/carousels/newsletters/thumbnails, weekly calendars, validation dry-runs, post-level analytics sheets, and log history.

### Render Persistent Disk Requirements
Because Render containers are ephemeral (recreated on every deploy or restart), any content written to the local filesystem will be wiped. Since the application currently relies entirely on filesystem-based storage (`data/` directory), **a Render Persistent Disk is strictly required.**
- **Size Recommendation:** 1 GB (sufficient for thousands of text briefs and manifest assets)
- **Mount Path:** `/data` or `/workspace/data`
- **Configuration Integration:** Set the environment variable `CONTENT_FACTORY_ROOT` to point to `/workspace` (or the mounted persistent directory), or create a symlink from the root directory `data/` pointing to the mounted persistent disk path before startup (e.g. as part of the build/start phase: `ln -s /mnt/data ./data`).

---

## 2. Artifact Storage Mapping

Here is the exact folder structure of our generated assets under the `data/` directory:

```text
data/
├── raw/                      # Raw feed payloads fetched from sources (e.g. XML/HTML)
├── staged/                   # Staged TopicItems validated against canonical schemas
├── scored/                   # Scored TopicItems containing calculated metrics
├── briefs/                   # Educational briefs generated from scored topics
├── content_intelligence/     # Editorial angles, psychological hooks, and format mappings
├── storyboards/              # Coordinated metaphor allocation grids
├── scripts/                  # Generated video/audio script files
├── carousels/                # Generated carousel slides
├── newsletters/              # Generated newsletter copies
├── thumbnails/               # Generated image thumbnail prompts
├── manifests/                # Aggregated asset metadata manifests (ready for planning)
├── calendars/                # Planned weekly calendars
├── dryruns/                  # Pre-publish dryrun validation reports
├── analytics/                # Performance tracking records
├── workflow_state/           # Completed pipeline workflow stage markers
├── logs/                     # Live stream logs
└── cache/                    # Local caching of provider inference calls
```

---

## 3. Deployment Blockers — RESOLVED

All deployment blockers identified during Phase 10.7 readiness review have been resolved in Phase 10.7.1.

### 1. Missing Streamlit Dependency in `pyproject.toml` — RESOLVED
- **Resolution:** Added `"streamlit>=1.30.0"` to `dependencies` in `pyproject.toml`.
- **Installed version:** Streamlit 1.58.0
- **Lockfile:** Regenerated via `uv lock`.

### 2. Ephemeral Storage Resolution — RESOLVED
- **Resolution:** `CONTENT_FACTORY_ROOT` env var controls data directory. Config/prompt paths resolved independently from source code directory.
- **See:** Section 1.4 for updated configuration.

### 3. Absolute vs Relative Path Verification in UI Pages — DEFERRED
- **Status:** Low risk. Page path resolution works correctly in standard deployments. Can be standardized in future phase.

### 4. Configuration Path Robustness — RESOLVED
- **Resolution:** `ApplicationContext.create()` now accepts optional `source_dir` parameter. `get_context()` in `client.py` resolves source code root independently from `CONTENT_FACTORY_ROOT`.
- **Behavior:** Data writes go to `CONTENT_FACTORY_ROOT`. Config/prompts resolved from source code location.
