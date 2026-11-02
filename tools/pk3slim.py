#!/usr/bin/env python3
"""pk3slim — build a small pk3 with only what the browser client needs for chosen maps.

    tools/pk3slim.py --maps czest1tourney,oa_dm4 [--src content/openarena/baseoa]
                     [--out content/build] [--code code] [--trace content/trace/*.log]

Dependencies are collected from:
  1. the maps: BSP shader and fog lumps, entity keys (model, model2, noise, music),
     levelshot and .arena script;
  2. shader scripts (map, clampMap, animMap, skyParms boxes) of every used shader;
  3. MD3 surface shaders, player .skin files, animation.cfg;
  4. string literals with asset paths in cgame/q3_ui/bg_misc (format strings like
     "sound/player/%s/death1.wav" are expanded for the player models we ship);
  5. --trace: fs_debug logs of the web client ("FS_FOpenFileRead: <path> (found in ...)")
     and "WARNING: ... not found" lines.

Paths are resolved like ioq3 does it: later pk3 files override earlier ones, and
missing images/sounds are looked up with alternative extensions
(.tga/.jpg/.png, .wav/.ogg). Output: <out>/arena-oa-<sha8>.pk3 and <out>/missing.txt.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import io
import os
import re
import struct
import sys
import zipfile

IMAGE_EXT = (".tga", ".jpg", ".png")
SOUND_EXT = (".wav", ".ogg")

# Player models we ship: default (cgame DEFAULT_MODEL) + the bots the manager adds.
PLAYER_MODELS = ["sarge", "grism", "kyonshi"]

# Whole directories the HUD reads by building names at run time (small).
WHOLE_DIRS = [
    "gfx/2d/", "gfx/damage/", "gfx/misc/", "sprites/", "fonts/", "icons/",
    "models/weaphits/", "models/gibs/", "sound/feedback/", "sound/weapons/", "sound/items/", "sound/misc/",
]
# Never: not used by the browser client (bots, CTF/team, music, cinematics, other maps)
SKIP_PREFIXES = ["botfiles/", "music/", "video/", "levelshots/", "maps/", "sound/teamplay/",
                 "models/flags/", "models/flag2/", "models/powerups/obelisk/", "team_icon/", "ui/"]
# Player skins we need: default + team colours for later team modes are not needed now
PLAYER_SKINS = ("default",)


class Vfs:
    """Merged view of all pk3 files, ioq3 priority (later sorted name wins)."""

    def __init__(self, src: str):
        self.files: dict[str, tuple[str, str]] = {}  # lower path -> (pk3, real name)
        self.zips: dict[str, zipfile.ZipFile] = {}
        for pk3 in sorted(glob.glob(os.path.join(src, "*.pk3"))):
            z = zipfile.ZipFile(pk3)
            self.zips[pk3] = z
            for info in z.infolist():
                if info.is_dir():
                    continue
                self.files[info.filename.lower()] = (pk3, info.filename)
        if not self.files:
            sys.exit(f"no pk3 files in {src}")

    def has(self, path: str) -> bool:
        return path.lower() in self.files

    def read(self, path: str) -> bytes:
        pk3, name = self.files[path.lower()]
        return self.zips[pk3].read(name)

    def size(self, path: str) -> int:
        pk3, name = self.files[path.lower()]
        return self.zips[pk3].getinfo(name).file_size

    def resolve(self, path: str) -> str | None:
        """Real path for a reference, trying alternative extensions."""
        p = path.replace("\\", "/").strip().lstrip("/").lower()
        if not p:
            return None
        if p in self.files:
            return p
        base, ext = os.path.splitext(p)
        alts = IMAGE_EXT if ext in IMAGE_EXT or ext == "" else SOUND_EXT if ext in SOUND_EXT else ()
        for e in alts:
            if base + e in self.files:
                return base + e
        return None

    def listdir(self, prefix: str) -> list[str]:
        return [p for p in self.files if p.startswith(prefix)]


# ---------------------------------------------------------------- shaders

def parse_shader_scripts(vfs: Vfs) -> tuple[dict[str, str], dict[str, str]]:
    """shader name -> body text of ALL its definitions (several .shader files may define the
    same name and we cannot cheaply tell which one the engine picks); name -> first script file."""
    bodies: dict[str, str] = {}
    owner: dict[str, str] = {}
    for path in sorted(p for p in vfs.files if p.startswith("scripts/") and p.endswith(".shader")):
        text = vfs.read(path).decode("latin-1")
        text = re.sub(r"//[^\n]*", "", text)
        i, n = 0, len(text)
        while i < n:
            m = re.compile(r"\s*([^\s{}]+)\s*\{").match(text, i)
            if not m:
                j = text.find("{", i)
                if j < 0:
                    break
                i = j
                m = None
            name = m.group(1).lower() if m else None
            start = (m.end() if m else i + 1)
            depth, k = 1, start
            while k < n and depth:
                if text[k] == "{":
                    depth += 1
                elif text[k] == "}":
                    depth -= 1
                k += 1
            if name:
                bodies[name] = bodies.get(name, "") + "\n" + text[start:k - 1]
                owner.setdefault(name, path)
            i = k
    return bodies, owner


def shader_images(body: str) -> list[str]:
    out: list[str] = []
    for line in body.splitlines():
        t = line.strip().split()
        if not t:
            continue
        key = t[0].lower()
        if key in ("map", "clampmap") and len(t) > 1 and not t[1].startswith("$"):
            out.append(t[1])
        elif key == "animmap" and len(t) > 2:
            out.extend(x for x in t[2:])
        elif key == "skyparms" and len(t) > 1:
            for box in (t[1], t[3] if len(t) > 3 else "-"):
                if box != "-":
                    out.extend(f"{box}_{s}.tga" for s in ("rt", "bk", "lf", "ft", "up", "dn"))
        elif key in ("qer_editorimage",):
            continue
    return out


# ---------------------------------------------------------------- file formats

def bsp_refs(data: bytes) -> tuple[list[str], list[str], str]:
    """(shader names, fog shader names, entity text) from a Q3 BSP (IBSP v46)."""
    ident, version = struct.unpack_from("<4si", data, 0)
    if ident != b"IBSP":
        raise ValueError("not an IBSP file")
    lumps = [struct.unpack_from("<ii", data, 8 + i * 8) for i in range(17)]
    ofs, ln = lumps[0]
    entities = data[ofs:ofs + ln].decode("latin-1").rstrip("\0")
    ofs, ln = lumps[1]
    shaders = [data[o:o + 64].split(b"\0")[0].decode("latin-1") for o in range(ofs, ofs + ln, 72)]
    ofs, ln = lumps[12]
    fogs = [data[o:o + 64].split(b"\0")[0].decode("latin-1") for o in range(ofs, ofs + ln, 72)]
    return shaders, fogs, entities


def entity_refs(entities: str) -> list[str]:
    out = []
    for key, val in re.findall(r'"([^"]+)"\s+"([^"]*)"', entities):
        k = key.lower()
        if k in ("model", "model2") and val and not val.startswith("*"):
            out.append(val)
        elif k == "noise" and val and not val.startswith("*"):
            out.append(val)
        elif k == "music":
            out.extend(val.split())
    return out


def md3_shaders(data: bytes) -> list[str]:
    if data[:4] != b"IDP3":
        return []
    (num_surfaces,) = struct.unpack_from("<i", data, 84)
    (ofs_surfaces,) = struct.unpack_from("<i", data, 100)
    out = []
    o = ofs_surfaces
    for _ in range(num_surfaces):
        if data[o:o + 4] != b"IDP3":
            break
        num_shaders, = struct.unpack_from("<i", data, o + 76)
        ofs_shaders, = struct.unpack_from("<i", data, o + 92)
        ofs_end, = struct.unpack_from("<i", data, o + 104)
        for s in range(num_shaders):
            name = data[o + ofs_shaders + s * 68:o + ofs_shaders + s * 68 + 64].split(b"\0")[0].decode("latin-1")
            if name:
                out.append(name)
        o += ofs_end
    return out


def skin_refs(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if "," in line:
            v = line.split(",", 1)[1].strip()
            if v and not v.startswith("tag_"):
                out.append(v)
    return out


# ---------------------------------------------------------------- code literals

PATH_RE = re.compile(r'"((?:models|sound|gfx|sprites|menu|fonts|textures|icons|botfiles|scripts|music)/[^"\n]+)"')


def code_refs(code_dir: str) -> list[str]:
    out: list[str] = []
    files = glob.glob(os.path.join(code_dir, "cgame", "*.c")) + glob.glob(os.path.join(code_dir, "q3_ui", "*.c")) + \
        [os.path.join(code_dir, "game", "bg_misc.c")]
    for f in files:
        with open(f, encoding="latin-1") as fh:
            for lit in PATH_RE.findall(fh.read()):
                out.extend(expand_format(lit))
    return out


def expand_format(lit: str) -> list[str]:
    if "%" not in lit:
        return [lit]
    res = [lit]
    for spec, values in (("%s", PLAYER_MODELS + ["default"]), ("%i", [str(i) for i in range(10)]),
                         ("%d", [str(i) for i in range(10)]), ("%c", list("0123456789abc"))):
        nxt = []
        for r in res:
            if spec in r:
                nxt.extend(r.replace(spec, v, 1) for v in values)
            else:
                nxt.append(r)
        res = nxt
    # a second %s/%i after the first expansion
    return [r for r in res if "%" not in r]


# ---------------------------------------------------------------- collector

class Collector:
    def __init__(self, vfs: Vfs, bodies: dict[str, str], owner: dict[str, str]):
        self.vfs, self.bodies, self.owner = vfs, bodies, owner
        self.files: set[str] = set()
        self.missing: set[str] = set()
        self.shaders_done: set[str] = set()

    def add_file(self, ref: str, required: bool = True) -> str | None:
        if any(ref.lower().startswith(sp) for sp in SKIP_PREFIXES) and not ref.lower().startswith("maps/"):
            return None
        p = self.vfs.resolve(ref)
        if p is None:
            if required:
                self.missing.add(ref.lower())
            return None
        if p in self.files:
            return p
        self.files.add(p)
        if p.endswith(".md3"):
            for s in md3_shaders(self.vfs.read(p)):
                self.add_shader(s)
        elif p.endswith(".skin"):
            for s in skin_refs(self.vfs.read(p).decode("latin-1")):
                self.add_shader(s)
        return p

    def add_shader(self, name: str) -> None:
        key = os.path.splitext(name.replace("\\", "/").lower())[0] if name.lower().endswith(IMAGE_EXT) else name.replace("\\", "/").lower()
        if key in self.shaders_done or key in ("noshader", ""):
            return
        self.shaders_done.add(key)
        body = self.bodies.get(key)
        if body is None:
            # implicit shader: the image itself
            self.add_file(key, required=not key.startswith("textures/common/"))
            return
        self.files.add(self.owner[key])
        for img in shader_images(body):
            self.add_file(img)

    def add_map(self, name: str) -> None:
        bsp = f"maps/{name}.bsp"
        if not self.vfs.has(bsp):
            sys.exit(f"map {name} not found")
        self.add_file(bsp)
        shaders, fogs, entities = bsp_refs(self.vfs.read(bsp))
        for s in shaders + fogs:
            self.add_shader(s)
        for ref in entity_refs(entities):
            if ref.lower().endswith(".md3"):
                self.add_file(ref)
            else:
                self.add_file(ref, required=True)
        for opt in (f"levelshots/{name}", f"scripts/{name}.arena"):
            self.add_file(opt, required=False)
        for p in self.vfs.listdir(f"maps/{name}/"):   # external lightmaps
            self.add_file(p)

    def add_player(self, model: str) -> None:
        base = f"models/players/{model}/"
        for p in self.vfs.listdir(base):
            rest = p[len(base):]
            if "/" in rest:          # variants in subdirectories (e.g. sarge/classic) — only if a skin points there
                continue
            if p.endswith((".md3", ".cfg")):
                self.add_file(p)
            elif p.endswith(".skin") and any(p.endswith(f"_{s}.skin") for s in PLAYER_SKINS):
                self.add_file(p)
            elif os.path.basename(p).startswith("icon_") and any(s in p for s in PLAYER_SKINS):
                self.add_file(p)
        for p in self.vfs.listdir(f"sound/player/{model}/"):
            self.add_file(p)

    def add_dirs(self, prefixes: list[str]) -> None:
        for d in prefixes:
            for p in self.vfs.listdir(d):
                if any(p.startswith(s) for s in SKIP_PREFIXES):
                    continue
                self.add_file(p)


def trace_refs(paths: list[str]) -> list[str]:
    """Asset paths from web client logs with fs_debug 1."""
    pats = [
        re.compile(r"FS_FOpenFileRead: (\S+) \(found in"),
        re.compile(r"could not find '[^']+' in shader '([^']+)'"),   # R_FindImageFile: take the whole shader
        re.compile(r"could not find '([^']+)'"),
        re.compile(r"Failed to load sound (\S+?)!?$"),
        re.compile(r"Using default sound for (\S+)"),
        re.compile(r"Couldn't find image file '?([^'\s]+)"),
    ]
    out = []
    for f in paths:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for p in pats:          # all patterns: a missing image line gives both the shader and the file
                    m = p.search(line.strip())
                    if m:
                        out.append(m.group(1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--maps", required=True, help="comma separated map names")
    ap.add_argument("--src", default="content/openarena/baseoa")
    ap.add_argument("--out", default="content/build")
    ap.add_argument("--code", default="code")
    ap.add_argument("--trace", nargs="*", default=[], help="fs_debug logs of the web client")
    ap.add_argument("--no-whole-dirs", action="store_true", help="only exact references (for size experiments)")
    ap.add_argument("--report", action="store_true", help="print the biggest files and directories")
    a = ap.parse_args()

    vfs = Vfs(a.src)
    bodies, owner = parse_shader_scripts(vfs)
    c = Collector(vfs, bodies, owner)
    for m in a.maps.split(","):
        c.add_map(m.strip())
    for model in PLAYER_MODELS:
        c.add_player(model)
    for ref in code_refs(a.code):
        if ref.lower().endswith(".md3"):
            c.add_file(ref, required=False)
            stem = ref[:-4]
            for suffix in ("_flash", "_barrel", "_hand"):
                c.add_file(stem + suffix + ".md3", required=False)
        elif "/" in ref and "." in os.path.basename(ref):
            c.add_file(ref, required=False)
        else:
            c.add_shader(ref)
    if not a.no_whole_dirs:
        c.add_dirs(WHOLE_DIRS)
    c.add_file("default.cfg")
    for p in vfs.listdir("scripts/"):          # shader scripts are text and small; the engine parses them all
        if p.endswith(".shader"):
            c.files.add(p)
    for ref in trace_refs(a.trace):
        if ref.lower() in bodies:
            c.add_shader(ref)
        elif c.add_file(ref, required=False) is None:
            c.add_shader(ref)

    os.makedirs(a.out, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(c.files):
            pk3, name = vfs.files[p]
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            data = vfs.read(p)
            # already compressed formats: store
            info.compress_type = zipfile.ZIP_STORED if name.lower().endswith((".jpg", ".png", ".ogg")) else zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    blob = buf.getvalue()
    sha8 = hashlib.sha256(blob).hexdigest()[:8]
    for old in glob.glob(os.path.join(a.out, "arena-oa-*.pk3")):
        os.remove(old)
    out = os.path.join(a.out, f"arena-oa-{sha8}.pk3")
    with open(out, "wb") as fh:
        fh.write(blob)
    with open(os.path.join(a.out, "missing.txt"), "w") as fh:
        fh.write("\n".join(sorted(c.missing)) + ("\n" if c.missing else ""))
    raw = sum(vfs.size(p) for p in c.files)
    print(f"{out}: {len(c.files)} files, {raw / 1e6:.1f} MB raw, {len(blob) / 1e6:.1f} MB pk3; "
          f"{len(c.missing)} missing -> {a.out}/missing.txt")
    if a.report:
        by_dir: dict[str, int] = {}
        for p in c.files:
            d = "/".join(p.split("/")[:2])
            by_dir[d] = by_dir.get(d, 0) + vfs.size(p)
        for d, s in sorted(by_dir.items(), key=lambda x: -x[1])[:25]:
            print(f"  {s / 1e6:7.2f} MB  {d}")


if __name__ == "__main__":
    main()
