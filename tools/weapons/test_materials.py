# Pangea Arena — W1 check: bake every material + the 4 ochre variants into a contact sheet.
# blender -b --python-exit-code 1 -P tools/weapons/test_materials.py -- <out.tga>
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

from lib import bake, geo, materials, tga  # noqa: E402

out = sys.argv[sys.argv.index("--") + 1]
S = 192
tiles = []


def tile(kind, shape="shaft", paint=None, variant=None, **p):
    geo.reset_scene()
    m = materials.make(kind, paint=paint, **p)
    if shape == "shaft":
        o = geo.tube("t", [(-10, 0, 0), (10, 0, 0)], 2.0, sides=10, mat=m)
    elif shape == "disc":
        o = geo.lathe("t", [(0.6, 0), (0.5, 9.0), (-0.5, 9.0), (-0.6, 0)], sides=16, mat=m)
    else:
        o = geo.blob("t", radii=(4, 3, 2.5), segs=12, rings=8, mat=m, jitter=0.2)
    bake.unwrap([o])
    res = bake.run([o], (S, S), samples_ao=8)
    if variant:
        from lib import ochre
        res["color"] = ochre.apply(res["color"], res["P"], res["M"], variant)
    tiles.append(bake.compose(res))


for k, kw in [("flint", {}), ("obsidian", {}), ("bone", {}), ("wood_ash", {}), ("wood_yew", {}),
              ("wood_charred", {}), ("hide", {}), ("leather_wrap", {}), ("sinew", {}),
              ("river_stone", {"shade": 0}), ("river_stone", {"shade": 1}),
              ("river_stone", {"shade": 2}), ("river_stone", {"shade": 3}), ("fur", {}),
              ("feather", {"color": 0}), ("feather", {"color": 1}), ("pitch", {}), ("birch", {}),
              ("tow", {})]:
    tile(k, shape="blob" if k in ("river_stone", "flint", "obsidian") else "shaft", **kw)
shaft = {"axis": 'X', "size": 10.0, "proj": 'Z'}
disc = {"axis": 'Y', "proj": 'X', "size": 9.0, "shape": "disc"}
for v in (1, 2, 3, 4):
    tile("wood_ash", paint=shaft, variant=v)
for v in (1, 2, 3, 4):
    tile("hide", shape="disc", paint=disc, variant=v)
cols = 6
rows = (len(tiles) + cols - 1) // cols
sheet = np.zeros((rows * S, cols * S, 3))
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    sheet[r * S:(r + 1) * S, c * S:(c + 1) * S] = t
tga.write(out, sheet)
print("SHEET", out, len(tiles))
