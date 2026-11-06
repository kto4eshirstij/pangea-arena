#!/usr/bin/env python3
"""Authoring helpers: generate the fronts (3v3) and arena8 (8-FFA) archetype YAMLs with computed
coordinates, so symmetric geometry stays exact. Run once; the YAMLs are committed and hand-tunable.
Design rules (research-arena-maps-pangea.md §2): no pits / no falling into void, every void has a floor;
height changes only by stairs, ledges and jump pads.
"""
import os, sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "content", "pangea", "archetypes")
SKIN = {"floor": "textures/pangea_skin/floor_a", "wall": "textures/pangea_skin/wall_a",
        "ceil": "textures/pangea_skin/ceil_a", "trim": "textures/pangea_skin/trim_a", "sky": "textures/pangea_skin/sky"}


def fronts():
    """3v3 «Стенка»: two mirrored bases, contested centre, three routes (low, upper gallery, south flank)."""
    half = {
        "rooms": [
            {"id": "base", "box": [-1856, -320, 0, 768, 640, 384], "tiers": [0, 160]},
        ],
        "halls": [
            {"id": "low", "width": 192, "height": 192, "path": [[-1088, 0, 0], [-512, 0, 0]]},
            {"id": "upper", "width": 128, "height": 144,
             "path": [[-1472, 320, 160], [-1472, 560, 160], [-1472, 784, 256], [-256, 784, 256], [-256, 512, 256]]},
            {"id": "flank", "width": 160, "height": 160, "path": [[-1472, -320, 0], [-1472, -704, 0], [0, -704, 0]]},
        ],
        "ledges": [
            {"room": "base", "side": "west", "z": 160, "width": 192},                      # back platform (spawn shelf)
            {"room": "base", "side": "north", "z": 160, "width": 128, "from": -1664, "to": -1200},  # shelf to the upper exit
        ],
        "stairs": [
            {"from": [-1408, 0, 0], "to": [-1664, 0, 160], "width": 128},                # floor -> back platform, rising west
            {"from": [-1300, 0, 0], "to": [-1300, 192, 160], "width": 128},              # floor -> north shelf, rising north
            {"from": [-384, 0, 0], "to": [-160, 0, 128], "width": 160},                   # centre plinth stairs
        ],
        "jumppads": [
            {"at": [-384, 384, 0], "target": [-384, 460, 300]},                            # centre floor -> north gallery
        ],
        "items": [
            {"kind": "hide", "at": [-1200, -240, 0]},
            {"kind": "water", "at": [-1760, 0, 160]},
            {"kind": "water", "at": [-900, 784, 256]},
            {"kind": "fruit", "at": [-440, -440, 0], "n": 3},
            {"kind": "scrap", "at": [-900, -704, 0], "n": 3},
            {"kind": "spear", "at": [-1120, 0, 0]},
            {"kind": "spear", "at": [-448, 448, 256]},
            {"kind": "stones", "at": [-1472, -560, 0]},
            {"kind": "quiver", "at": [-1472, 240, 160]},
            {"kind": "campfire", "at": [-1700, -290, 160]},
        ],
        "spawns": [
            {"at": [-1760, -200, 160], "angle": 0},
            {"at": [-1760, 200, 160], "angle": 0},
            {"at": [-1400, -250, 0], "angle": 0},
            {"at": [-1400, 250, 0], "angle": 0},
            {"at": [-1200, 0, 0], "angle": 0},
            {"at": [-1472, -620, 0], "angle": 90},
        ],
    }
    spec = {
        "name": "fronts", "title": "Стенка (реликт)", "connectivity": "bottom_loop",
        "archetype_doc": "3 на 3: две зеркальные базы, спорный центр с помостом (источник) и галереями (панцирь), "
                         "три пути — низ, верхняя галерея, южный обход. Без пропастей.",
        "units": {"wall": 32}, "ambient": 8, "skin_textures": SKIN,
        "mirror": {"axis": "x", "at": 0},
        "rooms": [{"id": "centre", "box": [-512, -512, 0, 1024, 1024, 512], "open_top": True, "tiers": [0, 128, 256]}],
        "ledges": [
            {"room": "centre", "side": "north", "z": 256, "width": 128},                    # north gallery (carapace)
            {"room": "centre", "side": "south", "z": 256, "width": 128},                    # south gallery
        ],
        "blocks": [{"box": [-160, -160, 0, 320, 320, 128]}],                                  # centre plinth
        "items": [
            {"kind": "carapace", "at": [0, 448, 256]},                                         # north gallery of the centre
            {"kind": "spring", "at": [0, -704, 0]},                                            # south flank: the bypass matters
            {"kind": "scrap", "at": [0, -448, 256], "n": 2},
            {"kind": "water", "at": [0, 0, 128]},                                              # plinth top
        ],
        "spawns": [],
        "half": half,
        "intermission": {"at": [0, -300, 440], "angle": 90},
        "rules": {"carapace": 1, "spring": 1, "hide": 2, "scrap_groups_max": 3, "spawns": [10, 16],
                  "min_dist_carapace": 512, "min_dist_spring": 384, "players": [4, 8],
                  "modes": ["team"], "ring": False, "no_pits": True, "health": [120, 220]},
    }
    return spec


def arena8():
    """8-player FFA: open courtyard with a raised carapace platform, four rooms N/E/S/W, ring corridor
    between neighbouring rooms (bottom loop), two tiers everywhere, fist ring off the south room."""
    R = 1152   # distance from centre to room centre
    rooms, halls, ledges, stairs, items, spawns, jumppads = [], [], [], [], [], [], []
    # courtyard
    rooms.append({"id": "yard", "box": [-640, -640, 0, 1280, 1280, 512], "open_top": True, "tiers": [0, 192]})
    # central platform: 384x384, z 192, reachable by two stairs (N and S); carapace on top
    blocks = [{"box": [-192, -192, 0, 384, 384, 192]}]
    stairs += [{"from": [0, 448, 0], "to": [0, 192, 192], "width": 128},
               {"from": [0, -448, 0], "to": [0, -192, 192], "width": 128}]
    items.append({"kind": "carapace", "at": [0, 0, 192]})
    # four rooms
    dirs = {"n": (0, 1), "e": (1, 0), "s": (0, -1), "w": (-1, 0)}
    for name, (dx, dy) in dirs.items():
        cx, cy = dx * R, dy * R
        # room oriented so that the long side faces the yard; 768 along tangent, 576 radial
        if dx == 0:
            box = [cx - 384, cy - 288, 0, 768, 576, 352]
        else:
            box = [cx - 288, cy - 384, 0, 576, 768, 352]
        rooms.append({"id": name, "box": box, "tiers": [0, 160]})
        # ledge on the far wall (away from yard)
        far = {"n": "north", "s": "south", "e": "east", "w": "west"}[name]
        ledges.append({"room": name, "side": far, "z": 160, "width": 128})
        # stairs up to the far ledge along one side
        if dx == 0:
            sx = cx - 320
            stairs.append({"from": [sx, cy - dy * 32, 0], "to": [sx, cy + dy * 224, 160], "width": 112})
        else:
            sy = cy - 320
            stairs.append({"from": [cx - dx * 32, sy, 0], "to": [cx + dx * 224, sy, 160], "width": 112})
        # corridor room -> yard (radial), width 192
        inner_room = (cx - dx * 288, cy - dy * 288) if dx != 0 else (cx - dx * 288, cy - dy * 288)
        yard_edge = (dx * 640, dy * 640)
        halls.append({"id": f"{name}_in", "width": 192, "height": 192,
                      "path": [[inner_room[0], inner_room[1], 0], [yard_edge[0], yard_edge[1], 0]]})
    # ring corridors between neighbouring rooms (diagonals), width 160, with one bend
    pairs = [("n", "e"), ("e", "s"), ("s", "w"), ("w", "n")]
    for a, b in pairs:
        ax, ay = dirs[a][0] * R, dirs[a][1] * R
        bx, by = dirs[b][0] * R, dirs[b][1] * R
        # leave room a from its side wall toward b, bend at the corner (ax or bx), enter b from its side wall
        if dirs[a][0] == 0:   # a is n/s: exit east/west wall at x = ax +- 384 ; b is e/w
            start = [ax + (384 if bx > ax else -384), ay, 0]
            corner = [bx, ay, 0]
            end = [bx, by + (384 if ay > by else -384), 0]
        else:                 # a is e/w, b is n/s
            start = [ax, ay + (384 if by > ay else -384), 0]
            corner = [ax, by, 0]
            end = [bx + (384 if ax > bx else -384), by, 0]
        halls.append({"id": f"ring_{a}{b}", "width": 160, "height": 160, "path": [start, corner, end]})
    # items
    items += [
        {"kind": "spring", "at": [0, R + 200, 160]},               # north room far ledge
        {"kind": "hide", "at": [R + 200, 0, 160]},                 # east ledge
        {"kind": "hide", "at": [-R - 200, 0, 160]},                # west ledge
        {"kind": "mushroom", "at": [0, -R - 200, 160]},            # south ledge: мухомор
        {"kind": "scrap", "at": [R, R, 0], "n": 3},                # ring corners
        {"kind": "scrap", "at": [-R, -R, 0], "n": 3},
        {"kind": "scrap", "at": [R, -R, 0], "n": 2},
        {"kind": "water", "at": [448, 448, 0]}, {"kind": "water", "at": [-448, -448, 0]},
        {"kind": "water", "at": [-448, 448, 0]}, {"kind": "water", "at": [448, -448, 0]},
        {"kind": "water", "at": [0, R - 200, 0]}, {"kind": "water", "at": [0, -R + 200, 0]},
        {"kind": "fruit", "at": [R - 200, 300, 0], "n": 3, "along": "y"},
        {"kind": "fruit", "at": [-R + 200, -300, 0], "n": 3, "along": "y"},
        {"kind": "fruit", "at": [-300, R - 200, 0], "n": 3},
        {"kind": "fruit", "at": [300, -R + 200, 0], "n": 3},
        {"kind": "spear", "at": [-R, R, 0]}, {"kind": "spear", "at": [R, -700, 0]},
        {"kind": "spear", "at": [-R + 200, -R, 0]}, {"kind": "spear", "at": [0, 560, 0]},
        {"kind": "stones", "at": [R - 200, -R, 0]}, {"kind": "stones", "at": [-R + 200, R, 0]},
        {"kind": "stones", "at": [560, 0, 0]}, {"kind": "stones", "at": [-560, 0, 0]},
        {"kind": "quiver", "at": [R + 200, 300, 160]}, {"kind": "quiver", "at": [-R - 200, -300, 160]},
        {"kind": "quiver", "at": [300, R + 200, 160]}, {"kind": "quiver", "at": [-300, -R - 200, 160]},
        {"kind": "campfire", "at": [R + 200, -300, 160]}, {"kind": "campfire", "at": [-R - 200, 300, 160]},
    ]
    # spawns: 3 per room + 4 in ring corners
    for name, (dx, dy) in dirs.items():
        cx, cy = dx * R, dy * R
        tx, ty = -dy, dx   # tangent
        face = {"n": 270, "e": 180, "s": 90, "w": 0}[name]   # face the yard
        if name == "n":   # the spring room: spawns near the yard side only
            spawns += [{"at": [cx + tx * 250, cy - dy * 200, 0], "angle": face},
                       {"at": [cx - tx * 250, cy - dy * 200, 0], "angle": face}]
        else:
            spawns += [{"at": [cx + tx * 250, cy + ty * 250, 0], "angle": face},
                       {"at": [cx - tx * 250, cy - ty * 250, 0], "angle": face},
                       {"at": [cx + dx * 200 + tx * 150, cy + dy * 200 + ty * 150, 160], "angle": face}]
    for (sx, sy, ang) in [(R, R - 160, 225), (-R, R - 160, 315), (-R, -R + 160, 45), (R, -R + 160, 135)]:
        spawns.append({"at": [sx, sy, 0], "angle": ang})
    # fist ring off the south room (west side), link 96 wide
    ring = {"box": [-1024, -1024, 0, 384, 384, 256]}          # west of the south room, north of the ring corridor
    halls.append({"id": "ring_link", "width": 96, "height": 128, "path": [[-640, -960, 0], [-384, -960, 0]]})
    items.append({"kind": "water", "at": [-832, -860, 0]})
    spawns += [{"at": [-960, -960, 0], "angle": 0, "ring": True},
               {"at": [-704, -960, 0], "angle": 180, "ring": True}]
    spec = {
        "name": "arena8", "title": "Четыре двора (реликт)", "connectivity": "bottom_loop",
        "archetype_doc": "Бойня на 8: открытый двор с помостом (панцирь), четыре зала по сторонам света, "
                         "кольцевой коридор между соседями, два яруса, кольцо для кулаков у южного зала. Без пропастей.",
        "units": {"wall": 32}, "ambient": 8, "skin_textures": SKIN,
        "rooms": rooms, "halls": halls, "ledges": ledges, "stairs": stairs, "blocks": blocks,
        "items": items, "spawns": spawns, "ring": ring,
        "intermission": {"at": [0, -560, 460], "angle": 90},
        "rules": {"carapace": 1, "spring": 1, "hide": 2, "scrap_groups_max": 3, "spawns": [12, 20],
                  "min_dist_carapace": 512, "min_dist_spring": 384, "players": [3, 8],
                  "modes": ["brawl", "ranged"], "ring": True, "no_pits": True, "health": [180, 320]},
    }
    return spec


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def flow_lists(d):
    return d


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for spec in (fronts(), arena8()):
        path = os.path.join(OUT, spec["name"] + ".yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Архетип «{spec['title']}» — сгенерировано tools/mapgen/author.py, можно править руками.\n")
            f.write("# Координаты абсолютные (юниты Q3). Правило: без пропастей, у каждой пустоты есть пол.\n")
            yaml.dump(spec, f, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=120, default_flow_style=None)
        print("wrote", path)
