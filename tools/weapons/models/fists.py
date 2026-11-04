# Fists (wraps of the pit fighter, concept 1A). No weapon geometry: the wraps and the bone
# plate are the "wraps" surface of the hands models (tools/weapons/hands). This model only
# carries tag_flash for hit effects; textures are baked by the hands stage.
from lib import geo

ID = "fists"
KIND = "weapon"
TEX = 0
TRI_MAX = 0
PAINT = False


def build():
    return [geo.tag("tag_weapon"), geo.tag("tag_flash", (3.0, 0, 0))]
