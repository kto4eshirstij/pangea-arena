# Braided sling (concept 4A): two sinew cords, punched leather pouch with a pebble,
# finger loop at the origin, knotted tassel on the release end. Hangs along -Z.
from lib import geo
from lib import materials as M

ID = "sling"
KIND = "weapon"
TEX = 512
TRI_MAX = 300
PAINT = True

POUCH_Z = -16.6


def build():
    sinew = M.make("sinew", "sling_cord", axis='Z', scale=8.0)
    hide = M.make("hide", "sling_pouch", holes=2.2, scale=3.0,
                  paint={"axis": 'Y', "center": (0, 0, POUCH_Z), "size": 2.0, "proj": 'X'})
    stone = M.make("river_stone", "sling_stone", shade=1, scale=2.0)
    o = []
    o.append(geo.tube("loop", geo.ring_path((0, 0, 0), 0.62, 8, 'Y'), 0.13, sides=3, mat=sinew,
                      closed=True))
    o.append(geo.tube("cord_a", [(0, -0.2, -0.6), (0, -1.05, -8.5), (0, -2.15, POUCH_Z + 0.9)],
                      0.12, sides=3, mat=sinew, caps=(False, False)))
    o.append(geo.tube("cord_b", [(0.25, 0.55, -0.25), (0, 1.05, -8.5), (0, 2.15, POUCH_Z + 0.9)],
                      0.12, sides=3, mat=sinew, caps=(False, False)))
    o.append(geo.tube("pouch", [(0, -2.35, POUCH_Z + 1.0), (0, -1.3, POUCH_Z - 0.25),
                                (0, 0, POUCH_Z - 0.7), (0, 1.3, POUCH_Z - 0.25),
                                (0, 2.35, POUCH_Z + 1.0)],
                      [0.4, 1.05, 1.3, 1.05, 0.4], sides=8, mat=hide, flat=(1.0, 0.28),
                      up=(0, 0, 1)))
    o.append(geo.blob("stone", (0, 0, POUCH_Z + 0.25), (1.05, 1.0, 0.85), segs=8, rings=5,
                      mat=stone, jitter=0.07, seed=21))
    o.append(geo.blob("knot", (0.35, 0.75, -0.15), (0.38, 0.38, 0.38), segs=5, rings=3,
                      mat=sinew))
    for k, d in enumerate(((0.5, 0.3), (0.2, 0.7), (0.65, 0.95))):
        o.append(geo.tube("tassel%d" % k, [(0.4, 0.75, -0.3), (0.4 + d[0], 0.75 + d[1] * 0.6, -2.4)],
                          [0.09, 0.0], sides=3, mat=sinew, caps=(False, False)))
    o.append(geo.tag("tag_weapon"))
    o.append(geo.tag("tag_flash", (0, 0, POUCH_Z + 0.25)))
    return o
