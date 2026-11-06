#!/usr/bin/env python3
"""Pack Pangea's own content into content/build/arena-pangea-<sha8>.pk3 + content/pangea/maps/index.json.

    python tools/mapgen/pack.py [--content content/pangea] [--out content/build]

Included: maps/*.bsp|*.aas, scripts/*.shader|*.arena, textures/pangea/**, models/pangea/**, sound/pangea/**,
levelshots/*.jpg, gfx/pangea/**, cfg/*.cfg. Excluded: *.map, *.prt, *.srf, *.layout.png, vm/, archetypes/, skins/.
The pak name sorts after arena-oa-*.pk3, so in the browser (fs_game baseoa) it overrides OpenArena files.
"""
import argparse, glob, hashlib, io, json, os, zipfile
import yaml

INCLUDE_DIRS = ("textures/pangea", "models/pangea", "sound/pangea", "gfx/pangea", "levelshots", "cfg")
INCLUDE_EXT = {"maps": (".bsp", ".aas"), "scripts": (".shader", ".arena")}


def collect(content):
    files = []
    for sub, exts in INCLUDE_EXT.items():
        for f in sorted(glob.glob(os.path.join(content, sub, "*"))):
            if f.lower().endswith(exts):
                files.append(f)
    for d in INCLUDE_DIRS:
        for root, _, names in os.walk(os.path.join(content, d)):
            for n in sorted(names):
                if not n.lower().endswith((".txt", ".md")):
                    files.append(os.path.join(root, n))
    return files


def index(content):
    maps = []
    for yml in sorted(glob.glob(os.path.join(content, "archetypes", "*.yaml"))):
        spec = yaml.safe_load(open(yml, encoding="utf-8"))
        if "name" not in spec:
            continue
        for bsp in sorted(glob.glob(os.path.join(content, "maps", f"pangea_{spec['name']}_*.bsp"))):
            name = os.path.splitext(os.path.basename(bsp))[0]
            skin = name.split("_", 2)[2]
            r = spec.get("rules", {})
            skin_yaml = os.path.join(content, "skins", skin, "skin.yaml")
            sk = yaml.safe_load(open(skin_yaml, encoding="utf-8")) if os.path.exists(skin_yaml) else {}
            maps.append({
                "key": name, "bsp": name,
                "title": f"{spec.get('title', spec['name'])}" if skin == "relic" else f"{sk.get('title_ru', skin)}: {spec.get('title', spec['name'])}",
                "archetype": spec["name"], "skin": skin,
                "craton": sk.get("craton"), "niche": sk.get("niche"),
                "connectivity": spec.get("connectivity"), "modes": r.get("modes", []),
                "players": r.get("players", [2, 8]), "ring": bool(r.get("ring")),
                "no_pits": bool(r.get("no_pits", True)),
                "levelshot": f"levelshots/{name}.jpg" if os.path.exists(os.path.join(content, "levelshots", name + ".jpg")) else None,
                "aas": os.path.exists(os.path.join(content, "maps", name + ".aas")),
                "doc": spec.get("archetype_doc", ""),
            })
    return maps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", default="content/pangea")
    ap.add_argument("--out", default="content/build")
    a = ap.parse_args()
    files = collect(a.content)
    maps = index(a.content)
    os.makedirs(a.out, exist_ok=True)
    idx_path = os.path.join(a.content, "maps", "index.json")
    json.dump({"maps": maps}, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            arc = os.path.relpath(f, a.content).replace(os.sep, "/")
            z.write(f, arc)
        z.write(idx_path, "maps/index.json")
    data = buf.getvalue()
    sha = hashlib.sha256(data).hexdigest()[:8]
    for old in glob.glob(os.path.join(a.out, "arena-pangea-*.pk3")):
        os.remove(old)
    pak = os.path.join(a.out, f"arena-pangea-{sha}.pk3")
    open(pak, "wb").write(data)
    print(f"{pak}: {len(files) + 1} files, {len(data) / 1e6:.1f} MB, {len(maps)} maps in index")
    for m in maps:
        print(f"  {m['bsp']}: {m['title']} [{','.join(m['modes'])}] players {m['players']}")


if __name__ == "__main__":
    main()
