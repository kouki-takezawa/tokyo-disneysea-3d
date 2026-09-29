"""舞浜駅南口 → ボン・ヴォヤージュ → 東京ディズニーランド・ステーション -- the walk between JR Maihama Station and the Land's
Resort Line station, outside the park (plain Python: shapely + numpy, Blender is not needed; no trees).

  python src/ds_tdl_gateway.py       # -> output/disneysea/models/tdl_gateway.json (glTF, buffer embedded) + a summary
  python src/export_mock.py          # rebuilds the page; D.models picks the file up ("tdl_gateway", layer 舞浜駅・周辺)

What is modelled (OSM, plateau_data/disneyland_osm.json), inside BOX (x -500..-60, y 925..1125, local m):
  ground    the same method as ds_tdl_hotel_ground.py, over what that model and the entrance plaza do not cover: roads (tertiary 8 m,
            service 4.5-6 m: ESTIMATES), footways 3 m, pedestrian areas and the faces of the OSM linework between them (asphalt
            along a road, pink brick beside it, curbed planters for lawns / gardens). Nothing where a building or water is.
  decks     the pedestrian bridges (舞浜駅南口歩道橋, 東京ディズニーランド・ゲートウェイ, the level-1 pedestrian areas and colonnade
            at the station): one deck level Z_DECK = mean ground under them + DECK_H (ESTIMATE: OSM gives layer 1 only), a girder
            under the slab, parapets, columns to the ground (not under the buildings or the Resort Line beam), stairs where an OSM
            `steps` way joins a deck (rise = deck height, step 0.17 m), a flat roof on posts over the covered parts and the
            ゲートウェイキューポラ at the junction (rebuilt from the user's photo: see cupola()).
  Bon Voyage  the shop (OSM way 152465275, 1385 m2), rebuilt from the user's photos (2026-09-29): a giant quilted suitcase with a
            silver frame and handle, and a giant hat box lying across the deck (the walk runs through it). See bon_voyage().
Left out: the JR station building and the viaduct (tracks.json has the line and the platforms), the Resort Gateway Station (x = 0),
  Ikspiari, the interior of the shop, signs, lamps, trees, anything under layer 0 (tunnels).
Meshes are named GW_<ground material> and GB_<building material>; the page colours them (mock_template.html MODEL_MAT).
"""
import sys, math, pathlib

import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, box
from shapely.ops import unary_union, polygonize
import shapely

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
import ds_tdl_hotel_ground as H

OUT = ROOT / "output" / "disneysea" / "models" / "tdl_gateway.json"
BOX = (-500.0, 925.0, -60.0, 1125.0)
BV_WAY = 152465275
DECK_H, GIRDER = 5.4, 0.7                 # the deck's walking surface above the ground; the girder under it (ESTIMATES)
RISER = 0.17
PARAPET_H, PARAPET_W = 1.1, 0.25
ROOF_H, ROOF_T = 3.6, 0.3                 # covered walkway: roof underside above the deck, roof thickness
W_TERTIARY, W_UNCLASSIFIED = 8.0, 6.0
FILL_NEAR = 30.0                          # the open ground beside the route that is paved (m)
W_GATEWAY, W_BRIDGE, W_DECK = 6.0, 5.0, 3.5
STAIR_W = 3.0
GROUND = ("GW_road", "GW_path", "GW_plaza", "GW_curb", "GW_soil", "GW_edge")
BUILD = ("GB_cream", "GB_trim", "GB_stone", "GB_brick", "GB_copper", "GB_gold", "GB_iron", "GB_white", "GB_glass", "GB_win_dark",
         "GB_deck", "GB_concrete", "GB_quilt", "GB_silver", "GB_hat_red", "GB_hat_navy", "GB_hat_blue", "GB_vault",
         "GB_poster1", "GB_poster2", "GB_poster3", "GB_neon", "GB_medal",
         "GB_mint", "GB_sign_cream", "GB_sign_red", "GB_clock", "GB_flag_red", "GB_flag_yellow", "GB_lamp")


# ------------------------------------------------------------------ mesh helpers (flat / smooth normals, plan x y, z up)
def _tri(m, a, b, c):
    a, b, c = np.array(a, float), np.array(b, float), np.array(c, float)
    n = np.cross(b - a, c - a)
    L = np.linalg.norm(n)
    if L < 1e-12:
        return
    n /= L
    m.add([a, b, c], [n, n, n])


def _quad(m, a, b, c, d):
    _tri(m, a, b, c); _tri(m, a, c, d)


def _ccw(ring):
    ring = [tuple(p) for p in ring]
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    s = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))
    return ring if s > 0 else ring[::-1]


def prism(m, ring, z0, z1, top=True, bottom=False):
    """walls (outward) from z0 to z1 on a ring; optionally the top / bottom cap"""
    ring = _ccw(ring)
    n = len(ring)
    for i in range(n):
        (ax, ay), (bx, by) = ring[i], ring[(i + 1) % n]
        if math.hypot(bx - ax, by - ay) < 1e-6:
            continue
        _quad(m, (ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1))
    if top or bottom:
        for c in G.cdt(Polygon(ring)):
            if top:
                _tri(m, (*c[0], z1), (*c[1], z1), (*c[2], z1))
            if bottom:
                _tri(m, (*c[0], z0), (*c[2], z0), (*c[1], z0))


def slab(m, geom, z0, z1):
    """a slab with a top, a bottom and outside walls (holes: walls facing into the hole)"""
    for p in G._polys(geom):
        ext = _ccw(list(p.exterior.coords))
        for i in range(len(ext)):
            (ax, ay), (bx, by) = ext[i], ext[(i + 1) % len(ext)]
            if math.hypot(bx - ax, by - ay) > 1e-6:
                _quad(m, (ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1))
        for h in p.interiors:
            hr = _ccw(list(h.coords))[::-1]          # clockwise: the right side of a->b is into the hole
            for i in range(len(hr)):
                (ax, ay), (bx, by) = hr[i], hr[(i + 1) % len(hr)]
                if math.hypot(bx - ax, by - ay) > 1e-6:
                    _quad(m, (ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1))
        for c in G.cdt(p):
            _tri(m, (*c[0], z1), (*c[1], z1), (*c[2], z1))
            _tri(m, (*c[0], z0), (*c[2], z0), (*c[1], z0))


def rot_ring(cx, cy, ang, sx, sy):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + ca * x - sa * y, cy + sa * x + ca * y) for x, y in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2))]


def obox(m, cx, cy, ang, sx, sy, z0, z1, top=True, bottom=True):
    prism(m, rot_ring(cx, cy, ang, sx, sy), z0, z1, top, bottom)


def loc(cx, cy, ang, u, v):
    """plan point at (u along, v across) of a frame at (cx, cy) turned by ang"""
    ca, sa = math.cos(ang), math.sin(ang)
    return cx + ca * u - sa * v, cy + sa * u + ca * v


def cyl(m, cx, cy, r, z0, z1, n=28, top=True, bottom=False, r1=None):
    """a cylinder (or a cone frustum when r1 is given for the top) with smooth wall normals"""
    r1 = r if r1 is None else r1
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        p = [(cx + r * math.cos(a0), cy + r * math.sin(a0), z0), (cx + r * math.cos(a1), cy + r * math.sin(a1), z0),
             (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z1)]
        k = (r - r1) / max(z1 - z0, 1e-6)
        ns = [np.array([math.cos(a), math.sin(a), k]) for a in (a0, a1, a1, a0)]
        ns = [v / np.linalg.norm(v) for v in ns]
        m.add([p[0], p[1], p[2]], [ns[0], ns[1], ns[2]]); m.add([p[0], p[2], p[3]], [ns[0], ns[2], ns[3]])
    if top and r1 > 1e-6:
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            _tri(m, (cx, cy, z1), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z1), (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1))
    if bottom:
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            _tri(m, (cx, cy, z0), (cx + r * math.cos(a1), cy + r * math.sin(a1), z0), (cx + r * math.cos(a0), cy + r * math.sin(a0), z0))


def dome(m, cx, cy, r, z0, rings=8, n=28, squash=1.0):
    """a hemisphere with smooth normals, base at z0"""
    for j in range(rings):
        t0, t1 = 0.5 * math.pi * j / rings, 0.5 * math.pi * (j + 1) / rings
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            def P(t, a):
                return (cx + r * math.cos(t) * math.cos(a), cy + r * math.cos(t) * math.sin(a), z0 + r * squash * math.sin(t))
            def N(t, a):
                v = np.array([math.cos(t) * math.cos(a), math.cos(t) * math.sin(a), math.sin(t) / squash]); return v / np.linalg.norm(v)
            q = [(P(t0, a0), N(t0, a0)), (P(t0, a1), N(t0, a1)), (P(t1, a1), N(t1, a1)), (P(t1, a0), N(t1, a0))]
            m.add([q[0][0], q[1][0], q[2][0]], [q[0][1], q[1][1], q[2][1]])
            if j < rings - 1:
                m.add([q[0][0], q[2][0], q[3][0]], [q[0][1], q[2][1], q[3][1]])


# ------------------------------------------------------------------ plan (ground, decks, stairs)
def _hw(t):
    hw = t["highway"]
    if hw == "tertiary":
        return W_TERTIARY
    if hw == "unclassified":
        return W_UNCLASSIFIED
    return H._width(t)


def _is_deck(t):
    if t.get("tunnel") in ("yes", "building_passage") or t.get("highway") not in ("footway", "pedestrian"):
        return False
    return (t.get("bridge") in ("yes", "viaduct") or t.get("layer") in ("1", "2") or t.get("level") == "1")


def _deck_w(t):
    n = t.get("name", "")
    return W_GATEWAY if "ゲートウェイ" in n else W_BRIDGE if "歩道橋" in n else W_DECK


def plan():
    fb = box(*BOX)
    W = DL.DATA["ways"]
    bv = Polygon(DL.WAYS[BV_WAY]["pts"]).buffer(0)
    solid = [Polygon(w["pts"]).buffer(0) for w in W if w["closed"] and len(w["pts"]) >= 4 and "building" in w["tags"] and w["tags"]["building"] != "roof"]
    solid += [Polygon(w["pts"]).buffer(0) for w in W if w["closed"] and len(w["pts"]) >= 4 and (w["tags"].get("natural") == "water" or w["tags"].get("water"))]
    solid += [Polygon(o).buffer(0) for r in DL.DATA["relations"] if r["tags"].get("building") == "train_station" for o in DL.outer_rings(r)]
    solid = unary_union([g for g in solid if g.intersects(fb)])
    hp = H.plan()
    covered = unary_union([hp["road"], hp["path"], hp["plaza"], hp["station_path"], hp["station"]] + list(hp["planters"]))
    entrance = G.plan()["closed"]
    blocked = unary_union([solid, entrance, covered])

    roads, paths, peds, lines = [], [], [], []
    for w in W:
        t = w["tags"]; hw = t.get("highway")
        pts = w["pts"]
        if len(pts) < 2 or not LineString(pts).intersects(fb):
            continue
        ground = H._on_ground(t)
        if ground and (hw in ("footway", "service", "pedestrian", "steps", "tertiary", "unclassified", "residential") or "building" in t
                       or "barrier" in t or t.get("leisure") in ("garden", "park") or t.get("landuse") in ("grass", "forest", "flowerbed", "meadow")
                       or t.get("natural") in ("water", "wood", "scrub", "grassland")):
            lines.append(LineString(pts))
        elif t.get("railway") == "monorail" or "building" in t:
            lines.append(LineString(pts))
        if not ground or hw not in ("service", "footway", "pedestrian", "tertiary", "unclassified", "residential"):
            continue
        if w["closed"] and (hw == "pedestrian" or t.get("area") == "yes") and len(pts) >= 4:
            p = Polygon(pts).buffer(0)
            if p.area > 3:
                peds.append(p.intersection(fb))
            continue
        ls = LineString(pts)
        if ls.length < 3:
            continue
        (roads if hw in ("service", "tertiary", "unclassified", "residential") else paths).append(ls.intersection(fb).buffer(_hw(t) / 2, cap_style=2, join_style=1))
    for r in DL.DATA["relations"]:
        if r["tags"].get("highway") == "pedestrian" and r["id"] not in H.ENTRANCE_RELS and r["id"] != H.SQUARE_REL:
            for o in DL.outer_rings(r):
                p = Polygon(o).buffer(0)
                if p.intersects(fb) and Polygon(o).centroid.x > BOX[0]:
                    peds.append(p.intersection(fb))
    z_road = unary_union(roads).difference(blocked)
    z_plaza = unary_union(peds).difference(blocked).difference(z_road)
    z_path = unary_union(paths).difference(blocked).difference(z_road).difference(z_plaza)

    dlines_ = [(LineString(w["pts"]), 0) for w in W if _is_deck(w["tags"]) and len(w["pts"]) >= 2 and not w["closed"] and LineString(w["pts"]).intersects(fb)]
    lines.append(fb.exterior)
    faces = [f for f in polygonize(unary_union(lines)) if fb.contains(f.representative_point()) and f.area > 1.0]
    greens = unary_union([Polygon(w["pts"]).buffer(0) for w in W if w["closed"] and len(w["pts"]) >= 4 and (
        w["tags"].get("leisure") in ("garden", "park") or w["tags"].get("landuse") in ("grass", "forest", "flowerbed", "meadow")
        or w["tags"].get("natural") in ("wood", "scrub", "grassland")) and Polygon(w["pts"]).intersects(fb)])
    lanes = unary_union([LineString(w["pts"]).buffer(_hw(w["tags"]) / 2, cap_style=2) for w in W
                         if w["tags"].get("highway") in ("service", "tertiary", "unclassified") and H._on_ground(w["tags"])
                         and LineString(w["pts"]).intersects(fb)])
    built = unary_union([blocked, z_road, z_plaza, z_path])
    fill_road, fill_plaza, planters = [], [], []
    for f in faces:
        rest = f.difference(built)
        if rest.area < 1.0:
            continue
        if f.intersection(greens).area > 0.5 * f.area:
            planters += [p for p in G._polys(rest) if p.area > G.MIN_PLANTER]
        elif f.area < 8000:
            fill_road.append(rest.intersection(lanes))
            fill_plaza.append(rest.difference(lanes))
    z_road = unary_union([z_road] + fill_road)
    z_plaza = unary_union([z_plaza] + fill_plaza)
    # what the linework leaves open along the route (OSM draws the forecourts as lines only, so no face closes round them): paved too,
    # up to FILL_NEAR m from a road, footway or deck
    route = unary_union([l for l in lines if l.geom_type == "LineString" and l is not fb.exterior] + [ls for ls, _ in dlines_])
    fixed = unary_union([blocked, z_road, z_plaza, z_path] + planters)
    extra = fb.intersection(route.buffer(FILL_NEAR)).difference(fixed).difference(solid.buffer(0.3))
    extra = unary_union([p for p in G._polys(extra) if p.area > 1.0])
    z_road = unary_union([z_road, extra.intersection(lanes)])
    z_plaza = unary_union([z_plaza, extra.difference(lanes)])
    keep = lambda g: unary_union([p for p in G._polys(g) if p.area > 0.6])

    # decks
    decks, roofs, dlines = [], [], []
    for w in W:
        t = w["tags"]
        if not _is_deck(t) or len(w["pts"]) < 2 or not LineString(w["pts"]).intersects(fb):
            continue
        if w["closed"] and len(w["pts"]) >= 4:
            decks.append(Polygon(w["pts"]).buffer(0))
            if t.get("covered"):
                roofs.append((Polygon(w["pts"]).buffer(0), None))
            continue
        ls = LineString(w["pts"])
        decks.append(ls.buffer(_deck_w(t) / 2, cap_style=2, join_style=1))
        dlines.append((ls, _deck_w(t)))
        if t.get("covered") in ("yes", "colonnade"):
            roofs.append((ls.buffer(_deck_w(t) / 2 + 0.6, cap_style=2, join_style=1), ls))
    for w in W:                                       # the roofs on posts over the station's concourse (OSM building=roof, layer 1-2)
        t = w["tags"]
        if (t.get("building") == "roof" and t.get("layer") in ("1", "2") and w["closed"] and Polygon(w["pts"]).intersects(fb)
                and "キューポラ" not in t.get("name", "")):                 # the cupola is modelled on its own (cupola())
            roofs.append((Polygon(w["pts"]).buffer(0), None))
    deck = unary_union(decks).difference(bv.buffer(1.0))
    deck = unary_union([p for p in G._polys(deck) if p.area > 4.0]).intersection(fb)
    stairs = []
    for w in W:
        t = w["tags"]
        if t.get("highway") != "steps" or len(w["pts"]) < 2 or not LineString(w["pts"]).intersects(fb):
            continue
        a, b = w["pts"][0], w["pts"][-1]
        da, db = deck.distance(Point(a)), deck.distance(Point(b))
        if (da < 2.0) == (db < 2.0):
            continue
        hi, lo = (a, b) if da < 2.0 else (b, a)
        stairs.append((hi, lo))
    return dict(road=keep(z_road), path=keep(z_path), plaza=keep(z_plaza), planters=planters, void=solid.buffer(H.BUILDING_MARGIN),
                deck=deck, roofs=roofs, dlines=dlines, stairs=stairs, bv=bv, solid=solid)


# ------------------------------------------------------------------ terrain, ground, decks
def ground_meshes(P, T, meshes):
    zones = [("GW_road", P["road"]), ("GW_path", P["path"]), ("GW_plaza", P["plaza"])]
    pl_lines = unary_union([q.exterior for q in P["planters"]]) if P["planters"] else None
    for name, g in zones:
        if not g.is_empty:
            G.add_zone(meshes, T, name, g, edge="GW_edge", avoid=pl_lines)
    for q in P["planters"]:
        G.add_planter(meshes, T, q, curb="GW_curb", soil="GW_soil")


def deck_level(P, T):
    pts = []
    for ls, _ in P["dlines"]:
        pts += list(ls.coords)
    z = T.z(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
    return float(np.mean(z)) + DECK_H


def deck_meshes(P, T, M, ZD):
    deck = P["deck"]
    if deck.is_empty:
        return
    slab(M["GB_concrete"], deck.buffer(0), ZD - GIRDER, ZD - 0.05)                 # girder
    for p in G._polys(deck):                                                       # the walking surface
        for c in G.cdt(p):
            _tri(M["GB_deck"], (*c[0], ZD), (*c[1], ZD), (*c[2], ZD))
    # parapets on the outline, open at the stair mouths and where a roofed walkway's posts stand instead
    mouths = unary_union([Point(hi).buffer(STAIR_W / 2 + 0.5) for hi, _ in P["stairs"]]) if P["stairs"] else Polygon()
    edge = unary_union([p.exterior for p in G._polys(deck)] + [h for p in G._polys(deck) for h in p.interiors]).difference(mouths)
    par = edge.buffer(PARAPET_W / 2, cap_style=2, join_style=2)
    par = par.difference(P["bv"].buffer(0.5))
    for p in G._polys(par):
        slab(M["GB_white"], p, ZD, ZD + PARAPET_H - 0.1)
        slab(M["GB_trim"], p, ZD + PARAPET_H - 0.1, ZD + PARAPET_H)
    # columns
    beam = unary_union([LineString(w["pts"]) for w in DL.DATA["ways"] if w["tags"].get("railway") == "monorail" and len(w["pts"]) > 1]).buffer(4.0)
    for ls, w in P["dlines"]:
        L = ls.length
        for k in range(max(1, int(L // 10.0))):
            pt = ls.interpolate((k + 0.5) * L / max(1, int(L // 10.0)))
            if P["solid"].buffer(1.0).contains(pt) or not deck.contains(pt) or beam.contains(pt):
                continue
            zg = float(T.z(pt.x, pt.y)) - 0.3
            obox(M["GB_concrete"], pt.x, pt.y, 0.0, 0.8, 0.8, zg, ZD - GIRDER, top=False, bottom=False)
    # roofs on posts
    for poly, ls in P["roofs"]:
        poly = poly.intersection(BOXG).difference(_cupola_area())
        if poly.is_empty:
            continue
        zr = ZD + ROOF_H
        slab(M["GB_copper"], poly, zr, zr + ROOF_T)
        if ls is not None:
            L = ls.length
            n = max(2, int(L // 6.0))
            for k in range(n + 1):
                pt, pt2 = ls.interpolate(k * L / n), ls.interpolate(min(L, k * L / n + 0.5))
                ang = math.atan2(pt2.y - pt.y, pt2.x - pt.x) if L > 0 else 0
                for sgn in (-1, 1):
                    x, y = loc(pt.x, pt.y, ang, 0, sgn * 2.1)
                    if deck.contains(Point(x, y)) and not _cupola_area().contains(Point(x, y)):
                        obox(M["GB_white"], x, y, ang, 0.35, 0.35, ZD, zr, top=False, bottom=False)


BOXG = box(*BOX)


def _cupola_area():
    """plan area kept clear for the cupola (no walkway roof or posts in it)"""
    return unary_union([Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"] if "キューポラ" in w["tags"].get("name", "")]).buffer(2.5)


def stair_meshes(P, T, M, ZD):
    for hi, lo in P["stairs"]:
        zlo = float(T.z(lo[0], lo[1]))
        rise = ZD - zlo
        if rise < 0.5:
            continue
        d = np.array([hi[0] - lo[0], hi[1] - lo[1]]); L = np.linalg.norm(d)
        if L < 0.5:
            continue
        d /= L
        n = int(math.ceil(rise / RISER))
        run = max(L, n * 0.28)                            # the flight is at least 0.28 m per tread; extended past the low end
        ang = math.atan2(d[1], d[0])
        lo2 = (hi[0] - d[0] * run, hi[1] - d[1] * run)
        tread = run / n
        for k in range(n):
            z1 = zlo + rise * (k + 1) / n
            cu, cv = loc(lo2[0], lo2[1], ang, tread * (k + 0.5), 0)
            obox(M["GB_stone"], cu, cv, ang, tread, STAIR_W, min(zlo, z1) - 0.4 if k == 0 else z1 - RISER * 2.5, z1, top=True, bottom=False)
        lx, ly = loc(hi[0], hi[1], ang, 0.9, 0)                  # a landing over the deck's edge: OSM's end of the steps can be up to 2 m short of the deck
        obox(M["GB_stone"], lx, ly, ang, 2.0, STAIR_W, ZD - 0.6, ZD - 0.02, top=True, bottom=False)
        for sgn in (-1, 1):                               # side walls (parapets along the flight)
            a = loc(lo2[0], lo2[1], ang, 0, sgn * (STAIR_W / 2 + 0.1))
            b = loc(lo2[0], lo2[1], ang, run, sgn * (STAIR_W / 2 + 0.1))
            m = M["GB_white"]
            hs = 0.9
            _quad(m, (*a, zlo - 0.4), (*b, ZD - 0.4), (*b, ZD + hs), (*a, zlo + hs)) if sgn < 0 else _quad(m, (*b, ZD - 0.4), (*a, zlo - 0.4), (*a, zlo + hs), (*b, ZD + hs))
            _quad(m, (*a, zlo + hs), (*b, ZD + hs), (*b, ZD - 0.4), (*a, zlo - 0.4)) if sgn < 0 else _quad(m, (*b, ZD + hs), (*a, zlo + hs), (*a, zlo - 0.4), (*b, ZD - 0.4))


# ------------------------------------------------------------------ the cupola
# From the user's photo (2026-09-29): an open pavilion over the deck in mint green -- clusters of square pillars at the four corners,
# arches between them (and crossing inside), a glazed canopy, an arched sign board front and back ("Tokyo Disneyland": cream
# panel, red border; no lettering), a clock tower on top (the round castle medallion under the clock, a small dome, lantern and
# spire, a weathervane), red-and-yellow flags on two finials, lamp standards with clusters of white globes at the corners.
# The front faces the walk from Maihama Station. Sizes from the photo against people: ESTIMATES.
CU_HALF_A, CU_HALF_B = 5.6, 6.4          # half depth (along the deck) and half width
CU_POST = 4.2                             # pillar height above the deck
CU_EAVE = 5.0


def _sphere(m, c, r, n=12, rings=8):
    for j in range(rings):
        t0, t1 = -0.5 * math.pi + math.pi * j / rings, -0.5 * math.pi + math.pi * (j + 1) / rings
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            P_ = lambda t, a: np.array([math.cos(t) * math.cos(a), math.cos(t) * math.sin(a), math.sin(t)])
            q = [P_(t0, a0), P_(t0, a1), P_(t1, a1), P_(t1, a0)]
            pts = [np.array(c) + r * v for v in q]
            m.add([pts[0], pts[1], pts[2]], q[:3]); m.add([pts[0], pts[2], pts[3]], [q[0], q[2], q[3]])


def _lamp(M, x, y, z0, h=5.2):
    cyl(M["GB_mint"], x, y, 0.3, z0, z0 + 0.8, n=10)
    cyl(M["GB_mint"], x, y, 0.1, z0 + 0.8, z0 + h, n=8)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        gx, gy = x + 0.55 * math.cos(a), y + 0.55 * math.sin(a)
        _tube(M["GB_mint"], _smooth([(x, y, z0 + h - 0.9), (gx, gy, z0 + h - 0.8), (gx, gy, z0 + h - 0.45)], 2), 0.05, n=6, caps=False)
        _sphere(M["GB_lamp"], (gx, gy, z0 + h - 0.2), 0.28)
    _sphere(M["GB_lamp"], (x, y, z0 + h + 0.25), 0.3)


def cupola(P, T, M, ZD):
    ways = [w for w in DL.DATA["ways"] if "キューポラ" in w["tags"].get("name", "")]
    for w in ways:
        poly = Polygon(w["pts"]).buffer(0)
        c = poly.centroid
        ls = min((l for l, _ in P["dlines"] if l.length > 40), key=lambda l: l.distance(c))   # the walk from Maihama Station
        t = ls.project(c)
        q0, q1 = ls.interpolate(max(0.0, t - 8.0)), ls.interpolate(min(ls.length, t + 8.0))
        d = np.array([q1.x - q0.x, q1.y - q0.y]); d /= np.linalg.norm(d)
        if d[0] < 0:                                                     # a points east, away from the station; the front faces west
            d = -d
        ang = math.atan2(d[1], d[0])
        A3, B3, U3 = _v3(d[0], d[1], 0), _v3(-d[1], d[0], 0), _v3(0, 0, 1)
        C = _v3(c.x, c.y, ZD)
        L = lambda a, b, z: C + a * A3 + b * B3 + z * U3
        ha, hb = CU_HALF_A, CU_HALF_B
        # pillar clusters: two across the front and back, one behind each
        for sa in (-1, 1):
            for sb in (-1, 1):
                for da, db in ((0, 0), (0, -1.0), (-1.0, 0)):
                    p = L(sa * (ha + da), sb * (hb + db), 0)
                    obox(M["GB_mint"], p[0], p[1], ang, 0.9, 0.9, ZD, ZD + 0.9)
                    obox(M["GB_mint"], p[0], p[1], ang, 0.55, 0.55, ZD + 0.9, ZD + CU_POST - 0.4, top=False, bottom=False)
                    obox(M["GB_mint"], p[0], p[1], ang, 0.8, 0.8, ZD + CU_POST - 0.4, ZD + CU_POST)
        # arches: along each side, and two crossing ones
        def arch(p0, p1, rise, r=0.22):
            pts = [p0 + (p1 - p0) * (k / 16) + U3 * rise * math.sin(math.pi * k / 16) for k in range(17)]
            _tube(M["GB_mint"], pts, r, n=8)
        for sa in (-1, 1):
            arch(L(sa * ha, -hb + 1.0, CU_POST), L(sa * ha, hb - 1.0, CU_POST), 1.3)
        for sb in (-1, 1):
            arch(L(-ha + 1.0, sb * hb, CU_POST), L(ha - 1.0, sb * hb, CU_POST), 1.0)
        arch(L(-ha + 0.5, -hb + 0.5, CU_POST), L(ha - 0.5, hb - 0.5, CU_POST), 1.8, 0.16)
        arch(L(-ha + 0.5, hb - 0.5, CU_POST), L(ha - 0.5, -hb + 0.5, CU_POST), 1.8, 0.16)
        # the canopy: an eave beam round the top, a glazed hipped roof with green ribs
        ring = [tuple(L(sa * (ha + 0.9), sb * (hb + 0.9), 0)[:2]) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        inner = [tuple(L(sa * (ha - 0.2), sb * (hb - 0.2), 0)[:2]) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        slab(M["GB_mint"], Polygon(ring).difference(Polygon(inner)), ZD + CU_EAVE, ZD + CU_EAVE + 0.55)
        top = [L(sa * 2.0, sb * 2.4, CU_EAVE + 1.6) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        low = [_v3(*r, ZD + CU_EAVE + 0.55) for r in inner]
        for i in range(4):
            j = (i + 1) % 4
            _tri_facing(M["GB_glass"], low[i], low[j], top[j], U3); _tri_facing(M["GB_glass"], low[i], top[j], top[i], U3)
            _tube(M["GB_mint"], [low[i], top[i]], 0.12, n=6)
        for tri in ((top[0], top[1], top[2]), (top[0], top[2], top[3])):
            _tri_facing(M["GB_mint"], *tri, U3)
        # the sign boards front and back: an arched green frame, a cream panel with a red border
        for sa in (-1, 1):
            a0 = sa * (ha + 0.95)
            out = A3 * sa
            fr = Polygon([(-4.8, CU_EAVE + 0.3)] + [(4.8 * math.cos(math.pi * k / 20), CU_EAVE + 1.7 + 0.9 * math.sin(math.pi * k / 20)) for k in range(21)][::-1][::-1]
                         + [(-4.8, CU_EAVE + 0.3)])
            fr = Polygon([(4.8, CU_EAVE + 0.3)] + [(4.8 * math.cos(math.pi * k / 20), CU_EAVE + 1.8 + 1.0 * math.sin(math.pi * k / 20)) for k in range(21)]
                         + [(-4.8, CU_EAVE + 0.3)])
            panel = box(-3.9, CU_EAVE + 1.0, 3.9, CU_EAVE + 2.2)
            for mat, g, off in (("GB_mint", fr, 0.0), ("GB_sign_red", panel.buffer(0.14, join_style=2), 0.08), ("GB_sign_cream", panel, 0.12)):
                for tri in G.cdt(g):
                    _tri_facing(M[mat], *[L(a0 + sa * off, q[0], q[1]) for q in tri], out)
                if mat == "GB_mint":
                    for tri in G.cdt(g):
                        _tri_facing(M[mat], *[L(a0 - sa * 0.35, q[0], q[1]) for q in tri], -out)
            # finials with flags at the ends of the board
            for sb in (-1, 1):
                p = L(a0, sb * 4.6, CU_EAVE + 2.2)
                cyl(M["GB_mint"], p[0], p[1], 0.12, p[2], p[2] + 2.6, n=8, r1=0.05)
                f0 = p + U3 * 2.5
                _tri_facing(M["GB_flag_red"], f0, f0 - U3 * 0.9, f0 + B3 * sb * 1.4 - U3 * 0.35, out)
                _tri_facing(M["GB_flag_red"], f0, f0 + B3 * sb * 1.4 - U3 * 0.35, f0 - U3 * 0.9, -out)
                _tri_facing(M["GB_flag_yellow"], f0 - U3 * 0.45, f0 - U3 * 0.9, f0 + B3 * sb * 1.0 - U3 * 0.6, out)
                _tri_facing(M["GB_flag_yellow"], f0 - U3 * 0.45, f0 + B3 * sb * 1.0 - U3 * 0.6, f0 - U3 * 0.9, -out)
        # the clock tower
        zt = ZD + CU_EAVE + 1.6
        tw = [tuple(L(sa * 1.3, sb * 1.3, 0)[:2]) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        prism(M["GB_mint"], tw, zt - 0.3, zt + 3.2)
        for sa in (-1, 1):                                                   # clock faces on all four sides, the medallion front and back
            for axis, s2 in ((A3, sa), (B3, sa)):
                cc = C + axis * s2 * 1.32 + U3 * (CU_EAVE + 1.6 + 2.4)
                e1 = B3 if axis is A3 else A3
                _disc(M["GB_gold"], cc, e1, U3, axis * s2, 0.78, n=24)
                _disc(M["GB_clock"], cc + axis * s2 * 0.03, e1, U3, axis * s2, 0.66, n=24)
            mc = C + A3 * sa * 1.45 + U3 * (CU_EAVE + 1.6 + 0.95)
            _disc(M["GB_mint"], mc, B3, U3, A3 * sa, 0.95, n=24)
            _disc(M["GB_medal"], mc + A3 * sa * 0.04, B3, U3, A3 * sa, 0.78, n=24)
            _disc(M["GB_white"], mc + A3 * sa * 0.07 - U3 * 0.2, B3, U3, A3 * sa, 0.28, n=10)    # the castle in it, as a pale blot
        for sa in (-1, 1):
            for sb in (-1, 1):
                p = L(sa * 1.3, sb * 1.3, 0)
                cyl(M["GB_mint"], p[0], p[1], 0.14, zt + 3.2, zt + 4.1, n=8, r1=0.02)
        slab(M["GB_mint"], Polygon(tw).buffer(0.25, join_style=2), zt + 3.2, zt + 3.45)
        dome(M["GB_mint"], C[0], C[1], 1.25, zt + 3.45, squash=0.9)
        cyl(M["GB_mint"], C[0], C[1], 0.45, zt + 4.4, zt + 5.2, n=12)
        dome(M["GB_mint"], C[0], C[1], 0.55, zt + 5.2, squash=1.1)
        cyl(M["GB_gold"], C[0], C[1], 0.07, zt + 5.7, zt + 7.3, n=6, r1=0.02)
        wv = C + U3 * (zt - ZD + 7.0)                                           # the weathervane: a copper silhouette on the spire
        _tri_facing(M["GB_copper"], wv, wv + A3 * 0.9 + U3 * 0.5, wv + A3 * 1.1 - U3 * 0.1, B3)
        _tri_facing(M["GB_copper"], wv, wv + A3 * 1.1 - U3 * 0.1, wv + A3 * 0.9 + U3 * 0.5, -B3)
        # lamp standards with globe clusters, at the corners outside the pillars
        for sa in (-1, 1):
            for sb in (-1, 1):
                p = L(sa * (ha + 2.6), sb * (hb + 0.2), 0)
                _lamp(M, p[0], p[1], ZD)


# ------------------------------------------------------------------ Bon Voyage
# From the user's photos (2026-09-29): the shop is a giant suitcase -- walls in an orange-brown diamond quilt (GB_quilt, drawn by
# the page) under a rounded silver frame, a huge silver carrying handle over the deck-level entrance, which is framed by a silver
# arch ring; a round emblem on the facade. At its south-east end a giant hat box lies on its side across the deck: red with navy
# Mickey heads, a blue ring band on each face, a silver lid lip and handle; the deck runs through it in a vaulted passage hung with
# travel posters, with the red "BON VOYAGE" neon over the shop door. Sizes are read off the photos against people (door ~3 m):
# ESTIMATES. No lettering (the ring band and the neon are plain).
BV_TOP = 9.5                 # suitcase top above the deck
BV_RIM = 1.1                 # radius of the rounded silver frame along the top edge
HB_R, HB_D = 8.0, 10.0       # hat box radius (it stands on the ground) and depth along the deck
HB_W, HB_H = 6.8, 5.4        # passage through it: width, height above the deck (round top)
HB_OVER = 4.0                # how far the hat box overlaps the end of the suitcase


def _v3(*a):
    return np.array(a, float)


def _tri_facing(m, a, b, c, want):
    a, b, c = np.array(a, float), np.array(b, float), np.array(c, float)
    n = np.cross(b - a, c - a)
    if np.dot(n, want) < 0:
        b, c = c, b
    _tri(m, a, b, c)


def _disc(m, c, e1, e2, nrm, r, n=16, ang=0.0):
    """a flat disc at c in the plane (e1, e2), facing nrm"""
    ca, sa = math.cos(ang), math.sin(ang)
    e1, e2 = ca * e1 + sa * e2, -sa * e1 + ca * e2
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        _tri_facing(m, c, c + r * (math.cos(a0) * e1 + math.sin(a0) * e2), c + r * (math.cos(a1) * e1 + math.sin(a1) * e2), nrm)


def _mickey(m, c, e1, e2, nrm, s, ang):
    """a Mickey head (three discs) of head radius s"""
    ca, sa = math.cos(ang), math.sin(ang)
    u, v = ca * e1 + sa * e2, -sa * e1 + ca * e2
    _disc(m, c, u, v, nrm, s)
    for sx in (-1, 1):
        _disc(m, c + s * (sx * 1.0 * u + 1.0 * v) + 0.005 * nrm, u, v, nrm, s * 0.62, n=12)


def _smooth(pts, it=3):
    """Chaikin corner cutting (keeps the ends)"""
    pts = [np.array(p, float) for p in pts]
    for _ in range(it):
        out = [pts[0]]
        for i in range(len(pts) - 1):
            out += [0.75 * pts[i] + 0.25 * pts[i + 1], 0.25 * pts[i] + 0.75 * pts[i + 1]]
        out.append(pts[-1]); pts = out
    return pts


def _tube(m, pts, r, n=14, caps=True):
    """a tube along a 3D polyline, smooth normals (frames carried along the path)"""
    pts = [np.array(p, float) for p in pts]
    T_ = [pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)] for i in range(len(pts))]
    T_ = [t / (np.linalg.norm(t) or 1) for t in T_]
    ref = np.array([0, 0, 1.0]) if abs(T_[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N = np.cross(T_[0], ref); N /= np.linalg.norm(N)
    rings = []
    for i, p in enumerate(pts):
        N = N - np.dot(N, T_[i]) * T_[i]; N /= (np.linalg.norm(N) or 1)
        B = np.cross(T_[i], N)
        rings.append([(p + r * (math.cos(2 * math.pi * k / n) * N + math.sin(2 * math.pi * k / n) * B),
                       math.cos(2 * math.pi * k / n) * N + math.sin(2 * math.pi * k / n) * B) for k in range(n)])
    for i in range(len(rings) - 1):
        for k in range(n):
            a, b, c, d = rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]
            m.add([a[0], b[0], c[0]], [a[1], b[1], c[1]]); m.add([a[0], c[0], d[0]], [a[1], c[1], d[1]])
    if caps:
        for ring, p, t in ((rings[0], pts[0], -T_[0]), (rings[-1], pts[-1], T_[-1])):
            for k in range(n):
                _tri_facing(m, p, ring[k][0], ring[(k + 1) % n][0], t)


def _rounded_rim(M, poly, zt, R, steps=5):
    """the suitcase's rounded frame along the top edge: a quarter round of radius R, stepped"""
    for i in range(steps):
        t0, t1 = 0.5 * math.pi * i / steps, 0.5 * math.pi * (i + 1) / steps
        inset = R * (1 - math.cos((t0 + t1) / 2))
        g = poly.buffer(-inset, join_style=2)
        if g.is_empty:
            continue
        for p in G._polys(g):
            prism(M["GB_silver"], list(p.exterior.coords), zt - R + R * math.sin(t0), zt - R + R * math.sin(t1), top=False)
    for p in G._polys(poly.buffer(-R, join_style=2)):                       # the roof inside the frame
        for c in G.cdt(p):
            _tri(M["GB_concrete"], (*c[0], zt), (*c[1], zt), (*c[2], zt))


def _deck_axis(P, poly):
    """the deck line beside the shop, the along-deck span of the shop, and which way is the south-east end"""
    ls = min((l for l, _ in P["dlines"] if l.length > 40), key=lambda l: l.distance(poly))   # the walkway itself, not a stub to a door
    ts = [ls.project(Point(p)) for p in poly.exterior.coords]
    t_lo, t_hi = min(ts), max(ts)
    se_hi = ls.interpolate(t_hi).x > ls.interpolate(t_lo).x                 # the end towards the Resort Gateway Station (east)
    return ls, t_lo, t_hi, se_hi


def hat_frame(P, poly):
    """where the hat box stands: its centre on the deck line (plan Point), the unit axis d along the deck (towards the south-east)
    and v across it; its plan footprint"""
    ls, t_lo, t_hi, se_hi = _deck_axis(P, poly)
    t = (t_hi + HB_D / 2 - HB_OVER) if se_hi else (t_lo - HB_D / 2 + HB_OVER)
    c = ls.interpolate(t)
    a, b = ls.interpolate(t - 1.0), ls.interpolate(t + 1.0)
    d = np.array([b.x - a.x, b.y - a.y]); d /= np.linalg.norm(d)
    if not se_hi:
        d = -d
    v = np.array([-d[1], d[0]])
    foot = Polygon([(c.x + d[0] * u + v[0] * w, c.y + d[1] * u + v[1] * w)
                    for u, w in ((-HB_D / 2, -HB_R - 0.5), (HB_D / 2, -HB_R - 0.5), (HB_D / 2, HB_R + 0.5), (-HB_D / 2, HB_R + 0.5))])
    return c, d, v, foot


def _hat_box(P, T, M, ZD, poly):
    c, d, v, _ = hat_frame(P, poly)
    D3, V3, U3 = _v3(d[0], d[1], 0), _v3(v[0], v[1], 0), _v3(0, 0, 1)
    zg = float(T.z(c.x, c.y)) - 0.2
    zc = zg + HB_R
    C = _v3(c.x, c.y, zc)
    W = lambda u, vv, z: C + u * D3 + vv * V3 + z * U3                      # local (along, across, up from the centre) -> plan xyz
    hs = HB_H - HB_W / 2                                                     # passage: straight walls up to hs, then a half round
    zdk = ZD - zc
    arch = Polygon([(-HB_W / 2, zdk - 0.02)] + [(HB_W / 2 * math.cos(math.pi * k / 16), zdk + hs + HB_W / 2 * math.sin(math.pi * k / 16))
                                                for k in range(17)][::-1][::-1] + [(-HB_W / 2, zdk - 0.02)])
    arch = Polygon([(HB_W / 2, zdk - 0.02)] + [(HB_W / 2 * math.cos(math.pi * k / 16), zdk + hs + HB_W / 2 * math.sin(math.pi * k / 16)) for k in range(17)]
                   + [(-HB_W / 2, zdk - 0.02)])
    circle = Point(0, 0).buffer(HB_R, resolution=24)
    # the drum
    n = 64
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        for u0, u1, r, mat in ((-HB_D / 2 + 0.6, HB_D / 2 - 1.4, HB_R, "GB_hat_red"), (-HB_D / 2, -HB_D / 2 + 0.6, HB_R + 0.12, "GB_silver"),
                               (HB_D / 2 - 1.4, HB_D / 2, HB_R + 0.3, "GB_silver")):
            p = [W(u, r * math.cos(q), r * math.sin(q)) for u, q in ((u0, a0), (u0, a1), (u1, a1), (u1, a0))]
            nn = [math.cos(q) * V3 + math.sin(q) * U3 for q in (a0, a1, a1, a0)]
            want = nn[0]
            A = np.cross(p[1] - p[0], p[2] - p[0])
            if np.dot(A, want) < 0:
                p = [p[0], p[3], p[2], p[1]]; nn = [nn[0], nn[3], nn[2], nn[1]]
            M[mat].add([p[0], p[1], p[2]], [nn[0], nn[1], nn[2]]); M[mat].add([p[0], p[2], p[3]], [nn[0], nn[2], nn[3]])
    for u0, r0, r1 in ((-HB_D / 2, HB_R, HB_R + 0.12), (-HB_D / 2 + 0.6, HB_R, HB_R + 0.12), (HB_D / 2 - 1.4, HB_R, HB_R + 0.3), (HB_D / 2, HB_R, HB_R + 0.3)):
        ring = Point(0, 0).buffer(r1, resolution=24).difference(Point(0, 0).buffer(r0, resolution=24))   # the lips' edges
        for tri in G.cdt(ring):
            _tri_facing(M["GB_silver"], *[W(u0, q[0], q[1]) for q in tri], D3 * (1 if u0 > 0 else -1))
    # the two faces: red, a blue ring band, Mickey heads; the passage cut out
    face = circle.difference(arch)
    band = Point(0, 0).buffer(HB_R * 0.9, resolution=24).difference(Point(0, 0).buffer(HB_R * 0.78, resolution=24)).difference(arch.buffer(0.3))
    rng = np.random.default_rng(7)
    for sgn in (-1, 1):
        u = sgn * HB_D / 2
        out = D3 * sgn
        for tri in G.cdt(face):
            _tri_facing(M["GB_hat_red"], *[W(u, q[0], q[1]) for q in tri], out)
        for tri in G.cdt(band):
            _tri_facing(M["GB_hat_blue"], *[W(u + sgn * 0.03, q[0], q[1]) for q in tri], out)
        free = circle.buffer(-0.3).difference(band.buffer(0.1)).difference(arch.buffer(0.5))
        for gx in np.arange(-HB_R, HB_R, 1.7):
            for gz in np.arange(-HB_R, HB_R, 1.5):
                x, z = gx + (0.85 if int(round(gz / 1.5)) % 2 else 0), gz
                if free.contains(Point(x, z).buffer(0.62)):
                    _mickey(M["GB_hat_navy"], W(u + sgn * 0.04, x, z), V3, U3, out, 0.34, rng.uniform(-0.5, 0.5))
    # Mickeys round the drum
    for q in np.arange(0, 2 * math.pi, 2.3 / HB_R):
        nrm = math.cos(q) * V3 + math.sin(q) * U3
        if W(0, 0, 0)[2] + HB_R * math.sin(q) < zg + 0.8:
            continue
        for k, u in enumerate(np.arange(-HB_D / 2 + 1.8, HB_D / 2 - 2.0, 2.3)):
            uu = u + (1.1 if int(round(q * HB_R / 2.3)) % 2 else 0)
            if uu > HB_D / 2 - 2.2:
                continue
            e2 = np.cross(nrm, D3)
            _mickey(M["GB_hat_navy"], W(uu, 0, 0) + (HB_R + 0.03) * nrm, D3, e2, nrm, 0.42, rng.uniform(-0.5, 0.5))
    # the handle strap on top
    top = [W(u, 0, HB_R + 0.1) for u in (-2.6, -2.6)] 
    path = _smooth([W(-2.4, 0, HB_R), W(-2.2, 0, HB_R + 1.3), W(2.2, 0, HB_R + 1.3), W(2.4, 0, HB_R)], 3)
    _tube(M["GB_silver"], path, 0.28)
    for u in (-2.4, 2.4):
        obox(M["GB_silver"], *W(u, 0, 0)[:2], math.atan2(d[1], d[0]), 1.0, 0.9, zc + HB_R - 0.3, zc + HB_R + 0.3)
    # the passage: walls and a round vault (facing in), posters on the vault, the neon over the shop door
    m = 20
    prof = [(HB_W / 2, zdk)] + [(HB_W / 2 * math.cos(math.pi * k / m), zdk + hs + HB_W / 2 * math.sin(math.pi * k / m)) for k in range(m + 1)] + [(-HB_W / 2, zdk)]
    for i in range(len(prof) - 1):
        (v0, z0), (v1, z1) = prof[i], prof[i + 1]
        mid = np.array([(v0 + v1) / 2, (z0 + z1) / 2])
        want = -(mid[0] * V3 + (mid[1] - (zdk + hs if mid[1] > zdk + hs else mid[1])) * U3)
        if np.linalg.norm(want) < 1e-6:
            want = -mid[0] * V3
        p = [W(-HB_D / 2, v0, z0), W(-HB_D / 2, v1, z1), W(HB_D / 2, v1, z1), W(HB_D / 2, v0, z0)]
        _tri_facing(M["GB_vault"], p[0], p[1], p[2], want); _tri_facing(M["GB_vault"], p[0], p[2], p[3], want)
    cols = ("GB_poster1", "GB_poster2", "GB_poster3")
    for i, (u, q) in enumerate([(-3.6, 60), (-1.4, 100), (0.8, 55), (2.9, 115), (-2.6, 130), (1.9, 82), (3.8, 70), (-0.3, 140), (-3.9, 105)]):
        q = math.radians(q)
        nrm = -(math.cos(q) * V3 + math.sin(q) * U3)
        c0 = W(u, (HB_W / 2 - 0.04) * math.cos(q), zdk + hs + (HB_W / 2 - 0.04) * math.sin(q))
        e2 = np.cross(nrm, D3)
        ang = rng.uniform(-0.35, 0.35)
        ca, sa = math.cos(ang), math.sin(ang)
        e1r, e2r = ca * D3 + sa * e2, -sa * D3 + ca * e2
        for mat, w, h, off in (("GB_white", 1.25, 1.0, 0.0), (cols[i % 3], 1.05, 0.8, 0.02)):
            p = [c0 + off * nrm + sx * w / 2 * e1r + sy * h / 2 * e2r for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            _tri_facing(M[mat], p[0], p[1], p[2], nrm); _tri_facing(M[mat], p[0], p[2], p[3], nrm)
    # which wall of the passage faces the shop: the side towards the suitcase's centre
    cen = poly.centroid
    side = -1 if np.dot(np.array([cen.x - c.x, cen.y - c.y]), v) > 0 else 1   # the wall at v = -side*W/2 ... is the shop side
    vs = -side * (HB_W / 2 - 0.06)
    obox(M["GB_neon"], *W(-1.0, vs, 0)[:2], math.atan2(d[1], d[0]), 5.0, 0.12, ZD + 2.7, ZD + 3.4)
    obox(M["GB_win_dark"], *W(-1.0, vs, 0)[:2], math.atan2(d[1], d[0]), 4.0, 0.1, ZD, ZD + 2.5, top=False, bottom=False)
    return Polygon([tuple(W(u, vv, 0)[:2]) for u, vv in ((-HB_D / 2, -HB_R), (HB_D / 2, -HB_R), (HB_D / 2, HB_R), (-HB_D / 2, HB_R))])


def bon_voyage(P, T, M, ZD):
    ring = [tuple(p) for p in DL.WAYS[BV_WAY]["pts"]]
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    poly = Polygon(ring).buffer(0.6, join_style=2).buffer(-0.6, join_style=2).simplify(0.4)
    xs, ys = np.array([p[0] for p in ring]), np.array([p[1] for p in ring])
    z0 = float(np.min(T.z(xs, ys))) - 0.3
    zt = ZD + BV_TOP
    # the suitcase stops at the hat box (which overlaps its end), so nothing of it stands in the passage
    case = max(G._polys(poly.difference(hat_frame(P, poly)[3])), key=lambda g: g.area)
    ring_o = _ccw(list(case.exterior.coords))
    prism(M["GB_quilt"], ring_o, z0, zt - BV_RIM, top=False)
    _rounded_rim(M, case, zt, BV_RIM)
    band = case.buffer(0.12, join_style=2).difference(case)                   # the silver plinth band at deck level
    slab(M["GB_silver"], band, ZD - 0.15, ZD + 0.7)
    # the facade on the deck: the edge facing the deck, the longest one near the north-west end
    ls, t_lo, t_hi, se_hi = _deck_axis(P, poly)
    n = len(ring_o)
    best = None
    for i in range(n):
        a, b = ring_o[i], ring_o[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ang = math.atan2(b[1] - a[1], b[0] - a[0]); nx, ny = math.sin(ang), -math.cos(ang)
        if L > 8 and ls.distance(Point(mx + nx * 3, my + ny * 3)) < ls.distance(Point(mx, my)) and (best is None or L > best[0]):
            best = (L, a, b, ang, nx, ny)
    if best:
        L, a, b, ang, nx, ny = best
        ux, uy = math.cos(ang), math.sin(ang)
        Fn, Fu = _v3(nx, ny, 0), _v3(ux, uy, 0)
        F = lambda s, off, z: _v3(a[0] + ux * s + nx * off, a[1] + uy * s + ny * off, z)
        # the entrance: a silver arch ring round dark glass doors
        s0, hw, hh = L * 0.45, 3.3, 5.2
        path = [F(s0 - hw, 0.55, ZD)] + [F(s0 + hw * math.cos(math.pi - math.pi * k / 16), 0.55, ZD + hh - hw + hw * math.sin(math.pi * k / 16)) for k in range(17)] + [F(s0 + hw, 0.55, ZD)]
        _tube(M["GB_silver"], path, 0.5)
        door = [F(s0 - hw + 0.3, 0.08, ZD), F(s0 + hw - 0.3, 0.08, ZD)]
        obox(M["GB_win_dark"], *((door[0] + door[1]) / 2)[:2], ang, 2 * hw - 0.6, 0.12, ZD, ZD + hh - 0.8, top=False, bottom=False)
        obox(M["GB_glass"], *F(s0, 0.18, 0)[:2], ang, 2 * hw - 0.6, 0.05, ZD, ZD + hh - 0.8, top=False, bottom=False)
        # the carrying handle over it, standing off the top of the facade, the ends bent back into brackets
        ha, hb, zh = max(1.5, s0 - 7.0), min(L - 1.0, s0 + 7.0), zt - BV_RIM - 0.4
        pts = _smooth([F(ha, 0.3, zh - 0.6), F(ha, 2.6, zh - 0.2), F(ha + 1.2, 3.1, zh + 0.2), F(hb - 1.2, 3.1, zh + 0.2), F(hb, 2.6, zh - 0.2), F(hb, 0.3, zh - 0.6)], 3)
        _tube(M["GB_silver"], pts, 0.6, n=18)
        for sx in (ha, hb):
            obox(M["GB_silver"], *F(sx, 0.35, 0)[:2], ang, 1.6, 0.9, zh - 1.6, zh + 0.3)
        # the luggage-tag cord looping down from the left end
        cord = _smooth([F(ha + 0.2, 1.2, zh - 0.7), F(ha - 0.6, 1.6, zh - 3.0), F(ha + 0.4, 1.2, zh - 5.0), F(ha + 1.4, 0.8, zh - 3.2), F(ha + 0.6, 0.6, zh - 1.0)], 3)
        _tube(M["GB_silver"], cord, 0.1, n=8)
        # the round emblem further along the facade
        if L > 2 * hw + 6:
            e = F(min(L - 2.0, s0 + hw + 3.0), 0.12, ZD + 4.2)
            _disc(M["GB_silver"], e, Fu, _v3(0, 0, 1), Fn, 1.7, n=28)
            _disc(M["GB_medal"], e + Fn * 0.04, Fu, _v3(0, 0, 1), Fn, 1.45, n=28)
    hb = _hat_box(P, T, M, ZD, poly)
    return poly, hb


# ------------------------------------------------------------------ build
def build():
    P = plan()
    allz = [P["road"], P["path"], P["plaza"], P["deck"]] + P["planters"] + [P["bv"]]
    T = G.Terrain(unary_union(allz).bounds, void=P["void"])
    M = {n: G.Mesh(n) for n in GROUND + BUILD}
    ground_meshes(P, T, M)
    ZD = deck_level(P, T)
    deck_meshes(P, T, M, ZD)
    stair_meshes(P, T, M, ZD)
    cupola(P, T, M, ZD)
    bon_voyage(P, T, M, ZD)
    return P, T, M, ZD


def main():
    P, T, M, ZD = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, M)
    zs = np.concatenate([np.array(m.tris)[:, :, 2].ravel() for m in M.values() if m.tris])
    print(f"[gateway] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles, z {zs.min():.2f} .. {zs.max():.2f} m; deck level {ZD:.2f} m")
    print("  areas m2: roads %.0f, paths %.0f, plazas %.0f, %d planters, deck %.0f, %d stairs; Bon Voyage %.0f m2" % (
        P["road"].area, P["path"].area, P["plaza"].area, len(P["planters"]), P["deck"].area, len(P["stairs"]), P["bv"].area))
    print("  triangles:", {k: len(m.tris) for k, m in M.items() if m.tris})


if __name__ == "__main__":
    main()
