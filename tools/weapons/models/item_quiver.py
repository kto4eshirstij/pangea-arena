# Quiver pickup / belt model: birch-bark tube, fur collar, strap, five fletchings.
import math

from lib import geo
from lib import materials as M

ID = "item_quiver"
KIND = "item"
TEX = 256
TRI_MAX = 300
PAINT = False


def build():
    bark = M.make("birch", "quiver_bark", axis='Z')
    fur = M.make("fur", "quiver_fur", axis='Z')
    strap = M.make("leather_wrap", "quiver_strap", axis='Z', turns=0.6)
    feather = M.make("feather", "quiver_fl", color=1, axis='Z', bars=2.0)
    reed = M.make("wood_ash", "quiver_reed", axis='Z', grain=3.0)
    o = [geo.tube("tube", [(0, 0, 0), (0, 0, 9), (0, 0, 18.5)], [2.2, 2.35, 2.45], sides=8,
                  mat=bark, caps=(True, False)),
         geo.tube("collar", [(0, 0, 17.6), (0, 0, 19.6)], [2.8, 2.65], sides=8, mat=fur,
                  caps=(False, False), jitter=0.1),
         geo.tube("strap", [(0, -2.55, 2.0), (0, -2.75, 10), (0, -2.65, 18.0)], 0.6, sides=4,
                  mat=strap, flat=(1.0, 0.3), up=(0, 1, 0))]
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        base = geo.Vector((math.cos(a) * 1.1, math.sin(a) * 1.1, 18.5))
        tip = base + geo.Vector((math.cos(a) * 0.4, math.sin(a) * 0.4, 4.4))
        o.append(geo.tube("reed%d" % k, [base, tip], 0.15, sides=3, mat=reed, caps=(False, True)))
        r = geo.rot(0, -90, math.degrees(a) + 90 * (k % 2))
        o.append(geo.blob("fl%d" % k, base + geo.Vector((0, 0, 2.6)), (1.7, 0.04, 0.5), segs=4,
                          rings=2, mat=feather, r=r, sharp=80))
    return o
