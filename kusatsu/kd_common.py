# -*- coding: utf-8 -*-
"""kd_common.py -- 草津 湯畑ジオラマ共通部品(データ読み込み・座標・メッシュ作成・glTF 書き出し)。
座標: 原点=湯畑重心(OSM relation 12852884, 36.622927N 138.596740E)、+X=東、+Y=北、Blender の Z = 標高 - ZBASE(1153 m)。
Blender 5.2 のヘッドレスで import される。bpy が無い環境でも データ部分(load_*, dem, polygon 関数)は使える。
"""
import json
import math
import os

import numpy as np

try:
    import bpy
except ImportError:  # データ部分だけ使うとき
    bpy = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAT0, LON0 = 36.622927, 138.596740
KX = 111320.0 * math.cos(math.radians(LAT0))
KY = 110540.0
ZBASE = 1153.0          # Blender Z = 標高 - ZBASE
R_MESH = 200.0          # ジオラマの半径 m
OUT_BLEND = os.path.join(ROOT, 'output', 'kusatsu')
OUT_WEB = os.path.join(ROOT, 'kusatsu-diorama', 'models')


def xy(p):
    return ((p['lon'] - LON0) * KX, (p['lat'] - LAT0) * KY)


def load_osm():
    return json.load(open(os.path.join(ROOT, 'plateau_data', 'kusatsu_osm.json'), encoding='utf-8'))


def zone_of(x, y):
    """フェーズ1と同じ区域分け(inventory 第8節)。"""
    if x >= -25 and y <= 25:
        return 'A'
    if x < -25 and y < -80:
        return 'D'
    if x < -25 and y > 15:
        return 'C'
    if x >= -25 and y > 70:
        return 'C'
    return 'B'


# ---------------------------------------------------------------- DEM
class Dem:
    def __init__(self):
        d = json.load(open(os.path.join(ROOT, 'plateau_data', 'kusatsu_dem.json'), encoding='utf-8'))
        self.z = np.array(d['z_rows_south_to_north'], dtype=np.float64)   # [iy][ix]
        self.step = float(d['step'])
        self.x0 = float(d['x0'])
        self.y0 = float(d['y0'])
        self.ny, self.nx = self.z.shape

    @staticmethod
    def _cr(t):
        """Catmull-Rom の4重み。t: (...)"""
        t2, t3 = t * t, t * t * t
        return (-0.5 * t3 + t2 - 0.5 * t, 1.5 * t3 - 2.5 * t2 + 1.0, -1.5 * t3 + 2.0 * t2 + 0.5 * t, 0.5 * t3 - 0.5 * t2)

    def sample(self, X, Y):
        """双3次(Catmull-Rom)で標高(m, 海抜)を返す。"""
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)
        fx = (X - self.x0) / self.step
        fy = (Y - self.y0) / self.step
        ix = np.clip(np.floor(fx).astype(int), 1, self.nx - 3)
        iy = np.clip(np.floor(fy).astype(int), 1, self.ny - 3)
        tx = np.clip(fx - ix, 0, 1)
        ty = np.clip(fy - iy, 0, 1)
        wx = self._cr(tx)
        wy = self._cr(ty)
        out = np.zeros(np.broadcast(X, Y).shape)
        for j in range(4):
            row = np.zeros_like(out)
            for i in range(4):
                row = row + wx[i] * self.z[iy + j - 1, ix + i - 1]
            out = out + wy[j] * row
        return out


# ---------------------------------------------------------------- 幾何
def poly_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def ccw(pts):
    return pts if poly_area(pts) > 0 else pts[::-1]


def clean_ring(pts):
    pts = list(pts)
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6:
        pts = pts[:-1]
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > 1e-4 or abs(p[1] - out[-1][1]) > 1e-4:
            out.append(p)
    return out


def points_in_poly(px, py, poly):
    """ray casting。px,py: numpy 配列。"""
    inside = np.zeros(px.shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if y0 == y1:
            continue
        cond = ((y0 > py) != (y1 > py))
        xint = (x1 - x0) * (py - y0) / (y1 - y0) + x0
        inside ^= cond & (px < xint)
    return inside


def resample(pts, step):
    """折れ線を step m ごとに再サンプル。(N,2) を返す。"""
    pts = np.asarray(pts, dtype=np.float64)
    seg = np.hypot(*(pts[1:] - pts[:-1]).T)
    total = float(seg.sum())
    if total < 1e-6:
        return pts[:1], np.zeros(1)
    n = max(2, int(math.ceil(total / step)) + 1)
    s = np.linspace(0, total, n)
    cum = np.concatenate([[0], np.cumsum(seg)])
    x = np.interp(s, cum, pts[:, 0])
    y = np.interp(s, cum, pts[:, 1])
    return np.stack([x, y], axis=1), s


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------- OSM 抽出
def osm_ways(osm, pred):
    out = []
    for e in osm['elements']:
        if e['type'] == 'way' and e.get('geometry') and pred(e.get('tags', {})):
            out.append((e['id'], e.get('tags', {}), [xy(p) for p in e['geometry']]))
    return out


def osm_buildings(osm):
    """OSM 建物の外形。way と relation の outer を (id, tags, ring) で返す。範囲(重心が半径205m以内)だけ。"""
    res = []
    for e in osm['elements']:
        t = e.get('tags', {})
        if 'building' not in t:
            continue
        rings = []
        if e['type'] == 'way' and e.get('geometry'):
            rings.append(('%d' % e['id'], [xy(p) for p in e['geometry']]))
        elif e['type'] == 'relation':
            k = 0
            for m in e.get('members', []):
                if m.get('role') == 'outer' and m.get('geometry'):
                    rings.append(('r%d_%d' % (e['id'], k), [xy(p) for p in m['geometry']]))
                    k += 1
        for bid, ring in rings:
            ring = clean_ring(ring)
            if len(ring) < 3:
                continue
            ring = ccw(ring)
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
            if math.hypot(cx, cy) > 204:
                continue
            res.append(dict(id=bid, tags=t, ring=ring, c=(cx, cy), area=poly_area(ring), zone=zone_of(cx, cy)))
    return res


# ---------------------------------------------------------------- Blender 側
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name, rough=0.9, metallic=0.0, base=(1, 1, 1, 1), vcol=True, emit=None):
    """頂点カラー(属性名 Col)を基本色にする Principled マテリアル。"""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    if nt is None:
        m.diffuse_color = base
        return m
    nodes, links = nt.nodes, nt.links
    pb = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if pb is None:
        pb = nodes.new('ShaderNodeBsdfPrincipled')
        out = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None) or nodes.new('ShaderNodeOutputMaterial')
        links.new(pb.outputs['BSDF'], out.inputs['Surface'])
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Metallic'].default_value = metallic
    pb.inputs['Base Color'].default_value = base
    if vcol:
        cn = nodes.new('ShaderNodeVertexColor')
        cn.layer_name = 'Col'
        links.new(cn.outputs['Color'], pb.inputs['Base Color'])
    if emit is not None:
        pb.inputs['Emission Color'].default_value = emit
        pb.inputs['Emission Strength'].default_value = 0.15
    m.diffuse_color = base
    return m


def make_object(name, verts, faces, colors=None, color_mode='face', material=None, smooth=False, collection=None):
    """verts: (N,3)、faces: 頂点番号リストのリスト。colors: 'face' なら面数x(3|4)、'vert' なら頂点数x(3|4)。"""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(np.asarray(verts, dtype=np.float64).tolist(), [], [list(map(int, f)) for f in faces])
    mesh.update()
    if colors is not None:
        colors = np.asarray(colors, dtype=np.float32)
        if colors.shape[1] == 3:
            colors = np.concatenate([colors, np.ones((len(colors), 1), np.float32)], axis=1)
        ca = mesh.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        lv = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get('vertex_index', lv)
        if color_mode == 'vert':
            lc = colors[lv]
        else:
            tot = np.array([len(f) for f in faces])
            lc = np.repeat(colors, tot, axis=0)
        ca.data.foreach_set('color', lc.astype(np.float32).ravel())
    if smooth:
        try:
            mesh.shade_smooth()
        except Exception:
            for p in mesh.polygons:
                p.use_smooth = True
    else:
        try:
            mesh.shade_flat()
        except Exception:
            pass
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    return obj


def new_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def count_tris(objs):
    n = 0
    for o in objs:
        for p in o.data.polygons:
            n += max(1, len(p.vertices) - 2)
    return n


def export_glb(objs, path, draco=True, pos_bits=14, level=7):
    """objs を選択して GLB 出力(Draco 圧縮、Y-up)。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
              export_cameras=False, export_lights=False, export_extras=False)
    if draco:
        kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=level,
                  export_draco_position_quantization=pos_bits, export_draco_normal_quantization=10,
                  export_draco_texcoord_quantization=12, export_draco_color_quantization=8,
                  export_draco_generic_quantization=12)
    try:
        kw['export_vertex_color'] = 'MATERIAL'
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop('export_vertex_color', None)
        bpy.ops.export_scene.gltf(**kw)
    return os.path.getsize(path)


# ---------------------------------------------------------------- 色・メッシュ収集
def srgb(h):
    """'#rrggbb' または (r,g,b)(0..1, sRGB) -> リニア RGB タプル。glTF の頂点色はリニア。"""
    if isinstance(h, str):
        h = h.lstrip('#')
        c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    else:
        c = list(h)
    f = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]))


def tint(col, k):
    return (min(col[0] * k, 1.0), min(col[1] * k, 1.0), min(col[2] * k, 1.0))


class MB:
    """メッシュ収集(頂点・面・面色)。quad/tri/box を手で組む。"""

    def __init__(self):
        self.v = []
        self.f = []
        self.c = []

    def vert(self, p):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.v) - 1

    def poly(self, pts, col, up=False, inside=None):
        """pts: 3Dの点列(反時計回りで外向き)。up=True なら法線が +Z になるよう、inside=点 なら その点から離れる向きにそろえる。"""
        P = np.array(pts, dtype=np.float64)
        n = np.zeros(3)
        for i in range(1, len(P) - 1):
            n += np.cross(P[i] - P[0], P[i + 1] - P[0])
        flip = False
        if up:
            flip = n[2] < 0
        elif inside is not None:
            c = P.mean(axis=0)
            flip = np.dot(n, c - np.asarray(inside)) < 0
        if flip:
            P = P[::-1]
        idx = [self.vert(p) for p in P]
        self.f.append(idx)
        self.c.append(col)

    def box_sloped(self, a, b, za_top, zb_top, za_bot, zb_bot, off, thick, col, tint_k=1.0):
        """平面上の線分 a→b に沿い、横にずらした(off m、左が正)厚さ thick の傾いた梁/壁。top/bot は区間両端の Z。"""
        a = np.asarray(a, float); b = np.asarray(b, float)
        d = b - a
        L = np.hypot(*d)
        if L < 1e-6:
            return
        u = d / L
        v = np.array([-u[1], u[0]])
        h = thick / 2.0
        c = lambda p, o: p + v * o
        A0, A1 = c(a, off - h), c(a, off + h)
        B0, B1 = c(b, off - h), c(b, off + h)
        P = {
            'a0t': (*A0, za_top), 'a1t': (*A1, za_top), 'b0t': (*B0, zb_top), 'b1t': (*B1, zb_top),
            'a0b': (*A0, za_bot), 'a1b': (*A1, za_bot), 'b0b': (*B0, zb_bot), 'b1b': (*B1, zb_bot),
        }
        cen = ((A0[0] + B1[0]) / 2, (A0[1] + B1[1]) / 2, (za_top + zb_top + za_bot + zb_bot) / 4)
        cc = tint(col, tint_k)
        for q in (('a0t', 'b0t', 'b1t', 'a1t'), ('a0b', 'a1b', 'b1b', 'b0b'), ('a0b', 'b0b', 'b0t', 'a0t'),
                  ('a1b', 'a1t', 'b1t', 'b1b'), ('a0b', 'a0t', 'a1t', 'a1b'), ('b0b', 'b1b', 'b1t', 'b0t')):
            self.poly([P[k] for k in q], cc, inside=cen)

    def to_object(self, name, material, smooth=False, collection=None):
        if not self.f:
            return None
        return make_object(name, np.array(self.v), self.f, np.array(self.c), 'face', material, smooth, collection)


def hash_noise(x, y, seed=0):
    """決定的な 0..1 の疑似乱数(座標から)。"""
    h = np.sin(np.asarray(x) * 12.9898 + np.asarray(y) * 78.233 + seed * 37.719) * 43758.5453
    return h - np.floor(h)


def vnoise(x, y, scale, seed=0):
    """なめらかな値ノイズ(0..1)。"""
    x = np.asarray(x) / scale; y = np.asarray(y) / scale
    x0 = np.floor(x); y0 = np.floor(y)
    tx = x - x0; ty = y - y0
    tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty)
    n00 = hash_noise(x0, y0, seed); n10 = hash_noise(x0 + 1, y0, seed)
    n01 = hash_noise(x0, y0 + 1, seed); n11 = hash_noise(x0 + 1, y0 + 1, seed)
    return (n00 * (1 - tx) + n10 * tx) * (1 - ty) + (n01 * (1 - tx) + n11 * tx) * ty
