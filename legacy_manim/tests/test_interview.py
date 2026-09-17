import json
import re
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from video_automation import pipeline, workflow
from video_automation.animation import RenderError
from video_automation.spec import Plan
from video_automation.universe import interview_v1
from video_automation.universe.interview_v1 import (
    Appearance,
    InterviewStage,
    Moment,
    group_simultaneous,
    plan_moments,
)
from video_automation.voice import ingest

from conftest import SCENES, FakeTranscriber, ffmpeg, requires_ffmpeg, spoken_words

COMPONENT = "video_automation.universe.interview_v1:Interview"
FRAME_WIDTH, FRAME_HEIGHT = 4.5, 8.0


def event(action, time=0.0, **params):
    return {"action": action, "time": time, "params": params}


def cues(**known):
    table = {"start": 0.0, "end": 5.0, **known}

    def resolve(name):
        if name not in table:
            raise RenderError(f"unknown cue {name!r}")
        return table[name]

    return resolve


def stage(on_stage=()):
    return InterviewStage(FRAME_WIDTH, FRAME_HEIGHT, Appearance(), list(on_stage))


def box(mobject):
    return (
        mobject.get_left()[0],
        mobject.get_right()[0],
        mobject.get_bottom()[1],
        mobject.get_top()[1],
    )


def test_speech_expands_into_start_and_cue_bounded_end():
    moments = plan_moments(
        [
            event("enter", 0.0, character="candidate"),
            event("speak", 1.0, character="candidate", text="hello", until="answer"),
            event("react", 2.0, character="candidate", reaction="thinking"),
        ],
        cues(answer=3.5),
        5.0,
    )
    assert [(m.time, m.action) for m in moments] == [
        (0.0, "enter"),
        (1.0, "speak"),
        (2.0, "react"),
        (3.5, "silence"),
    ]
    assert moments[1].params == {"text": "hello"}
    assert moments[1].speech == moments[3].speech


def test_speech_defaults_to_scene_end():
    moments = plan_moments([event("speak", 1.0, character="interviewer")], cues(), 5.0)
    assert moments[-1] == Moment(5.0, "silence", "interviewer", {}, 0)


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (event("dance", character="candidate"), "does not support action 'dance'"),
        (event("enter"), "needs character"),
        (event("enter", character="narrator"), "needs character"),
        (event("enter", character="candidate", speed=2), "unknown params"),
        (event("react", character="candidate", reaction="angry"), "reaction must be one of"),
        (event("react", character="candidate"), "reaction must be one of"),
        (event("speak", 2.0, character="candidate", until="early"), "not after it starts"),
        (event("speak", character="candidate", until="missing"), "unknown cue"),
        (event("speak", character="candidate", text=3), "must be a string"),
    ],
)
def test_invalid_events_are_rejected(bad, message):
    with pytest.raises(RenderError, match=message):
        plan_moments([bad], cues(early=1.0), 5.0)


def test_simultaneous_moments_play_together():
    moments = [
        Moment(1.0, "enter", "candidate"),
        Moment(1.01, "enter", "interviewer"),
        Moment(2.0, "exit", "candidate"),
    ]
    assert [len(g) for g in group_simultaneous(moments, 1 / 30)] == [2, 1]


def test_characters_have_stable_positions_inside_the_frame_above_captions():
    first, second = stage(), stage(["candidate", "interviewer"])
    caption_top = -FRAME_HEIGHT / 2 + FRAME_HEIGHT * 0.18 + 0.5
    for name in interview_v1.CHARACTERS:
        assert (first.figures[name].get_center() == second.figures[name].get_center()).all()
        left, right, bottom, top = box(first.figures[name])
        assert -FRAME_WIDTH / 2 < left < right < FRAME_WIDTH / 2
        assert caption_top < bottom < top < FRAME_HEIGHT / 2
    assert box(first.figures["candidate"])[1] < box(first.figures["interviewer"])[0]


@pytest.mark.parametrize("character", interview_v1.CHARACTERS)
def test_long_speech_bubble_stays_inside_the_frame_above_the_speaker(character):
    s = stage([character])
    s.apply(Moment(0.0, "speak", character, {"text": "a very long line of speech " * 3}, 0))
    left, right, bottom, top = box(s.bubble)
    assert -FRAME_WIDTH / 2 <= left and right <= FRAME_WIDTH / 2 and top < FRAME_HEIGHT / 2
    assert bottom > s.head(character).get_top()[1] - 0.2


def test_entrance_exit_and_presence_rules():
    s = stage()
    with pytest.raises(RenderError, match="not on stage"):
        s.apply(Moment(0.0, "speak", "candidate", {}, 0))
    assert s.apply(Moment(0.0, "enter", "candidate"))
    assert s.present == {"candidate"}
    with pytest.raises(RenderError, match="already on stage"):
        s.apply(Moment(0.5, "enter", "candidate"))
    s.apply(Moment(1.0, "speak", "candidate", {"text": "hi"}, 1))
    s.apply(Moment(1.5, "react", "candidate", {"reaction": "surprised"}))
    s.apply(Moment(2.0, "exit", "candidate"))
    assert s.present == set() and s.bubble is None and s.marks == {}
    with pytest.raises(RenderError, match="not on stage"):
        s.apply(Moment(3.0, "exit", "candidate"))


def test_new_speaker_replaces_bubble_and_old_speech_end_does_not_remove_it():
    s = stage(["candidate", "interviewer"])
    s.apply(Moment(0.0, "speak", "candidate", {"text": "first"}, 0))
    s.apply(Moment(1.0, "speak", "interviewer", {"text": "second"}, 1))
    assert s.bubble_owner == "interviewer"
    assert s.apply(Moment(2.0, "silence", "candidate", {}, 0)) == []
    assert s.bubble is not None
    assert s.apply(Moment(3.0, "silence", "interviewer", {}, 1))
    assert s.bubble is None


def test_reaction_mark_never_overlaps_the_speakers_bubble():
    for character in interview_v1.CHARACTERS:
        s = stage([character])
        s.apply(Moment(0.0, "react", character, {"reaction": "thinking"}))
        s.apply(Moment(0.0, "speak", character, {"text": "a long answer " * 4}, 0))
        mark_left, mark_right, mark_bottom, mark_top = box(s.marks[character])
        left, right, bottom, top = box(s.bubble)
        assert mark_top < bottom or mark_right < left or mark_left > right
        assert -FRAME_WIDTH / 2 < mark_left and mark_right < FRAME_WIDTH / 2


def test_reactions_add_replace_and_clear_marks():
    s = stage(["candidate"])
    s.apply(Moment(0.0, "react", "candidate", {"reaction": "thinking"}))
    thinking = s.marks["candidate"]
    s.apply(Moment(1.0, "react", "candidate", {"reaction": "surprised"}))
    assert s.marks["candidate"] is not thinking
    assert s.apply(Moment(2.0, "react", "candidate", {"reaction": "positive"}))
    assert "candidate" not in s.marks
    s.apply(Moment(3.0, "react", "candidate", {"reaction": "thinking"}))
    s.apply(Moment(4.0, "react", "candidate", {"reaction": "neutral"}))
    assert "candidate" not in s.marks


def test_on_stage_rejects_unknown_characters():
    with pytest.raises(RenderError, match="unknown characters"):
        stage(["narrator"])


def test_every_shape_uses_the_single_appearance_colour():
    s = stage(["candidate", "interviewer"])
    s.apply(Moment(0.0, "speak", "candidate", {"text": "hi"}, 0))
    s.apply(Moment(0.0, "react", "interviewer", {"reaction": "thinking"}))
    shapes = [*s.figures.values(), s.bubble, *s.marks.values()]
    colours = {
        m.get_stroke_color().to_hex().upper()
        if m.get_stroke_width()
        else m.get_fill_color().to_hex().upper()
        for shape in shapes
        for m in shape.family_members_with_points()
    }
    assert colours == {Appearance().color}


def test_component_contains_no_episode_specific_logic():
    source = Path(interview_v1.__file__).read_text().lower()
    plan = json.loads((Path(__file__).parents[1] / "examples/smoke/plan.json").read_text())
    specific = {"smoke", "rag"}
    for scene in plan["scenes"]:
        specific |= {scene["id"], *scene.get("cues", {})}
        specific |= {e["params"].get("text", "").lower() for e in scene.get("events", [])}
    specific.discard("")
    found = {word for word in specific if re.search(rf"\b{re.escape(word)}\b", source)}
    assert found == set()


def interview_plan(first_events, second_events, second_on_stage):
    claim, notes = json.loads(json.dumps(SCENES))
    claim["visual"] = {"component": COMPONENT, "params": {"on_stage": []}}
    claim["events"] = first_events
    claim["sounds"] = []
    notes["visual"] = {"component": COMPONENT, "params": {"on_stage": second_on_stage}}
    notes["events"] = second_events
    return {"scenes": [claim, notes]}


def approve_plan(ep, plan, settings, tmp_path):
    Plan.model_validate(plan)
    ep.document_path("plan").write_text(json.dumps(plan))
    workflow.submit(ep, "plan")
    workflow.approve(ep)
    recording = tmp_path / "take.wav"
    if not recording.exists():
        ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=6", str(recording))
    ingest(recording, ep.voice_dir, settings.voice.silence_threshold_db)
    workflow.transition(ep, "provide_voice")


def left_side_has_figure(video, seconds, tmp_path):
    frame = tmp_path / f"frame_{seconds:.3f}.png"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(frame),
        ],
        check=True,
    )
    image = Image.open(frame).convert("L")
    width, height = image.size
    region = image.crop((0, int(height * 0.3), width // 2, int(height * 0.7)))
    return region.point(lambda v: 255 if v > 60 else 0).getbbox() is not None


@requires_ffmpeg
@pytest.mark.media
def test_component_renders_in_two_scenes_driven_by_voice_cues(approved_episode, tmp_path):
    ep, settings = approved_episode
    plan = interview_plan(
        [
            {"at": "start", "action": "enter", "params": {"character": "interviewer"}},
            {"at": "train", "action": "enter", "params": {"character": "candidate"}},
            {
                "at": "train",
                "offset": 0.4,
                "action": "speak",
                "params": {"character": "candidate", "text": "hi"},
            },
        ],
        [
            {
                "at": "start",
                "offset": 0.2,
                "action": "react",
                "params": {"character": "interviewer", "reaction": "surprised"},
            },
            {
                "at": "start",
                "offset": 0.3,
                "action": "speak",
                "params": {"character": "interviewer", "until": "end"},
            },
            {"at": "end", "offset": -0.5, "action": "exit", "params": {"character": "candidate"}},
        ],
        ["candidate", "interviewer"],
    )
    approve_plan(ep, plan, settings, tmp_path)
    report = pipeline.generate(ep, settings, FakeTranscriber(spoken_words(), 6.0))
    assert report.ok, report.errors
    assert report.warnings == []

    timeline = json.loads((ep.build / "timeline.json").read_text())
    claim, notes = timeline["scenes"]
    enters = claim["start"] + claim["cues"]["train"]
    exits = notes["start"] + notes["duration"] - 0.5
    video = ep.output / "final.mp4"
    assert not left_side_has_figure(video, enters - 0.2, tmp_path)
    assert left_side_has_figure(video, enters + 0.5, tmp_path)
    assert left_side_has_figure(video, notes["start"] + 0.1, tmp_path)
    assert not left_side_has_figure(video, exits + 0.4, tmp_path)

    take2 = tmp_path / "take2.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=330:duration=5", str(take2))
    ingest(take2, ep.voice_dir, settings.voice.silence_threshold_db)
    workflow.transition(ep, "provide_voice")
    faster = FakeTranscriber(spoken_words(step=0.2), 5.0)
    assert pipeline.generate(ep, settings, faster).ok
    assert faster.calls == 1
    moved = json.loads((ep.build / "timeline.json").read_text())["scenes"][0]
    earlier = moved["start"] + moved["cues"]["train"]
    assert earlier < enters
    assert not left_side_has_figure(video, earlier - 0.2, tmp_path)
    assert left_side_has_figure(video, earlier + 0.5, tmp_path)


@requires_ffmpeg
@pytest.mark.media
def test_unsupported_action_fails_the_render_with_a_clear_error(approved_episode, tmp_path):
    ep, settings = approved_episode
    plan = interview_plan(
        [{"at": "start", "action": "dance", "params": {"character": "candidate"}}], [], []
    )
    approve_plan(ep, plan, settings, tmp_path)
    with pytest.raises(RenderError, match="does not support action 'dance'"):
        pipeline.generate(ep, settings, FakeTranscriber(spoken_words(), 6.0))
    assert ep.load().state == workflow.State.GENERATION
