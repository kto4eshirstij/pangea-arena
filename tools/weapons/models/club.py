# Club with a river-stone head (concept 2A): ash handle, stone in the split end, sinew
# cross-binding, pitch in the gaps, leather grip, wrist loop.
# Handle is arm-length (~70 cm = 28 u), see docs/weapons/README.md.
from lib import geo
from lib import materials as M

ID = "club"
KIND = "weapon"
TEX = 512
TRI_MAX = 500
PAINT = True

HEAD_X = 27.0


def build():
    ash = M.make("wood_ash", "club_ash", axis='X',
                 paint={"axis": 'X', "center": (13.5, 0, 0), "size": 8.5, "proj": 'Z'})
    wrap = M.make("leather_wrap", "club_wrap", axis='X', turns=1.5)
    stone = M.make("river_stone", "club_stone", shade=2, scale=0.7)
    sinew = M.make("sinew", "club_sinew", axis='Y')
    pitch = M.make("pitch", "club_pitch")
    o = []
    o.append(geo.tube("handle", [(-5.2, 0, 0), (-4, 0, 0), (6, 0, 0), (16, 0, 0), (23.8, 0, 0)],
                      [0.55, 0.72, 0.74, 0.84, 1.0], sides=6, mat=ash, jitter=0.03, seed=1))
    o.append(geo.tube("grip", [(-4.2, 0, 0), (0, 0, 0), (4.6, 0, 0)], [0.86, 0.88, 0.86],
                      sides=6, mat=wrap))
    for s in (1, -1):
        o.append(geo.tube("prong%d" % s,
                          [(23.0, 0.45 * s, 0), (25.0, 2.05 * s, 0), (28.5, 2.25 * s, 0), (31.0, 1.4 * s, 0)],
                          [0.62, 0.55, 0.5, 0.0], sides=5, mat=ash, flat=(0.55, 1.0), up=(0, 0, 1)))
    o.append(geo.blob("stone", (HEAD_X + 0.4, 0, 0), (3.1, 1.85, 3.3), segs=10, rings=7, mat=stone,
                      jitter=0.18, seed=3, sharp=75))
    for k, a in enumerate((32, -32)):
        pts = [geo.rot(0, a, 0) @ p for p in geo.ring_path((0, 0, 0), 0, 10, 'X', rx=2.75, ry=3.2)]
        pts = [p + geo.Vector((HEAD_X + 0.3, 0, 0)) for p in pts]
        o.append(geo.tube("bind%d" % k, pts, 0.22, sides=3, mat=sinew, closed=True))
    o.append(geo.blob("pitch", (24.2, 0, 0), (1.0, 1.55, 1.25), segs=6, rings=4, mat=pitch,
                      jitter=0.12, seed=5))
    o.append(geo.tube("loop", geo.ring_path((-5.9, 0, -1.7), 0, 8, 'Y', rx=0.9, ry=1.9), 0.15, sides=3,
                      mat=sinew, closed=True))
    o.append(geo.tag("tag_weapon"))
    o.append(geo.tag("tag_flash", (HEAD_X, 0, 0)))
    return o
