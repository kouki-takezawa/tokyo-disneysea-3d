# -*- coding: utf-8 -*-
"""kd_zone_B.py -- 草津 湯畑ジオラマ フェーズ6: 区域B(湯畑の西〜南西と北)の建物を BuildingSpec で 1 棟ずつ作る。

区域B = kd_common.zone_of が 'B' を返す範囲(x < -25 かつ -80 <= y <= 15、または x >= -25 かつ 25 < y <= 70)。OSM 41 外形。
- 手作り(カード+動画フレーム): 御座之湯(試作のコピー)、熱乃湯+観光案内所、白旗の湯+格子の小塔、白旗源泉の屋根、草津館(東の棟+西の棟)、
  ホテル一井 本館(古典風の 2 階の基壇+白い 6 階の塔)、セブン-イレブン、黄土色の宿(セブンの北西隣)、大東館の階段室(relation の小片)、
  湯路広場の木のアーケード(OSM に外形が無いので歩道 955567265 に沿わせた。門+3 区間)。
- 推定(動画で確認できない棟): OSM の外形+階数(タグ>面積・通りの様式)+様式(_generic)。看板は枠だけ・文字なし。
- 山本館・益成屋(B_yamamotokan / B_masunariya のカード)は区域C のカードが正なので使わない(外形も区域C)。
- ホテル一井 別館(954965075)は重心が区域C なので区域C(フェーズ7)で作る。

実行(他タブの Blender が動いていないことを tasklist で確認して 1 つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_zone_B.py      # buildings_B.glb だけ
  python kusatsu/kd_zone_B.py --count     # Blender 無しで三角形数(1 棟ごと)
  python kusatsu/kd_zone_B.py --list      # 1 棟ごとの階数・屋根・様式・根拠(phase6_notes 用)
地形(敷地の均し)を変えたときは kd_terrain.py -- --zones=B で terrain.glb と buildings_B.glb を作り直す。
"""
import math
import os
import sys
import zlib
from dataclasses import replace as dreplace

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import kd_common as C  # noqa: E402
import kd_parts as P  # noqa: E402
import kd_zone_A as ZA  # noqa: E402  (site/base_for/cut/nearest_road と、Builder の zA_open・zA_round を使う)
from kd_parts import (BuildingSpec, WallFinish, Timber, Facade, Balcony, Pent, Roof, Attach, Wall, lin, tint)  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]

DARK = '#2b2420'
site, base_for, cut, ring_of, bld, uvec, bearing = ZA.site, ZA.base_for, ZA.cut, ZA.ring_of, ZA.bld, ZA.uvec, ZA.bearing


def get_field():
    return ZA.get_field()


def set_field(field):
    ZA.set_field(field)


# ====================================================================== 補助
def face_z(ring, front, off=1.0, n=7):
    """外形の最小矩形の、方位 front に最も近い辺の外 off m の地面の高さ(中央値)。正面の向きを自分で決めた棟の 1 階の床の基準。"""
    F = get_field()
    (cx, cy), ang, L, W = P.obb(ring)
    u = np.array([math.cos(ang), math.sin(ang)])
    v = np.array([-u[1], u[0]])
    fv = uvec(front)
    c = max([u, -u, v, -v], key=lambda d: float(d @ fv))
    lf = abs(float(c @ u)) < 0.5
    half = (W / 2) if lf else (L / 2)
    along = (L if lf else W)
    tv = np.array([-c[1], c[0]])
    ss = np.linspace(-along / 2 + 0.6, along / 2 - 0.6, n)
    fx = cx + c[0] * (half + off) + tv[0] * ss
    fy = cy + c[1] * (half + off) + tv[1] * ss
    return float(np.median(F.Z(fx, fy)))


def rect(c, axis_deg, length, width):
    """中心 c、長辺の方位 axis_deg の矩形(反時計回り)。"""
    u = uvec(axis_deg)
    v = np.array([-u[1], u[0]])
    c = np.asarray(c, float)
    pts = [c - u * length / 2 - v * width / 2, c + u * length / 2 - v * width / 2, c + u * length / 2 + v * width / 2, c - u * length / 2 + v * width / 2]
    return C.ccw([tuple(map(float, p)) for p in pts])


def proj(ring, deg):
    d = uvec(deg)
    return np.array(ring, float) @ d


# ====================================================================== 部品の追加(区域B の spec に印がある時だけ効く)
def _zB_open_walls(self):
    """柱だけの建物(アーケード・源泉の屋根): 外形の辺に沿って柱(沓石つき)と桁、妻側に繋ぎ梁。"""
    pb, lod = self.pb, self.lod
    self.edge_ops = {}
    ring = self.rings[0]
    z1 = self.ztop
    col = lin(getattr(self.spec, 'zB_post_col', '#d2ad7c'))
    stone = lin('#9c9890')
    pitch = getattr(self.spec, 'zB_pitch', 3.5)
    for i in range(len(ring)):
        W = Wall(ring[i], ring[(i + 1) % len(ring)])
        if W.L < 0.3:
            continue
        n = max(1, int(round(W.L / pitch)))
        for j in range(n):
            sj = W.L * j / n
            zg = self.ground(*W.P(sj + 0.1, 0, -0.1)[:2])
            W.box(pb, 'wood', sj + 0.0, sj + 0.2, zg + 0.18, z1, -0.2, 0.0, col, skip=('-z',))
            if lod >= 1:
                W.box(pb, 'stone', sj - 0.08, sj + 0.28, zg - 0.1, zg + 0.18, -0.28, 0.08, stone, skip=('-z',))
            if lod >= 2:     # 方杖(柱から桁へ)
                for sd in ((0.2, 0.75), (0.0, -0.55)):
                    if 0.0 < sj + sd[1] < W.L:
                        W.beam(pb, 'wood', (sj + sd[0], z1 - 0.75, -0.1), (sj + sd[0] + sd[1], z1 - 0.2, -0.1), 0.1, 0.1, col)
        W.box(pb, 'wood', 0.0, W.L, z1 - 0.26, z1, -0.22, 0.02, tint(col, 0.94), skip=())


def _zB_truss(self, info):
    """柱だけの建物の切妻の妻と小屋組: 妻は開けたまま、柱筋ごとに陸梁+束+登り梁、棟木、化粧垂木(lod2)。"""
    pb, lod = self.pb, self.lod
    fr = info['fr']
    zt = self.ztop
    R = self.spec.roof
    col = lin(getattr(self.spec, 'zB_post_col', '#d2ad7c'))
    hx, hy, s = fr.hx, fr.hy, R.slope
    zr = zt + hy * s - self.rthick(R) - 0.05
    pitch = getattr(self.spec, 'zB_pitch', 3.5)
    n = max(1, int(round(2 * hx / pitch)))
    for j in range(n + 1):
        x = -hx + 2 * hx * j / n
        x = min(max(x, -hx + 0.1), hx - 0.1)
        P.beam(pb, 'wood', fr.P(x, -hy, zt - 0.05), fr.P(x, hy, zt - 0.05), 0.14, 0.24, col)
        P.beam(pb, 'wood', fr.P(x, 0, zt - 0.05), fr.P(x, 0, zr), 0.14, 0.14, col)
        for sg in (1, -1):
            P.beam(pb, 'wood', fr.P(x, sg * hy, zt), fr.P(x, 0, zr), 0.12, 0.2, tint(col, 1.04))
    P.beam(pb, 'wood', fr.P(-hx - 0.3, 0, zr), fr.P(hx + 0.3, 0, zr), 0.16, 0.2, col)
    if lod >= 2:
        for x in np.arange(-hx, hx + 0.01, 0.6):
            for sg in (1, -1):
                P.beam(pb, 'wood', fr.P(x, sg * (hy + R.eave * 0.9), zt - R.eave * 0.9 * s - 0.12), fr.P(x, 0, zr - 0.02), 0.06, 0.08,
                       tint(col, 1.08), skip=('+z',))


def att_zB_slats(self, A):
    """縦格子の板壁(アーケードの側面・塀): 辺の s〜s+w に細い縦材を 0.15 m おきに、上下に貫。"""
    pb, lod = self.pb, self.lod
    W, s, k = self.attach_wall(A)
    w = A.w or 3.0
    h = A.h or 2.4
    d = A.d if A.d is not None else -0.1
    col = lin(A.color or '#d8b88a')
    s0, s1 = max(0.25, s), min(W.L - 0.25, s + w)
    if s1 - s0 < 0.3:
        return
    zg0 = self.ground(*W.P(s0, 0, d)[:2])
    zg1 = self.ground(*W.P(s1, 0, d)[:2])
    if lod == 0:
        pb.poly('wood', [W.P(s0, zg0 + 0.1, d), W.P(s1, zg1 + 0.1, d), W.P(s1, zg1 + h, d), W.P(s0, zg0 + h, d)], col, W.nrm())
        return
    step = A.prm.get('step', 0.15)
    for sx in np.arange(s0, s1, step):
        zg = zg0 + (zg1 - zg0) * (sx - s0) / max(s1 - s0, 1e-6)
        W.box(pb, 'wood', sx, sx + 0.07, zg + 0.1, zg + h, d - 0.05, d + 0.05, P.hj(col, 0.04, int(sx / step)), skip=('-z', '+z'))
    for zz in (0.15, h - 0.12):
        W.beam(pb, 'wood', (s0, zg0 + zz, d), (s1, zg1 + zz, d), 0.12, 0.14, tint(col, 0.92))


def att_zB_cloth(self, A):
    """幕(白旗源泉の白い布): 辺の前に垂れる布 1 枚(上は竿、下はゆるいたるみ)。"""
    pb = self.pb
    W, s, k = self.attach_wall(A)
    w = A.w or 3.0
    h = A.h or 0.8
    d = A.d if A.d is not None else 0.1
    zt = self.zs[0] + (A.z if A.z is not None else self.fh[0] - 0.2)
    c = lin(A.color or '#f2f0ea')
    n = 8
    pts_top = [W.P(s - w / 2 + w * j / n, zt, d) for j in range(n + 1)]
    pts_bot = [W.P(s - w / 2 + w * j / n, zt - h - 0.18 * math.sin(math.pi * j / n), d + 0.02) for j in range(n + 1)]
    for j in range(n):
        pb.poly('fabric', [pts_bot[j], pts_bot[j + 1], pts_top[j + 1], pts_top[j]], c, W.nrm())
        pb.poly('fabric', [pts_bot[j + 1], pts_bot[j], pts_top[j], pts_top[j + 1]], tint(c, 0.85), W.nrm(-1))
    W.beam(pb, 'wood', (s - w / 2 - 0.1, zt + 0.03, d), (s + w / 2 + 0.1, zt + 0.03, d), 0.05, 0.05, lin('#6b4a33'))


_PREV_WALLS = P.Builder.walls          # kd_zone_A の差し替え(zA_open)を含む
_PREV_GFILL = P.Builder.gable_fill


def _walls_B(self):
    if getattr(self.spec, 'zB_open', False):
        return _zB_open_walls(self)
    return _PREV_WALLS(self)


def _gable_fill_B(self, info):
    if getattr(self.spec, 'zB_open', False):
        return _zB_truss(self, info)
    return _PREV_GFILL(self, info)


P.Builder.walls = _walls_B
P.Builder.gable_fill = _gable_fill_B
P.Builder.att_zB_slats = att_zB_slats
P.Builder.att_zB_cloth = att_zB_cloth


# ====================================================================== 手作り(カードあり)
def otonoyu():
    """御座之湯(954786837、B_otonoyu、Y 2:24 f_049 / R 20:21 f_408 / R 18:18 f_367): kd_parts_test.otonoyu() のコピー。
    1 階の床を正面(北東)の広場の高さ+0.55(玄関の石段 3〜4 段)に合わせた(試作は敷地の平均)。"""
    fac = Facade(bay=1.8, margin=0.3, ground='L', win='R', frame='wood', glass='#647f8f', lattice_col='#6b4428',
                 sizes={'R': (None, 1.75, 0.65), 'L': (1.4, 1.2, 0.9)})
    ring = ring_of('954786837')
    return BuildingSpec(
        id='954786837', name='御座之湯', zone='B', floors=2, floor_h=[3.6, 3.5], found_h=0.55, found='stone', found_col='#8a867e', front=58,
        base_z=face_z(ring, 58) + 0.55,
        walls={1: WallFinish('board_v', '#b4703e', pitch=0.9, koshi=(0.8, 'board_h', '#6b4a33')), 2: WallFinish('board_h', '#b97543', pitch=0.22)},
        facades={'front': fac, 'back': dreplace(fac, ground='.L.', win='W.', lod=1), '*': dreplace(fac, ground='.L..L.')},
        setbacks={2: {'front': -0.6, 'left': -0.4, 'right': -0.4}},
        pents=[Pent(1, side=['front', 'left', 'right'], depth=1.5, slope=0.3, z=3.25, mat='tonton')],
        roof=Roof('irimoya', 'tonton', slope=0.55, eave=1.1, verge=0.5, irimoya_k=0.5, gable_style='timber', gable_col='#efebe2',
                  hafu_col='#6b4a33', soffit_col='#c08a5c', gutters=False, color='#80786d'),
        attach=[
            Attach('porch', side='front', at=0.5, w=3.8, d=2.6, h=3.0, color='#7d7569', color2='#8a5a36',
                   prm=dict(roof='gable', mat='tonton', slope=0.55, noren='#f0ede4', noren_w=2.6, noren_h=1.05, lanterns=['#f3efe6', '#f3efe6'],
                            post_mat='wood', gable_col='#6b4a33', kengyo=False)),
            Attach('sign', side='front', at=0.5, floor=1, z=3.05, d=2.55, w=1.9, h=0.42, style='yoko', color='#c08a4a', color2='#6b4a33', text='御座之湯'),
            Attach('ac', side='back', n=2, w=1.1),
        ],
        lod=2, age=0.25, note='試作のコピー。裏(南西)は動画に出ないので推定(窓は同じ規則)')


def atsunoyu():
    """熱乃湯(954629638、B_atsunoyu、K 7:57 f_160 / Y 1:51 f_038 / Y 1:54 f_039): 2 階+屋根裏、灰青の下見板に濃い灰青の付け柱、
    1 階の半円アーチ窓と細かい格子の縦長窓、東(湯畑側)に妻を向けた大きな切妻と 2 階の開いた縁(白い手すり)、2 階の東面は赤茶の板、
    棟の北寄りにルーバーの越屋根。南東の小さな出っ張りは観光案内所(別 spec)。"""
    # 南東の角(観光案内所)を外す: 南端から 5.2 m の帯のうち東 5.6 m
    rest = _atsu_split()[0]
    s = site('954629638', rest)
    grey = '#a7b2b1'
    pil = Timber('#62717a', w=0.22, proud=0.05, posts='bay', beams=('bottom', 'top'))
    fac_s = Facade(bay=2.3, margin=0.4, pattern={1: 'A.LDL.A', 2: '.T..T..'}, frame='white', glass='#9fb4ad', trim=True,
                   lattice_col='#d7ddd6', sizes={'A': (1.25, 3.0, 0.45), 'L': (1.1, 1.6, 0.9), 'T': (0.8, 1.35, 0.7), 'D': (1.6, 2.6, 0.0)})
    fac_e = Facade(bay=2.2, margin=0.5, pattern={1: 'AA.G.AA', 2: 'TTTT'}, frame='white', glass='#9fb4ad', trim=True,
                   sizes={'A': (1.05, 2.9, 0.45), 'G': (2.2, 2.7, 0.0), 'T': (0.8, 1.35, 0.7)})
    return BuildingSpec(
        id='954629638', name='熱乃湯', zone='B', ring=rest, floors=2, floor_h=[4.2, 3.8], base_z=base_for(s, 0.15), front=112,
        replaces=['954629638'],
        walls={1: WallFinish('board_h', grey, pitch=0.2, timber=pil), '*': WallFinish('board_h', '#a9b0ae', pitch=0.2, timber=pil)},
        side_walls={'front': {2: WallFinish('board_v', '#7d5747', pitch=0.3, timber=Timber('#5b4034', w=0.18, posts='bay', beams=('bottom', 'top')))}},
        facades={'front': fac_e, 'S': fac_s, 'SSE': fac_s,
                 '*': Facade(bay=2.4, pattern={1: '.L.L.', 2: '.T.T.'}, frame='white', glass='#9fb4ad', lattice_col='#d7ddd6', trim=True, lod=1,
                             sizes={'L': (1.1, 1.6, 0.9), 'T': (0.8, 1.35, 0.7)})},
        balconies=[Balcony(2, 'front', depth=1.1, rail='lattice', color='#e3e2da', rail_h=1.0, s0=1.2, s1=-1.2),
                   Balcony(2, ['S', 'SSE'], depth=0.7, rail='lattice', color='#e3e2da', s0=0.8, s1=-6.0)],
        pents=[Pent(1, side='*', depth=0.95, slope=0.32, mat='kawara', color='#55504b', z=4.0)],
        roof=Roof('gable', 'kawara', slope=0.62, eave=0.7, verge=0.55, axis=24, color='#5a4d46', hafu_col='#4f4a46', soffit_col='#b9b4a9',
                  chidori=[(0.25, 8.5, 1)], gutters=False),
        attach=[Attach('cupola', prm=dict(u=4.5, v=0.0, roof='hip', slope=0.55), w=2.6, d=2.6, h=2.2, color='#8d8278', color2='#5a4d46'),
                Attach('sign', side=['S', 'SSE'], floor=1, s=7.0, z=3.15, w=2.2, h=0.6, style='yoko', color='#d9a54a', color2='#5a4636', text='熱乃湯'),
                Attach('sign', side='front', floor=2, z=3.0, w=2.0, h=0.55, style='yoko', color='#c99a52', color2='#5a4636'),
                Attach('ac', side='back', n=2, w=1.2), Attach('pipe', side='back', s=1.0)],
        lod=2, age=0.3,
        note='東の大きな妻は千鳥破風、越屋根は cupola。東面 2 階の額は読めないので文字なし(Y 1:51)')


ATSU_U, ATSU_E, ATSU_DU, ATSU_DE = 24.0, 114.0, 5.2, 5.6     # 熱乃湯の長辺の方位、東の方位、案内所の角の大きさ(南から m、東から m)


def _atsu_split():
    """熱乃湯の外形 -> (本体=南東の角を切り取った多角形, 観光案内所=南東の角)。"""
    ring = ring_of('954629638')
    u, e = uvec(ATSU_U), uvec(ATSU_E)
    ucut = float(proj(ring, ATSU_U).min()) + ATSU_DU
    ecut = float(proj(ring, ATSU_E).max()) - ATSU_DE
    south = cut(ring, u * ucut, u, -1)
    info = cut(south, e * ecut, e, 1)
    a = u * ucut + e * ecut                     # 2 本の切り線の交点(u と e は直交)
    return _replace_corner(ring, a, ucut, ecut), info


def _replace_corner(ring, a, ucut, ecut):
    """外形から「u < ucut かつ e > ecut」の角を切り取った多角形(切り口は交点 a を通る 2 本の直線)。"""
    u, e = uvec(ATSU_U), uvec(ATSU_E)
    out = []
    n = len(ring)
    R = [np.array(p, float) for p in ring]
    inside = [(float(p @ u) < ucut and float(p @ e) > ecut) for p in R]

    def fu(p):
        return float(p @ u) - ucut          # 負=角の側

    def fe(p):
        return ecut - float(p @ e)          # 負=角の側
    for i in range(n):
        p, q = R[i], R[(i + 1) % n]
        if not inside[i]:
            out.append(tuple(p))
        if inside[i] == inside[(i + 1) % n]:
            continue
        ts = []
        for f in (fu, fe):
            fp, fq = f(p), f(q)
            if (fp < 0) != (fq < 0):
                ts.append(fp / (fp - fq))
        if not ts:
            continue
        t = max(ts) if not inside[i] else min(ts)     # 入る時は最後に満たす条件、出る時は最初に破る条件
        x = p + (q - p) * t
        if inside[i]:
            out.append(tuple(a))
        out.append(tuple(x))
    return C.ccw(C.clean_ring(out))


def kankou():
    """観光案内所(熱乃湯の南東の角、B_atsunoyu、K 8:03 f_162 / Y 1:54 f_039): 平屋、妻を東に向けた小さな切妻・深い軒、灰青の板、
    窓口のガラスと掲示板、木の額「観光案内所」。"""
    ring = _atsu_split()[1]
    s = site('954629638', ring)
    return BuildingSpec(
        id='954629638#kankou', name='観光案内所', zone='B', ring=ring, use_obb=True, floors=1, floor_h=3.0, base_z=base_for(s, 0.15), front=112,
        replaces=[],
        walls={'*': WallFinish('board_v', '#a3aeae', pitch=0.3, timber=Timber('#5f6d75', w=0.18, posts='ends', beams=('bottom', 'top')))},
        facades={'front': Facade(bay=1.4, margin=0.35, pattern={1: 'GWW'}, frame='white', glass='#5d6b70', sizes={'W': (1.2, 1.5, 0.9), 'G': (1.1, 2.3, 0.0)}),
                 'S': Facade(bay=1.4, pattern={1: '.W.'}, frame='white', glass='#5d6b70', sizes={'W': (1.4, 1.4, 0.9)}),
                 '*': Facade(pattern={1: '..'}, lod=0)},
        roof=Roof('gable', 'kawara', slope=0.55, eave=1.15, verge=0.9, axis=112, color='#5d5550', hafu_col='#4f4a46', soffit_col='#c9c3b6',
                  gutters=False),
        attach=[Attach('sign', side='front', floor=1, z=2.55, w=2.2, h=0.4, style='yoko', color='#d9a54a', color2='#5a4636', text='観光案内所'),
                Attach('box', side='front', s=-0.6, z=0.4, w=0.9, h=1.2, d=0.12, color='#2f4d6b', prm=dict(dep=0.1))],
        lod=2, age=0.3, note='OSM では熱乃湯の外形の南東の角(位置は Y 1:54 の並びから)')


def shirahata():
    """白旗の湯(954786834、B_shirahata、Y 1:54 f_039 / Y 2:03 f_042 / R 20:00 f_401): 平屋の高い木造(屋根裏)、濃茶の横板、
    灰黒の瓦の入母屋、東の玄関に向拝風の切妻(乳白の妻、白い無地の暖簾、木の縁)、板額「白旗乃湯」(2 字目は確度 中)。"""
    s = site('954786834')
    return BuildingSpec(
        id='954786834', name='白旗の湯', zone='B', floors=1, floor_h=4.6, base_z=base_for(s, 0.3), front=114, found='stone', found_h=0.3,
        found_col='#8c887f',
        walls={'*': WallFinish('board_h', '#4a3426', pitch=0.24, timber=Timber('#2e221b', w=0.15, posts='bay', beams=('bottom', 'top', 'head')))},
        facades={'front': Facade(bay=1.6, margin=0.3, pattern={1: 'L.D.L'}, frame='wood', glass='#e6dfc9', lattice_col='#2e221b',
                                 sizes={'L': (1.2, 1.1, 1.0), 'D': (1.8, 2.2, 0.0)}),
                 '*': Facade(bay=2.0, pattern={1: '.L.'}, frame='wood', glass='#e6dfc9', lattice_col='#2e221b', lod=1, sizes={'L': (1.1, 0.9, 1.6)})},
        roof=Roof('irimoya', 'kawara', slope=0.62, eave=0.85, verge=0.45, irimoya_k=0.55, color='#3b3d40', hafu_col='#3a2a20',
                  gable_style='lattice', gable_col='#ece6d8', soffit_col='#6b4f3a', kengyo=True),
        attach=[Attach('porch', side='front', at=0.5, w=3.0, d=2.1, h=2.85, color='#3e4043', color2='#4a3426',
                       prm=dict(roof='gable', mat='kawara', slope=0.6, noren='#f2f0ea', noren_w=1.9, noren_h=1.0, post_mat='wood',
                                gable_col='#ece6d8', kengyo=True)),
                Attach('sign', side='front', at=0.5, floor=1, z=3.1, d=2.15, w=1.5, h=0.38, style='yoko', color='#7a3a2a', color2='#3a2a20',
                       text='白旗乃湯'),
                Attach('box', side='front', s=-0.9, z=1.0, w=0.4, h=0.5, d=0.2, color='#c8a35a', prm=dict(dep=0.18))],
        lod=2, age=0.35, note='額の 2 字目(乃/の)は確度 中。小塔は別 spec(shirahata_tower)')


def shirahata_tower():
    """白旗の湯の南西の格子の小塔(B_shirahata、Y 1:54 f_039 左上、R 20:00 f_401 中央): 黒い井桁の格子に黄みの障子、3 層、小さな寄棟の瓦。
    OSM に外形が無いので白旗の湯の外形の南西角の内側に 3.2 m 角で置いた(帰属は未確定)。"""
    ring = ring_of('954786834')
    a, b = np.array((-42.3, -45.5)), np.array((-49.0, -42.6))         # 白旗の湯の南の辺
    t = (b - a) / np.linalg.norm(b - a)
    inward = np.array([-t[1], t[0]])
    if float(inward @ (np.array(P.obb(ring)[0]) - a)) < 0:
        inward = -inward
    c = a + t * 3.6 + inward * 1.9
    r = rect(c, bearing(t), 3.2, 3.2)
    s = site('954786834')
    grid = Timber('#1c1a19', w=0.12, proud=0.04, posts=0.55, beams=('bottom', 'top', 0.7, 1.4, 2.1))
    return BuildingSpec(
        id='954786834#tower', name='白旗の湯の格子の小塔', zone='B', ring=r, floors=3, floor_h=[3.0, 2.7, 2.7], base_z=base_for(s, 0.3),
        front=114, replaces=[], found='none',
        walls={1: WallFinish('board_h', '#4a3426', pitch=0.24), '*': WallFinish('paint', '#e3cf8e', timber=grid)},
        facades={'*': Facade(pattern={1: '.', 2: '.', 3: '.'}, lod=1)},
        pents=[Pent(2, side='all', depth=0.45, slope=0.4, mat='kawara', color='#3b3d40', z=2.65)],
        roof=Roof('hip', 'kawara', slope=0.6, eave=0.6, color='#3b3d40', hafu_col='#2e221b', soffit_col='#3a2a20', gutters=False),
        lod=2, age=0.3, note='位置は推定(Y 1:54 と R 20:00 の並びで白旗の湯の南西)')


def shirahata_gensen():
    """白旗源泉の屋根(955804968、building=roof、Y 2:24 f_049 / R 20:12 f_405): 木の柱の切妻の差し掛け屋根(灰茶の板葺き)、
    木の額「白旗源泉」、白い幕(中央に「白旗」)、軒の白い提灯、柱の間の低い格子。"""
    ring = ring_of('955804968')
    s = site('955804968')
    sp = BuildingSpec(
        id='955804968', name='白旗源泉の屋根', zone='B', floors=1, floor_h=2.75, base_z=base_for(s, 0.0), front=153, found='none',
        walls={'*': WallFinish('board_v', '#8a6a4a')},
        facades={'*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('gable', 'tonton', slope=0.62, eave=0.9, verge=0.8, axis=333, color='#867c70', hafu_col='#7a5a3e', soffit_col='#a9865f',
                  gutters=False, oni=False),
        attach=[Attach('sign', side='front', floor=1, z=2.55, w=1.9, h=0.42, style='yoko', color='#9a7650', color2='#5a4030', text='白旗源泉', d=0.95),
                Attach('zB_cloth', side='front', z=2.45, w=3.6, h=0.75, d=0.95, color='#f2f0ea', text='白旗'),
                Attach('lanterns', side='front', floor=1, z=2.3, d=1.0, n=3, w=4.6, color='#f3efe6'),
                Attach('zB_slats', side='back', s=0.3, w=6.8, h=1.0, d=-0.1, color='#8a6a4a', prm=dict(step=0.22))],
        lod=2, age=0.4, note='正面は広場側(南東)。石で囲った細長い湯だまりは作っていない(地形側の小物、フェーズ9)')
    sp.zB_open, sp.zB_post_col, sp.zB_pitch = True, '#8a6a4a', 3.6
    return sp


def kusatsukan():
    """草津館(954786833、R 20:12 f_405 / R 20:00 f_401 の白い真壁の 3 階+妻): 白漆喰に黒い化粧柱梁、妻を南南西(湯路広場・石段側)に向けた切妻、
    妻に看板(文字は読めない)、南東の長辺に瓦の下屋の玄関。外形は東の棟(23x11 m)と西の棟(10x10 m)に分けた。
    カード B_kusatsukan の「黄土色の 5 階」は R 18:15〜18:18(f_366/367)で石段の脇(区域D 側)の建物と分かったので使わない。"""
    ring = ring_of('954786833')
    v = uvec(114)
    p0 = v * (-40.0)
    east = cut(ring, p0, v, 1)
    west = cut(ring, p0, v, -1)
    tim = Timber('#1f1c1a', w=0.15, posts='bay', beams=('bottom', 'top', 'head', 'sill'))
    se = site('954786833', east)
    zf = face_z(east, 114)
    main = BuildingSpec(
        id='954786833', name='草津館', zone='B', ring=east, use_obb=True, floors=3, floor_h=[3.3, 2.9, 2.9], base_z=zf + 0.2, front=114,
        replaces=['954786833'],
        walls={1: WallFinish('plaster', '#efede6', timber=tim, koshi=(0.9, 'board_v', '#3a2a20')), '*': WallFinish('plaster', '#f0eee8', timber=tim)},
        facades={'front': Facade(bay=2.1, margin=0.4, pattern={1: 'W.GDG.W.W', 2: 'W.W.W.W.W', 3: 'W.W.W.W.W'}, frame='black', glass='#38424a',
                                 sizes={'W': (1.6, 1.3, 0.75)}),
                 'SSW': Facade(bay=2.0, pattern={1: '.W.W.', 2: '.WW.', 3: '.WW.'}, frame='black', glass='#38424a', sizes={'W': (1.5, 1.3, 0.75)}),
                 '*': Facade(bay=2.4, win='W.', ground='.W', frame='black', glass='#38424a', lod=0)},
        pents=[Pent(1, 'front', depth=0.9, slope=0.35, mat='kawara', color='#3e4044', z=3.05), Pent(2, ['front', 'SSW'], depth=0.5, slope=0.35,
                                                                                                   mat='kawara', color='#3e4044', z=2.7)],
        roof=Roof('gable', 'kawara', slope=0.55, eave=0.7, verge=0.6, axis=24, color='#4a4c50', hafu_col='#1f1c1a', soffit_col='#e8e4da',
                  gable_window=True),
        attach=[Attach('porch', side='front', at=0.42, w=3.6, d=2.4, h=3.0, color='#3e4044', color2='#2e2420',
                       prm=dict(roof='shed', mat='kawara', slope=0.3, platform=True)),
                Attach('sign', side='SSW', floor=3, z=3.4, w=2.2, h=0.6, style='flat', color='#f0eee8', color2='#1f1c1a'),
                Attach('lanterns', side='front', floor=1, z=2.85, d=0.85, n=4, w=8.0, color='#f3efe6'),
                Attach('ac', side='back', n=3, w=1.2), Attach('pipe', side='back', s=1.5)],
        lod=2, age=0.35, note='同定は位置から(R 20:12 の正面の白い真壁の棟)。妻の看板は判読不能なので文字なし')
    sw = site('954786833', west)
    wing = BuildingSpec(
        id='954786833#west', name='草津館 西の棟(推定)', zone='B', ring=west, floors=3, floor_h=[3.2, 2.9, 2.9], base_z=max(sw['z_front'], zf) + 0.2,
        front=294, replaces=[], same_level=False,
        walls={'*': WallFinish('plaster', '#ecebe5', timber=Timber('#2a2420', w=0.14, posts='bay', beams=('bottom', 'top')))},
        facades={'*': Facade(bay=2.4, win='W.', ground='.W', frame='black', glass='#3a444c', lod=0)},
        roof=Roof('hip', 'kawara', slope=0.5, eave=0.6, color='#4a4c50', hafu_col='#1f1c1a'),
        attach=[Attach('ac', side='*', n=2, w=1.2)], lod=1, age=0.4)
    return [main, wing]


def ichii():
    """ホテル一井 本館(605546948、B_hotel_ichii、R 1:18 f_027 / S 3:03 f_062 / R 20:12 f_405): 8 階。1〜2 階は古典風の白い基壇
    (付け柱・大きな窓・軒蛇腹・欄干)、3〜8 階は白い吹付の塔(基壇から 2.2 m 下がる、各階の細い帯と横に並ぶ小窓)、南端に「一井」の塔屋。"""
    ring = ring_of('605546948')
    s = site('605546948')
    base = base_for(s, 0.1)
    (cx, cy), ang, L, W = P.obb(ring)
    u = np.array([math.cos(ang), math.sin(ang)])
    south = -1.0 if u[1] > 0 else 1.0
    cream = '#e8e4d8'
    fac_b = Facade(bay=4.6, margin=0.8, pattern={1: 'G', 2: 'W'}, frame='dark', glass='#3b464d', fins=(0.75, 0.22), belt=True, trim=True,
                   sizes={'W': (3.0, 2.4, 1.0), 'G': (3.2, 3.3, 0.0)})
    base_spec_tower = BuildingSpec(
        id='605546948#tower', name='ホテル一井 本館 3〜8 階', zone='B', ring=P.offset_ring(ring, 2.2), floors=6, floor_h=3.1,
        base_z=base + 4.5 + 4.3, replaces=[], same_level=False, found='none',
        walls={'*': WallFinish('spray', '#f0efeb')},
        facades={'SE': Facade(bay=2.9, win='W', frame='alu', glass='#46525a', belt=True, sizes={'W': (1.7, 1.35, 0.85)}),
                 'NE': Facade(bay=2.9, win='W', frame='alu', glass='#46525a', belt=True, sizes={'W': (1.7, 1.35, 0.85)}),
                 '*': Facade(bay=3.0, win='W', frame='alu', glass='#46525a', lod=0)},
        roof=Roof('flat', parapet=0.9, coping_col='#d9d8d2', penthouse=[(south * (L / 2 - 6.0), 0.0, 4.0, 6.0, 4.2), (2.0, 2.0, 6.0, 5.0, 2.8)]),
        attach=[Attach('sign', side='SE', floor=6, s=(3.0 if south < 0 else -6.0), z=3.7, w=3.0, h=1.8, d=0.2, style='flat', color='#f4f3ef',
                       color2='#3a3a3a', text='一井'),
                Attach('ac', side='NW', floor=6, z=3.1, d=-2.0, n=4, w=2.0, prm=dict(mount='roof'))],
        lod=1, age=0.3)
    return BuildingSpec(
        id='605546948', name='ホテル一井 本館', zone='B', floors=2, floor_h=[4.5, 4.3], base_z=base, front=121,
        walls={'*': WallFinish('paint', cream)},
        facades={'SE': fac_b, 'NE': fac_b, '*': dreplace(fac_b, pattern={1: '.W', 2: 'W.'}, fins=None, lod=0)},
        balconies=[Balcony(2, ['SE', 'NE'], depth=0.45, z=4.3, rail='lattice', color='#f2f0ea', slab_color='#e3dfd3', rail_h=0.95, brackets=False,
                           ends=False, extend=0.45)],
        roof=Roof('flat', parapet=0.35, coping_col='#d6d2c6'),
        attach=[Attach('sign', side='SE', floor=1, s=4.0, z=3.4, w=0.5, h=2.4, style='tate', color='#d9a54a', color2='#3a2e26'),
                Attach('sign', side='NE', floor=1, s=3.0, z=3.5, w=2.2, h=0.45, style='yoko', color='#f2f0ea', color2='#3a3a3a', text='たばこ')],
        wings=[base_spec_tower], lod=1, age=0.3,
        note='基壇の欄干は 2 階の上の縁(lattice)、軒蛇腹は帯。塔は基壇から 2.2 m 内側(実物の段の幅は推定)')


def seven():
    """セブン-イレブン(954629632、B_seven_north、R 29:18 f_586 / S 3:03 f_062 / W 1:31 f_091): 2 階、1 階のガラスの店頭、
    2 階はクリームの吹付に横長の窓、濃灰の低い寄棟。正面は西の河原通りの入口の角(南西の短辺)と湯畑側(南東の長辺)。"""
    s = site('954629632')
    return BuildingSpec(
        id='954629632', name='セブン-イレブン', zone='B', floors=2, floor_h=[3.7, 3.0], base_z=base_for(s, 0.12), front=236, use_obb=True,
        walls={1: WallFinish('paint', '#3a3a3a'), '*': WallFinish('spray', '#e9e2cf')},
        facades={'front': Facade(bay=2.0, margin=0.3, pattern={1: 'GGG.', 2: '.RR.'}, frame='dark', glass='#5a6870', sizes={'G': (None, 2.6, 0.0)}),
                 'SE': Facade(bay=2.2, margin=0.3, pattern={1: 'GGGGG..', 2: '.RRRRR.'}, frame='dark', glass='#5a6870', sizes={'G': (None, 2.6, 0.0)}),
                 '*': Facade(bay=2.4, win='.W', ground='..', frame='alu', lod=0)},
        roof=Roof('hip', 'metal', slope=0.3, eave=0.6, color='#4d4f52', hafu_col='#3a3a3a', soffit_col='#e9e2cf'),
        attach=[Attach('sign', side='front', floor=1, z=3.0, w=4.6, h=0.55, style='yoko', color='#f4f2ec', color2='#e8762b', text='7-ELEVEN'),
                Attach('sign', side='SE', floor=1, z=3.0, w=8.0, h=0.55, style='yoko', color='#f4f2ec', color2='#e8762b', text='7-ELEVEN'),
                Attach('sign', side='front', floor=1, s=0.5, z=2.0, w=0.6, h=0.6, d=0.5, style='tate', color='#f4f2ec', color2='#e8762b', text='7'),
                Attach('box', side='front', s=-1.2, z=0.0, w=1.0, h=0.9, d=0.6, color='#4f86b5', prm=dict(dep=0.5)),
                Attach('ac', side='back', n=3, w=1.2, prm=dict(mount='roof'), floor=2, z=3.0, d=-2.0)],
        lod=2, age=0.25, note='店頭の立て看板(キャンペーン)は置かない')


def ochre_inn():
    """セブンの北西隣の黄土色の宿(954629634、B_seven_north、W 1:31 f_091 / R 29:18 f_586): 3 階、黄土色の壁に濃茶の帯、
    小さな縦長の窓、最上階に丸窓、濃茶の深い軒の寄棟。縦の看板は判読不能(文字なし)。"""
    ring = ring_of('954629634')
    zf = face_z(ring, 211)
    return BuildingSpec(
        id='954629634', name='黄土色の宿(セブンの北西隣、名前不明)', zone='B', floors=3, floor_h=[3.3, 2.9, 2.9], base_z=zf + 0.2, front=211, use_obb=True,
        walls={'*': WallFinish('paint', '#d1ae68')},
        facades={'front': Facade(bay=2.0, margin=0.5, pattern={1: 'G.W.W', 2: '.T.T.T', 3: '.T..T'}, frame='dark', glass='#3a3f42', belt=True,
                                 sizes={'T': (0.9, 1.5, 0.7)}),
                 '*': Facade(bay=2.4, win='T.', ground='.W', frame='dark', glass='#3a3f42', belt=True, lod=1, sizes={'T': (0.9, 1.5, 0.7)})},
        pents=[Pent(1, 'front', depth=1.1, slope=0.3, mat='teppan', color='#3a2e28', z=3.1)],
        roof=Roof('hip', 'teppan', slope=0.4, eave=0.95, color='#3a3532', hafu_col='#3e2e26', soffit_col='#5a4636'),
        attach=[Attach('zA_round', side='front', floor=3, s=-2.2, z=1.5, w=0.42, color='#2d3236', color2='#efe7d2'),
                Attach('sign', side='front', floor=2, s=0.8, z=0.5, w=0.55, h=2.6, style='flat', color='#2b2420', color2='#1d1916'),
                Attach('ac', side='back', n=2, w=1.2), Attach('pipe', side='back', s=0.8)],
        lod=2, age=0.35)


def daito_core():
    """大東館の階段室(r12857070_3、relation 12857070 の東の小片、OSM 9 階): 本館の北東に付く白い塔(8 階+塔屋、遠景の品質)。"""
    s = site('r12857070_3')
    return BuildingSpec(
        id='r12857070_3', name='大東館 階段室(推定)', zone='B', floors=8, floor_h=3.0, base_z=base_for(s, 0.2), front=s['front'], use_obb=True,
        walls={'*': WallFinish('spray', '#e6e5df')},
        facades={'*': Facade(bay=2.0, win='.', ground='G', frame='dark', lod=0)},
        roof=Roof('flat', parapet=0.6), lod=0, age=0.35, note='9 階は relation 全体のタグ。本館と同じ 8 階にした')


def arcade():
    """湯路広場の木のアーケード(B_toji_arcade、K 7:30 f_151、R 18:24〜19:27): OSM に外形が無い。K 7:30 の「左に道(中央通り)、
    右に石積みのテラス、右奥に黄土色の 5 階」の並びから、中央通りと平行な歩道 955567265 に沿わせた。南東の続き(と南で西へ折れる部分)は
    OSM の building=roof 955557540(区域A、フェーズ5 で屋根だけの棟として作った)なので、その始まりの辺まで(約 22 m)を作る。
    北西端に入母屋風の門(額「湯路広場」)、その先は柱(約 20 cm 角、間隔 3.5 m、沓石)と切妻の屋根(内側は化粧垂木)、両側に部分的な縦格子。
    斜面(北西→南東に約 4 m 上る)に合わせて 3 区間の段にした。"""
    F = get_field()
    a, b = np.array((-24.2, -49.6)), np.array((2.8, -83.6))
    t = (b - a) / np.linalg.norm(b - a)
    # 南東の続きは OSM の building=roof 955557540(区域A、歩道沿いから南で西へ折れる L 字の屋根)。その始まりの辺の手前 0.2 m で止めてつなぐ
    q0, q1 = np.array((-12.3, -62.6)), np.array((-15.3, -65.1))
    dq = q1 - q0
    den = t[0] * (-dq[1]) - t[1] * (-dq[0])
    Ltot = float(((q0 - a)[0] * (-dq[1]) - (q0 - a)[1] * (-dq[0])) / den) - 0.2
    ax = bearing(t)
    out = []
    gate_L = 4.4
    nseg = 3
    seg_L = (Ltot - gate_L) / nseg
    wid = 3.6
    post = '#d4b07e'

    def zmid(p0, p1):
        q = np.linspace(0, 1, 5)
        pts = p0[None, :] + (p1 - p0)[None, :] * q[:, None]
        return float(np.median(F.Z(pts[:, 0], pts[:, 1])))
    # 門
    g0, g1 = a, a + t * gate_L
    gz = zmid(g0, g1)
    gate = BuildingSpec(
        id='B_arcade_gate', name='湯路広場の門(アーケードの北西端)', zone='B', ring=rect((g0 + g1) / 2, ax, gate_L, wid + 0.8), floors=1, floor_h=3.4,
        base_z=gz + 0.05, front=(ax + 180) % 360, found='none', replaces=[],
        walls={'*': WallFinish('board_v', post)}, facades={'*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('gable', 'metal', slope=0.62, eave=0.9, verge=1.1, axis=ax, color='#6b6863', hafu_col='#c9a271',
                  soffit_col='#dcc095', rafters=True, rafter_col='#d4b07e', gutters=False, oni=False),
        attach=[Attach('sign', side='front', floor=1, z=3.62, w=2.3, h=0.56, d=0.25, style='flat', color='#c9a271', color2='#8a6a4a', text='湯路広場')],
        lod=2, age=0.15, note='位置は推定(K 7:30 の並びと歩道 955567265)。妻は開いて小屋組が見える(K 7:30)')
    gate.zB_open, gate.zB_post_col, gate.zB_pitch = True, post, 2.2
    out.append(gate)
    for k in range(nseg):
        p0 = a + t * (gate_L + seg_L * k)
        p1 = a + t * (gate_L + seg_L * (k + 1))
        z = zmid(p0, p1)
        sp = BuildingSpec(
            id='B_arcade_%d' % k, name='湯路広場の木のアーケード %d' % (k + 1), zone='B', ring=rect((p0 + p1) / 2, ax, seg_L + 0.02, wid), floors=1,
            floor_h=2.75, base_z=z + 0.05, front=(ax + 90) % 360, found='none', replaces=[],
            walls={'*': WallFinish('board_v', post)}, facades={'*': Facade(pattern={1: '.'}, lod=0)},
            roof=Roof('gable', 'metal', slope=0.5, eave=0.55, verge=0.25, axis=ax, color='#6b6863', hafu_col='#c9a271', soffit_col='#dcc095',
                      rafters=True, rafter_col='#d4b07e', gutters=False, oni=False),
            attach=[Attach('zB_slats', side='front', s=0.3 + 1.2 * k, w=3.2, h=2.4, color='#d8b88a'),        # 右(南西=広場側)の縦格子の壁
                    Attach('zB_slats', side='back', s=seg_L * 0.45, w=3.4, h=2.4, color='#d8b88a')],      # 左(道側)
            lod=2, age=0.15, note='区間 %d/%d(段は地面の中央値)' % (k + 1, nseg))
        sp.zB_open, sp.zB_post_col, sp.zB_pitch = True, post, 3.5
        out.append(sp)
    return out


# ====================================================================== 推定(動画で確認できない棟)
HAND_IDS = {'954786837', '954629638', '954786834', '955804968', '954786833', '605546948', '954629632', '954629634', 'r12857070_3'}

PALETTES = {
    # 湯畑の北の並び(白・黄土・茶・黒の板が混ざる。W 1:31 / R 29:18 の遠景)
    'north': [('paint', '#ecebe6', False), ('paint', '#d6bf8a', False), ('board_h', '#7a5a40', False), ('board_v', '#2b2725', False),
              ('mortar', '#d9d2c3', False), ('plaster', '#efebe2', True)],
    # 湯畑の西の斜面(草津館・御座之湯の裏): 白漆喰+柱梁、吹付、板
    'west': [('plaster', '#efede6', True), ('spray', '#ebe8e0', False), ('board_h', '#8a6a4c', False), ('spray', '#e3dccb', False)],
    # 裏の住宅・小さな旅館(吹付・サイディング)
    'back': [('spray', '#ece9e1', False), ('spray', '#e3dccb', False), ('spray', '#d9d6cf', False), ('board_h', '#c7c2b8', False),
             ('board_h', '#a8b0b3', False), ('mortar', '#cfc6b5', False), ('tile', '#c8b9a0', False)],
    # 大きなホテル(一井 西館・西の大ホテル): 白〜クリームの吹付
    'hotel': [('spray', '#efeeea', False), ('spray', '#e8e4d8', False), ('tile', '#d8cfbd', False)],
    'ryokan': [('spray', '#eae7df', False), ('tile', '#cdbfa6', False), ('spray', '#e2d9c7', False), ('plaster', '#ece8dd', True)],
}
METAL_COLS = ZA.METAL_COLS


def _rs(fid):
    return np.random.RandomState(zlib.crc32(fid.encode('utf-8')) & 0xffffffff)


def style_of(s, tags):
    x, y = s['c']
    if s['area'] < 25:
        return 'tiny'
    if tags.get('building') == 'roof':
        return 'canopy'
    if x < -100 and (s['area'] >= 300 or tags.get('building') == 'hotel' or tags.get('building:levels')):
        return 'hotel'
    if tags.get('tourism') in ('hotel', 'guest_house') or tags.get('building') in ('hotel', 'apartments') or s['area'] >= 300:
        return 'ryokan'
    if -25 <= x < 50 and 25 < y <= 70 and s['road_d'] < 9:
        return 'north'
    if -100 < x < -25:
        return 'west'
    return 'back'


def floors_of(st, s, tags, rs):
    lv = tags.get('building:levels')
    if lv and str(lv).isdigit() and int(lv) <= 9:
        return int(lv), 'OSM'
    a = s['area']
    if st == 'tiny':
        return 1, '面積'
    if st == 'canopy':
        return 1, 'building=roof'
    if st == 'hotel':
        return (5 if a > 1500 else 4), '大きなホテル(面積)'
    if st == 'ryokan':
        return (4 if a > 600 else 3), '旅館・面積'
    if a < 55:
        return (1 if a < 35 else 2), '面積'
    if st == 'north':
        return (3 if (a > 140 and rs.rand() < 0.5) else 2), '北の並び(2〜3 階)'
    if st == 'west':
        return (3 if a > 110 else 2), '西の斜面(面積)'
    return (3 if (a > 160 and rs.rand() < 0.45) else 2), '裏(面積)'


def _generic(fid, ring=None, tags=None, name=None, sid=None, replaces=None):
    """推定の棟: OSM の外形+階数+様式から spec を作る(kd_zone_A._generic と同じ規則、区域B の様式)。看板は枠だけ。"""
    b = bld(fid)
    tags = tags if tags is not None else (b['tags'] if b else {})
    s = site(fid, ring)
    rs = _rs(sid or fid)
    st = style_of(s, tags)
    nf, why = floors_of(st, s, tags, rs)
    shop_street = st == 'north'
    a = s['area']
    pal = PALETTES.get(st if st in PALETTES else 'back')
    wk, wc, timb = pal[rs.randint(len(pal))]
    wc = '#%02x%02x%02x' % tuple(int(np.clip(int(wc[i:i + 2], 16) * (0.96 + 0.08 * rs.rand()), 0, 255)) for i in (1, 3, 5))
    tim = Timber(DARK if rs.rand() < 0.7 else '#4a3426', w=0.11, posts='bay', beams=('top', 'head'), braces=rs.rand() < 0.25) if timb else None
    walls = {'*': WallFinish(wk, wc, timber=tim)}
    if shop_street and nf >= 2 and rs.rand() < 0.55:
        walls[1] = WallFinish(*[('board_v', '#2c2826'), ('board_v', '#4a3426'), ('mortar', '#bdb6aa'), ('paint', wc)][rs.randint(4)])
    fh1 = 3.4 if shop_street else 3.0
    fh = [fh1] + [round(2.8 + 0.25 * rs.rand(), 2)] * (nf - 1)
    if st in ('ryokan', 'hotel'):
        fh = [3.3] + [3.0] * (nf - 1)
    if st == 'tiny':
        fh = [2.5 + 0.4 * rs.rand()]
    # ---- 屋根
    ratio = s['ratio']
    use_obb = ratio >= 0.9 or (ratio >= 0.8 and a < 160)
    pitched = use_obb or ratio >= 0.84
    tsuma = rs.rand() < (0.6 if shop_street else 0.35)
    rax = s['front'] if tsuma else (s['front'] + 90) % 360
    if st == 'hotel':
        roof = Roof('flat', parapet=0.9 + 0.3 * rs.rand(), penthouse=[(rs.uniform(-3, 3), rs.uniform(-2, 2), 4.0, 3.0, 2.8)] if a > 300 else [])
    elif st == 'ryokan':
        if pitched and nf <= 3 and rs.rand() < 0.6:
            roof = Roof('irimoya' if rs.rand() < 0.5 else 'hip', 'kawara', slope=0.45, eave=0.8, verge=0.4, axis='long', irimoya_k=0.5,
                        hafu_col=DARK, gable_style='plaster')
        else:
            roof = Roof('flat', parapet=0.8 + 0.3 * rs.rand(), penthouse=[(rs.uniform(-2, 2), rs.uniform(-1, 1), 3.0, 2.6, 2.4)] if a > 200 else [])
    elif st == 'canopy':
        roof = Roof('hip', 'teppan', slope=0.3, eave=0.4, color=METAL_COLS[rs.randint(len(METAL_COLS))], gutters=False)
    elif not pitched:
        roof = Roof('flat', parapet=0.6 + 0.4 * rs.rand())
    elif shop_street or st == 'west':
        mat = 'kawara' if rs.rand() < 0.6 else 'teppan'
        kind = 'gable' if (shop_street or rs.rand() < 0.6) else 'hip'
        roof = Roof(kind, mat, slope=round(0.42 + 0.2 * rs.rand(), 2), eave=0.5 + 0.3 * rs.rand(), verge=0.4, axis=rax if kind == 'gable' else 'long',
                    color=None if mat == 'kawara' else METAL_COLS[rs.randint(len(METAL_COLS))], hafu_col=DARK,
                    kengyo=(mat == 'kawara' and tsuma and rs.rand() < 0.3))
    else:
        kind = ['gable', 'gable', 'hip', 'shed'][rs.randint(4)] if a > 30 else ['gable', 'shed'][rs.randint(2)]
        mat = 'teppan' if rs.rand() < 0.55 else 'metal'
        roof = Roof(kind, mat, slope=round(0.28 + 0.17 * rs.rand(), 2), eave=0.4 + 0.25 * rs.rand(), verge=0.35, axis=rax if kind == 'gable' else 'long',
                    color=METAL_COLS[rs.randint(len(METAL_COLS))], hafu_col='#5a5048' if rs.rand() < 0.5 else '#e3e0d8', soffit_col='#d9d3c6')
    # ---- 窓割り
    if shop_street:
        g = ['S', 'SG', 'GS', 'S.', 'H', 'SSG', 'G.'][rs.randint(7)]
        w = ['W', 'L', 'W.', '.W', 'R', 'T.', 'LL.'][rs.randint(7)]
        nor = [None, None, '#273149', '#7a2a24', '#e9e4d8', '#2f4a3a', '#5a4632'][rs.randint(7)]
        front_fac = Facade(bay=1.6 + 0.5 * rs.rand(), ground=g, win=w, noren=nor, frame=['alu', 'wood', 'dark', 'white'][rs.randint(4)],
                           glass=['#3c464d', '#46535c', '#e6dfc9'][rs.randint(3)] if 'L' not in w else '#e6dfc9', lattice_col=DARK, trim=rs.rand() < 0.3)
        side_fac = Facade(bay=2.4, win='.W' if rs.rand() < 0.5 else 'W.', ground='..', frame='alu', lod=0)
    elif st in ('ryokan', 'hotel'):
        front_fac = Facade(bay=2.6, win='W', ground='G.W', frame='alu' if rs.rand() < 0.6 else 'dark', glass='#3c4850',
                           fins=(0.4, 0.25) if rs.rand() < 0.3 else None, belt=st == 'hotel')
        side_fac = Facade(bay=2.8, win='W.', ground='.W', frame='alu', lod=0)
    elif st in ('tiny', 'canopy'):
        front_fac = Facade(bay=2.0, pattern={1: ['P', 'G', 'D', '.W'][rs.randint(4)]}, frame='alu', lod=0)
        side_fac = Facade(bay=2.0, win='.', ground='.', lod=0)
    else:
        front_fac = Facade(bay=2.2, ground=['G.W', '.GW', 'W.G', 'GW'][rs.randint(4)], win=['W', 'W.', '.W', 'WW.'][rs.randint(4)],
                           frame='alu' if (st != 'west' or rs.rand() < 0.5) else 'black', glass='#46535c', lod=None)
        side_fac = Facade(bay=2.6, win='.W', ground='W.', frame='alu', lod=0)
    # ---- 品質(道から見える棟だけ lod1、正面以外は面だけ。区域A と同じ基準)
    near = s['road_d'] < 8.0
    lod = 1 if (near and a >= 30 and st not in ('tiny', 'canopy', 'hotel')) else 0
    if st == 'ryokan' and (s['road_d'] > 6 or len(s['ring']) > 16):
        lod = 0
    if not near or lod == 0:
        front_fac = dreplace(front_fac, lod=0)
    facades = {'front': front_fac, '*': side_fac}
    pents, balconies, attach, setbacks = [], [], [], {}
    if shop_street and nf >= 2:
        if rs.rand() < 0.72:
            pents.append(Pent(1, 'front', depth=round(0.75 + 0.4 * rs.rand(), 2), slope=0.3, mat='kawara' if rs.rand() < 0.6 else 'teppan',
                              color=None if rs.rand() < 0.6 else '#2c2a28', z=fh[0] - 0.15))
        elif rs.rand() < 0.6:
            attach.append(Attach('tent', side='front', floor=1, w=min(s['front_len'] - 0.8, 4.5), d=1.0,
                                 color=['#2f5d3a', '#7a2a24', '#c8a23a', '#30476b'][rs.randint(4)], color2='#efe9da' if rs.rand() < 0.5 else None))
        if rs.rand() < 0.3:
            balconies.append(Balcony(2, 'front', depth=0.6, z=0.0, rail=['wood', 'steel', 'lattice'][rs.randint(3)], color=DARK))
        if rs.rand() < 0.75:
            attach.append(Attach('sign', side='front', floor=1, z=fh[0] - 0.35, w=round(min(3.4, s['front_len'] * 0.7), 2), h=0.42, style='yoko',
                                 color=['#3a2a20', '#f0ede4', '#2d4a3a', '#efe9da', '#2b2725', '#7a2a24'][rs.randint(6)], color2=DARK))
        if rs.rand() < 0.35:
            attach.append(Attach('sign', side='front', floor=2, s=0.5, z=1.2, w=0.5, h=1.5, style='tate', color='#f2efe6', color2=DARK))
        if rs.rand() < 0.2:
            attach.append(Attach('lanterns', side='front', floor=1, z=fh[0] - 0.5, d=0.6, n=2, w=min(2.4, s['front_len'] * 0.5),
                                 color='#c03a2b' if rs.rand() < 0.6 else '#efe9da'))
    elif st in ('ryokan', 'hotel'):
        if rs.rand() < 0.5 and nf >= 3 and lod >= 1:
            balconies.extend(Balcony(f, 'front', depth=0.9, rail=['wall', 'steel', 'wood'][rs.randint(3)], s0=0.8, s1=-0.8,
                                     color='#e9e8e3') for f in range(2, nf + 1))
        if lod >= 1 and rs.rand() < 0.5:
            attach.append(Attach('porch', side='front', at=0.3 + 0.4 * rs.rand(), w=3.2, d=2.0, h=3.0, color2='#5a4a3e',
                                 prm=dict(roof='shed', mat='kawara', slope=0.3, platform=True)))
    elif st in ('back', 'west') and nf >= 2:
        if rs.rand() < 0.35:
            balconies.append(Balcony(2, 'front', depth=0.8, rail=['steel', 'wood'][rs.randint(2)], s0=0.5, s1=-0.5))
        if rs.rand() < 0.35:
            pents.append(Pent(1, 'front', depth=0.7, slope=0.3, mat='teppan', color=METAL_COLS[rs.randint(len(METAL_COLS))], s0=0.3, s1=-0.3))
    if st not in ('tiny', 'canopy') and lod >= 1:
        attach.append(Attach('ac', side=['left', 'right', 'back'][rs.randint(3)], n=1 + rs.randint(3), w=1.2))
        if rs.rand() < 0.4:
            attach.append(Attach('pipe', side=['left', 'right', 'back'][rs.randint(3)], s=0.6))
    # ---- 床の高さ(正面の地面=道)と基礎
    drop = s['z_front'] - s['z_min']
    found = 'stone' if drop > 1.4 else 'concrete'
    fh_ = 0.12 if shop_street else 0.3
    nm = name or tags.get('name') or ''
    sp = BuildingSpec(
        id=sid or fid, name=nm or '(無名)', zone='B', ring=ring, floors=nf, floor_h=fh, base_z=base_for(s, fh_), front=s['front'],
        found=found, found_h=0.4 if found == 'stone' else 0.3, found_col='#8b877e' if found == 'stone' else None,
        walls=walls, facades=facades, setbacks=setbacks, pents=pents, balconies=balconies, roof=roof, attach=attach,
        use_obb=use_obb, lod=lod, age=round(0.3 + 0.25 * rs.rand(), 2), replaces=replaces,
        note='推定: 様式=%s、階数=%d(%s)、屋根=%s%s、道まで %.1f m' % (st, nf, why, roof.kind, '' if roof.kind == 'flat' else '/' + roof.mat, s['road_d']))
    if st == 'canopy':
        sp.zA_open = True
        sp.found = 'none'
        sp.walls = {'*': WallFinish('board_v', '#5a4a3e')}
    sp.zA_style = st
    sp.zA_why = why
    return sp


def generics():
    F = get_field()
    out = []
    for b in F.blds:
        if b['zone'] != 'B' or b['id'] in HAND_IDS:
            continue
        sp = _generic(b['id'])
        if b['id'] == '954786836':      # 草津館の北の白い棟(R 20:00 f_401 の左奥に見える): 道から遠いが見えるので lod1
            sp.lod = 1
            sp.facades['front'] = dreplace(sp.facades['front'], lod=None)
        out.append(sp)
    return out


def specs():
    """区域B の全 spec(手作り+推定)。kd_parts.zone_specs('B') と kd_buildings.build_buildings が呼ぶ。"""
    hand = [otonoyu(), atsunoyu(), kankou(), shirahata(), shirahata_tower(), shirahata_gensen(), *kusatsukan(), ichii(), seven(), ochre_inn(),
            daito_core(), *arcade()]
    for sp in hand:
        if not hasattr(sp, 'zA_style'):
            sp.zA_style, sp.zA_why = 'hand', 'カード・フレーム'
    return hand + generics()


# ====================================================================== 実行
def count_only(verbose=True):
    import time
    t0 = time.time()
    get_field()
    tot = 0
    rows = []
    for sp in specs():
        t1 = time.time()
        b = P.build_building(sp, get_field())
        tot += b.info['tris']
        rows.append((sp, b.info))
        if verbose:
            print('%-20s %-34s %-7s lod%d f%d %-8s tris %6d base %.2f (%.2fs)' % (sp.id, sp.name[:34], getattr(sp, 'zA_style', ''), b.info['lod'], sp.floors,
                                                                                sp.roof.kind, b.info['tris'], b.info['base_z'], time.time() - t1))
    print('buildings %d  total tris %d  (%.1fs)' % (len(rows), tot, time.time() - t0))
    return rows


def list_table():
    for sp in specs():
        r = sp.roof
        print('| %s | %s | %s | %d | %s | %s |' % (sp.id, sp.name, getattr(sp, 'zA_style', ''), sp.floors,
                                                  r.kind + ('' if r.kind in ('flat', 'none') else '/' + r.mat), getattr(sp, 'zA_why', '')))


if __name__ == '__main__':
    if '--count' in ARGS:
        count_only()
    elif '--list' in ARGS:
        list_table()
    else:
        P.run_zone('B')
