from fractions import Fraction
from itertools import pairwise
from pathlib import Path

from pydantic import BaseModel

from . import media
from .captions import Caption
from .config import VideoSettings
from .sound import ScheduledSound
from .spec import Timeline, Transcript
from .voice import MIN_MATCH_RATIO

CLIPPING_DB = -0.1
SHORT_SCENE_SECONDS = 0.5
DURATION_TOLERANCE = 0.1


class Report(BaseModel):
    errors: list[str] = []
    warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors


def check_final(
    output: Path,
    mix: Path,
    timeline: Timeline,
    transcript: Transcript,
    captions: list[Caption],
    render_reports: dict[str, dict],
    sounds: list[ScheduledSound],
    video: VideoSettings,
) -> Report:
    report = Report(warnings=list(timeline.notes))
    for scene in timeline.scenes:
        if scene.duration < SHORT_SCENE_SECONDS:
            report.warnings.append(
                f"scene {scene.id} is only {scene.duration:.2f}s long in the recording"
            )
    for s in sounds:
        if abs(s.time - s.requested_time) > 1 / timeline.fps:
            report.warnings.append(
                f"scene {s.scene_id}: sound for {s.event!r} requested at "
                f"{s.requested_time:.2f}s was moved to {s.time:.2f}s to fit the video"
            )
    try:
        info = media.probe(output)
    except media.MediaError as e:
        report.errors.append(str(e))
        return report
    vstreams, astreams = media.streams(info, "video"), media.streams(info, "audio")
    if len(vstreams) != 1:
        report.errors.append(f"expected 1 video stream, found {len(vstreams)}")
    if len(astreams) != 1:
        report.errors.append(f"expected 1 audio stream, found {len(astreams)}")
    if vstreams:
        v = vstreams[0]
        if (v.get("width"), v.get("height")) != (video.width, video.height):
            report.errors.append(
                f"frame size {v.get('width')}x{v.get('height')} != {video.width}x{video.height}"
            )
        if Fraction(v.get("r_frame_rate", "0/1")) != timeline.fps:
            report.errors.append(f"frame rate {v.get('r_frame_rate')} != {timeline.fps}")
        frames = int(v.get("nb_frames") or 0)
        if frames != timeline.frames:
            report.errors.append(f"{frames} video frames, expected {timeline.frames}")
    actual = media.duration(info)
    if abs(actual - timeline.duration) > DURATION_TOLERANCE:
        report.errors.append(f"duration {actual:.3f}s != narration {timeline.duration:.3f}s")
    try:
        media.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", output, "-f", "null", "-"],
            "decoding final video",
        )
    except media.MediaError as e:
        report.errors.append(str(e))
    mean, peak = media.volume_stats(mix)
    if mean < -50:
        report.errors.append(f"mixed audio is silent (mean {mean} dB)")
    if peak >= CLIPPING_DB:
        report.warnings.append(f"mixed audio peaks at {peak} dB and may clip")
    if timeline.match_ratio < MIN_MATCH_RATIO:
        report.warnings.append(
            f"only {timeline.match_ratio:.0%} of the approved script matched the recording"
        )
    for scene_id, r in render_reports.items():
        overrun = r["rendered_seconds"] - r["planned_seconds"]
        if overrun > 1 / timeline.fps:
            report.warnings.append(
                f"scene {scene_id} animation runs {overrun:.2f}s past its narration and was cut"
            )
        for action in r.get("clamped_events", []):
            report.warnings.append(
                f"scene {scene_id}: event {action!r} falls outside the scene and was clamped"
            )
    for a, b in pairwise(captions):
        if b.start < a.end:
            report.errors.append(f"captions overlap at {b.start:.2f}s")
    if captions and captions[-1].end > timeline.duration + DURATION_TOLERANCE:
        report.errors.append("captions extend past the end of the video")
    caption_words = sum(len(c.text.split()) for c in captions)
    transcript_words = sum(len(w.text.split()) for w in transcript.words)
    if captions and caption_words != transcript_words:
        report.errors.append(f"captions have {caption_words} words, transcript {transcript_words}")
    return report
