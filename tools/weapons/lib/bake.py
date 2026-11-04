# Pangea Arena — shared UV unwrap + Cycles CPU bake -> TGA. GPLv2+.
#
# All parts of a model stay separate objects (each keeps its own object-space procedural
# coordinates, e.g. wood grain along its own axis) but share ONE UV atlas and ONE image:
# smart project runs over all of them at once, then Cycles bakes them together.
import math

import bpy
import numpy as np

from . import materials, ochre, tga


def _select(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def bakeable(objs):
    return [o for o in objs if o.type == 'MESH' and not o.get("fixed_uv")]


def unwrap(objs, margin=0.008, angle=55.0):
    objs = bakeable(objs)
    _select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def _mats(objs):
    seen = []
    for o in objs:
        for m in o.data.materials:
            if m and m not in seen:
                seen.append(m)
    return seen


def _image(name, w, h):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    return img


def _pixels(img):
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()     # row 0 = top


def lin2srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def run(objs, size=(512, 512), samples_ao=32, margin_px=6, passes=("color", "ao", "P", "M")):
    """Bake the requested passes for `objs` into float arrays (row 0 = top).
    Returns dict: color (sRGB), ao (0..1), P, M (raw), glow (sRGB, if any material glows)."""
    objs = bakeable(objs)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    bk = sc.render.bake
    bk.margin = margin_px
    bk.margin_type = 'EXTEND'
    bk.use_clear = True
    bk.target = 'IMAGE_TEXTURES'
    mats = _mats(objs)
    texnodes = {}
    for m in mats:
        n = m.node_tree.nodes.new('ShaderNodeTexImage')
        n.name = "_bake"
        texnodes[m.name] = n
    passes = list(passes)
    if any(m.get("has_glow") for m in mats):
        passes.append("glow")
    out = {}
    w, h = size
    _select(objs)
    for ps in passes:
        img = _image("_bake_" + ps, w, h)
        for m in mats:
            n = texnodes[m.name]
            n.image = img
            m.node_tree.nodes.active = n
            materials.set_mode(m, "color" if ps in ("color", "ao") else ps)
        if ps == "color":
            sc.cycles.samples = 8
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
        elif ps == "ao":
            sc.cycles.samples = samples_ao
            bpy.ops.object.bake(type='AO')
        else:
            sc.cycles.samples = 4 if ps != "glow" else 8
            bpy.ops.object.bake(type='EMIT')
        px = _pixels(img)
        if ps in ("color", "glow"):
            px = lin2srgb(px)
        elif ps == "ao":
            px = px[..., 0]
        out[ps] = px
    for m in mats:
        materials.set_mode(m, "color")
        m.node_tree.nodes.remove(texnodes[m.name])
    return out


def compose(res, ao_strength=0.55):
    ao = res["ao"][..., None]
    return np.clip(res["color"] * (1.0 - ao_strength + ao_strength * ao), 0, 1)


def assign_texture(objs, path_or_array, name="_final"):
    """Swap the procedural materials for one image material (used by previews/icons)."""
    if isinstance(path_or_array, str):
        img = bpy.data.images.load(path_or_array, check_existing=True)
    else:
        arr = path_or_array
        h, w = arr.shape[:2]
        img = bpy.data.images.new(name, w, h)
        rgba = np.concatenate([arr[::-1], np.ones((h, w, 1))], -1).astype(np.float32)
        img.pixels.foreach_set(rgba.ravel())
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree.nodes.new('ShaderNodeTexImage')
    t.image = img
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs['Roughness'].default_value = 0.85
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    for o in bakeable(objs):
        o.data.materials.clear()
        o.data.materials.append(m)
    return m


def bake_set(objs, outdir, base, size=512, paint=True, ao_strength=0.55, seed=0):
    """Full texture set for a model: <base>.tga (+ _paint1..4, _glow). Returns dict of paths."""
    res = run(objs, (size, size))
    rgb = compose(res, ao_strength)
    paths = {"base": "%s/%s.tga" % (outdir, base)}
    tga.write(paths["base"], rgb)
    if paint and (res["M"][..., 0] > 0.5).any():
        for k in range(1, 5):
            pr = ochre.apply(res["color"], res["P"], res["M"], k, seed)
            res_k = dict(res, color=pr)
            p = "%s/%s_paint%d.tga" % (outdir, base, k)
            tga.write(p, compose(res_k, ao_strength))
            paths["paint%d" % k] = p
    if "glow" in res:
        p = "%s/%s_glow.tga" % (outdir, base)
        tga.write(p, res["glow"])
        paths["glow"] = p
    return paths
