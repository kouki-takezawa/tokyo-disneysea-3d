"""Tokyo DisneySea draft (blocking) scene - shared helpers.

Blender 5.2 pitfalls carried over from utsu_core/enoden work:
 - `from ds_core import *` re-import does NOT propagate re-assignment of a
   name inside another module; mutate the shared dict in place instead.
 - Sky Nishita was removed -> use MULTIPLE_SCATTERING.
 - Do not put Volume Scatter on the World in Cycles 5.2 (kills all lighting).
 - Use mathutils.geometry.tessellate_polygon for arbitrary (possibly
   concave) footprints instead of bmesh convex-hull fills.
"""
import json, math, pathlib
try:  # Blender; the data helpers below also work in plain Python (export_mock.py)
    import bpy, bmesh
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
except ImportError:
    bpy = bmesh = Vector = tessellate_polygon = None

ROOT = pathlib.Path(__file__).parent
DATA = json.loads((ROOT / "plateau_data" / "disneysea_osm.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- shared state (mutate in place)
D = {"scene": None, "collections": {}}

# ---------------------------------------------------------------- port (themed land) anchors
# Nearest-anchor classification is enough for a blocking pass; exact
# boundaries are refined later per area.
PORT_ANCHORS = {
    "mediterranean_harbor": (200, 20),
    "american_waterfront":  (150, -280),
    "mysterious_island":    (-60, -20),
    "port_discovery":       (-190, -210),
    "mermaid_lagoon":       (-200, 40),
    "arabian_coast":        (-330, 190),
    "lost_river_delta":     (-400, 60),
    "fantasy_springs":      (-680, 260),
}
PORT_DEFAULT_HEIGHT = {
    "mediterranean_harbor": 14.0,
    "american_waterfront":  16.0,
    "mysterious_island":    12.0,
    "port_discovery":       15.0,
    "mermaid_lagoon":       10.0,
    "arabian_coast":        16.0,
    "lost_river_delta":     13.0,
    "fantasy_springs":      14.0,
}
PORT_COLOR = {  # flat placeholder colors for the draft (no photo textures)
    "mediterranean_harbor": (0.80, 0.62, 0.42),
    "american_waterfront":  (0.75, 0.70, 0.58),
    "mysterious_island":    (0.35, 0.33, 0.32),
    "port_discovery":       (0.55, 0.58, 0.65),
    "mermaid_lagoon":       (0.55, 0.42, 0.62),
    "arabian_coast":        (0.82, 0.55, 0.30),
    "lost_river_delta":     (0.52, 0.45, 0.30),
    "fantasy_springs":      (0.70, 0.55, 0.68),
}

# Overrides keyed by OSM way id -> height (m). Sourced from OSM height tags
# or public approximations; flagged in memory as draft estimates.
HEIGHT_OVERRIDE = {
    217617810: 24.0,   # Hotel MiraCosta (OSM tag says 20m; harbor wings read taller)
    1259623365: 38.2,  # Fantasy Springs Hotel (OSM height tag)
}
NAME_HEIGHT_OVERRIDE = [
    ("ラプンツェル", 32.0),       # Rapunzel's Lantern Festival tower cluster
    ("ファンタジースプリングス・エントリーウェイ", 18.0),
]

# Detail priority list (2026-09-23): items other creators have modelled on
# Sketchfab (tag "tokyodisneysea", mostly user makotofalcon). We do not copy
# their files - this is only a checklist of which real objects to bring
# beyond box massing first, once the draft/blocking pass is approved.
# Matched against OSM name / name:en substrings.
DETAIL_PRIORITY = [
    "ホテルミラコスタ", "アクアスフィア", "ヴェネツィアン・ゴンドラ", "Calle Pippo",  # Mediterranean Harbor
    "S.S.コロンビア", "SS Columbia", "ニューヨーク市水道局", "トイ・ストーリー",         # American Waterfront
    "アラビアンコースト", "シンドバッド",                                       # Arabian Coast
    "インディ", "Indiana Jones", "ミゲル", "ハンガーステージ",                  # Lost River Delta
    "マーメイドラグーン", "トリトン",                                          # Mermaid Lagoon
    "ニモフレンズ", "Nemo",                                                    # Port Discovery
    "ミッキー＆フレンズ・グリーティングトレイル",                              # cross-park (near Mysterious Island)
]
# Reference-only (not in current OSM / current park layout - Tower of Terror /
# Hotel Hightower was demolished for Fantasy Springs): noted in case the user
# later wants the pre-2022 layout reconstructed as an alternate scene.
# Footprints rebuilt by ds_landmarks with a custom silhouette -> not boxed.
LANDMARK_SKIP = ["S.S.コロンビア", "SS Columbia"]
LANDMARK_SKIP_IDS = {217618801}  # unnamed building=yes on the AquaSphere pool circle (ds_aquasphere owns it)
REMOVED_LANDMARKS_NOTE = "Hotel Hightower / Tower of Terror: demolished 2022, not modelled unless requested."


def nearest_port(x, y):
    best, bd = None, 1e18
    for name, (ax, ay) in PORT_ANCHORS.items():
        dd = (x - ax) ** 2 + (y - ay) ** 2
        if dd < bd:
            best, bd = name, dd
    return best


def get_collection(name, parent=None):
    if name in D["collections"]:
        return D["collections"][name]
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    D["collections"][name] = col
    return col


def flat_material(name, color, roughness=0.85, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
    return mat


def _tessellate(pts):
    """Robust fill for a (possibly concave, non-self-intersecting) polygon."""
    tris = tessellate_polygon([[Vector((x, y, 0.0)) for x, y in pts]])
    return tris


def _clean_ring(pts):
    """Drop the closing duplicate and consecutive duplicates (tessellate_polygon
    does not handle zero-length edges)."""
    out = []
    for p in pts:
        p = (p[0], p[1])
        if not out or (abs(out[-1][0] - p[0]) > 1e-3 or abs(out[-1][1] - p[1]) > 1e-3):
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-3 and abs(out[0][1] - out[-1][1]) < 1e-3:
        out.pop()
    return out


def extrude_loops(mesh_name, loops, z0, height, mat, cap_bottom=False):
    """Solid prism from an outer ring plus optional hole rings (loops[0] = outer).
    tessellate_polygon fills nested loops as holes; side walls are built for
    every loop, so holes get inward-facing walls (quay walls around water)."""
    loops = [_clean_ring(l) for l in loops]
    loops = [l for l in loops if len(l) >= 3]
    if not loops:
        return None
    tris = tessellate_polygon([[Vector((x, y, 0.0)) for x, y in l] for l in loops])
    if not tris:
        return None
    bm = bmesh.new()
    bottom, top = [], []
    for l in loops:
        bottom.append([bm.verts.new((x, y, z0)) for x, y in l])
        top.append([bm.verts.new((x, y, z0 + height)) for x, y in l])
    flat_b = [v for ring in bottom for v in ring]
    flat_t = [v for ring in top for v in ring]
    for a, b, c in tris:
        try:
            bm.faces.new((flat_t[a], flat_t[b], flat_t[c]))
        except ValueError:
            pass
        if cap_bottom:
            try:
                bm.faces.new((flat_b[c], flat_b[b], flat_b[a]))
            except ValueError:
                pass
    for rb, rt in zip(bottom, top):
        n = len(rb)
        for i in range(n):
            j = (i + 1) % n
            try:
                bm.faces.new((rb[i], rb[j], rt[j], rt[i]))
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(mesh_name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(mesh_name, me)
    obj.data.materials.append(mat)
    return obj


def extrude_footprint(mesh_name, pts, z0, height, mat, cap_bottom=False):
    """Build a solid prism from a single closed 2D footprint."""
    return extrude_loops(mesh_name, [pts], z0, height, mat, cap_bottom)


# ---------------------------------------------------------------- multipolygons / clipping
WAYS = {w["id"]: w for w in DATA["ways"]}
PARK = _clean_ring(WAYS[203538370]["pts"])  # 東京ディズニーシー boundary (tourism=theme_park)


def point_in_poly(x, y, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def in_park(pts):
    cx, cy = poly_centroid(pts)
    return point_in_poly(cx, cy, PARK)


def ring_inside(ring, poly):
    return all(point_in_poly(x, y, poly) for x, y in ring[:: max(1, len(ring) // 12)])


def assemble_rings(way_ids):
    """Chain relation member ways into closed rings (members may be split)."""
    segs = [list(map(tuple, WAYS[i]["pts"])) for i in way_ids if i in WAYS]
    out = []
    while segs:
        r = segs.pop(0)
        changed = True
        while changed and r[0] != r[-1]:
            changed = False
            for s in segs:
                if s[0] == r[-1]:
                    r += s[1:]
                elif s[-1] == r[-1]:
                    r += s[::-1][1:]
                elif s[-1] == r[0]:
                    r = s + r[1:]
                elif s[0] == r[0]:
                    r = s[::-1] + r[1:]
                else:
                    continue
                segs.remove(s)
                changed = True
                break
        if r[0] == r[-1] and len(r) >= 4:
            out.append(r)
    return out


def multipolygons(tagkey, tagval=None):
    """Yield (relation, outers, inners) for multipolygon relations with the tag."""
    for r in DATA["relations"]:
        t = r["tags"]
        if tagkey not in t or (tagval is not None and t[tagkey] != tagval):
            continue
        outers = assemble_rings([m["way"] for m in r["members"] if m["role"] == "outer"])
        inners = assemble_rings([m["way"] for m in r["members"] if m["role"] == "inner"])
        if outers:
            yield r, outers, inners


def flat_fill(mesh_name, pts, z, mat, thickness=0.06):
    """Thin double-sided-looking slab for water / paths (drawn as a very low prism)."""
    return extrude_footprint(mesh_name, pts, z - thickness, thickness, mat, cap_bottom=True)


def link(obj, col):
    col.objects.link(obj)
    return obj


def ways_with(tagkey, tagval=None, closed_only=True):
    for w in DATA["ways"]:
        t = w["tags"]
        if tagkey not in t:
            continue
        if tagval is not None and t[tagkey] != tagval:
            continue
        if closed_only and not w["closed"]:
            continue
        yield w


def poly_area(pts):
    return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2


def poly_centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def height_for_way(w):
    wid = w["id"]
    if wid in HEIGHT_OVERRIDE:
        return HEIGHT_OVERRIDE[wid]
    name = w["tags"].get("name", "")
    for key, h in NAME_HEIGHT_OVERRIDE:
        if key in name:
            return h
    tag_h = w["tags"].get("height")
    if tag_h:
        try:
            return float(str(tag_h).replace("m", "").strip())
        except ValueError:
            pass
    levels = w["tags"].get("building:levels")
    if levels:
        try:
            return max(4.0, float(levels) * 3.6)
        except ValueError:
            pass
    cx, cy = poly_centroid(w["pts"])
    return PORT_DEFAULT_HEIGHT[nearest_port(cx, cy)]
