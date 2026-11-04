# Pebble pile pickup: six river stones.
import math

from lib import geo
from lib import materials as M

ID = "item_stones"
KIND = "item"
TEX = 256
TRI_MAX = 300
PAINT = False


def build():
    o = []
    spots = [(0, 0, 0.9, 1.25), (2.2, 0.9, 0.8, 1.05), (-1.6, 1.8, 0.75, 1.0), (-1.2, -2.0, 0.7, 1.1),
             (1.4, -1.8, 0.65, 0.95), (0.2, 0.3, 2.2, 0.95)]
    for k, (x, y, z, s) in enumerate(spots):
        m = M.make("river_stone", "pile%d" % k, shade=k % 4, scale=2.5)
        o.append(geo.blob("p%d" % k, (x, y, z), (1.4 * s, 1.1 * s, 0.85 * s), segs=6, rings=4,
                          mat=m, jitter=0.07, seed=90 + k, r=geo.rot(0, 0, k * 47),
                          sharp=80))
    return o
