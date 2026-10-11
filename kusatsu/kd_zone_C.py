# -*- coding: utf-8 -*-
"""kd_zone_C.py -- 草津 湯畑ジオラマ フェーズ7: 区域C(西の河原通りの店並び・旅館、湯滝通り、湯畑の北)の建物を BuildingSpec で 1 棟ずつ作る。

区域C = kd_common.zone_of が 'C' を返す範囲(x < -25 かつ y > 15、または x >= -25 かつ y > 70)。OSM 69 外形。
- 手作り(カード+動画フレーム): 山本館(試作のコピー)+奥の別棟、益成屋(玄関棟・客室棟・西の棟)、奈良屋、群龍館、松むら饅頭・山形屋・富貴堂、
  湯畑泉水(華紋)、関乃湯、するがや、極楽館、ドラゴン、湯滝通りの黄色い漆喰の 2 階建て、ホテル一井 別館(9 階)。
- 推定(動画で確認できない棟): OSM の外形+階数(タグ>面積・通りの様式)+様式(_generic)。看板は枠だけ・文字なし。
- 看板の文字・街灯・電柱・ボラードはフェーズ9。

実行(他タブの Blender が動いていないことを tasklist で確認して 1 つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_zone_C.py      # buildings_C.glb だけ
  python kusatsu/kd_zone_C.py --count     # Blender 無しで三角形数(1 棟ごと)
  python kusatsu/kd_zone_C.py --list      # 1 棟ごとの階数・屋根・様式・根拠(phase7_notes 用)
地形(敷地の均し)を変えたときは kd_terrain.py -- --zones=C で terrain.glb と buildings_C.glb を作り直す。
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
import kd_zone_A as ZA  # noqa: E402
import kd_zone_B as ZB  # noqa: E402  (face_z・rect と、att_zB_slats(板塀)を使う)
from kd_parts import (BuildingSpec, WallFinish, Timber, Facade, Balcony, Pent, Roof, Attach, lin, tint)  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]

DARK = '#2b2420'
site, base_for, cut, ring_of, bld, uvec, bearing = ZA.site, ZA.base_for, ZA.cut, ZA.ring_of, ZA.bld, ZA.uvec, ZA.bearing
face_z, rect = ZB.face_z, ZB.rect
METAL_COLS = ZA.METAL_COLS


def get_field():
    return ZA.get_field()


def set_field(field):
    ZA.set_field(field)


def _unit(deg):
    v = uvec(deg)
    return np.array([float(v[0]), float(v[1])])


def _pieces(ring, p0, deg, back_first=True):
    """ring を p0 を通り方位 deg に垂直な線で 2 つに切る -> (deg 側, 反対側)。"""
    d = _unit(deg)
    return cut(ring, p0, d, 1), cut(ring, p0, d, -1)


# ====================================================================== 手作り(カードあり)
def yamamotokan():
    """山本館(948490088、C_yamamotokan、R 29:18 f_587 / R 29:33 f_592 / K 14:36 f_293): kd_parts_test.yamamotokan() のコピー。
    1 階の床を正面の通りの高さ+石積みの基礎 0.95 m に合わせた(試作は敷地の平均)。"""
    ring = ring_of('948490088')
    tim = Timber(DARK, w=0.13, posts='bay', beams=('bottom', 'top', 'head', 'sill'))
    fac = Facade(bay=1.95, margin=0.25, ground='L', win='W', frame='wood', glass='#59636a', lattice_col=DARK,
                 sizes={'W': (1.7, 1.45, 0.62), 'L': (1.6, 1.15, 0.85)})
    return BuildingSpec(
        id='948490088', name='山本館', zone='C', floors=3, floor_h=[3.4, 3.0, 3.0], found_h=0.95, found='stone', found_col='#8b877e', front=210,
        base_z=face_z(ring, 210) + 0.95,
        walls={1: WallFinish('plaster', '#eeebe3', timber=Timber(DARK, w=0.13, posts='bay', beams=('top', 'head')), koshi=(0.85, 'board_v', '#2e2723')),
               '*': WallFinish('plaster', '#eeebe3', timber=tim)},
        facades={'front': fac, '*': dreplace(fac, frame='alu', glass='#4f5a61', ground='W', lod=1)},
        balconies=[Balcony(2, 'front', depth=0.42, z=0.32, rail='wood', color=DARK), Balcony(3, 'front', depth=0.42, z=0.32, rail='wood', color=DARK)],
        pents=[Pent(1, side=['front', 'left', 'right'], depth=1.0, slope=0.33), Pent(2, side=['front', 'left', 'right'], depth=0.75, slope=0.33)],
        roof=Roof('irimoya', 'kawara', slope=0.5, eave=1.0, verge=0.5, irimoya_k=0.5, color='#3e4146', hafu_col=DARK, kengyo=True,
                  chidori=[(-0.45, 3.4, 1), (0.5, 3.4, 1)], gable_style='timber', soffit_col='#d8cdb8'),
        attach=[
            Attach('porch', side='front', at=0.32, w=3.6, d=2.2, h=3.2, color2='#7b3a26', prm=dict(roof='kara', mat='kawara', platform=True)),
            Attach('sign', side='front', floor=2, s=-0.75, z=1.4, w=0.75, h=2.9, style='flat', color=DARK, color2='#3a2e26', text='山本館 本店'),
            Attach('ac', side='back', floor=1, n=3, w=1.2),
            Attach('pipe', side='back', s=1.0),
        ],
        lod=2, age=0.3, note='試作のコピー。1 階の床を通りの高さ+0.95 m に')


YAMA_AXIS, YAMA_BACK = 121.0, 31.0       # 山本館と別棟の長辺の方位、奥(北北東)の方位


def yamamotokan_annex():
    """山本館 別棟(954629633、C_yamamotokan、R 29:18 の奥): 本館の奥に続く同じ外観の棟。外形は本館の背面に接する長い棟(奥行 8.6 m)と、
    北北東へ伸びる腕に分けた。階数 3(推定)、屋根は本館から続く入母屋。"""
    ring = ring_of('954629633')
    p0 = np.array((-47.6, 44.0)) + _unit(YAMA_BACK) * 8.6
    wing, bar = _pieces(ring, p0, YAMA_BACK)
    tim = Timber(DARK, w=0.13, posts='bay', beams=('bottom', 'top', 'head', 'sill'))
    wall = WallFinish('plaster', '#eeebe3', timber=tim)
    fac = Facade(bay=2.2, margin=0.3, ground='W', win='W', frame='wood', glass='#59636a', lattice_col=DARK, sizes={'W': (1.6, 1.4, 0.65)}, lod=0)
    zf = face_z(bar, 211)
    out = []
    sb = BuildingSpec(
        id='954629633', name='山本館 別棟(推定)', zone='C', ring=bar, use_obb=True, floors=3, floor_h=[3.3, 3.0, 3.0], found='stone', found_h=0.5,
        found_col='#8b877e', base_z=zf + 0.5, front=211,
        walls={'*': wall}, facades={'front': fac, 'back': dreplace(fac, lod=1), '*': fac},
        balconies=[Balcony(2, 'back', depth=0.42, z=0.32, rail='wood', color=DARK), Balcony(3, 'back', depth=0.42, z=0.32, rail='wood', color=DARK)],
        pents=[Pent(1, side=['back', 'left', 'right'], depth=0.9, slope=0.33)],
        roof=Roof('irimoya', 'kawara', slope=0.5, eave=0.95, verge=0.5, irimoya_k=0.5, color='#3e4146', hafu_col=DARK, axis=YAMA_AXIS,
                  gable_style='timber', soffit_col='#d8cdb8', chidori=[(0.0, 3.2, -1)]),
        attach=[Attach('ac', side='back', floor=1, n=2, w=1.2), Attach('pipe', side='left', s=1.0)],
        lod=1, age=0.35, replaces=['954629633'], note='奥の別棟は動画では屋根と奥の面が少し見えるだけ(R 29:18)。階数は推定')
    out.append(sb)
    if wing is not None and abs(C.poly_area(wing)) > 20:
        sw = site('954629633', wing)
        zw = max(sw['z_front'], zf - 1.5)
        flat = sw['ratio'] < 0.84
        out.append(BuildingSpec(
            id='954629633#wing', name='山本館 別棟の腕(推定)', zone='C', ring=wing, use_obb=not flat, floors=3, floor_h=[3.3, 3.0, 3.0], found='stone', found_h=0.5,
            found_col='#8b877e', base_z=zw + 0.5, front=sw['front'], same_level=False, replaces=[],
            walls={'*': wall}, facades={'*': fac},
            roof=(Roof('flat', parapet=0.5) if flat else Roof('irimoya', 'kawara', slope=0.5, eave=0.9, verge=0.5, irimoya_k=0.5, color='#3e4146', hafu_col=DARK,
                                                              gable_style='timber', soffit_col='#d8cdb8')),
            attach=[Attach('ac', side='back', floor=1, n=2, w=1.2)], lod=0, age=0.35))
    return out


def masunariya():
    """益成屋(954965052、C_masunariya、R 29:51 f_599 / R 29:57 f_600 / K 13:30): 外形を 3 つに分けた。
    玄関棟(交差点に面す北北東、2 階+入母屋の瓦の玄関屋根、提灯・板塀・看板)、客室棟(白い壁+薄茶のタイルの帯、3 階、室外機)、西の棟(推定)。"""
    ring = ring_of('954965052')
    east = cut(ring, (-93.0, 0.0), np.array((1.0, 0.0)), 1)
    west = cut(ring, (-93.0, 0.0), np.array((1.0, 0.0)), -1)
    d = np.array((0.87, 0.5))
    d = d / np.linalg.norm(d)
    entr = cut(east, (-70.0, 31.0), d, 1)
    body = cut(east, (-70.0, 31.0), d, -1)
    out = []
    # 玄関棟
    se = site('954965052', entr)
    zf = face_z(entr, 30)
    tim = Timber('#3a2a22', w=0.12, posts='bay', beams=('bottom', 'top', 'head'))
    fac = Facade(bay=2.0, margin=0.4, pattern={1: 'G.W.W', 2: 'W.W.W'}, frame='wood', glass='#4a555b', lattice_col=DARK, sizes={'W': (1.5, 1.3, 0.8)})
    pc = np.array(P.obb(entr)[0])
    out.append(BuildingSpec(
        id='954965052', name='益成屋 玄関棟', zone='C', ring=entr, use_obb=True, floors=2, floor_h=[3.8, 3.0], found='stone', found_h=0.35, found_col='#8f8a80',
        base_z=zf + 0.35, front=30,
        walls={'*': WallFinish('plaster', '#efece4', timber=tim, koshi=(0.9, 'board_v', '#3a2e26'))},
        facades={'front': fac, '*': dreplace(fac, lod=1, pattern=None, ground='W', win='W.')},
        pents=[Pent(1, side=['front', 'left', 'right'], depth=1.4, slope=0.35, mat='kawara', color='#3e4146', z=3.5)],
        roof=Roof('irimoya', 'kawara', slope=0.5, eave=1.0, verge=0.5, irimoya_k=0.5, color='#3e4146', hafu_col=DARK, kengyo=True, gable_style='plaster'),
        attach=[Attach('lanterns', side='front', floor=1, z=3.0, d=1.3, n=4, w=6.0, color='#f3efe6'),
                Attach('sign', side='front', floor=2, at=0.5, z=1.3, w=2.4, h=0.9, style='flat', color='#f4f2ec', color2='#2b2420', text='益成屋'),
                Attach('sign', side='front', floor=1, s=1.2, z=1.0, w=0.8, h=1.6, d=0.1, style='flat', color='#a98a62', color2='#3a2e26'),
                Attach('noren', side='front', floor=1, at=0.5, z=2.4, w=2.2, h=1.0, color='#27304a')],
        lod=2, age=0.3, note='玄関の入母屋と提灯。看板は R 29:57(益成屋/押花草の宿/白旗源泉の湯 桧風呂)'))
    # 客室棟
    sbo = site('954965052', body)
    zb = face_z(body, 30)
    flat = sbo['ratio'] < 0.84
    brown = '#b98a62'
    fac_b = Facade(bay=2.4, margin=0.5, win='W', ground='W', frame='dark', glass='#454f55', belt=True, sizes={'W': (1.4, 1.35, 0.9)})
    out.append(BuildingSpec(
        id='954965052#body', name='益成屋 客室棟', zone='C', ring=body, use_obb=not flat, floors=3, floor_h=[3.3, 3.0, 3.0], found='stone', found_h=0.3,
        found_col='#8f8a80', base_z=zb + 0.3, front=30, replaces=[], same_level=False,
        walls={'*': WallFinish('spray', '#f0ede6', koshi=(1.1, 'tile', brown))},
        facades={'front': fac_b, '*': dreplace(fac_b, lod=0)},
        balconies=[Balcony(2, 'front', depth=0.5, z=0.0, rail='steel', color='#4a4036', s0=1.0, s1=-1.0)],
        roof=(Roof('flat', parapet=0.6, penthouse=[(0.0, 0.0, 4.0, 3.0, 2.4)]) if flat else
              Roof('hip', 'metal', slope=0.3, eave=0.8, color='#4b4d50', hafu_col='#4a4036', soffit_col='#e8e4da')),
        attach=[Attach('ac', side='front', floor=3, z=0.9, n=2, w=1.2, d=0.2), Attach('ac', side='back', floor=2, n=3, w=1.2)],
        lod=1, age=0.3, note='客室棟の階数は 3(カードは 3〜4)。外壁は白+薄茶のタイルの帯'))
    # 西の棟(推定)
    if west is not None and abs(C.poly_area(west)) > 30:
        sw = site('954965052', west)
        zw = face_z(west, sw['front'])
        out.append(BuildingSpec(
            id='954965052#west', name='益成屋 西の棟(推定)', zone='C', ring=west, floors=3, floor_h=[3.3, 3.0, 3.0], found='stone', found_h=0.3, found_col='#8f8a80',
            base_z=zw + 0.3, front=sw['front'], replaces=[], same_level=False,
            walls={'*': WallFinish('spray', '#eeebe3', koshi=(1.1, 'tile', brown))},
            facades={'*': Facade(bay=2.6, win='W', ground='W', frame='dark', glass='#454f55', lod=0)},
            roof=Roof('flat', parapet=0.5), attach=[Attach('ac', side='back', floor=2, n=2, w=1.2)], lod=0, age=0.3))
    return out


def naraya():
    """奈良屋(954629636、C_naraya、Y 3:06 f_063 / R 30:03 f_602): 3 階、白壁、2・3 階の焦げ茶の窓枠と木の手すりのバルコニー、玄関は寄棟の下屋と紺の暖簾、
    提灯、前庭は石畳。上階の屋根は見えない(仮に切妻の鉄板)。"""
    ring = ring_of('954629636')
    s = site('954629636')
    fr = 190
    zf = face_z(ring, fr)
    tim = Timber('#3a2a20', w=0.12, posts='bay', beams=('bottom', 'top', 'head'))
    fac = Facade(bay=2.1, margin=0.35, ground='G.W', win='W', frame='wood', glass='#4b565c', lattice_col=DARK, sizes={'W': (1.5, 1.35, 0.75), 'G': (1.8, 2.2, 0.0)})
    return BuildingSpec(
        id='954629636', name='奈良屋', zone='C', floors=3, floor_h=[3.6, 3.0, 3.0], found='stone', found_h=0.3, found_col='#8f8a80', base_z=zf + 0.3, front=fr,
        use_obb=s['ratio'] >= 0.8,
        walls={'*': WallFinish('plaster', '#f0ede6', timber=tim)},
        facades={'front': fac, '*': dreplace(fac, lod=1, ground='W')},
        balconies=[Balcony(2, ['front', 'left', 'right'], depth=0.9, z=0.0, rail='wood', color='#3a2a20'),
                   Balcony(3, ['front', 'left', 'right'], depth=0.9, z=0.0, rail='wood', color='#3a2a20')],
        pents=[Pent(1, side=['front', 'left', 'right'], depth=1.6, slope=0.35, mat='kawara', color='#4a4a4c', z=3.4)],
        roof=Roof('gable', 'metal', slope=0.4, eave=0.9, verge=0.6, axis='long', color='#55585a', hafu_col=DARK, soffit_col='#d8cdb8'),
        attach=[Attach('sign', side='front', floor=1, at=0.5, z=3.0, w=2.4, h=0.55, style='yoko', color='#6a4630', color2='#2b2420', text='奈良屋'),
                Attach('noren', side='front', floor=1, at=0.5, z=2.3, w=2.4, h=1.1, color='#27304a'),
                Attach('lanterns', side='front', floor=1, z=3.0, d=1.1, n=2, w=3.6, color='#f3efe6'),
                Attach('steps', side='front', at=0.5, w=3.0, d=1.0, prm=dict(tread=0.18)),
                Attach('ac', side='back', floor=2, n=2, w=1.2)],
        lod=2, age=0.3, note='前庭の石畳・築山は小物(フェーズ9)。屋根の形は推定')


def gunryukan():
    """群龍館(948490082、C_gunryukan、R 30:33 f_612): 3 階、白い大壁、1 階の腰は御影の割肌(高さ約 1.2 m)、2 階の足元に濃茶の片持ち庇、
    2 階に焦げ茶の縦ルーバー窓、3 階は白壁に細い縦長窓。看板は白地に黒の縦書き「群龍館」。屋根は不明(緩い切妻の鉄板とした)。"""
    ring = ring_of('948490082')
    s = site('948490082')
    fr = 205
    zf = face_z(ring, fr)
    fac = Facade(bay=2.3, margin=0.4, pattern={1: 'G.W.W', 2: 'LLLL', 3: 'T.T.T.T'}, frame='dark', glass='#454f55', lattice_col='#3b2a20',
                 sizes={'L': (2.6, 1.3, 0.8), 'T': (0.8, 1.5, 0.7), 'W': (1.4, 1.3, 0.8), 'G': (1.8, 2.3, 0.0)})
    return BuildingSpec(
        id='948490082', name='群龍館', zone='C', floors=3, floor_h=[3.4, 3.0, 3.0], found='concrete', found_h=0.2, base_z=zf + 0.2, front=fr, use_obb=s['ratio'] >= 0.75,
        walls={1: WallFinish('spray', '#efece6', koshi=(1.2, 'stone', '#8f9091')), '*': WallFinish('spray', '#efece6')},
        facades={'front': fac, '*': Facade(bay=2.6, win='T.', ground='.W', frame='dark', lod=0)},
        pents=[Pent(1, side='front', depth=1.2, slope=0.05, mat='metal', color='#3a2c24', z=3.3, brackets=False)],
        roof=Roof('gable', 'metal', slope=0.25, eave=0.7, verge=0.4, axis='long', color='#5a5d60', hafu_col='#3a2c24', soffit_col='#e0dcd2'),
        attach=[Attach('sign', side='front', floor=2, s=1.2, z=0.8, w=0.6, h=2.2, d=0.3, style='tate', color='#f4f2ec', color2='#3a2a20', text='群龍館'),
                Attach('ac', side='back', floor=2, n=3, w=1.2)],
        lod=2, age=0.3, note='屋根の形は動画に出ない(推定)')


def matsumura():
    """松むら饅頭(954796002、C_matsumura、R 31:24 f_629): 2 階、1 階は焦げ茶の木枠の大きなガラス戸+濃茶の腰板+紺の暖簾、2 階は白壁に縦ルーバー、
    赤茶の板に金文字の吊り看板、赤い縦幟、白い角行灯。屋根は入母屋風(推定)。"""
    ring = ring_of('954796002')
    s = site('954796002')
    fr = 195
    zf = face_z(ring, fr)
    fac = Facade(bay=1.9, margin=0.4, pattern={1: 'S', 2: 'W.W.W'}, frame='wood', glass='#4a555b', noren='#27304a', lattice_col='#3b2a20', sizes={'W': (1.3, 1.2, 0.8)})
    return BuildingSpec(
        id='954796002', name='松むら饅頭(と推定)', zone='C', floors=2, floor_h=[3.6, 3.0], found='stone', found_h=0.15, found_col='#8f8a80', base_z=zf + 0.15, front=fr,
        use_obb=s['ratio'] >= 0.8,
        walls={1: WallFinish('board_h', '#3a2a22', pitch=0.18), 2: WallFinish('plaster', '#efebe2', timber=Timber('#4a3224', w=0.1, posts='bay', beams=('top', 'bottom')))},
        facades={'front': fac, '*': Facade(bay=2.4, win='W.', ground='.W', frame='dark', lod=0)},
        pents=[Pent(1, side='front', depth=0.9, slope=0.3, mat='kawara', color='#3e4146', z=3.45)],
        roof=Roof('irimoya', 'kawara', slope=0.45, eave=0.9, verge=0.45, irimoya_k=0.5, color='#3e4146', hafu_col=DARK, gable_style='plaster'),
        attach=[Attach('sign', side='front', floor=1, s=2.0, z=3.1, w=2.2, h=0.5, style='hang', d=0.4, color='#7a3a2a', color2='#c8a23a', text='松むら饅頭'),
                Attach('nobori', side='front', floor=1, s=-1.2, w=1.0, n=1, d=0.7, color='#b8322a', color2='#4a3a30'),
                Attach('lanterns', side='front', floor=1, z=3.0, d=0.5, n=2, w=3.0, color='#f3efe6')],
        lod=2, age=0.3, note='屋根の上は見えない(推定)')


def yamagataya():
    """山形屋(954795998、C_matsumura、R 30:57 f_618 / K 16:00 f_321): 2 階、1 階の庇は濃紺の瓦棒葺きの下屋(出 1.5 m)、黒い木枠の細格子の引き戸、
    縦札「山形屋」、前に台。2 階は白壁。"""
    ring = ring_of('954795998')
    fr = 200
    zf = face_z(ring, fr)
    fac = Facade(bay=2.0, margin=0.3, pattern={1: 'LL', 2: 'W.W'}, frame='black', glass='#e6dfc9', lattice_col='#1f1b18', sizes={'L': (2.4, 2.3, 0.0), 'W': (1.3, 1.2, 0.8)})
    return BuildingSpec(
        id='954795998', name='山形屋(と推定)', zone='C', floors=2, floor_h=[3.4, 2.9], found='stone', found_h=0.15, found_col='#8f8a80', base_z=zf + 0.15, front=fr, use_obb=True,
        walls={1: WallFinish('board_v', '#2a2420', pitch=0.4), 2: WallFinish('plaster', '#f0ede6')},
        facades={'front': fac, '*': Facade(bay=2.4, win='W.', ground='.W', frame='dark', lod=0)},
        pents=[Pent(1, side='front', depth=1.5, slope=0.3, mat='metal', color='#27335a', z=3.3)],
        roof=Roof('gable', 'metal', slope=0.35, eave=0.5, verge=0.35, axis='long', color='#27335a', hafu_col=DARK, soffit_col='#d9d3c6'),
        attach=[Attach('sign', side='front', floor=1, s=-0.6, z=1.2, w=0.45, h=1.5, d=0.5, style='tate', color='#f2efe6', color2='#2a2420', text='山形屋')],
        lod=2, age=0.3)


def fukidou():
    """富貴堂(954796000、C_matsumura、R 31:09 f_624): 2 階、白漆喰+黒い柱、白幟「富貴堂 温泉饅頭」。外形は 9.5 x 3 m の細長い棟。"""
    ring = ring_of('954796000')
    fr = 200
    zf = face_z(ring, fr)
    return BuildingSpec(
        id='954796000', name='富貴堂(と推定)', zone='C', floors=2, floor_h=[3.3, 2.9], found='stone', found_h=0.15, found_col='#8f8a80', base_z=zf + 0.15, front=fr, use_obb=True,
        walls={'*': WallFinish('plaster', '#f0ede6', timber=Timber('#1f1b18', w=0.12, posts='bay', beams=('bottom', 'top', 'head')))},
        facades={'front': Facade(bay=2.0, margin=0.3, pattern={1: 'S', 2: 'W.W'}, frame='black', glass='#4a555b', noren='#efe9da'),
                 '*': Facade(bay=2.4, win='W', ground='.', frame='dark', lod=0)},
        pents=[Pent(1, side='front', depth=0.8, slope=0.3, mat='kawara', color='#3e4146', z=3.2)],
        roof=Roof('gable', 'kawara', slope=0.45, eave=0.5, verge=0.3, axis='long', color='#3e4146', hafu_col=DARK),
        attach=[Attach('nobori', side='front', floor=1, s=0.8, w=1.0, n=2, d=0.7, color='#f2efe6', color2='#4a3a30'),
                Attach('lanterns', side='front', floor=1, z=3.0, d=0.4, n=2, w=2.0, color='#f3efe6')],
        lod=1, age=0.3)


def kamon():
    """湯畑泉水(華紋 KAMON、1491049274、C_yubatakesensui、K 16:00 f_321 / K 16:03 f_322): 通りの南側の細長い新築。3 階、全面を濃い茶〜橙茶の縦ルーバーで覆い、
    1 階はガラスの大開口と木枠(店舗)、前に木のデッキと 3 段の階段。陸屋根(見えない)。紺の楕円の札に金の家紋の看板(文字なし)。"""
    ring = ring_of('1491049274')
    fr = 20
    zf = face_z(ring, fr)
    lou = '#9b6038'
    fac = Facade(bay=3.0, margin=0.5, pattern={1: 'G.G.G.G.G', 2: '.W..W..W.', 3: '.W..W..W.'}, frame='dark', glass='#34413f', lattice_col='#6b4328',
                 sizes={'G': (2.4, 3.0, 0.0), 'W': (1.4, 1.4, 0.9)})
    return BuildingSpec(
        id='1491049274', name='湯畑泉水(華紋)', zone='C', floors=3, floor_h=[3.9, 3.2, 3.0], found='concrete', found_h=0.3, base_z=zf + 0.3, front=fr,
        walls={1: WallFinish('louver', lou, pitch=0.1, koshi=(0.5, 'stone', '#8f8a80')), '*': WallFinish('louver', '#8c5632', pitch=0.1)},
        facades={'front': fac, '*': Facade(bay=3.0, win='W.', ground='G.', frame='dark', glass='#34413f', lod=0)},
        pents=[Pent(1, side='front', depth=1.2, slope=0.05, mat='teppan', color='#7a4a2c', z=3.7, brackets=False)],
        roof=Roof('flat', parapet=0.5, coping_col='#6b4328', penthouse=[(0.0, 0.0, 6.0, 4.0, 2.6)]),
        attach=[Attach('steps', side='front', at=0.45, w=5.0, d=1.2, prm=dict(tread=0.15)),
                Attach('sign', side='front', floor=1, s=3.0, z=3.5, w=1.8, h=0.7, style='yoko', color='#1d2c4a', color2='#c8a23a', text='華紋 KAMON'),
                Attach('ac', side='back', floor=2, n=3, w=1.4)],
        lod=2, age=0.15, note='K の完成後の姿。2 階以上の窓の位置・屋根の形は推定')


def sekinoyu():
    """関乃湯(954795995 にあてた、C_yubatakesensui、W 19:27 f_390): 黒い溶岩石の乱積みの腰(約 1.8 m)の上に白い大きな幕、木の標札。
    後ろに瓦屋根の木造の上屋。外形の割り当ては推定(低確度)。"""
    ring = ring_of('954795995')
    s = site('954795995')
    fr = s['front']
    zf = face_z(ring, fr)
    return BuildingSpec(
        id='954795995', name='関乃湯(と推定)', zone='C', floors=1, floor_h=4.2, found='none', base_z=zf + 0.05, front=fr, use_obb=True,
        walls={'*': WallFinish('plaster', '#f1efe8', koshi=(1.8, 'stone_round', '#34322f'))},
        facades={'front': Facade(bay=2.4, pattern={1: '..'}, lod=0), '*': Facade(bay=2.4, win='.', lod=0)},
        roof=Roof('gable', 'kawara', slope=0.45, eave=0.6, verge=0.4, axis='long', color='#4a4c50', hafu_col=DARK),
        attach=[Attach('sign', side='front', floor=1, at=0.5, z=2.3, w=1.6, h=0.5, d=0.12, style='yoko', color='#d6b98a', color2='#3a2a20', text='関乃湯')],
        lod=1, age=0.4, note='外形の割り当ては低確度')


def surugaya():
    """するがや(土産店、954965069、C_surugaya、R 32:12 f_645): 2 階、黒い木の柱と枠にガラスの大きな引き戸、橙の縦長の木札「するがや」。"""
    ring = ring_of('954965069')
    s = site('954965069')
    fr = 15
    zf = face_z(ring, fr)
    return BuildingSpec(
        id='954965069', name='するがや', zone='C', floors=2, floor_h=[3.5, 3.0], found='concrete', found_h=0.12, base_z=zf + 0.12, front=fr, use_obb=s['ratio'] >= 0.85,
        walls={'*': WallFinish('board_v', '#2a2522', pitch=0.35)},
        facades={'front': Facade(bay=2.1, margin=0.3, pattern={1: 'GGGG', 2: 'W.W.W'}, frame='dark', glass='#5a666c', sizes={'G': (None, 2.6, 0.0), 'W': (1.4, 1.2, 0.8)}),
                 '*': Facade(bay=2.4, win='W.', ground='.W', frame='dark', lod=0)},
        pents=[Pent(1, side='front', depth=0.6, slope=0.3, mat='kawara', color='#3e4146', z=3.35)],
        roof=Roof('gable', 'kawara', slope=0.4, eave=0.6, verge=0.4, axis='long', color='#3e4146', hafu_col=DARK),
        attach=[Attach('sign', side='front', floor=1, s=1.0, z=1.6, w=0.5, h=1.7, d=0.45, style='tate', color='#d9852b', color2='#2b2420', text='するがや')],
        lod=2, age=0.3, note='2 階は低確度')


def gokurakukan():
    """極楽館(954965063、C_surugaya、R 32:12 f_645): 3 階。1 階は赤茶のレンガ貼りの腰(約 1.8 m)とレンガの外階段、2 階はハーフティンバー風(白漆喰+焦げ茶の梁・方立)、
    3 階はクリーム色の吹付に細い縦長窓。屋根は緩い勾配の濃茶(見えない)。看板「極楽館」。外形を手前の矩形(通り側)と奥の細い部分に分けた。"""
    ring = ring_of('954965063')
    front_p, back_p = _pieces(ring, (-186.0, 73.0), 0.0)         # y>73 が奥(北)、y<=73 が手前
    out = []
    fr = 195
    tim = Timber('#3a2a20', w=0.16, posts='bay', beams=('bottom', 'top', 'head'), braces=True)
    fac = Facade(bay=2.2, margin=0.3, pattern={1: 'G.W.W', 2: 'W.W.W', 3: 'T.T.T'}, frame='wood', glass='#4a555b',
                 sizes={'W': (1.2, 1.4, 0.8), 'T': (0.8, 1.5, 0.7), 'G': (1.4, 2.2, 0.0)})
    for_ring = back_p if back_p is not None and abs(C.poly_area(back_p)) > 10 else None
    near = front_p if front_p is not None else ring
    zf = face_z(near, fr)
    out.append(BuildingSpec(
        id='954965063', name='極楽館', zone='C', ring=near, use_obb=True, floors=3, floor_h=[3.3, 3.0, 3.0], found='concrete', found_h=0.2, base_z=zf + 0.2, front=fr,
        walls={1: WallFinish('tile', '#9a4e3a', pitch=0.25), 2: WallFinish('plaster', '#efe9dc', timber=tim), 3: WallFinish('spray', '#e9dcb4')},
        facades={'front': fac, '*': dreplace(fac, lod=1, pattern=None, win='W.', ground='.W')},
        balconies=[Balcony(2, 'front', depth=0.5, z=-0.2, rail='wall', color='#efe9dc', s0=1.5, s1=-6.0)],
        roof=Roof('hip', 'metal', slope=0.2, eave=0.7, color='#4a3a32', hafu_col='#3a2a20', soffit_col='#d8cdb8'),
        attach=[Attach('stair', side='front', floor=1, s=-2.0, w=1.2, prm=dict(color='#9a4e3a')),
                Attach('sign', side='front', floor=3, s=-3.0, z=2.7, w=2.0, h=0.5, style='yoko', color='#e9dcb4', color2='#1f1b18', text='極楽館'),
                Attach('ac', side='back', floor=2, n=2, w=1.2)],
        lod=2, age=0.35, note='屋根は見えない(緩い勾配の寄棟とした)'))
    if for_ring is not None:
        sb = site('954965063', for_ring)
        out.append(BuildingSpec(
            id='954965063#back', name='極楽館 奥(推定)', zone='C', ring=for_ring, floors=3, floor_h=[3.3, 3.0, 3.0], found='concrete', found_h=0.2,
            base_z=max(sb['z_front'], zf) + 0.2, front=sb['front'], replaces=[], same_level=False,
            walls={'*': WallFinish('spray', '#e9dcb4')}, facades={'*': Facade(bay=2.6, win='W.', ground='.W', frame='alu', lod=0)},
            roof=Roof('flat', parapet=0.4), lod=0, age=0.35))
    return out


def dragon():
    """ドラゴン(954795991、C_yukitaki_lane、W 19:54 f_399): 湯滝通りの 2 階、黒に近い濃灰の漆喰の壁、1 階にシャッターの入口、2 階に黒い縦ルーバー、
    濃緑の板に金文字の看板、木枠。"""
    ring = ring_of('954795991')
    s = site('954795991')
    fr = s['front']
    zf = face_z(ring, fr)
    flat = s['ratio'] < 0.84
    return BuildingSpec(
        id='954795991', name='ドラゴン', zone='C', floors=2, floor_h=[3.4, 3.0], found='concrete', found_h=0.1, base_z=zf + 0.1, front=fr, use_obb=not flat,
        walls={1: WallFinish('plaster', '#3b3d3f'), 2: WallFinish('louver', '#1f1d1c', pitch=0.12)},
        facades={'front': Facade(bay=2.3, margin=0.3, pattern={1: 'HD.', 2: '.W.'}, frame='black', glass='#2e3538', shutter=0.9, sizes={'W': (0.9, 0.9, 1.0)}),
                 '*': Facade(bay=2.4, win='W.', ground='.', frame='dark', lod=0)},
        roof=(Roof('flat', parapet=0.5) if flat else Roof('gable', 'metal', slope=0.3, eave=0.4, verge=0.3, axis='long', color='#4d4f52', hafu_col='#2b2420')),
        attach=[Attach('sign', side='front', floor=1, at=0.5, z=3.3, w=2.2, h=0.6, style='yoko', color='#274537', color2='#6b4a2a', text='ドラゴン')],
        lod=2, age=0.4)


def ichii_annex():
    """ホテル一井 別館(954965075、B_hotel_ichii の別館、R 20:12 f_405 / R 20:00 f_401 の左奥): 9 階の白い箱形、白の吹付、横長のベランダ帯。
    外形は 34 頂点の大きな多角形(60 x 33 m)。陸屋根+塔屋。"""
    ring = ring_of('954965075')
    s = site('954965075')
    return BuildingSpec(
        id='954965075', name='ホテル一井 別館', zone='C', floors=9, floor_h=[3.6] + [3.1] * 8, found='concrete', found_h=0.3, base_z=base_for(s, 0.3), front=s['front'],
        walls={'*': WallFinish('spray', '#f0efea')},
        facades={'front': Facade(bay=2.6, margin=0.6, win='W', ground='W', frame='alu', glass='#47535b', sizes={'W': (1.7, 1.4, 0.8)}),
                 'back': Facade(bay=2.6, margin=0.6, win='W', ground='W', frame='alu', glass='#47535b', sizes={'W': (1.7, 1.4, 0.8)}, lod=0),
                 '*': Facade(bay=3.0, win='W', ground='W', frame='alu', glass='#47535b', lod=0)},
        balconies=[Balcony(f, ['front', 'back'], depth=1.1, z=0.0, rail='wall', color='#e9e7e0', slab_color='#dedbd2', rail_h=0.95, brackets=False, ends=False)
                   for f in range(2, 10)],
        roof=Roof('flat', parapet=0.8, coping_col='#d6d4cc', penthouse=[(-6.0, 3.0, 7.0, 5.0, 3.0), (12.0, -2.0, 5.0, 4.0, 2.4)]),
        attach=[Attach('ac', side='back', floor=8, n=4, w=2.0, prm=dict(mount='roof'))],
        lod=0, age=0.3, note='9 階はタグ。動画では遠景だけ。基壇や看板は不明')


def yellow_inn():
    """湯滝通りの西寄りの黄色い漆喰+黒い柱梁の 2 階建て(954796003 にあてた、C_yukitaki_lane、W 18:21〜18:45、位置は低確度): 黒い瓦の切妻、庇の瓦、木の格子窓。"""
    ring = ring_of('954796003')
    s = site('954796003')
    fr = s['front']
    zf = face_z(ring, fr)
    return BuildingSpec(
        id='954796003', name='黄色い漆喰の 2 階建て(位置は推定)', zone='C', floors=2, floor_h=[3.2, 2.9], found='concrete', found_h=0.15, base_z=zf + 0.15, front=fr, use_obb=s['ratio'] >= 0.84,
        walls={'*': WallFinish('plaster', '#d8c27a', timber=Timber('#1f1b18', w=0.13, posts='bay', beams=('bottom', 'top', 'head')))},
        facades={'front': Facade(bay=2.0, margin=0.4, pattern={1: 'L.W.L', 2: 'W.W.W'}, frame='black', glass='#4a555b', lattice_col='#2b2420', sizes={'L': (1.2, 1.3, 0.8), 'W': (1.3, 1.2, 0.8)}),
                 '*': Facade(bay=2.4, win='W.', ground='.W', frame='dark', lod=0)},
        pents=[Pent(1, side='front', depth=0.8, slope=0.3, mat='kawara', color='#3a3a3c', z=3.0)],
        roof=Roof('gable', 'kawara', slope=0.5, eave=0.6, verge=0.4, axis='long', color='#34363a', hafu_col=DARK),
        lod=1, age=0.35, note='W 18:21〜18:45 の黄色い漆喰の棟(位置の同定は低確度)')


# ====================================================================== 推定(動画で確認できない棟)
HAND_IDS = {'948490088', '954629633', '954965052', '954629636', '948490082', '954796002', '954795998', '954796000', '1491049274', '954795995', '954965069',
            '954965063', '954795991', '954965075', '954796003'}

PALETTES = {
    # 西の河原通りの入口〜約 100 m の旅館・店(黒柱白壁、R 29:18〜30:33 の遠景): 白漆喰+黒い柱梁が主
    'row_e': [('plaster', '#efebe2', True), ('plaster', '#f0ede6', True), ('spray', '#ebe8e0', False), ('board_h', '#7a5a40', False), ('mortar', '#d9d2c3', False)],
    # 約 100 m 以西と湯滝通りの 2 階建ての店(板張り・格子・暖簾、色も高さも不揃い)
    'row_w': [('board_h', '#7a5a40', False), ('board_v', '#2b2725', False), ('plaster', '#efebe2', True), ('mortar', '#cfc6b5', False), ('board_h', '#a8957a', False),
              ('spray', '#d9d6cf', False), ('paint', '#d6bf8a', False)],
    'ryokan': [('spray', '#eae7df', False), ('tile', '#cdbfa6', False), ('spray', '#e2d9c7', False), ('plaster', '#ece8dd', True)],
    'hotel': [('spray', '#efeeea', False), ('spray', '#e8e4d8', False), ('tile', '#d8cfbd', False)],
    'back': [('spray', '#ece9e1', False), ('spray', '#e3dccb', False), ('spray', '#d9d6cf', False), ('board_h', '#c7c2b8', False),
             ('board_h', '#a8b0b3', False), ('mortar', '#cfc6b5', False), ('tile', '#c8b9a0', False)],
}


def _rs(fid):
    return np.random.RandomState(zlib.crc32(fid.encode('utf-8')) & 0xffffffff)


def style_of(s, tags):
    x, y = s['c']
    if s['area'] < 25:
        return 'tiny'
    if s['z_front'] > 14:                       # 湯畑北の山手(段の上の小さな家)
        return 'back'
    if tags.get('tourism') in ('hotel', 'guest_house') or tags.get('building') in ('hotel', 'apartments') or s['area'] >= 300:
        return 'ryokan'
    if x < -25 and 30 < y < 100 and s['road_d'] < 6:
        return 'row_e' if x >= -100 else 'row_w'
    return 'back'


def floors_of(st, s, tags, rs):
    lv = tags.get('building:levels')
    if lv and str(lv).isdigit() and int(lv) <= 9:
        return int(lv), 'OSM'
    a = s['area']
    if st == 'tiny':
        return 1, '面積'
    if st == 'ryokan':
        return (4 if a > 600 else 3), '旅館・面積'
    if a < 55:
        return (1 if a < 35 else 2), '面積'
    if st == 'row_e':
        return (3 if a > 90 else 2), '入口側の並び(旅館の 3 階)'
    if st == 'row_w':
        return (3 if (a > 150 and rs.rand() < 0.4) else 2), '西の店並び(2 階)'
    return (3 if (a > 160 and rs.rand() < 0.45) else 2), '裏(面積)'


def _generic(fid, ring=None, tags=None, name=None, sid=None, replaces=None):
    """推定の棟: OSM の外形+階数+様式から spec を作る(kd_zone_B._generic と同じ規則、区域C の様式)。看板は枠だけ。"""
    b = bld(fid)
    tags = tags if tags is not None else (b['tags'] if b else {})
    s = site(fid, ring)
    rs = _rs(sid or fid)
    st = style_of(s, tags)
    nf, why = floors_of(st, s, tags, rs)
    shop_street = st in ('row_e', 'row_w')
    a = s['area']
    pal = PALETTES.get(st if st in PALETTES else 'back')
    wk, wc, timb = pal[rs.randint(len(pal))]
    wc = '#%02x%02x%02x' % tuple(int(np.clip(int(wc[i:i + 2], 16) * (0.96 + 0.08 * rs.rand()), 0, 255)) for i in (1, 3, 5))
    tim = Timber(DARK if rs.rand() < 0.7 else '#4a3426', w=0.11, posts='bay', beams=('top', 'head'), braces=rs.rand() < 0.25) if timb else None
    walls = {'*': WallFinish(wk, wc, timber=tim)}
    if shop_street and nf >= 2 and st == 'row_w' and rs.rand() < 0.55:
        walls[1] = WallFinish(*[('board_v', '#2c2826'), ('board_v', '#4a3426'), ('mortar', '#bdb6aa'), ('paint', wc)][rs.randint(4)])
    fh1 = 3.5 if shop_street else 3.0
    fh = [fh1] + [round(2.8 + 0.25 * rs.rand(), 2)] * (nf - 1)
    if st in ('ryokan', 'hotel'):
        fh = [3.3] + [3.0] * (nf - 1)
    if st == 'tiny':
        fh = [2.5 + 0.4 * rs.rand()]
    ratio = s['ratio']
    use_obb = ratio >= 0.9 or (ratio >= 0.8 and a < 160)
    pitched = use_obb or ratio >= 0.84
    tsuma = rs.rand() < (0.45 if shop_street else 0.35)
    rax = s['front'] if tsuma else (s['front'] + 90) % 360
    if st == 'hotel':
        roof = Roof('flat', parapet=0.9 + 0.3 * rs.rand(), penthouse=[(rs.uniform(-3, 3), rs.uniform(-2, 2), 4.0, 3.0, 2.8)] if a > 300 else [])
    elif st == 'ryokan':
        if pitched and nf <= 3 and rs.rand() < 0.6:
            roof = Roof('irimoya' if rs.rand() < 0.5 else 'hip', 'kawara', slope=0.45, eave=0.8, verge=0.4, axis='long', irimoya_k=0.5, hafu_col=DARK, gable_style='plaster')
        else:
            roof = Roof('flat', parapet=0.8 + 0.3 * rs.rand(), penthouse=[(rs.uniform(-2, 2), rs.uniform(-1, 1), 3.0, 2.6, 2.4)] if a > 200 else [])
    elif not pitched:
        roof = Roof('flat', parapet=0.6 + 0.4 * rs.rand())
    elif shop_street:
        mat = 'kawara' if rs.rand() < 0.6 else 'teppan'
        kind = 'gable' if rs.rand() < 0.75 else 'hip'
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
    elif st == 'tiny':
        front_fac = Facade(bay=2.0, pattern={1: ['P', 'G', 'D', '.W'][rs.randint(4)]}, frame='alu', lod=0)
        side_fac = Facade(bay=2.0, win='.', ground='.', lod=0)
    else:
        front_fac = Facade(bay=2.2, ground=['G.W', '.GW', 'W.G', 'GW'][rs.randint(4)], win=['W', 'W.', '.W', 'WW.'][rs.randint(4)],
                           frame='alu' if rs.rand() < 0.5 else 'black', glass='#46535c', lod=None)
        side_fac = Facade(bay=2.6, win='.W', ground='W.', frame='alu', lod=0)
    # ---- 品質(通りから見える棟だけ lod1)
    near = s['road_d'] < 8.0 and s['z_front'] < 14
    lod = 1 if (near and a >= 30 and st not in ('tiny', 'hotel')) else 0
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
        if st == 'row_e' and nf >= 2 and rs.rand() < 0.6:
            balconies.append(Balcony(2, 'front', depth=0.5, z=0.3, rail='wood', color=DARK))
        elif rs.rand() < 0.3:
            balconies.append(Balcony(2, 'front', depth=0.6, z=0.0, rail=['wood', 'steel', 'lattice'][rs.randint(3)], color=DARK))
        if rs.rand() < 0.75:
            attach.append(Attach('sign', side='front', floor=1, z=fh[0] - 0.35, w=round(min(3.4, s['front_len'] * 0.7), 2), h=0.42, style='yoko',
                                 color=['#3a2a20', '#f0ede4', '#2d4a3a', '#efe9da', '#2b2725', '#7a2a24'][rs.randint(6)], color2=DARK))
        if rs.rand() < 0.35:
            attach.append(Attach('sign', side='front', floor=2, s=0.5, z=1.2, w=0.5, h=1.5, style='tate', color='#f2efe6', color2=DARK))
        if rs.rand() < 0.25:
            attach.append(Attach('lanterns', side='front', floor=1, z=fh[0] - 0.5, d=0.6, n=2, w=min(2.4, s['front_len'] * 0.5),
                                 color='#c03a2b' if rs.rand() < 0.6 else '#efe9da'))
    elif st in ('ryokan', 'hotel'):
        if rs.rand() < 0.5 and nf >= 3 and lod >= 1:
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
    if st != 'tiny' and lod >= 1:
        attach.append(Attach('ac', side=['left', 'right', 'back'][rs.randint(3)], n=1 + rs.randint(3), w=1.2))
        if rs.rand() < 0.4:
            attach.append(Attach('pipe', side=['left', 'right', 'back'][rs.randint(3)], s=0.6))
    # ---- 床の高さ(正面の地面=道)と基礎。裏が低い斜面は石積みの基礎を伸ばす
    drop = s['z_front'] - s['z_min']
    found = 'stone' if drop > 1.4 else 'concrete'
    fh_ = 0.12 if shop_street else 0.3
    nm = name or tags.get('name') or ''
    sp = BuildingSpec(
        id=sid or fid, name=nm or '(無名)', zone='C', ring=ring, floors=nf, floor_h=fh, base_z=base_for(s, fh_), front=s['front'],
        found=found, found_h=0.4 if found == 'stone' else 0.3, found_col='#8b877e' if found == 'stone' else None,
        walls=walls, facades=facades, setbacks=setbacks, pents=pents, balconies=balconies, roof=roof, attach=attach,
        use_obb=use_obb, lod=lod, age=round(0.3 + 0.25 * rs.rand(), 2), replaces=replaces,
        note='推定: 様式=%s、階数=%d(%s)、屋根=%s%s、道まで %.1f m' % (st, nf, why, roof.kind, '' if roof.kind == 'flat' else '/' + roof.mat, s['road_d']))
    sp.zA_style = st
    sp.zA_why = why
    return sp


def generics():
    F = get_field()
    out = []
    for b in F.blds:
        if b['zone'] != 'C' or b['id'] in HAND_IDS:
            continue
        out.append(_generic(b['id']))
    return out


def specs():
    """区域C の全 spec(手作り+推定)。kd_parts.zone_specs('C') と kd_buildings.build_buildings が呼ぶ。"""
    hand = [yamamotokan(), *yamamotokan_annex(), *masunariya(), naraya(), gunryukan(), matsumura(), yamagataya(), fukidou(), kamon(), sekinoyu(),
            surugaya(), *gokurakukan(), dragon(), yellow_inn(), ichii_annex()]
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
        P.run_zone('C')
