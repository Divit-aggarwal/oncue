# AI Explainer Video Engine

A local-first production system for creating short and long-form animated technical explainer videos.

The system is designed for a human-directed workflow:

**Concept → Storyboard → Creator Approval → Voice → Timings → Animation → Render → Creator Review**

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

## Workflow

1. Creator describes a concept.
2. Assistant writes `storyboards/<slug>.md`: hook, 4–6 beats, each with the exact sentence to say and what appears on screen. Iterate until the creator says "approved".
3. Creator records the voiceover.
4. `transcribe.py` cleans the recording and extracts word timings with local Whisper.
5. Assistant writes the scene from reusable components, timed to the words.
6. `npm run render` produces the MP4 and checks audio, loudness, duration and beat sync.
7. Creator reviews; feedback is applied per beat.

The full step-by-step checklist lives in `CLAUDE.md` §0.

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

* [Revideo](https://docs.re.video) 0.11 (TypeScript, a Motion Canvas fork) for animation and headless rendering with audio
* faster-whisper (local Whisper) for word timestamps
* DeepFilterNet `deep-filter` CLI for local, CPU-only voice denoising
* FFmpeg for audio cleanup, loudness normalization and checks
* Node 26 and uv (Python 3.13)
* Claude Code (or any assistant) as the development and reasoning assistant

The architecture remains model-agnostic: the production engine is plain files (storyboards, timings, scenes) and CLI commands.

## Setup

Requirements: Node ≥ 18 (developed on 26), FFmpeg on `PATH` (`brew install ffmpeg`), [uv](https://docs.astral.sh/uv/).

```bash
cd video
npm install
scripts/setup-deep-filter.sh     # downloads the denoiser into scripts/bin/ and checks its sha256
cp .env.example .env             # optional: DEEP_FILTER_ATTEN_LIM
```

The first transcription downloads the Whisper `small` model (about 480 MB). After that, everything runs offline.

## Making a Reel

From `video/`:

```bash
scripts/new-reel.sh rag-basics                                   # storyboard + scene templates
uv run python scripts/transcribe.py rag-basics ~/Recordings/take1.m4a
npm run render -- rag-basics                                     # output/rag-basics.mp4
VITE_SLUG=rag-basics npm run preview                             # optional: editor at http://localhost:9000
```

`render` prints the output path, duration, size, loudness and how late each beat's visual starts after its first word, and flags a duration outside 30–60s or a beat more than 0.3s late.

## Layout

```text
storyboards/<slug>.md          storyboard (the approval document)
docs/                          product docs; docs/COMPONENTS.md for the component library
video/src/scenes/<slug>.tsx    one scene per reel
video/src/components/          ConceptBox, Arrow, FlowStep, Tag, Headline, Highlight
video/src/motions/             fadeIn, fadeOut, slideIn, draw, highlight, clearScene
video/src/lib/                 theme.ts (all visual values), timing.ts (phrase -> time)
video/timings/<slug>.json      word timings (tracked)
video/public/audio/            cleaned voiceovers (git-ignored)
video/output/                  rendered reels (git-ignored)
legacy_manim/                  the retired Manim engine, kept for reference
```

## Troubleshooting

* `"<words>" not found in <slug>`: Whisper heard something different from the phrase passed to `startOf`. The error lists the words it heard next; use those, or fix the storyboard and re-transcribe.
* Whisper output is English instead of Hinglish: the storyboard was missing when transcribing. Create it, then re-run `transcribe.py`.
* A take sounds muffled: lower `DEEP_FILTER_ATTEN_LIM` in `video/.env` (e.g. 30–60) and re-run `transcribe.py`.
* Text renders in Times: the Inter font failed to load; check `video/public/fonts/InterVariable.woff2`.
* Preview shows `no src/scenes/.tsx`: start it with `VITE_SLUG=<slug>`.

More in `CLAUDE.md` → Known issues.
