"""Tests for packet_builder.py — verify structured packet construction."""

import pytest
from echo_core.core.packet_builder import build_packet, packet_to_delegation


def test_build_packet_has_required_fields():
    """A packet should have mission, routing, scope, verification, acceptance_criteria."""
    packet = build_packet("Add rate limiting", scope=["src/**"])
    assert "mission" in packet
    assert "routing" in packet
    assert "scope" in packet
    assert "verification" in packet
    assert "acceptance_criteria" in packet


def test_packet_routing_includes_tier_and_model():
    """Routing should include tier, model, and complexity from classify_task."""
    packet = build_packet("Fix a typo in README", scope=["README.md"])
    assert "tier" in packet["routing"]
    assert "model" in packet["routing"]
    assert "complexity" in packet["routing"]


def test_packet_scope_has_allowed_and_forbidden():
    """Scope should separate modify_allowed from modify_forbidden."""
    packet = build_packet(
        "Refactor auth module",
        scope=["src/auth/**"],
        forbidden=[".agent/**", "secrets/**"]
    )
    assert "modify_allowed" in packet["scope"]
    assert "modify_forbidden" in packet["scope"]
    assert ".agent/**" in packet["scope"]["modify_forbidden"]
    assert "secrets/**" in packet["scope"]["modify_forbidden"]


def test_simple_task_gets_free_model():
    """A simple typo fix should route to the free tier."""
    packet = build_packet("Fix a typo in the README", scope=["README.md"])
    assert packet["routing"]["tier"] == "free"
    assert "free" in packet["routing"]["model"]


def test_complex_task_gets_premium_or_escalation():
    """A complex architecture task should go premium or escalate."""
    packet = build_packet(
        "Design the database schema for the new microservice",
        scope=["src/**"]
    )
    assert packet["routing"]["tier"] in ["paid-premium", "escalation"]


def test_default_forbidden_paths():
    """Packets should have sensible default forbidden paths."""
    packet = build_packet("Simple task", scope=["src/**"])
    assert ".agent/**" in packet["scope"]["modify_forbidden"]
    assert ".github/**" in packet["scope"]["modify_forbidden"]
    assert "secrets/**" in packet["scope"]["modify_forbidden"]


def test_packet_to_delegation_has_goal_context_model():
    """packet_to_delegation should return valid delegate_task arguments."""
    packet = build_packet("Fix a typo", scope=["README.md"])
    delegation = packet_to_delegation(packet)
    assert "goal" in delegation
    assert "context" in delegation
    assert "model" in delegation


def test_packet_to_delegation_model_string():
    """Model string should combine provider and model."""
    packet = build_packet("Fix a typo", scope=["README.md"])
    delegation = packet_to_delegation(packet)
    assert delegation["model"] is None or "/" in delegation["model"]


def test_packet_to_delegation_contains_mission():
    """The delegation goal should contain the mission description."""
    packet = build_packet("Fix a typo", scope=["README.md"])
    delegation = packet_to_delegation(packet)
    assert "Fix a typo" in delegation["goal"]


def test_acceptance_criteria_included():
    """Acceptance criteria should be preserved in the packet."""
    packet = build_packet(
        "Add rate limiting",
        scope=["src/api/**"],
        acceptance_criteria=[
            "Rate limit headers present in response",
            "Configurable via env var"
        ]
    )
    assert len(packet["acceptance_criteria"]) == 2
    assert "Rate limit headers" in packet["acceptance_criteria"][0]


def test_verification_commands_default():
    """Default verification should run pytest."""
    packet = build_packet("Simple task", scope=["src/**"])
    assert "pytest" in packet["verification"]["commands"][0]