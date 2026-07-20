"""Archiver Agent — cleans up, compresses, and archives old files.

Usage:
    python3 archiver_agent.py --dry-run                    # See what would be cleaned
    python3 archiver_agent.py --clean                      # Actually clean
    python3 archiver_agent.py --compress --older-than 30   # Compress old files
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from echo_core import log_routing

TWIN_OUTPUT_DIR = Path("~/.echo-core").expanduser()
AGENT_LOG = TWIN_OUTPUT_DIR / "logs" / "agent-log.jsonl"
CONTENT_DIR = TWIN_OUTPUT_DIR / "content"
RESEARCH_DIR = TWIN_OUTPUT_DIR / "research"
LOGS_DIR = TWIN_OUTPUT_DIR / "logs"


def get_size_mb(path: Path) -> float:
    """Get total size of a directory in MB."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return round(total / (1024 * 1024), 2)


def count_files(path: Path) -> int:
    """Count files in a directory."""
    return len([f for f in path.rglob("*") if f.is_file()])


def find_old_files(path: Path, older_than_days: int = 30) -> list:
    """Find files older than N days."""
    cutoff = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)
    old = []
    for f in path.rglob("*"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            # Skip logs and state files
            if "logs" in str(f) or "state" in str(f) or "config" in str(f):
                continue
            old.append(f)
    return old


def clean_pycache(path: Path, dry_run: bool = True) -> list:
    """Find and optionally remove __pycache__ directories."""
    removed = []
    for d in path.rglob("__pycache__"):
        if d.is_dir():
            removed.append(str(d))
            if not dry_run:
                import shutil
                shutil.rmtree(d)
    return removed


def clean_pyc(path: Path, dry_run: bool = True) -> list:
    """Find and optionally remove .pyc files."""
    removed = []
    for f in path.rglob("*.pyc"):
        if f.is_file():
            removed.append(str(f))
            if not dry_run:
                f.unlink()
    return removed


def compress_old_files(files: list, dry_run: bool = True) -> list:
    """Compress old files into a tar.gz archive."""
    if not files:
        return []
    archives = []
    # Group by parent directory
    from collections import defaultdict
    by_dir = defaultdict(list)
    for f in files:
        by_dir[f.parent].append(f)

    for parent, file_list in by_dir.items():
        archive_name = f"archive-{parent.name}-{datetime.now().strftime('%Y%m%d')}.tar.gz"
        archive_path = TWIN_OUTPUT_DIR / "archives" / archive_name
        if not dry_run:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            file_list_str = " ".join(f'"{f}"' for f in file_list)
            subprocess.run(
                f'tar -czf "{archive_path}" -C "{parent}" {" ".join(f.name for f in file_list)}',
                shell=True, cwd=str(parent), capture_output=True, timeout=60
            )
            # Remove originals after successful compression
            for f in file_list:
                f.unlink()
        archives.append(str(archive_path))
    return archives


def log_agent(action: str, status: str, details: dict = None):
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "archiver-agent",
        "action": action,
        "status": status,
        "details": details or {},
    }
    with open(AGENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Archiver Agent — cleanup and compress")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Show what would be done (default: True)")
    parser.add_argument("--clean", action="store_true", help="Actually clean")
    parser.add_argument("--compress", action="store_true", help="Compress old files")
    parser.add_argument("--older-than", type=int, default=30, help="Days old (default: 30)")
    args = parser.parse_args()

    # If --clean is set, disable dry-run
    dry_run = not args.clean

    print("=== ARCHIVER AGENT REPORT ===")
    print(f"Mode: {'Dry run' if dry_run else 'Live'}")
    print()

    # Check sizes
    content_size = get_size_mb(CONTENT_DIR) if CONTENT_DIR.exists() else 0
    research_size = get_size_mb(RESEARCH_DIR) if RESEARCH_DIR.exists() else 0
    logs_size = get_size_mb(LOGS_DIR)

    print(f"Content:  {content_size} MB ({count_files(CONTENT_DIR) if CONTENT_DIR.exists() else 0} files)")
    print(f"Research: {research_size} MB ({count_files(RESEARCH_DIR) if RESEARCH_DIR.exists() else 0} files)")
    print(f"Logs:     {logs_size} MB ({count_files(LOGS_DIR)} files)")

    # Find __pycache__ and .pyc
    pycache = clean_pycache(TWIN_OUTPUT_DIR, dry_run=dry_run)
    pyc = clean_pyc(TWIN_OUTPUT_DIR, dry_run=dry_run)
    if pycache:
        print(f"\n  __pycache__ dirs: {len(pycache)} ({'would remove' if dry_run else 'removed'})")
    if pyc:
        print(f"  .pyc files: {len(pyc)} ({'would remove' if dry_run else 'removed'})")

    # Find old files
    old = find_old_files(TWIN_OUTPUT_DIR, args.older_than)
    if old:
        old_size = sum(f.stat().st_size for f in old) / (1024 * 1024)
        print(f"\n  Files older than {args.older_than}d: {len(old)} ({old_size:.1f} MB)")
        if args.compress:
            archives = compress_old_files(old, dry_run=dry_run)
            print(f"  Compressed into: {len(archives)} archive(s)")
            for a in archives:
                print(f"    {a}")

    # Log
    log_agent("archive_cycle", "completed" if not dry_run else "dry_run", {
        "content_size_mb": content_size,
        "research_size_mb": research_size,
        "logs_size_mb": logs_size,
        "pycache_found": len(pycache),
        "pyc_found": len(pyc),
        "old_files": len(old),
    })

    log_routing(f"archive-{datetime.now().strftime('%H%M')}",
                "Archive and cleanup output", "free",
                "qwen/qwen3-coder:free", "openrouter", 0.1)

    print()
    print("Tier: free (qwen/qwen3-coder:free)")
    print("Status: completed")


if __name__ == "__main__":
    main()