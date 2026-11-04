# Pangea Arena — race skin materials for first-person hands (13 races). GPLv2+.
# Colour + small details (scales, warts, fur, claws, pearl sheen) live in the texture only;
# geometry is shared per build.
from lib import materials as M

# base, shadow, nail, feature
RACE = {
    "human":      dict(base="#c4957a", dark="#9a6b55", nail="#dcb8a4"),
    "elf":        dict(base="#e3c6ac", dark="#b8957c", nail="#efd9c8"),
    "dwarf":      dict(base="#c08466", dark="#8f5a44", nail="#d9ab92", hair=0.5),
    "gnome":      dict(base="#d6a587", dark="#a8775e", nail="#ebc7b1"),
    "halfling":   dict(base="#c99271", dark="#9b6a50", nail="#e0b59c", hair=0.3),
    "orc":        dict(base="#768a52", dark="#4f603a", nail="#3b3a2a"),
    "goblin":     dict(base="#8f9b48", dark="#5f6a2e", nail="#3a3a22", warts=0.4),
    "goliath":    dict(base="#9d978c", dark="#6c675f", nail="#c2bcae", marks=True),
    "dragonborn": dict(base="#93503a", dark="#5a2c1e", nail="#2a1a14", scales=True),
    "tiefling":   dict(base="#b14a42", dark="#7a2c28", nail="#2a1414"),
    "troll":      dict(base="#7d8a7a", dark="#56604f", nail="#3a3b30", warts=1.0),
    "felar":      dict(base="#b48c5c", dark="#7c5a36", nail="#2c241c", fur=True),
    "fey":        dict(base="#f0dccd", dark="#c9aea0", nail="#fff4ec", pearl=True),
}


def make(race, tip=False):
    p = RACE[race]
    g = M.G("skin_%s%s" % (race, "_tip" if tip else ""))
    tone = g.noise(g.co, scale=0.6, detail=3)
    col = g.ramp(tone, [(0.25, p["dark"]), (0.75, p["base"])])
    blotch = g.noise(g.co, scale=1.8, detail=2)
    col = g.mix(col, p["dark"], g.math('MULTIPLY', g.smooth(blotch, 0.55, 0.75), 0.35))
    pores = g.noise(g.co, scale=18.0, detail=1)
    col = g.mix(col, p["dark"], g.math('MULTIPLY', g.smooth(pores, 0.62, 0.72), 0.18))
    if p.get("scales"):
        cell = g.voronoi(g.co, scale=2.6, feature='DISTANCE_TO_EDGE')
        col = g.mix(col, "#2e160e", g.math('MULTIPLY', g.smooth(cell, 0.08, 0.0), 0.85))
        hi = g.voronoi(g.co, scale=2.6, out='Distance')
        col = g.mix(col, "#c07a4e", g.math('MULTIPLY', g.smooth(hi, 0.3, 0.0), 0.35))
    if p.get("warts"):
        w = g.voronoi(g.co, scale=3.2, rand=1.0)
        col = g.mix(col, "#4b5244", g.math('MULTIPLY', g.smooth(w, 0.16, 0.06), p["warts"]))
        col = g.mix(col, "#a3ab92", g.math('MULTIPLY', g.smooth(w, 0.08, 0.0), p["warts"] * 0.7))
    if p.get("marks"):     # goliath stone-like markings
        m = g.wave(g.co, scale=0.35, dist=7.0, detail=3)
        col = g.mix(col, "#4a463f", g.math('MULTIPLY', g.smooth(m, 0.88, 0.97), 0.8))
    if p.get("fur") or p.get("hair"):
        f = g.noise(g.along('X', 0.2, 10.0), scale=4.0, detail=3)
        amt = 0.9 if p.get("fur") else p["hair"]
        col = g.mix(col, "#5a3f26", g.math('MULTIPLY', g.smooth(f, 0.45, 0.65), amt))
        if p.get("fur"):
            st = g.noise(g.co, scale=0.5, detail=2)
            col = g.mix(col, "#e2c79c", g.math('MULTIPLY', g.smooth(st, 0.55, 0.7), 0.5))
    if p.get("pearl"):
        sh = g.noise(g.co, scale=1.2, detail=2, color=True)
        col = g.mix(col, sh, 0.12, blend='OVERLAY')
        col = g.mix(col, "#e8f0ff", g.math('MULTIPLY', g.smooth(tone, 0.6, 0.9), 0.25))
    if tip:
        # nail on the dorsal side of the fingertip (canonical flat pose: dorsal = +Z)
        nz = g.add('ShaderNodeSeparateXYZ')
        g.put(nz.inputs[0], g.add('ShaderNodeNewGeometry').outputs['True Normal'])
        nail = g.smooth(nz.outputs['Z'], 0.45, 0.75)
        col = g.mix(col, p["nail"], g.math('MULTIPLY', nail, 0.9))
    g.put(g.bsdf.inputs['Base Color'], col)
    # same output modes as lib.materials (bake.py switches them)
    nodes = {"color": g.bsdf, "P": g.emission((0.5, 0.5, 0.5, 1)), "M": g.emission((0, 0, 0, 1)),
             "glow": g.emission((0, 0, 0, 1))}
    M._MODES[g.m.name] = nodes
    M.set_mode(g.m, "color")
    return g.m
