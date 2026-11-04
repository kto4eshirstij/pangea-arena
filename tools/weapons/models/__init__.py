# Pangea Arena — tier-0 weapon/projectile model registry. GPLv2+.
#
# Each module defines:
#   ID       model id (file names, MD3 surface name)
#   KIND     "weapon" -> models/weapons2/<id>/, "projectile"/"item" -> models/projectiles/
#   TEX      texture size (square)
#   TRI_MAX  triangle budget (world model, flame planes excluded)
#   PAINT    True -> 4 ochre variants (<id>_paint1..4.tga + .skin)
#   build()  -> list of objects: meshes (+ obj["surface"] for extra surfaces) and tag_* empties
# Conventions: 1 unit = 1 Q3 unit, +X forward, +Z up, grip at the origin.
import importlib

WEAPONS = ["fists", "club", "spear", "atlatl", "sling", "bow", "torch", "shield"]
PROJECTILES = ["proj_stone1", "proj_stone2", "proj_stone3", "proj_stone4", "proj_arrow",
               "proj_arrow_fire", "proj_bola", "proj_brand", "proj_boulder",
               "item_quiver", "item_stones"]
ALL = WEAPONS + PROJECTILES

_ALIAS = {"proj_stone1": "proj_stone", "proj_stone2": "proj_stone", "proj_stone3": "proj_stone",
          "proj_stone4": "proj_stone", "proj_arrow_fire": "proj_arrow"}


def load(mid):
    mod = importlib.import_module("models." + _ALIAS.get(mid, mid))
    if hasattr(mod, "variant"):
        return mod.variant(mid)
    return mod
