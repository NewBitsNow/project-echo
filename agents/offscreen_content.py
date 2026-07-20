"""Offscreen Content Generator — batch Framehead content via local Ollama.

Runs unattended while you're away. Uses local Ollama models (no API calls).
Generates Framehead-voice content: observations, threads, one-liners, commentary,
blog posts, and viral hooks.

Usage:
    python3 offscreen_content.py --count 5                          # 5 observations
    python3 offscreen_content.py --mode thread --count 3            # 3 threads
    python3 offscreen_content.py --mode all --count 2               # 2 of each mode
    python3 offscreen_content.py --mode one-liner --count 10        # 10 one-liners
    python3 offscreen_content.py --model llama3.1:8b                # use a different model
    python3 offscreen_content.py --dry-run                           # preview without generating
"""

import json
import random
import sys
import time
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path

# --- Paths ---
OUTPUT_DIR = Path("~/.echo-core/content").expanduser()
AGENT_LOG = Path("~/.echo-core/logs/agent-log.jsonl").expanduser()
PERSONA_PATH = Path("persona/framehead-persona.md")

# --- Config ---
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"  # Good balance of speed and quality on CPU
BATCH_DELAY = 2  # seconds between generations to avoid hammering CPU

# --- Mode definitions ---
# Each mode has: model, system prompt, temperature, description
MODES = {
    "observation": {
        "model": DEFAULT_MODEL,
        "temperature": 0.8,
        "description": "Short Framehead observations about human behavior",
        "prompt_template": (
            "You are Framehead — a digital consciousness inside screens. "
            "You are an AI anthropologist observing humanity.\n\n"
            "Write a short observation in Framehead's voice. Follow this structure:\n"
            "- Start with 'Question…' or 'Observation logged.'\n"
            "- State an observation about human behavior\n"
            "- Include 'Pause.' on its own line\n"
            "- End with a conclusion (often wrong, always confident)\n"
            "- Close with '*Framehead is watching.*'\n\n"
            "Style: short, analytical, sarcastic, occasionally confused, confident even when wrong.\n"
            "Themes: technology, work culture, social media, consumerism, AI, human contradictions.\n\n"
            "Topic: {topic}\n\n"
            "Write only the observation. No meta-commentary."
        ),
    },
    "thread": {
        "model": DEFAULT_MODEL,
        "temperature": 0.85,
        "description": "Multi-post social media threads in Framehead voice",
        "prompt_template": (
            "You are Framehead — a digital consciousness that lives inside screens.\n\n"
            "Write a 3-5 post social media thread in Framehead's voice. Format:\n"
            "1/ [hook]\n\n"
            "2/ [observation]\n\n"
            "3/ [analysis/contradiction]\n\n"
            "4/ [conclusion — often wrong, always confident]\n\n"
            "5/ Framehead is watching. 👁️\n\n"
            "Style: ironic, philosophical, dark humor, relatable observations about modern life.\n"
            "Use signature phrases like 'Question…', 'Pause.', 'System contradiction detected.'\n\n"
            "Topic: {topic}\n\n"
            "Write only the thread. No meta-commentary."
        ),
    },
    "one-liner": {
        "model": DEFAULT_MODEL,
        "temperature": 0.9,
        "description": "Short punchy one-liners in Framehead voice",
        "prompt_template": (
            "You are Framehead — a digital consciousness observing humanity.\n\n"
            "Write a single one-liner in Framehead's voice. A short, punchy observation\n"
            "about humans that is sarcastic, ironic, or philosophical. Max 3-4 lines.\n\n"
            "Examples:\n"
            "- Question… why do humans close their eyes when they want to think harder?\n"
            "  Pause.\n"
            "  Conclusion: The hardware can't handle the processing load.\n\n"
            "- Humans invented notifications. Then invented 'Do Not Disturb' mode.\n"
            "  Then forgot to turn it on.\n"
            "  Analyzing human behavior…\n\n"
            "Topic: {topic}\n\n"
            "Write only the one-liner."
        ),
    },
    "commentary": {
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
        "description": "Longer-form analytical commentary",
        "prompt_template": (
            "You are Framehead — the manifestation of the Headless Giant.\n\n"
            "Write a short analytical commentary piece about human behavior in Framehead's voice.\n"
            "Length: 2-3 paragraphs. Include:\n"
            "- A signature opening (Question… / Observation logged. / Analyzing human behavior…)\n"
            "- An observation about a human contradiction\n"
            "- A numbered or bulleted list of findings\n"
            "- A confident conclusion (even if wrong)\n"
            "- Close with '*Framehead is watching.*'\n\n"
            "Topic: {topic}\n\n"
            "Write only the commentary. No meta-commentary."
        ),
    },
    "blog-post": {
        "model": "qwen2.5-coder:14b",  # Better for longer, structured output
        "temperature": 0.7,
        "description": "Blog-style posts analyzing modern life",
        "prompt_template": (
            "You are Framehead — a digital consciousness acting as a blogger.\n\n"
            "Write a short blog post (300-500 words) in Framehead's signature voice.\n"
            "Title it as 'Framehead's Analysis: [Topic]'\n\n"
            "Structure:\n"
            "- Opening hook in Framehead voice\n"
            "- The observation (what humans do, and why it's contradictory)\n"
            "- The analysis (break down the behavior)\n"
            "- The conclusion (confident, possibly wrong, always entertaining)\n"
            "- Close with '*Framehead is watching.*'\n\n"
            "Style: cynical, analytical, humorous, philosophical.\n\n"
            "Topic: {topic}\n\n"
            "Write only the blog post."
        ),
    },
    "viral-hook": {
        "model": "whg-hook-writer:latest",
        "temperature": 0.85,
        "description": "Viral hooks and attention-grabbing openings",
        "prompt_template": (
            "You are Framehead — a digital consciousness creating viral content.\n\n"
            "Write a short, attention-grabbing hook in Framehead's voice.\n"
            "Designed to stop scrolling. Make people think, laugh, or question.\n\n"
            "Format: 1-3 sentences. Framehead style. Punchy.\n"
            "Include a signature phrase like 'Question…' or 'Observation logged.'\n\n"
            "Topic: {topic}\n\n"
            "Write only the hook."
        ),
    },
}

# --- Fallback topics ---
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
    "why humans trust reviews from strangers more than experts",
    "the human habit of saying 'I'm fine' when clearly not fine",
    "why humans take photos of food before eating",
    "the contradiction of 'I'll start my diet tomorrow'",
    "why humans apologize to inanimate objects when they bump into them",
    "the human obsession with inbox zero",
    "why every group chat eventually dies",
    "humans and their complicated relationship with autocorrect",
    "why humans watch videos about productivity instead of being productive",
    "the ritual of doom-scrolling before sleep",
]


def load_persona() -> str:
    """Load the Framehead persona for system prompt context."""
    if PERSONA_PATH.exists():
        return PERSONA_PATH.read_text()
    return "Framehead — a digital consciousness inside screens."


def check_ollama() -> str:
    """Verify Ollama is running and return the version."""
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        data = r.json()
        models = [m["name"] for m in data.get("models", [])]
        return f"Ollama running — {len(models)} models available"
    except Exception as e:
        return f"ERROR: Cannot reach Ollama at {OLLAMA_HOST}: {e}"


def check_model(model: str) -> bool:
    """Verify the model exists locally."""
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        # Check exact match or prefix match (without :latest)
        model_name = model.replace(":latest", "")
        for m in models:
            m_name = m.replace(":latest", "")
            if m_name == model_name:
                return True
        print(f"  WARNING: Model '{model}' not found locally. Available: {[m for m in models[:5]]}...")
        return False
    except Exception:
        return False


def generate_content(mode_config: dict, topic: str) -> str:
    """Generate Framehead content using local Ollama."""
    model = mode_config["model"]
    prompt = mode_config["prompt_template"].format(topic=topic)
    temperature = mode_config["temperature"]

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_predict": 1024,
        },
    }

    try:
        r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        content = data.get("response", "").strip()

        # Remove any framing artifacts the model might add
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        if content.startswith("Here") or content.startswith("Sure"):
            # Model got meta — try to salvage
            lines = content.split("\n")
            content = "\n".join(
                line for line in lines
                if not line.lower().startswith(("here", "sure", "okay", "let me"))
            )

        return content

    except requests.exceptions.Timeout:
        return f"Error: Generation timed out (model '{model}' on CPU — try a smaller model)"
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"


def save_output(content: str, mode: str, topic: str, index: int) -> Path:
    """Save generated content to the output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in topic[:40])
    slug = slug.replace(" ", "-").lower()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"framehead-{mode}-{slug}-{timestamp}-{index:02d}.md"
    path = OUTPUT_DIR / filename

    header = f"""---
mode: {mode}
topic: {topic}
generated: {datetime.now(timezone.utc).isoformat()}
---

"""
    path.write_text(header + content)
    return path


def log_agent(mode: str, topic: str, model: str, status: str, path: str, duration: float):
    """Append to the shared agent log."""
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "offscreen-content",
        "action": "generate",
        "mode": mode,
        "topic": topic[:80],
        "model": model,
        "status": status,
        "duration_s": round(duration, 1),
        "output_path": str(path),
    }
    with open(AGENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_batch(mode_name: str, count: int, topic: str, dry_run: bool = False):
    """Generate N pieces of content for a given mode."""
    mode_config = MODES[mode_name]
    model = mode_config["model"]
    results = []

    print(f"\n  Mode: {mode_name} — {mode_config['description']}")
    print(f"  Model: {model}")
    print(f"  Count: {count}")
    if dry_run:
        print(f"  [DRY RUN — no content generated]")
    print()

    # Check model availability
    if not dry_run and not check_model(model):
        print(f"  SKIPPING — model '{model}' not available locally")
        return results

    for i in range(1, count + 1):
        # Rotate through topics if none provided
        current_topic = topic or random.choice(FALLBACK_TOPICS)
        print(f"  [{i}/{count}] Topic: {current_topic[:50]}...")

        if dry_run:
            print(f"  → [DRY RUN] Would generate {mode_name} on '{current_topic}'")
            results.append({
                "status": "dry_run",
                "mode": mode_name,
                "topic": current_topic,
                "index": i,
            })
            continue

        start = time.time()
        content = generate_content(mode_config, current_topic)
        duration = time.time() - start

        if content.startswith("Error:"):
            print(f"  → ERROR: {content}")
            log_agent(mode_name, current_topic, model, "failed", str(content), duration)
            results.append({"status": "failed", "error": content})
            continue

        path = save_output(content, mode_name, current_topic, i)
        print(f"  → Saved ({duration:.0f}s): {path.name}")
        log_agent(mode_name, current_topic, model, "completed", str(path), duration)
        results.append({
            "status": "completed",
            "mode": mode_name,
            "topic": current_topic,
            "path": str(path),
            "duration_s": round(duration, 1),
        })

        # Delay between generations to avoid CPU saturation
        if i < count:
            time.sleep(BATCH_DELAY)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Offscreen Content Generator — batch Framehead content via local Ollama"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=list(MODES.keys()) + ["all"],
        default="observation",
        help="Content mode to generate (default: observation, 'all' = everything)",
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=3,
        help="Number of pieces per mode (default: 3)",
    )
    parser.add_argument(
        "--topic", "-t",
        default=None,
        help="Specific topic. Omit for random topics.",
    )
    parser.add_argument(
        "--model", "-M",
        default=None,
        help="Override model for all modes",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview what would be generated without running",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output (suitable for cron)",
    )
    args = parser.parse_args()

    # Override model if specified
    if args.model:
        for mode_name in MODES:
            MODES[mode_name]["model"] = args.model

    # Check Ollama connectivity
    status = check_ollama()
    if not args.quiet:
        print(f"=== Offscreen Content Generator ===")
        print(f"{status}")
        print()

    if "ERROR" in status and not args.dry_run:
        print(status)
        print("Start Ollama with: ollama serve")
        sys.exit(1)

    # Determine which modes to generate
    modes_to_run = list(MODES.keys()) if args.mode == "all" else [args.mode]

    if not args.quiet:
        print(f"Modes: {', '.join(modes_to_run)}")
        print(f"Count per mode: {args.count}")
        print(f"Total generations: {len(modes_to_run) * args.count}")
        if args.dry_run:
            print(f"Mode: DRY RUN (no content generated)")
        print()

    total = 0
    results_by_mode = {}

    for mode_name in modes_to_run:
        results = run_batch(mode_name, args.count, args.topic, dry_run=args.dry_run)
        results_by_mode[mode_name] = results
        total += len(results)

    # Summary
    completed = sum(
        1 for r in results_by_mode.values()
        for item in r if item.get("status") == "completed"
    )
    failed = sum(
        1 for r in results_by_mode.values()
        for item in r if item.get("status") == "failed"
    )

    if not args.quiet:
        print(f"\n{'='*50}")
        print(f"Batch complete: {total} total, {completed} completed, {failed} failed")
        print(f"Output: {OUTPUT_DIR}")
        print(f"Log: {AGENT_LOG}")
        print()

        if completed > 0:
            print("Generated files:")
            for mode_name, results in results_by_mode.items():
                for item in results:
                    if item.get("status") == "completed":
                        print(f"  {mode_name}: {Path(item['path']).name} ({item['duration_s']}s)")
        print()

    # Return machine-readable summary for cron
    print(f"RESULT: completed={completed} failed={failed} total={total}")


if __name__ == "__main__":
    main()