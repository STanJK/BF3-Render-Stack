"""Build the reconstructed BF3 lens-flare stack in Blender's compositor.

Public version: no Battlefield 3 assets are bundled. Put the six locally
extracted flare PNGs under //private/flare or change ASSET_DIR below.

Expected topology after running:

    Render Layers ----------------------------> Switch OFF
         |                                           |
         +--> Raw_HDR File Output (untouched)        v
         |                                         Bloom
         +--> + Star A
              + Star B
              + Ring A
              + Ring B
              + Lens Dirt
              + Warm Ghost
              + Blue Ghost --------------------> Switch ON

Every flare layer is added directly to a full-frame image. This is important:
pre-composing finite flare sprites into a small-domain image can create a
visible square seam in Blender's compositor.
"""

import bpy
import math
from pathlib import Path
from bpy_extras.object_utils import world_to_camera_view

SUN_OBJECT_NAME = "SunCircle"
ASSET_DIR = Path(bpy.path.abspath("//")) / "local_assets" / "flare"

MASTER_STRENGTH = 1.0
TEXTURE_GAIN = 1.0112

STAR_INTENSITY = 0.06178417
RING_INTENSITY = 0.01170392
DIRTY_INTENSITY = 0.24746911
WARM_INTENSITY = 0.17841211
BLUE_INTENSITY = 0.07087997

STAR_SCALE = 765.17 / 720.0
RING_SCALE = 1102.66 / 720.0
DIRTY_SCALE = 746.21 / 720.0
WARM_SCALE = 15360.0 / 720.0
BLUE_SCALE = 921.60 / 720.0

FRAME_NAME = "BF3_LENS_FLARE_GENERATED"
SWITCH_NAME = "BF3_FLARE_AB_SWITCH"

REQUIRED_ASSETS = (
    "star.png",
    "ring.png",
    "dirty_source.png",
    "lens_dirt.png",
    "warm_ghost.png",
    "blue_ghost.png",
)

scene = bpy.context.scene
scene.use_nodes = True
tree = scene.node_tree
nodes = tree.nodes
links = tree.links


def find_first(bl_idname):
    return next((n for n in nodes if n.bl_idname == bl_idname), None)


def remove_links(socket):
    for link in list(socket.links):
        links.remove(link)


def image_output(node):
    return node.outputs.get("Image") or node.outputs[0]


def load_image(filename):
    path = (ASSET_DIR / filename).resolve()
    if not path.exists():
        raise RuntimeError(f"Missing BF3 local reference asset: {path}")

    for img in bpy.data.images:
        try:
            if Path(bpy.path.abspath(img.filepath)).resolve() == path:
                result = img
                break
        except Exception:
            pass
    else:
        result = bpy.data.images.load(str(path), check_existing=True)

    try:
        result.colorspace_settings.name = "sRGB"
    except Exception:
        pass
    return result


def delete_old_generated_frame():
    old = nodes.get(FRAME_NAME)
    if old is None:
        return
    children = [n for n in nodes if n.parent == old]
    for node in children:
        nodes.remove(node)
    nodes.remove(old)


def find_switch():
    node = nodes.get(SWITCH_NAME)
    if node is not None:
        return node
    return next((n for n in nodes if n.bl_idname == "CompositorNodeSwitch"), None)


def find_bloom(existing_switch=None):
    if existing_switch is not None:
        for link in image_output(existing_switch).links:
            n = link.to_node
            if n.inputs.get("Image") is not None:
                return n

    for n in nodes:
        text = f"{n.name} {n.label}".lower()
        if "bloom" in text and n.inputs.get("Image") is not None:
            return n

    for n in nodes:
        if n.bl_idname == "CompositorNodeGlare":
            return n

    render_layers = find_first("CompositorNodeRLayers")
    if render_layers is not None:
        for link in tree.links:
            if link.from_node != render_layers or link.from_socket.name != "Image":
                continue
            n = link.to_node
            if n.bl_idname in {
                "CompositorNodeOutputFile",
                "CompositorNodeComposite",
                "CompositorNodeViewer",
                "CompositorNodeSwitch",
            }:
                continue
            if n.inputs.get("Image") is not None and n.outputs.get("Image") is not None:
                return n
    return None


def image_node(frame, filename, x, y, label):
    n = nodes.new("CompositorNodeImage")
    n.parent = frame
    n.image = load_image(filename)
    n.name = f"BF3_{label}"
    n.label = label
    n.location = (x, y)
    return n


def render_fit(frame, source, x, y, label, stretch=False):
    n = nodes.new("CompositorNodeScale")
    n.parent = frame
    n.label = label
    n.location = (x, y)
    try:
        n.space = "RENDER_SIZE"
        n.frame_method = "STRETCH" if stretch else "FIT"
    except Exception:
        try:
            n.space = "SCENE_SIZE"
        except Exception:
            pass
    links.new(source, n.inputs["Image"])
    return n


def transform_node(frame, source, x, y, tx, ty, scale, shader_angle, label):
    n = nodes.new("CompositorNodeTransform")
    n.parent = frame
    n.label = label
    n.location = (x, y)
    links.new(source, n.inputs["Image"])
    n.inputs["X"].default_value = tx
    n.inputs["Y"].default_value = ty
    n.inputs["Scale"].default_value = scale
    n.inputs["Angle"].default_value = -shader_angle
    try:
        n.filter_type = "BILINEAR"
    except Exception:
        pass
    return n


def rgb_node(frame, rgb, x, y, label):
    n = nodes.new("CompositorNodeRGB")
    n.parent = frame
    n.label = label
    n.location = (x, y)
    n.outputs[0].default_value = (
        float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0
    )
    return n


def multiply_color(frame, image, rgb, x, y, label):
    color = rgb_node(frame, rgb, x - 180, y - 115, f"{label} gain")
    n = nodes.new("CompositorNodeMixRGB")
    n.parent = frame
    n.blend_type = "MULTIPLY"
    n.use_alpha = False
    n.use_clamp = False
    n.inputs[0].default_value = 1.0
    n.label = label
    n.location = (x, y)
    links.new(image, n.inputs[1])
    links.new(color.outputs[0], n.inputs[2])
    return n


def add_image(frame, full_frame_background, flare_foreground, x, y, label):
    n = nodes.new("CompositorNodeMixRGB")
    n.parent = frame
    n.blend_type = "ADD"
    n.use_alpha = False
    n.use_clamp = False
    n.inputs[0].default_value = 1.0
    n.label = label
    n.location = (x, y)
    links.new(full_frame_background, n.inputs[1])
    links.new(flare_foreground, n.inputs[2])
    return n


def math_node(frame, op, x, y, label):
    n = nodes.new("CompositorNodeMath")
    n.parent = frame
    n.operation = op
    n.label = label
    n.location = (x, y)
    return n


for filename in REQUIRED_ASSETS:
    if not (ASSET_DIR / filename).exists():
        raise RuntimeError(
            f"Missing {filename}. Public repo does not ship DICE assets. "
            f"Place local references in: {ASSET_DIR}"
        )

render_layers = find_first("CompositorNodeRLayers")
if render_layers is None:
    raise RuntimeError("Render Layers node not found")
if scene.camera is None:
    raise RuntimeError("Scene has no active camera")

sun = bpy.data.objects.get(SUN_OBJECT_NAME)
if sun is None:
    raise RuntimeError(f'Object "{SUN_OBJECT_NAME}" not found')

switch = find_switch()
bloom = find_bloom(switch)
if bloom is None:
    raise RuntimeError("Could not identify existing Bloom / Glare node")

co = world_to_camera_view(scene, scene.camera, sun.matrix_world.translation)
if co.z <= 0:
    raise RuntimeError("SunCircle is behind the active camera")

sun_u = float(co.x)
sun_v_bl = float(co.y)
sun_v_top = 1.0 - sun_v_bl

resolution_scale = scene.render.resolution_percentage / 100.0
W = scene.render.resolution_x * resolution_scale
H = scene.render.resolution_y * resolution_scale

sun_tx = (sun_u - 0.5) * W
sun_ty = (0.5 - sun_v_top) * H

ndc_x = 2.0 * sun_u - 1.0
ndc_y = 1.0 - 2.0 * sun_v_top
center_dist = math.sqrt(ndc_x * ndc_x + ndc_y * ndc_y)

blue_u = 1.0 - sun_u
blue_v_top = 1.0 - sun_v_top
blue_tx = (blue_u - 0.5) * W
blue_ty = (0.5 - blue_v_top) * H

print("BF3 flare build")
print(f"  Render: {W:.0f} x {H:.0f}")
print(f"  Sun UV: ({sun_u:.6f}, {sun_v_top:.6f})")
print(f"  centerDist: {center_dist:.9f}")

delete_old_generated_frame()

frame = nodes.new("NodeFrame")
frame.name = FRAME_NAME
frame.label = "BF3 Lens Flare — RenderStack"
frame.location = (render_layers.location.x + 450, render_layers.location.y - 700)

# Star A
star_a_img = image_node(frame, "star.png", -1800, 900, "Star A texture")
star_a_fit = render_fit(frame, star_a_img.outputs["Image"], -1580, 900, "Star A fit")
star_a_xf = transform_node(
    frame, star_a_fit.outputs["Image"], -1360, 900,
    sun_tx, sun_ty, STAR_SCALE, 0.4 * center_dist, "Star A — 0.4d"
)
star_a = multiply_color(
    frame, star_a_xf.outputs["Image"],
    (
        12.000 * STAR_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        3.442 * STAR_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        0.079 * STAR_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
    ),
    -1100, 900, "STAR A"
)

# Star B
star_b_img = image_node(frame, "star.png", -1800, 620, "Star B texture")
star_b_fit = render_fit(frame, star_b_img.outputs["Image"], -1580, 620, "Star B fit")
star_b_xf = transform_node(
    frame, star_b_fit.outputs["Image"], -1360, 620,
    sun_tx, sun_ty, STAR_SCALE, 1.2 * center_dist, "Star B — 1.2d"
)
star_b = multiply_color(
    frame, star_b_xf.outputs["Image"],
    (
        11.299 * STAR_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        12.000 * STAR_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        7.828 * STAR_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
    ),
    -1100, 620, "STAR B"
)

# Ring A/B
ring_gain = (
    3.000 * RING_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
    2.550 * RING_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
    1.977 * RING_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
)

ring_a_img = image_node(frame, "ring.png", -1800, 300, "Ring A texture")
ring_a_fit = render_fit(frame, ring_a_img.outputs["Image"], -1580, 300, "Ring A fit")
ring_a_xf = transform_node(
    frame, ring_a_fit.outputs["Image"], -1360, 300,
    sun_tx, sun_ty, RING_SCALE, -2.0 * center_dist, "Ring A — -2d"
)
ring_a = multiply_color(frame, ring_a_xf.outputs["Image"], ring_gain, -1100, 300, "RING A")

ring_b_img = image_node(frame, "ring.png", -1800, 20, "Ring B texture")
ring_b_fit = render_fit(frame, ring_b_img.outputs["Image"], -1580, 20, "Ring B fit")
ring_b_xf = transform_node(
    frame, ring_b_fit.outputs["Image"], -1360, 20,
    sun_tx, sun_ty, RING_SCALE, 2.0 * center_dist, "Ring B — +2d"
)
ring_b = multiply_color(frame, ring_b_xf.outputs["Image"], ring_gain, -1100, 20, "RING B")

# Dirt source -> luminance
src_img = image_node(frame, "dirty_source.png", -1800, -340, "Dirty source")
src_fit = render_fit(frame, src_img.outputs["Image"], -1580, -340, "Dirty fit")
src_xf = transform_node(
    frame, src_fit.outputs["Image"], -1360, -340,
    sun_tx, sun_ty, DIRTY_SCALE, 0.0, "Dirty place"
)

sep = nodes.new("CompositorNodeSepRGBA")
sep.parent = frame
sep.location = (-1100, -340)
links.new(src_xf.outputs["Image"], sep.inputs["Image"])

rm = math_node(frame, "MULTIPLY", -900, -270, "R x 0.299")
rm.inputs[1].default_value = 0.299
links.new(sep.outputs["R"], rm.inputs[0])

gm = math_node(frame, "MULTIPLY", -900, -370, "G x 0.587")
gm.inputs[1].default_value = 0.587
links.new(sep.outputs["G"], gm.inputs[0])

bm = math_node(frame, "MULTIPLY", -900, -470, "B x 0.114")
bm.inputs[1].default_value = 0.114
links.new(sep.outputs["B"], bm.inputs[0])

rg = math_node(frame, "ADD", -700, -320, "R + G")
links.new(rm.outputs[0], rg.inputs[0])
links.new(gm.outputs[0], rg.inputs[1])

lum = math_node(frame, "ADD", -500, -370, "Luminance")
links.new(rg.outputs[0], lum.inputs[0])
links.new(bm.outputs[0], lum.inputs[1])

dirty_gain = math_node(frame, "MULTIPLY", -300, -370, "x30 x intensity")
dirty_gain.inputs[1].default_value = (
    30.0 * DIRTY_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH
)
links.new(lum.outputs[0], dirty_gain.inputs[0])

# Full-screen dirt
dirt_img = image_node(frame, "lens_dirt.png", -700, -650, "Lens dirt")
dirt_screen = render_fit(
    frame, dirt_img.outputs["Image"], -480, -650,
    "Lens dirt full screen", stretch=True
)
dirty_final = nodes.new("CompositorNodeMixRGB")
dirty_final.parent = frame
dirty_final.blend_type = "MULTIPLY"
dirty_final.use_alpha = False
dirty_final.use_clamp = False
dirty_final.inputs[0].default_value = 1.0
dirty_final.label = "LENS DIRT"
dirty_final.location = (-60, -500)
links.new(dirt_screen.outputs["Image"], dirty_final.inputs[1])
links.new(dirty_gain.outputs[0], dirty_final.inputs[2])

# Warm ghost
warm_img = image_node(frame, "warm_ghost.png", -1800, -850, "Warm ghost texture")
warm_fit = render_fit(frame, warm_img.outputs["Image"], -1580, -850, "Warm ghost fit")
warm_xf = transform_node(
    frame, warm_fit.outputs["Image"], -1360, -850,
    sun_tx, sun_ty, WARM_SCALE, 0.0, "Warm ghost — huge quad"
)
warm = multiply_color(
    frame, warm_xf.outputs["Image"],
    (
        1.000 * WARM_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        0.922 * WARM_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        0.554 * WARM_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
    ),
    -1080, -850, "WARM GHOST"
)

# Blue mirrored ghost
blue_img = image_node(frame, "blue_ghost.png", -1800, -1130, "Blue ghost texture")
blue_fit = render_fit(frame, blue_img.outputs["Image"], -1580, -1130, "Blue ghost fit")
blue_xf = transform_node(
    frame, blue_fit.outputs["Image"], -1360, -1130,
    blue_tx, blue_ty, BLUE_SCALE, 0.0, "Blue ghost mirrored"
)
blue = multiply_color(
    frame, blue_xf.outputs["Image"],
    (
        0.131 * BLUE_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        0.350 * BLUE_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
        1.174 * BLUE_INTENSITY * TEXTURE_GAIN * MASTER_STRENGTH,
    ),
    -1080, -1130, "BLUE GHOST"
)

# Full-frame accumulation: critical domain-preservation fix.
stage_1 = add_image(frame, render_layers.outputs["Image"], star_a.outputs[0], 300, 850, "HDR + Star A")
stage_2 = add_image(frame, stage_1.outputs[0], star_b.outputs[0], 520, 700, "+ Star B")
stage_3 = add_image(frame, stage_2.outputs[0], ring_a.outputs[0], 740, 550, "+ Ring A")
stage_4 = add_image(frame, stage_3.outputs[0], ring_b.outputs[0], 960, 400, "+ Ring B")
stage_5 = add_image(frame, stage_4.outputs[0], dirty_final.outputs[0], 1180, 250, "+ Lens Dirt")
stage_6 = add_image(frame, stage_5.outputs[0], warm.outputs[0], 1400, 100, "+ Warm Ghost")
scene_plus_flare = add_image(frame, stage_6.outputs[0], blue.outputs[0], 1620, -50, "+ Blue Ghost")
scene_plus_flare.label = "SCENE + BF3 FLARE — FULL FRAME"

# A/B switch -> existing Bloom
if switch is None:
    switch = nodes.new("CompositorNodeSwitch")
    switch.location = (bloom.location.x - 260, bloom.location.y)

switch.name = SWITCH_NAME
switch.label = "BF3 Flare A/B"

off_input = switch.inputs.get("Off") or switch.inputs[0]
on_input = switch.inputs.get("On") or switch.inputs[1]
remove_links(off_input)
remove_links(on_input)
links.new(render_layers.outputs["Image"], off_input)
links.new(scene_plus_flare.outputs[0], on_input)

bloom_input = bloom.inputs.get("Image")
if bloom_input is None:
    raise RuntimeError("Detected Bloom node has no Image input")
remove_links(bloom_input)
links.new(image_output(switch), bloom_input)

print("BF3 flare nodes built successfully")
print("  Switch OFF = original Render Layers")
print("  Switch ON  = full-frame Render Layers + reconstructed flare")
print("  Both paths -> same Bloom node")
