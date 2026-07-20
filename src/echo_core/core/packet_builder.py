"""Packet builder — constructs structured Agent Packets for domain agent delegation.

Inspired by ACP's Agent Packet Protocol (APP). Produces a standardized work unit
with mission, routing, scope boundaries, and verification steps.

Moved from Project Echo scripts into echo_core.core.
Original: ~/.echo-core/scripts/packet_builder.py
"""

from echo_core.core.classify_task import classify_task


def build_packet(
    mission: str,
    scope: list = None,
    forbidden: list = None,
    verification_commands: list = None,
    acceptance_criteria: list = None,
) -> dict:
    """Build a structured Agent Packet with routing, scope, and verification.

    Args:
        mission: Description of the task to accomplish.
        scope: List of glob patterns for files the agent may modify.
        forbidden: List of glob patterns the agent must NOT touch.
        verification_commands: Shell commands to verify the work.
        acceptance_criteria: List of criteria that define done.

    Returns:
        A dict with keys: mission, routing, scope, verification, acceptance_criteria.
    """
    routing = classify_task(mission)

    if scope is None:
        scope = ["src/**", "tests/**"]

    packet = {
        "mission": mission,
        "routing": {
            "tier": routing["tier"],
            "model": routing["model"],
            "provider": routing["provider"],
            "complexity": routing["complexity"],
            "task_type": routing["task_type"],
        },
        "scope": {
            "modify_allowed": scope,
            "modify_forbidden": forbidden or [
                ".agent/**", ".github/**", "secrets/**"],
        },
        "verification": {
            "commands": verification_commands or [
                "python -m pytest tests/ -q"],
        },
        "acceptance_criteria": acceptance_criteria or [],
    }

    return packet


def packet_to_delegation(packet: dict) -> dict:
    """Convert a packet into arguments suitable for delegate_task.

    Returns a dict with 'goal', 'context', and 'model' keys.
    """
    model_str = (
        f"{packet['routing']['provider']}/{packet['routing']['model']}"
        if packet['routing']['model'] and packet['routing']['provider']
        else None
    )

    forbidden_str = ", ".join(packet['scope']['modify_forbidden'])

    criteria_lines = "\n".join(
        f"- {c}" for c in packet['acceptance_criteria']
    ) if packet['acceptance_criteria'] else "None specified"

    context = f"""# Agent Packet

## Mission
{packet['mission']}

## Routing
- Tier: {packet['routing']['tier']}
- Model: {packet['routing']['model']}
- Complexity: {packet['routing']['complexity']}

## Scope
- Allowed: {', '.join(packet['scope']['modify_allowed'])}
- Forbidden: {forbidden_str}

## Verification
- Commands: {', '.join(packet['verification']['commands'])}

## Acceptance Criteria
{criteria_lines}
"""

    return {
        "goal": f"Execute packet: {packet['mission']}",
        "context": context,
        "model": model_str,
    }