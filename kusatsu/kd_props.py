# -*- coding: utf-8 -*-
"""kd_props.py -- 草津 湯畑ジオラマ フェーズ9: 看板の文字・街灯・電柱と電線・自販機・ポスト・ボラード・幟・標識・白線。

出力:
  kusatsu-diorama/models/props.glb   街灯・電柱・電線・自販機・ポスト・ボラード・幟の竿と旗・標識の支柱・白線・横断歩道・マンホール
  kusatsu-diorama/models/signs.json  文字を貼る面の一覧(看板・幟・標識)。ビューアが canvas の文字テクスチャを貼る
  output/kusatsu/props_stats.json    数値(個数・三角形)

作り方: 区域 A〜D の BuildingSpec を一度組んで看板の面(kd_parts の Built.signs)を集める(約 50 秒、Blender 無しでも動く)
        -> 読めた文字だけを signs.json に -> 道(Field.roads)・看板の位置に沿って小物を置く -> Blender で glb。
        建物の glb は作り直さない(md5 不変)。

実行(他タブの Blender が動いていないことを tasklist で確認して 1 つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_props.py
  python kusatsu/kd_props.py --count     # Blender 無し。個数・三角形・signs.json だけ(glb は作らない)
  --refresh : output/kusatsu/props_cache.json(看板の面)を作り直す
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import kd_common as C  # noqa: E402
import kd_field as F  # noqa: E402
import kd_parts as P  # noqa: E402
import kd_yb_layout as YB  # noqa: E402
from kd_parts import PB, beam, box, lin, prism  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
R_CLIP = 192.0


# ====================================================================== 看板の面(文字)
def collect_signs(field, refresh=False):
    cache = os.path.join(C.OUT_BLEND, 'props_cache.json')
    if os.path.exists(cache) and not refresh:
        return json.load(open(cache, encoding='utf-8'))
    signs, infos = [], []
    for z in 'ABCD':
        for sp in P.zone_specs(z):
            b = P.build_building(sp, field, None)
            for s in b.signs:
                s['zone'] = z
            signs.extend(b.signs)
            infos.append(dict(id=sp.id, name=sp.name, zone=z))
    os.makedirs(C.OUT_BLEND, exist_ok=True)
    json.dump(dict(signs=signs, infos=infos), open(cache, 'w', encoding='utf-8'), ensure_ascii=False)
    return dict(signs=signs, infos=infos)


def clean_text(t):
    """spec の text から、看板に書いてある文字だけを取り出す(注記・判読できなかったものは None)。"""
    t = (t or '').strip()
    if not t or t[0] in '((' or '…' in t:
        return None
    m = re.search(r'右書き「([^」]+)」', t)
    if m:
        return m.group(1)
    t = re.sub(r'[((][^))]*[))]', '', t).strip()
    return t or None


def luma(c):
    c = c.lstrip('#')
    r, g, b = [int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# 文字色の個別指定(実物の配色が分かるものだけ。他は地の明るさで黒/白)
FG_OVERRIDE = {'7-ELEVEN': '#d9531e', '7': '#d9531e', 'LAWSON': '#f4f2ec', '御座之湯': '#2a1a10', '益成屋': '#5a1f18'}


def sign_records(raw):
    out = []
    for s in raw['signs']:
        txt = clean_text(s.get('text'))
        if not txt or 'center' not in s:
            continue
        bg = s.get('bg') or '#2c2420'
        fg = FG_OVERRIDE.get(txt) or ('#1d1814' if luma(bg) > 0.45 else '#f4efe3')
        out.append(dict(text=txt, kind=s['kind'], w=s['w'], h=s['h'], center=s['center'], normal=s['normal'], right=s['right'],
                        bg=bg, fg=fg, two=bool(s.get('two_sided')), th=0.05 if s.get('two_sided') else 0.0, spec=s['spec'], shape='rect'))
    return out


# ====================================================================== 場所の補助
class Site:
    def __init__(self, field, raw):
        self.field = field
        self.osm = field.osm
        self.roads = {r['id']: r for r in field.roads}
        self.rings = [np.asarray(b["ring"], float) for b in C.osm_buildings(self.osm)]
        self.bbox = [(r[:, 0].min() - 1.5, r[:, 0].max() + 1.5, r[:, 1].min() - 1.5, r[:, 1].max() + 1.5) for r in self.rings]
        self.signs = {}
        for s in raw['signs']:
            if clean_text(s.get('text')) and 'center' in s:
                self.signs.setdefault(s['spec'], s)
        self.loop_out = np.asarray(field.yb.loop_out, float)
        self.road_list = field.roads
        self.why = {}
        self.rbox = [(r['pts'][:, 0].min() - 8, r['pts'][:, 0].max() + 8, r['pts'][:, 1].min() - 8, r['pts'][:, 1].max() + 8) for r in field.roads]

    def in_building(self, x, y, margin=0.0):
        for r, (x0, x1, y0, y1) in zip(self.rings, self.bbox):
            if x0 <= x <= x1 and y0 <= y <= y1:
                if C.points_in_poly(np.array([x]), np.array([y]), [tuple(p) for p in r])[0]:
                    return True
                if margin > 0 and YB.seg_nearest(np.array([x]), np.array([y]), r, closed=True)[0][0] < margin:
                    return True
        return False

    def on_other_road(self, x, y, skip_id=None, extra=0.2):
        for r, (x0, x1, y0, y1) in zip(self.road_list, self.rbox):
            if r['id'] == skip_id or r['cls'] in ('path', 'footway') or not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            d = YB.seg_nearest(np.array([x]), np.array([y]), r['pts'])[0][0]
            if d < r['hw'] + extra:
                return True
        return False

    def free(self, x, y, road_id=None):
        why = self.why
        if math.hypot(x, y) > R_CLIP:
            why['r'] = why.get('r', 0) + 1
            return False
        if YB.inside(np.array([x]), np.array([y]), self.loop_out)[0]:
            why['yb'] = why.get('yb', 0) + 1
            return False
        if self.in_building(x, y, 0.5):
            why['bld'] = why.get('bld', 0) + 1
            return False
        if self.on_other_road(x, y, road_id):
            why['road'] = why.get('road', 0) + 1
            return False
        return True

    def spot(self, x, y, tx, ty, nx, ny, hw, side, offs=(0.9, 0.5, 0.2, -0.2), slides=(0.0, 2.0, -2.0, 4.0, -4.0)):
        """道の点 (x,y) の side 側(+1=左)の縁で、建物・他の道に掛からない最初の場所。道の縁(車道の端)まで寄せる。"""
        for sl in slides:
            for o in offs:
                px, py = x + tx * sl + nx * side * (hw + o), y + ty * sl + ny * side * (hw + o)
                if self.free(px, py):
                    return px, py
        return None

    def nearest_road(self, x, y, classes=('trunk', 'residential', 'unclassified', 'service', 'pedestrian')):
        best = None
        for r in self.road_list:
            if r['cls'] not in classes:
                continue
            d, nx, ny, tx, ty = YB.seg_nearest(np.array([x]), np.array([y]), r['pts'])[:5]
            if best is None or d[0] < best[0]:
                best = (float(d[0]), r, float(nx[0]), float(ny[0]), float(tx[0]), float(ty[0]))
        return best


def chain(site, ids, reverse=()):
    """道の id を順につないだ折れ線(1.5 m 間隔)。reverse に入れた id は向きを逆に。"""
    pts = []
    hw = 0
    for wid in ids:
        r = site.roads[wid]
        p = r['pts'] if wid not in reverse else r['pts'][::-1]
        pts.extend([tuple(q) for q in (p if not pts else p[1:])])
        hw = max(hw, r['hw'])
    return np.array(pts), hw


def walk(pts, spacing, s0=0.0, s1=None):
    """折れ線に沿って spacing ごとの (x, y, 接線 tx, ty, 左法線 nx, ny, s)。"""
    seg = np.hypot(*(pts[1:] - pts[:-1]).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1]
    s1 = L if s1 is None else min(s1, L)
    out = []
    s = s0
    while s <= s1 + 1e-6:
        i = min(np.searchsorted(cum, s, side='right') - 1, len(seg) - 1)
        t = (s - cum[i]) / max(seg[i], 1e-9)
        p = pts[i] + (pts[i + 1] - pts[i]) * t
        d = (pts[i + 1] - pts[i]) / max(seg[i], 1e-9)
        out.append((float(p[0]), float(p[1]), float(d[0]), float(d[1]), float(-d[1]), float(d[0]), float(s)))
        s += spacing
    return out


# ====================================================================== 小物の幾何(Blender 座標。z は地面)
BLACK = '#262523'


def frame(x, y, yaw):
    """yaw = 正面の向き(ラジアン、+X から反時計回り)。P(a, b, z): a=正面に向かって右、b=正面方向。"""
    fx, fy = math.cos(yaw), math.sin(yaw)
    rx, ry = fy, -fx

    def Pt(a, b, z):
        return (x + a * rx + b * fx, y + a * ry + b * fy, z)
    return Pt, (rx, ry), (fx, fy)


def obox(pb, m, x, y, yaw, a0, a1, b0, b1, z0, z1, c, skip=()):
    Pt, r, f = frame(x, y, yaw)
    o = Pt(a0, b0, z0)
    box(pb, m, o, ((a1 - a0) * r[0], (a1 - a0) * r[1], 0), ((b1 - b0) * f[0], (b1 - b0) * f[1], 0), (0, 0, z1 - z0), c, skip)


def western_lamp(pb, x, y, z, col=BLACK, h=3.4):
    """黒(または緑)の鋳鉄の洋風街灯(角形のガラス灯)。"""
    c = lin(col)
    prism(pb, 'metal', (x, y), 0.17, 0.13, z, z + 0.38, 8, c)
    prism(pb, 'metal', (x, y), 0.13, 0.085, z + 0.38, z + 0.55, 8, c)
    prism(pb, 'metal', (x, y), 0.065, 0.048, z + 0.55, z + h - 0.7, 8, c)
    prism(pb, 'metal', (x, y), 0.095, 0.095, z + h - 0.78, z + h - 0.7, 8, c)
    zl = z + h - 0.7
    obox(pb, 'metal', x, y, 0, -0.17, 0.17, -0.17, 0.17, zl, zl + 0.04, c)
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam(pb, 'metal', (x + sx * 0.15, y + sy * 0.15, zl + 0.04), (x + sx * 0.15, y + sy * 0.15, zl + 0.44), 0.02, 0.02, c)
    obox(pb, 'fabric', x, y, 0, -0.14, 0.14, -0.14, 0.14, zl + 0.04, zl + 0.44, lin('#efe3c0'), skip=('-z',))
    obox(pb, 'metal', x, y, 0, -0.2, 0.2, -0.2, 0.2, zl + 0.44, zl + 0.48, c)
    prism(pb, 'metal', (x, y), 0.27, 0.05, zl + 0.48, zl + 0.66, 4, c, rot=math.pi / 4)
    prism(pb, 'metal', (x, y), 0.04, 0.0, zl + 0.66, zl + 0.78, 6, c)


def steel_lamp(pb, x, y, yaw, z, h=5.6):
    """黒い鋼管の街灯(腕の先に丸い電球が下がる)。腕は yaw の向きへ。"""
    c = lin('#2b2c2d')
    prism(pb, 'metal', (x, y), 0.09, 0.055, z, z + h, 8, c)
    prism(pb, 'metal', (x, y), 0.14, 0.14, z, z + 0.25, 8, c)
    Pt, _, _ = frame(x, y, yaw)
    a = Pt(0, 0, z + h - 0.1)
    b = Pt(0, 1.3, z + h + 0.25)
    beam(pb, 'metal', a, b, 0.05, 0.05, c)
    gx, gy, gz = b[0], b[1], b[2] - 0.12
    prism(pb, 'metal', (gx, gy), 0.09, 0.09, gz - 0.02, gz + 0.05, 8, c)
    prism(pb, 'fabric', (gx, gy), 0.11, 0.2, gz - 0.2, gz - 0.02, 8, lin('#f2eee2'), top=False)
    prism(pb, 'fabric', (gx, gy), 0.2, 0.0, gz - 0.38, gz - 0.2, 8, lin('#f2eee2'), top=False)


def utility_pole(pb, x, y, z, line_yaw, kind, h, arm_col=None):
    """電柱。line_yaw = 電線の走る向き。腕木は線に直角。返り値 = 電線の取り付け点 3 つ(線の左から右)。"""
    if kind == 'wood':
        c = lin('#6f5d4a')
        prism(pb, 'wood', (x, y), 0.15, 0.1, z - 0.2, z + h, 8, c)
    else:
        c = lin('#a6a39b')
        prism(pb, 'stone', (x, y), 0.18, 0.115, z - 0.2, z + h, 8, c)
    Pt, _, f = frame(x, y, line_yaw)
    ac = lin(arm_col or ('#8d6a3a' if kind == 'wood' else '#5c5c58'))
    za = z + h - 0.45
    obox(pb, 'wood' if kind == 'wood' else 'metal', x, y, line_yaw, -1.0, 1.0, -0.05, 0.05, za, za + 0.1, ac)
    ins = []
    for a in (-0.85, 0.0, 0.85):
        px, py, _ = Pt(a, 0, 0)
        prism(pb, 'stone', (px, py), 0.045, 0.03, za + 0.1, za + 0.27, 6, lin('#d8d6cf'))
        ins.append((px, py, za + 0.28))
    # 柱の上に 2 本目の腕(低い所に引込線・街灯用の小さな腕)
    zb = za - 0.75
    obox(pb, 'metal', x, y, line_yaw, -0.6, 0.6, -0.04, 0.04, zb, zb + 0.08, lin('#5c5c58'))
    for a in (-0.5, 0.5):
        px, py, _ = Pt(a, 0, 0)
        prism(pb, 'stone', (px, py), 0.035, 0.025, zb + 0.08, zb + 0.2, 6, lin('#d8d6cf'))
        ins.append((px, py, zb + 0.21))
    return ins


def wire(pb, a, b, sag_k=0.011, w=0.018, c='#1e1e1e', n=8):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    L = float(np.hypot(*(b[:2] - a[:2])))
    sag = sag_k * L
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a + (b - a) * t
        p[2] -= sag * 4 * t * (1 - t)
        pts.append(p)
    cc = lin(c)
    for i in range(n):
        beam(pb, 'dark', pts[i], pts[i + 1], w, w, cc, skip=('-x', '+x'))


def vending(pb, x, y, z, yaw, body, seed=0):
    """飲料の自販機(幅 0.78・奥 0.7・高 1.8)。yaw = 正面の向き。"""
    bc = lin(body)
    obox(pb, 'paint', x, y, yaw, -0.39, 0.39, -0.35, 0.35, z, z + 1.8, bc, skip=('-z',))
    obox(pb, 'glass', x, y, yaw, -0.31, 0.31, 0.35, 0.37, z + 0.85, z + 1.62, lin('#2a3238'))
    cols = ['#d9d4c8', '#c8372f', '#2d6aa8', '#3d8a4a', '#e0a02b', '#7a4a2a']
    for row, zz in enumerate((1.34, 1.04)):
        for j in range(6):
            cx = -0.25 + j * 0.1
            obox(pb, 'fabric', x, y, yaw, cx - 0.035, cx + 0.035, 0.37, 0.43, z + zz - 0.02, z + zz + 0.2 - 0.02 * row, lin(cols[(j + row * 2 + seed) % 6]))
    obox(pb, 'metal', x, y, yaw, 0.1, 0.34, 0.35, 0.38, z + 0.9, z + 1.4, lin('#9aa0a2'))      # ボタン列
    obox(pb, 'dark', x, y, yaw, -0.22, 0.12, 0.35, 0.37, z + 0.22, z + 0.42, lin('#141414'))   # 取り出し口
    obox(pb, 'fabric', x, y, yaw, -0.3, 0.3, 0.35, 0.36, z + 1.66, z + 1.76, lin('#f4f1e6'))   # 上の表示帯


def round_post(pb, x, y, z):
    """赤い丸ポスト。"""
    c = lin('#bd2a22')
    prism(pb, 'paint', (x, y), 0.24, 0.24, z, z + 0.08, 12, lin('#3a3a3a'))
    prism(pb, 'paint', (x, y), 0.21, 0.21, z + 0.08, z + 1.1, 12, c)
    prism(pb, 'paint', (x, y), 0.22, 0.17, z + 1.1, z + 1.28, 12, c)
    prism(pb, 'paint', (x, y), 0.17, 0.0, z + 1.28, z + 1.36, 12, c)
    prism(pb, 'dark', (x, y), 0.215, 0.215, z + 0.88, z + 0.96, 12, lin('#222222'), top=False)


def log_bollard(pb, x, y, z, h=0.8):
    c = lin('#6f4f35')
    prism(pb, 'wood', (x, y), 0.1, 0.1, z, z + h, 8, c)
    prism(pb, 'wood', (x, y), 0.1, 0.07, z + h, z + h + 0.06, 8, c)
    prism(pb, 'fabric', (x, y), 0.102, 0.102, z + h - 0.18, z + h - 0.1, 8, lin('#c8372f'), top=False)


def redwhite_bollard(pb, x, y, z, h=0.8):
    prism(pb, 'metal', (x, y), 0.045, 0.045, z, z + h, 8, lin('#eceae4'))
    for z0 in (0.12, 0.42):
        prism(pb, 'fabric', (x, y), 0.047, 0.047, z + z0, z + z0 + 0.14, 8, lin('#c8372f'), top=False)
    prism(pb, 'metal', (x, y), 0.045, 0.0, z + h, z + h + 0.04, 8, lin('#eceae4'))


def sign_post(pb, x, y, z, h, w=None, board_z=None, col='#8d9397'):
    c = lin(col)
    prism(pb, 'metal', (x, y), 0.04, 0.04, z, z + h, 8, c)
    prism(pb, 'metal', (x, y), 0.045, 0.0, z + h, z + h + 0.05, 8, c)


def nobori_pole(pb, x, y, z, yaw, H, fw, fh, fcol, pcol='#4e6fa3'):
    """幟: 竿+横棒+旗(旗の面は yaw の向き=読める向き。両面)。旗の面の記録(中心・向き)を返す。"""
    pc = lin(pcol)
    prism(pb, 'metal', (x, y), 0.03, 0.025, z - 0.3, z + H, 8, pc)
    Pt, r, f = frame(x, y, yaw)
    ztop = z + H - 0.12
    ar = Pt(0, 0, ztop)
    br = Pt(fw + 0.04, 0, ztop)
    beam(pb, 'metal', ar, br, 0.02, 0.02, pc)
    z1 = ztop - 0.03
    z0 = z1 - fh
    c = lin(fcol)
    q = [Pt(0.02, 0, z0), Pt(0.02 + fw, 0, z0), Pt(0.02 + fw, 0, z1), Pt(0.02, 0, z1)]
    pb.poly('fabric', q, c, (f[0], f[1], 0))
    pb.poly('fabric', q, c, (-f[0], -f[1], 0))
    ctr = Pt(0.02 + fw / 2, 0, (z0 + z1) / 2)
    return dict(center=[ctr[0], ctr[1], ctr[2]], normal=[f[0], f[1], 0.0], right=[r[0], r[1], 0.0], w=fw, h=fh)


# ====================================================================== 配置
def build_props(field, site, raw, log=print):
    pb = PB()
    recs = sign_records(raw)           # 文字の面(建物の看板)
    stats = {}

    def cnt(k, n=1):
        stats[k] = stats.get(k, 0) + n

    def gz(x, y):
        return float(field.Z(x, y))

    sg = site.signs

    # ---- 中央通りの黒い洋風街灯(歩道側、約 12 m 間隔。A_chuo_row)
    line, hw = chain(site, [594139677, 594139678])
    for (x, y, tx, ty, nx, ny, s) in walk(line, 12.0, 8.0):
        q = site.spot(x, y, tx, ty, nx, ny, hw, 1, offs=(0.8, 0.4, 0.1), slides=(0.0, 1.5, -1.5))
        if q:
            western_lamp(pb, q[0], q[1], gz(q[0], q[1]) + 0.1)
            cnt('lamp_black')

    # ---- 御座之湯の前: 緑の鋳鉄の洋風街灯 4 本+木のボラード(B_atsunoyu、K 8:00・Y 1:57)
    s = sg.get('954786837')
    if s:
        d, r, nx_, ny_, tx_, ty_ = site.nearest_road(s['center'][0], s['center'][1])
        # 道の縁に沿って、看板の位置から ±9 m
        base = np.array([s['center'][0], s['center'][1]])
        pts = r['pts']
        seg = YB.seg_nearest(np.array([base[0]]), np.array([base[1]]), pts)
        px0, py0, tx, ty = float(seg[1][0]), float(seg[2][0]), float(seg[3][0]), float(seg[4][0])
        # 道の縁(看板側)
        side = 1.0 if ((base[0] - px0) * (-ty) + (base[1] - py0) * tx) > 0 else -1.0
        nrm = (-ty * side, tx * side)
        for off in (-9.0, -3.0, 3.0, 9.0):
            q = site.spot(px0 + tx * off, py0 + ty * off, tx, ty, -ty, tx, r['hw'], side, offs=(0.6, 0.3, 0.0), slides=(0.0, 1.5, -1.5, 3.0, -3.0))
            if q:
                western_lamp(pb, q[0], q[1], gz(q[0], q[1]) + 0.1, col='#2f5a45', h=3.2)
                cnt('lamp_green')
        for off in np.arange(-7.0, 7.01, 1.75):
            x, y = px0 + tx * off + nrm[0] * (r['hw'] + 0.15), py0 + ty * off + nrm[1] * (r['hw'] + 0.15)
            if site.free(x, y):
                log_bollard(pb, x, y, gz(x, y) + 0.05)
                cnt('bollard_log')

    # ---- 山本館の前: 黒い鋼管の街灯(丸い電球。C_street R 29:27)
    s = sg.get('948490088')
    if s:
        d, r, nx_, ny_, tx_, ty_ = site.nearest_road(s['center'][0], s['center'][1])
        seg = YB.seg_nearest(np.array([s['center'][0]]), np.array([s['center'][1]]), r['pts'])
        px0, py0, tx, ty = float(seg[1][0]), float(seg[2][0]), float(seg[3][0]), float(seg[4][0])
        side = 1.0 if ((s['center'][0] - px0) * (-ty) + (s['center'][1] - py0) * tx) > 0 else -1.0
        for off in (-4.0, 6.0):
            q = site.spot(px0 + tx * off, py0 + ty * off, tx, ty, -ty, tx, r['hw'], side, offs=(0.4, 0.1, -0.2), slides=(0.0, 2.0, -2.0, 4.0))
            if q:
                x, y = q
                steel_lamp(pb, x, y, math.atan2(-tx * side, ty * side), gz(x, y) + 0.1)
                cnt('lamp_steel')

    # ---- 益成屋の交差点: 赤白の車止めポール(C_street R 29:57)と青い案内標識(C_masunariya)
    s = sg.get('954965052')
    sign_boards = []
    if s:
        d, r, nx_, ny_, tx_, ty_ = site.nearest_road(s['center'][0], s['center'][1])
        seg = YB.seg_nearest(np.array([s['center'][0]]), np.array([s['center'][1]]), r['pts'])
        px0, py0, tx, ty = float(seg[1][0]), float(seg[2][0]), float(seg[3][0]), float(seg[4][0])
        side = 1.0 if ((s['center'][0] - px0) * (-ty) + (s['center'][1] - py0) * tx) > 0 else -1.0
        nrm = (-ty * side, tx * side)
        for off in (-2.4, -1.2, 0.0):
            x, y = px0 + tx * off + nrm[0] * (r['hw'] + 0.3), py0 + ty * off + nrm[1] * (r['hw'] + 0.3)
            if site.free(x, y):
                redwhite_bollard(pb, x, y, gz(x, y) + 0.05)
                cnt('bollard_redwhite')
        # 案内標識(門の前の支柱。標識の面は道の向きに直角=通りを来る人に向ける)
        q = site.spot(px0 + tx * 3.2, py0 + ty * 3.2, tx, ty, -ty, tx, r['hw'], side, offs=(0.5, 0.2, -0.1), slides=(0.0, 2.0, -2.0, 4.0, -4.0, 6.0))
        if q:
            x, y = q
            z0 = gz(x, y) + 0.05
            sign_post(pb, x, y, z0, 2.6)
            yaw = math.atan2(ty, tx)       # 道の進行方向を向く面
            fx, fy = math.cos(yaw), math.sin(yaw)
            sign_boards.append(dict(text='西の河原公園\n天狗山・白根山  292', kind='road', w=1.5, h=0.55,
                                    center=[x + fx * 0.06, y + fy * 0.06, z0 + 2.3], normal=[fx, fy, 0.0], right=[fy, -fx, 0.0],
                                    bg='#1c4f9c', fg='#f4f6f8', two=True, back='#8d9397', shape='rect', border=True, spec='road'))
            cnt('sign_guide')

    # ---- 山本館の「西の河原公園 大滝乃湯」案内板(B_yamamotokan、R 29:18 右)
    s = sg.get('948490088')
    if s:
        d, r, nx_, ny_, tx_, ty_ = site.nearest_road(s['center'][0], s['center'][1])
        seg = YB.seg_nearest(np.array([s['center'][0]]), np.array([s['center'][1]]), r['pts'])
        px0, py0, tx, ty = float(seg[1][0]), float(seg[2][0]), float(seg[3][0]), float(seg[4][0])
        side = 1.0 if ((s['center'][0] - px0) * (-ty) + (s['center'][1] - py0) * tx) > 0 else -1.0
        q = site.spot(px0 + tx * 14.0, py0 + ty * 14.0, tx, ty, -ty, tx, r['hw'], side, offs=(0.45, 0.2, -0.1), slides=(0.0, 2.0, -2.0, 4.0, -4.0, 6.0))
        if q:
            x, y = q
            z0 = gz(x, y) + 0.05
            sign_post(pb, x, y, z0, 2.4)
            yaw = math.atan2(ty, tx)
            fx, fy = math.cos(yaw), math.sin(yaw)
            sign_boards.append(dict(text='西の河原公園\n大滝乃湯', kind='road', w=1.3, h=0.5,
                                    center=[x + fx * 0.06, y + fy * 0.06, z0 + 2.1], normal=[fx, fy, 0.0], right=[fy, -fx, 0.0],
                                    bg='#1c4f9c', fg='#f4f6f8', two=True, back='#8d9397', shape='rect', border=True, spec='road'))
            cnt('sign_guide')

    # ---- 湯滝通りの東端近く: 青い丸の標識+補助標識「自転車を除く」(C_yukitaki_lane、W 21:06)
    r = site.roads.get(89004799)
    if r is not None:
        pts = r['pts']
        for (x, y, tx, ty, nx, ny, s_) in walk(pts, 1.0, max(0.0, 195.0 - 16.0)):
            px, py = x + nx * (r['hw'] + 0.5), y + ny * (r['hw'] + 0.5)
            if site.free(px, py, r['id']):
                z0 = gz(px, py) + 0.05
                sign_post(pb, px, py, z0, 2.7)
                fx, fy = -tx, -ty              # 通りを東へ来る人に向ける(進行方向 tx,ty は東向き)
                yaw_c = (fx, fy)
                sign_boards.append(dict(text='→', kind='road', w=0.6, h=0.6, shape='circle',
                                        center=[px + yaw_c[0] * 0.06, py + yaw_c[1] * 0.06, z0 + 2.4], normal=[fx, fy, 0.0], right=[fy, -fx, 0.0],
                                        bg='#1f58b0', fg='#f4f6f8', two=True, back='#8d9397', spec='road', arrow=True))
                sign_boards.append(dict(text='自転車を除く', kind='road', w=0.55, h=0.22, shape='rect',
                                        center=[px + yaw_c[0] * 0.06, py + yaw_c[1] * 0.06, z0 + 2.0], normal=[fx, fy, 0.0], right=[fy, -fx, 0.0],
                                        bg='#f4f6f8', fg='#1d1814', two=True, back='#8d9397', spec='road', border=True))
                cnt('sign_regulatory')
                break

    # ---- OSM の点: 自販機・ポスト・止まれ・マンホール
    def osm_nodes(pred):
        for e in site.osm['elements']:
            if e['type'] == 'node' and 'lat' in e and pred(e.get('tags', {})):
                yield e, C.xy(e)

    for e, (x, y) in osm_nodes(lambda t: t.get('amenity') == 'vending_machine'):
        if math.hypot(x, y) > R_CLIP:
            continue
        d, r, nx_, ny_, tx_, ty_ = site.nearest_road(x, y)
        yaw = math.atan2(ny_ - y, nx_ - x) if d > 0.01 else 0.0
        vending(pb, x, y, gz(x, y), yaw, ['#e9e7e1', '#c8372f', '#2d5fa8'][int(e['id']) % 3], seed=int(e['id']) % 5)
        cnt('vending')
    for e, (x, y) in osm_nodes(lambda t: t.get('amenity') == 'post_box'):
        if math.hypot(x, y) <= R_CLIP:
            round_post(pb, x, y, gz(x, y))
            cnt('post')
    for e, (x, y) in osm_nodes(lambda t: t.get('highway') == 'stop'):
        if math.hypot(x, y) > R_CLIP:
            continue
        d, r, nx_, ny_, tx_, ty_ = site.nearest_road(x, y)
        z0 = gz(x, y) + 0.05
        sign_post(pb, x, y, z0, 2.3)
        yaw = math.atan2(ny_ - y, nx_ - x)
        fx, fy = math.cos(yaw), math.sin(yaw)
        sign_boards.append(dict(text='止まれ', kind='road', w=0.8, h=0.7, shape='tri',
                                center=[x + fx * 0.06, y + fy * 0.06, z0 + 2.0], normal=[fx, fy, 0.0], right=[fy, -fx, 0.0],
                                bg='#c8191f', fg='#ffffff', two=True, back='#8d9397', spec='road'))
        cnt('sign_stop')
    manhole = 0
    for e, (x, y) in osm_nodes(lambda t: t.get('man_made') == 'manhole'):
        if math.hypot(x, y) <= R_CLIP:
            z0 = gz(x, y) + 0.1
            prism(pb, 'metal', (x, y), 0.32, 0.32, z0, z0 + 0.02, 12, lin('#5a5b58'))
            for k in (-0.15, 0.0, 0.15):
                obox(pb, 'dark', x, y, 0, -0.26, 0.26, k - 0.015, k + 0.015, z0 + 0.02, z0 + 0.03, lin('#2c2d2b'))
            manhole += 1
    cnt('manhole', manhole)

    # ---- 電柱と電線
    def pole_line(pts_poly, hw, side, spacing, s0, s1, kind, h, arm_col=None, alt=False, zig=0):
        poles = []
        k = 0
        for (x, y, tx, ty, nx, ny, s) in walk(pts_poly, spacing, s0, s1):
            sd = side if not alt else (side if k % 2 == 0 else -side)
            k += 1
            q = site.spot(x, y, tx, ty, nx, ny, hw, sd, slides=(0.0, 3.0, -3.0, 6.0, -6.0))
            if q is None:
                continue
            poles.append((q[0], q[1], math.atan2(ty, tx), kind, h, arm_col))
        return poles

    lines = []
    # 中央通り: コンクリート柱、歩道の東側(A_lawson_terminal「電柱と電線が通りの両側」)
    pts, hw = chain(site, [594139677, 594139678])
    lines.append(pole_line(pts, hw, -1, 30.0, 14.0, None, 'concrete', 8.0))
    # 西の河原通り 東半分(奈良屋〜山形屋): コンクリート柱、南側(C_street R 30:09〜31:09)
    pts, hw = chain(site, [954965074])
    lines.append(pole_line(pts, hw, -1, 26.0, 8.0, None, 'concrete', 8.0))
    # 西の河原通り 西半分(松むら〜するがや): 木の柱(黄色い腕木が 1 本)、交互(C_street R 31:24〜32:03)
    pts, hw = chain(site, [303901745])
    lines.append(pole_line(pts, hw, 1, 24.0, 6.0, 90.0, 'wood', 9.0, alt=True))
    # 湯滝通り: 細い木・コンクリの電柱、南側(C_yukitaki_lane W 21:06)
    pts, hw = chain(site, [89004799], reverse=(89004799,))
    lines.append(pole_line(pts, hw, 1, 30.0, 14.0, None, 'concrete', 8.0))
    npole = 0
    for li, poles in enumerate(lines):
        ins_all = []
        for pi_, (px, py, yaw, kind, h, arm) in enumerate(poles):
            ac = '#d6a82b' if (kind == 'wood' and pi_ == 3) else arm
            z = gz(px, py) + 0.1
            ins = utility_pole(pb, px, py, z, yaw + math.pi / 2 * 0 + math.pi / 2, kind, h, ac)
            ins_all.append(ins)
            npole += 1
        for a, b in zip(ins_all[:-1], ins_all[1:]):
            for pa, pb_ in zip(a, b):
                wire(pb, pa, pb_)
                cnt('wire')
    cnt('pole', npole)

    # ---- 白線(車道の縁)と横断歩道
    wl = PB()
    lines_w = [(594139677, 2.4), (594139678, 2.4), (954965074, 2.5), (303901745, 2.5)]
    for wid, off in lines_w:
        r = site.roads.get(wid)
        if r is None:
            continue
        rank = F.ROAD_RANK[r['cls']]
        zoff = 0.07 + 0.008 * rank + 0.03
        pts = r['pts']
        tan = np.zeros_like(pts)
        tan[1:-1] = pts[2:] - pts[:-2]
        tan[0] = pts[1] - pts[0]
        tan[-1] = pts[-1] - pts[-2]
        tan = tan / np.maximum(np.hypot(*tan.T), 1e-9)[:, None]
        nor = np.stack([-tan[:, 1], tan[:, 0]], axis=1)
        for sd in (-1, 1):
            o = sd * min(off, r['hw'] - 0.25)
            for i in range(len(pts) - 1):
                if any(math.hypot(*pts[j]) > R_CLIP for j in (i, i + 1)):
                    continue
                q = []
                ok = True
                for j in (i, i + 1):
                    for w in (-0.06, 0.06):
                        p = pts[j] + nor[j] * (o + w)
                        if YB.inside(np.array([p[0]]), np.array([p[1]]), site.loop_out)[0]:
                            ok = False
                        q.append((p[0], p[1], float(field.Z(p[0], p[1])) + zoff))
                if ok:
                    wl.poly('wall', [q[0], q[1], q[3], q[2]], lin('#e8e6df'), (0, 0, 1))
                    cnt('whiteline_seg')
    for e, (x, y) in osm_nodes(lambda t: t.get('crossing') == 'marked'):
        if math.hypot(x, y) > R_CLIP:
            continue
        d, r, nx_, ny_, tx_, ty_ = site.nearest_road(x, y)
        if d > 4:
            continue
        seg = YB.seg_nearest(np.array([x]), np.array([y]), r['pts'])
        tx, ty = float(seg[3][0]), float(seg[4][0])
        nx, ny = -ty, tx
        rank = F.ROAD_RANK[r['cls']]
        zoff = 0.07 + 0.008 * rank + 0.03
        nb = int(2 * r['hw'] / 0.9)
        for k in range(nb):
            a = -r['hw'] + 0.45 + k * 0.9 + (2 * r['hw'] - nb * 0.9) / 2
            q = []
            for (u, v) in ((a - 0.22, -1.5), (a + 0.22, -1.5), (a + 0.22, 1.5), (a - 0.22, 1.5)):
                px, py = x + tx * v + nx * u, y + ty * v + ny * u
                q.append((px, py, float(field.Z(px, py)) + zoff))
            wl.poly('wall', q, lin('#ecebe4'), (0, 0, 1))
        cnt('crosswalk')
    pb_lines = wl

    # ---- 光泉寺: 洋風街灯(D_stairs・D_hibi_toro)と赤い幟「奉納 南無薬師如来」(D_stairs)
    for (x, y) in ((-72.0, -93.4), (-75.6, -97.8), (-84.4, -103.3), (-128.0, -108.0), (-98.0, -118.0), (-111.0, -104.0)):
        if not site.in_building(x, y, 0.2) and math.hypot(x, y) < R_CLIP:
            western_lamp(pb, x, y, gz(x, y) + 0.1, h=3.5)
            cnt('lamp_kosenji')
    flights = [f for f in F.HOSEN if f['kind'] == 'main'][1:]
    nob = []
    for f in flights:
        p0, p1 = np.array(f['p0'], float), np.array(f['p1'], float)
        d = p1 - p0
        L = float(np.hypot(*d))
        d /= L
        right = np.array([d[1], -d[0]])
        n = max(2, int(L / 1.8))
        for i in range(n):
            t = (i + 0.5) / n
            p = p0 + (p1 - p0) * t + right * (f['width'] / 2 + 0.55)
            z = f['z0'] + (f['z1'] - f['z0']) * t - C.ZBASE
            # 旗の面は階段の登る向きに直角(登る人に正面)
            yaw = math.atan2(-d[1], -d[0])
            rec = nobori_pole(pb, float(p[0]), float(p[1]), z + 0.02, yaw, 3.5, 0.62, 2.4, '#bd2d27')
            rec.update(text='奉納 南無薬師如来', kind='nobori', bg='#bd2d27', fg='#f4efe3', two=True, shape='rect', spec='D_stairs', vertical=True)
            nob.append(rec)
            cnt('nobori')
    s = sg.get('1312003251')
    if s:
        n = np.array(s['normal'][:2])
        rgt = np.array(s['right'][:2])
        c = np.array(s['center'][:2]) + rgt * 1.9 + n * 1.0
        z0 = gz(c[0], c[1]) + 0.05
        rec = nobori_pole(pb, float(c[0]), float(c[1]), z0, math.atan2(n[1], n[0]), 3.4, 0.7, 2.9, '#f1eee6', '#2c2c2c')
        rec.update(text='お守り・お札', kind='nobori', bg='#f1eee6', fg='#1d1814', two=True, shape='rect', spec='D_omamori', vertical=True)
        nob.append(rec)
        cnt('nobori_white')

    all_signs = recs + sign_boards + nob
    return pb, pb_lines, all_signs, stats


# ====================================================================== 実行
def main():
    import time
    t0 = time.time()

    def log(*a):
        print('[props %.1fs]' % (time.time() - t0), *a, flush=True)
    field = F.Field(C.load_osm(), log=lambda *a: None)
    log('field ready')
    raw = collect_signs(field, '--refresh' in ARGS)
    log('signs collected: %d' % len(raw['signs']))
    site = Site(field, raw)
    pb, pbl, signs, stats = build_props(field, site, raw, log)
    pb.merge(pbl)
    tris = pb.tris()
    for s in signs:
        for k in ('center', 'normal', 'right'):
            s[k] = [round(float(v), 3) for v in s[k]]
        s['w'] = round(float(s['w']), 3)
        s['h'] = round(float(s['h']), 3)
    for s in signs:
        s.pop('spec', None)
    log('props tris %d, signs %d, stats %s' % (tris, len(signs), stats))
    log('rejected', site.why)
    out = C.OUT_WEB
    os.makedirs(out, exist_ok=True)
    json.dump(signs, open(os.path.join(out, 'signs.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    st = dict(tris=tris, signs=len(signs), by_mat=pb.tris_by_mat(), stats=stats)
    if '--count' in ARGS or C.bpy is None:
        print(json.dumps(st, ensure_ascii=False))
        return
    C.reset_scene()
    mats = P.get_materials()
    coll = C.new_collection('Props')
    objs = pb.to_objects('Props', mats, coll)
    size = C.export_glb(objs, os.path.join(out, 'props.glb'), pos_bits=16)
    st['glb_bytes'] = size
    os.makedirs(C.OUT_BLEND, exist_ok=True)
    json.dump(st, open(os.path.join(C.OUT_BLEND, 'props_stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('exported props.glb %d bytes' % size)


if __name__ == '__main__':
    main()
