#!/usr/bin/env python3
"""Procedural PBR-ish texture sets for a skin (512x512 TGA): <name>.tga (diffuse), <name>_n.tga (normal,
OpenGL convention, +Y up), <name>_s.tga (specular RGB + gloss in alpha), <name>_g.tga (glow) where used.
Placeholders until real art arrives; file names are the contract for artists.

Usage: python texgen.py <skin> <out_dir>
"""
import os, sys
import numpy as np
from PIL import Image

SIZE = 512
PALETTES = {
    "relic": {
        "floor": ((118, 112, 104), (52, 50, 48), (96, 104, 78)),   # base, mortar/dark, moss tint
        "wall": ((124, 116, 106), (58, 54, 50), (110, 100, 84)),
        "ceil": ((70, 66, 62), (28, 27, 26), (60, 56, 52)),
        "trim": ((104, 74, 46), (44, 30, 18), (176, 92, 30)),       # rusted iron, glow = ember orange
        "glow": (255, 150, 60),
        "ring": ((150, 140, 120), (70, 64, 56), (210, 170, 90)),
        "sky": ((26, 32, 52), (6, 7, 12)),
        "clouds": ((200, 196, 210), (30, 34, 48)),
    },
}


def rng_for(skin):
    return np.random.default_rng(sum(ord(c) * (i + 1) for i, c in enumerate(skin)))


def fbm(rng, size, cells, octaves=5, persistence=0.5):
    acc = np.zeros((size, size), np.float32); amp, total, c = 1.0, 0.0, cells
    for _ in range(octaves):
        g = rng.random((c + 1, c + 1)).astype(np.float32)
        g[-1, :] = g[0, :]; g[:, -1] = g[:, 0]
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        acc += amp * (np.asarray(img, np.float32) / 255.0); total += amp; amp *= persistence; c *= 2
    return acc / total


def block_height(size, bw, bh, gap, bevel, offset=True, jitter=0.0, rng=None):
    """Height field of beveled blocks separated by gaps (0 in gaps, 1 on block tops), tileable."""
    h = np.zeros((size, size), np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    rows = size // bh
    for r in range(rows):
        y0 = r * bh; off = (bw // 2) if (offset and r % 2) else 0
        for x0 in range(-off, size, bw):
            jx = int(rng.integers(-jitter, jitter + 1)) if (rng is not None and jitter) else 0
            # block interior region (wrapping in x)
            bx0, bx1 = x0 + gap // 2 + jx, x0 + bw - gap // 2 + jx
            by0, by1 = y0 + gap // 2, y0 + bh - gap // 2
            dx = np.minimum(xx - bx0, bx1 - 1 - xx)
            dxw = np.minimum((xx + size) - bx0, bx1 - 1 - (xx + size))
            dxw2 = np.minimum((xx - size) - bx0, bx1 - 1 - (xx - size))
            dx = np.maximum(dx, np.maximum(dxw, dxw2))
            dy = np.minimum(yy - by0, by1 - 1 - yy)
            d = np.minimum(dx, dy)
            v = np.clip(d / float(bevel), 0, 1)
            h = np.maximum(h, np.where(d >= 0, v, 0))
    return h


def normal_from_height(h, strength=2.0):
    gx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    gy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx, ny, nz = -gx * strength, gy * strength, np.ones_like(h)   # +Y up (OpenGL)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / l, ny / l, nz / l], -1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def colorize(v, base, dark):
    base, dark = np.array(base, np.float32), np.array(dark, np.float32)
    return np.clip(dark + (base - dark) * v[..., None], 0, 255)


def save(path, arr, mode="RGB"):
    Image.fromarray(arr.astype(np.uint8), mode).save(path)
    print("wrote", path)


def material(out, name, height, color, spec_rgb, gloss, ao=None, glow=None, nstrength=2.0, noise=None):
    diffuse = color
    if ao is not None:
        diffuse = diffuse * (0.55 + 0.45 * ao)[..., None]
    save(os.path.join(out, name + ".tga"), np.clip(diffuse, 0, 255))
    save(os.path.join(out, name + "_n.tga"), normal_from_height(height, nstrength))
    s = np.zeros((SIZE, SIZE, 4), np.float32)
    nz = noise if noise is not None else np.ones((SIZE, SIZE), np.float32)
    s[..., :3] = np.array(spec_rgb, np.float32)[None, None, :] * 255 * (0.5 + 0.5 * nz)[..., None]
    s[..., 3] = np.clip(np.broadcast_to(np.asarray(gloss, np.float32), (SIZE, SIZE)), 0, 1) * 255
    save(os.path.join(out, name + "_s.tga"), np.clip(s, 0, 255), "RGBA")
    if glow is not None:
        save(os.path.join(out, name + "_g.tga"), np.clip(glow, 0, 255))


def make(skin, out):
    pal = PALETTES.get(skin, PALETTES["relic"])
    rng = rng_for(skin)
    os.makedirs(out, exist_ok=True)

    # ---- floor: large flagstones with moss in the joints ----
    bh = block_height(SIZE, 128, 128, 8, 6, offset=True, jitter=6, rng=rng)
    grain = fbm(rng, SIZE, 16, 5)
    h = bh * (0.75 + 0.25 * grain) + 0.12 * fbm(rng, SIZE, 64, 2)
    moss = np.clip((1 - bh) * 1.4 + 0.3 * fbm(rng, SIZE, 8, 3) - 0.35, 0, 1)
    col = colorize(0.45 + 0.55 * grain, pal["floor"][0], pal["floor"][1])
    col = col * (1 - moss[..., None] * 0.6) + np.array(pal["floor"][2], np.float32) * moss[..., None] * 0.6
    material(out, "floor_a", h, col, (0.22, 0.22, 0.2), 0.35 * bh + 0.05, ao=bh, nstrength=2.4, noise=grain)

    # ---- wall: ashlar blocks 128x64, slight offset per row ----
    bh = block_height(SIZE, 128, 64, 6, 5, offset=True, jitter=3, rng=rng)
    grain = fbm(rng, SIZE, 24, 5)
    h = bh * (0.8 + 0.2 * grain) + 0.1 * fbm(rng, SIZE, 96, 2)
    col = colorize(0.4 + 0.6 * grain, pal["wall"][0], pal["wall"][1])
    streak = np.clip(fbm(rng, SIZE, 4, 2) - 0.5, 0, 1) * 0.5
    col = col * (1 - streak[..., None]) + np.array(pal["wall"][2], np.float32) * streak[..., None]
    material(out, "wall_a", h, col, (0.18, 0.18, 0.17), 0.25 * bh + 0.05, ao=bh, nstrength=2.2, noise=grain)

    # ---- ceiling: rough rock ----
    h = fbm(rng, SIZE, 6, 6, 0.55)
    col = colorize(0.3 + 0.7 * fbm(rng, SIZE, 12, 4), pal["ceil"][0], pal["ceil"][1])
    material(out, "ceil_a", h, col, (0.08, 0.08, 0.08), 0.1, nstrength=3.0)

    # ---- trim: rusted iron bands with an engraved glowing line ----
    bh = block_height(SIZE, 512, 128, 10, 8, offset=False, rng=rng)
    rust = fbm(rng, SIZE, 20, 5)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    line = np.exp(-((yy % 128 - 64) ** 2) / (2 * 4.0 ** 2))                      # one groove per band
    runes = (np.sin(xx / 512 * 2 * np.pi * 24) > 0.6).astype(np.float32) * np.exp(-((yy % 128 - 64) ** 2) / (2 * 10.0 ** 2))
    glow_mask = np.clip(line + 0.8 * runes, 0, 1)
    h = bh * (0.9 + 0.1 * rust) - 0.5 * glow_mask
    col = colorize(0.35 + 0.65 * rust, pal["trim"][0], pal["trim"][1])
    col = col * (1 - glow_mask[..., None] * 0.7)
    glow = np.array(pal["glow"], np.float32)[None, None, :] * glow_mask[..., None]
    material(out, "trim_a", h, col, (0.45, 0.4, 0.35), 0.5 + 0.3 * rust, ao=bh, glow=glow, nstrength=2.0, noise=rust)

    # ---- lamp: emissive relic panel (sun-disc) ----
    cx, cy = SIZE / 2, SIZE / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (SIZE / 2)
    disc = np.clip(1.2 - r * 1.6, 0, 1) ** 1.5
    rays = (np.cos(np.arctan2(yy - cy, xx - cx) * 12) > 0.3).astype(np.float32) * np.clip(1 - r, 0, 1) * 0.6
    gm = np.clip(disc + rays * (r > 0.45), 0, 1)
    frame = block_height(SIZE, 512, 512, 24, 12, offset=False, rng=rng)
    col = colorize(0.35 + 0.65 * rust, pal["trim"][0], pal["trim"][1]) * (1 - gm[..., None] * 0.8) + np.array(pal["glow"], np.float32) * gm[..., None] * 0.8
    material(out, "lamp", frame - 0.3 * gm, col, (0.4, 0.4, 0.4), 0.6, ao=frame, glow=np.array(pal["glow"], np.float32)[None, None, :] * gm[..., None])

    # ---- ring floor: circle marking (fist duel) ----
    ringm = np.exp(-((r - 0.82) ** 2) / (2 * 0.02 ** 2)) + np.exp(-((r - 0.5) ** 2) / (2 * 0.012 ** 2))
    bh = block_height(SIZE, 64, 64, 4, 3, offset=False, rng=rng)
    grain = fbm(rng, SIZE, 16, 5)
    col = colorize(0.45 + 0.55 * grain, pal["ring"][0], pal["ring"][1])
    col = col * (1 - ringm[..., None] * 0.5) + np.array(pal["ring"][2], np.float32) * ringm[..., None] * 0.5
    material(out, "ring_floor", bh * (0.8 + 0.2 * grain) - 0.4 * ringm, col, (0.25, 0.25, 0.22), 0.3, ao=bh, noise=grain)

    # ---- jump pad / teleporter: concentric rings and a spiral (animated by shader tcMod) ----
    pad = np.clip(np.sin(r * 2 * np.pi * 4) ** 8, 0, 1) * (r < 0.95)
    save(os.path.join(out, "pad_rings.tga"), np.stack([pad * 255] * 3, -1) * np.array([0.7, 0.9, 1.0]))
    ang = np.arctan2(yy - cy, xx - cx)
    spiral = np.clip(np.sin(ang * 3 + r * 18) ** 6, 0, 1) * (r < 0.95)
    save(os.path.join(out, "tele_spiral.tga"), np.stack([spiral * 255] * 3, -1) * np.array([0.9, 0.6, 1.0]))
    save(os.path.join(out, "pad_base.tga"), colorize(0.4 + 0.6 * rust, pal["trim"][0], pal["trim"][1]) * (1 - 0.6 * (r < 0.9)[..., None]))

    # ---- sky: gradient + two cloud layers ----
    grad = np.clip(1 - yy / SIZE, 0, 1)[..., None]
    sky = np.array(pal["sky"][1], np.float32) + (np.array(pal["sky"][0], np.float32) - np.array(pal["sky"][1], np.float32)) * grad
    save(os.path.join(out, "sky.tga"), sky)
    cl = fbm(rng, SIZE, 4, 6, 0.55)
    save(os.path.join(out, "clouds.tga"), colorize(np.clip((cl - 0.38) * 2.4, 0, 1), pal["clouds"][0], pal["clouds"][1]))
    cl2 = fbm(rng, SIZE, 6, 6, 0.5)
    save(os.path.join(out, "clouds2.tga"), colorize(np.clip((cl2 - 0.45) * 3.0, 0, 1), pal["clouds"][0], (0, 0, 0)))
    # env box for skyParms (6 faces: same gradient, cheap)
    env = os.path.join(out, "env"); os.makedirs(env, exist_ok=True)
    for face in ("rt", "lf", "bk", "ft", "up", "dn"):
        img = sky if face not in ("up", "dn") else np.full((SIZE, SIZE, 3), pal["sky"][0 if face == "up" else 1], np.float32)
        save(os.path.join(env, f"sky_{face}.tga"), img)


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2])
