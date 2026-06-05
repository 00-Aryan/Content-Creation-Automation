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


google/genai/types.py
DeprecationWarning:
'_UnionGenericAlias' is deprecated