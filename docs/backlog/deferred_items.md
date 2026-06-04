# Deferred Items Backlog

Items deferred from active phases due to scope, dependency, or complexity constraints.

---

## BACKLOG-001

**Title:** Runtime Scoring Configuration

**Status:** Deferred

**Source:**
Phase 10.3 Audit — Warning W-002

**Current Behavior:**

* ScoreTopicsService loads weights from config/scoring.yaml
* UI weight sliders do not affect scoring
* No runtime override interface exists

**Reason Deferred:**

* Outside Phase 10.4 scope
* Would require service contract changes
* Requires additional validation and testing

**Potential Future Direction:**

```
UI Controls
    ↓
Scoring Configuration Service
    ↓
Temporary Config Object
    ↓
ScoreTopicsService
```

**Priority:** Medium

**Target Phase:** Post-Deployment Enhancement

---

## BACKLOG-002

**Title:** Concurrent Review History Writes

**Status:** Deferred

**Source:**
Phase 10.4 Audit — Risk R-006

**Current Behavior:**

* `save_review_history_entry()` performs read-modify-write without file locking
* Concurrent writes could overwrite each other's entries

**Reason Deferred:**

* Single-operator deployment target
* File locking adds complexity without current benefit
* Risk is negligible in single-user Streamlit deployment

**Potential Future Solution:**

* File locking via `fcntl.flock()` or `portalocker`
* Transactional persistence layer
* SQLite-backed review history

**Priority:** Low

**Target Phase:** Multi-User Deployment

---

## BACKLOG-005

**Title:** Operator Pipeline Results UX

**Status:** Deferred

**Category:** Operator Experience

**Priority:** Medium

**Problem:**

The current pipeline completion screen exposes developer-oriented information rather than operator-oriented information.

* Raw pipeline result JSON is displayed by default.
* Internal filesystem paths are displayed (log paths).
* Duration is displayed as raw seconds.
* Pipeline outcomes require interpretation of technical counters.
* Generated asset outcomes are not summarized clearly.

**Desired Outcome:**

Pipeline completion should communicate business outcomes first and technical details second.

**Requirements:**

1. Replace developer-facing completion output with an operator-facing summary.
2. Remove filesystem paths from operator-facing views (e.g., do not display `/opt/render/project/src/data/logs/...`).
3. Convert duration display into human-readable format (e.g., `226.44s` becomes `3m 46s`).
4. Display pipeline results as a concise summary (e.g., Topics Collected, Topics Scored, Briefs Generated, Content Intelligence Generated, Storyboards Generated, Assets Generated, Manifests Built).
5. Display generated asset outcomes clearly (e.g., ✓ Script, ✓ Thumbnail, ✓ Carousel, ✓ Newsletter).
6. Preserve raw pipeline JSON only inside an expandable technical diagnostics section.
7. Do not modify pipeline logic.
8. Do not modify backend services.
9. UI-only change.

**Target Phase:** Operator Experience Polish

