# -*- coding: utf-8 -*-
"""kd_buildings.py -- 建物の仮置き(フェーズ4〜8で本物に置き換える仮のもの)。
OSM の外形をそのまま立て、階数 x 階高 + 簡単な切妻(または陸屋根)を載せるだけ。区域 A〜D ごとに別オブジェクト・別 glTF。
階数: OSM building:levels > 名前/位置の上書き(カードで確定したもの) > 面積で推定(小さい=2階、ほか3階)。高さはすべて推定。
"""
import math
import zlib

import numpy as np

import kd_common as C

try:
    import bmesh
    from mathutils import Vector, geometry
except ImportError:
    bmesh = None

# 名前の一部 -> (階数, 階高 m, 屋根 'gable'|'flat', 傾き)  ※名前は OSM のタグ
NAME_RULES = [
    ('五重塔', (5, 4.4, 'gable', 0.55)), ('光泉寺', (1, 6.0, 'gable', 0.6)), ('釋迦堂', (1, 5.2, 'gable', 0.7)),
    ('不動堂', (1, 4.6, 'gable', 0.6)), ('慈照殿', (2, 3.6, 'gable', 0.45)), ('白根神社', (1, 4.5, 'gable', 0.6)),
    ('熱乃湯', (2, 4.4, 'gable', 0.42)), ('白旗の湯', (1, 5.0, 'gable', 0.45)), ('御座之湯', (2, 4.0, 'gable', 0.5)),
    ('湯けむり亭', (1, 3.0, 'gable', 0.35)), ('山本館', (3, 3.3, 'gable', 0.45)), ('益成屋', (3, 3.3, 'gable', 0.45)),
    ('奈良屋', (3, 3.3, 'gable', 0.45)), ('群龍館', (3, 3.3, 'gable', 0.45)), ('ホテル一井', None), ('ローソン', (2, 3.4, 'gable', 0.4)),
    ('トイレ', (1, 3.0, 'gable', 0.3)), ('湯畑観光駐車場', (1, 3.0, 'flat', 0)),
]
# 位置(x,y,半径 m) -> (階数, 階高, 屋根, 傾き)  ※フェーズ1のカード(動画で確認した階数)
POS_RULES = [
    ((12, -31, 6), (3, 3.2, 'gable', 0.5)),    # ちちや 3階
    ((0, -49, 7), (3, 3.3, 'gable', 0.5)),     # おみやげの本多 3階+屋根裏
    ((6, -53, 7), (2, 3.5, 'gable', 0.45)),    # 月乃井 2階
    ((45, -2, 8), (4, 3.2, 'flat', 0)),        # お宿 平の家 4階 陸屋根ぎみ
    ((24, -17, 6), (3, 3.2, 'gable', 0.45)),   # 縦看板の3階建て
    ((17, -26, 6), (3, 3.2, 'gable', 0.45)),   # 黒い丸石壁の店 3階
    ((26, -10, 6), (2, 3.4, 'gable', 0.5)),    # 黒い2連切妻
    ((-39, -83, 7), (3, 3.2, 'gable', 0.4)),   # ぬ志勇旅館 3階
]

WALL_COLS = ['#ece6d8', '#ddd4c2', '#c9bba3', '#b9a58a', '#d3d1c9', '#f3f1ea', '#a89580', '#e3d9c6']
ROOF_COLS = ['#4b4b50', '#5a4a40', '#3f4a54', '#6a5a50', '#55555a']
FOUND_COL = '#8d8b86'


def rules_for(b):
    t = b['tags']
    name = t.get('name', '')
    lv = t.get('building:levels')
    for key, v in NAME_RULES:
        if key and key in name:
            if v is None:     # ホテル一井: 階数はタグ
                continue
            return dict(levels=v[0], fh=v[1], roof=v[2], slope=v[3], src='name')
    for (x, y, r), v in POS_RULES:
        if math.hypot(b['c'][0] - x, b['c'][1] - y) <= r:
            return dict(levels=v[0], fh=v[1], roof=v[2], slope=v[3], src='card')
    if 'big' in t:
        pass
    if lv and str(lv).isdigit():
        n = int(lv)
        return dict(levels=n, fh=3.3 if n >= 4 else 3.2, roof='flat' if n >= 5 or b['area'] > 450 else 'gable', slope=0.4, src='osm')
    if t.get('building') == 'roof':
        return dict(levels=1, fh=3.0, roof='gable', slope=0.35, src='osm')
    if b['area'] > 700:
        return dict(levels=4, fh=3.3, roof='flat', slope=0, src='guess')
    n = 2 if b['area'] < 50 else 3
    return dict(levels=n, fh=3.2, roof='flat' if b['area'] > 450 else 'gable', slope=0.42, src='guess')


def obb(ring):
    P = np.array(ring)
    best = None
    for a in np.deg2rad(np.arange(0, 90, 2.0)):
        c, s = math.cos(a), math.sin(a)
        u = P[:, 0] * c + P[:, 1] * s
        v = -P[:, 0] * s + P[:, 1] * c
        area = (u.max() - u.min()) * (v.max() - v.min())
        if best is None or area < best[0]:
            best = (area, a, u.min(), u.max(), v.min(), v.max())
    _, a, u0, u1, v0, v1 = best
    c, s = math.cos(a), math.sin(a)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    cx, cy = cu * c - cv * s, cu * s + cv * c
    long_is_u = (u1 - u0) >= (v1 - v0)
    ang = a if long_is_u else a + math.pi / 2
    return (cx, cy), ang, max(u1 - u0, v1 - v0), min(u1 - u0, v1 - v0)


def gable_roof(ring, eave, slope, rise_cap=4.8):
    """外形を OBB の長軸方向の棟で切り、屋根面の三角形と壁の上端(z つき)を返す。"""
    (cx, cy), ang, Lw, Wd = obb(ring)
    dx, dy = math.cos(ang), math.sin(ang)       # 棟の向き
    nx, ny = -dy, dx                            # 棟に直交
    ds = [(p[0] - cx) * nx + (p[1] - cy) * ny for p in ring]
    hw = max(abs(d) for d in ds)
    rise = min(hw * slope, rise_cap)
    k = rise / max(hw, 1e-6)
    bm = bmesh.new()
    vs = [bm.verts.new((p[0], p[1], 0.0)) for p in ring]
    bm.faces.new(vs)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector((cx, cy, 0)), plane_no=Vector((nx, ny, 0)))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    for v in bm.verts:
        d = (v.co.x - cx) * nx + (v.co.y - cy) * ny
        v.co.z = eave + k * (hw - abs(d))
    tris = [[tuple(v.co) for v in f.verts] for f in bm.faces]
    edges = []
    for e in bm.edges:
        if e.is_boundary:
            lp = e.link_loops[0]
            a, b = lp.vert, lp.link_loop_next.vert
            edges.append((tuple(a.co), tuple(b.co)))
    bm.free()
    return tris, edges, rise


def flat_roof(ring, eave):
    pts = [Vector((p[0], p[1], eave)) for p in ring]
    idx = geometry.tessellate_polygon([pts])
    tris = [[tuple(pts[i]) for i in t] for t in idx]
    edges = [((ring[i][0], ring[i][1], eave), (ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1], eave)) for i in range(len(ring))]
    return tris, edges


def build_buildings(field, mats, collections, log=print):
    """区域ごとの MB を作って返す。 -> ({zone: obj}, index list)"""
    mbs = {z: C.MB() for z in 'ABCD'}
    index = []
    rs = np.random.RandomState(7)
    wc = [C.srgb(h) for h in WALL_COLS]
    rc = [C.srgb(h) for h in ROOF_COLS]
    fc = C.srgb(FOUND_COL)
    for b in field.blds:
        ring = b['ring']
        r = rules_for(b)
        pad = b['pad'] - C.ZBASE
        # 外周と外側1mの地面の低い方まで基礎を伸ばす
        P = np.array(ring)
        cen = np.array(b['c'])
        out = P + (P - cen) / np.maximum(np.hypot(*(P - cen).T), 1e-6)[:, None] * 1.0
        zg = field.Z(np.concatenate([P[:, 0], out[:, 0]]), np.concatenate([P[:, 1], out[:, 1]]))
        bottom = min(float(zg.min()), pad) - 0.25
        eave = pad + r['levels'] * r['fh']
        h = zlib.crc32(b['id'].encode()) % 1000
        wcol = wc[h % len(wc)]
        rcol = rc[(h // 7) % len(rc)]
        try:
            if r['roof'] == 'gable':
                tris, edges, rise = gable_roof(ring, eave, r['slope'])
            else:
                tris, edges = flat_roof(ring, eave + 0.1)
                rise = 0.0
        except Exception as ex:      # 自己交差などで失敗したら陸屋根
            log('  roof fallback %s: %s' % (b['id'], ex))
            tris, edges = flat_roof(ring, eave + 0.1)
            rise = 0.0
            r['roof'] = 'flat'
        mb = mbs[b['zone']]
        for t in tris:
            mb.poly(t, rcol, up=True)
        cz = pad + 0.5
        for (a, bb) in edges:
            # 基礎(地面付近) と 壁
            zf = pad + 0.25
            mb.poly([(a[0], a[1], bottom), (bb[0], bb[1], bottom), (bb[0], bb[1], zf), (a[0], a[1], zf)], fc, inside=(cen[0], cen[1], cz))
            mb.poly([(a[0], a[1], zf), (bb[0], bb[1], zf), (bb[0], bb[1], bb[2]), (a[0], a[1], a[2])], wcol, inside=(cen[0], cen[1], cz))
        index.append(dict(id=b['id'], name=b['tags'].get('name', ''), zone=b['zone'], levels=r['levels'], floor_h=r['fh'],
                          roof=r['roof'], rise=round(rise, 2), src=r['src'], pad_z=round(pad, 2), bottom_z=round(bottom, 2),
                          eave_z=round(eave, 2), area=round(b['area'], 1), c=[round(b['c'][0], 1), round(b['c'][1], 1)],
                          ring=[[round(p[0], 2), round(p[1], 2)] for p in ring]))
    objs = {}
    for z, mb in mbs.items():
        objs[z] = mb.to_object('Buildings_%s' % z, mats['bldg'], False, collections[z])
    return objs, index
