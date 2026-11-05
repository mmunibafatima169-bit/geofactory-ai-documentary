"""Reusable documentary design system: palette, typography, motion presets.

Shared by the Remotion templates, Blender scenes, Manim scenes and the
editorial QA heuristics so that every engine renders the same visual identity.
"""

from __future__ import annotations

PALETTE = {
    "ink": "#0A1018",          # cinematic near-black background
    "panel": "#121C28",        # card / lower-third panel
    "ocean": "#163E5A",        # deep sea blue (reference palette)
    "terrain": "#B89264",      # earth tan (reference palette)
    "accent": "#F2C14E",       # headline keyword amber
    "alert": "#E23A2E",        # X-marks / danger / highlight red
    "growth": "#598C7D",       # positive teal-green
    "text": "#F5F1E8",         # warm white
    "muted": "#8B94A3",        # secondary text
    "hairline": "#2E3E54",     # borders and rules
}

TYPOGRAPHY = {
    "family": "DejaVu Sans",
    "title_weight": 800,
    "lower_third_weight": 600,
    "min_mobile_read_px": 58,   # headline px on a 1080p canvas for 160px-mobile check
    "headline_max_words": 5,
    "tracking_upper_em": 0.08,
}

# Camera movement presets consumed by Remotion (springs), Blender (keyframes)
# and the FFmpeg Ken Burns layer — one vocabulary across engines.
CAMERA_PRESETS = {
    "push_in":    {"kind": "zoom", "direction": "in",    "easing": "smooth", "from": 1.00, "to": 1.10},
    "pull_back":  {"kind": "zoom", "direction": "out",   "easing": "smooth", "from": 1.10, "to": 1.00},
    "pan_right":  {"kind": "pan",  "axis": "x", "from": -1.0, "to": 1.0},
    "pan_down":   {"kind": "pan",  "axis": "y", "from": -1.0, "to": 1.0},
    "dolly_orbit": {"kind": "orbit", "degrees": 18},       # Blender 3D dolly
    "crane_rise": {"kind": "crane", "metres": 6},          # Blender 3D crane
}

TRANSITION_PRESETS = {
    "cut":          {"seconds": 0.0},
    "dip_to_black": {"seconds": 0.4},
    "zoom_punch":   {"seconds": 0.35, "scale": 1.06},
    "wipe_map":     {"seconds": 0.5, "axis": "x"},
}

SOUND_PRESETS = {
    "narration_bed":  {"music_level_db": -20, "limiter": 0.95},
    "scene_whoosh":   {"gain_db": -14},
    "sting_title":    {"gain_db": -10},
}

# Per-engine scene style registry — visual identity per render engine so the
# Visual Director can reason about coherent style, not just tool availability.
ENGINE_STYLES = {
    "remotion": {"use": "motion graphics, kinetic type, animated maps, lower thirds"},
    "blender":  {"use": "3D terrain, engineering demonstrations, exploded views"},
    "manim":    {"use": "graphs, statistics, technical timelines, formula visuals"},
    "ffmpeg":   {"use": "licensed stills with Ken Burns, final assembly, loudness"},
}
