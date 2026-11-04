# Pangea Arena — MD3 (IDP3 v15) writer and reader. GPLv2+. Pure Python (struct), no deps,
# runs both in Blender's Python and the system Python.
#
# Format per code/qcommon/qfiles.h. Conventions of this writer:
#   * static models are 1 frame; tags are per frame;
#   * triangles are written clockwise seen from the front (ioq3 culls GL_FRONT for
#     front-sided shaders), callers pass counter-clockwise (Blender) triangles;
#   * st: t = 1 - v (Blender UV origin bottom-left, Q3 top-left);
#   * normals: lat/lng bytes, angle = byte * 2pi/256 exactly as tr_model.c decodes them.
#
# python3 tools/md3/md3.py <file.md3>  -> prints a summary (surfaces, verts, tris, tags)
import math
import struct
import sys

IDENT = b"IDP3"
VERSION = 15
MAX_QPATH = 64
XYZ_SCALE = 64.0
LIMIT_VERTS = 999       # project limit per surface (engine: 4096)
LIMIT_TRIS = 1999       # project limit per surface (engine: 8192)


def _name(s, n=MAX_QPATH):
    b = s.encode("ascii")
    if len(b) >= n:
        raise ValueError("name too long (%d >= %d): %s" % (len(b), n, s))
    return b + b"\0" * (n - len(b))


def encode_normal(n):
    x, y, z = n
    ln = math.sqrt(x * x + y * y + z * z) or 1.0
    x, y, z = x / ln, y / ln, z / ln
    if abs(x) < 1e-6 and abs(y) < 1e-6:
        return 0 if z > 0 else 128          # lat 0, lng 0 | 128
    lat = int(round(math.atan2(y, x) * 256.0 / (2 * math.pi))) & 0xFF
    lng = int(round(math.acos(max(-1.0, min(1.0, z))) * 256.0 / (2 * math.pi))) & 0xFF
    return (lat << 8) | lng


def decode_normal(v):
    lat = ((v >> 8) & 0xFF) * 2 * math.pi / 256.0
    lng = (v & 0xFF) * 2 * math.pi / 256.0
    return (math.cos(lat) * math.sin(lng), math.sin(lat) * math.sin(lng), math.cos(lng))


def _short(v):
    i = int(round(v * XYZ_SCALE))
    if not -32768 <= i <= 32767:
        raise ValueError("vertex out of MD3 range (+-512 u): %r" % v)
    return i


def write(path, name, surfaces, tags=(), frame_name="frame0"):
    """surfaces: [{name, shader, verts[(x,y,z)], normals[(x,y,z)], st[(s,t)], tris[(a,b,c)]}]
    (tris counter-clockwise, st already in Q3 convention). tags: [{name, origin, axis}] with
    axis = 3 rows (X, Y, Z axis vectors of the tag)."""
    allv = [v for s in surfaces for v in s["verts"]]
    if allv:
        lo = [min(v[i] for v in allv) for i in range(3)]
        hi = [max(v[i] for v in allv) for i in range(3)]
        radius = max(math.sqrt(sum(c * c for c in v)) for v in allv)
    else:
        lo = hi = [0.0, 0.0, 0.0]
        radius = 0.0
    frame = struct.pack("<3f3f3ff16s", *lo, *hi, 0.0, 0.0, 0.0, radius,
                        _name(frame_name, 16))
    tagdata = b""
    for t in tags:
        ax = t["axis"]
        tagdata += _name(t["name"]) + struct.pack("<3f9f", *t["origin"], *ax[0], *ax[1], *ax[2])
    surfdata = b""
    for s in surfaces:
        nv, nt = len(s["verts"]), len(s["tris"])
        if nv > LIMIT_VERTS or nt > LIMIT_TRIS:
            raise ValueError("surface %s too big: %d verts, %d tris" % (s["name"], nv, nt))
        shaders = _name(s["shader"]) + struct.pack("<i", 0)
        tris = b"".join(struct.pack("<3i", a, c, b) for a, b, c in s["tris"])   # -> clockwise
        st = b"".join(struct.pack("<2f", *uv) for uv in s["st"])
        xyzn = b"".join(struct.pack("<3hH", *map(_short, v), encode_normal(n))
                        for v, n in zip(s["verts"], s["normals"]))
        hdr_size = 108
        ofs_sh = hdr_size
        ofs_tri = ofs_sh + len(shaders)
        ofs_st = ofs_tri + len(tris)
        ofs_xyz = ofs_st + len(st)
        ofs_end = ofs_xyz + len(xyzn)
        hdr = IDENT + _name(s["name"]) + struct.pack(
            "<10i", 0, 1, 1, nv, nt, ofs_tri, ofs_sh, ofs_st, ofs_xyz, ofs_end)
        surfdata += hdr + shaders + tris + st + xyzn
    ofs_frames = 108
    ofs_tags = ofs_frames + len(frame)
    ofs_surf = ofs_tags + len(tagdata)
    ofs_end = ofs_surf + len(surfdata)
    header = IDENT + struct.pack("<i", VERSION) + _name(name) + struct.pack(
        "<9i", 0, 1, len(tags), len(surfaces), 0, ofs_frames, ofs_tags, ofs_surf, ofs_end)
    with open(path, "wb") as f:
        f.write(header + frame + tagdata + surfdata)


def read(path):
    """Parse an MD3 (frame 0) -> dict(name, tags, surfaces) with the same fields as write()
    takes (tris returned counter-clockwise again)."""
    with open(path, "rb") as f:
        b = f.read()
    if b[:4] != IDENT:
        raise ValueError("not an MD3: %s" % path)
    ver, = struct.unpack_from("<i", b, 4)
    name = b[8:72].split(b"\0")[0].decode()
    flags, nfr, ntag, nsurf, nskin, ofr, otag, osurf, oend = struct.unpack_from("<9i", b, 72)
    tags = []
    for i in range(ntag):
        o = otag + i * 112
        tname = b[o:o + 64].split(b"\0")[0].decode()
        v = struct.unpack_from("<12f", b, o + 64)
        tags.append({"name": tname, "origin": v[0:3], "axis": (v[3:6], v[6:9], v[9:12])})
    surfaces = []
    o = osurf
    for i in range(nsurf):
        sname = b[o + 4:o + 68].split(b"\0")[0].decode()
        (sflags, snfr, nsh, nv, nt, otri, osh, ost, oxyz, send) = struct.unpack_from("<10i", b, o + 68)
        shader = b[o + osh:o + osh + 64].split(b"\0")[0].decode()
        tris = [struct.unpack_from("<3i", b, o + otri + 12 * k) for k in range(nt)]
        tris = [(a, c, bb) for a, bb, c in tris]
        st = [struct.unpack_from("<2f", b, o + ost + 8 * k) for k in range(nv)]
        verts, normals = [], []
        for k in range(nv):
            x, y, z, n = struct.unpack_from("<3hH", b, o + oxyz + 8 * k)
            verts.append((x / XYZ_SCALE, y / XYZ_SCALE, z / XYZ_SCALE))
            normals.append(decode_normal(n))
        surfaces.append({"name": sname, "shader": shader, "verts": verts, "normals": normals,
                         "st": st, "tris": tris})
        o += send
    return {"name": name, "version": ver, "frames": nfr, "tags": tags, "surfaces": surfaces}


def summary(path):
    m = read(path)
    lines = ["%s  v%d frames=%d" % (m["name"], m["version"], m["frames"])]
    for s in m["surfaces"]:
        lines.append("  surface %-8s %4d verts %4d tris  %s" % (s["name"], len(s["verts"]),
                                                             len(s["tris"]), s["shader"]))
    for t in m["tags"]:
        lines.append("  %-14s (%.2f %.2f %.2f)" % (t["name"], *t["origin"]))
    return "\n".join(lines)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(summary(p))
