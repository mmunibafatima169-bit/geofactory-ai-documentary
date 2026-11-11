"""Generic Blender scene builder; saves an editable .blend, never renders video.

Run only after the blocked runtime is repaired and scene creation is approved:
.venv-blender/bin/python studio/blender/terrain_scene.py --config CONFIG.json --out scene.blend
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import bpy
from mathutils import Vector


def build_scene(config: dict, output: Path) -> None:
    terrain = config["terrain"]
    if terrain["vertical_exaggeration"] <= 0 or not terrain["source_attribution"]:
        raise ValueError("Invalid terrain configuration")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = int(config["fps"])
    scene.render.resolution_x, scene.render.resolution_y = map(int, config["resolution"])
    # Raster sampling is done through Blender's image data, preserving the source DEM.
    image = bpy.data.images.load(str(Path(terrain["dem_path"]).resolve()))
    width, height = image.size
    if width < 2 or height < 2:
        raise ValueError("DEM is too small")
    subdivisions = int(terrain["subdivisions"])
    sx, sy = min(width - 1, subdivisions), min(height - 1, subdivisions)
    pixels = list(image.pixels[:])
    vertices = []
    for y in range(sy + 1):
        py = min(height - 1, round(y / sy * (height - 1)))
        for x in range(sx + 1):
            px = min(width - 1, round(x / sx * (width - 1)))
            elevation = pixels[(py * width + px) * 4]
            vertices.append((x / sx - 0.5, y / sy - 0.5, elevation * terrain["vertical_exaggeration"]))
    faces = []
    for y in range(sy):
        for x in range(sx):
            a = y * (sx + 1) + x
            faces.append((a, a + 1, a + sx + 2, a + sx + 1))
    mesh = bpy.data.meshes.new("terrain_from_verified_dem")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Terrain", mesh)
    scene.collection.objects.link(obj)
    obj["dem_source"] = terrain["dem_path"]
    obj["vertical_datum"] = terrain["vertical_datum"]
    obj["vertical_exaggeration"] = terrain["vertical_exaggeration"]
    obj["attribution"] = terrain["source_attribution"]
    material = bpy.data.materials.new("TerrainMaterial")
    material.diffuse_color = (0.28, 0.32, 0.24, 1)
    material.roughness = float(config["environment"]["material_roughness"])
    obj.data.materials.append(material)
    world = bpy.data.worlds.new("DocumentaryWorld")
    world.color = tuple(config["environment"]["world_colour"])
    scene.world = world
    light = bpy.data.lights.new("Sun", "SUN")
    light.energy = float(config["environment"]["sun_energy"])
    light_obj = bpy.data.objects.new("Sun", light)
    light_obj.rotation_euler = tuple(config["environment"]["sun_rotation_deg"])
    scene.collection.objects.link(light_obj)
    camera_data = bpy.data.cameras.new("DocumentaryCamera")
    camera = bpy.data.objects.new("DocumentaryCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for key in config["camera_keys"]:
        camera.location = key["location"]
        direction = Vector(key["target"]) - camera.location
        camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        camera_data.lens = float(key["lens_mm"])
        camera.keyframe_insert(data_path="location", frame=int(key["frame"]))
        camera.keyframe_insert(data_path="rotation_euler", frame=int(key["frame"]))
        camera_data.keyframe_insert(data_path="lens", frame=int(key["frame"]))
    scene["source_attribution"] = terrain["source_attribution"]
    scene["render_policy"] = "Editable scene only; rendering requires separate approval"
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    build_scene(json.loads(args.config.read_text()), args.out)


if __name__ == "__main__":
    main()
