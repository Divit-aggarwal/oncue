# AI Explainer Video Engine

A local-first production system for creating short and long-form animated technical explainer videos.

The system is designed for a human-directed workflow:

**Idea → Creative Development → Human Approval → Implementation Plan → Human Approval → Voice → Animation → Sound Design → Compositing → Final Video**

The system is not intended to autonomously invent the creator's visual identity.

## Core Objective

Create technically accurate, entertaining, highly recognizable animated explainers for an Indian audience, initially using Hinglish and the creator's own voice.

The system should eventually support:

* Short-form Instagram/Reels content
* Longer technical videos
* Hinglish and English
* User-recorded narration
* Animation synchronized to narration
* Subtle environmental and character sound effects
* Automatic captions
* Reusable visual components
* Reusable animation patterns
* Consistent visual identity
* Human approval at creative checkpoints
* Local-first processing

## Core Principle

The creator is the director.

AI assists with:

* creative exploration
* scripting
* technical explanation
* storyboarding
* implementation planning
* coding
* debugging
* timing
* production assistance

AI does not own:

* the visual identity
* recurring character design
* comedic identity
* brand personality
* final creative decisions
* the visual universe

## Target Workflow

1. Creator provides a rough video idea.
2. System develops the concept.
3. System proposes creative directions.
4. Creator modifies or approves the direction.
5. System creates a detailed implementation plan.
6. Creator approves the implementation plan.
7. Creator provides narration.
8. System analyzes narration and timing.
9. System generates animation.
10. System adds approved sound effects.
11. System generates captions.
12. System composites the final video.
13. Creator reviews the final output.

## Design Philosophy

The system should be:

* local-first
* modular
* deterministic where possible
* human-controlled
* reusable
* extensible
* easy to debug
* inexpensive to operate

The system should avoid unnecessary AI agents, unnecessary cloud APIs, and unnecessary abstraction.

## Technology

* Manim for programmatic animation
* Python for orchestration
* faster-whisper (local Whisper) for speech recognition
* FFmpeg for media processing and compositing
* Claude Code (or any assistant) as the development and reasoning assistant

The architecture must remain model-agnostic so that other AI systems can be introduced later without rewriting the production engine.

## Current Scope

The production pipeline is implemented. See [docs/02_SYSTEM_ARCHITECTURE.md](docs/02_SYSTEM_ARCHITECTURE.md).

The creator's visual universe will be designed separately over time.

No automatic visual-universe generation is permitted by default.

## Setup

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/), FFmpeg on `PATH` (`brew install ffmpeg`), and the Manim system libraries (Cairo, Pango).

```bash
uv sync
uv run video-automation --help
```

The first transcription downloads the configured Whisper model from Hugging Face (about 480 MB for `small`). After that, everything runs offline.

## Producing an Episode

Run the commands from this directory. Episodes live in `episodes/<id>/`.

```bash
uv run video-automation new rag-basics --idea "RAG explained as an open-book exam"
# write episodes/rag-basics/proposal.json
uv run video-automation submit rag-basics proposal
uv run video-automation approve rag-basics          # Gate A, or: changes rag-basics --note "..."
# write episodes/rag-basics/plan.json
uv run video-automation submit rag-basics plan
uv run video-automation approve rag-basics          # Gate B
uv run video-automation voice rag-basics ~/Recordings/take1.m4a
uv run video-automation analyze rag-basics          # optional: inspect scene timing
uv run video-automation generate rag-basics         # writes output/final.mp4
uv run video-automation finalize rag-basics
```

`status <id>` prints the current state and the next step. `list` shows all episodes. `check plan <file>` validates a document without submitting it.

Editing `proposal.json` or `plan.json` after approval blocks generation until the document is resubmitted and approved again.

To revise, change a layer and run `generate` again. Only stages whose inputs changed run again:

| Change | Re-runs |
| --- | --- |
| new recording (`voice`) | transcription, timing, affected scenes, mix, captions, compose |
| edited `build/transcript.json` | timing, captions, and anything the timing moved |
| scene params or component code | that scene, compose |
| sound events | mix, compose |
| caption style | captions, compose |

A complete example proposal and plan lives in `examples/smoke/`.

## Episode Files

```text
episodes/<id>/
  episode.json      state, approvals (document hashes), history
  proposal.json     Gate A document
  plan.json         Gate B document
  *.py              optional episode-specific Manim components
  sfx/              optional episode-specific sound assets
  voice/            the narration recording (git-ignored)
  build/            transcript.json and timeline.json (tracked); renders, mix, manifest, logs (git-ignored)
  output/           final.json metadata + QC report and final.srt (tracked); final.mp4 (git-ignored)
```

## Configuration

Optional `engine.toml` in the project root. Every key has a default:

```toml
episodes_dir = "episodes"
sfx_dirs = ["assets/sfx"]

[video]
width = 1080
height = 1920
fps = 30
crf = 18
audio_bitrate = "192k"
sample_rate = 48000

[voice]
model = "small"              # any faster-whisper model: tiny, base, small, medium, large-v3, turbo
language = "en"              # "en" keeps Roman Hinglish; "hi" gives Devanagari; "auto" detects
device = "auto"
compute_type = "default"
use_script_as_prompt = true  # bias spelling toward the approved narration
silence_threshold_db = -50.0

[render]
workers = 3                  # scenes rendered in parallel

[captions]
font_size = 40
max_width_ratio = 0.9
bottom_margin_ratio = 0.18
stroke_width = 8
```

## Development

```bash
uv run pytest                              # unit + real manim/ffmpeg integration tests
VAE_WHISPER_TEST=1 uv run pytest -m whisper  # macOS: synthesizes speech with `say`, runs real Whisper
uv run ruff check src tests && uv run ruff format --check src tests
```

The codebase intentionally contains no comments. Documentation lives in `docs/`.

## Troubleshooting

* `error: ... changed after approval`: resubmit and re-approve the document.
* `scene X failed to render (log: ...)`: open the log. The stage is not marked complete, so fix the problem and run `generate` again.
* `episode is busy`: another command is running on this episode. The lock is released automatically when that process exits or crashes.
* `none of its narration was found in the recording`: the recording doesn't contain that scene's narration. Re-record, or correct `build/transcript.json` and run `generate` again.
* QC warning `animation runs Xs past its narration and was cut`: the scene's animation is longer than the spoken section. Shorten it or use `time_until`/`hold_until`.
* Ctrl+C is safe. Completed stages are kept, and the next run resumes from the first incomplete stage.
