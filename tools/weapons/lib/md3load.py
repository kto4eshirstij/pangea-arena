# Pangea Arena — load exported MD3 (+ .skin) back into Blender for previews. GPLv2+.
import os

import bpy
from mathutils import Matrix, Vector

from md3 import md3

def _image(pak, q):
    return bpy.data.images.load(os.path.abspath(os.path.join(pak, q)), check_existing=True)


def material(pak, shader, glow_ids=()):
    name = "q3:" + shader
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    if shader.endswith("/flame"):
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = _image(pak, shader + "1.tga")
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Strength'].default_value = 3.0
        nt.links.new(tex.outputs['Color'], em.inputs['Color'])
        bw = nt.nodes.new('ShaderNodeRGBToBW')
        nt.links.new(tex.outputs['Color'], bw.inputs[0])
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(bw.outputs[0], mix.inputs[0])
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])
        return m
    tga = shader if shader.endswith(".tga") else shader + ".tga"
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = _image(pak, tga)
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    b.inputs['Roughness'].default_value = 0.85
    b.inputs['Specular IOR Level'].default_value = 0.2
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    if not shader.endswith(".tga"):
        base = shader.split("_paint")[0]
        gp = os.path.join(pak, base + "_glow.tga")
        if os.path.exists(gp):
            g = nt.nodes.new('ShaderNodeTexImage')
            g.image = _image(pak, base + "_glow.tga")
            nt.links.new(g.outputs['Color'], b.inputs['Emission Color'])
            b.inputs['Emission Strength'].default_value = 2.0
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def read_skin(pak, q):
    out = {}
    with open(os.path.join(pak, q)) as f:
        for line in f:
            if "," in line:
                k, v = line.strip().split(",", 1)
                if v:
                    out[k] = v
    return out


def load(pak, q, skin=None, matrix=None, name=None):
    """Returns (objects, tags {name: Matrix}) for models/....md3 inside `pak`."""
    m = md3.read(os.path.join(pak, q))
    remap = read_skin(pak, skin) if skin else {}
    M = matrix or Matrix.Identity(4)
    objs = []
    for s in m["surfaces"]:
        me = bpy.data.meshes.new(s["name"])
        me.from_pydata(s["verts"], [], [tuple(t) for t in s["tris"]])
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                u, t = s["st"][vi]
                uv.data[li].uv = (u, 1.0 - t)
        me.normals_split_custom_set_from_vertices(s["normals"])
        for poly in me.polygons:
            poly.use_smooth = True
        me.materials.append(material(pak, remap.get(s["name"], s["shader"])))
        ob = bpy.data.objects.new((name or "") + s["name"], me)
        ob.matrix_world = M
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
    tags = {}
    for t in m["tags"]:
        r = Matrix((t["axis"][0], t["axis"][1], t["axis"][2])).transposed().to_4x4()
        r.translation = Vector(t["origin"])
        tags[t["name"]] = M @ r
    return objs, tags
