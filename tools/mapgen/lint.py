#!/usr/bin/env python3
"""Lint a Pangea archetype YAML against the competitive-design rules (research-arena-maps-pangea.md §2.3).

Usage: python lint.py content/pangea/archetypes/depth.yaml   -> exit 1 on errors
"""
import math, sys
import yaml


def inside(p, box):
    x, y, z = p
    x0, y0, z0, x1, y1, z1 = box
    return x0 <= x <= x1 and y0 <= y <= y1 and z0 - 1 <= z <= z1


def rb(r):
    x, y, z, dx, dy, dz = r["box"]
    return (x, y, z, x + dx, y + dy, z + dz)


def hall_boxes(h):
    out = []
    pts = [tuple(p) for p in h["path"]]
    w, hh = h["width"], h["height"]
    for (ax, ay, az), (bx, by, bz) in zip(pts, pts[1:]):
        lo, hi = min(az, bz), max(az, bz)
        if ax != bx:
            out.append((min(ax, bx), ay - w / 2, lo, max(ax, bx), ay + w / 2, hi + hh))
        else:
            out.append((ax - w / 2, min(ay, by), lo, ax + w / 2, max(ay, by), hi + hh))
    return out


def main(path):
    spec = yaml.safe_load(open(path, encoding="utf-8"))
    rules = spec.get("rules", {})
    errors, warns = [], []
    voids = {r["id"]: rb(r) for r in spec.get("rooms", [])}
    if spec.get("ring"):
        voids["ring"] = rb(spec["ring"])
    for h in spec.get("halls", []):
        for i, b in enumerate(hall_boxes(h)):
            voids[f"{h.get('id','hall')}.{i}"] = b

    def where(p):
        return [k for k, b in voids.items() if inside(p, b)]

    items = spec.get("items", [])
    kinds = {}
    for it in items:
        kinds.setdefault(it["kind"], []).append(it)
    for kind in ("carapace", "spring", "hide"):
        want = rules.get(kind)
        if want is not None and sum(i.get("n", 1) for i in kinds.get(kind, [])) != want:
            errors.append(f"{kind}: want {want}, have {sum(i.get('n',1) for i in kinds.get(kind, []))}")
    if kinds.get("carapace") and kinds.get("spring"):
        ca, sp = where(kinds["carapace"][0]["at"]), where(kinds["spring"][0]["at"])
        if not ca or not sp:
            errors.append(f"carapace/spring outside any void: {ca} / {sp}")
        elif set(ca) & set(sp):
            errors.append("carapace and spring share a room")
        d = math.dist(kinds["carapace"][0]["at"], kinds["spring"][0]["at"])
        if d < 700:
            warns.append(f"carapace-spring straight distance {d:.0f} < 700")
    sg = kinds.get("scrap", [])
    if len(sg) > rules.get("scrap_groups_max", 2):
        errors.append(f"scrap groups {len(sg)} > {rules.get('scrap_groups_max', 2)}")
    for g in sg:
        if not 2 <= g.get("n", 1) <= 5:
            errors.append(f"scrap group at {g['at']} has n={g.get('n',1)} (want 2..5)")
    for it in items:
        if not where(it["at"]):
            errors.append(f"item {it['kind']} at {it['at']} is outside all voids")
    spawns = spec.get("spawns", [])
    main_spawns = [s for s in spawns if not s.get("ring")]
    lo, hi = rules.get("spawns", [6, 12])
    if not lo <= len(main_spawns) <= hi:
        errors.append(f"spawns {len(main_spawns)} not in {lo}..{hi}")
    if rules.get("ring") and len([s for s in spawns if s.get("ring")]) < 2:
        errors.append("ring needs >= 2 ring spawns")
    for s in spawns:
        if not where(s["at"]):
            errors.append(f"spawn at {s['at']} outside all voids")
        if kinds.get("carapace"):
            d = math.dist(s["at"], kinds["carapace"][0]["at"])
            if d < rules.get("min_dist_carapace", 512) and not s.get("ring"):
                errors.append(f"spawn {s['at']} is {d:.0f} from carapace (< {rules.get('min_dist_carapace', 512)})")
        if kinds.get("spring"):
            d = math.dist(s["at"], kinds["spring"][0]["at"])
            if d < rules.get("min_dist_spring", 384) and not s.get("ring"):
                errors.append(f"spawn {s['at']} is {d:.0f} from spring (< {rules.get('min_dist_spring', 384)})")
    # per-spawn spacing
    for i, a in enumerate(main_spawns):
        for b in main_spawns[i + 1:]:
            if math.dist(a["at"], b["at"]) < 256:
                warns.append(f"spawns {a['at']} and {b['at']} closer than 256")
    # health budget (vanilla values): water 25, fruit 5
    health = sum(25 * i.get("n", 1) for i in kinds.get("water", [])) + sum(5 * i.get("n", 1) for i in kinds.get("fruit", []))
    if not 100 <= health <= 200:
        warns.append(f"health without spring = {health} (canon 125..175)")
    # chokepoint: at least one hall segment with width <= 128
    if spec.get("connectivity") == "branched" and not any(h["width"] <= 128 for h in spec.get("halls", [])):
        errors.append("branched archetype needs a hall with width <= 128 (chokepoint)")
    for w in warns:
        print("WARN", w)
    for e in errors:
        print("ERROR", e)
    print(f"{path}: {len(errors)} errors, {len(warns)} warnings; voids={len(voids)} items={sum(i.get('n',1) for i in items)} spawns={len(spawns)} health={health}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
