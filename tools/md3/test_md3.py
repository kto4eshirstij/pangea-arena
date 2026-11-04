# Round-trip test for tools/md3/md3.py:  python3 tools/md3/test_md3.py [some_real.md3 ...]
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md3  # noqa: E402


def main():
    verts = [(x, y, z) for x in (-1.5, 1.5) for y in (-2, 2) for z in (-3, 3)]
    normals = [tuple(c / math.sqrt(3) * (1 if c > 0 else 1) for c in v) for v in verts]
    normals = [(n[0] / abs(n[0]) / math.sqrt(3), n[1] / abs(n[1]) / math.sqrt(3), n[2] / abs(n[2]) / math.sqrt(3)) for n in normals]
    st = [(i / 8.0, 1 - i / 8.0) for i in range(8)]
    tris = [(0, 1, 2), (1, 3, 2), (4, 6, 5), (5, 6, 7)]
    tags = [{"name": "tag_flash", "origin": (3.0, 0.5, -1.25),
             "axis": ((0, 1, 0), (-1, 0, 0), (0, 0, 1))}]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.md3")
        md3.write(p, "models/test/t.md3",
                  [{"name": "t", "shader": "models/test/t.tga", "verts": verts, "normals": normals,
                    "st": st, "tris": tris}], tags)
        m = md3.read(p)
    s = m["surfaces"][0]
    assert m["version"] == 15 and m["frames"] == 1
    assert s["tris"] == tris, s["tris"]
    assert all(abs(a - b) < 1 / 64 for v, w in zip(s["verts"], verts) for a, b in zip(v, w))
    assert all(abs(a - b) < 0.03 for v, w in zip(s["normals"], normals) for a, b in zip(v, w)), \
        list(zip(s["normals"], normals))
    assert s["st"] == st
    assert m["tags"][0]["name"] == "tag_flash" and m["tags"][0]["origin"] == (3.0, 0.5, -1.25)
    # normal encoder over the sphere
    worst = 0.0
    for i in range(200):
        z = -1 + 2 * (i + 0.5) / 200
        a = i * 2.399963
        r = math.sqrt(1 - z * z)
        n = (r * math.cos(a), r * math.sin(a), z)
        dn = md3.decode_normal(md3.encode_normal(n))
        worst = max(worst, math.acos(max(-1, min(1, sum(p * q for p, q in zip(n, dn))))))
    assert worst < math.radians(1.6), math.degrees(worst)
    print("md3 round-trip OK, worst normal error %.2f deg" % math.degrees(worst))
    for p in sys.argv[1:]:
        print(md3.summary(p))


main()
