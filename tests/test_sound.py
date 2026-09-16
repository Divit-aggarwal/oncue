import pytest

from video_automation import media
from video_automation.sound import SoundError, mix, resolve_asset, schedule
from video_automation.spec import Plan, Transcript
from video_automation.voice import align

from conftest import SCENES, ffmpeg, requires_ffmpeg, spoken_words

pytestmark = requires_ffmpeg


def timeline():
    words = spoken_words()
    t = Transcript(engine="t", model="t", language="en", duration=6.0, words=words)
    return align(Plan.model_validate({"scenes": SCENES}), t, fps=30)


def test_missing_asset_is_reported(tmp_path):
    with pytest.raises(SoundError, match="'tone' not found"):
        resolve_asset("tone", [tmp_path])


def test_sound_is_scheduled_on_its_cue_and_mixed(tmp_path):
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=880:duration=0.5", str(tmp_path / "tone.wav"))
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=6", str(tmp_path / "voice.wav"))
    tl = timeline()
    [sound] = schedule(Plan.model_validate({"scenes": SCENES}), tl, [tmp_path])
    assert sound.time == pytest.approx(tl.scenes[0].start + tl.scenes[0].cues["train"])
    assert sound.duration == pytest.approx(0.5, abs=0.01)
    out = tmp_path / "mix.wav"
    mix(tmp_path / "voice.wav", [sound], tl.duration, 48000, out)
    info = media.probe(out)
    assert media.duration(info) == pytest.approx(tl.duration, abs=0.01)
    assert media.streams(info, "audio")[0]["channels"] == 2


def test_sound_outside_narration_is_rejected(tmp_path):
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=880:duration=0.5", str(tmp_path / "tone.wav"))
    scenes = [
        dict(SCENES[0], sounds=[{"asset": "tone", "event": "late", "at": "end", "offset": 30}]),
        SCENES[1],
    ]
    with pytest.raises(SoundError, match="outside"):
        schedule(Plan.model_validate({"scenes": scenes}), timeline(), [tmp_path])
