#!/usr/bin/env python3
"""Pangea Arena map generator: YAML blockout -> Quake 3 .map (legacy brush format).

Usage:
  python gen.py content/pangea/archetypes/depth.yaml --skin relic -o content/pangea/maps/pangea_depth_relic.map --png layout.png

Model (axis-aligned boxes, Q3 units; x east, y north, z up):
  voids  : rooms, hall segments and the ring are hollow boxes. Around every void six slabs
           (floor, ceiling, 4 walls) are generated; every other void is subtracted from those
           slabs, so openings appear wherever voids touch or overlap. No explicit doors.
  solids : ledges (slabs along a wall), stairs, blocks (platforms / pillars) are added inside voids.
  entities: jumppads, teleports, items, spawns, lights, pangea_ring trigger.
Textures use the alias prefix 'pangea_skin/<name>'; --skin rewrites it to 'pangea/<skin>/<name>'
(.map texture names carry no 'textures/' prefix).
"""
import argparse, math, os, sys
import yaml

TEXFMT = "{tex} 0 0 0 0.5 0.5 0 0 0"
CAULK = "common/caulk"
TRIGGER = "common/trigger"

DEFAULT_CLASSES = {          # vanilla Q3 stand-ins; overridden by common.yaml / skin.yaml item_classes
    "carapace": "item_armor_body",
    "spring": "item_health_mega",
    "hide": "item_armor_combat",
    "scrap": "item_armor_shard",
    "water": "item_health",
    "fruit": "item_health_small",
    "spear": "weapon_rocketlauncher",
    "stones": "ammo_shells",
    "quiver": "ammo_bullets",
    "campfire": "pangea_campfire",
    "mushroom": "item_quad",            # мухомор (урон x2)
    "honey": "item_haste",              # пьяный мёд (скорость)
    "glowshroom": "item_regen",         # светящиеся грибы (регенерация)
}


def fmt(v):
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:.3f}"


FIT_TEX = 1024          # size of "fit" textures (lamp, ring floor, pads): art2skin/texgen write them at 1024
TRIM_H = 256            # trim band height in texels (maps onto the brush's vertical extent)

# Q3 legacy texture projection: per dominant axis -> (s axis, t axis) in world space
_AXES = {"z": ((1, 0, 0), (0, -1, 0)), "x": ((0, 1, 0), (0, 0, -1)), "y": ((1, 0, 0), (0, 0, -1))}


def _face_tex(axis, box, tex, fit, size):
    """Return texture params string for a face with dominant normal `axis`.
    fit: None (default 0.5 scale), 'both' (texture spans the face exactly), 'vertical' (t spans face height)."""
    x0, y0, z0, x1, y1, z1 = box
    sv, tv = _AXES[axis]
    def ext(v):   # extent of the face along world vector v, and the world coordinate where t/s should be 0
        if v[0]: return (x1 - x0), (x0 if v[0] > 0 else x1)
        if v[1]: return (y1 - y0), (y0 if v[1] > 0 else y1)
        return (z1 - z0), (z0 if v[2] > 0 else z1)
    W, H = size
    xs = ys = 0.5
    xoff = yoff = 0
    if fit in ("both", "vertical"):
        es, s0 = ext(sv)
        et, t0 = ext(tv)
        if fit == "both" and es >= 1:
            xs = es / W
            xoff = (-(s0 * (1 if sv[0] + sv[1] + sv[2] > 0 else -1)) / xs) % W
        if et >= 1:
            ys = et / H
            yoff = (-(t0 * (1 if tv[0] + tv[1] + tv[2] > 0 else -1)) / ys) % H
    return f"{tex} {fmt(xoff)} {fmt(yoff)} 0 {fmt(xs)} {fmt(ys)} 0 0 0"


def box_brush(b, tex, textop=None, texbot=None, fit=None, fit_faces=("top",), size=(FIT_TEX, FIT_TEX), fit_box=None):
    """Axis-aligned box brush; points are ordered so plane normals face outward.
    fit/fit_faces: apply texture fitting to 'top', 'bottom' and/or 'sides'."""
    x0, y0, z0, x1, y1, z1 = b
    if x1 - x0 < 1 or y1 - y0 < 1 or z1 - z0 < 1:
        raise ValueError(f"degenerate box {b}")
    tt, tb = textop or tex, texbot or tex
    faces = [
        ((x0, y0, z1), (x0, y1, z1), (x1, y1, z1), tt, "z", "top"),
        ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), tb, "z", "bottom"),
        ((x0, y0, z0), (x0, y0, z1), (x1, y0, z1), tex, "y", "sides"),
        ((x1, y1, z0), (x1, y1, z1), (x0, y1, z1), tex, "y", "sides"),
        ((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), tex, "x", "sides"),
        ((x0, y1, z0), (x0, y1, z1), (x0, y0, z1), tex, "x", "sides"),
    ]
    lines = ["{"]
    for p1, p2, p3, t, axis, kind in faces:
        pts = " ".join("( %s %s %s )" % tuple(fmt(c) for c in p) for p in (p1, p2, p3))
        f = fit if (fit and kind in fit_faces) else None
        lines.append(f"{pts} {_face_tex(axis, fit_box or b, t, f, size)}")
    lines.append("}")
    return "\n".join(lines)


def overlap(a, b):
    return a[0] < b[3] and a[3] > b[0] and a[1] < b[4] and a[4] > b[1] and a[2] < b[5] and a[5] > b[2]


def subtract3(s, u):
    """Box s minus box u -> list of boxes (up to 6)."""
    if not overlap(s, u):
        return [s]
    x0, y0, z0, x1, y1, z1 = s
    cx0, cy0, cz0 = max(x0, u[0]), max(y0, u[1]), max(z0, u[2])
    cx1, cy1, cz1 = min(x1, u[3]), min(y1, u[4]), min(z1, u[5])
    out = []
    if cz0 > z0: out.append((x0, y0, z0, x1, y1, cz0))
    if cz1 < z1: out.append((x0, y0, cz1, x1, y1, z1))
    if cy0 > y0: out.append((x0, y0, cz0, x1, cy0, cz1))
    if cy1 < y1: out.append((x0, cy1, cz0, x1, y1, cz1))
    if cx0 > x0: out.append((x0, cy0, cz0, cx0, cy1, cz1))
    if cx1 < x1: out.append((cx1, cy0, cz0, x1, cy1, cz1))
    return [b for b in out if b[3] - b[0] >= 1 and b[4] - b[1] >= 1 and b[5] - b[2] >= 1]


def subtract_all(s, voids):
    pieces = [s]
    for u in voids:
        nxt = []
        for p in pieces:
            nxt.extend(subtract3(p, u))
        pieces = nxt
        if not pieces:
            break
    return pieces


def expand_mirror(spec):
    """If spec has `mirror: {axis: x, at: X}` and a `half:` section, append mirrored copies of every
    element of `half` to the top-level lists (and the originals too). Shared elements stay top-level."""
    m = spec.get("mirror")
    half = spec.get("half")
    if not m or not half:
        return spec
    X = m.get("at", 0)
    axis = m.get("axis", "x")
    ix = 0 if axis == "x" else 1

    def mp(p):
        p = list(p); p[ix] = 2 * X - p[ix]; return p

    def mbox(b):
        b = list(b); b[ix] = 2 * X - (b[ix] + b[ix + 3]); return b

    def mang(a):
        return (180 - a) % 360 if axis == "x" else (-a) % 360

    swap = {"east": "west", "west": "east"} if axis == "x" else {"north": "south", "south": "north"}
    out = {k: list(spec.get(k, [])) for k in ("rooms", "halls", "ledges", "stairs", "blocks", "jumppads", "teleports", "items", "spawns", "lights")}
    for r in half.get("rooms", []):
        out["rooms"].append(r); out["rooms"].append({**r, "id": r["id"] + "_m", "box": mbox(r["box"])})
    for h in half.get("halls", []):
        out["halls"].append(h); out["halls"].append({**h, "id": h.get("id", "hall") + "_m", "path": [mp(p) for p in h["path"]]})
    for l in half.get("ledges", []):
        out["ledges"].append(l)
        lm = {**l, "room": l["room"] + "_m", "side": swap.get(l["side"], l["side"])}
        along_mirror_axis = (l["side"] in ("north", "south")) == (axis == "x")
        if along_mirror_axis and ("from" in l or "to" in l):
            f, t = l.get("from"), l.get("to")
            lm["from"], lm["to"] = (2 * X - t if t is not None else None), (2 * X - f if f is not None else None)
            lm = {k: v for k, v in lm.items() if v is not None}
        out["ledges"].append(lm)
    for st in half.get("stairs", []):
        out["stairs"].append(st); out["stairs"].append({**st, "from": mp(st["from"]), "to": mp(st["to"])})
    for b in half.get("blocks", []):
        out["blocks"].append(b); out["blocks"].append({**b, "box": mbox(b["box"])})
    for j in half.get("jumppads", []):
        out["jumppads"].append(j); out["jumppads"].append({**j, "at": mp(j["at"]), "target": mp(j["target"])})
    for t in half.get("teleports", []):
        out["teleports"].append(t); out["teleports"].append({**t, "at": mp(t["at"]), "dest": mp(t["dest"]), "angle": mang(t.get("angle", 0))})
    for it in half.get("items", []):
        out["items"].append(it); out["items"].append({**it, "at": mp(it["at"])})
    for sp in half.get("spawns", []):
        out["spawns"].append(sp); out["spawns"].append({**sp, "at": mp(sp["at"]), "angle": mang(sp.get("angle", 0))})
    for lt in half.get("lights", []):
        out["lights"].append(lt); out["lights"].append({**lt, "at": mp(lt["at"])})
    spec = dict(spec); spec.update(out)
    return spec


class Gen:
    def __init__(self, spec, skin, common):
        spec = expand_mirror(spec)
        self.spec, self.skin, self.common = spec, skin or {}, common or {}
        self.W = spec.get("units", {}).get("wall", 32)
        self.tex = {k: v.replace("textures/", "", 1) for k, v in spec.get("skin_textures", {}).items()}
        for k in ("ring_floor", "pad", "tele", "lamp"):
            self.tex.setdefault(k, "pangea_skin/" + k)
        self.classes = dict(DEFAULT_CLASSES)
        self.classes.update(self.common.get("item_classes", {}))
        self.classes.update(self.skin.get("item_classes", {}))
        self.brushes, self.ents, self.n = [], [], 0
        self.voids = []       # (box, kind, meta)
        self.rooms = {}
        for r in spec.get("rooms", []):
            self.rooms[r["id"]] = r
            self.voids.append((self.rb(r), "room", r))
        if spec.get("ring"):
            ring = dict(spec["ring"]); ring.setdefault("id", "ring"); ring["is_ring"] = True
            self.rooms[ring["id"]] = ring
            self.voids.append((self.rb(ring), "ring", ring))
        for h in spec.get("halls", []):
            for seg in self.hall_segments(h):
                self.voids.append(seg)

    @staticmethod
    def rb(r):
        x, y, z, dx, dy, dz = r["box"]
        return (x, y, z, x + dx, y + dy, z + dz)

    def uid(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def ent(self, classname, origin=None, **kv):
        s = ["{", f'"classname" "{classname}"']
        if origin is not None:
            s.append('"origin" "%s %s %s"' % tuple(fmt(c) for c in origin))
        for k, v in kv.items():
            if v is not None:
                s.append(f'"{k}" "{v}"')
        return s

    def point(self, classname, origin, **kv):
        self.ents.append("\n".join(self.ent(classname, origin, **kv) + ["}"]))

    def brush_ent(self, classname, brushes, **kv):
        self.ents.append("\n".join(self.ent(classname, None, **kv) + brushes + ["}"]))

    # ---- halls -> void segments ----
    def hall_segments(self, h):
        pts = [tuple(p) for p in h["path"]]
        width, height = h["width"], h["height"]
        segs = []
        for i, ((ax, ay, az), (bx, by, bz)) in enumerate(zip(pts, pts[1:])):
            if ax != bx and ay != by:
                raise ValueError(f"hall {h.get('id')} segment {i} not axis-aligned")
            lo, hi = min(az, bz), max(az, bz)
            if ax != bx:
                b = (min(ax, bx), ay - width / 2, lo, max(ax, bx), ay + width / 2, hi + height)
            else:
                b = (ax - width / 2, min(ay, by), lo, ax + width / 2, max(ay, by), hi + height)
            meta = {"id": f"{h.get('id','hall')}.{i}", "a": (ax, ay, az), "b": (bx, by, bz), "width": width,
                    "step_h": h.get("step_h", 16), "light": h.get("light", 120)}
            segs.append((b, "hall", meta))
        return segs

    # ---- shell around every void ----
    def build_shells(self):
        W = self.W
        floor, wall, ceil = self.tex["floor"], self.tex["wall"], self.tex["ceil"]
        allv = [v[0] for v in self.voids]
        for box, kind, meta in self.voids:
            x0, y0, z0, x1, y1, z1 = box
            others = [v for v in allv if v is not box]
            sky = kind == "room" and meta.get("open_top")
            ftex = self.tex["ring_floor"] if kind == "ring" else floor
            slabs = [
                ((x0 - W, y0 - W, z0 - W, x1 + W, y1 + W, z0), CAULK, ftex, None),             # floor
                ((x0 - W, y0 - W, z1, x1 + W, y1 + W, z1 + W), (self.tex.get("sky", ceil) if sky else CAULK), None, (None if sky else ceil)),  # ceiling
                ((x1, y0 - W, z0, x1 + W, y1 + W, z1), wall, None, None),                     # east
                ((x0 - W, y0 - W, z0, x0, y1 + W, z1), wall, None, None),                     # west
                ((x0 - W, y1, z0, x1 + W, y1 + W, z1), wall, None, None),                     # north
                ((x0 - W, y0 - W, z0, x1 + W, y0, z1), wall, None, None),                     # south
            ]
            for s, tex, top, bot in slabs:
                for p in subtract_all(s, others):
                    if kind == "ring" and top == ftex:
                        # ring floor: fit the ring texture to the ring's interior box (not to each slab piece)
                        self.brushes.append(box_brush(p, tex, textop=top, texbot=bot, fit="both", fit_faces=("top",), fit_box=box))
                    else:
                        self.brushes.append(box_brush(p, tex, textop=top, texbot=bot))
            if kind == "hall" and meta["a"][2] != meta["b"][2]:
                self.stairs(meta["a"], meta["b"], meta["width"], meta["step_h"])
            if kind == "ring":
                self.brush_ent("pangea_ring", [box_brush(box, TRIGGER)], ring="1")
            if kind in ("room", "ring") and not meta.get("no_lamps"):
                self.lamps(box, others)
            self.auto_light(box, kind, meta)

    def lamps(self, box, others, size=64, thick=8, step=384, below_ceiling=112):
        """Emissive relic panels on room walls near the ceiling (q3map2 surfacelight in the shader)."""
        x0, y0, z0, x1, y1, z1 = box
        zt = z1 - below_ceiling
        if zt - size < z0 + 160:      # low rooms: keep lamps above head height
            zt = min(z1 - 16, z0 + 160 + size)
        lamp = self.tex["lamp"]
        for side in ("north", "south", "east", "west"):
            L = (x1 - x0) if side in ("north", "south") else (y1 - y0)
            n = max(1, int(L // step))
            for i in range(n):
                c = (i + 0.5) * L / n
                if side == "north":   b = (x0 + c - size / 2, y1 - thick, zt - size, x0 + c + size / 2, y1, zt)
                elif side == "south": b = (x0 + c - size / 2, y0, zt - size, x0 + c + size / 2, y0 + thick, zt)
                elif side == "east":  b = (x1 - thick, y0 + c - size / 2, zt - size, x1, y0 + c + size / 2, zt)
                else:                 b = (x0, y0 + c - size / 2, zt - size, x0 + thick, y0 + c + size / 2, zt)
                if any(overlap(b, o) for o in others):
                    continue
                self.brushes.append(box_brush(b, lamp, fit="both", fit_faces=("sides",)))
                self.stats_lamps = getattr(self, "stats_lamps", 0) + 1

    def auto_light(self, box, kind, meta):
        if meta.get("no_auto_light"):
            return
        x0, y0, z0, x1, y1, z1 = box
        color = self.skin.get("light_color")
        if kind == "hall":
            L = max(x1 - x0, y1 - y0); n = max(1, int(L // 320))
            for i in range(n):
                t = (i + 0.5) / n
                px = x0 + (x1 - x0) * (t if x1 - x0 >= y1 - y0 else 0.5)
                py = y0 + (y1 - y0) * (t if y1 - y0 > x1 - x0 else 0.5)
                self.point("light", (px, py, z1 - 24), light=meta.get("light", 120), _color=color)
            return
        area = (x1 - x0) * (y1 - y0)
        inten = meta.get("light", self.skin.get("room_light", 220))
        if area < 250000:
            pts = [((x0 + x1) / 2, (y0 + y1) / 2)]
        else:
            pts = [(x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy) for fx in (0.28, 0.72) for fy in (0.28, 0.72)]
        for px, py in pts:
            self.point("light", (px, py, z1 - 48), light=inten, _color=color)

    # ---- solids ----
    def stairs(self, a, b, width, step_h=16, base=None):
        (ax, ay, az), (bx, by, bz) = a, b
        rise = bz - az
        n = int(round(abs(rise) / step_h))
        if n == 0:
            return
        lo = min(az, bz) if base is None else base
        floor = self.tex["floor"]
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            top = az + rise * ((i + 1) / n if rise > 0 else i / n)
            if top - lo < 1:
                continue
            if ax != bx:
                sx0, sx1 = ax + (bx - ax) * t0, ax + (bx - ax) * t1
                bx0, bx1, by0, by1 = min(sx0, sx1), max(sx0, sx1), ay - width / 2, ay + width / 2
            else:
                sy0, sy1 = ay + (by - ay) * t0, ay + (by - ay) * t1
                by0, by1, bx0, bx1 = min(sy0, sy1), max(sy0, sy1), ax - width / 2, ax + width / 2
            self.brushes.append(box_brush((bx0, by0, lo - self.W, bx1, by1, top), self.tex.get("trim", self.tex["wall"]), textop=floor, texbot=CAULK))

    def build_solids(self):
        floor, wall = self.tex["floor"], self.tex["wall"]
        trim = self.tex.get("trim", wall)
        for l in self.spec.get("ledges", []):
            x0, y0, z0, x1, y1, z1 = self.rb(self.rooms[l["room"]])
            z, w, th = l["z"], l["width"], l.get("thick", 32)
            side = l["side"]
            if side in ("north", "south"):
                a0, a1 = l.get("from", x0), l.get("to", x1)
                yy0, yy1 = (y1 - w, y1) if side == "north" else (y0, y0 + w)
                self.brushes.append(box_brush((a0, yy0, z - th, a1, yy1, z), trim, textop=floor, fit="vertical", fit_faces=("sides",), size=(FIT_TEX, TRIM_H)))
            else:
                a0, a1 = l.get("from", y0), l.get("to", y1)
                xx0, xx1 = (x1 - w, x1) if side == "east" else (x0, x0 + w)
                self.brushes.append(box_brush((xx0, a0, z - th, xx1, a1, z), trim, textop=floor, fit="vertical", fit_faces=("sides",), size=(FIT_TEX, TRIM_H)))
        for s in self.spec.get("stairs", []):
            self.stairs(tuple(s["from"]), tuple(s["to"]), s["width"], s.get("step_h", 16), s.get("base"))
        for bk in self.spec.get("blocks", []):
            x, y, z, dx, dy, dz = bk["box"]
            t = self.tex.get(bk.get("tex", "wall"), wall)
            self.brushes.append(box_brush((x, y, z, x + dx, y + dy, z + dz), t, textop=floor))

    # ---- entities ----
    def build_entities(self):
        trim = self.tex.get("trim", self.tex["wall"])
        for jp in self.spec.get("jumppads", []):
            x, y, z = jp["at"]; s = jp.get("size", 64); name = self.uid("jp")
            self.brush_ent("trigger_push", [box_brush((x - s / 2, y - s / 2, z, x + s / 2, y + s / 2, z + 16), TRIGGER)], target=name)
            self.point("target_position", tuple(jp["target"]), targetname=name)
            self.brushes.append(box_brush((x - s / 2, y - s / 2, z - 8, x + s / 2, y + s / 2, z), trim, textop=self.tex["pad"], fit="both", fit_faces=("top",)))
        for tp in self.spec.get("teleports", []):
            x, y, z = tp["at"]; s = tp.get("size", 64); h = tp.get("height", 96); name = self.uid("tp")
            self.brush_ent("trigger_teleport", [box_brush((x - s / 2, y - s / 2, z, x + s / 2, y + s / 2, z + h), TRIGGER)], target=name)
            self.point("misc_teleporter_dest", tuple(tp["dest"]), targetname=name, angle=tp.get("angle", 0))
            self.brushes.append(box_brush((x - s / 2, y - s / 2, z - 8, x + s / 2, y + s / 2, z), trim, textop=self.tex["tele"], fit="both", fit_faces=("top",)))
        for it in self.spec.get("items", []):
            cls = self.classes.get(it["kind"], it["kind"])
            x, y, z = it["at"]; n = it.get("n", 1); sp = it.get("spread", 40); along = it.get("along", "x")
            for i in range(n):
                off = (i - (n - 1) / 2) * sp
                self.point(cls, (x + (off if along == "x" else 0), y + (off if along == "y" else 0), z + 24), wait=it.get("wait"))  # item bbox is +-15: keep it clear of the floor
        for s in self.spec.get("spawns", []):
            x, y, z = s["at"]
            self.point("info_player_deathmatch", (x, y, z + 25), angle=s.get("angle", 0), ring=("1" if s.get("ring") else None))
        for lt in self.spec.get("lights", []):
            self.point("light", tuple(lt["at"]), light=lt.get("light", 200), _color=lt.get("color"))
        im = self.spec.get("intermission")
        if im:
            self.point("info_player_intermission", tuple(im["at"]), angle=im.get("angle", 0))

    def render(self):
        ws = {"message": self.spec.get("title", self.spec["name"]),
              "ambient": str(self.skin.get("ambient", self.spec.get("ambient", 6))),
              "_lightmapscale": "0.5", "gridsize": "64 64 128",
              "_pangea_archetype": self.spec["name"]}
        out = ["{", '"classname" "worldspawn"'] + [f'"{k}" "{v}"' for k, v in ws.items()] + self.brushes + ["}"] + self.ents
        return "\n".join(out) + "\n"

    def generate(self):
        self.build_shells()
        self.build_solids()
        self.build_entities()
        return self.render()

    def stats(self):
        return {"voids": len(self.voids), "brushes": len(self.brushes), "entities": len(self.ents), "lamps": getattr(self, "stats_lamps", 0)}


def layout_png(spec, path):
    spec = expand_mirror(spec)
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("pillow missing, no png", file=sys.stderr); return
    rooms = list(spec.get("rooms", [])) + ([dict(spec["ring"], id="ring")] if spec.get("ring") else [])
    xs = [r["box"][0] for r in rooms] + [r["box"][0] + r["box"][3] for r in rooms]
    ys = [r["box"][1] for r in rooms] + [r["box"][1] + r["box"][4] for r in rooms]
    for h in spec.get("halls", []):
        for p in h["path"]:
            xs.append(p[0]); ys.append(p[1])
    minx, maxx, miny, maxy = min(xs) - 128, max(xs) + 128, min(ys) - 128, max(ys) + 128
    sc = 0.5
    W, H = int((maxx - minx) * sc), int((maxy - miny) * sc)
    img = Image.new("RGB", (W, H), (24, 24, 28)); d = ImageDraw.Draw(img)
    P = lambda x, y: ((x - minx) * sc, (maxy - y) * sc)
    for h in spec.get("halls", []):
        pts = [P(p[0], p[1]) for p in h["path"]]
        d.line(pts, fill=(70, 120, 70), width=int(h["width"] * sc), joint="curve")
        d.text(pts[0], f"{h.get('id','hall')} z{h['path'][0][2]}->{h['path'][-1][2]}", fill=(180, 255, 180))
    for r in rooms:
        x, y, z, dx, dy, dz = r["box"]
        d.rectangle([P(x, y + dy), P(x + dx, y)], outline=(200, 200, 200), width=2)
        d.text((P(x, y + dy)[0] + 4, P(x, y + dy)[1] + 4), f"{r['id']} z{z}..{z+dz}", fill=(230, 230, 230))
    for l in spec.get("ledges", []):
        r = next(rr for rr in rooms if rr["id"] == l["room"]); x, y, z, dx, dy, dz = r["box"]; w = l["width"]
        if l["side"] in ("north", "south"):
            a0, a1 = l.get("from", x), l.get("to", x + dx)
            yy0, yy1 = (y + dy - w, y + dy) if l["side"] == "north" else (y, y + w)
            d.rectangle([P(a0, yy1), P(a1, yy0)], fill=(70, 90, 140)); d.text(P(a0 + 4, yy1 - 4), f"z{l['z']}", fill=(160, 180, 255))
        else:
            a0, a1 = l.get("from", y), l.get("to", y + dy)
            xx0, xx1 = (x + dx - w, x + dx) if l["side"] == "east" else (x, x + w)
            d.rectangle([P(xx0, a1), P(xx1, a0)], fill=(70, 90, 140)); d.text(P(xx0 + 4, a1 - 4), f"z{l['z']}", fill=(160, 180, 255))
    for s in spec.get("stairs", []):
        d.line([P(*s["from"][:2]), P(*s["to"][:2])], fill=(220, 160, 60), width=int(s["width"] * sc))
        d.text(P(*s["from"][:2]), f"stairs z{s['from'][2]}->{s['to'][2]}", fill=(255, 200, 120))
    for bk in spec.get("blocks", []):
        x, y, z, dx, dy, dz = bk["box"]; d.rectangle([P(x, y + dy), P(x + dx, y)], fill=(110, 110, 120))
    for jp in spec.get("jumppads", []):
        d.line([P(*jp["at"][:2]), P(*jp["target"][:2])], fill=(255, 120, 255), width=2)
        d.ellipse([P(jp["at"][0] - 24, jp["at"][1] + 24), P(jp["at"][0] + 24, jp["at"][1] - 24)], outline=(255, 120, 255), width=2)
    for tp in spec.get("teleports", []):
        d.line([P(*tp["at"][:2]), P(*tp["dest"][:2])], fill=(120, 220, 255), width=2)
    colors = {"carapace": (255, 60, 60), "spring": (60, 120, 255), "hide": (255, 220, 60), "scrap": (255, 240, 160),
              "water": (120, 200, 255), "fruit": (120, 255, 120), "campfire": (255, 140, 40), "spear": (200, 160, 120)}
    for it in spec.get("items", []):
        c = colors.get(it["kind"], (200, 200, 200)); x, y = it["at"][:2]
        d.ellipse([P(x - 14, y + 14), P(x + 14, y - 14)], fill=c)
        d.text(P(x + 16, y + 16), f"{it['kind']}{'x' + str(it['n']) if it.get('n', 1) > 1 else ''} z{it['at'][2]}", fill=c)
    for sp in spec.get("spawns", []):
        x, y = sp["at"][:2]; a = math.radians(sp.get("angle", 0))
        d.ellipse([P(x - 10, y + 10), P(x + 10, y - 10)], outline=(255, 255, 255), width=2)
        d.line([P(x, y), P(x + 40 * math.cos(a), y + 40 * math.sin(a))], fill=(255, 255, 255), width=2)
    img.save(path)
    print(f"layout png: {path} ({W}x{H})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archetype")
    ap.add_argument("--skin", default="relic")
    ap.add_argument("--skins-dir")
    ap.add_argument("--common")
    ap.add_argument("-o", "--out")
    ap.add_argument("--png")
    a = ap.parse_args()
    spec = yaml.safe_load(open(a.archetype, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.archetype))
    skins_dir = a.skins_dir or os.path.join(base, "..", "skins")
    sp = os.path.join(skins_dir, a.skin, "skin.yaml")
    skin = yaml.safe_load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
    cp = a.common or os.path.join(base, "common.yaml")
    common = yaml.safe_load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    g = Gen(spec, skin, common)
    text = g.generate().replace("pangea_skin/", f"pangea/{a.skin}/")
    out = a.out or f"pangea_{spec['name']}_{a.skin}.map"
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(f"wrote {out}: {g.stats()}")
    # .arena passport (ioq3 UI format + Pangea keys), next to scripts/
    bsp = os.path.splitext(os.path.basename(out))[0]
    rules = spec.get("rules", {})
    modes = rules.get("modes", [])
    q3types = " ".join(t for t, ok in (("tourney", "honor" in modes or "fists" in modes or "ranged" in modes),
                                       ("ffa", "brawl" in modes), ("team", "team" in modes)) if ok) or "ffa"
    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(out)), "..", "scripts")
    if os.path.isdir(scripts_dir):
        pmin, pmax = rules.get("players", [2, 8])
        arena = ["{", f'map "{bsp}"', f'longname "{spec.get("title", spec["name"])}"', f'type "{q3types}"',
                 f'pangea_archetype "{spec["name"]}"', f'pangea_skin "{a.skin}"', f'pangea_modes "{",".join(modes)}"',
                 f'pangea_players "{pmin}-{pmax}"', f'pangea_ring "{1 if rules.get("ring") else 0}"',
                 f'pangea_connectivity "{spec.get("connectivity", "")}"', "}"]
        ap = os.path.join(scripts_dir, bsp + ".arena")
        open(ap, "w", encoding="utf-8", newline="\n").write("\n".join(arena) + "\n")
        print(f"wrote {ap}")
    if a.png:
        layout_png(spec, a.png)


if __name__ == "__main__":
    main()
