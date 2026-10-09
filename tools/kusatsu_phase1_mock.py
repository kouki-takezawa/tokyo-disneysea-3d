#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""フェーズ1の結果モック: OSM建物(半径200m)を区域色+確度で塗り、区域まとめ表の行を重ねた2D地図。
  python tools/kusatsu_phase1_mock.py  -> output/kusatsu/phase1_mock.html
"""
import json, math, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAT0, LON0 = 36.622927, 138.596740
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540


def xy(p):
    return ((p['lon'] - LON0) * KX, (p['lat'] - LAT0) * KY)


d = json.load(open(os.path.join(ROOT, 'plateau_data/kusatsu_osm.json'), encoding='utf-8'))


def zone_of(x, y):
    if x >= -25 and y <= 25: return 'A'
    if x < -25 and y < -80: return 'D'
    if x < -25 and y > 15: return 'C'
    if x >= -25 and y > 70: return 'C'
    return 'B'


blds = []
for e in d['elements']:
    t = e.get('tags', {})
    if e['type'] == 'way' and 'building' in t and e.get('geometry'):
        pts = [xy(p) for p in e['geometry']]
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        if math.hypot(cx, cy) > 205: continue
        blds.append(dict(id=e['id'], pts=pts, c=(cx, cy), name=t.get('name', ''), lv=t.get('building:levels', ''),
                         z=zone_of(cx, cy), conf='', note='', card=''))
roads = []
for e in d['elements']:
    t = e.get('tags', {})
    if e['type'] == 'way' and 'highway' in t and e.get('geometry'):
        roads.append(([xy(p) for p in e['geometry']], t['highway']))
water = [[xy(p) for p in e['geometry']] for e in d['elements']
         if e['type'] == 'way' and e.get('geometry') and e.get('tags', {}).get('natural') == 'water']

rows = []
for z in 'ABCD':
    p = os.path.join(ROOT, f'docs/kusatsu/cards/zone_{z}.md')
    for ln in open(p, encoding='utf-8'):
        if not ln.startswith('|'): continue
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        m = re.search(r'\((-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\)', ln)
        if not m or len(cells) < 3: continue
        conf = next((c for c in cells if re.match(r'^(高|中|低)', c) and len(c) <= 12), '')
        card = re.search(r'\[([A-D]_\w+)\]', ln)
        rows.append(dict(z=z, x=float(m[1]), y=float(m[2]), name=re.sub(r'[\[\]*]|\(.*?\)', '', cells[0])[:30],
                         conf=conf[:1] or '低', text=' / '.join(cells[1:])[:300], card=card[1] if card else ''))


def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c


rank = {'高': 3, '中': 2, '低': 1, '': 0}
for r in rows:
    best = next((b for b in blds if inside((r['x'], r['y']), b['pts'])), None)
    if not best:
        dd = [(math.hypot(b['c'][0] - r['x'], b['c'][1] - r['y']), b) for b in blds]
        dd = [t for t in dd if t[0] < 12]
        best = min(dd, key=lambda t: t[0])[1] if dd else None
    r['placed'] = bool(best)
    if best and rank[r['conf']] >= rank[best['conf']]:
        best.update(conf=r['conf'], note=r['name'] + ': ' + r['text'], card=r['card'])
pins = [r for r in rows if not r['placed']]

rd = lambda pts: [[round(a, 1), round(c, 1)] for a, c in pts]
out = dict(blds=[dict(id=b['id'], p=rd(b['pts']), n=b['name'], lv=b['lv'], z=b['z'], cf=b['conf'], note=b['note'], card=b['card']) for b in blds],
           roads=[[rd(pts), h] for pts, h in roads], water=[rd(w) for w in water],
           pins=[dict(x=r['x'], y=r['y'], n=r['name'], cf=r['conf'], z=r['z'], note=r['text'], card=r['card']) for r in pins])
html = open(os.path.join(ROOT, 'tools/kusatsu_phase1_mock.tpl.html'), encoding='utf-8').read().replace('__DATA__', json.dumps(out, ensure_ascii=False))
os.makedirs(os.path.join(ROOT, 'output/kusatsu'), exist_ok=True)
open(os.path.join(ROOT, 'output/kusatsu/phase1_mock.html'), 'w', encoding='utf-8').write(html)
print('buildings', len(blds), 'with card info', sum(1 for b in blds if b['conf']), 'rows', len(rows), 'unplaced pins', len(pins))
