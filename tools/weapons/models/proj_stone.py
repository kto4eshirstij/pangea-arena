# Sling/throw pebbles proj_stone1..4: four shapes, four river-stone shades.
from types import SimpleNamespace

from lib import geo
from lib import materials as M

SHAPES = {1: ((1.5, 1.2, 0.95), 0.08), 2: ((1.3, 1.25, 1.15), 0.1),
          3: ((1.75, 1.0, 0.8), 0.07), 4: ((1.4, 1.1, 0.7), 0.12)}


def variant(mid):
    n = int(mid[-1])

    def build():
        radii, jit = SHAPES[n]
        m = M.make("river_stone", mid, shade=n - 1, scale=2.5)
        return [geo.blob(mid, (0, 0, 0), radii, segs=8, rings=5, mat=m, jitter=jit, seed=50 + n,
                         sharp=80)]
    return SimpleNamespace(ID=mid, KIND="projectile", TEX=128, TRI_MAX=80, PAINT=False,
                           build=build)
