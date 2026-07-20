"""Night Shift — the persistent background goal engine.

Runs during off-hours (01:00-09:00 by default), one task per invocation.
Rotates through content generation, clip creation, research, catalog updates,
health checks, and reel compilation.

Designed to be fired by the orchestrator cron job each hour during idle windows.

Usage:
    python3 night_shift.py                    # run one task
    python3 night_shift.py --dry-run          # preview what would happen
    python3 night_shift.py --force            # run even outside off-hours
    python3 night_shift.py --status           # show state + available stock
    python3 night_shift.py --reset            # reset state counters
"""

import json
import random
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──

TWIN_OUTPUT = Path("~/.echo-core").expanduser()
SCRIPTS_DIR = TWIN_OUTPUT / "scripts"
STATE_FILE = TWIN_OUTPUT / "state" / "night-shift-state.json"
CONTENT_DIR = TWIN_OUTPUT / "content"
SHORTS_DIR = CONTENT_DIR / "framehead-shorts"
IMAGES_DIR = CONTENT_DIR / "framehead-images"
RESEARCH_DIR = TWIN_OUTPUT / "research"
LOGS_DIR = TWIN_OUTPUT / "logs"
AGENT_LOG = LOGS_DIR / "agent-log.jsonl"

# ── Config ──

OFF_HOURS_START = 1   # 1:00 AM
OFF_HOURS_END = 9     # 9:00 AM

# How many unused clips before we can compile a reel
MIN_CLIPS_FOR_REEL = 4
# Target reel duration in seconds
REEL_TARGET_DURATION = 90
# Tasks in rotation order
TASK_ROTATION = [
    "generate_observation",
    "generate_oneliner",
    "update_catalog",
    "generate_clip",
    "generate_observation",
    "generate_thread",
    "update_catalog",
    "generate_clip",
    "research_sweep",
    "generate_commentary",
    "generate_clip",
    "health_check",
]

# ── Default state ──

DEFAULT_STATE = {
    "twin_id": "echo-core-v0",
    "night_shift_version": 1,
    "enabled": True,
    "off_hours_start": OFF_HOURS_START,
    "off_hours_end": OFF_HOURS_END,
    "last_task_index": -1,  # -1 means none yet
    "tasks_completed": {},
    "total_tasks_completed": 0,
    "clips_generated": 0,
    "clips_used_in_reels": 0,
    "compilations_complete": 0,
    "last_compilation": None,
    "last_task_time": None,
    "last_task_name": None,
    "current_reel_id": None,
    "research_topics_used": [],
}


# ── State management ──


def load_state() -> dict:
    """Load the night shift state file, creating defaults if missing."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            # Ensure all default keys exist
            for k, v in DEFAULT_STATE.items():
                state.setdefault(k, v)
            return state
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_STATE)


def save_state(state: dict):
    """Persist the night shift state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def record_task(state: dict, task_name: str):
    """Update state after completing a task."""
    state["last_task_index"] = (state["last_task_index"] + 1) % len(TASK_ROTATION)
    state["last_task_name"] = task_name
    state["last_task_time"] = datetime.now(timezone.utc).isoformat()
    state["total_tasks_completed"] += 1

    tasks = state.setdefault("tasks_completed", {})
    tasks[task_name] = tasks.get(task_name, 0) + 1

    save_state(state)


# ── Time checks ──


def is_off_hours(state: dict = None) -> bool:
    """Check if the current time is within the off-hours window."""
    if state is None:
        state = load_state()
    now = datetime.now()
    hour = now.hour
    start = state.get("off_hours_start", OFF_HOURS_START)
    end = state.get("off_hours_end", OFF_HOURS_END)

    if start <= end:
        return start <= hour < end
    else:
        # Wraps around midnight (e.g. 22:00 - 06:00)
        return hour >= start or hour < end


def minutes_until_off_hours(state: dict = None) -> int:
    """How many minutes until the next off-hours window opens."""
    if state is None:
        state = load_state()
    now = datetime.now()
    start = state.get("off_hours_start", OFF_HOURS_START)
    current_hour = now.hour

    if current_hour < start:
        # Later today
        target = now.replace(hour=start, minute=0, second=0, microsecond=0)
    else:
        # Tomorrow
        from datetime import timedelta
        target = (now + timedelta(days=1)).replace(
            hour=start, minute=0, second=0, microsecond=0
        )

    diff = (target - now).total_seconds()
    return max(0, int(diff // 60))


# ── Stockpile counting ──


def count_clips() -> list[Path]:
    """Count unused Shorts MP4 files (excludes audio temp files)."""
    shorts = sorted(SHORTS_DIR.glob("framehead-short-*.mp4"))
    return shorts


def count_images() -> int:
    """Count available Framehead images."""
    return len(list(IMAGES_DIR.glob("framehead-*.png")))


def count_content() -> dict:
    """Count generated content by mode."""
    counts = Counter()
    for f in CONTENT_DIR.glob("framehead-*.md"):
        parts = f.name.split("-")
        if len(parts) >= 2:
            mode = parts[1]
            counts[mode] += 1
    return dict(counts)


# ── Task implementations ──


def task_generate_observation(state: dict, dry_run: bool = False) -> dict:
    """Generate one Framehead observation via Ollama."""
    print("  Task: generate observation")
    if dry_run:
        return {"task": "generate_observation", "status": "dry_run"}

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "offscreen_content.py"),
         "--mode", "observation", "--count", "1", "--quiet"],
        capture_output=True, text=True, timeout=300,
    )
    ok = result.returncode == 0
    print(f"    {'OK' if ok else 'FAILED'}: {result.stdout.strip()[-100:]}")
    return {"task": "generate_observation", "status": "completed" if ok else "failed"}


def task_generate_oneliner(state: dict, dry_run: bool = False) -> dict:
    """Generate one Framehead one-liner via Ollama."""
    print("  Task: generate one-liner")
    if dry_run:
        return {"task": "generate_oneliner", "status": "dry_run"}

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "offscreen_content.py"),
         "--mode", "one-liner", "--count", "1", "--quiet"],
        capture_output=True, text=True, timeout=300,
    )
    ok = result.returncode == 0
    print(f"    {'OK' if ok else 'FAILED'}: {result.stdout.strip()[-100:]}")
    return {"task": "generate_oneliner", "status": "completed" if ok else "failed"}


def task_generate_thread(state: dict, dry_run: bool = False) -> dict:
    """Generate one Framehead thread via Ollama."""
    print("  Task: generate thread")
    if dry_run:
        return {"task": "generate_thread", "status": "dry_run"}

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "offscreen_content.py"),
         "--mode", "thread", "--count", "1", "--quiet"],
        capture_output=True, text=True, timeout=300,
    )
    ok = result.returncode == 0
    print(f"    {'OK' if ok else 'FAILED'}: {result.stdout.strip()[-100:]}")
    return {"task": "generate_thread", "status": "completed" if ok else "failed"}


def task_generate_commentary(state: dict, dry_run: bool = False) -> dict:
    """Generate one Framehead commentary via Ollama."""
    print("  Task: generate commentary")
    if dry_run:
        return {"task": "generate_commentary", "status": "dry_run"}

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "offscreen_content.py"),
         "--mode", "commentary", "--count", "1", "--quiet"],
        capture_output=True, text=True, timeout=300,
    )
    ok = result.returncode == 0
    print(f"    {'OK' if ok else 'FAILED'}: {result.stdout.strip()[-100:]}")
    return {"task": "generate_commentary", "status": "completed" if ok else "failed"}


def task_update_catalog(state: dict, dry_run: bool = False) -> dict:
    """Scan images and update the image catalog."""
    print("  Task: update image catalog")
    if dry_run:
        return {"task": "update_catalog", "status": "dry_run"}

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "framehead_image_catalog.py"),
         "--stats"],
        capture_output=True, text=True, timeout=30,
    )
    ok = result.returncode == 0
    if ok:
        # Extract image count from output
        for line in result.stdout.split("\n"):
            if "Total images:" in line:
                print(f"    {line.strip()}")
    else:
        print(f"    FAILED: {result.stderr.strip()[-200:]}")
    return {"task": "update_catalog", "status": "completed" if ok else "failed"}


def task_generate_clip(state: dict, dry_run: bool = False) -> dict:
    """Generate one Shorts clip from existing content and images."""
    print("  Task: generate clip")
    if dry_run:
        return {"task": "generate_clip", "status": "dry_run"}

    # Pick a mode randomly from available content
    content_counts = count_content()
    available_modes = [m for m in ["one-liner", "observation"] if content_counts.get(m, 0) > 0]
    mode = random.choice(available_modes) if available_modes else "one-liner"

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "shorts_generator.py"),
         "--mode", mode, "--batch", "1", "--quiet"],
        capture_output=True, text=True, timeout=300,
    )
    ok = result.returncode == 0
    if ok:
        state["clips_generated"] = state.get("clips_generated", 0) + 1
        save_state(state)
        print(f"    OK — clips generated: {state['clips_generated']}")
    else:
        print(f"    FAILED: {result.stderr.strip()[-200:]}")
    return {"task": "generate_clip", "status": "completed" if ok else "failed"}


def task_research_sweep(state: dict, dry_run: bool = False) -> dict:
    """Run a research sweep on a rotating topic."""
    topics = [
        "multi-agent AI systems",
        "local LLM deployment",
        "AI safety and alignment",
        "autonomous agents",
        "model compression quantization",
        "reinforcement learning from human feedback",
        "edge AI inference",
        "digital twin architectures",
    ]

    used = state.get("research_topics_used", [])
    available = [t for t in topics if t not in used]
    if not available:
        available = topics  # cycle back
        used = []

    topic = random.choice(available)
    print(f"  Task: research sweep — '{topic}'")
    if dry_run:
        return {"task": "research_sweep", "topic": topic, "status": "dry_run"}

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "research_agent.py"),
         topic, "--max", "3", "--sources", "arxiv"],
        capture_output=True, text=True, timeout=60,
    )
    ok = result.returncode == 0

    # Update used topics
    used.append(topic)
    state["research_topics_used"] = used[-len(topics):]
    save_state(state)

    print(f"    {'OK' if ok else 'FAILED'}: {result.stdout.strip()[-150:]}")
    return {"task": "research_sweep", "topic": topic, "status": "completed" if ok else "failed"}


def task_health_check(state: dict, dry_run: bool = False) -> dict:
    """Quick system health check — disk, git, stockpile."""
    print("  Task: health check")

    if dry_run:
        return {"task": "health_check", "status": "dry_run"}

    clips = count_clips()
    images = count_images()
    content = count_content()
    total_content = sum(content.values())

    print(f"    Clips stockpiled: {len(clips)}")
    print(f"    Images available: {images}")
    print(f"    Content pieces:   {total_content}")
    print(f"    Tasks completed:  {state.get('total_tasks_completed', 0)}")

    # Check disk
    import shutil
    disk = shutil.disk_usage(IMAGES_DIR)
    free_gb = disk.free // (1024**3)
    print(f"    Disk free:        {free_gb} GB")

    # Log health
    log_entry(state, "health_check", {
        "clips": len(clips),
        "images": images,
        "content": total_content,
        "free_gb": free_gb,
    })

    return {
        "task": "health_check", "status": "completed",
        "clips": len(clips), "images": images,
        "content": total_content, "free_gb": free_gb,
    }


# ── Reel compilation ──


def compile_reel(state: dict, dry_run: bool = False) -> dict:
    """Compile stockpiled clips into a longer reel video.

    Takes the oldest N unused clips, concatenates them with crossfade,
    adds intro/outro cards, and outputs a single MP4.
    """
    clips = count_clips()
    unused_clips = clips  # For now, all clips are "unused"

    if len(unused_clips) < MIN_CLIPS_FOR_REEL:
        print(f"  Not enough clips for a reel ({len(unused_clips)} < {MIN_CLIPS_FOR_REEL})")
        return {"task": "compile_reel", "status": "skipped", "reason": "not_enough_clips"}

    if dry_run:
        print(f"  Would compile {min(6, len(unused_clips))} clips into a reel")
        return {"task": "compile_reel", "status": "dry_run"}

    # Pick oldest N clips (up to 6 for a ~90s reel)
    clip_count = min(6, len(unused_clips))
    selected = unused_clips[:clip_count]

    print(f"  Compiling {clip_count} clips into reel...")

    # Create a temporary file list for ffmpeg concat
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for clip in selected:
            f.write(f"file '{clip}'\n")
        filelist = f.name

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = CONTENT_DIR / "framehead-reels" / f"framehead-reel-{timestamp}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Build ffmpeg concat command with crossfade transitions
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", filelist,
            "-c", "copy",  # Stream copy since all clips are same format
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            size_kb = output_path.stat().st_size // 1024
            print(f"    Reel created: {output_path.name} ({size_kb} KB)")

            # Update state
            state["clips_used_in_reels"] = state.get("clips_used_in_reels", 0) + clip_count
            state["compilations_complete"] = state.get("compilations_complete", 0) + 1
            state["last_compilation"] = datetime.now(timezone.utc).isoformat()
            save_state(state)

            # Log
            log_entry(state, "compile_reel", {
                "clips_used": clip_count,
                "output": str(output_path),
                "size_kb": size_kb,
            })

            return {
                "task": "compile_reel", "status": "completed",
                "clips_used": clip_count, "output": str(output_path),
            }
        else:
            print(f"    FAILED: {result.stderr.strip()[-200:]}")
            return {"task": "compile_reel", "status": "failed", "error": result.stderr.strip()[-200:]}

    except Exception as e:
        print(f"    ERROR: {e}")
        return {"task": "compile_reel", "status": "failed", "error": str(e)}
    finally:
        import os
        os.unlink(filelist)


# ── Dispatch ──

TASK_MAP = {
    "generate_observation": task_generate_observation,
    "generate_oneliner": task_generate_oneliner,
    "generate_thread": task_generate_thread,
    "generate_commentary": task_generate_commentary,
    "update_catalog": task_update_catalog,
    "generate_clip": task_generate_clip,
    "research_sweep": task_research_sweep,
    "health_check": task_health_check,
}


def run_next_task(state: dict, dry_run: bool = False) -> dict:
    """Run the next task in the rotation."""
    idx = state.get("last_task_index", -1) + 1
    if idx >= len(TASK_ROTATION):
        idx = 0

    task_name = TASK_ROTATION[idx]
    print(f"\n{'='*60}")
    print(f"  Night Shift — Task {idx + 1}/{len(TASK_ROTATION)}")
    print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    task_fn = TASK_MAP.get(task_name)
    if not task_fn:
        print(f"  Unknown task: {task_name}")
        return {"task": task_name, "status": "unknown"}

    result = task_fn(state, dry_run=dry_run)

    if not dry_run:
        record_task(state, task_name)

    return result


def run_reel_check(state: dict, dry_run: bool = False) -> dict:
    """Check if it's time to compile a reel and do it."""
    clips = count_clips()
    if len(clips) >= MIN_CLIPS_FOR_REEL:
        # Only compile if we haven't done one recently
        last = state.get("last_compilation")
        if last:
            from datetime import datetime as dt
            try:
                last_time = dt.fromisoformat(last)
                hours_since = (datetime.now() - last_time.replace(tzinfo=None)).total_seconds() / 3600
                if hours_since < 6:
                    return {"task": "compile_reel", "status": "skipped",
                            "reason": f"recent compilation ({hours_since:.0f}h ago)"}
            except (ValueError, TypeError):
                pass

        return compile_reel(state, dry_run=dry_run)

    return {"task": "compile_reel", "status": "skipped", "reason": "not_enough_clips"}


# ── Logging ──


def log_entry(state: dict, action: str, details: dict = None):
    """Append a night shift entry to the agent log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "night-shift",
        "action": action,
        "total_tasks": state.get("total_tasks_completed", 0),
    }
    if details:
        entry.update(details)
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AGENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Status report ──


def print_status():
    """Print a full status report of the night shift system."""
    state = load_state()
    clips = count_clips()
    images = count_images()
    content = count_content()
    total_content = sum(content.values())

    print(f"\n{'='*60}")
    print(f"  NIGHT SHIFT STATUS")
    print(f"{'='*60}")
    print(f"  Enabled:       {state.get('enabled', True)}")
    print(f"  Off-hours:     {state.get('off_hours_start', 1):02d}:00 - {state.get('off_hours_end', 9):02d}:00")
    print(f"  Current time:  {datetime.now().strftime('%H:%M')}")
    print(f"  In window:     {'YES' if is_off_hours(state) else 'NO'}")
    divider = "=" * 50
    print(f"  {divider}")
    print(f"  Tasks done:    {state.get('total_tasks_completed', 0)}")
    print(f"  Last task:     {state.get('last_task_name', 'none')}")
    last_run = state.get('last_task_time', 'never')
    print(f"  Last run:      {last_run[:19] if isinstance(last_run, str) and last_run != 'never' else last_run}")
    print(f"  {divider}")
    print(f"  Stockpile:")
    print(f"    Video clips:     {len(clips)}")
    print(f"    Images:          {images}")
    print(f"    Content pieces:  {total_content}")
    for mode, count in sorted(content.items()):
        print(f"      {mode}: {count}")
    print(f"  {divider}")
    print(f"  Reels compiled:  {state.get('compilations_complete', 0)}")
    print(f"  Clips used:      {state.get('clips_used_in_reels', 0)}")
    if state.get("last_compilation"):
        print(f"  Last reel:       {state['last_compilation'][:19]}")
    print(f"  {divider}")
    print(f"  Disk: {IMAGES_DIR}")
    import shutil
    disk = shutil.disk_usage(IMAGES_DIR)
    free_gb = disk.free // (1024**3)
    total_gb = disk.total // (1024**3)
    print(f"    {free_gb} GB free / {total_gb} GB total")
    print()


# ── Main ──


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Night Shift — persistent background goal engine for Project Echo"
    )
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview what would happen without doing anything")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Run even outside off-hours window")
    parser.add_argument("--status", "-s", action="store_true",
                        help="Show status report and exit")
    parser.add_argument("--reset", action="store_true",
                        help="Reset all state counters")
    parser.add_argument("--reel", action="store_true",
                        help="Force reel compilation check")
    parser.add_argument("--task", "-t",
                        help="Run a specific task by name (bypasses rotation)")
    parser.add_argument("--once", action="store_true",
                        help="Run one task and exit (default behavior)")
    args = parser.parse_args()

    state = load_state()

    # Handle special flags
    if args.reset:
        save_state(dict(DEFAULT_STATE))
        print("State reset to defaults.")
        return

    if args.status:
        print_status()
        return

    # Check off-hours window
    if not args.force and not is_off_hours(state):
        mins = minutes_until_off_hours(state)
        print(f"Not in off-hours window ({OFF_HOURS_START}:00-{OFF_HOURS_END}:00).")
        print(f"Next window opens in ~{mins} minutes.")
        print("Use --force to run anyway, or --status to check state.")
        return

    if not state.get("enabled", True):
        print("Night shift is disabled. Enable by setting enabled=true in state file.")
        return

    # Run specific task or rotation
    if args.task:
        task_fn = TASK_MAP.get(args.task)
        if not task_fn:
            print(f"Unknown task: {args.task}")
            print(f"Available: {', '.join(sorted(TASK_MAP.keys()))}")
            return
        result = task_fn(state, dry_run=args.dry_run)
        if not args.dry_run:
            record_task(state, args.task)
    elif args.reel:
        result = run_reel_check(state, dry_run=args.dry_run)
    else:
        # Run one task from rotation
        result = run_next_task(state, dry_run=args.dry_run)

    # After task, check if we should compile a reel
    if not args.dry_run and not args.task:
        reel_result = run_reel_check(state, dry_run=False)
        if reel_result.get("status") == "completed":
            print(f"\n  🎬 Reel compiled: {reel_result.get('output', '')}")

    # Log the run
    if not args.dry_run:
        log_entry(state, "cycle", {
            "task": result.get("task", "unknown"),
            "status": result.get("status", "unknown"),
        })

    print(f"\n  Done. Total night shift tasks: {state.get('total_tasks_completed', 0)}")


if __name__ == "__main__":
    main()