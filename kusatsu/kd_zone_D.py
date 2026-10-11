# -*- coding: utf-8 -*-
"""kd_zone_D.py -- 草津 湯畑ジオラマ フェーズ8: 区域D(光泉寺の境内・石段の周り・湯畑観光駐車場)の建物を BuildingSpec で 1 棟ずつ作る。

区域D = kd_common.zone_of が 'D' を返す範囲(x < -25 かつ y < -80)。OSM 23 外形(+石灯籠・碑・像を小さな spec として足す)。
- 手作り(カード+動画フレーム): 本堂(試作のコピー)、山門(仁王門)、釈迦堂(茅葺き)、五重塔(5 重+相輪)、不動堂、鐘楼、手水舎、湯喜堂、お守り頒布所、
  庫裏(長い棟)、ぬ志勇旅館、湯畑観光駐車場、石灯籠(OSM の 6 点+釈迦堂の参道)、弘法大師像、記念碑、「草津山 光泉寺」の石碑。
- 推定(動画で確認できない棟): kd_zone_C._generic と同じ規則。石段・擁壁は kd_terrain(フェーズ2)のまま。
- 看板の文字・街灯・幟・植物はフェーズ9・10。

実行(他タブの Blender が動いていないことを tasklist で確認して 1 つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_zone_D.py      # buildings_D.glb だけ
  python kusatsu/kd_zone_D.py --count     # Blender 無しで三角形数(1 棟ごと)
  python kusatsu/kd_zone_D.py --list      # 1 棟ごとの階数・屋根・様式・根拠(phase8_notes 用)
地形(敷地の均し)を変えたときは kd_terrain.py -- --zones=D で terrain.glb と buildings_D.glb を作り直す。
"""
import math
import os
import sys
from dataclasses import replace as dreplace

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import kd_common as C  # noqa: E402
import kd_parts as P  # noqa: E402
import kd_zone_A as ZA  # noqa: E402
import kd_zone_C as ZC  # noqa: E402
from kd_parts import (BuildingSpec, WallFinish, Timber, Facade, Balcony, Pent, Roof, Attach, Frame, lin, tint, beam, prism)  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]

DARK = '#2b2420'
VERM = '#b23a2c'          # 朱
VERM_D = '#8e2f25'
site, base_for, cut, ring_of, bld, uvec, bearing = ZA.site, ZA.base_for, ZA.cut, ZA.ring_of, ZA.bld, ZA.uvec, ZA.bearing
face_z, rect = ZC.face_z, ZC.rect


def get_field():
    return ZA.get_field()


def set_field(field):
    ZA.set_field(field)


def _gz(x, y):
    return float(get_field().Z(np.array([x]), np.array([y]))[0])


def fbox(pb, fr, m, x0, x1, y0, y1, z0, z1, col, skip=()):
    """Frame fr の局所座標(x=u、y=v)で箱を置く。"""
    o = fr.P(x0, y0, z0)
    ex = np.array(fr.P(x1, y0, z0)) - np.array(o)
    ey = np.array(fr.P(x0, y1, z0)) - np.array(o)
    P.box(pb, m, o, tuple(ex), tuple(ey), (0.0, 0.0, z1 - z0), col, skip)


# ====================================================================== 区域内だけで使う部品(印がある時だけ効く)
def _gate_walls(self):
    """山門(仁王門): 中央が通路(幅 3 m、板敷)、左右が仁王像を納める朱の壁の室(六角の金網の窓)、通路の両端に丸い柱+貫+組物。"""
    pb, lod = self.pb, self.lod
    self.edge_ops = {}
    ring = self.rings[0]
    (cx, cy), ang, L, Wd = P.obb(ring)
    u = P.bearing_vec(self.spec.zD_axis)
    fr = Frame((cx, cy), u, L / 2, Wd / 2)
    hx, hy = fr.hx, fr.hy
    z0 = self.base_z
    H = self.ztop - z0
    red, redd = lin(VERM), lin(VERM_D)
    pas = 1.5                       # 通路の半幅
    # 板敷の床
    fbox(pb, fr, 'wood', -hx, hx, -pas, pas, z0 - 0.08, z0 + 0.02, lin('#8c8478'))
    for sg in (1, -1):
        y0, y1 = (pas, hy - 0.15) if sg > 0 else (-hy + 0.15, -pas)
        fbox(pb, fr, 'paint', -hx + 0.2, hx - 0.2, y0, y1, z0, z0 + 1.0, red)          # 腰の板壁
        fbox(pb, fr, 'paint', -hx + 0.2, hx - 0.2, y0, y1, z0 + 1.0, z0 + H - 0.4, tint(red, 0.96))
        # 端の面の金網の窓(中が暗い)
        for sx in (1, -1):
            xe = sx * (hx - 0.2)
            fbox(pb, fr, 'dark', xe - 0.0 if sx < 0 else xe, xe + (-0.04 if sx < 0 else 0.04), y0 + 0.3, y1 - 0.3, z0 + 1.2, z0 + H - 0.7, lin('#1f1c1a'),
                 skip=())
            if lod >= 1:
                for yy in np.linspace(y0 + 0.3, y1 - 0.3, 7):
                    fbox(pb, fr, 'metal', xe + (-0.06 if sx < 0 else 0.0), xe + (0.0 if sx < 0 else 0.06), yy - 0.015, yy + 0.015, z0 + 1.2, z0 + H - 0.7,
                         lin('#8c8c88'))
        # 室の側面(外)にも同じ金網窓(1 つ)
        yo = (hy - 0.15) if sg > 0 else (-hy + 0.15)
        fbox(pb, fr, 'dark', -1.2, 1.2, yo, yo + sg * 0.04, z0 + 1.3, z0 + H - 0.8, lin('#1f1c1a'))
    # 通路の柱(丸い)と貫・長押
    for sx in (1, -1):
        for sg in (1, -1):
            c = fr.P(sx * (hx - 0.25), sg * pas, 0)
            prism(pb, 'paint', c, 0.2, 0.18, z0, z0 + H - 0.2, 8, red)
            if lod >= 1:
                prism(pb, 'stone', c, 0.3, 0.26, z0 - 0.04, z0 + 0.14, 8, lin('#8d8981'))
    for sx in (1, -1):
        xe = sx * (hx - 0.25)
        fbox(pb, fr, 'paint', xe - 0.17, xe + 0.17, -hy + 0.1, hy - 0.1, z0 + H - 0.62, z0 + H - 0.3, redd)         # 内法長押
        fbox(pb, fr, 'paint', xe - 0.15, xe + 0.15, -hy + 0.1, hy - 0.1, z0 + H - 1.2, z0 + H - 1.0, redd)           # 貫
        if lod >= 1:
            for yy in np.linspace(-hy + 0.4, hy - 0.4, 6):                                                          # 組物(出組風の升)
                fbox(pb, fr, 'wood', xe - 0.26, xe + 0.26, yy - 0.2, yy + 0.2, z0 + H - 0.3, z0 + H, lin('#f1ece2'))
    # 高欄(低い朱の板の柵)を通路の前後に
    for sx in (1, -1):
        for sg in (1, -1):
            fbox(pb, fr, 'paint', sx * (hx + 0.1) - 0.04, sx * (hx + 0.1) + 0.04, sg * (pas + 0.3), sg * (hy - 0.1), z0 - 0.2, z0 + 0.9, red)
    # 天井の梁(中の組み天井)
    fbox(pb, fr, 'wood', -hx + 0.3, hx - 0.3, -pas, pas, z0 + H - 0.3, z0 + H - 0.1, lin('#d9d2c2'))


def _bell_walls(self):
    """鐘楼: 方 1 間の吹き放ち。石の台(1 段)、4 本の朱の柱、2 段の貫、梵鐘(黒い鋳鉄)。"""
    pb, lod = self.pb, self.lod
    self.edge_ops = {}
    ring = self.rings[0]
    (cx, cy), ang, L, Wd = P.obb(ring)
    fr = Frame((cx, cy), (math.cos(ang), math.sin(ang)), L / 2, Wd / 2)
    z0, z1 = self.base_z, self.ztop
    red = lin(VERM)
    fbox(pb, fr, 'stone', -fr.hx - 0.1, fr.hx + 0.1, -fr.hy - 0.1, fr.hy + 0.1, z0 - 0.4, z0 + 0.0, lin('#8f8c86'))
    for sx in (1, -1):
        for sy in (1, -1):
            fbox(pb, fr, 'paint', sx * (fr.hx - 0.25) - 0.15, sx * (fr.hx - 0.25) + 0.15, sy * (fr.hy - 0.25) - 0.15, sy * (fr.hy - 0.25) + 0.15,
                 z0, z1 - 0.2, red, skip=('-z',))
    for zz in (z1 - 0.55, z1 - 1.4):
        for sg in (1, -1):
            fbox(pb, fr, 'paint', -fr.hx + 0.1, fr.hx - 0.1, sg * (fr.hy - 0.25) - 0.08, sg * (fr.hy - 0.25) + 0.08, zz, zz + 0.2, lin(VERM_D))
            fbox(pb, fr, 'paint', sg * (fr.hx - 0.25) - 0.08, sg * (fr.hx - 0.25) + 0.08, -fr.hy + 0.1, fr.hy - 0.1, zz, zz + 0.2, lin(VERM_D))
    fbox(pb, fr, 'wood', -fr.hx + 0.1, fr.hx - 0.1, -0.05, 0.05, z1 - 0.4, z1 - 0.3, lin('#3a2e28'))
    bc = fr.P(0, 0, 0)
    prism(pb, 'metal', bc, 0.34, 0.4, z0 + 0.8, z0 + 1.8, 10, lin('#2a2826'))                     # 梵鐘
    prism(pb, 'metal', bc, 0.4, 0.42, z0 + 0.8, z0 + 0.9, 10, lin('#2a2826'), top=False)
    prism(pb, 'metal', bc, 0.1, 0.08, z0 + 1.8, z0 + 2.15, 6, lin('#2a2826'))
    if lod >= 1:
        fbox(pb, fr, 'stone', -fr.hx - 0.1, fr.hx + 0.1, fr.hy + 0.15, fr.hy + 0.55, z0 - 0.3, z0 + 0.35, lin('#3a3836'))


def _chozu_walls(self):
    """手水舎: 4 本の黒褐色の柱、桁、石の水盤。"""
    pb = self.pb
    self.edge_ops = {}
    ring = self.rings[0]
    (cx, cy), ang, L, Wd = P.obb(ring)
    fr = Frame((cx, cy), (math.cos(ang), math.sin(ang)), L / 2, Wd / 2)
    z0, z1 = self.base_z, self.ztop
    col = lin('#3a2c24')
    for sx in (1, -1):
        for sy in (1, -1):
            fbox(pb, fr, 'wood', sx * (fr.hx - 0.2) - 0.08, sx * (fr.hx - 0.2) + 0.08, sy * (fr.hy - 0.2) - 0.08, sy * (fr.hy - 0.2) + 0.08, z0, z1 - 0.15, col,
                 skip=('-z',))
            fbox(pb, fr, 'stone', sx * (fr.hx - 0.2) - 0.14, sx * (fr.hx - 0.2) + 0.14, sy * (fr.hy - 0.2) - 0.14, sy * (fr.hy - 0.2) + 0.14, z0 - 0.3, z0 + 0.25,
                 lin('#8d8981'), skip=('-z',))
    for sg in (1, -1):
        fbox(pb, fr, 'wood', -fr.hx, fr.hx, sg * (fr.hy - 0.2) - 0.07, sg * (fr.hy - 0.2) + 0.07, z1 - 0.4, z1 - 0.15, col)
    fbox(pb, fr, 'stone', -0.7, 0.7, -0.35, 0.35, z0 - 0.1, z0 + 0.55, lin('#8a8780'))
    fbox(pb, fr, 'dark', -0.58, 0.58, -0.23, 0.23, z0 + 0.5, z0 + 0.56, lin('#30363a'))


def _item_walls(self):
    """石灯籠(春日型)・石碑・像: ring の重心に 1 基。kind は spec.zD_kind。"""
    pb = self.pb
    self.edge_ops = {}
    ring = self.rings[0]
    (cx, cy), ang, L, Wd = P.obb(ring)
    c = (cx, cy)
    z0 = self.base_z
    kind = self.spec.zD_kind
    if kind == 'lantern':
        g = lin('#8c9088')
        g2 = lin('#7c8078')
        fr = Frame(c, (math.cos(ang), math.sin(ang)), 0.25, 0.25)
        fbox(pb, fr, 'stone', -0.27, 0.27, -0.27, 0.27, z0 - 0.15, z0 + 0.12, g2)                       # 基礎
        prism(pb, 'stone', (cx, cy), 0.26, 0.2, z0 + 0.12, z0 + 0.26, 6, g)                            # 反花
        prism(pb, 'stone', (cx, cy), 0.1, 0.1, z0 + 0.26, z0 + 0.85, 8, g)                             # 竿
        prism(pb, 'stone', (cx, cy), 0.22, 0.26, z0 + 0.85, z0 + 0.95, 6, g)                           # 中台
        if self.lod >= 1:
            prism(pb, 'stone', (cx, cy), 0.2, 0.18, z0 + 0.95, z0 + 1.0, 6, g2)
        for k in range(6):                                                                              # 火袋(六角、4 面に火口)
            a0 = k * math.pi / 3
            a1 = (k + 1) * math.pi / 3
            r = 0.2
            q = [(cx + r * math.cos(a0), cy + r * math.sin(a0)), (cx + r * math.cos(a1), cy + r * math.sin(a1))]
            nrm = (math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0.0)
            col = lin('#1f2220') if k % 3 != 2 else g
            pb.poly('dark' if k % 3 != 2 else 'stone', [(q[0][0], q[0][1], z0 + 1.0), (q[1][0], q[1][1], z0 + 1.0), (q[1][0], q[1][1], z0 + 1.34),
                                                         (q[0][0], q[0][1], z0 + 1.34)], col, nrm)
        prism(pb, 'stone', (cx, cy), 0.44, 0.1, z0 + 1.34, z0 + 1.62, 6, g)                            # 笠
        prism(pb, 'stone', (cx, cy), 0.07, 0.0, z0 + 1.62, z0 + 1.78, 6, g)                            # 宝珠
    elif kind == 'stele':
        w, d, h = self.spec.zD_size
        col = lin(self.spec.zD_col)
        fr = Frame(c, (math.cos(ang), math.sin(ang)), w / 2, d / 2)
        if self.spec.zD_round:
            prism(pb, 'stone', (cx, cy), 0.62, 0.58, z0 - 0.1, z0 + 0.35, 12, lin('#8a8780'))
            z0 += 0.35
        else:
            fbox(pb, fr, 'stone', -w * 0.75, w * 0.75, -d * 0.9, d * 0.9, z0 - 0.15, z0 + 0.25, lin('#8a8780'))
            z0 += 0.25
        fbox(pb, fr, 'stone', -w / 2, w / 2, -d / 2, d / 2, z0, z0 + h, col)
        if self.spec.zD_plaque:
            fbox(pb, fr, 'stone', -w * 0.3, w * 0.3, d / 2, d / 2 + 0.02, z0 + h * 0.2, z0 + h * 0.85, lin(self.spec.zD_plaque))
    elif kind == 'statue':
        fr = Frame(c, (math.cos(ang), math.sin(ang)), 0.5, 0.5)
        fbox(pb, fr, 'stone', -0.55, 0.55, -0.55, 0.55, z0 - 0.15, z0 + 1.2, lin('#8f8c86'))
        fbox(pb, fr, 'stone', -0.62, 0.62, -0.62, 0.62, z0 + 1.2, z0 + 1.3, lin('#7d7a74'))
        bz = z0 + 1.3
        bronze = lin('#4b5a4a')
        prism(pb, 'metal', (cx, cy), 0.3, 0.2, bz, bz + 1.0, 8, bronze)
        prism(pb, 'metal', (cx, cy), 0.14, 0.12, bz + 1.0, bz + 1.22, 8, bronze)
        prism(pb, 'metal', (cx, cy), 0.34, 0.0, bz + 1.2, bz + 1.34, 8, bronze)                         # 笠
        beam(pb, 'metal', (cx, cy, bz + 0.2), (cx + 0.1, cy, bz + 1.5), 0.03, 0.03, lin('#6a5a3a'))      # 錫杖


def att_zD_sorin(self, A):
    """五重塔の相輪: 露盤・伏鉢・請花・九輪・水煙・宝珠(金)。屋根の頂点の上に。"""
    pb, lod = self.pb, self.lod
    fr = self.roofinfo.get('fr')
    zr = self.roofinfo.get('zr', self.ztop)
    c = fr.P(0, 0, 0)[:2]
    gold = lin('#c8a23a')
    dk = lin('#4a2622')
    z = zr - 0.1
    prism(pb, 'wood', c, 0.62, 0.58, z, z + 0.28, 4, dk, rot=math.pi / 4)                              # 露盤
    z += 0.28
    prism(pb, 'metal', c, 0.5, 0.18, z, z + 0.4, 12, gold)                                              # 伏鉢
    z += 0.4
    prism(pb, 'metal', c, 0.2, 0.26, z, z + 0.16, 8, gold)                                              # 請花
    z += 0.16
    prism(pb, 'metal', c, 0.06, 0.06, z, z + 2.9, 6, gold)                                              # 心柱
    for k in range(9):                                                                                  # 九輪
        r = 0.46 - 0.025 * k
        prism(pb, 'metal', c, r, r * 0.9, z + 0.1 + 0.26 * k, z + 0.16 + 0.26 * k, 10 if lod >= 1 else 8, gold, bottom=True)
    z += 2.5
    prism(pb, 'metal', c, 0.22, 0.1, z, z + 0.28, 6, gold)                                              # 水煙
    prism(pb, 'metal', c, 0.14, 0.0, z + 0.28, z + 0.55, 8, gold)                                       # 宝珠
    self.signs = self.signs


_PREV_WALLS = P.Builder.walls


def _walls_D(self):
    k = getattr(self.spec, 'zD', None)
    if k == 'gate':
        return _gate_walls(self)
    if k == 'bell':
        return _bell_walls(self)
    if k == 'chozu':
        return _chozu_walls(self)
    if k == 'item':
        return _item_walls(self)
    return _PREV_WALLS(self)


P.Builder.walls = _walls_D
P.Builder.att_zD_sorin = att_zD_sorin


# ====================================================================== 手作り(カードあり)
HONDEN_MAIN = [(-118.16, -128.70), (-125.03, -111.58), (-141.51, -118.08), (-134.66, -135.21)]


def honden():
    """光泉寺 本堂(1311927446、D_honden、R 22:36 f_455 ほか): kd_parts_test.honden() のコピー。一重の入母屋・明灰の金属板、朱の柱・長押+白壁、
    正面(東北東)に板戸と連子窓・花頭窓、縁にステンレスの手すり、向拝(低い庇)と石段 5 段。"""
    tim = Timber('#b23a2c', w=0.24, proud=0.05, posts='bay', beams=('bottom', 'top', 'head'), mat='paint')
    fac = Facade(bay=2.6, margin=0.25, frame='wood', glass='#2b2622', door_col='#6e5038', lattice_col='#8d9293', rev=0.16,
                 sizes={'P': (None, 3.05, 0.0), 'L': (1.7, 1.55, 0.95), 'K': (1.05, 1.6, 0.85)})
    return BuildingSpec(
        id='1311927446', name='光泉寺 本堂', zone='D', ring=HONDEN_MAIN, floors=1, floor_h=5.0, found_h=0.9, found='stone', found_col='#a19d94',
        front=68, replaces=['1311927446'],
        walls={'*': WallFinish('plaster', '#f0ede6', timber=tim)},
        facades={'front': dreplace(fac, pattern={1: 'KLPPPLK'}), 'left': dreplace(fac, pattern={1: '.L.K.L.'}),
                 'right': dreplace(fac, pattern={1: '.L.K.L.'}), '*': dreplace(fac, pattern={1: '.......'})},
        balconies=[Balcony(1, 'front', depth=1.5, rail='steel', extend=1.65, ends=False, gap=(0.515, 5.8), slab_color='#c7b49a', brackets=False),
                   Balcony(1, ['left', 'right'], depth=1.5, rail='steel', extend=0.15, ends=False, slab_color='#c7b49a', brackets=False)],
        roof=Roof('irimoya', 'metal', slope=0.46, eave=1.9, verge=0.6, irimoya_k=0.45, color='#a7acae', hafu_col='#8e2f25', kengyo=True,
                  soffit_col='#ece8dd', rafters=True, rafter_col='#b23a2c', gable_style='lattice', gable_col='#f0ede6', gutters=False),
        attach=[
            Attach('porch', side='front', at=0.515, w=7.4, d=3.7, h=3.5, color='#aab0b2', color2='#b23a2c',
                   prm=dict(roof='shed', mat='metal', slope=0.18, platform=False, post_mat='paint')),
            Attach('steps', side='front', at=0.515, w=5.6, d=1.5, prm=dict(tread=0.36)),
            Attach('sign', side='front', floor=1, z=3.9, w=1.0, h=0.42, style='yoko', color='#2a2522', color2='#8e2f25', d=0.0),
        ],
        lod=2, age=0.25, note='試作のコピー。扁額は判読不能なので板だけ')


def sanmon():
    """山門(955188993、D_sanmon、R 21:12 f_425 / R 21:21 f_428 / R 25:57 f_520〜526): 石段の途中に載る一重の寄棟。全体が朱、中央が通路(板敷)、
    左右が仁王像の室(六角の金網の窓)、灰銀の金属板(とんとん葺き風)、軒の出が大きい。通路は南西(方位 229°)へ抜ける。"""
    c = (-70.5, -92.6)
    ring = rect(c, 229.0, 8.4, 7.6)
    sp = BuildingSpec(
        id='955188993', name='光泉寺 山門(仁王門)', zone='D', ring=ring, floors=1, floor_h=3.7, found='stone', found_h=0.3, found_col='#8d8981', front=49,
        replaces=['955188993'], walls={'*': WallFinish('paint', VERM)}, facades={'*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('hip', 'tonton', slope=0.55, eave=1.5, color='#8f9498', hafu_col=VERM_D, soffit_col='#c9b79c', rafters=True, rafter_col=VERM_D, gutters=False),
        lod=2, age=0.3, note='扁額は見えない。通路の床は板敷、左右の室の金網の窓は端の面だけ')
    sp.zD, sp.zD_axis = 'gate', 229.0
    return sp


def shakado():
    """釈迦堂(912422963、D_shakado、R 24:36〜24:57 f_493〜500): 一重、茅葺きの寄棟(厚い茅、丸い軒先)、小さな千鳥破風、朱の縁と高欄が全周、
    南向きの向拝(茅葺きの庇、朱の柱、3 段の階段)、緑の連子窓(火灯窓)。壁は古い暗茶。"""
    ring = C.ccw([(-114.5, -91.4), (-113.3, -99.9), (-105.8, -98.5), (-107.1, -90.3)])
    zf = face_z(ring, 185)
    fac = Facade(bay=2.4, margin=0.4, pattern={1: 'K.K'}, frame='wood', glass='#2a352c', lattice_col='#3f6a4a', door_col='#5a3a2a',
                 sizes={'K': (1.0, 1.5, 0.8)})
    return BuildingSpec(
        id='912422963', name='釈迦堂', zone='D', ring=ring, floors=1, floor_h=3.0, found='stone', found_h=0.9, found_col='#8d8981', base_z=zf + 0.9, front=185,
        replaces=['912422963'], use_obb=True,
        walls={'*': WallFinish('plaster', '#4a3a30', timber=Timber('#a63a2c', w=0.18, proud=0.04, posts='bay', beams=('bottom', 'top', 'head'), mat='paint'))},
        facades={'front': fac, '*': dreplace(fac, pattern={1: '.K.'}, lod=1)},
        balconies=[Balcony(1, ['front', 'back', 'left', 'right'], depth=0.9, rail='wood', color='#a63a2c', slab_color='#8a5a40', z=0.0, rail_h=0.85, brackets=True,
                           ends=False)],
        roof=Roof('hip', 'kaya', slope=0.75, eave=1.6, color='#6b5a43', hafu_col='#4a3a30', soffit_col='#7a6a52', gutters=False, chidori=[(0.0, 2.6, 1)]),
        attach=[Attach('porch', side='front', at=0.5, w=3.0, d=2.4, h=3.0, color='#6b5a43', color2='#a63a2c',
                       prm=dict(roof='shed', mat='kaya', slope=0.5, platform=True, post_mat='paint')),
                Attach('steps', side='front', at=0.5, w=2.2, d=1.0, prm=dict(tread=0.2))],
        lod=2, age=0.4, note='背面と側面は動画に出ない(推定)。幟・石香炉は小物(フェーズ9)')


def gojunoto():
    """五重塔(1312003250、D_gojunoto、R 23:42〜23:57 f_475〜480): 全体が朱、初重は白壁に朱の扉(両開き)と緑の連子窓、二重〜五重は朱の壁と高欄、
    各重に深い軒の暗い赤の屋根、頂部に金の相輪(九輪・宝珠)。高さは推定(相輪まで約 17 m)。工事の柵は作らない。"""
    ring = ring_of('1312003250')
    zf = _gz(*site('1312003250')['c'])
    base = zf + 0.5
    tiers = []
    heights = [3.3, 2.5, 2.4, 2.3, 2.2]
    z = base
    for k in range(5):
        r = ring if k == 0 else P.offset_ring(ring, 0.38 * k)
        red = '#c4381f'
        rt = Roof('hip', 'metal', slope=0.42, eave=1.5 - 0.06 * k, color='#4a2622', hafu_col=VERM_D, soffit_col='#8e2f25', rafters=True, rafter_col=VERM_D, gutters=False)
        if k == 0:
            fac = Facade(bay=1.8, margin=0.3, pattern={1: 'L.DD.L'}, frame='wood', glass='#2a352c', lattice_col='#3f6a4a', door_col='#a63a2c',
                         sizes={'L': (0.8, 1.4, 0.9), 'D': (1.1, 2.2, 0.0)})
            walls = {'*': WallFinish('plaster', '#f2efe8', timber=Timber('#b23a2c', w=0.22, proud=0.05, posts='bay', beams=('bottom', 'top', 'head'), mat='paint'))}
            fcs = {'front': fac, '*': dreplace(fac, pattern={1: '.L.'}, lod=1)}
        else:
            walls = {'*': WallFinish('paint', red, timber=Timber('#8e2a1f', w=0.18, proud=0.04, posts='bay', beams=('bottom', 'top')))}
            fcs = {'*': Facade(bay=1.5, pattern={1: '.W.'}, frame='wood', glass='#2a352c', lattice_col='#3f6a4a', lod=1, sizes={'W': (0.7, 1.0, 0.8)})}
        sp = BuildingSpec(
            id='1312003250' if k == 0 else '1312003250#%d' % (k + 1), name='光泉寺 五重塔 %d 重' % (k + 1), zone='D', ring=r, floors=1, floor_h=heights[k],
            found='stone' if k == 0 else 'none', found_h=0.5, found_col='#8d8981', base_z=z, front=158, replaces=(['1312003250'] if k == 0 else []),
            same_level=False, walls=walls, facades=fcs, roof=rt,
            balconies=[Balcony(1, ['front', 'back', 'left', 'right'], depth=0.8, rail='wood', color='#a63a2c', slab_color='#8e2f25', z=0.0, rail_h=0.8, ends=False,
                               brackets=False)] if k > 0 else [],
            attach=[Attach('zD_sorin')] if k == 4 else [],
            lod=2 if k < 2 else 1, age=0.3, note='相輪を含む高さは推定(工事用の柵は省いた)' if k == 0 else '')
        tiers.append(sp)
        z += heights[k]
    main = tiers[0]
    main.wings = tiers[1:]
    main.same_level = True
    return main


def fudodo():
    """不動堂(1311927452、D_fudodo_shoro、R 25:42〜26:12 f_515〜524): 方 1 間の小堂、黒い宝形屋根、白壁に朱の柱、扉は暗い赤。名称の文字は読めない。"""
    ring = ring_of('1311927452')
    zf = face_z(ring, 20)
    return BuildingSpec(
        id='1311927452', name='不動堂', zone='D', floors=1, floor_h=3.0, found='stone', found_h=0.35, found_col='#8d8981', base_z=zf + 0.35, front=20, use_obb=True,
        walls={'*': WallFinish('plaster', '#f0ede6', timber=Timber('#9a3226', w=0.18, proud=0.04, posts='bay', beams=('bottom', 'top', 'head'), mat='paint'))},
        facades={'front': Facade(bay=1.5, margin=0.3, pattern={1: '.D.'}, frame='wood', door_col='#7a2c22', sizes={'D': (1.1, 2.2, 0.0)}), '*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('hogyo', 'kawara', slope=0.55, eave=0.9, color='#2e2b2a', hafu_col='#2b2420', soffit_col='#a9998a'),
        lod=2, age=0.35)


def shorou():
    """鐘楼(1311927451、D_fudodo_shoro、R 25:15〜25:30 f_506〜511): 石垣の上、方 1 間の吹き放ち、4 本の朱の柱+貫、梵鐘、暗褐色〜黒の宝形、垂木の木口が白。"""
    ring = ring_of('1311927451')
    zf = face_z(ring, 225)
    sp = BuildingSpec(
        id='1311927451', name='鐘楼', zone='D', floors=1, floor_h=3.0, found='stone', found_h=0.3, found_col='#8d8981', base_z=zf + 0.4, front=225, use_obb=True,
        walls={'*': WallFinish('paint', VERM)}, facades={'*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('hogyo', 'kawara', slope=0.5, eave=0.95, color='#33292a', hafu_col='#2b2420', soffit_col='#a9998a', rafters=True, rafter_col='#efe9da'),
        lod=2, age=0.3)
    sp.zD = 'bell'
    return sp


def chozusha():
    """手水舎(1311927453、D_fudodo_shoro、R 22:12 f_445): 黒褐色の柱 4 本、暗い瓦の切妻、石の水盤、柱の根元は石積み。"""
    ring = ring_of('1311927453')
    zf = face_z(ring, 45)
    sp = BuildingSpec(
        id='1311927453', name='手水舎', zone='D', floors=1, floor_h=2.9, found='none', base_z=zf + 0.1, front=45, use_obb=True,
        walls={'*': WallFinish('paint', '#3a2c24')}, facades={'*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('gable', 'kawara', slope=0.5, eave=0.6, verge=0.35, axis='long', color='#3e4146', hafu_col='#2b2420', soffit_col='#8a7a6a'),
        lod=1, age=0.3)
    sp.zD = 'chozu'
    return sp


def yukido():
    """湯喜堂(955188994、D_yukido、R 21:27 f_430): 方 1 間の小堂、白漆喰の大壁、黒褐色の宝形、軒下に暗い茶の組物、左側面に暗い木の格子戸。"""
    ring = ring_of('955188994')
    zf = face_z(ring, 49)
    return BuildingSpec(
        id='955188994', name='湯喜堂', zone='D', floors=1, floor_h=3.0, found='stone', found_h=0.3, found_col='#8d8981', base_z=zf + 0.3, front=49, use_obb=True,
        walls={'*': WallFinish('plaster', '#f0ede6')},
        facades={'left': Facade(bay=1.5, margin=0.3, pattern={1: '.K.'}, frame='dark', lattice_col='#3a2c24', sizes={'K': (0.9, 1.9, 0.0)}), '*': Facade(pattern={1: '.'}, lod=0)},
        roof=Roof('hogyo', 'kawara', slope=0.5, eave=0.65, color='#33292a', hafu_col='#3a2c24', soffit_col='#6a4a38', rafters=True, rafter_col='#4a3226'),
        lod=2, age=0.3)


def omamori():
    """お守り頒布所(1312003251、D_omamori、R 23:18 f_467 / R 24:27〜24:30): 一重の切妻、赤い縁取りの暗灰の板葺き、白漆喰+黒褐色の腰板+朱の柱、
    東の長辺に販売窓の台と暗い窓、幟(白)。OSM の外形(2 m 角)は小さすぎるので実物の寸法(4.5 x 2.5 m)に置き換えた。"""
    ring = rect((-116.0, -110.0), 0.0, 4.5, 2.5)
    return BuildingSpec(
        id='1312003251', name='お守り頒布所', zone='D', ring=ring, floors=1, floor_h=2.9, found='stone', found_h=0.25, found_col='#8d8981', base_z=_gz(-114.5, -110.0) + 0.25,
        front=90, replaces=['1312003251'],
        walls={'*': WallFinish('plaster', '#f1eee7', timber=Timber('#b23a2c', w=0.12, posts='bay', beams=('bottom', 'top', 'head'), mat='paint'),
                               koshi=(0.8, 'board_v', '#3a2c24'))},
        facades={'front': Facade(bay=1.4, margin=0.3, pattern={1: 'WWW'}, frame='wood', glass='#2a2622', sizes={'W': (1.0, 1.0, 1.0)}),
                 '*': Facade(bay=2.0, win='W.', ground='.D', frame='wood', door_col='#a63a2c', lod=0)},
        roof=Roof('gable', 'metal', slope=0.4, eave=0.7, verge=0.5, axis=0.0, color='#5b5f62', hafu_col='#b23a2c', soffit_col='#d8cdb8', gutters=False),
        attach=[Attach('nobori', side='front', floor=1, s=0.5, w=1.0, n=1, d=0.9, color='#f2efe6', color2='#4a3a30'),
                Attach('sign', side='front', floor=1, at=0.5, z=2.6, w=2.0, h=0.4, d=0.0, style='yoko', color='#7a2a24', color2='#2b2420', text='お守り頒布所')],
        lod=2, age=0.3, note='外形は実物の寸法に拡大')


def kuri():
    """庫裏(912422961、D_kuri、R 24:15 f_486 / R 25:09 f_504): 境内の南端の横長の白い建物。二階の長い切妻(緩い勾配、茶〜赤茶の大きな屋根)、
    白漆喰に朱の柱と連続する窓。北の長辺に沿う矩形を主棟、南の出っ張りを低い棟に分けた。"""
    ring = ring_of('912422961')
    d = np.array((0.952, 0.302))
    n = np.array((0.302, -0.952))
    p0 = np.array((-124.3, -134.3)) + n * 13.0
    main = cut(ring, p0, n, -1)
    rest = cut(ring, p0, n, 1)
    fac = Facade(bay=2.2, margin=0.4, win='W', ground='W', frame='alu', glass='#4a555b', sizes={'W': (1.5, 1.3, 0.9)})
    zf = face_z(main, 340)
    out = [BuildingSpec(
        id='912422961', name='庫裏(推定)', zone='D', ring=main, use_obb=True, floors=2, floor_h=[3.3, 3.0], found='concrete', found_h=0.3, base_z=zf + 0.3, front=340,
        replaces=['912422961'],
        walls={'*': WallFinish('plaster', '#f1eee7', timber=Timber('#a63a2c', w=0.16, proud=0.04, posts='bay', beams=('bottom', 'top'), mat='paint'))},
        facades={'front': fac, 'back': dreplace(fac, lod=1), '*': dreplace(fac, win='.W', ground='W.', lod=0)},
        pents=[Pent(1, side='front', depth=1.0, slope=0.3, mat='kawara', color='#5a4540', z=3.15)],
        roof=Roof('gable', 'kawara', slope=0.32, eave=1.0, verge=0.6, axis='long', color='#7a4a3a', hafu_col='#3a2c24', soffit_col='#d8cdb8'),
        lod=1, age=0.35, note='動画で見えるのは長い白い棟(遠景)。名称・階数は推定')]
    if rest is not None and abs(C.poly_area(rest)) > 25:
        sr = site('912422961', rest)
        out.append(BuildingSpec(
            id='912422961#annex', name='庫裏の南の棟(推定)', zone='D', ring=rest, floors=1, floor_h=3.2, found='concrete', found_h=0.3, base_z=zf + 0.3, front=sr['front'],
            replaces=[], same_level=False, walls={'*': WallFinish('plaster', '#ece8df')}, facades={'*': Facade(bay=2.6, win='W.', ground='.W', frame='alu', lod=0)},
            roof=Roof('flat', parapet=0.4), lod=0, age=0.35))
    return out


def nushiyu():
    """ぬ志勇旅館(954629639、D_nushiyu、R 20:36 f_413 / R 26:48 f_537): 3 階、白漆喰に黒い柱・梁(真壁)、各階に黒い手すりのベランダ、石段(北北西)に大きな妻面を向ける
    急な板葺き(とんとん葺き風)の切妻、1 階は黒い板壁と大きなガラス戸、軒下に看板板(黒地に白文字「ぬ志勇旅館」)。"""
    ring = ring_of('954629639')
    s = site('954629639')
    fr = 335
    zf = face_z(ring, fr)
    tim = Timber('#1f1b18', w=0.14, posts='bay', beams=('bottom', 'top', 'head', 'sill'))
    fac = Facade(bay=2.0, margin=0.35, pattern={1: 'G.G', 2: 'W.W', 3: 'W.W'}, frame='black', glass='#3a444b', lattice_col='#1f1b18', sizes={'W': (1.4, 1.3, 0.8), 'G': (1.6, 2.3, 0.0)})
    return BuildingSpec(
        id='954629639', name='ぬ志勇旅館', zone='D', floors=3, floor_h=[3.5, 3.1, 3.1], found='stone', found_h=0.3, found_col='#8d8981', base_z=zf + 0.3, front=fr,
        use_obb=True, replaces=['954629639'],
        walls={1: WallFinish('board_h', '#2c2826', pitch=0.2, timber=tim), '*': WallFinish('plaster', '#f0ede6', timber=tim)},
        facades={'front': fac, '*': dreplace(fac, pattern=None, win='W.', ground='.W', lod=1)},
        balconies=[Balcony(2, ['front', 'left', 'right'], depth=0.7, rail='wood', color='#1f1b18', z=0.0), Balcony(3, ['front'], depth=0.7, rail='wood', color='#1f1b18', z=0.0)],
        roof=Roof('gable', 'tonton', slope=0.75, eave=0.9, verge=0.6, axis='long', color='#7b6a58', hafu_col='#1f1b18', soffit_col='#d8cdb8', gable_style='timber', gable_col='#f0ede6'),
        attach=[Attach('sign', side='front', floor=1, at=0.5, z=3.2, w=2.6, h=0.5, style='yoko', color='#1f1b18', color2='#6b6055', text='ぬ志勇旅館'),
                Attach('sign', side='front', floor=1, s=0.5, z=0.5, w=0.5, h=1.5, d=0.4, style='tate', color='#1f1b18', color2='#6b6055', text='ぬ志勇旅館'),
                Attach('ac', side='back', floor=2, n=2, w=1.2)],
        lod=2, age=0.35, note='同定は位置から(OSM の名前付き点と外形が一致しない。確度 中)')


def parking():
    """湯畑観光駐車場(954982175、D_parking、W 0:21〜0:30 f_008〜011): 立体(3 層)の打放しコンクリート、各層の横長の開口(暗い帯)、屋上の低い胸壁。
    東面(入口)に庇と看板「湯畑観光駐車場」。他の面は動画に出ない(同じ様式)。"""
    ring = ring_of('954982175')
    s = site('954982175')
    fr = 70
    conc = '#a7a49d'
    fac = Facade(bay=4.0, margin=1.0, win='R', ground='R', frame='dark', glass='#2a2a2a', sizes={'R': (None, 1.4, 0.9)}, belt=True)
    return BuildingSpec(
        id='954982175', name='湯畑観光駐車場', zone='D', floors=3, floor_h=[3.2, 3.0, 3.0], found='concrete', found_h=0.3, base_z=base_for(s, 0.3), front=fr,
        replaces=['954982175'],
        walls={'*': WallFinish('mortar', conc, pitch=0.6)},
        facades={'front': fac, '*': dreplace(fac, lod=0)},
        roof=Roof('flat', parapet=1.1, coping_col='#d6d4cc'),
        attach=[Attach('sign', side='front', floor=1, at=0.5, z=2.6, w=5.0, h=0.9, style='yoko', color='#f4f2ec', color2='#1f1b18', text='湯畑観光駐車場'),
                Attach('sign', side='front', floor=1, s=3.0, z=0.0, w=1.2, h=5.0, d=3.0, style='tate', color='#5a3f2c', color2='#2b2420', text='湯畑観光駐車場')],
        lod=1, age=0.35, note='階数・背面は推定。看板塔は縦札で代用')


# ====================================================================== 石灯籠・像・碑(小さな spec)
def _item(iid, kind, x, y, rot=0.0, name='', **kw):
    ring = rect((x, y), rot, 0.7, 0.7)
    sp = BuildingSpec(id=iid, name=name, zone='D', ring=ring, floors=1, floor_h=1.0, found='none', base_z=_gz(x, y), replaces=[], same_level=False,
                      walls={'*': WallFinish('paint', '#8c9088')}, facades={'*': Facade(pattern={1: '.'}, lod=0)}, roof=Roof('none'), lod=1, age=0.0)
    sp.zD, sp.zD_kind = 'item', kind
    for k, v in kw.items():
        setattr(sp, k, v)
    sp.zA_style, sp.zA_why = 'item', kw.get('zD_why', 'カード')
    return sp


def items():
    out = []
    pts = [(-105, -111), (-103, -116), (-87, -104), (-86, -104), (-84, -108), (-83, -107)]       # OSM の lamp 6 点
    for i, (x, y) in enumerate(pts):
        out.append(_item('D_lamp_osm_%d' % i, 'lantern', x, y, 10.0 * i, '石灯籠', zD_why='OSM の lamp 点'))
    for i, (x, y) in enumerate([(-111.8, -104.0), (-108.2, -104.0), (-111.8, -107.5), (-108.2, -107.5), (-111.8, -111.0), (-108.2, -111.0)]):   # 釈迦堂の参道の両側
        out.append(_item('D_lamp_shaka_%d' % i, 'lantern', x, y, 0.0, '石灯籠(釈迦堂の参道)', zD_why='D_shakado: 参道の両側に 3〜4 基'))
    out.append(_item('D_statue_kobo', 'statue', -115.0, -121.0, 68.0, '弘法大師尊像', zD_why='D_hibi_toro(R 22:36 f_455)'))
    out.append(_item('D_stele_1300', 'stele', -118.0, -110.0, 68.0, '壹千參百年記念之碑', zD_size=(0.5, 0.3, 2.2), zD_col='#26282a', zD_round=True, zD_plaque='#d8d6d0',
                     zD_why='D_hibi_toro(R 23:18 f_467)'))
    out.append(_item('D_stele_kousenji', 'stele', -52.0, -73.0, 330.0, '石碑「草津山 光泉寺」', zD_size=(0.65, 0.5, 3.0), zD_col='#8d8f8b', zD_round=False, zD_plaque='#6f726f',
                     zD_why='D_hibi_toro(R 20:24 f_409)'))
    return out


# ====================================================================== 推定(動画で確認できない棟)
HAND_IDS = {'1311927446', '955188993', '912422963', '1312003250', '1311927452', '1311927451', '1311927453', '955188994', '1312003251', '912422961', '954629639',
            '954982175'}


def generics():
    F = get_field()
    out = []
    for b in F.blds:
        if b['zone'] != 'D' or b['id'] in HAND_IDS:
            continue
        sp = ZC._generic(b['id'])
        sp.zone = 'D'
        out.append(sp)
    return out


def specs():
    """区域D の全 spec(手作り+石灯籠・像・碑+推定)。kd_parts.zone_specs('D') と kd_buildings.build_buildings が呼ぶ。"""
    hand = [honden(), sanmon(), shakado(), gojunoto(), fudodo(), shorou(), chozusha(), yukido(), omamori(), *kuri(), nushiyu(), parking()]
    for sp in hand:
        if not hasattr(sp, 'zA_style'):
            sp.zA_style, sp.zA_why = 'hand', 'カード・フレーム'
    return hand + items() + generics()


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
            print('%-20s %-34s %-7s lod%d f%d %-8s tris %6d base %.2f top %.2f (%.2fs)' % (sp.id, sp.name[:34], getattr(sp, 'zA_style', ''), b.info['lod'], sp.floors,
                                                                                         sp.roof.kind, b.info['tris'], b.info['base_z'], b.info['ridge_z'], time.time() - t1))
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
        P.run_zone('D')
