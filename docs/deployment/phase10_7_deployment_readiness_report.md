# Phase 10.7 Deployment Readiness Report

**Date:** 2026-06-03  
**Status:** COMPLETE  
**Backend Contract Reference:** [v0.6_backend_signoff.md](../release/v0.6_backend_signoff.md)  
**Validation Reference:** [phase10_6_validation_report.md](../ui/phase10_6_validation_report.md)  
**Existing Plan:** [render_deployment_plan.md](./render_deployment_plan.md)

---

## Deployment Readiness Assessment

### 1. Dependency Readiness: BLOCKED

**`pyproject.toml` analysis:**

| Dependency | Status | Notes |
|-----------|--------|-------|
| `requests>=2.31.0` | ✅ Present | HTTP client for RSS ingestion |
| `pydantic>=2.0.0` | ✅ Present | Data validation |
| `python-dotenv>=1.0.0` | ✅ Present | Env file loading |
| `feedparser>=6.0.10` | ✅ Present | RSS feed parsing |
| `pyyaml>=6.0.0` | ✅ Present | YAML config parsing |
| `google-genai>=2.2.0` | ✅ Present | Gemini API client |
| `streamlit` | ❌ **MISSING** | Required for UI — will cause `ImportError` |

**Additional issues:**
- No `requirements.txt` generated — Render can use `pyproject.toml` but lockfile must be current
- No `uv.lock` verified in repository root
- Dev dependencies (`pytest`, `black`, etc.) should not be installed on Render

**Remediation required:**
1. Add `"streamlit>=1.30.0"` to `dependencies` in `pyproject.toml`
2. Run `uv lock` to regenerate lockfile
3. Verify `uv.lock` is committed

---

### 2. Application Startup: BLOCKED

**Entrypoint:** `src/content_creation/ui/app.py` — `main()` function

**Startup command (from existing plan):**
```bash
streamlit run src/content_creation/ui/app.py --server.port $PORT --server.address 0.0.0.0
```

**Issues identified:**

1. **No `.streamlit/config.toml`:** Streamlit requires server configuration for headless mode. Without it, Streamlit may attempt to open a browser or use default ports.

2. **Path resolution in pages:** Each page file contains:
   ```python
   src_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
   if src_dir not in sys.path:
       sys.path.insert(0, src_dir)
   ```
   This works but is fragile. If the working directory differs from expectations, imports may fail.

3. **`ApplicationContext.create()` path resolution** (`client.py:31-43`):
   ```python
   @st.cache_resource
   def get_context() -> ApplicationContext:
       root_env = os.environ.get("CONTENT_FACTORY_ROOT")
       if root_env:
           base_dir = Path(root_env)
       else:
           base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
           if not (base_dir / "config").exists():
               base_dir = Path.cwd()
       return ApplicationContext.create(base_dir)
   ```
   If `CONTENT_FACTORY_ROOT` points to a persistent disk mount (e.g., `/workspace`), the `config/` directory must exist at that path. Source code config files are in the repo root, not on the persistent disk.

**Remediation required:**
1. Create `.streamlit/config.toml` with headless mode and server settings
2. Ensure `config/` directory is accessible from the resolved `base_dir`
3. Test startup with `CONTENT_FACTORY_ROOT` set to a non-source-code path

---

### 3. Environment Configuration: DOCUMENTED

**Required variables:**

| Variable | Required | Purpose | Default |
|----------|----------|---------|---------|
| `GEMINI_API_KEY` | Yes | Primary AI content generation provider | None (will error) |
| `OPENROUTER_API_KEY` | No | Fallback AI provider | None (optional) |
| `CONTENT_FACTORY_ROOT` | No | Override base directory for storage | Auto-detect from script path |
| `PYTHON_VERSION` | Yes (Render) | Python runtime version | `3.11` recommended |

**Secrets handling:**
- `app.py:62` uses `st.secrets.get("GEMINI_API_KEY")` for the E2E pipeline button
- Individual pages use `os.environ.get("GEMINI_API_KEY")` for sidebar override
- Render supports environment variables natively — no `.env` file needed

**Configuration files (checked into repo):**
- `config/feeds.yaml` — RSS feed sources
- `config/scoring.yaml` — Scoring weights and thresholds
- `config/publishing.yaml` — Publishing schedule configuration
- `prompts/*.md` — 7 prompt templates for content generation

---

### 4. Storage Readiness: REQUIRES CONFIGURATION

**Storage architecture:** File-based via `LocalStorage` class.

**Directory structure (16 directories under `data/`):**

| Directory | Purpose | Criticality |
|-----------|---------|-------------|
| `data/raw/` | Raw feed payloads | Low (regenerable) |
| `data/staged/` | Normalized topic items | High (ingestion state) |
| `data/scored/` | Scored topics | High (scoring state) |
| `data/briefs/` | Generated briefs | High (content artifacts) |
| `data/content_intelligence/` | CI analysis | High (content artifacts) |
| `data/storyboards/` | Storyboard plans | High (content artifacts) |
| `data/scripts/` | Video scripts | High (content artifacts) |
| `data/carousels/` | Carousel slides | High (content artifacts) |
| `data/newsletters/` | Newsletter copy | High (content artifacts) |
| `data/thumbnails/` | Thumbnail prompts | High (content artifacts) |
| `data/manifests/` | Asset manifests | High (planning state) |
| `data/calendars/` | Weekly calendars | Medium (planning state) |
| `data/dryruns/` | Validation reports | Low (diagnostic) |
| `data/analytics/` | Performance metrics | Medium (analytics) |
| `data/review_history/` | Review audit trail | High (compliance) |
| `data/workflow_state/` | Pipeline stage markers | Critical (resumability) |
| `data/logs/` | Pipeline execution logs | Low (diagnostic) |

**Render Persistent Disk requirements:**
- **Size:** 1 GB (sufficient for thousands of text artifacts)
- **Mount path:** `/mnt/data` (Render default)
- **Symlink strategy:** `ln -s /mnt/data ./data` in build command
- **Alternative:** Set `CONTENT_FACTORY_ROOT=/workspace` and mount disk at `/workspace/data`

**Fresh deployment behavior:**
- `LocalStorage.__init__()` creates all directories via `LocalBackend` on first access
- `ApplicationContext.create()` initializes storage, workflow, and prompt registry
- No migration or seed data required — directories are created empty

---

### 5. Logging & Error Visibility: PASS

| Error Type | Visibility Mechanism | Location |
|-----------|---------------------|----------|
| Startup failure | Streamlit error page + stderr | Streamlit framework |
| API key missing | `st.sidebar.error("Gemini API: Key Missing")` | `status.py:22` |
| Pipeline failure | `st.error(f"Failed to execute pipeline service: {e}")` | `app.py:83` |
| Stage failure | `st.status(state="error")` + `st.error()` | All page files |
| Service exception | try/except → `st.error(f"Failed: {e}")` | All page files |
| Generation failure | `st.error(f"Generate ... failed: {e}")` | All page files |
| Workflow divergence | `logger.warning()` | `asset_generation_service.py:86` |
| Pipeline logs | `data/logs/pipeline_{timestamp}.jsonl` | `pipeline_run_service.py:48` |

**Verified:** All errors surface clearly. No silent failures. UI remains stable on all error paths.

---

### 6. Deployment Documentation: EXISTS

Existing document: `docs/deployment/render_deployment_plan.md`

**Coverage:**
- ✅ Build command
- ✅ Start command
- ✅ Environment variables
- ✅ Storage mapping
- ✅ Persistent disk requirements
- ⚠️ Missing: `.streamlit/config.toml` specification
- ⚠️ Missing: Rollback steps
- ⚠️ Missing: Health check configuration

---

### 7. Backlog Review: NO BLOCKERS

| Item | Title | Blocks Deployment? | Reason |
|------|-------|-------------------|--------|
| BACKLOG-001 | Runtime Scoring Configuration | No | UI sliders work as preview; scoring uses `config/scoring.yaml` |
| BACKLOG-002 | Concurrent Review History Writes | No | Single-user deployment; no concurrent writes expected |

---

## Deployment Blockers

### Blocker 1 — Missing Streamlit Dependency (CRITICAL)
- **Issue:** `streamlit` not declared in `pyproject.toml` dependencies
- **Impact:** `ImportError: No module named 'streamlit'` on deployment
- **Remediation:** Add `"streamlit>=1.30.0"` to `dependencies` list, run `uv lock`

### Blocker 2 — No Streamlit Server Configuration (HIGH)
- **Issue:** No `.streamlit/config.toml` for headless mode
- **Impact:** Streamlit may attempt browser launch or use wrong port
- **Remediation:** Create `.streamlit/config.toml` with:
  ```toml
  [server]
  headless = true
  address = "0.0.0.0"
  port = 8501
  enableCORS = false
  enableXsrfProtection = false
  
  [browser]
  gatherUsageStats = false
  ```

### Blocker 3 — Config Path Resolution with Persistent Disk (HIGH)
- **Issue:** `ApplicationContext.create(base_dir)` looks for `base_dir / "config"` — if `CONTENT_FACTORY_ROOT` points to persistent disk mount, config files are not there
- **Impact:** `FileNotFoundError` for config files on startup
- **Remediation:** Either:
  - (A) Symlink `config/` to persistent disk: `ln -s /workspace/config /mnt/data/config`
  - (B) Set `CONTENT_FACTORY_ROOT` to repo root (not mount point) and only mount `data/`
  - (C) Modify `ApplicationContext` to separate code config path from data path

### Blocker 4 — No `requirements.txt` for Render (MEDIUM)
- **Issue:** Render typically uses `requirements.txt` for Python services
- **Impact:** Build command must use `uv pip install` instead of standard pip
- **Remediation:** Generate `requirements.txt` via `uv pip compile pyproject.toml -o requirements.txt` OR use the `uv`-based build command from existing plan

---

## Deployment Risks

**RISK-001 (Low) — Ephemeral filesystem data loss.**  
Without persistent disk, all pipeline state, artifacts, and review history are lost on redeploy. Mitigated by persistent disk configuration.

**RISK-002 (Low) — `st.secrets` vs environment variable inconsistency.**  
`app.py:62` uses `st.secrets.get("GEMINI_API_KEY")` while individual pages use `os.environ.get("GEMINI_API_KEY")`. On Render, `st.secrets` reads from environment variables, so this works. But if Streamlit secrets management is configured separately, keys could diverge.

**RISK-003 (Low) — `sys.path` manipulation in page files.**  
Each page file modifies `sys.path` at import time. This is fragile but functional. Standardizing via `PYTHONPATH` environment variable would be more robust.

**RISK-004 (Low) — No health check endpoint.**  
Render can configure health checks, but Streamlit doesn't expose a dedicated `/health` endpoint. The main page serves as an implicit health check.

---

## Required Remediation

### Before Deployment (Must Fix)

| # | Task | Priority | Effort |
|---|------|----------|--------|
| 1 | Add `streamlit>=1.30.0` to `pyproject.toml` dependencies | Critical | 5 min |
| 2 | Run `uv lock` to regenerate lockfile | Critical | 1 min |
| 3 | Create `.streamlit/config.toml` with headless mode | High | 5 min |
| 4 | Resolve config path issue for persistent disk | High | 15 min |
| 5 | Generate `requirements.txt` or verify `uv` build command works | Medium | 10 min |

### Recommended (Can Defer)

| # | Task | Priority | Effort |
|---|------|----------|--------|
| 6 | Add health check route or endpoint | Low | 15 min |
| 7 | Standardize `sys.path` via `PYTHONPATH` env var | Low | 30 min |
| 8 | Consolidate `st.secrets` vs `os.environ` usage | Low | 15 min |

---

## Render Configuration

### Service Type
- **Type:** Web Service
- **Runtime:** Python
- **Python Version:** 3.11 (via `PYTHON_VERSION` env var)

### Build Command
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv pip install --system -e .
```

### Start Command
```bash
streamlit run src/content_creation/ui/app.py --server.port $PORT --server.address 0.0.0.0
```

### Environment Variables
| Key | Value | Type |
|-----|-------|------|
| `GEMINI_API_KEY` | *(user-provided)* | Secret |
| `OPENROUTER_API_KEY` | *(user-provided, optional)* | Secret |
| `CONTENT_FACTORY_ROOT` | `/workspace` | Env Var |
| `PYTHON_VERSION` | `3.11` | Env Var |

### Persistent Disk
| Setting | Value |
|---------|-------|
| Size | 1 GB |
| Mount Path | `/mnt/data` |
| Mount Point in App | `/workspace/data` |

### Build-Time Setup (in Build Command)
```bash
ln -s /mnt/data ./data && ln -s /workspace/config ./config
```

---

## Final Recommendation

> **REQUIRES DEPLOYMENT REMEDIATION**

Four deployment blockers must be resolved before Render deployment:

1. **Streamlit dependency** — missing from `pyproject.toml` (CRITICAL)
2. **Streamlit server config** — no `.streamlit/config.toml` (HIGH)
3. **Config path resolution** — `CONTENT_FACTORY_ROOT` + persistent disk breaks config loading (HIGH)
4. **requirements.txt or uv build verification** — deployment install path unverified (MEDIUM)

Once these are remediated, the application is ready for Render deployment. The existing `render_deployment_plan.md` provides the correct deployment strategy — this report validates and extends it with specific file-level findings.
