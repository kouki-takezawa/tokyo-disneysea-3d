# -*- coding: utf-8 -*-
"""kd_parts.py -- 草津 湯畑ジオラマ フェーズ4: 建物の共通部品ライブラリ(フェーズ5〜8の区域スクリプトが import する)。

使い方(区域スクリプト kusatsu/kd_zone_<A-D>.py の例):
    import kd_parts as P
    def specs():
        return [P.BuildingSpec(id='605309932', name='ちちや', floors=3, floor_h=[3.4, 3.0, 2.6], front=314,
                               walls={1: P.WallFinish('board_v', '#5a3a28'), '*': P.WallFinish('plaster', timber=P.Timber())},
                               roof=P.Roof('gable', 'kawara', slope=0.55, kengyo=True), ...)]
    if __name__ == '__main__':
        P.run_zone('A', specs())        # Blender: 箱(残り)+本物 → kusatsu-diorama/models/buildings_A.glb

- 形はすべて静止・頂点色。面は材質(kusatsu_*)ごとにまとめる。幾何は numpy/python だけで作り(Blender 無しでも三角形数を数えられる)、
  `PB.to_objects()` だけが bpy を使う。
- 座標: 平面は kd_common と同じ(+X 東、+Y 北、m)、Z は Blender の Z(標高-1153)。外形は反時計回り(ccw)。
- 方位: `front` は真北から時計回りの度(68 = 東北東)か 16 方位の文字('ENE')。辺の向きは「正面/背面/左/右」(正面に向かって左右)と
  8 方位('N','NE',…)の両方で呼べる。辺の番号(int)でも可。
- 開口の割り付けは `Facade.pattern`(階ごとの文字列、1 文字=1 柱間): W 窓(サッシ/木枠)、w 小窓、T 縦長窓、L 格子窓、R 連窓、
  A 半円アーチ窓、K 花頭窓、D 格子戸(引き戸)、G ガラス戸、P 板戸、S 店先(奥に暗がり+暖簾)、H シャッター、. 壁。
  R/S/H/P は続けて書くと1つの開口になる。
"""
import importlib
import json
import math
import os
import sys
import zlib
from dataclasses import dataclass, field as dfield, replace as dreplace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import kd_common as C  # noqa: E402

try:
    import bpy  # noqa: F401
    from mathutils import Vector as _Vec, geometry as _mgeo
except ImportError:
    bpy = None
    _mgeo = None
    _Vec = None

# ====================================================================== 材質・色
# key: (粗さ, 金属, 経年の効き 0..1)。Blender 名は 'kusatsu_' + key。色は頂点色(Col)。
MATERIALS = {
    'wall': (0.92, 0.0, 1.0),     # 漆喰・モルタル・吹付・タイル・塗り壁
    'wood': (0.80, 0.0, 0.7),     # 板張り・柱梁・格子・木の手すり・暖簾の竿
    'paint': (0.55, 0.0, 0.5),    # 朱塗り・塗装した木部
    'roof': (0.70, 0.0, 0.6),     # 瓦・とんとん葺き
    'metal': (0.42, 0.45, 0.3),   # 金属板屋根・サッシ・手すり・樋・室外機
    'stone': (0.90, 0.0, 0.8),    # 基礎・石段・礎石
    'glass': (0.12, 0.0, 0.0),    # ガラス(環境マップが無いので色で暗く見せる)
    'dark': (0.97, 0.0, 0.0),     # 開口の奥の暗がり
    'fabric': (0.95, 0.0, 0.2),   # 暖簾・提灯・幟・テント
    'thatch': (1.00, 0.0, 0.5),   # 茅
}

PAL = dict(
    plaster='#ece8dd', plaster_warm='#e6dfcf', spray='#e7e6e1', mortar='#bdb6aa', tile_beige='#c8b9a0',
    timber='#3a2a20', timber_black='#2a221d', wood='#8a6446', cedar='#b4703e', cedar_old='#8b6a50',
    board_black='#2c2826', vermilion='#b23a2c', vermilion_dark='#8e2f25',
    kawara='#4a4d52', tonton='#7b7368', metal='#8d9397', metal_light='#b9bec0', teppan='#5d625f', kaya='#7a6a52',
    stone='#8f8c86', stone_dark='#6f6c66', concrete='#a7a49d',
    alu='#b9bcbd', alu_dark='#4b4c4c', glass='#46535c', glass_dark='#2c343a', shoji='#e6dfc9',
    interior='#2a2420', noren_navy='#273149', lantern_red='#c03a2b', lantern_white='#efe9da',
    ac='#e2e1dc', gutter='#6d6a64', soffit='#c9b79c', terrace='#9d9a93', roof_flat='#8a8a84',
)
FRAME_COL = dict(alu='#b9bcbd', dark='#3d3d3c', wood='#4a3426', white='#e9e7e0', black='#262321')
ROOF_MAT = {'kawara': 'roof', 'tonton': 'roof', 'metal': 'metal', 'teppan': 'metal', 'kaya': 'thatch'}
ROOF_COL = {'kawara': PAL['kawara'], 'tonton': PAL['tonton'], 'metal': PAL['metal'], 'teppan': PAL['teppan'], 'kaya': PAL['kaya']}
ROOF_THICK = {'kawara': 0.22, 'tonton': 0.12, 'metal': 0.12, 'teppan': 0.12, 'kaya': 0.6}

_MATS = {}


def get_materials():
    """kusatsu_* マテリアル(同じ Blender セッションでは使い回す)。"""
    out = {}
    for k, (r, m, _) in MATERIALS.items():
        nm = 'kusatsu_' + k
        mat = bpy.data.materials.get(nm)
        if mat is None:
            mat = C.make_material(nm, r, m)
        out[k] = mat
    return out


def lin(c):
    """'#rrggbb'(sRGB) -> リニア RGB。タプルはリニアとみなしてそのまま。"""
    if c is None:
        return (0.3, 0.3, 0.3)
    if isinstance(c, str):
        return C.srgb(PAL.get(c, c))
    return tuple(c)


def tint(c, k):
    return (min(c[0] * k, 1.0), min(c[1] * k, 1.0), min(c[2] * k, 1.0))


def hj(c, a, *keys):
    """決定的な色むら(keys から)。"""
    h = 0.123
    for i, kk in enumerate(keys):
        h += float(kk) * (12.9898 + 31.7 * i)
    f = math.sin(h) * 43758.5453
    f -= math.floor(f)
    return tint(c, 1.0 - a + 2.0 * a * f)


def hfrac(*keys):
    h = 0.321
    for i, kk in enumerate(keys):
        h += float(kk) * (78.233 + 17.3 * i)
    f = math.sin(h) * 43758.5453
    return f - math.floor(f)


# ====================================================================== メッシュ収集(材質別)
def newell(P):
    nx = ny = nz = 0.0
    n = len(P)
    for i in range(n):
        x0, y0, z0 = P[i]
        x1, y1, z1 = P[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return (nx, ny, nz)


class PB:
    """材質ごとの頂点・頂点色・面。面は頂点を共有しない(色は頂点ごと=経年の色むらを後から掛けられる)。"""

    def __init__(self):
        self.g = {}

    def _grp(self, m):
        g = self.g.get(m)
        if g is None:
            g = self.g[m] = ([], [], [])
        return g

    def poly(self, m, pts, c, nrm=None):
        if len(pts) < 3:
            return
        if nrm is not None:
            n = newell(pts)
            if n[0] * nrm[0] + n[1] * nrm[1] + n[2] * nrm[2] < 0:
                pts = pts[::-1]
        V, Cl, F = self._grp(m)
        i0 = len(V)
        for p in pts:
            V.append((float(p[0]), float(p[1]), float(p[2])))
        Cl.extend([c] * len(pts))
        F.append(list(range(i0, i0 + len(pts))))

    def merge(self, o):
        for m, (V, Cl, F) in o.g.items():
            V0, C0, F0 = self._grp(m)
            k = len(V0)
            V0.extend(V)
            C0.extend(Cl)
            F0.extend([[i + k for i in f] for f in F])

    def tris(self):
        return sum(len(f) - 2 for (_, _, F) in self.g.values() for f in F)

    def tris_by_mat(self):
        return {m: sum(len(f) - 2 for f in F) for m, (_, _, F) in self.g.items()}

    def nverts(self):
        return sum(len(V) for (V, _, _) in self.g.values())

    def to_objects(self, prefix, mats, coll=None):
        objs = []
        for m in sorted(self.g):
            V, Cl, F = self.g[m]
            if not F:
                continue
            objs.append(C.make_object('%s_%s' % (prefix, m), np.array(V), F, np.array(Cl), 'vert', mats[m], False, coll))
        return objs


# ====================================================================== 幾何の部品
_BOXF = {
    '-x': ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
    '+x': ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
    '-y': ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
    '+y': ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
    '-z': ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
    '+z': ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
}


def box(pb, m, o, ex, ey, ez, c, skip=()):
    """平行六面体(角 o、3 辺 ex,ey,ez)。skip に '-x' などで面を省く。"""
    ox, oy, oz = o
    cx = ox + (ex[0] + ey[0] + ez[0]) / 2
    cy = oy + (ex[1] + ey[1] + ez[1]) / 2
    cz = oz + (ex[2] + ey[2] + ez[2]) / 2

    def P(i, j, k):
        return (ox + i * ex[0] + j * ey[0] + k * ez[0], oy + i * ex[1] + j * ey[1] + k * ez[1], oz + i * ex[2] + j * ey[2] + k * ez[2])
    for key, q in _BOXF.items():
        if key in skip:
            continue
        pts = [P(*t) for t in q]
        fx = sum(p[0] for p in pts) / 4 - cx
        fy = sum(p[1] for p in pts) / 4 - cy
        fz = sum(p[2] for p in pts) / 4 - cz
        pb.poly(m, pts, c, (fx, fy, fz))


def beam(pb, m, a, b, w, h, c, up=(0, 0, 1), skip=()):
    """a→b の角材(幅 w=横、高さ h=up 方向)。'-x','+x' は端の面、'-z' は下(up の逆)。"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = b - a
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return
    t = d / L
    sd = np.cross(t, np.asarray(up, float))
    ns = float(np.linalg.norm(sd))
    if ns < 1e-6:
        for alt in ((1.0, 0, 0), (0, 1.0, 0)):
            sd = np.cross(t, alt)
            ns = float(np.linalg.norm(sd))
            if ns > 1e-6:
                break
    sd = sd / ns
    uu = np.cross(sd, t)
    o = a - sd * w / 2 - uu * h / 2
    box(pb, m, tuple(o), tuple(d), tuple(sd * w), tuple(uu * h), c, skip)


def prism(pb, m, c, r0, r1, z0, z1, n, col, rot=0.0, top=True, bottom=False):
    """鉛直の n 角錐台。"""
    a = [rot + i * 2 * math.pi / n for i in range(n)]
    B = [(c[0] + r0 * math.cos(t), c[1] + r0 * math.sin(t), z0) for t in a]
    T = [(c[0] + r1 * math.cos(t), c[1] + r1 * math.sin(t), z1) for t in a]
    for i in range(n):
        j = (i + 1) % n
        mx = math.cos(a[i] + math.pi / n)
        my = math.sin(a[i] + math.pi / n)
        pb.poly(m, [B[i], B[j], T[j], T[i]], col, (mx, my, (r0 - r1) / max(z1 - z0, 1e-6)))
    if top and r1 > 1e-4:
        pb.poly(m, T, col, (0, 0, 1))
    if bottom:
        pb.poly(m, B, col, (0, 0, -1))


def unit2(v):
    v = np.asarray(v, float)
    return v / max(float(np.hypot(*v)), 1e-12)


def poly_area(ring):
    return C.poly_area(ring)


def obb(ring):
    """最小回転矩形。-> (中心, 長辺の角 rad, 長さ, 幅)。"""
    P = np.array(ring, float)
    best = None
    for a in np.deg2rad(np.arange(0, 90, 1.0)):
        c, s = math.cos(a), math.sin(a)
        u = P[:, 0] * c + P[:, 1] * s
        v = -P[:, 0] * s + P[:, 1] * c
        area = (u.max() - u.min()) * (v.max() - v.min())
        if best is None or area < best[0] - 1e-9:
            best = (area, a, u.min(), u.max(), v.min(), v.max())
    _, a, u0, u1, v0, v1 = best
    c, s = math.cos(a), math.sin(a)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    cx, cy = cu * c - cv * s, cu * s + cv * c
    long_is_u = (u1 - u0) >= (v1 - v0)
    ang = a if long_is_u else a + math.pi / 2
    return (cx, cy), ang, max(u1 - u0, v1 - v0), min(u1 - u0, v1 - v0)


def obb_ring(ring):
    (cx, cy), ang, L, W = obb(ring)
    u = np.array([math.cos(ang), math.sin(ang)])
    v = np.array([-u[1], u[0]])
    c = np.array([cx, cy])
    pts = [c - u * L / 2 - v * W / 2, c + u * L / 2 - v * W / 2, c + u * L / 2 + v * W / 2, c - u * L / 2 + v * W / 2]
    return C.ccw([(float(p[0]), float(p[1])) for p in pts])


def offset_ring(ring, d):
    """外形の辺を内側へ d m(辺ごとのリスト可、負=外側)ずらした外形。"""
    n = len(ring)
    P = np.array(ring, float)
    if np.isscalar(d):
        d = [float(d)] * n
    T, N = [], []
    for i in range(n):
        t = unit2(P[(i + 1) % n] - P[i])
        T.append(t)
        N.append(np.array([-t[1], t[0]]))
    out = []
    for j in range(n):
        i = (j - 1) % n
        p1 = P[i] + N[i] * d[i]
        p2 = P[j] + N[j] * d[j]
        t1, t2 = T[i], T[j]
        den = t1[0] * t2[1] - t1[1] * t2[0]
        if abs(den) < 1e-4:
            q = P[j] + N[j] * d[j]
        else:
            s = ((p2[0] - p1[0]) * t2[1] - (p2[1] - p1[1]) * t2[0]) / den
            q = p1 + t1 * s
            lim = 4.0 * max(abs(d[i]), abs(d[j]), 1e-3)
            if float(np.hypot(*(q - P[j]))) > lim + 1e-6:
                q = P[j] + (N[i] * d[i] + N[j] * d[j]) / 2
        out.append((float(q[0]), float(q[1])))
    return out


def tess(ring):
    """多角形(2D、凹でも可)の三角形分割 -> 頂点番号の三つ組。"""
    if _mgeo is not None:
        return [tuple(t) for t in _mgeo.tessellate_polygon([[_Vec((p[0], p[1], 0.0)) for p in ring]])]
    pts = [tuple(p[:2]) for p in ring]
    idx = list(range(len(pts)))
    if poly_area(pts) < 0:
        idx.reverse()
    out = []

    def cr(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    guard = 0
    while len(idx) > 3 and guard < 20000:
        guard += 1
        ok = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if cr(a, b, c) <= 1e-12:
                continue
            inside = False
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                p = pts[j]
                if cr(a, b, p) >= 0 and cr(b, c, p) >= 0 and cr(c, a, p) >= 0:
                    inside = True
                    break
            if inside:
                continue
            out.append((i0, i1, i2))
            idx.pop(k)
            ok = True
            break
        if not ok:
            break
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def subtract(iv, cuts):
    """区間 [(a,b)] から cuts を引く。"""
    out = list(iv)
    for c0, c1 in cuts:
        nxt = []
        for a, b in out:
            if c1 <= a or c0 >= b:
                nxt.append((a, b))
                continue
            if c0 > a:
                nxt.append((a, c0))
            if c1 < b:
                nxt.append((c1, b))
        out = nxt
    return [(a, b) for a, b in out if b - a > 1e-3]


def clip_half(poly, a, b, c):
    """2D 多角形を a*x+b*y+c >= 0 で切る。"""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp = a * p[0] + b * p[1] + c
        fq = a * q[0] + b * q[1] + c
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def vextent(poly, x):
    ys = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        if (p[0] - x) * (q[0] - x) <= 0 and abs(q[0] - p[0]) > 1e-9:
            t = (x - p[0]) / (q[0] - p[0])
            ys.append(p[1] + (q[1] - p[1]) * t)
    if len(ys) < 2:
        return None
    return min(ys), max(ys)


WIND16 = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
WIND8 = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']


def bearing_vec(b):
    """方位(真北から時計回りの度 or 16方位) -> 平面の単位ベクトル。"""
    if isinstance(b, str):
        b = WIND16.index(b.upper()) * 22.5
    r = math.radians(float(b))
    return np.array([math.sin(r), math.cos(r)])


def compass8(n):
    b = (math.degrees(math.atan2(n[0], n[1])) + 360.0) % 360.0
    return WIND8[int(((b + 22.5) % 360) // 45)]


# ====================================================================== 局所座標(壁・矩形)
class Wall:
    """外形の辺 a→b。局所座標 s(辺に沿う m)、z(Blender Z)、d(外向き m)。反時計回りの外形なら右側が外。"""

    def __init__(self, a, b, off=0.0):
        a = np.array(a[:2], float)
        b = np.array(b[:2], float)
        dv = b - a
        self.L = float(np.hypot(*dv))
        self.t = dv / max(self.L, 1e-9)
        self.n = np.array([self.t[1], -self.t[0]])
        self.a = a + self.n * off

    def P(self, s, z, d=0.0):
        return (self.a[0] + self.t[0] * s + self.n[0] * d, self.a[1] + self.t[1] * s + self.n[1] * d, z)

    def vec(self, ds, dz, dd):
        return (self.t[0] * ds + self.n[0] * dd, self.t[1] * ds + self.n[1] * dd, dz)

    def nrm(self, k=1.0):
        return (self.n[0] * k, self.n[1] * k, 0.0)

    def tv(self, k=1.0):
        return (self.t[0] * k, self.t[1] * k, 0.0)

    def quad(self, pb, m, s0, z0, s1, z1, d, c, k=1.0):
        pb.poly(m, [self.P(s0, z0, d), self.P(s1, z0, d), self.P(s1, z1, d), self.P(s0, z1, d)], c, self.nrm(k))

    def box(self, pb, m, s0, s1, z0, z1, d0, d1, c, skip=('-y',)):
        """局所の直方体。'-y'=壁側(奥)、'+y'=手前、'-x','+x'=左右、'-z','+z'=下上。"""
        box(pb, m, self.P(s0, z0, d0), self.vec(s1 - s0, 0, 0), self.vec(0, 0, d1 - d0), (0, 0, z1 - z0), c, skip)

    def beam(self, pb, m, p, q, w, dep, c, skip=()):
        """局所 p=(s,z,d)→q の角材。w=壁面内の幅、dep=法線方向の厚み('-z'=壁側の面)。"""
        beam(pb, m, self.P(*p), self.P(*q), w, dep, c, up=self.nrm(), skip=skip)


def wall_facing(p, q, out):
    """p→q の Wall を、外向きが out(2D)になるように作る。"""
    W = Wall(p, q)
    if W.n[0] * out[0] + W.n[1] * out[1] < 0:
        W = Wall(q, p)
    return W


class Frame:
    """矩形(屋根)の局所座標 x=棟方向 u、y=直交 v。"""

    def __init__(self, c, u, hx, hy):
        self.c = np.array(c[:2], float)
        self.u = unit2(u)
        self.v = np.array([-self.u[1], self.u[0]])
        self.hx = float(hx)
        self.hy = float(hy)

    def P(self, x, y, z):
        p = self.c + self.u * x + self.v * y
        return (float(p[0]), float(p[1]), float(z))

    def d2(self, a, b):
        return self.u * a + self.v * b

    def d3(self, a, b, c=0.0):
        d = self.d2(a, b)
        return (float(d[0]), float(d[1]), float(c))

    def loc(self, x, y):
        p = np.array([x, y], float) - self.c
        return float(p @ self.u), float(p @ self.v)


# ====================================================================== 仕様(BuildingSpec)
@dataclass
class Timber:
    """化粧柱・梁(真壁・ハーフティンバー)。"""
    color: str = '#3a2a20'
    w: float = 0.12               # 見付け幅
    proud: float = 0.03           # 壁面からの出
    posts: object = 'bay'         # 'bay'(柱間ごと)| 'ends' | 数値(間隔 m)
    beams: tuple = ('bottom', 'top', 'head')   # 'bottom','top','head'(開口の上=長押),'sill', 数値=階の床から m
    braces: bool = False          # 開口の無い柱間に筋交い
    mat: str = 'wood'


@dataclass
class WallFinish:
    kind: str = 'plaster'         # plaster|mortar|spray|paint|board_h|board_v|tile|stone|stone_round|louver
    color: str = '#ece8dd'
    pitch: float = None           # 板・押縁・タイル・石の割り m(None=既定)
    timber: Timber = None
    koshi: tuple = None           # (高さ m, kind, color) 腰壁
    mat: str = None               # 材質の上書き('wall','wood','stone','paint')


@dataclass
class Facade:
    bay: float = 1.8              # 柱間(自動割り付けの目安)
    margin: float = 0.35          # 辺の両端の余白
    pattern: dict = None          # {階: '文字列', '*': 既定}
    win: str = 'W'                # 自動割り付けの窓の文字(複数文字なら模様として繰り返す 例 'W.')
    ground: str = None            # 1 階の自動割り付けの文字/模様(None=win)
    frame: str = 'alu'            # alu|dark|wood|white|black
    glass: str = '#46535c'        # ガラスの色(障子なら '#e6dfc9')
    rev: float = 0.18             # 開口の見込み(壁厚)
    sizes: dict = None            # {文字: (幅|None, 高さ|None, 腰高)}
    trim: bool = False            # 額縁
    belt: bool = False            # 階ごとの帯(胴蛇腹)
    fins: tuple = None            # (幅, 出, ) 柱間ごとの縦フィン(壁柱)
    noren: str = None             # 店先 S の暖簾の色(None=暖簾なし)
    door_col: str = '#4a3426'
    shutter: float = 1.0          # H の閉じ具合 0..1
    lattice_col: str = None       # 格子の色(None=frame の木色)
    lod: int = None               # この面の細部の上限(裏側を軽くする。None=建物の lod)


@dataclass
class Balcony:
    floor: int = 2
    side: object = 'front'        # 'front'/'N'/辺番号、またはそのリスト
    depth: float = 0.9
    s0: float = None              # 辺の始点からの m(None=0.15、負=終点から)
    s1: float = None
    z: float = 0.0                # 階の床からの高さ(窓前の手すりなら 0.3 など)
    rail: str = 'wood'            # wood|lattice|steel|wall|glass
    rail_h: float = 0.95
    color: str = None
    slab_color: str = None
    brackets: bool = True
    ends: bool = True             # 両端の手すり
    extend: float = 0.0           # 辺の両端より外へ伸ばす m(縁側を角で回すとき)
    gap: tuple = None             # 手すりの切れ目 (位置の割合 0..1, 幅 m)(階段の上がり口)


@dataclass
class Pent:
    """庇・下屋(階の上端に付く片流れ)。"""
    floor: int = 1
    side: object = 'front'        # 'all' で全周
    depth: float = 0.9
    slope: float = 0.35
    mat: str = 'kawara'
    color: str = None
    z: float = None               # 付け根の高さ(階の床から m、None=階の上端-0.1)
    s0: float = None
    s1: float = None
    brackets: bool = True
    gutter: bool = False
    rafters: bool = False         # 化粧垂木(lod2 のとき)


@dataclass
class Roof:
    kind: str = 'gable'           # gable|hip|irimoya|hogyo|shed|flat|none
    mat: str = 'kawara'           # kawara|metal|teppan|tonton|kaya
    slope: float = 0.5            # 勾配(5 寸=0.5)
    eave: float = 0.7             # 軒の出
    verge: float = 0.5            # けらばの出(切妻)/入母屋の妻の出/片流れの背の出
    axis: object = 'long'         # 棟の向き 'long'|'short'|方位の度
    color: str = None
    thick: float = None
    ridge: bool = True
    oni: bool = True              # 鬼瓦
    kengyo: bool = False          # 懸魚
    hafu_col: str = '#3a2e26'     # 破風板・鼻隠し
    soffit_col: str = '#c9b79c'   # 軒裏
    rafters: object = None        # 化粧垂木(None=lod2 で)
    rafter_col: str = None
    gutters: bool = True
    irimoya_k: float = 0.5        # 入母屋の寄棟部分の高さの割合
    chidori: list = dfield(default_factory=list)    # 千鳥破風 [(位置 -1..1, 幅 m, +1 前/-1 後)]
    gable_window: bool = False    # 切妻の妻の小窓
    gable_col: str = None         # 入母屋の妻壁の色(None=最上階の壁)
    gable_style: str = 'plaster'  # plaster|timber|lattice
    parapet: float = 0.8          # 陸屋根のパラペット
    coping_col: str = '#9a9a96'
    penthouse: list = dfield(default_factory=list)  # 陸屋根の塔屋 [(dx, dy, 幅, 奥行, 高さ)](屋根の矩形の u,v 方向 m)
    finial: bool = True           # 宝形の宝珠


@dataclass
class Attach:
    """付属物。kind: ac|pipe|sign|lanterns|nobori|chimney|tent|stair|steps|porch|noren|crest|tank|box|cupola"""
    kind: str
    side: object = 'front'
    floor: int = 1
    s: float = None               # 辺の始点から m(負=終点から)
    at: float = None              # 辺の割合 0..1(s より優先)
    z: float = None               # 階の床から m
    d: float = None               # 壁から外へ m
    w: float = None
    h: float = None
    n: int = 1
    color: str = None
    color2: str = None
    style: str = None
    text: str = ''                # 看板の文字(このフェーズでは枠だけ。後で使う)
    prm: dict = dfield(default_factory=dict)


@dataclass
class BuildingSpec:
    id: str
    name: str = ''
    ring: list = None             # 外形(None なら OSM の id から)
    zone: str = None
    floors: int = 2
    floor_h: object = 3.0         # 数値か階ごとのリスト
    found_h: float = 0.3          # 基礎の天端=1 階の床の、敷地からの高さ
    found: str = 'concrete'       # concrete|stone|stone_round|none
    found_col: str = None
    base_z: float = None          # 1 階の床の Blender Z(None=敷地+found_h)
    front: object = None          # 正面の方位(度/16方位)。None=最長辺
    walls: dict = dfield(default_factory=lambda: {'*': WallFinish()})   # {階|'*': WallFinish}
    side_walls: dict = dfield(default_factory=dict)                       # {辺: {階|'*': WallFinish}}
    facades: dict = dfield(default_factory=lambda: {'*': Facade()})     # {辺|'*': Facade}
    setbacks: dict = dfield(default_factory=dict)                         # {階: {辺: m}}(内へ。負=張り出し)
    terrace_rail: str = 'wall'    # セットバックの屋上テラスの手すり(None=なし)
    balconies: list = dfield(default_factory=list)
    pents: list = dfield(default_factory=list)
    roof: Roof = dfield(default_factory=Roof)
    attach: list = dfield(default_factory=list)
    wings: list = dfield(default_factory=list)    # 別棟(BuildingSpec)。same_level=True なら床の高さを親に合わせる
    same_level: bool = True
    use_obb: bool = False         # 外形を最小回転矩形にする
    lod: int = 1                  # 0=遠景(開口は面だけ・屋根の割りなし) 1=標準 2=主役(垂木・細かい格子・石積み)
    age: float = 0.4              # 経年(足元の汚れ・雨だれ・色むら)
    seed: int = None
    replaces: list = None         # 消す仮の箱の id(None=[id])
    note: str = ''


@dataclass
class Op:
    ch: str
    s0: float
    s1: float
    zb: float
    zt: float


SIZES = {  # 文字: (幅 | None=柱間いっぱい, 高さ | None=階高-0.45-腰高, 腰高)
    'W': (1.6, 1.25, 0.85), 'w': (0.75, 0.6, 1.35), 'T': (0.85, 1.9, 0.55), 'L': (1.7, 1.1, 0.8),
    'R': (None, 1.3, 0.8), 'A': (1.0, 2.1, 0.55), 'K': (0.95, 1.25, 0.75),
    'D': (1.8, 2.1, 0.0), 'G': (1.8, 2.2, 0.0), 'P': (None, 2.4, 0.0), 'S': (None, None, 0.0), 'H': (None, None, 0.0),
}
MERGE = set('RSHP')
GLASSY = set('WwTRLAK')


def layout(L, fac, floor, hfl):
    """辺の長さ L・階・階高 -> (開口 [Op(相対 z)], 柱間の境界 s のリスト)。"""
    pat = None
    if fac.pattern:
        pat = fac.pattern.get(floor, fac.pattern.get('*'))
    usable = L - 2 * fac.margin
    if usable < 0.7:
        return [], []
    if pat is None:
        ch = fac.ground if (floor == 1 and fac.ground) else fac.win
        n = int(round(usable / fac.bay))
        if n < 1 or not ch:
            return [], []
        pat = (ch * n)[:n]       # 1 文字なら全部その文字、複数文字なら繰り返しの模様
    pat = pat.replace(' ', '')
    n = len(pat)
    if n == 0:
        return [], []
    bw = usable / n
    bounds = [fac.margin + i * bw for i in range(n + 1)]
    sizes = dict(SIZES)
    if fac.sizes:
        sizes.update(fac.sizes)
    ops = []
    i = 0
    while i < n:
        c = pat[i]
        if c not in sizes:
            i += 1
            continue
        j = i
        if c in MERGE:
            while j + 1 < n and pat[j + 1] == c:
                j += 1
        s0, s1 = bounds[i], bounds[j + 1]
        span = s1 - s0
        w, h, sill = sizes[c]
        w = span - 0.24 if (w is None or c in MERGE) else min(w, span - 0.24)
        if w >= 0.3:
            if h is None:
                h = hfl - 0.45 - sill
            h = min(h, hfl - sill - 0.22)
            if h >= 0.3:
                sc = (s0 + s1) / 2
                ops.append(Op(c, sc - w / 2, sc + w / 2, sill, sill + h))
        i = j + 1
    return ops, bounds


# ====================================================================== 屋根面
def roof_plane(pb, pts, kind, col, lod, anchor=None, thick=0.0, under_col=None, seed=0):
    """屋根面(3D の凸多角形、最初の辺が軒)を、材の割り(瓦の段と筋・縦ハゼ・瓦棒・とんとんの段・茅の段)で張る。"""
    m = ROOF_MAT.get(kind, 'roof')
    P = [np.array(p, float) for p in pts]
    n = np.array(newell(pts), float)
    nn = float(np.linalg.norm(n))
    if nn < 1e-9:
        return
    n = n / nn
    if n[2] < 0:
        n = -n
    e = P[1] - P[0]
    e = e / max(float(np.linalg.norm(e)), 1e-9)
    w = np.cross(n, e)
    if w[2] < 0:
        w = -w
    a0 = np.array(anchor if anchor is not None else pts[0], float)
    base = a0 - n * float((a0 - P[0]) @ n)
    poly = [(float((p - base) @ e), float((p - base) @ w)) for p in P]
    ys = [q[1] for q in poly]
    xs = [q[0] for q in poly]
    ymin, ymax = min(ys), max(ys)
    xmin, xmax = min(xs), max(xs)

    def W3(x, y, h=0.0):
        p = base + e * x + w * y + n * h
        return (p[0], p[1], p[2])
    course = {'kawara': 0.3, 'tonton': 0.2, 'kaya': 0.36, 'metal': 99.0, 'teppan': 99.0}.get(kind, 99.0)
    step = {'kawara': 0.022, 'tonton': 0.016, 'kaya': 0.07}.get(kind, 0.0)
    if lod <= 0:
        course, step = 99.0, 0.0
    elif lod == 1:
        if kind == 'tonton':
            course = 0.3
        if kind == 'kawara':
            step = 0.0
    k0 = int(math.floor(ymin / course))
    k1 = int(math.ceil(ymax / course))
    for k in range(k0, k1):
        ya, yb = max(k * course, ymin), min((k + 1) * course, ymax)
        if yb - ya < 1e-4:
            continue
        Q = clip_half(poly, 0.0, 1.0, -ya)
        Q = clip_half(Q, 0.0, -1.0, yb)
        if len(Q) < 3:
            continue
        lift = step if (step > 0 and ya > ymin + 1e-4) else 0.0
        cc = hj(col, 0.05, k, seed) if course < 50 else col
        if course < 50 and k % 2:
            cc = tint(cc, 0.93)
        Q3 = [W3(x, y, lift if abs(y - ya) < 1e-6 else 0.0) for (x, y) in Q]
        pb.poly(m, Q3, cc, tuple(n))
        if lift > 0:
            xs_ = [x for (x, y) in Q if abs(y - ya) < 1e-6]
            if len(xs_) >= 2:
                xa, xb = min(xs_), max(xs_)
                pb.poly(m, [W3(xa, ya, 0), W3(xb, ya, 0), W3(xb, ya, lift), W3(xa, ya, lift)], tint(cc, 0.82), tuple(-w))
    # 縦の筋(瓦の丸瓦の列・縦ハゼ・瓦棒)
    rib = {'kawara': (0.30, 0.075, 0.055), 'metal': (0.45, 0.012, 0.035), 'teppan': (0.42, 0.025, 0.04)}.get(kind)
    if rib and lod >= 1:
        pitch, hw, hh = rib
        if lod == 1 and kind == 'kawara':
            pitch = 0.36
        rc = tint(col, 0.88)
        for k in range(int(math.ceil((xmin + 0.05) / pitch)), int(math.floor((xmax - 0.05) / pitch)) + 1):
            x = k * pitch
            ext = vextent(poly, x)
            if ext is None:
                continue
            ya, yb = ext[0] + 0.02, ext[1] - 0.04
            if yb - ya < 0.2:
                continue
            l0, l1 = W3(x - hw, ya, 0.004), W3(x - hw, yb, 0.004)
            r0, r1 = W3(x + hw, ya, 0.004), W3(x + hw, yb, 0.004)
            t0, t1 = W3(x, ya, hh + step), W3(x, yb, hh + step)
            if kind == 'teppan':
                tl0, tl1 = W3(x - hw, ya, hh), W3(x - hw, yb, hh)
                tr0, tr1 = W3(x + hw, ya, hh), W3(x + hw, yb, hh)
                pb.poly(m, [l0, l1, tl1, tl0], rc, tuple(n - e))
                pb.poly(m, [tl0, tl1, tr1, tr0], rc, tuple(n))
                pb.poly(m, [tr0, tr1, r1, r0], rc, tuple(n + e))
            else:
                pb.poly(m, [l0, l1, t1, t0], rc, tuple(n - e * 0.7))
                pb.poly(m, [t0, t1, r1, r0], rc, tuple(n + e * 0.7))
                if kind == 'kawara' and lod >= 2:
                    pb.poly(m, [l0, t0, r0], tint(rc, 0.8), tuple(-w))
    if thick > 0:
        U = [(p[0], p[1], p[2] - thick) for p in pts]
        pb.poly(m if under_col is None else 'wood', U, lin(under_col) if under_col is not None else tint(col, 0.7), (0, 0, -1))


# ====================================================================== 1 棟の組み立て
@dataclass
class Built:
    pb: PB
    signs: list
    info: dict


class Builder:
    def __init__(self, spec, field=None, lod_cap=None, parent=None):
        self.spec = spec
        self.field = field
        self.lod = spec.lod if lod_cap is None else min(spec.lod, lod_cap)
        self.lod_cap = lod_cap
        seed = spec.seed if spec.seed is not None else (zlib.crc32(spec.id.encode('utf-8')) & 0xffff)
        self.seed = seed
        self.rs = np.random.RandomState(seed)
        self.pb = PB()
        self.signs = []
        self.parent = parent
        self.roofinfo = {}

    def sk(self, kind):
        """細い部材の省く面(lod1 は見えにくい小口を省く)。v=縦材、h=横材、b=両面から見える縦の子。"""
        if kind == 'v':
            return ('-y',) if self.lod >= 2 else ('-y', '-z', '+z')
        if kind == 'h':
            return ('-y',) if self.lod >= 2 else ('-y', '-x', '+x')
        return ('-z', '+z', '-x', '+x')

    # -------------------------------------------------- 地面・高さ
    def ground(self, x, y):
        if self.field is not None:
            return float(self.field.Z(np.array([x]), np.array([y]))[0])
        return self.gmin + 0.25

    def resolve_ring(self):
        sp = self.spec
        ring = sp.ring
        if ring is None:
            if self.field is None:
                raise ValueError('ring が無く field も無い: %s' % sp.id)
            b = _bld_by_id(self.field).get(sp.id)
            if b is None:
                raise ValueError('OSM に無い id: %s' % sp.id)
            ring = b['ring']
        ring = C.ccw(C.clean_ring([tuple(map(float, p[:2])) for p in ring]))
        if sp.use_obb:
            ring = obb_ring(ring)
        return ring

    def levels(self, ring):
        sp = self.spec
        P = np.array(ring)
        cen = P.mean(axis=0)
        if self.field is None:
            pad = (sp.base_z - sp.found_h) if sp.base_z is not None else 0.0
            return pad, pad - 0.25
        b = _bld_by_id(self.field).get(sp.id)
        if b is not None:
            pad = b['pad'] - C.ZBASE
        else:
            pad = float(np.mean(self.field.Z(np.append(P[:, 0], cen[0]), np.append(P[:, 1], cen[1]))))
        dv = P - cen
        out = P + dv / np.maximum(np.hypot(*dv.T), 1e-6)[:, None] * 1.0
        zg = self.field.Z(np.concatenate([P[:, 0], out[:, 0]]), np.concatenate([P[:, 1], out[:, 1]]))
        return pad, min(float(zg.min()), pad) - 0.25

    # -------------------------------------------------- 辺の呼び名
    def classify(self, ring):
        n = len(ring)
        Ls, N = [], []
        for i in range(n):
            W = Wall(ring[i], ring[(i + 1) % n])
            Ls.append(W.L)
            N.append(W.n)
        if self.spec.front is not None:
            f = bearing_vec(self.spec.front)
        else:
            i = int(np.argmax(Ls))
            f = N[i]
        self.front = f
        right = np.array([-f[1], f[0]])      # 正面に向かって右
        rel, cmp_ = [], []
        for nv in N:
            dt = float(nv @ f)
            if dt >= math.cos(math.radians(45)):
                rel.append('front')
            elif dt <= -math.cos(math.radians(45)):
                rel.append('back')
            else:
                rel.append('right' if float(nv @ right) > 0 else 'left')
            cmp_.append(compass8(nv))
        self.rel = rel
        self.cmp = cmp_

    def match(self, i, side):
        if side is None or side == '*' or side == 'all':
            return True
        if isinstance(side, (list, tuple, set)):
            return any(self.match(i, s) for s in side)
        if isinstance(side, int):
            return i == side
        return side == self.rel[i] or side == self.cmp[i]

    def lookup(self, d, i, default):
        for key in (i, self.cmp[i], self.rel[i], '*'):
            if key in d:
                return d[key]
        return default

    def facade_for(self, i):
        return self.lookup(self.spec.facades, i, Facade())

    def finish_for(self, floor, i):
        sw = self.lookup(self.spec.side_walls, i, None)
        for dct in ((sw or {}), self.spec.walls):
            if floor in dct:
                return dct[floor]
            if '*' in dct:
                return dct['*']
        return WallFinish()

    def edges(self, side, k=0, minlen=0.8):
        ring = self.rings[k]
        out = []
        for i in range(len(ring)):
            if self.match(i, side):
                W = Wall(ring[i], ring[(i + 1) % len(ring)])
                if W.L >= minlen:
                    out.append((i, W))
        return out

    def main_edge(self, side, k=0):
        es = self.edges(side, k, 0.3)
        if not es:
            es = self.edges('*', k, 0.3)
        return max(es, key=lambda e: e[1].L)

    # -------------------------------------------------- 本体
    def run(self):
        sp = self.spec
        ring = self.resolve_ring()
        self.ring0 = ring
        pad, gmin = self.levels(ring)
        self.gmin = gmin
        if self.parent is not None and sp.same_level and sp.base_z is None:
            base = self.parent.base_z
        else:
            base = sp.base_z if sp.base_z is not None else pad + sp.found_h
        self.base_z = base
        nf = max(1, int(sp.floors))
        fh = list(sp.floor_h) if isinstance(sp.floor_h, (list, tuple)) else [float(sp.floor_h)] * nf
        fh = (fh + [fh[-1]] * nf)[:nf]
        self.fh = fh
        self.zs = [base + sum(fh[:k]) for k in range(nf)]
        self.ztop = base + sum(fh)
        self.classify(ring)
        # 階ごとの外形(セットバック・張り出し)
        rings = []
        cur = [0.0] * len(ring)
        for k in range(nf):
            sb = sp.setbacks.get(k + 1)
            if sb:
                cur = [0.0] * len(ring)
                for i in range(len(ring)):
                    for key, dv in sb.items():
                        if self.match(i, key):
                            cur[i] = float(dv)
            rings.append(offset_ring(ring, cur) if any(abs(x) > 1e-6 for x in cur) else list(ring))
        self.rings = rings
        self.foundation()
        self.walls()
        self.caps()
        self.build_roof()
        for B in sp.balconies:
            self.balcony(B)
        for Pn in sp.pents:
            self.pent_spec(Pn)
        for A in sp.attach:
            try:
                self.attach(A)
            except Exception as ex:  # 付属物の失敗は建物全体を止めない
                print('  attach %s failed on %s: %s' % (A.kind, sp.id, ex))
        if self.spec.age > 0:
            weather(self.pb, self.spec.age, self.gmin + 0.25, self.seed)
        for wsp in sp.wings:
            wb = Builder(wsp, self.field, self.lod_cap, parent=self)
            r = wb.run()
            self.pb.merge(r.pb)
            self.signs.extend(r.signs)
        info = dict(id=sp.id, name=sp.name, tris=self.pb.tris(), by_mat=self.pb.tris_by_mat(), lod=self.lod,
                    base_z=round(base, 2), top_z=round(self.ztop, 2), ridge_z=round(self.roofinfo.get('zr', self.ztop), 2),
                    floors=nf, ring=[[round(p[0], 2), round(p[1], 2)] for p in ring])
        return Built(self.pb, self.signs, info)

    # -------------------------------------------------- 基礎
    def foundation(self):
        sp = self.spec
        if sp.found == 'none':
            return
        z0, z1 = self.gmin, self.base_z
        if z1 - z0 < 0.02:
            return
        kind = {'stone': 'stone', 'stone_round': 'stone_round'}.get(sp.found, 'mortar')
        col = sp.found_col or ('#8f8c86' if kind == 'stone' else '#3a3836' if kind == 'stone_round' else PAL['concrete'])
        fin = WallFinish(kind, col, mat='stone')
        ring = self.ring0
        off = 0.04
        zcut = max(z0, z1 - (sp.found_h + 0.35)) if kind in ('stone', 'stone_round') else z0
        for i in range(len(ring)):
            W = Wall(ring[i], ring[(i + 1) % len(ring)], off)
            if W.L < 0.05:
                continue
            if zcut > z0 + 0.01:     # 深い所(斜面の低い側)は石を積まずにコンクリート
                W.quad(self.pb, 'stone', -off, z0, W.L + off, zcut, -0.01, lin('#8e8b84'))
            lod_save = self.lod
            fl = self.facade_for(i).lod
            if fl is not None:
                self.lod = min(self.lod, fl)
            self.piece(W, -off, W.L + off, zcut, z1, fin)
            self.lod = lod_save
            if self.lod >= 1 and kind == 'mortar':     # 天端の水切り
                W.box(self.pb, 'stone', -off, W.L + off, z1 - 0.04, z1, 0, 0.025, tint(lin(col), 0.85))

    # -------------------------------------------------- 壁の仕上げ(矩形 1 枚)
    def piece(self, W, s0, s1, z0, z1, fin):
        if s1 - s0 < 1e-3 or z1 - z0 < 1e-3:
            return
        pb, lod = self.pb, self.lod
        kind = fin.kind
        c = lin(fin.color)
        m = fin.mat or ('wood' if kind in ('board_h', 'board_v', 'louver') else 'stone' if kind in ('stone', 'stone_round') else 'wall')
        if lod == 0 or kind in ('plaster', 'mortar', 'spray', 'paint'):
            W.quad(pb, m, s0, z0, s1, z1, 0.0, c)
            return
        if kind == 'board_h':           # 下見板(横羽目): 段ごとに下端を少し出す
            bh = fin.pitch or (0.2 if lod >= 2 else 0.3)
            lap = 0.018
            for r in range(int(math.floor(z0 / bh)), int(math.ceil(z1 / bh))):
                za, zb = max(r * bh, z0), min((r + 1) * bh, z1)
                if zb - za < 1e-3:
                    continue
                cc = hj(c, 0.05, r, self.seed)
                pb.poly(m, [W.P(s0, za, lap), W.P(s1, za, lap), W.P(s1, zb, 0.0), W.P(s0, zb, 0.0)], cc, W.nrm())
            return
        if kind == 'board_v':           # 縦板張り+押縁
            p = fin.pitch or 0.45
            ks = list(range(int(math.ceil(s0 / p)), int(math.floor(s1 / p)) + 1))
            edges_ = [s0] + [k * p for k in ks if s0 + 0.02 < k * p < s1 - 0.02] + [s1]
            for j in range(len(edges_) - 1):
                cc = hj(c, 0.06, round(edges_[j] / p), self.seed) if lod >= 2 else c
                W.quad(pb, m, edges_[j], z0, edges_[j + 1], z1, 0.0, cc)
            bc = tint(c, 0.82)
            for s in edges_[1:-1]:
                W.box(pb, m, s - 0.022, s + 0.022, z0, z1, 0.0, 0.022, bc, skip=('-y', '-z', '+z'))
            return
        if kind == 'louver':            # 縦格子張り(ルーバー)
            W.quad(pb, 'dark', s0, z0, s1, z1, 0.0, tint(c, 0.35))
            p = fin.pitch or (0.12 if lod >= 2 else 0.2)
            for k in range(int(math.ceil((s0 + 0.02) / p)), int(math.floor((s1 - 0.02) / p)) + 1):
                s = k * p
                W.box(pb, m, s - 0.02, s + 0.02, z0, z1, 0.0, 0.07, hj(c, 0.05, k, self.seed), skip=('-y', '-z', '+z'))
            return
        if kind == 'tile':              # タイル張り: 目地の面の上に段(lod2 は1枚ずつ)
            th = fin.pitch or 0.24
            g = 0.012
            W.quad(pb, m, s0, z0, s1, z1, 0.0, tint(c, 0.78))
            tl = th * 2.2
            for r in range(int(math.floor(z0 / th)), int(math.ceil(z1 / th))):
                za, zb = max(r * th + g / 2, z0), min((r + 1) * th - g / 2, z1)
                if zb - za < 1e-3:
                    continue
                if lod >= 2:
                    off = (r % 2) * tl / 2
                    for k in range(int(math.floor((s0 - off) / tl)), int(math.ceil((s1 - off) / tl))):
                        sa, sb = max(k * tl + off + g / 2, s0), min((k + 1) * tl + off - g / 2, s1)
                        if sb - sa > 1e-3:
                            W.quad(pb, m, sa, za, sb, zb, 0.006, hj(c, 0.04, r, k, self.seed))
                else:
                    W.quad(pb, m, s0, za, s1, zb, 0.006, hj(c, 0.03, r, self.seed))
            return
        if kind == 'stone':             # 切石積み(布積み): 石を1個ずつ出す
            ch = fin.pitch or 0.32
            g = 0.018
            bl = 1.0 if lod >= 2 else 1.4
            W.quad(pb, m, s0, z0, s1, z1, 0.0, tint(c, 0.6))
            for r in range(int(math.floor(z0 / ch)), int(math.ceil(z1 / ch))):
                za, zb = max(r * ch + g / 2, z0), min((r + 1) * ch - g / 2, z1)
                if zb - za < 0.02:
                    continue
                off = (r % 2) * bl / 2
                for k in range(int(math.floor((s0 - off) / bl)), int(math.ceil((s1 - off) / bl))):
                    sa, sb = max(k * bl + off + g / 2, s0), min((k + 1) * bl + off - g / 2, s1)
                    if sb - sa < 0.03:
                        continue
                    pr = 0.025 + 0.025 * hfrac(r, k, self.seed) if lod >= 2 else 0.03
                    W.box(pb, m, sa, sb, za, zb, 0.0, pr, hj(c, 0.09, r, k, self.seed), skip=('-y',) if lod >= 2 else ('-y', '-z'))
            return
        if kind == 'stone_round':       # 玉石積み: 丸い石のふくらみ
            W.quad(pb, m, s0, z0, s1, z1, 0.0, tint(c, 0.55))
            rr = fin.pitch or 0.17
            nseg = 8 if lod >= 2 else 6
            for r in range(int(math.floor(z0 / (rr * 1.75))), int(math.ceil(z1 / (rr * 1.75)))):
                zc = (r + 0.5) * rr * 1.75
                off = (r % 2) * rr
                for k in range(int(math.floor((s0 - off) / (rr * 2))), int(math.ceil((s1 - off) / (rr * 2)))):
                    sc = (k + 0.5) * rr * 2 + off
                    r2 = rr * (0.8 + 0.25 * hfrac(r, k, self.seed))
                    if sc - r2 < s0 or sc + r2 > s1 or zc - r2 < z0 or zc + r2 > z1:
                        continue
                    apex = W.P(sc, zc, r2 * 0.7)
                    cc = hj(c, 0.15, r, k, self.seed)
                    ring_ = [W.P(sc + r2 * math.cos(a), zc + r2 * 0.9 * math.sin(a), 0.01) for a in np.linspace(0, 2 * math.pi, nseg, endpoint=False)]
                    for j in range(nseg):
                        pb.poly(m, [ring_[j], ring_[(j + 1) % nseg], apex], cc, W.nrm())
            return
        W.quad(pb, m, s0, z0, s1, z1, 0.0, c)

    def surface(self, W, bands, ops):
        """壁面を開口で抜いて仕上げの矩形に分ける。bands=[(z0,z1,WallFinish)]。"""
        for (za, zb, fin) in bands:
            if zb - za < 1e-3:
                continue
            xs = {0.0, W.L}
            for o in ops:
                if o.zt > za and o.zb < zb:
                    xs.add(min(max(o.s0, 0.0), W.L))
                    xs.add(min(max(o.s1, 0.0), W.L))
            xs = sorted(xs)
            for sa, sb in zip(xs[:-1], xs[1:]):
                if sb - sa < 1e-4:
                    continue
                sm = (sa + sb) / 2
                cuts = sorted((max(o.zb, za), min(o.zt, zb)) for o in ops if o.s0 < sm < o.s1 and o.zt > za and o.zb < zb)
                z = za
                for c0, c1 in cuts:
                    if c0 > z + 1e-4:
                        self.piece(W, sa, sb, z, c0, fin)
                    z = max(z, c1)
                if zb > z + 1e-4:
                    self.piece(W, sa, sb, z, zb, fin)

    # -------------------------------------------------- 壁・開口
    def walls(self):
        sp = self.spec
        self.edge_ops = {}
        nf = len(self.fh)
        for k in range(nf):
            ring = self.rings[k]
            z0 = self.zs[k]
            z1 = z0 + self.fh[k]
            for i in range(len(ring)):
                W = Wall(ring[i], ring[(i + 1) % len(ring)])
                if W.L < 0.05:
                    continue
                fac = self.facade_for(i)
                fin = self.finish_for(k + 1, i)
                lod_save = self.lod
                if fac.lod is not None:
                    self.lod = min(self.lod, fac.lod)
                if W.L >= 1.0:
                    rel_ops, bounds = layout(W.L, fac, k + 1, self.fh[k])
                else:
                    rel_ops, bounds = [], []
                ops = [Op(o.ch, o.s0, o.s1, z0 + o.zb, z0 + o.zt) for o in rel_ops]
                bands = [(z0, z1, fin)]
                if fin.koshi:
                    kh, kk, kc = fin.koshi
                    bands = [(z0, min(z0 + kh, z1), WallFinish(kk, kc)), (min(z0 + kh, z1), z1, fin)]
                self.surface(W, bands, ops)
                for o in ops:
                    self.opening(W, o, fac, fin)
                if fin.koshi and self.lod >= 1:      # 腰の見切り
                    zk = z0 + fin.koshi[0]
                    for sa, sb in subtract([(0.0, W.L)], [(o.s0, o.s1) for o in ops if o.zb < zk < o.zt]):
                        W.box(self.pb, 'wood', sa, sb, zk - 0.03, zk + 0.03, 0.0, 0.035, tint(lin(fin.koshi[2]), 0.8))
                if fin.timber is not None:
                    self.timber(W, z0, z1, ops, bounds, fin.timber)
                if fac.fins and bounds and self.lod >= 0:
                    fw, fd = fac.fins[0], fac.fins[1]
                    for s in bounds:
                        if fw / 2 < s < W.L - fw / 2:
                            W.box(self.pb, 'wall', s - fw / 2, s + fw / 2, z0, z1, 0.0, fd, tint(lin(fin.color), 0.97))
                if fac.belt and k > 0 and self.lod >= 1:
                    W.box(self.pb, 'wall', 0.0, W.L, z0 - 0.09, z0 + 0.09, 0.0, 0.05, tint(lin(fin.color), 0.9))
                self.edge_ops[(k, i)] = (W, ops, bounds)
                self.lod = lod_save

    def timber(self, W, z0, z1, ops, bounds, tim):
        if self.lod == 0:
            return
        pb = self.pb
        w, pr, c, m = tim.w, tim.proud, lin(tim.color), tim.mat
        ss = [w / 2, W.L - w / 2]
        if tim.posts == 'bay':
            if bounds:
                ss += list(bounds)
            else:
                n = max(1, int(round(W.L / 1.8)))
                ss += [W.L * j / n for j in range(1, n)]
        elif isinstance(tim.posts, (int, float)):
            n = max(1, int(round(W.L / tim.posts)))
            ss += [W.L * j / n for j in range(1, n)]
        ss = sorted(ss)
        uniq = []
        for s in ss:
            if not uniq or s - uniq[-1] > w * 1.5:
                uniq.append(s)
        for s in uniq:
            s = min(max(s, w / 2), W.L - w / 2)
            segs = subtract([(z0, z1)], [(o.zb, o.zt) for o in ops if o.s0 < s + w / 2 and o.s1 > s - w / 2])
            for za, zb in segs:
                W.box(pb, m, s - w / 2, s + w / 2, za, zb, 0.0, pr, c, skip=self.sk('v'))
        zl = []
        for b in tim.beams:
            if b == 'bottom':
                zl.append(z0 + w / 2)
            elif b == 'top':
                zl.append(z1 - w / 2)
            elif b == 'head':
                heads = [o.zt for o in ops if o.zt < z1 - w * 1.5]
                if heads:
                    zl.append(max(heads) + w / 2)
                else:
                    zl.append(z0 + (z1 - z0) * 0.72)
            elif b == 'sill':
                sills = [o.zb for o in ops if o.zb > z0 + 0.3]
                if sills:
                    zl.append(min(sills) - w / 2)
            elif isinstance(b, (int, float)):
                zl.append(z0 + b)
        for zc in zl:
            for sa, sb in subtract([(0.0, W.L)], [(o.s0, o.s1) for o in ops if o.zb < zc + w / 2 and o.zt > zc - w / 2]):
                W.box(pb, m, sa, sb, zc - w / 2, zc + w / 2, 0.0, pr * 1.2, tint(c, 0.95), skip=self.sk('h'))
        if tim.braces:
            pts = uniq
            for j in range(len(pts) - 1):
                sa, sb = pts[j], pts[j + 1]
                if sb - sa < 0.6 or any(o.s0 < sb and o.s1 > sa for o in ops):
                    continue
                if j % 2:
                    W.beam(pb, m, (sa + w * 0.7, z0 + w, pr / 2), (sb - w * 0.7, z1 - w, pr / 2), w * 0.75, pr, c, skip=('-z',))
                else:
                    W.beam(pb, m, (sa + w * 0.7, z1 - w, pr / 2), (sb - w * 0.7, z0 + w, pr / 2), w * 0.75, pr, c, skip=('-z',))

    def arc_pts(self, ch, s0, s1, zs, zt):
        n = 8 if self.lod >= 2 else 5
        sc, hw = (s0 + s1) / 2, (s1 - s0) / 2
        if ch == 'A':
            return [(sc - hw * math.cos(t), zs + (zt - zs) * math.sin(t)) for t in np.linspace(0, math.pi, n + 1)]
        # 花頭窓: 左右から内へふくらんでから尖る(ベジェ)
        P0, P1, P2, P3 = np.array([s0, zs]), np.array([s0 - 0.1 * hw, zs + 0.55 * (zt - zs)]), np.array([sc - 0.35 * hw, zt - 0.05 * (zt - zs)]), np.array([sc, zt])
        left = []
        for t in np.linspace(0, 1, n + 1):
            p = (1 - t) ** 3 * P0 + 3 * (1 - t) ** 2 * t * P1 + 3 * (1 - t) * t * t * P2 + t ** 3 * P3
            left.append((float(p[0]), float(p[1])))
        right = [(2 * sc - s, z) for (s, z) in reversed(left[:-1])]
        return left + right

    def opening(self, W, o, fac, fin):
        pb, lod = self.pb, self.lod
        ch, s0, s1, zb, zt = o.ch, o.s0, o.s1, o.zb, o.zt
        w = s1 - s0
        wallc = lin(fin.color if not fin.koshi or zb > self.zs[0] + fin.koshi[0] else fin.color)
        wm = fin.mat or ('wood' if fin.kind in ('board_h', 'board_v', 'louver') else 'stone' if fin.kind in ('stone', 'stone_round') else 'wall')
        if lod == 0:
            if ch in GLASSY:
                W.quad(pb, 'glass', s0, zb, s1, zt, 0.015, lin(fac.glass))
            else:
                W.quad(pb, 'dark', s0, zb, s1, zt, 0.015, lin(PAL['interior']))
            return
        rev = fac.rev
        if ch == 'S':
            rev = max(rev, 0.7)
        elif ch == 'H':
            rev = max(rev, 0.3)
        elif ch in 'DGP':
            rev = max(rev, 0.22)
        arch = ch in 'AK'
        zs_ = max(zt - (w / 2 if ch == 'A' else 0.62 * w), zb + 0.2) if arch else zt
        rc = tint(wallc, 0.8)
        pb.poly(wm, [W.P(s0, zb, 0), W.P(s0, zs_, 0), W.P(s0, zs_, -rev), W.P(s0, zb, -rev)], rc, W.tv(1))
        pb.poly(wm, [W.P(s1, zb, 0), W.P(s1, zb, -rev), W.P(s1, zs_, -rev), W.P(s1, zs_, 0)], rc, W.tv(-1))
        if not arch:
            pb.poly(wm, [W.P(s0, zt, 0), W.P(s0, zt, -rev), W.P(s1, zt, -rev), W.P(s1, zt, 0)], tint(rc, 0.8), (0, 0, -1))
        floorish = ch in 'SDGPH'
        pb.poly('stone' if floorish else wm, [W.P(s0, zb, 0), W.P(s1, zb, 0), W.P(s1, zb, -rev), W.P(s0, zb, -rev)],
                lin('#77736c') if floorish else tint(rc, 1.1), (0, 0, 1))
        arcs = None
        if arch:
            arcs = self.arc_pts(ch, s0, s1, zs_, zt)
            sc = (s0 + s1) / 2
            half = len(arcs) // 2
            for j in range(half):       # 左右の三角(壁)
                pb.poly(wm, [W.P(s0, zt, 0), W.P(*arcs[j], 0), W.P(*arcs[j + 1], 0)], wallc, W.nrm())
            for j in range(half, len(arcs) - 1):
                pb.poly(wm, [W.P(s1, zt, 0), W.P(*arcs[j], 0), W.P(*arcs[j + 1], 0)], wallc, W.nrm())
            for j in range(len(arcs) - 1):
                (sa, za), (sb_, zb_) = arcs[j], arcs[j + 1]
                mx, mz = (sa + sb_) / 2, (za + zb_) / 2
                dn = (sc - mx, zs_ - mz)
                pb.poly(wm, [W.P(sa, za, 0), W.P(sb_, zb_, 0), W.P(sb_, zb_, -rev), W.P(sa, za, -rev)], rc,
                        (W.t[0] * dn[0], W.t[1] * dn[0], dn[1]))
        d = -rev
        if ch in GLASSY:
            self.window(W, o, fac, d, zs_, arcs)
        elif ch == 'D':
            self.door_lattice(W, o, fac, d)
        elif ch == 'G':
            W.quad(pb, 'glass', s0, zb, s1, zt, d, lin(PAL['glass_dark']))
            fc = lin(FRAME_COL.get(fac.frame, '#b9bcbd'))
            n = 2 if w < 2.6 else 4
            for j in range(n):
                la, lb = s0 + j * w / n, s0 + (j + 1) * w / n
                dj = d + 0.02 + 0.03 * (j % 2)
                for (a_, b_) in ((la, la + 0.06), (lb - 0.06, lb)):
                    W.box(pb, 'metal', a_, b_, zb, zt, dj - 0.03, dj, fc)
                W.box(pb, 'metal', la, lb, zb, zb + 0.1, dj - 0.03, dj, fc)
                W.box(pb, 'metal', la, lb, zt - 0.06, zt, dj - 0.03, dj, fc)
        elif ch == 'P':
            self.itado(W, o, fac, d)
        elif ch == 'S':
            W.quad(pb, 'dark', s0, zb, s1, zt, d, lin('#3a2f27'))
            if lod >= 1:     # 奥の陳列台
                W.box(pb, 'wood', s0 + 0.25, s1 - 0.25, zb, zb + 0.85, d, d + 0.45, lin('#5a4535'), skip=('-y',))
            if fac.noren:
                self.noren(W, s0 + 0.05, s1 - 0.05, zt - 0.02, min(0.95, 0.42 * (zt - zb)), fac.noren, -0.07)
        elif ch == 'H':
            W.quad(pb, 'dark', s0, zb, s1, zt, d, lin('#2f2b28'))
            zc = zt - fac.shutter * (zt - zb)
            sc_ = lin('#a3a7a8')
            pitch = 0.1 if lod >= 2 else 0.25
            for r in range(int(math.ceil((zt - zc) / pitch))):
                za, zb2 = max(zt - (r + 1) * pitch, zc), zt - r * pitch
                pb.poly('metal', [W.P(s0, za, -0.11), W.P(s1, za, -0.11), W.P(s1, zb2, -0.13), W.P(s0, zb2, -0.13)], hj(sc_, 0.03, r), W.nrm())
            W.box(pb, 'metal', s0 - 0.06, s1 + 0.06, zt, zt + 0.32, 0.0, 0.24, lin('#8e9293'))
            for sa in (s0, s1 - 0.06):
                W.box(pb, 'metal', sa, sa + 0.06, zb, zt, -0.16, -0.06, lin('#7d8183'), skip=('-y', '-z'))

    def window(self, W, o, fac, d, zs_, arcs):
        pb, lod = self.pb, self.lod
        ch, s0, s1, zb, zt = o.ch, o.s0, o.s1, o.zb, o.zt
        w = s1 - s0
        wood = fac.frame == 'wood'
        fw = 0.065 if wood else 0.045
        fd = 0.06
        fm = 'wood' if wood else 'metal'
        fc = lin(FRAME_COL.get(fac.frame, fac.frame))
        gc = lin(fac.glass)
        if arcs:
            pts = [W.P(s0, zb, d), W.P(s1, zb, d)] + [W.P(s, z, d) for (s, z) in reversed(arcs[1:-1])]
            pb.poly('glass', pts, gc, W.nrm())
            W.box(pb, fm, s0, s0 + fw, zb, zs_, d, d + fd, fc)
            W.box(pb, fm, s1 - fw, s1, zb, zs_, d, d + fd, fc)
            for j in range(len(arcs) - 1):
                (sa, za), (sb_, zb_) = arcs[j], arcs[j + 1]
                W.beam(pb, fm, (sa, za - fw / 2, d + fd / 2), (sb_, zb_ - fw / 2, d + fd / 2), fw, fd, fc, skip=('-z', '-x', '+x'))
        else:
            W.quad(pb, 'glass', s0, zb, s1, zt, d, gc)
            W.box(pb, fm, s0, s0 + fw, zb, zt, d, d + fd, fc, skip=self.sk('v') + ('-x',))
            W.box(pb, fm, s1 - fw, s1, zb, zt, d, d + fd, fc, skip=self.sk('v') + ('+x',))
            W.box(pb, fm, s0, s1, zt - fw, zt, d, d + fd, fc, skip=self.sk('h') + ('+z',))
        W.box(pb, fm, s0, s1, zb, zb + fw, d, d + fd, fc, skip=self.sk('h') + ('-z',))
        # 中桟・方立
        if ch == 'R':
            n = max(2, int(round(w / 0.9)))
        elif ch in 'WT':
            n = 1 if w < 0.9 else (2 if w < 2.6 else 4)
        elif ch == 'A':
            n = 2
        elif ch == 'w':
            n = 1 if w < 0.9 else 2
        else:
            n = 1
        for j in range(1, n):
            sm = s0 + j * w / n
            W.box(pb, fm, sm - fw * 0.55, sm + fw * 0.55, zb, zs_, d, d + fd * 1.3, fc, skip=self.sk('v'))
        if ch == 'T' and lod >= 1:
            zm = zb + 0.72 * (zt - zb)
            W.box(pb, fm, s0, s1, zm - fw / 2, zm + fw / 2, d, d + fd, fc)
        if ch == 'A':
            W.box(pb, fm, s0, s1, zs_ - fw / 2, zs_ + fw / 2, d, d + fd, fc)
        if ch in 'LK':   # 格子(縦)
            lc = lin(fac.lattice_col) if fac.lattice_col else (fc if wood else lin(FRAME_COL['wood']))
            pitch = 0.075 if lod >= 2 else 0.13
            dd = d + min(0.12, (-d) * 0.6)
            bw = 0.026
            for k in range(1, int(w / pitch)):
                s = s0 + k * w / int(w / pitch)
                ztop = zt
                if arcs:
                    for j in range(len(arcs) - 1):
                        if (arcs[j][0] - s) * (arcs[j + 1][0] - s) <= 0 and abs(arcs[j + 1][0] - arcs[j][0]) > 1e-9:
                            tt = (s - arcs[j][0]) / (arcs[j + 1][0] - arcs[j][0])
                            ztop = arcs[j][1] + (arcs[j + 1][1] - arcs[j][1]) * tt
                            break
                W.box(pb, 'wood', s - bw / 2, s + bw / 2, zb, ztop, dd - 0.035, dd, lc, skip=('-y', '-z', '+z') if self.lod >= 2 else ('-y', '-z', '+z', '-x', '+x'))
            W.box(pb, 'wood', s0, s1, zb, zb + 0.05, dd - 0.045, dd, lc, skip=('-y',))
            if not arcs:
                W.box(pb, 'wood', s0, s1, zt - 0.05, zt, dd - 0.045, dd, lc, skip=('-y',))
                if lod >= 2 and zt - zb > 0.9:
                    zm = (zb + zt) / 2
                    W.box(pb, 'wood', s0, s1, zm - 0.02, zm + 0.02, dd - 0.045, dd, lc, skip=('-y',))
        # 水切り・額縁
        if zb - self.zs[0] > 0.2 or ch not in 'DGPSH':
            W.box(pb, 'metal' if not wood else 'wood', s0 - 0.04, s1 + 0.04, zb - 0.045, zb, 0.0, 0.05, tint(fc, 0.9), skip=self.sk('h'))
        if fac.trim:
            tc = tint(lin('#f0eee8'), 1.0)
            W.box(pb, 'wall', s0 - 0.08, s0, zb, zt, 0.0, 0.03, tc)
            W.box(pb, 'wall', s1, s1 + 0.08, zb, zt, 0.0, 0.03, tc)
            if not arcs:
                W.box(pb, 'wall', s0 - 0.08, s1 + 0.08, zt, zt + 0.08, 0.0, 0.03, tc)

    def door_lattice(self, W, o, fac, d):
        pb, lod = self.pb, self.lod
        s0, s1, zb, zt = o.s0, o.s1, o.zb, o.zt
        w = s1 - s0
        W.quad(pb, 'dark', s0, zb, s1, zt, d, lin('#2b2521'))
        fc = lin(fac.door_col)
        n = 1 if w < 1.1 else (2 if w < 3.0 else 4)
        zm = zb + 0.38 * (zt - zb)
        pitch = 0.05 if lod >= 2 else 0.1
        for j in range(n):
            la, lb = s0 + j * w / n, s0 + (j + 1) * w / n
            dj = d + 0.035 + 0.035 * (j % 2)
            for (a_, b_) in ((la, la + 0.05), (lb - 0.05, lb)):
                W.box(pb, 'wood', a_, b_, zb, zt, dj - 0.035, dj, fc)
            for (za, zb_) in ((zb, zb + 0.12), (zt - 0.07, zt), (zm - 0.03, zm + 0.03)):
                W.box(pb, 'wood', la + 0.05, lb - 0.05, za, zb_, dj - 0.035, dj, fc)
            W.quad(pb, 'wood', la + 0.05, zb + 0.12, lb - 0.05, zm - 0.03, dj - 0.02, tint(fc, 1.15))
            k = int((lb - la - 0.1) / pitch)
            for q in range(1, k):
                s = la + 0.05 + q * (lb - la - 0.1) / k
                W.box(pb, 'wood', s - 0.009, s + 0.009, zm + 0.03, zt - 0.07, dj - 0.03, dj - 0.005, fc, skip=('-y', '-z', '+z') if lod >= 2 else ('-y', '-z', '+z', '-x', '+x'))

    def itado(self, W, o, fac, d):
        pb, lod = self.pb, self.lod
        s0, s1, zb, zt = o.s0, o.s1, o.zb, o.zt
        fc = lin(fac.door_col)
        zr = zt - 0.5 if zt - zb > 2.3 else zt
        W.quad(pb, 'wood', s0, zb, s1, zr, d, tint(fc, 1.1))
        if zr < zt:          # 欄間(格子)
            W.quad(pb, 'dark', s0, zr, s1, zt, d, lin('#2b2521'))
            pitch = 0.06 if lod >= 2 else 0.12
            for k in range(1, int((s1 - s0) / pitch)):
                s = s0 + k * pitch
                W.box(pb, 'wood', s - 0.012, s + 0.012, zr, zt, d, d + 0.03, fc, skip=('-y', '-z', '+z'))
            W.box(pb, 'wood', s0, s1, zr - 0.04, zr + 0.04, d, d + 0.06, fc)
        n = max(2, int(round((s1 - s0) / 0.9)))
        for j in range(n + 1):
            s = s0 + j * (s1 - s0) / n
            W.box(pb, 'wood', max(s - 0.04, s0), min(s + 0.04, s1), zb, zr, d, d + 0.05, tint(fc, 0.85))
        for zz in (zb + 0.15, (zb + zr) / 2):
            W.box(pb, 'wood', s0, s1, zz - 0.04, zz + 0.04, d, d + 0.04, tint(fc, 0.85))
        if lod >= 2:
            p = 0.22
            for k in range(1, int((s1 - s0) / p)):
                s = s0 + k * p
                W.box(pb, 'wood', s - 0.006, s + 0.006, zb, zr, d, d + 0.012, tint(fc, 0.75), skip=('-y', '-z', '+z'))

    def noren(self, W, s0, s1, ztop, h, col, d):
        pb = self.pb
        W.box(pb, 'wood', s0 - 0.05, s1 + 0.05, ztop - 0.045, ztop, d - 0.02, d + 0.02, lin('#3a2c22'), skip=())
        n = max(2, int(round((s1 - s0) / 0.5)))
        pw = (s1 - s0) / n
        c = lin(col)
        tilt = 0.03 if self.lod >= 2 else 0.0
        for j in range(n):
            sa, sb = s0 + j * pw + 0.012, s0 + (j + 1) * pw - 0.012
            cc = hj(c, 0.04, j, self.seed)
            dz = 0.015 * (j % 2)
            pb.poly('fabric', [W.P(sa, ztop - 0.045 - h + dz, d + tilt), W.P(sb, ztop - 0.045 - h + dz, d + tilt),
                               W.P(sb, ztop - 0.045, d), W.P(sa, ztop - 0.045, d)], cc, W.nrm())
            pb.poly('fabric', [W.P(sa, ztop - 0.045 - h + dz, d + tilt - 0.004), W.P(sa, ztop - 0.045, d - 0.004),
                               W.P(sb, ztop - 0.045, d - 0.004), W.P(sb, ztop - 0.045 - h + dz, d + tilt - 0.004)], tint(cc, 0.8), W.nrm(-1))

    # -------------------------------------------------- 階の段差(屋上テラス・張り出しの下面)
    def caps(self):
        pb = self.pb
        for k in range(1, len(self.rings)):
            lo, hi = self.rings[k - 1], self.rings[k]
            if all(abs(a[0] - b[0]) < 1e-4 and abs(a[1] - b[1]) < 1e-4 for a, b in zip(lo, hi)):
                continue
            z = self.zs[k]
            for t in tess(lo):
                pb.poly('wall', [(lo[j][0], lo[j][1], z + 0.005) for j in t], lin(PAL['terrace']), (0, 0, 1))
            for t in tess(hi):
                pb.poly('wall', [(hi[j][0], hi[j][1], z - 0.005) for j in t], lin(PAL['soffit']), (0, 0, -1))
            fin = self.finish_for(k, 0)
            for i in range(len(lo)):
                a, b = lo[i], lo[(i + 1) % len(lo)]
                a2, b2 = hi[i], hi[(i + 1) % len(hi)]
                Wl = Wall(a, b)
                shift = float((np.array(a2) - np.array(a)) @ (-Wl.n))   # 正=上の階が内へ下がった
                if Wl.L < 0.3:
                    continue
                if shift > 0.3:       # 屋上テラスの縁(スラブの小口+手すり)
                    Wl.box(pb, 'wall', 0.0, Wl.L, z - 0.25, z + 0.06, 0.0, 0.05, tint(lin(fin.color), 0.92))
                    if self.spec.terrace_rail:
                        Wr = Wall(Wl.P(0.05, 0, -0.08), Wl.P(Wl.L - 0.05, 0, -0.08))
                        self.rail(Wr, 0.0, Wr.L, z + 0.06, self.spec.terrace_rail, 0.95, fin.color if self.spec.terrace_rail == 'wall' else None)
                elif shift < -0.2:    # 上の階が張り出す: 持ち送り
                    Wh = Wall(a2, b2)
                    if self.lod >= 1:
                        n = max(1, int(round(Wh.L / 1.8)))
                        for j in range(n + 1):
                            s = min(max(Wh.L * j / n, 0.1), Wh.L - 0.1)
                            Wh.beam(pb, 'wood', (s, z - 0.7, shift), (s, z - 0.03, -0.05), 0.09, 0.09, lin(PAL['timber']))
                    Wh.box(pb, 'wood', 0.0, Wh.L, z - 0.22, z, 0.0, 0.04, tint(lin(PAL['timber']), 1.0))

    # -------------------------------------------------- 手すり
    def rail(self, Wr, sa, sb, z, kind, h, color=None):
        pb, lod = self.pb, self.lod
        if sb - sa < 0.1:
            return
        if kind == 'wall':
            c = lin(color or PAL['spray'])
            Wr.box(pb, 'wall', sa, sb, z, z + h, -0.06, 0.06, c, skip=())
            Wr.box(pb, 'metal', sa - 0.02, sb + 0.02, z + h, z + h + 0.04, -0.075, 0.075, lin('#9a9a96'), skip=('-z',))
            return
        if lod == 0:
            c = lin(color or ('#3b2a20' if kind in ('wood', 'lattice') else '#b8bcbe'))
            Wr.quad(pb, 'wood' if kind in ('wood', 'lattice') else 'metal', sa, z, sb, z + h, 0.0, c)
            Wr.quad(pb, 'wood' if kind in ('wood', 'lattice') else 'metal', sa, z, sb, z + h, 0.0, c, k=-1)
            return
        if kind in ('wood', 'lattice'):
            c = lin(color or '#3b2a20')
            pw = 0.09
            n = max(1, int(round((sb - sa) / 1.8)))
            for j in range(n + 1):
                s = min(max(sa + (sb - sa) * j / n, sa + pw / 2), sb - pw / 2)
                Wr.box(pb, 'wood', s - pw / 2, s + pw / 2, z, z + h + 0.03, -pw / 2, pw / 2, c, skip=('-z',))
            Wr.box(pb, 'wood', sa, sb, z + h - 0.07, z + h, -0.05, 0.05, c, skip=())
            Wr.box(pb, 'wood', sa, sb, z + 0.05, z + 0.11, -0.03, 0.03, c, skip=('-z',))
            pitch = (0.07 if kind == 'lattice' else 0.13) * (1.0 if lod >= 2 else 1.6)
            bw = 0.024
            k = int((sb - sa) / pitch)
            for q in range(1, k):
                s = sa + q * (sb - sa) / k
                Wr.box(pb, 'wood', s - bw / 2, s + bw / 2, z + 0.11, z + h - 0.07, -0.012, 0.012, c, skip=self.sk('b'))
            return
        if kind == 'glass':
            Wr.quad(pb, 'glass', sa, z + 0.1, sb, z + h - 0.05, 0.0, lin('#7f939c'))
            Wr.quad(pb, 'glass', sa, z + 0.1, sb, z + h - 0.05, 0.0, lin('#7f939c'), k=-1)
            Wr.box(pb, 'metal', sa, sb, z + h - 0.05, z + h, -0.03, 0.03, lin('#b8bcbe'), skip=())
            return
        # steel(ステンレス): 支柱+横 3 本
        c = lin(color or '#b8bcbe')
        n = max(1, int(round((sb - sa) / 1.2)))
        for j in range(n + 1):
            s = min(max(sa + (sb - sa) * j / n, sa + 0.02), sb - 0.02)
            Wr.box(pb, 'metal', s - 0.02, s + 0.02, z, z + h, -0.02, 0.02, c, skip=('-z',))
        for zz, t in ((z + h - 0.025, 0.045), (z + h * 0.55, 0.026), (z + 0.15, 0.026)):
            Wr.box(pb, 'metal', sa, sb, zz - t / 2, zz + t / 2, -t / 2, t / 2, c, skip=())

    # -------------------------------------------------- バルコニー
    def balcony(self, B):
        pb = self.pb
        k = min(max(B.floor, 1), len(self.rings)) - 1
        z = self.zs[k] + B.z
        for i, W in self.edges(B.side, k, 1.2):
            s0 = (0.15 if B.s0 is None else (W.L + B.s0 if B.s0 < 0 else B.s0)) - B.extend
            s1 = (W.L - 0.15 if B.s1 is None else (W.L + B.s1 if B.s1 < 0 else B.s1)) + B.extend
            if s1 - s0 < 0.5:
                continue
            dep = B.depth
            t = 0.12 if B.rail in ('wood', 'lattice') else 0.18
            slc = lin(B.slab_color or ('#4a3a2e' if B.rail in ('wood', 'lattice') else PAL['spray']))
            W.box(pb, 'wood' if B.rail in ('wood', 'lattice') else 'wall', s0, s1, z - t, z, 0.0, dep, slc)
            Wf = Wall(W.P(s0, 0, dep - 0.05), W.P(s1, 0, dep - 0.05))
            segs = [(0.0, Wf.L)]
            if B.gap:
                gc = B.gap[0] * W.L - s0
                segs = subtract(segs, [(gc - B.gap[1] / 2, gc + B.gap[1] / 2)])
            for ra, rb in segs:
                self.rail(Wf, ra, rb, z, B.rail, B.rail_h, B.color)
            if B.ends:
                for s in (s0 + 0.05, s1 - 0.05):
                    We = Wall(W.P(s, 0, 0.02), W.P(s, 0, dep - 0.05))
                    self.rail(We, 0.0, We.L, z, B.rail, B.rail_h, B.color)
            if B.brackets and self.lod >= 1 and z - t - 0.8 > self.gmin:
                n = max(1, int(round((s1 - s0) / 1.8)))
                bc = lin('#3b2a20' if B.rail in ('wood', 'lattice') else PAL['spray'])
                bm = 'wood' if B.rail in ('wood', 'lattice') else 'wall'
                for j in range(n + 1):
                    s = min(max(s0 + (s1 - s0) * j / n, s0 + 0.1), s1 - 0.1)
                    W.box(pb, bm, s - 0.05, s + 0.05, z - t - 0.14, z - t, 0.0, dep - 0.05, bc)
                    if dep > 0.4:
                        W.beam(pb, bm, (s, z - t - min(0.8, dep * 0.9), 0.0), (s, z - t - 0.1, dep - 0.2), 0.08, 0.08, bc)

    # -------------------------------------------------- 庇・下屋
    def pent_spec(self, Pn):
        k = min(max(Pn.floor, 1), len(self.rings)) - 1
        zr = self.zs[k] + (Pn.z if Pn.z is not None else self.fh[k] - 0.1)
        allside = Pn.side == 'all'
        for i, W in self.edges(Pn.side, k, 1.0):
            if allside:
                s0, s1 = -Pn.depth, W.L + Pn.depth
            else:
                s0 = 0.0 if Pn.s0 is None else (W.L + Pn.s0 if Pn.s0 < 0 else Pn.s0)
                s1 = W.L if Pn.s1 is None else (W.L + Pn.s1 if Pn.s1 < 0 else Pn.s1)
            self.pent(W, s0, s1, zr, Pn.depth, Pn.slope, Pn.mat, Pn.color, Pn.brackets, ends=not allside, gutter=Pn.gutter, rafters=Pn.rafters)

    def pent(self, W, s0, s1, zr, dep, slope, mat, color=None, brackets=True, ends=True, gutter=False, post_col=None, rafters=False):
        pb, lod = self.pb, self.lod
        th = 0.1
        zo = zr - dep * slope
        col = lin(color or ROOF_COL.get(mat, PAL['kawara']))
        pts = [W.P(s0, zo, dep), W.P(s1, zo, dep), W.P(s1, zr, 0.0), W.P(s0, zr, 0.0)]
        roof_plane(pb, pts, mat, col, lod, anchor=W.P(0.0, zr, 0.0), thick=th, under_col=PAL['soffit'], seed=self.seed)
        fc = lin('#3a2e26')
        pb.poly('wood', [W.P(s0, zo, dep), W.P(s1, zo, dep), W.P(s1, zo - th, dep), W.P(s0, zo - th, dep)], fc, W.nrm())
        if mat == 'kawara' and lod >= 1:
            beam(pb, 'roof', W.P(s0, zo + 0.03, dep - 0.04), W.P(s1, zo + 0.03, dep - 0.04), 0.12, 0.07, tint(col, 0.85))
        if ends:
            pb.poly('wood', [W.P(s0, zr, 0), W.P(s0, zo, dep), W.P(s0, zo - th, dep), W.P(s0, zr - th, 0)], fc, W.tv(-1))
            pb.poly('wood', [W.P(s1, zr, 0), W.P(s1, zr - th, 0), W.P(s1, zo - th, dep), W.P(s1, zo, dep)], fc, W.tv(1))
        if lod >= 1:
            W.box(pb, 'metal', s0, s1, zr - 0.02, zr + 0.06, 0.0, 0.05, lin('#55585a'))   # 壁との水切り
        if brackets and lod >= 1 and dep > 0.45:
            bc = lin(post_col or PAL['timber'])
            n = max(1, int(round((s1 - s0) / 1.8)))
            for j in range(n + 1):
                s = min(max(s0 + (s1 - s0) * j / n, s0 + 0.25), s1 - 0.25)
                W.beam(pb, 'wood', (s, zr - th - 0.6, 0.0), (s, zo - th - 0.02 + 0.15 * slope, dep - 0.2), 0.08, 0.08, bc)
                W.box(pb, 'wood', s - 0.045, s + 0.045, zr - th - 0.18, zr - th - 0.04, 0.0, dep - 0.12, bc)
        if lod >= 2 and rafters:     # 化粧垂木
            rc = lin('#5a4636')
            for s in np.arange(s0 + 0.2, s1 - 0.1, 0.45):
                beam(pb, 'wood', W.P(s, zr - th - 0.03, 0.0), W.P(s, zo - th - 0.03, dep - 0.08), 0.05, 0.06, rc, skip=('+z',))
        if gutter and lod >= 1:
            self.gutter_run(W.P(s0, zo - th, dep + 0.07), W.P(s1, zo - th, dep + 0.07), drop_to=W)
        return zo

    def gutter_run(self, a, b, drop_to=None, drop_at=None):
        """軒樋(a→b)+端の縦樋。"""
        pb = self.pb
        gc = lin(PAL['gutter'])
        beam(pb, 'metal', (a[0], a[1], a[2] - 0.05), (b[0], b[1], b[2] - 0.05), 0.12, 0.1, gc)
        pts = drop_at or [b]
        for p in pts:
            q = np.array(p[:2], float)
            if drop_to is not None:     # 壁際へ寄せる
                s = float((q - drop_to.a) @ drop_to.t)
                q2 = drop_to.P(min(max(s, 0.15), drop_to.L - 0.15), 0, 0.08)
            else:
                q2 = (q[0], q[1], 0)
            zt = p[2] - 0.1
            zw = zt - 0.3
            beam(pb, 'metal', (q[0], q[1], zt), (q2[0], q2[1], zw), 0.07, 0.07, gc)
            zg = self.ground(q2[0], q2[1]) + 0.03
            if zw - zg > 0.2:
                beam(pb, 'metal', (q2[0], q2[1], zw), (q2[0], q2[1], zg), 0.07, 0.07, gc)

    # -------------------------------------------------- 屋根
    def roof_frame(self, ring, R, front=None):
        (cx, cy), ang, Lw, Wd = obb(ring)
        if R.axis == 'short':
            ang += math.pi / 2
        elif isinstance(R.axis, (int, float)) and not isinstance(R.axis, bool):
            bv = bearing_vec(R.axis)
            ang = math.atan2(bv[1], bv[0])
        u = np.array([math.cos(ang), math.sin(ang)])
        v = np.array([-u[1], u[0]])
        f = self.front if front is None else front
        if f is not None and float(v @ f) < 0:
            u, v = -u, -v
        P = np.array(ring, float)
        pu = P @ u
        pv = P @ v
        c = u * (pu.min() + pu.max()) / 2 + v * (pv.min() + pv.max()) / 2
        return Frame(c, u, (pu.max() - pu.min()) / 2, (pv.max() - pv.min()) / 2)

    def build_roof(self):
        R = self.spec.roof
        ring = self.rings[-1]
        zt = self.ztop
        if R.kind == 'none':
            self.roofinfo = {}
            return
        if R.kind == 'flat':
            self.roofinfo = self.roof_flat(ring, zt, R)
            return
        fr = self.roof_frame(ring, R)
        self.roof_fr = fr
        if R.kind == 'gable':
            info = self.roof_gable(fr, zt, R)
        elif R.kind in ('hip', 'hogyo'):
            info = self.roof_hip(fr, zt, R, hogyo=(R.kind == 'hogyo'))
        elif R.kind == 'irimoya':
            info = self.roof_irimoya(fr, zt, R)
        elif R.kind == 'shed':
            info = self.roof_shed(fr, zt, R)
        else:
            raise ValueError('roof kind %s' % R.kind)
        for ch in R.chidori:
            self.chidori(fr, zt, R, ch, info)
        self.roofinfo = info
        if info.get('h_fn') is not None:
            self.gable_fill(info)

    def rcol(self, R):
        return lin(R.color or ROOF_COL.get(R.mat, PAL['kawara']))

    def rthick(self, R):
        return R.thick if R.thick is not None else ROOF_THICK.get(R.mat, 0.18)

    def fascia(self, a, b, out, th, R, col=None):
        """軒先の小口(a,b は屋根の上面の点、out は外向き 2D)。茅は丸く。"""
        pb = self.pb
        if R.mat == 'kaya':
            c = tint(self.rcol(R), 0.85)
            prof = [(0.0, 0.0), (0.1 * th, -0.18 * th), (0.14 * th, -0.5 * th), (0.08 * th, -0.85 * th), (0.0, -th)]
            for j in range(len(prof) - 1):
                (o0, z0), (o1, z1) = prof[j], prof[j + 1]
                A0 = (a[0] + out[0] * o0, a[1] + out[1] * o0, a[2] + z0)
                B0 = (b[0] + out[0] * o0, b[1] + out[1] * o0, b[2] + z0)
                A1 = (a[0] + out[0] * o1, a[1] + out[1] * o1, a[2] + z1)
                B1 = (b[0] + out[0] * o1, b[1] + out[1] * o1, b[2] + z1)
                pb.poly('thatch', [A0, B0, B1, A1], hj(c, 0.05, j), (out[0], out[1], 0.3 - j * 0.3))
            return
        c = lin(col or R.hafu_col)
        pb.poly('wood', [a, b, (b[0], b[1], b[2] - th), (a[0], a[1], a[2] - th)], c, (out[0], out[1], 0))
        if R.mat == 'kawara' and self.lod >= 1:     # 軒瓦の列
            beam(pb, 'roof', (a[0] - out[0] * 0.05, a[1] - out[1] * 0.05, a[2] + 0.03), (b[0] - out[0] * 0.05, b[1] - out[1] * 0.05, b[2] + 0.03),
                 0.12, 0.07, tint(self.rcol(R), 0.82))

    def hafu(self, a, b, out, R, h0=0.26, h1=0.4, th=0.07, col=None):
        """破風板(a=軒側の上面の点、b=頂部)。頂部ほど幅広(拝みの簡略形)。"""
        pb = self.pb
        if R.mat == 'kaya':
            return
        c = lin(col or R.hafu_col)
        a = np.array(a, float) + np.array([out[0], out[1], 0]) * 0.03
        b = np.array(b, float) + np.array([out[0], out[1], 0]) * 0.03
        o = np.array([out[0], out[1], 0.0]) * th / 2
        segs = 3 if self.lod >= 1 else 1
        for j in range(segs):
            t0, t1 = j / segs, (j + 1) / segs
            Ta = a + (b - a) * t0 + np.array([0, 0, 0.06])
            Tb = a + (b - a) * t1 + np.array([0, 0, 0.06])
            ha = h0 + (h1 - h0) * t0 ** 2
            hb = h0 + (h1 - h0) * t1 ** 2
            Ba = Ta - np.array([0, 0, ha])
            Bb = Tb - np.array([0, 0, hb])
            pb.poly('wood', [tuple(Ta + o), tuple(Tb + o), tuple(Bb + o), tuple(Ba + o)], c, (out[0], out[1], 0))
            pb.poly('wood', [tuple(Ta - o), tuple(Ba - o), tuple(Bb - o), tuple(Tb - o)], tint(c, 0.9), (-out[0], -out[1], 0))
            pb.poly('wood', [tuple(Ta + o), tuple(Ta - o), tuple(Tb - o), tuple(Tb + o)], c, (0, 0, 1))
            pb.poly('wood', [tuple(Ba + o), tuple(Bb + o), tuple(Bb - o), tuple(Ba - o)], tint(c, 0.8), (0, 0, -1))

    def kengyo(self, apex, out, right, sc=1.0, col=None):
        """懸魚(頂部の下に下がる飾り板)。"""
        if self.lod < 1:
            return
        pb = self.pb
        c = lin(col or self.spec.roof.hafu_col)
        shape = [(0, 0), (0.22, -0.05), (0.32, -0.3), (0.22, -0.52), (0.09, -0.6), (0, -0.74), (-0.09, -0.6), (-0.22, -0.52), (-0.32, -0.3), (-0.22, -0.05)]
        ax, ay, az = apex
        F = [(ax + right[0] * x * sc + out[0] * 0.06, ay + right[1] * x * sc + out[1] * 0.06, az + z * sc) for x, z in shape]
        B = [(p[0] - out[0] * 0.05, p[1] - out[1] * 0.05, p[2]) for p in F]
        pb.poly('wood', F, c, (out[0], out[1], 0))
        pb.poly('wood', B, tint(c, 0.85), (-out[0], -out[1], 0))
        if self.lod >= 2:   # 六葉(中央の飾り)
            cx, cy, cz = ax + out[0] * 0.08, ay + out[1] * 0.08, az - 0.3 * sc
            ring_ = [(cx + right[0] * 0.07 * sc * math.cos(t), cy + right[1] * 0.07 * sc * math.cos(t), cz + 0.07 * sc * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
            pb.poly('metal', ring_, lin('#b49a52'), (out[0], out[1], 0))

    def oni(self, p, out, right, R, sc=1.0):
        """鬼瓦(棟の端)。"""
        if self.lod < 1 or R.mat not in ('kawara',) or not R.oni:
            return
        pb = self.pb
        c = tint(self.rcol(R), 0.78)
        shape = [(-0.24, 0), (0.24, 0), (0.27, 0.28), (0.13, 0.42), (0, 0.5), (-0.13, 0.42), (-0.27, 0.28)]
        px, py, pz = p
        F = [(px + right[0] * x * sc + out[0] * 0.08, py + right[1] * x * sc + out[1] * 0.08, pz + z * sc) for x, z in shape]
        B = [(q[0] - out[0] * 0.16, q[1] - out[1] * 0.16, q[2]) for q in F]
        pb.poly('roof', F, c, (out[0], out[1], 0))
        pb.poly('roof', B, c, (-out[0], -out[1], 0))
        n = len(F)
        for j in range(n):
            k = (j + 1) % n
            mx = (F[j][0] + F[k][0]) / 2 - px
            my = (F[j][1] + F[k][1]) / 2 - py
            mz = (F[j][2] + F[k][2]) / 2 - (pz + 0.22 * sc)
            pb.poly('roof', [F[j], F[k], B[k], B[j]], tint(c, 0.9), (mx - out[0] * ((mx * out[0] + my * out[1])), my - out[1] * ((mx * out[0] + my * out[1])), mz))

    def ridge(self, a, b, R):
        """棟(瓦は熨斗の段+冠瓦)。a,b は屋根の頂の点。"""
        if not R.ridge:
            return
        pb = self.pb
        c = tint(self.rcol(R), 0.85)
        a = np.array(a, float)
        b = np.array(b, float)
        if R.mat == 'kawara':
            layers = [(0.34, 0.1), (0.29, 0.09), (0.24, 0.09)] if self.lod >= 2 else [(0.32, 0.18), (0.24, 0.09)]
            z = -0.02
            for j, (w, h) in enumerate(layers):
                beam(pb, 'roof', a + [0, 0, z + h / 2], b + [0, 0, z + h / 2], w, h, tint(c, 1.0 - 0.04 * j))
                z += h
            if self.lod >= 1:
                d = b - a
                L = float(np.linalg.norm(d))
                t = d / max(L, 1e-9)
                sd = np.cross(t, [0, 0, 1.0])
                sd = sd / max(float(np.linalg.norm(sd)), 1e-9)
                top = z + 0.09
                A0, B0 = a + [0, 0, z], b + [0, 0, z]
                pb.poly('roof', [tuple(A0 + sd * 0.1), tuple(B0 + sd * 0.1), tuple(B0 + [0, 0, top - z]), tuple(A0 + [0, 0, top - z])], c, tuple(sd + [0, 0, 1]))
                pb.poly('roof', [tuple(A0 - sd * 0.1), tuple(A0 + [0, 0, top - z]), tuple(B0 + [0, 0, top - z]), tuple(B0 - sd * 0.1)], c, tuple(-sd + [0, 0, 1]))
        elif R.mat == 'kaya':
            beam(pb, 'thatch', a + [0, 0, 0.1], b + [0, 0, 0.1], 0.7, 0.35, tint(c, 0.8))
            beam(pb, 'wood', a + [0, 0, 0.32], b + [0, 0, 0.32], 0.36, 0.12, lin('#4a4038'))
            if self.lod >= 1:
                d = b - a
                L = float(np.linalg.norm(d))
                n = max(2, int(L / 0.9))
                for j in range(n + 1):
                    p = a + d * (j / n)
                    sd = np.cross(d / L, [0, 0, 1.0])
                    beam(pb, 'wood', p - sd * 0.42 + [0, 0, 0.12], p + sd * 0.42 + [0, 0, 0.12], 0.08, 0.08, lin('#3e352e'), up=tuple(d / L))
        else:
            w, h = (0.3, 0.07) if R.mat in ('metal', 'teppan') else (0.3, 0.12)
            beam(pb, ROOF_MAT.get(R.mat, 'roof'), a + [0, 0, 0.02], b + [0, 0, 0.02], w, h, c)

    def hip_ridge(self, a, b, R):
        pb = self.pb
        c = tint(self.rcol(R), 0.85)
        if R.mat == 'kaya':
            return
        w, h = (0.24, 0.13) if R.mat == 'kawara' else (0.16, 0.06)
        beam(pb, ROOF_MAT.get(R.mat, 'roof'), (a[0], a[1], a[2] + 0.04), (b[0], b[1], b[2] + 0.04), w, h, c)

    def rafters(self, fr, R, xs, y_wall, y_eave, z_wall, z_eave, along='x'):
        """軒裏の化粧垂木(壁 y_wall → 軒 y_eave、x は位置の列)。along='y' なら x,y を入れ替え(妻側)。"""
        if not (R.rafters or (R.rafters is None and self.lod >= 2)):
            return
        rc = lin(R.rafter_col or '#5a4636')
        th = self.rthick(R)
        for x in xs:
            if along == 'x':
                a, b = fr.P(x, y_wall, z_wall - th - 0.04), fr.P(x, y_eave * 0.98 + y_wall * 0.02, z_eave - th - 0.04)
            else:
                a, b = fr.P(y_wall, x, z_wall - th - 0.04), fr.P(y_eave * 0.98 + y_wall * 0.02, x, z_eave - th - 0.04)
            beam(self.pb, 'wood', a, b, 0.06, 0.08, rc, skip=('+z',))

    def gutters_for(self, fr, R, X, Y, ze, sides=(1, -1), hx=None, hy=None):
        if not R.gutters or self.lod < 1 or R.mat == 'kaya':
            return
        th = self.rthick(R)
        hx = fr.hx if hx is None else hx
        hy = fr.hy if hy is None else hy
        for sg in sides:
            a = fr.P(-X + 0.1, sg * (Y + 0.07), ze - th)
            b = fr.P(X - 0.1, sg * (Y + 0.07), ze - th)
            pb = self.pb
            gc = lin(PAL['gutter'])
            beam(pb, 'metal', (a[0], a[1], a[2] - 0.05), (b[0], b[1], b[2] - 0.05), 0.12, 0.1, gc)
            for sx in (-1, 1):
                top = fr.P(sx * (hx - 0.25), sg * (Y + 0.07), ze - th - 0.1)
                wl = fr.P(sx * (hx - 0.25), sg * (hy + 0.08), ze - th - 0.45)
                beam(pb, 'metal', top, wl, 0.07, 0.07, gc)
                zg = self.ground(wl[0], wl[1]) + 0.03
                if wl[2] - zg > 0.3:
                    beam(pb, 'metal', wl, (wl[0], wl[1], zg), 0.07, 0.07, gc)

    def roof_gable(self, fr, zt, R):
        pb = self.pb
        s, e, g = R.slope, R.eave, R.verge
        th = self.rthick(R)
        hx, hy = fr.hx, fr.hy
        X, Y = hx + g, hy + e
        ze, zr = zt - e * s, zt + hy * s
        col = self.rcol(R)
        anchor = fr.P(0, 0, zr)
        for sg in (1, -1):
            pts = [fr.P(-X, sg * Y, ze), fr.P(X, sg * Y, ze), fr.P(X, 0, zr), fr.P(-X, 0, zr)]
            roof_plane(pb, pts, R.mat, col, self.lod, anchor=anchor, thick=th, under_col=R.soffit_col, seed=self.seed + sg)
            self.fascia(pts[0], pts[1], fr.d2(0, sg), th, R)
            self.rafters(fr, R, np.arange(-hx, hx + 0.01, 0.45), sg * hy, sg * Y, zt, ze)
        for sx in (1, -1):
            for sg in (1, -1):
                self.hafu(fr.P(sx * X, sg * Y, ze), fr.P(sx * X, 0, zr), fr.d2(sx, 0), R)
                if R.mat == 'kawara' and self.lod >= 1:      # 降り棟(けらば寄り)
                    self.hip_ridge(fr.P(sx * (X - 0.3), 0, zr), fr.P(sx * (X - 0.3), sg * (Y - 0.2), ze + 0.2 * s), R)
            if R.kengyo:
                self.kengyo(fr.P(sx * (X + 0.04), 0, zr - 0.08), fr.d2(sx, 0), fr.d2(0, 1), sc=min(1.3, 0.35 + hy * 0.12))
            self.oni(fr.P(sx * (X - 0.05), 0, zr), fr.d2(sx, 0), fr.d2(0, 1), R, sc=min(1.2, 0.6 + hy * 0.06))
        self.ridge(fr.P(-X, 0, zr), fr.P(X, 0, zr), R)
        self.gutters_for(fr, R, X, Y, ze)
        hyw = hy

        def h_fn(x, y, fr=fr, zt=zt, s=s, hyw=hyw):
            lx, ly = fr.loc(x, y)
            return zt + (hyw - abs(ly)) * s - 0.03
        return dict(kind='gable', zr=zr, ze=ze, h_fn=h_fn, fr=fr, ridge_y=0.0)

    def roof_hip(self, fr, zt, R, hogyo=False):
        pb = self.pb
        s, e = R.slope, R.eave
        th = self.rthick(R)
        hx, hy = fr.hx, fr.hy
        X, Y = hx + e, hy + e
        ze, zr = zt - e * s, zt + hy * s
        rl = 0.0 if hogyo else max(0.0, hx - hy)
        col = self.rcol(R)
        anchor = fr.P(0, 0, zr)
        for sg in (1, -1):
            if rl > 0.02:
                pts = [fr.P(-X, sg * Y, ze), fr.P(X, sg * Y, ze), fr.P(rl, 0, zr), fr.P(-rl, 0, zr)]
            else:
                pts = [fr.P(-X, sg * Y, ze), fr.P(X, sg * Y, ze), fr.P(0, 0, zr)]
            roof_plane(pb, pts, R.mat, col, self.lod, anchor=anchor, thick=th, under_col=R.soffit_col, seed=self.seed + sg)
            self.fascia(pts[0], pts[1], fr.d2(0, sg), th, R)
            self.rafters(fr, R, np.arange(-hx, hx + 0.01, 0.45), sg * hy, sg * Y, zt, ze)
        for sx in (1, -1):
            pts = [fr.P(sx * X, -Y, ze), fr.P(sx * X, Y, ze), fr.P(sx * rl, 0, zr)]
            roof_plane(pb, pts, R.mat, col, self.lod, anchor=anchor, thick=th, under_col=R.soffit_col, seed=self.seed + 3 * sx)
            self.fascia(pts[0], pts[1], fr.d2(sx, 0), th, R)
            self.rafters(fr, R, np.arange(-hy, hy + 0.01, 0.45), sx * hx, sx * X, zt, ze, along='y')
            for sg in (1, -1):
                self.hip_ridge(fr.P(sx * X, sg * Y, ze), fr.P(sx * rl, 0, zr), R)
        if rl > 0.02:
            self.ridge(fr.P(-rl, 0, zr), fr.P(rl, 0, zr), R)
            for sx in (1, -1):
                self.oni(fr.P(sx * rl, 0, zr), fr.d2(sx, 0), fr.d2(0, 1), R, sc=0.7)
        if hogyo and R.finial and self.lod >= 1:
            c0 = fr.P(0, 0, zr)
            mc = lin('#6d6a62')
            prism(pb, 'metal', c0, 0.22, 0.18, zr - 0.05, zr + 0.25, 8, mc)
            prism(pb, 'metal', c0, 0.12, 0.2, zr + 0.25, zr + 0.45, 8, mc)
            prism(pb, 'metal', c0, 0.2, 0.0, zr + 0.45, zr + 0.75, 8, mc)
        self.gutters_for(fr, R, X, Y, ze)
        if R.mat == 'kaya':
            self.ridge(fr.P(-max(rl, 0.3), 0, zr), fr.P(max(rl, 0.3), 0, zr), R)
        return dict(kind='hip', zr=zr, ze=ze, h_fn=None, fr=fr)

    def roof_irimoya(self, fr, zt, R):
        pb = self.pb
        s, e = R.slope, R.eave
        th = self.rthick(R)
        hx, hy = fr.hx, fr.hy
        X, Y = hx + e, hy + e
        ze, zr = zt - e * s, zt + hy * s
        zk = ze + R.irimoya_k * (zr - ze)
        xg = X - (zk - ze) / s
        yk = Y - (zk - ze) / s
        og = min(R.verge, 0.6)
        if xg < 0.6:
            return self.roof_hip(fr, zt, R)
        col = self.rcol(R)
        anchor = fr.P(0, 0, zr)
        for sg in (1, -1):
            lower = [fr.P(-X, sg * Y, ze), fr.P(X, sg * Y, ze), fr.P(xg, sg * yk, zk), fr.P(-xg, sg * yk, zk)]
            upper = [fr.P(-(xg + og), sg * yk, zk), fr.P(xg + og, sg * yk, zk), fr.P(xg + og, 0, zr), fr.P(-(xg + og), 0, zr)]
            roof_plane(pb, lower, R.mat, col, self.lod, anchor=anchor, thick=th, under_col=R.soffit_col, seed=self.seed + sg)
            roof_plane(pb, upper, R.mat, col, self.lod, anchor=anchor, thick=th * 0.6, under_col=R.soffit_col, seed=self.seed + sg)
            self.fascia(lower[0], lower[1], fr.d2(0, sg), th, R)
            for sx in (1, -1):
                self.fascia(fr.P(sx * xg, sg * yk, zk), fr.P(sx * (xg + og), sg * yk, zk), fr.d2(0, sg), th * 0.6, R)
            self.rafters(fr, R, np.arange(-hx, hx + 0.01, 0.45), sg * hy, sg * Y, zt, ze)
        gcol = lin(R.gable_col or self.finish_for(len(self.fh), 0).color)
        for sx in (1, -1):
            end = [fr.P(sx * X, -Y, ze), fr.P(sx * X, Y, ze), fr.P(sx * xg, yk, zk), fr.P(sx * xg, -yk, zk)]
            roof_plane(pb, end, R.mat, col, self.lod, anchor=anchor, thick=th, under_col=R.soffit_col, seed=self.seed + 5 * sx)
            self.fascia(end[0], end[1], fr.d2(sx, 0), th, R)
            self.rafters(fr, R, np.arange(-hy, hy + 0.01, 0.45), sx * hx, sx * X, zt, ze, along='y')
            # 妻壁
            tri = [fr.P(sx * xg, -yk, zk), fr.P(sx * xg, yk, zk), fr.P(sx * xg, 0, zr - 0.05)]
            pb.poly('wall', tri, gcol, fr.d3(sx, 0))
            if self.lod >= 1 and R.gable_style in ('timber', 'lattice'):
                tc = lin(R.hafu_col)
                pitch = 0.6 if R.gable_style == 'timber' else 0.3
                Wg = wall_facing(fr.P(sx * xg, -yk, 0)[:2], fr.P(sx * xg, yk, 0)[:2], fr.d2(sx, 0))
                for q in np.arange(-yk + pitch, yk - 0.05, pitch):
                    zz = zk + (yk - abs(q)) * s - 0.08
                    sq = float((np.array(fr.P(sx * xg, q, 0)[:2]) - Wg.a) @ Wg.t)
                    if zz - zk > 0.15:
                        Wg.box(pb, 'wood', sq - 0.035, sq + 0.035, zk, zz, 0.0, 0.03, tc)
                if R.gable_style == 'lattice':
                    for zz in np.arange(zk + pitch, zr - 0.2, pitch):
                        half = yk - (zz - zk) / s
                        if half < 0.2:
                            continue
                        sa = float((np.array(fr.P(sx * xg, -half, 0)[:2]) - Wg.a) @ Wg.t)
                        sb = float((np.array(fr.P(sx * xg, half, 0)[:2]) - Wg.a) @ Wg.t)
                        Wg.box(pb, 'wood', min(sa, sb), max(sa, sb), zz - 0.03, zz + 0.03, 0.0, 0.03, tc)
                Wg.box(pb, 'wood', 0.0, Wg.L, zk, zk + 0.14, 0.0, 0.05, tc)
            for sg in (1, -1):
                self.hafu(fr.P(sx * (xg + og), sg * yk, zk), fr.P(sx * (xg + og), 0, zr), fr.d2(sx, 0), R)
                self.hip_ridge(fr.P(sx * X, sg * Y, ze), fr.P(sx * xg, sg * yk, zk), R)
                if R.mat == 'kawara' and self.lod >= 1:
                    self.hip_ridge(fr.P(sx * (xg + og - 0.25), 0, zr), fr.P(sx * (xg + og - 0.25), sg * (yk - 0.1), zk + 0.1 * s), R)
            if R.kengyo:
                self.kengyo(fr.P(sx * (xg + og + 0.04), 0, zr - 0.08), fr.d2(sx, 0), fr.d2(0, 1), sc=min(1.4, 0.4 + yk * 0.12))
            self.oni(fr.P(sx * (xg + og - 0.05), 0, zr), fr.d2(sx, 0), fr.d2(0, 1), R, sc=min(1.3, 0.6 + hy * 0.06))
        self.ridge(fr.P(-(xg + og), 0, zr), fr.P(xg + og, 0, zr), R)
        self.gutters_for(fr, R, X, Y, ze)
        return dict(kind='irimoya', zr=zr, ze=ze, h_fn=None, fr=fr)

    def roof_shed(self, fr, zt, R):
        pb = self.pb
        s, e, g = R.slope, R.eave, R.verge
        th = self.rthick(R)
        hx, hy = fr.hx, fr.hy
        X = hx + g
        Yf, Yb = hy + e, hy + g
        zlo = zt - e * s
        zhi = zt + (2 * hy + g) * s
        col = self.rcol(R)
        pts = [fr.P(-X, Yf, zlo), fr.P(X, Yf, zlo), fr.P(X, -Yb, zhi), fr.P(-X, -Yb, zhi)]
        roof_plane(pb, pts, R.mat, col, self.lod, anchor=fr.P(0, 0, zt), thick=th, under_col=R.soffit_col, seed=self.seed)
        self.fascia(pts[0], pts[1], fr.d2(0, 1), th, R)
        self.fascia(pts[3], pts[2], fr.d2(0, -1), th, R)
        for sx in (1, -1):
            self.hafu(fr.P(sx * X, Yf, zlo), fr.P(sx * X, -Yb, zhi), fr.d2(sx, 0), R, h0=0.22, h1=0.22)
        self.gutters_for(fr, R, X, Yf, zlo, sides=(1,))
        hyw = hy

        def h_fn(x, y, fr=fr, zt=zt, s=s, hyw=hyw):
            lx, ly = fr.loc(x, y)
            return zt + (hyw - ly) * s - 0.03
        return dict(kind='shed', zr=zhi, ze=zlo, h_fn=h_fn, fr=fr, ridge_y=None)

    def roof_flat(self, ring, zt, R):
        pb, lod = self.pb, self.lod
        p = R.parapet
        fin = self.finish_for(len(self.fh), 0)
        wc = lin(fin.color)
        inner = offset_ring(ring, 0.2)
        for i in range(len(ring)):
            W = Wall(ring[i], ring[(i + 1) % len(ring)])
            if W.L < 0.05:
                continue
            W.quad(pb, 'wall', 0.0, zt, W.L, zt + p, 0.0, wc)
            Wi = Wall(inner[i], inner[(i + 1) % len(inner)])
            if Wi.L > 0.05:
                Wi.quad(pb, 'wall', 0.0, zt + 0.05, Wi.L, zt + p, 0.0, tint(wc, 0.9), k=-1)
            a, b, ia, ib = ring[i], ring[(i + 1) % len(ring)], inner[i], inner[(i + 1) % len(inner)]
            cc = lin(R.coping_col)
            pb.poly('metal', [(a[0], a[1], zt + p + 0.03), (b[0], b[1], zt + p + 0.03), (ib[0], ib[1], zt + p + 0.03), (ia[0], ia[1], zt + p + 0.03)], cc, (0, 0, 1))
            if lod >= 1:
                W.quad(pb, 'metal', -0.03, zt + p - 0.05, W.L + 0.03, zt + p + 0.03, 0.03, tint(cc, 0.9))
        for t in tess(inner):
            pb.poly('wall', [(inner[j][0], inner[j][1], zt + 0.05) for j in t], lin(PAL['roof_flat']), (0, 0, 1))
        fr = self.roof_frame(ring, Roof(axis='long'))
        for (dx, dy, w, dd, h) in R.penthouse:
            c = fr.c + fr.u * dx + fr.v * dy
            F2 = Frame(c, fr.u, w / 2, dd / 2)
            corners = [F2.P(-w / 2, -dd / 2, 0)[:2], F2.P(w / 2, -dd / 2, 0)[:2], F2.P(w / 2, dd / 2, 0)[:2], F2.P(-w / 2, dd / 2, 0)[:2]]
            corners = C.ccw(corners)
            z0 = zt + 0.05
            for i in range(4):
                W = Wall(corners[i], corners[(i + 1) % 4])
                W.quad(pb, 'wall', 0.0, z0, W.L, z0 + h, 0.0, tint(wc, 0.97))
                if i == 0 and lod >= 1:
                    W.box(pb, 'metal', W.L / 2 - 0.45, W.L / 2 + 0.45, z0, z0 + 2.0, 0.0, 0.02, lin('#7c8082'))
            for t in tess(corners):
                pb.poly('wall', [(corners[j][0], corners[j][1], z0 + h) for j in t], lin(PAL['roof_flat']), (0, 0, 1))
            for i in range(4):
                W = Wall(corners[i], corners[(i + 1) % 4])
                W.box(pb, 'wall', -0.05, W.L + 0.05, z0 + h, z0 + h + 0.3, 0.0, 0.05, tint(wc, 0.95), skip=('-y',))
        return dict(kind='flat', zr=zt + p, ze=zt, h_fn=None, fr=fr)

    def gable_fill(self, info):
        """切妻・片流れの最上階の壁を屋根の下まで伸ばす(妻壁)。"""
        pb = self.pb
        hf = info['h_fn']
        fr = info['fr']
        k = len(self.fh) - 1
        ring = self.rings[k]
        zt = self.ztop
        R = self.spec.roof
        for i in range(len(ring)):
            W = Wall(ring[i], ring[(i + 1) % len(ring)])
            if W.L < 0.05:
                continue
            ss = [0.0, W.L]
            if info.get('ridge_y') is not None:
                ya = fr.loc(*W.P(0, 0)[:2])[1]
                yb = fr.loc(*W.P(W.L, 0)[:2])[1]
                if (ya - info['ridge_y']) * (yb - info['ridge_y']) < 0:
                    ss.insert(1, W.L * (info['ridge_y'] - ya) / (yb - ya))
            tops = [hf(*W.P(s, 0)[:2]) for s in ss]
            if max(tops) - zt < 0.06:
                continue
            fin = self.finish_for(k + 1, i)
            c = lin(fin.color)
            m = fin.mat or ('wood' if fin.kind in ('board_h', 'board_v', 'louver') else 'wall')

            def top_at(s):
                return float(np.interp(s, ss, tops))
            win = None
            if R.gable_window and max(tops) - zt > 1.4 and len(ss) == 3:
                sc = ss[1]
                hh = min(0.8, (max(tops) - zt) * 0.35)
                ww = min(1.0, W.L * 0.15)
                zb0 = zt + (max(tops) - zt) * 0.3
                win = Op('w', sc - ww / 2, sc + ww / 2, zb0, zb0 + hh)
            cutsx = [0.0, W.L] if win is None else [0.0, win.s0, win.s1, W.L]
            for j in range(len(cutsx) - 1):
                sa, sb = cutsx[j], cutsx[j + 1]
                inner = [s for s in ss if sa + 1e-6 < s < sb - 1e-6]
                if win is not None and j == 1:
                    W.quad(pb, m, sa, zt, sb, win.zb, 0.0, c)
                    pts = [W.P(sa, win.zt), W.P(sb, win.zt), W.P(sb, top_at(sb))] + [W.P(s, top_at(s)) for s in reversed(inner)] + [W.P(sa, top_at(sa))]
                    pb.poly(m, pts, c, W.nrm())
                else:
                    pts = [W.P(sa, zt), W.P(sb, zt), W.P(sb, top_at(sb))] + [W.P(s, top_at(s)) for s in reversed(inner)] + [W.P(sa, top_at(sa))]
                    pts = [p for p in pts]
                    pb.poly(m, pts, c, W.nrm())
            if win is not None:
                fac = Facade(frame='wood' if fin.timber else 'alu', glass='#3d4850', rev=0.12)
                self.opening(W, win, fac, fin)
            if fin.timber is not None and self.lod >= 1 and len(ss) == 3:
                tim = fin.timber
                tc = lin(tim.color)
                hmax = max(tops)
                sc = ss[1]
                if win is None:
                    W.box(pb, tim.mat, sc - tim.w / 2, sc + tim.w / 2, zt, hmax - 0.15, 0.0, tim.proud, tc)
                ztie = zt + 0.38 * (hmax - zt)
                xs = np.linspace(0.0, W.L, 41)
                inside = [s for s in xs if top_at(s) > ztie + tim.w]
                if inside:
                    for sa, sb in subtract([(min(inside), max(inside))], [] if win is None else [(win.s0, win.s1)] if win.zb < ztie < win.zt else []):
                        W.box(pb, tim.mat, sa, sb, ztie - tim.w / 2, ztie + tim.w / 2, 0.0, tim.proud, tc)
                W.box(pb, tim.mat, 0.0, W.L, zt - tim.w / 2, zt + tim.w / 2, 0.0, tim.proud * 1.2, tc)

    def chidori(self, fr, zt, R, ch, info):
        """千鳥破風(屋根面の三角の出窓屋根)。ch=(位置 -1..1, 幅, +1/-1)。"""
        pb = self.pb
        pos, w, sg = ch
        s, e = R.slope, R.eave
        Y = fr.hy + e
        ze = zt - e * s
        zr = info['zr']
        x0 = pos * fr.hx * 0.7
        s2 = max(s * 1.15, 0.6)
        y_f = fr.hy * 0.85
        zb = ze + (Y - y_f) * s
        za = zb + (w / 2) * s2
        if za > zr - 0.25:
            za = zr - 0.25
            w = 2 * (za - zb) / s2
        if w < 1.0:
            return
        y_r = Y - (za - ze) / s
        ov, ovs = 0.35, 0.22
        yA = y_f + ov
        yA2 = y_f + ovs * s2 / s
        col = self.rcol(R)
        th = self.rthick(R) * 0.7
        for sx in (-1, 1):
            xl = x0 + sx * (w / 2 + ovs)
            A = fr.P(xl, sg * yA, zb - ovs * s2)
            B = fr.P(x0, sg * yA, za)
            Cr = fr.P(x0, sg * y_r, za)
            A2 = fr.P(xl, sg * yA2, zb - ovs * s2)
            roof_plane(pb, [A2, A, B, Cr], R.mat, col, self.lod, anchor=fr.P(x0, sg * y_r, za), thick=th, under_col=R.soffit_col, seed=self.seed + 11)
            self.fascia(A2, A, fr.d2(sx, 0), th, R)
            self.hafu(A, B, fr.d2(0, sg), R, h0=0.2, h1=0.3)
        gcol = lin(R.gable_col or self.finish_for(len(self.fh), 0).color)
        tri = [fr.P(x0 - w / 2, sg * y_f, zb), fr.P(x0 + w / 2, sg * y_f, zb), fr.P(x0, sg * y_f, za)]
        pb.poly('wall', tri, gcol, fr.d3(0, sg))
        if self.lod >= 1:
            Wg = wall_facing(fr.P(x0 - w / 2, sg * y_f, 0)[:2], fr.P(x0 + w / 2, sg * y_f, 0)[:2], fr.d2(0, sg))
            sc = Wg.L / 2
            hh = (za - zb) * 0.4
            ww = min(0.9, w * 0.3)
            z0 = zb + (za - zb) * 0.12
            Wg.quad(pb, 'glass', sc - ww / 2, z0, sc + ww / 2, z0 + hh, 0.01, lin('#3d4850'))
            fc = lin(R.hafu_col)
            for (a_, b_, c_, d_) in ((sc - ww / 2 - 0.05, sc - ww / 2, z0, z0 + hh), (sc + ww / 2, sc + ww / 2 + 0.05, z0, z0 + hh),
                                     (sc - ww / 2 - 0.05, sc + ww / 2 + 0.05, z0 - 0.05, z0), (sc - ww / 2 - 0.05, sc + ww / 2 + 0.05, z0 + hh, z0 + hh + 0.05)):
                Wg.box(pb, 'wood', a_, b_, c_, d_, 0.0, 0.04, fc)
            for q in np.linspace(sc - ww / 2, sc + ww / 2, 4)[1:-1]:
                Wg.box(pb, 'wood', q - 0.012, q + 0.012, z0, z0 + hh, 0.0, 0.03, fc, skip=('-y', '-z', '+z'))
        if R.kengyo:
            self.kengyo(fr.P(x0, sg * (yA + 0.04), za - 0.06), fr.d2(0, sg), fr.d2(1, 0), sc=0.5)
        self.ridge(fr.P(x0, sg * (yA - 0.02), za), fr.P(x0, sg * y_r, za), dreplace(R, mat=R.mat))
        self.oni(fr.P(x0, sg * yA, za), fr.d2(0, sg), fr.d2(1, 0), R, sc=0.55)

    # -------------------------------------------------- 付属物
    def attach_wall(self, A):
        k = min(max(A.floor, 1), len(self.rings)) - 1
        i, W = self.main_edge(A.side, k)
        if A.at is not None:
            s = A.at * W.L
        elif A.s is None:
            s = W.L / 2
        else:
            s = W.L + A.s if A.s < 0 else A.s
        return W, s, k

    def attach(self, A):
        kind = A.kind
        fn = getattr(self, 'att_' + kind, None)
        if fn is None:
            raise ValueError('unknown attach kind %s' % kind)
        fn(A)

    def att_ac(self, A):
        """エアコン室外機(n 台を w 間隔で)。z=None なら地面(またはバルコニーの床)。"""
        pb, lod = self.pb, self.lod
        W, s, k = self.attach_wall(A)
        step = A.w or 1.0
        for j in range(max(1, A.n)):
            sj = s + (j - (A.n - 1) / 2) * step
            if sj < 0.45 or sj > W.L - 0.45:
                continue
            if A.z is None:
                z = self.ground(*W.P(sj, 0, 0.3)[:2]) + 0.08
                wall_mount = False
            else:
                z = self.zs[k] + A.z
                wall_mount = (z - self.ground(*W.P(sj, 0, 0.3)[:2])) > 1.0 and A.prm.get('mount', 'wall') == 'wall'
            d0 = A.d or 0.08
            c = lin(A.color or PAL['ac'])
            W.box(pb, 'metal', sj - 0.4, sj + 0.4, z, z + 0.6, d0, d0 + 0.28, c, skip=('-z',) if not wall_mount else ())
            if lod >= 2:
                cx = sj - 0.1
                ring_ = [W.P(cx + 0.2 * math.cos(t), z + 0.3 + 0.2 * math.sin(t), d0 + 0.285) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
                pb.poly('dark', ring_, lin('#2e3032'), W.nrm())
                beam(pb, 'metal', W.P(sj + 0.3, z + 0.15, d0), W.P(sj + 0.3, z + 0.15, 0.0), 0.04, 0.04, lin('#d8d6cf'))
            elif lod == 1:
                W.quad(pb, 'dark', sj - 0.3, z + 0.12, sj + 0.1, z + 0.5, d0 + 0.285, lin('#2e3032'))
            if wall_mount and lod >= 1:
                for q in (sj - 0.3, sj + 0.3):
                    W.box(pb, 'metal', q - 0.02, q + 0.02, z - 0.04, z, 0.0, d0 + 0.3, lin('#6d6a64'))

    def att_pipe(self, A):
        """配管(縦。prm['run']=横に伸ばす m)。z=下端(None=地面)、h=長さ(None=最上階の上端まで)。"""
        W, s, k = self.attach_wall(A)
        dia = A.w or 0.08
        c = lin(A.color or '#8d8a84')
        z0 = self.ground(*W.P(s, 0, 0.1)[:2]) if A.z is None else self.zs[k] + A.z
        z1 = (self.ztop - 0.2) if A.h is None else z0 + A.h
        d = (A.d or 0.08)
        beam(self.pb, 'metal', W.P(s, z0, d), W.P(s, z1, d), dia, dia, c)
        run = A.prm.get('run')
        if run:
            beam(self.pb, 'metal', W.P(s, z1, d), W.P(s + run, z1, d), dia, dia, c)
            beam(self.pb, 'metal', W.P(s + run, z1, d), W.P(s + run, z1 - 0.4, d), dia, dia, c)

    def att_sign(self, A):
        """看板の取り付け枠(文字は後のフェーズ)。style: yoko(壁の横長)|tate(突き出しの縦)|flat(壁に縦長)|roof(屋上)|hang(軒下の吊り)。"""
        pb, lod = self.pb, self.lod
        W, s, k = self.attach_wall(A)
        st = A.style or 'yoko'
        w = A.w or 2.0
        h = A.h or 0.6
        zc = self.zs[k] + (A.z if A.z is not None else self.fh[k] * 0.8)
        bc = lin(A.color or '#2c2420')
        fc = lin(A.color2 or '#3a2e26')
        rec = dict(spec=self.spec.id, kind=st, text=A.text, w=w, h=h)
        if st in ('yoko', 'flat', 'hang'):
            d0 = (A.d or 0.0)
            if st == 'hang':
                for q in (s - w / 2 + 0.1, s + w / 2 - 0.1):
                    beam(pb, 'metal', W.P(q, zc + h / 2, d0 + 0.05), W.P(q, zc + h / 2 + 0.35, d0 + 0.05), 0.02, 0.02, lin('#333333'))
            W.box(pb, 'wood', s - w / 2, s + w / 2, zc - h / 2, zc + h / 2, d0 + 0.02, d0 + 0.07, bc, skip=('-y',) if st != 'hang' else ())
            if lod >= 1:
                fw = 0.05
                for (a_, b_, c_, d_) in ((s - w / 2 - fw, s - w / 2, zc - h / 2 - fw, zc + h / 2 + fw), (s + w / 2, s + w / 2 + fw, zc - h / 2 - fw, zc + h / 2 + fw),
                                         (s - w / 2, s + w / 2, zc - h / 2 - fw, zc - h / 2), (s - w / 2, s + w / 2, zc + h / 2, zc + h / 2 + fw)):
                    W.box(pb, 'wood', a_, b_, c_, d_, d0 + 0.02, d0 + 0.1, fc)
            ctr = W.P(s, zc, d0 + 0.071)
            rec.update(center=[round(x, 3) for x in ctr], normal=[round(float(W.n[0]), 4), round(float(W.n[1]), 4), 0.0],
                       right=[round(float(W.t[0]), 4), round(float(W.t[1]), 4), 0.0], up=[0, 0, 1])
        elif st == 'tate':
            d0, d1 = 0.3, 0.3 + w
            W.box(pb, 'wood', s - 0.05, s + 0.05, zc - h / 2, zc + h / 2, d0, d1, bc, skip=())
            if lod >= 1:
                for zz in (zc + h / 2 - 0.1, zc - h / 2 + 0.1):
                    W.box(pb, 'metal', s - 0.02, s + 0.02, zz - 0.02, zz + 0.02, 0.0, d0, lin('#333333'))
                W.box(pb, 'wood', s - 0.06, s + 0.06, zc - h / 2 - 0.05, zc - h / 2, d0 - 0.03, d1 + 0.03, fc, skip=())
                W.box(pb, 'wood', s - 0.06, s + 0.06, zc + h / 2, zc + h / 2 + 0.05, d0 - 0.03, d1 + 0.03, fc, skip=())
            ctr = W.P(s, zc, (d0 + d1) / 2)
            rec.update(center=[round(x, 3) for x in ctr], normal=[round(float(W.t[0]), 4), round(float(W.t[1]), 4), 0.0],
                       right=[round(float(W.n[0]), 4), round(float(W.n[1]), 4), 0.0], up=[0, 0, 1], two_sided=True, thick=0.1)
        elif st == 'roof':
            zr = self.roofinfo.get('zr', self.ztop) if A.z is None else self.zs[k] + A.z
            d0 = -(A.d or 1.0)
            for q in (s - w / 2 + 0.2, s + w / 2 - 0.2):
                W.box(pb, 'metal', q - 0.04, q + 0.04, zr, zr + 0.6, d0 - 0.04, d0 + 0.04, lin('#55585a'), skip=('-z',))
            W.box(pb, 'wood', s - w / 2, s + w / 2, zr + 0.6, zr + 0.6 + h, d0, d0 + 0.08, bc, skip=())
            ctr = W.P(s, zr + 0.6 + h / 2, d0 + 0.081)
            rec.update(center=[round(x, 3) for x in ctr], normal=[round(float(W.n[0]), 4), round(float(W.n[1]), 4), 0.0],
                       right=[round(float(W.t[0]), 4), round(float(W.t[1]), 4), 0.0], up=[0, 0, 1])
        self.signs.append(rec)

    def lantern(self, x, y, ztop, r, h, col, capc=None):
        pb, lod = self.pb, self.lod
        capc = lin(capc or '#262321')
        c = lin(col)
        beam(pb, 'metal', (x, y, ztop), (x, y, ztop + 0.25), 0.015, 0.015, capc)
        if lod == 0:
            box(pb, 'fabric', (x - r, y - r, ztop - h), (2 * r, 0, 0), (0, 2 * r, 0), (0, 0, h), c)
            return
        n = 8 if lod >= 2 else 6
        prism(pb, 'wood', (x, y), r * 0.58, r * 0.58, ztop - 0.07, ztop, n, capc)
        zb = ztop - 0.07 - h
        fr = [0.0, 0.2, 0.5, 0.8, 1.0]
        rr = [0.6, 0.93, 1.0, 0.93, 0.6]
        for j in range(4):
            prism(pb, 'fabric', (x, y), r * rr[j], r * rr[j + 1], zb + h * fr[j], zb + h * fr[j + 1], n, hj(c, 0.03, j), top=False)
        prism(pb, 'wood', (x, y), r * 0.58, r * 0.58, zb - 0.06, zb, n, capc, bottom=True)

    def att_lanterns(self, A):
        """提灯の列(n 個、w=列の長さ、z=吊りの上端の高さ、d=壁から)。"""
        W, s, k = self.attach_wall(A)
        n = max(1, A.n)
        span = min(A.w if A.w is not None else W.L * 0.8, max(W.L - 0.5, 0.0))
        ztop = self.zs[k] + (A.z if A.z is not None else self.fh[k] - 0.35)
        d = A.d if A.d is not None else 0.55
        r = A.prm.get('r', 0.17)
        hh = A.h or 0.42
        for j in range(n):
            sj = s if n == 1 else s - span / 2 + span * j / (n - 1)
            p = W.P(sj, 0, d)
            self.lantern(p[0], p[1], ztop, r, hh, A.color or PAL['lantern_red'], A.color2)

    def att_nobori(self, A):
        """幟(竿+静止した旗)。n 本を w 間隔で、壁から d m。"""
        pb = self.pb
        W, s, k = self.attach_wall(A)
        d = A.d if A.d is not None else 0.8
        step = A.w or 1.2
        fc = lin(A.color or '#c0392b')
        pc = lin(A.color2 or '#4e6fa3')
        for j in range(max(1, A.n)):
            sj = s + (j - (A.n - 1) / 2) * step
            p = W.P(sj, 0, d)
            zg = self.ground(p[0], p[1])
            H = A.h or 3.8
            beam(pb, 'metal', (p[0], p[1], zg), (p[0], p[1], zg + H), 0.035, 0.035, pc)
            fw, fh_ = 0.48, H - 1.25
            q0 = W.P(sj + 0.03, zg + H - 0.12 - fh_, d)
            q1 = W.P(sj + 0.03 + fw, zg + H - 0.12, d)
            pts = [W.P(sj + 0.03, q0[2], d), W.P(sj + 0.03 + fw, q0[2], d), W.P(sj + 0.03 + fw, q1[2], d), W.P(sj + 0.03, q1[2], d)]
            pb.poly('fabric', pts, hj(fc, 0.04, j), W.nrm())
            pb.poly('fabric', pts, hj(fc, 0.04, j), W.nrm(-1))
            beam(pb, 'metal', W.P(sj, zg + H - 0.1, d), W.P(sj + 0.03 + fw, zg + H - 0.1, d), 0.02, 0.02, pc)
            ctr = W.P(sj + 0.03 + fw / 2, (q0[2] + q1[2]) / 2, d)
            self.signs.append(dict(spec=self.spec.id, kind='nobori', text=A.text, w=fw, h=fh_, center=[round(x, 3) for x in ctr],
                                   normal=[round(float(W.n[0]), 4), round(float(W.n[1]), 4), 0.0], right=[round(float(W.t[0]), 4), round(float(W.t[1]), 4), 0.0],
                                   up=[0, 0, 1], two_sided=True))

    def roof_top_at(self, x, y):
        info = self.roofinfo
        if info.get('h_fn') is not None:
            return info['h_fn'](x, y) + 0.05
        fr = info.get('fr')
        if info.get('kind') in ('hip', 'irimoya') and fr is not None:
            lx, ly = fr.loc(x, y)
            R = self.spec.roof
            return self.ztop + (fr.hy - abs(ly)) * R.slope
        return info.get('zr', self.ztop)

    def att_chimney(self, A):
        """煙突(prm['u'], prm['v'] = 屋根の矩形の局所 m)。"""
        pb = self.pb
        fr = self.roofinfo.get('fr') or self.roof_frame(self.rings[-1], Roof())
        p = fr.P(A.prm.get('u', 0.0), A.prm.get('v', 0.0), 0)
        w = A.w or 0.5
        zr = self.roof_top_at(p[0], p[1]) - 0.3
        H = A.h or 1.2
        c = lin(A.color or '#6f6c66')
        box(pb, 'stone', (p[0] - w / 2, p[1] - w / 2, zr), (w, 0, 0), (0, w, 0), (0, 0, H + 0.3), c, skip=('-z',))
        box(pb, 'metal', (p[0] - w / 2 - 0.06, p[1] - w / 2 - 0.06, zr + H + 0.3), (w + 0.12, 0, 0), (0, w + 0.12, 0), (0, 0, 0.08), lin('#4d4f50'))

    def att_tank(self, A):
        """屋上のタンク・ボンベ(prm['u'],['v'])。"""
        fr = self.roofinfo.get('fr') or self.roof_frame(self.rings[-1], Roof())
        p = fr.P(A.prm.get('u', 0.0), A.prm.get('v', 0.0), 0)
        r = A.w or 0.35
        H = A.h or 1.3
        z0 = self.roofinfo.get('ze', self.ztop) + 0.05 if A.z is None else self.zs[0] + A.z
        for j in range(max(1, A.n)):
            q = (p[0] + fr.u[0] * j * (2 * r + 0.15), p[1] + fr.u[1] * j * (2 * r + 0.15))
            prism(self.pb, 'metal', q, r, r, z0, z0 + H, 10 if self.lod >= 2 else 6, lin(A.color or '#9a9c9a'))
            prism(self.pb, 'metal', q, r, r * 0.4, z0 + H, z0 + H + r * 0.5, 10 if self.lod >= 2 else 6, lin(A.color or '#9a9c9a'))

    def att_tent(self, A):
        """庇テント(布、前垂れ付き)。"""
        pb = self.pb
        W, s, k = self.attach_wall(A)
        w = A.w or 2.4
        dep = A.d or 1.0
        z = self.zs[k] + (A.z if A.z is not None else self.fh[k] - 0.6)
        zo = z - dep * 0.45
        c = lin(A.color or '#2f5d3a')
        c2 = lin(A.color2) if A.color2 else None
        s0, s1 = s - w / 2, s + w / 2
        n = max(1, int(w / 0.3)) if c2 is not None else 1
        for j in range(n):
            sa, sb = s0 + (s1 - s0) * j / n, s0 + (s1 - s0) * (j + 1) / n
            cc = c if (c2 is None or j % 2 == 0) else c2
            pb.poly('fabric', [W.P(sa, zo, dep), W.P(sb, zo, dep), W.P(sb, z, 0.0), W.P(sa, z, 0.0)], cc, (W.n[0], W.n[1], 1.0))
            pb.poly('fabric', [W.P(sa, zo, dep), W.P(sb, zo, dep), W.P(sb, zo - 0.25, dep), W.P(sa, zo - 0.25, dep)], cc, W.nrm())
        for sx, ss in ((-1, s0), (1, s1)):
            pb.poly('fabric', [W.P(ss, z, 0.0), W.P(ss, zo, dep), W.P(ss, zo - 0.25, dep)], tint(c, 0.85), W.tv(sx))
        if self.lod >= 1:
            for ss in (s0 + 0.05, s1 - 0.05):
                beam(pb, 'metal', W.P(ss, z - 0.5, 0.0), W.P(ss, zo + 0.02, dep - 0.05), 0.025, 0.025, lin('#555555'))

    def att_stair(self, A):
        """外階段(壁沿い、s から +t 方向へ w=長さ、地面から階 floor の床まで)。prm['width']。"""
        pb = self.pb
        W, s, k = self.attach_wall(A)
        width = A.prm.get('width', 0.9)
        L = A.w or 3.6
        d0 = A.d or 0.05
        zg = self.ground(*W.P(s, 0, d0 + width / 2)[:2])
        z1 = self.zs[k]
        n = max(2, int(math.ceil((z1 - zg) / 0.19)))
        rise = (z1 - zg) / n
        run = L / n
        c = lin(A.color or '#6e6a64')
        for j in range(n):
            sa = s + j * run
            W.box(pb, 'metal', sa, sa + run + 0.03, zg + (j + 1) * rise - 0.04, zg + (j + 1) * rise, d0, d0 + width, c)
        for dd in (d0 + 0.02, d0 + width - 0.02):
            W.beam(pb, 'metal', (s, zg, dd), (s + L, z1, dd), 0.2, 0.04, tint(c, 0.85), skip=())
        Wr = Wall(W.P(s, 0, d0 + width), W.P(s + L, 0, d0 + width))
        for j in range(n + 1):
            sj = j * run
            Wr.box(pb, 'metal', sj - 0.02, sj + 0.02, zg + j * rise, zg + j * rise + 0.9, -0.02, 0.02, lin('#9a9c9a'), skip=('-z',))
        beam(pb, 'metal', W.P(s, zg + 0.9, d0 + width), W.P(s + L, z1 + 0.9, d0 + width), 0.04, 0.04, lin('#9a9c9a'))

    def att_steps(self, A):
        """玄関の石段(壁の前、d=始まる位置)。n=None なら床と地面の差から。"""
        pb = self.pb
        W, s, k = self.attach_wall(A)
        w = A.w or 2.0
        d0 = A.d or 0.0
        zt = self.zs[0] if A.z is None else self.zs[0] + A.z
        zg = self.ground(*W.P(s, 0, d0 + 0.8)[:2])
        n = A.n if A.n > 1 else max(1, int(round((zt - zg) / 0.17)))
        if zt - zg < 0.08:
            return
        rise = (zt - zg) / n
        tread = A.prm.get('tread', 0.32)
        c = lin(A.color or '#9a968e')
        for j in range(n):
            ztop = zt - j * rise
            W.box(pb, 'stone', s - w / 2, s + w / 2, zg - 0.1, ztop, 0.0 + d0, d0 + (j + 1) * tread, hj(c, 0.05, j), skip=('-y', '-z'))

    def att_noren(self, A):
        W, s, k = self.attach_wall(A)
        w = A.w or 1.6
        ztop = self.zs[k] + (A.z if A.z is not None else 2.3)
        self.noren(W, s - w / 2, s + w / 2, ztop, A.h or 0.9, A.color or PAL['noren_navy'], A.d if A.d is not None else 0.08)

    def att_crest(self, A):
        """紋(円盤+輪)。"""
        pb = self.pb
        W, s, k = self.attach_wall(A)
        r = A.w or 0.35
        zc = self.zs[k] + (A.z if A.z is not None else self.fh[k] / 2)
        if A.prm.get('gable'):
            zc = self.roofinfo.get('zr', self.ztop) - (A.z or 1.0)
        n = 16 if self.lod >= 2 else 10
        c = lin(A.color or '#f2efe8')
        c2 = lin(A.color2 or '#2a2522')
        pts = [W.P(s + r * math.cos(t), zc + r * math.sin(t), 0.04) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]
        pb.poly('wood', pts, c, W.nrm())
        if self.lod >= 1:
            for j in range(n):
                t0, t1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
                q = [W.P(s + r * math.cos(t0), zc + r * math.sin(t0), 0.05), W.P(s + r * math.cos(t1), zc + r * math.sin(t1), 0.05),
                     W.P(s + 0.82 * r * math.cos(t1), zc + 0.82 * r * math.sin(t1), 0.05), W.P(s + 0.82 * r * math.cos(t0), zc + 0.82 * r * math.sin(t0), 0.05)]
                pb.poly('wood', q, c2, W.nrm())
            for a in (math.pi / 4, -math.pi / 4):
                W.beam(pb, 'wood', (s - 0.7 * r * math.cos(a), zc - 0.7 * r * math.sin(a), 0.045), (s + 0.7 * r * math.cos(a), zc + 0.7 * r * math.sin(a), 0.045), 0.07 * r / 0.35, 0.012, c2)

    def att_box(self, A):
        W, s, k = self.attach_wall(A)
        z = self.zs[k] + (A.z or 0.0)
        d = A.d or 0.0
        W.box(self.pb, A.prm.get('mat', 'wall'), s - (A.w or 1.0) / 2, s + (A.w or 1.0) / 2, z, z + (A.h or 1.0), d, d + A.prm.get('dep', 0.5), lin(A.color or '#888888'), skip=())

    def att_porch(self, A):
        """玄関ポーチ・向拝(柱+梁+屋根)。prm: roof='gable'|'shed'|'kara'、mat、slope、platform、post_mat('paint'/'wood')、noren、lanterns。"""
        pb, lod = self.pb, self.lod
        W, s, k = self.attach_wall(A)
        w = A.w or 3.0
        dep = A.d or 2.0
        z0 = self.zs[0]
        ze = z0 + (A.h or 3.0)
        pc = lin(A.color2 or '#7a3b28')
        pm = A.prm.get('post_mat', 'wood')
        rkind = A.prm.get('roof', 'gable')
        rmat = A.prm.get('mat', 'kawara')
        slope = A.prm.get('slope', 0.5)
        R2 = dreplace(self.spec.roof, kind='gable', mat=rmat, slope=slope, eave=0.45, verge=A.prm.get('verge', 0.5),
                      color=A.color, chidori=[], kengyo=A.prm.get('kengyo', True), gutters=False, rafters=None)
        if A.prm.get('platform', True):
            zgf = self.ground(*W.P(s, 0, dep)[:2])
            W.box(pb, 'stone', s - w / 2 - 0.1, s + w / 2 + 0.1, min(zgf, z0) - 0.2, z0 - 0.02, 0.0, dep + 0.1, lin('#8d8981'))
            nst = int(round((z0 - zgf) / 0.17))
            if nst > 0:
                rise = (z0 - zgf) / (nst + 1)
                for j in range(nst):
                    W.box(pb, 'stone', s - w / 2 + 0.25, s + w / 2 - 0.25, zgf - 0.1, z0 - (j + 1) * rise, dep + 0.1, dep + 0.1 + (j + 1) * 0.3,
                          hj(lin('#9a968e'), 0.05, j), skip=('-y', '-z'))
        posts = [s - w / 2 + 0.2, s + w / 2 - 0.2]
        pd = dep - 0.2
        for ps in posts:
            zg = z0 if A.prm.get('platform', True) else self.ground(*W.P(ps, 0, pd)[:2])
            W.box(pb, pm, ps - 0.11, ps + 0.11, zg, ze - 0.05, pd - 0.11, pd + 0.11, pc, skip=('-z',))
            if lod >= 1:
                W.box(pb, 'stone', ps - 0.17, ps + 0.17, zg - 0.05, zg + 0.12, pd - 0.17, pd + 0.17, lin('#8a8680'), skip=('-z',))
            W.box(pb, pm, ps - 0.08, ps + 0.08, ze - 0.4, ze - 0.12, 0.0, pd, pc, skip=())
        W.box(pb, pm, s - w / 2 + 0.05, s + w / 2 - 0.05, ze - 0.48, ze - 0.14, pd - 0.09, pd + 0.09, pc, skip=())
        if lod >= 1:   # 蟇股風の束
            W.box(pb, pm, s - 0.2, s + 0.2, ze - 0.14, ze + 0.12, pd - 0.07, pd + 0.07, tint(pc, 1.1), skip=())
        pb.poly('wood', [W.P(s - w / 2, ze - 0.12, 0.0), W.P(s + w / 2, ze - 0.12, 0.0), W.P(s + w / 2, ze - 0.12, dep), W.P(s - w / 2, ze - 0.12, dep)],
                lin(self.spec.roof.soffit_col), (0, 0, -1))
        if rkind == 'shed':
            self.pent(W, s - w / 2 - 0.35, s + w / 2 + 0.35, ze + 0.12 + (dep + 0.45) * slope, dep + 0.45, slope, rmat, A.color, brackets=False)
        elif rkind == 'kara':
            self.karahafu(W, s, w, dep, ze, R2)
        else:
            c = W.P(s, 0, (dep + 0.1) / 2)
            fr = Frame(c[:2], W.n, (dep + 0.1) / 2, w / 2)
            self.roof_gable(fr, ze + 0.1, R2)
            # 妻(正面)の三角を塞ぐ
            zr = ze + 0.1 + (w / 2) * slope
            tri = [W.P(s - w / 2, ze + 0.1, dep - 0.05), W.P(s + w / 2, ze + 0.1, dep - 0.05), W.P(s, zr - 0.08, dep - 0.05)]
            pb.poly('wood', tri, lin(A.prm.get('gable_col', '#6b4a33')), W.nrm())
            if A.text:
                pass
        if A.prm.get('noren'):
            nw = A.prm.get('noren_w', w * 0.6)
            self.noren(W, s - nw / 2, s + nw / 2, ze - 0.5, A.prm.get('noren_h', 1.0), A.prm['noren'], 0.06)
        for j, lc in enumerate(A.prm.get('lanterns', [])):
            ps = posts[j % 2]
            p = W.P(ps + (0.35 if j % 2 == 0 else -0.35), 0, pd)
            self.lantern(p[0], p[1], ze - 0.5, 0.17, 0.42, lc, None)

    def karahafu(self, W, s, w, dep, ze, R):
        """唐破風(正面に向いた曲線の破風)。断面(幅方向)を曲線にして奥行き方向へ押し出す。"""
        pb, lod = self.pb, self.lod
        Hc = 0.55 + 0.12 * w
        hw = w / 2 + 0.45
        N = 12 if lod >= 2 else 8
        col = lin(R.color or ROOF_COL.get(R.mat, PAL['kawara']))

        def prof(x):
            return Hc * ((1 + math.cos(math.pi * x)) / 2) ** 1.3 + 0.14 * abs(x) ** 6 - 0.14
        xs = np.linspace(-1, 1, N + 1)
        S = [s + x * hw for x in xs]
        Z = [ze + prof(x) for x in xs]
        dB, dF = -0.05, dep + 0.45
        nd = max(2, int((dF - dB) / 0.3)) if lod >= 1 else 1
        th = 0.18
        for i in range(N):
            for j in range(nd):
                da, db = dB + (dF - dB) * j / nd, dB + (dF - dB) * (j + 1) / nd
                cc = hj(col, 0.04, j, i) if j % 2 == 0 else tint(hj(col, 0.04, j, i), 0.93)
                pb.poly('roof', [W.P(S[i], Z[i], db), W.P(S[i + 1], Z[i + 1], db), W.P(S[i + 1], Z[i + 1], da), W.P(S[i], Z[i], da)], cc, (0, 0, 1))
            pb.poly('wood', [W.P(S[i], Z[i] - th, dB), W.P(S[i + 1], Z[i + 1] - th, dB), W.P(S[i + 1], Z[i + 1] - th, dF), W.P(S[i], Z[i] - th, dF)],
                    lin(R.soffit_col), (0, 0, -1))
            # 正面の曲線の破風板
            beam(pb, 'wood', W.P(S[i], Z[i] - 0.08, dF + 0.05), W.P(S[i + 1], Z[i + 1] - 0.08, dF + 0.05), 0.12, 0.34, lin(R.hafu_col))
        for sx, i in ((-1, 0), (1, N)):
            pb.poly('wood', [W.P(S[i], Z[i], dB), W.P(S[i], Z[i], dF), W.P(S[i], Z[i] - th, dF), W.P(S[i], Z[i] - th, dB)], lin(R.hafu_col), W.tv(sx))
        if lod >= 1:
            beam(pb, 'roof', W.P(s, ze + Hc - 0.12, dB), W.P(s, ze + Hc - 0.12, dF), 0.22, 0.14, tint(col, 0.85))
        self.kengyo(W.P(s, ze + Hc - 0.32, dF + 0.08), (W.n[0], W.n[1]), (W.t[0], W.t[1]), sc=0.65, col=R.hafu_col)

    def att_cupola(self, A):
        """越屋根・小塔(屋根の上の小屋)。prm['u'],['v'] 位置、w×d、h=壁高、prm['roof']='hip'|'hogyo'。"""
        pb = self.pb
        fr0 = self.roofinfo.get('fr') or self.roof_frame(self.rings[-1], Roof())
        c = fr0.P(A.prm.get('u', 0.0), A.prm.get('v', 0.0), 0)
        w = A.w or 2.0
        dd = A.d or w
        H = A.h or 1.2
        z0 = self.roof_top_at(c[0], c[1]) - 0.3
        F2 = Frame(c[:2], fr0.u, w / 2, dd / 2)
        cs = C.ccw([F2.P(-w / 2, -dd / 2, 0)[:2], F2.P(w / 2, -dd / 2, 0)[:2], F2.P(w / 2, dd / 2, 0)[:2], F2.P(-w / 2, dd / 2, 0)[:2]])
        wc = lin(A.color or self.finish_for(len(self.fh), 0).color)
        for i in range(4):
            W = Wall(cs[i], cs[(i + 1) % 4])
            W.quad(pb, 'wall', 0.0, z0, W.L, z0 + H, 0.0, wc)
            if self.lod >= 1:     # ルーバー窓
                W.quad(pb, 'dark', 0.2, z0 + 0.45, W.L - 0.2, z0 + H - 0.15, 0.01, lin('#2a2624'))
                for zz in np.arange(z0 + 0.5, z0 + H - 0.15, 0.12):
                    W.beam(pb, 'wood', (0.2, zz, 0.02), (W.L - 0.2, zz, 0.02), 0.03, 0.06, lin('#4a3a2e'), skip=())
        R2 = dreplace(self.spec.roof, kind='hip', slope=A.prm.get('slope', 0.5), eave=0.35, color=A.color2 or self.spec.roof.color, gutters=False, chidori=[])
        self.roof_hip(Frame(c[:2], fr0.u, w / 2, dd / 2), z0 + H, R2, hogyo=A.prm.get('roof', 'hip') == 'hogyo')


# ====================================================================== 経年(頂点色)
def weather(pb, age, z_ground, seed):
    """足元の汚れ・縦の雨だれ・大きな色むらを頂点色に掛ける(材質ごとの効き MATERIALS[2])。"""
    for m, (V, Cl, F) in pb.g.items():
        wt = MATERIALS.get(m, (0, 0, 0))[2]
        if wt <= 0 or not V:
            continue
        A = np.asarray(V, float)
        Cc = np.asarray(Cl, float)
        h = np.clip(A[:, 2] - z_ground, 0, None)
        grime = np.exp(-h / 0.9)
        hor = A[:, 0] * 0.83 + A[:, 1] * 0.56
        streak = C.vnoise(hor, A[:, 2] * 0.1, 0.5, seed)
        mott = C.vnoise(A[:, 0] + A[:, 2] * 0.3, A[:, 1] - A[:, 2] * 0.2, 3.0, seed + 7)
        k = 1.0 - wt * age * (0.22 * grime + 0.16 * np.clip(streak - 0.55, 0, 1) / 0.45) + wt * age * 0.10 * (mott - 0.5)
        Cc = Cc * k[:, None]
        Cc[:, 2] *= 1.0 - wt * age * 0.06 * grime
        Cc = np.clip(Cc, 0.0, 1.0)
        pb.g[m] = (V, [tuple(c) for c in Cc], F)


# ====================================================================== 入口
def _bld_by_id(field):
    d = getattr(field, '_kp_by_id', None)
    if d is None:
        d = {b['id']: b for b in field.blds}
        field._kp_by_id = d
    return d


def build_building(spec, field=None, lod_cap=None):
    """BuildingSpec -> Built(pb=材質別のメッシュ, signs=看板の面, info=数値)。"""
    return Builder(spec, field, lod_cap).run()


def replaced_ids(specs):
    out = set()
    for sp in specs:
        out.update(sp.replaces if sp.replaces is not None else [sp.id])
    return out


def _try_import(name):
    try:
        return importlib.import_module(name)
    except ImportError as ex:
        if ex.name == name:
            return None
        raise


def zone_specs(zone):
    """区域の BuildingSpec の一覧。kd_zone_<zone>.specs() があればそれ、無ければ kd_parts_test の試作(その区域の分)。"""
    mod = _try_import('kd_zone_%s' % zone)
    if mod is not None and hasattr(mod, 'specs'):
        return list(mod.specs())
    mod = _try_import('kd_parts_test')
    if mod is not None and hasattr(mod, 'proto_specs'):
        return [s for s in mod.proto_specs() if (s.zone or '') == zone]
    return []


def build_details(field, specs, mats, coll, zone, lod_cap=None, log=print):
    """区域の本物の建物をまとめて作る -> (objs, 置き換えた id, 1 棟ごとの info, 看板)。"""
    pb = PB()
    infos, signs = [], []
    for sp in specs:
        b = build_building(sp, field, lod_cap)
        pb.merge(b.pb)
        infos.append(b.info)
        signs.extend(b.signs)
        log('  %s %s: %d tris (lod %d)' % (sp.id, sp.name, b.info['tris'], b.info['lod']))
    objs = pb.to_objects('Bld_%s' % zone, mats, coll) if bpy is not None else []
    return objs, replaced_ids(specs), infos, signs


def export_zone(zone, objs, out_web=None, pos_bits=16):
    """区域の glb(Draco)。細かい部品があるので位置の量子化は 16 bit。"""
    out_web = out_web or C.OUT_WEB
    path = os.path.join(out_web, 'buildings_%s.glb' % zone)
    return C.export_glb([o for o in objs if o is not None], path, pos_bits=pos_bits)


def run_zone(zone, specs=None, out_web=None, lod_cap=None, boxes=True, log=None):
    """区域スクリプトの main(Blender ヘッドレス): 仮の箱(残り)+本物 -> buildings_<zone>.glb、数値は output/kusatsu/parts_<zone>.json。"""
    import time
    import kd_field as F
    import kd_buildings as KB
    t0 = time.time()
    if log is None:
        def log(*a):
            print('[parts %s %.1fs]' % (zone, time.time() - t0), *a, flush=True)
    C.reset_scene()
    field = F.Field(C.load_osm(), log=log)
    specs = zone_specs(zone) if specs is None else specs
    mats = get_materials()
    coll = C.new_collection('Buildings_%s' % zone)
    objs, rep, infos, signs = build_details(field, specs, mats, coll, zone, lod_cap, log)
    bidx = []
    if boxes:
        bobjs, bidx = KB.build_boxes(field, {'bldg': C.make_material('kd_bldg', 0.9)}, {zone: coll}, zones=zone, skip=rep, log=log)
        objs = [o for o in [bobjs.get(zone)] if o is not None] + objs
    out_web = out_web or C.OUT_WEB
    size = export_zone(zone, objs, out_web)
    tris = C.count_tris(objs)
    stats = dict(zone=zone, glb_bytes=size, tris=tris, detail_tris=sum(i['tris'] for i in infos), boxes=len(bidx),
                 buildings=infos, signs=signs, replaced=sorted(rep))
    os.makedirs(C.OUT_BLEND, exist_ok=True)
    json.dump(stats, open(os.path.join(C.OUT_BLEND, 'parts_%s.json' % zone), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    _update_index(out_web, rep, zone)
    log('exported buildings_%s.glb %d bytes, %d tris (detail %d, boxes %d)' % (zone, size, tris, stats['detail_tris'], len(bidx)))
    return stats


def _update_index(out_web, rep, zone=None):
    """buildings_index.json の detail 印を更新(zone を渡したらその区域の行だけ。他区域の印は残す)。"""
    p = os.path.join(out_web, 'buildings_index.json')
    if not os.path.exists(p):
        return
    try:
        idx = json.load(open(p, encoding='utf-8'))
        for b in idx:
            if zone is not None and b.get('zone') != zone:
                continue
            b['detail'] = b['id'] in rep
        json.dump(idx, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception:
        pass
