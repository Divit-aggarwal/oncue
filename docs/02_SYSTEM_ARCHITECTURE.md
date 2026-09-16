# System Architecture

This document describes the architecture as implemented.

## Overview

```text
proposal.json ──Gate A──▶ plan.json ──Gate B──▶ voice recording
                                                    │
                                   voice.wav ◀──────┘
                                       │
                         faster-whisper transcript.json
                                       │
                  plan narration ──▶ align ──▶ timeline.json
                                       │
          ┌────────────────────────────┼──────────────────────────┐
          ▼                            ▼                          ▼
  Manim scene renders           SFX schedule + mix         caption segments
  build/scenes/<id>.mp4         build/mix.wav              build/captions/*.png, final.srt
          └────────────────────────────┼──────────────────────────┘
                                       ▼
                         FFmpeg compose → output/final.mp4
                                       ▼
                        QC validation → output/final.json
```

One Python package, `src/video_automation/`, with one module per production layer:

| Module | Responsibility | Depends on |
| --- | --- | --- |
| `spec.py` | Pydantic schemas for every artifact, `EngineError` base, tokenizer | pydantic |
| `config.py` | `engine.toml` settings with defaults | pydantic, tomllib |
| `workflow.py` | Episode directory, state machine, hash-pinned approvals, atomic writes, episode lock | spec |
| `media.py` | FFmpeg/ffprobe subprocess wrapper, probing, volume stats | ffmpeg |
| `voice.py` | Recording validation and ingest, WAV conversion, `Transcriber` interface, faster-whisper backend, script-to-recording alignment | spec, media |
| `animation.py` | `TimedScene` base class for Manim components, isolated render subprocess | manim, spec |
| `placeholders.py` | Temporary, non-canonical `TextCard` component used by tests | animation |
| `universe/interview_v1.py` | First canonical component: Candidate + Interviewer (see `docs/08_VISUAL_UNIVERSE_CONTRACT.md`) | animation |
| `sound.py` | Asset resolution, event scheduling from the timeline, FFmpeg mix | spec, media |
| `captions.py` | Caption segmentation, SRT, caption images rendered through Manim/Pango | spec, manim |
| `compose.py` | One FFmpeg pass: frame-exact scene concat, caption overlays, audio mux | media |
| `validate.py` | QC report on the final output | media, spec |
| `pipeline.py` | Stage orchestration, fingerprint manifest, output metadata | all layers |
| `cli.py` | Command-line interface | workflow, pipeline |

Boundaries:

* The creative documents (`proposal.json`, `plan.json`) reference visual components only by import path (`module:Class`). They contain no Manim code.
* Voice processing produces `transcript.json` and `timeline.json` and knows nothing about Manim.
* Sound events are anchored to scene cues, not to visual components.
* Every layer communicates through a JSON artifact on disk that can be inspected and edited.

## Episode Lifecycle

States follow `docs/09_APPROVAL_AND_GENERATION_PROTOCOL.md`:

```text
IDEA → AWAITING_APPROVAL_A → APPROVED_CREATIVE → AWAITING_APPROVAL_B → APPROVED_PLAN
     → VOICE_INPUT → VOICE_ANALYSIS → GENERATION → PREVIEW → FINAL
```

`CREATIVE_PROPOSAL` and `PRODUCTION_PLAN` are the drafting states entered when the creator requests changes at a gate. The transition table in `workflow.py` rejects every other move. Returning to an earlier stage is explicit:

* `submit <id> proposal` from any non-final state returns to Gate A and revokes both approvals.
* `submit <id> plan` from any state after Gate A returns to Gate B and revokes the plan approval.
* `voice <id> <file>` from any state after Gate B replaces the recording.
* `reopen <id>` moves `FINAL` back to `PREVIEW`.

Approval stores the SHA-256 of the approved document. `analyze`, `generate` and `voice` refuse to run if the document on disk no longer matches that hash. Silence is not approval.

Each episode transition is appended to `episode.json` `history` with a timestamp and optional note.

## Stage Execution and Caching

`pipeline.generate` runs these stages in order:

1. `voice_wav`: convert the recording to 48 kHz stereo PCM (mono recordings are duplicated to both channels at their original level)
2. `transcript`: faster-whisper with word timestamps, VAD disabled so pauses survive, prompted with the approved narration
3. `timeline`: align the plan to the transcript
4. `scene:<id>`: one Manim render per scene, run in parallel (`render.workers`)
5. `sound_mix`: voice plus scheduled SFX
6. `captions`: segment the transcript, render caption PNGs, write `final.srt`
7. `compose`: final MP4
8. QC validation and `final.json` metadata

Each stage records a fingerprint in `build/manifest.json`. The fingerprint is a SHA-256 of the stage's inputs (content hashes of input files, relevant settings and spec fragments) plus the source of the engine modules that implement it. The `timeline` stage also hashes `spec.py`, because tokenization lives there. For scenes it also includes every `.py` file in the component's directory. A stage runs again only if its fingerprint changed or an output is missing.

Failure and interruption:

* Outputs are written to a temporary name and renamed into place.
* The stage entry is removed before a stage runs and written back only after its outputs exist, so an interrupted stage always runs again.
* A failed render leaves its log in `build/logs/<scene>.log`. The episode stays in `GENERATION`.
* `episode.json` and the manifest are written atomically.
* A per-episode `.lock` file protected by an OS file lock (`fcntl.flock`, POSIX only) prevents concurrent commands. The OS releases the lock automatically when a process dies.

Deliberate limitations:

* The `transcript` stage does not fingerprint `voice.py`, so a change to the transcription code does not re-transcribe existing episodes. Delete `build/transcript.json` to force it.
* Changing any scene's narration changes the Whisper prompt and triggers transcription again, which overwrites manual edits to `build/transcript.json`.
* The component fingerprint covers the component module's directory, not modules it imports from elsewhere.
* Recording, render and output media are git-ignored. `build/transcript.json`, `build/timeline.json`, `output/final.json` and `output/final.srt` are tracked, so timing and output metadata can be versioned with the episode.

## Timing Bridge

`voice.align` maps the approved narration onto the actual recording:

1. Scene narration and transcript words are tokenized the same way: whitespace split, punctuation stripped (including `।`), lowercased. Devanagari and Roman Hindi are kept as-is.
2. `difflib.SequenceMatcher` matches script tokens to spoken tokens. Ad-libs and misrecognitions are tolerated. `match_ratio` is recorded, and a value below 0.5 produces a QC warning.
3. Each scene after the first starts 0.2 s before its first spoken word, never earlier than the previous word's end, rounded down to a frame. The first scene starts at 0 and the last ends at the end of the recording, so pauses belong to the scene they follow.
4. Boundaries are snapped to the frame grid. Scene frame counts sum exactly to the total, so there is no cumulative drift. Every scene gets at least one frame: boundaries that would collide (Whisper often gives consecutive words identical, zero-length timestamps) are nudged forward and recorded in `timeline.json` `notes`. A recording with fewer frames than scenes is an error.
5. Cues (`"cues": {"notes": "brought notes"}`) resolve to the start time of the first matched word at or after the phrase, relative to the scene start and clamped inside the scene. If Whisper recognised none of those words, the cue falls back to the end of the last recognised word before the phrase (or the scene start), and a note is recorded.
6. Each scene carries the words assigned to it by alignment (not by timestamp, since Whisper words often touch across the boundary) and every silence of 0.3 s or longer, including silence before its first word and after its last word.

Components never hard-code the video duration. `TimedScene` exposes:

| Member | Meaning |
| --- | --- |
| `scene_duration` | seconds this scene occupies in the recording |
| `cue(name)` | seconds from scene start (`start`, `end`, or a plan cue) |
| `events()` | plan events with resolved `time`, sorted |
| `time_until(moment)` | seconds left until a cue or time, for choosing `run_time` |
| `hold_until(moment)` | wait until a cue or time |
| `params`, `words`, `pauses`, `fps` | plan params and scene-local timing |

After `construct`, the scene is padded to its duration. The compose step pads or trims every scene to its exact frame count. Animation that overruns is cut, and QC reports it.

## Visual Universe Extension Point

A component is any `TimedScene` subclass that can be imported:

* built-in temporary: `video_automation.placeholders:TextCard`
* canonical, creator-approved: `video_automation.universe.<name>_v<N>:<Class>`, currently `video_automation.universe.interview_v1:Interview`
* episode-local: `episodes/<id>/scenes.py` → `scenes:MyScene` (the episode directory is on the import path during renders)

Versioning uses module names (`..._v1`, `..._v2`). Existing plans keep pointing at the version they were approved with. The engine itself (timing, pipeline, CLI) knows nothing about any component's internals. It passes timing, `params` and `events` to whichever class the plan names. `placeholders.py` exists only for tests.

## Sound

Assets resolve by name from `episodes/<id>/sfx/`, then each `sfx_dirs` entry. The extension may be omitted. Each plan sound event names the on-screen `event` it accompanies, an anchor (`start`, `end` or a cue), offset, volume (default 0.6), optional duration and fades. The mix is `amix` with `normalize=0`, so the voice keeps its original level. Peaks at or above -0.1 dBFS produce a clipping warning.

## Captions

Captions come from the transcript: the spoken words, never translated. Caption times are clamped to the video duration. A new caption starts when adding a word would exceed `max_chars`, after a gap longer than `max_gap_seconds`, or after sentence-ending punctuation. Each caption stays up for 0.4 s after its last word, but never overlaps the next one.

The system FFmpeg build has no libass or drawtext, so captions are rendered as transparent PNGs through Manim/Pango, which shapes Devanagari correctly. They are overlaid in the compose pass. All captions in an episode share one scale factor. `output/final.srt` is written as a sidecar. The caption style is a temporary default.

## Output and QC

`output/final.mp4`: H.264 `yuv420p`, AAC, `+faststart`, at the configured resolution and frame rate.

QC errors keep the episode in `GENERATION`:

* stream count
* frame size
* frame rate
* exact frame count
* duration versus narration (±0.1 s)
* full decode without errors
* silent mix
* overlapping captions or captions past the end
* caption word count differing from the transcript

QC warnings:

* clipping
* low script match ratio
* animation overrun
* timeline notes (moved boundaries, estimated cues)
* scenes shorter than 0.5 s
* animation events whose time falls outside their scene (clamped into the scene)
* sounds whose requested time does not fit the video (moved inside it)

`output/final.json` records approvals, voice hash, transcript engine, model and language, sound events, full settings, tool versions, output hash and the QC report.
