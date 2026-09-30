"""アドベンチャーランド -- Adventureland of Tokyo Disneyland: New Orleans Square, the Adventureland plaza and bazaar, the
Jungle Cruise / Western River Railroad station and the Polynesian corner (video-frame plan, range 1; plain Python, Blender
is not needed; no trees, no palms, no round clipped shrubs, no night version):

  python src/ds_tdl_adventureland.py   # -> output/disneysea/models/tdl_adv_ground.json (ground, beds, kerbs)
                                       #    + output/disneysea/models/tdl_adventureland.json (buildings, props, planting)
  python src/ds_ground.py tdl_land_ground   # the Land's ground, now cut round tdl_adv_ground
  python src/export_mock.py            # rebuilds the page (layer ディズニーランド)

Sources (docs/video_frames/range1.md has the frame list):
  video frames (view only, never copied or used as textures): v2 (daytime) 0:07:40-0:14:10 -- the Pirates facade over the
    green plaza (0:07:40-0:07:52), Royal Street and Cafe Orleans (0:08:04-0:08:48), the iron arch (0:08:52), the jungle path
    with white benches (0:09:04), the blue house (0:09:22), the Adventureland plaza (0:09:46), the boat works and the flag
    pergola (0:10:04-0:10:22), the Jungle Cruise gable and the railroad stairs (0:11:16-0:11:46), the queue roof (0:11:58),
    the Polynesian corner with its tiered tower, thatch, lava rock and Stitch's red ship (0:12:10-0:13:10), bamboo fences
    (0:13:46); v1 (dusk) 0:12:00-0:17:54 for the shapes (galleries, the yellow stucco block with terracotta roofs and its
    tower 0:14:18-0:15:12, the station 0:15:48-0:16:06, the Tiki Room's A-frame gable 0:16:42-0:16:48).
  OSM (plateau_data/disneyland_osm.json): the building ways below, gardens, water, paths. Google's satellite view at
    zoom 19-20 (0.2425 / 0.121 m per pixel, centred on the requested point) for the roofs, Royal Street (a notch between the
    Pirates block and the Cafe Orleans lobe of way 72865092) and the ground colours; labels there: ロイヤルストリート,
    カフェ・オーリンズ, スクウィーザーズ・トロピカル・ジュースバー, フレッシュフルーツオアシス, スキッパーズ・ギャレー.
  web (general knowledge, checked on tokyodisneyresort.jp names): Pirates of the Caribbean (1983) behind the New Orleans
    facades, Blue Bayou inside; Cafe Orleans; the Jungle Cruise (Wildlife Expeditions) dock under the Western River
    Railroad's station (a two-storey timber station, stairs up to the platform); the Enchanted Tiki Room (Stitch Presents
    "Aloha e Komo Mai!", 2008) with its tiered tiki tower; the Polynesian Terrace Restaurant under a big thatch roof;
    Swiss Family Treehouse (a tree: NOT built, no trees).

What is modelled (every height is an ESTIMATE from storeys: ground floor 4 m, upper 3.4 m, windows 1.2-1.6 m):
  New Orleans  way 72865092 split: its public edges get a 12 m deep row of 3-storey townhouse facades (pink, mint, ochre,
               blue, cream, brick; cream cornices, teal shutters, arched ground-floor openings, iron balconies and two-
               storey galleries with lace railings and flower boxes, a slate mansard with dormers and chimneys, a cupola),
               the rest is the show building (15 m, grey roof); the lobe south of Royal Street is Cafe Orleans (mint, a
               gallery on teal columns). Theatre Orleans (217842054) and the small blocks nearby as 2-storey houses.
  Adventureland the yellow stucco blocks with terracotta hips (the bazaar 1116316882/883, China Voyager 203424097) and
               their tower; timber stalls (boat works, juice bars) with red or thatch roofs; umbrellas on the small round
               roof ways; the flag pergola.
  Jungle Cruise the station relation 17744012: ground floor salmon timber with green trim and the JUNGLE CRUISE gable,
               the queue under it (green posts, rails), upper floor = the Western River Railroad station (tan boards, green
               gallery railings, stairs with the WESTERN RIVER RAILROAD sign).
  Polynesian   the Tiki Room (217929351): thatch hips, the A-frame gable with a carved face board, the 7-tier tower;
               Polynesian Terrace (218409834): a big thatch roof and A-frame; small thatch stalls; the railway trestle
               (roof way 1116316886) over the path.
  ground       (tdl_adv_ground) the guest area of the land (ds_ground's Adventureland region inside a hand drawn box, minus
               the plaza hub, the jungle and the backstage): mint-green painted paving with expansion joints (the plazas),
               blue-grey asphalt with raised beige flagstone sidewalks and kerbs (Royal Street and the street past the
               arch), grey cobbles (the bazaar courtyard), sandy concrete (Jungle Cruise front), light grey-brown
               concrete (Polynesian corner), manholes; every OSM garden as a bed: brick / stone / lava-rock kerb, a dark
               soil ribbon with flowers and ferns, a shrub mass inside (the page's hedge shader, key AG_soil).
  planting     flowers in six colours, ferns, big-leaf fans (green and red), potted flowers at doors, flower boxes on the
               balconies; lamps, white cast-iron benches, bins, bamboo and rustic fences, lava rocks, rope queue posts,
               barrels and crates, Stitch's red ship by the Tiki Room.
ESTIMATES: all heights and the facade rhythm (the fisheye frames give colours and elements, not sizes); which edge carries
  which colour; the cupola and the tower's places; the plan of the Pirates/Cafe block's arch (the street is NOT opened
  through it: its end is a painted arch); the zones' borders; the plant scatter. Interiors are not modelled.
Walk: buildings are closed solids down into the ground; sidewalks are 0.12 m kerbs, beds 0.25 m kerbs (walls to the walker).
Frame: the mock's local metres (+x east, +y north), z up; plan (x, y, z) -> glTF (x, z, -y) by ds_tdl_ground.write_gltf.
"""
import sys, math, pathlib

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
import ds_ground as GR
from ds_tdl_plaza_center import tri, frustum, box, lathe, sphere, Surface
from ds_tdl_plaza_hub import load_tris, quad, P3, UP, loft_rect, arched_window, bar
from ds_tdl_tomorrowland_terrace import polys, cap, sides, plate, text_poly

MODELS = ROOT / "output" / "disneysea" / "models"
OUT_G, OUT_B = MODELS / "tdl_adv_ground.json", MODELS / "tdl_adventureland.json"
BOX = sbox(-440.0, 682.0, -186.0, 905.0)
NORTH = Polygon([(-440, 905), (-440, 884), (-400, 884), (-330, 860), (-318, 852), (-296, 845), (-270, 832), (-250, 822),
                 (-228, 812), (-186, 812), (-186, 905)])          # backstage behind the facades (not paved here)
JUNGLE = Polygon([(-238, 748), (-236, 812), (-186, 812), (-186, 752)])   # the Jungle Cruise's river and jungle
CUT_MODELS = ("tdl_plaza_ground", "tdl_plaza_hub", "tdl_plaza_center", "tdl_world_bazaar", "tdl_water")
PIRATES, STATION, TIKI, POLY_T, TRESTLE = 72865092, 17744012, 217929351, 218409834, 1116316886
BAZAAR, BAZAAR2, CHINA, THEATRE = 1116316882, 1116316883, 203424097, 217842054
SHOW = (72865087, 1299467905, 119894891, 1283322069)
LOBE = slice(27, 51)                 # Cafe Orleans: points 27..50 of way 72865092 (south of Royal Street)
NOTCH = slice(43, 60)                # Royal Street: the notch between the lobe and the block (points 43..59)
# ground zones (plan polygons; the first that contains a piece's point wins; the rest is the green plaza paving)
Z_STREET = Polygon([(-345, 812), (-345, 866), (-296, 852), (-296, 815), (-318, 810)])
Z_COBBLE = Polygon([(-309, 789), (-283, 785), (-279, 813), (-305, 818)])
Z_SAND = Polygon([(-285, 745), (-285, 832), (-228, 832), (-228, 745)])
Z_POLY = Polygon([(-300, 682), (-300, 748), (-228, 748), (-228, 760), (-186, 760), (-186, 682)])
GREEN_LANDUSE = ("grass", "meadow", "flowerbed", "forest")     # planted ground; "forest" / "wood" become shrub and fern beds (no trees)
GREEN_NATURAL = ("wood", "scrub", "grassland", "heath")
CURB_H, CURB_W, RIBBON, KERB = 0.25, 0.3, 0.75, 0.12
SIDEWALK = 1.9                        # m: the flagstone sidewalks along the facades in the streets
JOINT, FLAG = 5.0, 1.1                # expansion joint spacing in the green paving; flagstone size
PALETTE = ("AD_pink", "AD_mint", "AD_yellow", "AD_cream", "AD_blue", "AD_brick", "AD_pgreen", "AD_salmon")
G_NAMES = ("AG_green", "AG_joint", "AG_street", "AG_flag", "AG_flag2", "AG_kerb", "AG_cobble", "AG_cobble2", "AG_sand",
           "AG_poly", "AG_manhole", "AG_edge", "AG_curb", "AG_brick", "AG_rock", "AG_bed", "AG_soil", "AG_floor")
FLOWERS = ("AD_fl_red", "AD_fl_pink", "AD_fl_yel", "AD_fl_org", "AD_fl_wht", "AD_fl_pur")
B_NAMES = PALETTE + ("AD_trim", "AD_shutter", "AD_iron", "AD_glass", "AD_door", "AD_slate", "AD_slated", "AD_roofred",
                     "AD_ochre", "AD_timber", "AD_timberd", "AD_orange", "AD_tgreen", "AD_thatch", "AD_thatchd", "AD_show",
                     "AD_showroof", "AD_sign", "AD_signr", "AD_signg", "AD_text", "AD_lamp", "AD_globe", "AD_bench", "AD_bin",
                     "AD_umb_r", "AD_umb_w", "AD_umb_t", "AD_umb_o", "AD_canvas", "AD_pot", "AD_fern", "AD_leaf", "AD_leafr",
                     "AD_bamboo", "AD_rope", "AD_post", "AD_rust", "AD_rock", "AD_stitch", "AD_flag1", "AD_flag2", "AD_flag3",
                     "AD_carve", "AD_carvey", "AD_table", "AD_stone") + FLOWERS
RNG = np.random.default_rng(1983)


# ---------------------------------------------------------------- small helpers
def V(p):
    return np.array([p[0], p[1]], float)


def ring_edges(poly):
    """(a, b, outward normal) for the edges of the CCW exterior ring."""
    cs = [np.array(c) for c in orient(poly, 1.0).exterior.coords]
    out = []
    for a, b in zip(cs[:-1], cs[1:]):
        L = np.linalg.norm(b - a)
        if L > 0.05:
            e = (b - a) / L
            out.append((a, b, np.array([e[1], -e[0]])))
    return out


def rect_of(poly):
    mr = poly.minimum_rotated_rectangle
    cs = [np.array(c) for c in list(mr.exterior.coords)[:4]]
    e1, e2 = cs[1] - cs[0], cs[2] - cs[1]
    l1, l2 = np.linalg.norm(e1), np.linalg.norm(e2)
    c = np.mean(cs, 0)
    if l1 >= l2:
        return c, e1 / l1, e2 / l2, l1 / 2, l2 / 2
    return c, e2 / l2, e1 / l1, l2 / 2, l1 / 2


def B3(e, n):
    return (np.array([e[0], e[1], 0.0]), np.array([n[0], n[1], 0.0]), UP)


def hip_strip(mesh, top, poly, z0, d, h, out=0.45):
    """A hipped / mansard roof over any plan: the strip between the eave (poly + out) and an inset d m in rises h m
    (heights from the distance to the eave), the inset part is flat at z0 + h (`top`)."""
    P = poly.buffer(out, join_style=2)
    c, u, v, hu, hv = rect_of(poly)
    d = min(d, 0.8 * hv + out)
    inner = P.buffer(-d, join_style=2)
    strip = P.difference(inner) if not inner.is_empty else P
    bnd = P.boundary
    for p in polys(strip.segmentize(3.0), 1e-4):
        for t in G.cdt(p):
            pts = [P3(q, z0 + h * min(1.0, bnd.distance(Point(*q)) / d)) for q in t]
            tri(mesh, *pts, UP)
    if not inner.is_empty:
        cap(top, inner, z0 + h)
    return inner, z0 + h


def rail(M, p0, p1, z, h=1.0, step=0.28, mesh="AD_iron", boxes=None):
    """A lace iron railing from p0 to p1 (plan) standing on z: top and bottom rails, thin balusters, a lace band."""
    p0, p1 = V(p0), V(p1)
    L = np.linalg.norm(p1 - p0)
    if L < 0.3:
        return
    bar(M[mesh], P3(p0, z + h), P3(p1, z + h), w=0.03, d=0.03)
    bar(M[mesh], P3(p0, z + 0.08), P3(p1, z + 0.08), w=0.025, d=0.02)
    bar(M[mesh], P3(p0, z + h - 0.18), P3(p1, z + h - 0.18), w=0.05, d=0.015)
    for t in np.arange(0.0, L + 1e-6, step):
        q = p0 + (p1 - p0) * t / L
        bar(M[mesh], P3(q, z + 0.08), P3(q, z + h), w=0.012, d=0.012)
    if boxes:
        e = (p1 - p0) / L; n = np.array([-e[1], e[0]])
        for t in np.arange(0.8, L - 0.5, 2.6):
            q = p0 + e * t
            box(M["AD_trim"], P3(q, z + h + 0.1), (0.4, 0.12, 0.1), B3(e, n))
            box(M[boxes[int(t * 7) % len(boxes)]], P3(q, z + h + 0.28), (0.42, 0.15, 0.12), B3(e, n))


# ---------------------------------------------------------------- the ground
def closed_polys(pred):
    out = []
    for w in DL.DATA["ways"]:
        if w["closed"] and len(w["pts"]) >= 4 and pred(w["tags"]):
            out.append(Polygon(w["pts"]).buffer(0))
    for r in DL.DATA["relations"]:
        if pred(r["tags"]):
            out += [Polygon(x).buffer(0) for x in DL.outer_rings(r)]
    return [p for p in out if not p.is_empty]


def plan():
    lands = GR.land_regions(BOX)
    area = BOX.intersection(lands["adv"].buffer(6.0)).difference(NORTH).difference(JUNGLE)
    cut = unary_union([g for g in (GR.model_footprint(m) for m in CUT_MODELS) if g is not None and not g.is_empty])
    buildings = unary_union([p for p in closed_polys(lambda t: "building" in t and t["building"] not in ("roof", "no")) if p.intersects(BOX)])
    water = unary_union([p for p in closed_polys(lambda t: t.get("natural") == "water" or bool(t.get("water"))) if p.intersects(BOX)])
    area = area.difference(cut.buffer(0.05)).difference(water)
    gardens = unary_union([p for p in closed_polys(lambda t: t.get("leisure") == "garden" or t.get("landuse") in GREEN_LANDUSE
                                                   or t.get("natural") in GREEN_NATURAL) if p.intersects(BOX)])
    open_ = area.difference(buildings)
    beds = [q for q in G._polys(open_.intersection(gardens)) if q.area >= 2.0]
    beds = [q.buffer(-0.02, join_style=2) for q in beds]
    beds = [q for q in beds if not q.is_empty and q.geom_type == "Polygon"]
    paving = unary_union([p for p in G._polys(open_.difference(unary_union(beds).buffer(0.02))) if p.area > 1.0])
    ways = {w["id"]: w for w in DL.DATA["ways"]}
    pts = ways[PIRATES]["pts"]
    notch = Polygon(pts[NOTCH]).buffer(0).difference(buildings)
    return dict(area=area, paving=paving, beds=beds, buildings=buildings, water=water, notch=notch, cut=cut)


def zone_of(q):
    p = q.representative_point()
    for name, z in (("cobble", Z_COBBLE), ("street", Z_STREET), ("poly", Z_POLY), ("sand", Z_SAND)):
        if z.contains(p):
            return name
    return "green"


def grid_lines(bounds, step, width, ang=0.0):
    x0, y0, x1, y1 = bounds
    c = ((x0 + x1) / 2, (y0 + y1) / 2); R = math.hypot(x1 - x0, y1 - y0) / 2 + step
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for k in np.arange(-R, R, step):
        for (ux, uy) in ((ca, sa), (-sa, ca)):
            px, py = c[0] + k * -uy, c[1] + k * ux
            out.append(LineString([(px - R * ux, py - R * uy), (px + R * ux, py + R * uy)]).buffer(width / 2, cap_style=2))
    return unary_union(out)


def checker(geom, step, ang):
    """Split geom into two alternating sets of squares (flagstones / cobbles)."""
    x0, y0, x1, y1 = geom.bounds
    ca, sa = math.cos(ang), math.sin(ang)
    a, b = [], []
    for i in range(int((x0 - 5) // step), int((x1 + 5) // step) + 1):
        for j in range(int((y0 - 5) // step), int((y1 + 5) // step) + 1):
            s = sbox(i * step + 0.03, j * step + 0.03, (i + 1) * step - 0.03, (j + 1) * step - 0.03)
            s = shapely.affinity.rotate(s, math.degrees(ang), origin=(0, 0))
            if s.intersects(geom):
                (a if (i + j) % 2 else b).append(s)
    A = unary_union(a).intersection(geom) if a else Polygon()
    Bq = unary_union(b).intersection(geom) if b else Polygon()
    return A, Bq, geom.difference(A).difference(Bq)


def surface(meshes, T, name, geom, dz=0.0, skirt="AG_edge", kerb=None):
    """Terrain (+dz) over geom; its free edges get a skirt (or a kerb face down to the terrain when raised)."""
    tris = []
    for poly in G._polys(geom):
        if poly.area > 1e-3:
            tris += G.top_surface(meshes[name], T, poly, dz=dz)
    for a, b in G.free_edges(tris):
        za, zb = float(T.z(a[0], a[1])) + dz, float(T.z(b[0], b[1])) + dz
        G.wall(meshes[kerb or skirt], a, b, za, zb, za - dz - 0.15, zb - dz - 0.15)
    return tris


def add_bed(meshes, T, q, zone):
    """A bed: kerb ring, a flat dark soil ribbon (flowers and ferns stand on it), a shrub mass inside (AG_soil)."""
    curb = {"street": "AG_brick", "green": "AG_brick", "poly": "AG_rock", "sand": "AG_rock"}.get(zone, "AG_curb")
    if q.representative_point().y > 798 and q.representative_point().x < -345:
        curb = "AG_brick"
    q = orient(q, 1.0)
    q_in = q.buffer(-CURB_W, join_style=2)
    ring = q.difference(q_in) if not q_in.is_empty else q
    tris = []
    for poly in G._polys(ring):
        tris += G.top_surface(meshes[curb], T, poly, dz=CURB_H)
    for a, b in G.free_edges(tris):
        za, zb = float(T.z(a[0], a[1])) + CURB_H, float(T.z(b[0], b[1])) + CURB_H
        G.wall(meshes[curb], a, b, za, zb, za - CURB_H - 0.1, zb - CURB_H - 0.1)
    if q_in.is_empty:
        return None, None
    inner = q_in.buffer(-RIBBON, join_style=2) if q_in.area > 10.0 else Polygon()
    rib = q_in.difference(inner) if not inner.is_empty else q_in
    for poly in G._polys(rib):
        G.top_surface(meshes["AG_bed"], T, poly, dz=CURB_H - 0.06)
    for poly in G._polys(inner):
        G.top_surface(meshes["AG_soil"], T, poly, dz=CURB_H - 0.06)
    return rib, inner


def build_ground():
    P = plan()
    T = G.Terrain(P["area"].buffer(10).bounds, void=unary_union([P["buildings"], P["water"]]).buffer(3.0))
    meshes = {n: G.Mesh(n) for n in G_NAMES}
    # split the paving by the zone polygons (in order), the rest is green
    rest = P["paving"]
    parts = {}
    for name, zp in (("cobble", Z_COBBLE), ("street", Z_STREET), ("poly", Z_POLY), ("sand", Z_SAND)):
        parts[name] = rest.intersection(zp); rest = rest.difference(zp)
    parts["street"] = unary_union([parts["street"], P["paving"].intersection(P["notch"].buffer(0.3))])
    parts["green"] = rest.difference(P["notch"].buffer(0.3))
    for k in ("cobble", "poly", "sand"):
        parts[k] = parts[k].difference(P["notch"].buffer(0.3))
    info = {k: round(v.area) for k, v in parts.items()}
    # streets: asphalt with raised flagstone sidewalks along the buildings
    side = parts["street"].intersection(P["buildings"].buffer(SIDEWALK, join_style=2))
    road = parts["street"].difference(side)
    fa, fb, fj = checker(side, FLAG, math.radians(28))
    surface(meshes, T, "AG_street", road)
    for name, g in (("AG_flag", fa), ("AG_flag2", fb), ("AG_kerb", fj)):
        surface(meshes, T, name, g, dz=KERB, kerb="AG_kerb")
    # green paving with expansion joints
    for key, mat in (("green", "AG_green"), ("poly", "AG_poly"), ("sand", "AG_sand")):
        g = parts[key]
        if g.is_empty:
            continue
        lines = grid_lines(g.bounds, JOINT if key == "green" else 4.0, 0.09, math.radians(28)).intersection(g)
        surface(meshes, T, mat, g.difference(lines))
        surface(meshes, T, "AG_joint", lines)
    ca, cb, cj = checker(parts["cobble"], 0.6, math.radians(15))
    for name, g in (("AG_cobble", ca), ("AG_cobble2", cb), ("AG_joint", cj)):
        surface(meshes, T, name, g)
    # manholes on the streets and plazas (every ~22 m along the paving's middle, ESTIMATE)
    holes = []
    for key in ("street", "green", "sand"):
        for p in G._polys(parts[key].buffer(-2.5)):
            for d in np.arange(6.0, p.exterior.length, 22.0):
                q = p.exterior.interpolate(d)
                holes.append(q)
    for q in holes[::2]:
        disc = q.buffer(0.35, 8)
        for t in G.cdt(disc):
            z = T.z(t[:, 0], t[:, 1]) + 0.015
            meshes["AG_manhole"].add(np.column_stack([t[:, :2], z]), np.tile(UP, (3, 1)))
    ribs, inners = [], []
    for q in P["beds"]:
        zone = zone_of(q)
        rib, inner = add_bed(meshes, T, q, zone)
        if rib is not None:
            ribs.append((rib, zone)); inners.append((inner, zone))
    info["beds"] = (len(P["beds"]), round(sum(q.area for q in P["beds"])))
    return P, T, meshes, dict(ribs=ribs, inners=inners, parts=parts), info


# ---------------------------------------------------------------- buildings: facades
class Ctx:
    def __init__(self, M, gr, paving):
        self.M, self.gr, self.paving = M, gr, paving
        self.pv = paving.buffer(0.6)
        self.lamp_spots, self.pot_spots = [], []
        self.bld = Polygon()

    def space(self, a, b, nrm):
        """Free distance in front of an edge (to the nearest other building), sampled at three points."""
        best = 30.0
        for t in (0.25, 0.5, 0.75):
            m = a + (b - a) * t
            ray = LineString([m + nrm * 0.4, m + nrm * 30.0])
            hit = ray.intersection(self.bld)
            if not hit.is_empty:
                best = min(best, 0.4 + Point(*(m + nrm * 0.4)).distance(hit))
        return best

    def is_front(self, a, b, nrm, reach=2.0):
        m = (a + b) / 2
        return self.pv.contains(Point(*(m + nrm * reach))) or self.pv.contains(Point(*(m + nrm * 0.8)))


def floor_of(ctx, poly):
    zlo, zhi = ctx.gr.span(poly, 0.8)
    return zlo - 0.5, zhi + 0.05


def plain_walls(M, poly, zb, ztop, mat):
    sides(M[mat], poly, zb, ztop)


def nola_edge(ctx, a, b, nrm, zb, zf, n, sh, colours, galleries, cafe=False):
    """One public edge of a New Orleans block: coloured segments, arched ground-floor openings, shuttered upper windows,
    floor bands, iron balconies or two-storey galleries, a cornice. Returns the top of the wall."""
    M = ctx.M
    L = np.linalg.norm(b - a); e = (b - a) / L; E3, N3 = np.array([*e, 0]), np.array([*nrm, 0])
    space = ctx.space(a, b, nrm)
    if space < 6.5:                                     # a narrow street (Royal Street): balconies only, no galleries
        galleries = False
    z1 = zf + 4.0; ztop = zf + 4.0 + (n - 1) * sh + 0.7
    nseg = max(1, int(round(L / RNG.uniform(7.5, 11.0))))
    for s in range(nseg):
        s0, s1 = L * s / nseg, L * (s + 1) / nseg
        pa, pb = a + e * s0, a + e * s1
        col = colours[int(RNG.integers(len(colours)))]
        zt = ztop + (0.0 if cafe else float(RNG.choice([0.0, 0.0, 0.8, -0.6])))
        quad(M[col], P3(pa, zb), P3(pb, zb), P3(pb, zt), P3(pa, zt), N3)
        box(M["AD_trim"], P3((pa + pb) / 2, zt - 0.2) + N3 * 0.18, ((s1 - s0) / 2 + 0.05, 0.2, 0.22), (E3, N3, UP))   # cornice
        box(M["AD_trim"], P3(pa, (zb + zt) / 2) + N3 * 0.06, (0.18, 0.08, (zt - zb) / 2), (E3, N3, UP))           # pilaster
        seg = s1 - s0
        nb = max(1, int(round(seg / 3.1))); bw = seg / nb
        gal = galleries and (cafe or RNG.random() < 0.45)
        for k in range(nb):
            c = pa + e * (k + 0.5) * bw
            w = min(1.5, bw - 0.9)
            if w < 0.7:
                continue
            door = (k % 2 == 0)
            z0 = zf + (0.02 if door else 0.75)
            arched_window(M["AD_trim"], c - e * (w / 2 + 0.12), c + e * (w / 2 + 0.12), nrm, z0, zf + 3.1 - w / 2, off=0.03)
            arched_window(M["AD_glass" if not door else "AD_door"], c - e * w / 2, c + e * w / 2, nrm, z0, zf + 3.0 - w / 2, off=0.05)
            if door and k % 4 == 0:
                ctx.pot_spots.append((c + nrm * 0.55 - e * (w / 2 + 0.35), c + nrm * 0.55 + e * (w / 2 + 0.35)))
            for f in range(1, n):
                zz = zf + 4.0 + (f - 1) * sh
                ww = min(1.1, bw - 1.4)
                if ww < 0.5:
                    continue
                quad(M["AD_glass"], P3(c - e * ww / 2, zz + 0.35) + N3 * 0.05, P3(c + e * ww / 2, zz + 0.35) + N3 * 0.05,
                     P3(c + e * ww / 2, zz + sh - 0.55) + N3 * 0.05, P3(c - e * ww / 2, zz + sh - 0.55) + N3 * 0.05, N3)
                box(M["AD_trim"], P3(c, zz + sh - 0.45) + N3 * 0.07, (ww / 2 + 0.15, 0.07, 0.1), (E3, N3, UP))
                for sgn in (-1, 1):
                    box(M["AD_shutter"], P3(c + e * sgn * (ww / 2 + 0.3), zz + 0.35 + (sh - 0.9) / 2) + N3 * 0.08,
                        (0.27, 0.04, (sh - 0.9) / 2), (E3, N3, UP))
        for f in range(1, n):                              # floor bands, balconies / galleries
            zz = zf + 4.0 + (f - 1) * sh
            box(M["AD_trim"], P3((pa + pb) / 2, zz) + N3 * 0.08, (seg / 2, 0.1, 0.14), (E3, N3, UP))
            dep = 2.3 if gal else min(0.95, space / 5.0)
            if not gal and RNG.random() < 0.35:
                continue
            box(M["AD_iron"], P3((pa + pb) / 2, zz - 0.06) + N3 * dep / 2, (seg / 2 - 0.1, dep / 2, 0.08), (E3, N3, UP))
            q0, q1 = pa + e * 0.15 + nrm * dep, pb - e * 0.15 + nrm * dep
            rail(M, q0, q1, zz + 0.02, boxes=FLOWERS[:3] if RNG.random() < 0.7 else None)
            rail(M, pa + e * 0.15, q0, zz + 0.02); rail(M, pb - e * 0.15, q1, zz + 0.02)
            if gal:
                for t in np.linspace(0.3, seg - 0.3, max(2, int(seg / 2.6) + 1)):
                    q = pa + e * t + nrm * (dep - 0.12)
                    frustum(M["AD_iron"], P3(q, zz - 0.06), P3(q, zz - (4.0 if f == 1 else sh) + 0.02 if f > 1 else zb + 0.4), 0.07, 0.07, n=6)
                    bar(M["AD_iron"], P3(q, zz - 0.35), P3(q - nrm * 0.7, zz - 0.08), w=0.02, d=0.02)   # lace bracket
                if f == n - 1:                                  # the gallery's roof
                    zr = zz + sh - 0.25
                    for t in np.linspace(0.3, seg - 0.3, max(2, int(seg / 2.6) + 1)):
                        q = pa + e * t + nrm * (dep - 0.12)
                        frustum(M["AD_iron"], P3(q, zz), P3(q, zr), 0.05, 0.05, n=6)
                    quad(M["AD_slated"], P3(pa, zr + 0.35), P3(pb, zr + 0.35), P3(pb + nrm * (dep + 0.15), zr), P3(pa + nrm * (dep + 0.15), zr), UP)
        if gal and n >= 2:                                  # ground level of a gallery: the column bases are on the pavement
            for t in np.linspace(0.3, seg - 0.3, max(2, int(seg / 2.6) + 1)):
                q = pa + e * t + nrm * 2.18
                frustum(M["AD_iron"], P3(q, zb + 0.3), P3(q, zf + 3.94), 0.075, 0.075, n=6)
                frustum(M["AD_iron"], P3(q, zf - 0.05), P3(q, zf + 0.5), 0.13, 0.1, n=6)
    for t in np.arange(4.0, L - 1.0, 12.0):
        ctx.lamp_spots.append(a + e * t + nrm * (3.2 if galleries else 2.4))
    return ztop


def nola_block(ctx, poly, n=3, sh=3.4, colours=PALETTE, back="AD_cream", galleries=True, cafe=False, roof=True, chimneys=True):
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    ztop = zf + 4.0 + (n - 1) * sh + 0.7
    fronts = 0
    for a, b, nrm in ring_edges(poly):
        if ctx.is_front(a, b, nrm):
            nola_edge(ctx, a, b, nrm, zb, zf, n, sh, colours, galleries, cafe); fronts += 1
        else:
            quad(M[back], P3(a, zb), P3(b, zb), P3(b, ztop), P3(a, ztop), np.array([*nrm, 0]))
    if roof:
        cap(M["AD_slated"], poly, ztop - 0.05)
        inner, zr = hip_strip(M["AD_slate"], M["AD_slated"], poly, ztop - 0.05, 2.6, 2.4, out=0.25)
        if chimneys and not inner.is_empty:
            for p in G._polys(inner):
                ring = p.exterior
                for d in np.arange(3.0, ring.length, 13.0):
                    q = ring.interpolate(d)
                    box(M["AD_brick"], (q.x, q.y, zr + 0.9), (0.45, 0.7, 1.1))
                    box(M["AD_trim"], (q.x, q.y, zr + 2.05), (0.55, 0.8, 0.08))
        # dormers on the public slopes
        for a, b, nrm in ring_edges(poly):
            L = np.linalg.norm(b - a)
            if L < 5 or not ctx.is_front(a, b, nrm):
                continue
            e = (b - a) / L
            for t in np.arange(2.5, L - 1.5, 4.5):
                p = a + e * t - nrm * 1.0
                B = B3(e, nrm)
                box(M["AD_trim"], P3(p, ztop + 0.9), (0.6, 0.6, 0.75), B)
                arched_window(M["AD_glass"], p - e * 0.35 + nrm * 0.6, p + e * 0.35 + nrm * 0.6, nrm, ztop + 0.45, ztop + 1.2, off=0.02, n=4)
                loft_rect(M["AD_slate"], P3(p, ztop + 1.65), e, nrm, [(0.75, 0.75, 0.0), (0.05, 0.6, 0.55)])
    return dict(fronts=fronts, top=round(ztop, 1))


def pirates(ctx, poly_all):
    """72865092: the Cafe Orleans lobe, a 12 m deep row of townhouse facades on the public edges, the show building behind."""
    M = ctx.M
    pts = DL.WAYS[PIRATES]["pts"]
    lobe = Polygon(pts[LOBE]).buffer(0).intersection(poly_all)
    lobe = max(G._polys(lobe), key=lambda p: p.area)
    rest = poly_all.difference(lobe.buffer(0.01))
    rest = max(G._polys(rest), key=lambda p: p.area)
    fronts = [LineString([a, b]) for a, b, nrm in ring_edges(rest) if ctx.is_front(a, b, nrm)]
    strip = rest.intersection(unary_union([f.buffer(12.0, cap_style=2, join_style=2) for f in fronts]))
    strip = unary_union([p for p in G._polys(strip) if p.area > 20]).buffer(0.3).buffer(-0.3)
    back = rest.difference(strip.buffer(0.02))
    info = {}
    for p in G._polys(strip):
        info.setdefault("front", []).append(nola_block(ctx, p, n=3, sh=3.4))
    zb, zf = floor_of(ctx, rest)
    for p in G._polys(back):
        if p.area < 5:
            continue
        sides(M["AD_show"], p, zb, zf + 15.0)
        cap(M["AD_showroof"], p, zf + 15.0)
    info["cafe"] = nola_block(ctx, lobe, n=2, sh=3.6, colours=("AD_mint",), back="AD_mint", cafe=True)
    # the cupola over the facade's west part (0:07:40), ESTIMATE of its place
    fp = max(G._polys(strip), key=lambda p: p.area)
    q = min([np.array(c) for c in fp.exterior.coords], key=lambda c: c[0])
    q = np.array(fp.buffer(-5).representative_point().coords[0]) if fp.buffer(-5).area > 0 else q
    zt = zf + 4.0 + 2 * 3.4 + 0.7 + 2.4
    loft_rect(M["AD_cream"], P3(q, zt - 1), (1, 0), (0, 1), [(1.8, 1.8, 0), (1.8, 1.8, 3.2)])
    for s in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        n2 = np.array(s, float); e2 = np.array([-s[1], s[0]], float)
        arched_window(M["AD_glass"], q + n2 * 1.8 - e2 * 0.5, q + n2 * 1.8 + e2 * 0.5, n2, zt - 0.3, zt + 1.3, off=0.03)
    lathe(M["AD_slate"], (q[0], q[1], zt + 2.2), [(2.2, 0), (1.9, 0.5), (1.2, 1.3), (0.5, 1.9), (0.12, 2.3), (0.0, 2.4)], n=12)
    lathe(M["AD_signg"], (q[0], q[1], zt + 4.6), [(0.1, 0), (0.05, 1.0), (0, 1.3)], n=6)
    # the Pirates sign over the entrance: an oval on the facade nearest the plaza's middle
    best = None
    for a, b, nrm in ring_edges(fp):
        if ctx.is_front(a, b, nrm):
            m = (a + b) / 2
            d = np.linalg.norm(m - np.array([-380.0, 826.0]))
            if best is None or d < best[0]:
                best = (d, m, (b - a) / np.linalg.norm(b - a), nrm)
    if best:
        _, m, e, nrm = best
        c3 = P3(m, zf + 4.9) + np.array([*nrm, 0]) * 2.45
        el = Point(0, 0).buffer(1.0, 24)
        el = shapely.affinity.scale(el, 2.1, 0.8)
        plate(M["AD_signg"], el, c3, np.array([*e, 0]), UP, np.array([*nrm, 0]), off=0.0, t=0.08)
        plate(M["AD_umb_t"], shapely.affinity.scale(el, 0.9, 0.82), c3, np.array([*e, 0]), UP, np.array([*nrm, 0]), off=0.02)
        plate(M["AD_trim"], text_poly("PIRATES OF THE CARIBBEAN", 0.26), c3, np.array([*e, 0]), UP, np.array([*nrm, 0]), off=0.04)
    # the painted arch at Royal Street's east end (the street is not opened through the block)
    info["show_area"] = round(back.area)
    return info


# ---------------------------------------------------------------- buildings: other styles
def stucco_block(ctx, poly, n=2, tower=False, wall="AD_ochre"):
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    ztop = zf + 4.2 + (n - 1) * 3.4
    for a, b, nrm in ring_edges(poly):
        N3 = np.array([*nrm, 0]); L = np.linalg.norm(b - a); e = (b - a) / L
        quad(M[wall], P3(a, zb), P3(b, zb), P3(b, ztop), P3(a, ztop), N3)
        if not ctx.is_front(a, b, nrm):
            continue
        nb = max(1, int(round(L / 3.4))); bw = L / nb
        for k in range(nb):
            c = a + e * (k + 0.5) * bw; w = min(1.6, bw - 1.0)
            if w < 0.7:
                continue
            door = k % 3 == 1
            arched_window(M["AD_roofred" if door else "AD_trim"], c - e * (w / 2 + 0.15), c + e * (w / 2 + 0.15), nrm, zf + (0.02 if door else 0.8), zf + 3.0 - w / 2, off=0.03)
            arched_window(M["AD_door" if door else "AD_glass"], c - e * w / 2, c + e * w / 2, nrm, zf + (0.02 if door else 0.8), zf + 2.9 - w / 2, off=0.05)
            for f in range(1, n):
                zz = zf + 4.2 + (f - 1) * 3.4
                arched_window(M["AD_glass"], c - e * 0.45, c + e * 0.45, nrm, zz + 0.5, zz + 2.2, off=0.05, n=4)
                box(M["AD_timberd"], P3(c, zz - 0.1) + N3 * 0.5, (min(1.2, bw / 2 - 0.2), 0.5, 0.06), B3(e, nrm))   # little balcony
        if L > 6:                                          # a striped awning over the ground floor (v1 0:15:06)
            quad(M["AD_umb_r"], P3(a + e * 0.4, zf + 3.4) + N3 * 0.05, P3(b - e * 0.4, zf + 3.4) + N3 * 0.05,
                 P3(b - e * 0.4 + nrm * 1.2, zf + 2.9), P3(a + e * 0.4 + nrm * 1.2, zf + 2.9), UP)
            ctx.lamp_spots.append((a + b) / 2 + nrm * 3.0)
    cap(M["AD_ochre"], poly, ztop)
    hip_strip(M["AD_roofred"], M["AD_roofred"], poly, ztop, 3.0, 2.0, out=0.6)
    if tower:
        c, u, v, hu, hv = rect_of(poly)
        q = c + u * (hu - 3.0) + v * (hv - 3.0)
        if not poly.buffer(-0.5).contains(Point(*q)):
            q = np.array(poly.buffer(-2.5).representative_point().coords[0])
        loft_rect(M[wall], P3(q, zf), u, v, [(2.2, 2.2, 0), (2.2, 2.2, ztop - zf + 5.0)])
        for s in (1, -1):
            for ax, bx in ((u, v), (v, u)):
                arched_window(M["AD_glass"], q + ax * s * 2.2 - bx * 0.5, q + ax * s * 2.2 + bx * 0.5, ax * s, ztop + 2.4, ztop + 3.8, off=0.03)
        box(M["AD_timberd"], P3(q, ztop + 5.0), (2.6, 2.6, 0.12), (np.r_[u, 0], np.r_[v, 0], UP))
        loft_rect(M["AD_roofred"], P3(q, ztop + 5.1), u, v, [(2.8, 2.8, 0), (0.15, 0.15, 2.4)])
    return round(ztop, 1)


def timber_block(ctx, poly, roof="AD_roofred", wall="AD_timber", n=1, open_front=False, stall=False, h=None):
    """Timber shops and stalls: boards with green corner posts and trim, windows or an open counter, a hip roof."""
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    H = h or (3.4 if stall else 4.0 + (n - 1) * 3.2)
    for a, b, nrm in ring_edges(poly):
        N3 = np.array([*nrm, 0]); L = np.linalg.norm(b - a); e = (b - a) / L
        front = ctx.is_front(a, b, nrm)
        if stall and front and L > 1.5:
            quad(M[wall], P3(a, zb), P3(b, zb), P3(b, zf + 1.05), P3(a, zf + 1.05), N3)
            quad(M["AD_glass"], P3(a, zf + 1.05), P3(b, zf + 1.05), P3(b, zf + 2.4), P3(a, zf + 2.4), N3)
            quad(M[wall], P3(a, zf + 2.4), P3(b, zf + 2.4), P3(b, zf + H), P3(a, zf + H), N3)
            box(M["AD_tgreen"], P3((a + b) / 2, zf + 1.05) + N3 * 0.2, (L / 2, 0.25, 0.05), B3(e, nrm))
        else:
            quad(M[wall], P3(a, zb), P3(b, zb), P3(b, zf + H), P3(a, zf + H), N3)
            if front and L > 2.5 and not stall:
                nb = max(1, int(L // 3.0)); bw = L / nb
                for k in range(nb):
                    c = a + e * (k + 0.5) * bw
                    quad(M["AD_glass"], P3(c - e * 0.6, zf + 0.9) + N3 * 0.04, P3(c + e * 0.6, zf + 0.9) + N3 * 0.04,
                         P3(c + e * 0.6, zf + 2.6) + N3 * 0.04, P3(c - e * 0.6, zf + 2.6) + N3 * 0.04, N3)
                    box(M["AD_tgreen"], P3(c, zf + 2.7) + N3 * 0.06, (0.75, 0.06, 0.08), B3(e, nrm))
                    for f in range(1, n):
                        zz = zf + 4.0 + (f - 1) * 3.2
                        quad(M["AD_glass"], P3(c - e * 0.5, zz + 0.6) + N3 * 0.04, P3(c + e * 0.5, zz + 0.6) + N3 * 0.04,
                             P3(c + e * 0.5, zz + 2.1) + N3 * 0.04, P3(c - e * 0.5, zz + 2.1) + N3 * 0.04, N3)
        box(M["AD_tgreen"], P3(a, (zb + zf + H) / 2), (0.1, 0.1, (zf + H - zb) / 2))
        box(M["AD_tgreen"], P3((a + b) / 2, zf + H - 0.1) + N3 * 0.05, (L / 2, 0.05, 0.12), B3(e, nrm))
    c, u, v, hu, hv = rect_of(poly)
    if poly.area < 60 or poly.area / (4 * hu * hv) > 0.85:
        rh = min(2.2, 0.55 * hv + 0.5)
        loft_rect(M[roof], P3(c, zf + H), u, v, [(hu + 0.5, hv + 0.5, 0.0), (max(hu - hv, 0.05) + 0.05, 0.05, rh)])
    else:
        cap(M[wall], poly, zf + H)
        hip_strip(M[roof], M[roof], poly, zf + H, 3.0, 1.8, out=0.5)
    return round(zf + H, 1)


def thatch_roof_rect(M, c, u, v, hu, hv, z, rh, mat="AD_thatch"):
    loft_rect(M[mat], P3(c, z), u, v, [(hu + 0.7, hv + 0.7, 0.0), (hu + 0.55, hv + 0.55, 0.25), (max(hu - hv, 0.05) + 0.1, 0.1, rh)])


def aframe(M, c, u, v, half_w, length, z0, h, face=1, carve=True, mat="AD_thatch"):
    """A steep A-frame roof: the ridge along u over c (length m), eaves at +-half_w along v; the gable at the +u end
    (face=1) carries a carved board (yellow with red and dark triangles, the tiki faces by ESTIMATE)."""
    c = np.asarray(c, float); u = np.asarray(u, float); v = np.asarray(v, float)
    A0, A1 = P3(c - u * length / 2, z0 + h), P3(c + u * length / 2, z0 + h)
    for s in (1, -1):
        E0, E1 = P3(c - u * length / 2 + v * s * half_w, z0), P3(c + u * length / 2 + v * s * half_w, z0)
        quad(M[mat], E0, E1, A1, A0, np.array([*(v * s), 0.6]))
        quad(M["AD_thatchd"], E0 - UP * 0.35, E1 - UP * 0.35, E1, E0, np.array([*(v * s), 0.0]))
    gc = c + u * face * (length / 2 - 0.4)
    tri(M["AD_carvey"], P3(gc + v * half_w * 0.85, z0 + 0.2), P3(gc - v * half_w * 0.85, z0 + 0.2), P3(gc, z0 + h * 0.92), np.array([*(u * face), 0]))
    back = c - u * face * (length / 2 - 0.4)
    tri(M["AD_timberd"], P3(back + v * half_w * 0.85, z0 + 0.2), P3(back - v * half_w * 0.85, z0 + 0.2), P3(back, z0 + h * 0.92), np.array([*(-u * face), 0]))
    if carve:
        off = np.array([*(u * face), 0]) * 0.05
        for k in range(4):
            y0 = z0 + 0.6 + k * h * 0.2; w0 = half_w * 0.85 * (1 - (y0 - z0) / h) - 0.3
            if w0 < 0.4:
                break
            for j in np.linspace(-w0, w0, max(2, int(w0 * 1.4))):
                m = "AD_carve" if (k + int(j * 3)) % 2 else "AD_text"
                q = gc + v * j
                tri(M[m], P3(q - v * 0.22, y0) + off, P3(q + v * 0.22, y0) + off, P3(q, y0 + 0.5) + off, np.array([*(u * face), 0]))


def pagoda(M, q, z0, tiers=7, r0=3.4, r1=1.1, h=2.0):
    """The Tiki Room's tiered tower: a dark timber core with thatched skirts, a spike on top."""
    z = z0
    for k in range(tiers):
        r = r0 + (r1 - r0) * k / (tiers - 1)
        loft_rect(M["AD_timberd"], P3(q, z), (1, 0), (0, 1), [(r * 0.7, r * 0.7, 0), (r * 0.7, r * 0.7, h * 0.6)], cap=False)
        loft_rect(M["AD_thatch"], P3(q, z + h * 0.45), (1, 0), (0, 1), [(r + 0.5, r + 0.5, 0.0), (r * 0.6, r * 0.6, h * 0.55)])
        z += h * 0.95
    lathe(M["AD_timberd"], (q[0], q[1], z), [(0.35, 0), (0.25, 0.6), (0.06, 2.4), (0.0, 2.6)], n=6)
    return z


def station(ctx, poly):
    """17744012: the Jungle Cruise dock (ground floor) under the Western River Railroad station (upper floor)."""
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    Z1 = zf + 4.3; Z2 = Z1 + 3.4
    c, u, v, hu, hv = rect_of(poly)
    core = poly.buffer(-2.5, join_style=2)
    core = max(G._polys(core), key=lambda p: p.area) if not core.is_empty else poly
    for a, b, nrm in ring_edges(core):                      # the dock's walls behind the open front
        quad(M["AD_orange"], P3(a, zb), P3(b, zb), P3(b, Z1), P3(a, Z1), np.array([*nrm, 0]))
    cap(M["AD_floor"] if "AD_floor" in M else M["AD_timberd"], poly, zf)
    # the floor slab under the whole footprint (walkable), posts round the edge
    for a, b, nrm in ring_edges(poly):
        quad(M["AD_timberd"], P3(a, zb), P3(b, zb), P3(b, zf), P3(a, zf), np.array([*nrm, 0]))
        L = np.linalg.norm(b - a); e = (b - a) / L
        for t in np.arange(0.2, L, 2.8):
            p = a + e * t - nrm * 0.25
            box(M["AD_tgreen"], P3(p, (zf + Z1) / 2), (0.14, 0.14, (Z1 - zf) / 2))
            if t > 0.5:
                bar(M["AD_tgreen"], P3(p, Z1 - 0.9), P3(p - e * 0.8, Z1 - 0.05), w=0.05, d=0.05)
    slab_ = poly.buffer(0.3, join_style=2)
    cap(M["AD_timberd"], slab_, Z1); cap(M["AD_timberd"], slab_, Z1 - 0.3)
    sides(M["AD_tgreen"], slab_, Z1 - 0.3, Z1)
    # upper floor: the station house (inset) and the platform gallery with green railings
    house = poly.buffer(-3.2, join_style=2)
    house = max(G._polys(house), key=lambda p: p.area) if not house.is_empty else core
    for a, b, nrm in ring_edges(house):
        N3 = np.array([*nrm, 0]); L = np.linalg.norm(b - a); e = (b - a) / L
        quad(M["AD_timber"], P3(a, Z1), P3(b, Z1), P3(b, Z2), P3(a, Z2), N3)
        for t in np.arange(1.2, L - 0.8, 2.6):
            q = a + e * t
            quad(M["AD_glass"], P3(q - e * 0.5, Z1 + 0.9) + N3 * 0.04, P3(q + e * 0.5, Z1 + 0.9) + N3 * 0.04,
                 P3(q + e * 0.5, Z1 + 2.4) + N3 * 0.04, P3(q - e * 0.5, Z1 + 2.4) + N3 * 0.04, N3)
    for a, b, nrm in ring_edges(poly.buffer(0.15, join_style=2)):
        rail(ctx.M, a, b, Z1, h=1.05, step=0.35, mesh="AD_tgreen")
        L = np.linalg.norm(b - a); e = (b - a) / L
        for t in np.arange(0.2, L, 3.0):
            frustum(M["AD_tgreen"], P3(a + e * t, Z1), P3(a + e * t, Z2 + 0.3), 0.1, 0.1, n=6)
    hip_strip(M["AD_roofred"], M["AD_roofred"], poly, Z2 + 0.3, 3.5, 2.4, out=0.8)
    # the JUNGLE CRUISE gable on the west (plaza) face; the stairs with the railroad sign south of it (0:11:22, 0:11:40)
    west = min(ring_edges(poly), key=lambda t: ((t[0] + t[1]) / 2)[0] + 50 * (t[2][0] > -0.6))
    a, b, nrm = west
    m = (a + b) / 2; e = (b - a) / np.linalg.norm(b - a)
    g = m + nrm * 1.2
    aframe(M, g, np.array(nrm), e, 3.2, 3.0, Z1 - 0.2, 2.6, face=1, carve=False, mat="AD_roofred")
    tri(M["AD_orange"], P3(g + nrm * 1.3 + e * 2.9, Z1), P3(g + nrm * 1.3 - e * 2.9, Z1), P3(g + nrm * 1.3, Z1 + 2.3), np.array([*nrm, 0]))
    sc = P3(g + nrm * 1.4, Z1 + 0.9)
    plate(M["AD_sign"], shapely.affinity.scale(Point(0, 0).buffer(1, 20), 2.3, 0.6), sc, np.array([*e, 0]), UP, np.array([*nrm, 0]), t=0.06)
    plate(M["AD_signr"], text_poly("JUNGLE CRUISE", 0.42), sc, np.array([*e, 0]), UP, np.array([*nrm, 0]), off=0.03)
    for s in (1, -1):
        p = g + nrm * 1.2 + e * s * 2.6
        box(M["AD_tgreen"], P3(p, (zf + Z1) / 2), (0.16, 0.16, (Z1 - zf) / 2))
    # stairs up from the plaza to the platform, along the west face (ESTIMATE of their place)
    sp = a + e * 1.0 + nrm * 0.3
    nstep = int((Z1 - zf) / 0.18)
    for k in range(nstep):
        q = sp + nrm * (nstep - k) * 0.28
        box(M["AD_timber"], P3(q, zf + (k + 0.5) * 0.18 - (0.09 if k else 0)), (0.14, 0.14 + 0 * k, 0.09 + (k * 0.18 / 2 if k == 0 else 0)),
            (np.array([*nrm, 0]), np.array([*e, 0]), UP))
        box(M["AD_timber"], P3(q + e * 0.8, zf + (k + 1) * 0.18 - 0.09), (0.14, 0.8, 0.09), (np.array([*nrm, 0]), np.array([*e, 0]), UP))
    top = sp + nrm * 0.0; bot = sp + nrm * (nstep + 1) * 0.28
    for s in (0.0, 1.6):
        bar(M["AD_tgreen"], P3(bot + e * s, zf + 1.0), P3(top + e * s, Z1 + 1.0), w=0.05, d=0.05)
        for k in range(0, nstep, 3):
            q = sp + nrm * (nstep - k) * 0.28 + e * s
            bar(M["AD_tgreen"], P3(q, zf + (k + 1) * 0.18), P3(q, zf + (k + 1) * 0.18 + 1.0), w=0.04, d=0.04)
    sc2 = P3(sp + e * 0.8 + nrm * 0.1, Z1 + 1.9) + np.array([*nrm, 0]) * 0.2
    plate(M["AD_timberd"], shapely.affinity.scale(Point(0, 0).buffer(1, 16), 1.9, 0.55), sc2, np.array([*e, 0]), UP, np.array([*nrm, 0]), t=0.06)
    plate(M["AD_sign"], text_poly("WESTERN RIVER RAILROAD", 0.2), sc2, np.array([*e, 0]), UP, np.array([*nrm, 0]), off=0.03)
    # the queue under the roof: green-railed switchbacks (0:11:58)
    for k, t in enumerate(np.linspace(-hv + 1.2, hv - 1.2, 4)):
        p0 = c - u * (hu - 1.0) + v * t; p1 = c + u * (hu - 3.0) + v * t
        if poly.contains(Point(*p0)) and poly.contains(Point(*p1)):
            rail(M, p0, p1, zf, h=0.95, step=1.2, mesh="AD_tgreen")
    return dict(floor=round(zf, 2), platform=round(Z1, 2))


def tiki_room(ctx, poly):
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    H = 4.2
    for a, b, nrm in ring_edges(poly):
        quad(M["AD_timberd"], P3(a, zb), P3(b, zb), P3(b, zf + H), P3(a, zf + H), np.array([*nrm, 0]))
        L = np.linalg.norm(b - a); e = (b - a) / L
        for t in np.arange(0.0, L, 3.0):
            box(M["AD_timber"], P3(a + e * t, (zb + zf + H) / 2), (0.16, 0.16, (zf + H - zb) / 2))
    cap(M["AD_thatchd"], poly, zf + H)
    inner, zr = hip_strip(M["AD_thatch"], M["AD_thatchd"], poly, zf + H, 4.0, 3.6, out=0.9)
    q = np.array([-252.0, 708.0])
    if not poly.buffer(-3).contains(Point(*q)):
        q = np.array(poly.buffer(-4).representative_point().coords[0])
    ztop = pagoda(M, q, zr - 0.5)
    # the A-frame entrance on the plaza side (v1 0:16:42): the front edge nearest the plaza's middle
    best = max((t for t in ring_edges(poly) if np.linalg.norm(t[1] - t[0]) > 5 and ctx.is_front(*t)),
               key=lambda t: -np.linalg.norm((t[0] + t[1]) / 2 - np.array([-275.0, 735.0])), default=None)
    if best:
        a, b, nrm = best
        m = (a + b) / 2; e = (b - a) / np.linalg.norm(b - a)
        aframe(M, m + nrm * 1.0, nrm, e, 3.6, 6.0, zf + 2.6, 5.6, face=1)
        for s in (1, -1):
            box(M["AD_carve"], P3(m + nrm * 3.6 + e * s * 2.6, zf + 1.35), (0.25, 0.25, 1.35))
            lathe(M["AD_carvey"], (*(m + nrm * 3.6 + e * s * 2.6), zf + 2.7), [(0.35, 0), (0.25, 0.4), (0, 0.5)], n=6)
        sc = P3(m + nrm * 3.9, zf + 3.4)
        plate(M["AD_timberd"], sbox(-2.4, -0.35, 2.4, 0.35), sc, np.array([*e, 0]), UP, np.array([*nrm, 0]), t=0.06)
        plate(M["AD_carvey"], text_poly("ENCHANTED TIKI ROOM", 0.3), sc, np.array([*e, 0]), UP, np.array([*nrm, 0]), off=0.03)
        ctx.tiki_front = m + nrm * 7.0
    return dict(floor=round(zf, 2), tower_top=round(ztop, 1), gable=None if best is None else [round(float(v), 1) for v in (best[0] + best[1]) / 2])


def poly_terrace(ctx, poly):
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    H = 3.8
    for a, b, nrm in ring_edges(poly):
        N3 = np.array([*nrm, 0]); L = np.linalg.norm(b - a); e = (b - a) / L
        quad(M["AD_timber"], P3(a, zb), P3(b, zb), P3(b, zf + 1.0), P3(a, zf + 1.0), N3)
        quad(M["AD_glass"], P3(a, zf + 1.0) - N3 * 0.6, P3(b, zf + 1.0) - N3 * 0.6, P3(b, zf + H) - N3 * 0.6, P3(a, zf + H) - N3 * 0.6, N3)
        for t in np.arange(0.0, L, 3.2):
            box(M["AD_timberd"], P3(a + e * t, zf + H / 2), (0.18, 0.18, H / 2))
    cap(M["AD_timber"], poly, zf + 1.0)
    inner, zr = hip_strip(M["AD_thatch"], M["AD_thatchd"], poly, zf + H, 7.0, 6.5, out=1.2)
    c, u, v, hu, hv = rect_of(poly)
    aframe(M, c, u, v, min(hv, 8.0), 2 * hu * 0.8, zr - 0.6, 5.5, face=-1)
    sc = P3(c - u * (hu * 0.8), zr + 1.0) - np.array([*u, 0]) * 0.1
    plate(M["AD_timberd"], sbox(-2.6, -0.4, 2.6, 0.4), sc, np.array([*v, 0]) * -1, UP, np.array([*(-u), 0]), t=0.06)
    plate(M["AD_carvey"], text_poly("POLYNESIAN TERRACE", 0.32), sc, np.array([*v, 0]) * -1, UP, np.array([*(-u), 0]), off=0.03)
    return round(zr + 5, 1)


def trestle(ctx, poly):
    """The railway's trestle over the path (roof way 1116316886): a deck at 5 m on timber bents."""
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    zd = zf + 5.0
    slab_ = poly
    cap(M["AD_timberd"], slab_, zd + 0.6); cap(M["AD_timberd"], slab_, zd)
    sides(M["AD_timber"], slab_, zd, zd + 0.6)
    line = LineString([p for p in poly.minimum_rotated_rectangle.exterior.coords])
    ring = poly.exterior
    for d in np.arange(0, ring.length, 4.0):
        q = ring.interpolate(d)
        if ctx.pv.contains(q):
            continue
        frustum(M["AD_timberd"], (q.x, q.y, zb), (q.x, q.y, zd), 0.16, 0.16, n=6)
    for a, b, nrm in ring_edges(poly):
        rail(M, a, b, zd + 0.6, h=0.9, step=1.5, mesh="AD_timber")


def small_building(ctx, poly, zone, name_hint=""):
    if zone == "poly":
        c, u, v, hu, hv = rect_of(poly)
        zb, zf = floor_of(ctx, poly)
        timber_block(ctx, poly, roof="AD_thatch", wall="AD_timberd", stall=True, h=2.9)
        thatch_roof_rect(ctx.M, c, u, v, hu, hv, zf + 2.9, min(2.6, hv + 1.2))
        return "thatch stall"
    if zone in ("cobble", "sand") or poly.area < 30:
        timber_block(ctx, poly, roof="AD_roofred" if RNG.random() < 0.6 else "AD_thatch", wall=("AD_timber", "AD_orange", "AD_pgreen")[int(RNG.integers(3))], stall=True)
        return "stall"
    timber_block(ctx, poly, roof="AD_roofred", wall=("AD_timber", "AD_orange")[int(RNG.integers(2))], n=1)
    return "timber"


def boat_stack(M, q, z):
    """The red and white striped stack over the boat works (0:10:04)."""
    for k in range(6):
        frustum(M["AD_umb_r" if k % 2 == 0 else "AD_umb_w"], (q[0], q[1], z + k * 0.9), (q[0], q[1], z + (k + 1) * 0.9), 0.55, 0.55, n=10)
    lathe(M["AD_iron"], (q[0], q[1], z + 5.4), [(0.7, 0), (0.7, 0.2), (0.4, 0.5), (0, 0.55)], n=10)


def umbrella(M, x, y, z, r=1.4, h=2.4, mats=("AD_umb_o",), table=True):
    frustum(M["AD_iron"], (x, y, z), (x, y, z + h + 0.3), 0.03, 0.03, n=4)
    n = 8
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        tri(M[mats[k % len(mats)]], (x, y, z + h + 0.45), (x + r * math.cos(a0), y + r * math.sin(a0), z + h),
            (x + r * math.cos(a1), y + r * math.sin(a1), z + h), UP)
    if table:
        frustum(M["AD_table"], (x, y, z + 0.7), (x, y, z + 0.75), 0.45, 0.45, n=8)
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4
            px, py = x + 0.8 * math.cos(a), y + 0.8 * math.sin(a)
            box(M["AD_table"], (px, py, z + 0.45), (0.2, 0.2, 0.03))
            box(M["AD_table"], (px + 0.2 * math.cos(a), py + 0.2 * math.sin(a), z + 0.7), (0.03, 0.2, 0.25),
                (np.array([math.cos(a), math.sin(a), 0]), np.array([-math.sin(a), math.cos(a), 0]), UP))


# ---------------------------------------------------------------- street furniture and planting
def lamp(M, x, y, z):
    """A gas-lamp style post: a dark green fluted post, a lantern with a lit glass and a cap (New Orleans and the land)."""
    lathe(M["AD_lamp"], (x, y, z), [(0.16, 0.0), (0.16, 0.4), (0.1, 0.55), (0.065, 0.7), (0.055, 3.1), (0.12, 3.2), (0.0, 3.22)], n=8)
    box(M["AD_globe"], (x, y, z + 3.55), (0.17, 0.17, 0.3))
    loft_rect(M["AD_lamp"], (x, y, z + 3.85), (1, 0), (0, 1), [(0.26, 0.26, 0.0), (0.03, 0.03, 0.3)])


def bench(M, x, y, z, face):
    """A white cast-iron bench (the frames: all white, scrolled ends, slatted seat and back)."""
    f = np.array([face[0], face[1], 0.0]); r = np.array([face[1], -face[0], 0.0])
    P = lambda uu, vv, ww: np.array([x, y, z]) + uu * r + vv * f + ww * UP
    for s in (-0.8, 0.8):
        box(M["AD_bench"], P(s, 0.0, 0.42), (0.04, 0.28, 0.42), (r, f, UP))
    for vv in (0.16, 0.04, -0.08):
        box(M["AD_bench"], P(0, vv, 0.45), (0.86, 0.05, 0.02), (r, f, UP))
    for ww in (0.62, 0.78, 0.94):
        box(M["AD_bench"], P(0, -0.2, ww), (0.86, 0.02, 0.05), (r, f, UP))


def fern(M, x, y, z, s=1.0, mat="AD_fern", n=6, rot=0.0):
    """A fern / big-leaf clump: n long leaves arching out from the centre (two triangles each)."""
    for k in range(n):
        a = rot + 2 * math.pi * k / n
        d = np.array([math.cos(a), math.sin(a)]); w = np.array([-d[1], d[0]])
        base = np.array([x, y, z])
        mid = base + np.r_[d * 0.45 * s, 0.55 * s]
        tip = base + np.r_[d * 0.9 * s, 0.2 * s]
        tri(M[mat], base, mid + np.r_[w * 0.13 * s, 0], mid - np.r_[w * 0.13 * s, 0], UP)
        tri(M[mat], mid + np.r_[w * 0.13 * s, 0], tip, mid - np.r_[w * 0.13 * s, 0], UP)


def flower_clump(M, x, y, z, mat, s=1.0):
    """A clump of bedding flowers: a dark leaf cushion with a flat coloured top (octahedron-like)."""
    r = 0.2 * s
    pts = [(x + r * math.cos(2 * math.pi * k / 6), y + r * math.sin(2 * math.pi * k / 6), z + 0.24 * s) for k in range(6)]
    for k in range(6):
        tri(M["AD_leaf"], (x, y, z), pts[k], pts[(k + 1) % 6], np.array([pts[k][0] - x, pts[k][1] - y, -0.2]))
        tri(M[mat], (x, y, z + 0.32 * s), pts[k], pts[(k + 1) % 6], UP)


def bamboo_fence(M, line, z_of, h=1.0, rustic=False):
    L = line.length
    if L < 1.0:
        return
    mat = "AD_rust" if rustic else "AD_bamboo"
    step = 1.8 if rustic else 0.22
    for d in np.arange(0.0, L, step):
        q = line.interpolate(d); z = z_of(q.x, q.y)
        hh = h * (1.0 + (0.12 * math.sin(d * 7.1) if not rustic else 0.0))
        frustum(M[mat], (q.x, q.y, z - 0.1), (q.x, q.y, z + hh), 0.04 if not rustic else 0.07, 0.04 if not rustic else 0.06, n=4, caps=False)
    cs = list(line.coords)
    for (xa, ya), (xb, yb) in zip(cs[:-1], cs[1:]):
        za, zb = z_of(xa, ya), z_of(xb, yb)
        for hh in ((0.35, 0.8) if not rustic else (0.45, 0.9)):
            bar(M[mat], (xa, ya, za + hh), (xb, yb, zb + hh), w=0.035, d=0.035)


def stitch_ship(M, x, y, z, face):
    """Stitch's red spaceship (the Tiki Room's garden, 0:12:40): a red pod with a nose, fins and a blue canopy."""
    f = np.array([face[0], face[1], 0.3]); f /= np.linalg.norm(f)
    base = np.array([x, y, z + 0.9])
    frustum(M["AD_stitch"], base - f * 1.3, base + f * 0.6, 0.55, 0.75, n=10)
    frustum(M["AD_stitch"], base + f * 0.6, base + f * 1.9, 0.75, 0.05, n=10)
    sphere(M["AD_umb_t"], base + f * 0.2 + UP * 0.6, 0.42, n=8, m=5)
    r = np.cross(f, UP); r /= np.linalg.norm(r)
    for s in (1, -1):
        tri(M["AD_stitch"], base - f * 1.0, base - f * 0.2, base - f * 1.4 + r * s * 1.2 - UP * 0.3, UP)
    frustum(M["AD_rock"], (x, y, z), (x, y, z + 0.5), 0.8, 0.5, n=7)


def planting(ctx, ribs, inners, gr_z):
    """Flowers, ferns and big-leaf fans on the beds' soil ribbons; taller fans poking out of the shrub masses."""
    M = ctx.M; count = 0
    palettes = {"green": ("AD_fl_red", "AD_fl_pink", "AD_fl_wht", "AD_fl_yel", "AD_fl_org"),
                "street": ("AD_fl_red", "AD_fl_pink", "AD_fl_wht", "AD_fl_pur"),
                "poly": ("AD_fl_red", "AD_fl_org", "AD_fl_yel", "AD_fl_pink"),
                "sand": ("AD_fl_red", "AD_fl_org", "AD_fl_yel"), "cobble": ("AD_fl_red", "AD_fl_yel")}
    for rib, zone in ribs:
        pal = palettes.get(zone, palettes["green"])
        for p in G._polys(rib):
            mid = p.buffer(-0.18)
            lines = [g for g in G._polys(mid)] or [p]
            for g in lines:
                ring = g.exterior
                run_col = pal[int(RNG.integers(len(pal)))]; run_left = 0
                for d in np.arange(0.0, ring.length, 0.62):
                    q = ring.interpolate(d); z = gr_z(q.x, q.y) + CURB_H - 0.06
                    if run_left <= 0:
                        run_col = pal[int(RNG.integers(len(pal)))]; run_left = int(RNG.integers(4, 12))
                    run_left -= 1
                    k = RNG.random()
                    if k < 0.58:
                        flower_clump(M, q.x, q.y, z, run_col, s=RNG.uniform(0.8, 1.2))
                    elif k < 0.85:
                        fern(M, q.x, q.y, z, s=RNG.uniform(0.55, 0.9), rot=RNG.uniform(0, 6.3))
                    else:
                        fern(M, q.x, q.y, z, s=RNG.uniform(0.9, 1.3), mat="AD_leafr" if zone in ("poly", "sand") or RNG.random() < 0.3 else "AD_leaf", n=7, rot=RNG.uniform(0, 6.3))
                    count += 1
    for inner, zone in inners:
        for p in G._polys(inner):
            n = int(p.area / 5.0)
            x0, y0, x1, y1 = p.bounds
            for _ in range(n):
                q = Point(RNG.uniform(x0, x1), RNG.uniform(y0, y1))
                if not p.contains(q):
                    continue
                z = gr_z(q.x, q.y) + CURB_H + 0.5
                if RNG.random() < 0.5:
                    fern(M, q.x, q.y, z, s=RNG.uniform(1.2, 1.7), mat="AD_leafr" if RNG.random() < 0.3 else "AD_leaf", n=7, rot=RNG.uniform(0, 6.3))
                else:
                    flower_clump(M, q.x, q.y, z + 0.1, FLOWERS[int(RNG.integers(len(FLOWERS)))], s=1.3)
                count += 1
    return count


def build():
    P, T, gm, beds, ginfo = build_ground()
    info = dict(ground=ginfo)
    # ground surface for the buildings: this model's triangles + the plaza's and the Land's
    tris = [np.array(m.tris) for k, m in gm.items() if m.tris and k not in ("AG_edge", "AG_kerb") ]
    own = np.concatenate([t.reshape(-1, 3, 3) for t in tris])
    bb = BOX.buffer(30).bounds
    others = [load_tris(MODELS / "tdl_plaza_ground.json", lambda n: n != "TP_edge", bb),
              load_tris(MODELS / "tdl_land_ground.json", lambda n: n != "TL_edge", bb)]

    class GrS:
        def __init__(self):
            self.a = Surface(own); self.b = Surface(np.concatenate(others))

        def z(self, x, y):
            v = self.a.z(x, y)
            if v is None:
                v = self.b.z(x, y)
            if v is None:
                return float(T.z(x, y))
            return float(v)

        def span(self, poly, out=1.0):
            ring = poly.buffer(out, join_style=2).exterior
            zs = [self.z(*ring.interpolate(d).coords[0]) for d in np.arange(0, ring.length, 2.0)]
            return min(zs), max(zs)

    gr = GrS()
    M = {n: G.Mesh(n) for n in B_NAMES}
    ctx = Ctx(M, gr, P["paving"])
    ctx.bld = P["buildings"]
    ctx.tiki_front = None
    taken = unary_union([g for g in (GR.model_footprint(m) for m in ("tdl_plaza_hub", "tdl_plaza_buildings", "tdl_world_bazaar")) if g is not None])
    items = []
    for w in DL.DATA["ways"]:
        if "building" in w["tags"] and w["closed"] and len(w["pts"]) >= 4:
            items.append((w["id"], w["tags"], Polygon(w["pts"]).buffer(0)))
    for r in DL.DATA["relations"]:
        if "building" in r["tags"]:
            rings = DL.outer_rings(r)
            if rings:
                items.append((r["id"], r["tags"], Polygon(rings[0]).buffer(0)))
    done, styles = [], {}
    region = BOX.difference(JUNGLE)
    for oid, tags, poly in items:
        if poly.is_empty or poly.area < 2.0 or not region.contains(poly.centroid) or DL.MODEL_KEYS.get(oid, "dladv") != "dladv":
            continue
        if taken.intersection(poly).area > 0.3 * poly.area:
            continue
        if DL.land_of_name(tags.get("name", "")) not in (None, 1):
            continue
        zone = zone_of(poly)
        roof_only = tags.get("building") == "roof"
        try:
            if oid == PIRATES:
                styles[oid] = pirates(ctx, poly)
            elif oid == STATION:
                styles[oid] = station(ctx, poly)
            elif oid == TIKI:
                styles[oid] = tiki_room(ctx, poly)
            elif oid == POLY_T:
                styles[oid] = poly_terrace(ctx, poly)
            elif oid == TRESTLE:
                trestle(ctx, poly); styles[oid] = "trestle"
            elif oid in SHOW:
                zb, zf = floor_of(ctx, poly)
                h = 14.0 if poly.area > 1000 else 5.0
                sides(M["AD_show"], poly, zb, zf + h); cap(M["AD_showroof"], poly, zf + h); styles[oid] = "show"
            elif oid in (BAZAAR, CHINA):
                styles[oid] = ("stucco", stucco_block(ctx, poly, n=2, tower=True))
            elif oid == BAZAAR2:
                styles[oid] = ("stucco", stucco_block(ctx, poly, n=1))
            elif oid == THEATRE:
                styles[oid] = nola_block(ctx, poly, n=2, sh=3.4, colours=("AD_pgreen", "AD_yellow"), back="AD_pgreen", galleries=False)
            elif roof_only:
                c, u, v, hu, hv = rect_of(poly)
                zb, zf = floor_of(ctx, poly)
                if poly.area < 7:
                    umbrella(M, c[0], c[1], zf, r=max(1.0, math.sqrt(poly.area / math.pi) + 0.3), mats=("AD_umb_o", "AD_umb_w"))
                    styles[oid] = "umbrella"
                else:
                    for su in (-1, 1):
                        for sv in (-1, 1):
                            p = c + su * (hu - 0.2) * u + sv * (hv - 0.2) * v
                            frustum(M["AD_timberd"], P3(p, zb), P3(p, zf + 2.8), 0.1, 0.1, n=6)
                    (thatch_roof_rect if zone == "poly" else (lambda M_, c_, u_, v_, hu_, hv_, z_, rh_: loft_rect(M_["AD_canvas"], P3(c_, z_), u_, v_, [(hu_ + 0.3, hv_ + 0.3, 0), (max(hu_ - hv_, 0.05), 0.05, rh_)])))(M, c, u, v, hu, hv, zf + 2.8, 1.2)
                    styles[oid] = "canopy"
            elif poly.area < 120:
                styles[oid] = small_building(ctx, poly, zone)
            else:
                if zone == "poly":
                    styles[oid] = small_building(ctx, poly, zone)
                elif poly.centroid.y > 820 or poly.centroid.x < -345:
                    styles[oid] = nola_block(ctx, poly, n=2, galleries=True)
                else:
                    styles[oid] = ("timber", timber_block(ctx, poly, n=2))
            done.append(oid)
        except Exception as ex:          # keep going; the draft box stays for this one
            styles[oid] = f"FAILED {ex!r}"[:120]
    info["buildings"] = len(done)
    info["styles"] = {k: (v if isinstance(v, str) else "ok") for k, v in styles.items()}
    info["tiki"] = styles.get(TIKI)
    # boat works stack and flag pergola (0:10:04, ESTIMATE of their places)
    bw = Point(-306.0, 790.0)
    boat_stack(M, (bw.x, bw.y), gr.z(bw.x, bw.y) + 4.2)
    pg0, pg1 = np.array([-298.5, 797.0]), np.array([-289.0, 806.5])
    if P["paving"].buffer(0.5).contains(LineString([pg0, pg1])):
        zp = gr.z(*((pg0 + pg1) / 2))
        e = (pg1 - pg0) / np.linalg.norm(pg1 - pg0); n = np.array([-e[1], e[0]])
        for t in np.linspace(0, 1, 4):
            for s in (-1.6, 1.6):
                q = pg0 + (pg1 - pg0) * t + n * s
                frustum(M["AD_timberd"], P3(q, zp - 0.2), P3(q, zp + 3.2), 0.1, 0.1, n=6)
        for s in (-1.6, 1.6):
            bar(M["AD_timberd"], P3(pg0 + n * s, zp + 3.2), P3(pg1 + n * s, zp + 3.2), w=0.09, d=0.09)
        for t in np.linspace(0, 1, 8):
            q = pg0 + (pg1 - pg0) * t
            bar(M["AD_timber"], P3(q - n * 2.0, zp + 3.35), P3(q + n * 2.0, zp + 3.35), w=0.06, d=0.06)
        for k in range(3):                                   # strings of pennants
            a3, b3 = P3(pg0 + n * (k - 1) * 1.4, zp + 3.3), P3(pg1 + n * (k - 1) * 1.4, zp + 3.3)
            for j in range(14):
                q = a3 + (b3 - a3) * (j + 0.5) / 14 - UP * 0.25 * math.sin(math.pi * (j + 0.5) / 14)
                tri(M[("AD_flag1", "AD_flag2", "AD_flag3")[j % 3]], q + np.r_[e * 0.2, 0], q - np.r_[e * 0.2, 0], q - UP * 0.35, np.r_[n, 0])
        info["pergola"] = True
    # umbrellas: Cafe Orleans terrace (red / white), the Jungle Cruise front (terracotta), the Pirates front (teal)
    pv = P["paving"].buffer(-1.2)
    blocked = P["buildings"].buffer(1.5)
    def free(x, y):
        return pv.contains(Point(x, y)) and not blocked.contains(Point(x, y))
    n_umb = 0
    for x in np.arange(-369.0, -346.0, 3.4):
        for y in np.arange(817.0, 833.0, 3.4):
            if free(x, y):
                umbrella(M, x, y, gr.z(x, y), r=1.3, mats=("AD_umb_r", "AD_umb_w")); n_umb += 1
    for x, y in ((-262, 776), (-257, 769), (-267, 768), (-262, 761), (-270, 780)):
        if free(x, y):
            umbrella(M, x, y, gr.z(x, y), r=1.9, h=2.6, mats=("AD_umb_o",)); n_umb += 1
    for x, y in ((-386, 829), (-378, 827), (-370, 824)):
        if free(x, y):
            umbrella(M, x, y, gr.z(x, y), r=1.5, mats=("AD_umb_t", "AD_umb_w"), table=False); n_umb += 1
    info["umbrellas"] = n_umb
    # lamps (along the facades, and along the beds elsewhere)
    lamps = []
    for q in ctx.lamp_spots:
        if free(*q) and all(np.hypot(q[0] - a, q[1] - b) > 6 for a, b in lamps):
            lamps.append((q[0], q[1]))
    benches = []
    for rib, zone in beds["ribs"]:
        for p in G._polys(rib):
            outer = p.buffer(CURB_W + 0.02).exterior if p.area > 0 else None
    bed_polys = [q for q in P["beds"]]
    for q in bed_polys:
        ring = q.buffer(0.75, join_style=2).exterior
        zone = zone_of(q)
        for d in np.arange(3.0, ring.length - 2.0, 11.0):
            s = ring.interpolate(d)
            s2 = ring.interpolate(d + 0.5)
            t = np.array([s2.x - s.x, s2.y - s.y]); t /= (np.linalg.norm(t) or 1)
            nrm = np.array([t[1], -t[0]])
            if q.contains(Point(s.x + nrm[0] * 1.0, s.y + nrm[1] * 1.0)):
                nrm = -nrm
            if not free(s.x + nrm[0] * 0.3, s.y + nrm[1] * 0.3) and not pv.buffer(0.9).contains(s):
                continue
            if zone in ("green", "sand", "street") and len(benches) < 90 and d % 22 < 11 and q.area > 12:
                if all(np.hypot(s.x - a, s.y - b) > 5 for a, b, _ in benches):
                    benches.append((s.x, s.y, nrm))
            elif all(np.hypot(s.x - a, s.y - b) > 12 for a, b in lamps) and q.area > 6:
                lamps.append((s.x, s.y))
    for x, y in lamps:
        lamp(M, x, y, gr.z(x, y))
    for k, (x, y, nrm) in enumerate(benches):
        bench(M, x, y, gr.z(x, y), nrm)
        if k % 3 == 0:
            e = np.array([-nrm[1], nrm[0]])
            bx, by = x + e[0] * 1.4, y + e[1] * 1.4
            zb_ = gr.z(bx, by)
            loft_rect(M["AD_bin"], (bx, by, zb_), (1, 0), (0, 1), [(0.3, 0.3, 0), (0.3, 0.3, 0.95)])
            loft_rect(M["AD_timberd"], (bx, by, zb_ + 0.95), (1, 0), (0, 1), [(0.34, 0.34, 0), (0.1, 0.1, 0.2)])
    info["lamps"], info["benches"] = len(lamps), len(benches)
    # pots with flowers at the New Orleans doors
    n_pots = 0
    for a, b in ctx.pot_spots:
        for q in (a, b):
            if free(*q) or pv.buffer(1.0).contains(Point(*q)):
                z = gr.z(*q)
                lathe(M["AD_pot"], (q[0], q[1], z), [(0.18, 0), (0.3, 0.45), (0.33, 0.5), (0.0, 0.5)], n=8)
                fern(M, q[0], q[1], z + 0.45, s=0.55, mat="AD_leaf", n=6)
                flower_clump(M, q[0], q[1], z + 0.5, FLOWERS[n_pots % 3], s=0.9); n_pots += 1
    info["pots"] = n_pots
    # fences: bamboo along the beds of the street past the arch (the jungle path), rustic rails round the Polynesian beds;
    # lava rocks along the Polynesian beds
    n_f = 0
    for q in bed_polys:
        zone = zone_of(q)
        if zone not in ("street", "poly") or q.area < 8:
            continue
        qi = G._polys(q.buffer(-0.12, join_style=2))
        if not qi:
            continue
        ring = max(qi, key=lambda g: g.area).exterior
        pieces = ring.difference(P["buildings"].buffer(1.0))
        for ls in getattr(pieces, "geoms", [pieces]):
            if ls.geom_type == "LineString" and ls.length > 2.0:
                bamboo_fence(M, ls.simplify(0.2), lambda x, y: gr.z(x, y) + CURB_H, h=0.9 if zone == "street" else 0.85, rustic=zone == "poly")
                n_f += 1
        if zone == "poly":
            r2 = orient(q, 1.0).buffer(0.2).exterior
            for d in np.arange(0, r2.length, 1.6):
                s = r2.interpolate(d)
                sphere(M["AD_rock"], (s.x, s.y, gr.z(s.x, s.y) + 0.1), RNG.uniform(0.3, 0.55), n=5, m=3, sc=(1.3, 1.0, 0.6))
    info["fences"] = n_f
    # queue posts with ropes in front of the Jungle Cruise (0:11:22)
    st = [p for i, t, p in items if i == STATION]
    if st:
        sp = st[0]
        west = min(ring_edges(sp), key=lambda t: ((t[0] + t[1]) / 2)[0])
        a, b, nrm = west
        e = (b - a) / np.linalg.norm(b - a)
        for row in (5.0, 7.0):
            pts = [a + nrm * row + e * t for t in np.arange(0.0, np.linalg.norm(b - a), 1.8)]
            pts = [q for q in pts if free(*q) or pv.buffer(1).contains(Point(*q))]
            for q in pts:
                frustum(M["AD_post"], P3(q, gr.z(*q)), P3(q, gr.z(*q) + 1.0), 0.05, 0.05, n=6)
            for q0, q1 in zip(pts[:-1], pts[1:]):
                if np.linalg.norm(q1 - q0) < 2.0:
                    bar(M["AD_rope"], P3(q0, gr.z(*q0) + 0.85), P3(q1, gr.z(*q1) + 0.85), w=0.02, d=0.02)
        for k in range(5):                                       # barrels and crates by the gable
            q = a + e * (0.5 + 0.9 * k) + nrm * 2.2
            if not free(*q) and not pv.buffer(1).contains(Point(*q)):
                continue
            z = gr.z(*q)
            if k % 2:
                box(M["AD_timber"], P3(q, z + 0.3), (0.35, 0.3, 0.3))
            else:
                lathe(M["AD_rust"], (q[0], q[1], z), [(0.28, 0), (0.33, 0.45), (0.28, 0.9), (0, 0.9)], n=8)
    # Stitch's ship in the bed nearest the Tiki Room's gable
    if ctx.tiki_front is not None:
        near = min(bed_polys, key=lambda q: q.distance(Point(*ctx.tiki_front)))
        s = near.representative_point()
        stitch_ship(M, s.x, s.y, gr.z(s.x, s.y) + CURB_H, (1.0, 0.3))
        info["stitch"] = (round(s.x, 1), round(s.y, 1))
    info["plants"] = planting(ctx, beds["ribs"], beds["inners"], gr.z)
    return gm, M, info


def main():
    gm, M, info = build()
    MODELS.mkdir(parents=True, exist_ok=True)
    ng = G.write_gltf(OUT_G, {k: m for k, m in gm.items() if m.tris})
    nb = G.write_gltf(OUT_B, {k: m for k, m in M.items() if m.tris})
    print(f"[adventureland] {OUT_G.name} {OUT_G.stat().st_size / 1024:.0f} KB {ng} tris; {OUT_B.name} {OUT_B.stat().st_size / 1024:.0f} KB {nb} tris")
    for k, v in info.items():
        print(f"  {k}: {v}")
    big = sorted(((len(m.tris), k) for k, m in M.items()), reverse=True)[:12]
    print("  top meshes:", big)


if __name__ == "__main__":
    main()
