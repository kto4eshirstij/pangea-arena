# Pangea Arena — minimal TGA writer/reader (uncompressed 24/32-bit). GPLv2+.
# Works inside Blender's Python (numpy only, no PIL).
import struct

import numpy as np


def write(path, rgb, alpha=None):
    """rgb: HxWx3 float 0..1 or uint8, row 0 = top. alpha: HxW or None."""
    a = np.asarray(rgb)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    h, w = a.shape[:2]
    chans = [a[..., 2], a[..., 1], a[..., 0]]          # BGR
    bpp, desc = 24, 0x20                                # origin top-left
    if alpha is not None:
        al = np.asarray(alpha)
        if al.dtype != np.uint8:
            al = (np.clip(al, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        chans.append(al)
        bpp, desc = 32, 0x28
    data = np.stack(chans, axis=-1)
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, bpp, desc)
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(data.tobytes())


def read(path):
    """Returns HxWx(3|4) uint8 RGB(A), row 0 = top."""
    with open(path, "rb") as f:
        b = f.read()
    idlen, cmap, itype = b[0], b[1], b[2]
    w, h, bpp, desc = struct.unpack("<HHBB", b[12:18])
    if itype != 2 or cmap != 0:
        raise ValueError("only uncompressed true-color TGA supported: %s" % path)
    n = bpp // 8
    px = np.frombuffer(b, np.uint8, w * h * n, 18 + idlen).reshape(h, w, n)
    if not desc & 0x20:
        px = px[::-1]
    out = px[..., [2, 1, 0] + ([3] if n == 4 else [])]
    return np.ascontiguousarray(out)
