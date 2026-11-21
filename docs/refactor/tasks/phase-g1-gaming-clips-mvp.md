# Task Specification: Phase G1 — Gaming Clips Tracer-Bullet MVP

- **Phase ID:** `G1-gaming-clips-mvp`
- **Target Branch:** `feat/phase-g1-gaming-clips-mvp` branched from `main`
- **Prerequisites:** `Phase 2A merged into main` (Commit `b09f85b`)
- **Applicable Workspace Skills:**
  - `.agents/skills/windows-python-hygiene/SKILL.md`
  - `.agents/skills/security-and-cost-guard/SKILL.md`
  - `.agents/skills/langgraph-pydanticai-patterns/SKILL.md`
- **Associated Architecture Decision Record:**
  - `docs/refactor/adrs/002-multi-genre-studio-and-gaming-clips.md`

---

## 1. Governance & Explicit Scope Unfreezes (`AGENTS.md` §14)

- **Frozen Paths Evaluation:**
  - `src/content_creation/models/`: **NOT TOUCHED** (Strictly frozen; zero modification to educational models).
  - `src/content_creation/generation/`: **NOT TOUCHED** (Strictly frozen; all educational brief, script, and carousel generators untouched).
  - `prompts/`: **NOT TOUCHED** (Strictly frozen; all prompt templates untouched).
  - `docs/schema.md`: **NOT TOUCHED** (Strictly frozen; data contracts unchanged).
- **Domain Isolation Boundary:**
  - All new gaming clipping models, detectors, transcribers, renderers, and services are strictly encapsulated under `src/content_creation/domains/gaming_clips/`.
- **Secondary Channel Preservation Invariant:**
  - Explicit confirmation that `newsletter` (`src/content_creation/models/newsletter.py`, `src/content_creation/generation/newsletter.py`, `prompts/newsletter.md`) and `linkedin_post` (`prompts/linkedin_post.md`) are preserved **100% intact**.
  - All existing educational UI pages (`1_topic_collection.py` through `6_operations_dashboard.py`) remain completely unchanged and operational.

---

## 2. Objective & Defect Resolution Scope

Phase G1 delivers the **Tracer-Bullet MVP (v0)** for the new Gaming / Streamer Clipping vertical in `Content-Creation-Automation`. It establishes the multi-genre studio pattern on top of shared platform infrastructure (WAL-mode SQLite, job queue, lock manager, review state machine) and implements the **Coarse-to-Fine 4-Signal Multimodal Funnel** under strict low-config PC resource constraints ($\le 2\text{ GB}$ peak RAM, CPU-only execution, zero full-VOD 1080p downloads):

1. **Home Page Genre Router (`FEAT-G01`):**
   - Provide a seamless studio selector on the Streamlit dashboard (`Educational Content Studio` | `Gaming Clips Studio`) in `src/content_creation/ui/app.py` and a dedicated UI page `src/content_creation/ui/pages/7_gaming_clips.py`.
   - Preserve all existing educational dashboard controls and views without regression.

2. **Coarse-to-Fine Multimodal Candidate Detection (`FEAT-G02`):**
   - **Signal 1 (Chat Spike Detector):** Parse Twitch/YouTube timestamped chat replays to calculate rolling 30s message velocity and emote intensity ($Z > 2.5$).
   - **Signal 2 (Audio Energy & Facecam Clamping):** Analyze coarse audio decibels/RMS to confirm reaction peaks, pairing with sparse keyframe facecam bounding box clamping to eliminate shaky auto-crop camera motion.
   - **Signal 3 (Targeted `faster-whisper` `int8` CPU Transcriber):** Transcribe only shortlisted 30–90s candidate audio slices on CPU to extract word-level timestamps without transcribing the full VOD.
   - **Signal 4 (Streamer Lore & Virality Scoring):** Evaluate candidate narrative and hook punchlines using a structured `StreamerProfile` and PydanticAI narrative schema.

3. **Low-Resource Fetching & Vertical Rendering (`FEAT-G03`):**
   - **Section Fetcher (`yt-dlp` Wrapper):** Ingest VOD metadata/chat first, downloading only shortlisted video sections (`yt-dlp --download-sections "*MM:SS-MM:SS"`), saving tens of gigabytes of disk space and bandwidth.
   - **SSRF URL Guard:** Enforce `.agents/skills/security-and-cost-guard/SKILL.md` URL validation, rejecting private/loopback IP addresses (`127.0.0.0/8`, `::1`, `169.254.169.254`).
   - **Deterministic FFmpeg Command Builder:** Build single-worker vertical 9:16 filtergraphs (facecam box top, gameplay bottom, ASS subtitle overlay) with explicit `-threads 2` CPU safety.

- **Features & Drift Resolved:**
  - `FEAT-G01`: Multi-genre UI routing without breaking educational studio.
  - `FEAT-G02`: Low-resource coarse-to-fine candidate detection.
  - `FEAT-G03`: Targeted section fetching and bounded FFmpeg rendering.
  - Windows hygiene compliance (`encoding="utf-8"`, atomic writes, subprocess safety).

---

## 3. Atomic Commit Plan

Ordered, single-concern commits to be executed sequentially by `refactor-executor`:

### Commit 1: `feat(gaming-clips): core domain models, protocols, and chat spike detection`
- **Files to Touch:**
  - `src/content_creation/domains/gaming_clips/__init__.py` (Package exports)
  - `src/content_creation/domains/gaming_clips/models.py` (Pydantic v2 domain schemas: `ChatMessage`, `ClipCandidate`, `StreamerProfile`, `GameLoreContext`, `RenderSpec`, `ClipReviewStatus`)
  - `src/content_creation/domains/gaming_clips/chat_detector.py` (Rolling window message velocity, hype emote weighting, rolling mean/stddev Z-score calculation, cluster merging)
  - `tests/test_gaming_chat_detector.py` (Mocked Twitch/YouTube chat replay fixtures, Z-score boundary verification, cluster merging assertions)
- **Feature IDs Addressed:** `FEAT-G02`
- **Acceptance Criteria:**
  - `chat_detector.py` processes timestamped chat messages and flags peaks where $Z \ge 2.5$.
  - Adjacent peak windows within 20 seconds are merged into candidate clip clusters between 30 and 90 seconds.
  - Zero external network calls required; 100% offline deterministic test suite in `tests/test_gaming_chat_detector.py`.
  - All file I/O operations pass explicit `encoding="utf-8"`.

### Commit 2: `feat(gaming-clips): audio energy detector and targeted section fetcher`
- **Files to Touch:**
  - `src/content_creation/domains/gaming_clips/audio_detector.py` (Stream-chunked RMS decibel calculation, vocal burst detection, sparse keyframe facecam bounding box clamping model)
  - `src/content_creation/domains/gaming_clips/section_fetcher.py` (`yt-dlp` wrapper protocol using `--download-sections` and `--write-subs`; SSRF URL validation blocking private IPs and loopback addresses)
  - `tests/test_gaming_audio_detector.py` (Synthetic WAV audio peak fixtures, RMS volume threshold tests, bounding box clamping stability)
  - `tests/test_gaming_section_fetcher.py` (URL SSRF validation tests, `yt-dlp` command-line argument verification with mocked subprocess)
- **Feature IDs Addressed:** `FEAT-G02`, `FEAT-G03`
- **Acceptance Criteria:**
  - `audio_detector.py` calculates RMS energy in memory chunks $< 30\text{ MB}$ RAM and filters candidate clips lacking audio peak confirmation.
  - Facecam box heuristic clamps bounding box coordinates statically across clip duration without jitter.
  - `section_fetcher.py` rejects invalid protocols and private IP ranges (`http://127.0.0.1`, `http://169.254.169.254`, `http://10.0.0.1`).
  - Unit tests verify `yt-dlp` is invoked with `--download-sections "*start-end"` rather than full-VOD downloads.

### Commit 3: `feat(gaming-clips): targeted whisper transcript adapter and ffmpeg builder`
- **Files to Touch:**
  - `src/content_creation/domains/gaming_clips/transcriber.py` (`faster-whisper` `int8` CPU transcription adapter with fallback mock protocol, word-level timestamp generation, punctuation boundary detection)
  - `src/content_creation/domains/gaming_clips/ffmpeg_builder.py` (Deterministic FFmpeg filtergraph builder for vertical 9:16 layout: facecam crop top, gameplay crop/pad bottom, word-by-word subtitle burn, with `-threads 2` flag)
  - `tests/test_gaming_transcriber.py` (Mocked Whisper transcript fixtures, word timestamp slicing, sentence boundary alignment)
  - `tests/test_gaming_ffmpeg_builder.py` (Unit tests verifying filtergraph syntax, vertical dimensions `1080x1920`, thread caps, audio normalization flags)
- **Feature IDs Addressed:** `FEAT-G02`, `FEAT-G03`
- **Acceptance Criteria:**
  - `transcriber.py` operates strictly on sliced candidate audio (duration $\le 90\text{s}$) with `int8` compute type.
  - `ffmpeg_builder.py` produces deterministic CLI argument lists without invoking shell strings (`shell=False` Windows safety).
  - Filtergraph creates valid 1080x1920 layout and formats ASS subtitle timing accurately.
  - Tests pass 100% offline without requiring pre-installed FFmpeg binary or CUDA runtime.

### Commit 4: `feat(gaming-clips): CLI commands, UI genre router, and studio page`
- **Files to Touch:**
  - `src/content_creation/domains/gaming_clips/service.py` (`GamingClipsService` orchestrating the 4-signal funnel, candidate persistence in `data/gaming_clips/`, and job queue interaction)
  - `src/content_creation/cli/gaming.py` (Typer command group: `content-creation clips detect`, `clips render`, `clips list`)
  - `src/content_creation/cli/__init__.py` (Register `register_gaming_commands(app)`)
  - `src/content_creation/ui/app.py` (Add Home Page Genre Router toggle between Educational Content Studio and Gaming Clips Studio)
  - `src/content_creation/ui/pages/7_gaming_clips.py` (Streamlit page for Streamer URL input, candidate gallery review, vertical preview, and render queue)
  - `tests/test_gaming_cli.py` (Typer `CliRunner` tests for `clips --help`, `clips detect`, `clips list`)
  - `tests/test_gaming_ui.py` (Streamlit `AppTest` verifying genre switching, zero crashing on missing files, and clean rendering)
- **Feature IDs Addressed:** `FEAT-G01`, `FEAT-G02`, `FEAT-G03`
- **Acceptance Criteria:**
  - Running `content-creation clips --help` displays all subcommands with accurate help text.
  - Switching between `Educational Content Studio` and `Gaming Clips Studio` on the Home Page toggles views cleanly without state leakage.
  - All existing educational pages and tests pass without regression.
  - Streamlit UI interacts with backend strictly via `GamingClipsService` facade (zero direct SQLite DDL or unhandled exceptions in UI).

---

## 4. Strict File Allowlist

### 4.1 Existing Files to Modify (Strictly 2 files)
- `src/content_creation/cli/__init__.py` (Register Typer gaming command group)
- `src/content_creation/ui/app.py` (Add Home Page Genre Router selector)

### 4.2 New Files to Create (Domain-Named Only)
- **Domain Package (`src/content_creation/domains/gaming_clips/`):**
  - `src/content_creation/domains/gaming_clips/__init__.py`
  - `src/content_creation/domains/gaming_clips/models.py`
  - `src/content_creation/domains/gaming_clips/chat_detector.py`
  - `src/content_creation/domains/gaming_clips/audio_detector.py`
  - `src/content_creation/domains/gaming_clips/section_fetcher.py`
  - `src/content_creation/domains/gaming_clips/transcriber.py`
  - `src/content_creation/domains/gaming_clips/ffmpeg_builder.py`
  - `src/content_creation/domains/gaming_clips/service.py`
- **CLI & UI Entrypoints:**
  - `src/content_creation/cli/gaming.py`
  - `src/content_creation/ui/pages/7_gaming_clips.py`
- **Deterministic Domain Test Suites (`tests/`):**
  - `tests/test_gaming_chat_detector.py`
  - `tests/test_gaming_audio_detector.py`
  - `tests/test_gaming_section_fetcher.py`
  - `tests/test_gaming_transcriber.py`
  - `tests/test_gaming_ffmpeg_builder.py`
  - `tests/test_gaming_cli.py`
  - `tests/test_gaming_ui.py`

### 4.3 Files to Delete / Retire
- **None.** (Zero files deleted).

### 4.4 Prohibited File Names (Anti-Drift Guardrail)
- **Prohibited:** Phase-named test files (e.g., `tests/test_phase_g1.py`, `tests/test_gaming_mvp.py`, `tests/test_g1_refactor.py`).
- **Prohibited:** Generic or ambiguous script files in repo root (e.g., `clip.py`, `run_gaming.py`).
- All tests must strictly follow the domain module naming scheme (`tests/test_gaming_<subsystem>.py`).

---

## 5. Explicit Out-of-Scope / Deferred Items

The following items are strictly forbidden on this branch to prevent scope creep:
- [ ] **No Live Stream Real-Time Daemon:** Real-time RTMP stream capturing or live bot scraping during active broadcasts is deferred to Phase G2.
- [ ] **No Dense Optical Flow or Continuous Face Tracking:** Heavy frame-by-frame deep learning trackers (YOLOv8, MediaPipe continuous mesh) are strictly deferred.
- [ ] **No Direct Social Media API Auto-Publishing:** Direct OAuth publishing to TikTok, YouTube Shorts, or Instagram Reels APIs is deferred; output files are rendered to disk for human operator sign-off.
- [ ] **No CUDA / GPU Acceleration Requirements:** Implementation must operate 100% on CPU; optional CUDA acceleration toggles are deferred to Phase G2.
- [ ] **No Multi-Container Plumbing:** No Docker, Kubernetes, Celery, or Redis dependencies (`AGENTS.md` §6.1). Execution remains local and in-process.

---

## 6. Required Verification Gates (Zero-Trust)

`contract-verifier` and `qa-test-engineer` will validate against these explicit gates before signaling completion:

1. **Gate 1: Scope Compliance:**
   - Git diff inspection confirms modifications are strictly confined to the 2 existing files and 10 new `src/` files listed in §4.
   - Zero modifications to `src/content_creation/models/`, `generation/`, `prompts/`, or `docs/schema.md`.
   - Secondary educational formats (`newsletter`, `linkedin_post`) confirmed 100% untouched.

2. **Gate 2: Static Typing Ratchet (`mypy --strict`):**
   - Command:
     ```powershell
     uv run mypy src/content_creation/domains/gaming_clips src/content_creation/cli/gaming.py --strict
     ```
   - Expected: 0 errors. Baseline error count on untouched files must not increase.

3. **Gate 3: AST Layer-Violation & Windows Hygiene Check:**
   - Layer check: Zero imports of `src/content_creation/ui/` inside `src/content_creation/domains/gaming_clips/`.
   - Windows hygiene: Every `open()`, `Path.read_text()`, and `Path.write_text()` in touched files has explicit `encoding="utf-8"`.
   - Zero hardcoded `bash` or `sh` subprocess invocations (`.agents/skills/windows-python-hygiene/SKILL.md`).

4. **Gate 4: Targeted & Baseline Test Suites:**
   - Targeted gaming suite:
     ```powershell
     uv run python -m pytest tests/test_gaming_*.py -v
     ```
     Expected: 100% passing tests.
   - Baseline regression check:
     ```powershell
     uv run python -m pytest --tb=no -q
     ```
     Expected: Passing test count must not decrease compared to the pre-branch baseline.

5. **Gate 5: Real Runtime Verification Check:**
   - Typer CLI command verification:
     ```powershell
     uv run python -m content_creation.cli clips --help
     ```
   - Streamlit headless render check:
     ```powershell
     uv run python -m pytest tests/test_gaming_ui.py -v
     ```

---

## 7. Orchestrator Chain Directive

The `phase-orchestrator` must execute this specification using the standard sequential lifecycle:
1. `refactor-executor` implements Commits 1 through 4 on feature branch `feat/phase-g1-gaming-clips-mvp`.
2. `contract-verifier` audits the tree against Gates 1 through 5 (halts if BLOCK).
3. `error-taxonomy-chronicler` harvests any observed errors or unexpected exceptions.
4. `qa-test-engineer` runs comprehensive boundary checks, fault injection (corrupt chat JSON, zero-length audio, SSRF attacks), and confirms offline test determinism.
5. Final taxonomy sync.
6. Halt for human review — **DO NOT MERGE TO MAIN, DO NOT PUSH REMOTE**.
