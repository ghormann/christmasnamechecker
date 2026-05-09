# Cache Persistence Design

**Date:** 2026-05-09  
**Status:** Approved

## Problem

When the Docker container restarts, all in-memory state in `text_server.py` is lost. The three fields that matter are:

- `history` — up to 200 recent SMS submissions, used for spam detection (`num_recent_calls`) and the admin UI
- `blocked` — phone numbers currently blocked from submitting names, critical for spam prevention
- `outPhone` — up to 20 recent outbound messages shown in the admin UI

All other `masterData` fields (`queue`, `ready`, `buttons`, `timeinfo`, etc.) are repopulated from MQTT on reconnect and do not need persistence.

## Solution

### Periodic background save (every 60 seconds)

A daemon thread starts at program init alongside the MQTT client. It loops forever, sleeping 60 seconds between iterations. On each wake it:

1. Acquires `data_lock`
2. Serializes `history`, `blocked`, and `outPhone` to JSON
3. Releases `data_lock`
4. Writes to `cache/state.json.tmp`
5. Calls `os.replace("cache/state.json.tmp", "cache/state.json")` for an atomic swap

The atomic rename prevents a corrupt partial file being read on the next restart.

### Startup restore

Before Flask starts, the server attempts to load `cache/state.json`. On success it populates `masterData["history"]`, `masterData["blocked"]`, and `masterData["outPhone"]` directly. The two `addHistory` test calls in `__main__` are guarded by `if not masterData["history"]` so they only fire when no cache was loaded (first run or empty cache).

### Error handling

| Scenario | Behavior |
|---|---|
| Cache file missing | Skip silently (normal on first run) |
| Cache file corrupt / invalid JSON | Log a warning, start with empty state |
| Save failure | Log the exception, continue running (do not crash) |

## docker-compose.yml fix

`christmasnames-cache` is referenced as a volume mount but not declared in the top-level `volumes:` section. This causes `docker compose up` to fail. Add it alongside the existing `christmasnames-log` declaration.

## Files changed

- `text_server.py` — add `load_cache()`, `save_cache()`, `_cache_saver_thread()`, start thread at init, guard test `addHistory` calls in `__main__`
- `docker-compose.yml` — declare `christmasnames-cache:` in top-level `volumes:`
