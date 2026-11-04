#!/usr/bin/env python3
# Pangea Arena — assemble W5 preview sheets from preview.py tiles (system Python + PIL).
#   python3 tools/weapons/sheets.py <tiles_dir> docs/weapons/preview
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

TILES, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
man = json.load(open(os.path.join(TILES, "manifest.json")))
BG = (22, 18, 15)
INK = (226, 182, 116)
DIM = (150, 128, 100)


def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


F, FS, FT = font(22), font(15), font(30)


def im(name, size=None):
    i = Image.open(os.path.join(TILES, name + ".png")).convert("RGB")
    return i.resize(size, Image.LANCZOS) if size else i


def label(d, xy, text, f=FS, fill=INK):
    x, y = xy
    d.text((x + 1, y + 1), text, font=f, fill=(0, 0, 0))
    d.text((x, y), text, font=f, fill=fill)


def header(w, title, sub):
    img = Image.new("RGB", (w, 70), BG)
    d = ImageDraw.Draw(img)
    label(d, (16, 8), title, FT)
    label(d, (18, 44), sub, FS, DIM)
    return img


def stack(parts):
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts)
    out = Image.new("RGB", (w, h), BG)
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height
    return out


TITLES = {"fists": "Кулаки — обмотки", "club": "Палица с голышом", "spear": "Копьё, кремнёвый лист",
          "atlatl": "Копьеметалка (левая рука)", "sling": "Плетёная праща", "bow": "Тисовый лук",
          "torch": "Смоляной факел", "shield": "Круглый щит из шкуры"}

# weapons ------------------------------------------------------------------------------
rows = [header(1440, "Pangea Arena — оружие порога «Пещера»",
               "3/4 на камне · вид от 1-го лица (руки medium, человек) · 4 росписи охрой")]
for mid, t in man.get("weapons", {}).items():
    row = Image.new("RGB", (1440, 360 + 34), BG)
    d = ImageDraw.Draw(row)
    label(d, (14, 6), "%s  ·  %s  ·  %s" % (mid, TITLES.get(mid, ""),
                                           ("%d треуг." % t["tris"]) if t["tris"] else "без своей геометрии"), F)
    row.paste(im(t["34"]), (0, 34))
    row.paste(im(t["fp"]), (480, 34))
    for k, p in enumerate(t["paint"]):
        row.paste(im(p, (240, 180)), (960 + (k % 2) * 240, 34 + (k // 2) * 180))
        label(d, (966 + (k % 2) * 240, 38 + (k // 2) * 180),
              "%d %s" % (k + 1, ["полосы", "точки", "ладонь", "зигзаг"][k]))
    rows.append(row)
stack(rows).save(os.path.join(OUT, "sheet-weapons.png"), optimize=True)

# projectiles --------------------------------------------------------------------------
PT = {"proj_stone1": "голыш 1", "proj_stone2": "голыш 2", "proj_stone3": "голыш 3",
      "proj_stone4": "голыш 4", "proj_arrow": "стрела", "proj_arrow_fire": "огненная стрела",
      "proj_bola": "бола", "proj_brand": "головня", "proj_boulder": "валун голиафа",
      "item_quiver": "колчан (пикап)", "item_stones": "кучка голышей (пикап)"}
items = list(man.get("projectiles", {}).items())
cols = 4
g = Image.new("RGB", (cols * 360, ((len(items) + cols - 1) // cols) * 270), BG)
d = ImageDraw.Draw(g)
for i, (mid, t) in enumerate(items):
    x, y = (i % cols) * 360, (i // cols) * 270
    g.paste(im(t["tile"]), (x, y))
    label(d, (x + 10, y + 8), "%s · %s · %d треуг." % (mid, PT.get(mid, ""), t["tris"]))
stack([header(cols * 360, "Снаряды и предметы", "рендер из MD3 пака, 3/4 на камне"), g]).save(
    os.path.join(OUT, "sheet-projectiles.png"), optimize=True)

# hands --------------------------------------------------------------------------------
b = man.get("builds", [])
top = Image.new("RGB", (3 * 480, 2 * 360), BG)
d = ImageDraw.Draw(top)
order = ["small", "medium", "large"]
for name, build, pose in b:
    x = order.index(build) * 480
    y = 0 if pose == "fist" else 360
    top.paste(im(name), (x, y))
    label(d, (x + 10, y + 8), "%s · %s" % (build, pose), F)
sk = man.get("skins", [])
cols = 5
bottom = Image.new("RGB", (cols * 288, ((len(sk) + cols - 1) // cols) * 216), BG)
d = ImageDraw.Draw(bottom)
for i, (name, race, build) in enumerate(sk):
    x, y = (i % cols) * 288, (i // cols) * 216
    t = im(name)
    w, h = t.size
    bottom.paste(t.crop((int(w * 0.12), int(h * 0.38), int(w * 0.88), h)).resize((288, 216), Image.LANCZOS),
                 (x, y))
    label(d, (x + 8, y + 192), "%s · %s" % (race, build))
stack([header(1440, "Руки от 1-го лица: 3 комплекции и 13 народов",
              "верх: кулаки и хват палицы (гном / человек / голиаф) · низ: обряд «ладони чашей», кожа по народу"),
       top, bottom]).save(os.path.join(OUT, "sheet-hands.png"), optimize=True)
print("SHEETS", OUT)
