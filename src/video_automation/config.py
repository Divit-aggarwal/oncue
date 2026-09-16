import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VideoSettings(Section):
    width: int = Field(1080, gt=0, multiple_of=2)
    height: int = Field(1920, gt=0, multiple_of=2)
    fps: int = Field(30, gt=0, le=120)
    crf: int = Field(18, ge=0, le=51)
    audio_bitrate: str = "192k"
    sample_rate: int = 48000


class VoiceSettings(Section):
    model: str = "small"
    language: str = "en"
    device: str = "auto"
    compute_type: str = "default"
    use_script_as_prompt: bool = True
    silence_threshold_db: float = -50.0


class RenderSettings(Section):
    workers: int = Field(3, ge=1)


class CaptionStyle(Section):
    font_size: float = Field(40, gt=0)
    max_width_ratio: float = Field(0.9, gt=0, le=1)
    bottom_margin_ratio: float = Field(0.18, ge=0, lt=1)
    stroke_width: float = Field(8, ge=0)


class Settings(Section):
    episodes_dir: Path = Path("episodes")
    sfx_dirs: list[Path] = [Path("assets/sfx")]
    video: VideoSettings = VideoSettings()
    voice: VoiceSettings = VoiceSettings()
    render: RenderSettings = RenderSettings()
    captions: CaptionStyle = CaptionStyle()


def load_settings(project_root: Path) -> Settings:
    path = project_root / "engine.toml"
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    settings = Settings.model_validate(data)
    settings.episodes_dir = project_root / settings.episodes_dir
    settings.sfx_dirs = [project_root / d for d in settings.sfx_dirs]
    return settings
