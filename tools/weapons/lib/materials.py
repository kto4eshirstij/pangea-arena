# Pangea Arena — procedural Blender materials for tier-0 ("Cave") weapons. GPLv2+.
#
# Every material has several outputs that bake.py switches between:
#   color — Principled BSDF with the procedural base colour (bake DIFFUSE/COLOR)
#   P     — emission = ochre-paint coordinates of the texel (float bake, see ochre.py)
#   M     — emission = (canvas mask, strength, shape 0=shaft/1=disc): where ochre may go
#   glow  — emission = self-illumination mask (embers), black if none
# Bump/roughness are folded into the colour: Q3 shading is diffuse-only.
import math

import bpy
from mathutils import Matrix, Vector


def lin(h):
    """sRGB hex -> linear RGBA."""
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


AXES = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}


class G:
    """Small node-graph builder."""

    def __init__(self, name):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        self.m = m
        self.nt = m.node_tree
        self.nt.nodes.clear()
        self.out = self.add('ShaderNodeOutputMaterial')
        self.bsdf = self.add('ShaderNodeBsdfPrincipled')
        self.bsdf.inputs['Roughness'].default_value = 0.8
        self.co = self.add('ShaderNodeTexCoord').outputs['Object']

    def add(self, t, **props):
        n = self.nt.nodes.new(t)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def put(self, inp, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, inp)
        elif isinstance(v, str):
            inp.default_value = lin(v)
        else:
            inp.default_value = v

    # --- coordinates -------------------------------------------------------
    def vec(self, scale=(1, 1, 1), loc=(0, 0, 0), rotd=(0, 0, 0), src=None):
        n = self.add('ShaderNodeMapping')
        self.put(n.inputs['Vector'], src if src is not None else self.co)
        n.inputs['Location'].default_value = loc
        n.inputs['Rotation'].default_value = [math.radians(a) for a in rotd]
        n.inputs['Scale'].default_value = scale if hasattr(scale, "__len__") else (scale,) * 3
        return n.outputs[0]

    def along(self, axis, stretch, scale=1.0, src=None):
        """Coordinates stretched along `axis` (grain, fibres): `stretch` < 1 = long streaks."""
        s = [scale, scale, scale]
        s["XYZ".index(axis)] *= stretch
        return self.vec(scale=s, src=src)

    # --- textures ----------------------------------------------------------
    def noise(self, v, scale=4.0, detail=4.0, rough=0.55, dist=0.0, color=False):
        n = self.add('ShaderNodeTexNoise')
        self.put(n.inputs['Vector'], v)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = dist
        return n.outputs['Color' if color else 'Fac']

    def voronoi(self, v, scale=5.0, feature='F1', out='Distance', rand=1.0):
        n = self.add('ShaderNodeTexVoronoi', feature=feature)
        self.put(n.inputs['Vector'], v)
        n.inputs['Scale'].default_value = scale
        n.inputs['Randomness'].default_value = rand
        return n.outputs[out]

    def wave(self, v, scale=5.0, kind='BANDS', axis='X', profile='SIN', dist=0.0, detail=2.0,
             phase=0.0):
        n = self.add('ShaderNodeTexWave', wave_type=kind, wave_profile=profile)
        if kind == 'BANDS':
            n.bands_direction = axis
        else:
            n.rings_direction = axis
        self.put(n.inputs['Vector'], v)
        n.inputs['Scale'].default_value = scale
        n.inputs['Distortion'].default_value = dist
        n.inputs['Detail'].default_value = detail
        n.inputs['Phase Offset'].default_value = phase
        return n.outputs['Fac']

    def ramp(self, fac, stops, interp='LINEAR'):
        n = self.add('ShaderNodeValToRGB')
        self.put(n.inputs['Fac'], fac)
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > len(stops):
            cr.elements.remove(cr.elements[-1])
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (pos, col) in zip(cr.elements, stops):
            el.position = pos
            el.color = lin(col) if isinstance(col, str) else col
        return n.outputs['Color']

    def mix(self, a, b, fac, blend='MIX', clamp=True):
        n = self.add('ShaderNodeMixRGB', blend_type=blend, use_clamp=clamp)
        self.put(n.inputs['Fac'], fac)
        self.put(n.inputs['Color1'], a)
        self.put(n.inputs['Color2'], b)
        return n.outputs['Color']

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.add('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        self.put(n.inputs[1], b)
        self.put(n.inputs[2], c)
        return n.outputs[0]

    def smooth(self, x, lo, hi):
        """smoothstep(lo, hi, x) via Map Range."""
        n = self.add('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        self.put(n.inputs['Value'], x)
        n.inputs['From Min'].default_value = lo
        n.inputs['From Max'].default_value = hi
        return n.outputs['Result']

    def pointiness(self):
        return self.add('ShaderNodeNewGeometry').outputs['Pointiness']

    def emission(self, col):
        e = self.add('ShaderNodeEmission')
        self.put(e.inputs['Color'], col)
        e.inputs['Strength'].default_value = 1.0
        return e

    def combine(self, x, y, z):
        n = self.add('ShaderNodeCombineXYZ')
        self.put(n.inputs[0], x)
        self.put(n.inputs[1], y)
        self.put(n.inputs[2], z)
        return n.outputs[0]

    def dot(self, v, w):
        n = self.add('ShaderNodeVectorMath', operation='DOT_PRODUCT')
        self.put(n.inputs[0], v)
        n.inputs[1].default_value = w
        return n.outputs['Value']


# ---------------------------------------------------------------------------
# Palette (sRGB hex). Warm Pangea range; obsidian is the only deep black.
PAL = {
    "ochre_red": "#b5532a", "ochre_yellow": "#c99a3a", "soot": "#1e1a17",
}

STONE_SHADES = ["#85807a", "#8f7c63", "#5d6264", "#8d6b57"]
FEATHER = [("#ddd6c6", "#3b332c"), ("#7a5536", "#d2b58a")]


def m_flint(g, p):
    big = g.noise(g.co, scale=0.9, detail=3)
    base = g.ramp(big, [(0.3, "#4f483f"), (0.7, "#7a6e60")])
    # conchoidal fracture scars: rippled cells, the fresh ones bluish-grey
    cell = g.voronoi(g.co, scale=p.get("chip", 1.6), out='Distance')
    rip = g.math('SINE', g.math('MULTIPLY', cell, 38.0))
    fresh = g.smooth(g.noise(g.co, scale=1.3, detail=1), 0.55, 0.7)
    col = g.mix(base, "#8b989d", g.math('MULTIPLY', g.smooth(cell, 0.22, 0.04), fresh))
    col = g.mix(col, "#3b3631", g.math('MULTIPLY', g.smooth(rip, 0.6, 1.0), 0.3))
    edge = g.smooth(g.pointiness(), 0.56, 0.66)
    col = g.mix(col, "#b9bcb4", g.math('MULTIPLY', edge, 0.6))
    return col, None


def m_obsidian(g, p):
    n = g.noise(g.co, scale=1.4, detail=2)
    band = g.wave(g.co, scale=1.2, dist=4.0, detail=3)
    col = g.ramp(n, [(0.3, "#08070a"), (0.7, "#18171d")])
    col = g.mix(col, "#3a3d4a", g.math('MULTIPLY', g.smooth(band, 0.85, 1.0), 0.6))
    return col, None


def m_bone(g, p):
    ax = p.get("axis", 'X')
    tone = g.noise(g.along(ax, 0.3, 0.6), scale=1.5, detail=3)
    col = g.ramp(tone, [(0.25, "#c7b48a"), (0.75, "#e3d7b5")])
    pores = g.noise(g.co, scale=22.0, detail=1)
    col = g.mix(col, "#8c7a58", g.math('MULTIPLY', g.smooth(pores, 0.62, 0.72), 0.6))
    crack = g.voronoi(g.along(ax, 0.25, 1.0), scale=1.6, feature='DISTANCE_TO_EDGE')
    cmask = g.math('MULTIPLY', g.smooth(crack, 0.03, 0.0), g.smooth(g.noise(g.co, 0.8), 0.45, 0.6))
    col = g.mix(col, "#4e3f2b", cmask)
    worn = g.smooth(g.pointiness(), 0.51, 0.58)
    col = g.mix(col, "#f2ead2", g.math('MULTIPLY', worn, 0.6))
    return col, None


def _wood(g, p, light, dark, heart=None):
    ax = p.get("axis", 'X')
    sc = p.get("grain", 1.0)
    fib = g.noise(g.along(ax, 0.06, 2.2 * sc), scale=3.0, detail=6, rough=0.6, dist=0.6)
    col = g.ramp(fib, [(0.35, dark), (0.65, light)])
    streak = g.noise(g.along(ax, 0.04, 6.0 * sc), scale=4.0, detail=2)
    col = g.mix(col, dark, g.math('MULTIPLY', g.smooth(streak, 0.55, 0.7), 0.5))
    if heart:
        h = g.noise(g.along(ax, 0.1, 0.5 * sc), scale=1.5, detail=2)
        col = g.mix(col, heart, g.math('MULTIPLY', g.smooth(h, 0.45, 0.6), 0.65))
    knot = g.voronoi(g.along(ax, 0.5, 0.35 * sc), scale=1.0)
    col = g.mix(col, "#4a3423", g.math('MULTIPLY', g.smooth(knot, 0.08, 0.02), 0.8))
    return col


def m_wood_ash(g, p):
    return _wood(g, p, "#c8ab80", "#8e7151"), None


def m_wood_yew(g, p):
    return _wood(g, p, "#d4a46c", "#8a4f2d", heart="#9a4a2a"), None


def m_wood_charred(g, p):
    crack = g.voronoi(g.co, scale=p.get("scale", 1.4), feature='DISTANCE_TO_EDGE')
    n = g.noise(g.co, scale=3.0, detail=4)
    col = g.ramp(n, [(0.3, "#151110"), (0.7, "#2e2420")])
    cm = g.smooth(crack, 0.06, 0.0)
    col = g.mix(col, "#5a2a14", g.math('MULTIPLY', cm, 0.8))
    glow = None
    if p.get("glow"):
        glow = g.ramp(g.math('MULTIPLY', cm, g.smooth(n, 0.35, 0.6)),
                      [(0.0, "#000000"), (0.4, "#5a1405"), (1.0, "#ffa040")])
    return col, glow


def m_hide(g, p):
    tone = g.noise(g.co, scale=0.35 * p.get("scale", 1.0), detail=4)
    col = g.ramp(tone, [(0.3, "#8d6a48"), (0.7, "#c09c72")])
    blot = g.noise(g.co, scale=1.1 * p.get("scale", 1.0), detail=2)
    col = g.mix(col, "#6c4f35", g.math('MULTIPLY', g.smooth(blot, 0.6, 0.75), 0.6))
    hair = g.noise(g.co, scale=30.0, detail=1)
    col = g.mix(col, "#e0c8a4", g.math('MULTIPLY', g.smooth(hair, 0.66, 0.75), 0.35))
    vein = g.voronoi(g.co, scale=0.9, feature='DISTANCE_TO_EDGE')
    col = g.mix(col, "#755638", g.math('MULTIPLY', g.smooth(vein, 0.04, 0.0), 0.4))
    if p.get("holes"):   # punched decoration (sling pouch)
        h = g.voronoi(g.co, scale=p["holes"], rand=0.15)
        col = g.mix(col, "#1a120c", g.smooth(h, 0.16, 0.12))
    return col, None


def m_leather_wrap(g, p):
    ax = p.get("axis", 'X')
    turns = p.get("turns", 1.4)        # turns per unit length
    v = g.co
    # bands across the axis, tilted (spiral): coordinate = axis + 0.25 * other
    oth = 'Z' if ax != 'Z' else 'X'
    w = g.math('ADD', g.dot(v, AXES[ax]), g.math('MULTIPLY', g.dot(v, AXES[oth]), 0.3))
    saw = g.math('FRACT', g.math('MULTIPLY', w, turns))
    seam = g.math('MAXIMUM', g.smooth(saw, 0.12, 0.0), g.smooth(saw, 0.85, 1.0))
    tone = g.noise(g.co, scale=1.0, detail=3)
    col = g.ramp(tone, [(0.3, p.get("dark", "#5f4530")), (0.7, p.get("light", "#93704c"))])
    col = g.mix(col, "#2c2016", g.math('MULTIPLY', seam, 0.85))
    shine = g.smooth(saw, 0.35, 0.55)
    col = g.mix(col, p.get("hi", "#b08a62"), g.math('MULTIPLY', shine, 0.25))
    return col, None


def m_sinew(g, p):
    ax = p.get("axis", 'X')
    tw = g.wave(g.vec(rotd=(0, 0, 35)), scale=p.get("scale", 4.0), axis=ax, dist=1.0)
    col = g.ramp(tw, [(0.0, "#9c7a45"), (1.0, "#e2c48a")])
    return col, None


def m_river_stone(g, p):
    shade = STONE_SHADES[p.get("shade", 0) % 4]
    n = g.noise(g.co, scale=0.8 * p.get("scale", 1.0), detail=3)
    col = g.ramp(n, [(0.2, "#4a4642"), (0.5, shade), (0.85, "#b8b2a6")])
    sp = g.noise(g.co, scale=14.0 * p.get("scale", 1.0), detail=1)
    col = g.mix(col, "#2e2b28", g.math('MULTIPLY', g.smooth(sp, 0.68, 0.74), 0.5))
    vein = g.wave(g.co, scale=0.45, dist=9.0, detail=3)
    vmask = g.math('MULTIPLY', g.smooth(vein, 0.975, 1.0), g.smooth(g.noise(g.co, 0.7), 0.5, 0.62))
    col = g.mix(col, "#cfc8ba", g.math('MULTIPLY', vmask, 0.35))
    return col, None


def m_fur(g, p):
    ax = p.get("axis", 'X')
    f = g.noise(g.along(ax, 0.15, 9.0), scale=4.0, detail=3)
    col = g.ramp(f, [(0.3, p.get("dark", "#4f3a26")), (0.7, p.get("light", "#a58660"))])
    return col, None


def m_feather(g, p):
    a, b = FEATHER[p.get("color", 0) % 2]
    ax = p.get("axis", 'X')
    bars = g.wave(g.co, scale=p.get("bars", 1.2), axis=ax, dist=0.8)
    col = g.mix(a, b, g.smooth(bars, 0.55, 0.7))
    barb = g.noise(g.along(ax, 3.0, 4.0), scale=6.0, detail=1)
    col = g.mix(col, "#000000", g.math('MULTIPLY', barb, 0.25))
    return col, None


def m_pitch(g, p):
    n = g.noise(g.co, scale=2.0, detail=3)
    col = g.ramp(n, [(0.4, "#0e0a07"), (0.75, "#3a2a1a")])
    gloss = g.smooth(g.pointiness(), 0.52, 0.56)
    col = g.mix(col, "#6b5236", g.math('MULTIPLY', gloss, 0.5))
    glow = None
    if p.get("glow"):
        glow = g.ramp(g.noise(g.co, scale=4.0, detail=3), [(0.55, "#000000"), (0.8, "#ff7a2a")])
    return col, glow


def m_birch(g, p):
    ax = p.get("axis", 'Z')
    n = g.noise(g.co, scale=0.8, detail=3)
    col = g.ramp(n, [(0.3, "#cfc6b4"), (0.7, "#ece6d8")])
    len_ = g.noise(g.along(ax, 6.0, 1.5), scale=3.0, detail=2)
    col = g.mix(col, "#2b2622", g.smooth(len_, 0.66, 0.7))
    peel = g.noise(g.co, scale=1.6, detail=2)
    col = g.mix(col, "#b58a5e", g.math('MULTIPLY', g.smooth(peel, 0.68, 0.74), 0.7))
    return col, None


def m_tow(g, p):
    """Bast/tow stuffing of the torch head (pitch-soaked fibres)."""
    f = g.noise(g.along(p.get("axis", 'X'), 0.3, 6.0), scale=4.0, detail=4, dist=1.5)
    col = g.ramp(f, [(0.3, "#2a1d12"), (0.6, "#6d5434"), (0.8, "#9a7c52")])
    glow = None
    if p.get("glow"):
        glow = g.ramp(f, [(0.62, "#000000"), (0.8, "#ff8030")])
    return col, glow


def m_solid(g, p):
    return p.get("color", "#808080"), None


KINDS = {
    "flint": m_flint, "obsidian": m_obsidian, "bone": m_bone,
    "wood_ash": m_wood_ash, "wood_yew": m_wood_yew, "wood_charred": m_wood_charred,
    "hide": m_hide, "leather_wrap": m_leather_wrap, "sinew": m_sinew,
    "river_stone": m_river_stone, "fur": m_fur, "feather": m_feather, "pitch": m_pitch,
    "birch": m_birch, "tow": m_tow, "solid": m_solid,
}


def paint_matrix(spec):
    """4x4 object->paint space: centre -> origin, spec['axis'] -> +X, spec['proj'] -> +Z,
    divided by spec['size']."""
    ax = Vector(spec.get("axis_vec") or AXES[spec.get("axis", 'X')]).normalized()
    pj = Vector(spec.get("proj_vec") or AXES[spec.get("proj", 'Z')])
    pj = (pj - pj.dot(ax) * ax).normalized()
    ay = pj.cross(ax)
    R = Matrix((ax, ay, pj))
    s = 1.0 / spec.get("size", 1.0)
    T = Matrix.Translation(-Vector(spec.get("center", (0, 0, 0))))
    return (Matrix.Diagonal((s, s, s, 1.0)) @ R.to_4x4() @ T)


def make(kind, name=None, paint=None, **p):
    """Create material `kind`. paint = ochre canvas spec (see paint_matrix) or None."""
    g = G(name or kind)
    col, glow = KINDS[kind](g, p)
    g.put(g.bsdf.inputs['Base Color'], col)
    nodes = {"color": g.bsdf}
    # P: paint coordinates, encoded 0.5 + 0.05 * p (range +-10)
    M = paint_matrix(paint) if paint else Matrix.Identity(4)
    comps = []
    for i in range(3):
        d = g.dot(g.co, Vector(M[i][:3]))
        d = g.math('ADD', d, M[i][3])
        comps.append(g.math('MULTIPLY_ADD', d, 0.05, 0.5))
    nodes["P"] = g.emission(g.combine(*comps))
    shape = {"shaft": 0.0, "disc": 1.0}[paint.get("shape", "shaft")] if paint else 0.0
    nodes["M"] = g.emission((1.0 if paint else 0.0, paint.get("strength", 1.0) if paint else 0.0,
                             shape, 1.0))
    nodes["glow"] = g.emission(glow if glow is not None else (0, 0, 0, 1))
    g.m["has_glow"] = glow is not None
    g.m["kind"] = kind
    g.m["_modes"] = list(nodes.keys())
    _MODES[g.m.name] = nodes
    set_mode(g.m, "color")
    return g.m


_MODES = {}


def set_mode(mat, mode):
    nodes = _MODES[mat.name]
    out = [n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    mat.node_tree.links.new(nodes[mode].outputs[0], out.inputs['Surface'])
