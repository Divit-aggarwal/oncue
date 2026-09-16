# Language and Localization

> Status: draft assembled from `CLAUDE.md` §7 and `05_VOICE_AND_TIMING.md`. Awaiting creator review.

## Principles

* Hinglish is a first-class content language.
* Preserve Hindi, English, Roman Hindi, technical English and Indian conversational phrasing.
* Never translate or "correct" natural Hinglish unless translation is explicitly requested.

## Implementation

* Transcription always uses Whisper's `transcribe` task, never `translate`.
* `voice.language` (default `en`) controls the script Whisper writes in. Measured on a synthetic Hinglish recording:
  * `en` with the approved narration as prompt gave near-verbatim Roman Hinglish ("dobara train nahi kar rahe").
  * `auto` detected Hindi and produced unreliable mixed-script output.
  * `hi` gives Devanagari.
* `use_script_as_prompt` biases spelling toward the approved narration, so technical terms and Roman Hindi spellings match the script.
* Captions show the transcript words verbatim. `build/transcript.json` can be corrected by hand before `generate`.
* Tokenizing for alignment is script-agnostic: Devanagari, Latin, and `।` punctuation.
* Caption images are rendered with Pango, which shapes Devanagari correctly.

## Not Yet Implemented

* English-only or translated caption tracks
* Transliteration between Devanagari and Roman Hindi
