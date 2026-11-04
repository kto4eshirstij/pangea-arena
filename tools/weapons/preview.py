# Pangea Arena — W5 preview tiles, rendered from the EXPORTED pak (MD3 + TGA + .skin), so the
# sheets show exactly what ships. GPLv2+. Cycles CPU.
#
#   blender -b --python-exit-code 1 -P tools/weapons/preview.py -- content/pangea <tiles_dir>
#   python3 tools/weapons/sheets.py <tiles_dir> docs/weapons/preview
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import models  # noqa: E402
from hands.poses import BUILDS, POSE_ITEMS, RACE_BUILD, RACES  # noqa: E402
from lib import geo, md3load, render  # noqa: E402
from stages import WEAPON_POSE, qdir  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
PAK, OUT = argv[0], argv[1]
ONLY = argv[2:]
os.makedirs(OUT, exist_ok=True)
SAMPLES = 40
AZ = {"shield": 215.0, "bow": 60.0, "sling": 60.0, "fists": 120.0}
manifest = {}


def item_q(mid):
    mod = models.load(mid)
    return "%s/%s.md3" % (qdir(mod), mid)


def three_quarter(path, objs, az=35.0, w=480, h=360, samples=SAMPLES):
    lo, hi = render.bbox(objs)
    render.stage(ground_z=lo.z - 0.02)
    c, rad = render.view34(objs, az=az)
    render.lights(c, scale=max(rad / 20.0, 0.15))
    render.render(path, w, h, samples=samples)


def first_person(path, pose, build="medium", race="human", skin_hands=None, w=480, h=360,
                 item_skins=None):
    q = "models/hands/%s/%s.md3" % (build, pose)
    objs, tags = md3load.load(PAK, q, skin=skin_hands or "models/hands/skin/%s.skin" % race)
    for tname, mid in POSE_ITEMS[pose].items():
        if tname in tags:
            sk = (item_skins or {}).get(mid)
            o, _ = md3load.load(PAK, item_q(mid), skin=sk, matrix=tags[tname], name=mid + ":")
            objs += o
    render.world("#16110e", 1.0)
    render.lights((14, 0, -4), scale=0.35)
    render.q3_view()
    render.render(path, w, h, samples=SAMPLES)


def tile(name):
    return os.path.join(OUT, name + ".png")


def want(mid):
    return not ONLY or mid in ONLY


# --- weapons: 3/4 base, first person, 4 paint variants ---------------------------------
for mid in models.WEAPONS:
    if not want(mid):
        continue
    mod = models.load(mid)
    pose = WEAPON_POSE[mid][0]
    qd = qdir(mod)
    t = {}
    if mid == "fists":
        def vload(skin="models/hands/skin/human.skin"):
            o, _ = md3load.load(PAK, "models/hands/medium/fist.md3", skin=skin)
            return o
        geo.reset_scene()
        three_quarter(tile(mid + "_34"), vload(), az=AZ[mid])
        variants = ["models/hands/skin/human_fists%d.skin" % k for k in range(1, 5)]
    else:
        def vload(skin=None, _mid=mid):
            o, _ = md3load.load(PAK, item_q(_mid), skin=skin)
            return o
        geo.reset_scene()
        three_quarter(tile(mid + "_34"), vload(), az=AZ.get(mid, 35.0))
        variants = ["%s/%s_paint%d.skin" % (qd, mid, k) for k in range(1, 5)]
    t["34"] = mid + "_34"
    geo.reset_scene()
    first_person(tile(mid + "_fp"), pose)
    t["fp"] = mid + "_fp"
    t["paint"] = []
    for k, sk in enumerate(variants, 1):
        if not os.path.exists(os.path.join(PAK, sk)):
            continue
        geo.reset_scene()
        three_quarter(tile("%s_p%d" % (mid, k)), vload(sk), az=AZ.get(mid, 35.0), w=240, h=180,
                      samples=24)
        t["paint"].append("%s_p%d" % (mid, k))
    with open(os.path.join(PAK, "..", "build", "weapons-meta", mid + ".json")) as f:
        t["tris"] = json.load(f)["tris"]
    manifest.setdefault("weapons", {})[mid] = t
    print("PREVIEW", mid)

# --- projectiles and pickups ------------------------------------------------------------
for mid in models.PROJECTILES:
    if not want(mid):
        continue
    geo.reset_scene()
    o, _ = md3load.load(PAK, item_q(mid))
    three_quarter(tile(mid), o, w=360, h=270)
    with open(os.path.join(PAK, "..", "build", "weapons-meta", mid + ".json")) as f:
        manifest.setdefault("projectiles", {})[mid] = {"tile": mid, "tris": json.load(f)["tris"]}
    print("PREVIEW", mid)

# --- hands: three builds, 13 skins ------------------------------------------------------
if want("hands"):
    for b in BUILDS:
        for pose in ("fist", "club"):
            geo.reset_scene()
            first_person(tile("hands_%s_%s" % (b, pose)), pose, build=b,
                         race={"small": "gnome", "medium": "human", "large": "goliath"}[b])
            manifest.setdefault("builds", []).append(("hands_%s_%s" % (b, pose), b, pose))
    for race in RACES:
        geo.reset_scene()
        first_person(tile("skin_" + race), "rite", build=RACE_BUILD[race], race=race, w=320, h=240)
        manifest.setdefault("skins", []).append(("skin_" + race, race, RACE_BUILD[race]))
    print("PREVIEW hands")

with open(os.path.join(OUT, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=1)
