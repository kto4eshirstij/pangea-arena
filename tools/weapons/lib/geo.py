# Pangea Arena — low-poly procedural primitives for Blender (bmesh). GPLv2+.
# Units: 1 Blender unit = 1 Q3 unit (~1 inch). Axes as Q3: +X forward, +Y left, +Z up.
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

CM = 0.3937  # centimetres -> Q3 units


def cm(x):
    return x * CM


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'NONE'
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    return sc


def rot(x=0.0, y=0.0, z=0.0):
    """Rotation matrix from Euler degrees (XYZ)."""
    return Euler((math.radians(x), math.radians(y), math.radians(z)), 'XYZ').to_matrix()


def finish(name, bm, mat, sharp=60.0, smooth=True, surface=None, matrix=None, flip=False):
    """Triangulate, set smoothing (edges sharper than `sharp` degrees split), link object."""
    if matrix is not None:
        bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if flip:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    lim = math.radians(sharp)
    for f in bm.faces:
        f.smooth = smooth
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(0.0) < lim
        else:
            e.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if mat is not None:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if surface:
        ob["surface"] = surface
    return ob


def _jitter(bm, amount, seed, keep=()):
    if amount <= 0:
        return
    rnd = random.Random(seed)
    for v in bm.verts:
        if v.index in keep:
            continue
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * amount


def _frames(pts, closed, up):
    n = len(pts)
    T = []
    for i in range(n):
        if closed:
            a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        T.append((b - a).normalized())
    if up is None:
        up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((0, 1, 0))
    N = T[0].cross(Vector(up)).normalized()
    out = []
    for i in range(n):
        N = (N - N.dot(T[i]) * T[i]).normalized()
        out.append((T[i], N, T[i].cross(N)))
    return out


def tube(name, pts, radii, sides=6, mat=None, caps=(True, True), flat=(1.0, 1.0),
         closed=False, twist=0.0, up=None, jitter=0.0, seed=0, **kw):
    """Loft a polygonal cross-section along a polyline. radius 0 at an end -> pointed tip.
    flat=(a, b) scales the cross-section along frame N / B (N = T x up)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    if not hasattr(radii, "__len__"):
        radii = [radii] * n
    frames = _frames(pts, closed, up)
    bm = bmesh.new()
    rings = []
    for i, (p, (T, N, B)) in enumerate(zip(pts, frames)):
        r = radii[i]
        fl = flat[i] if isinstance(flat, list) else flat
        if r <= 1e-6:
            rings.append([bm.verts.new(p)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides + twist
            ring.append(bm.verts.new(p + N * (math.cos(a) * r * fl[0]) + B * (math.sin(a) * r * fl[1])))
        rings.append(ring)
    segs = n if closed else n - 1
    for i in range(segs):
        ra, rb = rings[i], rings[(i + 1) % n]
        if len(ra) == 1 and len(rb) == 1:
            continue
        if len(ra) == 1 or len(rb) == 1:
            pole, ring = (ra[0], rb) if len(ra) == 1 else (rb[0], ra)
            for k in range(sides):
                bm.faces.new((pole, ring[k], ring[(k + 1) % sides]))
            continue
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new((ra[k], ra[k2], rb[k2], rb[k]))
    if not closed:
        if caps[0] and len(rings[0]) > 2:
            bm.faces.new(rings[0])
        if caps[1] and len(rings[-1]) > 2:
            bm.faces.new(rings[-1])
    _jitter(bm, jitter, seed)
    return finish(name, bm, mat, **kw)


def ring_path(center, radius, n, axis='X', rx=None, ry=None):
    """Closed circle of points around `axis` through `center`."""
    c = Vector(center)
    rx = rx or radius
    ry = ry or radius
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        u, v = math.cos(a) * rx, math.sin(a) * ry
        if axis == 'X':
            out.append(c + Vector((0, u, v)))
        elif axis == 'Y':
            out.append(c + Vector((u, 0, v)))
        else:
            out.append(c + Vector((u, v, 0)))
    return out


def blob(name, center=(0, 0, 0), radii=(1, 1, 1), segs=8, rings=5, mat=None, jitter=0.0,
         seed=0, sharpen=0.0, r=None, squash=None, **kw):
    """Low-poly ellipsoid (UV sphere with poles on X). sharpen>0 pulls the X poles to points
    (flint leaves); squash(fn) -> optional per-vertex callable(v: Vector) -> Vector."""
    bm = bmesh.new()
    top = bm.verts.new((1, 0, 0))
    bot = bm.verts.new((-1, 0, 0))
    grid = []
    for i in range(1, rings):
        t = math.pi * i / rings
        x, s = math.cos(t), math.sin(t)
        if sharpen:
            s = s ** (1.0 + sharpen)
        grid.append([bm.verts.new((x, s * math.cos(2 * math.pi * k / segs), s * math.sin(2 * math.pi * k / segs)))
                     for k in range(segs)])
    for k in range(segs):
        k2 = (k + 1) % segs
        bm.faces.new((top, grid[0][k2], grid[0][k]))
        bm.faces.new((bot, grid[-1][k], grid[-1][k2]))
        for i in range(len(grid) - 1):
            bm.faces.new((grid[i][k], grid[i][k2], grid[i + 1][k2], grid[i + 1][k]))
    rnd = random.Random(seed)
    for v in bm.verts:
        co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
        if jitter:
            co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * jitter
        if squash:
            co = squash(co)
        v.co = co
    m = Matrix.Translation(Vector(center))
    if r is not None:
        m = m @ r.to_4x4()
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return finish(name, bm, mat, **kw)


def box(name, center=(0, 0, 0), size=(1, 1, 1), mat=None, r=None, taper=None, **kw):
    """Box; taper=(sy, sz) scales the +X end face (wedges, boards)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        x, y, z = v.co
        if taper and x > 0:
            y *= taper[0]
            z *= taper[1]
        v.co = Vector((x * size[0], y * size[1], z * size[2]))
    m = Matrix.Translation(Vector(center))
    if r is not None:
        m = m @ r.to_4x4()
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    kw.setdefault("smooth", False)
    return finish(name, bm, mat, **kw)


def lathe(name, profile, sides=12, mat=None, matrix=None, **kw):
    """Revolve profile [(x, r), ...] around +X. r=0 at an end -> pole."""
    pts = [Vector((x, 0, 0)) for x, _ in profile]
    radii = [r for _, r in profile]
    ob = tube(name, pts, radii, sides=sides, mat=mat, up=(0, 0, 1), **kw)
    if matrix is not None:
        ob.data.transform(matrix)
    return ob


def cross_planes(name, center, width, height, mat=None, n=2, surface=None, axis_up=(0, 0, 1)):
    """n vertical quads crossing at `center` (flames). Bottom edge at center.z."""
    bm = bmesh.new()
    c = Vector(center)
    for i in range(n):
        a = math.pi * i / n
        d = Vector((math.cos(a), math.sin(a), 0)) * (width / 2)
        up = Vector(axis_up) * height
        vs = [bm.verts.new(c - d), bm.verts.new(c + d), bm.verts.new(c + d + up), bm.verts.new(c - d + up)]
        bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if mat is not None:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if surface:
        ob["surface"] = surface
    # planar UVs: u across, v up — whole flame frame on each quad
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            k = me.loops[li].vertex_index % 4
            uv.data[li].uv = ((0, 0), (1, 0), (1, 1), (0, 1))[k]
    ob["fixed_uv"] = 1
    return ob


def tag(name, loc=(0, 0, 0), r=None):
    """Q3 tag as an empty (artists keep the same names)."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = 2.0
    m = Matrix.Translation(Vector(loc))
    if r is not None:
        m = m @ r.to_4x4()
    e.matrix_world = m
    bpy.context.scene.collection.objects.link(e)
    return e


def tri_count(objs):
    return sum(len(o.data.polygons) for o in objs if o.type == 'MESH')
