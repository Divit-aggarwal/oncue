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
    claim = timeline.scenes[0]
    inner, trailing = claim.pauses
    assert inner.start == pytest.approx(words[2].end) and inner.end == pytest.approx(words[3].start)
    assert trailing.start == pytest.approx(words[9].end)
    assert trailing.end == pytest.approx(claim.duration)


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


def simple_plan(*narrations, cues=None):
    return Plan.model_validate(
        {
            "scenes": [
                {
                    "id": f"s{i}",
                    "narration": n,
                    "visual": {"component": "m:C"},
                    "cues": (cues or {}).get(i, {}),
                }
                for i, n in enumerate(narrations)
            ]
        }
    )


def timed(*spec, duration):
    return transcript([Word(text=t, start=s, end=e) for t, s, e in spec], duration=duration)


def test_zero_length_whisper_words_never_collapse_scene_boundaries():
    plan = simple_plan("a", "b", "c")
    timeline = align(
        plan, timed(("a", 0.0, 1.0), ("b", 1.0, 1.0), ("c", 1.0, 1.2), duration=2.0), fps=30
    )
    starts = [s.start_frame for s in timeline.scenes]
    assert starts == sorted(set(starts))
    assert all(s.frames >= 1 for s in timeline.scenes)
    assert sum(s.frames for s in timeline.scenes) == timeline.frames
    assert timeline.notes


def test_recording_shorter_than_one_frame_per_scene_is_an_error():
    with pytest.raises(VoiceError, match="too short"):
        align(
            simple_plan("a", "b", "c"),
            timed(("a", 0, 0.01), ("b", 0.01, 0.02), ("c", 0.02, 0.03), duration=0.05),
            fps=30,
        )


def test_unrecognised_cue_word_falls_back_to_previous_word():
    plan = simple_plan("a b", "c d e", cues={1: {"e": "e"}})
    timeline = align(
        plan,
        timed(("a", 0, 0.5), ("b", 0.5, 1.0), ("c", 1.1, 1.3), ("d", 1.4, 1.6), duration=2.0),
        fps=30,
    )
    scene = timeline.scenes[1]
    assert scene.cues["e"] == pytest.approx(1.6 - scene.start)
    assert any("'e'" in note for note in timeline.notes)


def test_cue_on_final_word_stays_inside_scene():
    plan = simple_plan("a b", "c d", cues={1: {"d": "d"}})
    timeline = align(
        plan,
        timed(("a", 0, 0.5), ("b", 0.5, 1.0), ("c", 1.1, 1.3), ("d", 2.5, 2.6), duration=2.0),
        fps=30,
    )
    scene = timeline.scenes[1]
    assert 0 <= scene.cues["d"] <= scene.duration


def test_fillers_repeats_and_punctuation_do_not_break_alignment():
    plan = simple_plan("Hello, world!", "model ko... notes?")
    timeline = align(
        plan,
        timed(
            ("um", 0, 0.1),
            ("hello", 0.2, 0.5),
            ("World.", 0.5, 1.0),
            ("model", 1.1, 1.2),
            ("model", 1.25, 1.35),
            ("ko", 1.4, 1.5),
            ("like", 1.5, 1.55),
            ("Notes", 1.6, 1.9),
            duration=2.0,
        ),
        fps=30,
    )
    assert timeline.match_ratio == 1.0
    assert [w.text for w in timeline.scenes[1].words][-1] == "Notes"
    assert timeline.scenes[1].start == pytest.approx(1.0)


def test_touching_whisper_timestamps_keep_first_word_in_its_own_scene():
    plan = simple_plan(
        "Basically RAG mein model ko dobara train nahi kar rahe.",
        "Hum bas model ko notes de rahe hain.",
    )
    spoken = [
        ("Basically", 0.0, 1.18),
        ("RAG", 1.18, 1.68),
        ("mein", 1.68, 1.92),
        ("model", 1.92, 2.70),
        ("ko", 2.70, 2.90),
        ("dobara", 2.90, 3.16),
        ("train", 3.16, 3.48),
        ("nahi", 3.48, 3.78),
        ("kar", 3.78, 3.94),
        ("rahe.", 3.94, 4.82),
        ("Hum", 4.82, 5.00),
        ("bas", 5.00, 5.16),
        ("model", 5.16, 5.50),
        ("ko", 5.50, 5.66),
        ("notes", 5.66, 6.02),
        ("de", 6.02, 6.24),
        ("rahe", 6.24, 6.54),
        ("hain.", 6.54, 7.12),
    ]
    timeline = align(plan, timed(*spoken, duration=7.5), fps=30)
    claim, notes = timeline.scenes
    assert [w.text for w in claim.words][-1] == "rahe."
    assert [w.text for w in notes.words][0] == "Hum"
    assert notes.start <= 4.82
    assert notes.pauses[-1].start == pytest.approx(7.12 - notes.start)


def test_leading_silence_is_a_pause_of_the_first_scene():
    timeline = align(
        simple_plan("a b"), timed(("a", 0.6, 0.9), ("b", 0.9, 1.2), duration=1.3), fps=30
    )
    assert timeline.scenes[0].pauses[0].start == 0.0
    assert timeline.scenes[0].pauses[0].end == pytest.approx(0.6)
