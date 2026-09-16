import pytest

from video_automation.spec import Plan, Transcript, Word
from video_automation.voice import VoiceError, align

from conftest import SCENES, spoken_words

PLAN = Plan.model_validate({"scenes": SCENES})


def transcript(words, duration=6.0):
    return Transcript(engine="t", model="t", language="en", duration=duration, words=words)


def test_scene_boundaries_follow_the_recording():
    words = spoken_words()
    timeline = align(PLAN, transcript(words), fps=30)
    claim, notes = timeline.scenes
    assert timeline.match_ratio == 1.0
    assert claim.start == 0 and claim.start_frame == 0
    assert notes.start == pytest.approx(round((words[10].start - 0.2) * 30) / 30)
    assert claim.frames + notes.frames == timeline.frames == round(6.0 * 30)
    assert claim.cues["train"] == pytest.approx(words[5].start)
    assert [w.text for w in notes.words][0] == "Hum"
    assert notes.words[0].start == pytest.approx(words[10].start - notes.start)


def test_faster_speech_moves_timing_without_changing_plan():
    slow = align(PLAN, transcript(spoken_words(step=0.35)), fps=30)
    fast = align(PLAN, transcript(spoken_words(step=0.15)), fps=30)
    assert fast.scenes[1].start < slow.scenes[1].start
    assert fast.scenes[0].cues["train"] < slow.scenes[0].cues["train"]


def test_pauses_are_detected():
    words = spoken_words()
    words = words[:3] + [Word(text=w.text, start=w.start + 1.0, end=w.end + 1.0) for w in words[3:]]
    timeline = align(PLAN, transcript(words, duration=7.0), fps=30)
    assert len(timeline.scenes[0].pauses) == 1


def test_ad_libs_and_misrecognitions_still_align():
    words = spoken_words()
    words.insert(4, Word(text="yaar", start=1.5, end=1.55))
    words[1] = Word(text="RAAG", start=words[1].start, end=words[1].end)
    timeline = align(PLAN, transcript(words), fps=30)
    assert timeline.match_ratio < 1.0
    assert timeline.scenes[1].words[0].text == "Hum"


def test_scene_missing_from_recording_is_an_error():
    words = spoken_words()[:10]
    with pytest.raises(VoiceError, match="scene notes"):
        align(PLAN, transcript(words, duration=4.0), fps=30)


def test_empty_transcript_is_an_error():
    with pytest.raises(VoiceError, match="no words"):
        align(PLAN, transcript([]), fps=30)


def test_unmatched_opening_words_do_not_steal_previous_scene_words():
    plan = Plan.model_validate(
        {
            "scenes": [
                {"id": "a", "narration": "one two three four", "visual": {"component": "m:C"}},
                {"id": "b", "narration": "five six seven eight", "visual": {"component": "m:C"}},
            ]
        }
    )
    spoken = ["one", "two", "three", "four", "seven", "eight"]
    words = [Word(text=w, start=i * 0.5, end=i * 0.5 + 0.3) for i, w in enumerate(spoken)]
    timeline = align(plan, transcript(words, duration=3.5), fps=30)
    assert [w.text for w in timeline.scenes[0].words] == ["one", "two", "three", "four"]
    assert [w.text for w in timeline.scenes[1].words] == ["seven", "eight"]
