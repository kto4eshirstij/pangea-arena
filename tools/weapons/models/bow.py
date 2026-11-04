# Yew longbow (concept 5A): shoulder-high stave, leather grip, horn nocks, sinew string,
# ochre on the limbs. Vertical along Z, arrow flies +X, string at -X (brace height).
from lib import geo
from lib import materials as M

ID = "bow"
KIND = "weapon"
TEX = 512
TRI_MAX = 600
PAINT = True

HALF = 29.0      # half length (58 u ~ 1.5 m)
BRACE = 6.8      # tip offset toward the archer


def limb_x(z):
    t = abs(z) / HALF
    return -BRACE * t ** 1.8


def build():
    yew = M.make("wood_yew", "bow_yew", axis='Z', grain=1.2,
                 paint={"axis": 'Z', "center": (0, 0, 0), "size": 24.0, "proj": 'X'})
    wrap = M.make("leather_wrap", "bow_wrap", axis='Z', turns=1.7)
    horn = M.make("bone", "bow_horn", axis='Z')
    sinew = M.make("sinew", "bow_string", axis='Z', scale=10.0)
    o = []
    zs = [-HALF + 2 * HALF * i / 18 for i in range(19)]
    pts = [(limb_x(z), 0, z) for z in zs]
    width = [1.05 - 0.6 * (abs(z) / HALF) ** 1.2 for z in zs]
    depth = [(0.62 - 0.3 * (abs(z) / HALF)) / w for z, w in zip(zs, width)]
    o.append(geo.tube("stave", pts, width, sides=6, mat=yew, flat=[(d, 1.0) for d in depth],
                      up=(0, 1, 0)))
    gz = [-2.8, 0, 2.8]
    o.append(geo.tube("grip", [(limb_x(z) + 0.0, 0, z) for z in gz], [1.12, 1.15, 1.12], sides=6,
                      mat=wrap, flat=(0.66, 1.0), up=(0, 1, 0)))
    for s in (1, -1):
        z0, z1 = s * (HALF - 1.9), s * (HALF + 0.7)
        o.append(geo.tube("nock%d" % s, [(limb_x(z0), 0, z0), (limb_x(z1) - 0.2 * 0, 0, z1)],
                          [0.52, 0.18], sides=6, mat=horn))
    sx = limb_x(HALF - 0.6)
    o.append(geo.tube("string", [(sx, 0, -(HALF - 0.6)), (sx, 0, HALF - 0.6)], 0.1, sides=3,
                      mat=sinew, caps=(False, False)))
    o.append(geo.tag("tag_weapon"))
    o.append(geo.tag("tag_flash", (sx, 0, 0)))
    return o
