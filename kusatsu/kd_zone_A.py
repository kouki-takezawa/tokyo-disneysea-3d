# -*- coding: utf-8 -*-
"""kd_zone_A.py -- 草津 湯畑ジオラマ フェーズ5: 区域A(湯畑の南・東)の建物を BuildingSpec で 1 棟ずつ作る。

区域A = 重心が x >= -25 かつ y <= 25(kd_common.zone_of)。OSM 114 外形(湯けむり亭は湯畑側で作るので除く)。
- 手作り(カードで外観が決まっているもの): ちちや、黒い玉石壁、山びこ温泉まんじゅう、黒い切妻 2 連、平の家・草庵、白い 3 階(カラ…)、
  月乃井、おみやげの本多、中央通りの長い棟(店ごとに分割)、清月堂、花いんげん、ローソン、お食事処、大東館(本館・西棟・1 階の店・正面玄関・別棟)。
  ちちや・大東館の spec は kd_parts_test.py の試作からコピー(試作のまま)。
- 推定(動画で確認できない約 90 棟): OSM の外形+階数(タグ>面積・通りの様式)+通りごとの様式(_generic)。看板は枠だけ・文字なし。

実行(他タブの Blender が動いていないことを tasklist で確認して 1 つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_zone_A.py      # buildings_A.glb だけ
  python kusatsu/kd_zone_A.py --count     # Blender 無しで三角形数(1 棟ごと)
  python kusatsu/kd_zone_A.py --list      # 1 棟ごとの階数・屋根・様式・根拠(phase5_notes 用)
地形(敷地の均し)を変えたときは kd_terrain.py -- --zones=A で terrain.glb と buildings_A.glb を作り直す。
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
from kd_parts import (BuildingSpec, WallFinish, Timber, Facade, Balcony, Pent, Roof, Attach, Wall, lin, tint, beam)  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]

DARK = '#2b2420'

# ====================================================================== 試作からのコピー(kd_parts_test.py、フェーズ4)
# 大東館: relation 12857070 の outer 1 を、湯畑側の西棟(段状のバルコニー)と奥の本館に分ける
DAITO_WEST = [(30.85, 34.0), (31.56, 22.22), (43.64, 22.77), (43.17, 30.77), (43.0, 34.2)]
DAITO_MAIN = [(30.85, 34.0), (43.0, 34.2), (43.17, 30.77), (61.29, 31.66), (71.04, 32.15), (57.67, 11.35), (50.33, -0.08), (56.65, -4.08),
              (56.19, -4.81), (64.71, -12.0), (65.63, -10.0), (66.36, -10.55), (83.69, 16.39), (82.66, 29.54), (82.31, 31.87), (82.1, 32.59),
              (80.39, 38.24), (76.26, 43.61), (70.52, 43.48), (70.48, 43.94), (41.71, 42.61)]


def chichiya():
    """ちちや: 3 階、妻入り(北西の妻面が湯畑・車道側)、白漆喰+濃茶の化粧柱梁・筋交い、1 階は赤みの濃茶の板と店先、庇に提灯。"""
    tim = Timber('#3a2a20', w=0.11, posts=0.95, beams=('bottom', 'top', 'head'), braces=True)
    return BuildingSpec(
        id='605309932', name='ちちや', zone='A', floors=3, floor_h=[3.4, 3.0, 2.6], found_h=0.15, front=314,
        walls={1: WallFinish('board_v', '#5b3a29', pitch=0.45), '*': WallFinish('plaster', '#efebe2', timber=tim)},
        facades={
            'front': Facade(bay=1.5, margin=0.3, pattern={1: 'SSSS', 2: '.LL.', 3: '....'}, frame='wood', glass='#e6dfc9',
                            noren='#4a3a30', lattice_col='#3f2a1e', sizes={'L': (1.3, 1.1, 0.75)}),
            'SW': Facade(bay=2.0, pattern={1: 'SSSSSS.', 2: '.L..L..', 3: '..w..w.'}, frame='wood', glass='#e6dfc9', noren='#4a3a30',
                         lattice_col='#3f2a1e', sizes={'L': (1.5, 1.1, 0.75)}),
            '*': Facade(bay=2.2, pattern={1: '.W..W.', 2: '.W..W.', 3: '..w..'}, frame='alu', glass='#4a565e'),
        },
        pents=[Pent(1, side=['front', 'SW'], depth=0.9, slope=0.35, mat='kawara')],
        roof=Roof('gable', 'kawara', slope=0.6, eave=0.75, verge=0.65, kengyo=True, hafu_col='#241e1a', soffit_col='#5a4636'),
        attach=[
            Attach('sign', side='front', floor=3, z=1.15, w=2.7, h=0.95, style='flat', color='#f2efe6', color2='#241e1a', text='ちちや'),
            Attach('crest', side='front', floor=3, w=0.36, prm=dict(gable=True), z=1.05, color='#f2efe6', color2='#241e1a'),
            Attach('sign', side='front', floor=2, s=-0.55, z=1.6, w=0.6, h=2.4, style='flat', color='#241e1a', color2='#3a2a20'),
            Attach('sign', side='front', floor=1, z=2.75, w=2.6, h=0.45, style='yoko', color='#6b4a2e', color2='#3a2a20', text='ちちや'),
            Attach('lanterns', side='front', floor=1, z=2.95, d=0.7, n=3, w=4.0),
            Attach('lanterns', side='SW', floor=1, z=2.95, d=0.7, n=6, w=12.0),
            Attach('ac', side='back', floor=1, n=2, w=1.1),
            Attach('pipe', side='NE', s=2.0),
        ],
        lod=2, age=0.35, note='妻入りの向きは S 2:33 / S 6:27 で確認(カードの「正面 西南西」は車道側の長辺)')


def daitokan():
    """大東館 西棟(湯畑側、段状のバルコニー)+本館(塊、遠景の品質)+1 階の飲食店。kd_parts_test.daitokan() のコピー。"""
    west = BuildingSpec(
        id='r12857070_1#west', name='大東館 西棟', zone='A', ring=DAITO_WEST, floors=5, floor_h=3.0, found_h=0.2, front=262,
        walls={'*': WallFinish('spray', '#e9e8e3')},
        facades={'*': Facade(bay=2.4, win='W', frame='dark', glass='#3c4850', fins=(0.45, 0.32), sizes={'W': (1.8, 1.45, 0.6)}),
                 'front': Facade(bay=3.0, win='W', ground='G', frame='dark', glass='#3c4850', fins=(0.45, 0.32), sizes={'W': (2.2, 1.6, 0.5)})},
        setbacks={3: {'front': 1.6}, 4: {'front': 3.2}, 5: {'front': 4.8}},
        balconies=[Balcony(2, 'front', depth=1.1, rail='wall', color='#e9e8e3')],
        roof=Roof('flat', parapet=0.9, penthouse=[(1.0, -1.0, 3.5, 3.0, 2.6)]),
        attach=[Attach('ac', side='front', floor=2, z=0.0, d=0.35, n=3, w=2.5),
                Attach('sign', side='SW', floor=3, s=-1.0, z=0.3, w=1.0, h=5.0, style='flat', color='#e9e8e3', color2='#d9d8d2', text='(緑の縦書き「東」「館」)')],
        lod=1, age=0.3, same_level=False)
    main = BuildingSpec(
        id='r12857070_1', name='大東館 本館', zone='A', ring=DAITO_MAIN, floors=8, floor_h=3.0, found_h=0.2, front=262,
        walls={'*': WallFinish('spray', '#e6e5df')},
        facades={'*': Facade(bay=3.4, win='W', frame='dark', glass='#3c4850', sizes={'W': (2.0, 1.4, 0.7)})},
        roof=Roof('flat', parapet=1.0, penthouse=[(-8.0, 4.0, 6.0, 5.0, 3.0)]),
        attach=[Attach('sign', side='front', style='roof', w=6.0, h=1.6, d=1.5, color='#e6e5df', color2='#5a5a56', text='(屋上の看板)')],
        wings=[west], lod=0, age=0.35, replaces=['r12857070_1'], note='本館は遠景の品質(lod0)。西棟は lod1')
    shop = BuildingSpec(
        id='r12857070_0', name='大東館 1階の飲食店(魚民・十割そば)', zone='A', floors=1, floor_h=4.0, found_h=0.1, front=262,
        walls={'*': WallFinish('board_v', '#2a2624', pitch=0.3)},
        facades={'front': Facade(pattern={1: 'SSSS'}, noren='#2a2624'), '*': Facade(pattern={1: '..'})},
        pents=[Pent(1, 'front', depth=0.9, slope=0.3, z=3.35, mat='kawara')],
        roof=Roof('flat', parapet=0.5),
        attach=[Attach('lanterns', side='front', z=3.1, d=0.62, n=8, w=7.5, color='#f1ece0'),
                Attach('sign', side='front', z=3.7, w=4.5, h=0.5, style='yoko', color='#1e1c1b', color2='#3a2e26', text='十割そば'),
                Attach('tank', prm=dict(u=1.5, v=-0.8), n=3, w=0.3, h=1.3),
                Attach('ac', side='back', floor=1, z=4.05, d=-1.2, n=2, w=1.0, prm=dict(mount='roof'))],
        lod=1, age=0.4)
    return [main, shop]


# ====================================================================== 区域の補助(幾何・道・地面)
_FIELD = None


def set_field(field):
    global _FIELD
    _FIELD = field


def get_field():
    global _FIELD
    if _FIELD is None:
        import kd_field as F
        _FIELD = F.Field(C.load_osm(), log=lambda *a: None)
    return _FIELD


def bld(fid):
    return P._bld_by_id(get_field()).get(fid)


def ring_of(fid):
    return [tuple(p) for p in bld(fid)['ring']]


def bearing(v):
    return (math.degrees(math.atan2(v[0], v[1])) + 360.0) % 360.0


def uvec(deg):
    return P.bearing_vec(deg)


def cut(ring, p0, dirv, keep=1):
    """ring を p0 を通り dirv(2D)に垂直な線で切り、dirv 側(keep=1)か反対側(-1)を返す。"""
    a, b = float(dirv[0]) * keep, float(dirv[1]) * keep
    c = -(a * p0[0] + b * p0[1])
    out = P.clip_half(list(ring), a, b, c)
    return C.ccw(C.clean_ring(out)) if len(out) >= 3 else None


def slices_along(ring, axis_deg, fracs):
    """外形を軸(方位 axis_deg)に沿って割合 fracs(0..1 の区切り)で切り分ける -> 外形のリスト。"""
    u = uvec(axis_deg)
    Pp = np.array(ring, float)
    pu = Pp @ u
    lo, hi = float(pu.min()), float(pu.max())
    out = []
    bounds = [0.0] + list(fracs) + [1.0]
    for i in range(len(bounds) - 1):
        r = list(ring)
        a = lo + (hi - lo) * bounds[i]
        b = lo + (hi - lo) * bounds[i + 1]
        if i > 0:
            r = cut(r, u * a, u, 1)
        if r and i < len(bounds) - 2:
            r = cut(r, u * b, u, -1)
        if r and abs(C.poly_area(r)) > 2.0:
            out.append(r)
    return out


_SEGS = None
RANK = {'trunk': 3, 'residential': 3, 'unclassified': 3, 'service': 2, 'pedestrian': 2, 'footway': 1, 'path': 1}
CHUO = 594139678        # 中央通り(湯畑の南西角から南東へ)


def road_segs():
    global _SEGS
    if _SEGS is None:
        F = get_field()
        rows = []
        for r in F.roads:
            p = r['pts']
            for i in range(len(p) - 1):
                rows.append((p[i][0], p[i][1], p[i + 1][0], p[i + 1][1], RANK.get(r['cls'], 1), r['id']))
        lp = list(F.yb.loop) + [F.yb.loop[0]]
        for i in range(len(lp) - 1):
            rows.append((lp[i][0], lp[i][1], lp[i + 1][0], lp[i + 1][1], 3, -1))      # 湯畑の周回の車道
        _SEGS = np.array(rows, float)
    return _SEGS


def nearest_road(pts, minrank=1):
    """点群(建物の外形+重心)から、ランク minrank 以上の道への最短距離・最近点・道の id。"""
    S = road_segs()
    S = S[S[:, 4] >= minrank]
    best = (1e9, None, None)
    A = S[:, 0:2]
    D = S[:, 2:4] - A
    L2 = np.maximum((D ** 2).sum(1), 1e-9)
    for p in pts:
        t = np.clip(((p[0] - A[:, 0]) * D[:, 0] + (p[1] - A[:, 1]) * D[:, 1]) / L2, 0, 1)
        Q = A + D * t[:, None]
        d = np.hypot(Q[:, 0] - p[0], Q[:, 1] - p[1])
        i = int(np.argmin(d))
        if d[i] < best[0]:
            best = (float(d[i]), (float(Q[i, 0]), float(Q[i, 1])), int(S[i, 5]))
    return best


def site(fid, ring=None):
    """敷地の情報: 外形・面積・最小矩形・矩形らしさ・正面(道への向きを矩形の辺の法線に合わせる)・道までの距離・正面の地面の高さ。"""
    F = get_field()
    ring = ring or ring_of(fid)
    area = abs(C.poly_area(ring))
    (cx, cy), ang, L, W = P.obb(ring)
    ratio = area / max(L * W, 1e-6)
    pts = list(ring) + [(cx, cy)]
    main = nearest_road(pts, 3)
    sec = nearest_road(pts, 2)
    anyr = nearest_road(pts, 1)
    if main[0] < 9.0:
        road = main
    elif sec[0] < 7.0:
        road = sec
    elif anyr[0] < 5.0:
        road = anyr
    else:
        road = main if main[0] < sec[0] + 8 else sec
    q = road[1]
    to = np.array([q[0] - cx, q[1] - cy])
    u = np.array([math.cos(ang), math.sin(ang)])
    v = np.array([-u[1], u[0]])
    cands = [u, -u, v, -v]
    fv = max(cands, key=lambda c: float(c @ to))
    front = bearing(fv)
    long_front = abs(float(fv @ u)) < 0.5        # 正面が長辺
    # 正面の辺の外 1 m の地面(1 階の床の高さの基準)
    half = (W / 2) if long_front else (L / 2)
    along = (L if long_front else W)
    tv = np.array([-fv[1], fv[0]])
    ss = np.linspace(-along / 2 + 0.6, along / 2 - 0.6, 7)
    fx = cx + fv[0] * (half + 1.0) + tv[0] * ss
    fy = cy + fv[1] * (half + 1.0) + tv[1] * ss
    zf = F.Z(fx, fy)
    Pp = np.array(ring, float)
    zr = F.Z(Pp[:, 0], Pp[:, 1])
    return dict(id=fid, ring=ring, area=area, c=(cx, cy), ang=ang, L=L, W=W, ratio=ratio, front=front, fv=fv, long_front=long_front,
                road_d=road[0], road_id=road[2], main_d=main[0], main_id=main[2], z_front=float(np.median(zf)),
                z_min=float(zr.min()), z_max=float(zr.max()), front_len=along)


def base_for(s, found_h=0.15, lift=0.0):
    """1 階の床の Z: 正面の地面(道)+ found_h。裏が低ければ基礎が伸び、高ければ壁が地面に入る(切り土の跡を作らない)。"""
    return s['z_front'] + found_h + lift


# ====================================================================== 部品の追加(区域内だけで使う)
def _stone_cap(pb, c, n, r, h, col, lod):
    n = np.asarray(n, float)
    n = n / max(np.linalg.norm(n), 1e-9)
    t1 = np.cross(n, (0.0, 0.0, 1.0))
    if np.linalg.norm(t1) < 1e-4:
        t1 = np.array([1.0, 0.0, 0.0])
    t1 = t1 / np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    c = np.asarray(c, float)
    k = 6 if lod < 2 else 7
    ang = np.linspace(0, 2 * math.pi, k, endpoint=False)
    R0 = [c + t1 * r * math.cos(a) + t2 * r * math.sin(a) - n * 0.02 for a in ang]
    if lod >= 2:
        R1 = [c + t1 * r * 0.7 * math.cos(a) + t2 * r * 0.7 * math.sin(a) + n * h * 0.7 for a in ang]
        apex = c + n * h
        for i in range(k):
            j = (i + 1) % k
            pb.poly('stone', [tuple(R0[i]), tuple(R0[j]), tuple(R1[j]), tuple(R1[i])], col, tuple(n))
            pb.poly('stone', [tuple(R1[i]), tuple(R1[j]), tuple(apex)], tint(col, 1.08), tuple(n))
    else:
        apex = c + n * h
        for i in range(k):
            j = (i + 1) % k
            pb.poly('stone', [tuple(R0[i]), tuple(R0[j]), tuple(apex)], col, tuple(n))


def att_zA_tama(self, A):
    """黒い玉石の凹凸壁(A_east_row): 壁の上ほど張り出して軒の下で丸く戻る枕形の殻に、直径 25〜40 cm の黒い玉石を埋め込む。
    prm: z0(殻の下端、1 階の床から m)、top(上端、最上階の上端から m)、D=d(最大の張り出し m)、step(石の間隔)。"""
    pb, lod = self.pb, self.lod
    W, s, k = self.attach_wall(A)
    z0 = self.zs[0] + A.prm.get('z0', 1.0)
    z1 = self.ztop + A.prm.get('top', 0.4)
    D = A.d or 1.2
    Lw = W.L
    shell = lin(A.color or '#1d1c1b')
    stc = lin(A.color2 or '#3c3b39')

    def prof(t):
        return math.sin(math.pi * min(max(t, 0), 1)) ** 0.75 * (0.45 + 0.55 * t)

    def gs(u):
        return math.sin(math.pi * min(max(u, 0), 1)) ** 0.28

    def S(u, t):
        return np.array(W.P(u * Lw, z0 + (z1 - z0) * t, D * prof(t) * gs(u)))
    nu, nt = (16, 12) if lod >= 1 else (8, 6)
    G = [[S(i / nu, j / nt) for j in range(nt + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nt):
            pb.poly('wall', [tuple(G[i][j]), tuple(G[i + 1][j]), tuple(G[i + 1][j + 1]), tuple(G[i][j + 1])],
                    P.hj(shell, 0.03, i, j), W.nrm())
    if lod == 0:
        return
    step = A.prm.get('step', 0.78)
    rs = np.random.RandomState(self.seed + 3)
    hgt = (z1 - z0)
    nrow = int(hgt / (step * 0.87))
    for jr in range(1, nrow):
        t = jr / nrow
        if t > 0.93:
            continue
        ncol = int(Lw / step)
        off = 0.5 if jr % 2 else 0.0
        for ic in range(ncol):
            u = (ic + off + 0.5 + rs.uniform(-0.2, 0.2)) / (ncol + 0.5)
            if u < 0.05 or u > 0.95:
                continue
            tt = t + rs.uniform(-0.02, 0.02)
            p = S(u, tt)
            du = S(min(u + 0.01, 1), tt) - S(max(u - 0.01, 0), tt)
            dt = S(u, min(tt + 0.01, 1)) - S(u, max(tt - 0.01, 0))
            n = np.cross(du, dt)
            if float(n[0] * W.n[0] + n[1] * W.n[1]) < 0:
                n = -n
            if rs.rand() < 0.18:      # ところどころ石が抜ける(写真の不規則な並び)
                continue
            r = rs.uniform(0.11, 0.17)
            _stone_cap(pb, p, n, r, r * 0.5, P.hj(stc, 0.1, ic, jr), lod)


def _open_walls(self):
    """building=roof(屋根だけの建物): 壁の代わりに柱と桁。"""
    pb = self.pb
    self.edge_ops = {}
    ring = self.rings[0]
    z0, z1 = self.zs[0], self.ztop
    col = lin(getattr(self.spec, 'zA_post_col', '#5a4a3e'))
    for i in range(len(ring)):
        W = Wall(ring[i], ring[(i + 1) % len(ring)])
        if W.L < 0.3:
            continue
        n = max(1, int(round(W.L / 3.2)))
        for j in range(n):
            sj = W.L * j / n
            zg = self.ground(*W.P(sj + 0.12, 0, -0.15)[:2])
            W.box(pb, 'wood', sj + 0.02, sj + 0.2, zg, z1, -0.2, -0.02, col, skip=('-z',))
        W.box(pb, 'wood', 0.0, W.L, z1 - 0.28, z1, -0.22, 0.0, tint(col, 0.9), skip=())


_ORIG_WALLS = P.Builder.walls
_ORIG_FOUND = P.Builder.foundation


def _walls(self):
    if getattr(self.spec, 'zA_open', False):
        return _open_walls(self)
    return _ORIG_WALLS(self)


def _foundation(self):
    if getattr(self.spec, 'zA_open', False):
        return
    return _ORIG_FOUND(self)


def att_zA_round(self, A):
    """丸窓(破風の丸い時計窓): 白い縁の輪+暗いガラス(紋と違って斜めの桟なし)。"""
    pb = self.pb
    W, s, k = self.attach_wall(A)
    r = A.w or 0.4
    zc = self.zs[k] + (A.z if A.z is not None else self.fh[k] / 2)
    if A.prm.get('gable'):
        zc = self.roofinfo.get('zr', self.ztop) - (A.z or 1.0)
    n = 16 if self.lod >= 2 else 10
    g, rc = lin(A.color or '#2d3236'), lin(A.color2 or '#ebe8e0')
    pb.poly('glass', [W.P(s + r * math.cos(t), zc + r * math.sin(t), 0.02) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)], g, W.nrm())
    for j in range(n):
        t0, t1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
        pb.poly('wood', [W.P(s + (r + 0.09) * math.cos(t0), zc + (r + 0.09) * math.sin(t0), 0.06), W.P(s + (r + 0.09) * math.cos(t1), zc + (r + 0.09) * math.sin(t1), 0.06),
                         W.P(s + r * math.cos(t1), zc + r * math.sin(t1), 0.06), W.P(s + r * math.cos(t0), zc + r * math.sin(t0), 0.06)], rc, W.nrm())
    if self.lod >= 1:
        W.box(pb, 'wood', s - 0.02, s + 0.02, zc - r, zc + r, 0.02, 0.05, rc)


P.Builder.att_zA_round = att_zA_round
P.Builder.att_zA_tama = att_zA_tama
P.Builder.walls = _walls
P.Builder.foundation = _foundation


# ====================================================================== 手作り(カードあり)
def kurotama():
    """黒い玉石壁の店(605309933、A_east_row 1、R 3:06 f_63 / S 2:33 f_52): 3 階、黒い殻に玉石、窓は小さい、正面(北西)の殻が上へ張り出す。"""
    s = site('605309933')
    return BuildingSpec(
        id='605309933', name='黒い玉石壁の店(頼朝・らーめん壱番の棟、推定)', zone='A', floors=3, floor_h=[3.4, 3.0, 2.8],
        base_z=base_for(s, 0.12), front=314,
        walls={'*': WallFinish('paint', '#1f1d1c')},
        facades={'front': Facade(bay=1.8, pattern={1: '.SS.', 2: '....', 3: '....'}, noren='#2b2a28', frame='black'),
                 'SW': Facade(bay=2.2, pattern={1: 'SS.S..', 2: '..w..w', 3: '.w....'}, frame='black', glass='#30383d', noren='#3a2a20'),
                 '*': Facade(bay=2.4, win='.w', ground='.W', frame='black', lod=0)},
        pents=[Pent(1, side='SW', depth=0.8, slope=0.3, mat='kawara', z=3.0)],
        roof=Roof('gable', 'metal', slope=0.85, eave=0.25, verge=0.2, color='#232221', hafu_col='#1c1b1a', soffit_col='#2a2826', gutters=False, oni=False),
        attach=[Attach('zA_tama', side='front', d=1.25, color='#1c1b1a', color2='#6a6864', prm=dict(z0=1.2, top=1.6, step=0.78)),
                Attach('sign', side='front', floor=1, z=3.05, w=3.2, h=0.4, style='yoko', color='#2a2624', color2='#1c1b1a'),
                Attach('nobori', side='SW', s=3.0, n=2, w=1.1, color='#e2b23a', color2='#3a3a3a'),
                Attach('ac', side='back', n=2, w=1.2)],
        lod=2, age=0.3, note='OSM との対応は並び順(確度 低〜中)。殻と玉石は区域ファイルの att_zA_tama')


def yamabiko():
    """山びこ温泉まんじゅうの縦看板の建物(605309935、R 3:06 f_63、R 3:09 f_64、S 2:12 f_45): 3 階、薄茶の箱(陸屋根の看板壁)、白い縦看板、1 階は瓦の庇。"""
    s = site('605309935')
    return BuildingSpec(
        id='605309935', name='山びこ温泉まんじゅうの建物', zone='A', floors=3, floor_h=[3.3, 3.0, 2.9], base_z=base_for(s, 0.12), front=314,
        walls={1: WallFinish('board_v', '#3a2c24', pitch=0.35), '*': WallFinish('paint', '#cdb492')},
        side_walls={'back': {'*': WallFinish('mortar', '#bdb39f')}},
        facades={'front': Facade(bay=1.7, pattern={1: 'SSSS', 2: '.WW.', 3: '.ww.'}, noren='#3e4f73', frame='dark', glass='#3a4348', trim=True),
                 '*': Facade(bay=2.4, win='.W', ground='..', frame='alu', lod=1),
                 'back': Facade(bay=2.4, win='W.', ground='.G', frame='alu', lod=0)},
        pents=[Pent(1, 'front', depth=1.0, slope=0.32, mat='kawara', z=2.95)],
        roof=Roof('flat', parapet=1.3, coping_col='#a89574'),
        attach=[Attach('sign', side='front', floor=2, s=-0.75, z=2.6, w=0.95, h=5.0, style='flat', color='#f1eee6', color2='#cdb492', text='山びこ温泉まんじゅう'),
                Attach('sign', side='front', floor=2, s=3.4, z=0.35, w=4.2, h=0.55, style='yoko', color='#3d2c22', color2='#2a201a', text='山びこ…(判読できた部分のみ)'),
                Attach('nobori', side='front', s=1.0, n=2, w=1.0, color='#d93a2b', color2='#3a3a3a'),
                Attach('ac', side='back', n=2, w=1.2), Attach('pipe', side='back', s=1.2)],
        lod=2, age=0.35)


def twin_gables():
    """黒い切妻の 2 連(A_east_row 3、R 3:09 f_64、S 2:12 f_45): 黒い板張り、妻面を道(北西)へ、破風に白い縁の丸窓。
    OSM 896878998 は幅 5.2 m しかないので、北隣の 605309940(平の家)の北西の端 9 m を 2 つ目の切妻にした(写真では 2 棟が並ぶ)。"""
    out = []
    ring2 = ring_of('605309940')
    s2 = site('605309940')
    u = uvec(s2['front'] if False else 314)   # 北西
    Pp = np.array(ring2)
    tip = Pp[np.argmax(Pp @ u)]
    nw = cut(ring2, tip - u * 9.0, u, 1)
    for k, (fid, ring) in enumerate((('896878998', ring_of('896878998')), ('605309940#nw', nw))):
        s = site(fid if k == 0 else '605309940', ring)
        out.append(BuildingSpec(
            id=fid, name='黒い切妻 2 連の%s' % ('南' if k == 0 else '北(平の家の北西端)'), zone='A', ring=ring, use_obb=True,
            floors=2, floor_h=[3.3, 3.0], base_z=base_for(s, 0.12), front=314, replaces=['896878998'] if k == 0 else [],
            walls={'*': WallFinish('board_v', '#252220', pitch=0.32)},
            facades={'front': Facade(bay=1.6, pattern={1: 'SG' if k == 0 else 'SSG', 2: 'W' if k == 0 else '.WW.'}, frame='black',
                                     glass='#323a3f', noren='#e6e1d4' if k == 0 else '#3b3f4a'),
                     '*': Facade(bay=2.2, win='.w', ground='..', frame='black', lod=0)},
            pents=[Pent(1, 'front', depth=0.85, slope=0.33, mat='kawara', z=3.0)],
            roof=Roof('gable', 'kawara', slope=0.75, eave=0.45, verge=0.4, axis=314, color='#3c3e42', hafu_col='#1e1c1b', soffit_col='#2c2826'),
            attach=[Attach('zA_round', side='front', floor=2, w=0.42, prm=dict(gable=True), z=1.25, color='#2d3236', color2='#ebe8e0'),
                    Attach('sign', side='front', floor=1, z=3.45, w=min(3.0, s['front_len'] * 0.7), h=0.4, style='yoko', color='#2a2522', color2='#1c1b1a'),
                    Attach('lanterns', side='front', floor=1, z=2.9, d=0.6, n=2 + k, w=2.4 + k, color='#efe9da')],
            lod=2, age=0.3, note='丸窓は紋の部品(白い輪+暗い面)'))
    return out


def hira_no_ie():
    """お宿 平の家(605309940 の北西端 9 m を除いた残り、A_hira_no_ie、R 3:09 f_64): 4 階の白い陸屋根、各階の横帯バルコニー。"""
    ring2 = ring_of('605309940')
    u = uvec(314)
    Pp = np.array(ring2)
    tip = Pp[np.argmax(Pp @ u)]
    rest = cut(ring2, tip - u * 9.0, u, -1)
    s = site('605309940', rest)
    bal = [Balcony(f, 'SW', depth=1.0, rail='wall', color='#e9e8e3', rail_h=1.0) for f in (2, 3, 4)]
    return BuildingSpec(
        id='605309940', name='お宿 平の家', zone='A', ring=rest, floors=4, floor_h=[3.2, 3.0, 3.0, 3.0], base_z=base_for(s, 0.2),
        front=227, walls={'*': WallFinish('spray', '#e9e8e3')},
        facades={'SW': Facade(bay=2.6, win='W', ground='GW', frame='alu', glass='#3c4850', sizes={'W': (1.9, 1.5, 0.5)}),
                 'NW': Facade(bay=2.6, win='W', ground='.W', frame='alu', glass='#3c4850'),
                 '*': Facade(bay=2.8, win='W.', ground='.W', frame='alu', lod=0)},
        balconies=bal, roof=Roof('flat', parapet=0.9, penthouse=[(4.0, 0.5, 3.0, 2.6, 2.4)]),
        attach=[Attach('ac', side='SW', floor=2, z=0.05, d=0.3, n=4, w=4.5), Attach('ac', side='SW', floor=3, z=0.05, d=0.3, n=3, w=5.5),
                Attach('ac', side='NE', n=3, w=1.2), Attach('pipe', side='NE', s=3.0)],
        lod=1, age=0.3, note='OSM 4 階。北西の端は黒い切妻(twin_gables)に回した')


def soan():
    """草庵・ナカヨシ堂の棟(605309937、A_hira_no_ie、S 2:12 遠景): 3 階の白い陸屋根の箱(推定)。"""
    s = site('605309937')
    return BuildingSpec(
        id='605309937', name='草庵・ナカヨシ堂の棟', zone='A', floors=3, floor_h=[3.2, 3.0, 3.0], base_z=base_for(s, 0.2), front=227,
        walls={'*': WallFinish('spray', '#e4e2db')},
        facades={'SW': Facade(bay=2.5, win='W', ground='G.W', frame='alu', glass='#3f4b52'), '*': Facade(bay=2.8, win='.W', ground='.W', frame='alu', lod=0)},
        balconies=[Balcony(2, 'SW', depth=0.9, rail='steel', s0=1.0, s1=-1.0), Balcony(3, 'SW', depth=0.9, rail='steel', s0=1.0, s1=-1.0)],
        roof=Roof('flat', parapet=0.8),
        attach=[Attach('ac', side='NE', n=3, w=1.3), Attach('tank', prm=dict(u=4.0, v=1.0), n=1, w=0.5, h=1.4, color='#b9bcbd')],
        lod=1, age=0.35)


def white3():
    """月乃井の北隣の白い 3 階建て(912422960、A_chuo_row、S 6:27 f_130): 白い塗り壁、2・3 階の大きな黒枠の窓、1 階は黒い庇と暖色の店先。"""
    s = site('912422960')
    return BuildingSpec(
        id='912422960', name='白い 3 階建て(月乃井の北隣)', zone='A', floors=3, floor_h=[3.4, 3.1, 3.0], base_z=base_for(s, 0.12), front=314,
        walls={'*': WallFinish('paint', '#ecebe6')},
        facades={'front': Facade(bay=1.7, pattern={1: 'SSSS', 2: '.RR', 3: '.RR'}, frame='black', glass='#2f3940', noren=None,
                                 sizes={'R': (None, 1.5, 0.75)}),
                 'SW': Facade(bay=2.6, win='W.', ground='.W', frame='alu', lod=1),
                 '*': Facade(bay=2.6, win='W.', ground='..', frame='alu', lod=0)},
        pents=[Pent(1, 'front', depth=1.1, slope=0.25, mat='teppan', color='#262321', z=3.15)],
        roof=Roof('gable', 'metal', slope=0.42, eave=0.35, verge=0.3, color='#9a9ea0', hafu_col='#e9e8e3', soffit_col='#e9e8e3'),
        attach=[Attach('sign', side='front', floor=1, z=3.0, w=3.2, h=0.35, style='yoko', color='#3a2a20', color2='#262321'),
                Attach('lanterns', side='front', floor=1, z=2.85, d=0.9, n=2, w=3.0, color='#c03a2b'),
                Attach('pipe', side='front', s=-0.25), Attach('ac', side='NE', n=2, w=1.2)],
        lod=2, age=0.3, note='2 階の窓の看板「カラ…」は判読不完全なので文字なし')


def tsukinoi():
    """月乃井(912422971 の北西 14 m、A_tsukinoi、S 6:27 f_130): 2 階の擬洋風、ミントの下見板、1 階は半円アーチの連続、2 階は縦長窓と白い手すり、妻に小窓。
    残り(南東)は同じ外形の続きの 2 階建て(推定)。"""
    ring = ring_of('912422971')
    u = uvec(314)
    Pp = np.array(ring)
    tip = Pp[np.argmax(Pp @ u)]
    nw = cut(ring, tip - u * 14.0, u, 1)
    rest = cut(ring, tip - u * 14.0, u, -1)
    s = site('912422971', nw)
    mint = '#c3d6cc'
    main = BuildingSpec(
        id='912422971', name='月乃井', zone='A', ring=nw, use_obb=True, floors=2, floor_h=[3.9, 3.0], base_z=base_for(s, 0.15), front=314,
        replaces=['912422971'],
        walls={'*': WallFinish('board_h', mint, pitch=0.16)},
        facades={'front': Facade(bay=2.2, margin=0.4, pattern={1: 'AAA', 2: '.TT.'}, frame='white', glass='#3d4a52', trim=True, belt=True,
                                 sizes={'A': (1.9, 2.75, 0.0), 'T': (1.15, 1.75, 0.5)}),
                 '*': Facade(bay=2.4, win='T.', ground='.A', frame='white', glass='#3d4a52', trim=True, lod=1,
                             sizes={'A': (1.4, 2.4, 0.4), 'T': (0.9, 1.5, 0.6)})},
        balconies=[Balcony(2, 'front', depth=0.28, rail='steel', color='#f0efe9', rail_h=0.7, s0=1.2, s1=-1.2, brackets=True)],
        roof=Roof('gable', 'metal', slope=0.62, eave=0.45, verge=0.4, color='#8f9599', hafu_col='#eeede8', soffit_col='#eeede8', gable_window=True),
        attach=[Attach('sign', side='front', floor=1, z=3.55, w=2.8, h=0.5, style='yoko', color='#1f1d1c', color2='#2a2826', text='月乃井'),
                Attach('sign', side='front', floor=1, z=3.1, w=3.6, h=0.3, style='yoko', color='#f2efe6', color2='#d9d6cf', text='自家製洋菓子 & レストラン'),
                Attach('box', side='front', s=-0.8, z=0.0, w=0.45, h=0.9, d=0.4, color='#c4352b', prm=dict(dep=0.35)),
                Attach('box', side='front', s=-1.5, z=0.0, w=0.45, h=0.9, d=0.4, color='#c4352b', prm=dict(dep=0.35)),
                Attach('ac', side='back', n=2, w=1.2)],
        lod=2, age=0.25, note='OSM の外形は大きい(25 m)ので北西 14 m を月乃井、残りを続きの棟にした')
    s2 = site('912422971', rest)
    back = BuildingSpec(
        id='912422971#rest', name='月乃井の続きの棟(推定)', zone='A', ring=rest, floors=2, floor_h=[3.4, 2.9], base_z=base_for(s2, 0.15),
        front=s2['front'], replaces=[],
        walls={'*': WallFinish('board_h', '#b9cbc1', pitch=0.2)},
        facades={'*': Facade(bay=2.4, win='W.', ground='.W', frame='white', lod=0)},
        roof=Roof('flat', parapet=0.6), attach=[Attach('ac', side='*', n=2, w=1.2)], lod=1, age=0.35)
    return [main, back]


def honda():
    """おみやげの本多(605085501、A_honda、S 6:30 f_131): 3 階+屋根裏、白漆喰に黒い化粧柱梁、2・3 階が持ち送りで張り出す、
    白い額縁の縦長窓と窓下の黒い箱、1 階は黒い木枠のガラスの店と黒い庇。正面は中央通り側(南西)の長辺。"""
    s = site('605085501')
    tim = Timber('#1f1c1a', w=0.15, posts='bay', beams=('bottom', 'top', 'head', 'sill'))
    return BuildingSpec(
        id='605085501', name='おみやげの本多', zone='A', floors=3, floor_h=[3.4, 2.9, 2.7], base_z=base_for(s, 0.12), front=225,
        walls={1: WallFinish('board_v', '#26211e', pitch=0.4), '*': WallFinish('plaster', '#f2f0ea', timber=tim)},
        facades={'front': Facade(bay=1.25, margin=0.3, pattern={1: 'SSSSSSSSS', 2: '.TT.TT.TT.', 3: '.TT.TT.TT.'}, frame='white', glass='#3e4950',
                                 trim=True, noren=None, sizes={'T': (0.78, 1.45, 0.62)}),
                 'NW': Facade(bay=1.3, pattern={1: 'SSSS', 2: '.TT.', 3: '.TT.'}, frame='white', glass='#3e4950', trim=True,
                              sizes={'T': (0.78, 1.45, 0.62)}),
                 '*': Facade(bay=2.2, win='.W', ground='..', frame='alu', lod=0)},
        setbacks={2: {'front': -0.35, 'NW': -0.35}, 3: {'front': -0.6, 'NW': -0.6}},
        balconies=[Balcony(2, ['front', 'NW'], depth=0.28, z=0.32, rail='wall', rail_h=0.28, color='#262220', brackets=True),
                   Balcony(3, ['front', 'NW'], depth=0.28, z=0.32, rail='wall', rail_h=0.28, color='#262220', brackets=True)],
        pents=[Pent(1, ['front', 'NW'], depth=1.05, slope=0.22, mat='teppan', color='#2a2826', z=3.3)],
        roof=Roof('gable', 'kawara', slope=0.85, eave=0.35, verge=0.3, color='#3d3f44', hafu_col='#1f1c1a', soffit_col='#2c2826', gable_window=True),
        attach=[Attach('sign', side='front', floor=1, z=2.95, w=8.0, h=0.62, style='yoko', color='#f2efe6', color2='#1f1c1a', text='おみやげの本多'),
                Attach('sign', side='front', floor=1, z=2.5, s=2.6, w=3.6, h=0.28, style='yoko', color='#f2efe6', color2='#1f1c1a', text='手作りお菓子工房', d=0.02),
                Attach('box', side='front', s=-0.5, z=0.0, w=0.42, h=1.25, d=0.7, color='#c4352b', prm=dict(dep=0.42)),
                Attach('lanterns', side='front', floor=1, z=3.05, d=0.75, n=4, w=8.0, color='#f0c060'),
                Attach('ac', side='back', n=2, w=1.2), Attach('pipe', side='back', s=1.0)],
        lod=2, age=0.3, note='正面は S 6:30 の長辺(中央通り側と判断、確度 低)。屋根裏は急勾配の切妻と妻の小窓')


def chuo_long():
    """中央通りの長い棟(605085502、A_chuo_row、S 8:15〜8:33 遠景): OSM の外形は L 字。中央通り沿いの帯(幅 7.4 m)を 5 軒に分け、
    奥の腕は別の 2 階建て。店の名前(繕・そばきち・SORAN・まんだら堂・ともえや・水穂)は動画で読めないので看板は無地。"""
    ring = ring_of('605085502')
    a, b = np.array((-9.24, -46.92)), np.array((6.44, -65.7))        # 帯の北東の辺
    t = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([t[1], -t[0]])                                      # 帯の内側(南西)向き
    strip = cut(ring, a, nrm, 1)
    arm = cut(ring, a, nrm, -1)
    axis = bearing(t)
    parts = slices_along(strip, axis, [0.2, 0.39, 0.58, 0.79])
    looks = [   # (階数, 階高, 1 階の壁, 上の壁, 屋根, 1 階, 2 階, 色)
        (2, [3.4, 2.9], ('board_v', '#2b2725'), ('paint', '#e9e6de'), ('gable', 'kawara', 0.55, 'tsuma'), 'SSS', '.L.', '#273149'),
        (2, [3.5, 3.0], ('board_h', '#6e5139'), ('board_h', '#7b5b41'), ('gable', 'teppan', 0.45, 'hira'), 'SS', 'WW', None),
        (3, [3.3, 2.8, 2.7], ('paint', '#d5e0d6'), ('paint', '#d5e0d6'), ('gable', 'metal', 0.4, 'tsuma'), 'GSS', '.W.', None),
        (2, [3.4, 2.9], ('board_v', '#3a2c24'), ('plaster', '#ece8dd'), ('gable', 'kawara', 0.6, 'tsuma'), 'SSS', 'L.L', '#7a2a24'),
        (2, [3.3, 2.8], ('mortar', '#cdc5b6'), ('mortar', '#d9d2c3'), ('gable', 'teppan', 0.4, 'hira'), 'HS', 'W.W', None),
    ]
    out = []
    for k, r in enumerate(parts):
        nf, fh, w1, w2, rf, g1, g2, nor = looks[k % len(looks)]
        s = site('605085502', r)
        tim = Timber(DARK, w=0.11, posts='bay', beams=('top', 'head')) if w2[0] == 'plaster' else None
        rax = s['front'] if rf[3] == 'tsuma' else (s['front'] + 90) % 360
        out.append(BuildingSpec(
            id='605085502#%d' % k, name='中央通りの長い棟 %d 軒目(推定)' % (k + 1), zone='A', ring=r, use_obb=True, floors=nf, floor_h=fh,
            base_z=base_for(s, 0.12), front=s['front'], replaces=['605085502'] if k == 0 else [],
            walls={1: WallFinish(*w1), '*': WallFinish(w2[0], w2[1], timber=tim)},
            facades={'front': Facade(bay=1.6, pattern={1: g1, 2: g2, 3: '.W.'}, noren=nor, frame='wood' if 'L' in g2 else 'alu',
                                     glass='#3c464d', lattice_col=DARK),
                     '*': Facade(bay=2.4, win='.W', ground='..', frame='alu', lod=0)},
            pents=[Pent(1, 'front', depth=0.9, slope=0.3, mat='kawara' if k % 2 == 0 else 'teppan', z=fh[0] - 0.2)],
            roof=Roof(rf[0], rf[1], slope=rf[2], eave=0.5, verge=0.4, axis=rax, color=['#4a4d52', '#5a4a40', '#7d8184', '#3f4146', '#6e3b32'][k],
                      hafu_col=DARK),
            attach=[Attach('sign', side='front', floor=1, z=fh[0] - 0.3, w=min(3.2, s['front_len'] * 0.7), h=0.42, style='yoko',
                           color=['#3a2a20', '#f0ede4', '#2d4a3a', '#efe9da', '#2b2725'][k], color2=DARK),
                    Attach('sign', side='front', floor=2, s=0.6, z=1.4, w=0.5, h=1.6, style='tate', color='#f2efe6', color2=DARK)]
            + ([Attach('nobori', side='front', s=1.2, n=1, color=['#d93a2b', '#e2b23a', '#3b6fb0'][k % 3])] if k in (0, 2, 3) else [])
            + ([Attach('lanterns', side='front', floor=1, z=fh[0] - 0.55, d=0.6, n=2, w=2.0)] if k == 3 else []),
            lod=1, age=0.4))
    s = site('605085502', arm)
    out.append(BuildingSpec(
        id='605085502#arm', name='中央通りの長い棟 奥の腕(推定)', zone='A', ring=arm, use_obb=False, floors=2, floor_h=[3.0, 2.8],
        base_z=base_for(s, 0.15), front=s['front'], replaces=[],
        walls={'*': WallFinish('spray', '#dcd6c9')},
        facades={'*': Facade(bay=2.6, win='W.', ground='.G', frame='alu', lod=0)},
        roof=Roof('gable', 'teppan', slope=0.35, eave=0.4, verge=0.3, color='#5d625f'),
        attach=[Attach('ac', side='*', n=2, w=1.3)], lod=1, age=0.4))
    return out


def seigetsudo():
    """御菓子司 清月堂(605546937、A_seigetsudo、K 6:39 f_134): 2 階、白漆喰+濃茶の柱梁、1 階はガラス張りと出入口、白い暖簾、
    平入りの深い軒(化粧垂木)、2 階の木の縦格子の手すり、ベンガラの縦板の袖壁、黒い吊り灯籠。"""
    s = site('605546937')
    tim = Timber('#3a2a20', w=0.12, posts='bay', beams=('bottom', 'top', 'head'))
    return BuildingSpec(
        id='605546937', name='御菓子司 清月堂', zone='A', floors=2, floor_h=[3.5, 2.8], base_z=base_for(s, 0.15), front=s['front'],
        walls={'*': WallFinish('plaster', '#efebe2', timber=tim)},
        side_walls={'right': {'*': WallFinish('louver', '#7a3324', pitch=0.15)}},
        facades={'front': Facade(bay=1.6, margin=0.25, pattern={1: 'GSSG.', 2: 'LLLL'}, frame='wood', glass='#4a5258', noren='#f0ece2',
                                 lattice_col='#3a2a20', sizes={'L': (1.3, 1.25, 0.7)}),
                 '*': Facade(bay=2.2, win='.L', ground='..', frame='wood', glass='#e6dfc9', lattice_col='#3a2a20', lod=1)},
        balconies=[Balcony(2, 'front', depth=0.55, z=0.0, rail='lattice', color='#3a2a20', rail_h=1.0)],
        pents=[Pent(1, 'front', depth=1.25, slope=0.3, mat='kawara', rafters=True, z=3.35)],
        roof=Roof('gable', 'kawara', slope=0.5, eave=1.0, verge=0.5, axis=(s['front'] + 90) % 360, hafu_col='#3a2a20', soffit_col='#6b4f3a', rafters=True),
        attach=[Attach('sign', side='front', floor=1, z=3.0, w=3.6, h=0.75, style='yoko', color='#7a5a3a', color2='#3a2a20', text='清月堂(右書き「堂月清」)'),
                Attach('sign', side='front', floor=1, s=0.55, z=2.85, w=0.32, h=1.1, style='flat', color='#7a5a3a', color2='#3a2a20', text='創業 大正十二年'),
                Attach('lanterns', side='front', floor=1, z=3.25, d=1.05, n=3, w=4.6, color='#efe9da', color2='#1e1c1b'),
                Attach('ac', side='back', n=1)],
        lod=2, age=0.3, note='正面は中央通りへの向き(OSM の外形からの計算)。看板の字は K 6:39 で読めた')


def hanaingen_cafe():
    """カフェ花いんげん(菓匠清月堂 門前通り店、954910750、A_seigetsudo、K 6:36 f_133): 白漆喰の壁と古い木の柱、赤茶の縦格子の袖壁、格子ガラスの引き戸、黒い吊り灯籠。"""
    s = site('954910750')
    tim = Timber('#4a3426', w=0.13, posts='bay', beams=('bottom', 'top', 'head'))
    return BuildingSpec(
        id='954910750', name='カフェ花いんげん', zone='A', floors=2, floor_h=[3.3, 2.8], base_z=base_for(s, 0.15), front=s['front'], use_obb=True,
        walls={'*': WallFinish('plaster', '#ece8dd', timber=tim)},
        side_walls={'left': {1: WallFinish('louver', '#7a3324', pitch=0.15)}},
        facades={'front': Facade(bay=1.5, pattern={1: '.DDG.', 2: '.LL.'}, frame='wood', glass='#4a5258', lattice_col='#4a3426', noren='#f0ece2'),
                 '*': Facade(bay=2.2, win='.W', ground='..', frame='wood', lod=0)},
        pents=[Pent(1, 'front', depth=0.9, slope=0.3, mat='kawara', z=3.15)],
        roof=Roof('gable', 'kawara', slope=0.5, eave=0.6, verge=0.45, axis=(s['front'] + 90) % 360, hafu_col='#3a2a20'),
        attach=[Attach('lanterns', side='front', floor=1, z=3.0, d=0.75, n=2, w=2.6, color='#efe9da', color2='#1e1c1b'),
                Attach('noren', side='front', floor=1, w=1.4, z=2.35, color='#f0ece2'),
                Attach('ac', side='back', n=1)],
        lod=2, age=0.3, note='暖簾「菓匠 清月堂」「花いんげん」(K 6:36)は文字面なし')


def lawson():
    """ローソン(895855244、A_lawson_terminal、W 0:30 f_11): 2 階、妻入り(南西の交差点側)、2 階は黒い縦板と白い額縁の窓 2 つ、
    破風に白い丸時計窓、1 階はガラスの店舗と緑黒の庇、庇の上に LAWSON。"""
    s = site('895855244')
    return BuildingSpec(
        id='895855244', name='ローソン', zone='A', floors=2, floor_h=[3.7, 2.8], base_z=base_for(s, 0.15), front=233,
        walls={1: WallFinish('board_v', '#2f2c2a', pitch=0.3), 2: WallFinish('board_v', '#242120', pitch=0.15)},
        facades={'front': Facade(bay=1.6, margin=0.4, pattern={1: 'GSSSSG', 2: '..W..W..'}, frame='white', glass='#3a454c', trim=True,
                                 sizes={'W': (1.25, 1.25, 0.7)}),
                 'SE': Facade(bay=2.0, pattern={1: 'SSSS..', 2: '.W..W.'}, frame='white', glass='#3a454c', trim=True),
                 '*': Facade(bay=2.4, win='.W', ground='..', frame='alu', lod=0)},
        pents=[Pent(1, ['front', 'SE'], depth=1.0, slope=0.3, mat='kawara', color='#2c3a33', z=3.45)],
        roof=Roof('gable', 'metal', slope=0.55, eave=0.35, verge=0.35, color='#3f4448', hafu_col='#1f1d1c', soffit_col='#2a2826'),
        attach=[Attach('zA_round', side='front', floor=2, w=0.4, prm=dict(gable=True), z=1.05, color='#f0eee8', color2='#3a3a3a'),
                Attach('sign', side='front', floor=1, z=3.95, w=2.6, h=0.4, style='yoko', color='#2c3a33', color2='#1f1d1c', text='LAWSON', d=0.75),
                Attach('ac', side='back', n=3, w=1.2), Attach('pipe', side='back', s=0.8)],
        lod=2, age=0.3)


def oshokujidokoro():
    """お食事処(ローソンの北西隣、895855246 と推定。A_lawson_terminal、W 0:30 f_11): 2 階、妻入り、白い塗り壁、2 階の妻面に黒い縦格子の窓 3 連、
    1 階は木の格子と腰壁、濃灰の下屋。看板「お食事処」(縦の看板は判読不能)。OSM の名前は「旬彩茶屋 夢花」だが動画の看板と一致は確認できない。"""
    s = site('895855246')
    return BuildingSpec(
        id='895855246', name='お食事処(旬彩茶屋 夢花の外形、対応は推定)', zone='A', floors=2, floor_h=[3.3, 2.8], base_z=base_for(s, 0.15), front=234,
        walls={1: WallFinish('plaster', '#ebe7de', koshi=(0.9, 'board_v', '#4a3426')), '*': WallFinish('plaster', '#ebe7de')},
        facades={'front': Facade(bay=1.6, pattern={1: 'DLLD', 2: '.LLL.'}, frame='black', glass='#2e2a27', lattice_col='#1f1c1a', sizes={'L': (1.3, 1.15, 0.75)}),
                 '*': Facade(bay=2.4, win='.W', ground='.W', frame='alu', lod=0)},
        pents=[Pent(1, ['front', 'SE'], depth=1.0, slope=0.3, mat='kawara', z=3.05)],
        roof=Roof('gable', 'kawara', slope=0.5, eave=0.5, verge=0.4, hafu_col=DARK),
        attach=[Attach('sign', side='front', floor=2, z=2.35, w=2.6, h=0.5, style='yoko', color='#f2efe6', color2=DARK, text='お食事処'),
                Attach('sign', side='front', floor=2, s=-0.6, z=1.2, w=0.45, h=1.8, style='flat', color='#f2efe6', color2=DARK),
                Attach('sign', side='front', floor=1, z=2.7, w=1.6, h=0.35, style='yoko', color='#c08a4a', color2=DARK),
                Attach('ac', side='back', n=2, w=1.2)],
        lod=2, age=0.35)


def daito_entrance():
    """大東館 正面玄関(r12857070_2、OSM「大東舘(正面玄関)」の点の位置): 本館の西の細い楔形。1 階のガラスの玄関と陸屋根の庇(推定)。"""
    s = site('r12857070_2')
    return BuildingSpec(
        id='r12857070_2', name='大東館 正面玄関(推定)', zone='A', floors=1, floor_h=4.2, base_z=base_for(s, 0.15), front=290,
        walls={'*': WallFinish('spray', '#e6e5df')},
        facades={'*': Facade(bay=2.2, win='G', ground='G', frame='dark', glass='#34414a', lod=1)},
        roof=Roof('flat', parapet=0.6), lod=1, age=0.3)


def daito_annex():
    """大東館 別棟(r12857070_4、A_daitokan の relation の東の outer): 外観は動画に出ない。本館と同じ白い吹付・陸屋根、6 階(推定)。"""
    s = site('r12857070_4')
    return BuildingSpec(
        id='r12857070_4', name='大東館 別棟(推定)', zone='A', floors=6, floor_h=3.0, base_z=base_for(s, 0.2), front=s['front'],
        walls={'*': WallFinish('spray', '#e3e1da')},
        facades={'*': Facade(bay=3.2, win='W', ground='.W', frame='dark', glass='#3c4850', lod=0)},
        roof=Roof('flat', parapet=0.9, penthouse=[(2.0, 0.0, 5.0, 4.0, 2.8)]),
        lod=0, age=0.4, note='階数は推定(OSM の 9 は relation 全体のタグ)')


# ====================================================================== 推定(動画で確認できない棟)
HAND_IDS = {'605309932', 'r12857070_1', 'r12857070_0', 'r12857070_2', 'r12857070_4', '605309933', '605309935', '896878998',
            '605309940', '605309937', '912422960', '912422971', '605085501', '605085502', '605546937', '954910750', '895855244', '895855246'}

PALETTES = {
    # 湯畑の東(黒・濃茶と白が交互、妻入りの 3 階)
    'east': [('plaster', '#eeebe4', True), ('board_v', '#2a2624', False), ('paint', '#d8c9ad', False), ('board_v', '#4a3528', False)],
    # 中央通り(白・淡い緑・茶・黒が混ざる)
    'chuo': [('paint', '#ecebe6', False), ('paint', '#d3ded3', False), ('board_h', '#7a5a40', False), ('board_v', '#2b2725', False),
             ('mortar', '#d9d2c3', False), ('plaster', '#efebe2', True)],
    # 中央通りの南(白漆喰+濃茶の柱梁、黒い縦板、茶の板)
    'south': [('plaster', '#eeeae0', True), ('board_v', '#2a2624', False), ('board_h', '#8a6a4c', False), ('paint', '#e8e4da', False),
              ('mortar', '#c9c0b0', False), ('plaster', '#efebe2', True)],
    # 裏の住宅・小さな旅館(吹付・サイディング)
    'back': [('spray', '#ece9e1', False), ('spray', '#e3dccb', False), ('spray', '#d9d6cf', False), ('board_h', '#c7c2b8', False),
             ('board_h', '#a8b0b3', False), ('mortar', '#cfc6b5', False), ('tile', '#c8b9a0', False)],
    # 旅館・ホテル
    'ryokan': [('spray', '#eae7df', False), ('tile', '#cdbfa6', False), ('spray', '#e2d9c7', False), ('plaster', '#ece8dd', True)],
}
METAL_COLS = ['#5a4a40', '#6e3b32', '#4c5866', '#4e5e50', '#7d8184', '#3f4146', '#7a5a3c']


def _rs(fid):
    return np.random.RandomState(zlib.crc32(fid.encode('utf-8')) & 0xffffffff)


def style_of(s, tags):
    x, y = s['c']
    if s['area'] < 25:
        return 'tiny'
    if tags.get('building') == 'roof':
        return 'canopy'
    if tags.get('tourism') in ('hotel', 'guest_house') or tags.get('building') in ('hotel', 'apartments') or s['area'] >= 300:
        return 'ryokan'
    if -5 < x < 55 and -48 < y < 8 and s['main_d'] < 18:
        return 'east'
    if s['main_d'] < 10 and (s['main_id'] == CHUO or s['main_id'] == -1) and y > -100:
        return 'chuo'
    if s['main_d'] < 10 and y <= -100 and x < 75:
        return 'south'
    if s['main_d'] < 10 and x < 75:
        return 'chuo'
    return 'back'


def floors_of(st, s, tags, rs):
    lv = tags.get('building:levels')
    if lv and str(lv).isdigit() and int(lv) <= 6:
        return int(lv), 'OSM'
    a = s['area']
    if st == 'tiny':
        return 1, '面積'
    if st == 'canopy':
        return 1, 'building=roof'
    if st == 'ryokan':
        return (4 if a > 600 else 3), '旅館・面積'
    if a < 55:
        return (1 if a < 35 else 2), '面積'
    if st == 'east':
        return 3, '東の並び(3 階)'
    if st in ('chuo',):
        return (3 if (a > 140 and rs.rand() < 0.5) else 2), '中央通り(2〜3 階)'
    if st == 'south':
        return (3 if rs.rand() < 0.2 else 2), '南の店並び(2 階中心)'
    return (3 if (a > 160 and rs.rand() < 0.45) else 2), '裏(面積)'


def _generic(fid, ring=None, tags=None, name=None, sid=None, replaces=None):
    """推定の棟: OSM の外形+階数+通りの様式から spec を作る。看板は枠だけ。"""
    b = bld(fid)
    tags = tags if tags is not None else (b['tags'] if b else {})
    s = site(fid, ring)
    rs = _rs(sid or fid)
    st = style_of(s, tags)
    nf, why = floors_of(st, s, tags, rs)
    shop_street = st in ('east', 'chuo', 'south')
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
    if st == 'ryokan':
        fh = [3.3] + [3.0] * (nf - 1)
    if st == 'tiny':
        fh = [2.5 + 0.4 * rs.rand()]
    # ---- 屋根
    ratio = s['ratio']
    use_obb = ratio >= 0.9 or (ratio >= 0.8 and a < 160)
    pitched = use_obb or ratio >= 0.84
    tsuma = rs.rand() < (0.7 if shop_street else 0.35)
    rax = s['front'] if tsuma else (s['front'] + 90) % 360
    if st == 'ryokan':
        if pitched and nf <= 3 and rs.rand() < 0.6:
            roof = Roof('irimoya' if rs.rand() < 0.5 else 'hip', 'kawara', slope=0.45, eave=0.8, verge=0.4, axis='long', irimoya_k=0.5,
                        hafu_col=DARK, gable_style='plaster')
        else:
            roof = Roof('flat', parapet=0.8 + 0.3 * rs.rand(),
                        penthouse=[(rs.uniform(-2, 2), rs.uniform(-1, 1), 3.0, 2.6, 2.4)] if a > 200 else [])
    elif st == 'canopy' and ratio < 0.8:
        roof = Roof('flat', parapet=0.15, coping_col='#6d6a64')
    elif st == 'canopy':
        roof = Roof('hip', 'teppan', slope=0.3, eave=0.4, color=METAL_COLS[rs.randint(len(METAL_COLS))], gutters=False)
    elif not pitched:
        roof = Roof('flat', parapet=0.6 + 0.4 * rs.rand())
    elif shop_street:
        mat = 'kawara' if rs.rand() < 0.65 else 'teppan'
        roof = Roof('gable', mat, slope=round(0.42 + 0.2 * rs.rand(), 2), eave=0.5 + 0.3 * rs.rand(), verge=0.4, axis=rax,
                    color=None if mat == 'kawara' else METAL_COLS[rs.randint(len(METAL_COLS))], hafu_col=DARK,
                    kengyo=(mat == 'kawara' and tsuma and rs.rand() < 0.4))
    else:
        kind = ['gable', 'gable', 'hip', 'shed'][rs.randint(4)] if a > 30 else ['gable', 'shed'][rs.randint(2)]
        mat = 'teppan' if rs.rand() < 0.55 else 'metal'
        roof = Roof(kind, mat, slope=round(0.28 + 0.17 * rs.rand(), 2), eave=0.4 + 0.25 * rs.rand(), verge=0.35, axis=rax if kind == 'gable' else 'long',
                    color=METAL_COLS[rs.randint(len(METAL_COLS))], hafu_col='#5a5048' if rs.rand() < 0.5 else '#e3e0d8',
                    soffit_col='#d9d3c6')
    # ---- 窓割り
    if shop_street:
        g = ['S', 'SG', 'GS', 'S.', 'H', 'SSG', 'G.'][rs.randint(7)]
        w = ['W', 'L', 'W.', '.W', 'R', 'T.', 'LL.'][rs.randint(7)]
        nor = [None, None, '#273149', '#7a2a24', '#e9e4d8', '#2f4a3a', '#5a4632'][rs.randint(7)]
        front_fac = Facade(bay=1.6 + 0.5 * rs.rand(), ground=g, win=w, noren=nor, frame=['alu', 'wood', 'dark', 'white'][rs.randint(4)],
                           glass=['#3c464d', '#46535c', '#e6dfc9'][rs.randint(3)] if 'L' not in w else '#e6dfc9', lattice_col=DARK,
                           trim=rs.rand() < 0.3)
        side_fac = Facade(bay=2.4, win='.W' if rs.rand() < 0.5 else 'W.', ground='..', frame='alu', lod=0)
    elif st == 'ryokan':
        front_fac = Facade(bay=2.6, win='W', ground='G.W', frame='alu' if rs.rand() < 0.6 else 'dark', glass='#3c4850', fins=(0.4, 0.25) if rs.rand() < 0.3 else None)
        side_fac = Facade(bay=2.8, win='W.', ground='.W', frame='alu', lod=0)
    elif st == 'tiny' or st == 'canopy':
        front_fac = Facade(bay=2.0, pattern={1: ['P', 'G', 'D', '.W'][rs.randint(4)]}, frame='alu', lod=0)
        side_fac = Facade(bay=2.0, win='.', ground='.', lod=0)
    else:
        front_fac = Facade(bay=2.2, ground=['G.W', '.GW', 'W.G', 'GW'][rs.randint(4)], win=['W', 'W.', '.W', 'WW.'][rs.randint(4)],
                           frame='alu', glass='#46535c', lod=None)
        side_fac = Facade(bay=2.6, win='.W', ground='W.', frame='alu', lod=0)
    # ---- 品質(道から見える棟だけ lod1、正面以外は面だけ)
    near = s['road_d'] < 8.0
    lod = 1 if (near and a >= 30 and st not in ('tiny', 'canopy')) else 0
    if st == 'ryokan' and (s['road_d'] > 6 or len(s['ring']) > 16):
        lod = 0
    if not near:
        front_fac = dreplace(front_fac, lod=0)
    facades = {'front': front_fac, '*': side_fac}
    # 角地(横の辺も道に面する)
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
        elif rs.rand() < 0.2:
            setbacks[2] = {'front': -0.35}
        if rs.rand() < 0.75:
            attach.append(Attach('sign', side='front', floor=1, z=fh[0] - 0.35, w=round(min(3.4, s['front_len'] * 0.7), 2), h=0.42, style='yoko',
                                 color=['#3a2a20', '#f0ede4', '#2d4a3a', '#efe9da', '#2b2725', '#7a2a24'][rs.randint(6)], color2=DARK))
        if rs.rand() < 0.4:
            attach.append(Attach('sign', side='front', floor=2, s=0.5, z=1.2, w=0.5, h=1.5, style='tate', color='#f2efe6', color2=DARK))
        if rs.rand() < 0.2:
            attach.append(Attach('lanterns', side='front', floor=1, z=fh[0] - 0.5, d=0.6, n=2, w=min(2.4, s['front_len'] * 0.5),
                                 color='#c03a2b' if rs.rand() < 0.6 else '#efe9da'))
        if rs.rand() < 0.15:
            attach.append(Attach('nobori', side='front', s=0.9, n=1, color=['#d93a2b', '#e2b23a', '#3b6fb0'][rs.randint(3)]))
    elif st == 'ryokan':
        if rs.rand() < 0.5 and nf >= 3:
            balconies.extend(Balcony(f, 'front', depth=0.9, rail=['wall', 'steel', 'wood'][rs.randint(3)], s0=0.8, s1=-0.8,
                                     color='#e9e8e3') for f in range(2, nf + 1))
        if lod >= 1 and rs.rand() < 0.5:
            attach.append(Attach('porch', side='front', at=0.3 + 0.4 * rs.rand(), w=3.2, d=2.0, h=3.0, color2='#5a4a3e',
                                 prm=dict(roof='shed', mat='kawara', slope=0.3, platform=True)))
    elif st == 'back' and nf >= 2:
        if rs.rand() < 0.35:
            balconies.append(Balcony(2, 'front', depth=0.8, rail=['steel', 'wood'][rs.randint(2)], s0=0.5, s1=-0.5))
        if rs.rand() < 0.35:
            pents.append(Pent(1, 'front', depth=0.7, slope=0.3, mat='teppan', color=METAL_COLS[rs.randint(len(METAL_COLS))], s0=0.3, s1=-0.3))
    if st not in ('tiny', 'canopy'):
        n_ac = 1 + rs.randint(3)
        attach.append(Attach('ac', side=['left', 'right', 'back'][rs.randint(3)], n=n_ac, w=1.2))
        if nf >= 2 and rs.rand() < 0.4:
            attach.append(Attach('ac', side=['left', 'right'][rs.randint(2)], floor=2, z=0.2, n=1))
        if rs.rand() < 0.4:
            attach.append(Attach('pipe', side=['left', 'right', 'back'][rs.randint(3)], s=0.6))
    # ---- 床の高さ(正面の地面=道)と基礎
    drop = s['z_front'] - s['z_min']
    found = 'stone' if drop > 1.4 else 'concrete'
    fh_ = 0.12 if shop_street else 0.3
    nm = name or tags.get('name') or ''
    sp = BuildingSpec(
        id=sid or fid, name=nm or '(無名)', zone='A', ring=ring, floors=nf, floor_h=fh, base_z=base_for(s, fh_), front=s['front'],
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


def special_generic():
    """名前はあるが外観が動画に出ない棟の型(推定、看板の文字は書かない)。"""
    out = []
    # 目洗い地蔵尊(小さな祠): 1 階、格子戸、瓦の切妻、石の基壇
    s = site('956109288')
    out.append(BuildingSpec(
        id='956109288', name='目洗い地蔵尊(祠、形は推定)', zone='A', floors=1, floor_h=2.5, base_z=base_for(s, 0.45), front=s['front'],
        found='stone', found_h=0.45, found_col='#8b877e', use_obb=True,
        walls={'*': WallFinish('board_v', '#6b4a33', pitch=0.25)},
        facades={'front': Facade(bay=1.8, pattern={1: 'DD'}, frame='wood', lattice_col='#4a3426'), '*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('gable', 'kawara', slope=0.6, eave=0.7, verge=0.5, axis=s['front'], kengyo=True, hafu_col='#4a3426'),
        attach=[Attach('lanterns', side='front', floor=1, z=2.2, d=0.5, n=2, w=1.6, color='#efe9da')],
        lod=1, age=0.5, note='推定: 祠の型(OSM place_of_worship)'))
    out[-1].zA_style, out[-1].zA_why = 'shrine', 'OSM の用途'
    # 瑠璃乃湯(共同浴場): 1 階の木造、切妻の鉄板、暖簾の入口
    s = site('954965045')
    out.append(BuildingSpec(
        id='954965045', name='瑠璃乃湯(共同浴場、形は推定)', zone='A', floors=1, floor_h=3.0, base_z=base_for(s, 0.2), front=s['front'], use_obb=True,
        walls={'*': WallFinish('board_h', '#8b6a50', pitch=0.22)},
        facades={'front': Facade(bay=1.6, pattern={1: '.D.w'}, frame='wood', lattice_col='#4a3426'), '*': Facade(bay=2.0, pattern={1: '.w.'}, lod=0)},
        roof=Roof('gable', 'teppan', slope=0.5, eave=0.5, verge=0.4, color='#5a4a40', axis=s['front'] + 90),
        attach=[Attach('noren', side='front', floor=1, w=1.0, z=2.1, color='#273149'), Attach('pipe', side='back', s=0.8)],
        lod=1, age=0.5, note='推定: 共同浴場の型(OSM public_bath)'))
    out[-1].zA_style, out[-1].zA_why = 'bath', 'OSM の用途'
    return out


def generics():
    F = get_field()
    done = HAND_IDS | {'956109288', '954965045'}
    out = []
    for b in F.blds:
        if b['zone'] != 'A' or b['id'] in done:
            continue
        out.append(_generic(b['id']))
    return out


def specs():
    """区域A の全 spec(手作り+推定)。kd_parts.zone_specs('A') と kd_buildings.build_buildings が呼ぶ。"""
    hand = [chichiya(), *daitokan(), daito_entrance(), daito_annex(), kurotama(), yamabiko(), *twin_gables(), hira_no_ie(), soan(),
            white3(), *tsukinoi(), honda(), *chuo_long(), seigetsudo(), hanaingen_cafe(), lawson(), oshokujidokoro()]
    for sp in hand:
        if not hasattr(sp, 'zA_style'):
            sp.zA_style, sp.zA_why = 'hand', 'カード'
    return hand + special_generic() + generics()


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
            print('%-20s %-34s %-7s lod%d f%d %-8s tris %6d (%.2fs)' % (sp.id, sp.name[:34], getattr(sp, 'zA_style', ''), b.info['lod'], sp.floors,
                                                                       sp.roof.kind, b.info['tris'], time.time() - t1))
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
        P.run_zone('A')
