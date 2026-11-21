# ADR 005: Low-Spec Media Execution Budget, Subprocess Isolation & Ephemeral Disk Lifecycle

- **Status:** PROPOSED
- **Date:** 2026-11-21
- **Deciders:** `spec-architect`, `phase-orchestrator`
- **Target Phase:** Phase G1 / Phase G2 (`gaming_clips` & Multimodal Media Pipelines)
- **Consulted:** `.agents/skills/performance-optimization/SKILL.md`, `.agents/skills/windows-python-hygiene/SKILL.md`, `docs/refactor/adrs/002-multi-genre-studio-and-gaming-clips.md`, `docs/refactor/adrs/003-single-wal-sqlite-database.md`

---

## 1. Context & Problem Statement

The `Content-Creation-Automation` platform is expanding from text/editorial synthesis into automated multimodal gaming highlight clipping (Phase G1/G2 per ADR-002). This vertical requires ingesting multi-hour stream VODs (Twitch, YouTube Gaming, Kick), performing audio energy analysis, extracting timestamped chat replays, transcribing speech with word-level timestamps (`faster-whisper`), and rendering vertical 9:16 highlight shorts with karaoke subtitles via `ffmpeg`.

However, executing heavy multimodal workloads on personal creator hardware presents severe stability and operating system resource bottlenecks:

### 1.1 The Host Hardware Ceiling
The target development, testing, and production workstation is strictly bounded:
- **CPU:** AMD Ryzen 5 7600X (6 physical cores / 12 threads @ 4.7 GHz base)
- **RAM:** **8 GB DDR5** total physical memory
- **Operating System:** Windows 11 (64-bit)
- **Available RAM Headroom:** Windows 11 base system services, desktop window manager (`dwm.exe`), IDE/terminal, and background browser tabs consume **5.5–6.0 GB RAM**. This leaves only **~2.0–2.5 GB of usable physical memory headroom** for all Python processes, workers, and subprocesses combined.
- **Storage:** 256 GB NVMe SSD with limited free disk capacity (~20–40 GB typically free).

### 1.2 The Failure Modes of Naive Media Pipelines
Under this hardware baseline, standard media pipeline architectures induce immediate fatal crashes:
1. **Out-of-Memory (OOM) Crashes and Pagefile Thrashing:**
   - Loading standard ML libraries (PyTorch, Whisper, Torchaudio, OpenCV) inside a long-running Streamlit process pushes resident set size (RSS) past 3 GB.
   - When RAM is exhausted, Windows begins aggressive pagefile swapping to the NVMe SSD (`pagefile.sys`). System latency spikes from milliseconds to seconds, GUI applications freeze, and CPython aborts with `MemoryError` or `[WinError 1455] The paging file is too small for this operation to complete`.
2. **CPython Memory Fragmentation and Non-Reclamation:**
   - CPython’s native `pymalloc` allocator manages small object heaps (`<= 512 bytes`). When large audio/video arrays or neural network weights are loaded and subsequently deleted in Python (`del model; gc.collect()`), memory arenas are often retained by the process heap and never returned to the Windows NT virtual memory manager. Over repeated tasks, a single Python worker slowly bloats until it crashes.
3. **Streamlit Thread Poisoning & UI Freezes:**
   - Executing blocking media tasks (`yt-dlp` download, `faster-whisper` inference, or `ffmpeg` rendering) directly inside Streamlit script evaluation threads or callbacks locks the Streamlit WebSocket heartbeats, triggering client disconnects (`Connection timed out`), browser tab crashes, and UI rendering stalls.
4. **Catastrophic Disk Exhaustion:**
   - Downloading full 4–8 hour 1080p stream VODs requires 15–30 GB per stream. Running 2–3 runs without aggressive stage-by-stage auto-purging fills the 256 GB SSD, crashing both the database and the Windows operating system.

---

## 2. Decision Drivers

- **Deterministic $\le 2.0\text{ GB}$ Peak RAM Ceiling:** The entire media processing pipeline must never exceed 2.0 GB peak resident memory across all concurrent processes, preserving system headroom and preventing pagefile swapping.
- **Strict Ephemeral Disk Footprint ($\le 500\text{ MB}$ Active):** The active disk footprint for any ongoing clipping run must remain $\le 500\text{ MB}$, enforcing byte-range section downloading and immediate stage-by-stage artifact purging.
- **Subprocess Isolation for Guaranteed Memory Reclamation:** Heavy compute stages must execute as independent short-lived subprocesses. When the subprocess terminates, the Windows kernel unconditionally reclaims 100% of allocated physical and virtual memory.
- **Asynchronous, Non-Blocking UI Architecture:** Streamlit must never run media inference inline; it functions strictly as a human review UI that enqueues jobs into `data/content_factory.db` and polls status.
- **Windows-First Subprocess & Audio Hygiene:** Adhere to `.agents/skills/windows-python-hygiene/SKILL.md` (no `shell=True`, explicit `encoding="utf-8"`, `sys.executable`, atomic file replacement, and Windows process priority classes).
- **Graceful Desktop Interactivity:** Background media operations must not hijack all 12 CPU threads; background workers must run with `BELOW_NORMAL_PRIORITY_CLASS` and capped thread counts.

---

## 3. Architecture Overview

```
+--------------------------------------------------------------------------------------------------+
| STREAMLIT UI TIER (src/content_creation/ui/views/7_gaming_clips.py)                              |
| - Read-only job status polling via ServiceClient & @st.fragment                                  |
| - Action buttons: Enqueue Clip Job -> INSERT INTO jobs (status='PENDING') in content_factory.db   |
+--------------------------------------------------+-----------------------------------------------+
                                                   | SQLite Job Queue
                                                   v
+--------------------------------------------------------------------------------------------------+
| BACKGROUND CLI WORKER (run_worker.py)                                                            |
| - Polls jobs table; acquires cooperative lease via locks table (ADR-003)                        |
| - Coordinates Sequential Single-Stage Execution Pipeline                                         |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                     +-----------------------------+-----------------------------+
                     | Pre-flight Disk Guard: shutil.disk_usage() >= 5.0 GB Free |
                     +-----------------------------+-----------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| STAGE 1: Chat Spike & Metadata Ingestion                                                        |
| - Subprocess: python -m content_creation.gaming_clips.ingest                                     |
| - Memory Budget: <= 150 MB RSS | Input: VOD URL | Output: chat_spikes.json                        |
| - Subprocess terminates -> 100% RAM reclaimed by OS                                              |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| STAGE 2: Audio Extraction & Peak Detection                                                       |
| - Subprocess: ffmpeg extracts 16kHz mono WAV (audio only)                                        |
| - Subprocess: python -m content_creation.gaming_clips.audio_peaks (chunked streaming)            |
| - Memory Budget: <= 120 MB RSS | Output: candidate_windows.json (30-90s slices)                   |
| - Subprocess terminates -> 100% RAM reclaimed by OS                                              |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| STAGE 3: Targeted Speech Transcription & Word Timestamps                                         |
| - Subprocess: python -m content_creation.gaming_clips.transcribe                                 |
| - faster-whisper int8 CPU (cpu_threads=4, num_workers=1, vad_filter=True)                        |
| - Transcribes ONLY shortlisted candidate audio windows (never full VOD)                          |
| - Memory Budget: <= 1.1 GB RSS | Output: transcripts.json                                        |
| - AUTO-PURGE: Delete intermediate full-stream mono WAV immediately!                              |
| - Subprocess terminates -> 100% RAM reclaimed by OS                                              |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| STAGE 4: Section Video Download (yt-dlp --download-sections)                                     |
| - Subprocess: yt-dlp fetches ONLY top-ranked 30-90s video slices                                 |
| - Memory Budget: <= 100 MB RSS | Output: raw_slice_<id>.mp4 (~40-80 MB each)                     |
| - Subprocess terminates -> 100% RAM reclaimed by OS                                              |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| STAGE 5: Vertical 9:16 Video Rendering & Karaoke Subtitling                                      |
| - Sequential Render Queue: Process one clip at a time!                                           |
| - Subprocess: ffmpeg (-threads 2, libx264, preset veryfast, crf 23)                              |
| - Memory Budget: <= 500 MB RSS | Output: final_clip_<id>.mp4 (15-30 MB)                          |
| - AUTO-PURGE: Delete raw_slice_<id>.mp4 immediately after its 9:16 render completes!            |
| - Subprocess terminates -> 100% RAM reclaimed by OS                                              |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
| STAGE 6: Run Completion & Telemetry Logging                                                      |
| - Record execution metrics (peak RAM, latency, disk freed) into media_execution_ledger           |
| - Final Active Disk Footprint: <= 100 MB (final vertical MP4s + JSON metadata only)              |
+--------------------------------------------------------------------------------------------------+
```

---

## 4. Decision 1 — Subprocess Isolation & $\le 2.0\text{ GB}$ Peak RAM Ceiling

### 4.1 The Process Boundary Isolation Principle
To solve CPython's memory fragmentation and retention issues:
- **Zero Heavy In-Process Libraries in UI or Long-Running Daemons:** The Streamlit process and the root CLI orchestrator must never import `torch`, `faster_whisper`, `librosa`, or `cv2`.
- **Sequential One-Stage Subprocesses:** Heavy stages execute via discrete Python invocations:
  `[sys.executable, "-m", "content_creation.gaming_clips.<stage_module>", ...]`.
- **Guaranteed OS Reclamation:** When each stage subprocess completes, the Windows NT kernel tears down the process address space, unmaps virtual pages, and returns physical RAM to the OS instantly.

### 4.2 Prohibiting Inline Execution in Streamlit
Running FFmpeg or Whisper inline in Streamlit is strictly prohibited:
```python
# FORBIDDEN (Directly violates ADR-001 and ADR-005):
def on_generate_clips_clicked():
    model = WhisperModel("base", device="cpu")  # Crashes Streamlit with OOM
    result = model.transcribe("stream.wav")
    render_video(result)

# MANDATED:
def on_generate_clips_clicked():
    # Enqueue job in SQLite; UI stays 100% responsive
    service_client.enqueue_clip_generation_job(vod_url=vod_url, title=title)
    st.success("Clipping job enqueued. Progress will update automatically.")
```

### 4.3 Per-Stage Memory Budgets

Each pipeline stage operates under an explicit, enforceable resident memory budget:

| Stage Identifier | Primary Tools | Execution Method | Peak RSS Budget | Invariant / Boundary Rule |
| :--- | :--- | :--- | :---: | :--- |
| **Stage 1: Ingest & Chat** | `requests`, `json` | Subprocess | **$\le 150\text{ MB}$** | Stream chat events line-by-line; calculate rolling Z-scores in fixed arrays. |
| **Stage 2: Audio Peaks** | `ffmpeg`, `wave`, `numpy` | Subprocess | **$\le 120\text{ MB}$** | Read 16kHz audio in 64 KB chunks; never load full WAV into NumPy. |
| **Stage 3: Whisper STT** | `faster-whisper` (`int8`) | Subprocess | **$\le 1,100\text{ MB}$** | Transcribe only shortlisted candidate windows; release model on completion. |
| **Stage 4: Slice Download**| `yt-dlp` | Subprocess | **$\le 100\text{ MB}$** | Use `--download-sections` for selected 30–90s ranges; zero full VOD downloads. |
| **Stage 5: 9:16 Render** | `ffmpeg` | Subprocess | **$\le 500\text{ MB}$** | Single sequential render queue; `-threads 2`; one clip at a time. |
| **Combined Maximum** | System Peak | Sequential | **$\le 1,100\text{ MB}$** | **Total RAM headroom maintained $\ge 1.0\text{ GB}$ at all times.** |

---

## 5. Decision 2 — Ephemeral Disk Budget & Auto-Purge Lifecycle ($\le 500\text{ MB}$ Active Footprint)

### 5.1 Pre-Flight Disk Guard
Before creating any directories or launching child processes, the worker verifies that host disk headroom is safe:
```python
import shutil
from pathlib import Path
from content_creation.core.exceptions import InsufficientDiskSpaceError

def assert_disk_headroom(target_path: Path, min_free_gb: float = 5.0) -> None:
    """Ensure host has at least min_free_gb free space before processing."""
    total, used, free = shutil.disk_usage(target_path)
    free_gb = free / (1024 ** 3)
    if free_gb < min_free_gb:
        raise InsufficientDiskSpaceError(
            f"Host disk space critical: {free_gb:.2f} GB free on {target_path.anchor}, "
            f"minimum required is {min_free_gb:.1f} GB. Aborting media job."
        )
```

### 5.2 Directory Hierarchy Under `data/tmp/clips/<run_id>/`
All intermediate media must be strictly isolated in dedicated, run-scoped temporary directories:
```
data/
└── tmp/
    └── clips/
        └── <run_id>/
            ├── meta/
            │   ├── chat_spikes.json
            │   └── candidates.json
            ├── audio/
            │   └── stream_mono_16k.wav    <-- AUTO-PURGED after Stage 3!
            ├── slices/
            │   ├── raw_slice_01.mp4       <-- AUTO-PURGED after Stage 5 render!
            │   └── raw_slice_02.mp4       <-- AUTO-PURGED after Stage 5 render!
            └── output/
                ├── clip_01_vertical.mp4   <-- RETAINED final artifact
                ├── clip_01_subs.ass       <-- RETAINED subtitle track
                └── run_manifest.json      <-- RETAINED metadata
```

### 5.3 Stage-by-Stage Auto-Purge Lifecycle

Intermediate artifacts are deleted immediately upon completion of their dependent stage:

| Artifact Path | Format | Typical Size | Creation Stage | Deletion Stage | Persistence Rationale |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `audio/stream_mono_16k.wav` | 16kHz Mono WAV | 150–250 MB | Stage 2 (Audio Extract) | **Stage 3 Completion** | Transcripts are persisted to JSON; raw audio is no longer needed. |
| `slices/raw_slice_<id>.mp4` | 1080p H.264 slice | 40–80 MB | Stage 4 (Slice Fetch) | **Stage 5 Clip Render** | Deleted immediately after the 9:16 vertical render finishes. |
| `output/clip_<id>_vertical.mp4`| 1080x1920 9:16 MP4 | 15–30 MB | Stage 5 (Render) | **Permanent / Stored** | Final production artifact presented for human review. |
| `output/run_manifest.json` | JSON | < 50 KB | Stage 6 (Finalize) | **Permanent / Stored** | Metadata record linking candidate scores, words, and costs. |

**Guaranteed Active Footprint:** At no point during execution does the directory exceed **$\sim 450\text{ MB}$**.

### 5.4 24-Hour TTL Orphan Reaper Routine
If a worker process crashes, is force-killed by the user, or terminates unexpectedly, intermediate files could remain on disk. Every CLI worker and background job execution executes an automatic orphan cleanup on startup:
```python
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def reap_orphan_clip_directories(tmp_root: Path, max_age_hours: float = 24.0) -> int:
    """Purge temporary clip processing directories older than max_age_hours."""
    if not tmp_root.exists():
        return 0
    now = time.time()
    reaped_count = 0
    max_age_seconds = max_age_hours * 3600.0

    for run_dir in tmp_root.iterdir():
        if run_dir.is_dir():
            dir_age = now - run_dir.stat().st_mtime
            if dir_age > max_age_seconds:
                try:
                    shutil.rmtree(run_dir)
                    reaped_count += 1
                    logger.info("Reaped abandoned clip run directory: %s (age: %.1f hours)", run_dir.name, dir_age / 3600)
                except OSError as err:
                    logger.warning("Failed to reap directory %s: %s", run_dir, err)
    return reaped_count
```

---

## 6. Decision 3 — Deterministic CPU, Whisper & FFmpeg Settings (Windows-First)

### 6.1 `faster-whisper` CPU Execution Profile
To achieve maximum transcription throughput without exceeding the 1.1 GB RAM budget or stalling the host CPU:
- **Engine:** `faster-whisper` (CTranslate2 backend)
- **Model Size:** `base.en` (or `small.en` if word error rate requires higher fidelity)
- **Device & Quantization:** `device="cpu"`, `compute_type="int8"`
  *(int8 quantization reduces weight footprint from 500 MB to ~150 MB and leverages AVX2/AVX-512 SIMD vectorization on Ryzen 7600X).*
- **Thread Allocation:** `cpu_threads=4`
  *(Allocates 4 threads to CTranslate2, leaving 8 virtual threads completely free for Windows OS, UI, and audio decoding).*
- **Worker Allocation:** `num_workers=1` *(Prevents multi-process model duplication in memory).*
- **Voice Activity Detection:** `vad_filter=True` *(Pre-segments audio into speech chunks, skipping background game noise and silent sections).*
- **Two-Pass Beam Strategy:**
  - **Pass 1 (Candidate Selection & Ranking):** `beam_size=1` (greedy decoding for ultra-fast word boundary discovery).
  - **Pass 2 (Finalist Subtitle Alignment):** `beam_size=3` (applied only to top 3 selected clips for precision `.ass` karaoke word timestamps).

```python
# Canonical faster-whisper configuration for low-spec PC
from faster_whisper import WhisperModel

def create_low_spec_whisper_model() -> WhisperModel:
    return WhisperModel(
        model_size_or_path="base.en",
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        num_workers=1,
    )
```

### 6.2 `ffmpeg` Windows-First Configuration
- **Single Sequential Render Queue:** Never execute concurrent `ffmpeg` render passes. Clips are processed strictly one after another ($O(1)$ concurrent rendering).
- **CPU Thread Cap:** `-threads 2`
  *(Caps FFmpeg internal threading to 2 cores, eliminating CPU thermal throttling).*
- **Standardized Video Filtergraph & Encoding:**
  - Codec: `libx264`
  - Preset: `veryfast` *(Optimal balance of encoding speed and memory efficiency on CPU).*
  - Rate Control: `-crf 23`
  - Pixel Format: `-pix_fmt yuv420p` *(Universal mobile and browser compatibility).*
  - Audio Codec: `-c:a aac -b:a 128k -ar 44100`
  - Streaming Optimization: `-movflags +faststart` *(Places MP4 moov atom at beginning of file for instant Streamlit UI playback).*

```bash
# Canonical FFmpeg vertical 9:16 short render invocation
ffmpeg -y -threads 2 \
  -i "data/tmp/clips/<run_id>/slices/raw_slice_01.mp4" \
  -vf "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,subtitles='data/tmp/clips/<run_id>/output/clip_01_subs.ass'" \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 44100 -movflags +faststart \
  "data/tmp/clips/<run_id>/output/clip_01_vertical.mp4"
```

### 6.3 Windows Subprocess Hygiene
Adhering strictly to `.agents/skills/windows-python-hygiene/SKILL.md`:
1. **Process Priority Class:** Child processes must be spawned with `creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS` on Windows. This prevents the OS from lagging user input, cursor movement, or audio playback during video rendering.
2. **Explicit UTF-8 Encoding:** Subprocess pipes must specify `encoding="utf-8"` to prevent `cp1252` encoding crashes on non-ASCII stream metadata or chat titles.
3. **No Shell Invocations:** `shell=True` is strictly banned (`shell=False` only). All subprocess arguments are passed as explicit lists to eliminate command injection and shell wrapper overhead.

```python
import subprocess
import sys
import os

def run_low_priority_subprocess(cmd: list[str], timeout_s: float = 300.0) -> subprocess.CompletedProcess[str]:
    """Execute subprocess with below-normal priority and explicit UTF-8 encoding on Windows."""
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS"):
        creationflags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        creationflags=creationflags,
        timeout=timeout_s,
        check=True,
    )
```

---

## 7. Decision 4 — Verification & Telemetry Hooks

### 7.1 Telemetry Schema in `data/content_factory.db`
To catch memory bloat or disk leaks before code is merged, each stage records lightweight execution telemetry into SQLite:

```sql
CREATE TABLE IF NOT EXISTS media_execution_ledger (
    execution_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    peak_rss_mb REAL NOT NULL,
    duration_s REAL NOT NULL,
    disk_freed_mb REAL NOT NULL DEFAULT 0.0,
    exit_code INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_media_ledger_run ON media_execution_ledger(run_id);
CREATE INDEX IF NOT EXISTS idx_media_ledger_stage ON media_execution_ledger(stage_name);
```

### 7.2 Peak-RSS Capture Routine
Every isolated subprocess wraps its execution in `tracemalloc` (for pure Python stages) or `psutil` (for FFmpeg child processes):
```python
import psutil
import os

def get_current_process_rss_mb() -> float:
    """Return current process resident set size in megabytes."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)
```

### 7.3 Automated Test Contract Assertions
Integration tests under `tests/test_gaming_clips_budget.py` assert compliance against these budgets:
```python
def test_audio_peak_detection_memory_ceiling(tmp_path: Path):
    """Assert audio peak detection does not exceed 120 MB RAM ceiling on 1-hour synthetic WAV."""
    synthetic_wav = create_synthetic_wav(tmp_path, duration_seconds=3600)
    
    tracemalloc.start()
    peaks = detect_audio_energy_peaks_chunked(synthetic_wav)
    peak_bytes = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    
    peak_mb = peak_bytes / (1024 * 1024)
    assert peak_mb <= 120.0, f"Audio peak detection used {peak_mb:.2f} MB, exceeding 120 MB budget!"
    assert len(peaks) > 0
```

---

## 8. Consequences & Trade-Offs

### Positive Consequences
- **Total Crash Elimination:** Eliminates OOM crashes and `[WinError 1455]` pagefile thrashing on 8 GB RAM machines.
- **Responsive Workstation:** The system user can continue browsing, coding, or working while clipping jobs execute in the background due to `BELOW_NORMAL_PRIORITY_CLASS` and `-threads 2`.
- **Zero Disk Bloat:** Intermediate video and audio files are wiped immediately; the 256 GB SSD remains healthy.
- **Fast Clean Up:** Subprocess crashes leave zero dangling memory handles in Python.

### Negative Consequences & Mitigations
- **Subprocess Startup Overhead:** Launching discrete Python processes introduces ~150–300 ms of Python interpreter startup overhead per stage.
  - *Mitigation:* Negligible compared to the duration of audio transcription (20–60s) and video rendering (10–30s).
- **Sequential Rendering Throughput:** Rendering vertical clips one by one is slower than rendering in parallel on high-end 64 GB workstations.
  - *Mitigation:* Necessary trade-off for 8 GB RAM budget. Typical rendering for a 60-second clip on Ryzen 7600X takes ~12–18 seconds on `veryfast` preset.

---

## 9. Phased Implementation Hooks

| Phase | Module / Target | Implementation Hook |
| :--- | :--- | :--- |
| **Phase 2C** | `src/content_creation/core/db/` | Add `media_execution_ledger` table creation to consolidated SQLite database schema. |
| **Phase G1** | `src/content_creation/gaming_clips/audio.py` | Implement chunked WAV streaming peak detection ($\le 120\text{ MB}$ RSS). |
| **Phase G1** | `src/content_creation/gaming_clips/transcribe.py` | Implement subprocess-isolated `faster-whisper` (`int8`, `threads=4`, `vad=True`). |
| **Phase G1** | `src/content_creation/gaming_clips/render.py` | Implement sequential FFmpeg render queue (`-threads 2`, `veryfast`, auto-purge). |
| **Phase G2** | `src/content_creation/gaming_clips/reaper.py` | Hook `reap_orphan_clip_directories()` into background worker initialization. |

---

## 10. Compliance & Verification Checklist

Before completing tasks implementing this ADR, verify:
- [ ] **RAM Ceiling:** Measured peak RSS across every stage $\le 2.0\text{ GB}$ (tested via `test_gaming_clips_budget.py`).
- [ ] **Disk Footprint:** Active directory size in `data/tmp/clips/<run_id>/` never exceeds $500\text{ MB}$.
- [ ] **Zero Streamlit Inlining:** `src/content_creation/ui/views/7_gaming_clips.py` contains zero imports of `torch`, `faster_whisper`, `ffmpeg`, or `cv2`.
- [ ] **Windows Hygiene:** All subprocess calls use `creationflags=BELOW_NORMAL_PRIORITY_CLASS`, `encoding="utf-8"`, and `shell=False`.
- [ ] **Auto-Purge Verified:** Intermediates (`stream_mono_16k.wav`, `raw_slice_*.mp4`) are confirmed deleted upon stage completion.
