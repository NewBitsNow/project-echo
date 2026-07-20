"""Tests for consent.py — verify contract reading and validation."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from echo_core.core.consent import (
    load_contract,
    is_consent_valid,
    check_consent,
    read_consent,
    consent_status,
    set_contract_path,
)


@pytest.fixture
def valid_contract():
    """Create a temporary valid consent contract."""
    contract = {
        "twin_id": "test-twin",
        "subject": "Test User",
        "created": "2026-07-15",
        "version": 1,
        "domains": {
            "code": {
                "enabled": True,
                "label": "Code Agent",
                "tools": ["terminal", "file"],
                "write_paths": ["/tmp/test/**"],
                "restrictions": [],
            },
            "content": {
                "enabled": False,
                "label": "Content Agent",
            },
        },
        "global_restrictions": [
            "no spending money",
            "no modifying system config",
        ],
        "write_whitelist": ["/tmp/test/**"],
        "expiry": {
            "duration_days": 30,
            "auto_renew": False,
            "on_expiry": "halt_and_report",
        },
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(contract, f)
        f.flush()
        path = f.name

    set_contract_path(path)
    yield contract, path
    os.unlink(path)


@pytest.fixture
def expired_contract():
    """Create a temporary expired contract."""
    contract = {
        "twin_id": "test-twin",
        "subject": "Test User",
        "created": "2024-01-01",
        "domains": {"code": {"enabled": True, "label": "Code Agent"}},
        "expiry": {"duration_days": 1},
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(contract, f)
        f.flush()
        path = f.name

    set_contract_path(path)
    yield contract, path
    os.unlink(path)


def test_load_contract_returns_dict(valid_contract):
    """load_contract should return a parsed YAML dict."""
    contract, _ = valid_contract
    result = load_contract()
    assert isinstance(result, dict)
    assert result["twin_id"] == "test-twin"


def test_load_contract_file_not_found():
    """load_contract should raise FileNotFoundError for missing files."""
    set_contract_path("/tmp/nonexistent-consent.yaml")
    with pytest.raises(FileNotFoundError):
        load_contract()


def test_is_consent_valid_valid(valid_contract):
    """A valid contract should return True."""
    contract, _ = valid_contract
    assert is_consent_valid(contract) is True


def test_is_consent_valid_expired(expired_contract):
    """An expired contract should return False."""
    contract, _ = expired_contract
    assert is_consent_valid(contract) is False


def test_check_consent_enabled_domain(valid_contract):
    """check_consent for an enabled domain should return enabled=True."""
    contract, _ = valid_contract
    result = check_consent("code", contract)
    assert result["enabled"] is True
    assert result["domain"] == "code"


def test_check_consent_disabled_domain(valid_contract):
    """check_consent for a disabled domain should return enabled=False."""
    contract, _ = valid_contract
    result = check_consent("content", contract)
    assert result["enabled"] is False


def test_read_consent_returns_active(valid_contract):
    """read_consent for a valid contract should return status='active'."""
    contract, _ = valid_contract
    result = read_consent()
    assert result["status"] == "active"
    assert "code" in result["enabled_domains"]
    assert "content" not in result["enabled_domains"]


def test_read_consent_returns_expired(expired_contract):
    """read_consent for an expired contract should return status='expired'."""
    contract, _ = expired_contract
    result = read_consent()
    assert result["status"] == "expired"


def test_consent_status_active(valid_contract):
    """consent_status for a valid contract should return 'active'."""
    contract, _ = valid_contract
    assert consent_status() == "active"


def test_consent_status_expired(expired_contract):
    """consent_status for an expired contract should return 'expired'."""
    contract, _ = expired_contract
    assert consent_status() == "expired"


def test_consent_status_not_found():
    """consent_status for a missing file should return 'not_found'."""
    set_contract_path("/tmp/nonexistent-consent.yaml")
    assert consent_status() == "not_found"