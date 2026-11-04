# Pangea Arena — ochre/soot body-paint generator. GPLv2+.
#
# Works in texture space with numpy: bake.py bakes, for every texel, its position in the
# "paint space" of the part it belongs to (P) and a canvas mask (M). Patterns are then
# simple functions of 3D position, so they stay continuous across UV seams.
#
# Paint space (materials.paint_matrix): x along the part's main axis, z = projection axis
# (towards the viewer of a handprint), canvas roughly spans x in [-1, 1].
# Shapes: shaft (handles, shafts, limbs) and disc (shield face; x/y in the disc plane).
#
# Variants (one per <id>_paintN.tga):
#   1 stripes  — red ochre bands with thin soot edges
#   2 dots     — rows of yellow-ochre dots, red ring
#   3 palm     — red-ochre handprint, soot fingertip dots
#   4 zigzag   — soot zigzag with yellow-ochre companion
import numpy as np

RED = np.array([0xb5, 0x53, 0x2a]) / 255.0
YELLOW = np.array([0xc9, 0x9a, 0x3a]) / 255.0
SOOT = np.array([0x1e, 0x1a, 0x17]) / 255.0
NAMES = {1: "stripes", 2: "dots", 3: "palm", 4: "zigzag"}


def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(p, freq=1.0, seed=0):
    """Trilinear value noise, p: (N, 3)."""
    q = p * freq
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * \
                    (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(p, freq, seed, octaves=3):
    s, a, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + a * vnoise(p, freq * 2 ** o, seed + o)
        tot += a
        a *= 0.5
    return s / tot


def _band(d, w, soft=0.02):
    """1 inside |d| < w, soft edge."""
    return np.clip((w - np.abs(d)) / soft + 0.5, 0, 1)


def _capsule(u, v, a, b, r):
    pa = np.stack([u - a[0], v - a[1]], -1)
    ba = np.array([b[0] - a[0], b[1] - a[1]])
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    d = pa - h[:, None] * ba
    return np.sqrt((d ** 2).sum(-1)) - r


def handprint_sdf(u, v):
    """Signed distance to a stylised left handprint, fingers toward +u, size ~1."""
    palm = np.sqrt(((u + 0.15) / 0.36) ** 2 + (v / 0.32) ** 2) - 1.0
    d = palm * 0.3
    fingers = [((0.12, 0.2), (0.52, 0.27), 0.065), ((0.17, 0.07), (0.62, 0.09), 0.07),
               ((0.17, -0.07), (0.58, -0.09), 0.068), ((0.1, -0.2), (0.43, -0.27), 0.058)]
    for a, b, r in fingers:
        d = np.minimum(d, _capsule(u, v, a, b, r))
    d = np.minimum(d, _capsule(u, v, (-0.2, 0.25), (0.02, 0.52), 0.075))   # thumb
    return d


def _tri(t):
    return 2 * np.abs(t - np.floor(t + 0.5))   # 0..1 triangle wave


def patterns(p, shape, variant):
    """Returns list of (mask, colour) for texels at paint-space positions p (N,3)."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    disc = shape > 0.5
    r = np.sqrt(x * x + y * y)
    th = np.arctan2(y, x)                      # angle in disc plane
    ang = np.arctan2(z, y)                     # angle around a shaft
    out = []
    if variant == 1:
        c = np.where(disc, r, x)
        red = sum(_band(c - k, 0.09) for k in (-0.55, 0.0, 0.55))
        red = np.where(disc, _band(r - 0.78, 0.09) + _band(r - 0.42, 0.07), red)
        soot = sum(_band(c - k, 0.022) for k in (-0.7, -0.4, -0.15, 0.15, 0.4, 0.7))
        soot = np.where(disc, _band(r - 0.62, 0.025) + _band(r - 0.92, 0.02), soot)
        out += [(np.clip(red, 0, 1), RED), (np.clip(soot, 0, 1), SOOT)]
    elif variant == 2:
        cell = 0.2
        q = p / cell
        qi = np.floor(q)
        jit = np.stack([_hash(qi[:, 0].astype(np.int64), qi[:, 1].astype(np.int64),
                              qi[:, 2].astype(np.int64), 7 + k) for k in range(3)], -1)
        cen = (qi + 0.3 + 0.4 * jit) * cell
        dist = np.sqrt(((p - cen) ** 2).sum(-1))
        dots = np.clip((0.055 - dist) / 0.015 + 0.5, 0, 1)
        rows = np.where(disc, _band(r - 0.6, 0.2), _band(np.abs(x) - 0.45, 0.2))
        ring = np.where(disc, _band(r - 0.9, 0.05), _band(x, 0.05))
        out += [(dots * rows, YELLOW), (ring, RED)]
    elif variant == 3:
        hs = 0.62
        hp = np.clip(-handprint_sdf(x / hs, y / hs) / 0.03 + 0.5, 0, 1)
        ring_dots = np.zeros_like(x)
        for k in range(9):
            a = 2 * np.pi * k / 9
            d = np.hypot(x - 0.86 * np.cos(a), y - 0.86 * np.sin(a))
            ring_dots += np.clip((0.05 - d) / 0.012 + 0.5, 0, 1)
        lines = _band(x + 0.82, 0.03) + _band(x - 0.82, 0.03)
        out += [(hp, RED), (np.clip(np.where(disc, ring_dots, lines), 0, 1), SOOT)]
    elif variant == 4:
        n = 6
        t = np.where(disc, th / (2 * np.pi), ang / (2 * np.pi))
        c = np.where(disc, r, x)
        zz = _band(c - 0.25 - 0.22 * _tri(t * n), 0.045)
        zz2 = _band(c + 0.45 - 0.22 * _tri(t * n + 0.5), 0.035)
        zz2 = np.where(disc, _band(r - 0.8 - 0.1 * _tri(t * n * 2), 0.03), zz2)
        out += [(zz, SOOT), (zz2, YELLOW)]
    return out


def apply(base, P, M, variant, seed=0):
    """base: HxWx3 sRGB float; P: HxWx3 encoded paint coords; M: HxWx3 canvas mask.
    Returns painted copy (sRGB float)."""
    h, w = base.shape[:2]
    flat = base.reshape(-1, 3).copy()
    m = M.reshape(-1, 3)
    idx = np.nonzero(m[:, 0] > 0.5)[0]
    if idx.size == 0:
        return base.copy()
    p = (P.reshape(-1, 3)[idx] - 0.5) / 0.05
    shape = m[idx, 2]
    strength = m[idx, 1]
    wear = np.clip((fbm(p, 3.0, seed + variant * 31) - 0.28) * 4.0, 0, 1)
    speck = np.clip((vnoise(p, 22.0, seed + 5) - 0.18) * 6.0, 0, 1)
    fade = wear * speck * strength * 0.92
    for mask, col in patterns(p, shape, variant):
        a = np.clip(mask, 0, 1) * fade
        under = flat[idx]
        painted = col[None, :] * (0.75 + 0.25 * under.mean(-1, keepdims=True) / 0.5)
        flat[idx] = under * (1 - a[:, None]) + np.clip(painted, 0, 1) * a[:, None]
    return flat.reshape(h, w, 3)
