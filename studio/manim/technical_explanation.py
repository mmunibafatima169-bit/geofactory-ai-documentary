"""Reusable data-driven Manim scene. Construction does not imply a render test.

After runtime repair, pass ScientificExplanationConfig JSON and invoke Manim only
with separate approval. No location-specific data or style is embedded here.
"""

from __future__ import annotations

import json
from pathlib import Path

from manim import BarChart, DOWN, Scene, Text, VGroup


class TechnicalExplanation(Scene):
    config_path: str | None = None

    def construct(self):
        if not self.config_path:
            raise ValueError("TechnicalExplanation.config_path is required")
        config = json.loads(Path(self.config_path).read_text(encoding="utf-8"))
        if config["explanation_kind"] != "bar_comparison":
            raise ValueError("This first reusable adapter supports bar_comparison only")
        if len(config["labels"]) != len(config["values"]) or not config["source_ids"]:
            raise ValueError("Aligned values and source ids are required")
        title = Text(config["title"], font_size=34)
        title.to_edge(DOWN, buff=0.4)
        chart = BarChart(
            values=config["values"],
            bar_names=config["labels"],
            y_length=4.5,
            x_length=10,
            y_axis_config={"font_size": 24},
            x_axis_config={"font_size": 24},
        )
        unit = Text(f"Unit: {config['unit']}", font_size=22)
        sources = Text("Sources: " + ", ".join(config["source_ids"]), font_size=18)
        note = Text(config["note"], font_size=20)
        text = VGroup(title, unit, note, sources).arrange(DOWN, aligned_edge=DOWN, buff=0.15)
        text.to_edge(DOWN)
        self.add(chart, text)
        # No animation/render call is made by the production configuration phase.
