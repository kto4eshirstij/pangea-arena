# Thrown brand: stub of a torch, charred and smouldering at the front end.
from lib import geo
from lib import materials as M

ID = "proj_brand"
KIND = "projectile"
TEX = 256
TRI_MAX = 150
PAINT = False


def build():
    wood = M.make("wood_yew", "brand_wood", axis='X')
    char = M.make("wood_charred", "brand_char", glow=True, scale=2.2)
    return [geo.tube("log", [(-5.0, 0, 0), (-1.5, 0.1, 0.05), (2.0, 0, 0)], [0.85, 0.95, 1.0],
                     sides=6, mat=wood, jitter=0.06, seed=70),
            geo.tube("scorch", [(0.2, 0, 0), (2.3, 0, 0)], [1.02, 1.08], sides=6, mat=char,
                     caps=(False, False), jitter=0.05),
            geo.blob("ember", (3.6, 0, 0), (2.1, 1.25, 1.25), segs=6, rings=4, mat=char,
                     jitter=0.14, seed=71),
            geo.tag("tag_flash", (4.6, 0, 0))]
