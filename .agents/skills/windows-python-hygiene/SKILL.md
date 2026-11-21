---
name: windows-python-hygiene
description: Enforce Windows-first engineering rules for Python file I/O, subprocesses, SQLite ordering, signals, and sockets. Load whenever writing, refactoring, verifying, or testing code on Windows.
---

# Windows Python Hygiene

Essential Windows-first engineering rules grounded in real repository failures to prevent runtime crashes, flaky tests, and subtle bugs across file I/O, subprocess execution, database timestamps, signals, and socket networking.

## Mandatory Engineering Rules

### Rule 1 — Explicit UTF-8 File I/O (Prevents `0x97` `cp1252` crashes)
*Rationale: Windows default system encoding (`cp1252`) crashes with `UnicodeDecodeError: 'cp1252' codec can't decode byte 0x97` when reading smart quotes or em dashes.*
- **Do**: Always pass `encoding="utf-8"` to every `open()`, `Path.read_text()`, and `Path.write_text()` call across `src/`, `cli/`, and `tests/`.
- **Do**: When reading external/legacy JSON or RSS text that may contain Windows smart quotes, attempt `utf-8` first and fall back to `cp1252` with a `WARNING` log.
- **Don't**: Rely on default encoding or unparameterized file methods (`Path.read_text()` without `encoding`).
- **Don't**: Assume standard streams (`sys.stdout`/`sys.stderr`) accept arbitrary Unicode without UTF-8 reconfiguring.

```python
# Pattern: Explicit UTF-8 with fallback
try:
    content = path.read_text(encoding="utf-8")
except UnicodeDecodeError:
    logger.warning("UTF-8 decoding failed for %s, falling back to cp1252", path)
    content = path.read_text(encoding="cp1252")
```

### Rule 2 — Zero Hardcoded POSIX `bash` Subprocesses (Prevents `[WinError 1920]` & Sandbox `0xC0000022`)
*Rationale: Windows lacks `/bin/bash` (`[WinError 1920]`), and MSYS2/Git Bash aborts with `0xC0000022` inside Windows AppContainer sandboxes.*
- **Do**: Use `sys.executable` (`[sys.executable, "-m", ...]`) for launching Python subprocesses.
- **Do**: Use pure Python (`pathlib`, `shutil`) for filesystem manipulation rather than shell commands (`rm`, `mkdir`, `cp`).
- **Do**: Guard shell commands with `if os.name == "nt":` and invoke Windows-native commands (`cmd.exe /c` or PowerShell).
- **Don't**: Hardcode `bash`, `sh`, or POSIX pipelines (`grep`, `tail`, `cat`) in `subprocess.run()` or `subprocess.Popen()`.

### Rule 3 — Deterministic Ordering Over Wall-Clock Timestamps (Prevents 15.6 ms Clock-Tick Races)
*Rationale: Windows `datetime.now(timezone.utc)` has ~15.6 ms default timer granularity, causing rapid consecutive records to produce identical timestamps.*
- **Do**: Always use SQLite `rowid`, `INTEGER PRIMARY KEY AUTOINCREMENT`, monotonic counters, or explicitly injected test timestamps for sequence ordering.
- **Don't**: Rely on `time.sleep(0.01)` or random UUID4 string tie-breaking (`ORDER BY created_at, id`) to order rapid pipeline events.
- **Don't**: Rely on sub-15ms timestamp differences to establish event causality in unit tests.

### Rule 4 — Explicit IPv4 `127.0.0.1` Loopback Over `localhost` (Prevents `[WinError 10013]`)
*Rationale: On Windows, `localhost` often resolves to IPv6 `::1` while servers bind IPv4, triggering `[WinError 10013]` (WSAEACCES) permission errors.*
- **Do**: Always bind and connect local servers, streaming endpoints, and test sockets explicitly via `127.0.0.1`.
- **Do**: Validate socket test availability with both `bind()` and `connect()` before testing client connections.
- **Don't**: Use `"localhost"` as host in server binding, client URLs, or test socket fixtures.

### Rule 5 — Windows-Safe Atomic Writes, Paths & Signals
*Rationale: Windows locks open files against rename/unlink (`PermissionError`, `WinError 32`), fails cross-volume renames, and lacks POSIX signals.*
- **Do**: Create atomic temporary files in the *same* target directory before calling `os.replace()`, closing handles before rename.
- **Do**: Guard POSIX-only signals (`SIGTERM`, `SIGHUP`, `SIGUSR1`) with `hasattr(signal, "SIG...")` checks before attaching handlers.
- **Do**: Isolate all test filesystem writes inside `pytest`'s `tmp_path` fixture; never mutate real `data/` or working trees.
- **Don't**: Attempt atomic renames across different drives/volumes or rename a file while any open handle exists.

```python
# Pattern: Atomic write in same directory
tmp_file = target_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
tmp_file.write_text(data, encoding="utf-8")
os.replace(tmp_file, target_path)
```

## Quick Verification Checklist

Before finishing any task, `refactor-executor`, `contract-verifier`, and `qa-test-engineer` must scan:
1. **[ ] Explicit UTF-8**: Every `open()`, `Path.read_text()`, and `Path.write_text()` has explicit `encoding="utf-8"`.
2. **[ ] Native Execution**: Zero hardcoded `bash`/`sh` calls; uses `sys.executable` and `pathlib` with `os.name == "nt"` guards.
3. **[ ] Deterministic Order**: Ordering relies on SQLite autoincrement/rowid/counters rather than wall-clock timestamps or short sleeps.
4. **[ ] IPv4 Loopback**: Sockets and test server connections explicitly target `127.0.0.1` instead of `localhost`.
5. **[ ] Handles & Signals**: Atomic writes close handles and share directories; POSIX signals use `hasattr()`; tests use `tmp_path`.
