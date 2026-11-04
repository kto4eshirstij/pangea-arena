# Pangea Arena — Blender objects -> MD3 (runs inside Blender). GPLv2+.
#
# Mesh objects are grouped into MD3 surfaces by obj["surface"] (default: the model id);
# every surface gets one shader name. Empties named tag_* become tags (origin + axes).
# Vertices are split wherever position, UV or the corner normal differs.
import os

from mathutils import Matrix

from md3 import md3


def _surfaces(objs, default, shaders):
    groups = {}
    for o in objs:
        if o.type != 'MESH' or o.get("preview_only"):
            continue
        groups.setdefault(o.get("surface") or default, []).append(o)
    out = []
    for name in sorted(groups, key=lambda n: (n != default, n)):
        verts, normals, st, tris, index = [], [], [], [], {}
        for o in groups[name]:
            me = o.data
            me.calc_loop_triangles()
            cn = me.corner_normals
            uvl = me.uv_layers.active
            M = o.matrix_world
            N = M.to_3x3().inverted().transposed()
            for lt in me.loop_triangles:
                tri = []
                for li in lt.loops:
                    vi = me.loops[li].vertex_index
                    uv = tuple(uvl.data[li].uv) if uvl else (0.0, 0.0)
                    n = (N @ cn[li].vector).normalized()
                    key = (o.name, vi, round(uv[0], 5), round(uv[1], 5),
                           round(n.x, 3), round(n.y, 3), round(n.z, 3))
                    k = index.get(key)
                    if k is None:
                        k = index[key] = len(verts)
                        verts.append(tuple(M @ me.vertices[vi].co))
                        normals.append(tuple(n))
                        st.append((uv[0], 1.0 - uv[1]))
                    tri.append(k)
                tris.append(tuple(tri))
        out.append({"name": name, "shader": shaders.get(name, shaders.get("*", "")),
                    "verts": verts, "normals": normals, "st": st, "tris": tris})
    return out


def tag_dict(name, m):
    m = Matrix(m)
    r = m.to_3x3().normalized()
    return {"name": name, "origin": tuple(m.translation),
            "axis": (tuple(r.col[0]), tuple(r.col[1]), tuple(r.col[2]))}


def export(path, qpath, objs, default_surface, shaders, extra_tags=None):
    """Write `objs` to `path` (qpath = name inside the pak). Returns stats dict."""
    surfaces = _surfaces(objs, default_surface, shaders)
    tags = [tag_dict(o.name, o.matrix_world) for o in objs
            if o.type == 'EMPTY' and o.name.startswith("tag_")]
    for name, m in sorted((extra_tags or {}).items()):
        tags.append(tag_dict(name, m))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    md3.write(path, qpath, surfaces, tags)
    return {s["name"]: (len(s["verts"]), len(s["tris"])) for s in surfaces}
