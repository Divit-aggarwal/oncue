import json
import re
import shutil
import subprocess
from pathlib import Path

from .spec import EngineError


class MediaError(EngineError):
    pass


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise MediaError(f"{name} not found on PATH; install it (macOS: brew install ffmpeg)")
    return path


def run(cmd: list[str | Path], what: str) -> subprocess.CompletedProcess:
    args = [str(c) for c in cmd]
    require_tool(args[0])
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-15:])
        raise MediaError(f"{what} failed (exit {result.returncode}):\n{tail}")
    return result


def probe(path: Path) -> dict:
    if not path.exists():
        raise MediaError(f"missing media file {path}")
    try:
        out = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            f"probing {path.name}",
        )
    except MediaError as e:
        raise MediaError(f"{path.name} is not readable media: {e}") from e
    return json.loads(out.stdout)


def streams(info: dict, kind: str) -> list[dict]:
    return [s for s in info.get("streams", []) if s.get("codec_type") == kind]


def stereo_filter(path: Path, sample_rate: int) -> str:
    audio = streams(probe(path), "audio")
    layout = "pan=stereo|c0=c0|c1=c0," if audio and audio[0].get("channels") == 1 else ""
    return f"aresample={sample_rate},{layout}aformat=sample_fmts=fltp:channel_layouts=stereo"


def duration(info: dict) -> float:
    return float(info.get("format", {}).get("duration") or 0.0)


def volume_stats(path: Path) -> tuple[float, float]:
    out = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            path,
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        f"measuring volume of {path.name}",
    ).stderr
    mean = re.search(r"mean_volume: (-?[\d.]+|-inf) dB", out)
    peak = re.search(r"max_volume: (-?[\d.]+|-inf) dB", out)
    if not mean or not peak:
        raise MediaError(f"{path.name} has no measurable audio")
    return float(mean.group(1)), float(peak.group(1))


def tool_versions() -> dict[str, str]:
    from importlib.metadata import version

    versions = {pkg: version(pkg) for pkg in ("manim", "faster-whisper", "pydantic")}
    versions["ffmpeg"] = run(["ffmpeg", "-version"], "ffmpeg -version").stdout.splitlines()[0]
    return versions
