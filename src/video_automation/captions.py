import json
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel

from .config import CaptionStyle
from .spec import EngineError, Transcript

HOLD_SECONDS = 0.4
SENTENCE_END = (".", "?", "!", "।", "॥")


class Caption(BaseModel):
    start: float
    end: float
    text: str


class CaptionError(EngineError):
    pass


def segment(transcript: Transcript, max_chars: int, max_gap: float) -> list[Caption]:
    groups: list[list] = []
    for word in transcript.words:
        current = groups[-1] if groups else None
        if (
            current is None
            or len(" ".join(w.text for w in current)) + 1 + len(word.text) > max_chars
            or word.start - current[-1].end > max_gap
            or current[-1].text.endswith(SENTENCE_END)
        ):
            groups.append([word])
        else:
            current.append(word)
    captions = []
    for i, group in enumerate(groups):
        limit = groups[i + 1][0].start if i + 1 < len(groups) else transcript.duration
        end = max(min(group[-1].end + HOLD_SECONDS, limit, transcript.duration), group[0].start)
        captions.append(
            Caption(
                start=group[0].start,
                end=end,
                text=" ".join(w.text for w in group),
            )
        )
    return captions


def srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3_600_000:02}:{ms // 60_000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def to_srt(captions: list[Caption]) -> str:
    return "".join(
        f"{i}\n{srt_time(c.start)} --> {srt_time(c.end)}\n{c.text}\n\n"
        for i, c in enumerate(captions, start=1)
    )


def render_images(
    captions: list[Caption], style: CaptionStyle, width: int, height: int, directory: Path
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob("*.png"):
        old.unlink()
    job = directory / "job.json"
    job.write_text(
        json.dumps(
            {
                "texts": [c.text for c in captions],
                "style": style.model_dump(),
                "width": width,
                "height": height,
            }
        )
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"from video_automation.captions import run_job; run_job({str(job)!r})",
        ],
        capture_output=True,
        text=True,
    )
    paths = [directory / f"{i:04}.png" for i in range(len(captions))]
    if result.returncode != 0 or not all(p.exists() for p in paths):
        raise CaptionError(f"caption rendering failed:\n{result.stderr[-2000:]}")
    return paths


def run_job(job_path: str) -> None:
    from manim import Camera, Text, tempconfig

    job_file = Path(job_path)
    job = json.loads(job_file.read_text())
    style = CaptionStyle.model_validate(job["style"])
    frame_height = 8.0
    frame_width = frame_height * job["width"] / job["height"]
    with tempconfig(
        {
            "pixel_width": job["width"],
            "pixel_height": job["height"],
            "frame_height": frame_height,
            "frame_width": frame_width,
            "media_dir": str(job_file.parent / "manim"),
        }
    ):
        mobjects = [Text(text, font_size=style.font_size) for text in job["texts"]]
        widest = max((m.width for m in mobjects), default=0.0)
        factor = min(1.0, frame_width * style.max_width_ratio / widest) if widest else 1.0
        for i, mobject in enumerate(mobjects):
            mobject.scale(factor)
            mobject.set_stroke(color="#000000", width=style.stroke_width, background=True)
            camera = Camera(background_opacity=0)
            camera.capture_mobject(mobject)
            image = camera.get_image()
            box = image.getbbox()
            if box is None:
                raise CaptionError(f"caption {i} rendered empty")
            image.crop(box).save(job_file.parent / f"{i:04}.png")
