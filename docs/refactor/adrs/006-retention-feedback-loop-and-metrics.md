# ADR 006: Post-Publication Retention Feedback Loop, Metric Ingestion & Prompt Diagnostic Cadence

- **Status:** PROPOSED
- **Date:** 2026-11-21
- **Deciders:** `spec-architect`, `prompt-eval-auditor`, `phase-orchestrator`
- **Target Phase:** Phase 3B / Phase G3 (Cross-Vertical Retention & Audience Analytics)
- **Consulted:** `docs/refactor/adrs/001-native-fragments-and-ui-facades.md`, `docs/refactor/adrs/003-single-wal-sqlite-database.md`, `docs/refactor/adrs/004-llm-cost-governance-and-eval-harness.md`, `docs/refactor/adrs/005-low-spec-media-execution-budget.md`

---

## 1. Context & Business Objective

The `Content-Creation-Automation` platform generates educational video scripts, carousels, and gaming highlight shorts across YouTube Shorts, Instagram Reels, and Facebook Reels. Prior architecture decisions established pre-generation cost governance (ADR-004), offline rubric evaluation (Pass 1 & Pass 2 in `prompt-eval-auditor`), and low-spec media rendering (ADR-005).

However, pre-publication evaluation only measures *synthesized intent*. The ultimate monetization and reach of content is dictated by post-publication audience retention, algorithmic distribution velocity, and viewer actions (shares, saves, skip rates).

Operating an AI content pipeline without a disciplined post-publication feedback loop introduces severe business and architectural liabilities:

### 1.1 The Trap of Premature Prompt Overfitting (The "N=1" Anti-Pattern)
Algorithmic recommendation engines (YouTube Shorts algorithm, Instagram Reels graph) exhibit extreme distribution variance. Two videos produced with identical prompt versions, identical hook styles, and identical cut pacing can achieve 400 views or 400,000 views based on external platform factors (time of day, audience cold-start seed clusters, competing trending audio, platform testing windows).
- **The Anti-Pattern:** When creators mutate system prompts, change hook formulas, or alter playbooks after only 1 or 2 poorly performing posts, they chase noise and overfit to random algorithmic variance.
- **The Remedy:** Prompt and playbook revisions must be gated by a **15-post cohort evaluation cadence**. No prompt or director playbook may be altered until a full cohort of 15 consecutive published posts has accumulated stable 72-hour audience metrics.

### 1.2 Local Host & Zero-SaaS Analytics Constraint
- **Hardware Baseline:** AMD Ryzen 5 7600X, **8 GB RAM**, 256 GB NVMe SSD on Windows 11.
- **Zero SaaS / Zero Heavy Stack Mandate:** Commercial social media analytics suites (e.g., Sprout Social, Hootsuite, Tubular, Datadog) cost $100–$500/month and require heavy background daemons or external database clusters. The analytics engine must operate 100% locally using free official APIs (YouTube Data & Analytics API, Instagram Graph API) and lightweight local persistence inside `data/content_factory.db` (WAL-mode SQLite per ADR-003).

### 1.3 Full-Funnel Attribution (From Token Cost to Watch Time)
Every published asset must maintain unbroken lineage back to its upstream generation telemetry:
`TopicItem` $\rightarrow$ `EvidenceBundle` $\rightarrow$ `RunBudget` / `run_id` (ADR-004) $\rightarrow$ `prompt_version` $\rightarrow$ `shadow_cost_usd` $\rightarrow$ `post_id` $\rightarrow$ `metric_snapshots` (24h, 72h, 7d).
This allows the system to compute true **Audience ROI**:
$$\text{Audience ROI} = \frac{\text{Engaged View Hours}}{\text{Actual USD Spend} + \text{Shadow Cost USD}}$$

---

## 2. Decision Drivers

- **Zero-Cost Official API Ingestion:** Ingest metrics strictly through free official platform APIs (YouTube Data API v3, YouTube Analytics API via free Google OAuth; Instagram Graph API v22.0+ via free Meta Creator/Business accounts).
- **2026 Meta API Deprecation Compliance:** Explicitly ban deprecated Instagram metrics (`impressions`, `plays`, `clips_replays_count`) and standardize on current fields (`views`, `reach`, `shares`, `saved`, `skip_rate`).
- **Immediate Day-1 Usability (Manual Entry Fallback):** Provide a lightweight CLI and Streamlit manual metric entry interface (`cli metrics log`) so tracking begins on day 1 before OAuth credentials or Meta App Review are completed.
- **Secret Hygiene & Token Storage:** OAuth refresh tokens and client secrets must reside strictly in `.env` / OS keyring, never committed to git or exposed in logs (`AGENTS.md` §6.2, §16).
- **15-Post Cohort Discipline:** Enforce strict prompt version freezing across 15-post cohorts to eliminate stochastic noise before allowing playbook mutations.
- **Diagnostic Actionability:** Map metric underperformance directly to targeted system components (e.g., low 3-second hold $\rightarrow$ `director.md` hook; low average view percentage $\rightarrow$ `editor_cuts.md` pacing; high human edit percentage $\rightarrow$ prompt alignment).
- **50+ Post Tabular ML Hook Scorer:** Lay the structural groundwork for an offline, local machine-learning pre-scorer (LightGBM/Logistic Regression) once 50+ posts have accumulated 72-hour retention curves.

---

## 3. Architecture & Data Flow

```
+--------------------------------------------------------------------------------------------------+
| PUBLICATION & PROVENANCE TRACKING                                                                |
| - Stage 5 / Human Review approves asset -> Operator publishes to YouTube Shorts / Reels         |
| - Record created in published_posts: links external_post_id to run_id, prompt_version, cost       |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| INGESTION TIER: AUTOMATED CRON OR MANUAL CLI ENTRY                                              |
|                                                                                                  |
| [Option A: Automated OAuth Fetcher]              [Option B: Day-1 Manual CLI Fallback]           |
| - YouTube Analytics API (daily cron)             - cli metrics log --post-id P-101               |
| - Instagram Graph API v22.0+ (daily cron)          --views 1420 --avg-pct 72.4 --shares 18       |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| METRIC TIME-SERIES SNAPSHOTS (data/content_factory.db)                                           |
| - INSERT INTO metric_snapshots: records 24h, 72h, 7d performance windows                        |
| - Captures views, reach, avg_view_pct, hook_hold_3s_pct, and 10-bucket retention_curve_json      |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| 15-POST COHORT EVALUATION ENGINE                                                                 |
| - Computes cohort aggregates: Mean Hook Hold %, Mean View %, Shares per 1k views                |
| - Compares cohort against Target Benchmarks                                                      |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| DIAGNOSTIC DECISION MATRIX (Automated Playbook Tuning Triggers)                                  |
|                                                                                                  |
| Metric Symptom                  Root Cause Stage              Remediation Action                 |
| ──────────────────────────────  ────────────────────────────  ────────────────────────────────── |
| Hook Hold (0-3s) < 55%          Stage 2 / director.md         Tighten verbal interrupt; cut <2s  |
| Avg View Pct < 70%              Stage 2 / editor_cuts.md      Increase visual cut density (3.0s) |
| Shares per 1k views < 5         Stage 1.5 / Intel Briefing    Raise technical novelty threshold  |
| Human Edit Pct > 50%            Stage 2 Generator Prompt      Inject editor diff into guidelines |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                         +-------------------------+-------------------------+
                         |                                                   |
                         v                                                   v
+--------------------------------------------------+     +-------------------------------------+
| STREAMLIT RETENTION & ROI DASHBOARD              |     | 50+ POST LOCAL TABULAR ML PRE-SCORER |
| - Filter by Genre, Platform, Prompt Version      |     | - LightGBM CPU model (< 20 MB RAM)  |
| - Plot 10-Bucket Retention Curves                |     | - Predicts 72h view % from hook text |
| - Displays Audience ROI ($ / Engaged Hour)       |     | - Offline pre-filter for generators |
| (Rendered via ServiceClient + @st.fragment)      |     +-------------------------------------+
+--------------------------------------------------+
```

---

## 4. Decision 1 — Free API Ingestion & 2026 Schema Compliance

### 4.1 YouTube Data API v3 & YouTube Analytics API (Free Tier)
Google Cloud provides 10,000 free quota units per day for YouTube Data API v3, and the YouTube Analytics API is fully free for channel owners under standard OAuth 2.0 user credentials.
- **Ingestion Endpoint:** `https://youtubeanalytics.googleapis.com/v2/reports`
- **Standardized Ingestion Fields:**
  - Core engagement: `views`, `likes`, `comments`, `shares`, `subscribersGained`.
  - Retention metrics: `averageViewDuration` (seconds), `averageViewPercentage` (0.0–100.0%).
  - Audience curve: `audienceWatchRatio` across 10 normalized duration intervals ($0\%, 10\%, \dots, 90\%$).
  - Monetization: `estimatedRevenue` (if channel is in YouTube Partner Program, else 0.0).

### 4.2 Instagram Graph API v22.0+ (Free Creator/Business Accounts)
Meta provides free API access for Instagram Professional (Creator or Business) accounts connected to a Facebook Page. In 2025/2026, Meta overhauled video analytics to unify video and Reels metrics under a unified `views` definition.
- **Strictly Banned Deprecated Fields:**
  - `impressions` *(Deprecated across video endpoints)*
  - `plays` *(Deprecated)*
  - `clips_replays_count` *(Deprecated)*
  - `ig_reels_aggregated_all_plays_count` *(Deprecated)*
- **Mandated Active 2026 Ingestion Fields:**
  - Endpoint: `GET /{ig-media-id}/insights?metric=views,reach,saved,shares,likes,comments,reposts`
  - Reels Retention: `views` (total plays + replays), `reach` (unique accounts), `shares`, `saved`, `reposts`.
  - Skip / Drop-off Rate: Measured by comparing unique 3-second views against total reach:
    $$\text{Hook Hold Rate (3s)} = \frac{\text{3-Second Continuous Views}}{\text{Reach}} \times 100\%$$

### 4.3 Day-1 Manual Metric Entry Fallback (`cli metrics log`)
Because Meta App Review and Google Cloud OAuth verification can take 2–4 weeks, the system must not block on API approval. Operators can record metrics manually via CLI or Streamlit in under 30 seconds:

```bash
# Day-1 CLI manual logging command
python -m content_creation.cli metrics log \
  --post-id "yt_shorts_20261121_01" \
  --window "72h" \
  --views 4820 \
  --avg-view-pct 74.2 \
  --hook-hold-pct 68.0 \
  --shares 32 \
  --saves 18 \
  --source "manual_entry"
```

### 4.4 Secret Hygiene & Token Management (`AGENTS.md` §6.2)
- OAuth refresh tokens and client IDs are loaded strictly from environment variables:
  `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `INSTAGRAM_ACCESS_TOKEN`.
- Real tokens must never be written to SQLite, committed to git, or printed in logs.
- If token refresh fails with `401 Unauthorized`, the worker logs a sanitized `WARNING: OAuth refresh token expired for YouTube [Code: ERR_AUTH_REFRESH]` and halts without crashing.

---

## 5. Decision 2 — SQLite `published_posts` & `metric_snapshots` Schema

All post records and historical metric snapshots reside in the single consolidated database `data/content_factory.db` (WAL-mode per ADR-003):

```sql
-- Published Posts: Core registry connecting published social assets to generation lineage
CREATE TABLE IF NOT EXISTS published_posts (
    post_id TEXT PRIMARY KEY,                       -- Internal unique ID (e.g., 'post_yt_20261121_001')
    run_id TEXT,                                    -- Foreign Key to eval_runs.run_id or jobs.job_id
    genre TEXT NOT NULL,                            -- 'educational' or 'gaming_clips'
    platform TEXT NOT NULL,                         -- 'youtube_shorts', 'instagram_reels', 'facebook_reels'
    external_post_id TEXT,                          -- Platform video ID (e.g., YouTube videoId, IG media_id)
    external_url TEXT,                              -- Direct public URL to published post
    prompt_version TEXT NOT NULL DEFAULT 'v1.0.0',  -- Prompt git commit or semantic version
    playbook_version TEXT NOT NULL DEFAULT 'v1.0',  -- Director/Editor playbook version
    hook_type TEXT NOT NULL,                        -- 'question', 'contrarian', 'curiosity_gap', 'clutch_moment'
    duration_sec REAL NOT NULL,                     -- Final video duration in seconds
    human_edit_pct REAL NOT NULL DEFAULT 0.0,       -- Estimated % of script/cut modified by human editor
    shadow_cost_usd REAL NOT NULL DEFAULT 0.0,      -- Carried forward from ADR-004 llm_usage_ledger
    published_at TEXT NOT NULL,                     -- ISO8601 UTC timestamp of publication
    created_at TEXT NOT NULL                        -- ISO8601 UTC timestamp of record creation
);

CREATE INDEX IF NOT EXISTS idx_published_posts_genre ON published_posts(genre);
CREATE INDEX IF NOT EXISTS idx_published_posts_prompt ON published_posts(prompt_version);
CREATE INDEX IF NOT EXISTS idx_published_posts_published_at ON published_posts(published_at);
CREATE INDEX IF NOT EXISTS idx_published_posts_run_id ON published_posts(run_id);

-- Metric Snapshots: Time-series performance windows (24h, 72h, 7d, 30d)
CREATE TABLE IF NOT EXISTS metric_snapshots (
    snapshot_id TEXT PRIMARY KEY,                   -- UUID4 string
    post_id TEXT NOT NULL,                          -- Foreign Key to published_posts.post_id
    window_label TEXT NOT NULL,                     -- '24h', '72h', '7d', '30d'
    views INTEGER NOT NULL DEFAULT 0,               -- Total view count (or Reel plays)
    reach INTEGER NOT NULL DEFAULT 0,               -- Unique accounts reached
    likes INTEGER NOT NULL DEFAULT 0,               -- Total likes
    comments INTEGER NOT NULL DEFAULT 0,            -- Total comments
    shares INTEGER NOT NULL DEFAULT 0,              -- Total shares (vital algorithmic signal)
    saves INTEGER NOT NULL DEFAULT 0,               -- Total saves / bookmarks
    avg_view_duration_sec REAL NOT NULL DEFAULT 0.0,-- Mean seconds watched
    avg_view_pct REAL NOT NULL DEFAULT 0.0,         -- Mean percentage watched (e.g., 78.5%)
    hook_hold_3s_pct REAL NOT NULL DEFAULT 0.0,     -- % of viewers still watching at 3.0s
    skip_rate_pct REAL NOT NULL DEFAULT 0.0,        -- % of viewers who swiped away before 3.0s
    retention_curve_json TEXT,                      -- 10-bucket array: '[100, 78, 65, 58, 52, 48, 45, 42, 40, 38]'
    ingestion_source TEXT NOT NULL,                 -- 'youtube_api', 'instagram_graph_api', 'manual_entry'
    captured_at TEXT NOT NULL,                      -- ISO8601 UTC timestamp of metric fetch
    FOREIGN KEY(post_id) REFERENCES published_posts(post_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_post_window ON metric_snapshots(post_id, window_label);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_captured ON metric_snapshots(captured_at);
```

---

## 6. Decision 3 — 15-Post Cohort Evaluation Cadence & Diagnostic Matrix

### 6.1 The 15-Post Cohort Freeze Rule
To eliminate stochastic algorithmic noise:
1. When a new `prompt_version` (e.g., `v1.2.0`) or `playbook_version` (e.g., `director-v2.0`) is deployed, it is **frozen** for at least **15 consecutive published posts** within that genre.
2. No prompts, temperature settings, or few-shot examples may be adjusted during the active cohort.
3. At the conclusion of the 15th post’s 72-hour window, the Cohort Evaluator calculates cohort aggregates:
   - Cohort Mean Hook Hold % ($\mu_{\text{hook}}$)
   - Cohort Mean View % ($\mu_{\text{view}}$)
   - Cohort Mean Shares per 1k views ($\mu_{\text{shares}}$)
   - Cohort Mean Human Edit % ($\mu_{\text{human}}$)

### 6.2 The Diagnostic Decision Matrix

When cohort averages fail to meet target retention benchmarks, the system prescribes explicit, targeted interventions. Engineers must not guess where to make edits:

| Observed Symptom | Threshold Failure | Root Cause Subsystem | Mandatory Engineering Action |
| :--- | :--- | :--- | :--- |
| **Weak 0–3s Retention** | $\mu_{\text{hook}} < 55.0\%$ | `prompts/director.md`<br>`gaming_clips/audio.py` | 1. Ban introductory filler words; mandate concrete visual pattern interrupt within first 1.5s.<br>2. In gaming clips, trim leading audio silence/buildup by 1.2s prior to the scream/decibel spike. |
| **Mid-Video Viewer Drop** | $\mu_{\text{view}} < 70.0\%$ | `prompts/editor_cuts.md`<br>FFmpeg Filtergraph | 1. Increase cut density: enforce visual transition every 2.5–3.5s (down from 5.0s).<br>2. Shorten target script duration from 55s to 38–42s.<br>3. Introduce b-roll/zoom cuts at the 50% duration mark. |
| **Low Share / Save Ratio** | $\mu_{\text{shares}} < 5.0\text{ per 1k}$ | `prompts/content_intelligence.md`<br>Lore Ranker | 1. Raise evidence novelty filter: require at least 1 benchmark or contrarian stat.<br>2. In gaming clips, raise lore relevance threshold so only high-context channel inside jokes are selected. |
| **High Editor Friction** | $\mu_{\text{human}} > 50.0\%$ | Stage 2 Script Generator | 1. Human editor is rewriting $> 50\%$ of the AI script.<br>2. Extract git diff between raw AI script and final published script; run `prompt-eval-auditor` to update few-shot prompt examples with the editor's preferred cadence. |

### 6.3 The 50+ Post Milestone: Lightweight Local Tabular ML Hook Scorer
Once $\ge 50$ posts with stable 72-hour metric snapshots have accumulated in `content_factory.db`:
- The system trains a compact, offline tabular model (e.g., `LightGBM` or `scikit-learn` `RidgeClassifier`) on CPU.
- **Engineered Features ($< 20$ numerical features):**
  - Hook character and word count.
  - Sentiment polarity & subjectivity (`textblob` / lightweight VADER).
  - Presence of numbers, percentages, or dollar signs (`has_numeric_stat`).
  - Question hook vs contrarian statement (Boolean).
  - Initial 1D audio decibel peak ratio (for gaming clips).
  - Target video duration in seconds.
- **Target Variable:** Binary classification: Will post achieve $\text{avg\_view\_pct} \ge 75\%$?
- **Operational Integration:** Runs during candidate generation in Stage 2 / G1 in $< 15\text{ ms}$ on CPU, rejecting weak candidate hooks *before* spending downstream generation tokens or FFmpeg render time.

---

## 7. Decision 4 — Streamlit Retention & ROI Operations Dashboard

Adhering strictly to ADR-001 (`ServiceClient` facade + `@st.fragment`), a dedicated **Retention & Audience Analytics** tab is integrated into the Streamlit Operations Hub:

```
+--------------------------------------------------------------------------------------------------+
| Streamlit Operations Hub: Retention & Audience ROI (Fragment)                                    |
+--------------------------------------------------------------------------------------------------+
| [Active Cohort: v1.2.0 (Post 12/15)]  [Mean 3s Hold: 64.2% (PASS)]  [Audience ROI: 142 hrs / $]   |
| [===============================================>          ] 80% Cohort Completion               |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
| 10-Bucket Retention Curve (Mean vs Benchmark)          Cohort Performance Summary (72h Window)   |
| 100% | \                                               +---------------------------------------+ |
|  80% |  \--- v1.2.0 (Current: 74%)                     | Prompt Ver   Posts  AvgView%  Shares  | |
|  60% |   \---- Benchmark Target (70%)                  | v1.2.0 (Act) 12     74.2%     8.4/1k  | |
|  40% |    \--- v1.1.0 (Prior: 58%)                     | v1.1.0 (Old) 15     62.1%     4.1/1k  | |
|   0% +----------------------------------------         | v1.0.0 (Old) 15     55.8%     2.8/1k  | |
|      0%  20%  40%  60%  80% 100% Video Duration        +---------------------------------------+ |
+--------------------------------------------------------------------------------------------------+
```

### 7.1 Read-Only SQLite & Facade Hygiene
- **UI Facade Methods on `ServiceClient`:**
  - `get_active_cohort_summary(genre: str) -> CohortSummary`
  - `get_retention_curve_comparison(prompt_version_a: str, prompt_version_b: str) -> RetentionCurveData`
  - `get_post_roi_breakdown(limit: int = 50) -> list[PostROIRow]`
- **Render Hygiene:** Querying occurs through read-only SQLite connections; zero DDL or schema checks inside the render path.
- **MCP Compatibility:** Because `data/content_factory.db` follows standard SQLite schema conventions, the database can be queried directly by AI assistants using the read-only `sqlite` MCP for ad-hoc retention audits.

---

## 8. Consequences & Trade-Offs

### Positive Consequences
- **Eliminates Prompt Thrashing:** Protects the engineering team from chasing algorithmic noise by enforcing the 15-post cohort freeze.
- **Closed-Loop Engineering:** Directly attributes viewer retention and watch time back to exact prompt versions, visual cut densities, and token costs.
- **Zero Ongoing Cloud SaaS Costs:** Uses free official platform APIs and local SQLite storage; zero recurring monthly software subscriptions.
- **Local Host Compatibility:** Lightweight SQL analytics and tabular models consume $< 50\text{ MB}$ RAM, fully respecting the 8 GB host ceiling.

### Negative Consequences & Mitigations
- **Delayed Feedback Latency:** Algorithmic metrics take 24–72 hours to stabilize, meaning prompt iterations require days rather than minutes.
  - *Mitigation:* This is an unavoidable reality of social platform distribution. Pre-publication evaluation (`prompt-eval-auditor` ADR-004) catches syntax, clichés, and grounding errors immediately; post-publication metrics measure true audience resonance.
- **Manual Logging Burden Before API Verification:** Entering metrics manually via CLI requires 30 seconds per post.
  - *Mitigation:* The CLI command `python -m content_creation.cli metrics log` is streamlined with smart defaults to minimize friction.

---

## 9. Phased Implementation Hooks

| Phase | Module / Target | Implementation Hook |
| :--- | :--- | :--- |
| **Phase 2C** | `src/content_creation/core/db/` | Add `create_retention_metrics_schema(conn)` to consolidated SQLite migration in `data/content_factory.db` per ADR-003. |
| **Phase 3B** | `src/content_creation/analytics/ingest.py` | Implement `YouTubeAnalyticsClient` and `InstagramInsightsClient` with rate-limited cron execution. |
| **Phase 3B** | `src/content_creation/cli/commands/metrics.py` | Implement `cli metrics log` command for manual entry fallback. |
| **Phase 3B** | `src/content_creation/ui/views/retention_roi.py`| Implement Streamlit Retention & Audience ROI dashboard fragment using `ServiceClient`. |
| **Phase G3** | `src/content_creation/analytics/ml_scorer.py` | Implement 50+ post tabular LightGBM pre-scorer for candidate hooks. |

---

## 10. Compliance & Verification Checklist

Before completing tasks implementing this ADR, verify:
- [ ] **2026 Meta API Compliance:** Zero queries request deprecated Instagram fields (`impressions`, `plays`, `clips_replays_count`).
- [ ] **Secret Hygiene:** OAuth client secrets and refresh tokens are loaded strictly from environment variables and never logged or committed.
- [ ] **Zero UI DDL:** Streamlit retention dashboard queries read-only SQL via `ServiceClient`; zero DDL inside render loops.
- [ ] **Full Lineage Integrity:** Every record in `published_posts` references valid `run_id`, `prompt_version`, and `shadow_cost_usd` values from ADR-004.
- [ ] **Offline Testing:** Unit tests in `tests/test_retention_metrics.py` run 100% offline using `tmp_path` and synthetic JSON payloads.
