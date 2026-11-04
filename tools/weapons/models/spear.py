# Spear with a flint leaf (concept 3A): 70 u shaft (shortened for the Q3 frame), leaf blade
# in a split end, sinew + pitch, fur/feather clan tuft, fire-hardened butt.
# Also used as the thrown/stuck projectile (proj_spear = spear.md3).
from lib import geo
from lib import materials as M

ID = "spear"
KIND = "weapon"
TEX = 512
TRI_MAX = 450
PAINT = True

TIP_X = 55.6


def build():
    ash = M.make("wood_ash", "spear_ash", axis='X', grain=0.8,
                 paint={"axis": 'X', "center": (24, 0, 0), "size": 13.0, "proj": 'Z'})
    char = M.make("wood_charred", "spear_char")
    flint = M.make("flint", "spear_flint", chip=0.9)
    sinew = M.make("sinew", "spear_sinew", axis='X', scale=6.0)
    fur = M.make("fur", "spear_fur", axis='X')
    feather = M.make("feather", "spear_feather", color=0, axis='X', bars=0.9)
    o = []
    o.append(geo.tube("shaft", [(-21, 0, 0), (-10, 0, 0.05), (4, 0, 0), (20, 0, -0.06), (34, 0, 0),
                                (46.2, 0, 0)],
                      [0.56, 0.57, 0.56, 0.54, 0.5, 0.46], sides=6, mat=ash, caps=(False, True)))
    o.append(geo.tube("butt", [(-24.6, 0, 0), (-21, 0, 0)], [0.0, 0.56], sides=6, mat=char,
                      caps=(False, False), jitter=0.04))
    o.append(geo.blob("leaf", (50.8, 0, 0), (5.0, 1.55, 0.34), segs=8, rings=6, mat=flint,
                      sharpen=0.5, jitter=0.06, seed=11, sharp=25, smooth=True))
    o.append(geo.tube("bind", [(44.0, 0, 0), (45.4, 0, 0), (46.8, 0, 0)], [0.6, 0.66, 0.55],
                      sides=6, mat=sinew))
    o.append(geo.tube("tuft", [(41.0, 0, 0), (41.8, 0, 0), (43.0, 0, 0), (44.0, 0, 0)],
                      [0.55, 1.25, 1.1, 0.6], sides=6, mat=fur, jitter=0.12, seed=12))
    for k, s in enumerate((1, -1)):
        o.append(geo.blob("feather%d" % k, (40.4, 0.9 * s, -2.1), (2.3, 0.5, 0.07), segs=6, rings=3,
                          mat=feather, r=geo.rot(0, -58, 18 * s), sharp=80))
    o.append(geo.tag("tag_weapon"))
    o.append(geo.tag("tag_flash", (TIP_X, 0, 0)))
    return o
