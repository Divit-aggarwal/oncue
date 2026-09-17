"""Convert a voiceover to public/audio/<slug>.mp3 and write word timings to timings/<slug>.json.

usage: uv run python scripts/transcribe.py <slug> <recording> [--model small]

If storyboards/<slug>.md exists, its **Say:** lines are passed to Whisper as a prompt.
Without a prompt, Whisper tends to translate Hinglish into English.
"""

import argparse
import json
import re
import subprocess
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
# Standard conversion: stereo, +3 dB (Revideo renders mono voice about 3 dB quieter).
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-i", str(args.recording), "-vn",
     "-ac", "2", "-af", "volume=3dB", "-c:a", "libmp3lame", "-q:a", "2", str(audio)],
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
print(f"{audio.relative_to(ROOT)}  peak {peak} dB")
print(f"{out.relative_to(ROOT)}  {len(words)} words, {info.duration:.2f}s, prompt={'yes' if prompt else 'no'}")
print(" ".join(f"[{w['start']:.2f}]{w['text']}" for w in words))
