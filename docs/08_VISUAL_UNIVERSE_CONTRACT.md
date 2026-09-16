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
  * `video_automation.placeholders:TextCard`: temporary, not canonical.
  * Episode-local modules in `episodes/<id>/`: scoped to that episode.
* A future canonical library is an importable package (for example `universe/`) whose modules are versioned by name (`characters.v1`, `characters.v2`). Changing a canonical component substantially means adding a new version. Approved plans keep referencing the old one, so earlier episodes stay reproducible.
* Render fingerprints include the component's source files, so changing a component re-renders only the scenes that use it.

The creator's earlier experiment `video.py` (RAG scene) is kept as-is and is not part of the engine.
