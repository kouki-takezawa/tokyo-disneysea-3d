# -*- coding: utf-8 -*-
"""kd_parts_test.py -- フェーズ4 の試作: 代表 5 棟を BuildingSpec から作り、仮の箱と差し替えて区域別 glb に書き出す。

実行(他タブの Blender が動いていないことを tasklist で確認して 1 つだけ):
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --python kusatsu/kd_parts_test.py -- [--lod=N] [--out-web=DIR] [--only=A]
Blender 無しで三角形数だけ数える: python kusatsu/kd_parts_test.py --count

試作 5 棟(カードの記述と使ったフレーム):
  A ちちや 605309932(A_chichiya: R 2:48 f_000057、S 6:27 f_000130、S 2:33 f_000052)
  A 大東館 西棟+本館(塊)+1 階の飲食店 r12857070_1 / r12857070_0(A_daitokan: S 5:09 f_000104、R 3:57)
  B 御座之湯 954786837(B_otonoyu: Y 2:24 f_000049、R 20:21 f_000408)
  C 山本館 948490088(C_yamamotokan: R 29:18 f_000587、R 29:33、K 14:36)
  D 光泉寺 本堂 1311927446(D_honden: R 23:03 f_000462、R 22:57 f_000460)
区域スクリプト kd_zone_<A-D>.py ができたら、そちらの specs() が優先される(kd_parts.zone_specs)。
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kd_common as C  # noqa: E402
import kd_parts as P  # noqa: E402
from kd_parts import (BuildingSpec, WallFinish, Timber, Facade, Balcony, Pent, Roof, Attach)  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]

# 光泉寺 本堂: OSM の外形から向拝の張り出し 4 点を外した主屋の矩形(向拝は Attach の porch で作る)
HONDEN_MAIN = [(-118.16, -128.70), (-125.03, -111.58), (-141.51, -118.08), (-134.66, -135.21)]
# 大東館: relation 12857070 の outer 1 を、湯畑側の西棟(段状のバルコニー)と奥の本館に分ける
DAITO_WEST = [(30.85, 34.0), (31.56, 22.22), (43.64, 22.77), (43.17, 30.77), (43.0, 34.2)]
DAITO_MAIN = [(30.85, 34.0), (43.0, 34.2), (43.17, 30.77), (61.29, 31.66), (71.04, 32.15), (57.67, 11.35), (50.33, -0.08), (56.65, -4.08),
              (56.19, -4.81), (64.71, -12.0), (65.63, -10.0), (66.36, -10.55), (83.69, 16.39), (82.66, 29.54), (82.31, 31.87), (82.1, 32.59),
              (80.39, 38.24), (76.26, 43.61), (70.52, 43.48), (70.48, 43.94), (41.71, 42.61)]

DARK = '#2b2420'


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


def yamamotokan():
    """山本館: 3 階+屋根裏、入母屋+千鳥破風、黒柱白壁、各階の庇、2・3 階の窓前の木の手すり、切石の基礎、唐破風の玄関。"""
    tim = Timber(DARK, w=0.13, posts='bay', beams=('bottom', 'top', 'head', 'sill'))
    fac = Facade(bay=1.95, margin=0.25, ground='L', win='W', frame='wood', glass='#59636a', lattice_col=DARK,
                 sizes={'W': (1.7, 1.45, 0.62), 'L': (1.6, 1.15, 0.85)})
    return BuildingSpec(
        id='948490088', name='山本館', zone='C', floors=3, floor_h=[3.4, 3.0, 3.0], found_h=0.95, found='stone', found_col='#8b877e', front=210,
        walls={1: WallFinish('plaster', '#eeebe3', timber=Timber(DARK, w=0.13, posts='bay', beams=('top', 'head')), koshi=(0.85, 'board_v', '#2e2723')),
               '*': WallFinish('plaster', '#eeebe3', timber=tim)},
        facades={'front': fac, '*': dict_replace(fac, frame='alu', glass='#4f5a61', ground='W', lod=1)},
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
        lod=2, age=0.3, note='奥の別棟 954629633 は区域C のフェーズ7で(同じ外観の続き)')


def honden():
    """光泉寺 本堂: 一重の入母屋・明灰の金属板、朱の柱・長押+白壁、正面に板戸と連子窓・花頭窓、縁にステンレスの手すり、向拝(低い庇)と石段 5 段。"""
    tim = Timber('#b23a2c', w=0.24, proud=0.05, posts='bay', beams=('bottom', 'top', 'head'), mat='paint')
    fac = Facade(bay=2.6, margin=0.25, frame='wood', glass='#2b2622', door_col='#6e5038', lattice_col='#8d9293', rev=0.16,
                 sizes={'P': (None, 3.05, 0.0), 'L': (1.7, 1.55, 0.95), 'K': (1.05, 1.6, 0.85)})
    return BuildingSpec(
        id='1311927446', name='光泉寺 本堂', zone='D', ring=HONDEN_MAIN, floors=1, floor_h=5.0, found_h=0.9, found='stone', found_col='#a19d94',
        front=68, replaces=['1311927446'],
        walls={'*': WallFinish('plaster', '#f0ede6', timber=tim)},
        facades={'front': dict_replace(fac, pattern={1: 'KLPPPLK'}), 'left': dict_replace(fac, pattern={1: '.L.K.L.'}),
                 'right': dict_replace(fac, pattern={1: '.L.K.L.'}), '*': dict_replace(fac, pattern={1: '.......'})},
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
        lod=2, age=0.25, note='縁の手すりはステンレス(2 段)。扁額は判読不能なので板だけ')


def otonoyu():
    """御座之湯: 2 階、杉板(橙茶)の外壁、2 階は連続ガラス窓が 1 階より張り出す、入母屋のとんとん葺き、1 階の下屋、切妻の玄関ポーチと暖簾。"""
    fac = Facade(bay=1.8, margin=0.3, ground='L', win='R', frame='wood', glass='#647f8f', lattice_col='#6b4428',
                 sizes={'R': (None, 1.75, 0.65), 'L': (1.4, 1.2, 0.9)})
    return BuildingSpec(
        id='954786837', name='御座之湯', zone='B', floors=2, floor_h=[3.6, 3.5], found_h=0.55, found='stone', found_col='#8a867e', front=58,
        walls={1: WallFinish('board_v', '#b4703e', pitch=0.9, koshi=(0.8, 'board_h', '#6b4a33')), 2: WallFinish('board_h', '#b97543', pitch=0.22)},
        facades={'front': fac, 'back': dict_replace(fac, ground='.L.', win='W.', lod=1), '*': dict_replace(fac, ground='.L..L.')},
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
        lod=2, age=0.25, note='裏(南西)は動画に出ないので推定(窓は同じ規則)')


def daitokan():
    """大東館 西棟(湯畑側、段状のバルコニー)+本館(塊、遠景の品質)。"""
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


def dict_replace(fac, **kw):
    from dataclasses import replace
    return replace(fac, **kw)


def proto_specs():
    return [chichiya(), *daitokan(), otonoyu(), yamamotokan(), honden()]


# ====================================================================== 実行
def count_only():
    import kd_field as F
    field = F.Field(C.load_osm(), log=lambda *a: None)
    tot = 0
    for sp in proto_specs():
        t0 = time.time()
        b = P.build_building(sp, field)
        tot += b.info['tris']
        print('%-22s %-34s tris %6d  %s  (%.2fs)  ridge %.2f' % (sp.id, sp.name, b.info['tris'], b.info['by_mat'], time.time() - t0, b.info['ridge_z']))
    print('total', tot)


def main():
    import bpy
    import kd_field as F
    import kd_buildings as KB
    t0 = time.time()

    def log(*a):
        print('[parts_test %.1fs]' % (time.time() - t0), *a, flush=True)
    out_web = C.OUT_WEB
    lod_cap = None
    only = 'ABCD'
    for a in ARGS:
        if a.startswith('--out-web='):
            out_web = a.split('=', 1)[1]
        if a.startswith('--lod='):
            lod_cap = int(a.split('=', 1)[1])
        if a.startswith('--only='):
            only = a.split('=', 1)[1]
    C.reset_scene()
    field = F.Field(C.load_osm(), log=log)
    mats = P.get_materials()
    bmat = {'bldg': C.make_material('kd_bldg', 0.9)}
    specs = proto_specs()
    stats = dict(zones={}, buildings=[], signs=[])
    for z in only:
        zs = [s for s in specs if s.zone == z]
        coll = C.new_collection('Buildings_%s' % z)
        objs, rep, infos, signs = P.build_details(field, zs, mats, coll, z, lod_cap, log)
        bobjs, bidx = KB.build_boxes(field, bmat, {z: coll}, zones=z, skip=rep, log=log)
        allo = [o for o in [bobjs.get(z)] if o is not None] + objs
        size = P.export_zone(z, allo, out_web)
        stats['zones'][z] = dict(glb_bytes=size, tris=C.count_tris(allo), detail_tris=sum(i['tris'] for i in infos), boxes=len(bidx),
                                 objects={o.name: C.count_tris([o]) for o in allo})
        stats['buildings'].extend(infos)
        stats['signs'].extend(signs)
        P._update_index(out_web, rep)
        log('zone %s: %s' % (z, stats['zones'][z]))
    os.makedirs(C.OUT_BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.OUT_BLEND, 'kusatsu_parts_test.blend'))
    json.dump(stats, open(os.path.join(C.OUT_BLEND, 'parts_test_stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('done')


if __name__ == '__main__':
    if '--count' in ARGS:
        count_only()
    else:
        main()
