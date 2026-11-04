# Pangea Arena — first-person hands: 3 builds x 9 poses, segmented fingers, no skeleton.
# GPLv2+.
#
# Every hand of every build/pose has the SAME topology (same generator, only proportions and
# joint angles differ), so one UV layout — unwrapped once on the canonical medium flat hand —
# serves all of them, and one skin texture per race fits every build and pose.
import math

import bpy
from mathutils import Matrix, Vector

from lib import bake, geo
from lib import materials as M

from . import skins
from .poses import BUILDS, CURLS, GRIPS, POSES

MIRROR = Matrix.Diagonal((1, -1, 1, 1))
FINGERS = [  # y offset of the knuckle, segment lengths, radii (base..tip), spread deg
    (1.15, (1.75, 1.05, 0.85), (0.43, 0.39, 0.35, 0.31), 6.0),
    (0.40, (1.95, 1.15, 0.90), (0.45, 0.41, 0.36, 0.32), 1.0),
    (-0.38, (1.80, 1.10, 0.85), (0.42, 0.38, 0.34, 0.30), -4.0),
    (-1.12, (1.40, 0.85, 0.72), (0.37, 0.33, 0.30, 0.27), -10.0),
]


def _rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, Vector(axis))


def _chain(name, base, d0, n, lengths, radii, curls, skin, tip, kn=1.0):
    axis = d0.cross(n).normalized()
    parts = []
    p = Vector(base)
    d = Vector(d0)
    last = len(lengths) - 1
    for j, ln in enumerate(lengths):
        d = (_rot(axis, curls[j]) @ d).normalized()
        r0, r1 = radii[j] * (kn if j == 0 else 1.0), radii[j + 1]
        e = p + d * ln
        if j < last:
            pts, rr = [p - d * (0.25 * r0), e], [r0, r1]
        else:
            pts, rr = [p - d * (0.25 * r0), e, e + d * (0.55 * r1)], [r0, r1, 0.0]
        parts.append(geo.tube("%s%d" % (name, j), pts, rr, sides=6, mat=tip if j == last else skin,
                              flat=(1.0, 0.86), up=tuple(axis), caps=(j == 0, False), sharp=75))
        p = e
    return parts


def hand_local(build, curl, mats, wraps_mats=None, wrist=(0.0, 0.0)):
    """Right hand in hand-local space. wrist = (flex, deviation) degrees: bends the forearm
    toward the palm (flex) / toward the pinky side (deviation). Returns (hand, wraps|None)."""
    B = BUILDS[build]
    C = CURLS[curl]
    s = B["s"]
    skin, tip = mats
    L = 3.7 * s
    W = 3.3 * s * B["pw"]
    T = 1.15 * s * B["pw"] ** 0.5
    ar = s * B["ar"]
    parts = [
        geo.tube("forearm", [(-13 * s, 0, -0.1 * s), (-6 * s, 0, 0.1 * s), (0.5 * s, 0, 0)],
                 [1.55 * ar, 1.32 * ar, 1.0 * ar], sides=8, mat=skin, flat=(1.0, 0.78),
                 up=(0, 0, 1), caps=(True, False)),
        geo.tube("palm", [(-0.3 * s, 0, 0), (L * 0.5, 0, 0.05 * s), (L, 0, 0.1 * s)],
                 [W * 0.36, W * 0.5, W * 0.5], sides=8, mat=skin,
                 flat=[(1.0, T / (W * 0.72)), (1.0, T / W), (1.0, 0.9 * T / W)], up=(0, 0, 1)),
        geo.blob("thenar", (1.25 * s, W * 0.3, -0.33 * s), (1.45 * s, 0.75 * s, 0.6 * s), segs=6,
                 rings=4, mat=skin),
    ]
    fr, fl, kn = s * B["fr"], s * B["fl"], B["kn"]
    for i, (y, lens, radii, spread) in enumerate(FINGERS):
        d0 = _rot((0, 0, 1), spread * C["spread"]) @ Vector((1, 0, 0))
        parts += _chain("f%d_" % i, (L - 0.25 * s, y * s * B["pw"], 0.1 * s), d0, Vector((0, 0, -1)),
                        [ln * fl for ln in lens], [r * fr for r in radii], C["f"][i], skin, tip, kn)
    d0 = (_rot((1, 0, 0), -C["t_opp"]) @ Vector((0.55, 0.8, -0.25))).normalized()
    parts += _chain("thumb", (0.85 * s, W * 0.4, -0.3 * s), d0, Vector((0.2, -0.6, -0.8)).normalized(),
                    [1.55 * fl, 1.2 * fl, 0.95 * fl], [0.6 * fr, 0.52 * fr, 0.47 * fr, 0.41 * fr],
                    C["t"], skin, tip)
    W_ = _wrist(wrist)
    parts[0].data.transform(W_)
    hand = geo.merge("hand", parts, surface="hands")
    wraps = None
    if wraps_mats:
        band, plate = wraps_mats
        wp = [geo.tube("w_knuckle", [(L - 1.15 * s, 0, 0.08 * s), (L - 0.05 * s, 0, 0.1 * s)],
                       W * 0.535, sides=8, mat=band, flat=(1.0, 1.22 * T / W), up=(0, 0, 1),
                       caps=(False, False)),
              geo.tube("w_wrist", [(-1.4 * s, 0, 0.0), (0.35 * s, 0, 0.0)], 1.09 * ar, sides=8,
                       mat=band, flat=(1.0, 0.82), up=(0, 0, 1), caps=(False, False),
                       matrix=W_),
              geo.box("w_plate", (1.85 * s, 0, T * 0.5 + 0.1 * s), (1.5 * s, 1.35 * s, 0.24 * s),
                      mat=plate, taper=(0.8, 1.0))]
        wraps = geo.merge("wraps", wp, surface="wraps")
    return hand, wraps


def _wrist(wrist):
    flex, dev = wrist
    # flex: forearm (-X) swings toward the dorsal side (+Z) = hand bends toward the palm;
    # deviation: forearm swings toward -Y (pinky side of the right hand)
    return (Matrix.Rotation(math.radians(dev), 4, 'Z') @
            Matrix.Rotation(math.radians(flex), 4, 'Y'))


_UV = {}


def _uv_get(ob):
    me = ob.data
    a = [0.0] * (len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", a)
    return a


def _uv_set(ob, a):
    me = ob.data
    if len(a) != len(me.loops) * 2:
        raise RuntimeError("topology mismatch on %s: %d vs %d loops" % (ob.name, len(a) // 2, len(me.loops)))
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    me.uv_layers.active.data.foreach_set("uv", a)


def canonical(mats=None, wraps_mats=None):
    """Medium flat right hand (+ wraps) with the shared UV layout."""
    mats = mats or (skins.make("human"), skins.make("human", tip=True))
    hand, wraps = hand_local("medium", "flat", mats, wraps_mats)
    bake.unwrap([hand], margin=0.01, angle=60)
    if wraps:
        bake.unwrap([wraps], margin=0.01, angle=60)
    return hand, wraps


def uv_layouts():
    """Unwrap once per session and remember the per-loop UVs."""
    if not _UV:
        wm = wraps_materials()
        hand, wraps = canonical(wraps_mats=wm)
        _UV["hands"] = _uv_get(hand)
        _UV["wraps"] = _uv_get(wraps)
        for o in (hand, wraps):
            bpy.data.objects.remove(o)
    return _UV


def wraps_materials():
    band = M.make("leather_wrap", "wraps_band", axis='X', turns=2.4, light="#cdb084",
                  dark="#957251", hi="#e6cda2",
                  paint={"axis": 'X', "center": (1.6, 0, 0), "size": 2.6, "proj": 'Z'})
    plate = M.make("bone", "wraps_plate", axis='Y')
    return band, plate


def grip_matrix(grip, build, side):
    g = GRIPS[grip]
    s = BUILDS[build]["s"]
    ax = [Vector(a) for a in g["axes"]]
    m = Matrix((ax[0], ax[1], ax[2])).transposed().to_4x4()
    m.translation = Vector(g["o"]) * s
    if side == "L":
        m = MIRROR @ m @ MIRROR
    return m


def place(ob, side, mat):
    if side == "L":
        ob.data.transform(MIRROR)
        ob.data.flip_normals()
    ob.data.transform(mat)
    ob.data.update()


def build_pose(build, pose, mats=None, wraps_mats=None):
    """Hands for `pose` in view space. Returns (objects, tags {name: Matrix})."""
    uv = uv_layouts()
    mats = mats or (skins.make("human"), skins.make("human", tip=True))
    if wraps_mats is None and any(h.get("wraps") for h in POSES[pose]):
        wraps_mats = wraps_materials()
    objs, tags = [], {}
    for h in POSES[pose]:
        G = grip_matrix(h["grip"], build, h["side"])
        if "item" in h:
            ix, iy, at = h["item"]
            H = geo.frame(ix, iy, at) @ G.inverted()
        elif "on" in h:
            ref, off, roll = h["on"]
            Tw = tags[ref] @ Matrix.Translation((off, 0, 0)) @ Matrix.Rotation(math.radians(roll), 4, 'X')
            H = Tw @ G.inverted()
        else:
            H = geo.frame(h["x"], h["y"])
            H.translation = Vector(h["at"]) - H.to_3x3() @ G.translation
        tags[h["tag"]] = H @ G
        hand, wraps = hand_local(build, h["curl"], mats, wraps_mats if h.get("wraps") else None,
                                 h.get("wrist", (0.0, 0.0)))
        _uv_set(hand, uv["hands"])
        place(hand, h["side"], H)
        hand.name = "hand_" + h["side"]
        objs.append(hand)
        if wraps:
            _uv_set(wraps, uv["wraps"])
            place(wraps, h["side"], H)
            wraps.name = "wraps_" + h["side"]
            objs.append(wraps)
    return objs, tags


def bake_skins(skin_dir, races=None, size=(256, 512)):
    """models/hands/skin/<race>.tga — baked on the canonical hand (shared UVs)."""
    import os
    from lib import tga
    from .poses import RACES
    os.makedirs(skin_dir, exist_ok=True)
    uv = uv_layouts()
    out = {}
    for race in races or RACES:
        hand, _ = hand_local("medium", "flat", (skins.make(race), skins.make(race, tip=True)))
        _uv_set(hand, uv["hands"])
        res = bake.run([hand], size, samples_ao=24, passes=("color", "ao"))
        path = os.path.join(skin_dir, race + ".tga")
        tga.write(path, bake.compose(res, 0.45))
        out[race] = path
        bpy.data.objects.remove(hand)
    return out


def bake_wraps(wraps_path, paint_dir, size=256):
    """models/hands/wraps.tga (+ models/weapons2/fists/fists_paint1..4.tga)."""
    import os
    from lib import ochre, tga
    uv = uv_layouts()
    _, wraps = hand_local("medium", "fist", (skins.make("human"), skins.make("human", tip=True)),
                          wraps_materials())
    _uv_set(wraps, uv["wraps"])
    res = bake.run([wraps], (size, size), samples_ao=24)
    tga.write(wraps_path, bake.compose(res, 0.4))
    os.makedirs(paint_dir, exist_ok=True)
    paths = [wraps_path]
    for k in range(1, 5):
        pr = ochre.apply(res["color"], res["P"], res["M"], k, seed=7)
        p = os.path.join(paint_dir, "fists_paint%d.tga" % k)
        tga.write(p, bake.compose(dict(res, color=pr), 0.4))
        paths.append(p)
    return paths
