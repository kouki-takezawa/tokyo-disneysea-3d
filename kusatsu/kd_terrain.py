# -*- coding: utf-8 -*-
"""kd_terrain.py -- 草津 湯畑ジオラマ フェーズ2: 地形・台座・道・水・石段・擁壁・建物(仮)を作って glTF に書き出す。

実行(ヘッドレス Blender 5.2。他タブの Blender が動いていないことを tasklist で確認してから、1つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_terrain.py -- [--no-export] [--no-buildings]

座標: 原点=湯畑重心、+X=東、+Y=北、Blender の Z = 標高(海抜 m) - 1153。高さは誇張なし(1:1)。
出力: output/kusatsu/kusatsu_diorama.blend(git 無視)、kusatsu-diorama/models/{terrain,buildings_A..D}.glb、meta.json、buildings_index.json
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, geometry  # noqa: E402

import kd_common as C  # noqa: E402
import kd_field as F  # noqa: E402
import kd_buildings as KB  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
R = C.R_MESH
ZB = C.ZBASE
T0 = time.time()


def log(*a):
    print('[kd %.1fs]' % (time.time() - T0), *a, flush=True)


# ====================================================================== 地形
def ground_colors(field, x, y, z):
    """地面の頂点色(リニア)。草木は置かない方針なので、土・砂利・石の地面だけで表す。"""
    gy, gx = np.gradient(field.E, field.res)
    slope = np.hypot(field.bil(x, y, gx), field.bil(x, y, gy))
    n1 = C.vnoise(x, y, 9.0, 1)
    n2 = C.vnoise(x, y, 2.3, 2)
    soil_a = np.array(C.srgb('#6a5f45')); soil_b = np.array(C.srgb('#7d7455')); rock = np.array(C.srgb('#756c5e'))
    t = (0.6 * n1 + 0.4 * n2)[:, None]
    col = soil_a * (1 - t) + soil_b * t
    rk = np.clip((slope - 0.45) / 0.5, 0, 1)[:, None]
    col = col * (1 - rk) + rock * rk * (0.85 + 0.3 * n2[:, None])
    # 敷地(建物の外まわり): コンクリートの土間ぽく
    ix = np.clip(((x + field.half) / field.res).round().astype(int), 0, field.n - 1)
    iy = np.clip(((y + field.half) / field.res).round().astype(int), 0, field.n - 1)
    pad = field.pad_mask[iy, ix]
    col = np.where(pad[:, None], np.array(C.srgb('#8c8981')) * (0.92 + 0.16 * n2[:, None]), col)
    # 池の底
    sd = field.bil(x, y, field.pond_sd)
    col = np.where((sd < 0.2)[:, None], np.array(C.srgb('#59615c')), col)
    return col


def build_terrain(field, step, mats, coll):
    xs = np.arange(-R, R + 1e-6, step)
    n = len(xs)
    cc = (xs[:-1] + step / 2)
    CX, CY = np.meshgrid(cc, cc)
    inc = np.hypot(CX, CY) < R
    # 湯畑の穴(石柵の内側・滝壺)は地形を描かない。縁から 1.5 m 外までの升目も抜き、湯畑側の周回路の舗装で覆う。
    near = (np.abs(CX) < 60) & (np.abs(CY) < 70)
    hole = np.zeros_like(inc)
    hole[near] = field.yb.in_hole(CX[near], CY[near], dilate=1.5)
    inc = inc & ~hole
    used = np.zeros((n, n), bool)
    used[:-1, :-1] |= inc; used[1:, :-1] |= inc; used[:-1, 1:] |= inc; used[1:, 1:] |= inc
    vid = -np.ones((n, n), int)
    vid[used] = np.arange(used.sum())
    GX, GY = np.meshgrid(xs, xs)
    vx = GX[used]; vy = GY[used]
    r = np.hypot(vx, vy)
    sc = np.minimum(1.0, R / np.maximum(r, 1e-9))
    vx = vx * sc; vy = vy * sc
    vz = field.Z(vx, vy)
    faces = []
    jj, ii = np.nonzero(inc)
    for j, i in zip(jj.tolist(), ii.tolist()):
        a, b, c, d = vid[j, i], vid[j, i + 1], vid[j + 1, i + 1], vid[j + 1, i]   # 00 10 11 01
        if abs(vz[a] - vz[c]) < abs(vz[b] - vz[d]):
            faces.append((a, b, c)); faces.append((a, c, d))
        else:
            faces.append((a, b, d)); faces.append((b, c, d))
    verts = np.stack([vx, vy, vz], axis=1)
    cols = ground_colors(field, vx, vy, vz)
    obj = C.make_object('Terrain', verts, faces, cols, 'vert', mats['ground'], True, coll)
    # 縁の輪(境界エッジ)を角度順に
    cnt = {}
    for f in faces:
        for k in range(3):
            e = tuple(sorted((f[k], f[(k + 1) % 3])))
            cnt[e] = cnt.get(e, 0) + 1
    rim = set()
    for e, c in cnt.items():
        if c == 1:
            rim.update(e)
    rim = [k for k in rim if math.hypot(verts[k][0], verts[k][1]) > R - 3.0]     # 湯畑の穴の縁は除く
    rim = sorted(rim, key=lambda k: math.atan2(verts[k][1], verts[k][0]))
    ring = verts[rim]
    return obj, ring, len(faces)


def build_pedestal(ring, mats, coll):
    """縁の輪から下へ地層の断面、さらに下に台座(板)。"""
    zb = float(ring[:, 2].min()) - 15.0
    mb = C.MB()
    bands = [(0.0, '#3b2a1b'), (1.1, '#7b5d3a'), (3.4, '#b1a68d'), (7.5, '#6b655b'), (12.0, '#8b8576'), (17.0, '#3c3b40')]
    m = len(ring)
    for i in range(m):
        a = ring[i]; b = ring[(i + 1) % m]
        ang = math.atan2(a[1], a[0])
        for k, (d0, col) in enumerate(bands):
            def zl(p, ang_, kk):
                if kk >= len(bands):
                    return zb
                wob = 1 + 0.22 * math.sin(3 * ang_ + kk * 1.7) + 0.12 * math.sin(7 * ang_ + kk * 0.9) + 0.07 * math.sin(19 * ang_ + kk)
                return max(zb + 0.5, p[2] - bands[kk][0] * (wob if kk > 0 else 1.0))
            angb = math.atan2(b[1], b[0])
            hi_a, hi_b = zl(a, ang, k), zl(b, angb, k)
            lo_a, lo_b = zl(a, ang, k + 1), zl(b, angb, k + 1)
            if k + 1 == len(bands):
                lo_a = lo_b = zb
            if hi_a - lo_a < 0.02 and hi_b - lo_b < 0.02:
                continue
            nz = 0.88 + 0.24 * float(C.vnoise(ang * 40, k * 5.0, 1.0, k))
            mb.poly([(a[0], a[1], lo_a), (b[0], b[1], lo_b), (b[0], b[1], hi_b), (a[0], a[1], hi_a)],
                    C.tint(C.srgb(col), nz), inside=(0, 0, (zb + a[2]) / 2))
    # 台座(板): 断面図の下の暗い木の盤
    prof = [(R, zb, '#2a1b12'), (R + 7, zb, '#2a1b12'), (R + 8.6, zb - 1.6, '#4b3322'), (R + 8.6, zb - 8, '#2a1b12'), (R - 20, zb - 8, '#1a110c')]
    seg = 180
    for s in range(seg):
        t0 = 2 * math.pi * s / seg; t1 = 2 * math.pi * (s + 1) / seg
        for k in range(len(prof) - 1):
            r0, z0, c0 = prof[k]; r1, z1, _ = prof[k + 1]
            mb.poly([(r0 * math.cos(t0), r0 * math.sin(t0), z0), (r0 * math.cos(t1), r0 * math.sin(t1), z0),
                     (r1 * math.cos(t1), r1 * math.sin(t1), z1), (r1 * math.cos(t0), r1 * math.sin(t0), z1)],
                    C.tint(C.srgb(c0), 0.95 + 0.1 * (s % 2)), inside=(0, 0, zb - 4))
    return mb.to_object('Pedestal', mats['strata'], False, coll), zb


# ====================================================================== 道
def ribbon(mb, field, pts, hw, colfn, zoff, ncol_w=None, clip=R - 0.6, cs_samples=None):
    """折れ線を地面に張り付ける帯。colfn(i, c) で色。"""
    pts = np.asarray(pts)
    if len(pts) < 2:
        return
    tan = np.zeros_like(pts)
    tan[1:-1] = pts[2:] - pts[:-2]
    tan[0] = pts[1] - pts[0]
    tan[-1] = pts[-1] - pts[-2]
    tl = np.maximum(np.hypot(*tan.T), 1e-9)
    tan = tan / tl[:, None]
    nor = np.stack([-tan[:, 1], tan[:, 0]], axis=1)
    ncol = ncol_w or max(1, int(math.ceil(2 * hw / 1.4)))
    offs = np.linspace(-hw, hw, ncol + 1)
    grid = []
    for o in offs:
        p = pts + nor * o
        z = field.Z(p[:, 0], p[:, 1]) + zoff
        grid.append(np.concatenate([p, z[:, None]], axis=1))
    for i in range(len(pts) - 1):
        if np.hypot(*pts[i]) > clip or np.hypot(*pts[i + 1]) > clip:
            continue
        for c in range(ncol):
            q = [grid[c][i], grid[c + 1][i], grid[c + 1][i + 1], grid[c][i + 1]]
            mb.poly(q, colfn(i, c), up=True)


def subdivided_fill(mb, field, ring, col_fn, zoff):
    """多角形を細かく分割して地面に張る。"""
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new((p[0], p[1], 0)) for p in ring]
    try:
        bm.faces.new(vs)
    except ValueError:
        bm.free()
        return
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    for _ in range(5):
        long_e = [e for e in bm.edges if e.calc_length() > 2.2]
        if not long_e:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
    for f in bm.faces:
        pts = [(v.co.x, v.co.y, float(field.Z(v.co.x, v.co.y)) + zoff) for v in f.verts]
        cx = sum(p[0] for p in pts) / 3; cy = sum(p[1] for p in pts) / 3
        mb.poly(pts, col_fn(cx, cy), up=True)
    bm.free()


def build_roads(field, mats, coll):
    mb = C.MB()
    rs = np.random.RandomState(3)
    base = {'asphalt': '#444448', 'asphalt2': '#58585a', 'paving': '#a59d8d', 'path': '#8f7e63'}
    stats = {}
    for r in sorted(field.roads, key=lambda r: F.ROAD_RANK[r['cls']]):
        kind = r['kind']
        if r.get('surface') == 'wood':
            kind = 'wood'
            base_c = C.srgb('#7a5b3b')
        else:
            base_c = C.srgb(base[kind])
        rank = F.ROAD_RANK[r['cls']]
        stats[r['cls']] = stats.get(r['cls'], 0) + 1

        def colfn(i, c, base_c=base_c, kind=kind):
            k = 0.88 + 0.24 * rs.rand() if kind in ('paving', 'path', 'wood') else 0.93 + 0.14 * rs.rand()
            return C.tint(base_c, k)
        hw = r['hw']
        ribbon(mb, field, r['pts'], hw, colfn, 0.07 + 0.008 * rank, ncol_w=None if kind in ('paving', 'path') else max(1, int(math.ceil(2 * hw / 3.2))))
    # 歩行者エリア(湯畑まわりの広場)
    pc = C.srgb('#a89f8e')
    for ring in field.ped_areas:
        subdivided_fill(mb, field, ring, lambda x, y: C.tint(pc, 0.88 + 0.24 * float(C.hash_noise(round(x, 0), round(y, 0)))), 0.09)
    # 石段の踊り場・山門の通路など(平らな帯)
    for f in field.flights:
        if f['kind'] == 'ramp':
            col = {'山門の通路': '#7a5b3b', '踊り場': '#9d9686', '本堂前': '#a89a82'}.get(f['name'], '#9d9686')
            pts = [f['p0'], f['p1']] if 'pts' not in f else f['pts']
            pts, _ = C.resample(pts, 1.2)
            bc = C.srgb(col)
            ribbon(mb, field, pts, f['width'] / 2, lambda i, c, bc=bc: C.tint(bc, 0.88 + 0.24 * rs.rand()), 0.09)
    obj = mb.to_object('Roads', mats['road'], False, coll)
    return obj, stats


# ====================================================================== 水
def build_water(field, mats, coll):
    objs = []
    p = field.pond

    def tessellate(ring, z):
        pts = [Vector((q[0], q[1], z)) for q in ring]
        idx = geometry.tessellate_polygon([pts])
        v = [tuple(q) for q in pts]
        return v, [tuple(t) for t in idx]
    # 湯畑の池・滝壺の水は kd_yubatake.py(yubatake.glb)で作る
    for k, o in enumerate(p['others']):
        v, f = tessellate(o['ring'], o['z_water'] - ZB)
        f = [t if np.cross(np.subtract(v[t[1]], v[t[0]]), np.subtract(v[t[2]], v[t[0]]))[2] > 0 else (t[0], t[2], t[1]) for t in f]
        objs.append(C.make_object('Water_Pond_%d' % k, v, f, None, 'face', mats['water_dark'], False, coll))
    return objs


# ====================================================================== 石段・擁壁
GRANITE = C.srgb('#9a9a96')


def add_flight(mb, f, rs):
    p0 = np.array(f['p0'], float); p1 = np.array(f['p1'], float)
    z0 = f['z0'] - ZB; z1 = f['z1'] - ZB
    if z1 < z0:
        p0, p1, z0, z1 = p1, p0, z1, z0
    d = p1 - p0
    L = float(np.hypot(*d))
    u = d / L
    v = np.array([-u[1], u[0]])
    n = f['n']
    w = f['width']
    riser = (z1 - z0) / n
    tread = L / n
    cheek = 0.30 if f.get('side') else 0.2

    def steps(off_c, width, base, slabs, thin):
        for i in range(n):
            s0, s1 = i * tread, (i + 1) * tread
            zt = z0 + (i + 1) * riser
            edges = np.linspace(-width / 2, width / 2, slabs + 1)
            # 継ぎ目をずらす
            if slabs > 1:
                shift = (rs.rand() - 0.5) * width / slabs * 0.6
                edges[1:-1] += shift
            for k in range(slabs):
                c = C.tint(base, 0.85 + 0.25 * rs.rand())
                l0, l1 = off_c + edges[k], off_c + edges[k + 1]
                A = p0 + u * s0 + v * l0; B = p0 + u * s0 + v * l1
                Cc = p0 + u * s1 + v * l1; D = p0 + u * s1 + v * l0
                mb.poly([(*A, zt), (*B, zt), (*Cc, zt), (*D, zt)], c, up=True)
                zbot = zt - riser - 0.06
                mb.poly([(*A, zbot), (*B, zbot), (*B, zt), (*A, zt)], C.tint(c, 0.8), inside=(*(p0 + u * (s0 + tread * 0.5) + v * ((l0 + l1) / 2)), zt - 0.3))
    steps(0.0, w, GRANITE, 3, False)
    # 脇: 御影石の袖
    for off in (w / 2 + cheek / 2,):
        mb.box_sloped(p0, p1, z0 + 0.5, z1 + 0.5, z0 - 0.7, z1 - 0.7, off, cheek, C.srgb('#8c8c88'))
    if f.get('side'):
        # 手すり(主階段と副階段の境)、副階段(グレーチングの踏板)、右の袖
        sub_w = 1.1
        sub_off = -(w / 2 + 0.25 + sub_w / 2)
        steps(sub_off, sub_w, C.srgb('#2e3033'), 1, True)
        rail_off = -(w / 2 + 0.12)
        mb.box_sloped(p0, p1, z0 + 1.0, z1 + 1.0, z0 + 0.95, z1 + 0.95, rail_off, 0.06, C.srgb('#b9bcc0'))
        mb.box_sloped(p0, p1, z0 + 0.55, z1 + 0.55, z0 + 0.5, z1 + 0.5, rail_off, 0.05, C.srgb('#b9bcc0'))
        k = int(L / 2.0)
        for q in range(k + 1):
            s = L * q / max(k, 1)
            zz = z0 + (z1 - z0) * s / L + riser
            pc = p0 + u * s
            mb.box_sloped(pc, pc + u * 0.06, zz + 1.0, zz + 1.0, zz - 0.05, zz - 0.05, rail_off, 0.07, C.srgb('#27468f'))
        mb.box_sloped(p0, p1, z0 + 0.5, z1 + 0.5, z0 - 0.7, z1 - 0.7, -(w / 2 + 0.25 + sub_w + cheek / 2), cheek, C.srgb('#8c8c88'))


def build_structures(field, mats, coll):
    rs = np.random.RandomState(11)
    mb = C.MB()
    nsteps = 0
    for f in field.flights:
        if f['kind'] == 'main' and f['n'] >= 2:
            add_flight(mb, f, rs)
            nsteps += f['n']
    # 擁壁(OSM barrier=retaining_wall)
    walls = C.osm_ways(field.osm, lambda t: t.get('barrier') == 'retaining_wall')
    nw = 0
    for wid, t, pts in walls:
        if all(math.hypot(*p) > 199 for p in pts):
            continue
        rp, _ = C.resample(pts, 1.5)
        if len(rp) < 2:
            continue
        for i in range(len(rp) - 1):
            a, b = rp[i], rp[i + 1]
            if math.hypot(*a) > 198 or math.hypot(*b) > 198:
                continue
            u = (b - a) / max(np.hypot(*(b - a)), 1e-9)
            nrm = np.array([-u[1], u[0]])
            za = [float(field.Z(*(a + nrm * s * 1.6))) for s in (1, -1)]
            zb_ = [float(field.Z(*(b + nrm * s * 1.6))) for s in (1, -1)]
            hi_a, hi_b = max(za), max(zb_)
            lo_a, lo_b = min(za), min(zb_)
            side = 1 if za[0] > za[1] else -1       # 高い側
            la = float(field.Z(*a)); lb = float(field.Z(*b))
            top_a = max(hi_a, la + 0.5); top_b = max(hi_b, lb + 0.5)
            bot_a = min(lo_a, la - 0.2) - 0.3; bot_b = min(lo_b, lb - 0.2) - 0.3
            mb.box_sloped(a, b, top_a, top_b, bot_a, bot_b, side * 0.15, 0.4, C.srgb('#7f786d'), tint_k=0.85 + 0.3 * rs.rand())
        nw += 1
    return mb.to_object('Stairs_and_Walls', mats['stone'], False, coll), nsteps, nw


# ====================================================================== 本体
def main():
    out_web = C.OUT_WEB
    for a in ARGS:
        if a.startswith('--out-web='):
            out_web = a.split('=', 1)[1]
    do_export = '--no-export' not in ARGS
    do_bld = '--no-buildings' not in ARGS
    C.reset_scene()
    osm = C.load_osm()
    field = F.Field(osm, log=log)
    dem_all = field.dem.z
    mats = dict(
        ground=C.make_material('kd_ground', 0.97),
        road=C.make_material('kd_road', 0.9),
        stone=C.make_material('kd_stone', 0.88),
        strata=C.make_material('kd_strata', 0.95),
        bldg=C.make_material('kd_bldg', 0.9),
        water=C.make_material('kd_water', 0.06, vcol=False, base=(*C.srgb('#a9d8cf'), 1.0)),
        water_dark=C.make_material('kd_pond', 0.05, vcol=False, base=(*C.srgb('#4d6b66'), 1.0)),
    )
    coll_t = C.new_collection('Terrain')
    coll_b = {z: C.new_collection('Buildings_%s' % z) for z in 'ABCD'}

    terr, ring, ntri = build_terrain(field, 2.0, mats, coll_t)
    ped, zb = build_pedestal(ring, mats, coll_t)
    roads, rstats = build_roads(field, mats, coll_t)
    water = build_water(field, mats, coll_t)
    stru, nsteps, nw = build_structures(field, mats, coll_t)
    log('terrain tris %d, rim verts %d, base bottom Z %.1f, steps %d, retaining walls %d, roads %s' % (ntri, len(ring), zb, nsteps, nw, rstats))

    # 太陽・空はビューア側。シーンは glTF 用にオブジェクトだけ。
    objs_t = [terr, ped, roads, stru] + water
    objs_t = [o for o in objs_t if o is not None]
    bobjs, bindex = ({}, [])
    if do_bld:
        bobjs, bindex = KB.build_buildings(field, mats, coll_b, log=log)
        log('buildings: %d' % len(bindex))

    os.makedirs(C.OUT_BLEND, exist_ok=True)
    blend = os.path.join(C.OUT_BLEND, 'kusatsu_diorama.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    log('saved', blend)

    meta = dict(
        origin_latlon=[C.LAT0, C.LON0], zbase=ZB, radius=R, plinth_bottom_z=round(zb - 8, 2), base_bottom_z=round(zb, 2),
        dem_min_max_r200=[round(float(field.E0[np.hypot(field.X, field.Y) <= R].min()), 2), round(float(field.E0[np.hypot(field.X, field.Y) <= R].max()), 2)],
        dem_min_max_all=[round(float(dem_all.min()), 2), round(float(dem_all.max()), 2)],
        field_min_max_r200=[round(float(field.E[np.hypot(field.X, field.Y) <= R].min()), 2), round(float(field.E[np.hypot(field.X, field.Y) <= R].max()), 2)],
        yubatake=dict(rim_plane=[F.YB.RIM_C, F.YB.RIM_GX, F.YB.RIM_GY], hole_area_m2=round(C.poly_area(field.yb.hole), 1),
                      skipped_ways=field.yb_skipped_ways,
                      hole=[[round(p[0], 2), round(p[1], 2)] for p in field.yb.hole]),
        flights=[{k: (list(v) if isinstance(v, tuple) else v) for k, v in f.items() if k not in ('pts',)} for f in field.flights],
        terrain_tris=ntri,
    )
    if do_export:
        os.makedirs(out_web, exist_ok=True)
        sizes = {}
        tris = {}
        p = os.path.join(out_web, 'terrain.glb')
        sizes['terrain.glb'] = C.export_glb(objs_t, p, pos_bits=16)
        tris['terrain.glb'] = C.count_tris(objs_t)
        for z, o in bobjs.items():
            ol = [x for x in (o if isinstance(o, list) else [o]) if x is not None]   # 仮の箱+本物(kd_parts)
            if not ol:
                continue
            nm = 'buildings_%s.glb' % z
            sizes[nm] = C.export_glb(ol, os.path.join(out_web, nm), pos_bits=16 if len(ol) > 1 else 14)
            tris[nm] = C.count_tris(ol)
        meta['glb_bytes'] = sizes
        meta['glb_tris'] = tris
        meta['total_tris'] = int(sum(tris.values()))
        json.dump(bindex, open(os.path.join(out_web, 'buildings_index.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        log('exported', sizes, tris)
    json.dump(meta, open(os.path.join(out_web, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('done')


main()
