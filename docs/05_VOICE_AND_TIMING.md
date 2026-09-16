# Voice and Timing

## 1. Voice Source

The creator records the complete narration.

The recording should be treated as the authoritative performance.

## 2. Voice Processing

The system should extract:

* transcript
* timestamps
* sentence boundaries
* phrase boundaries
* pauses
* approximate emphasis points where detectable

Whisper is the initial speech-recognition system.

Whisper supports multilingual speech recognition and can run locally.

## 3. Hinglish

Hinglish is a supported first-class language mode.

The system should preserve:

* Hindi words
* English technical terminology
* Roman Hindi
* natural code-switching
* informal speech

Example:

> "Basically RAG mein model ko dobara train nahi kar rahe."

The system should not normalize this into:

> "Basically, in RAG, the model is not retrained."

unless translation is explicitly requested.

## 4. Timing

Voice timing should drive animation timing.

For example:

```text
0.00–1.20
Hook

1.20–3.40
Character enters

3.40–5.10
Dialogue

5.10–7.00
Reaction

7.00–10.00
Technical explanation
```

The system should derive these timings from the actual recording.

## 5. Pauses

Pauses should be preserved.

A pause may be intentionally used for:

* comedy
* anticipation
* reaction
* scene transition
* technical emphasis

## 6. Re-recording

The system should make re-recording cheap.

If the creator changes the narration:

* replace the voice file
* regenerate timing
* adjust animation timing
* avoid unnecessarily rebuilding unrelated assets

## 7. Audio Quality

The system should eventually support:

* silence trimming where explicitly requested
* loudness normalization
* noise reduction where appropriate
* voice/SFX balancing

The creator's natural voice should remain recognizable.

## 8. Voice as Timeline

The system should treat the narration as a timeline rather than merely an audio track.

Conceptually:

```text
VOICE
│
├── phrase
├── pause
├── phrase
├── emphasis
├── phrase
└── punchline
        ↓
ANIMATION TIMELINE
```

This is central to the system.
