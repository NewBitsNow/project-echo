"""Shorts Pipeline — end-to-end YouTube Shorts factory.

Runs the full pipeline unattended:
1. Generate Framehead content (one-liners, observations) via local Ollama
2. Optionally generate Framehead images via ComfyUI
3. Create YouTube Shorts from images + text + TTS

Usage:
    python3 shorts_pipeline.py                           # full pipeline
    python3 shorts_pipeline.py --count 5                  # 5 Shorts
    python3 shorts_pipeline.py --content-only             # just generate content
    python3 shorts_pipeline.py --shorts-only              # just create Shorts from existing assets
    python3 shorts_pipeline.py --dry-run                  # preview
    python3 shorts_pipeline.py --force                    # bypass time guard
"""

import json
import subprocess
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path("~/.echo-core/scripts").expanduser()
CONTENT_DIR = Path("~/.echo-core/content").expanduser()
SHORTS_DIR = CONTENT_DIR / "framehead-shorts"
IMAGE_DIR = CONTENT_DIR / "framehead-images"
LOG_DIR = Path("~/.echo-core/logs").expanduser()
AGENT_LOG = LOG_DIR / "agent-log.jsonl"

# --- Pipeline stages ---

def run_content_gen(count: int = 5, modes: list = None, dry_run: bool = False) -> bool:
    """Stage 1: Generate Framehead content via local Ollama.

    Returns True if successful.
    """
    modes = modes or ["one-liner", "observation"]
    print(f"\n{'='*60}")
    print(f"Stage 1: Content Generation")
    print(f"{'='*60}")
    print(f"Modes: {', '.join(modes)}")
    print(f"Count per mode: {count}")
    print()

    success = True
    for mode in modes:
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "offscreen_content.py"),
            "--mode", mode,
            "--count", str(count),
            "--quiet",
        ]
        if dry_run:
            cmd.append("--dry-run")

        print(f"  Running: {' '.join(cmd[-6:])}")
        if not dry_run:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            print(f"  {result.stdout.strip()}")
            if result.returncode != 0:
                print(f"  ERROR: {result.stderr.strip()}")
                success = False

    return success


def run_image_gen(dry_run: bool = False, force: bool = False) -> bool:
    """Stage 2: Generate Framehead images via ComfyUI.

    Only runs if fewer than 5 images exist. Returns True if successful.
    """
    existing = list(IMAGE_DIR.glob("framehead-*.png"))
    if len(existing) >= 5:
        print(f"\n  Stage 2: {len(existing)} images already exist — skipping")
        return True

    print(f"\n{'='*60}")
    print(f"Stage 2: Image Generation")
    print(f"{'='*60}")
    print(f"Existing: {len(existing)} images")
    print(f"Need: {5 - len(existing)} more")
    print()

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "framehead_generator.py"),
        "--variant", "headshot",
        "--count", "3",
    ]
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")

    print(f"  Running: {' '.join(cmd[-6:])}")
    if not dry_run:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        print(f"  {result.stdout.strip()[-300:]}")
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip()[-200:]}")
            return False

    return True


def run_shorts_gen(count: int = 5, dry_run: bool = False, no_tts: bool = False,
                   voice: str = "lessac", speed: float = 1.0,
                   expressiveness: float = 0.67, rhythm: float = 0.67) -> bool:
    """Stage 3: Create YouTube Shorts from images + text.

    Returns True if successful.
    """
    print(f"\n{'='*60}")
    print(f"Stage 3: Shorts Generation")
    print(f"{'='*60}")
    print(f"Count: {count}")
    print(f"TTS: {'OFF' if no_tts else 'ON'}")
    print()

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "shorts_generator.py"),
        "--batch", str(count),
        "--mode", "one-liner",
        "--voice", voice,
        "--speed", str(speed),
        "--expressiveness", str(expressiveness),
        "--rhythm", str(rhythm),
    ]
    if no_tts:
        cmd.append("--no-tts")
    if dry_run:
        cmd.append("--dry-run")

    print(f"  Running: shorts_generator.py --batch {count}")
    if not dry_run:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        print(f"  {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip()[-300:]}")
            return False

    return True


def run_full_pipeline(content_count: int = 5, shorts_count: int = 5,
                      dry_run: bool = False, no_tts: bool = False,
                      force: bool = False, skip_content: bool = False,
                      skip_images: bool = False, skip_shorts: bool = False,
                      voice: str = "lessac", speed: float = 1.0,
                      expressiveness: float = 0.67, rhythm: float = 0.67) -> dict:
    """Run the full pipeline end-to-end.

    Returns a summary dict.
    """
    start = datetime.now()
    results = {
        "content": {"status": "skipped", "count": 0},
        "images": {"status": "skipped", "count": 0},
        "shorts": {"status": "skipped", "count": 0},
        "started": start.isoformat(),
        "duration_s": 0,
    }

    # Stage 1: Content
    if not skip_content:
        ok = run_content_gen(count=content_count, dry_run=dry_run)
        results["content"]["status"] = "completed" if ok else "failed"
        if ok:
            # Count new content files
            before = set(CONTENT_DIR.glob("framehead-*.md"))
            # Re-count after
            results["content"]["count"] = len(list(CONTENT_DIR.glob("framehead-*.md")))

    # Stage 2: Images
    if not skip_images:
        ok = run_image_gen(dry_run=dry_run, force=force)
        results["images"]["status"] = "completed" if ok else "failed"
        results["images"]["count"] = len(list(IMAGE_DIR.glob("framehead-*.png")))

    # Stage 3: Shorts
    if not skip_shorts:
        ok = run_shorts_gen(count=shorts_count, dry_run=dry_run, no_tts=no_tts,
                       voice=voice, speed=speed,
                       expressiveness=expressiveness, rhythm=rhythm)
        results["shorts"]["status"] = "completed" if ok else "failed"
        results["shorts"]["count"] = len(list(SHORTS_DIR.glob("framehead-short-*.mp4")))

    # Summary
    duration = (datetime.now() - start).total_seconds()
    results["duration_s"] = round(duration, 1)
    results["finished"] = datetime.now().isoformat()

    # Log
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AGENT_LOG, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "shorts-pipeline",
            "action": "full_pipeline",
            "content": results["content"]["status"],
            "images": results["images"]["status"],
            "shorts": results["shorts"]["status"],
            "duration_s": results["duration_s"],
        }) + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Shorts Pipeline — end-to-end YouTube Shorts factory"
    )
    parser.add_argument("--count", "-c", type=int, default=5,
                        help="Number of Shorts to generate (default: 5)")
    parser.add_argument("--content-count", type=int, default=5,
                        help="Number of content pieces per mode (default: 5)")
    parser.add_argument("--content-only", action="store_true",
                        help="Only generate content, skip images and shorts")
    parser.add_argument("--shorts-only", action="store_true",
                        help="Only create Shorts from existing assets")
    parser.add_argument("--images-only", action="store_true",
                        help="Only generate images")
    parser.add_argument("--no-tts", action="store_true",
                        help="Skip voiceover")
    parser.add_argument("--voice", "-v", default="lessac",
                        choices=["lessac", "amy", "libritts", "alan"],
                        help="Piper voice (default: lessac)")
    parser.add_argument("--speed", "-s", type=float, default=1.0,
                        help="Speed: 0.5=2x faster, 1.0=normal (default: 1.0)")
    parser.add_argument("--expressiveness", "-e", type=float, default=0.67,
                        help="Expressiveness: 0.0=robotic, 1.0=expressive (default: 0.67)")
    parser.add_argument("--rhythm", "-r", type=float, default=0.67,
                        help="Rhythm: 0.0=monotone, 1.0=natural (default: 0.67)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview without generating")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Bypass time guard (for image generation)")
    args = parser.parse_args()

    print(f"=== Framehead Shorts Pipeline ===")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if args.dry_run:
        print(f"DRY RUN — no content will be generated")
        print()

    if args.content_only:
        ok = run_content_gen(count=args.content_count, dry_run=args.dry_run)
        print(f"\nContent generation: {'OK' if ok else 'FAILED'}")
        return

    if args.images_only:
        ok = run_image_gen(dry_run=args.dry_run, force=args.force)
        print(f"\nImage generation: {'OK' if ok else 'FAILED'}")
        return

    if args.shorts_only:
        ok = run_shorts_gen(count=args.count, dry_run=args.dry_run, no_tts=args.no_tts,
                           voice=args.voice, speed=args.speed,
                           expressiveness=args.expressiveness, rhythm=args.rhythm)
        print(f"\nShorts generation: {'OK' if ok else 'FAILED'}")
        return

    # Full pipeline
    results = run_full_pipeline(
        content_count=args.content_count,
        shorts_count=args.count,
        dry_run=args.dry_run,
        no_tts=args.no_tts,
        force=args.force,
        voice=args.voice,
        speed=args.speed,
        expressiveness=args.expressiveness,
        rhythm=args.rhythm,
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"  Content:  {results['content']['status']}")
    print(f"  Images:   {results['images']['status']}")
    print(f"  Shorts:   {results['shorts']['status']}")
    print(f"  Duration: {results['duration_s']:.0f}s")
    print()

    if results["shorts"]["count"] > 0:
        print(f"Shorts output: {SHORTS_DIR}")
        for f in sorted(SHORTS_DIR.glob("framehead-short-*.mp4"))[-5:]:
            size = f.stat().st_size // 1024
            print(f"  {f.name} ({size}KB)")

    print(f"\nRESULT: content={results['content']['status']} "
          f"images={results['images']['status']} "
          f"shorts={results['shorts']['status']}")


if __name__ == "__main__":
    main()