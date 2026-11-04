# Spear-thrower (atlatl), left hand: board with a hook-spur and a carved beast-head handle.
from lib import geo
from lib import materials as M

ID = "atlatl"
KIND = "weapon"
TEX = 512
TRI_MAX = 200
PAINT = True


def build():
    board = M.make("wood_ash", "atl_board", axis='X',
                   paint={"axis": 'X', "center": (9.5, 0, 0), "size": 7.5, "proj": 'Z'})
    carve = M.make("wood_yew", "atl_head", axis='X', grain=2.0)
    bone = M.make("bone", "atl_spur")
    wrap = M.make("leather_wrap", "atl_wrap", axis='X', turns=2.0)
    o = []
    o.append(geo.box("board", (9.6, 0, 0), (17.6, 1.5, 0.48), mat=board, taper=(0.65, 0.8)))
    o.append(geo.tube("spur", [(17.9, 0, 0.1), (18.5, 0, 0.7), (18.2, 0, 1.3)], [0.28, 0.2, 0.0],
                      sides=4, mat=bone))
    o.append(geo.tube("grip", [(-1.2, 0, 0), (1.9, 0, 0)], [0.62, 0.58], sides=6, mat=wrap))
    o.append(geo.blob("head", (-2.4, 0, 0.25), (1.35, 0.82, 1.0), segs=6, rings=4, mat=carve,
                      jitter=0.05, sharp=50))
    o.append(geo.blob("snout", (-3.6, 0, -0.05), (0.85, 0.5, 0.55), segs=6, rings=3, mat=carve,
                      sharp=50))
    for s in (1, -1):
        o.append(geo.tube("ear%d" % s, [(-1.9, 0.45 * s, 0.95), (-1.6, 0.6 * s, 1.9)], [0.32, 0.0],
                          sides=3, mat=carve, caps=(False, False)))
    o.append(geo.tag("tag_weapon_l"))
    return o
