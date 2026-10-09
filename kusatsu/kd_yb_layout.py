# -*- coding: utf-8 -*-
"""kd_yb_layout.py -- 湯畑(フェーズ3)の配置と高さの定義。numpy だけ(Blender 外でも動く)。

kd_field.py(地形の高さ場・地形の穴)と kd_yubatake.py(Blender で湯畑の形を作る)の両方がここを使う。
座標: 原点=湯畑重心、+X=東、+Y=北、Z = Blender Z(標高 - 1153 m)。

根拠(docs/kusatsu/phase3_notes.md に詳しく):
- 平面形は OSM: 柵 912422978/912422980(湯畑を囲む石柵)、池 954786841(南の源泉の池)と 896878996(北の湯滝の滝壺)、
  湯樋 7 本 = waterway=ditch 954629652〜954629658、集め樋 954629659、湯滝へ落とす樋 954629660、湯滝 896878997、
  見学デッキの階段 898032021/22/23、デッキの柵 954629665/954629669、北の柵 954629666、西の柵 954629649、周回の車道 594139679。
- 高さは DEM5A(柵の線上の標高に平面を当てはめ、残差 0.17 m)と動画フレーム(樋と柵・デッキの見え方)。
  湯畑は南(熱乃湯側)が高く北(湯滝側)が低い。滝壺は周回路より約 4 m 低い(DEM と OSM の階段・デッキ)。
"""
import math

import numpy as np

import kd_common as C

# ---------------------------------------------------------------- OSM の id
W_FENCE_ENC = 912422978      # 湯畑を囲む石柵(西→南→東)
W_FENCE_ENC2 = 912422980     # 石柵の北東の続き
W_FENCE_EDECK_OUT = 954629665
W_FENCE_EDECK_IN = 954629669
W_FENCE_N = 954629666
W_FENCE_W = 954629649
W_FENCE_POND_N = 954629668   # 滝壺の北の木柵
W_POND_S = 954786841         # 源泉の池(南)
W_POND_N = 896878996         # 湯滝の滝壺(北)
W_TROUGHS = [954629652, 954629653, 954629654, 954629655, 954629656, 954629657, 954629658]
W_COLLECT = 954629659
W_DRAIN = 954629660
W_STREAM = 896878997
W_STEPS_W = 898032021        # 西の見学デッキの木の階段(滝壺 → 周回路)
W_STEPS_NE = 898032022
W_STEPS_E = 898032023
W_LOOP = 594139679           # 湯畑を一周する車道(layer=-1 なのでフェーズ2の道には入っていない)
YB_STEPS = {W_STEPS_W, W_STEPS_NE, W_STEPS_E}
YB_BUILDINGS = {'898032029'}   # 足湯 湯けむり亭(building=roof)は kd_yubatake.py で作る

# ---------------------------------------------------------------- 高さ(Blender Z)
# 周回路(柵の足元)の高さ = DEM を柵の線上で当てはめた平面(北東へ下る)。平均は約 1.2、南端 2.0、北東端 0.6。
RIM_C, RIM_GX, RIM_GY = 1.15, -0.012, -0.022
TR_W, TR_H, TR_T = 0.45, 0.18, 0.035      # 湯樋 幅・高さ・板厚(m)
TR_Z0 = 1.02                               # 湯樋の底(南の始まり)
TR_DROP = math.tan(math.radians(0.6))      # 傾斜 0.6 度(40 m で約 0.42 m)
POST_H = 1.15                              # 樋の底から床(岩・砂利)まで
POOL_S_WATER = 1.10                        # 源泉の池の水面
POOL_S_FLOOR = 0.25
LOW_Z = -4.0                               # 滝壺のまわりの低い通路・西デッキの地面
BASIN_WATER = -4.35                        # 滝壺の水面
BASIN_FLOOR = -5.0
EDECK_Z = -1.6                             # 東の見学デッキの床
WALK_Z = 0.90                              # 西の見学デッキ(上の通路)の床。北西の車道とそろえる
WDECK_Z = -3.85                            # 西の見学デッキ(下、滝壺の脇)の床

# 崖の線(湯畑の床 → 滝壺へ落ちる岩の縁)。この線より北が低い側。OSM の滝壺の南岸から 0.6〜1.2 m 南。
CLIFF = [(-4.4, 17.6), (-2.6, 19.6), (0.5, 20.4), (3.0, 21.6), (4.9, 22.3), (6.3, 22.0), (8.0, 21.9), (10.2, 23.2),
         (12.6, 24.1), (15.0, 24.2), (17.6, 24.1), (19.4, 23.4), (22.6, 19.0), (24.5, 17.0)]
# 東の見学デッキの床の外形
EDECK = [(21.2, 19.6), (22.8, 19.6), (24.0, 22.0), (25.3, 24.8), (25.45, 31.0), (21.4, 31.0), (21.4, 29.7), (19.5, 29.7), (19.1, 22.9)]
# 湯けむり亭(OSM way 898032029 の最小矩形)
YUKEMURI = dict(c=(9.0, -5.0), L=5.9, W=3.8, ang=59.0)
# 小物の位置(OSM の点。無いものは動画から決めた推定位置)
TEARAI = [(4.9, -13.8), (-12.9, 9.2), (19.2, 34.1)]           # 手洗乃湯(OSM information=board の位置)
LANTERNS = [(4.7, 18.7, 3.3), (-17.2, -29.0, 2.9)]            # 石灯籠 (x, y, 高さ)。1つ目は OSM man_made=lamp「灯籠」
BENCHES = [(3.3, -16.8), (-20.6, -6.2), (-19.1, -1.3), (-16.7, 2.9), (9.6, 2.9)]   # OSM amenity=bench
BOARDS = [(-20.4, -4.0), (-17.3, -29.7), (13.8, 38.3), (13.5, 30.9)]            # 案内板(文字は読めないので入れない)
STELE = (16.7, 6.6)          # ロマンティック・シュトラーセ記念碑(OSM)。文字は読めない
SIGN_STONE = (12.6, 8.6)     # 「草津温泉 湯畑」の黒い石標(S 4:30。位置は推定)
TAKINOYU = (14.1, 36.3)      # 足湯 滝の湯(OSM)
EPAVILION = (23.4, 27.6)     # 東デッキの東屋(W 6:21〜6:36、S 5:12〜5:18)
YUWAKU = (-14.6, -26.6)      # 御汲上げの湯枠(源泉の池の木枠。R 2:27)


def rim(x, y):
    return RIM_C + RIM_GX * np.asarray(x, float) + RIM_GY * np.asarray(y, float)


# ---------------------------------------------------------------- 幾何の補助
def seg_nearest(px, py, poly, closed=False):
    """点群から折れ線への最短距離・最近点・その線分の向き(単位)。"""
    px = np.asarray(px, float); py = np.asarray(py, float)
    P = np.asarray(poly, float)
    if closed:
        P = np.vstack([P, P[:1]])
    best = np.full(px.shape, np.inf)
    nx = np.zeros(px.shape); ny = np.zeros(px.shape)
    tx = np.zeros(px.shape); ty = np.zeros(px.shape)
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        d = b - a
        L2 = float(d @ d)
        if L2 < 1e-12:
            continue
        t = np.clip(((px - a[0]) * d[0] + (py - a[1]) * d[1]) / L2, 0, 1)
        qx = a[0] + d[0] * t; qy = a[1] + d[1] * t
        dist = np.hypot(px - qx, py - qy)
        m = dist < best
        best = np.where(m, dist, best)
        nx = np.where(m, qx, nx); ny = np.where(m, qy, ny)
        L = math.sqrt(L2)
        tx = np.where(m, d[0] / L, tx); ty = np.where(m, d[1] / L, ty)
    return best, nx, ny, tx, ty


def side_of(px, py, poly):
    """折れ線の左(進行方向に対して)が正の符号つき距離。"""
    d, qx, qy, tx, ty = seg_nearest(px, py, poly)
    cr = tx * (np.asarray(py) - qy) - ty * (np.asarray(px) - qx)
    return np.where(cr >= 0, d, -d)


def inside(px, py, ring):
    return C.points_in_poly(np.asarray(px, float), np.asarray(py, float), [tuple(p) for p in ring])


def sdist(px, py, ring):
    """多角形への符号つき距離(内側が負)。"""
    d = seg_nearest(px, py, ring, closed=True)[0]
    return np.where(inside(px, py, ring), -d, d)


def offset_ring(ring, d, step=1.0):
    """ccw の閉じた輪を d m 外へずらす(なめらかな輪向け。各点の法線で)。"""
    P, _ = C.resample(list(ring) + [ring[0]], step)
    P = P[:-1]
    tan = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    tan /= np.maximum(np.hypot(*tan.T), 1e-9)[:, None]
    nor = np.stack([tan[:, 1], -tan[:, 0]], axis=1)      # ccw の外向き
    return [tuple(p) for p in (P + nor * d)]


def polyline_len(P):
    P = np.asarray(P, float)
    return float(np.hypot(*(P[1:] - P[:-1]).T).sum())


# ---------------------------------------------------------------- 配置
class Layout:
    def __init__(self, osm):
        ways = {}
        for e in osm['elements']:
            if e['type'] == 'way' and e.get('geometry'):
                ways[e['id']] = [C.xy(p) for p in e['geometry']]
        self.ways = ways
        g = lambda i: [tuple(map(float, p)) for p in ways[i]]
        enc = g(W_FENCE_ENC) + g(W_FENCE_ENC2)[1:]
        self.enc_line = enc                                    # 石柵(湯畑の床を囲む)
        edo = g(W_FENCE_EDECK_OUT)
        nf = g(W_FENCE_N)[::-1]
        wf = g(W_FENCE_W)[::-1]
        # 穴(地形を抜いて湯畑側で作る範囲)の外形。区間ごとに種類を付ける。
        pieces = [
            ('balustrade', enc),
            ('opening', [enc[-1], edo[0]]),     # 東の階段(898032023)の上り口
            ('woodrail', edo),
            ('opening', [edo[-1], nf[0]]),
            ('woodrail', nf),
            ('opening', [nf[-1], wf[0]]),
            ('guard', wf),
            ('opening', [wf[-1], enc[0]]),
        ]
        ring, kinds = [], []
        for k, pts in pieces:
            for i in range(len(pts) - 1):
                ring.append(pts[i]); kinds.append(k)
        # 最初の区間(北西の入口の脇)だけ柵がある。開口の区間は柵を立てない
        self.hole = ring                    # ccw(西を南へ、東を北へ)
        self.hole_kind = kinds              # 区間 i = ring[i] -> ring[i+1]
        if C.poly_area(self.hole) < 0:
            raise RuntimeError('hole ring must be ccw')
        self.pool_s = C.ccw(C.clean_ring(g(W_POND_S)))
        self.pool_n = C.ccw(C.clean_ring(g(W_POND_N)))
        tr = [g(i) for i in W_TROUGHS]
        # 南西(源泉の池側)を始点に
        self.troughs = [(np.array(t[0]), np.array(t[-1])) if t[0][1] < t[-1][1] else (np.array(t[-1]), np.array(t[0])) for t in tr]
        self.troughs.sort(key=lambda ab: ab[0][0])            # 西から東へ
        a0 = np.mean([t[0] for t in self.troughs], axis=0)
        a1 = np.mean([t[1] for t in self.troughs], axis=0)
        self.tr_a0, self.tr_a1 = a0, a1
        self.tr_len = float(np.hypot(*(a1 - a0)))
        self.tr_u = (a1 - a0) / self.tr_len
        self.collect = g(W_COLLECT)
        self.drain = g(W_DRAIN)
        self.stream = g(W_STREAM)
        self.steps_w = g(W_STEPS_W)          # [(4.6,27.8) 下, (-6.3,12.9) 上]
        self.steps_ne = g(W_STEPS_NE)
        self.steps_e = g(W_STEPS_E)          # [(23.6,23.8) 下, (21.7,16.4) 上]
        self.fence_edeck_in = g(W_FENCE_EDECK_IN)
        self.fence_pond_n = g(W_FENCE_POND_N)
        loop = C.clean_ring(g(W_LOOP))
        self.loop = C.ccw(loop)
        self.loop_out = offset_ring(self.loop, 3.0)      # 車道の外の縁(車道の半幅 3 m)
        self.loop_in = offset_ring(self.loop, -3.0)
        self.cliff = CLIFF
        self.edeck = EDECK

    # ------------------------------------------------ 高さ
    def tr_s(self, x, y):
        """湯樋の軸に沿った距離(南の始まり=0)。"""
        return (np.asarray(x) - self.tr_a0[0]) * self.tr_u[0] + (np.asarray(y) - self.tr_a0[1]) * self.tr_u[1]

    def trough_bottom(self, s):
        return TR_Z0 - TR_DROP * np.asarray(s, float)

    def in_hole(self, x, y, dilate=0.0):
        x = np.asarray(x, float); y = np.asarray(y, float)
        m = inside(x, y, self.hole)
        if dilate > 0:
            m = m | (seg_nearest(x, y, self.hole, closed=True)[0] < dilate)
        return m

    def low_side(self, x, y):
        """崖の線より北(低い側)なら正。"""
        return side_of(x, y, self.cliff) > 0   # 崖の線は西→東に引いてあるので、左(北)が正

    def bed(self, x, y):
        """湯畑の床(樋の下の砂利・岩)の高さ。"""
        s = self.tr_s(x, y)
        L = self.tr_len
        b = self.trough_bottom(np.clip(s, 0, L)) - POST_H
        b = b - 0.25 * C.smoothstep((s - L) / 8.0)          # 樋の先(湯滝へ向かう岩場)は少し下がる
        n = C.vnoise(x, y, 1.7, 5) - 0.5
        return b + 0.10 * n

    def interior(self, x, y):
        """穴の中の地面の高さ(Blender Z)と区分(0=床 1=源泉の池 2=低い通路 3=滝壺 4=東デッキの下 5=流れ)。"""
        x = np.asarray(x, float); y = np.asarray(y, float)
        z = self.bed(x, y)
        kind = np.zeros(x.shape, int)
        # 源泉の池と縁の岩の盛り上がり
        dps = sdist(x, y, self.pool_s)
        z = np.where(dps < 0, POOL_S_FLOOR + 0.25 * C.smoothstep(1 - (-dps) / 2.5), z)
        lev = (dps >= 0) & (dps < 1.6)
        z = np.where(lev, np.maximum(z, POOL_S_WATER + 0.12 - 0.9 * C.smoothstep(dps / 1.6)), z)
        kind = np.where(dps < 0, 1, kind)
        # 樋の先から崖へ流れる白い湯の筋(浅い溝)
        flow = [(6.8, 19.1), (8.6, 20.2), (10.2, 21.6), (11.4, 23.0)]
        dfl = seg_nearest(x, y, flow)[0]
        z = np.where(dfl < 0.9, z - 0.10 * (1 - dfl / 0.9), z)
        kind = np.where((dfl < 0.55) & (kind == 0), 5, kind)
        # 崖より北(低い側)
        low = self.low_side(x, y)
        dpn = sdist(x, y, self.pool_n)
        zl = np.full(x.shape, LOW_Z) + 0.03 * (C.vnoise(x, y, 0.9, 8) - 0.5)
        zl = np.where(dpn < 0, BASIN_WATER - 0.15 + (BASIN_FLOOR - BASIN_WATER + 0.15) * C.smoothstep(-dpn / 2.2), zl)
        ed = inside(x, y, self.edeck)
        zl = np.where(ed & (dpn >= 0), -3.2 + 0.25 * (C.vnoise(x, y, 2.0, 9) - 0.5), zl)
        kl = np.where(dpn < 0, 3, np.where(ed, 4, 2))
        z = np.where(low, zl, z)
        kind = np.where(low, kl, kind)
        return z, kind
