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
