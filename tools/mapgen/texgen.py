#!/usr/bin/env python3
"""Procedural placeholder textures for a skin (512x512 TGA). Replaced later by real art.

Usage: python texgen.py <skin> <out_dir>   e.g. texgen.py relic content/pangea/textures/pangea/relic
Palettes per skin are in PALETTES; unknown skin -> relic palette.
"""
import os, sys
import numpy as np
from PIL import Image

SIZE = 512
PALETTES = {
    # name: (base rgb, dark rgb, accent rgb)
    "relic":  {"floor": ((96, 92, 86), (58, 55, 52)), "wall": ((110, 104, 96), (70, 66, 62)),
               "ceil": ((62, 60, 58), (36, 35, 34)), "trim": ((150, 92, 48), (90, 50, 24)),
               "sky": ((40, 48, 70), (12, 14, 24)), "clouds": ((190, 190, 200), (40, 45, 60))},
}


def value_noise(rng, size, cells, octaves=4, persistence=0.5):
    acc = np.zeros((size, size), dtype=np.float32)
    amp, total = 1.0, 0.0
    c = cells
    for _ in range(octaves):
        grid = rng.random((c + 1, c + 1)).astype(np.float32)
        grid[-1, :] = grid[0, :]; grid[:, -1] = grid[:, 0]   # tileable
        img = Image.fromarray((grid * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        acc += amp * (np.asarray(img, dtype=np.float32) / 255.0)
        total += amp; amp *= persistence; c *= 2
    return acc / total


def blocks_mask(size, bw, bh, gap=6, offset=True):
    m = np.ones((size, size), dtype=np.float32)
    for row, y in enumerate(range(0, size, bh)):
        off = (bw // 2) if (offset and row % 2) else 0
        m[y:y + gap, :] = 0.0
        for x in range(-off, size, bw):
            xx = x % size
            m[:, xx:xx + gap] = 0.0 if xx + gap <= size else m[:, xx:xx + gap]
    return m


def cracks(rng, size, n=40):
    m = np.ones((size, size), dtype=np.float32)
    for _ in range(n):
        x, y = rng.integers(0, size, 2); dx, dy = rng.normal(0, 1, 2)
        for _ in range(rng.integers(40, 200)):
            dx += rng.normal(0, 0.3); dy += rng.normal(0, 0.3)
            x = (x + np.sign(dx)) % size; y = (y + np.sign(dy)) % size
            m[int(y), int(x)] = 0.55
    return m


def colorize(noise, base, dark):
    base = np.array(base, np.float32); dark = np.array(dark, np.float32)
    rgb = dark[None, None, :] + (base - dark)[None, None, :] * noise[..., None]
    return np.clip(rgb, 0, 255).astype(np.uint8)


def make(skin, out):
    pal = PALETTES.get(skin, PALETTES["relic"])
    rng = np.random.default_rng(abs(hash(skin)) % (2 ** 32))
    os.makedirs(out, exist_ok=True)
    n = value_noise(rng, SIZE, 8)
    tex = {}
    tex["floor_a"] = colorize(np.clip(n * 0.8 + 0.2, 0, 1) * blocks_mask(SIZE, 128, 128, 4, False) * cracks(rng, SIZE, 25), *pal["floor"])
    tex["wall_a"] = colorize(np.clip(value_noise(rng, SIZE, 16) * 0.7 + 0.3, 0, 1) * blocks_mask(SIZE, 128, 64, 6, True), *pal["wall"])
    tex["ceil_a"] = colorize(np.clip(value_noise(rng, SIZE, 6, 5) * 0.9 + 0.1, 0, 1), *pal["ceil"])
    rust = value_noise(rng, SIZE, 12, 5)
    tex["trim_a"] = colorize(np.clip(rust * 0.9 + 0.1, 0, 1) * blocks_mask(SIZE, 256, 64, 8, False), *pal["trim"])
    tex["sky"] = colorize(np.clip(value_noise(rng, SIZE, 4, 3), 0, 1), *pal["sky"])
    cl = value_noise(rng, SIZE, 4, 6, 0.55)
    tex["clouds"] = colorize(np.clip((cl - 0.35) * 2.2, 0, 1), *pal["clouds"])
    for name, arr in tex.items():
        Image.fromarray(arr, "RGB").save(os.path.join(out, name + ".tga"))
        print("wrote", os.path.join(out, name + ".tga"))


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2])
