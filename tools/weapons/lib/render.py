# Pangea Arena — preview staging and rendering (Cycles CPU). GPLv2+.
import math

import bpy
from mathutils import Vector

from . import materials


def world(color="#0b0907", strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = materials.lin(color)
    bg.inputs[1].default_value = strength
    sc.world = w


def stage(ground_z=None, size=400.0):
    """Dark stone floor + warm light from above + dim fill."""
    world("#0d0b0a", 1.0)
    if ground_z is not None:
        m = materials.make("river_stone", "_floor", shade=2, scale=0.08)
        bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, ground_z))
        fl = bpy.context.active_object
        fl.data.materials.append(m)
        fl["preview_only"] = 1
        # darken the floor
        b = m.node_tree.nodes.get("Principled BSDF")
        mixn = m.node_tree.nodes.new('ShaderNodeMixRGB')
        mixn.blend_type = 'MULTIPLY'
        mixn.inputs['Fac'].default_value = 1.0
        mixn.inputs['Color2'].default_value = materials.lin("#3a3430")
        src = b.inputs['Base Color'].links[0].from_socket
        m.node_tree.links.new(src, mixn.inputs['Color1'])
        m.node_tree.links.new(mixn.outputs[0], b.inputs['Base Color'])


def lights(target=(0, 0, 0), scale=1.0, key=1.0):
    t = Vector(target)
    for name, off, energy, col, sz in (
            ("key", (-10, 25, 60), 90000 * key, "#ffc890", 30),
            ("rim", (40, -50, 20), 30000 * key, "#ffa560", 20),
            ("fill", (-50, -20, 10), 14000 * key, "#b9a48c", 40)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = energy * scale * scale
        ld.color = materials.lin(col)[:3]
        ld.size = sz * scale
        ob = bpy.data.objects.new(name, ld)
        ob.location = t + Vector(off) * scale
        d = t - ob.location
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.scene.collection.objects.link(ob)


def bbox(objs):
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != 'MESH' or o.get("preview_only"):
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def camera(loc, target, lens=50.0, ortho=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start = 0.5
    cd.clip_end = 5000
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new("cam", cd)
    ob.location = Vector(loc)
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def view34(objs, az=35.0, el=28.0, lens=50.0, margin=0.8, aspect=4 / 3):
    lo, hi = bbox(objs)
    c = (lo + hi) / 2
    rad = (hi - lo).length / 2
    fov = 2 * math.atan(36 / 2 / lens) / aspect if aspect > 1 else 2 * math.atan(36 / 2 / lens)
    dist = rad * margin / math.tan(fov / 2)
    a, e = math.radians(az), math.radians(el)
    loc = c + Vector((-math.cos(e) * math.cos(a), -math.cos(e) * math.sin(a), math.sin(e))) * dist
    camera(loc, c, lens)
    return c, rad


def q3_view(fov_x=90.0):
    """First-person camera = Q3 view origin: at 0,0,0 looking +X, Z up."""
    cd = bpy.data.cameras.new("eye")
    cd.sensor_fit = 'HORIZONTAL'
    cd.angle = math.radians(fov_x)
    cd.clip_start = 0.5
    ob = bpy.data.objects.new("eye", cd)
    ob.rotation_euler = (math.radians(90), 0, math.radians(-90))
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def render(path, w=640, h=480, samples=48, transparent=False):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
