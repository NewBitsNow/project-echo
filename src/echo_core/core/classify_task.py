"""Task classifier — scores task complexity and routes to the cheapest adequate model tier.

Moved from Project Echo scripts into echo_core.core.
Original: ~/.echo-core/scripts/classify_task.py
"""

import re
import yaml
from pathlib import Path

# Default paths (overridable via ECHO_CORE config)
TIERS_PATH = Path("~/.echo-core/config/model-tiers.yaml").expanduser()

# Heuristic signals that increase complexity (keyword → weight 0.0-1.0)
COMPLEXITY_SIGNALS = {
    "architecture": 0.8,
    "design": 0.7,
    "refactor": 0.6,
    "migrate": 0.7,
    "restructure": 0.7,
    "optimize": 0.5,
    "security": 0.7,
    "database": 0.5,
    "schema": 0.5,
    "deploy": 0.5,
    "pipeline": 0.5,
    "infrastructure": 0.7,
    "api": 0.4,
    "integration": 0.5,
    "test": 0.2,
    "fix": 0.2,
    "typo": 0.05,
    "readme": 0.05,
    "spelling": 0.05,
    "format": 0.1,
    "rename": 0.1,
}

# Task type detection — patterns mapped to task types
TASK_PATTERNS = {
    "simple-edit": [
        r"typo", r"spelling", r"format", r"rename", r"change\s+(a|the)\s+\w+",
        r"fix\s+(a\s+)?(small|minor|tiny|simple)",
    ],
    "read-only": [
        r"what\s+(is|are|does)", r"show\s+me", r"list\s+",
        r"search\s+", r"read\s+", r"check\s+",
    ],
    "architecture": [
        r"architecture", r"design", r"plan\s+", r"strategy",
        r"decision", r"trade.?off",
    ],
    "refactor": [
        r"refactor", r"restructure", r"migrate", r"rewrite", r"clean.?up",
    ],
    "complex-task": [
        r"implement\s+(a\s+)?(complex|full|complete)",
        r"build\s+(a\s+)?(system|service|pipeline|framework)",
        r"multi.?step", r"end.?to.?end",
    ],
}


def classify_task(task_description: str) -> dict:
    """Classify a task by complexity and determine the appropriate model tier.

    Args:
        task_description: Natural language description of the task.

    Returns:
        dict with keys: tier, complexity, task_type, model, provider.
        If no suitable tier is found, returns escalation tier with model=None.
    """
    task_lower = task_description.lower()
    word_count = len(task_description.split())

    # Calculate complexity score (0.0 - 1.0)
    complexity = 0.0

    for signal, weight in COMPLEXITY_SIGNALS.items():
        if signal in task_lower:
            complexity += weight

    # Length signals
    if word_count > 150:
        complexity += 0.5
    elif word_count > 50:
        complexity += 0.3

    complexity = min(complexity, 1.0)

    # Detect task type from patterns
    task_type = "unknown"
    for ttype, patterns in TASK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, task_lower):
                task_type = ttype
                break
        if task_type != "unknown":
            break

    # Load tiers and find the best match
    if not TIERS_PATH.exists():
        # Default routing if no config file
        if complexity <= 0.3:
            return {
                "tier": "free", "complexity": round(complexity, 2),
                "task_type": task_type, "model": "qwen/qwen3-coder:free",
                "provider": "openrouter",
            }
        elif complexity <= 0.6:
            return {
                "tier": "paid-cheap", "complexity": round(complexity, 2),
                "task_type": task_type, "model": "qwen/qwen3-coder",
                "provider": "openrouter",
            }
        else:
            return {
                "tier": "paid-premium", "complexity": round(complexity, 2),
                "task_type": task_type, "model": "anthropic/claude-sonnet-4",
                "provider": "openrouter",
            }

    with open(TIERS_PATH) as f:
        tiers = yaml.safe_load(f)["tiers"]

    # Try to match task type to a tier's suitable_for list
    for tier in tiers:
        if task_type in tier.get("suitable_for", []):
            max_complexity = 1.0 - tier["confidence_threshold"] + 0.3
            if complexity <= max_complexity:
                model_info = tier["models"][0] if tier["models"] else {}
                return {
                    "tier": tier["name"],
                    "complexity": round(complexity, 2),
                    "task_type": task_type,
                    "model": model_info.get("model"),
                    "provider": model_info.get("provider"),
                }

    # Fallback: find the cheapest tier that can handle this complexity
    for tier in tiers:
        if tier["name"] == "escalation":
            continue
        threshold = 1.0 - tier["confidence_threshold"]
        if complexity <= threshold + 0.3:
            model_info = tier["models"][0] if tier["models"] else {}
            return {
                "tier": tier["name"],
                "complexity": round(complexity, 2),
                "task_type": task_type,
                "model": model_info.get("model"),
                "provider": model_info.get("provider"),
            }

    # Nothing could handle it — escalate to human
    return {
        "tier": "escalation", "complexity": round(complexity, 2),
        "task_type": task_type, "model": None, "provider": None,
    }


def set_tiers_path(path: str):
    """Override the default tiers config path."""
    global TIERS_PATH
    TIERS_PATH = Path(path).expanduser()