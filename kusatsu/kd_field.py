# -*- coding: utf-8 -*-
"""kd_field.py -- 湯畑ジオラマの高さ場(numpy だけ。Blender 外でも動く)。
DEM(双3次)を土台に、池 → 道 → 石段 → 建物の敷地 の順で「平らにする/なだらかにする」を重ねて 1 m 格子の標高場 E(海抜 m)を作る。
高さは 1:1(誇張しない)。Blender の Z = E - ZBASE。
"""
import math

import numpy as np

import kd_common as C

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
        osm = self.osm
        ponds = C.osm_ways(osm, lambda t: t.get('natural') == 'water' and t.get('water') == 'pond')
        ends = [(i, np.array(p[:-1] if p[0] == p[-1] else p)) for i, t, p in ponds]
        # 湯畑本体 = 原点付近の2つの端のポリゴン。残りは光泉寺の小さな池。
        yub = [e for e in ends if np.hypot(*e[1].mean(axis=0)) < 60]
        other = [(i, p) for i, p in ends if np.hypot(*p.mean(axis=0)) >= 60]
        a, b = yub[0][1], yub[1][1]
        if a.mean(axis=0)[1] > b.mean(axis=0)[1]:
            a, b = b, a                                    # a = 南西の端、b = 北東の端
        ca, cb = a.mean(axis=0), b.mean(axis=0)
        ra = float(np.hypot(*(a - ca).T).mean() * 1.05)
        rb = float(np.hypot(*(b - cb).T).mean() * 1.05)
        neck = 4.2
        L = float(np.hypot(*(cb - ca)))
        u = (cb - ca) / L
        nvec = np.array([-u[1], u[0]])
        # 瓢箪形の外形: 軸に沿った半幅 r(s) = max(球1, 球2, 首)
        ss = np.linspace(0, L + ra + rb, 240)
        # 軸上の位置 s' は ca から測る: -ra .. L+rb
        s = np.linspace(-ra, L + rb, 220)
        r = np.maximum(np.sqrt(np.maximum(ra ** 2 - s ** 2, 0)), np.sqrt(np.maximum(rb ** 2 - (s - L) ** 2, 0)))
        r = np.maximum(r, np.where((s > 0) & (s < L), neck, 0.0))
        r[0] = r[-1] = 0
        left = [ca + u * si + nvec * ri for si, ri in zip(s, r)]
        right = [ca + u * si - nvec * ri for si, ri in zip(s, r)][::-1]
        outline = [tuple(p) for p in left + right]
        # 重複点(両端 r=0)を除く
        outline = C.clean_ring(outline)
        self.pond = dict(ca=ca, cb=cb, ra=ra, rb=rb, neck=neck, outline=C.ccw(outline), others=[])
        # 周囲の標高(池の縁の外 1〜4 m)を平均して縁の高さに
        X, Y = self.X, self.Y

        def sd(px, py):
            d1 = np.hypot(px - ca[0], py - ca[1]) - ra
            d2 = np.hypot(px - cb[0], py - cb[1]) - rb
            t = np.clip(((px - ca[0]) * u[0] + (py - ca[1]) * u[1]), 0, L)
            d3 = np.hypot(px - (ca[0] + u[0] * t), py - (ca[1] + u[1] * t)) - neck
            return np.minimum(np.minimum(d1, d2), d3)
        D = sd(X, Y)
        ring = (D > 1.0) & (D < 5.0)
        z_rim = float(np.median(self.E[ring]))
        self.pond.update(z_rim=z_rim, z_water=z_rim - 0.45, z_floor=z_rim - 1.1)
        floor = D < 0.0
        shoulder = (D >= 0.0) & (D < 3.0)
        fade = 1.0 - C.smoothstep((D - 3.0) / 3.0)
        E = self.E
        E = np.where(floor, z_rim - 1.1, E)
        E = np.where(shoulder, z_rim, E)
        E = np.where((D >= 3.0) & (D < 6.0), E * (1 - fade) + z_rim * fade, E)
        self.E = E
        self.pond_sd = D
        # 光泉寺の池など
        for i, p in other:
            pz = float(np.median(self.bil(p[:, 0], p[:, 1])))
            self.pond['others'].append(dict(id=i, ring=C.ccw([tuple(q) for q in p]), z_water=pz - 0.25, z_floor=pz - 0.8))
            m = C.points_in_poly(X, Y, [tuple(q) for q in p])
            self.E = np.where(m, pz - 0.8, self.E)
        self.log('  pond: axis len %.1f m, ra %.1f rb %.1f, rim z %.2f (water %.2f)' % (L, ra, rb, z_rim, z_rim - 0.45))

    # ------------------------------------------------ 道
    def build_roads(self):
        osm = self.osm
        ways = C.osm_ways(osm, lambda t: t.get('highway') in ROAD_CLASS and t.get('area') != 'yes' and t.get('tunnel') != 'yes'
                          and t.get('layer', '0') not in ('-1',) and t.get('tunnel') != 'building_passage')
        roads = []
        sx, sy, sz, shw = [], [], [], []
        for wid, t, pts in ways:
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
            if wid in HOSEN_WAYS:
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
        for b in blds:
            m = C.points_in_poly(self.X, self.Y, b['ring'])
            if not m.any():
                z = float(self.bil(*b['c']))
                b['pad'] = z
                continue
            z = float(np.mean(self.E[m]))
            b['pad'] = z
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
