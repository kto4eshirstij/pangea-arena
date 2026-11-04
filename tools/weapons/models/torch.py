# Pitch torch (concept 6A): split stick stuffed with birch bark and tow, charred top.
# Flame = separate surface "flame": two crossed planes, animated shader
# (scripts/pangea_weapons.shader: models/weapons2/torch/flame). Raised 42 deg.
import math

from lib import geo
from lib import materials as M

ID = "torch"
KIND = "weapon"
TEX = 512
TRI_MAX = 350
PAINT = True

ANG = 42.0
D = geo.Vector((math.cos(math.radians(ANG)), 0, math.sin(math.radians(ANG))))
R = geo.rot(0, -ANG, 0)          # +X -> D
TOP = D * 27.4


def at(t, off=(0, 0, 0)):
    return D * t + R @ geo.Vector(off)


def build():
    ash = M.make("wood_ash", "torch_stick", axis='X',
                 paint={"axis_vec": tuple(D), "center": tuple(D * 8.0), "size": 7.0,
                        "proj_vec": (0, 1, 0)})
    char = M.make("wood_charred", "torch_char", glow=True, scale=2.0)
    tow = M.make("tow", "torch_tow", axis='X', glow=True)
    bark = M.make("birch", "torch_bark", axis='X')
    sinew = M.make("sinew", "torch_bind")
    o = []
    o.append(geo.tube("stick", [at(-6.5), at(0), at(10), at(19.5)], [0.72, 0.76, 0.82, 0.92],
                      sides=6, mat=ash, jitter=0.03, seed=31))
    o.append(geo.blob("bundle", at(23.6), (3.9, 1.6, 1.6), segs=8, rings=5, mat=tow, r=R,
                      jitter=0.16, seed=32))
    o.append(geo.blob("crown", at(26.6), (1.9, 1.45, 1.45), segs=6, rings=4, mat=char, r=R,
                      jitter=0.15, seed=33))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        off = (0, math.cos(a) * 1.45, math.sin(a) * 1.45)
        o.append(geo.tube("bark%d" % k, [at(20.0, off), at(23.5, tuple(1.12 * c for c in off)),
                                         at(26.0, tuple(0.8 * c for c in off))],
                          [0.45, 0.55, 0.3], sides=4, mat=bark, flat=(1.0, 0.3),
                          up=tuple(R @ geo.Vector((0, math.cos(a), math.sin(a))))))
    o.append(geo.tube("bind", [at(19.6), at(20.6)], [1.08, 1.08], sides=6, mat=sinew))
    o.append(geo.cross_planes("flame", TOP - geo.Vector((0, 0, 1.0)), 6.5, 12.0, n=2,
                              surface="flame"))
    o.append(geo.tag("tag_weapon"))
    o.append(geo.tag("tag_flash", TOP + geo.Vector((0, 0, 4.5))))
    return o
