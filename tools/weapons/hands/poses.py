# Pangea Arena — first-person hand builds, finger curl presets and the 9 grip poses. GPLv2+.
#
# Hand-local frame (right hand): wrist at the origin, fingers +X, palm faces -Z (dorsal +Z),
# thumb on +Y. The left hand is the mirror image (thumb on -Y).
# View space = Q3 view origin: eye at 0,0,0 looking +X, +Y left, +Z up, fov 90.

BUILDS = {
    #          scale  palm-w  finger-r  finger-len  knuckle  forearm-r
    "small":  dict(s=0.84, pw=0.95, fr=0.88, fl=0.96, kn=1.0, ar=0.9),
    "medium": dict(s=1.0, pw=1.0, fr=1.0, fl=1.0, kn=1.0, ar=1.0),
    "large":  dict(s=1.2, pw=1.12, fr=1.22, fl=0.94, kn=1.18, ar=1.22),
}
RACE_BUILD = {
    "gnome": "small", "halfling": "small", "goblin": "small", "fey": "small",
    "human": "medium", "elf": "medium", "dwarf": "medium", "orc": "medium",
    "dragonborn": "medium", "tiefling": "medium", "felar": "medium",
    "goliath": "large", "troll": "large",
}
RACES = ["human", "elf", "dwarf", "gnome", "halfling", "orc", "goblin", "goliath",
         "dragonborn", "tiefling", "troll", "felar", "fey"]

# Finger curl presets: degrees per joint [MCP, PIP, DIP] for index, middle, ring, pinky;
# thumb: opp (swing under the palm), curl per joint.
CURLS = {
    "flat":  dict(f=[[0, 0, 0]] * 4, spread=1.0, t_opp=0, t=[0, 0, 0]),
    "fist":  dict(f=[[88, 100, 75]] * 4, spread=0.2, t_opp=55, t=[25, 45, 35]),
    "grip":  dict(f=[[62, 82, 55], [66, 84, 56], [70, 86, 58], [74, 88, 60]], spread=0.15,
                  t_opp=48, t=[20, 32, 22]),
    "loose": dict(f=[[25, 35, 20], [30, 40, 22], [35, 45, 25], [40, 50, 28]], spread=0.6,
                  t_opp=20, t=[5, 15, 10]),
    "pinch": dict(f=[[40, 62, 35], [48, 62, 38], [78, 90, 62], [82, 92, 62]], spread=0.3,
                  t_opp=40, t=[12, 30, 30]),
    "hook":  dict(f=[[55, 85, 60], [85, 98, 72], [88, 100, 74], [90, 100, 75]], spread=0.2,
                  t_opp=50, t=[18, 35, 28]),
    "stone": dict(f=[[45, 55, 35], [50, 58, 38], [55, 60, 40], [60, 62, 42]], spread=0.3,
                  t_opp=45, t=[10, 25, 20]),
    "cup":   dict(f=[[12, 18, 10], [12, 18, 10], [14, 20, 12], [16, 22, 12]], spread=0.1,
                  t_opp=15, t=[0, 10, 10]),
}

# Grip frames (right hand, medium, hand-local): where the held item's origin sits and how its
# axes map. axes = (item X, item Y, item Z) as hand-local vectors.
GRIPS = {
    "grip":   dict(o=(3.45, 0.05, -1.3), axes=((0, 1, 0), (-1, 0, 0), (0, 0, 1))),
    "fist":   dict(o=(4.6, 0.0, -0.6), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1))),
    "bow":    dict(o=(3.45, 0.05, -1.3), axes=((0, 0, 1), (1, 0, 0), (0, 1, 0))),
    "shield": dict(o=(-5.0, 0.0, 0.0), axes=((0, 0, 1), (1, 0, 0), (0, 1, 0))),
    "hook":   dict(o=(4.9, 1.15, -1.2), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1))),
    "stone":  dict(o=(2.6, 0.1, -1.55), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1))),
    # arrow on the string: item origin = arrow balance point, 14 u ahead of the fingers
    "pinch":  dict(o=(4.7 + 14.0, 0.9, -1.1), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1))),
    # torch: stick (raised 42 deg in the model) runs up through the fist along the thumb
    "torch":  dict(o=(3.45, 0.05, -1.3), axes=((0, 0.743, 0.669), (1, 0, 0), (0, 0.669, -0.743))),
    "cup":    dict(o=(2.2, 0.0, -0.7), axes=((1, 0, 0), (0, 1, 0), (0, 0, 1))),
}

# Poses. Each hand: side, curl preset, grip frame, and placement:
#   x/y  = view-space directions of the hand's fingers (X) and thumb side (Y)
#   at   = view-space point where the grip origin lands
#   item = (item X dir, item Y dir, item origin) — place the held item, the hand follows
#   on   = (tag of another hand, offset along that item's X, roll deg) — hand slides onto the
#          same item (two-handed spear)
#   wrist = (flex, deviation) degrees, bends the forearm (see hands._wrist)
# tag = name of the MD3 tag written at this hand's grip frame.
POSES = {
    "fist": [
        dict(side="R", curl="fist", grip="fist", x=(0.6, 0.65, 0.45), y=(0.1, -0.3, 1),
             at=(14.0, -3.8, -4.6), tag="tag_flash", wraps=True, wrist=(-15, 25)),
        dict(side="L", curl="fist", grip="fist", x=(0.6, -0.65, 0.45), y=(0.1, 0.3, -1),
             at=(15.5, 4.2, -5.0), tag="tag_flash_l", wraps=True, wrist=(-15, 25)),
    ],
    "club": [
        dict(side="R", curl="grip", grip="grip", x=(0.35, 0.92, -0.2), y=(0.55, -0.15, 1),
             at=(12.5, -6.5, -8.0), tag="tag_weapon", wrist=(0, 20)),
    ],
    "spear": [
        dict(side="R", curl="grip", grip="grip", x=(0.05, 0.75, -0.65), y=(1, 0.2, 0.1),
             at=(9.0, -6.0, -7.0), tag="tag_weapon", wrist=(0, 30)),
        dict(side="L", curl="grip", grip="grip", on=("tag_weapon", 12.0, 0), tag="tag_weapon_l"),
    ],
    "spear_atlatl": [
        dict(side="R", curl="grip", grip="grip", x=(-0.1, 0.55, 0.85), y=(1, 0.12, 0.1),
             at=(10.0, -6.5, -1.0), tag="tag_weapon", wrist=(0, -30)),
        dict(side="L", curl="grip", grip="grip", item=((1, -0.3, 0.05), (0.3, 1, 0), (14.0, 4.0, -7.5)),
             tag="tag_weapon_l", wrist=(0, 35)),
    ],
    "sling": [
        dict(side="R", curl="hook", grip="hook", x=(0.55, 0.8, 0.1), y=(-0.75, 0.55, 0),
             at=(17.0, -5.0, 2.5), tag="tag_weapon"),
        dict(side="L", curl="stone", grip="stone", x=(0.75, -0.6, 0.2), y=(-0.55, -0.75, 0.1),
             at=(14.0, 5.5, -7.5), tag="tag_weapon_l"),
    ],
    "bow": [
        dict(side="L", curl="grip", grip="bow", item=((1, -0.12, 0), (0.12, 1, 0.3), (19.0, 6.0, -2.0)),
             tag="tag_weapon_l", wrist=(-40, 60)),
        dict(side="R", curl="pinch", grip="pinch", x=(1, 0.3, 0.05), y=(-0.25, 0.4, 1),
             at=(26.0, 4.5, -3.2), tag="tag_weapon", wrist=(0, 25)),
    ],
    "torch": [
        dict(side="R", curl="grip", grip="torch", item=((1, 0.2, 0), (-0.2, 1, 0), (11.5, -7.0, -8.5)),
             tag="tag_weapon", wrist=(0, 45)),
    ],
    "shield": [
        dict(side="L", curl="fist", grip="shield", x=(0.25, -1, 0.15), y=(0.05, -0.15, -1),
             at=(19.0, 5.0, -7.0), tag="tag_weapon_l"),
        dict(side="R", curl="fist", grip="fist", x=(0.6, 0.65, 0.45), y=(0.1, -0.3, 1),
             at=(14.0, -5.0, -6.0), tag="tag_weapon", wrist=(-15, 25)),
    ],
    "rite": [
        dict(side="R", curl="cup", grip="cup", x=(0.92, 0.3, 0.15), y=(0.3, -0.95, 0),
             at=(15.0, -1.7, -6.5), tag="tag_flash"),
        dict(side="L", curl="cup", grip="cup", x=(0.92, -0.3, 0.15), y=(-0.3, -0.95, 0),
             at=(15.0, 1.7, -6.5), tag="tag_flash_l"),
    ],
}

# which item each pose shows in the preview (W5) and in cgame (W6): tag -> model id
POSE_ITEMS = {
    "fist": {}, "club": {"tag_weapon": "club"}, "spear": {"tag_weapon": "spear"},
    "spear_atlatl": {"tag_weapon": "spear", "tag_weapon_l": "atlatl"},
    "sling": {"tag_weapon": "sling", "tag_weapon_l": "proj_stone2"},
    "bow": {"tag_weapon_l": "bow", "tag_weapon": "proj_arrow"},
    "torch": {"tag_weapon": "torch"}, "shield": {"tag_weapon_l": "shield"}, "rite": {},
}
