import json
import shutil
import subprocess
from pathlib import Path

import pytest

from video_automation import workflow
from video_automation.config import Settings
from video_automation.spec import Transcript, Word

SCENES = [
    {
        "id": "claim",
        "narration": "Basically RAG mein model ko dobara train nahi kar rahe.",
        "visual": {
            "component": "video_automation.placeholders:TextCard",
            "params": {"lines": ["RAG"]},
        },
        "cues": {"train": "dobara train"},
        "events": [{"at": "train", "action": "show", "params": {"text": "no retraining"}}],
        "sounds": [{"asset": "tone", "event": "text appears", "at": "train", "volume": 0.3}],
    },
    {
        "id": "notes",
        "narration": "Hum bas model ko notes de rahe hain.",
        "visual": {
            "component": "video_automation.placeholders:TextCard",
            "params": {"lines": ["notes"]},
        },
    },
]

PROPOSAL = {
    "title": "Test",
    "concept": "pipeline test",
    "hook": "n/a",
    "comedy_direction": "",
    "analogy": "",
    "analogy_limitations": "",
    "technical_explanation": "RAG adds retrieved context; weights are unchanged.",
    "narrative_structure": ["claim", "notes"],
    "ending": "",
    "language": "hinglish",
    "target_duration_seconds": 6,
}


def spoken_words(start: float = 0.2, step: float = 0.25) -> list[Word]:
    text = " ".join(s["narration"] for s in SCENES).split()
    words, t = [], start
    for i, w in enumerate(text):
        if i == 10:
            t += 0.8
        words.append(Word(text=w, start=round(t, 3), end=round(t + step * 0.8, 3)))
        t += step
    return words


class FakeTranscriber:
    def __init__(self, words: list[Word], duration: float):
        self.words, self.duration, self.calls = words, duration, 0

    def transcribe(self, audio: Path, prompt: str | None) -> Transcript:
        self.calls += 1
        return Transcript(
            engine="fake", model="fake", language="en", duration=self.duration, words=self.words
        )


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, Settings]:
    settings = Settings(
        episodes_dir=tmp_path / "episodes",
        sfx_dirs=[tmp_path / "sfx"],
    )
    settings.video.width, settings.video.height, settings.video.fps = 270, 480, 15
    return tmp_path, settings


@pytest.fixture
def approved_episode(project):
    root, settings = project
    ep = workflow.create_episode(settings.episodes_dir, "demo", "idea")
    ep.document_path("proposal").write_text(json.dumps(PROPOSAL))
    ep.document_path("plan").write_text(json.dumps({"scenes": SCENES}))
    workflow.submit(ep, "proposal")
    workflow.approve(ep)
    workflow.submit(ep, "plan")
    workflow.approve(ep)
    return ep, settings


requires_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg missing")
