import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from video_automation import media
from video_automation.cli import main

EXAMPLE = Path(__file__).parents[1] / "examples" / "smoke"

pytestmark = [
    pytest.mark.whisper,
    pytest.mark.skipif(
        not (shutil.which("say") and os.environ.get("VAE_WHISPER_TEST")),
        reason="set VAE_WHISPER_TEST=1 on macOS to run real speech synthesis and whisper",
    ),
]

NARRATION = (
    "Basically RAG mein model ko dobara train nahi kar rahe. [[slnc 700]] "
    "Hum bas model ko notes de rahe hain. "
    "Retriever relevant documents dhoondta hai, aur LLM answer likhta hai."
)


def cli(root: Path, *args: str) -> int:
    return main(["--project", str(root), *args])


def test_real_production_through_cli(tmp_path, capsys):
    (tmp_path / "engine.toml").write_text(
        '[voice]\nmodel = "small"\n[video]\nwidth = 540\nheight = 960\n'
    )
    sfx = tmp_path / "assets" / "sfx"
    sfx.mkdir(parents=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=0.25",
            str(sfx / "example_tone.wav"),
        ],
        check=True,
    )
    recording = tmp_path / "narration.aiff"
    subprocess.run(["say", "-o", str(recording), NARRATION], check=True)

    assert cli(tmp_path, "new", "smoke", "--idea", "engine smoke test") == 0
    episode = tmp_path / "episodes" / "smoke"
    shutil.copy(EXAMPLE / "proposal.json", episode)
    assert cli(tmp_path, "voice", "smoke", str(recording)) == 1
    assert cli(tmp_path, "submit", "smoke", "proposal") == 0
    assert cli(tmp_path, "approve", "smoke") == 0
    shutil.copy(EXAMPLE / "plan.json", episode)
    assert cli(tmp_path, "submit", "smoke", "plan") == 0
    assert cli(tmp_path, "approve", "smoke") == 0
    assert cli(tmp_path, "voice", "smoke", str(recording)) == 0
    assert cli(tmp_path, "generate", "smoke") == 0
    out = capsys.readouterr().out
    assert "state:   PREVIEW" in out

    timeline = json.loads((episode / "build" / "timeline.json").read_text())
    assert timeline["match_ratio"] > 0.8
    srt = (episode / "output" / "final.srt").read_text().lower()
    assert "dobara train nahi" in srt
    info = media.probe(episode / "output" / "final.mp4")
    assert media.streams(info, "video")[0]["height"] == 960
    assert cli(tmp_path, "finalize", "smoke") == 0
