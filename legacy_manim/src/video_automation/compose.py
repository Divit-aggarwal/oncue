from pathlib import Path

from . import media
from .captions import Caption
from .config import CaptionStyle, VideoSettings
from .spec import Timeline


def compose(
    scene_videos: list[Path],
    timeline: Timeline,
    audio: Path,
    captions: list[tuple[Caption, Path]],
    video: VideoSettings,
    style: CaptionStyle,
    output: Path,
) -> None:
    fps = timeline.fps
    inputs: list[str | Path] = []
    filters = []
    for i, (path, timing) in enumerate(zip(scene_videos, timeline.scenes, strict=True)):
        inputs += ["-i", path]
        filters.append(
            f"[{i}:v]fps={fps},scale={video.width}:{video.height},setsar=1,"
            f"tpad=stop_mode=clone:stop={timing.frames},trim=end_frame={timing.frames},"
            f"setpts=N/FRAME_RATE/TB[v{i}]"
        )
    labels = "".join(f"[v{i}]" for i in range(len(scene_videos)))
    filters.append(f"{labels}concat=n={len(scene_videos)}:v=1:a=0,format=yuv420p[base]")
    audio_index = len(scene_videos)
    inputs += ["-i", audio]
    current = "base"
    margin = round(video.height * style.bottom_margin_ratio)
    for k, (caption, image) in enumerate(captions):
        index = audio_index + 1 + k
        inputs += ["-i", image]
        filters.append(
            f"[{current}][{index}:v]overlay=x=(W-w)/2:y=H-h-{margin}:"
            f"enable='gte(t,{caption.start:.3f})*lt(t,{caption.end:.3f})'[c{k}]"
        )
        current = f"c{k}"
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
            f"[{current}]",
            "-map",
            f"{audio_index}:a",
            "-frames:v",
            str(timeline.frames),
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-crf",
            str(video.crf),
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            video.audio_bitrate,
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            tmp,
        ],
        "composing final video",
    )
    tmp.replace(output)
