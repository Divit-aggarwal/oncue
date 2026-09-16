# Visual Universe Contract

> Status: draft assembled from `CLAUDE.md` §2, §14, §15. Awaiting creator review.

## Contract

The visual universe is intentionally undefined. It will be designed by the creator over time.

Nothing becomes canonical without explicit creator approval:

* characters and character designs
* locations
* recurring objects and technical entities
* color systems and visual style
* animation language and technical metaphors
* recurring sound identities

Temporary visuals are allowed for development and testing. They must be clearly temporary and must never be promoted automatically.

## How the Engine Hosts a Universe

* A visual component is a Python class deriving from `video_automation.animation.TimedScene`, referenced from `plan.json` as `module:Class`.
* Components receive timing (`scene_duration`, cues, words, pauses), plan `params` and `events`. They never hard-code narration timing.
* Current components:
  * `video_automation.universe.interview_v1:Interview`: canonical, see below.
  * `video_automation.placeholders:TextCard`: temporary, not canonical, used by tests.
  * Episode-local modules in `episodes/<id>/`: scoped to that episode.
* Canonical components live in `src/video_automation/universe/`, one module per component, versioned by name (`interview_v1`, `interview_v2`). Changing a canonical component substantially means adding a new version. Approved plans keep referencing the old one, so earlier episodes stay reproducible.
* Render fingerprints include the component's source files, so changing a component re-renders only the scenes that use it.

The creator's earlier experiment `video.py` (RAG scene) is kept as-is and is not part of the engine.

## Canonical Component: Candidate + Interviewer (`interview_v1`)

> Status: first canonical component. Its interface is the stable part. Its appearance is deliberately neutral, temporary and awaiting creator direction.

### Interface

Plan usage:

```json
"visual": {
  "component": "video_automation.universe.interview_v1:Interview",
  "params": {"on_stage": ["candidate", "interviewer"]}
},
"events": [
  {"at": "start", "action": "enter", "params": {"character": "candidate"}},
  {"at": "question", "action": "speak",
   "params": {"character": "interviewer", "text": "What is RAG?", "until": "answer"}},
  {"at": "answer", "offset": 0.2, "action": "react",
   "params": {"character": "candidate", "reaction": "thinking"}},
  {"at": "end", "offset": -0.5, "action": "exit", "params": {"character": "candidate"}}
]
```

| Item | Values |
| --- | --- |
| characters | `candidate`, `interviewer` |
| scene param `on_stage` | characters already present when the scene starts (default none) |
| `enter` / `exit` | fade in or out with a short sideways move; exit also clears that character's bubble and mark |
| `speak` | shows a speech bubble above the speaker from the event time until the `until` anchor (`start`, `end` or a scene cue; default `end`). `text` is optional and shows `...` when omitted. A new speaker replaces the current bubble. |
| `react` | `neutral` (clears the mark), `surprised` (`!` beside the head), `thinking` (`?` beside the head), `positive` (a nod) |

Rules:

* Unknown actions, characters, reactions or params fail the render with a clear `RenderError`. So does acting on a character who is not on stage.
* Timing comes only from the engine: event times come from the voice-derived cues via `TimedScene.events()`, and `until` resolves through `TimedScene.cue()`.
* Scene time, action time, speech time and cue time are independent. An action happens at its event time, not at scene start.
* Events within one frame of each other animate together. Transitions last at most 0.3 s and are shortened so they never run into the next event.
* An action in the scene's last frame changes state but is not animated.
* A `speak` whose `until` resolves at or before its start (for example `at: "end"` with the default `until`) is a `RenderError`, not a clamped warning. Zero-length speech is always a plan mistake, unlike sounds and events that drift past a scene edge because of voice timing.
* Each scene is rendered independently. Only on-stage presence carries across scenes, declared with `on_stage`. Bubbles and marks do not carry over.

### Deliberately Undefined

Every visual value is in one `Appearance` dataclass at the top of the module: colour (plain white), figure height, stroke width, placement ratios, font sizes, bubble padding and motion distances.

The stick figure reuses the simple shape from the creator's early `video.py` experiment. These are placeholders, not channel rules:

* character design and proportions
* colours (none chosen; everything uses one neutral value)
* expressions and speaking style
* typography
* backgrounds and environments
* animation style

A new look is a new version (`interview_v2`) or a changed `Appearance`. Plans, timing, captions, sound, CLI and approvals do not change.

### Adding Future Components

A component such as an LLM, database or server follows the same pattern:

* a `TimedScene` subclass in `universe/<name>_v1.py`
* its own action vocabulary, validated inside the component
* timing through `events()`, `cue()`, `time_until()` and `hold_until()`

No engine change is needed.
