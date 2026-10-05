"""Leaf-cluster atlases for the page's trees and palms (docs/plants/plan.md, phase 1).

  python tools/make_leaf_atlases.py

The CC0 leaf sheets in output/disneysea/tex/plants/ (ambientCG, LICENSES.md) hold single leaves in a grid. A tree's leaf card
needs a spray: leaves along a branched twig. This draws them with Pillow from the WebP sheets (full 8-bit alpha; the PNG
copies are 256-colour and their edges are rough) and writes:

  leaves_near.webp   2048 x 2048, 4 x 4 sprays: one row per kind (broadleaf, deciduous, pine, conifer), 4 sprays each
                     (a card of ~1 m: twig with side twigs and ~35 leaves / pine shoots with needle brushes / fir sprigs)
  leaves_far.webp    1024 x 1024, 4 x 4 clumps, rows as above (a card of ~2-3 m: many sprays heaped into a rounded clump,
                     shaded darker underneath) for the mid and far copies of the same trees
  bark_atlas_color.webp / _normal.webp   1024 x 512: grey broadleaf bark | red pine bark side by side (one material for
                     every tree kind; the page wraps the u inside each half)
  palm_atlas.webp    1024 x 1024, tiles of 256 x 512 (base at the bottom of each), top row: pinnate frond (canary palm) |
                     the same dead (tan, leaflets folded and missing) | washingtonia fan (u = round the fan, v = out from
                     the petiole: segments joined near the base, split and pointed further out) | the fan dead (straw);
                     bottom row: two bamboo sprays (hanging twigs of narrow leaves) | a second frond | a second fan
                     (phase 3, 2026-10-05; phase 1 wrote one frond, palm_frond.webp)
All the kinds share one atlas so a block of mixed trees is one leaf mesh (one draw). (Phase 2, 2026-10-05; phase 1 wrote
one 2 x 2 atlas per kind, cluster_<kind>_near/far.webp.)

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
    "conifer_sprig": (1, 3),
}
KINDS = {   # cluster kind -> leaf sheet, leaf size range in px on the 512 px spray, twig colour
    "broadleaf": ("leaf_evergreen_oval", (64, 96), (88, 74, 52)),
    "deciduous": ("leaf_deciduous_light", (56, 84), (96, 84, 64)),
}
ROWS = ["broadleaf", "deciduous", "pine", "conifer"]   # the atlas rows, top to bottom (plants.js: KROW)


def blobs(sheet, rotate, min_px=900):
    """Sheets whose items are not on a grid (pine needle bundles): connected blobs of the alpha (on a 1/4 grid), each
    cropped and turned so its base is at the bottom (`rotate` degrees counter-clockwise)."""
    im = Image.open(TEX / f"{sheet}.webp").convert("RGBA")
    a = np.asarray(im.getchannel("A").resize((im.width // 4, im.height // 4), Image.BOX)) > 10
    lab = np.zeros(a.shape, np.int32); n = 0; out = []
    for y0, x0 in zip(*np.nonzero(a)):
        if lab[y0, x0]:
            continue
        n += 1; st = [(y0, x0)]; lab[y0, x0] = n; ys = []; xs = []
        while st:
            y, x = st.pop(); ys.append(y); xs.append(x)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < a.shape[0] and 0 <= xx < a.shape[1] and a[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n; st.append((yy, xx))
        if len(ys) * 16 < min_px:
            continue
        box = (max(0, min(xs) * 4 - 4), max(0, min(ys) * 4 - 4), min(im.width, max(xs) * 4 + 8), min(im.height, max(ys) * 4 + 8))
        out.append(im.crop(box).rotate(rotate, expand=True, resample=Image.BICUBIC))
    return out


def tint(img, rgb, keep=0.2):
    """Recolour an RGBA image: its luminance times a colour (the pine needles are brown on the sheet), a little of the
    original kept."""
    a = np.asarray(img).astype(np.float32)
    lum = (a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11) / 140.0
    for i in range(3):
        a[..., i] = a[..., i] * keep + (1 - keep) * lum * rgb[i]
    a[..., :3] = a[..., :3].clip(0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def leaves(sheet, rotate=0):
    """The single leaves of a sheet: RGBA crops trimmed to their alpha (turned `rotate` degrees so the stalk is down)."""
    im = Image.open(TEX / f"{sheet}.webp").convert("RGBA")
    cols, rows = SHEETS[sheet]
    w, h = im.width // cols, im.height // rows
    out = []
    for r in range(rows):
        for c in range(cols):
            cell = im.crop((c * w, r * h, (c + 1) * w, (r + 1) * h))
            box = cell.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
            if box:
                c = cell.crop(box)
                out.append(c.rotate(rotate, expand=True, resample=Image.BICUBIC) if rotate else c)
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


def frond_tile(rng, lv, dead=False, W=256, H=512):
    """frond() at the atlas tile's size; a dead one has fewer leaflets, folded towards the rachis, straw-brown."""
    img = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(img)
    cx = W / 2
    items = []
    y = H - 14
    while y > 8:
        t = 1 - y / H
        prof = math.sin(math.pi * min(1.0, 0.10 + t * 0.95)) ** 0.7
        L = (W * 0.50) * (0.12 + 0.88 * prof)
        for side in (-1, 1):
            if dead and rng.random() < 0.3:
                continue
            a = side * (math.radians(rng.uniform(18, 30) if dead else rng.uniform(38, 55)) + 0.25 * t)
            items.append(((cx + side * 2, y), a, L * rng.uniform(0.9, 1.05) * (0.85 if dead else 1), rng.uniform(0.32, 0.45),
                          rng.uniform(0.62, 0.95)))
        y -= rng.uniform(3.5, 5)
    items.sort(key=lambda p: p[4])
    for at, a, ln, sq, k in items:
        paste_leaf(img, rng.choice(lv), at, a, ln, sq, k)
    for i in range(H - 2, 5, -2):
        t = 1 - i / H
        d.line([(cx, i), (cx, i - 2)], fill=(150, 130, 80, 255) if dead else (120, 118, 70, 255), width=max(1, int(round(5 * (1 - t) + 4))))
    return img


def fan_tile(rng, dead=False, W=256, H=512):
    """A washingtonia fan unrolled: u = round the fan, v = out from the petiole (bottom). ~34 segments, joined up to
    40-55 % of the radius with darker folds between them, then each splits off, narrows to a point (some droop
    shorter, a few with the thread-like fibres of the species between them)."""
    a = np.zeros((H, W, 4), np.float32)
    n = 34; sw = W / n
    base = np.array([0.36, 0.47, 0.25]) if not dead else np.array([0.66, 0.56, 0.38])
    yy = np.arange(H)[:, None] / H                       # 0 tip (top) .. 1 base
    r = 1 - yy                                            # 0 at the petiole .. 1 at the fan's edge
    for k in range(n):
        x0 = k * sw; c = x0 + sw / 2
        split = rng.uniform(0.38, 0.55)
        tip = rng.uniform(0.86, 0.99) if rng.random() > 0.15 else rng.uniform(0.7, 0.85)
        kk = rng.uniform(0.85, 1.12) * (1.0 if not dead else rng.uniform(0.8, 1.15))
        xs = np.arange(W)[None, :]
        # the half-width of the segment along r: the full slot up to the split, then narrowing to the tip
        hw = np.where(r < split, sw / 2 + 0.6, (sw / 2) * np.clip((tip - r) / (tip - split), 0, 1) ** 0.8)
        dx = np.abs(xs + 0.5 - c)
        cover = np.clip(hw - dx + 0.5, 0, 1) * (r < tip) * (r > 0.015)
        fold = 0.78 + 0.22 * np.cos(np.clip(dx / (sw / 2), 0, 1) * math.pi / 2)   # darker in the folds
        light = (0.82 + 0.25 * r) * kk * fold
        for i in range(3):
            a[..., i] = np.where(cover > a[..., 3], base[i] * 255 * light, a[..., i])
        a[..., 3] = np.maximum(a[..., 3], cover * 255)
    if not dead:                                          # fibres: thin pale threads hanging from the splits
        d_img = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA"); d = ImageDraw.Draw(d_img)
        for k in range(1, n):
            if rng.random() < 0.35:
                x = k * sw; y0 = H * (1 - rng.uniform(0.45, 0.6)); y1 = y0 - H * rng.uniform(0.1, 0.25)
                d.line([(x, y0), (x + rng.uniform(-3, 3), y1)], fill=(200, 196, 170, 200), width=1)
        return d_img
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def bamboo_tile(rng, lv, W=256, H=512):
    """A bamboo spray: a thin culm branch from the bottom, side twigs, narrow leaves hanging in fans of 3-6 from each node."""
    img = Image.new("RGBA", (W, H)); stems = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(stems)
    lv = [tint(l, (150, 175, 70), keep=0.35) for l in lv]
    placed = []

    def grow(x, y, ang, L, depth):
        n = 7; pts = [(x, y)]
        for i in range(n):
            ang += rng.uniform(-0.08, 0.08)
            x += math.sin(ang) * L / n; y -= math.cos(ang) * L / n; pts.append((x, y))
        twig(d, pts, 3 - depth, 1.0, (130, 140, 70))
        for i in range(2, len(pts)):
            for _ in range(rng.randint(3, 6)):
                a = math.pi + rng.uniform(-1.3, 1.3)       # hanging down and out from the node
                placed.append((pts[i], a, rng.uniform(60, 95), rng.uniform(0.5, 0.8), rng.uniform(0.62, 1.08)))
            if depth == 0 and rng.random() < 0.7:
                side = 1 if i % 2 else -1
                grow(pts[i][0], pts[i][1], ang + side * rng.uniform(0.5, 0.9), L * rng.uniform(0.3, 0.45), 1)
    grow(W / 2, H - 4, rng.uniform(-0.1, 0.1), H * 0.8, 0)
    img.alpha_composite(stems)
    placed.sort(key=lambda p: p[4])
    for at, a, ln, sq, k in placed:
        paste_leaf(img, rng.choice(lv), at, a, ln, sq, k)
    return img


def palm_atlas():
    lv = leaves("leaf_narrow_palm")
    rng = random.Random("palm-atlas")
    dead_lv = [tint(l, (175, 150, 95), keep=0.1) for l in lv[:4]]
    tiles = [frond_tile(rng, lv[:4]), frond_tile(rng, dead_lv, dead=True), fan_tile(rng), fan_tile(rng, dead=True),
             bamboo_tile(rng, lv), bamboo_tile(rng, lv), frond_tile(rng, lv[:4]), fan_tile(rng)]
    out = Image.new("RGBA", (1024, 1024))
    for i, t in enumerate(tiles):
        out.alpha_composite(t, ((i % 4) * 256, (i // 4) * 512))
    dilate(out).save(TEX / "palm_atlas.webp", quality=88, method=6)
    print("palm_atlas ok")


def pine_spray(rng, needles, S=512):
    """Black pine: a forked twig whose shoots end in brushes of needles (bundles radiating up and out from each shoot tip,
    the older needles lower down the shoot pointing out sideways)."""
    img = Image.new("RGBA", (S, S)); stems = Image.new("RGBA", (S, S)); d = ImageDraw.Draw(stems)
    col = (92, 70, 50)
    tufts = []

    def shoot(x, y, ang, L, depth):
        n = 6; pts = [(x, y)]
        for i in range(n):
            ang += rng.uniform(-0.1, 0.1)
            x += math.sin(ang) * L / n; y -= math.cos(ang) * L / n; pts.append((x, y))
        twig(d, pts, 7 - depth * 2.5, 2.5, col)
        tufts.append((x, y, ang, 1.0))
        for i in (3, 4, 5):
            tufts.append((pts[i][0], pts[i][1], ang, 0.55 + 0.1 * i / 5))
        if depth < 2:
            for side in (-1, 1):
                if rng.random() < (0.9 if depth == 0 else 0.6):
                    i = rng.randint(2, 4)
                    shoot(pts[i][0], pts[i][1], ang + side * rng.uniform(0.45, 0.85), L * rng.uniform(0.5, 0.7), depth + 1)
    shoot(S / 2 + rng.uniform(-10, 10), S - 8, rng.uniform(-0.1, 0.1), S * 0.42, 0)
    items = []
    for x, y, ang, w in tufts:
        for k in range(int(40 * w)):
            a = ang + rng.gauss(0, 0.75 if w == 1.0 else 1.0)
            ln = rng.uniform(70, 120) * (0.6 + 0.4 * w)
            items.append(((x, y), a, ln, rng.uniform(1.0, 1.4), rng.uniform(0.62, 1.08)))
    img.alpha_composite(stems)
    items.sort(key=lambda p: p[4])
    for at, a, ln, sq, k in items:
        paste_leaf(img, rng.choice(needles), at, a, ln, sq, k)
    return img


def conifer_spray(rng, sprigs, S=512):
    """Fir / cypress: a short twig fanning into flat sprigs (the long one on the axis, shorter ones either side)."""
    img = Image.new("RGBA", (S, S))
    base = (S / 2 + rng.uniform(-10, 10), S - 6)
    items = []
    for j in range(rng.randint(5, 7)):
        side = 0 if j == 0 else (1 if j % 2 else -1)
        a = side * rng.uniform(0.25, 0.75) * (1 + 0.25 * (j // 2)) + rng.uniform(-0.08, 0.08)
        a *= 0.7
        ln = S * (0.72 if j == 0 else rng.uniform(0.4, 0.55))
        off = rng.uniform(0.05, 0.3) * S if j else 0
        at = (base[0] + math.sin(a * 0.3) * off, base[1] - off)
        items.append((at, a, ln, rng.uniform(0.75, 1.0), rng.uniform(0.7, 1.05) if j else 1.05))
    items.sort(key=lambda p: p[4])
    for at, a, ln, sq, k in items:
        paste_leaf(img, rng.choice(sprigs), at, a, ln, sq, k)
    return img


def clump_of(rng, sprays, S=256, flat=1.0):
    """A far clump made of whole sprays heaped into a rounded (flat < 1: a wider, flatter pad) mass, darker inside and
    underneath, drawn at 2x and reduced. Each spray is centred on its point (not hung from it) so the middle is full."""
    B = S * 2
    img = Image.new("RGBA", (B, B))
    lobes = [(B / 2 + rng.uniform(-0.14, 0.14) * B, B * 0.5 + rng.uniform(-0.1, 0.1) * B * flat, rng.uniform(0.15, 0.22) * B) for _ in range(6)]
    items = []
    for i in range(170):
        cx, cy, R = rng.choice(lobes)
        a = rng.uniform(0, 2 * math.pi); r = R * rng.random() ** 0.5
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * flat
        rim = r / R
        k = (0.5 + 0.32 * rim) * (0.8 + 0.4 * (1 - y / B)) * rng.uniform(0.88, 1.1)
        ang = rng.uniform(-1.9, 1.9); ln = B * rng.uniform(0.16, 0.22)
        items.append((k, (x - math.sin(ang) * ln * 0.5, y + math.cos(ang) * ln * 0.5), ang, ln))
    items.sort(key=lambda t: t[0])
    for k, at, a, ln in items:
        paste_leaf(img, rng.choice(sprays), at, a, ln, 1.0, k)
    return img.resize((S, S), Image.LANCZOS)


def bark_atlas():
    """Grey broadleaf bark | red pine bark, 512 px each, for the one bark material of every tree."""
    for part in ("color", "normal"):
        out = Image.new("RGB", (1024, 512))
        for i, name in enumerate(("bark_grey", "bark_pine_red")):
            out.paste(Image.open(TEX / f"{name}_{part}.webp").convert("RGB").resize((512, 512), Image.LANCZOS), (i * 512, 0))
        out.save(TEX / f"bark_atlas_{part}.webp", quality=86, method=6)


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


def grid(tiles, S, cols=2):
    out = Image.new("RGBA", (S * cols, S * ((len(tiles) + cols - 1) // cols)))
    for i, t in enumerate(tiles):
        out.alpha_composite(t, ((i % cols) * S, (i // cols) * S))
    return out


def main():
    near, far = [], []
    for kind in ROWS:
        rng = random.Random(f"cluster-{kind}")
        if kind in KINDS:
            sheet, size_rng, col = KINDS[kind]
            lv = leaves(sheet)
            near += [spray(rng, lv, size_rng, col) for _ in range(4)]
            far += [clump(rng, lv, size_rng) for _ in range(4)]
        elif kind == "pine":
            nd = [tint(n, (58, 92, 50)) for n in blobs("pine_needles", 90)]
            sp = [pine_spray(rng, nd) for _ in range(4)]
            near += sp
            far += [clump_of(rng, sp, flat=0.62) for _ in range(4)]
        else:
            sg = leaves("conifer_sprig", -90)
            sp = [conifer_spray(rng, sg) for _ in range(4)]
            near += sp
            far += [clump_of(rng, sp, flat=0.85) for _ in range(4)]
        print(kind, "ok")
    dilate(grid(near, 512, 4)).save(TEX / "leaves_near.webp", quality=86, method=6)
    dilate(grid(far, 256, 4)).save(TEX / "leaves_far.webp", quality=86, method=6)
    bark_atlas()
    print("leaves_near / leaves_far / bark_atlas ok")
    palm_atlas()


if __name__ == "__main__":
    import sys
    palm_atlas() if sys.argv[1:] == ["palm"] else main()
