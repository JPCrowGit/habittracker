#!/usr/bin/env python3
"""One-time icon generator for the habit tracker PWA. Pure stdlib (zlib +
struct), no Pillow/ImageMagick required. Run once from repo root:

    python3 scripts/gen_icons.py

Rasterizes a rounded-square (or full-bleed) dark background with the app's
amber checkmark glyph (matches .check-btn svg.tick's path) centered, at 2x
supersample then box-downsampled for cheap antialiasing.
"""
import math
import os
import struct
import zlib

BG = (0x15, 0x12, 0x1a)
ACCENT = (0xe7, 0xa8, 0x3d)

# Checkmark glyph, from the app's 20x20 viewBox path: M4 10 L8 14 L16 5
GLYPH_SEGMENTS = [((4, 10), (8, 14)), ((8, 14), (16, 5))]
GLYPH_BBOX_CX, GLYPH_BBOX_CY = 10.0, 9.5  # center of glyph bbox (x:4-16, y:5-14)
GLYPH_BBOX_W = 12.0
GLYPH_FRAC = 0.55  # glyph width as fraction of icon size; comfortably inside an 80% maskable safe zone
STROKE_VIEWBOX_HALF = 1.5  # half of the original stroke-width (3) in viewBox units


def dist_point_segment(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    len2 = dx * dx + dy * dy
    if len2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def render(size, corner_frac, full_bleed):
    ss = 2  # supersample factor
    w = size * ss
    scale = (GLYPH_FRAC * w) / GLYPH_BBOX_W
    stroke_half = STROKE_VIEWBOX_HALF * scale
    corner_r = 0 if full_bleed else w * corner_frac

    big = bytearray(w * w * 4)
    for y in range(w):
        for x in range(w):
            idx = (y * w + x) * 4
            inside = True
            if corner_r > 0:
                cx = cy = None
                if x < corner_r and y < corner_r:
                    cx, cy = corner_r, corner_r
                elif x >= w - corner_r and y < corner_r:
                    cx, cy = w - corner_r, corner_r
                elif x < corner_r and y >= w - corner_r:
                    cx, cy = corner_r, w - corner_r
                elif x >= w - corner_r and y >= w - corner_r:
                    cx, cy = w - corner_r, w - corner_r
                if cx is not None and math.hypot(x - cx, y - cy) > corner_r:
                    inside = False

            if not inside:
                big[idx:idx + 4] = bytes((0, 0, 0, 0))
                continue

            vx = (x - w / 2) / scale + GLYPH_BBOX_CX
            vy = (y - w / 2) / scale + GLYPH_BBOX_CY
            on_glyph = False
            for (ax, ay), (bx, by) in GLYPH_SEGMENTS:
                if dist_point_segment(vx, vy, ax, ay, bx, by) * scale <= stroke_half:
                    on_glyph = True
                    break

            color = ACCENT if on_glyph else BG
            big[idx:idx + 4] = bytes(color + (255,))

    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            r = g = b = a = 0
            for dy in range(ss):
                for dx in range(ss):
                    sidx = ((y * ss + dy) * w + (x * ss + dx)) * 4
                    r += big[sidx]
                    g += big[sidx + 1]
                    b += big[sidx + 2]
                    a += big[sidx + 3]
            n = ss * ss
            oidx = (y * size + x) * 4
            out[oidx:oidx + 4] = bytes((r // n, g // n, b // n, a // n))
    return bytes(out)


def write_png(path, width, height, pixels_rgba):
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                 struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA, color type 6
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None) per scanline
        raw.extend(pixels_rgba[y * stride:(y + 1) * stride])
    idat = zlib.compress(bytes(raw), 9)
    with open(path, 'wb') as f:
        f.write(sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b''))


def main():
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icons'))
    os.makedirs(out_dir, exist_ok=True)

    specs = [
        ('icon-192.png', 192, 0.18, False),
        ('icon-512.png', 512, 0.18, False),
        ('icon-512-maskable.png', 512, 0.0, True),
        ('apple-touch-icon-180.png', 180, 0.0, True),
    ]
    for filename, size, corner_frac, full_bleed in specs:
        pixels = render(size, corner_frac, full_bleed)
        path = os.path.join(out_dir, filename)
        write_png(path, size, size, pixels)
        print(f'wrote {path} ({size}x{size})')


if __name__ == '__main__':
    main()
