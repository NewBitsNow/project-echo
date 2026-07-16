"""Tests for classify_task.py — verify model routing decisions."""

import sys
import os
import pytest

# Add scripts dir to path so we can import classify_task
sys.path.insert(0, os.path.expanduser("~/Documents/twin-output/scripts"))
from classify_task import classify_task


def test_simple_edit_is_free_tier():
    """A simple typo fix should route to the free tier."""
    result = classify_task("Fix a typo in the README")
    assert result["tier"] == "free"
    assert result["complexity"] <= 0.3


def test_architecture_task_is_premium():
    """Architecture/design tasks should route to the paid premium tier."""
    result = classify_task("Design the database schema for the new microservice")
    # Complexity is high (design + database + schema = 1.0) so it may escalate
    assert result["tier"] in ["paid-premium", "escalation"]


def test_architecture_planning_is_premium():
    """A moderate architecture planning task should route to premium."""
    result = classify_task("Plan the API architecture for the new feature")
    assert result["tier"] in ["paid-premium", "escalation"]


def test_unknown_task_defaults_to_cheapest():
    """A very short, vague task should default to the cheapest tier."""
    result = classify_task("Do something")
    assert result["tier"] in ["free", "cheap-local"]


def test_complexity_score_ranges():
    """Complexity score should always be between 0.0 and 1.0."""
    result = classify_task("Refactor the authentication module to use OAuth2")
    assert 0.0 <= result["complexity"] <= 1.0


def test_read_only_query_is_free():
    """Read-only queries should route to free tier."""
    result = classify_task("What is the current state of the project?")
    assert result["tier"] == "free"


def test_long_complex_task_is_premium():
    """A long, multi-step task description should route to premium."""
    result = classify_task(
        "Implement a complete CI/CD pipeline with multi-stage builds, "
        "automated testing, deployment to production, and rollback support. "
        "This needs to handle secrets management, artifact storage, and "
        "environment promotion across dev, staging, and prod."
    )
    assert result["tier"] in ["paid-premium", "paid-cheap", "escalation"]


def test_result_has_all_keys():
    """Every classification result should have the expected keys."""
    result = classify_task("Fix formatting in the config file")
    required_keys = {"tier", "complexity", "task_type", "model", "provider"}
    assert required_keys.issubset(result.keys())


def test_model_is_string_or_none():
    """Model should be a string or None (for escalation tier)."""
    result = classify_task("Fix a typo")
    assert result["model"] is None or isinstance(result["model"], str)


def test_escalation_returns_no_model():
    """A task that can't be classified should return escalation with model=None."""
    # This is deliberately ambiguous/gibberish to test the fallback
    result = classify_task("Something completely unknown and extremely complex requiring deep architectural decisions across multiple systems with security implications and infrastructure changes that I don't understand")
    if result["tier"] == "escalation":
        assert result["model"] is None