# Cache Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist `history`, `blocked`, and `outPhone` from `text_server.py` to `cache/state.json` every 60 seconds so the data survives container restarts.

**Architecture:** Two pure functions (`load_cache`, `save_cache`) handle file I/O; a daemon thread calls save every 60 seconds; startup reads the file before Flask begins. docker-compose.yml is fixed to declare the `christmasnames-cache` volume.

**Tech Stack:** Python stdlib (`json`, `os`, `threading`), pytest for tests.

---

## File Map

- **Modify:** `docker-compose.yml` — declare `christmasnames-cache:` in top-level `volumes:`
- **Modify:** `text_server.py` — add `load_cache()`, `save_cache()`, `_cache_saver_thread()`, startup restore, guard test calls
- **Create:** `tests/test_cache.py` — unit tests for `load_cache` and `save_cache`
- **Modify:** `requirements.txt` — add `pytest` for tests

---

### Task 1: Fix docker-compose.yml missing volume declaration

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add the missing volume declaration**

The file currently declares `christmasnames-log:` but not `christmasnames-cache:`, causing `docker compose up` to fail. The top-level `volumes:` section must list both.

Open `docker-compose.yml` and change:

```yaml
volumes:
  christmasnames-log:
    driver: local
```

to:

```yaml
volumes:
  christmasnames-log:
    driver: local
  christmasnames-cache:
    driver: local
```

- [ ] **Step 2: Verify the file is valid YAML**

```bash
python3 -c "import yaml, sys; yaml.safe_load(open('docker-compose.yml'))" 2>&1 || echo "YAML error"
```

Expected: no output (no error).

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "fix: declare christmasnames-cache volume in docker-compose.yml"
```

---

### Task 2: Add pytest and create test scaffold

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Add pytest to requirements.txt**

Append `pytest` to `requirements.txt`:

```
paho-mqtt
flask
twilio
pytest
```

- [ ] **Step 2: Install pytest locally**

```bash
pip install pytest
```

Expected: Successfully installed pytest (or already satisfied).

- [ ] **Step 3: Create tests/__init__.py**

Create an empty file at `tests/__init__.py`.

- [ ] **Step 4: Create the test file with failing tests**

Create `tests/test_cache.py`:

```python
import json
import os
import pytest
import tempfile


# These imports will fail until Task 3 adds the functions to text_server.
# That is expected — the tests are written first.
from text_server import load_cache, save_cache


@pytest.fixture
def tmp_path_cache(tmp_path):
    return str(tmp_path / "state.json")


def test_load_cache_missing_file_returns_none(tmp_path_cache):
    result = load_cache(tmp_path_cache)
    assert result is None


def test_load_cache_corrupt_json_returns_none(tmp_path_cache):
    with open(tmp_path_cache, "w") as f:
        f.write("not valid json {{{{")
    result = load_cache(tmp_path_cache)
    assert result is None


def test_load_cache_returns_dict_with_all_fields(tmp_path_cache):
    data = {
        "history": [{"phone": "123", "name": "Alice", "valid": True, "blocked": False, "nameCnt": 1, "recent": 0, "ts": 1000.0}],
        "blocked": [{"phone": "456", "ts": 2000.0, "length": 10}],
        "outPhone": [{"phone": "789", "message": "Hi", "ts": 3000.0}],
    }
    with open(tmp_path_cache, "w") as f:
        json.dump(data, f)
    result = load_cache(tmp_path_cache)
    assert result["history"][0]["name"] == "Alice"
    assert result["blocked"][0]["phone"] == "456"
    assert result["outPhone"][0]["message"] == "Hi"


def test_load_cache_missing_keys_defaults_to_empty_lists(tmp_path_cache):
    with open(tmp_path_cache, "w") as f:
        json.dump({}, f)
    result = load_cache(tmp_path_cache)
    assert result["history"] == []
    assert result["blocked"] == []
    assert result["outPhone"] == []


def test_save_cache_creates_file(tmp_path_cache):
    data = {"history": [], "blocked": [], "outPhone": []}
    save_cache(data, tmp_path_cache)
    assert os.path.exists(tmp_path_cache)


def test_save_cache_round_trips_data(tmp_path_cache):
    data = {
        "history": [{"phone": "111", "name": "Bob", "valid": True, "blocked": False, "nameCnt": 1, "recent": 0, "ts": 500.0}],
        "blocked": [],
        "outPhone": [],
    }
    save_cache(data, tmp_path_cache)
    result = load_cache(tmp_path_cache)
    assert result["history"][0]["name"] == "Bob"


def test_save_cache_is_atomic(tmp_path_cache):
    """Verify no .tmp file is left behind after a successful save."""
    data = {"history": [], "blocked": [], "outPhone": []}
    save_cache(data, tmp_path_cache)
    tmp_file = tmp_path_cache + ".tmp"
    assert not os.path.exists(tmp_file)
```

- [ ] **Step 5: Run the tests and confirm they fail with ImportError**

```bash
pytest tests/test_cache.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'load_cache' from 'text_server'` (or similar). This confirms the tests are wired correctly before the implementation exists.

---

### Task 3: Implement load_cache and save_cache in text_server.py

**Files:**
- Modify: `text_server.py`

- [ ] **Step 1: Add the two functions after the imports block**

In `text_server.py`, after the `import unicodedata` line (line 18) and before `with open('greglights_config.json')`, add:

```python
CACHE_PATH = "cache/state.json"


def load_cache(path=CACHE_PATH):
    """Return persisted state dict or None if file is missing or corrupt."""
    try:
        with open(path) as f:
            data = json.load(f)
        return {
            "history": data.get("history", []),
            "blocked": data.get("blocked", []),
            "outPhone": data.get("outPhone", []),
        }
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, Exception) as e:
        logging.warning("Cache load failed: %s", e)
        return None


def save_cache(data, path=CACHE_PATH):
    """Atomically write state dict to path."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)
    except Exception as e:
        logging.warning("Cache save failed: %s", e)
```

- [ ] **Step 2: Run the tests and confirm they all pass**

```bash
pytest tests/test_cache.py -v
```

Expected output (all 7 tests pass):
```
tests/test_cache.py::test_load_cache_missing_file_returns_none PASSED
tests/test_cache.py::test_load_cache_corrupt_json_returns_none PASSED
tests/test_cache.py::test_load_cache_returns_dict_with_all_fields PASSED
tests/test_cache.py::test_load_cache_missing_keys_defaults_to_empty_lists PASSED
tests/test_cache.py::test_save_cache_creates_file PASSED
tests/test_cache.py::test_save_cache_round_trips_data PASSED
tests/test_cache.py::test_save_cache_is_atomic PASSED
```

- [ ] **Step 3: Commit**

```bash
git add text_server.py tests/__init__.py tests/test_cache.py requirements.txt
git commit -m "feat: add load_cache and save_cache with tests"
```

---

### Task 4: Add background saver thread and startup restore

**Files:**
- Modify: `text_server.py`

- [ ] **Step 1: Add the background thread function**

In `text_server.py`, after the `save_cache` function, add:

```python
def _cache_saver_thread():
    while True:
        time.sleep(60)
        with data_lock:
            data = {
                "history": list(masterData["history"]),
                "blocked": list(masterData["blocked"]),
                "outPhone": list(masterData["outPhone"]),
            }
        save_cache(data)
```

- [ ] **Step 2: Start the thread and restore state at startup**

The thread and the restore must happen after `masterData` and `data_lock` are initialized but before Flask starts serving requests. They should be placed at module level, after the `mqtt = MQTTClient(...)` line (currently line 98).

Find this block near line 98:

```python
mqtt = MQTTClient(handler=AppMQTTHandler())
```

Replace it with:

```python
mqtt = MQTTClient(handler=AppMQTTHandler())

_cached = load_cache()
if _cached:
    masterData["history"] = _cached["history"]
    masterData["blocked"] = _cached["blocked"]
    masterData["outPhone"] = _cached["outPhone"]
    logger.info("Cache restored: %d history, %d blocked, %d outPhone",
                len(_cached["history"]), len(_cached["blocked"]), len(_cached["outPhone"]))

_saver = threading.Thread(target=_cache_saver_thread, daemon=True, name="cache-saver")
_saver.start()
```

- [ ] **Step 3: Guard the test addHistory calls in __main__**

Find the `__main__` block at the bottom of the file:

```python
if __name__ == "__main__":
    addHistory('123-456-7890', 'Test', False, 1)
    addHistory('123-456-7890', 'Test2', False, 1)
    app.run(host='0.0.0.0', port=9999)
```

Replace with:

```python
if __name__ == "__main__":
    if not masterData["history"]:
        addHistory('123-456-7890', 'Test', False, 1)
        addHistory('123-456-7890', 'Test2', False, 1)
    app.run(host='0.0.0.0', port=9999)
```

- [ ] **Step 4: Run existing tests to confirm nothing broke**

```bash
pytest tests/test_cache.py -v
```

Expected: all 7 tests still pass.

- [ ] **Step 5: Smoke test the startup restore manually**

```bash
mkdir -p cache
python3 -c "
import json
data = {'history': [{'phone': '555', 'name': 'TestRestore', 'valid': True, 'blocked': False, 'nameCnt': 1, 'recent': 0, 'ts': 1000.0}], 'blocked': [], 'outPhone': []}
with open('cache/state.json', 'w') as f:
    json.dump(data, f)
print('Wrote test cache')
"
python3 -c "
from text_server import masterData
print('history count:', len(masterData['history']))
print('first name:', masterData['history'][0]['name'])
" 2>&1 | grep -E "history count|first name|Cache restored"
```

Expected output:
```
history count: 1
first name: TestRestore
```

- [ ] **Step 6: Clean up test cache file**

```bash
rm cache/state.json
```

- [ ] **Step 7: Commit**

```bash
git add text_server.py
git commit -m "feat: restore cache on startup and save every 60s in background thread"
```
