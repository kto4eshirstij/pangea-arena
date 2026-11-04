# Bola: three stone-filled leather pouches on three thongs tied in a knot; flies spinning
# with the thongs spread as a star (in the XY plane).
import math

from lib import geo
from lib import materials as M

ID = "proj_bola"
KIND = "projectile"
TEX = 256
TRI_MAX = 200
PAINT = False


def build():
    hide = M.make("hide", "bola_pouch", scale=3.0)
    thong = M.make("leather_wrap", "bola_thong", axis='X', turns=3.0)
    o = [geo.blob("knot", (0, 0, 0), (0.6, 0.6, 0.5), segs=6, rings=3, mat=thong, jitter=0.05)]
    for k in range(3):
        a = 2 * math.pi * k / 3
        d = geo.Vector((math.cos(a), math.sin(a), 0))
        o.append(geo.tube("thong%d" % k, [d * 0.4, d * 6.0], 0.13, sides=3, mat=thong,
                          caps=(False, False)))
        o.append(geo.blob("pouch%d" % k, d * 7.1, (1.3, 1.15, 1.1), segs=6, rings=4, mat=hide,
                          jitter=0.12, seed=60 + k, r=geo.rot(0, 0, math.degrees(a))))
    return o
