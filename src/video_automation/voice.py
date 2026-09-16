import logging
import shutil
from difflib import SequenceMatcher
from itertools import pairwise
from pathlib import Path
from typing import Protocol

from . import media
from .config import VoiceSettings
from .spec import (
    EngineError,
    Pause,
    Plan,
    SceneTiming,
    Timeline,
    Transcript,
    Word,
    find_phrase,
    tokens,
)

log = logging.getLogger(__name__)

MIN_VOICE_SECONDS = 0.5
SCENE_LEAD_SECONDS = 0.2
PAUSE_SECONDS = 0.3
MIN_MATCH_RATIO = 0.5


class VoiceError(EngineError):
    pass


class Transcriber(Protocol):
    def transcribe(self, audio: Path, prompt: str | None) -> Transcript: ...


class FasterWhisperTranscriber:
    def __init__(self, settings: VoiceSettings):
        self.settings = settings

    def transcribe(self, audio: Path, prompt: str | None) -> Transcript:
        from faster_whisper import WhisperModel

        s = self.settings
        model = WhisperModel(s.model, device=s.device, compute_type=s.compute_type)
        segments, info = model.transcribe(
            str(audio),
            language=None if s.language == "auto" else s.language,
            task="transcribe",
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt=prompt,
        )
        words = [
            Word(text=w.word.strip(), start=w.start, end=w.end, probability=w.probability)
            for segment in segments
            for w in segment.words or []
            if w.word.strip()
        ]
        return Transcript(
            engine="faster-whisper",
            model=s.model,
            language=info.language,
            duration=info.duration,
            words=words,
        )


def validate_voice(path: Path, silence_threshold_db: float) -> float:
    info = media.probe(path)
    if not media.streams(info, "audio"):
        raise VoiceError(f"{path.name} has no audio stream")
    seconds = media.duration(info)
    if seconds < MIN_VOICE_SECONDS:
        raise VoiceError(f"{path.name} is too short ({seconds:.2f}s)")
    mean, _ = media.volume_stats(path)
    if mean < silence_threshold_db:
        raise VoiceError(f"{path.name} is silent (mean volume {mean} dB)")
    return seconds


def ingest(source: Path, voice_dir: Path, silence_threshold_db: float) -> Path:
    if not source.is_file():
        raise VoiceError(f"voice file not found: {source}")
    validate_voice(source, silence_threshold_db)
    voice_dir.mkdir(parents=True, exist_ok=True)
    target = voice_dir / f"narration{source.suffix.lower()}"
    tmp = voice_dir / f".incoming{source.suffix.lower()}"
    shutil.copyfile(source, tmp)
    for old in voice_dir.glob("narration.*"):
        old.unlink()
    tmp.replace(target)
    return target


def to_wav(source: Path, target: Path, sample_rate: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}")
    media.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            source,
            "-vn",
            "-ac",
            "2",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            tmp,
        ],
        "converting narration to wav",
    )
    tmp.replace(target)


def align(plan: Plan, transcript: Transcript, fps: int) -> Timeline:
    words = transcript.words
    if not words:
        raise VoiceError("transcript contains no words; check the recording")
    spoken: list[tuple[str, int]] = [(t, i) for i, w in enumerate(words) for t in tokens(w.text)]
    scripted: list[tuple[str, int, int]] = [
        (t, si, ti)
        for si, scene in enumerate(plan.scenes)
        for ti, t in enumerate(tokens(scene.narration))
    ]
    matcher = SequenceMatcher(
        None, [t for t, _, _ in scripted], [t for t, _ in spoken], autojunk=False
    )
    word_for: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            word_for[block.a + k] = spoken[block.b + k][1]
    match_ratio = len(word_for) / len(scripted)
    if match_ratio < MIN_MATCH_RATIO:
        log.warning("only %.0f%% of the script matched the recording", match_ratio * 100)

    first_word: list[int] = []
    last_matched = -1
    offset = 0
    for scene in plan.scenes:
        count = len(tokens(scene.narration))
        matched = [(k, word_for[offset + k]) for k in range(count) if offset + k in word_for]
        if not matched:
            raise VoiceError(
                f"scene {scene.id}: none of its narration was found in the recording; "
                "check the recording or edit build/transcript.json"
            )
        k, word = matched[0]
        floor = max(first_word[-1] + 1, last_matched + 1) if first_word else 0
        first_word.append(max(floor, word - k))
        last_matched = matched[-1][1]
        offset += count

    total_frames = round(transcript.duration * fps)
    boundaries = [0]
    for idx in first_word[1:]:
        lead_start = max(words[idx - 1].end, words[idx].start - SCENE_LEAD_SECONDS)
        boundaries.append(round(lead_start * fps))
    boundaries.append(total_frames)

    scenes = []
    offset = 0
    for i, scene in enumerate(plan.scenes):
        start_frame, end_frame = boundaries[i], boundaries[i + 1]
        if end_frame <= start_frame:
            raise VoiceError(f"scene {scene.id} has no duration in the recording")
        start, end = start_frame / fps, end_frame / fps
        scene_tokens = tokens(scene.narration)
        cues = {}
        for name, phrase in scene.cues.items():
            index = find_phrase(scene_tokens, tokens(phrase))
            candidates = [
                offset + k for k in range(index, len(scene_tokens)) if offset + k in word_for
            ]
            if not candidates:
                raise VoiceError(f"scene {scene.id}: cue {name!r} not found in the recording")
            cues[name] = max(0.0, min(words[word_for[candidates[0]]].start, end) - start)
        offset += len(scene_tokens)
        local = [
            Word(text=w.text, start=w.start - start, end=w.end - start, probability=w.probability)
            for w in words
            if start <= w.start < end
        ]
        pauses = [
            Pause(start=a.end, end=b.start)
            for a, b in pairwise(local)
            if b.start - a.end >= PAUSE_SECONDS
        ]
        scenes.append(
            SceneTiming(
                id=scene.id,
                start=start,
                start_frame=start_frame,
                frames=end_frame - start_frame,
                duration=end - start,
                cues=cues,
                words=local,
                pauses=pauses,
            )
        )
    return Timeline(
        fps=fps,
        duration=total_frames / fps,
        frames=total_frames,
        match_ratio=round(match_ratio, 4),
        scenes=scenes,
    )
