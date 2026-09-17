from manim import *


class RAG(Scene):
    def construct(self):
        # ------------------------------------------------------------
        # GLOBAL SETUP
        # ------------------------------------------------------------
        self.camera.background_color = "#111111"

        # ------------------------------------------------------------
        # HELPERS
        # ------------------------------------------------------------
        def character(color=BLUE):
            """Simple faceless person."""
            head = Circle(radius=0.28, color=color, stroke_width=4)
            body = Line(UP * 0.0, DOWN * 0.65, color=color, stroke_width=5)
            left_arm = Line(DOWN * 0.15, LEFT * 0.42 + DOWN * 0.42,
                            color=color, stroke_width=5)
            right_arm = Line(DOWN * 0.15, RIGHT * 0.42 + DOWN * 0.42,
                             color=color, stroke_width=5)
            left_leg = Line(DOWN * 0.65, LEFT * 0.25 + DOWN * 1.05,
                            color=color, stroke_width=5)
            right_leg = Line(DOWN * 0.65, RIGHT * 0.25 + DOWN * 1.05,
                             color=color, stroke_width=5)

            return VGroup(
                head,
                body,
                left_arm,
                right_arm,
                left_leg,
                right_leg,
            )

        def speech_bubble(text, width=4.8):
            bubble = RoundedRectangle(
                corner_radius=0.15,
                width=width,
                height=1.25,
                color=WHITE,
                stroke_width=3,
            )
            label = Text(
                text,
                font_size=25,
                color=WHITE,
                line_spacing=0.9,
            )
            label.move_to(bubble.get_center())
            return VGroup(bubble, label)

        def document(title):
            page = RoundedRectangle(
                corner_radius=0.08,
                width=2.5,
                height=1.15,
                color=WHITE,
                stroke_width=3,
            )

            heading = Text(
                title,
                font_size=23,
                color=WHITE,
            )

            lines = VGroup(
                Line(LEFT * 0.75, RIGHT * 0.75, stroke_width=2),
                Line(LEFT * 0.75, RIGHT * 0.55, stroke_width=2),
                Line(LEFT * 0.75, RIGHT * 0.7, stroke_width=2),
            ).arrange(DOWN, buff=0.14)

            heading.move_to(page.get_center() + UP * 0.28)
            lines.move_to(page.get_center() + DOWN * 0.22)

            return VGroup(page, heading, lines)

        def box(label, width=2.7, height=1.2):
            rectangle = RoundedRectangle(
                corner_radius=0.15,
                width=width,
                height=height,
                color=WHITE,
                stroke_width=3,
            )
            text = Text(label, font_size=25)
            text.move_to(rectangle.get_center())
            return VGroup(rectangle, text)

        # ============================================================
        # SCENE 1 — HOOK
        # ============================================================

        title = Text(
            "YOU'RE IN AN AI INTERVIEW",
            font_size=36,
            weight=BOLD,
        )

        interviewer = character(RED).scale(0.9)
        candidate = character(BLUE).scale(0.9)

        interviewer.to_edge(LEFT, buff=0.8)
        candidate.to_edge(RIGHT, buff=0.8)

        question = speech_bubble(
            "What is our\nrefund policy?",
            width=4.2,
        )

        question.next_to(interviewer, DOWN, buff=0.35)

        self.play(
            Write(title),
            FadeIn(interviewer),
            FadeIn(candidate),
        )

        self.play(
            FadeIn(question, shift=DOWN * 0.2),
        )

        self.wait(1)

        # Candidate panic
        panic = Text(
            "uhhhhh...",
            font_size=32,
        )

        panic.next_to(candidate, UP, buff=0.4)

        self.play(
            Write(panic),
            candidate.animate.shift(LEFT * 0.15),
        )

        self.wait(1)

        # ============================================================
        # SCENE 2 — "I HAVE NO IDEA"
        # ============================================================

        self.play(
            FadeOut(title),
            FadeOut(interviewer),
            FadeOut(question),
            FadeOut(panic),
        )

        big_no = Text(
            "I HAVE NO IDEA.",
            font_size=48,
            weight=BOLD,
        )

        self.play(
            Write(big_no),
        )

        self.wait(1)

        tiny = Text(
            "But what if I could LOOK IT UP?",
            font_size=27,
        )

        tiny.next_to(big_no, DOWN, buff=0.45)

        self.play(
            FadeIn(tiny),
        )

        self.wait(1)

        # ============================================================
        # SCENE 3 — THE CHEATING ANALOGY
        # ============================================================

        self.play(
            FadeOut(big_no),
            FadeOut(tiny),
            FadeOut(candidate),
        )

        analogy_title = Text(
            "Imagine the LLM is this guy.",
            font_size=34,
        )

        student = character(BLUE).scale(1.15)
        student.move_to(DOWN * 0.5)

        self.play(
            Write(analogy_title),
            FadeIn(student),
        )

        self.wait(1)

        notes = VGroup(
            document("Company Docs"),
            document("FAQs"),
            document("Policies"),
        ).arrange(
            DOWN,
            buff=0.25,
        ).scale(0.75)

        notes.to_edge(RIGHT, buff=0.4)

        self.play(
            LaggedStart(
                *[FadeIn(doc, shift=LEFT * 0.3) for doc in notes],
                lag_ratio=0.2,
            )
        )

        self.wait(1)

        cheat = Text(
            "bro brought NOTES",
            font_size=30,
            weight=BOLD,
        )

        cheat.next_to(student, UP, buff=0.35)

        self.play(
            Write(cheat),
        )

        self.wait(1)

        # ============================================================
        # SCENE 4 — INTRODUCE RAG
        # ============================================================

        self.play(
            FadeOut(analogy_title),
            FadeOut(student),
            FadeOut(notes),
            FadeOut(cheat),
        )

        rag_title = Text(
            "That's basically RAG.",
            font_size=44,
            weight=BOLD,
        )

        self.play(
            Write(rag_title),
        )

        self.wait(1)

        self.play(
            rag_title.animate.to_edge(UP, buff=0.5),
        )

        # ============================================================
        # SCENE 5 — THE RAG PIPELINE
        # ============================================================

        query = box(
            "YOUR\nQUESTION",
            width=2.7,
            height=1.35,
        )

        search = box(
            "RETRIEVER",
            width=2.7,
            height=1.35,
        )

        database = box(
            "YOUR DOCS",
            width=2.7,
            height=1.35,
        )

        llm = box(
            "LLM",
            width=2.7,
            height=1.35,
        )

        answer = box(
            "ANSWER",
            width=2.7,
            height=1.35,
        )

        # Arrange vertically for phone screen
        pipeline = VGroup(
            query,
            search,
            database,
            llm,
            answer,
        ).arrange(
            DOWN,
            buff=0.42,
        )

        pipeline.scale(0.8)
        pipeline.shift(DOWN * 0.35)

        # We don't want the boxes to be too low
        pipeline.shift(UP * 0.15)

        self.play(
            FadeIn(query),
        )

        self.play(
            GrowArrow(
                Arrow(
                    query.get_bottom(),
                    search.get_top(),
                    buff=0.12,
                    stroke_width=4,
                )
            ),
            FadeIn(search),
        )

        self.play(
            GrowArrow(
                Arrow(
                    search.get_bottom(),
                    database.get_top(),
                    buff=0.12,
                    stroke_width=4,
                )
            ),
            FadeIn(database),
        )

        self.wait(0.7)

        # Highlight retrieved information
        retrieved = Text(
            "find relevant information",
            font_size=23,
        )

        retrieved.next_to(database, RIGHT, buff=0.25)

        self.play(
            Write(retrieved),
        )

        self.wait(0.7)

        self.play(
            FadeOut(retrieved),
        )

        self.play(
            GrowArrow(
                Arrow(
                    database.get_bottom(),
                    llm.get_top(),
                    buff=0.12,
                    stroke_width=4,
                )
            ),
            FadeIn(llm),
        )

        context = Text(
            "+ relevant context",
            font_size=23,
        )

        context.next_to(llm, RIGHT, buff=0.25)

        self.play(
            Write(context),
        )

        self.wait(0.7)

        self.play(
            FadeOut(context),
        )

        self.play(
            GrowArrow(
                Arrow(
                    llm.get_bottom(),
                    answer.get_top(),
                    buff=0.12,
                    stroke_width=4,
                )
            ),
            FadeIn(answer),
        )

        self.wait(1)

        # ============================================================
        # SCENE 6 — THE PAYOFF
        # ============================================================

        self.play(
            FadeOut(rag_title),
            FadeOut(pipeline),
        )

        punchline = Text(
            "THE MODEL DIDN'T\nSUDDENLY GET SMARTER.",
            font_size=39,
            weight=BOLD,
            line_spacing=0.9,
        )

        self.play(
            Write(punchline),
        )

        self.wait(1)

        self.play(
            punchline.animate.scale(0.85).shift(UP * 0.8),
        )

        second = Text(
            "We just gave it the NOTES.",
            font_size=36,
            weight=BOLD,
        )

        second.next_to(punchline, DOWN, buff=0.7)

        self.play(
            Write(second),
        )

        self.wait(1)

        # Final tiny tag
        final = Text(
            "RAG = Retrieve → Augment → Generate",
            font_size=24,
        )

        final.to_edge(DOWN, buff=0.45)

        self.play(
            FadeIn(final),
        )

        self.wait(2)
