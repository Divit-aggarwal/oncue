from dataclasses import dataclass
from pathlib import Path

from . import media
from .spec import EngineError, Plan, Timeline

AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aiff", ".flac", ".ogg")


class SoundError(EngineError):
    pass


@dataclass(frozen=True)
class ScheduledSound:
    scene_id: str
    event: str
    path: Path
    time: float
    requested_time: float
    volume: float
    duration: float
    fade_in: float
    fade_out: float


def resolve_asset(name: str, search_dirs: list[Path]) -> Path:
    for directory in search_dirs:
        for candidate in [directory / name, *(directory / f"{name}{e}" for e in AUDIO_EXTENSIONS)]:
            if candidate.is_file():
                return candidate
    raise SoundError(f"sound asset {name!r} not found in {', '.join(map(str, search_dirs))}")


def schedule(plan: Plan, timeline: Timeline, search_dirs: list[Path]) -> list[ScheduledSound]:
    scheduled = []
    for scene, timing in zip(plan.scenes, timeline.scenes, strict=True):
        anchors = {"start": 0.0, "end": timing.duration, **timing.cues}
        for sound in scene.sounds:
            path = resolve_asset(sound.asset, search_dirs)
            info = media.probe(path)
            if not media.streams(info, "audio"):
                raise SoundError(f"sound asset {path} has no audio stream")
            requested = timing.start + anchors[sound.at] + sound.offset
            length = min(sound.duration or media.duration(info), timeline.duration)
            time = min(max(requested, 0.0), timeline.duration - length)
            scheduled.append(
                ScheduledSound(
                    scene_id=scene.id,
                    event=sound.event,
                    path=path,
                    time=time,
                    requested_time=requested,
                    volume=sound.volume,
                    duration=length,
                    fade_in=min(sound.fade_in, length),
                    fade_out=min(sound.fade_out, length),
                )
            )
    return scheduled


def mix(
    voice_wav: Path, sounds: list[ScheduledSound], duration: float, sample_rate: int, output: Path
) -> None:
    inputs: list[str | Path] = ["-i", voice_wav]
    voice_fmt = media.stereo_filter(voice_wav, sample_rate)
    filters = [f"[0:a]{voice_fmt},apad,atrim=0:{duration:.6f}[voice]"]
    labels = ["[voice]"]
    for i, s in enumerate(sounds, start=1):
        inputs += ["-i", s.path]
        chain = [
            media.stereo_filter(s.path, sample_rate),
            f"atrim=0:{s.duration:.6f}",
            "asetpts=PTS-STARTPTS",
        ]
        if s.fade_in:
            chain.append(f"afade=t=in:st=0:d={s.fade_in:.6f}")
        if s.fade_out:
            chain.append(f"afade=t=out:st={s.duration - s.fade_out:.6f}:d={s.fade_out:.6f}")
        chain += [f"volume={s.volume}", f"adelay={round(s.time * 1000)}:all=1"]
        filters.append(f"[{i}:a]{','.join(chain)}[s{i}]")
        labels.append(f"[s{i}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0[mix]")
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(f".{output.name}")
    media.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[mix]",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            tmp,
        ],
        "mixing narration and sound effects",
    )
    tmp.replace(output)
