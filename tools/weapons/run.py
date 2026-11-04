# Pangea Arena — tier-0 weapons pipeline entry point (runs inside Blender). GPLv2+.
#
#   blender -b --python-exit-code 1 -P tools/weapons/run.py -- <stage> [args]
#
# stages:
#   look  <outdir> [ids]   quick 3/4 renders with procedural materials + triangle counts
#   model <pak> [ids]      build -> bake textures -> export MD3/.skin into <pak> (content/pangea)
#   hands <pak>            hands: 3 builds x 9 poses, 13 race skins, wraps (+ fists paints)
#   fx    <pak>            flame animMap frames
#   icons <pak>            HUD icons iconw_<id>.tga
#   preview <pak> <outdir> preview sheets' tiles (rendered from the exported MD3s)
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))          # tools/ -> md3 package

import models  # noqa: E402
from lib import geo  # noqa: E402


def ids_or(default, rest):
    return rest if rest else default


def stage_look(outdir, ids):
    from lib import render
    os.makedirs(outdir, exist_ok=True)
    for mid in ids_or(models.ALL, ids):
        mod = models.load(mid)
        geo.reset_scene()
        objs = mod.build()
        meshes = [o for o in objs if o.type == 'MESH']
        tris = geo.tri_count([o for o in meshes if o.get("surface") != "flame"])
        print("TRIS %-16s %4d / %d" % (mid, tris, mod.TRI_MAX))
        if not meshes:
            continue
        lo, hi = render.bbox(meshes)
        render.stage(ground_z=lo.z - 0.05)
        c, rad = render.view34(meshes)
        render.lights(c, scale=max(rad / 20.0, 0.15))
        render.render(os.path.join(outdir, mid + ".png"), 480, 360, samples=24)


def place_items(tags, items, loader):
    """Attach item models (procedural or exported) at pose tags."""
    out = []
    for tname, mid in items.items():
        if tname not in tags:
            continue
        for o in loader(mid):
            o.matrix_world = tags[tname] @ o.matrix_world
            out.append(o)
    return out


def _procedural(mid):
    return [o for o in models.load(mid).build() if o.type == 'MESH']


def stage_hands_look(outdir, build="medium", poses=None):
    from hands import hands
    from hands.poses import POSE_ITEMS, POSES
    from lib import render
    os.makedirs(outdir, exist_ok=True)
    for pose in poses or list(POSES):
        geo.reset_scene()
        objs, tags = hands.build_pose(build, pose)
        place_items(tags, POSE_ITEMS[pose], _procedural)
        print("TRIS hands %-7s %-13s %4d" % (build, pose, geo.tri_count(objs)))
        render.world("#1a1512", 1.0)
        render.lights((14, 0, -4), scale=0.35)
        render.q3_view()
        render.render(os.path.join(outdir, "%s_%s.png" % (build, pose)), 480, 360, samples=16)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    st, rest = argv[0], argv[1:]
    if st == "look":
        stage_look(rest[0], rest[1:])
    elif st == "hands_look":
        stage_hands_look(rest[0], *(rest[1:2] or ["medium"]), poses=rest[2:] or None)
    else:
        from stages import run_stage
        run_stage(st, rest)


if __name__ == "__main__":
    main()
