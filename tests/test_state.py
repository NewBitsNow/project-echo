"""Tests for state.py — verify state file CRUD operations."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from echo_core.core.state import (
    read_state,
    update_state,
    increment_cycle,
    system_status,
    init_state,
    set_state_path,
)


@pytest.fixture
def state_file():
    """Create a temporary state file."""
    state = {
        "twin_id": "test-twin",
        "status": "active",
        "current_cycle": 10,
        "last_wake": "2026-07-15T12:00:00Z",
        "active_domains": ["code"],
        "pending_escalations": [],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(state, f)
        f.flush()
        path = f.name

    set_state_path(path)
    yield state, path
    os.unlink(path)


def test_read_state_returns_dict(state_file):
    """read_state should return a dict."""
    expected, _ = state_file
    result = read_state()
    assert isinstance(result, dict)
    assert result["current_cycle"] == 10
    assert result["status"] == "active"


def test_read_state_not_found():
    """read_state for a missing file should return a default dict."""
    set_state_path("/tmp/nonexistent-state.json")
    result = read_state()
    assert result["status"] == "uninitialized"
    assert result["current_cycle"] == 0


def test_update_state_modifies_fields(state_file):
    """update_state should update specific fields and save."""
    expected, _ = state_file
    result = update_state({"status": "paused"})
    assert result["status"] == "paused"
    assert result["current_cycle"] == 10  # unchanged
    assert "last_updated" in result


def test_increment_cycle(state_file):
    """increment_cycle should add 1 to the cycle counter."""
    expected, _ = state_file
    result = increment_cycle()
    assert result["current_cycle"] == 11
    assert result["last_wake"] is not None


def test_increment_cycle_twice(state_file):
    """Calling increment_cycle twice should add 2."""
    expected, _ = state_file
    result = increment_cycle()
    assert result["current_cycle"] == 11
    result = increment_cycle()
    assert result["current_cycle"] == 12


def test_system_status(state_file):
    """system_status should return the status string."""
    expected, _ = state_file
    assert system_status() == "active"


def test_system_status_not_found():
    """system_status for a missing file should return 'uninitialized'."""
    set_state_path("/tmp/nonexistent-state.json")
    assert system_status() == "uninitialized"


def test_init_state_creates_file():
    """init_state should create a new state file with default values."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        path = f.name
    os.unlink(path)

    set_state_path(path)
    result = init_state(twin_id="custom-twin", twin_name="Custom Twin")

    assert result["twin_id"] == "custom-twin"
    assert result["twin_name"] == "Custom Twin"
    assert result["current_cycle"] == 0
    assert result["status"] == "active"

    # Verify file was written
    assert Path(path).exists()
    with open(path) as f:
        loaded = json.load(f)
        assert loaded["twin_id"] == "custom-twin"

    os.unlink(path)