"""Leaf-cluster atlases for the page's trees and palms (docs/plants/plan.md, phase 1).

  python tools/make_leaf_atlases.py

The CC0 leaf sheets in output/disneysea/tex/plants/ (ambientCG, LICENSES.md) hold single leaves in a grid. A tree's leaf card
needs a spray: leaves along a branched twig. This draws them with Pillow from the WebP sheets (full 8-bit alpha; the PNG
copies are 256-colour and their edges are rough) and writes:

  cluster_<kind>_near.webp   1024 x 1024, 2 x 2 sprays (a card of ~0.8 m: twig with side twigs and ~35 leaves)
  cluster_<kind>_far.webp     512 x 512, 2 x 2 clumps (a card of ~2.2 m: many sprays heaped into a rounded clump, shaded
                              darker underneath) for the far copies of the same trees
  palm_frond.webp             256 x 1024, one pinnate frond (rachis up the middle, leaflets either side; base at the bottom)

The colour of transparent pixels is filled from the nearest leaf (dilation) so mipmaps do not fringe dark or white.
Deterministic (fixed seeds): running it again gives the same files.
"""
import math
import pathlib
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TEX = pathlib.Path(__file__).resolve().parent.parent / "output" / "disneysea" / "tex" / "plants"
SHEETS = {   # sheet -> (columns, rows) of single leaves, tip up, stalk down
    "leaf_evergreen_oval": (3, 2),
    "leaf_evergreen_round": (3, 3),
    "leaf_deciduous_light": (3, 2),
    "leaf_narrow_palm": (6, 1),
}
KINDS = {   # cluster kind -> leaf sheet, leaf size range in px on the 512 px spray, twig colour
    "broadleaf": ("leaf_evergreen_oval", (64, 96), (88, 74, 52)),
    "deciduous": ("leaf_deciduous_light", (56, 84), (96, 84, 64)),
}


def leaves(sheet):
    """The single leaves of a sheet: RGBA crops trimmed to their alpha."""
    im = Image.open(TEX / f"{sheet}.webp").convert("RGBA")
    cols, rows = SHEETS[sheet]
    w, h = im.width // cols, im.height // rows
    out = []
    for r in range(rows):
        for c in range(cols):
            cell = im.crop((c * w, r * h, (c + 1) * w, (r + 1) * h))
            box = cell.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
            if box:
                out.append(cell.crop(box))
    return out


def shade(img, k):
    """Darken/lighten the colour of an RGBA image by k (alpha kept)."""
    a = np.asarray(img).astype(np.float32)
    a[..., :3] = np.clip(a[..., :3] * k, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def paste_leaf(canvas, leaf, at, angle, length, squash, k):
    """A leaf with its stalk at `at`, pointing along `angle` (radians, 0 = up, + = clockwise on the image)."""
    s = length / leaf.height
    lf = leaf.resize((max(2, int(leaf.width * s * squash)), max(2, int(leaf.height * s))), Image.LANCZOS)
    lf = shade(lf, k)
    m = 2 * max(lf.width, lf.height) + 4
    big = Image.new("RGBA", (m, m))
    big.paste(lf, ((m - lf.width) // 2, m // 2 - lf.height))   # stalk (bottom centre) at the image centre
    rot = big.rotate(-math.degrees(angle), resample=Image.BICUBIC, center=(big.width / 2, big.height / 2))
    canvas.alpha_composite(rot, (int(at[0] - rot.width / 2), int(at[1] - rot.height / 2)))


def twig(draw, pts, w0, w1, col):
    for i in range(len(pts) - 1):
        w = w0 + (w1 - w0) * i / max(1, len(pts) - 2)
        draw.line([pts[i], pts[i + 1]], fill=col + (255,), width=max(1, int(round(w))))


def spray(rng, lv, size_rng, twig_col, S=512):
    """One spray: a main twig from the bottom centre with side twigs, leaves alternating along all of them."""
    img = Image.new("RGBA", (S, S))
    stems = Image.new("RGBA", (S, S)); d = ImageDraw.Draw(stems)
    placed = []   # (point, angle, length, squash, k), painted back to front
    def grow(x, y, ang, L, depth):
        n = 9; pts = [(x, y)]
        for i in range(n):
            ang += rng.uniform(-0.12, 0.12)
            x += math.sin(ang) * L / n; y -= math.cos(ang) * L / n; pts.append((x, y))
        twig(d, pts, 4 - depth * 1.5, 1.2, twig_col)
        for i in range(1, len(pts)):
            t = i / len(pts)
            for side in (-1, 1):
                for _ in range(2 if rng.random() < 0.45 else 1):
                    a = ang + side * rng.uniform(0.35, 1.25) + rng.uniform(-0.25, 0.25)
                    ln = rng.uniform(*size_rng) * (1.0 - 0.3 * t) * (0.85 if depth else 1)
                    placed.append(((pts[i][0], pts[i][1]), a, ln, rng.uniform(0.6, 1.0), rng.uniform(0.6, 1.08)))
            if depth == 0 and i in (2, 3, 4, 5, 6) and rng.random() < 0.85:
                side = 1 if i % 2 else -1
                grow(pts[i][0], pts[i][1], ang + side * rng.uniform(0.45, 0.8), L * rng.uniform(0.38, 0.52), 1)
        placed.append(((x, y), ang + rng.uniform(-0.2, 0.2), rng.uniform(*size_rng) * 0.8, 0.9, 1.0))   # the tip leaf
    grow(S / 2 + rng.uniform(-8, 8), S - 6, rng.uniform(-0.12, 0.12), S * 0.66, 0)
    img.alpha_composite(stems)
    rng.shuffle(placed)
    placed.sort(key=lambda p: p[4])   # darker (further back) first
    for at, a, ln, sq, k in placed:
        paste_leaf(img, rng.choice(lv), at, a, ln, sq, k)
    return img


def clump(rng, lv, size_rng, S=256):
    """A far clump: a rounded heap of leaves with a ragged edge, darker underneath and inside, drawn at 2x then reduced."""
    B = S * 2
    img = Image.new("RGBA", (B, B))
    lobes = [(B / 2 + rng.uniform(-0.17, 0.17) * B, B * 0.5 + rng.uniform(-0.15, 0.15) * B, rng.uniform(0.2, 0.3) * B) for _ in range(6)]
    items = []
    for i in range(900):
        cx, cy, R = rng.choice(lobes)
        a = rng.uniform(0, 2 * math.pi); r = R * rng.random() ** 0.45
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        rim = r / R                                     # 0 inside .. 1 at the edge
        k = (0.50 + 0.30 * rim) * (0.80 + 0.40 * (1 - y / B)) * rng.uniform(0.85, 1.12)
        items.append((k, (x, y), rng.uniform(0, 2 * math.pi), rng.uniform(*size_rng) * 0.42, rng.uniform(0.6, 1.0)))
    items.sort(key=lambda t: t[0])                      # darker (inner, lower) first
    for k, at, a, ln, sq in items:
        paste_leaf(img, rng.choice(lv), at, a, ln, sq, k)
    return img.resize((S, S), Image.LANCZOS)


def frond(rng, lv, W=256, H=1024):
    """A pinnate palm frond, base at the bottom: a tapering rachis and leaflets on both sides pointing up and out."""
    img = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(img)
    cx = W / 2
    items = []
    y = H - 30
    while y > 14:
        t = 1 - y / H                                  # 0 base .. 1 tip
        prof = math.sin(math.pi * min(1.0, 0.10 + t * 0.95)) ** 0.7
        L = (W * 0.50) * (0.12 + 0.88 * prof)
        for side in (-1, 1):
            a = side * (math.radians(rng.uniform(38, 55)) + 0.25 * t)
            items.append(((cx + side * 2, y), a, L * rng.uniform(0.9, 1.05), rng.uniform(0.32, 0.45), rng.uniform(0.62, 0.95)))
        y -= rng.uniform(7, 10)
    items.sort(key=lambda p: p[4])
    for at, a, ln, sq, k in items:
        paste_leaf(img, rng.choice(lv), at, a, ln, sq, k)
    for i in range(H - 2, 10, -4):                     # the rachis on top
        t = 1 - i / H
        w = 7 * (1 - t) + 1.5
        d.line([(cx, i), (cx, i - 4)], fill=(120, 118, 70, 255), width=int(round(w)))
    return img


def dilate(img, steps=24):
    """Fill the colour of transparent pixels from their neighbours (alpha untouched) so mipmaps keep leaf colours."""
    a = np.asarray(img).astype(np.float32)
    rgb, al = a[..., :3].copy(), a[..., 3]
    have = al > 8
    rgb[~have] = 0
    for _ in range(steps):
        if have.all():
            break
        acc = np.zeros_like(rgb); cnt = np.zeros(have.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(rgb * have[..., None], dy, 0), dx, 1)
            cnt += np.roll(np.roll(have, dy, 0), dx, 1)
        new = (~have) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        have = have | new
    if not have.all():
        rgb[~have] = rgb[have].mean(0)
    out = np.dstack([rgb, al]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def grid(tiles, S):
    out = Image.new("RGBA", (S * 2, S * 2))
    for i, t in enumerate(tiles):
        out.alpha_composite(t, ((i % 2) * S, (i // 2) * S))
    return out


def main():
    for kind, (sheet, size_rng, col) in KINDS.items():
        rng = random.Random(f"cluster-{kind}")
        lv = leaves(sheet)
        near = [spray(rng, lv, size_rng, col) for _ in range(4)]
        dilate(grid(near, 512)).save(TEX / f"cluster_{kind}_near.webp", quality=88, method=6)
        far = [clump(rng, lv, size_rng) for _ in range(4)]
        dilate(grid(far, 256)).save(TEX / f"cluster_{kind}_far.webp", quality=88, method=6)
        print(kind, "ok")
    rng = random.Random("palm-frond")
    dilate(frond(rng, leaves("leaf_narrow_palm")[:4])).save(TEX / "palm_frond.webp", quality=88, method=6)
    print("palm_frond ok")


if __name__ == "__main__":
    main()
