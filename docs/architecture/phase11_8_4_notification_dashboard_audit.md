# Phase 11.8.4 — Notification Consumption & Dashboard Integration Audit

**Date:** 2026-06-04
**Status:** APPROVED
**Author:** Principal Distributed Systems & Workflow Infrastructure Architect

---

## 1. Page Inventory

| Page | File | Lines | Purpose |
|------|------|-------|---------|
| Dashboard | `ui/app.py` | 168 | Main entry: metrics, pipeline orchestration, workflow matrix, activity |
| Topic Collection | `pages/1_topic_collection.py` | 69 | Ingest topics, list staged |
| Topic Pipeline | `pages/2_topic_pipeline.py` | 117 | Score topics, weight preview, inspector |
| Brief Viewer | `pages/3_brief_viewer.py` | 243 | Brief display, review controls, generation |
| Storyboard | `pages/4_storyboard.py` | 309 | CI + storyboard display, review, generation |
| Asset Workshop | `pages/5_asset_workshop.py` | 329 | Asset generation, manifest, multi-format review |

### Shared Components

| Component | File | Purpose |
|-----------|------|---------|
| Status | `components/status.py` | Header, API health sidebar, metric cards |

### Infrastructure

| Layer | File | Purpose |
|-------|------|---------|
| ServiceClient | `services/client.py` | Adapter bridging UI to backend services |
| Session State | `state/session.py` | Topic/brief selection, generic filters |

---

## 2. Existing Status Indicators

| Page | Indicator | Mechanism |
|------|-----------|-----------|
| Dashboard | Pipeline metrics (5 counts) | `st.metric()` columns |
| Dashboard | Workflow status matrix | DataFrame with emoji status |
| Dashboard | Recent activity table | Static table from workflow states |
| Dashboard | API health | Sidebar success/error badge |
| Brief Viewer | Review status badge | Text display from brief model |
| Brief Viewer | Review history | Last 5 entries table |
| Storyboard | Review status | Text display |
| Storyboard | Review history | Last 5 entries table |
| Asset Workshop | Manifest status badge | 3 metric cards |
| Asset Workshop | Review history | Last 10 entries table |

**Observation:** All status indicators are pull-based (read from storage on page load). No push-based notification mechanism exists.

---

## 3. Existing Alert Banners

| Page | Alert Type | Trigger |
|------|-----------|---------|
| Dashboard | `st.error()` | Pipeline execution failure |
| Dashboard | `st.success()` | Pipeline completion |
| Dashboard | `st.info()` | No data available |
| Brief Viewer | `st.warning()` | Review confirmation prompt |
| Brief Viewer | `st.error()` | Generation failure |
| Storyboard | `st.warning()` | Review confirmation prompt |
| Asset Workshop | `st.warning()` | Review confirmation prompt |

**Observation:** Alerts are transient (lost on page refresh). No persistent notification mechanism.

---

## 4. Existing Polling Mechanisms

| Component | Mechanism | Interval |
|-----------|-----------|----------|
| None | N/A | N/A |

**Observation:** The Streamlit UI has no polling. All data is loaded on page render via `st.cache_resource` for `ApplicationContext`. No auto-refresh exists.

---

## 5. Notification Insertion Points

### 5.1 Dashboard (`app.py`)

| Insertion Point | Location | Type |
|-----------------|----------|------|
| Unread count badge | Sidebar, below health check | Persistent counter |
| Notification summary panel | Below metric cards | Category breakdown |
| Critical alerts section | Below pipeline orchestration | ERROR/CRITICAL notifications |
| Recent notifications table | Below activity table | Last 10 notifications |

### 5.2 Brief Viewer (`3_brief_viewer.py`)

| Insertion Point | Location | Type |
|-----------------|----------|------|
| Review result feedback | After `apply_brief_decision()` | Inline notification |
| Generation completion | After `generate_briefs()` | Inline notification |
| Dependency failure alert | When brief dependencies missing | Warning banner |

### 5.3 Storyboard (`4_storyboard.py`)

| Insertion Point | Location | Type |
|-----------------|----------|------|
| Review result feedback | After `apply_storyboard_decision()` | Inline notification |
| Generation completion | After `generate_storyboards()` | Inline notification |
| CI generation result | After `generate_content_intelligence()` | Inline notification |

### 5.4 Asset Workshop (`5_asset_workshop.py`)

| Insertion Point | Location | Type |
|-----------------|----------|------|
| Review decision result | After `apply_asset_decisions()` | Inline notification |
| Asset generation result | After `generate_asset_suite()` | Inline notification |
| Manifest status change | After rebuild | Status banner |

---

## 6. User Journeys

### 6.1 Operator Feedback Loop (Current → Enhanced)

**Current:**
1. Operator triggers action (e.g., generate briefs)
2. `ServiceClient` calls `WorkflowActionExecutor.execute()`
3. Executor emits events (Phase 11.8.2)
4. Subscribers create notifications (Phase 11.8.3)
5. **Notifications are persisted but invisible to operator**

**Enhanced (Phase 11.8.4):**
1. Operator triggers action
2. Events emitted, notifications created (same as before)
3. Notification Center shows unread count badge
4. Operator sees notification in dropdown
5. Operator marks read or archives
6. Dashboard shows summary metrics

### 6.2 Review Decision Journey

**Current:**
1. Operator reviews brief/storyboard/asset
2. Selects approval/rejection
3. Clicks "Apply" button
4. Success/error message shown (transient)

**Enhanced:**
1. Operator reviews item
2. Selects decision, clicks "Apply"
3. Event emitted → notification created
4. Inline feedback confirms notification was created
5. Notification visible in center with full context

---

## 7. Operator Workflow Mapping

| Workflow Phase | Current Feedback | Enhanced Feedback |
|----------------|------------------|-------------------|
| Topic Collection | `st.status()` spinner | + Notification on completion |
| Scoring | `st.status()` spinner | + Notification on completion |
| Brief Generation | `st.status()` + count display | + Notification with counts |
| Brief Review | Review history table | + Notification for approval/rejection |
| CI Generation | `st.status()` spinner | + Notification on completion |
| Storyboard Generation | `st.status()` spinner | + Notification on completion |
| Storyboard Review | Review history table | + Notification for approval/rejection |
| Asset Generation | `st.status()` spinner | + Notification on completion |
| Asset Review | Review history table | + Notification per asset decision |
| Pipeline Execution | Status update + JSON dump | + Notification on completion/failure |

---

## 8. Risks

1. **Stale Notification Counts**: Without polling/auto-refresh, unread counts will be stale until page reload.
   - *Mitigation*: Use `st.rerun()` after mutations, or accept manual refresh.

2. **Service Layer Coupling**: `ServiceClient` currently has no notification awareness.
   - *Mitigation*: Add notification methods to `ServiceClient` that delegate to `NotificationService`.

3. **SQLite Connection Sharing**: `NotificationService` and `ServiceClient` may need the same connection.
   - *Mitigation*: Use `@st.cache_resource` for connection singleton.

4. **Notification Volume**: High-frequency events could flood the notification center.
   - *Mitigation*: `NotificationMaintenanceService` with configurable retention; display limits.

5. **Performance**: Each page load queries notification counts.
   - *Mitigation*: Cache unread count in session state; invalidate on mutations.

---

## 9. Integration Recommendations

1. **Create `NotificationService`** as a pure application service (no Streamlit imports).
2. **Create `NotificationMaintenanceService`** for cleanup operations.
3. **Create `components/notification_panel.py`** as a reusable UI component.
4. **Add notification methods to `ServiceClient`** for UI access.
5. **Add notification state keys to `session.py`** for UI state management.
6. **Modify `app.py`** to render notification summary on dashboard.
7. **Modify review pages** to show inline notification feedback after decisions.
8. **Use `@st.cache_resource`** for SQLite connection to avoid connection leaks.
