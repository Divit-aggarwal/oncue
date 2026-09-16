# Language and Localization

> Status: draft assembled from `CLAUDE.md` §7 and `05_VOICE_AND_TIMING.md`. Awaiting creator review.

## Principles

* Hinglish is a first-class content language.
* Preserve Hindi, English, Roman Hindi, technical English and Indian conversational phrasing.
* Never translate or "correct" natural Hinglish unless translation is explicitly requested.

## Implementation

* Transcription always uses Whisper's `transcribe` task, never `translate`.
* `voice.language` (default `en`) controls the script Whisper writes in.
* Measured on the creator's real Hinglish recording (`smoke` script, 12 s) with the `small` model:
  * `en` with the approved narration as prompt: verbatim Roman Hinglish, all 28 words matched.
  * `en` without a prompt: Whisper translates into English ("in RAG, the model is not being trained"). Do not set `use_script_as_prompt = false` with `en`.
  * `auto` and `hi`: Hindi detected, Devanagari output with misspellings. `large-v3-turbo` with `auto` is much closer but still Devanagari.
  * `en` with a deliberately wrong script as prompt still transcribed the spoken words ("notes", "relevant documents"), not the prompt's words. The prompt steers spelling and script, not content, so ad-libs still show up in captions.
* `use_script_as_prompt` (default `true`) is what keeps `en` output in Roman Hinglish rather than English.
* Low word probabilities (0.00 to 0.2) on Roman Hindi words are normal with the prompt and do not indicate misrecognition.
* Captions show the transcript words verbatim. `build/transcript.json` can be corrected by hand before `generate`.
* Tokenizing for alignment is script-agnostic: Devanagari, Latin, and `।` punctuation.
* Caption images are rendered with Pango, which shapes Devanagari correctly.

## Not Yet Implemented

* English-only or translated caption tracks
* Transliteration between Devanagari and Roman Hindi
