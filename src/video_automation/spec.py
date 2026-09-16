import re
import string
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

SPEC_VERSION = 1
ID_PATTERN = r"^[a-z0-9][a-z0-9_-]*$"
COMPONENT_PATTERN = r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$"
SCENE_ANCHORS = ("start", "end")
PUNCTUATION = string.punctuation + "।॥…“”‘’«»—–"


def tokens(text: str) -> list[str]:
    return [t for t in (w.strip(PUNCTUATION).lower() for w in text.split()) if t]


class EngineError(Exception):
    pass


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class State(StrEnum):
    IDEA = "IDEA"
    CREATIVE_PROPOSAL = "CREATIVE_PROPOSAL"
    AWAITING_APPROVAL_A = "AWAITING_APPROVAL_A"
    APPROVED_CREATIVE = "APPROVED_CREATIVE"
    PRODUCTION_PLAN = "PRODUCTION_PLAN"
    AWAITING_APPROVAL_B = "AWAITING_APPROVAL_B"
    APPROVED_PLAN = "APPROVED_PLAN"
    VOICE_INPUT = "VOICE_INPUT"
    VOICE_ANALYSIS = "VOICE_ANALYSIS"
    GENERATION = "GENERATION"
    PREVIEW = "PREVIEW"
    FINAL = "FINAL"


class Transition(Model):
    at: datetime
    source: State
    target: State
    action: str
    note: str = ""


class Episode(Model):
    id: str = Field(pattern=ID_PATTERN)
    spec_version: int = SPEC_VERSION
    created_at: datetime
    idea: str
    state: State = State.IDEA
    approvals: dict[str, str] = {}
    history: list[Transition] = []


class Proposal(Model):
    title: str = Field(min_length=1)
    concept: str = Field(min_length=1)
    hook: str = Field(min_length=1)
    comedy_direction: str
    analogy: str
    analogy_limitations: str
    technical_explanation: str = Field(min_length=1)
    narrative_structure: list[str] = Field(min_length=1)
    ending: str
    language: str = Field(min_length=1)
    target_duration_seconds: float = Field(gt=0)
    pacing: str = ""
    visual_opportunities: list[str] = []
    sound_opportunities: list[str] = []


class Event(Model):
    at: str = "start"
    offset: float = 0.0
    action: str = Field(min_length=1)
    params: dict[str, Any] = {}


class SoundEvent(Model):
    asset: str = Field(min_length=1)
    event: str = Field(min_length=1)
    at: str = "start"
    offset: float = 0.0
    volume: float = Field(0.6, ge=0, le=4)
    duration: float | None = Field(None, gt=0)
    fade_in: float = Field(0.0, ge=0)
    fade_out: float = Field(0.0, ge=0)


class Visual(Model):
    component: str = Field(pattern=COMPONENT_PATTERN)
    params: dict[str, Any] = {}


class Scene(Model):
    id: str = Field(pattern=ID_PATTERN)
    narration: str = Field(min_length=1)
    visual: Visual
    cues: dict[str, str] = {}
    events: list[Event] = []
    sounds: list[SoundEvent] = []
    notes: str = ""

    @model_validator(mode="after")
    def references_resolve(self) -> "Scene":
        narration = tokens(self.narration)
        if not narration:
            raise ValueError(f"scene {self.id}: narration has no words")
        for name, phrase in self.cues.items():
            if name in SCENE_ANCHORS or not re.fullmatch(r"\w+", name):
                raise ValueError(f"scene {self.id}: invalid cue name {name!r}")
            if find_phrase(narration, tokens(phrase)) is None:
                raise ValueError(
                    f"scene {self.id}: cue {name!r} phrase {phrase!r} not in narration"
                )
        for anchor in [e.at for e in self.events] + [s.at for s in self.sounds]:
            if anchor not in SCENE_ANCHORS and anchor not in self.cues:
                raise ValueError(f"scene {self.id}: unknown anchor {anchor!r}")
        return self


class CaptionPlan(Model):
    enabled: bool = True
    max_chars: int = Field(28, ge=8)
    max_gap_seconds: float = Field(0.6, gt=0)


class Plan(Model):
    scenes: list[Scene] = Field(min_length=1)
    captions: CaptionPlan = CaptionPlan()
    timing_strategy: str = ""
    implementation_notes: str = ""

    @model_validator(mode="after")
    def unique_scene_ids(self) -> "Plan":
        ids = [s.id for s in self.scenes]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate scene ids: {duplicates}")
        return self


def find_phrase(haystack: list[str], needle: list[str]) -> int | None:
    for i in range(len(haystack) - len(needle) + 1):
        if needle and haystack[i : i + len(needle)] == needle:
            return i
    return None


class Word(Model):
    text: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    probability: float = 1.0


class Transcript(Model):
    engine: str
    model: str
    language: str
    duration: float = Field(gt=0)
    words: list[Word]


class Pause(Model):
    start: float
    end: float


class SceneTiming(Model):
    id: str
    start: float
    start_frame: int
    frames: int = Field(gt=0)
    duration: float
    cues: dict[str, float]
    words: list[Word]
    pauses: list[Pause]


class Timeline(Model):
    fps: int
    duration: float
    frames: int
    match_ratio: float
    scenes: list[SceneTiming]
    notes: list[str] = []
