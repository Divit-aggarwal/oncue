import re
import subprocess
from dataclasses import replace

import pytest

from video_automation import media
from video_automation.sound import SoundError, mix, resolve_asset, schedule
from video_automation.spec import Plan, Transcript
from video_automation.voice import align, to_wav

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


def test_sound_at_end_of_video_finishes_at_the_end(tmp_path):
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=880:duration=0.5", str(tmp_path / "tone.wav"))
    scenes = [SCENES[0], dict(SCENES[1], sounds=[{"asset": "tone", "event": "outro", "at": "end"}])]
    tl = timeline()
    sound = schedule(Plan.model_validate({"scenes": scenes}), tl, [tmp_path])[-1]
    assert sound.time + sound.duration == pytest.approx(tl.duration)


@pytest.mark.parametrize("offset", [30.0, -30.0])
def test_sound_outside_video_is_moved_inside_and_keeps_requested_time(tmp_path, offset):
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=880:duration=0.5", str(tmp_path / "tone.wav"))
    scenes = [
        dict(SCENES[0], sounds=[{"asset": "tone", "event": "x", "at": "end", "offset": offset}]),
        SCENES[1],
    ]
    tl = timeline()
    [sound] = schedule(Plan.model_validate({"scenes": scenes}), tl, [tmp_path])
    assert 0 <= sound.time and sound.time + sound.duration <= tl.duration + 1e-9
    assert sound.requested_time == pytest.approx(tl.scenes[0].duration + offset)


def peaks(path):
    out = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "astats=measure_perchannel=Peak_level:measure_overall=none",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    return [float(v) for v in re.findall(r"Peak level dB: (-?[\d.]+)", out)]


def test_mono_narration_and_sounds_keep_their_level_in_stereo(tmp_path):
    ffmpeg(
        "-f", "lavfi", "-i", "sine=frequency=220:duration=6", "-ac", "1", str(tmp_path / "take.wav")
    )
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=0.5",
        "-ac",
        "1",
        str(tmp_path / "tone.wav"),
    )
    [source_peak] = peaks(tmp_path / "take.wav")
    to_wav(tmp_path / "take.wav", tmp_path / "voice.wav", 48000)
    assert peaks(tmp_path / "voice.wav") == pytest.approx([source_peak] * 2, abs=0.1)
    tl = timeline()
    [sound] = schedule(Plan.model_validate({"scenes": SCENES}), tl, [tmp_path])
    silent = tmp_path / "silence.wav"
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "6", str(silent))
    mix(silent, [replace(sound, volume=1.0)], tl.duration, 48000, tmp_path / "mix.wav")
    assert peaks(tmp_path / "mix.wav") == pytest.approx([source_peak] * 2, abs=0.1)
