# Pangea Arena — build stages for the tier-0 weapon pak (run inside Blender via run.py).
# GPLv2+.
import json
import math
import os

import bpy
import numpy as np

import export
import models
from lib import bake, geo, render, tga
from lib import materials as M

FLAME_SHADER = "models/weapons2/torch/flame"
FLAME_FRAMES = 8
# weapon -> (pose, tag in that pose where the weapon sits) for <id>_hand.md3
WEAPON_POSE = {"fists": ("fist", "tag_flash"), "club": ("club", "tag_weapon"),
               "spear": ("spear", "tag_weapon"), "atlatl": ("spear_atlatl", "tag_weapon_l"),
               "sling": ("sling", "tag_weapon"), "bow": ("bow", "tag_weapon_l"),
               "torch": ("torch", "tag_weapon"), "shield": ("shield", "tag_weapon_l")}


def qdir(mod):
    return "models/weapons2/%s" % mod.ID if mod.KIND == "weapon" else "models/projectiles"


def meta_dir(pak):
    d = os.path.join(os.path.dirname(os.path.abspath(pak)), "build", "weapons-meta")
    os.makedirs(d, exist_ok=True)
    return d


def write_meta(pak, name, data):
    with open(os.path.join(meta_dir(pak), name + ".json"), "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)


def write_skin(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write("".join("%s,%s\n" % kv for kv in lines))


# --- weapons, projectiles, items -------------------------------------------------------
def stage_model(pak, ids):
    for mid in ids or models.ALL:
        mod = models.load(mid)
        geo.reset_scene()
        objs = mod.build()
        qd = qdir(mod)
        ad = os.path.join(pak, qd)
        os.makedirs(ad, exist_ok=True)
        meshes = [o for o in objs if o.type == 'MESH' and o.get("surface") != "flame"]
        tris = geo.tri_count(meshes)
        if tris > mod.TRI_MAX:
            raise RuntimeError("%s: %d tris > budget %d" % (mid, tris, mod.TRI_MAX))
        paths = {}
        if mod.TEX and meshes:
            bake.unwrap(objs)
            paths = bake.bake_set(objs, ad, mid, size=mod.TEX, paint=mod.PAINT, seed=len(mid))
        glow = "glow" in paths
        base = "%s/%s" % (qd, mid) + ("" if glow else ".tga")
        shaders = {mid: base, "flame": FLAME_SHADER}
        has_flame = any(o.get("surface") == "flame" for o in objs)
        stats = export.export(os.path.join(ad, mid + ".md3"), "%s/%s.md3" % (qd, mid), objs, mid,
                              shaders)
        npaint = len([k for k in paths if k.startswith("paint")])
        for k in range(1, npaint + 1):
            lines = [(mid, ("%s/%s_paint%d" % (qd, mid, k)) + ("" if glow else ".tga"))]
            if has_flame:
                lines.append(("flame", FLAME_SHADER))
            write_skin(os.path.join(ad, "%s_paint%d.skin" % (mid, k)), lines)
        if mod.KIND == "weapon":
            hand_md3(pak, mid)
        write_meta(pak, mid, {"id": mid, "kind": mod.KIND, "qdir": qd, "tris": tris,
                              "surfaces": stats, "glow": glow, "paint": npaint,
                              "flame": has_flame, "tex": mod.TEX})
        print("MODEL %-16s %4d tris  %s" % (mid, tris, stats))


def hand_md3(pak, mid):
    """<id>_hand.md3: only tag_weapon = where the weapon sits in the medium first-person pose."""
    from hands import hands
    pose, tname = WEAPON_POSE[mid]
    geo.reset_scene()
    objs, tags = hands.build_pose("medium", pose)
    qd = "models/weapons2/%s" % mid
    export.export(os.path.join(pak, qd, mid + "_hand.md3"), "%s/%s_hand.md3" % (qd, mid), [],
                  mid, {}, extra_tags={"tag_weapon": tags[tname]})


# --- hands ------------------------------------------------------------------------------
def stage_hands(pak):
    from hands import hands
    from hands.poses import BUILDS, POSES, RACES
    geo.reset_scene()
    skin_dir = os.path.join(pak, "models/hands/skin")
    hands.bake_skins(skin_dir)
    hands.bake_wraps(os.path.join(pak, "models/hands/wraps.tga"),
                     os.path.join(pak, "models/weapons2/fists"))
    wraps_q = "models/hands/wraps.tga"
    for race in RACES:
        sk = "models/hands/skin/%s.tga" % race
        write_skin(os.path.join(skin_dir, race + ".skin"),
                   [("hands", sk), ("hands_l", sk), ("wraps", wraps_q)])
        for k in range(1, 5):
            write_skin(os.path.join(skin_dir, "%s_fists%d.skin" % (race, k)),
                       [("hands", sk), ("hands_l", sk),
                        ("wraps", "models/weapons2/fists/fists_paint%d.tga" % k)])
    for k in range(1, 5):
        write_skin(os.path.join(pak, "models/weapons2/fists/fists_paint%d.skin" % k),
                   [("wraps", "models/weapons2/fists/fists_paint%d.tga" % k)])
    stats = {}
    for build in BUILDS:
        for pose in POSES:
            geo.reset_scene()
            objs, tags = hands.build_pose(build, pose)
            q = "models/hands/%s/%s.md3" % (build, pose)
            st = export.export(os.path.join(pak, q), q, objs, "hands",
                               {"hands": "models/hands/skin/human.tga",
                                "hands_l": "models/hands/skin/human.tga", "wraps": wraps_q},
                               extra_tags=tags)
            stats["%s/%s" % (build, pose)] = {"surfaces": st, "tags": sorted(tags),
                                              "tris": geo.tri_count(objs)}
            print("HANDS %-7s %-13s %s" % (build, pose, st))
    write_meta(pak, "hands", stats)


# --- flame frames -----------------------------------------------------------------------
def _flame_material(t):
    """Procedural flame on a 0..1 UV plane; t in [0, 1) loops (two 4D noises cross-faded)."""
    g = M.G("flame")
    uv = g.add('ShaderNodeTexCoord').outputs['UV']
    sep = g.add('ShaderNodeSeparateXYZ')
    g.put(sep.inputs[0], uv)
    x, y = sep.outputs['X'], sep.outputs['Y']

    def n4(w, rise):
        n = g.add('ShaderNodeTexNoise', noise_dimensions='4D')
        sc = g.vec(scale=(3.0, 1.6, 1.0), loc=(0, -rise * 1.4, 0), src=uv)
        g.put(n.inputs['Vector'], sc)
        n.inputs['W'].default_value = w
        n.inputs['Scale'].default_value = 2.2
        n.inputs['Detail'].default_value = 4.0
        n.inputs['Roughness'].default_value = 0.55
        return n.outputs['Fac']
    # rising tongues; the second noise is the same field one loop later -> seamless animMap
    na = n4(t * 2.0, t)
    nb = n4(t * 2.0 - 2.0, t - 1.0)
    n = g.math('ADD', g.math('MULTIPLY', na, 1.0 - t), g.math('MULTIPLY', nb, t))
    dx = g.math('ABSOLUTE', g.math('SUBTRACT', x, 0.5))
    dx = g.math('ADD', g.math('MULTIPLY', dx, 2.0), g.math('MULTIPLY', g.math('SUBTRACT', n, 0.5),
                                                          g.math('MULTIPLY', y, 1.3)))
    width = g.math('ADD', g.math('MULTIPLY', g.math('POWER', g.math('SUBTRACT', 1.0, y), 1.3), 0.85), 0.02)
    body = g.math('SUBTRACT', 1.0, g.math('DIVIDE', g.math('ABSOLUTE', dx), width), clamp=True)
    base = g.smooth(y, 0.0, 0.12)
    tongues = g.math('SUBTRACT', g.math('MULTIPLY', body, base),
                     g.math('MULTIPLY', g.math('SUBTRACT', 1.0, n), g.math('MULTIPLY', y, 0.9)), clamp=True)
    heat = g.math('MULTIPLY', tongues, g.math('SUBTRACT', 1.25, g.math('MULTIPLY', y, 0.6)), clamp=True)
    col = g.ramp(heat, [(0.0, "#000000"), (0.12, "#3a0a02"), (0.35, "#b8320a"), (0.6, "#ff8a1c"),
                        (0.82, "#ffd36a"), (1.0, "#fff4d0")])
    e = g.emission(col)
    g.nt.links.new(e.outputs[0], g.out.inputs['Surface'])
    return g.m


def stage_fx(pak):
    out = os.path.join(pak, "models/weapons2/torch")
    os.makedirs(out, exist_ok=True)
    for k in range(FLAME_FRAMES):
        geo.reset_scene()
        render.world("#000000", 0.0)
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
        pl = bpy.context.active_object
        pl.scale = (0.5, 1.0, 1.0)
        pl.data.materials.append(_flame_material(k / FLAME_FRAMES))
        cam = render.camera((0, 0, 5), (0, 0, 0), ortho=1.0)
        cam.data.sensor_fit = 'VERTICAL'
        p = os.path.join(out, "flame%d.png" % (k + 1))
        render.render(p, 64, 128, samples=16)
        img = bpy.data.images.load(p)
        w, h = img.size
        a = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(a)
        rgb = a.reshape(h, w, 4)[::-1, :, :3]
        tga.write(os.path.join(out, "flame%d.tga" % (k + 1)), rgb)
        os.remove(p)
    print("FX flame frames:", FLAME_FRAMES)


# --- HUD icons --------------------------------------------------------------------------
ICON_VIEW = {  # model -> (rotation applied before the side view (deg about Y), view axis)
    "club": -45, "spear": -45, "atlatl": -35, "sling": 0, "bow": -20, "torch": 0, "shield": 0,
    "fists": 0,
}
ICON_FILL = (0xe2, 0xb6, 0x74)     # light ochre
ICON_EDGE = (0x5a, 0x2e, 0x14)


def _dilate(a, r):
    out = a.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out = np.maximum(out, np.roll(np.roll(a, dy, 0), dx, 1))
    return out


def stage_icons(pak, ids=None):
    from hands import hands
    out = os.path.join(pak, "icons")
    os.makedirs(out, exist_ok=True)
    for mid in ids or models.WEAPONS:
        geo.reset_scene()
        if mid == "fists":
            h, w = hands.hand_local("medium", "fist", (M.make("solid"), M.make("solid")),
                                    hands.wraps_materials())
            objs = [h, w]
            for o in objs:
                o.data.transform(geo.rot(0, 0, 90).to_4x4() @ geo.rot(-90, 0, 0).to_4x4())
        else:
            objs = [o for o in models.load(mid).build() if o.type == 'MESH']
            for o in [o for o in objs if o.get("surface") == "flame"]:
                c = sum((o.matrix_world @ v.co for v in o.data.vertices), geo.Vector()) / len(o.data.vertices)
                objs.remove(o)
                bpy.data.objects.remove(o)
                objs.append(geo.blob("flame_icon", c, (2.6, 2.6, 5.5), segs=8, rings=6,
                                     squash=lambda v: geo.Vector((v.x * (1.1 - v.z / 11), v.y * (1.1 - v.z / 11), v.z))))
        r = geo.rot(0, ICON_VIEW.get(mid, 0), 0).to_4x4()
        for o in objs:
            o.data.transform(o.matrix_world)
            o.matrix_world = r
        white = bpy.data.materials.new("white")
        white.use_nodes = True
        nt = white.node_tree
        nt.nodes.clear()
        e = nt.nodes.new('ShaderNodeEmission')
        o_ = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(e.outputs[0], o_.inputs[0])
        for o in objs:
            o.data.materials.clear()
            o.data.materials.append(white)
        lo, hi = render.bbox(objs)
        c = (lo + hi) / 2
        if mid in ("shield", "sling"):
            size = max(hi.y - lo.y, hi.z - lo.z) * 1.12
            render.camera((c.x + 100, c.y, c.z), c, ortho=size)
        else:
            size = max(hi.x - lo.x, hi.z - lo.z) * 1.12
            render.camera((c.x, c.y - 100, c.z), c, ortho=size)
        render.world("#000000", 0.0)
        p = os.path.join(out, "_%s.png" % mid)
        render.render(p, 256, 256, samples=4, transparent=True)
        img = bpy.data.images.load(p)
        a = np.empty(256 * 256 * 4, np.float32)
        img.pixels.foreach_get(a)
        alpha = a.reshape(256, 256, 4)[::-1, :, 3]
        # thin parts are fattened (dilation) so they survive 64 px; dark rim under the fill;
        # then 4x box downsample to 64
        body = _dilate(alpha, 5)
        rim = _dilate(body, 5)
        fill = np.array(ICON_FILL) / 255.0
        edge = np.array(ICON_EDGE) / 255.0
        rgb = edge[None, None, :] * (1 - body[..., None]) + fill[None, None, :] * body[..., None]
        A = rim
        rgb = rgb.reshape(64, 4, 64, 4, 3).mean((1, 3))
        A = A.reshape(64, 4, 64, 4).mean((1, 3))
        tga.write(os.path.join(out, "iconw_%s.tga" % mid), rgb, A)
        os.remove(p)
        print("ICON", mid)


def run_stage(st, rest):
    if st == "model":
        stage_model(rest[0], rest[1:])
    elif st == "hands":
        stage_hands(rest[0])
    elif st == "fx":
        stage_fx(rest[0])
    elif st == "icons":
        stage_icons(rest[0], rest[1:])
    else:
        raise SystemExit("unknown stage %s" % st)
