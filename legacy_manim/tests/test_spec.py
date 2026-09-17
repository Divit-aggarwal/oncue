import copy

import pytest
from pydantic import ValidationError

from video_automation.spec import Plan, tokens

from conftest import SCENES


def plan_with(**changes):
    scene = copy.deepcopy(SCENES[0]) | changes
    return {"scenes": [scene, copy.deepcopy(SCENES[1])]}


def test_valid_plan():
    assert len(Plan.model_validate({"scenes": SCENES}).scenes) == 2


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"cues": {"train": "not spoken here"}}, "not in narration"),
        ({"events": [{"at": "missing", "action": "show"}]}, "unknown anchor"),
        ({"sounds": [{"asset": "tone", "event": "x", "at": "nowhere"}]}, "unknown anchor"),
        ({"sounds": [{"asset": "tone", "at": "start"}]}, "event"),
        ({"visual": {"component": "not a component"}}, "pattern"),
        ({"id": "Bad Id"}, "pattern"),
        ({"narration": "  ...  "}, "no words"),
        ({"surprise": 1}, "Extra inputs"),
    ],
)
def test_malformed_plans_are_rejected(changes, message):
    with pytest.raises(ValidationError, match=message):
        Plan.model_validate(plan_with(**changes))


def test_duplicate_scene_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        Plan.model_validate({"scenes": [SCENES[1], SCENES[1]]})


def test_tokens_keep_hinglish_and_devanagari():
    assert tokens("Basically, RAG mein — model ko 'dobara' train?") == [
        "basically",
        "rag",
        "mein",
        "model",
        "ko",
        "dobara",
        "train",
    ]
    assert tokens("मॉडल को दोबारा train नहीं।") == ["मॉडल", "को", "दोबारा", "train", "नहीं"]
