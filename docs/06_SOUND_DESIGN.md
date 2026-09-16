# Sound Design

> Status: draft assembled from `CLAUDE.md` §9 and the implementation. Awaiting creator review.

## Principles

* The creator's voice is the highest audio priority.
* Sound effects are event-driven: walking → footsteps, door → door sound, notification → notification sound.
* No arbitrary SFX added for drama.
* Sound supports immersion, comedy, clarity and timing.
* Recurring sound identities are part of the visual universe and require creator approval.

## Implementation

* Each plan sound event must name the on-screen `event` it accompanies.
* Timing anchors: scene `start`, `end`, or a narration cue, plus an offset. Sounds follow the real recording automatically.
* Asset lookup: `episodes/<id>/sfx/`, then `assets/sfx/` (configurable `sfx_dirs`). The file extension is optional.
* Per event: `volume` (default 0.6), optional `duration` trim, `fade_in`, `fade_out`.
* Mixing uses FFmpeg `amix` without normalization, so the narration level is untouched. QC warns on clipping.
* A missing asset fails generation. A sound whose requested time does not fit inside the video is moved inside it and reported as a QC warning, matching how animation events are clamped into their scene.
* Ambience is a long sound event with a `duration`.

No sound assets ship with the engine. The creator curates the library.

## Not Yet Implemented

* Automatic ducking of SFX under speech
* Loudness normalization to a platform target
* Noise reduction
