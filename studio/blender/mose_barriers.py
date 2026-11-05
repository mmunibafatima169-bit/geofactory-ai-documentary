"""MOSE barrier engineering demonstration — Blender headless scene.

Builds a stylised diagonal cut of a lagoon inlet: seabed, water, and one
hollow steel gate that swings up to block the tide, with a slow dolly orbit.
Mirrors design_tokens palette. Run:

    blender -b -noaudio -P studio/blender/mose_barriers.py -- \
        --frames 240 --width 1920 --height 1080 --out /tmp/mose.frames
"""

from __future__ import annotations

import argparse
import math
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--frames", type=int, default=240)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--out", required=True)
    return p.parse_args(argv)


def material(name: str, rgba: tuple[float, float, float, float], metallic: float = 0.0,
             roughness: float = 0.55) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def box(name: str, loc: tuple[float, float, float], scale: tuple[float, float, float],
        mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)
    return obj


def main() -> None:
    args = parse_args()
    from pathlib import Path
    Path(args.out).mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.fps = 30
    scene.render.image_settings.file_format = "PNG"
    scene.frame_start = 1
    scene.frame_end = args.frames
    scene.render.filepath = str(Path(args.out) / "frame_")

    seabed_mat = material("seabed", (0.36, 0.26, 0.15, 1), roughness=0.9)
    water_mat = material("water", (0.09, 0.24, 0.35, 0.85), roughness=0.15)
    water_mat.surface_render_method = "DITHERED"
    steel_mat = material("gate_steel", (0.55, 0.58, 0.62, 1), metallic=0.85, roughness=0.3)
    accent_mat = material("accent_paint", (0.95, 0.76, 0.31, 1), metallic=0.3, roughness=0.45)

    box("seabed", (0, 0, -2.2), (22, 12, 1.6), seabed_mat)
    box("water", (0, 0, 1.4), (22, 12, 1.9), water_mat)

    # Hollow gate: outer shell + painted band, hinged at the seabed (pivot empty)
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, -0.9))
    hinge = bpy.context.active_object
    hinge.name = "hinge"
    gate = box("gate", (0, 0, 0.8), (0.55, 7.5, 3.4), steel_mat)
    band = box("paint_band", (0, 0, 3.6), (0.58, 7.5, 0.55), accent_mat)
    gate.parent = hinge
    band.parent = hinge

    # Gate rests flat on the seabed, then swings up through mid-sequence.
    hinge.rotation_euler = (math.radians(90), 0, 0)
    hinge.keyframe_insert("rotation_euler", frame=40)
    hinge.rotation_euler = (math.radians(8), 0, 0)
    hinge.keyframe_insert("rotation_euler", frame=150)
    hinge.rotation_euler = (math.radians(8), 0, 0)
    hinge.keyframe_insert("rotation_euler", frame=args.frames)

    # Water rises against the gate after it is up (reads as "tide held back")
    water = bpy.data.objects["water"]
    water.scale = (1, 1, 1)
    water.keyframe_insert("scale", frame=150)
    water.scale = (1, 1, 1.35)
    water.location.z = 1.95
    water.keyframe_insert("scale", frame=args.frames)
    water.keyframe_insert("location", frame=args.frames)

    # Camera: slow dolly orbit around the hinge line
    bpy.ops.object.camera_add(location=(16, -18, 7))
    cam = bpy.context.active_object
    cam.data.lens = 42
    scene.camera = cam

    target = Vector((0, 0, 0.6))
    for frame, radius, angle in ((1, 30, math.radians(-52)), (args.frames, 24, math.radians(-18))):
        cam.location = (radius * math.cos(angle), radius * math.sin(angle), 7)
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)

    # Lighting: key sun + cool fill
    bpy.ops.object.light_add(type="SUN", location=(6, -4, 12))
    sun = bpy.context.active_object
    sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(28), math.radians(12), 0)
    bpy.ops.object.light_add(type="AREA", location=(-8, 6, 9))
    fill = bpy.context.active_object
    fill.data.energy = 900
    fill.data.color = (0.65, 0.75, 0.95)
    fill.data.shape = "DISK"
    fill.data.size = 8

    scene.world.color = (0.014, 0.02, 0.03)

    bpy.ops.render.render(animation=True)


main()
