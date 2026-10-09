# -*- coding: utf-8 -*-
"""kd_field.py -- 湯畑ジオラマの高さ場(numpy だけ。Blender 外でも動く)。
DEM(双3次)を土台に、池 → 道 → 石段 → 建物の敷地 の順で「平らにする/なだらかにする」を重ねて 1 m 格子の標高場 E(海抜 m)を作る。
高さは 1:1(誇張しない)。Blender の Z = E - ZBASE。
"""
import math

import numpy as np

import kd_common as C
import kd_yb_layout as YB

# OSM highway -> (半幅 m, 面の種類)
ROAD_CLASS = {
    'trunk': (4.5, 'asphalt'), 'residential': (3.0, 'asphalt'), 'unclassified': (2.8, 'asphalt'),
    'service': (1.8, 'asphalt2'), 'pedestrian': (2.5, 'paving'), 'footway': (1.1, 'paving'), 'path': (0.9, 'path'),
}
ROAD_RANK = {'path': 1, 'footway': 2, 'service': 3, 'pedestrian': 4, 'unclassified': 5, 'residential': 6, 'trunk': 7}

# 光泉寺の石段 (D_stairs.md の数値。座標 x,y と標高 z は DEM5A 海抜 m)。段数は動画からの推定(±10)。
# 登る向きは南西。width は主階段の幅。
HOSEN = [
    dict(name='第1段', p0=(-49.7, -75.0), z0=1158.4, p1=(-68.0, -91.0), z1=1167.2, n=55, width=3.6, side=True, kind='main'),
    dict(name='山門の通路', p0=(-68.0, -91.0), z0=1167.2, p1=(-73.1, -95.7), z1=1167.9, n=0, width=3.0, side=False, kind='ramp'),
    dict(name='第2段', p0=(-73.1, -95.7), z0=1167.9, p1=(-86.3, -106.5), z1=1174.2, n=36, width=3.6, side=True, kind='main'),
    dict(name='踊り場', p0=(-86.3, -106.5), z0=1174.2, p1=(-92.3, -109.2), z1=1175.3, n=0, width=3.8, side=False, kind='ramp'),
    dict(name='第3段', p0=(-92.3, -109.2), z0=1175.3, p1=(-100.26, -111.93), z1=1178.7, n=22, width=3.6, side=True, kind='main'),
    dict(name='本堂前', p0=(-100.26, -111.93), z0=1178.7, p1=(-106.6, -114.1), z1=1178.7, n=0, width=3.8, side=False, kind='ramp'),
]
HOSEN_WAYS = {1252020895, 1252020894, 162319857, 1311925443, 1311927449, 1311927450, 1311927448}
# 建物の敷地を均さない区域(フェーズ5〜)。建物を本物にした区域は、地面を DEM+道のまま残し、1 階の床(正面の道の高さ)と
# 基礎(斜面の低い側へ伸びる)・地面に入る壁(高い側)で納める。均すと建物の周り 3 m に切り土の溝・盛り土の土手ができる(フェーズ2の課題)。
NOFLAT_ZONES = {'A'}


class Field:
    def __init__(self, osm, log=print):
        self.log = log
        self.dem = C.Dem()
        self.osm = osm
        self.res = 1.0
        self.half = 214.0
        self.xs = np.arange(-self.half, self.half + 1e-6, self.res)
        self.n = len(self.xs)
        X, Y = np.meshgrid(self.xs, self.xs)
        self.X, self.Y = X, Y
        self.E0 = self.dem.sample(X, Y)
        self.E = self.E0.copy()
        self.road_samples = None
        self.flights = []
        self.pond = None
        self.pads = []
        self.yb = YB.Layout(osm)          # 湯畑(フェーズ3)の配置
        self.build_all()

    # ------------------------------------------------ 補助
    def bil(self, x, y, arr=None):
        arr = self.E if arr is None else arr
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        fx = np.clip((x + self.half) / self.res, 0, self.n - 1.001)
        fy = np.clip((y + self.half) / self.res, 0, self.n - 1.001)
        ix = fx.astype(int)
        iy = fy.astype(int)
        tx = fx - ix
        ty = fy - iy
        return (arr[iy, ix] * (1 - tx) * (1 - ty) + arr[iy, ix + 1] * tx * (1 - ty)
                + arr[iy + 1, ix] * (1 - tx) * ty + arr[iy + 1, ix + 1] * tx * ty)

    def Z(self, x, y):
        """Blender Z (標高 - ZBASE)。"""
        return self.bil(x, y) - C.ZBASE

    def stamp(self, sx, sy, sz, shw, margin, label=''):
        """サンプル点群(位置・目標標高・半幅)の回廊を E に重ねる。回廊内は目標標高、外側 margin m で元の高さへなだらかに戻る。"""
        sx, sy, sz, shw = [np.asarray(a, dtype=np.float32) for a in (sx, sy, sz, shw)]
        px = self.X.ravel().astype(np.float32)
        py = self.Y.ravel().astype(np.float32)
        E = self.E.ravel().astype(np.float32).copy()
        reach = shw + margin
        rmax = float(reach.max())
        # サンプルを粗いセルに振り分けて探索を減らす
        cell = 12.0
        cx = np.floor((sx + self.half) / cell).astype(int)
        cy = np.floor((sy + self.half) / cell).astype(int)
        buckets = {}
        for i, key in enumerate(zip(cx.tolist(), cy.tolist())):
            buckets.setdefault(key, []).append(i)
        pcx = np.floor((px + self.half) / cell).astype(int)
        pcy = np.floor((py + self.half) / cell).astype(int)
        reach_cells = int(math.ceil(rmax / cell))
        out = E.copy()
        # 点を所属セルごとにまとめる
        order = np.lexsort((pcy, pcx))
        keys = pcx[order] * 100000 + pcy[order]
        uniq, start = np.unique(keys, return_index=True)
        start = list(start) + [len(order)]
        for ui, k in enumerate(uniq):
            ids = order[start[ui]:start[ui + 1]]
            cxk, cyk = int(pcx[ids[0]]), int(pcy[ids[0]])
            cand = []
            for dx in range(-reach_cells, reach_cells + 1):
                for dy in range(-reach_cells, reach_cells + 1):
                    cand.extend(buckets.get((cxk + dx, cyk + dy), ()))
            if not cand:
                continue
            cand = np.array(cand)
            d2 = (px[ids][:, None] - sx[cand][None, :]) ** 2 + (py[ids][:, None] - sy[cand][None, :]) ** 2
            d = np.sqrt(d2)
            hw = shw[cand][None, :]
            near = d - hw                                  # 回廊の縁からの距離
            nmin = near.min(axis=1)
            w = 1.0 - C.smoothstep(nmin / max(margin, 1e-3))
            if not (w > 0).any():
                continue
            wt = np.where(near < margin, 1.0 / (np.maximum(near, 0) ** 2 + 0.6), 0.0)
            ws = wt.sum(axis=1)
            tz = (wt * sz[cand][None, :]).sum(axis=1) / np.maximum(ws, 1e-9)
            upd = w > 0
            idu = ids[upd]
            out[idu] = E[idu] * (1 - w[upd]) + tz[upd] * w[upd]
        self.E = out.reshape(self.E.shape).astype(np.float64)
        if label:
            self.log('  stamp %s: %d samples' % (label, len(sx)))

    # ------------------------------------------------ 池(湯畑)
    def build_pond(self):
        """光泉寺の小池など(湯畑以外の池)。湯畑の池・滝壺は build_yubatake と kd_yubatake.py。"""
        osm = self.osm
        ponds = C.osm_ways(osm, lambda t: t.get('natural') == 'water' and t.get('water') == 'pond')
        ends = [(i, np.array(p[:-1] if p[0] == p[-1] else p)) for i, t, p in ponds]
        other = [(i, p) for i, p in ends if np.hypot(*p.mean(axis=0)) >= 60]
        self.pond = dict(others=[])
        X, Y = self.X, self.Y
        for i, p in other:
            pz = float(np.median(self.bil(p[:, 0], p[:, 1])))
            self.pond['others'].append(dict(id=i, ring=C.ccw([tuple(q) for q in p]), z_water=pz - 0.25, z_floor=pz - 0.8))
            m = C.points_in_poly(X, Y, [tuple(q) for q in p])
            self.E = np.where(m, pz - 0.8, self.E)

    def build_yubatake(self):
        """湯畑: 石柵の内側と柵の外 3.5 m を周回路の高さ(DEM に当てはめた平面 YB.rim)にし、外へ 4.5 m でなだらかに戻す。
        穴の中(湯畑の床・滝壺)は地形を描かない(kd_terrain.build_terrain)ので、ここでは周回路の高さで埋めておく。"""
        L = self.yb
        X, Y = self.X, self.Y
        m = (np.abs(X) < 70) & (np.abs(Y) < 75)
        x, y = X[m], Y[m]
        hole = L.in_hole(x, y)
        low = L.low_side(x, y)
        d_enc = YB.seg_nearest(x, y, L.enc_line)[0]
        target = YB.rim(x, y) + C.ZBASE
        w = np.where(hole, np.where(low, 0.0, 1.0), 1.0 - C.smoothstep((d_enc - 3.5) / 4.5))
        E = self.E.copy()
        E[m] = E[m] * (1 - w) + target * w
        self.E = E
        sd = np.full(self.E.shape, 99.0)
        sd[m] = np.where(hole, -1.0, 99.0)
        self.pond_sd = sd
        self.log('  yubatake: hole %.0f m2, rim z %.2f..%.2f, roads skipped inside the loop: %d' % (
            C.poly_area(L.hole), float(YB.rim(*np.array(L.enc_line).T).min()), float(YB.rim(*np.array(L.enc_line).T).max()),
            len(self.yb_skipped_ways)))

    # ------------------------------------------------ 道
    def build_roads(self):
        osm = self.osm
        ways = C.osm_ways(osm, lambda t: t.get('highway') in ROAD_CLASS and t.get('area') != 'yes' and t.get('tunnel') != 'yes'
                          and t.get('layer', '0') not in ('-1',) and t.get('tunnel') != 'building_passage')
        roads = []
        sx, sy, sz, shw = [], [], [], []
        # 湯畑の周回の車道の内側にある道(デッキ・周回路の小道)は湯畑側(kd_yubatake.py)で作るので外す
        P_all = [np.array(p) for _, _, p in ways]
        skip = set()
        for (wid, t, pts), P in zip(ways, P_all):
            ins = YB.inside(P[:, 0], P[:, 1], self.yb.loop) | (YB.seg_nearest(P[:, 0], P[:, 1], self.yb.loop, closed=True)[0] < 0.8)
            if ins.all():
                skip.add(wid)
        self.yb_skipped_ways = sorted(skip)
        for wid, t, pts in ways:
            if wid in skip:
                continue
            hw, kind = ROAD_CLASS[t['highway']]
            if t.get('width'):
                try:
                    hw = max(hw, float(t['width']) / 2.0)
                except ValueError:
                    pass
            if all(math.hypot(*p) > 235 for p in pts):
                continue
            rs, s = C.resample(pts, 1.5)
            if len(rs) < 2:
                continue
            e = self.dem.sample(rs[:, 0], rs[:, 1])
            # 路面の縦断をなだらかに: 移動平均(約 21 m)。端は元の高さのまま
            k = 7
            if len(e) >= 3:
                pad = np.concatenate([np.full(k, e[0]), e, np.full(k, e[-1])])
                sm = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
                # 端付近は元の勾配を残す
                wgt = np.clip(np.minimum(np.arange(len(e)), np.arange(len(e))[::-1]) / float(k), 0, 1)
                e = e * (1 - wgt) + sm * wgt
            roads.append(dict(id=wid, cls=t['highway'], kind=kind, hw=hw, pts=rs, surface=t.get('surface')))
            if t['highway'] in ('path', 'footway') and hw < 1.2:
                pass
            sx.extend(rs[:, 0]); sy.extend(rs[:, 1]); sz.extend(e); shw.extend([hw] * len(e))
            roads[-1]['e'] = e
        self.roads = roads
        # 太い道ほど後から(優先)重ねる
        self.log('  roads: %d ways, %d samples' % (len(roads), len(sx)))
        self.road_samples = (np.array(sx), np.array(sy), np.array(sz), np.array(shw))
        self.stamp(*self.road_samples, margin=3.0, label='roads')
        # 道の E を平らにした結果で路面高を取り直す(描画用)
        for r in roads:
            r['e'] = self.bil(r['pts'][:, 0], r['pts'][:, 1])

        # 歩行者エリア(area=yes)
        areas = C.osm_ways(osm, lambda t: t.get('highway') in ('pedestrian',) and t.get('area') == 'yes')
        self.ped_areas = [C.ccw(C.clean_ring(p)) for _, _, p in areas]
        for ring in self.ped_areas:
            m = C.points_in_poly(self.X, self.Y, ring)
            if m.any():
                self.E = np.where(m, np.median(self.E[m]), self.E)
        self.log('  pedestrian areas: %d' % len(self.ped_areas))

    # ------------------------------------------------ 石段
    def build_stairs(self):
        flights = []
        for h in HOSEN:
            f = dict(h)
            flights.append(f)
        # 光泉寺以外の OSM steps(短い階段)も 1:1 の段にする
        ways = C.osm_ways(self.osm, lambda t: t.get('highway') == 'steps' and t.get('tunnel') != 'yes')
        generic = 0
        for wid, t, pts in ways:
            if wid in HOSEN_WAYS or wid in YB.YB_STEPS:
                continue
            if math.hypot(*pts[0]) > 215 and math.hypot(*pts[-1]) > 215:
                continue
            # 光泉寺の石段の回廊と重なる OSM steps は手で作った段に任せる
            near_h = any(math.hypot(p[0] - q[0], p[1] - q[1]) < 5 for p in pts for q in [h['p0'] for h in HOSEN] + [h['p1'] for h in HOSEN])
            if near_h:
                continue
            rs, s = C.resample(pts, 1.0)
            if len(rs) < 2 or s[-1] < 2.0:
                continue
            e0 = float(self.bil(rs[0, 0], rs[0, 1])); e1 = float(self.bil(rs[-1, 0], rs[-1, 1]))
            dz = e1 - e0
            width = float(t.get('width', 1.8)) if str(t.get('width', '')).replace('.', '', 1).isdigit() else 1.8
            n = int(round(abs(dz) / 0.16))
            flights.append(dict(name='steps_%d' % wid, p0=tuple(pts[0]), z0=e0, p1=tuple(pts[-1]), z1=e1, n=n, width=width,
                                side=False, kind='main' if n >= 2 else 'ramp', way=wid, pts=[tuple(p) for p in pts]))
            generic += 1
        self.flights = flights
        sx, sy, sz, shw = [], [], [], []
        for f in flights:
            p0, p1 = np.array(f['p0']), np.array(f['p1'])
            L = float(np.hypot(*(p1 - p0)))
            m = max(2, int(L / 0.7) + 1)
            t = np.linspace(0, 1, m)
            px = p0[0] + (p1[0] - p0[0]) * t
            py = p0[1] + (p1[1] - p0[1]) * t
            pz = f['z0'] + (f['z1'] - f['z0']) * t - (0.05 if f['kind'] == 'main' else 0.0)
            hwid = f['width'] / 2.0 + (0.9 if f.get('side') else 0.5) + (1.2 if f.get('side') else 0.0)
            sx.extend(px); sy.extend(py); sz.extend(pz); shw.extend([hwid] * m)
        self.stamp(np.array(sx), np.array(sy), np.array(sz), np.array(shw), margin=2.2, label='stairs (%d generic + %d Hosenji)' % (generic, len(HOSEN)))

    # ------------------------------------------------ 建物の敷地
    def build_pads(self):
        blds = C.osm_buildings(self.osm)
        n = self.n
        val = np.full((n, n), np.nan)
        dist = np.full((n, n), 99, dtype=np.int32)
        self.pad_of = {}
        masks = []
        blds = [b for b in blds if b['id'] not in YB.YB_BUILDINGS]
        for b in blds:
            m = C.points_in_poly(self.X, self.Y, b['ring'])
            if not m.any():
                z = float(self.bil(*b['c']))
                b['pad'] = z
                continue
            z = float(np.mean(self.E[m]))
            b['pad'] = z
            if b['zone'] in NOFLAT_ZONES:      # 地面はそのまま(均し跡・切り土の穴を作らない)。床の高さと基礎は区域ファイル側
                continue
            val[m] = z
            dist[m] = 0
            masks.append(m)
        self.blds = blds
        known = ~np.isnan(val)
        for k in (1, 2, 3):
            acc = np.zeros((n, n)); cnt = np.zeros((n, n))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    sh = np.roll(np.roll(val, dy, axis=0), dx, axis=1)
                    ok = ~np.isnan(sh)
                    acc += np.where(ok, sh, 0); cnt += ok
            new = (~known) & (cnt > 0)
            val = np.where(new, acc / np.maximum(cnt, 1), val)
            dist = np.where(new, k, dist)
            known = known | new
        wmap = {0: 1.0, 1: 0.75, 2: 0.45, 3: 0.18}
        w = np.zeros((n, n))
        for k, wv in wmap.items():
            w = np.where(dist == k, wv, w)
        E = np.where(w > 0, self.E * (1 - w) + np.nan_to_num(val) * w, self.E)
        self.E = E
        self.pad_mask = dist == 0
        self.log('  pads: %d buildings' % len(blds))

    def build_all(self):
        self.log('field: DEM min %.2f max %.2f (within r=200: %.2f..%.2f)' % (self.E0.min(), self.E0.max(),
                 *self._minmax(self.E0)))
        self.build_roads()
        self.build_pond()
        self.build_yubatake()
        self.build_pads()
        sx, sy, sz, shw = self.road_samples
        # 敷地のなだらかな縁が路面に食い込まないよう、路面の芯をもう一度平らにする
        self.stamp(sx, sy, sz, shw * 0.95, margin=1.5, label='roads core again')
        self.build_stairs()
        # ごく弱い平滑(格子の段差ならし)。敷地の内側は元のまま
        E = self.E
        bl = (E + 0.25 * (np.roll(E, 1, 0) + np.roll(E, -1, 0) + np.roll(E, 1, 1) + np.roll(E, -1, 1))) / 2.0
        keep = self.pad_mask | (self.pond_sd < 0.0)
        self.E = np.where(keep, E, 0.5 * E + 0.5 * bl)
        self.log('field done: E %.2f..%.2f (r<=200: %.2f..%.2f)' % (self.E.min(), self.E.max(), *self._minmax(self.E)))

    def _minmax(self, arr):
        m = np.hypot(self.X, self.Y) <= 200.0
        return float(arr[m].min()), float(arr[m].max())
