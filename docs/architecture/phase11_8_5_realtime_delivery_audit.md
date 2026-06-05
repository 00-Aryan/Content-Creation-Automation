# Phase 11.8.5 — Real-Time Notification Streaming (SSE) Audit

**Date:** 2026-06-04
**Status:** APPROVED
**Author:** Principal Distributed Systems & Workflow Infrastructure Architect

---

## 1. Current Refresh Paths

| Page | Refresh Mechanism | Trigger |
|------|-------------------|---------|
| Dashboard (`app.py`) | Full page render | Manual browser refresh or navigation |
| Brief Viewer | `st.rerun()` | After review decision |
| Storyboard | `st.rerun()` | After review decision |
| Asset Workshop | `st.rerun()` | After review decision |
| Topic Collection | `st.rerun()` | After collection action |
| Topic Pipeline | `st.rerun()` | After scoring action |

**Observation:** All refreshes are operator-initiated. No automatic refresh exists for notification delivery.

---

## 2. Current Polling Behavior

| Component | Polling | Interval |
|-----------|---------|----------|
| None | N/A | N/A |

**Observation:** The application has zero polling mechanisms. All data is fetched on-demand during page renders.

---

## 3. Notification Latency Analysis

| Path | Latency | Bottleneck |
|------|---------|------------|
| Event → Subscriber → Repository | ~1-5ms | In-memory bus + SQLite write |
| Repository → UI display | ∞ (until page refresh) | No push mechanism |
| **Total perceived latency** | **Manual refresh** | **No real-time delivery** |

**Critical Gap:** The notification persists in SQLite within milliseconds of the event, but the operator has no way to see it without refreshing the page.

---

## 4. Candidate Streaming Points

| Stream Event | Source | Priority | Audience |
|--------------|--------|----------|----------|
| `notification_created` | NotificationSubscriber | HIGH | All operators |
| `notification_read` | NotificationService | MEDIUM | Owner only |
| `notification_archived` | NotificationService | MEDIUM | Owner only |
| `job_started` | WorkerDaemon | HIGH | Job monitors |
| `job_completed` | WorkerDaemon | HIGH | Job monitors |
| `job_failed` | WorkerDaemon | CRITICAL | Job monitors |
| `brief_approved` | WorkflowActionExecutor | HIGH | Reviewers |
| `brief_rejected` | WorkflowActionExecutor | HIGH | Reviewers |
| `pipeline_completed` | WorkflowActionExecutor | HIGH | Dashboard |
| `pipeline_failed` | WorkflowActionExecutor | CRITICAL | Dashboard |

---

## 5. Failure Modes

| Failure Mode | Impact | Mitigation |
|--------------|--------|------------|
| SSE connection drops | Operator stops receiving real-time updates | Auto-reconnect in JavaScript EventSource |
| SSE server thread dies | All clients lose stream | Server auto-restarts on next connection attempt |
| SQLite write contention | Notification delayed or lost | WAL mode + busy_timeout (already implemented) |
| Memory leak from stale clients | Server resource exhaustion | Heartbeat-based cleanup every 30s |
| Browser tab backgrounded | EventSource may be paused by browser | Document.hidden API + reconnect strategy |

---

## 6. Browser Connection Limitations

| Browser | Max SSE Connections per Domain | Notes |
|---------|-------------------------------|-------|
| Chrome | 6 | Per-origin limit |
| Firefox | 6 | Per-origin limit |
| Safari | 6 | Per-origin limit |

**Impact:** Operators may have multiple tabs open. Each tab creates one SSE connection. With 6 max connections per domain, this is sufficient for normal use.

**Streamlit Specific:** Streamlit uses port 8501 by default. All SSE connections share this origin.

---

## 7. Architecture Decision: SSE via Python Built-in HTTP Server

**Rationale:**
- No new dependencies required (uses `http.server` + `threading` + `queue.Queue`)
- Runs as a background thread alongside Streamlit
- SSE endpoint served on a separate port (default 8502)
- JavaScript `EventSource` in browser connects to SSE endpoint
- Streamlit UI receives updates via `window.postMessage` bridge

**Data Flow:**
```
Workflow Event → Subscriber → Notification Repository
                                    ↓
                          Notification Publisher
                                    ↓
                          Connection Manager (broadcast)
                                    ↓
                          SSE HTTP Server (background thread)
                                    ↓
                          Browser EventSource (JavaScript)
                                    ↓
                          Streamlit UI Update (postMessage)
```
