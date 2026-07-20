"""Audio FX — ffmpeg-based audio processing.

All CPU-friendly, all local. No GPU needed. Uses your already-installed ffmpeg.

Features:
- Background music mixing (ducking under voice)
- Volume normalization (LUFS/RMS)
- Crossfade between clips
- Silence trimming
- Audio format conversion
- Generate tones / ambient noise
- Trim / concatenate audio

Usage:
    python3 audio_fx.py mix --voice voice.wav --music bg.mp3 --output mixed.wav
    python3 audio_fx.py normalize --input voice.wav --output norm.wav
    python3 audio_fx.py trim-silence --input voice.wav --output trimmed.wav
    python3 audio_fx.py crossfade --input1 a.wav --input2 b.wav --output joined.wav
    python3 audio_fx.py info --input voice.wav
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def probe_audio(path: str) -> dict:
    """Get audio file metadata using ffprobe.

    Returns dict with duration, sample_rate, channels, codec, etc.
    """
    cmd = [
        FFPROBE, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    return json.loads(result.stdout)


def get_duration(path: str) -> float:
    """Get audio duration in seconds."""
    data = probe_audio(path)
    if "error" in data:
        return 0
    return float(data.get("format", {}).get("duration", 0))


def info(args):
    """Show audio file metadata."""
    data = probe_audio(args.input)
    if "error" in data:
        print(f"Error: {data['error']}")
        return

    fmt = data.get("format", {})
    stream = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "audio":
            stream = s
            break

    print(f"File: {args.input}")
    print(f"  Format: {fmt.get('format_name', '?')}")
    print(f"  Duration: {float(fmt.get('duration', 0)):.1f}s")
    print(f"  Size: {int(fmt.get('size', 0)) // 1024}KB")
    if stream:
        print(f"  Sample rate: {stream.get('sample_rate', '?')} Hz")
        print(f"  Channels: {stream.get('channels', '?')}")
        print(f"  Codec: {stream.get('codec_name', '?')}")
        print(f"  Bitrate: {stream.get('bit_rate', '?')} bps")


def normalize(args):
    """Normalize audio volume using loudnorm (EBU R128 / LUFS).

    Targets -14 LUFS (streaming standard — YouTube, Spotify, Apple Music).
    """
    print(f"Normalizing: {args.input}")
    print(f"  Target LUFS: {args.lufs}")

    # First pass: detect loudness
    detect_cmd = [
        FFMPEG, "-y", "-i", args.input,
        "-af", f"loudnorm=I={args.lufs}:print_format=json",
        "-f", "null", "-",
    ]
    result = subprocess.run(detect_cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  Error: {result.stderr[-300:]}")
        return

    # Parse loudnorm output from stderr (it prints to stderr)
    import re
    measured = {}
    for line in result.stderr.split("\n"):
        match = re.search(r'"(\w+)":\s*"?([-\d.]+)"?', line)
        if match:
            measured[match.group(1)] = match.group(2)

    print(f"  Measured integrated: {measured.get('input_i', '?')} LUFS")
    print(f"  Measured true peak: {measured.get('input_tp', '?')} dBTP")
    print(f"  Measured range: {measured.get('input_lra', '?')} LU")

    # Second pass: apply normalization
    if args.dry_run:
        print(f"  [DRY RUN] Would normalize to {args.lufs} LUFS")
        return

    cmd = [
        FFMPEG, "-y", "-i", args.input,
        "-af", (
            f"loudnorm=I={args.lufs}:LRA={args.lra}:tp={args.tp}:"
            f"measured_I={measured.get('input_i', -24)}:"
            f"measured_LRA={measured.get('input_lra', 7)}:"
            f"measured_tp={measured.get('input_tp', -2)}:"
            f"measured_thresh={measured.get('input_thresh', -30)}:"
            f"offset={measured.get('target_offset', 0)}"
        ),
        "-ar", "44100",
        "-ac", "1",
        "-sample_fmt", "s16",
        "-c:a", "pcm_s16le",
        args.output,
    ]

    subprocess.run(cmd, check=True, timeout=120)
    size = Path(args.output).stat().st_size // 1024
    print(f"  → Saved: {args.output} ({size}KB)")


def trim_silence(args):
    """Remove silence from the beginning and end of audio."""
    print(f"Trimming silence: {args.input}")
    print(f"  Threshold: {args.threshold}dB")
    print(f"  Min duration: {args.min}s")

    if args.dry_run:
        print(f"  [DRY RUN] Would trim silence")
        return

    cmd = [
        FFMPEG, "-y", "-i", args.input,
        "-af", (
            f"silenceremove=start_periods=1:start_duration={args.min}:"
            f"start_threshold=-{args.threshold}dB:"
            f"stop_periods=1:stop_duration={args.min}:"
            f"stop_threshold=-{args.threshold}dB"
        ),
        "-ar", "44100",
        "-ac", "1",
        "-sample_fmt", "s16",
        "-c:a", "pcm_s16le",
        args.output,
    ]

    subprocess.run(cmd, check=True, timeout=120)
    original_dur = get_duration(args.input)
    new_dur = get_duration(args.output)
    trimmed = original_dur - new_dur
    size = Path(args.output).stat().st_size // 1024
    print(f"  → Saved: {args.output} ({size}KB)")
    print(f"  Trimmed: {trimmed:.1f}s of silence")


def mix(args):
    """Mix voice audio with background music using sidechain ducking.

    The music volume ducks (drops) automatically when the voice is speaking,
    then comes back up during pauses.
    """
    print(f"Mixing audio:")
    print(f"  Voice: {args.voice}")
    print(f"  Music: {args.music}")
    print(f"  Music volume: {args.music_vol}")
    print(f"  Ducking: {args.duck}dB reduction")

    voice_dur = get_duration(args.voice)
    music_dur = get_duration(args.music)
    print(f"  Voice duration: {voice_dur:.1f}s")
    print(f"  Music duration: {music_dur:.1f}s")

    if args.dry_run:
        print(f"  [DRY RUN] Would produce mixed audio")
        return

    # Build filter complex
    # The sidechain compressor takes two inputs: main audio + sidechain trigger
    # Main = music (being compressed), sidechain = voice (triggers ducking)
    filter_parts = [
        # Voice stream: normalize volume
        f"[0:a]loudnorm=I=-16:LRA=7:tp=-1.5[voice]",

        # Music stream: reduce volume, then compress sidechained against voice
        # When voice is loud, music ducks down
        f"[1:a]volume={args.music_vol}[music_base]",
        f"[music_base][0:a]sidechaincompress=threshold=0.2:ratio=3:attack=50:release=500:makeup=1[music]",

        # Mix voice and ducked music
        f"[voice][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
    ]

    filter_complex = "; ".join(filter_parts)

    cmd = [
        FFMPEG, "-y",
        "-i", args.voice,
        "-i", args.music,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ar", "44100",
        "-ac", "1",
        "-sample_fmt", "s16",
        "-c:a", "pcm_s16le",
        args.output,
    ]

    subprocess.run(cmd, check=True, timeout=300)
    size = Path(args.output).stat().st_size // 1024
    print(f"  → Saved: {args.output} ({size}KB)")


def crossfade(args):
    """Crossfade two audio files together."""
    print(f"Crossfading:")
    print(f"  Input 1: {args.input1}")
    print(f"  Input 2: {args.input2}")
    print(f"  Duration: {args.duration}s")

    if args.dry_run:
        print(f"  [DRY RUN] Would crossfade {args.duration}s")
        return

    cmd = [
        FFMPEG, "-y",
        "-i", args.input1,
        "-i", args.input2,
        "-filter_complex", f"acrossfade=d={args.duration}:curve1=tri:curve2=tri",
        "-ar", "44100",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        args.output,
    ]

    subprocess.run(cmd, check=True, timeout=120)
    size = Path(args.output).stat().st_size // 1024
    print(f"  → Saved: {args.output} ({size}KB)")


def tone(args):
    """Generate a test tone or ambient noise."""
    print(f"Generating tone:")
    print(f"  Type: {args.type}")
    print(f"  Duration: {args.duration}s")

    if args.type == "sine":
        src = f"sine=frequency={args.freq}:duration={args.duration}"
    elif args.type == "silence":
        src = f"anullsrc=r=44100:cl=mono:d={args.duration}"
    elif args.type == "noise":
        src = f"anoisesrc=d={args.duration}:c=pink:a={args.volume}"
    elif args.type == "sweep":
        src = f"aevalsrc=sin(2*PI*T*({args.freq}+({args.freq2}-{args.freq})*T/{args.duration})):d={args.duration}"
    else:
        print(f"  Unknown type: {args.type}")
        return

    if args.dry_run:
        print(f"  [DRY RUN] Would generate '{args.type}' tone")
        return

    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", src,
        "-ar", "44100",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        args.output,
    ]

    subprocess.run(cmd, check=True, timeout=30)
    size = Path(args.output).stat().st_size // 1024
    print(f"  → Saved: {args.output} ({size}KB)")


def concat(args):
    """Concatenate multiple audio files."""
    files = args.inputs
    print(f"Concatenating {len(files)} files")

    if args.dry_run:
        print(f"  [DRY RUN] Would concatenate {len(files)} files")
        return

    # Create a temp file list
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for path in files:
            f.write(f"file '{path}'\n")
        list_path = f.name

    try:
        cmd = [
            FFMPEG, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            args.output,
        ]
        subprocess.run(cmd, check=True, timeout=120)
        size = Path(args.output).stat().st_size // 1024
        print(f"  → Saved: {args.output} ({size}KB)")
    finally:
        Path(list_path).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Audio FX — ffmpeg-based audio processing"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    p = sub.add_parser("info", help="Show audio metadata")
    p.add_argument("--input", "-i", required=True, help="Input audio file")

    # normalize
    p = sub.add_parser("normalize", help="Normalize volume to streaming standard")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--lufs", type=float, default=-14, help="Target LUFS (default: -14)")
    p.add_argument("--lra", type=float, default=7, help="Loudness range (default: 7)")
    p.add_argument("--tp", type=float, default=-1.5, help="True peak limit (default: -1.5)")
    p.add_argument("--dry-run", "-n", action="store_true")

    # trim-silence
    p = sub.add_parser("trim-silence", help="Remove leading/trailing silence")
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--threshold", type=float, default=50, help="Silence threshold in dB (default: 50)")
    p.add_argument("--min", type=float, default=0.1, help="Min silence duration to trim (default: 0.1s)")
    p.add_argument("--dry-run", "-n", action="store_true")

    # mix
    p = sub.add_parser("mix", help="Mix voice + background music with ducking")
    p.add_argument("--voice", "-v", required=True, help="Voice audio file")
    p.add_argument("--music", "-m", required=True, help="Background music file")
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--music-vol", type=float, default=0.3, help="Music volume (0.0-1.0, default: 0.3)")
    p.add_argument("--duck", type=float, default=12, help="Ducking reduction in dB (default: 12)")
    p.add_argument("--dry-run", "-n", action="store_true")

    # crossfade
    p = sub.add_parser("crossfade", help="Crossfade two audio files")
    p.add_argument("--input1", "-a", required=True)
    p.add_argument("--input2", "-b", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--duration", "-d", type=float, default=2, help="Crossfade duration in seconds (default: 2)")
    p.add_argument("--dry-run", "-n", action="store_true")

    # tone
    p = sub.add_parser("tone", help="Generate test tones / noise")
    p.add_argument("--type", "-t", choices=["sine", "silence", "noise", "sweep"], default="sine")
    p.add_argument("--duration", "-d", type=float, default=1, help="Duration in seconds")
    p.add_argument("--freq", type=float, default=440, help="Frequency in Hz (for sine/sweep)")
    p.add_argument("--freq2", type=float, default=880, help="End frequency (for sweep)")
    p.add_argument("--volume", type=float, default=0.3, help="Volume (for noise, 0.0-1.0)")
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--dry-run", "-n", action="store_true")

    # concat
    p = sub.add_parser("concat", help="Concatenate multiple audio files")
    p.add_argument("--inputs", "-i", nargs="+", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--dry-run", "-n", action="store_true")

    args = parser.parse_args()

    handlers = {
        "info": info,
        "normalize": normalize,
        "trim-silence": trim_silence,
        "mix": mix,
        "crossfade": crossfade,
        "tone": tone,
        "concat": concat,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()