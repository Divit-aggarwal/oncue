from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Animation,
    Circle,
    FadeIn,
    FadeOut,
    Line,
    Mobject,
    Polygon,
    RoundedRectangle,
    Text,
    VGroup,
    there_and_back,
)

from ..animation import RenderError, TimedScene

CHARACTERS = ("candidate", "interviewer")
REACTIONS = ("neutral", "surprised", "thinking", "positive")
ACTION_PARAMS = {
    "enter": frozenset(),
    "exit": frozenset(),
    "speak": frozenset({"text", "until"}),
    "react": frozenset({"reaction"}),
}
SCENE_PARAMS = frozenset({"on_stage"})
TRANSITION_SECONDS = 0.3


@dataclass(frozen=True)
class Appearance:
    color: str = "#FFFFFF"
    figure_height: float = 2.0
    stroke_width: float = 6.0
    horizontal_offset_ratio: float = 0.25
    baseline_ratio: float = -0.175
    bubble_font_size: float = 30.0
    bubble_max_width_ratio: float = 0.8
    bubble_padding: float = 0.18
    mark_font_size: float = 44.0
    entrance_shift: float = 0.6
    nod_depth: float = 0.12


@dataclass(frozen=True)
class Moment:
    time: float
    action: str
    character: str
    params: dict[str, Any] = field(default_factory=dict)
    speech: int | None = None


def plan_moments(
    events: list[dict[str, Any]], cue: Callable[[str], float], duration: float
) -> list[Moment]:
    moments = []
    for index, event in enumerate(events):
        action = event["action"]
        if action not in ACTION_PARAMS:
            raise RenderError(
                f"Interview does not support action {action!r}; "
                f"supported: {', '.join(ACTION_PARAMS)}"
            )
        params = dict(event.get("params", {}))
        character = params.pop("character", None)
        if character not in CHARACTERS:
            raise RenderError(
                f"Interview action {action!r} needs character in {CHARACTERS}, got {character!r}"
            )
        unknown = set(params) - ACTION_PARAMS[action]
        if unknown:
            raise RenderError(f"Interview action {action!r} has unknown params {sorted(unknown)}")
        if action == "react" and params.get("reaction") not in REACTIONS:
            raise RenderError(
                f"Interview reaction must be one of {REACTIONS}, got {params.get('reaction')!r}"
            )
        if action == "speak":
            if not isinstance(params.get("text", ""), str):
                raise RenderError("Interview speak text must be a string")
            until = min(max(cue(params.pop("until", "end")), 0.0), duration)
            if until <= event["time"]:
                raise RenderError(
                    f"Interview speech by {character} ends at {until:.2f}s, "
                    f"not after it starts at {event['time']:.2f}s"
                )
            moments.append(Moment(event["time"], "speak", character, params, index))
            moments.append(Moment(until, "silence", character, {}, index))
        else:
            moments.append(Moment(event["time"], action, character, params))
    return sorted(moments, key=lambda m: m.time)


def group_simultaneous(moments: list[Moment], tolerance: float) -> list[list[Moment]]:
    groups: list[list[Moment]] = []
    for moment in moments:
        if groups and moment.time - groups[-1][0].time < tolerance:
            groups[-1].append(moment)
        else:
            groups.append([moment])
    return groups


def stick_figure(appearance: Appearance) -> VGroup:
    h = appearance.figure_height
    stroke = {"stroke_width": appearance.stroke_width, "color": appearance.color}
    head = Circle(radius=h * 0.14, **stroke).move_to(UP * h * 0.86)
    neck = UP * h * 0.72
    hip = UP * h * 0.38
    body = VGroup(
        Line(neck, hip, **stroke),
        Line(neck + DOWN * h * 0.08, hip + LEFT * h * 0.2 + UP * h * 0.02, **stroke),
        Line(neck + DOWN * h * 0.08, hip + RIGHT * h * 0.2 + UP * h * 0.02, **stroke),
        Line(hip, LEFT * h * 0.13, **stroke),
        Line(hip, RIGHT * h * 0.13, **stroke),
    )
    return VGroup(head, body)


class InterviewStage:
    def __init__(
        self,
        frame_width: float,
        frame_height: float,
        appearance: Appearance,
        on_stage: list[str],
    ):
        unknown = set(on_stage) - set(CHARACTERS)
        if unknown:
            raise RenderError(f"Interview on_stage has unknown characters {sorted(unknown)}")
        self.frame_width = frame_width
        self.appearance = appearance
        baseline = frame_height * appearance.baseline_ratio
        self.side = {"candidate": LEFT, "interviewer": RIGHT}
        self.figures: dict[str, VGroup] = {}
        for name in CHARACTERS:
            figure = stick_figure(appearance)
            figure.move_to(self.side[name] * frame_width * appearance.horizontal_offset_ratio)
            figure.shift(UP * (baseline - figure.get_bottom()[1]))
            self.figures[name] = figure
        self.present = set(on_stage)
        self.bubble: VGroup | None = None
        self.bubble_speech: int | None = None
        self.bubble_owner: str | None = None
        self.marks: dict[str, Mobject] = {}

    def head(self, character: str) -> Mobject:
        return self.figures[character][0]

    def require_present(self, moment: Moment) -> None:
        if moment.character not in self.present:
            raise RenderError(
                f"Interview {moment.action} at {moment.time:.2f}s: "
                f"{moment.character} is not on stage"
            )

    def apply(self, moment: Moment) -> list[Animation]:
        handler = getattr(self, f"_{moment.action}")
        return handler(moment)

    def _enter(self, moment: Moment) -> list[Animation]:
        if moment.character in self.present:
            raise RenderError(f"Interview enter: {moment.character} is already on stage")
        self.present.add(moment.character)
        inward = -self.side[moment.character] * self.appearance.entrance_shift
        return [FadeIn(self.figures[moment.character], shift=inward)]

    def _exit(self, moment: Moment) -> list[Animation]:
        self.require_present(moment)
        self.present.discard(moment.character)
        outward = self.side[moment.character] * self.appearance.entrance_shift
        animations = [FadeOut(self.figures[moment.character], shift=outward)]
        animations += self._clear_mark(moment.character)
        if self.bubble is not None and self.bubble_owner == moment.character:
            animations += self._clear_bubble()
        return animations

    def _speak(self, moment: Moment) -> list[Animation]:
        self.require_present(moment)
        animations = self._clear_bubble()
        self.bubble = self.speech_bubble(moment.character, moment.params.get("text", ""))
        self.bubble_speech = moment.speech
        self.bubble_owner = moment.character
        return [*animations, FadeIn(self.bubble, shift=UP * 0.1)]

    def _silence(self, moment: Moment) -> list[Animation]:
        if self.bubble_speech != moment.speech:
            return []
        return self._clear_bubble()

    def _react(self, moment: Moment) -> list[Animation]:
        self.require_present(moment)
        reaction = moment.params["reaction"]
        animations = self._clear_mark(moment.character)
        if reaction in ("surprised", "thinking"):
            mark = Text(
                "!" if reaction == "surprised" else "?",
                font_size=self.appearance.mark_font_size,
                color=self.appearance.color,
            )
            head = self.head(moment.character)
            mark.next_to(head, self.side[moment.character], buff=self.appearance.bubble_padding)
            self.marks[moment.character] = mark
            animations.append(FadeIn(mark, shift=UP * 0.1))
        if reaction == "positive":
            animations.append(
                self.figures[moment.character]
                .animate(rate_func=there_and_back)
                .shift(DOWN * self.appearance.nod_depth)
            )
        return animations

    def _clear_mark(self, character: str) -> list[Animation]:
        mark = self.marks.pop(character, None)
        return [FadeOut(mark)] if mark is not None else []

    def _clear_bubble(self) -> list[Animation]:
        if self.bubble is None:
            return []
        bubble, self.bubble, self.bubble_speech, self.bubble_owner = self.bubble, None, None, None
        return [FadeOut(bubble)]

    def speech_bubble(self, character: str, text: str) -> VGroup:
        a = self.appearance
        label = Text(text or "...", font_size=a.bubble_font_size, color=a.color)
        max_width = self.frame_width * a.bubble_max_width_ratio - 2 * a.bubble_padding
        if label.width > max_width:
            label.scale_to_fit_width(max_width)
        box = RoundedRectangle(
            corner_radius=a.bubble_padding,
            width=label.width + 2 * a.bubble_padding,
            height=label.height + 2 * a.bubble_padding,
            stroke_width=a.stroke_width * 0.5,
            color=a.color,
        )
        head = self.head(character)
        box.next_to(head, UP, buff=a.bubble_padding * 2)
        half = self.frame_width / 2
        box.shift(RIGHT * (min(half - box.get_right()[0], 0) + max(-half - box.get_left()[0], 0)))
        label.move_to(box)
        tip = head.get_top() + UP * a.bubble_padding * 0.5
        base = box.get_bottom()[1]
        tail_x = min(
            max(head.get_x(), box.get_left()[0] + a.bubble_padding * 2),
            box.get_right()[0] - a.bubble_padding * 2,
        )
        tail = Polygon(
            [tail_x - a.bubble_padding, base, 0],
            [tail_x + a.bubble_padding, base, 0],
            tip,
            stroke_width=a.stroke_width * 0.5,
            color=a.color,
        )
        return VGroup(box, tail, label)


class Interview(TimedScene):
    appearance = Appearance()

    def construct(self) -> None:
        unknown = set(self.params) - SCENE_PARAMS
        if unknown:
            raise RenderError(f"Interview has unknown params {sorted(unknown)}")
        on_stage = self.params.get("on_stage", [])
        if not isinstance(on_stage, list):
            raise RenderError("Interview on_stage must be a list of characters")
        stage = InterviewStage(
            self.camera.frame_width, self.camera.frame_height, self.appearance, on_stage
        )
        self.add(*(stage.figures[name] for name in CHARACTERS if name in stage.present))
        groups = group_simultaneous(
            plan_moments(self.events(), self.cue, self.scene_duration), 1 / self.fps
        )
        for index, group in enumerate(groups):
            self.hold_until(group[0].time)
            animations = [a for moment in group for a in stage.apply(moment)]
            if not animations or self.scene_duration - self.time < 1 / self.fps:
                continue
            following = (
                groups[index + 1][0].time if index + 1 < len(groups) else self.scene_duration
            )
            run_time = max(1 / self.fps, min(TRANSITION_SECONDS, following - self.time))
            self.play(*animations, run_time=run_time)
