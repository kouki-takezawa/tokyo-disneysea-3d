# -*- coding: utf-8 -*-
"""kd_yubatake.py -- 草津 湯畑ジオラマ フェーズ3: 湯畑(石柵・湯樋7本・湯滝・滝壺・見学デッキ・周回路・足湯・小物)を作り yubatake.glb に書き出す。

実行(ヘッドレス Blender 5.2。他タブの Blender が動いていないことを tasklist で確認してから、1つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_yubatake.py -- [--no-export] [--out-web=DIR]
地形側(地形の穴・周回路の高さ)は kd_terrain.py を先に(または後に)流して terrain.glb を作り直す。配置と高さは kd_yb_layout.py。

完全に静止(湯の流れ・湯滝は形と色で表す。湯けむりは作らない=フェーズ11で判断)。写真・フレームはテクスチャにしない(色は頂点色)。
看板・碑の文字は動画で読めたものだけ(「草津温泉」「湯畑」の黒い石標、「手洗乃湯」の標柱)。
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, geometry  # noqa: E402

import kd_common as C  # noqa: E402
import kd_field as F  # noqa: E402
import kd_yb_layout as YB  # noqa: E402
from kd_yb_layout import rim  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
T0 = time.time()
RS = np.random.RandomState(31)


def log(*a):
    print('[yb %.1fs]' % (time.time() - T0), *a, flush=True)


def col(h, k=1.0):
    return C.tint(C.srgb(h), k)


def jit(h, a=0.08):
    return col(h, 1.0 - a + 2 * a * RS.rand())


def unit(v):
    v = np.asarray(v, float)
    return v / max(float(np.hypot(*v)), 1e-9)


def perp(u):
    return np.array([-u[1], u[0]])


# ====================================================================== 部品
def obox(mb, c, u, hx, hy, z0, z1, colr, top=True, bottom=False, zt=None, shade=True):
    """向き u の直方体(中心 c、u 方向の半長 hx、直交方向の半長 hy)。zt=(za, zb) なら上面が u 方向に傾く。"""
    c = np.asarray(c, float)
    u = unit(u)
    v = perp(u)
    P = [c - u * hx - v * hy, c + u * hx - v * hy, c + u * hx + v * hy, c - u * hx + v * hy]
    if zt is None:
        ztt = [z1] * 4
    else:
        ztt = [zt[0], zt[1], zt[1], zt[0]]
    B = [(p[0], p[1], z0) for p in P]
    T = [(P[i][0], P[i][1], ztt[i]) for i in range(4)]
    cen = (c[0], c[1], (z0 + max(ztt)) / 2)
    if top:
        mb.poly(T, colr, up=True)
    if bottom:
        mb.poly(B, C.tint(colr, 0.7), inside=(c[0], c[1], z0 + 1))
    for i in range(4):
        j = (i + 1) % 4
        k = (0.93, 1.0, 0.9, 0.97)[i] if shade else 1.0
        mb.poly([B[i], B[j], T[j], T[i]], C.tint(colr, k), inside=cen)


def prism(mb, c, r0, r1, z0, z1, n, colr, rot=0.0, top=True, bottom=False):
    """n 角の錐台(下の外接半径 r0、上 r1)。"""
    a = rot + np.arange(n) * 2 * math.pi / n
    B = [(c[0] + r0 * math.cos(t), c[1] + r0 * math.sin(t), z0) for t in a]
    T = [(c[0] + r1 * math.cos(t), c[1] + r1 * math.sin(t), z1) for t in a]
    cen = (c[0], c[1], (z0 + z1) / 2)
    for i in range(n):
        j = (i + 1) % n
        mb.poly([B[i], B[j], T[j], T[i]], C.tint(colr, 0.9 + 0.1 * ((i % 3) / 2.0)), inside=cen)
    if top and r1 > 1e-4:
        mb.poly(T, colr, up=True)
    if bottom:
        mb.poly(B, C.tint(colr, 0.7), inside=(c[0], c[1], z0 + 1))


def beam(mb, a, b, za, zb, w, h, colr):
    """平面 a→b の梁(幅 w、高さ h、上端 za→zb)。"""
    mb.box_sloped(a, b, za, zb, za - h, zb - h, 0.0, w, colr)


class IMB:
    """頂点を共有するメッシュ(岩・しぶき)。色は頂点ごと(なめらか)。"""

    def __init__(self):
        self.v = []
        self.f = []
        self.c = []
        self.n = 0

    def add(self, V, Fc, vcols):
        V = np.asarray(V, float)
        self.v.append(V)
        self.f.extend([[int(i) + self.n for i in f] for f in Fc])
        self.c.append(np.asarray(vcols, float).reshape(len(V), 3))
        self.n += len(V)

    def to_object(self, name, mat, smooth=True, coll=None):
        if not self.f:
            return None
        return C.make_object(name, np.vstack(self.v), self.f, np.vstack(self.c), 'vert', mat, smooth, coll)


# ---------------------------------------------------------------- 岩(溶岩状)
def _icosphere1():
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    Fc = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
          (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    cache = {}

    def mid(i, j):
        k = (min(i, j), max(i, j))
        if k not in cache:
            m = V[i] + V[j]
            V.append(m / np.linalg.norm(m))
            cache[k] = len(V) - 1
        return cache[k]
    F2 = []
    for a, b, c in Fc:
        ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
        F2 += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
    return np.array(V), F2, np.array(V[:12]), Fc


ICO_V, ICO_F, ICO0_V, ICO0_F = _icosphere1()
_WAVES = np.random.RandomState(5).normal(size=(6, 3))


def rock(imb, x, y, zg, sx, sy, sz, seed, base='#3d3a37', wet=0.0, white=0.0, sink=0.3):
    """丸みのある溶岩の岩。zg=接地面の高さ。wet: 緑の湯の花、white: 白い湯の花の付き具合(0..1)。"""
    rs = np.random.RandomState(seed)
    lod1 = max(sx, sy) > 0.42
    D = ICO_V if lod1 else ICO0_V
    FF = ICO_F if lod1 else ICO0_F
    n = np.zeros(len(D))
    for k in range(6):
        w = _WAVES[k] * (1.6 + k * 0.9)
        n += (0.5 ** k) * np.sin(D @ w + rs.rand() * 6.28)
    n = n / 1.6
    r = 1.0 + 0.22 * n + 0.06 * rs.normal(size=len(D))
    P = D * r[:, None] * np.array([sx, sy, sz])
    P[:, 2] = np.maximum(P[:, 2], -sz * 0.55)
    a = rs.rand() * 6.28
    ca, sa = math.cos(a), math.sin(a)
    X = P[:, 0] * ca - P[:, 1] * sa
    Y = P[:, 0] * sa + P[:, 1] * ca
    V = np.stack([X + x, Y + y, P[:, 2] + zg + sz * (1 - sink)], axis=1)
    b = np.array(C.srgb(base))
    g1 = np.array(C.srgb('#6a7f3c')); g2 = np.array(C.srgb('#97a65a')); wh = np.array(C.srgb('#d9d6c6'))
    nz = D[:, 2]
    n2 = np.sin(D @ (_WAVES[1] * 2.2) + rs.rand() * 6.28)
    n3 = np.sin(D @ (_WAVES[3] * 3.1) + rs.rand() * 6.28)
    cols = b[None, :] * (0.78 + 0.16 * n[:, None] + 0.1 * nz[:, None] + 0.08 * rs.rand())
    if wet > 0:
        m = (nz > -0.25) & (n2 > 1 - 2.2 * wet)
        gm = np.where((n3 > 0.2)[:, None], g2[None, :], g1[None, :])
        cols = np.where(m[:, None], gm * (0.85 + 0.15 * n[:, None]), cols)
    if white > 0:
        m = (nz > 0.4) & (n3 > 1 - 1.4 * white)
        cols = np.where(m[:, None], wh[None, :] * (0.92 + 0.08 * n[:, None]), cols)
    cols = np.clip(cols, 0, 1)
    imb.add(V, FF, cols)


# ---------------------------------------------------------------- 格子で面を張る(縁は多角形の線に吸着)
def fill_grid(mb, x0, x1, y0, y1, step, keep, snap, zfun, colfun):
    xs = np.arange(x0, x1 + step * 0.5, step)
    ys = np.arange(y0, y1 + step * 0.5, step)
    GX, GY = np.meshgrid(xs, ys)
    ok = keep(GX, GY).astype(bool)
    oki = ok.astype(int)
    SX, SY = GX.copy(), GY.copy()
    bad = ~ok
    if bad.any():
        sx, sy = snap(GX[bad], GY[bad])
        SX[bad] = sx; SY[bad] = sy
    Z = zfun(SX, SY)
    nj, ni = GX.shape
    cnt = 0
    for j in range(nj - 1):
        for i in range(ni - 1):
            o = oki[j, i] + oki[j, i + 1] + oki[j + 1, i] + oki[j + 1, i + 1]
            if o < 2:
                continue
            p = [(SX[j, i], SY[j, i], Z[j, i]), (SX[j, i + 1], SY[j, i + 1], Z[j, i + 1]),
                 (SX[j + 1, i + 1], SY[j + 1, i + 1], Z[j + 1, i + 1]), (SX[j + 1, i], SY[j + 1, i], Z[j + 1, i])]
            for tri, ti in (((p[0], p[1], p[2]), 0), ((p[0], p[2], p[3]), 1)):
                a = np.array(tri)
                ar = abs(np.cross(a[1] - a[0], a[2] - a[0])[2])
                if ar < 1e-4:
                    continue
                mb.poly(tri, colfun(float(a[:, 0].mean()), float(a[:, 1].mean()), 0, j, i), up=True)
                cnt += 1
    return cnt


# ---------------------------------------------------------------- 文字(読めたものだけ)
FONT = None


def load_font():
    global FONT
    for p in [r'C:\Windows\Fonts\BIZ-UDMinchoM.ttc', r'C:\Windows\Fonts\YuGothM.ttc', r'C:\Windows\Fonts\msgothic.ttc']:
        if os.path.exists(p):
            try:
                FONT = bpy.data.fonts.load(p)
                log('font', p)
                return
            except Exception as ex:
                log('font fail', p, ex)


def text_tris(body, size):
    """文字を平面の三角形に(x 右, y 上, 中心揃え)。"""
    if FONT is None:
        return [], []
    cu = bpy.data.curves.new('yb_text', type='FONT')
    cu.body = body
    cu.font = FONT
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    ob = bpy.data.objects.new('yb_text', cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    V = [(v.co.x, v.co.y) for v in me.vertices]
    T = [tuple(lt.vertices) for lt in me.loop_triangles]
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return V, T


def put_text(mb, body, size, origin, right, up, normal, colr, vertical=False):
    """面(origin、右向き right、上向き up、外向き normal)に文字を貼る。vertical=True なら1字ずつ上から下へ。"""
    origin = np.asarray(origin, float); right = np.asarray(right, float); up = np.asarray(up, float); normal = np.asarray(normal, float)
    items = [(body, 0.0)] if not vertical else [(ch, -i * size * 1.08) for i, ch in enumerate(body)]
    n = 0
    off = (len(body) - 1) * size * 1.08 / 2 if vertical else 0.0
    for txt, dy in items:
        V, T = text_tris(txt, size)
        for t in T:
            pts = [tuple(origin + right * V[k][0] + up * (V[k][1] + dy + off) + normal * 0.004) for k in t]
            mb.poly(pts, colr, inside=tuple(origin - normal * 0.5))
            n += 1
    return n


# ====================================================================== 本体の部品
class Yubatake:
    def __init__(self, field):
        self.f = field
        self.L = field.yb
        self.mb = {k: C.MB() for k in ('stone', 'wood', 'roof', 'water', 'flow', 'pave', 'dark')}
        self.rocks = IMB()
        self.stats = {}

    # -------------------------------------------------- 地面
    def ground(self, x, y):
        """周回路・広場の舗装面の高さ(地形の高さ場、+0.10 m は Yb_Pave の厚み)。"""
        return self.f.Z(x, y)

    def inner(self, x, y):
        z, k = self.L.interior(np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(y, float)))
        return z, k

    def zin(self, x, y):
        return float(self.inner(x, y)[0][0])

    # -------------------------------------------------- 湯畑の床(高さ場)
    def build_bed(self, mats, coll):
        L = self.L
        H = np.array(L.hole)
        step = 0.5
        xs = np.arange(H[:, 0].min() - 1.0, H[:, 0].max() + 1.0, step)
        ys = np.arange(H[:, 1].min() - 1.0, H[:, 1].max() + 1.0, step)
        GX, GY = np.meshgrid(xs, ys)
        cx = GX[:-1, :-1] + step / 2; cy = GY[:-1, :-1] + step / 2
        inc = L.in_hole(cx.ravel(), cy.ravel(), dilate=0.45).reshape(cx.shape)
        used = np.zeros(GX.shape, bool)
        used[:-1, :-1] |= inc; used[1:, :-1] |= inc; used[:-1, 1:] |= inc; used[1:, 1:] |= inc
        vid = -np.ones(GX.shape, int)
        vid[used] = np.arange(used.sum())
        vx = GX[used]; vy = GY[used]
        vz, kind = L.interior(vx, vy)
        # 樋の下: 緑の藻と白い湯の花の筋
        dtr = np.full(vx.shape, 99.0)
        for a, b in L.troughs:
            dtr = np.minimum(dtr, YB.seg_nearest(vx, vy, [tuple(a), tuple(b)])[0])
        n1 = C.vnoise(vx, vy, 1.3, 11); n2 = C.vnoise(vx, vy, 0.45, 12); n3 = C.vnoise(vx, vy, 3.0, 13)
        gravel_a = np.array(C.srgb('#aaa598')); gravel_b = np.array(C.srgb('#8a857b'))
        green = np.array(C.srgb('#5f7c3e')); green2 = np.array(C.srgb('#8ea551'))
        white = np.array(C.srgb('#e6e2cf')); lava = np.array(C.srgb('#46423d'))
        pave = np.array(C.srgb('#8e8b84')); basin_f = np.array(C.srgb('#3f7a70')); pool_f = np.array(C.srgb('#c8cf9e'))
        dark = np.array(C.srgb('#4b4741')); flow = np.array(C.srgb('#e8efe7'))
        t = (0.55 * n1 + 0.45 * n2)[:, None]
        c = gravel_a * (1 - t) + gravel_b * t
        wetm = ((dtr < 0.5) & (n3 > 0.55)) | (n3 > 0.88)
        c = np.where(wetm[:, None], green * (1 - n2[:, None]) + green2 * n2[:, None], c)
        whm = (n2 > 0.72) & (dtr < 1.2)
        c = np.where(whm[:, None], white * (0.92 + 0.1 * n1[:, None]), c)
        lavam = n3 < 0.2
        c = np.where(lavam[:, None], lava * (0.85 + 0.3 * n2[:, None]), c)
        # 源泉の池のまわりの盛り上がり(溶岩)
        dps = YB.sdist(vx, vy, L.pool_s)
        c = np.where(((dps > 0) & (dps < 1.4))[:, None], lava * (0.8 + 0.35 * n2[:, None]), c)
        c = np.where((kind == 1)[:, None], pool_f, c)
        c = np.where((kind == 5)[:, None], flow * (0.95 + 0.05 * n1[:, None]), c)
        # 低い側: 石の舗装(目地の色むら)、滝壺の底、東デッキの下
        tile = (np.floor(vx / 0.6) + np.floor(vy / 0.45)) % 2
        c = np.where((kind == 2)[:, None], pave * (0.86 + 0.12 * tile[:, None] + 0.08 * n2[:, None]), c)
        c = np.where((kind == 3)[:, None], basin_f, c)
        c = np.where((kind == 4)[:, None], dark * (0.85 + 0.3 * n2[:, None]), c)
        faces = []
        jj, ii = np.nonzero(inc)
        for j, i in zip(jj.tolist(), ii.tolist()):
            a, b, cc, d = vid[j, i], vid[j, i + 1], vid[j + 1, i + 1], vid[j + 1, i]
            if abs(vz[a] - vz[cc]) < abs(vz[b] - vz[d]):
                faces += [(a, b, cc), (a, cc, d)]
            else:
                faces += [(a, b, d), (b, cc, d)]
        V = np.stack([vx, vy, vz], axis=1)
        obj = C.make_object('Yb_Bed', V, faces, c, 'vert', mats['bed'], True, coll)
        self.stats['bed_tris'] = len(faces)
        return obj

    # -------------------------------------------------- 崖(床 → 滝壺)
    def build_cliff(self, mats, coll):
        L = self.L
        P, s = C.resample(L.cliff, 0.22)
        ins = L.in_hole(P[:, 0], P[:, 1], dilate=0.6)
        idx = np.nonzero(ins)[0]
        P = P[idx[0]:idx[-1] + 1]
        n = len(P)
        tan = np.zeros_like(P)
        tan[1:-1] = P[2:] - P[:-2]; tan[0] = P[1] - P[0]; tan[-1] = P[-1] - P[-2]
        tan /= np.maximum(np.hypot(*tan.T), 1e-9)[:, None]
        nor = np.stack([-tan[:, 1], tan[:, 0]], axis=1)       # 北(低い側)向き
        rows = 22
        top = L.bed(P[:, 0] - nor[:, 0] * 0.25, P[:, 1] - nor[:, 1] * 0.25) + 0.04
        lowp = P + nor * 1.6
        zlow = L.interior(lowp[:, 0], lowp[:, 1])[0]
        bot = np.minimum(zlow, YB.LOW_Z) - 0.35
        su = np.concatenate([[0], np.cumsum(np.hypot(*(P[1:] - P[:-1]).T))])
        Hm = float(np.mean(top - bot))
        # 岩の塊(丸い玉石を積んだような崖、f_3 / K 9:45)
        rs = np.random.RandomState(41)
        nb = int(su[-1] * Hm / 0.45)
        bs = rs.uniform(-0.5, su[-1] + 0.5, nb); bh = rs.uniform(-0.2, 1.0, nb) * Hm; br = rs.uniform(0.35, 0.85, nb)
        self.fall_s = []
        for xx in (7.4, 8.9, 10.4, 11.6, 13.3, 2.6):
            i = int(np.argmin(np.abs(P[:, 0] - xx) + 3 * (np.abs(P[:, 1] - 22.5) > 4)))
            if 0 < i < n - 1:
                self.fall_s.append(i)
        b = np.array(C.srgb('#6b675f')); bd = np.array(C.srgb('#3e3b37')); g1 = np.array(C.srgb('#5f7a36'))
        g2 = np.array(C.srgb('#94a650')); g3 = np.array(C.srgb('#b5b562')); wh = np.array(C.srgb('#dcd9c9'))
        G = np.zeros((rows + 1, n, 3))
        cols = np.zeros((rows + 1, n, 3))
        for r in range(rows + 1):
            v = r / rows
            h = (1 - v) * (top - bot)                       # 下からの高さ m
            d2 = ((su[:, None] - bs[None, :]) ** 2 + (h[:, None] - bh[None, :]) ** 2) / (br[None, :] ** 2)
            bump = np.sqrt(np.clip(1 - d2, 0, 1)) * br[None, :]
            k = np.argmax(bump, axis=1)
            bmax = bump[np.arange(n), k]
            above = h - bh[k]                              # 塊の上半分(藻が付く)
            off = 0.2 + 0.45 * v + 0.95 * bmax
            z = top + (bot - top) * v
            X = P + nor * off[:, None]
            G[r] = np.stack([X[:, 0], X[:, 1], z], axis=1)
            nu = C.vnoise(su, np.full(n, v * 3.0), 0.7, 21)
            gm = C.vnoise(su * 1.3, np.full(n, v * 3.5), 1.0, 23)
            crev = np.clip(1 - bmax / 0.35, 0, 1)
            cc = b * (0.78 + 0.35 * nu)[:, None]
            green = (above > -0.1 * br[k]) & (gm > 0.25 + 0.35 * v)
            gc = np.where((gm > 0.62)[:, None], g2, g1)
            gc = np.where((gm > 0.8)[:, None], g3, gc)
            cc = np.where(green[:, None], gc * (0.82 + 0.3 * nu)[:, None], cc)
            cc = np.where(((nu > 0.78) & ~green)[:, None], wh * (0.9 + 0.1 * nu)[:, None], cc)
            cc = cc * (1 - 0.55 * crev[:, None]) + bd * 0.55 * crev[:, None]
            if v > 0.82:
                cc = cc * 0.75 + bd * 0.25
            cols[r] = cc
        for i in self.fall_s:        # 湯が落ちる筋は白く濡れる
            for di in range(-2, 3):
                if 0 <= i + di < n:
                    cols[:, i + di] = cols[:, i + di] * 0.4 + wh * 0.6
        self.cliff_grid = G
        V = G.reshape(-1, 3)
        cols = cols.reshape(-1, 3)
        faces = []
        for r in range(rows):
            for i in range(n - 1):
                a = r * n + i
                faces.append((a, a + 1, a + n + 1, a + n))
        obj = C.make_object('Yb_Cliff', V, faces, cols, 'vert', mats['bed'], True, coll)
        self.cliff_pts = (P, nor, top, bot)
        self.stats['cliff_tris'] = 2 * len(faces)
        # 崖の上の丸い岩(緑・白の湯の花)
        k = 0
        for i in range(0, n, 3):
            p = P[i] - nor[i] * (0.3 + 0.5 * RS.rand())
            rock(self.rocks, p[0], p[1], float(top[i]), 0.45 + 0.35 * RS.rand(), 0.4 + 0.3 * RS.rand(), 0.3 + 0.25 * RS.rand(),
                 1000 + k, base='#4a4740', wet=0.55, white=0.25)
            k += 1
        return obj

    # -------------------------------------------------- 水
    def water_grid(self, ring, z, colfun, dil=0.45, step=0.6):
        mb = self.mb['water']
        R = np.array(ring)
        L = self.L

        def keep(x, y):
            return YB.inside(x, y, ring) | (YB.seg_nearest(x, y, ring, closed=True)[0] < dil)

        def snap(x, y):
            return x, y
        return fill_grid(mb, R[:, 0].min() - 1, R[:, 0].max() + 1, R[:, 1].min() - 1, R[:, 1].max() + 1, step,
                         keep, snap, lambda x, y: np.full(x.shape, z), colfun)

    def build_water(self):
        L = self.L
        # 滝壺: 白濁したエメラルド。湯滝の落ち口のまわりは白い泡
        em = C.srgb('#26a596'); em2 = C.srgb('#46bcab'); milky = C.srgb('#93d8c8'); foam = C.srgb('#eef5f0')
        fall = np.array(self.fall_xy)

        def cb(x, y, t, j=0, i=0):
            d = math.hypot(x - fall[0], y - fall[1])
            dc = float(YB.sdist(np.array([x]), np.array([y]), L.pool_n)[0])
            n = float(C.vnoise(x, y, 1.1, 31))
            if d < 1.3 + 0.6 * n:
                return C.tint(foam, 0.95 + 0.05 * n)
            if d < 3.2 + n:
                return milky
            k = min(1.0, -dc / 2.5) if dc < 0 else 0
            c = np.array(em2) * (1 - k) + np.array(em) * k
            return tuple(c * (0.985 + 0.03 * n))
        n1 = self.water_grid(L.pool_n, YB.BASIN_WATER, cb, dil=0.5)
        # 源泉の池: 薄い黄緑の乳白
        pc = C.srgb('#bfd28a'); pc2 = C.srgb('#cddc9f')

        def cp(x, y, t, j=0, i=0):
            n = float(C.vnoise(x, y, 1.4, 32))
            return C.tint(pc if n < 0.6 else pc2, 0.98 + 0.03 * n)
        n2 = self.water_grid(L.pool_s, YB.POOL_S_WATER, cp, dil=0.5)
        self.stats['water_tris'] = n1 + n2

    # -------------------------------------------------- 湯樋 7 本
    def build_troughs(self):
        L = self.L
        mb = self.mb['wood']
        fl = self.mb['flow']
        wood = ['#8b5a46', '#96624b', '#7d5242', '#a06a52', '#875846']
        dep = C.srgb('#d8db9f'); dep2 = C.srgb('#e9e7c8'); crust = C.srgb('#d9d5c2')
        ntri0 = len(mb.f)
        hw = YB.TR_W / 2
        for ti, (p0, p1) in enumerate(L.troughs):
            u = unit(p1 - p0)
            v = perp(u)
            Lt = float(np.hypot(*(p1 - p0)))
            s0 = float(L.tr_s(*p0))
            nseg = int(math.ceil(Lt / 3.8))
            edges = np.linspace(0, Lt, nseg + 1)
            for k in range(nseg):
                a, b = edges[k] + (0.008 if k else 0), edges[k + 1] - (0.008 if k < nseg - 1 else 0)
                za = float(L.trough_bottom(s0 + a * float(u @ L.tr_u)))
                zb = float(L.trough_bottom(s0 + b * float(u @ L.tr_u)))
                A = p0 + u * a; B = p0 + u * b
                wc = jit(wood[(ti * 3 + k) % len(wood)], 0.05)
                T = YB.TR_T
                # 外側の底
                q = lambda pt, off: (pt + v * off)
                mb.poly([(*q(A, -hw), za), (*q(B, -hw), zb), (*q(B, hw), zb), (*q(A, hw), za)], C.tint(wc, 0.6), inside=(*A, za + 1))
                for sgn in (-1, 1):
                    # 外側の側板(木目の帯 3 本)
                    hh = [0, 0.06, 0.12, YB.TR_H]
                    for h in range(3):
                        kk = (0.92, 1.0, 0.95)[(h + k + ti) % 3]
                        mb.poly([(*q(A, sgn * hw), za + hh[h]), (*q(B, sgn * hw), zb + hh[h]), (*q(B, sgn * hw), zb + hh[h + 1]), (*q(A, sgn * hw), za + hh[h + 1])],
                                C.tint(wc, kk), inside=(*A, za + 0.09))
                    # 上端(白い付着物がところどころ)
                    cc = crust if RS.rand() < 0.55 else C.tint(wc, 1.08)
                    mb.poly([(*q(A, sgn * hw), za + YB.TR_H), (*q(B, sgn * hw), zb + YB.TR_H), (*q(B, sgn * (hw - T)), zb + YB.TR_H), (*q(A, sgn * (hw - T)), za + YB.TR_H)],
                            cc, up=True)
                    # 内側の側板: 下半分は湯の花、上は濡れた木
                    mid = 0.09
                    mb.poly([(*q(A, sgn * (hw - T)), za + T), (*q(B, sgn * (hw - T)), zb + T), (*q(B, sgn * (hw - T)), zb + mid), (*q(A, sgn * (hw - T)), za + mid)],
                            C.tint(dep2, 0.95), inside=(*A, za + 1.0))
                    mb.poly([(*q(A, sgn * (hw - T)), za + mid), (*q(B, sgn * (hw - T)), zb + mid), (*q(B, sgn * (hw - T)), zb + YB.TR_H), (*q(A, sgn * (hw - T)), za + YB.TR_H)],
                            C.tint(wc, 0.72), inside=(*A, za + 1.0))
                # 内側の底: 白〜黄の湯の花(流れる湯越し)
                nm = 4
                for m in range(nm):
                    a2, b2 = a + (b - a) * m / nm, a + (b - a) * (m + 1) / nm
                    z2a = za + (zb - za) * m / nm; z2b = za + (zb - za) * (m + 1) / nm
                    A2 = p0 + u * a2; B2 = p0 + u * b2
                    cc = C.tint(dep if RS.rand() < 0.7 else dep2, 0.95 + 0.08 * RS.rand())
                    fl.poly([(*q(A2, -(hw - T)), z2a + T + 0.04), (*q(B2, -(hw - T)), z2b + T + 0.04), (*q(B2, hw - T), z2b + T + 0.04), (*q(A2, hw - T), z2a + T + 0.04)],
                            cc, up=True)
                # 継ぎ目の帯(添え木)
                if k > 0:
                    za2 = za
                    obox(mb, A, u, 0.035, hw + 0.012, za2 - 0.012, za2 + YB.TR_H + 0.005, C.tint(wc, 0.7), top=True)
            # 端の板
            for (P, zz, sg) in ((p0, float(L.trough_bottom(s0)), -1), (p0 + u * Lt, float(L.trough_bottom(s0 + Lt * float(u @ L.tr_u))), 1)):
                obox(mb, P, u, 0.02, hw, zz, zz + YB.TR_H, col('#6f4a3a'))
        self.stats['trough_tris'] = (len(mb.f) - ntri0) * 2
        # 支え: 約 2.9 m ごとに各樋の両脇の柱 + 上の横木 + 下の枕木(全部の樋をまたぐ)
        wc2 = '#7a5444'
        ss = np.arange(1.2, L.tr_len - 0.4, 2.9)
        ends0 = [L.tr_s(*p0) for p0, _ in L.troughs]
        nposts = 0
        for s in ss:
            pts = []
            for (p0, p1), e0 in zip(L.troughs, ends0):
                u = unit(p1 - p0)
                d = (s - e0) / float(u @ L.tr_u)
                pts.append((p0 + u * d, u))
            zb = float(L.trough_bottom(s))
            zt = zb + YB.TR_H
            for c0, u in pts:
                v = perp(u)
                for sg in (-1, 1):
                    pc = c0 + v * sg * (hw + 0.06)
                    zg = self.zin(*pc)
                    obox(mb, pc, u, 0.045, 0.045, zg - 0.05, zt + 0.11, jit(wc2, 0.06))
                    nposts += 1
                obox(mb, c0, v, hw + 0.13, 0.04, zt + 0.02, zt + 0.11, jit(wc2, 0.06))
            # 枕木
            a = pts[0][0] - perp(pts[0][1]) * 0.6
            b = pts[-1][0] + perp(pts[-1][1]) * 0.6
            beam(mb, a, b, zb, zb, 0.1, 0.11, jit('#6b4a3c', 0.05))
        # 始まりの分湯の木箱(源泉の池の縁)
        a = L.troughs[0][0] - perp(L.tr_u) * 0.0
        p_first = L.troughs[0][0]; p_last = L.troughs[-1][0]
        cdir = unit(p_last - p_first)
        cen = (p_first + p_last) / 2 - L.tr_u * 0.25
        hl = float(np.hypot(*(p_last - p_first))) / 2 + 0.45
        z0 = YB.TR_Z0
        obox(mb, cen, cdir, hl, 0.32, z0 - 0.35, z0 + 0.32, col('#6e4a3b'))
        pv = perp(cdir) * 0.24
        fl.poly([(*(cen - cdir * (hl - 0.08) - pv), z0 + 0.25), (*(cen + cdir * (hl - 0.08) - pv), z0 + 0.25),
                 (*(cen + cdir * (hl - 0.08) + pv), z0 + 0.25), (*(cen - cdir * (hl - 0.08) + pv), z0 + 0.25)], C.srgb('#dfe6c4'), up=True)
        self.stats['trough_posts'] = nposts

    # -------------------------------------------------- 樋の先: 集め樋・板の落とし口・湯滝へ向かう樋・湯滝の樋
    def build_outflow(self):
        L = self.L
        mb = self.mb['wood']
        fl = self.mb['flow']
        white = C.srgb('#eef3ef'); white2 = C.srgb('#dfe9e3')
        zc = float(L.trough_bottom(L.tr_len)) - 0.1          # 集め樋の底
        col_pts = np.array(L.collect)
        a, b = col_pts[0], col_pts[-1]
        b = b + unit(b - a) * 0.6
        a = a - unit(b - a) * 0.5
        cu = unit(b - a)
        cl = float(np.hypot(*(b - a)))
        cen = (a + b) / 2
        self.channel_box(cen, cu, cl / 2, 0.45, zc, zc, 0.42)
        fl.poly([(*(a + perp(cu) * 0.38), zc + 0.2), (*(b + perp(cu) * 0.38), zc + 0.2), (*(b - perp(cu) * 0.38), zc + 0.2), (*(a - perp(cu) * 0.38), zc + 0.2)],
                C.srgb('#d6e3cf'), up=True)
        nrm = -perp(cu)          # 北向き(崖の方)
        if nrm[1] < 0:
            nrm = -nrm
        # 板の落とし口(白く湯の花が付いた広い斜めの板 3 枚、R 0:48 f_17)
        for t in (0.18, 0.38, 0.58):
            p = a + cu * cl * t + nrm * 0.45
            q = p + nrm * 3.0
            ztop = zc + 0.05
            zbot = self.zin(*q) + 0.08
            self.chute(p, q, ztop, zbot, 1.05, 0.22, white2, posts=True)
        # 湯滝へ向かう樋(OSM drain)
        d0 = np.array(L.drain[0]); d1 = np.array(L.drain[-1])
        du = unit(d1 - d0)
        dl = float(np.hypot(*(d1 - d0)))
        z_a = zc - 0.02
        z_b = -0.62
        self.channel_box((d0 + d1) / 2, du, dl / 2, 0.36, z_a, z_b, 0.38)
        fl.poly([(*(d0 + perp(du) * 0.3), z_a + 0.16), (*(d1 + perp(du) * 0.3), z_b + 0.16), (*(d1 - perp(du) * 0.3), z_b + 0.16), (*(d0 - perp(du) * 0.3), z_a + 0.16)],
                white, up=True)
        for s in np.arange(0.8, dl, 2.0):
            pc = d0 + du * s
            zt = z_a + (z_b - z_a) * s / dl
            for sg in (-1, 1):
                pp = pc + perp(du) * sg * 0.45
                obox(mb, pp, du, 0.05, 0.05, self.zin(*pp) - 0.05, zt + 0.42, jit('#6e4b3c', 0.05))
            obox(mb, pc, perp(du), 0.5, 0.05, zt - 0.14, zt - 0.03, col('#6a4839'))
        # 湯滝の樋(崖を斜めに下りて滝壺へ。f_3 の左の樋)
        s0 = np.array(L.stream[0]); s1 = np.array(L.stream[-1])
        su = unit(s1 - s0)
        p = d1 - du * 0.1
        q = p + su * 3.0
        zq = -3.05
        self.chute(p, q, z_b, zq, 1.45, 0.36, white, posts=True, frame=True)
        self.fall_xy = tuple(q + su * 0.8)
        # 落ちる湯(放物線の白い帯)
        w = 1.25
        pts = []
        vx = 1.7
        for k in range(9):
            tt = k * 0.08
            pts.append((q + su * vx * tt, zq + 0.12 - 4.9 * tt * tt))
        for k in range(len(pts) - 1):
            (pa, za), (pb, zb2) = pts[k], pts[k + 1]
            if za < YB.BASIN_WATER:
                break
            zb2 = max(zb2, YB.BASIN_WATER - 0.05)
            wa = w * (1 + 0.05 * k); wb = w * (1 + 0.05 * (k + 1))
            v = perp(su)
            c1 = C.tint(white, 0.97 + 0.03 * RS.rand())
            for th, cc in ((0.0, c1), (-0.14, C.tint(white2, 0.95))):
                A1 = pa + v * wa / 2; A2 = pa - v * wa / 2; B1 = pb + v * wb / 2; B2 = pb - v * wb / 2
                fl.poly([(*A1, za + th), (*A2, za + th), (*B2, zb2 + th), (*B1, zb2 + th)], cc, inside=(*(pa - su * 1.0), za - 1.0))
                fl.poly([(*A1, za + th), (*A2, za + th), (*B2, zb2 + th), (*B1, zb2 + th)], cc, inside=(*(pa + su * 1.0), za + 1.0))
        # 落ち口のしぶき(白い盛り上がり)
        imb = IMB()
        fx, fy = self.fall_xy
        rs = np.random.RandomState(77)
        for k in range(7):
            ang = rs.rand() * 6.28
            r = 0.2 + 0.7 * rs.rand()
            x = fx + r * math.cos(ang); y = fy + r * math.sin(ang)
            D = ICO_V
            sc = np.array([0.45 + 0.3 * rs.rand(), 0.45 + 0.3 * rs.rand(), 0.25 + 0.25 * rs.rand()])
            nn = 1 + 0.25 * np.sin(D @ (_WAVES[k % 6] * 2.5) + k)
            V = D * nn[:, None] * sc + np.array([x, y, YB.BASIN_WATER - 0.05])
            V[:, 2] = np.maximum(V[:, 2], YB.BASIN_WATER - 0.08)
            imb.add(V, ICO_F, [C.tint(white, 0.93 + 0.07 * rs.rand())] * len(V))
        self.splash = imb

    def channel_box(self, cen, u, hl, hw, za, zb, h):
        """開いた木の樋(底・両側板)。za/zb は底の高さ(u の負の端/正の端)。"""
        mb = self.mb['wood']
        u = unit(u); v = perp(u)
        A = cen - u * hl; B = cen + u * hl
        wc = jit('#7b5242', 0.05)
        mb.poly([(*(A - v * hw), za - 0.04), (*(B - v * hw), zb - 0.04), (*(B + v * hw), zb - 0.04), (*(A + v * hw), za - 0.04)], C.tint(wc, 0.6), inside=(*A, za + 1))
        mb.poly([(*(A - v * hw), za + 0.02), (*(B - v * hw), zb + 0.02), (*(B + v * hw), zb + 0.02), (*(A + v * hw), za + 0.02)], C.srgb('#dcdab0'), up=True)
        for sg in (-1, 1):
            mb.box_sloped(A, B, za + h, zb + h, za - 0.04, zb - 0.04, sg * (hw - 0.025), 0.05, wc)
        obox(mb, A, u, 0.025, hw, za - 0.04, za + h, C.tint(wc, 0.85))

    def chute(self, p, q, ztop, zbot, width, side_h, flow_col, posts=True, frame=False):
        """斜めの板の樋(底板・側板・中の白い湯)。p 上端、q 下端。"""
        mb = self.mb['wood']
        fl = self.mb['flow']
        p = np.asarray(p, float); q = np.asarray(q, float)
        u = unit(q - p); v = perp(u)
        hw = width / 2
        wc = jit('#806050', 0.05)
        mb.poly([(*(p - v * hw), ztop - 0.06), (*(q - v * hw), zbot - 0.06), (*(q + v * hw), zbot - 0.06), (*(p + v * hw), ztop - 0.06)], C.tint(wc, 0.55),
                inside=(*p, ztop + 2))
        for sg in (-1, 1):
            mb.box_sloped(p, q, ztop + side_h, zbot + side_h, ztop - 0.06, zbot - 0.06, sg * (hw + 0.03), 0.06, wc)
        nseg = 6
        for k in range(nseg):
            a = p + (q - p) * k / nseg; b = p + (q - p) * (k + 1) / nseg
            za = ztop + (zbot - ztop) * k / nseg; zb = ztop + (zbot - ztop) * (k + 1) / nseg
            fl.poly([(*(a - v * hw), za + 0.05), (*(b - v * hw), zb + 0.05), (*(b + v * hw), zb + 0.05), (*(a + v * hw), za + 0.05)],
                    C.tint(flow_col, 0.95 + 0.06 * RS.rand()), up=True)
        if posts:
            L = float(np.hypot(*(q - p)))
            for s in np.arange(0.6, L - 0.2, 1.2):
                pc = p + u * s
                zt = ztop + (zbot - ztop) * s / L - 0.06
                for sg in (-1, 1):
                    pp = pc + v * sg * (hw + 0.1)
                    zg = self.zin(*pp)
                    if zt - zg > 0.15:
                        obox(mb, pp, u, 0.05, 0.05, zg - 0.1, zt + side_h + 0.05, jit('#6a4a3b', 0.05))
        if frame:
            # 上の木の枠(柱 2 本と横木 2 本、f_3)
            for sg in (-1, 1):
                pp = p + u * 0.25 + v * sg * (hw + 0.12)
                obox(mb, pp, u, 0.07, 0.07, ztop - 0.5, ztop + 1.25, jit('#6e4e3e', 0.04))
            for zz in (ztop + 0.85, ztop + 1.2):
                beam(mb, p + u * 0.25 - v * (hw + 0.3), p + u * 0.25 + v * (hw + 0.3), zz, zz, 0.12, 0.12, col('#6a4a3a'))
            beam(mb, p - u * 0.2 + v * (hw + 0.12), p + u * 1.0 + v * (hw + 0.12), ztop + 1.2, ztop + 1.0, 0.1, 0.1, col('#6a4a3a'))
            beam(mb, p - u * 0.2 - v * (hw + 0.12), p + u * 1.0 - v * (hw + 0.12), ztop + 1.2, ztop + 1.0, 0.1, 0.1, col('#6a4a3a'))

    def build_small_falls(self):
        """崖を流れ落ちる細い湯滝(白い筋、f_3 の中央〜右)。崖の面に沿って 7 cm 浮かせる。"""
        P, nor, top, bot = self.cliff_pts
        G = self.cliff_grid
        fl = self.mb['flow']
        white = C.srgb('#eef3ee'); white2 = C.srgb('#d5e4dc')
        widths = [0.5, 0.35, 0.7, 0.4, 0.3, 0.3]
        rows = G.shape[0] - 1
        for i, w in zip(self.fall_s, widths):
            t = np.array([-nor[i][1], nor[i][0]])
            for r in range(rows):
                def pt(rr, side):
                    q = G[rr, i]
                    vv = rr / rows
                    p = q[:2] + nor[i] * 0.07 + t * side * w * (0.5 + 0.3 * vv)
                    return (p[0], p[1], max(q[2], YB.BASIN_WATER - 0.02))
                if G[r, i][2] < YB.BASIN_WATER:
                    break
                cc = C.tint(white if (r % 3) else white2, 0.95 + 0.05 * RS.rand())
                fl.poly([pt(r, -1), pt(r, 1), pt(r + 1, 1), pt(r + 1, -1)], cc, inside=(*(P[i] - nor[i] * 0.5), top[i] - 1.0))

    # -------------------------------------------------- 石垣(穴の縁の擁壁)と石の欄干
    def build_walls(self):
        L = self.L
        mb = self.mb['stone']
        H = L.hole
        n = len(H)
        mortar = col('#5a5751')
        stones = ['#8f8c84', '#7d7a73', '#9b978d', '#6f6c66', '#a29d92']
        nblk = 0
        for i in range(n):
            a = np.array(H[i]); b = np.array(H[(i + 1) % n])
            seg = float(np.hypot(*(b - a)))
            if seg < 0.05:
                continue
            u = unit(b - a)
            out = np.array([u[1], -u[0]])          # ccw の外向き
            m = max(1, int(math.ceil(seg / 0.9)))
            for k in range(m):
                pa = a + (b - a) * k / m; pb = a + (b - a) * (k + 1) / m
                zo = [float(self.f.Z(*(pp + out * 0.7))) + 0.1 for pp in (pa, pb)]
                zi = [self.zin(*(pp - out * 0.9)) for pp in (pa, pb)]
                top = [max(zo[0], zi[0] + 0.15), max(zo[1], zi[1] + 0.15)]
                botm = [min(zo[0], zi[0]) - 0.3, min(zo[1], zi[1]) - 0.3]
                # 壁の本体(内側の面は目地の色、外側は見えにくい)
                ia, ib = pa - out * 0.45, pb - out * 0.45
                mb.poly([(*ia, botm[0]), (*ib, botm[1]), (*ib, top[1]), (*ia, top[0])], mortar, inside=(*((pa + pb) / 2 + out * 0.3), (top[0] + botm[0]) / 2))
                mb.poly([(*pa, botm[0]), (*pb, botm[1]), (*pb, top[1]), (*pa, top[0])], C.tint(mortar, 1.1), inside=(*((pa + pb) / 2 - out * 1.0), (top[0] + botm[0]) / 2))
                mb.poly([(*ia, top[0]), (*ib, top[1]), (*pb, top[1]), (*pa, top[0])], col('#8a877f'), up=True)
                # 石積み(内側の面に 1〜2 個ずつ、段ごとに継ぎ目をずらす)
                zlo = min(zi) + 0.0
                zhi = max(top)
                if zhi - zlo < 0.2:
                    continue
                row_h = 0.31
                r = 0
                z = zlo - 0.05
                while z < zhi - 0.06:
                    z2 = z + row_h * (0.85 + 0.3 * RS.rand())
                    cuts = [0.0, 1.0] if RS.rand() < 0.45 else [0.0, 0.3 + 0.4 * RS.rand(), 1.0]
                    for c in range(len(cuts) - 1):
                        t0, t1 = cuts[c], cuts[c + 1]
                        q0 = ia + (ib - ia) * t0 - out * 0.0; q1 = ia + (ib - ia) * t1
                        tz0 = top[0] + (top[1] - top[0]) * t0; tz1 = top[0] + (top[1] - top[0]) * t1
                        za0, za1 = z + 0.015, min(z2 - 0.015, tz0 - 0.02)
                        zb0, zb1 = z + 0.015, min(z2 - 0.015, tz1 - 0.02)
                        if za1 - za0 < 0.05 and zb1 - zb0 < 0.05:
                            continue
                        rel = 0.012 + 0.03 * RS.rand()
                        g = 0.018
                        qa = q0 + (q1 - q0) * 0.0 + unit(q1 - q0) * g - out * rel
                        qb = q1 - unit(q1 - q0) * g - out * rel
                        mb.poly([(*qa, za0), (*qb, zb0), (*qb, zb1), (*qa, za1)], jit(stones[RS.randint(len(stones))], 0.06),
                                inside=(*((pa + pb) / 2 + out * 0.5), z))
                        nblk += 1
                    z = z2
                    r += 1
        self.stats['wall_blocks'] = nblk

    def build_balustrade(self):
        """石の欄干(地覆・親柱・束(名前の札付き)・笠木)。K 7:36 f_153、S 4:30 f_91。"""
        L = self.L
        mb = self.mb['stone']
        dk = self.mb['dark']
        H = L.hole
        n = len(H)
        gran = '#a19e96'; gran2 = '#928f87'; post = '#aaa79f'; plaque = col('#2f2f30')
        # 欄干の区間をつなげた折れ線ごとに
        runs, cur = [], []
        for i in range(n):
            if L.hole_kind[i] == 'balustrade':
                if not cur:
                    cur = [H[i]]
                cur.append(H[(i + 1) % n])
            else:
                if cur:
                    runs.append(cur); cur = []
        if cur:
            runs.append(cur)
        nb = 0
        for run in runs:
            P, s = C.resample(run, 0.05)
            total = s[-1]
            nsec = max(1, int(round(total / 1.8)))
            sec = total / nsec
            cum = s

            def at(d):
                d = min(max(d, 0), total)
                x = np.interp(d, cum, P[:, 0]); y = np.interp(d, cum, P[:, 1])
                return np.array([x, y])

            def dirat(d):
                return unit(at(min(d + 0.2, total)) - at(max(d - 0.2, 0)))
            for k in range(nsec + 1):
                d = k * sec
                pc = at(d); u = dirat(d); out = np.array([u[1], -u[0]])
                pc = pc + out * 0.05
                z0 = float(rim(*pc)) + 0.10
                # 親柱
                obox(mb, pc, u, 0.14, 0.14, z0 + 0.18, z0 + 0.98, jit(post, 0.04))
                prism(mb, pc, 0.14 * 1.41, 0.04, z0 + 0.98, z0 + 1.05, 4, jit(post, 0.04), rot=math.atan2(u[1], u[0]) + math.pi / 4, top=False)
                if k == nsec:
                    break
                # 地覆(1 区間 1 本、継ぎ目 1 cm)
                da, db = d + 0.005, d + sec - 0.005
                A = at(da) + out * 0.05; B = at(db) + out * 0.05
                za, zb = float(rim(*A)) + 0.10, float(rim(*B)) + 0.10
                mb.box_sloped(A, B, za + 0.18, zb + 0.18, za - 0.05, zb - 0.05, 0.0, 0.36, jit(gran2, 0.05))
                # 笠木(上が丸い: 中央を高く)
                A2 = at(d + 0.14) + out * 0.05; B2 = at(d + sec - 0.14) + out * 0.05
                za2, zb2 = float(rim(*A2)) + 0.10, float(rim(*B2)) + 0.10
                cg = jit(gran, 0.04)
                mb.box_sloped(A2, B2, za2 + 0.88, zb2 + 0.88, za2 + 0.74, zb2 + 0.74, 0.0, 0.25, cg)
                v = perp(unit(B2 - A2))
                mb.poly([(*(A2 + v * 0.125), za2 + 0.88), (*(B2 + v * 0.125), zb2 + 0.88), (*(B2 + v * 0.03), zb2 + 0.93), (*(A2 + v * 0.03), za2 + 0.93)], cg, up=True)
                mb.poly([(*(A2 - v * 0.03), za2 + 0.93), (*(B2 - v * 0.03), zb2 + 0.93), (*(B2 - v * 0.125), zb2 + 0.88), (*(A2 - v * 0.125), za2 + 0.88)], cg, up=True)
                mb.poly([(*(A2 + v * 0.03), za2 + 0.93), (*(B2 + v * 0.03), zb2 + 0.93), (*(B2 - v * 0.03), zb2 + 0.93), (*(A2 - v * 0.03), za2 + 0.93)], C.tint(cg, 1.04), up=True)
                # 束(3 本、外側の面に名前の黒い札)
                nbal = 4
                for j in range(nbal):
                    dd = d + sec * (j + 1) / (nbal + 1)
                    q = at(dd) + out * 0.05; uu = dirat(dd); oo = np.array([uu[1], -uu[0]])
                    zq = float(rim(*q)) + 0.10
                    obox(mb, q, uu, 0.085, 0.075, zq + 0.18, zq + 0.74, jit(gran, 0.05), top=False)
                    pq = q + oo * 0.078
                    dk.poly([(*(pq - uu * 0.035), zq + 0.30), (*(pq + uu * 0.035), zq + 0.30), (*(pq + uu * 0.035), zq + 0.66), (*(pq - uu * 0.035), zq + 0.66)],
                            plaque, inside=(*(q - oo), zq + 0.5))
                    nb += 1
            # 外側の足元の側溝の蓋(黒い格子の帯、S f_91)
            for k in range(len(P) - 1):
                if k % 8:
                    continue
                k2 = min(k + 8, len(P) - 1)
                A = P[k]; B = P[k2]
                if np.hypot(*(B - A)) < 0.05:
                    continue
                uu = unit(B - A); oo = np.array([uu[1], -uu[0]])
                za, zb = float(rim(*A)) + 0.10, float(rim(*B)) + 0.10
                dk.poly([(*(A + oo * 0.26), za + 0.015), (*(B + oo * 0.26), zb + 0.015), (*(B + oo * 0.46), zb + 0.015), (*(A + oo * 0.46), za + 0.015)],
                        col('#3a3a3b'), up=True)
        self.stats['balusters'] = nb

    # -------------------------------------------------- 周回路(石畳)と車道
    def build_pave(self):
        L = self.L
        mb = self.mb['pave']
        R = np.array(L.loop_out)
        hole = L.hole
        loop_c = L.loop
        mid = col('#8b8883'); dark = col('#6e6b67'); light = col('#a3a098'); rust = col('#83695c')
        asph = col('#424346')

        def keep(x, y):
            return YB.inside(x, y, L.loop_out) & ~YB.inside(x, y, hole)

        def snap(x, y):
            ih = YB.inside(x, y, hole)
            _, hx, hy, _, _ = YB.seg_nearest(x, y, hole, closed=True)
            _, ox, oy, _, _ = YB.seg_nearest(x, y, L.loop_out, closed=True)
            return np.where(ih, hx, ox), np.where(ih, hy, oy)

        def zf(x, y):
            return self.f.Z(x, y) + 0.10

        x0, y0 = R[:, 0].min(), R[:, 1].min()
        xs = np.arange(x0, R[:, 0].max() + 0.25, 0.5) + 0.25
        ys = np.arange(y0, R[:, 1].max() + 0.25, 0.5) + 0.25
        CXg, CYg = np.meshgrid(xs, ys)
        DL = YB.seg_nearest(CXg.ravel(), CYg.ravel(), loop_c, closed=True)[0].reshape(CXg.shape)

        def cf(x, y, t, j, i):
            dl = float(DL[min(j, DL.shape[0] - 1), min(i, DL.shape[1] - 1)])
            n = float(C.hash_noise(round(x * 2) + t * 0.37, round(y * 2), 3))
            if dl < 3.0:
                return C.tint(asph, 0.92 + 0.12 * n)
            # 波模様: ゆがんだ縞を 2 組重ねる
            w1 = math.sin((x * 0.8 + 1.6 * math.sin(y * 0.33 + 0.5)) * 2.6 + t * 0.6)
            w2 = math.sin((y * 0.7 + 1.4 * math.sin(x * 0.29)) * 2.2 - t * 0.5)
            if w1 > 0.82 or w2 > 0.9:
                return C.tint(dark, 0.9 + 0.15 * n)
            if w1 < -0.85:
                return C.tint(light, 0.95 + 0.08 * n)
            if C.vnoise(x, y, 7.0, 4) > 0.72 and w2 < -0.75:
                return C.tint(rust, 0.92 + 0.12 * n)
            return C.tint(mid, 0.95 + 0.07 * n)
        cnt = fill_grid(mb, R[:, 0].min(), R[:, 0].max(), R[:, 1].min(), R[:, 1].max(), 0.5, keep, snap, zf, cf)
        # 車道の白線(周回路側の縁)
        line = YB.offset_ring(loop_c, -2.75, 0.8)
        lw = col('#e9e8e2')
        for k in range(len(line)):
            A = np.array(line[k]); B = np.array(line[(k + 1) % len(line)])
            if YB.inside(np.array([A[0]]), np.array([A[1]]), hole)[0]:
                continue
            uu = unit(B - A); v = perp(uu)
            za = float(self.f.Z(*A)) + 0.115; zb = float(self.f.Z(*B)) + 0.115
            mb.poly([(*(A - v * 0.075), za), (*(B - v * 0.075), zb), (*(B + v * 0.075), zb), (*(A + v * 0.075), za)], lw, up=True)
        self.stats['pave_tris'] = cnt

    def build_bollards(self):
        L = self.L
        dk = self.mb['dark']
        line = YB.offset_ring(L.loop, -3.35, 2.2)
        n = 0
        for p in line:
            p = np.array(p)
            if p[1] > 14 or YB.seg_nearest(np.array([p[0]]), np.array([p[1]]), L.hole, closed=True)[0][0] < 1.5:
                continue
            z = float(self.f.Z(*p)) + 0.1
            prism(dk, p, 0.065, 0.065, z, z + 0.62, 8, col('#262626'))
            prism(dk, p, 0.066, 0.066, z + 0.62, z + 0.68, 8, col('#a32a22'))
            prism(dk, p, 0.065, 0.05, z + 0.68, z + 0.76, 8, col('#262626'))
            n += 1
        self.stats['bollards'] = n

    def build_guardrail(self):
        """白いガードレール(西の柵 954629649 沿い、車道側)。"""
        L = self.L
        mb = self.mb['stone']
        run = [H for H, k in zip(L.hole, L.hole_kind) if k == 'guard']
        pts = np.array(L.ways[YB.W_FENCE_W])
        P, s = C.resample(pts, 0.5)
        white = col('#ecebe6')
        for k in range(0, len(P) - 1):
            A, B = P[k], P[k + 1]
            uu = unit(B - A); out = -perp(uu)
            if out[0] > 0:
                out = -out           # 西(車道)側へ
            A2, B2 = A + out * 0.25, B + out * 0.25
            za, zb = float(self.f.Z(*A2)) + 0.1, float(self.f.Z(*B2)) + 0.1
            mb.box_sloped(A2, B2, za + 0.78, zb + 0.78, za + 0.5, zb + 0.5, 0.0, 0.05, white)
            if k % 4 == 0:
                obox(mb, A2 + out * 0.08, uu, 0.05, 0.05, za - 0.05, za + 0.72, white)

    # -------------------------------------------------- 木の柵(デッキ・階段)
    def rail(self, pts, zfun, h=1.05, spacing=1.8, close=False, caps=True):
        """木の手すり(柱+笠木+中の横板 2 本)。pts: 平面の折れ線、zfun(p)->床の高さ。"""
        mb = self.mb['wood']
        wc = '#6d5546'
        P, s = C.resample(list(pts) + ([pts[0]] if close else []), 0.25)
        total = s[-1]
        if total < 0.3:
            return
        nsec = max(1, int(math.ceil(total / spacing)))
        ds = np.linspace(0, total, nsec + 1)
        at = lambda d: np.array([np.interp(d, s, P[:, 0]), np.interp(d, s, P[:, 1])])
        for k, d in enumerate(ds):
            p = at(d)
            u = unit(at(min(d + 0.1, total)) - at(max(d - 0.1, 0)))
            z = zfun(p)
            obox(mb, p, u, 0.065, 0.065, z - 0.05, z + h + 0.06, jit(wc, 0.05))
            if caps:
                prism(mb, p, 0.1, 0.0, z + h + 0.06, z + h + 0.16, 4, col('#5c473a'), rot=math.atan2(u[1], u[0]) + math.pi / 4, top=False)
            if k == len(ds) - 1:
                break
            # 区間の笠木と横板
            sub = max(1, int(math.ceil((ds[k + 1] - d) / 0.6)))
            for m in range(sub):
                a = at(d + (ds[k + 1] - d) * m / sub); b = at(d + (ds[k + 1] - d) * (m + 1) / sub)
                za, zb = zfun(a), zfun(b)
                mb.box_sloped(a, b, za + h, zb + h, za + h - 0.06, zb + h - 0.06, 0.0, 0.12, jit('#76604f', 0.04))
                for hh in (0.62, 0.32):
                    mb.box_sloped(a, b, za + hh + 0.1, zb + hh + 0.1, za + hh, zb + hh, 0.0, 0.035, jit(wc, 0.05))

    def planks(self, poly, z, ang, pw=0.15, colh='#7a6352'):
        """板張りの床(多角形、板の向き ang、上面だけ+縁の板)。"""
        mb = self.mb['wood']
        R = np.array(poly)
        u = np.array([math.cos(ang), math.sin(ang)]); v = perp(u)
        cu = R @ u; cv = R @ v
        rows = np.arange(cv.min(), cv.max() + pw, pw)
        rs = np.random.RandomState(int(abs(z) * 100) + len(poly))
        cnt = 0
        for k in range(len(rows) - 1):
            v0, v1 = rows[k] + 0.006, rows[k + 1] - 0.006
            # その板の帯と多角形の交わり(u 方向の区間)
            samples = np.linspace(cu.min() - 0.1, cu.max() + 0.1, 160)
            vm = (v0 + v1) / 2
            X = samples[:, None] * u + vm * v
            ins = YB.inside(X[:, 0], X[:, 1], poly)
            if not ins.any():
                continue
            idx = np.nonzero(ins)[0]
            # 連続した区間ごと
            starts = [idx[0]]
            ends = []
            for a, b in zip(idx[:-1], idx[1:]):
                if b != a + 1:
                    ends.append(a); starts.append(b)
            ends.append(idx[-1])
            for a, b in zip(starts, ends):
                u0, u1 = samples[a], samples[b]
                c = jit(colh, 0.08)
                P = [u0 * u + v0 * v, u1 * u + v0 * v, u1 * u + v1 * v, u0 * u + v1 * v]
                mb.poly([(p[0], p[1], z) for p in P], c, up=True)
                cnt += 1
        # 縁(鼻隠しの板)
        n = len(poly)
        for i in range(n):
            a = np.array(poly[i]); b = np.array(poly[(i + 1) % n])
            mb.box_sloped(a, b, z, z, z - 0.22, z - 0.22, 0.0, 0.04, col('#5d4a3d'))
        return cnt

    def deck_posts(self, poly, z, grid=1.8):
        mb = self.mb['wood']
        R = np.array(poly)
        for x in np.arange(R[:, 0].min() + 0.3, R[:, 0].max(), grid):
            for y in np.arange(R[:, 1].min() + 0.3, R[:, 1].max(), grid):
                if YB.inside(np.array([x]), np.array([y]), poly)[0]:
                    zg = self.zin(x, y)
                    if z - zg > 0.3:
                        obox(mb, (x, y), (1, 0), 0.07, 0.07, zg - 0.1, z - 0.04, jit('#5b4739', 0.05))
                        beam(mb, (x - 0.9, y), (x + 0.9, y), z - 0.04, z - 0.04, 0.1, 0.16, col('#5b4739'))

    def stair(self, p_low, p_high, z_low, z_high, width, n=None, rails=(True, True), riser=0.175, tread=0.28):
        """木の階段(踏板・蹴込み・ささら桁・束・両側の手すり)。p_low→p_high の直線。"""
        mb = self.mb['wood']
        p_low = np.asarray(p_low, float); p_high = np.asarray(p_high, float)
        u = unit(p_high - p_low); v = perp(u)
        L = float(np.hypot(*(p_high - p_low)))
        n = n or max(2, int(round((z_high - z_low) / riser)))
        rz = (z_high - z_low) / n
        tr = min(tread, L / n)
        run = tr * n
        hw = width / 2
        for i in range(n):
            s0 = i * tr; s1 = s0 + tr + 0.03
            zt = z_low + (i + 1) * rz
            c = p_low + u * (s0 + s1) / 2
            obox(mb, c, u, (s1 - s0) / 2, hw, zt - 0.05, zt, jit('#7a6352', 0.07))
            # 蹴込み
            a = p_low + u * s0
            mb.poly([(*(a - v * hw), zt - rz), (*(a + v * hw), zt - rz), (*(a + v * hw), zt - 0.05), (*(a - v * hw), zt - 0.05)], col('#4f3f34'),
                    inside=(*(a + u), zt))
        pe = p_low + u * run
        for sg in (-1, 1):
            mb.box_sloped(p_low, pe, z_low + 0.12, z_high + 0.12, z_low - 0.25, z_high - 0.25, sg * (hw + 0.04), 0.08, col('#5e4a3c'))
        # 束
        for s in np.arange(0.9, run, 1.8):
            for sg in (-1, 1):
                pp = p_low + u * s + v * sg * (hw + 0.04)
                zg = self.zin(*pp)
                zz = z_low + (z_high - z_low) * s / run - 0.25
                if zz - zg > 0.2:
                    obox(mb, pp, u, 0.06, 0.06, zg - 0.1, zz, jit('#5b4739', 0.05))
        zf = lambda p: z_low + (z_high - z_low) * float(np.clip(((p - p_low) @ u) / run, 0, 1))
        for sg, on in zip((-1, 1), rails):
            if on:
                self.rail([tuple(p_low + v * sg * (hw + 0.06)), tuple(pe + v * sg * (hw + 0.06))], zf, h=0.95, spacing=1.6)
        return pe, run

    def build_decks(self):
        L = self.L
        # 西: 滝壺の脇のデッキ(下)→ 長い木の階段 → 上の通路(北西の車道へ)。OSM 898032021 / 954629651
        sw = np.array(L.steps_w)
        p_bot, p_top = sw[0], sw[-1]
        u = unit(p_top - p_bot); v = perp(u)
        land = p_bot + u * 0.9
        pe, run = self.stair(land, p_top, YB.WDECK_Z, YB.WALK_Z, 2.0)
        # 上の通路
        walk = [tuple(pe - v * 1.05), tuple(p_top - v * 1.05 + u * 0.4), tuple(p_top + v * 1.05 + u * 0.4), tuple(pe + v * 1.05)]
        self.planks(walk, YB.WALK_Z, math.atan2(v[1], v[0]))
        self.deck_posts(walk, YB.WALK_Z, grid=1.6)
        self.rail([tuple(pe - v * 1.1), tuple(p_top - v * 1.1)], lambda p: YB.WALK_Z)
        self.rail([tuple(pe + v * 1.1), tuple(p_top + v * 1.1)], lambda p: YB.WALK_Z)
        # 下のデッキ(階段の下 → 滝壺の西岸 → 北の通路)
        b2 = np.array(L.ways[954629651])
        q0, q1 = b2[0], b2[-1]
        uu = unit(q1 - q0); vv = perp(uu)
        ext = q1 + uu * 0.6
        low = [tuple(land + u * 0.3 - v * 1.2), tuple(p_bot - u * 0.4 - v * 1.2), tuple(q0 - uu * 0.6 + vv * 1.15 - v * 0.3),
               tuple(ext + vv * 1.15), tuple(ext - vv * 1.15), tuple(q0 - vv * 1.15 + uu * 0.5), tuple(land + u * 0.3 + v * 1.2)]
        low = C.ccw(low)
        self.planks(low, YB.WDECK_Z, math.atan2(uu[1], uu[0]) + math.pi / 2)
        self.deck_posts(low, YB.WDECK_Z, grid=1.6)
        # 水の側の手すり
        side = -vv if (np.array(L.pool_n).mean(axis=0) - q0) @ vv < 0 else vv
        self.rail([tuple(q0 + side * 1.2 - uu * 0.4), tuple(ext + side * 1.2)], lambda p: YB.WDECK_Z)
        # 東の見学デッキ(中段)と2本の階段(OSM 898032023 / 898032022)
        self.planks(L.edeck, YB.EDECK_Z, math.pi / 2)
        self.deck_posts(L.edeck, YB.EDECK_Z)
        se = np.array(L.steps_e)            # [下 (23.6,23.8), 上 (21.7,16.4)]
        sb, st = se[0], se[-1]
        ue = unit(st - sb)
        ztop = float(self.f.Z(*st)) + 0.1
        nst = int(round((ztop - YB.EDECK_Z) / 0.175))
        runE = nst * 0.28
        start = st - ue * runE
        self.stair(start, st, YB.EDECK_Z, ztop, 1.6, n=nst)
        # 北の階段: デッキの北の縁 → 低い通路
        ne_top = np.array([22.25, 31.0]); ne_bot = np.array([22.3, 34.9])
        nn = int(round((YB.EDECK_Z - YB.LOW_Z) / 0.175))
        un = unit(ne_bot - ne_top)
        self.stair(ne_top + un * (nn * 0.28), ne_top, YB.LOW_Z, YB.EDECK_Z, 1.4, n=nn)
        # デッキの柵(内側=崖の側、外側=車道の側)
        fin = L.fence_edeck_in
        self.rail(fin[1:5], lambda p: YB.EDECK_Z)
        eo = L.ways[YB.W_FENCE_EDECK_OUT]
        self.rail([eo[0], eo[1], eo[2]], lambda p: YB.EDECK_Z)
        self.rail([(25.45, 31.0), (23.1, 31.0)], lambda p: YB.EDECK_Z)
        # 東デッキの外側の板塀(車道側、下の空間を隠す)
        mb = self.mb['wood']
        for k in range(len(eo) - 1):
            a, b = np.array(eo[k]), np.array(eo[k + 1])
            za = min(float(self.f.Z(*a)), YB.EDECK_Z) - 0.3
            zb = min(float(self.f.Z(*b)), YB.EDECK_Z) - 0.3
            mb.box_sloped(a, b, YB.EDECK_Z - 0.02, YB.EDECK_Z - 0.02, za, zb, 0.0, 0.05, col('#5a4637'))
        # 北の通路の木柵(滝壺の北岸、OSM 954629668)と北の柵
        self.rail(L.fence_pond_n, lambda p: YB.LOW_Z, h=1.0)
        self.rail(L.ways[YB.W_FENCE_N], lambda p: YB.LOW_Z, h=1.0)

    # -------------------------------------------------- 石灯籠
    def lantern(self, x, y, zg, H):
        mb = self.mb['stone']
        s = H / 3.05
        c = (x, y)
        g1 = '#5f5d58'; g2 = '#6e6b65'
        prism(mb, c, 0.55 * s, 0.5 * s, zg, zg + 0.3 * s, 6, jit(g1, 0.05))
        prism(mb, c, 0.32 * s, 0.2 * s, zg + 0.3 * s, zg + 0.42 * s, 6, jit(g2, 0.05))
        prism(mb, c, 0.17 * s, 0.15 * s, zg + 0.42 * s, zg + 1.5 * s, 10, jit(g1, 0.05))
        prism(mb, c, 0.2 * s, 0.2 * s, zg + 0.9 * s, zg + 0.96 * s, 10, jit(g2, 0.05))
        prism(mb, c, 0.26 * s, 0.4 * s, zg + 1.5 * s, zg + 1.75 * s, 6, jit(g2, 0.05))
        prism(mb, c, 0.29 * s, 0.29 * s, zg + 1.75 * s, zg + 2.2 * s, 6, jit(g1, 0.05))
        # 火袋の窓(暗い)
        dk = self.mb['dark']
        for k in (0, 3):
            a = k * math.pi / 3 + math.pi / 6
            nrm = np.array([math.cos(a), math.sin(a)])
            t = perp(nrm)
            r = 0.29 * s * math.cos(math.pi / 6) + 0.004
            p = np.array(c) + nrm * r
            dk.poly([(*(p - t * 0.09 * s), zg + 1.84 * s), (*(p + t * 0.09 * s), zg + 1.84 * s), (*(p + t * 0.09 * s), zg + 2.1 * s), (*(p - t * 0.09 * s), zg + 2.1 * s)],
                    col('#1d1d1e'), inside=(c[0], c[1], zg + 2 * s))
        prism(mb, c, 0.75 * s, 0.75 * s, zg + 2.2 * s, zg + 2.3 * s, 6, jit(g2, 0.05))
        prism(mb, c, 0.75 * s, 0.14 * s, zg + 2.3 * s, zg + 2.68 * s, 6, jit(g1, 0.05))
        for k in range(6):
            a = k * math.pi / 3
            p = np.array(c) + np.array([math.cos(a), math.sin(a)]) * 0.72 * s
            prism(mb, p, 0.06 * s, 0.03 * s, zg + 2.24 * s, zg + 2.42 * s, 4, jit(g1, 0.05))
        prism(mb, c, 0.12 * s, 0.13 * s, zg + 2.68 * s, zg + 2.76 * s, 8, jit(g2, 0.05))
        prism(mb, c, 0.13 * s, 0.1 * s, zg + 2.76 * s, zg + 2.9 * s, 8, jit(g2, 0.05))
        prism(mb, c, 0.1 * s, 0.0, zg + 2.9 * s, zg + 3.05 * s, 8, jit(g2, 0.05), top=False)

    # -------------------------------------------------- 屋根(寄棟・瓦の段)
    def hip_roof(self, c, u, Lx, Wy, z_eave, slope, course=0.3):
        """寄棟(Lx>=Wy の矩形、軒の高さ z_eave、勾配 slope)。瓦の段を色の帯で。棟と隅棟の箱も。"""
        rf = self.mb['roof']
        c = np.asarray(c, float); u = unit(u); v = perp(u)
        hx, hy = Lx / 2, Wy / 2
        rise = hy * slope
        tile = col('#4a4d52'); tile2 = col('#3f4247'); ridge = col('#35383c')
        nlev = max(2, int(math.ceil(hy / course)))
        for k in range(nlev):
            t0, t1 = k / nlev, (k + 1) / nlev
            d0, d1 = hy * t0, hy * t1
            z0, z1 = z_eave + rise * t0, z_eave + rise * t1
            rect = lambda d: [c + u * (hx - d) + v * (hy - d), c - u * (hx - d) + v * (hy - d), c - u * (hx - d) - v * (hy - d), c + u * (hx - d) - v * (hy - d)]
            R0, R1 = rect(d0), rect(d1)
            cc = tile if k % 2 == 0 else tile2
            for i in range(4):
                j = (i + 1) % 4
                a0, b0, a1, b1 = R0[i], R0[j], R1[i], R1[j]
                if np.hypot(*(a1 - b1)) < 1e-3:
                    rf.poly([(*a0, z0), (*b0, z0), (*a1, z1)], cc, up=True)
                else:
                    rf.poly([(*a0, z0), (*b0, z0), (*b1, z1), (*a1, z1)], C.tint(cc, 0.96 + 0.08 * RS.rand()), up=True)
        # 軒の厚み(鼻隠し)
        R0 = [c + u * hx + v * hy, c - u * hx + v * hy, c - u * hx - v * hy, c + u * hx - v * hy]
        for i in range(4):
            a, b = R0[i], R0[(i + 1) % 4]
            rf.poly([(*a, z_eave - 0.1), (*b, z_eave - 0.1), (*b, z_eave), (*a, z_eave)], col('#2f3135'), inside=(c[0], c[1], z_eave))
        rf.poly([(*R0[0], z_eave - 0.1), (*R0[3], z_eave - 0.1), (*R0[2], z_eave - 0.1), (*R0[1], z_eave - 0.1)], col('#5a4636'), inside=(c[0], c[1], z_eave + 1))
        zr = z_eave + rise
        if hx - hy > 0.05:
            a, b = c - u * (hx - hy), c + u * (hx - hy)
            for k, (w, hh) in enumerate(((0.3, 0.1), (0.24, 0.1), (0.18, 0.08))):
                zz = zr + 0.02 + sum(x[1] for x in ((0.3, 0.1), (0.24, 0.1), (0.18, 0.08))[:k])
                rf.box_sloped(a - u * 0.1, b + u * 0.1, zz + hh, zz + hh, zz, zz, 0.0, w, ridge)
        for i in range(4):
            corner = R0[i]
            end = c + u * (hx - hy) * (1 if (corner - c) @ u > 0 else -1)
            rf.box_sloped(corner, end, z_eave + 0.12, zr + 0.12, z_eave, zr, 0.0, 0.16, ridge)
        return zr

    def gable_roof(self, c, u, Lx, Wy, z_eave, slope):
        rf = self.mb['roof']
        c = np.asarray(c, float); u = unit(u); v = perp(u)
        hx, hy = Lx / 2, Wy / 2
        zr = z_eave + hy * slope
        tile = col('#4a4d52')
        for sg in (-1, 1):
            for k in range(4):
                t0, t1 = k / 4, (k + 1) / 4
                a0 = c + v * sg * hy * (1 - t0); a1 = c + v * sg * hy * (1 - t1)
                z0 = z_eave + (zr - z_eave) * t0; z1 = z_eave + (zr - z_eave) * t1
                rf.poly([(*(a0 - u * hx), z0), (*(a0 + u * hx), z0), (*(a1 + u * hx), z1), (*(a1 - u * hx), z1)], C.tint(tile, 1.0 - 0.06 * (k % 2)), up=True)
        rf.box_sloped(c - u * hx, c + u * hx, zr + 0.14, zr + 0.14, zr - 0.02, zr - 0.02, 0.0, 0.22, col('#35383c'))
        for sg in (-1, 1):
            e = c + u * sg * hx
            rf.poly([(*(e - v * hy), z_eave), (*(e + v * hy), z_eave), (*e, zr)], col('#3a3b3d'), inside=(c[0], c[1], z_eave))
        return zr

    # -------------------------------------------------- 足湯 湯けむり亭(A_yukemuri_tei.md)
    def build_yukemuri(self):
        mb = self.mb['wood']; st = self.mb['stone']; wt = self.mb['water']
        Y = YB.YUKEMURI
        c = np.array(Y['c'])
        a = math.radians(Y['ang'])
        u = np.array([math.cos(a), math.sin(a)]); v = perp(u)
        hx, hy = Y['L'] / 2, Y['W'] / 2
        zg = float(self.f.Z(*c)) + 0.1
        dark = '#3f2f25'
        # 床の石
        obox(st, c, u, hx - 0.1, hy - 0.1, zg - 0.2, zg + 0.08, col('#6f6d68'))
        # 足湯の池: 黒灰のタイルの縁(腰掛け)、檜の板のベンチ
        px, py = hx - 0.75, hy - 0.7
        for sg in (-1, 1):
            obox(st, c + v * sg * (py - 0.12), u, px, 0.14, zg + 0.08, zg + 0.44, col('#454547'))
            obox(st, c + u * sg * (px - 0.14), v, 0.14, py - 0.26, zg + 0.08, zg + 0.44, col('#454547'))
            obox(mb, c + v * sg * (py + 0.18), u, px + 0.3, 0.2, zg + 0.40, zg + 0.46, col('#b08a62'))
            obox(mb, c + u * sg * (px + 0.18), v, 0.2, py - 0.1, zg + 0.40, zg + 0.46, col('#b08a62'))
            obox(st, c + v * sg * (py + 0.18), u, px + 0.25, 0.16, zg + 0.08, zg + 0.40, col('#3d3d3f'))
            obox(st, c + u * sg * (px + 0.18), v, 0.16, py - 0.12, zg + 0.08, zg + 0.40, col('#3d3d3f'))
        wt.poly([(*(c - u * (px - 0.28) - v * (py - 0.26)), zg + 0.32), (*(c + u * (px - 0.28) - v * (py - 0.26)), zg + 0.32),
                 (*(c + u * (px - 0.28) + v * (py - 0.26)), zg + 0.32), (*(c - u * (px - 0.28) + v * (py - 0.26)), zg + 0.32)], col('#557a68'), up=True)
        # 柱(黒褐色の角柱 6 本)、梁、方杖
        ze = zg + 2.75
        posts = [c + u * sx * (hx - 0.15) + v * sy * (hy - 0.15) for sx in (-1, 0, 1) for sy in (-1, 1)]
        for p in posts:
            obox(mb, p, u, 0.075, 0.075, zg + 0.08, ze, jit(dark, 0.04))
        for sy in (-1, 1):
            beam(mb, c - u * (hx + 0.1) + v * sy * (hy - 0.15), c + u * (hx + 0.1) + v * sy * (hy - 0.15), ze + 0.05, ze + 0.05, 0.15, 0.24, col(dark))
        for sx in (-1, 1):
            beam(mb, c + u * sx * (hx - 0.15) - v * (hy + 0.1), c + u * sx * (hx - 0.15) + v * (hy + 0.1), ze + 0.2, ze + 0.2, 0.15, 0.2, col(dark))
        for p in posts:
            for d in (u, -u):
                q = p + d * 0.55
                if np.hypot(*(q - c)) > max(hx, hy) + 0.2:
                    continue
                mb.box_sloped(p, q, ze - 0.55, ze - 0.05, ze - 0.65, ze - 0.15, 0.0, 0.08, col(dark))
        # 軒裏の垂木(化粧)
        for t in np.linspace(-hx - 0.7, hx + 0.7, 16):
            for sy in (-1, 1):
                a0 = c + u * t + v * sy * (hy - 0.1)
                a1 = c + u * t + v * sy * (hy + 0.85)
                mb.box_sloped(a0, a1, ze + 0.3, ze + 0.12, ze + 0.22, ze + 0.04, 0.0, 0.06, col('#4a382c'))
        # 二重屋根: 寄棟 + 越屋根
        zr = self.hip_roof(c, u, Y['L'] + 1.8, Y['W'] + 1.8, ze + 0.12, 0.52)
        # 越屋根の小壁(換気の格子)と切妻
        kw, kd = 1.6, 0.9
        zk0, zk1 = zr - 0.35, zr + 0.45
        for sg in (-1, 1):
            obox(mb, c + v * sg * kd / 2, u, kw / 2, 0.04, zk0, zk1, col('#3a2c22'))
            for t in np.linspace(-kw / 2 + 0.1, kw / 2 - 0.1, 9):
                obox(mb, c + v * sg * (kd / 2 + 0.04) + u * t, u, 0.02, 0.02, zk0 + 0.05, zk1 - 0.05, col('#6b5444'), top=False)
        for sg in (-1, 1):
            obox(mb, c + u * sg * kw / 2, v, 0.04, kd / 2, zk0, zk1, col('#3a2c22'))
        self.gable_roof(c, u, kw + 0.7, kd + 0.8, zk1, 0.6)

    def pavilion(self, c, z, size=2.6):
        """東デッキの東屋(瓦の寄棟、柱 4 本、ベンチ)。W 6:21〜6:36、S 5:12〜5:18。"""
        mb = self.mb['wood']
        c = np.asarray(c, float)
        u = np.array([0.0, 1.0]); v = perp(u)
        h = size / 2
        ze = z + 2.45
        for sx in (-1, 1):
            for sy in (-1, 1):
                obox(mb, c + u * sx * (h - 0.1) + v * sy * (h - 0.1), u, 0.07, 0.07, z, ze, jit('#4a382c', 0.04))
        for sx in (-1, 1):
            beam(mb, c + u * sx * (h - 0.1) - v * (h + 0.1), c + u * sx * (h - 0.1) + v * (h + 0.1), ze + 0.15, ze + 0.15, 0.13, 0.18, col('#4a382c'))
            beam(mb, c + v * sx * (h - 0.1) - u * (h + 0.1), c + v * sx * (h - 0.1) + u * (h + 0.1), ze + 0.15, ze + 0.15, 0.13, 0.18, col('#4a382c'))
        obox(mb, c + v * (h - 0.35), u, h - 0.3, 0.2, z + 0.4, z + 0.45, col('#8a6b52'))
        self.hip_roof(c, u, size + 1.2, size + 1.2, ze + 0.15, 0.55)

    # -------------------------------------------------- 手洗乃湯・石標・碑・案内板・ベンチ・足湯 滝の湯・湯枠
    def facing(self, p, away=True):
        """穴の縁から離れる向き(広場の側)。"""
        L = self.L
        d, qx, qy, _, _ = YB.seg_nearest(np.array([p[0]]), np.array([p[1]]), L.hole, closed=True)
        n = unit(np.array([p[0] - qx[0], p[1] - qy[0]]))
        return n if away else -n

    def build_props(self):
        L = self.L
        st = self.mb['stone']; mb = self.mb['wood']; dk = self.mb['dark']; fl = self.mb['flow']; wt = self.mb['water']
        black = col('#1a1a1b'); white = col('#e8e6df')
        # 手洗乃湯(K 9:15〜10:06): 御影石の箱 + 湯口 + 受け + 木の標柱(文字「手洗乃湯」は読めた)
        for i, p in enumerate(YB.TEARAI):
            p = np.array(p)
            inhole = L.in_hole(np.array([p[0]]), np.array([p[1]]))[0]
            if inhole:
                z = self.zin(*p)
                fwd = unit(np.array([-1.0, -0.2]))
            else:
                z = float(self.f.Z(*p)) + 0.1
                fwd = self.facing(p)
            side = perp(fwd)
            obox(st, p, side, 0.38, 0.23, z, z + 0.9, jit('#8c8a85', 0.04))
            obox(st, p, side, 0.44, 0.29, z + 0.9, z + 0.98, jit('#9a9892', 0.04))
            spout = p + fwd * 0.3
            obox(dk, spout, fwd, 0.07, 0.025, z + 0.74, z + 0.79, col('#6b5a3a'))
            tray = p + fwd * 0.5
            obox(st, tray, side, 0.45, 0.2, z, z + 0.14, col('#7a7873'))
            dk.poly([(*(tray - side * 0.38 - fwd * 0.14), z + 0.145), (*(tray + side * 0.38 - fwd * 0.14), z + 0.145),
                     (*(tray + side * 0.38 + fwd * 0.14), z + 0.145), (*(tray - side * 0.38 + fwd * 0.14), z + 0.145)], col('#2a2a2a'), up=True)
            w = p + fwd * 0.37
            obox(fl, w, fwd, 0.012, 0.012, z + 0.15, z + 0.75, col('#e9efe9'))
            sp = p + side * 0.7 + fwd * 0.05
            obox(mb, sp, side, 0.065, 0.065, z, z + 1.55, col('#cdb38e'))
            prism(mb, sp, 0.092, 0.0, z + 1.55, z + 1.66, 4, col('#bba07a'), rot=math.atan2(side[1], side[0]) + math.pi / 4, top=False)
            put_text(mb, '手洗乃湯', 0.095, (*(sp + fwd * 0.066), z + 1.18), (*side, 0), (0, 0, 1), (*fwd, 0), col('#1e1e1e'), vertical=True)
        # 「草津温泉 湯畑」の黒い石標(S 4:30 f_91): 八角の黒い磨き石 + 円盤の頂
        p = np.array(YB.SIGN_STONE)
        z = float(self.f.Z(*p)) + 0.1
        fwd = self.facing(p)
        side = perp(fwd)
        prism(dk, p, 0.34, 0.34, z, z + 0.72, 8, black, rot=math.atan2(fwd[1], fwd[0]) + math.pi / 8)
        prism(dk, p, 0.27, 0.27, z + 0.72, z + 0.78, 20, col('#242425'))
        r = 0.34 * math.cos(math.pi / 8)
        o = p + fwd * r
        put_text(dk, '草津温泉', 0.088, (*o, z + 0.55), (*side, 0), (0, 0, 1), (*fwd, 0), white)
        put_text(dk, '湯　畑', 0.15, (*o, z + 0.36), (*side, 0), (0, 0, 1), (*fwd, 0), white)
        # ロマンティック・シュトラーセ記念碑(OSM。形は W 7:06 の黒い角柱に合わせた。文字は読めないので無し)
        p = np.array(YB.STELE)
        z = float(self.f.Z(*p)) + 0.1
        fwd = self.facing(p)
        obox(st, p, perp(fwd), 0.42, 0.42, z, z + 0.12, col('#7e7c77'))
        obox(dk, p, perp(fwd), 0.3, 0.3, z + 0.12, z + 1.05, black)
        prism(dk, p, 0.44, 0.1, z + 1.05, z + 1.18, 4, col('#232324'), rot=math.atan2(fwd[1], fwd[0]) + math.pi / 4)
        # 案内板(木の枠と2本足。文字は読めないので無地)
        for i, p in enumerate(YB.BOARDS):
            p = np.array(p)
            inh = L.in_hole(np.array([p[0]]), np.array([p[1]]))[0]
            z = self.zin(*p) if inh else float(self.f.Z(*p)) + 0.1
            fwd = self.facing(p) if not inh else unit(np.array([0.0, -1.0]))
            side = perp(fwd)
            for sg in (-1, 1):
                obox(mb, p + side * sg * 0.62, side, 0.05, 0.05, z, z + 1.75, col('#4d3b2e'))
            obox(mb, p, side, 0.62, 0.04, z + 0.85, z + 1.65, col('#4d3b2e'))
            q = p + fwd * 0.045
            mb.poly([(*(q - side * 0.55), z + 0.92), (*(q + side * 0.55), z + 0.92), (*(q + side * 0.55), z + 1.58), (*(q - side * 0.55), z + 1.58)],
                    col('#d9d3c2'), inside=(*(p - fwd), z + 1.2))
            beam(mb, p - side * 0.75, p + side * 0.75, z + 1.82, z + 1.82, 0.22, 0.08, col('#3f3027'))
        # ベンチ(木の座面の弧、石の脚。R 1:30〜1:45)
        for i, p in enumerate(YB.BENCHES):
            p = np.array(p)
            z = float(self.f.Z(*p)) + 0.1
            n = self.facing(p)
            t = perp(n)
            R = 2.2
            cc = p + n * R
            a0 = math.atan2(-n[1], -n[0])
            angs = np.linspace(a0 - 0.45, a0 + 0.45, 7)
            for k in range(len(angs) - 1):
                A = cc + R * np.array([math.cos(angs[k]), math.sin(angs[k])])
                B = cc + R * np.array([math.cos(angs[k + 1]), math.sin(angs[k + 1])])
                mb.box_sloped(A, B, z + 0.44, z + 0.44, z + 0.36, z + 0.36, 0.0, 0.5, jit('#9b7a5a', 0.05))
            for k in (1, 5):
                A = cc + R * np.array([math.cos(angs[k]), math.sin(angs[k])])
                obox(st, A, t, 0.12, 0.2, z, z + 0.36, col('#8c8a85'))
        # 足湯 滝の湯(OSM 14.1,36.3。北の低い通路の脇): 石の湯船 + 木のベンチ
        p = np.array(YB.TAKINOYU)
        z = YB.LOW_Z
        u = unit(np.array(L.ways[YB.W_FENCE_N][-1]) - np.array(L.ways[YB.W_FENCE_N][0]))
        v = perp(u)
        for sg in (-1, 1):
            obox(st, p + v * sg * 0.42, u, 1.7, 0.1, z, z + 0.42, jit('#8d8a83', 0.04))
            obox(st, p + u * sg * 1.6, v, 0.1, 0.42, z, z + 0.42, jit('#8d8a83', 0.04))
        wt.poly([(*(p - u * 1.5 - v * 0.32), z + 0.3), (*(p + u * 1.5 - v * 0.32), z + 0.3), (*(p + u * 1.5 + v * 0.32), z + 0.3), (*(p - u * 1.5 + v * 0.32), z + 0.3)],
                col('#9fd8c9'), up=True)
        obox(mb, p + v * 0.82, u, 1.7, 0.2, z + 0.38, z + 0.44, col('#9b7a5a'))
        obox(mb, p - v * 0.82, u, 1.7, 0.2, z + 0.38, z + 0.44, col('#9b7a5a'))
        for sg in (-1, 1):
            for t in (-1.2, 0, 1.2):
                obox(st, p + v * sg * 0.82 + u * t, u, 0.08, 0.15, z, z + 0.38, col('#7d7b76'))
        # 御汲上げの湯枠(源泉の池の木の枠、R 2:27)
        p = np.array(YB.YUWAKU)
        z = YB.POOL_S_WATER
        u = L.tr_u
        v = perp(u)
        for sg in (-1, 1):
            obox(mb, p + v * sg * 0.9, u, 1.0, 0.08, z - 0.5, z + 0.18, col('#6a5040'))
            obox(mb, p + u * sg * 0.9, v, 0.08, 0.82, z - 0.5, z + 0.18, col('#6a5040'))
        # 東デッキの東屋
        self.pavilion(YB.EPAVILION, YB.EDECK_Z)
        # 石灯籠
        for x, y, h in YB.LANTERNS:
            zg = self.zin(x, y)
            for k in range(6):
                a = k * 1.05 + 0.3
                rock(self.rocks, x + 0.55 * math.cos(a), y + 0.55 * math.sin(a), zg, 0.45, 0.4, 0.35, 2000 + int(x * 10) + k, base='#3f3c38', wet=0.2)
            self.lantern(x, y, zg + 0.25, h)

    # -------------------------------------------------- 岩の配置
    def build_rocks(self):
        L = self.L
        rs = np.random.RandomState(9)
        k = 0
        # 源泉の池の縁(黒い溶岩)
        P, s = C.resample(L.pool_s + [L.pool_s[0]], 0.65)
        for p in P[:-1]:
            c = np.array(p)
            n = c - np.array(L.pool_s).mean(axis=0)
            n = unit(n)
            q = c + n * (0.25 + 0.3 * rs.rand())
            if not L.in_hole(np.array([q[0]]), np.array([q[1]]))[0]:
                continue
            # 樋の始まりの所は空ける
            if YB.seg_nearest(np.array([q[0]]), np.array([q[1]]), [tuple(t[0]) for t in L.troughs])[0][0] < 0.9:
                continue
            rock(self.rocks, q[0], q[1], self.zin(*q), 0.35 + 0.25 * rs.rand(), 0.3 + 0.2 * rs.rand(), 0.28 + 0.18 * rs.rand(), 3000 + k,
                 base='#363431', wet=0.15, white=0.1)
            k += 1
        # 池の中の岩(R 2:27 の黒い岩)
        for i in range(10):
            x = rs.uniform(-19, -5); y = rs.uniform(-30, -16)
            if YB.sdist(np.array([x]), np.array([y]), L.pool_s)[0] < -0.8:
                rock(self.rocks, x, y, YB.POOL_S_WATER - 0.1, 0.35, 0.3, 0.22, 3500 + i, base='#2f2e2c', sink=0.5)
        # 床の岩の塊(樋の間を避ける、北ほど多い)
        H = np.array(L.hole)
        tries = 0
        placed = 0
        while placed < 110 and tries < 4000:
            tries += 1
            x = rs.uniform(H[:, 0].min(), H[:, 0].max()); y = rs.uniform(H[:, 1].min(), H[:, 1].max())
            xa, ya = np.array([x]), np.array([y])
            if not L.in_hole(xa, ya)[0] or L.low_side(xa, ya)[0]:
                continue
            if YB.sdist(xa, ya, L.pool_s)[0] < 0.6:
                continue
            dtr = min(YB.seg_nearest(xa, ya, [tuple(a), tuple(b)])[0][0] for a, b in L.troughs)
            if dtr < 0.42:
                continue
            if YB.seg_nearest(xa, ya, L.hole, closed=True)[0][0] < 0.6:
                continue
            s = float(L.tr_s(x, y))
            dens = 0.25 + 0.75 * C.smoothstep((s - 20) / 15.0)
            if rs.rand() > dens:
                continue
            sz = 0.18 + 0.32 * rs.rand() * (1 + 0.6 * C.smoothstep((s - 30) / 10.0))
            rock(self.rocks, x, y, self.zin(x, y), sz * (1 + 0.4 * rs.rand()), sz * (1 + 0.3 * rs.rand()), sz * 0.8, 4000 + placed,
                 base='#3c3a36', wet=0.25 if dtr < 1.0 else 0.08, white=0.2)
            placed += 1
        # 滝壺の岸(崖の側以外)
        P, s = C.resample(L.pool_n + [L.pool_n[0]], 0.8)
        cen = np.array(L.pool_n).mean(axis=0)
        for i, p in enumerate(P[:-1]):
            c = np.array(p)
            if c[1] < 25.8 and c[0] > 4.0:      # 崖の側(南)
                continue
            n = unit(c - cen)
            q = c - n * (0.1 + 0.3 * rs.rand())
            rock(self.rocks, q[0], q[1], YB.BASIN_WATER - 0.2, 0.55 + 0.35 * rs.rand(), 0.45 + 0.3 * rs.rand(), 0.45 + 0.25 * rs.rand(), 5000 + i,
                 base='#353331', wet=0.2, white=0.12, sink=0.35)
        # 滝壺の中の大きな岩(f_3 手前)
        for i, (x, y, r) in enumerate(((9.8, 29.6, 0.9), (12.2, 30.2, 1.0), (14.6, 29.8, 0.8), (7.4, 27.0, 0.7), (11.0, 27.3, 0.45))):
            rock(self.rocks, x, y, YB.BASIN_WATER, r * 1.2, r, r * 0.75, 5500 + i, base='#302e2c', white=0.15, sink=0.55)
        self.stats['rocks'] = len(self.rocks.v)

    # -------------------------------------------------- まとめ
    def build_all(self, mats, coll):
        objs = []
        objs.append(self.build_bed(mats, coll))
        objs.append(self.build_cliff(mats, coll))
        log('bed, cliff')
        self.build_troughs()
        self.build_outflow()
        self.build_small_falls()
        log('troughs, outflow')
        self.build_water()
        self.build_walls()
        self.build_balustrade()
        log('walls, balustrade')
        self.build_pave()
        self.build_bollards()
        self.build_guardrail()
        log('pave')
        self.build_decks()
        self.build_yukemuri()
        self.build_props()
        self.build_rocks()
        log('decks, props, rocks')
        names = dict(stone=('Yb_Stone', 'stone'), wood=('Yb_Wood', 'wood'), roof=('Yb_Roof', 'roof'), water=('Water_Yb', 'water'),
                     flow=('Yb_Flow', 'flow'), pave=('Yb_Pave', 'pave'), dark=('Yb_Dark', 'dark'))
        for k, (nm, mk) in names.items():
            o = self.mb[k].to_object(nm, mats[mk], False, coll)
            if o is not None:
                objs.append(o)
        objs.append(self.rocks.to_object('Yb_Rocks', mats['rock'], True, coll))
        objs.append(self.splash.to_object('Yb_Splash', mats['flow'], True, coll))
        return [o for o in objs if o is not None]


def main():
    out_web = C.OUT_WEB
    for a in ARGS:
        if a.startswith('--out-web='):
            out_web = a.split('=', 1)[1]
    do_export = '--no-export' not in ARGS
    C.reset_scene()
    load_font()
    osm = C.load_osm()
    field = F.Field(osm, log=log)
    mats = dict(
        stone=C.make_material('yb_stone', 0.82), wood=C.make_material('yb_wood', 0.78), roof=C.make_material('yb_roof', 0.6),
        rock=C.make_material('yb_rock', 0.88), bed=C.make_material('yb_bed', 0.93), pave=C.make_material('yb_pave', 0.88),
        water=C.make_material('yb_water', 0.1), flow=C.make_material('yb_flow', 0.4), dark=C.make_material('yb_dark', 0.3),
    )
    coll = C.new_collection('Yubatake')
    yb = Yubatake(field)
    objs = yb.build_all(mats, coll)
    tris = {o.name: C.count_tris([o]) for o in objs}
    log('objects', tris, 'total', sum(tris.values()))
    os.makedirs(C.OUT_BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.OUT_BLEND, 'kusatsu_yubatake.blend'))
    info = dict(tris=tris, total_tris=int(sum(tris.values())), stats=yb.stats)
    if do_export:
        p = os.path.join(out_web, 'yubatake.glb')
        info['glb_bytes'] = C.export_glb(objs, p, pos_bits=14)
        log('exported', p, info['glb_bytes'])
    json.dump(info, open(os.path.join(C.OUT_BLEND, 'yubatake_stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    log('done', json.dumps(yb.stats, default=float))


main()
