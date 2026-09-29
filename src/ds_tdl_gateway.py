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
            ゲートウェイキューポラ (copper dome) at the west end.
  Bon Voyage  the shop (OSM way 152465275, 1385 m2) -- NO PHOTOS YET: the footprint is the OSM one; the wall heights, the storefront
            band, the awnings and the giant luggage on the roof (suitcases, a hat box) are a first guess from a text description
            (a building shaped like stacked travel cases). To be redone from the user's screenshots.
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
         "GB_awning", "GB_leather", "GB_leather2", "GB_teal", "GB_red", "GB_deck", "GB_concrete", "GB_sign")


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
        if t.get("building") == "roof" and t.get("layer") in ("1", "2") and w["closed"] and Polygon(w["pts"]).intersects(fb):
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
        poly = poly.intersection(BOXG)
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
                    if deck.contains(Point(x, y)):
                        obox(M["GB_white"], x, y, ang, 0.35, 0.35, ZD, zr, top=False, bottom=False)


BOXG = box(*BOX)


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
def cupola(P, T, M, ZD):
    ways = [w for w in DL.DATA["ways"] if "キューポラ" in w["tags"].get("name", "")]
    for w in ways:
        p = Polygon(w["pts"]).buffer(0)
        c = p.centroid
        r = 0.5 * min(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1])
        r = max(r, 4.0)
        z = ZD + ROOF_H + ROOF_T
        for k in range(4):                                                           # it stands on four posts (the deck stays open under it)
            a = math.pi / 4 + k * math.pi / 2
            obox(M["GB_white"], c.x + (r - 0.6) * math.cos(a), c.y + (r - 0.6) * math.sin(a), a, 0.5, 0.5, ZD, z, top=False, bottom=False)
        slab(M["GB_copper"], Point(c.x, c.y).buffer(r + 0.2, 16), z - ROOF_T, z)
        cyl(M["GB_cream"], c.x, c.y, r, z, z + 2.2, n=24, top=False)                 # drum
        for k in range(8):
            a = 2 * math.pi * k / 8
            x, y = c.x + (r + 0.02) * math.cos(a), c.y + (r + 0.02) * math.sin(a)
            obox(M["GB_win_dark"], x, y, a, 0.15, 1.3, z + 0.6, z + 1.9, top=False, bottom=False)
        cyl(M["GB_trim"], c.x, c.y, r + 0.35, z + 2.2, z + 2.5, n=24)
        dome(M["GB_copper"], c.x, c.y, r * 0.95, z + 2.5, squash=1.1)
        cyl(M["GB_gold"], c.x, c.y, 0.12, z + 2.5 + r * 1.05, z + 2.5 + r * 1.05 + 1.6, n=8, r1=0.03)


# ------------------------------------------------------------------ Bon Voyage
def _trunk(M, cx, cy, ang, L, W, Hh, z0, body="GB_leather", trim="GB_leather2", angle_handle=True):
    """a giant travelling case: body, a lid seam, two straps, brass corners and latches, a handle"""
    obox(M[body], cx, cy, ang, L, W, z0, z0 + Hh)
    obox(M[trim], cx, cy, ang, L + 0.12, W + 0.12, z0 + Hh * 0.64, z0 + Hh * 0.7, top=False, bottom=False)      # the seam between lid and base
    for s in (-0.28, 0.28):                                                                                   # straps over the top and down the sides
        u, v = loc(cx, cy, ang, s * L, 0)
        obox(M[trim], u, v, ang, 0.7, W + 0.16, z0 + 0.02, z0 + Hh + 0.06, top=True, bottom=False)
        for sgn in (-1, 1):
            a, b = loc(cx, cy, ang, s * L, sgn * (W / 2 + 0.12))
            obox(M["GB_gold"], a, b, ang, 0.55, 0.12, z0 + Hh * 0.6, z0 + Hh * 0.78, top=True, bottom=False)     # latch
    for su in (-1, 1):                                                                                        # brass corners
        for sv in (-1, 1):
            a, b = loc(cx, cy, ang, su * L / 2, sv * W / 2)
            obox(M["GB_gold"], a, b, ang, 0.7, 0.7, z0 + Hh - 0.7, z0 + Hh + 0.08)
            obox(M["GB_gold"], a, b, ang, 0.7, 0.7, z0 - 0.02, z0 + 0.7)
    if angle_handle:                                                                                          # carrying handle on the lid
        for su in (-0.5, 0.5):
            a, b = loc(cx, cy, ang, su * L * 0.3, 0)
            obox(M["GB_gold"], a, b, ang, 0.18, 0.18, z0 + Hh, z0 + Hh + 0.55)
        a, b = loc(cx, cy, ang, 0, 0)
        obox(M["GB_gold"], a, b, ang, L * 0.3 + 0.18, 0.2, z0 + Hh + 0.5, z0 + Hh + 0.7)


def _hatbox(M, cx, cy, r, z0, Hh):
    cyl(M["GB_cream"], cx, cy, r, z0, z0 + Hh, n=32, top=False)
    cyl(M["GB_red"], cx, cy, r + 0.05, z0 + Hh * 0.35, z0 + Hh * 0.5, n=32, top=False)                       # the ribbon band
    cyl(M["GB_trim"], cx, cy, r + 0.35, z0 + Hh, z0 + Hh + 0.7, n=32)                                          # the lid
    cyl(M["GB_cream"], cx, cy, r * 0.82, z0 + Hh + 0.7, z0 + Hh + 1.0, n=32)
    dome(M["GB_red"], cx, cy, 0.9, z0 + Hh + 1.0)                                                             # the knob


def bon_voyage(P, T, M):
    ring = [tuple(p) for p in DL.WAYS[BV_WAY]["pts"]]
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    poly = Polygon(ring)
    z0 = float(np.min(T.z(np.array([p[0] for p in ring]), np.array([p[1] for p in ring])))) - 0.3
    zb = float(np.mean(T.z(np.array([p[0] for p in ring]), np.array([p[1] for p in ring]))))
    H1, BAND = 8.0, 6.6
    prism(M["GB_cream"], ring, z0, zb + BAND, top=False)
    ring_o = _ccw(ring)
    n = len(ring_o)
    cen = poly.centroid
    for i in range(n):
        a, b = ring_o[i], ring_o[(i + 1) % n]
        Ls = math.hypot(b[0] - a[0], b[1] - a[1])
        if Ls < 3.0:
            continue
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, ny = math.sin(ang), -math.cos(ang)                                   # outward (right of a->b, ccw ring)
        # shop windows: a dark glass band 0.6..3.6 m with mullions
        ux, uy = math.cos(ang), math.sin(ang)
        k = max(1, int((Ls - 1.6) // 2.4))
        for j in range(k):
            s = 0.8 + (Ls - 1.6) * (j + 0.5) / k
            wc = (a[0] + ux * s + nx * 0.05, a[1] + uy * s + ny * 0.05)
            obox(M["GB_win_dark"], wc[0], wc[1], ang, (Ls - 1.6) / k - 0.35, 0.1, zb + 0.6, zb + 3.6, top=False, bottom=False)
            obox(M["GB_glass"], wc[0] + nx * 0.02, wc[1] + ny * 0.02, ang, (Ls - 1.6) / k - 0.35, 0.05, zb + 0.6, zb + 3.6, top=False, bottom=False)
        obox(M["GB_trim"], mx + nx * 0.06, my + ny * 0.06, ang, Ls, 0.15, zb + 3.65, zb + 3.95, top=True, bottom=False)     # lintel
        # a striped awning over the windows on the longer sides
        if Ls > 8.0:
            for j in range(int(Ls // 1.2)):
                s = 0.6 + j * 1.2
                if s + 1.2 > Ls:
                    break
                c0 = (a[0] + ux * (s + 0.6), a[1] + uy * (s + 0.6))
                q = [(c0[0] - ux * 0.6, c0[1] - uy * 0.6, zb + 4.0), (c0[0] + ux * 0.6, c0[1] + uy * 0.6, zb + 4.0),
                     (c0[0] + ux * 0.6 + nx * 1.5, c0[1] + uy * 0.6 + ny * 1.5, zb + 3.5), (c0[0] - ux * 0.6 + nx * 1.5, c0[1] - uy * 0.6 + ny * 1.5, zb + 3.5)]
                _quad(M["GB_awning" if j % 2 == 0 else "GB_white"], q[0], q[1], q[2], q[3])
    # the upper band: leather-brown like a case's binding, with brass rivet strips
    inner = poly.buffer(0.08)
    prism(M["GB_leather"], _ccw(list(poly.buffer(0.1, join_style=2).exterior.coords)), zb + BAND, zb + H1, top=False)
    slab(M["GB_trim"], poly.buffer(0.5, join_style=2).difference(poly.buffer(-0.3, join_style=2)), zb + H1, zb + H1 + 0.5)   # coping
    for p in G._polys(poly.buffer(-0.3, join_style=2)):
        for c in G.cdt(p):
            _tri(M["GB_concrete"], (*c[0], zb + H1), (*c[1], zb + H1), (*c[2], zb + H1))
    for i in range(n):
        a, b = ring_o[i], ring_o[(i + 1) % n]
        Ls = math.hypot(b[0] - a[0], b[1] - a[1])
        if Ls < 3.0:
            continue
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        nx, ny = math.sin(ang), -math.cos(ang)
        obox(M["GB_gold"], (a[0] + b[0]) / 2 + nx * 0.14, (a[1] + b[1]) / 2 + ny * 0.14, ang, Ls - 0.4, 0.06, zb + BAND + 0.25, zb + BAND + 0.4, top=False, bottom=False)
        obox(M["GB_gold"], (a[0] + b[0]) / 2 + nx * 0.14, (a[1] + b[1]) / 2 + ny * 0.14, ang, Ls - 0.4, 0.06, zb + H1 - 0.45, zb + H1 - 0.3, top=False, bottom=False)
    # the giant luggage on the roof, spread along the long axis of the footprint
    mrr = poly.minimum_rotated_rectangle
    c = list(mrr.exterior.coords)[:4]
    e = [(c[1][0] - c[0][0], c[1][1] - c[0][1]), (c[2][0] - c[1][0], c[2][1] - c[1][1])]
    ax = e[0] if math.hypot(*e[0]) >= math.hypot(*e[1]) else e[1]
    ang = math.atan2(ax[1], ax[0])
    ux, uy = math.cos(ang), math.sin(ang)
    ts = [(p[0] - cen.x) * ux + (p[1] - cen.y) * uy for p in ring]
    t0, t1 = min(ts), max(ts)
    inside = poly.buffer(-2.2)
    def at(t, v=0.0):
        x, y = loc(cen.x, cen.y, ang, t, v)
        pt = Point(x, y)
        if not inside.contains(pt):                                     # slide across to stay on the roof
            for dv in (1.5, -1.5, 3, -3, 4.5, -4.5, 6, -6):
                x2, y2 = loc(cen.x, cen.y, ang, t, v + dv)
                if inside.contains(Point(x2, y2)):
                    return x2, y2
        return x, y
    zt = zb + H1 + 0.55
    x, y = at(t0 + (t1 - t0) * 0.22)
    _trunk(M, x, y, ang + math.pi / 2, 11.0, 4.6, 3.6, zt, "GB_leather", "GB_leather2")
    _trunk(M, x, y, ang + math.pi / 2, 8.0, 3.6, 2.8, zt + 3.6, "GB_teal", "GB_leather2")
    x, y = at(t0 + (t1 - t0) * 0.55, 1.0)
    _trunk(M, x, y, ang + math.pi / 2 + 0.15, 13.0, 5.0, 4.2, zt, "GB_red", "GB_leather2")
    _hatbox(M, *at(t0 + (t1 - t0) * 0.55, -1.0), 3.4, zt + 4.2, 2.2)
    x, y = at(t0 + (t1 - t0) * 0.85)
    _hatbox(M, x, y, 4.2, zt, 3.6)
    # a sign plaque on the coping of the longest side (no lettering yet)
    best = max(range(n), key=lambda i: math.hypot(ring_o[(i + 1) % n][0] - ring_o[i][0], ring_o[(i + 1) % n][1] - ring_o[i][1]))
    a, b = ring_o[best], ring_o[(best + 1) % n]
    ang2 = math.atan2(b[1] - a[1], b[0] - a[0]); nx, ny = math.sin(ang2), -math.cos(ang2)
    Ls = math.hypot(b[0] - a[0], b[1] - a[1])
    obox(M["GB_sign"], (a[0] + b[0]) / 2 + nx * 0.25, (a[1] + b[1]) / 2 + ny * 0.25, ang2, min(Ls * 0.5, 16.0), 0.3, zb + 4.4, zb + 5.9)


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
    bon_voyage(P, T, M)
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
