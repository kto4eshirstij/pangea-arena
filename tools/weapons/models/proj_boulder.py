# Goliath boulder.
from lib import geo
from lib import materials as M

ID = "proj_boulder"
KIND = "projectile"
TEX = 256
TRI_MAX = 150
PAINT = False


def build():
    m = M.make("river_stone", "boulder", shade=2, scale=0.35)
    return [geo.blob("boulder", (0, 0, 0), (6.2, 5.2, 4.6), segs=9, rings=6, mat=m, jitter=0.55,
                     seed=80, sharp=55)]
