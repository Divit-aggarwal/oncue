from manim import DOWN, FadeIn, FadeOut, Text, VGroup

from .animation import RenderError, TimedScene

TRANSITION_SECONDS = 0.3


def fitted_text(text: str, frame_width: float) -> Text:
    mobject = Text(text, font_size=48)
    if mobject.width > frame_width * 0.85:
        mobject.scale_to_fit_width(frame_width * 0.85)
    return mobject


class TextCard(TimedScene):
    def transition_time(self) -> float:
        return max(1 / self.fps, min(TRANSITION_SECONDS, self.time_until("end")))

    def construct(self) -> None:
        shown = VGroup()
        for line in self.params.get("lines", []):
            shown.add(fitted_text(line, self.camera.frame_width))
        if shown:
            shown.arrange(DOWN, buff=0.4)
            self.play(FadeIn(shown), run_time=self.transition_time())
        for event in self.events():
            self.hold_until(event["time"])
            if event["action"] == "show":
                self.remove(*shown)
                shown = VGroup(fitted_text(event["params"]["text"], self.camera.frame_width))
                self.play(FadeIn(shown), run_time=self.transition_time())
            elif event["action"] == "clear" and shown:
                self.play(FadeOut(shown), run_time=self.transition_time())
                shown = VGroup()
            elif event["action"] != "clear":
                raise RenderError(f"TextCard does not support action {event['action']!r}")
