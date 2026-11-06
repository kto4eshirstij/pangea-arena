#!/usr/bin/env python3
"""Turn raw generated art (content/pangea/art/<skin>/*.png|jpg) into a skin texture set:
diffuse .tga (1024 square), _n normal map from a high-pass height estimate, _s specular/gloss,
_g glow from warm bright pixels, sky env box + clouds, levelshots 4:3 JPEG.

Usage: python art2skin.py <skin>
"""
import glob, os, sys
import numpy as np
from PIL import Image, ImageFilter

TEX = 1024
SKY = 512
MATERIALS = ["wall_a", "floor_a", "ceil_a", "trim_a", "lamp", "ring_floor", "pad_base"]
GLOW_MATERIALS = {"trim_a", "lamp"}


def load(path):
    return Image.open(path).convert("RGB")


def square(img, size):
    w, h = img.size
    s = min(w, h)
    img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    return img.resize((size, size), Image.LANCZOS)


def make_tileable(arr, border=0.12, axes=("x", "y")):
    """Cross-fade the edges with the opposite edges so the texture tiles (cheap but effective for stone)."""
    h, w, _ = arr.shape
    b = int(w * border)
    out = arr.astype(np.float32).copy()
    ramp = np.linspace(0, 1, b, dtype=np.float32)
    if "x" in axes:
        left, right = out[:, :b].copy(), out[:, w - b:].copy()
        out[:, :b] = left * ramp[None, :, None] + right * (1 - ramp)[None, :, None]
        out[:, w - b:] = right * (1 - ramp)[None, :, None][:, ::-1] + left * ramp[None, ::-1, None]
    if "y" in axes:
        top, bot = out[:b].copy(), out[h - b:].copy()
        out[:b] = top * ramp[:, None, None] + bot * (1 - ramp)[:, None, None]
        out[h - b:] = bot * (1 - ramp)[::-1][:, None, None] + top * ramp[::-1][:, None, None]
    return out


def _min_cut_x(L, R):
    """Vertical minimum-error path through the overlap of R (left of cut) and L (right of cut)."""
    e = ((L - R) ** 2).sum(-1)
    h, w = e.shape
    cost = e.copy()
    for y in range(1, h):
        prev = cost[y - 1]
        best = np.minimum(prev, np.minimum(np.r_[np.inf, prev[:-1]], np.r_[prev[1:], np.inf]))
        cost[y] += best
    path = np.zeros(h, int)
    path[-1] = int(np.argmin(cost[-1]))
    for y in range(h - 2, -1, -1):
        c = path[y + 1]
        lo, hi = max(0, c - 1), min(w, c + 2)
        path[y] = lo + int(np.argmin(cost[y, lo:hi]))
    return path


def seam_tile(arr, overlap=0.14, axes=("x", "y")):
    """Make a texture tileable by quilting its own edges: the right strip overlaps the left strip and the
    two are joined along the cheapest path (seams follow stone joints instead of a visible cross-fade)."""
    out = arr.astype(np.float32)
    for ax in axes:
        if ax == "y":
            out = out.transpose(1, 0, 2)
        h, w, _ = out.shape
        ov = int(w * overlap)
        L, R = out[:, :ov], out[:, w - ov:]
        path = _min_cut_x(L, R)
        cols = np.arange(ov)[None, :]
        # soft 3-px feather around the cut
        t = np.clip((cols - path[:, None] + 1.5) / 3.0, 0, 1)[..., None]
        joined = R * (1 - t) + L * t
        out = np.concatenate([joined, out[:, ov:w - ov]], axis=1)
        if ax == "y":
            out = out.transpose(1, 0, 2)
    return out


def height_from_rgb(arr, blur=12):
    lum = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]) / 255.0
    img = Image.fromarray((lum * 255).astype(np.uint8))
    low = np.asarray(img.filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255.0
    hp = lum - low                       # high-pass: fine relief
    mid = np.asarray(img.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255.0 - low
    h = np.clip(0.5 + 1.6 * hp + 0.8 * mid, 0, 1)
    return h


def normal_from_height(h, strength):
    gx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    gy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx, ny, nz = -gx * strength, gy * strength, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / l, ny / l, nz / l], -1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def glow_mask(arr):
    r, g, b = arr[..., 0] / 255.0, arr[..., 1] / 255.0, arr[..., 2] / 255.0
    warm = np.clip((r - b) * 2.2, 0, 1) * np.clip((r + g) / 2 - 0.45, 0, 1) * 2.5
    return np.clip(warm, 0, 1)


def save(path, arr, mode="RGB"):
    """ioq3 resolves textures by name with any of .tga/.jpg/.png, so we write compact files:
    RGB -> .jpg (q92), RGBA -> .png. Stale .tga with the same name is removed (it would win)."""
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode)
    base = os.path.splitext(path)[0]
    for ext in (".tga", ".jpg", ".png"):
        if os.path.exists(base + ext):
            os.remove(base + ext)
    if mode == "RGBA":
        img.save(base + ".png", optimize=True); print("wrote", base + ".png")
    else:
        img.save(base + ".jpg", quality=92); print("wrote", base + ".jpg")


def crop_to_panel(img):
    """Crop to the bounding box of the bright panel (lamp art sometimes leaves wall around the frame)."""
    a = np.asarray(img.convert("L"), np.float32)
    g = np.abs(np.diff(a, axis=0))[:, :-1] + np.abs(np.diff(a, axis=1))[:-1, :]
    rows = np.where(g.mean(1) > g.mean() * 0.9)[0]
    cols = np.where(g.mean(0) > g.mean() * 0.9)[0]
    if len(rows) < 10 or len(cols) < 10:
        return img
    y0, y1, x0, x1 = rows[0], rows[-1], cols[0], cols[-1]
    side = max(y1 - y0, x1 - x0)
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    box = (max(0, cx - side // 2), max(0, cy - side // 2), min(img.size[0], cx + side // 2), min(img.size[1], cy + side // 2))
    return img.crop(box)


def main(skin):
    raw = os.path.join("content", "pangea", "art", skin)
    out = os.path.join("content", "pangea", "textures", "pangea", skin)
    shots = os.path.join("content", "pangea", "levelshots")
    os.makedirs(out, exist_ok=True); os.makedirs(shots, exist_ok=True); os.makedirs(os.path.join(out, "env"), exist_ok=True)

    def find(name):
        for f in glob.glob(os.path.join(raw, name + ".*")):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                return f
        return None

    for name in MATERIALS:
        src = find(name)
        if not src:
            print("missing art:", name); continue
        if name == "trim_a":
            # the plating band sits in the middle of the generated image: crop it to a 1024x256 strip
            im = load(src); w, h = im.size
            img = im.crop((0, int(h * 0.26), w, int(h * 0.74))).resize((TEX, 256), Image.LANCZOS)
            arr = seam_tile(np.asarray(img, np.float32), axes=("x",))
            arr = np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((TEX, 256), Image.LANCZOS), np.float32)
        else:
            if name not in ("lamp", "ring_floor", "pad_base"):
                big = np.asarray(square(load(src), TEX + TEX // 4), np.float32)
                arr = seam_tile(big)
                arr = np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((TEX, TEX), Image.LANCZOS), np.float32)
            else:
                im = load(src)
                if name == "lamp":
                    im = crop_to_panel(im)
                arr = np.asarray(square(im, TEX), np.float32)
        save(os.path.join(out, name + ".tga"), arr)
        h = height_from_rgb(arr)
        strength = {"ceil_a": 5.0, "wall_a": 4.5, "floor_a": 4.2, "ring_floor": 3.5}.get(name, 3.0)
        save(os.path.join(out, name + "_n.tga"), normal_from_height(h, strength))
        lum = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]) / 255.0
        gloss = {"trim_a": 0.75, "lamp": 0.7, "pad_base": 0.7}.get(name, 0.35)
        spec_rgb = (0.55, 0.5, 0.45) if name in ("trim_a", "lamp", "pad_base") else (0.22, 0.22, 0.21)
        s = np.zeros(arr.shape[:2] + (4,), np.float32)
        s[..., :3] = np.array(spec_rgb)[None, None, :] * 255 * (0.6 + 0.4 * lum)[..., None]
        s[..., 3] = np.clip(gloss * (0.7 + 0.6 * lum), 0, 1) * 255
        save(os.path.join(out, name + "_s.tga"), s, "RGBA")
        if name in GLOW_MATERIALS:
            g = glow_mask(arr)
            save(os.path.join(out, name + "_g.tga"), arr * g[..., None])

    # sky: panoramic -> 4 side faces (slices), up/down flat, plus a square backdrop
    src = find("sky")
    if src:
        sky = load(src)
        w, h = sky.size
        face_w = w // 2
        for i, face in enumerate(("ft", "rt", "bk", "lf")):
            x0 = (i % 2) * face_w
            f = sky.crop((x0, 0, x0 + face_w, h))
            if i >= 2:
                f = f.transpose(Image.FLIP_LEFT_RIGHT)
            f = f.resize((SKY, SKY), Image.LANCZOS)
            save(os.path.join(out, "env", f"sky_{face}.tga"), np.asarray(f, np.float32))
        top = np.asarray(sky.resize((SKY, SKY)), np.float32)[:SKY // 6].mean(axis=(0, 1))
        bot = np.asarray(sky.resize((SKY, SKY)), np.float32)[-SKY // 6:].mean(axis=(0, 1))
        save(os.path.join(out, "env", "sky_up.tga"), np.full((SKY, SKY, 3), top, np.float32))
        save(os.path.join(out, "env", "sky_dn.tga"), np.full((SKY, SKY, 3), bot * 0.5, np.float32))
        save(os.path.join(out, "sky.tga"), np.asarray(square(sky, SKY), np.float32))
    src = find("clouds")
    if src:
        c = seam_tile(np.asarray(square(load(src), TEX), np.float32))
        lum = (0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2])
        save(os.path.join(out, "clouds.tga"), np.stack([lum] * 3, -1))
        save(os.path.join(out, "clouds2.tga"), np.stack([np.clip(lum * 0.6 - 20, 0, 255)] * 3, -1)[::-1, ::-1])
    # pads: reuse relic ring/spiral masks if present, else nothing (shader falls back)
    for name in ("pad_rings", "tele_spiral"):
        relic = next((f for f in glob.glob(os.path.join("content", "pangea", "textures", "pangea", "relic", name + ".*"))), None)
        if relic and not glob.glob(os.path.join(out, name + ".*")):
            save(os.path.join(out, name + ".tga"), np.asarray(Image.open(relic).convert("RGB"), np.float32))
    # levelshots
    for f in glob.glob(os.path.join(raw, "pangea_*.*")):
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            name = os.path.splitext(os.path.basename(f))[0]
            img = load(f)
            w, h = img.size
            tw = int(h * 4 / 3) if w >= h * 4 / 3 else w
            th = int(tw * 3 / 4)
            img = img.crop(((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th)).resize((1024, 768), Image.LANCZOS)
            img.save(os.path.join(shots, name + ".jpg"), quality=88); print("wrote levelshot", name)


    # keep sources in git as JPEG (the PNG originals are large); art2skin reads either
    for f in glob.glob(os.path.join(raw, "*.png")) + glob.glob(os.path.join(raw, "*.webp")):
        load(f).save(os.path.splitext(f)[0] + ".jpg", quality=93)
        os.remove(f); print("compressed", os.path.basename(f))


if __name__ == "__main__":
    main(sys.argv[1])
