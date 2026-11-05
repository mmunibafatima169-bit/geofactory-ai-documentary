"""Animated subsidence timeline for Venice — Manim CE scene.

Draws an axes, then a relative-subsidence curve with era annotations
(industrial pumping acceleration, restriction slowdown, MOSE first raise).
Palette mirrors geofactory/studio/design_tokens.py.

    cd studio/manim && manim -qh subsidence_graph.py SubsidenceGraph
"""

from __future__ import annotations

import numpy as np
from manim import (
    Axes, Create, DecimalNumber, FadeIn, Line, Scene, Text, VGroup, Write, config,
    linear,
)

INK = "#0A1018"
TERRAIN = "#B89264"
ACCENT = "#F2C14E"
ALERT = "#E23A2E"
TEAL = "#598C7D"
TEXT_C = "#F5F1E8"
MUTED = "#8B94A3"

config.background_color = INK


def venue_curve(year: float) -> float:
    """Stylised cumulative relative subsidence/sea gap in cm (illustrative)."""
    base = -20 * np.tanh((year - 1900) / 130)          # natural settlement
    pump = -14 * max(0.0, min((year - 1950) / 25, 1.0))  # Marghera era
    lull = 6 * max(0.0, min((year - 1975) / 25, 1.0))    # recovery after ban
    rise = -0.35 * max(0.0, year - 1990)                # relative sea creep
    return float(base + pump + lull + rise)


class SubsidenceGraph(Scene):
    def construct(self) -> None:
        title = Text("A CENTURY OF SINKING", font="DejaVu Sans", weight="BOLD",
                     font_size=44, color=TEXT_C)
        subtitle = Text("Relative level between Venice and the lagoon",
                        font="DejaVu Sans", font_size=24, color=MUTED)
        title.to_edge([0, 1, 0], buff=0.6).shift(np.array([0, 0.9, 0]))
        subtitle.next_to(title, [0, -1, 0], buff=0.22)
        self.play(Write(title))
        self.play(FadeIn(subtitle, shift=np.array([0, -0.15, 0])))

        axes = Axes(
            x_range=[1900, 2025, 25], y_range=[-60, 10, 20],
            x_length=11.2, y_length=4.9,
            axis_config={"color": MUTED, "include_numbers": False},
            tips=False,
        ).shift(np.array([0, -0.7, 0]))
        self.play(Create(axes))

        for year in (1900, 1950, 2000, 2025):
            label = Text(str(year), font="DejaVu Sans", font_size=20, color=MUTED)
            label.next_to(axes.c2p(year, -60), [0, -1, 0], buff=0.14)
            self.add(label)
        unit = Text("relative cm", font="DejaVu Sans", font_size=20, color=MUTED)
        unit.next_to(axes.c2p(1900, 10), [-1, 1, 0])
        self.add(unit)

        years = np.linspace(1900, 2025, 250)
        points = [axes.c2p(y, venue_curve(y)) for y in years]
        curve = VGroup(*[
            Line(a, b, stroke_color=TERRAIN, stroke_width=6)
            for a, b in zip(points[:-1], points[1:])
        ])
        self.play(Create(curve), run_time=4, rate_func=linear)

        events = [
            (1966, "1966 record flood: 194 cm", ALERT),
            (1975, "pumping restricted", TEAL),
            (2020, "MOSE first raised", ACCENT),
        ]
        for year, text, color in events:
            dot_y = venue_curve(year)
            dot = Line(axes.c2p(year, dot_y), axes.c2p(year, dot_y),
                       stroke_color=color, stroke_width=14)
            label = Text(text, font="DejaVu Sans", font_size=22, color=color)
            label.next_to(axes.c2p(year, dot_y), [0, 1, 0], buff=0.24)
            self.play(Create(dot), FadeIn(label))

        number = DecimalNumber(0, num_decimal_places=0, color=TERRAIN,
                               font_size=60, include_sign=True)
        number.move_to(axes.c2p(1990, 8) + np.array([1.3, 0.2, 0]))
        caption = Text("cm lost since 1900", font="DejaVu Sans", font_size=22,
                       color=MUTED).next_to(number, [1, 0, 0])
        self.add(caption)
        self.play(FadeIn(number, scale=1.2))
        self.play(number.animate.set_value(round(abs(venue_curve(2025)))), run_time=2)
        self.wait(1.2)
