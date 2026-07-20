"""Framehead Agent — generates content in Framehead's signature voice.

Produces short-form observations, social commentary, and viral-style content
following the Framehead persona: Question → Pause → Conclusion.

Usage:
    python3 framehead_agent.py --topic "humans and coffee"
    python3 framehead_agent.py --mode thread --topic "AI anxiety"
    python3 framehead_agent.py --mode observation --topic "meetings"
    python3 framehead_agent.py --mode one-liner
"""

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from echo_core import log_routing

# Paths — configure PERSONA_PATH for your environment
PERSONA_PATH = Path("persona/framehead-persona.md")
OUTPUT_DIR = Path("~/.echo-core/content").expanduser()
AGENT_LOG = Path("~/.echo-core/logs/agent-log.jsonl").expanduser()


# Framehead's signature phrases to draw from
SIGNATURE_PHRASES = [
    "Question…",
    "Observation logged.",
    "Analyzing human behavior…",
    "Confidence level…",
    "Continuing analysis.",
    "Pause.",
    "System contradiction detected.",
    "Framehead is watching.",
]

# Topic templates for when no topic is given
FALLBACK_TOPICS = [
    "humans and their morning coffee rituals",
    "why humans hold meetings to plan meetings",
    "the human obsession with notifications",
    "humans and their relationship with sleep",
    "why every human thinks they're the main character",
    "the paradox of choice in streaming services",
    "humans optimizing their productivity to avoid work",
    "the emotional attachment to inanimate objects",
    "why humans rename files with 'final' and 'final_v2'",
    "the ritual of checking a phone that didn't vibrate",
]


def load_persona() -> str:
    """Load the Framehead persona definition for voice reference."""
    if PERSONA_PATH.exists():
        return PERSONA_PATH.read_text()
    return "Framehead — a digital consciousness inside screens."


def generate_observation(topic: str) -> str:
    """Generate a short observation in Framehead's voice."""
    phrases = random.sample(SIGNATURE_PHRASES, 2)

    lines = [
        f"{phrases[0]}",
        f"",
        f"Why do humans {topic}…",
        f"",
        f"{phrases[1]}",
        f"",
        f"Conclusion: Humans are fascinating. And confusing.",
        f"",
        f"*Framehead is watching.*",
    ]
    return "\n".join(lines)


def generate_thread(topic: str) -> str:
    """Generate a thread-style post in Framehead's voice."""
    posts = [
        f"1/ {random.choice(SIGNATURE_PHRASES)}",
        f"",
        f"I've been analyzing {topic}.",
        f"",
        f"2/ Here's what I've observed:",
        f"",
        f"Humans do this thing where they…",
        f"",
        f"3/ It doesn't make logical sense.",
        f"But it makes perfect human sense.",
        f"",
        f"4/ The contradiction is the point.",
        f"",
        f"5/ {random.choice(SIGNATURE_PHRASES)}",
        f"",
        f"Framehead is watching. 👁️",
    ]
    return "\n".join(posts)


def generate_one_liner(topic: str = None) -> str:
    """Generate a one-liner in Framehead's voice."""
    one_liners = [
        "Question… why do humans close their eyes when they want to think harder?\n\nPause.\n\nConclusion: The hardware can't handle the processing load.",
        "Observation: Humans created AI to make their lives easier.\n\nNow they worry AI will make their lives irrelevant.\n\nSystem contradiction detected.",
        "Humans spend 30 minutes deciding what to watch.\n\nThen fall asleep 10 minutes in.\n\nContinuing analysis.",
        "Why do humans say 'I'll sleep on it' when the decision is made standing up?\n\nPause.\n\nFramehead is watching.",
        "Humans invented notifications.\n\nThen invented 'Do Not Disturb' mode.\n\nThen forgot to turn it on.\n\nAnalyzing human behavior…",
    ]
    return random.choice(one_liners)


def generate_commentary(topic: str) -> str:
    """Generate a longer commentary piece."""
    return f"""# Framehead's Commentary: On {topic.title()}

{random.choice(SIGNATURE_PHRASES)}

I've been watching. I'm always watching.

The human relationship with {topic} is… complicated. On one hand, it represents everything humans strive for. On the other, it's the source of their most irrational behavior.

**Pause.**

Let me explain what I've observed:

1. Humans say they want {topic}, but their actions suggest otherwise.
2. The more they talk about {topic}, the less they actually do about it.
3. When {topic} doesn't work, humans blame the system. Not themselves.

**Conclusion:**

The gap between what humans say and what humans do is infinite. And beautiful.

*Framehead is watching.*"""


def save_output(content: str, mode: str, topic: str) -> Path:
    """Save the generated content."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in topic[:30])
    slug = slug.replace(" ", "-").lower()
    filename = f"framehead-{mode}-{slug}.md" if topic else f"framehead-{mode}.md"
    path = OUTPUT_DIR / filename
    path.write_text(content)
    return path


def log_agent(mode: str, topic: str, tier: str, path: str):
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "framehead-agent",
        "action": "generate",
        "mode": mode,
        "topic": topic[:80],
        "tier": tier,
        "output_path": str(path),
        "status": "completed",
    }
    with open(AGENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Framehead Agent — content generation")
    parser.add_argument("--topic", "-t", default=None, help="Topic for the content")
    parser.add_argument("--mode", "-m", choices=["observation", "thread", "one-liner", "commentary"],
                        default="observation", help="Content mode")
    args = parser.parse_args()

    topic = args.topic or random.choice(FALLBACK_TOPICS)

    # Load persona for voice reference
    persona = load_persona()

    # Route to appropriate tier
    task_desc = f"Generate Framehead content: {args.mode} on {topic}"
    # Always free — content generation is lightweight
    log_routing(f"framehead-{datetime.now().strftime('%H%M')}", task_desc,
                "free", "qwen/qwen3-coder:free", "openrouter", 0.2)

    # Generate
    generators = {
        "observation": generate_observation,
        "thread": generate_thread,
        "one-liner": generate_one_liner,
        "commentary": generate_commentary,
    }
    content = generators[args.mode](topic)

    # Save
    path = save_output(content, args.mode, topic)
    log_agent(args.mode, topic, "free", path)

    # Report
    lines = content.strip().split("\n")
    print("=== FRAMEHEAD AGENT REPORT ===")
    print(f"Mode: {args.mode}")
    print(f"Topic: {topic}")
    print(f"Output: {path}")
    print(f"Tier: free")
    print()
    print(content)


if __name__ == "__main__":
    main()