# -*- coding: utf-8 -*-
"""kd_plants.py -- 草津 湯畑ジオラマ フェーズ10: 木と植物(動画・カードで確認できた位置だけ)。

確認できた位置(カードの記述):
  - 光泉寺 釈迦堂の参道の両側と境内: 赤松が多数(D_shakado、zone_D 9.)
  - 本堂の前庭: 松の古木 2〜3 本(f_000455)
  - 石段 第2段の両側: 笹・低木の斜面(zone_D 9.)
  - 奈良屋の前庭: 植栽の築山(紅葉・松)(C_naraya)
  - 益成屋の門前・清月堂の隣: 植え込み(C_masunariya、A_seigetsudo)
それ以外には置かない(`feedback_plants_confirmed_only`)。個々の木の位置は確認できた範囲の中で決めた推定。

出力: kusatsu-diorama/models/plants.glb、数値 output/kusatsu/plants_stats.json
実行: "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_plants.py   (--count は Blender 無し)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import kd_common as C  # noqa: E402
import kd_field as F  # noqa: E402
import kd_parts as P  # noqa: E402
import kd_props as K  # noqa: E402
from kd_parts import PB, lin, prism, hj  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]


def blob(pb, c, rx, rz, z0, col, seed, n=8, rings=4):
    """つぶれた球状の葉の塊(鉛直の n 角柱を段ごとに半径を変えて積む)。"""
    prof = [0.55, 0.95, 1.0, 0.8, 0.35]
    zs = [z0 + rz * 2 * i / (rings) for i in range(rings + 1)]
    for i in range(rings):
        r0 = rx * (prof[i] if rings == 4 else 1)
        r1 = rx * (prof[i + 1] if rings == 4 else 1)
        prism(pb, 'thatch', c, r0, r1, zs[i], zs[i + 1], n, hj(col, 0.12, seed, i), rot=0.3 * seed + 0.2 * i, top=(i == rings - 1), bottom=(i == 0))


def pine(pb, x, y, z, h, seed, old=False):
    trunk = lin('#5a4636')
    lean = (math.cos(seed * 2.1) * 0.06, math.sin(seed * 2.1) * 0.06)
    th = h * 0.72
    prism(pb, 'wood', (x, y), 0.17 * h / 8, 0.09 * h / 8, z - 0.2, z + th * 0.5, 6, trunk)
    prism(pb, 'wood', (x + lean[0] * th * 0.5, y + lean[1] * th * 0.5), 0.09 * h / 8, 0.05 * h / 8, z + th * 0.5, z + th, 6, trunk)
    g = lin('#34502d')
    for i, (f, r) in enumerate(((0.45, 0.30), (0.6, 0.26), (0.75, 0.22), (0.9, 0.15))):
        cx = x + lean[0] * th * f + math.cos(seed + i * 1.9) * 0.12 * h / 8
        cy = y + lean[1] * th * f + math.sin(seed + i * 1.9) * 0.12 * h / 8
        blob(pb, (cx, cy), r * h * (1.15 if old else 1.0), 0.07 * h, z + h * f, g, seed + i, n=8, rings=2)


def maple(pb, x, y, z, h, seed):
    prism(pb, 'wood', (x, y), 0.12, 0.07, z - 0.1, z + h * 0.5, 6, lin('#4a3a2e'))
    g = lin('#5c8a3a')
    blob(pb, (x, y), h * 0.34, h * 0.2, z + h * 0.42, g, seed, n=8, rings=4)
    blob(pb, (x + 0.5, y + 0.3), h * 0.22, h * 0.14, z + h * 0.52, hj(g, 0.1, seed), seed + 3, n=7, rings=4)


def shrub(pb, x, y, z, r, seed, col='#3f6a34'):
    blob(pb, (x, y), r, r * 0.5, z - 0.05, lin(col), seed, n=7, rings=4)


def sasa(pb, x, y, z, r, seed):
    """笹の株(細い葉を放射状に)。"""
    g = lin('#5d8a3e')
    for k in range(7):
        a = k * 2 * math.pi / 7 + seed
        L = r * (0.8 + 0.4 * ((seed * 7 + k * 13) % 5) / 5)
        top = (x + math.cos(a) * L * 0.9, y + math.sin(a) * L * 0.9, z + r * 1.3)
        base = (x + math.cos(a) * 0.05, y + math.sin(a) * 0.05, z)
        side = (-math.sin(a) * 0.06, math.cos(a) * 0.06, 0)
        pb.poly('thatch', [base, top, (top[0] + side[0], top[1] + side[1], top[2])], hj(g, 0.15, seed, k), (0, 0, 1))
        pb.poly('thatch', [base, (top[0] + side[0], top[1] + side[1], top[2]), top], hj(g, 0.15, seed, k), (0, 0, -1))


def build(field, site, raw, log=print):
    pb = PB()
    st = {}
    rs = np.random.RandomState(11)

    def cnt(k):
        st[k] = st.get(k, 0) + 1

    def gz(x, y):
        return float(field.Z(x, y))

    def ok(x, y, rb=1.2):
        return math.hypot(x, y) < 192 and not site.in_building(x, y, rb) and not site.on_other_road(x, y, None, 0.5)

    bld = {b['id']: b for b in C.osm_buildings(field.osm)}

    def cen(i):
        return np.array(bld[i]['c']) if i in bld else None

    # 1) 釈迦堂の参道の両側と境内: 赤松
    c = cen('912422963')
    if c is not None:
        placed = 0
        for k in range(60):
            a = rs.uniform(0, 2 * math.pi)
            r = rs.uniform(9, 26)
            x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
            if ok(x, y, 2.5) and all(math.hypot(x - q[0], y - q[1]) > 4.5 for q in [(0, 0)] if False):
                pine(pb, x, y, gz(x, y), rs.uniform(7, 10), k)
                cnt('pine_shaka')
                placed += 1
                if placed >= 9:
                    break
    # 2) 本堂の前庭: 松の古木 3 本
    for (x, y) in ((-104.0, -119.0), (-110.5, -109.5), (-98.0, -113.5)):
        if ok(x, y, 1.0):
            pine(pb, x, y, gz(x, y), 9.5, int(abs(x)), old=True)
            cnt('pine_honden')
    # 3) 第2段・第3段の両側: 笹と低木
    flights = [f for f in F.HOSEN if f['kind'] == 'main'][1:]
    for f in flights:
        p0, p1 = np.array(f['p0'], float), np.array(f['p1'], float)
        d = p1 - p0
        L = float(np.hypot(*d))
        d /= L
        nrm = np.array([-d[1], d[0]])
        for i in range(int(L / 2.6)):
            t = (i + 0.5) * 2.6 / L
            for sd in (-1, 1):
                off = f['width'] / 2 + 3.0 + rs.uniform(0, 1.8)
                p = p0 + d * (t * L) + nrm * sd * off
                if ok(p[0], p[1], 1.0):
                    if i % 3 == 0:
                        shrub(pb, p[0], p[1], gz(p[0], p[1]), rs.uniform(0.7, 1.1), i + sd)
                        cnt('shrub_stairs')
                    else:
                        sasa(pb, p[0], p[1], gz(p[0], p[1]), rs.uniform(0.5, 0.8), i * 3 + sd)
                        cnt('sasa_stairs')
    # 4) 奈良屋の前庭: 築山の紅葉と松
    s = site.signs.get('954629636')
    if s:
        n = np.array(s['normal'][:2])
        r_ = np.array(s['right'][:2])
        base = np.array(s['center'][:2])
        for (u, v, kind) in ((-2.6, 3.2, 'maple'), (2.4, 3.6, 'pine'), (0.0, 3.0, 'shrub'), (-4.2, 2.6, 'shrub')):
            p = base + r_ * u + n * v
            if ok(p[0], p[1], 0.3):
                z = gz(p[0], p[1])
                if kind == 'maple':
                    maple(pb, p[0], p[1], z, 5.5, 3)
                elif kind == 'pine':
                    pine(pb, p[0], p[1], z, 5.0, 5)
                else:
                    shrub(pb, p[0], p[1], z, 0.9, 7)
                cnt('naraya_' + kind)
    # 5) 益成屋の門前・清月堂の隣: 植え込み
    for sid, offs in (('954965052', ((-2.2, 2.2), (2.2, 2.2))), ('605546937', ((3.2, 1.2), (4.2, 1.2)))):
        s = site.signs.get(sid)
        if not s:
            continue
        n = np.array(s['normal'][:2])
        r_ = np.array(s['right'][:2])
        base = np.array(s['center'][:2])
        for (u, v) in offs:
            p = base + r_ * u + n * v
            if ok(p[0], p[1], 0.2):
                shrub(pb, p[0], p[1], gz(p[0], p[1]), 0.75, int(u * 10))
                cnt('shrub_front')
    return pb, st


def main():
    import time
    t0 = time.time()
    field = F.Field(C.load_osm(), log=lambda *a: None)
    raw = K.collect_signs(field)
    site = K.Site(field, raw)
    pb, st = build(field, site, raw)
    tris = pb.tris()
    print('[plants %.1fs] tris %d stats %s' % (time.time() - t0, tris, st), flush=True)
    out = dict(tris=tris, stats=st)
    if '--count' in ARGS or C.bpy is None:
        return
    C.reset_scene()
    mats = P.get_materials()
    coll = C.new_collection('Plants')
    objs = pb.to_objects('Plants', mats, coll)
    size = C.export_glb(objs, os.path.join(C.OUT_WEB, 'plants.glb'), pos_bits=16)
    out['glb_bytes'] = size
    json.dump(out, open(os.path.join(C.OUT_BLEND, 'plants_stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('exported plants.glb', size)


if __name__ == '__main__':
    main()
