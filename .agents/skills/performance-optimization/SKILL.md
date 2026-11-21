---
name: performance-optimization
description: Enforce strict resource budgets, coarse-to-fine filtering, and low-config PC execution limits. Load whenever building or refactoring media pipelines (gaming_clips, FFmpeg, Whisper, yt-dlp), batch ingestion, SQLite queries, or Streamlit rendering paths.
---

# Performance Optimization & Resource Budgets

Resource governance and performance discipline tailored for low-specification personal computers (CPU-only execution, <= 2 GB peak RAM) across media processing, ML inference, database access, and UI rendering.

## Mandatory Engineering Rules

### Rule 1 — Measure Before Optimizing
- **Profile First**: Benchmark wall-clock latency, peak RSS memory (`tracemalloc` or `psutil`), and disk I/O before adding caching, concurrency, or algorithmic complexity.
- **Establish Baselines**: Document exact baseline metrics (e.g., "120s latency, 1.8 GB RAM") before and after changes.
- **No Speculative Optimization**: Do not introduce caching layers, thread pools, or complex indices without measurable evidence of a bottleneck.

```python
# Pattern: Peak memory profiling with tracemalloc
import tracemalloc
tracemalloc.start()
result = execute_pipeline_stage(input_data)
peak_bytes = tracemalloc.get_traced_memory()[1]
tracemalloc.stop()
logger.info("Stage peak RSS: %.2f MB", peak_bytes / (1024 * 1024))
```

### Rule 2 — Coarse-to-Fine Funneling (Media & ML Pipelines)
- **Metadata First**: Filter candidate content using lightweight metadata, text transcripts, or duration checks before invoking compute-heavy processing.
- **Audio Energy Gating**: Perform lightweight 1D audio energy / voice-activity detection (VAD) passes before passing audio to Whisper. Never transcribe unshortlisted hours of audio.
- **Bounded Stream Downloads**: Never download full multi-gigabyte VODs with `yt-dlp`. Fetch metadata first, select targeted formats, and extract only requested time ranges or audio streams.

### Rule 3 — Strict Low-Config PC Execution Ceilings
- **CPU-Only Execution**: Design all pipelines to function reliably on CPU without assuming NVIDIA/CUDA availability.
- **Peak RAM Ceiling (<= 2 GB)**: Keep per-process peak resident memory strictly below 2 GB.
- **Quantized Inference**: Use quantized models (`int8`, `q8_0`, `ctranslate2`, tiny/base Whisper) for local transcription or embedding generation.
- **Bounded Concurrency**: Limit FFmpeg child processes to `-threads 2` and enforce a single sequential rendering queue to prevent CPU thrashing.
- **Streaming File I/O**: Stream and chunk large media and dataset files. Never read an entire media file into memory (`file.read()`).

```python
# Pattern: Bounded FFmpeg execution for low-config PC
cmd = ["ffmpeg", "-threads", "2", "-i", str(src_path), "-c:v", "libx264", "-preset", "veryfast", str(dst_path)]
```

### Rule 4 — Database & Streamlit Hot-Path Hygiene
- **SQLite WAL Mode**: Configure connections with `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;`. Ensure all frequent query filters have backing indexes.
- **Zero DDL in Hot Paths**: Never execute `CREATE TABLE`, `ALTER TABLE`, or schema checks inside UI render loops or per-item processing loops.
- **Streamlit Render Optimization**: Avoid opening fresh database connections on every widget interaction. Use `@st.cache_data`, `@st.cache_resource`, and `@st.fragment` for fine-grained partial rerenders.

## Anti-Patterns to Reject

| Anti-Pattern | Why It Fails & What to Do Instead |
| :--- | :--- |
| **Full File Memory Loads** | Loading entire video/audio files causes OOM crashes on 2 GB RAM; use streaming iterators. |
| **Unbounded FFmpeg Threads** | Default thread spawning causes 100% CPU lockups; cap strictly with `-threads 2`. |
| **Blind Audio Transcription** | Transcribing raw unshortlisted hours wastes compute; gate behind 1D energy / VAD checks. |
| **DDL in UI Render Loops** | Running table checks on every Streamlit rerun stalls rendering; run migrations at startup. |

## Quick Verification Checklist

Before finalizing any media, database, or UI feature, verify:
1. **[ ] Profiled**: Measured baseline vs optimized latency and memory (`tracemalloc`).
2. **[ ] Low-Config RAM**: Peak memory usage remains <= 2 GB during peak execution.
3. **[ ] Funneled Compute**: Heavy compute (Whisper/FFmpeg) is gated behind cheap metadata/energy filters.
4. **[ ] Concurrency Capped**: Subprocess threads bounded (`-threads 2` max for FFmpeg); CPU-only safe.
5. **[ ] Streamlit & DB Clean**: Database indexed and WAL-enabled; zero DDL or raw connections in UI render loops.
