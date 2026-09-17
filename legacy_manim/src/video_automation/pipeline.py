import json
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from . import animation, captions, compose, media, sound, spec, validate, voice
from .config import Settings
from .spec import SPEC_VERSION, Plan, Timeline, Transcript
from .workflow import (
    EpisodeDir,
    WorkflowError,
    atomic_write,
    load_json,
    require_approval,
    sha256_bytes,
    sha256_file,
    transition,
    write_model,
)

log = logging.getLogger(__name__)

STAGE_CODE = {
    "voice_wav": (voice,),
    "timeline": (voice, spec),
    "scene": (animation,),
    "sound_mix": (sound,),
    "captions": (captions,),
    "compose": (compose,),
}


class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self.entries: dict[str, str] = load_json(path)
        self.lock = threading.Lock()

    def run(
        self,
        episode_id: str,
        stage: str,
        inputs: object,
        outputs: list[Path],
        action: Callable[[], None],
    ) -> bool:
        modules = STAGE_CODE.get(stage.split(":")[0], ())
        engine = [sha256_file(Path(m.__file__)) for m in modules]
        payload = {"inputs": inputs, "engine": engine}
        fingerprint = sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode())
        if self.entries.get(stage) == fingerprint and all(p.exists() for p in outputs):
            log.info("episode=%s stage=%s reused", episode_id, stage)
            return False
        with self.lock:
            self.entries.pop(stage, None)
            self.save()
        started = time.monotonic()
        log.info("episode=%s stage=%s running", episode_id, stage)
        action()
        missing = [str(p) for p in outputs if not p.exists()]
        if missing:
            raise WorkflowError(f"stage {stage} did not produce {', '.join(missing)}")
        with self.lock:
            self.entries[stage] = fingerprint
            self.save()
        log.info("episode=%s stage=%s done in %.1fs", episode_id, stage, time.monotonic() - started)
        return True

    def save(self) -> None:
        atomic_write(self.path, json.dumps(self.entries, indent=2, sort_keys=True))


def script_prompt(plan: Plan) -> str:
    return " ".join(scene.narration for scene in plan.scenes)


def analyze(ep: EpisodeDir, settings: Settings, transcriber: voice.Transcriber) -> Timeline:
    require_approval(ep, "proposal")
    require_approval(ep, "plan")
    source = ep.voice_file()
    if source is None:
        raise WorkflowError("no narration provided; run `voice <episode> <file>` first")
    episode = transition(ep, "analyze_voice")
    plan: Plan = ep.load_document("plan")
    manifest = Manifest(ep.build / "manifest.json")
    wav = ep.build / "voice.wav"
    transcript_file = ep.build / "transcript.json"
    timeline_file = ep.build / "timeline.json"
    voice_sha = sha256_file(source)

    manifest.run(
        episode.id,
        "voice_wav",
        {"voice": voice_sha, "rate": settings.video.sample_rate},
        [wav],
        lambda: voice.to_wav(source, wav, settings.video.sample_rate),
    )
    prompt = script_prompt(plan) if settings.voice.use_script_as_prompt else None
    manifest.run(
        episode.id,
        "transcript",
        {"voice": voice_sha, "voice_settings": settings.voice.model_dump(), "prompt": prompt},
        [transcript_file],
        lambda: write_model(transcript_file, transcriber.transcribe(wav, prompt)),
    )
    transcript = Transcript.model_validate_json(transcript_file.read_text())
    manifest.run(
        episode.id,
        "timeline",
        {
            "transcript": sha256_file(transcript_file),
            "plan": sha256_file(ep.document_path("plan")),
            "fps": settings.video.fps,
        },
        [timeline_file],
        lambda: write_model(timeline_file, voice.align(plan, transcript, settings.video.fps)),
    )
    return Timeline.model_validate_json(timeline_file.read_text())


def generate(ep: EpisodeDir, settings: Settings, transcriber: voice.Transcriber) -> validate.Report:
    timeline = analyze(ep, settings, transcriber)
    episode = transition(ep, "generate")
    plan: Plan = ep.load_document("plan")
    manifest = Manifest(ep.build / "manifest.json")
    transcript_file = ep.build / "transcript.json"
    transcript = Transcript.model_validate_json(transcript_file.read_text())
    video = settings.video

    scene_videos = [ep.build / "scenes" / f"{s.id}.mp4" for s in plan.scenes]

    def render_scene(index: int) -> None:
        scene, timing, output = plan.scenes[index], timeline.scenes[index], scene_videos[index]
        job = {
            "scene_id": scene.id,
            "component": scene.visual.component,
            "search_path": str(ep.root),
            "params": scene.visual.params,
            "events": [e.model_dump() for e in scene.events],
            "cues": timing.cues,
            "words": [w.model_dump() for w in timing.words],
            "pauses": [p.model_dump() for p in timing.pauses],
            "frames": timing.frames,
            "fps": video.fps,
            "width": video.width,
            "height": video.height,
        }
        sources = {
            p.name: sha256_file(p)
            for p in animation.component_sources(scene.visual.component, ep.root)
        }
        manifest.run(
            episode.id,
            f"scene:{scene.id}",
            {
                "job": {**job, "search_path": None},
                "sources": sources,
            },
            [output, output.with_suffix(".json")],
            lambda: animation.render(
                job,
                ep.build / "jobs" / f"{scene.id}.json",
                output,
                ep.build / "logs" / f"{scene.id}.log",
            ),
        )

    with ThreadPoolExecutor(max_workers=settings.render.workers) as pool:
        list(pool.map(render_scene, range(len(plan.scenes))))
    render_reports = {
        s.id: json.loads(p.with_suffix(".json").read_text())
        for s, p in zip(plan.scenes, scene_videos, strict=True)
    }

    mix_file = ep.build / "mix.wav"
    scheduled = sound.schedule(plan, timeline, [ep.root / "sfx", *settings.sfx_dirs])
    manifest.run(
        episode.id,
        "sound_mix",
        {
            "voice": sha256_file(ep.build / "voice.wav"),
            "timeline": timeline.model_dump(),
            "sounds": [
                (s.event, sha256_file(s.path), s.time, s.volume, s.duration, s.fade_in, s.fade_out)
                for s in scheduled
            ],
            "rate": video.sample_rate,
        },
        [mix_file],
        lambda: sound.mix(
            ep.build / "voice.wav", scheduled, timeline.duration, video.sample_rate, mix_file
        ),
    )

    caption_list = (
        captions.segment(transcript, plan.captions.max_chars, plan.captions.max_gap_seconds)
        if plan.captions.enabled
        else []
    )
    caption_dir = ep.build / "captions"
    caption_images = [caption_dir / f"{i:04}.png" for i in range(len(caption_list))]
    srt_file = ep.output / "final.srt"
    manifest.run(
        episode.id,
        "captions",
        {
            "captions": [c.model_dump() for c in caption_list],
            "style": settings.captions.model_dump(),
            "size": [video.width, video.height],
        },
        [srt_file, *caption_images],
        lambda: (
            captions.render_images(
                caption_list, settings.captions, video.width, video.height, caption_dir
            ),
            atomic_write(srt_file, captions.to_srt(caption_list)),
        ),
    )

    final = ep.output / "final.mp4"
    manifest.run(
        episode.id,
        "compose",
        {
            "scenes": [sha256_file(p) for p in scene_videos],
            "timeline": timeline.model_dump(),
            "mix": sha256_file(mix_file),
            "captions": [sha256_file(p) for p in caption_images],
            "caption_times": [c.model_dump() for c in caption_list],
            "video": video.model_dump(),
            "style": settings.captions.model_dump(),
        },
        [final],
        lambda: compose.compose(
            scene_videos,
            timeline,
            mix_file,
            list(zip(caption_list, caption_images, strict=True)),
            video,
            settings.captions,
            final,
        ),
    )

    report = validate.check_final(
        final, mix_file, timeline, transcript, caption_list, render_reports, scheduled, video
    )
    metadata = {
        "episode_id": episode.id,
        "spec_version": SPEC_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "output": str(final.relative_to(ep.root)),
        "output_sha256": sha256_file(final),
        "duration": timeline.duration,
        "frames": timeline.frames,
        "approvals": ep.load().approvals,
        "voice_sha256": sha256_file(ep.voice_file()),
        "transcript": {
            "engine": transcript.engine,
            "model": transcript.model,
            "language": transcript.language,
        },
        "sound_events": [
            {"scene": s.scene_id, "event": s.event, "asset": s.path.name, "time": round(s.time, 3)}
            for s in scheduled
        ],
        "settings": json.loads(settings.model_dump_json()),
        "tool_versions": media.tool_versions(),
        "qc": report.model_dump(),
    }
    atomic_write(ep.output / "final.json", json.dumps(metadata, indent=2) + "\n")
    if report.ok:
        transition(ep, "preview")
    return report
