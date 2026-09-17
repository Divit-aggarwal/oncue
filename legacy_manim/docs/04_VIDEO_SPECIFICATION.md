# Video Specification

The machine-readable documents that define an episode. The authoritative schemas are the Pydantic models in `src/video_automation/spec.py`. Unknown keys are rejected. Run `video-automation check proposal|plan <file>` to validate a file.

## Output Format

Defaults for short-form vertical video, configurable in `engine.toml`:

| Property | Default |
| --- | --- |
| Resolution | 1080×1920 (9:16) |
| Frame rate | 30 fps |
| Video | H.264, yuv420p, CRF 18 |
| Audio | AAC 192 kbps, 48 kHz stereo |
| Duration | exactly the narration length |
| Captions | burned in, plus `final.srt` sidecar |

Manim scenes render with a frame height of 8 units. The frame width follows the aspect ratio: 4.5 units for 9:16.

## proposal.json (Gate A)

| Field | Type | Required |
| --- | --- | --- |
| `title` | string | yes |
| `concept` | string | yes |
| `hook` | string | yes |
| `comedy_direction` | string | yes (may be empty) |
| `analogy` | string | yes (may be empty) |
| `analogy_limitations` | string | yes: where the analogy stops being technically true |
| `technical_explanation` | string | yes |
| `narrative_structure` | list of strings | yes, at least one |
| `ending` | string | yes |
| `language` | string | yes, e.g. `hinglish` |
| `target_duration_seconds` | number > 0 | yes |
| `pacing` | string | no |
| `visual_opportunities` | list of strings | no |
| `sound_opportunities` | list of strings | no |

## plan.json (Gate B)

```json
{
  "timing_strategy": "free text",
  "implementation_notes": "free text",
  "captions": {"enabled": true, "max_chars": 28, "max_gap_seconds": 0.6},
  "scenes": [
    {
      "id": "claim",
      "narration": "Basically RAG mein model ko dobara train nahi kar rahe.",
      "visual": {
        "component": "video_automation.placeholders:TextCard",
        "params": {"lines": ["RAG"]}
      },
      "cues": {"train": "dobara train"},
      "events": [
        {"at": "train", "offset": 0.0, "action": "show", "params": {"text": "no retraining"}}
      ],
      "sounds": [
        {"asset": "whoosh", "event": "text appears", "at": "train", "offset": 0.0,
         "volume": 0.6, "duration": null, "fade_in": 0.0, "fade_out": 0.0}
      ],
      "notes": "free text"
    }
  ]
}
```

Rules enforced at validation:

* Scene `id`s match `^[a-z0-9][a-z0-9_-]*$` and are unique.
* `narration` contains at least one word. Scene narrations, in order, form the complete script the creator records.
* `visual.component` has the form `module.path:ClassName` and must name a `TimedScene` subclass (checked at render).
* `cues` map a name to a phrase that appears verbatim in the scene narration, ignoring case and punctuation.
* Every event and sound `at` is `start`, `end`, or a cue name defined in that scene.
* Every sound event names the on-screen `event` it accompanies.
* `volume` is between 0 and 4. `duration` is greater than 0 if present. Fades are 0 or more.

Events are interpreted by the component. `TextCard` supports `show` (`params.text`) and `clear`. `interview_v1:Interview` supports `enter`, `exit`, `speak` and `react` (see `08_VISUAL_UNIVERSE_CONTRACT.md`). Camera moves and transitions are expressed the same way: an event `action` implemented by the component.

## Generated Artifacts

| File | Schema |
| --- | --- |
| `build/transcript.json` | `Transcript`: engine, model, language, duration, words[text, start, end, probability] |
| `build/timeline.json` | `Timeline`: fps, duration, frames, match_ratio, scenes[id, start, start_frame, frames, duration, cues, words, pauses] |
| `build/manifest.json` | stage name → fingerprint |
| `build/scenes/<id>.json` | rendered vs planned seconds |
| `output/final.json` | output metadata and QC report |

Scene `words` and `pauses` in `timeline.json` are relative to the scene start. `transcript.json` times are absolute.
