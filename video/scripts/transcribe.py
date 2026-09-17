"""Convert a voiceover to public/audio/<slug>.mp3 and write word timings to timings/<slug>.json.

usage: uv run python scripts/transcribe.py <slug> <recording> [--model small]

If storyboards/<slug>.md exists, its **Say:** lines are passed to Whisper as a prompt.
Without a prompt, Whisper tends to translate Hinglish into English.
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser()
parser.add_argument("slug")
parser.add_argument("recording", type=Path)
parser.add_argument("--model", default="small")
args = parser.parse_args()

audio = ROOT / "public" / "audio" / f"{args.slug}.mp3"
audio.parent.mkdir(parents=True, exist_ok=True)
if args.recording.resolve() == audio:
    raise SystemExit(f"recording must not be {audio}; it is overwritten by the conversion")
deep_filter = ROOT / "scripts" / "bin" / "deep-filter"
if not deep_filter.exists():
    raise SystemExit("deep-filter not found; run scripts/setup-deep-filter.sh")


def setting(name: str, default: str) -> str:
    """Environment variable, else KEY=value from video/.env, else default."""
    if name in os.environ:
        return os.environ[name]
    env_file = ROOT / ".env"
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    for line in lines:
        key, sep, value = line.partition("=")
        if sep and key.strip() == name:
            return value.split("#")[0].strip().strip("\"'")
    return default


atten_lim = setting("DEEP_FILTER_ATTEN_LIM", "100")
try:
    float(atten_lim)
except ValueError:
    raise SystemExit(f"DEEP_FILTER_ATTEN_LIM must be a number of dB, got {atten_lim!r}") from None

# Cleanup chain; the raw recording is only read, never modified:
# denoise (DeepFilterNet, delay-compensated so timings don't shift) -> highpass 80 Hz
# -> light compression -> stereo +3 dB mp3 (Revideo renders mono voice about 3 dB quieter).
with tempfile.TemporaryDirectory() as tmp:
    wav = Path(tmp) / "voice.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(args.recording), "-vn",
         "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
        check=True,
    )
    subprocess.run(
        [str(deep_filter), "-D", "--atten-lim-db", atten_lim, "-o", f"{tmp}/denoised", str(wav)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", f"{tmp}/denoised/voice.wav",
         "-af", "highpass=f=80,acompressor=threshold=-18dB:ratio=2,volume=3dB",
         "-ac", "2", "-c:a", "libmp3lame", "-q:a", "2", str(audio)],
        check=True,
    )
stats = subprocess.run(
    ["ffmpeg", "-hide_banner", "-nostats", "-i", str(audio), "-af", "volumedetect", "-f", "null", "-"],
    capture_output=True, text=True, check=True,
).stderr
peak = float(re.search(r"max_volume: (-?[\d.]+) dB", stats).group(1))
if peak >= -0.1:
    print(f"WARNING: {audio.name} peaks at {peak} dB after +3 dB and may clip")

storyboard = ROOT.parent / "storyboards" / f"{args.slug}.md"
said = re.findall(r"\*\*Say:\*\*\s*(.+)", storyboard.read_text()) if storyboard.exists() else []
prompt = " ".join(s.strip() for s in said) or None

from faster_whisper import WhisperModel  # noqa: E402  (slow import, after cheap checks)

model = WhisperModel(args.model, device="auto", compute_type="int8")
segments, info = model.transcribe(
    str(audio),
    language="en",  # "en" + prompt keeps Roman Hinglish (see docs/07)
    task="transcribe",
    word_timestamps=True,
    vad_filter=False,
    condition_on_previous_text=False,
    initial_prompt=prompt,
)
words = [
    {"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
    for s in segments
    for w in s.words or []
    if w.word.strip()
]
out = ROOT / "timings" / f"{args.slug}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(
        {"model": args.model, "prompt": prompt, "duration": round(info.duration, 3), "words": words},
        indent=2,
        ensure_ascii=False,
    )
    + "\n"
)
print(f"{audio.relative_to(ROOT)}  peak {peak} dB, denoise atten limit {atten_lim} dB")
print(f"{out.relative_to(ROOT)}  {len(words)} words, {info.duration:.2f}s, prompt={'yes' if prompt else 'no'}")
print(" ".join(f"[{w['start']:.2f}]{w['text']}" for w in words))
