import importlib
import importlib.util
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from manim import Scene

from .spec import EngineError

log = logging.getLogger(__name__)

FRAME_HEIGHT = 8.0


class RenderError(EngineError):
    pass


class TimedScene(Scene):
    job: dict[str, Any] = {}

    @property
    def fps(self) -> int:
        return self.job["fps"]

    @property
    def scene_duration(self) -> float:
        return self.job["frames"] / self.fps

    @property
    def params(self) -> dict[str, Any]:
        return self.job["params"]

    @property
    def words(self) -> list[dict[str, Any]]:
        return self.job["words"]

    @property
    def pauses(self) -> list[dict[str, float]]:
        return self.job["pauses"]

    def cue(self, name: str) -> float:
        if name == "start":
            return 0.0
        if name == "end":
            return self.scene_duration
        if name not in self.job["cues"]:
            raise RenderError(f"scene {self.job['scene_id']}: unknown cue {name!r}")
        return self.job["cues"][name]

    def events(self) -> list[dict[str, Any]]:
        resolved = [
            {**e, "time": min(max(self.cue(e["at"]) + e["offset"], 0.0), self.scene_duration)}
            for e in self.job["events"]
        ]
        return sorted(resolved, key=lambda e: e["time"])

    def time_until(self, moment: float | str) -> float:
        target = self.cue(moment) if isinstance(moment, str) else moment
        return max(0.0, target - self.time)

    def hold_until(self, moment: float | str) -> None:
        remaining = self.time_until(moment)
        if remaining >= 1 / self.fps:
            self.wait(remaining)

    def tear_down(self) -> None:
        self.hold_until("end")
        overrun = self.time - self.scene_duration
        if overrun > 1 / self.fps:
            log.warning("scene %s runs %.2fs past its narration", self.job["scene_id"], overrun)


def component_sources(component: str, search_path: Path) -> list[Path]:
    module = component.split(":")[0]
    sys.path.insert(0, str(search_path))
    try:
        spec = importlib.util.find_spec(module)
    except ModuleNotFoundError:
        spec = None
    finally:
        sys.path.remove(str(search_path))
    if spec is None or spec.origin is None:
        raise RenderError(f"component module {module!r} not found")
    origin = Path(spec.origin)
    return sorted(origin.parent.glob("*.py"))


def render(job: dict[str, Any], job_file: Path, output: Path, log_file: Path) -> dict[str, Any]:
    job_file.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    output.with_suffix(".json").unlink(missing_ok=True)
    job_file.write_text(json.dumps({**job, "output": str(output)}, indent=2))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w") as log_stream:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"from video_automation.animation import run_job; run_job({str(job_file)!r})",
            ],
            stdout=log_stream,
            stderr=subprocess.STDOUT,
        )
    if result.returncode != 0:
        tail = "\n".join(log_file.read_text().strip().splitlines()[-20:])
        raise RenderError(f"scene {job['scene_id']} failed to render (log: {log_file}):\n{tail}")
    if not output.exists():
        raise RenderError(f"scene {job['scene_id']} produced no video")
    return json.loads(output.with_suffix(".json").read_text())


def run_job(job_path: str) -> None:
    from manim import tempconfig

    job_file = Path(job_path)
    job = json.loads(job_file.read_text())
    sys.path.insert(0, job["search_path"])
    module_name, class_name = job["component"].split(":")
    component = getattr(importlib.import_module(module_name), class_name, None)
    if not (isinstance(component, type) and issubclass(component, TimedScene)):
        raise RenderError(f"{job['component']} is not a TimedScene subclass")
    output = Path(job["output"])
    work = output.parent / "manim" / job["scene_id"]
    with tempconfig(
        {
            "pixel_width": job["width"],
            "pixel_height": job["height"],
            "frame_rate": job["fps"],
            "frame_height": FRAME_HEIGHT,
            "frame_width": FRAME_HEIGHT * job["width"] / job["height"],
            "media_dir": str(work),
            "video_dir": str(work),
            "output_file": job["scene_id"],
            "disable_caching": True,
            "progress_bar": "none",
            "verbosity": "WARNING",
        }
    ):
        scene = type(class_name, (component,), {"job": job})()
        scene.render()
        movie = Path(scene.renderer.file_writer.movie_file_path)
        report = {"rendered_seconds": scene.time, "planned_seconds": scene.scene_duration}
    output.with_suffix(".json").write_text(json.dumps(report))
    movie.replace(output)
