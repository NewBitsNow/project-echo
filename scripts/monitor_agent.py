"""Monitor Agent — checks system state, git status, and reports changes.

Usage:
    python3 monitor_agent.py [--report]
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Paths
SCRIPTS_DIR = Path("~/Documents/twin-output/scripts").expanduser()
sys.path.insert(0, str(SCRIPTS_DIR))

from routing_logger import log_routing

FRAMEHEAD_DIR = Path("/Volumes/4TB_SSD/FrameHead")
TWIN_OUTPUT_DIR = Path("~/Documents/twin-output").expanduser()
AGENT_LOG = TWIN_OUTPUT_DIR / "logs" / "agent-log.jsonl"
STATE_FILE = TWIN_OUTPUT_DIR / "state" / "system-state.json"


def run_git(dir_path: Path, *args: str) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=30,
            cwd=str(dir_path)
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def check_git_status() -> dict:
    """Check git status of the FrameHead repo."""
    status = {}

    # Branch
    status["branch"] = run_git(FRAMEHEAD_DIR, "branch", "--show-current")

    # Uncommitted changes
    status["has_uncommitted"] = False
    status["uncommitted_files"] = []
    dirty = run_git(FRAMEHEAD_DIR, "status", "--porcelain")
    if dirty:
        status["has_uncommitted"] = True
        status["uncommitted_files"] = [
            line.strip() for line in dirty.split("\n") if line.strip()
        ]

    # Ahead/behind remote
    status["ahead_behind"] = ""
    try:
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=str(FRAMEHEAD_DIR), capture_output=True, timeout=15
        )
        status["ahead_behind"] = run_git(FRAMEHEAD_DIR, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        status["ahead_behind"] = "unknown"

    # Recent commits
    log = run_git(FRAMEHEAD_DIR, "log", "--oneline", "-5")
    status["recent_commits"] = log.split("\n") if log else []

    return status


def check_twin_output() -> dict:
    """Check the twin-output directory for changes."""
    info = {}

    # File count and total size
    files = list(TWIN_OUTPUT_DIR.rglob("*"))
    info["file_count"] = len([f for f in files if f.is_file()])
    info["dir_count"] = len([f for f in files if f.is_dir()])

    # Total size
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    info["total_size_bytes"] = total_size
    info["total_size_mb"] = round(total_size / (1024 * 1024), 2)

    # Recent files (last 24h)
    cutoff = datetime.now(timezone.utc).timestamp() - 86400
    recent = [
        f for f in files if f.is_file()
        and f.stat().st_mtime > cutoff
        and ".pytest_cache" not in str(f)
        and "__pycache__" not in str(f)
    ]
    info["recent_files"] = [str(f.relative_to(TWIN_OUTPUT_DIR)) for f in recent[:20]]

    return info


def check_disk_usage() -> dict:
    """Check disk usage of the SSD."""
    stat = os.statvfs(str(FRAMEHEAD_DIR))
    total = stat.f_frsize * stat.f_blocks
    free = stat.f_frsize * stat.f_bfree
    used = total - free
    return {
        "total_gb": round(total / (1024**3), 1),
        "used_gb": round(used / (1024**3), 1),
        "free_gb": round(free / (1024**3), 1),
        "used_pct": round(used / total * 100, 1),
    }


def log_agent(action: str, status: str, details: dict = None):
    """Append to the shared agent log."""
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "monitor-agent",
        "action": action,
        "status": status,
        "details": details or {},
    }
    with open(AGENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monitor Agent — check system state")
    parser.add_argument("--report", action="store_true", help="Print full report")
    args = parser.parse_args()

    # Run checks
    git_status = check_git_status()
    twin_info = check_twin_output()
    disk_info = check_disk_usage()

    # Classify and route (simple — this is a read-only task, always free)
    task_desc = "Monitor system state: git status, file changes, disk usage"
    log_routing(f"monitor-{datetime.now().strftime('%H%M')}", task_desc,
                "free", "qwen/qwen3-coder:free", "openrouter", 0.1)

    # Log to agent log
    log_agent("monitor_cycle", "completed", {
        "git_branch": git_status["branch"],
        "uncommitted": git_status["has_uncommitted"],
        "file_count": twin_info["file_count"],
        "disk_used_gb": disk_info["used_gb"],
    })

    # Report
    if args.report:
        print("=== MONITOR AGENT REPORT ===")
        print()

        print("Git Status:")
        print(f"  Branch: {git_status['branch']}")
        if git_status["has_uncommitted"]:
            print(f"  Uncommitted: {len(git_status['uncommitted_files'])} file(s)")
            for f in git_status["uncommitted_files"][:5]:
                print(f"    {f}")
        else:
            print("  Clean")
        print(f"  Ahead/behind: {git_status['ahead_behind']}")
        if git_status["recent_commits"]:
            print(f"  Recent commits ({len(git_status['recent_commits'])}):")
            for c in git_status["recent_commits"]:
                print(f"    {c}")
        print()

        print("Twin Output:")
        print(f"  Files: {twin_info['file_count']}")
        print(f"  Dirs:  {twin_info['dir_count']}")
        print(f"  Size:  {twin_info['total_size_mb']} MB")
        if twin_info["recent_files"]:
            print(f"  Changed in last 24h ({len(twin_info['recent_files'])}):")
            for f in twin_info["recent_files"]:
                print(f"    {f}")
        print()

        print("Disk:")
        print(f"  {disk_info['used_gb']} GB / {disk_info['total_gb']} GB ({disk_info['used_pct']}%)")
        print()

        print("Tier: free (qwen/qwen3-coder:free)")
        print("Status: completed")

    # Return structured data for the orchestrator
    return {
        "git": git_status,
        "twin_output": twin_info,
        "disk": disk_info,
    }


if __name__ == "__main__":
    main()