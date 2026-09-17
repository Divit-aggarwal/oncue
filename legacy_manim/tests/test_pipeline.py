import json

import pytest

from video_automation import media, pipeline, workflow
from video_automation.animation import RenderError
from video_automation.sound import SoundError
from video_automation.spec import State
from video_automation.voice import VoiceError, ingest

from conftest import FakeTranscriber, ffmpeg, requires_ffmpeg, spoken_words

pytestmark = [requires_ffmpeg, pytest.mark.media]


@pytest.fixture
def ready(approved_episode, tmp_path):
    ep, settings = approved_episode
    settings.sfx_dirs[0].mkdir(parents=True)
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=0.3",
        str(settings.sfx_dirs[0] / "tone.wav"),
    )
    recording = tmp_path / "take1.m4a"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=6", "-c:a", "aac", str(recording))
    ingest(recording, ep.voice_dir, settings.voice.silence_threshold_db)
    workflow.transition(ep, "provide_voice")
    return ep, settings, FakeTranscriber(spoken_words(), 6.0)


def stages(ep):
    return json.loads((ep.build / "manifest.json").read_text())


def test_end_to_end_generation_reuse_and_revision(ready, caplog):
    ep, settings, transcriber = ready
    report = pipeline.generate(ep, settings, transcriber)
    assert report.ok, report.errors
    assert ep.load().state == State.PREVIEW

    final = ep.output / "final.mp4"
    info = media.probe(final)
    video = media.streams(info, "video")[0]
    assert (video["width"], video["height"]) == (270, 480)
    assert int(video["nb_frames"]) == 90
    assert media.streams(info, "audio")
    assert "Hum bas model ko notes de" in (ep.output / "final.srt").read_text()
    metadata = json.loads((ep.output / "final.json").read_text())
    assert metadata["qc"]["errors"] == []
    assert metadata["sound_events"][0]["event"] == "text appears"

    before = stages(ep)
    caplog.set_level("INFO", logger="video_automation.pipeline")
    caplog.clear()
    pipeline.generate(ep, settings, transcriber)
    assert transcriber.calls == 1
    assert "running" not in caplog.text
    assert stages(ep) == before

    plan_path = ep.document_path("plan")
    plan = json.loads(plan_path.read_text())
    plan["scenes"][1]["visual"]["params"]["lines"] = ["notes v2"]
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(workflow.WorkflowError, match="changed after approval"):
        pipeline.generate(ep, settings, transcriber)
    workflow.submit(ep, "plan")
    workflow.approve(ep)
    workflow.transition(ep, "provide_voice")
    caplog.clear()
    pipeline.generate(ep, settings, transcriber)
    ran = {
        line.split("stage=")[1].split()[0] for line in caplog.text.splitlines() if "running" in line
    }
    assert ran == {"timeline", "scene:notes", "compose"}


def test_rerecording_regenerates_timing(ready, tmp_path):
    ep, settings, transcriber = ready
    assert pipeline.generate(ep, settings, transcriber).ok
    first = (ep.build / "timeline.json").read_text()
    take2 = tmp_path / "take2.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=330:duration=5", str(take2))
    ingest(take2, ep.voice_dir, settings.voice.silence_threshold_db)
    workflow.transition(ep, "provide_voice")
    faster = FakeTranscriber(spoken_words(step=0.2), 5.0)
    report = pipeline.generate(ep, settings, faster)
    assert report.ok, report.errors
    assert faster.calls == 1
    assert (ep.build / "timeline.json").read_text() != first
    assert int(media.streams(media.probe(ep.output / "final.mp4"), "video")[0]["nb_frames"]) == 75


def test_render_failure_keeps_state_and_resumes(ready):
    ep, settings, transcriber = ready
    (ep.root / "broken.py").write_text(
        "from video_automation.animation import TimedScene\n\n\n"
        "class Broken(TimedScene):\n    def construct(self):\n        raise ValueError('boom')\n"
    )
    plan_path = ep.document_path("plan")
    original = plan_path.read_text()
    plan_path.write_text(
        original.replace("video_automation.placeholders:TextCard", "broken:Broken", 1)
    )
    workflow.submit(ep, "plan")
    workflow.approve(ep)
    workflow.transition(ep, "provide_voice")
    with pytest.raises(RenderError, match="boom"):
        pipeline.generate(ep, settings, transcriber)
    assert ep.load().state == State.GENERATION
    assert not (ep.output / "final.mp4").exists()
    assert "scene:claim" not in stages(ep)

    plan_path.write_text(original)
    workflow.submit(ep, "plan")
    workflow.approve(ep)
    workflow.transition(ep, "provide_voice")
    assert pipeline.generate(ep, settings, transcriber).ok


def test_interrupted_stage_is_rerun(ready):
    ep, settings, transcriber = ready
    assert pipeline.generate(ep, settings, transcriber).ok
    (ep.output / "final.mp4").unlink()
    manifest = stages(ep)
    manifest.pop("scene:notes")
    (ep.build / "manifest.json").write_text(json.dumps(manifest))
    assert pipeline.generate(ep, settings, transcriber).ok
    assert "scene:notes" in stages(ep)


def test_missing_sound_asset_fails_generation(ready):
    ep, settings, transcriber = ready
    (settings.sfx_dirs[0] / "tone.wav").unlink()
    with pytest.raises(SoundError, match="tone"):
        pipeline.generate(ep, settings, transcriber)


def test_generation_requires_voice(approved_episode):
    ep, settings = approved_episode
    with pytest.raises(workflow.WorkflowError, match="no narration"):
        pipeline.generate(ep, settings, FakeTranscriber([], 1.0))


@pytest.mark.parametrize("kind", ["not_audio", "silent", "missing"])
def test_invalid_audio_is_rejected(tmp_path, kind):
    path = tmp_path / "take.wav"
    if kind == "not_audio":
        path.write_text("definitely not audio")
    elif kind == "silent":
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "2", str(path))
    with pytest.raises((VoiceError, media.MediaError)):
        ingest(path, tmp_path / "voice", -50.0)
    assert not (tmp_path / "voice").exists() or not any((tmp_path / "voice").iterdir())
