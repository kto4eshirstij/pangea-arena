# Round hide shield on a willow frame (concept 7A): wicker rim ~60 cm, rawhide face,
# bone boss, two arm straps. Faces +X; the left forearm runs along Y through the origin.
from lib import geo
from lib import materials as M

ID = "shield"
KIND = "weapon"
TEX = 512
TRI_MAX = 500
PAINT = True

CX = 3.0      # face centre in front of the forearm
RAD = 12.0    # 24 u diameter


def build():
    hide = M.make("hide", "shield_hide", scale=0.5,
                  paint={"axis": 'Y', "proj": 'X', "center": (CX, 0, 0), "size": 10.5,
                         "shape": "disc"})
    rim = M.make("wood_ash", "shield_rim", axis='X', grain=3.0)
    bone = M.make("bone", "shield_boss", axis='Y')
    strap = M.make("leather_wrap", "shield_strap", axis='Z', turns=0.8)
    o = []
    o.append(geo.lathe("face", [(CX + 1.5, 0.0), (CX + 1.25, 4.0), (CX + 0.7, 8.6),
                                (CX + 0.25, RAD - 0.3), (CX - 0.15, RAD - 0.3), (CX - 0.25, 6.5),
                                (CX - 0.3, 0.0)], sides=16, mat=hide))
    o.append(geo.tube("rim", geo.ring_path((CX + 0.05, 0, 0), RAD, 14, 'X'), 0.55, sides=4,
                      mat=rim, closed=True, twist=0.785, jitter=0.05, seed=41))
    o.append(geo.blob("boss", (CX + 1.55, 0, 0), (1.15, 2.5, 2.5), segs=8, rings=4, mat=bone,
                      sharp=70))
    for k, y in enumerate((-3.2, 3.2)):
        o.append(geo.tube("strap%d" % k, [(CX - 0.3, y, -2.4), (-0.9, y, -1.8), (-1.75, y, 0),
                                          (-0.9, y, 1.8), (CX - 0.3, y, 2.4)],
                          0.55, sides=4, mat=strap, flat=(0.35, 1.0), up=(0, 1, 0)))
    o.append(geo.tag("tag_weapon"))
    o.append(geo.tag("tag_flash", (CX + 2.0, 0, 0)))
    return o
