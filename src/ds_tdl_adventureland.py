"""アドベンチャーランド -- Adventureland of Tokyo Disneyland: New Orleans Square, the Adventureland plaza and bazaar, the
Jungle Cruise / Western River Railroad station and the Polynesian corner (video-frame plan, range 1; plain Python, Blender
is not needed; no night version; the only trees are the two palms by the Pirates, the rest are the page's OSM trees):

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
                     "AD_carve", "AD_carvey", "AD_table", "AD_stone",
                     # the photographed facades (Pirates, Cafe Orleans)
                     "AD_ashlar", "AD_mortar", "AD_tealdoor", "AD_signbr", "AD_flagblk", "AD_navy", "AD_dome", "AD_tan",
                     "AD_vroof", "AD_oblue", "AD_giron", "AD_black", "AD_louver", "AD_osalmon", "AD_odoor", "AD_awning",
                     "AD_ppanel", "AD_pshut", "AD_brickj", "AD_tan2", "AD_curtain", "AD_louverd", "AD_palmt", "AD_palml") + FLOWERS
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
    pa = Polygon(DL.WAYS[PIRATES]["pts"]).buffer(0)
    buildings = buildings.difference(pa).union(unary_union(pirates_parts(pa)))   # the straightened photo fronts
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
        self.lamp_spots, self.pot_spots, self.fixed_lamps = [], [], []
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


def nola_block(ctx, poly, n=3, sh=3.4, colours=PALETTE, back="AD_cream", galleries=True, cafe=False, roof=True, chimneys=True,
               custom=()):
    """custom: (a, b, fn) -- the edges lying on the line a-b are one photographed facade, fn(ctx, zb, zf, ztop) draws it."""
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    ztop = zf + 4.0 + (n - 1) * sh + 0.7
    fronts = 0
    done = set()

    def custom_of(a, b):
        for k, (p0, p1, fn) in enumerate(custom):
            seg = LineString([p0, p1])
            if seg.distance(Point(*a)) < 0.15 and seg.distance(Point(*b)) < 0.15:
                return k
        return None
    for a, b, nrm in ring_edges(poly):
        k = custom_of(a, b)
        if k is not None:
            if k not in done:
                done.add(k); custom[k][2](ctx, zb, zf, ztop); fronts += 1
            continue
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
            if L < 5 or not ctx.is_front(a, b, nrm) or custom_of(a, b) is not None:
                continue
            e = (b - a) / L
            for t in np.arange(2.5, L - 1.5, 4.5):
                p = a + e * t - nrm * 1.0
                B = B3(e, nrm)
                box(M["AD_trim"], P3(p, ztop + 0.9), (0.6, 0.6, 0.75), B)
                arched_window(M["AD_glass"], p - e * 0.35 + nrm * 0.6, p + e * 0.35 + nrm * 0.6, nrm, ztop + 0.45, ztop + 1.2, off=0.02, n=4)
                loft_rect(M["AD_slate"], P3(p, ztop + 1.65), e, nrm, [(0.75, 0.75, 0.0), (0.05, 0.6, 0.55)])
    return dict(fronts=fronts, top=round(ztop, 1))


def osm_pt(i):
    """A point of way 72865092 (the Pirates / Cafe Orleans way) by its index."""
    return V(DL.WAYS[PIRATES]["pts"][i])


def pirates_parts(poly_all):
    """Way 72865092 split into the main block and the Cafe Orleans lobe. OSM's jogs are kept (they are the real
    projections and set-backs); only the notch behind the Pirates gallery and the kink behind Cafe Orleans' awning are
    filled."""
    pts = DL.WAYS[PIRATES]["pts"]
    lobe = Polygon(pts[LOBE]).buffer(0).intersection(poly_all)
    lobe = max(G._polys(lobe), key=lambda p: p.area)
    rest = poly_all.difference(lobe.buffer(0.01))
    rest = max(G._polys(rest), key=lambda p: p.area)
    rest = straighten(rest, osm_pt(69), osm_pt(66), depth=3.0)
    lobe = straighten(lobe, osm_pt(40), osm_pt(37), depth=3.0)
    lobe = straighten(lobe, osm_pt(36), osm_pt(34), depth=3.0)
    rest = max(G._polys(rest.difference(lobe.buffer(0.01))), key=lambda p: p.area)
    return rest, lobe


def pirates(ctx, poly_all):
    """72865092: the Pirates group as separate photographed masses (pc_masses), a 12 m deep row of generic townhouse
    facades on the other public edges, the show building behind, the Cafe Orleans lobe as three houses."""
    M = ctx.M
    rest, lobe = pirates_parts(poly_all)
    fronts = [LineString([a, b]) for a, b, nrm in ring_edges(rest) if ctx.is_front(a, b, nrm)]
    strip = rest.intersection(unary_union([f.buffer(12.0, cap_style=2, join_style=2) for f in fronts]))
    strip = unary_union([p for p in G._polys(strip) if p.area > 20]).buffer(0.3).buffer(-0.3)
    masses = pc_masses(rest)
    back = rest.difference(strip.buffer(0.02)).difference(unary_union([m["poly"] for m in masses]).buffer(0.05))
    zb, zf = floor_of(ctx, unary_union([m["poly"] for m in masses]))
    for m in masses:
        draw_mass(ctx, m, masses, zb, zf)
    info = {"masses": {m["name"]: round(m["poly"].area) for m in masses}}
    taken = unary_union([m["poly"] for m in masses]).buffer(0.05)
    for p in G._polys(strip.difference(taken)):
        if p.area > 20:
            info.setdefault("front", []).append(nola_block(ctx, p, n=2, sh=3.6))   # 2 storeys + galleries (v2 0:07:48 right)
    zb2, zf2 = floor_of(ctx, rest)
    for p in G._polys(back):
        if p.area < 5:
            continue
        sides(M["AD_show"], p, zb2, zf2 + 6.0)           # hidden behind the facades (sky over the Pirates in v2 0:07:48)
        cap(M["AD_showroof"], p, zf2 + 6.0)
    # Cafe Orleans: three houses split at OSM's corners 40 and 37 (co1-3): the blue one and the cream one 3 storeys,
    # the salmon one 2 storeys under a slate roof, 1.4 m forward of the cream one
    Fc, Fs = Face(*co_line("cream")), Face(*co_line("salmon"))
    p40, p37 = osm_pt(40), osm_pt(37)
    west = Polygon([p40 + Fc.n * 30, p40 - Fc.n * 30, p40 - Fc.n * 30 - Fc.e * 40, p40 + Fc.n * 30 - Fc.e * 40])
    east = Polygon([p37 + Fs.n * 30, p37 - Fs.n * 30, p37 - Fs.n * 30 + Fs.e * 40, p37 + Fs.n * 30 + Fs.e * 40])
    big = lambda g: max(G._polys(g), key=lambda p: p.area)
    blue_p, sal_p = big(lobe.intersection(west)), big(lobe.intersection(east).difference(west))
    cream_p = big(lobe.difference(west).difference(east))
    info["cafe"] = [
        nola_block(ctx, blue_p, n=3, sh=3.4, colours=("AD_oblue",), back="AD_oblue", galleries=False, custom=((*co_line("blue"), co_blue),)),
        nola_block(ctx, cream_p, n=3, sh=3.4, colours=("AD_cream",), back="AD_cream", galleries=False, custom=((*co_line("cream"), co_cream),)),
        nola_block(ctx, sal_p, n=2, sh=3.6, colours=("AD_osalmon",), back="AD_osalmon", galleries=False, custom=((*co_line("salmon"), co_salmon),))]
    info["show_area"] = round(back.area)
    return info


# ---------------------------------------------------------------- photo facades: Pirates of the Caribbean, Cafe Orleans
# (images/pirates_caribbean/pc1-3, images/cafe_orleans/co1-3, and three more photos seen in the conversation only: the
# Pirates front straight on, an older wide view, a close view of the entrance). OSM's jagged fronts are straightened to
# these lines (plan, a -> b with the street on the right hand). Sizes are read off the photos with people (~1.65 m) for
# scale: ESTIMATES. Everything has depth: openings are holes in the wall with reveals, pilasters, bands, cornices on
# modillions, keystones, rusticated blocks one by one, louvred shutters, cast-iron lace as a pierced pattern.
class Face:
    """A straight facade a -> b (plan) with its outward normal: points by (s along, d out, z)."""
    def __init__(self, a, b):
        self.a, self.b = V(a), V(b)
        self.L = float(np.linalg.norm(self.b - self.a))
        self.e = (self.b - self.a) / self.L
        self.n = np.array([self.e[1], -self.e[0]])
        self.E, self.N = np.r_[self.e, 0.0], np.r_[self.n, 0.0]
        self.B = (self.E, self.N, UP)

    def p(self, s, d=0.0):
        return self.a + self.e * s + self.n * d

    def P(self, s, z, d=0.0):
        return P3(self.p(s, d), z)

    def box(self, mesh, s, z, d, hs, hd, hz):
        """A box centred at (s, d, z) with half sizes along / out / up."""
        box(mesh, self.P(s, z, d), (hs, hd, hz), self.B)

    def plate(self, mesh, shape, d=0.0, t=0.0):
        """A shape drawn in (s, z) facade coordinates on the plane d out of the wall (t: thickness behind it)."""
        plate(mesh, shape, self.P(0.0, 0.0), self.E, UP, self.N, off=d, t=t)

    def side(self, s, dep, left=True):
        """The face of a projection's end at s (0 .. dep out), facing away from the facade's middle."""
        return Face(self.p(s, 0), self.p(s, dep)) if left else Face(self.p(s, dep), self.p(s, 0))


PC_D = 12.0                                        # m: depth of the photographed Pirates masses


def co_line(name):
    """Cafe Orleans' photographed fronts on OSM's corners of way 72865092: the blue house (41-40, south-west), the cream
    Cafe Orleans house (40-37), the salmon house (36-34, 1.4 m forward of the cream one)."""
    i, j = {"blue": (41, 40), "cream": (40, 37), "salmon": (36, 34)}[name]
    return osm_pt(i), osm_pt(j)


def straighten(poly, a, b, depth=6.0):
    """poly with its front between a and b replaced by the straight line a-b (filled behind, cut in front)."""
    F = Face(a, b)
    fill = Polygon([F.p(0.05), F.p(F.L - 0.05), F.p(F.L - 0.05, -depth), F.p(0.05, -depth)])
    cut = Polygon([F.p(0.05), F.p(F.L - 0.05), F.p(F.L - 0.05, depth), F.p(0.05, depth)])
    g = poly.union(fill).difference(cut).buffer(0)
    return max(G._polys(g), key=lambda p: p.area)


# ---- 2D shapes in facade coordinates (s, z)
def opening(s, w, z0, zs, rise=0.0):
    """A door / window outline: a rectangle up to the springing zs, an (elliptical / segmental) arch of `rise` on top."""
    g = sbox(s - w / 2, z0, s + w / 2, zs)
    if rise > 0:
        top = shapely.affinity.scale(Point(s, zs).buffer(1.0, 16), w / 2, rise).intersection(sbox(s - w, zs, s + w, zs + rise + 1))
        g = g.union(top)
    return g


def ellipse(s, z, rx, rz, n=16):
    return shapely.affinity.scale(Point(s, z).buffer(1.0, n), rx, rz)


_TILE = {}


def lace_tile(cell, W, H):
    """Cast-iron lace: octagonal rings that touch, a boss in each, small diamonds between (a pierced pattern)."""
    key = (cell, W, H)
    if key not in _TILE:
        bw = cell * 0.11
        r = cell * 0.53
        ring = Point(0, 0).buffer(r, 2).difference(Point(0, 0).buffer(r - bw, 2))
        boss = Point(0, 0).buffer(cell * 0.08, 1)
        h = cell * 0.2
        dia = Polygon([(0, -h), (h, 0), (0, h), (-h, 0)])
        dia = dia.difference(dia.buffer(-bw * 0.8, join_style=2))
        parts = []
        for i in range(int(W / cell) + 2):
            for j in range(int(H / cell) + 2):
                x, y = i * cell, j * cell
                parts += [shapely.affinity.translate(ring, x, y), shapely.affinity.translate(boss, x, y),
                          shapely.affinity.translate(dia, x + cell / 2, y + cell / 2)]
        _TILE[key] = unary_union(parts)
    return _TILE[key]


def lace_geom(clip, cell=0.26):
    x0, y0, x1, y1 = clip.bounds
    W, H = (16.0, 6.0) if cell > 0.2 else (16.0, 1.4)
    t = shapely.affinity.translate(lace_tile(cell, W, H), x0 - cell * 0.3, y0 - cell * 0.3)
    return t.intersection(clip).union(clip.boundary.buffer(cell * 0.09).intersection(clip))


def lattice_geom(clip, step=0.22, bw=0.03):
    """A diagonal (X) lattice, e.g. the veranda's valance."""
    x0, y0, x1, y1 = clip.bounds
    lines = []
    for k in np.arange(x0 - (y1 - y0) - 1, x1 + 1, step):
        lines.append(LineString([(k, y0), (k + (y1 - y0), y1)]).buffer(bw / 2, cap_style=2))
        lines.append(LineString([(k, y1), (k + (y1 - y0), y0)]).buffer(bw / 2, cap_style=2))
    return unary_union(lines).intersection(clip).union(clip.boundary.buffer(bw).intersection(clip))


def lines_in(shape, step, vertical=True):
    """Bars at a regular step clipped to a shape (glazing bars, slats): list of ((s0, z0), (s1, z1))."""
    x0, y0, x1, y1 = shape.bounds
    out = []
    for k in np.arange((x0 if vertical else y0) + step, (x1 if vertical else y1) - step * 0.3, step):
        ln = LineString([(k, y0 - 1), (k, y1 + 1)] if vertical else [(x0 - 1, k), (x1 + 1, k)]).intersection(shape)
        for g in getattr(ln, "geoms", [ln]):
            if g.geom_type == "LineString" and g.length > 0.05:
                out.append((g.coords[0], g.coords[-1]))
    return out


# ---- 3D pieces on a Face
def wall_with(M, F, mat, s0, s1, z0, z1, holes, d=0.0):
    F.plate(M[mat], sbox(s0, z0, s1, z1).difference(unary_union(holes)) if holes else sbox(s0, z0, s1, z1), d=d)


def recess(M, F, hole, depth, mat, d=0.0, fill=None):
    """The reveals of an opening (depth m into the wall), and its back filled with `fill`."""
    c = hole.centroid
    cs = list(orient(hole, 1.0).exterior.coords)
    for (s0, z0), (s1, z1) in zip(cs[:-1], cs[1:]):
        m = ((s0 + s1) / 2, (z0 + z1) / 2)
        want = F.E * (c.x - m[0]) + UP * (c.y - m[1])
        quad(M[mat], F.P(s0, z0, d), F.P(s1, z1, d), F.P(s1, z1, d - depth), F.P(s0, z0, d - depth), want)
    if fill:
        F.plate(M[fill], hole, d=d - depth)


def bars(M, mat, F, shape, d, du=None, dz=None, w=0.03):
    for step, vert in ((du, True), (dz, False)):
        if step:
            for (a0, b0), (a1, b1) in lines_in(shape, step, vert):
                bar(M[mat], F.P(a0, b0, d), F.P(a1, b1, d), w=w, d=w * 0.7)


def frame(M, mat, F, hole, width=0.13, d=0.0, t=0.05, above=None):
    """A moulded surround (only above `above` when given: an archivolt)."""
    g = hole.buffer(width, join_style=2).difference(hole)
    if above is not None:
        g = g.intersection(sbox(-1e3, above, 1e3, 1e3))
    F.plate(M[mat], g, d=d + t, t=t)


def shutter_pair(M, F, s, w, z0, z1, mat, slat, d=0.0, open_=True):
    """Louvred shutters beside a window (open against the wall) or half closed over it."""
    h = z1 - z0
    for sg in (-1, 1):
        sc = s + sg * (w / 2 + 0.3) if open_ else s + sg * w / 4
        hw = 0.28 if open_ else w / 4 - 0.02
        F.box(M[mat], sc, (z0 + z1) / 2, d + 0.05, hw, 0.025, h / 2)
        for z in np.arange(z0 + 0.12, z1 - 0.08, 0.11):
            bar(M[slat], F.P(sc - hw + 0.05, z, d + 0.085), F.P(sc + hw - 0.05, z, d + 0.085), w=0.012, d=0.012)
        F.box(M[mat], sc, (z0 + z1) / 2, d + 0.085, hw, 0.012, 0.05)


def flower_box(M, F, s, z, d, w=0.5, cols=("AD_fl_pink", "AD_fl_pur")):
    F.box(M["AD_timberd"], s, z + 0.1, d, w / 2, 0.11, 0.1)
    for k, u in enumerate(np.linspace(-w / 2 + 0.1, w / 2 - 0.1, 3)):
        sphere(M["AD_leaf"], F.P(s + u, z + 0.25, d + 0.02), 0.14, n=6, m=3, sc=(1, 1, 0.8))
        sphere(M[cols[k % len(cols)]], F.P(s + u + 0.05, z + 0.33, d + 0.08), 0.08, n=6, m=3)
    sphere(M["AD_leaf"], F.P(s, z - 0.05, d + 0.12), 0.12, n=6, m=3, sc=(1, 1, 1.6))       # trailing leaves


def lace_rail(M, mat, F, s0, s1, z, d, h=0.95, boxes=None, posts=True):
    """A cast-iron lace railing on the plane d out of F, from s0 to s1, standing on z."""
    bar(M[mat], F.P(s0, z + h, d), F.P(s1, z + h, d), w=0.045, d=0.05)
    bar(M[mat], F.P(s0, z + 0.07, d), F.P(s1, z + 0.07, d), w=0.03, d=0.03)
    if posts:
        for s in (s0, s1):
            bar(M[mat], F.P(s, z, d), F.P(s, z + h, d), w=0.05, d=0.05)
    F.plate(M[mat], lace_geom(sbox(s0, z + 0.09, s1, z + h - 0.03), 0.16), d=d)
    if boxes:
        for s in np.arange(s0 + 0.45, s1 - 0.3, 1.1):
            flower_box(M, F, s, z + h, d + 0.12, cols=boxes)


def gallery(M, F, s0, s1, floors, zroof, dep, iron, cols=None, lace=None, zground=None, bays=3, boxes=None,
            roof="AD_slated", cresting=False, spandrel=0.9):
    """A cast-iron gallery: slender columns (from the pavement, or brackets under the lowest floor), thin floors with
    lace railings, under every ceiling lace spandrels round arches from column to column (front and ends), a fascia,
    a roof sloping out from the wall, optional cresting."""
    cols, lace = cols or iron, lace or iron
    xs = np.linspace(s0, s1, bays + 1)
    dc = dep - 0.08
    zlo = zground if zground is not None else floors[0]
    for s in xs:
        frustum(M[cols], F.P(s, zlo, dc), F.P(s, zroof, dc), 0.055, 0.055, n=6)
        if zground is not None:
            frustum(M[cols], F.P(s, zground, dc), F.P(s, zground + 0.55, dc), 0.11, 0.075, n=6)
        else:
            bar(M[iron], F.P(s, floors[0] - 1.0, 0.05), F.P(s, floors[0] - 0.1, dc), w=0.03, d=0.03)
        for z in list(floors[1:]) + [zroof]:
            F.box(M[cols], s, z - 0.12, dc, 0.09, 0.09, 0.08)                              # capitals
    for z in floors:
        F.box(M[iron], (s0 + s1) / 2, z - 0.06, dep / 2, (s1 - s0) / 2 + 0.05, dep / 2, 0.06)
        lace_rail(M, lace, F, s0, s1, z, dc, boxes=boxes, posts=False)
        for left in (True, False):
            Fs = F.side(s0 if left else s1, dc, left)
            lace_rail(M, lace, Fs, 0.05, Fs.L, z, 0.0, posts=False)
    ceilings = list(floors[1:]) + [zroof] + ([floors[0] - 0.12] if zground is not None else [])
    for zc in ceilings:
        geo = []
        for u0, u1 in zip(xs[:-1], xs[1:]):
            arch = ellipse((u0 + u1) / 2, zc - spandrel, (u1 - u0) / 2 - 0.07, spandrel - 0.2)
            geo.append(sbox(u0, zc - spandrel, u1, zc).difference(arch))
        F.plate(M[lace], lace_geom(unary_union(geo), 0.2), d=dc)
        for left in (True, False):
            Fs = F.side(s0 if left else s1, dc, left)
            arch = ellipse(Fs.L / 2, zc - spandrel * 0.7, Fs.L / 2 - 0.1, spandrel * 0.7 - 0.15)
            Fs.plate(M[lace], lace_geom(sbox(0.0, zc - spandrel * 0.7, Fs.L, zc).difference(arch), 0.2))
    F.box(M[lace], (s0 + s1) / 2, zroof + 0.13, dep, (s1 - s0) / 2 + 0.06, 0.05, 0.14)              # fascia
    quad(M[roof], F.P(s0, zroof + 0.55), F.P(s1, zroof + 0.55), F.P(s1, zroof + 0.25, dep + 0.12), F.P(s0, zroof + 0.25, dep + 0.12), UP)
    quad(M[roof], F.P(s0, zroof, 0), F.P(s1, zroof, 0), F.P(s1, zroof, dep), F.P(s0, zroof, dep), -UP)
    if cresting:
        F.plate(M[lace], lace_geom(sbox(s0, zroof + 0.28, s1, zroof + 0.62), 0.16), d=dep)


def lamp_arms(M, x, y, z, along, top=True, h=3.3):
    """A lamp post with two arms (and a globe on top): the teal posts in front of the Pirates gallery and Cafe Orleans."""
    lathe(M["AD_lamp"], (x, y, z), [(0.17, 0.0), (0.17, 0.45), (0.1, 0.6), (0.065, 0.8), (0.055, h), (0.0, h + 0.02)], n=8)
    a = np.r_[np.asarray(along, float)[:2], 0.0]
    c = np.array([x, y, z + h - 0.35])
    for sg in (-1, 1):
        q = c + a * sg * 0.42
        bar(M["AD_lamp"], c, q + UP * 0.12, w=0.025, d=0.025)
        sphere(M["AD_globe"], q + UP * 0.38, 0.19, n=8, m=5)
    if top:
        sphere(M["AD_globe"], (x, y, z + h + 0.22), 0.2, n=8, m=5)


def flag(M, F, s, z, d, mat, side=1, L=1.7, drop=1.9, emblem=None):
    """A flag hanging from a pole leaning out of the gallery and to one side."""
    p0 = F.P(s, z, d)
    p1 = p0 + F.N * 0.9 + F.E * side * 1.0 + UP * 1.6
    bar(M["AD_lamp"], p0, p1, w=0.025, d=0.025)
    ax = (p1 - p0) / np.linalg.norm(p1 - p0)
    q = p1 - ax * L
    quad(M[mat], p1, q, q - UP * drop, p1 - UP * drop * 0.85, F.N)
    if emblem:
        m = (p1 + q) / 2 - UP * drop * 0.45 + F.N * 0.02
        sphere(M[emblem], m, 0.2, n=6, m=3, sc=(1, 0.2, 1))


def us_flag(M, base, along, w=1.9, h=1.0):
    """A small Stars and Stripes on top of a pole at `base` (the pole's top), flying along `along`."""
    a = np.r_[np.asarray(along, float)[:2], 0.0]
    n = np.cross(UP, a)
    for i in range(7):
        z0, z1 = -h + h * i / 7, -h + h * (i + 1) / 7
        quad(M["AD_flag1" if i % 2 == 0 else "AD_umb_w"], base + UP * z0, base + a * w + UP * z0, base + a * w + UP * z1, base + UP * z1, n)
    quad(M["AD_navy"], base + UP * (-h * 0.47) + n * 0.01, base + a * 0.8 + UP * (-h * 0.47) + n * 0.01,
         base + a * 0.8 + n * 0.01, base + n * 0.01, n)


def cornice(M, F, s0, s1, z, out=0.55, mat="AD_trim"):
    """A cornice on modillions: a frieze moulding, brackets every 0.45 m, the corona and a cyma on top (z = top)."""
    F.box(M[mat], (s0 + s1) / 2, z - 0.72, 0.1, (s1 - s0) / 2, 0.1, 0.05)
    F.box(M[mat], (s0 + s1) / 2, z - 0.5, 0.14, (s1 - s0) / 2 + 0.05, 0.14, 0.07)
    for s in np.arange(s0 + 0.2, s1 - 0.1, 0.45):
        F.box(M[mat], s, z - 0.33, out * 0.45, 0.06, out * 0.45, 0.09)
    F.box(M[mat], (s0 + s1) / 2, z - 0.17, out / 2, (s1 - s0) / 2 + 0.1, out / 2, 0.08)
    F.box(M[mat], (s0 + s1) / 2, z - 0.04, out / 2 + 0.04, (s1 - s0) / 2 + 0.13, out / 2 + 0.04, 0.05)


def pilaster(M, F, s, z0, z1, mat, cap="AD_trim", w=0.28, out=0.12):
    F.box(M[mat], s, (z0 + z1) / 2, out / 2, w, out / 2, (z1 - z0) / 2)
    F.box(M[cap], s, z1 - 0.1, out / 2 + 0.03, w + 0.05, out / 2 + 0.03, 0.1)
    F.box(M[cap], s, z0 + 0.15, out / 2 + 0.02, w + 0.04, out / 2 + 0.02, 0.15)


def finial(M, F, s, z, d=0.25):
    F.box(M["AD_trim"], s, z + 0.28, d, 0.2, 0.2, 0.28)
    F.box(M["AD_trim"], s, z + 0.6, d, 0.24, 0.24, 0.04)
    sphere(M["AD_trim"], F.P(s, z + 0.86, d), 0.2, n=8, m=5)


def window_full(M, F, hole, glass="AD_glass", frame_m="AD_trim", reveal="AD_trim", depth=0.3, du=0.36, dz=0.42, curtains=False, sill=True,
                hood=False, d=0.0):
    """A glazed opening: reveals, the glass at the back with glazing bars, a moulded surround, a sill, an optional hood."""
    recess(M, F, hole, depth, reveal, d=d, fill=glass)
    bars(M, frame_m, F, hole, d - depth + 0.03, du=du, dz=dz, w=0.03)
    frame(M, frame_m, F, hole, 0.12, d=d)
    x0, y0, x1, y1 = hole.bounds
    if curtains:
        F.plate(M["AD_curtain"], sbox(x0, y0 + 0.2, x0 + (x1 - x0) * 0.28, y1).intersection(hole), d=d - depth + 0.015)
        F.plate(M["AD_curtain"], sbox(x1 - (x1 - x0) * 0.28, y0 + 0.2, x1, y1).intersection(hole), d=d - depth + 0.015)
    if sill:
        F.box(M[frame_m], (x0 + x1) / 2, y0 - 0.1, d + 0.08, (x1 - x0) / 2 + 0.2, 0.08, 0.06)
    if hood:
        F.box(M[frame_m], (x0 + x1) / 2, y1 + 0.28, d + 0.14, (x1 - x0) / 2 + 0.3, 0.14, 0.07)
        F.box(M[frame_m], (x0 + x1) / 2, y1 + 0.18, d + 0.08, (x1 - x0) / 2 + 0.2, 0.08, 0.05)



def balcony(M, F, s0, s1, z, dep, iron="AD_iron", slab="AD_trim", boxes=("AD_fl_pink", "AD_fl_pur")):
    """A balcony: a moulded slab on scrolled brackets, a lace railing on three sides with flower boxes."""
    F.box(M[slab], (s0 + s1) / 2, z - 0.09, dep / 2, (s1 - s0) / 2, dep / 2, 0.09)
    F.box(M[slab], (s0 + s1) / 2, z - 0.2, dep / 2 - 0.05, (s1 - s0) / 2 - 0.05, dep / 2 - 0.05, 0.03)
    for s in np.linspace(s0 + 0.25, s1 - 0.25, max(2, int((s1 - s0) / 1.2) + 1)):
        Fb = F.side(s, dep - 0.1, True)
        Fb.plate(M[slab], Polygon([(0.0, z - 0.2), (Fb.L, z - 0.2), (0.0, z - 0.85)]).difference(
            Point(Fb.L * 0.95, z - 0.95).buffer(0.55, 8)), d=-0.06, t=0.12)
    lace_rail(M, iron, F, s0 + 0.05, s1 - 0.05, z, dep - 0.06, boxes=boxes)
    for left in (True, False):
        Fs = F.side(s0 + 0.05 if left else s1 - 0.05, dep - 0.06, left)
        lace_rail(M, iron, Fs, 0.02, Fs.L, z, 0.0)


def dormer(M, F, s, zb, w=1.9, h=2.3, mat="AD_trim", glass="AD_glass"):
    """A pedimented dormer standing on the cornice line (pc4): pilasters, an arched window, a triangular pediment,
    balls on its corners and apex."""
    F.box(M[mat], s, zb + h / 2, -0.95, w / 2, 0.95, h / 2)
    hole = opening(s, 0.8, zb + 0.35, zb + 1.35, 0.4)
    F.plate(M[glass], hole, d=0.015)
    bars(M, mat, F, hole, 0.03, du=0.4, dz=0.45, w=0.03)
    frame(M, mat, F, hole, 0.1, d=0.0)
    for sg in (-1, 1):
        pilaster(M, F, s + sg * (w / 2 - 0.12), zb, zb + h - 0.15, mat, w=0.12, out=0.08)
    F.box(M[mat], s, zb + h - 0.06, -0.85, w / 2 + 0.12, 1.0, 0.07)
    tri_ = Polygon([(s - w / 2 - 0.15, zb + h), (s + w / 2 + 0.15, zb + h), (s, zb + h + 0.8)])
    F.plate(M[mat], tri_, d=0.12, t=2.05)
    F.plate(M["AD_slated"], tri_.buffer(-0.12, join_style=2), d=0.14)
    for u, z in ((-w / 2 - 0.05, zb + h + 0.08), (w / 2 + 0.05, zb + h + 0.08), (0.0, zb + h + 0.85)):
        sphere(M[mat], F.P(s + u, z + 0.12, 0.05), 0.14, n=8, m=5)


# ---- the Pirates of the Caribbean group (pc1-3 + seven more photos seen in the conversation, video v2 0:07:40-0:07:56)
# Read off the photos: the Pirates house is ~14 m wide, 2 storeys + attic (ground floor 4.2 m, cornice at 8.7 m),
# three masses on OSM's jogs: the LEFT part (two window bays) projects 1.3 m, the GALLERY bay behind it carries the
# cast-iron gallery, the narrow RIGHT bay; the rusticated stone runs under the gallery and the right bay. West of it a
# low house behind two palms; east of it the TAN house angles back behind a veranda.
def pc_R():
    """The east end of the Pirates' right bay: 2.6 m along OSM's edge 66 -> 65 (the rest belongs to the tan house)."""
    a, b = osm_pt(66), osm_pt(65)
    return a + (b - a) / np.linalg.norm(b - a) * 2.6


def extrude(a, b, D=PC_D):
    F = Face(a, b)
    return Polygon([F.a, F.b, F.p(F.L, -D), F.p(0, -D)])


def pc_masses(rest):
    P, R = osm_pt, pc_R()
    spec = [
        dict(name="west", fronts=[(P(74), P(72), west_house)], h=7.2, mat="AD_cream", roof="hip"),
        dict(name="left", fronts=[(P(71), P(70), pc_left)], h=8.7, mat="AD_pink", roof="flat"),
        dict(name="gallery", fronts=[(P(69), P(66), pc_centre)], h=8.7, mat="AD_pink", roof="flat"),
        dict(name="right", fronts=[(P(66), R, pc_right)], h=8.7, mat="AD_pink", roof="flat"),
        dict(name="tan", fronts=[(R, P(65), tan_gable), (P(65), P(64), tan_plain), (P(64), P(63), tan_plain),
                                 (P(63), P(62), tan_main)], h=7.0, mat="AD_tan", roof="flat"),
    ]
    taken, out = Polygon(), []
    for m in spec:
        g = unary_union([extrude(a, b) for a, b, _ in m["fronts"]]).intersection(rest).difference(taken.buffer(0.01))
        ps = [p for p in G._polys(g) if p.area > 3]
        if ps:
            m["poly"] = max(ps, key=lambda p: p.area)
            taken = taken.union(m["poly"])
            out.append(m)
    return out


def draw_mass(ctx, m, masses, zb, zf):
    """One mass: its photographed fronts, plain walls with a cornice on the other visible sides (none where a mass at
    least as tall stands against it), its roof."""
    M = ctx.M
    poly, ztop = m["poly"], zf + m["h"]
    done = set()
    for a, b, nrm in ring_edges(poly):
        k = next((i for i, (p0, p1, fn) in enumerate(m["fronts"])
                  if LineString([p0, p1]).distance(Point(*a)) < 0.15 and LineString([p0, p1]).distance(Point(*b)) < 0.15), None)
        if k is not None:
            if k not in done:
                done.add(k)
                p0, p1, fn = m["fronts"][k]
                fn(ctx, Face(p0, p1), zb, zf, ztop)
            continue
        q = Point(*((a + b) / 2 + nrm * 0.3))
        if any(o is not m and o["h"] >= m["h"] and o["poly"].buffer(0.05).contains(q) for o in masses):
            continue
        quad(M[m["mat"]], P3(a, zb), P3(b, zb), P3(b, ztop), P3(a, ztop), np.r_[nrm, 0.0])
        if ctx.is_front(a, b, nrm, reach=1.0) or ctx.pv.contains(q):
            Fs = Face(a, b)
            cornice(M, Fs, 0.0, Fs.L, ztop, out=0.4)
            Fs.box(M["AD_trim"], Fs.L / 2, zf + 4.15, 0.08, Fs.L / 2, 0.08, 0.1)
    if m["roof"] == "hip":
        cap(M["AD_slated"], poly, ztop - 0.05)
        hip_strip(M["AD_slate"], M["AD_slated"], poly, ztop - 0.05, 2.2, 2.0, out=0.35)
    else:
        cap(M["AD_showroof"], poly, ztop - 0.35)


def stone_ground(M, F, s0, s1, zb, ztop_stone, holes):
    """Rusticated tan stone, block by block (0.95 x 0.43 m, staggered), proud of dark joints."""
    zone = sbox(s0, zb, s1, ztop_stone).difference(unary_union(holes).buffer(0.2, join_style=2)) if holes else sbox(s0, zb, s1, ztop_stone)
    F.plate(M["AD_mortar"], zone, d=0.01)
    blocks = []
    for j, z in enumerate(np.arange(zb, ztop_stone, 0.48)):
        off = 0.48 if j % 2 else 0.0
        for u in np.arange(s0 - 1.0 + off, s1, 0.96):
            blocks.append(sbox(u + 0.025, z + 0.025, u + 0.935, min(z + 0.455, ztop_stone - 0.02)))
    F.plate(M["AD_ashlar"], unary_union(blocks).intersection(zone), d=0.08, t=0.07)


def oval_panel(M, F, s, zat, rx, rz, wall):
    """An attic oval: a grey-green panel with a cream frame, the oval recessed with radial bars and four keystones."""
    h = ellipse(s, zat, rx, rz)
    pan = sbox(s - rx - 0.33, zat - rz - 0.14, s + rx + 0.33, zat + rz + 0.14)
    F.plate(M["AD_ppanel"], pan.difference(h.buffer(0.14)), d=0.015)
    frame(M, "AD_trim", F, pan, 0.08, d=0.0)
    recess(M, F, h, 0.25, wall, fill="AD_glass")
    frame(M, "AD_trim", F, h, 0.13, d=0.0)
    for i in range(8):
        t = 2 * math.pi * i / 8
        bar(M["AD_trim"], F.P(s, zat, -0.22), F.P(s + rx * math.cos(t), zat + rz * math.sin(t), -0.22), w=0.02, d=0.02)
    for t in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        F.box(M["AD_trim"], s + (rx + 0.1) * math.cos(t), zat + (rz + 0.1) * math.sin(t), 0.1, 0.08, 0.1, 0.09)


def french_window(M, F, s, z1, wall, w=1.3, top=2.5, rise=0.0, balc=True, shut="AD_pshut", flowers=("AD_fl_pink", "AD_fl_pur", "AD_fl_red")):
    """A first-floor French window: recessed, glazing bars, curtains, louvred shutters, a hood, a balcony."""
    h = opening(s, w, z1 + 0.18, z1 + top, rise)
    window_full(M, F, h, frame_m="AD_trim", reveal=wall, depth=0.3, du=w / 2, dz=0.45, curtains=True, hood=rise == 0)
    shutter_pair(M, F, s, w, z1 + 0.18, z1 + top, shut, "AD_shutter")
    if balc:
        balcony(M, F, s - w / 2 - 0.5, s + w / 2 + 0.5, z1 + 0.02, 0.72, iron="AD_iron", boxes=flowers)
    return h


def downpipe(M, F, s, z0, z1, d=0.12):
    frustum(M["AD_lamp"], F.P(s, z0, d), F.P(s, z1, d), 0.055, 0.055, n=6)
    F.box(M["AD_lamp"], s, z1 + 0.15, d + 0.02, 0.12, 0.1, 0.15)


def pc_left(ctx, F, zb, zf, ztop):
    """The projecting left part: two bays, each an arched ground-floor window, a French window with shutters on its
    own balcony, an attic oval; quoin pilasters, the cornice with balls, a dormer, a downpipe."""
    M = ctx.M; L = F.L
    z1, zat = zf + 4.2, zf + 7.38
    ss = (L * 0.25, L * 0.75)
    gw = [opening(s, 1.35, zf + 0.85, zf + 2.55, 0.68) for s in ss]
    uw = [opening(s, 1.3, z1 + 0.18, z1 + 2.5) for s in ss]
    ov = [ellipse(s, zat, 0.62, 0.32) for s in ss]
    wall_with(M, F, "AD_pink", 0.0, L, zb, ztop, gw + uw + ov)
    for s, h in zip(ss, gw):
        window_full(M, F, h, frame_m="AD_tealdoor", reveal="AD_pink", depth=0.35, du=0.34, dz=0.5)
        frame(M, "AD_trim", F, h, 0.16, d=0.0, above=zf + 2.45)
        F.box(M["AD_trim"], s, zf + 3.33, 0.16, 0.14, 0.1, 0.2)
        french_window(M, F, s, z1, "AD_pink")
        oval_panel(M, F, s, zat, 0.62, 0.32, "AD_pink")
    F.box(M["AD_trim"], L / 2, z1 - 0.05, 0.12, L / 2 + 0.05, 0.12, 0.13)
    F.box(M["AD_trim"], L / 2, z1 + 2.74, 0.07, L / 2, 0.07, 0.05)
    F.box(M["AD_pink"], L / 2, zb + 0.35, 0.06, L / 2, 0.06, 0.4)                    # plinth
    for s in (0.22, L / 2, L - 0.22):
        pilaster(M, F, s, zb, ztop - 0.8, "AD_pink", w=0.24 if s == L / 2 else 0.3, out=0.16)
    cornice(M, F, -0.1, L + 0.1, ztop)
    F.box(M["AD_pink"], L / 2, ztop + 0.3, -0.1, L / 2, 0.1, 0.3)                      # parapet
    for s in (0.22, L - 0.22):
        finial(M, F, s, ztop)
    dormer(M, F, L * 0.7, ztop - 0.05)
    downpipe(M, F, L - 0.05, zb, ztop - 0.85)


def pc_right(ctx, F, zb, zf, ztop):
    """The narrow right bay: the rusticated stone with a recessed arched teal door, a French window on a balcony, the
    attic oval, the cornice with a ball, a dormer."""
    M = ctx.M; L = F.L
    z1, zat = zf + 4.2, zf + 7.38
    s = L / 2
    door = opening(s, 1.35, zf, zf + 2.5, 0.68)
    uw = opening(s, 1.2, z1 + 0.18, z1 + 2.5)
    ov = ellipse(s, zat, 0.55, 0.3)
    wall_with(M, F, "AD_pink", 0.0, L, zb, ztop, [door, uw, ov])
    stone_ground(M, F, 0.0, L, zb, z1 - 0.38, [door])
    recess(M, F, door, 0.4, "AD_ashlar")
    F.plate(M["AD_tealdoor"], door.intersection(sbox(0, zb, L, zf + 2.5)), d=-0.4)
    for u in (s - 0.33, s + 0.33):
        for zc in (zf + 0.6, zf + 1.75):
            F.box(M["AD_tealdoor"], u, zc, -0.37, 0.24, 0.02, 0.45)
    F.plate(M["AD_glass"], door.intersection(sbox(0, zf + 2.55, L, ztop)), d=-0.38)
    for i in range(1, 6):
        t = math.pi * i / 6
        c = F.P(s, zf + 2.5, -0.35)
        bar(M["AD_trim"], c, c + F.E * 0.66 * math.cos(t) + UP * 0.66 * math.sin(t), w=0.025, d=0.02)
    frame(M, "AD_trim", F, door, 0.18, d=0.08, above=zf + 2.45)
    F.box(M["AD_trim"], s, zf + 3.25, 0.18, 0.14, 0.1, 0.22)
    french_window(M, F, s, z1, "AD_pink", w=1.2)
    oval_panel(M, F, s, zat, 0.55, 0.3, "AD_pink")
    F.box(M["AD_trim"], L / 2, z1 - 0.05, 0.12, L / 2, 0.12, 0.13)
    F.box(M["AD_trim"], L / 2, z1 + 2.74, 0.07, L / 2, 0.07, 0.05)
    pilaster(M, F, L - 0.22, z1, ztop - 0.8, "AD_pink", w=0.25, out=0.16)
    cornice(M, F, -0.1, L + 0.1, ztop)
    F.box(M["AD_pink"], L / 2, ztop + 0.3, -0.1, L / 2, 0.1, 0.3)
    finial(M, F, L - 0.22, ztop)
    dormer(M, F, s, ztop - 0.05, w=1.7)
    downpipe(M, F, L - 0.05, zb, ztop - 0.85)


def pc_centre(ctx, F, zb, zf, ztop):
    """The gallery bay: the rusticated stone ground floor with three recessed segmental-arched entrances (barred
    transoms, cream archivolts with keystones, teal leaves folded back), oval posters on the piers; French windows
    behind the gallery; the cornice; the cast-iron gallery (a thick cream floor on wooden brackets, one tall cage with
    arched lace screens, a cornice, a segmental pediment with louvres between two triangular ones, lanterns), the sign
    with the skull, the flags, the lamps with three globes, the cupola with the flag."""
    M = ctx.M; L = F.L
    z1 = zf + 4.2
    sm = L / 2
    ds = (sm - 2.25, sm, sm + 2.25)
    doors = [opening(s, 1.65, zf, zf + 2.7, 0.36) for s in ds]
    up = [opening(s, 1.15, z1 + 0.18, z1 + 2.3, 0.58 if s == sm else 0.0) for s in ds]
    wall_with(M, F, "AD_pink", 0.0, L, zb, ztop, doors + up)
    stone_ground(M, F, 0.0, L, zb, z1 - 0.38, doors)
    for h in doors:
        x0, y0, x1, y1 = h.bounds
        recess(M, F, h, 0.5, "AD_ashlar")
        zt = zf + 2.4
        F.plate(M["AD_glass"], h.intersection(sbox(x0, y0, x1, zt)), d=-0.5)
        for sg in (-1, 1):                                                    # leaves folded back into the reveal
            Fr = F.side(x0 if sg < 0 else x1, -0.5, sg < 0)
            quad(M["AD_tealdoor"], F.P(x0 + 0.05 if sg < 0 else x1 - 0.05, zf, -0.08), F.P(x0 + 0.05 if sg < 0 else x1 - 0.05, zf, -0.48),
                 F.P(x0 + 0.05 if sg < 0 else x1 - 0.05, zt - 0.05, -0.48), F.P(x0 + 0.05 if sg < 0 else x1 - 0.05, zt - 0.05, -0.08), F.E * -sg)
        tr = h.intersection(sbox(x0, zt + 0.08, x1, y1 + 1))
        F.plate(M["AD_glass"], tr, d=-0.42)
        bars(M, "AD_trim", F, tr, -0.39, du=0.17, w=0.022)
        F.box(M["AD_trim"], (x0 + x1) / 2, zt + 0.04, -0.4, (x1 - x0) / 2, 0.06, 0.05)
        frame(M, "AD_trim", F, h, 0.2, d=0.08, above=zf + 2.6)
        F.box(M["AD_trim"], (x0 + x1) / 2, y1 + 0.1, 0.18, 0.15, 0.1, 0.22)
    for s in (sm - 1.125, sm + 1.125):                                        # posters on the piers
        F.plate(M["AD_signg"], ellipse(s, zf + 1.65, 0.27, 0.36), d=0.17, t=0.04)
        F.plate(M["AD_sign"], ellipse(s, zf + 1.65, 0.21, 0.3), d=0.18)
        F.plate(M["AD_tealdoor"], ellipse(s, zf + 1.55, 0.12, 0.08), d=0.185)
    for h in up:
        x0, y0, x1, y1 = h.bounds
        window_full(M, F, h, frame_m="AD_trim", reveal="AD_pink", depth=0.3, du=(x1 - x0) / 2, dz=0.45, curtains=True)
        shutter_pair(M, F, (x0 + x1) / 2, x1 - x0, y0, min(y1, z1 + 2.3), "AD_pshut", "AD_shutter")
    F.box(M["AD_trim"], L / 2, z1 + 2.74, 0.07, L / 2, 0.07, 0.05)
    for s in (0.2, L - 0.2):
        pilaster(M, F, s, z1, ztop - 0.8, "AD_pink", w=0.22, out=0.12)
    cornice(M, F, -0.1, L + 0.1, ztop)
    F.box(M["AD_pink"], L / 2, ztop + 0.3, -0.1, L / 2, 0.1, 0.3)
    for s in (0.2, L - 0.2):
        finial(M, F, s, ztop)
    # -- the gallery
    zg = ztop - 0.15
    dep = 2.05
    g0, g1 = 0.5, L - 0.5
    F.box(M["AD_trim"], sm, z1 - 0.2, dep / 2, (g1 - g0) / 2 + 0.1, dep / 2, 0.2)          # the thick floor
    F.box(M["AD_trim"], sm, z1 - 0.43, dep - 0.04, (g1 - g0) / 2 + 0.12, 0.06, 0.05)
    for s in np.linspace(g0 + 0.2, g1 - 0.2, 8):                                       # wooden brackets
        Fb = F.side(s, dep - 0.15, True)
        Fb.plate(M["AD_timberd"], Polygon([(0.0, z1 - 0.4), (Fb.L, z1 - 0.4), (Fb.L - 0.1, z1 - 0.62), (0.0, z1 - 1.35)]), d=-0.07, t=0.14)
    xs = [g0, g0 + 1.85, g1 - 1.85, g1]
    for s in xs:
        F.box(M["AD_iron"], s, (z1 + zg) / 2, dep - 0.08, 0.07, 0.07, (zg - z1) / 2)
        F.box(M["AD_iron"], s, zg - 0.6, dep - 0.08, 0.11, 0.11, 0.06)
    lace_rail(M, "AD_iron", F, g0, g1, z1, dep - 0.08, h=1.0, boxes=("AD_fl_pink", "AD_fl_pur", "AD_fl_red"), posts=False)
    screens = []
    for (u0, u1), (sp, rise) in zip(zip(xs[:-1], xs[1:]), ((z1 + 2.95, 0.55), (z1 + 2.5, 1.3), (z1 + 2.95, 0.55))):
        arch = opening((u0 + u1) / 2, u1 - u0 - 0.45, z1 + 1.0, sp, rise)
        screens.append(sbox(u0, z1 + 1.0, u1, zg).difference(arch))
        F.plate(M["AD_iron"], arch.boundary.buffer(0.06).intersection(sbox(u0, z1 + 1.0, u1, zg)), d=dep - 0.06, t=0.04)
    F.plate(M["AD_iron"], lace_geom(unary_union(screens), 0.24), d=dep - 0.08)
    for left in (True, False):
        Fs = F.side(g0 if left else g1, dep - 0.08, left)
        lace_rail(M, "AD_iron", Fs, 0.05, Fs.L, z1, 0.0, h=1.0, posts=False)
        arch = opening(Fs.L / 2, Fs.L - 0.45, z1 + 1.0, z1 + 2.9, 0.6)
        Fs.plate(M["AD_iron"], lace_geom(sbox(0.0, z1 + 1.0, Fs.L, zg).difference(arch), 0.24))
        Fs.plate(M["AD_iron"], arch.boundary.buffer(0.06).intersection(sbox(0.0, z1 + 1.0, Fs.L, zg)), d=0.03, t=0.04)
    F.box(M["AD_iron"], sm, zg + 0.15, dep / 2 + 0.05, (g1 - g0) / 2 + 0.2, dep / 2 + 0.1, 0.15)        # its cornice
    F.box(M["AD_iron"], sm, zg + 0.36, dep / 2 + 0.08, (g1 - g0) / 2 + 0.28, dep / 2 + 0.14, 0.06)
    quad(M["AD_slated"], F.P(g0 - 0.2, zg + 0.42, dep + 0.2), F.P(g1 + 0.2, zg + 0.42, dep + 0.2), F.P(g1 + 0.2, zg + 1.2), F.P(g0 - 0.2, zg + 1.2), UP)
    for s in (g0 + 0.95, g1 - 0.95):                                                    # small triangular pediments
        t_ = Polygon([(s - 0.95, zg + 0.42), (s + 0.95, zg + 0.42), (s, zg + 1.04)])
        F.plate(M["AD_iron"], t_.difference(t_.buffer(-0.1, join_style=2)), d=dep + 0.2, t=0.12)
        F.plate(M["AD_slated"], t_.buffer(-0.1, join_style=2), d=dep + 0.12)
    ped = ellipse(sm, zg + 0.42, 1.9, 1.2, 24).intersection(sbox(sm - 3, zg + 0.42, sm + 3, zg + 3))
    inner = ellipse(sm, zg + 0.42, 1.62, 0.95, 24).intersection(sbox(sm - 3, zg + 0.42, sm + 3, zg + 3))
    F.plate(M["AD_iron"], ped.difference(inner), d=dep + 0.24, t=0.2)
    F.plate(M["AD_text"], inner, d=dep + 0.06)
    bars(M, "AD_iron", F, inner, dep + 0.1, dz=0.13, w=0.035)
    F.box(M["AD_iron"], sm, zg + 0.47, dep + 0.12, 1.95, 0.14, 0.05)
    loft_rect(M["AD_slated"], F.P(sm, zg + 0.42, dep / 2), F.e, F.n, [(1.9, dep / 2 + 0.1, 0.0), (0.3, 0.3, 1.25)])
    for s in (g0 + 1.85, g1 - 1.85):                                                   # lanterns inside
        bar(M["AD_iron"], F.P(s, zg, 1.0), F.P(s, zg - 0.7, 1.0), w=0.015, d=0.015)
        F.box(M["AD_black"], s, zg - 0.95, 1.0, 0.13, 0.13, 0.25)
        F.box(M["AD_globe"], s, zg - 0.95, 1.0, 0.1, 0.14, 0.18)
    for s in (g0 + 0.9, g1 - 0.9):                                                     # ferns hanging inside
        sphere(M["AD_leaf"], F.P(s, zg - 1.0, 0.9), 0.35, n=7, m=4, sc=(1, 1, 1.3))
    # -- the sign: a gilt cartouche, the skull in a tricorn, crossed swords
    c = z1 + 0.55
    cart = ellipse(sm, c, 1.35, 0.68, 24).union(sbox(sm - 1.45, c - 0.2, sm + 1.45, c + 0.2)).union(ellipse(sm, c + 0.55, 0.45, 0.3))
    F.plate(M["AD_signg"], cart, d=dep + 0.12, t=0.1)
    F.plate(M["AD_signbr"], cart.buffer(-0.1), d=dep + 0.14)
    F.plate(M["AD_sign"], shapely.affinity.translate(text_poly("Pirates", 0.34, "georgiaz.ttf"), sm, c + 0.12), d=dep + 0.16)
    F.plate(M["AD_sign"], shapely.affinity.translate(text_poly("of the Caribbean", 0.17, "georgiaz.ttf"), sm, c - 0.34), d=dep + 0.16)
    sphere(M["AD_trim"], F.P(sm, c + 1.05, dep + 0.15), 0.24, n=8, m=5)
    sphere(M["AD_flagblk"], F.P(sm, c + 1.27, dep + 0.12), 0.36, n=8, m=4, sc=(1, 0.6, 0.35))
    for sg in (-1, 1):
        bar(M["AD_trim"], F.P(sm - 0.55 * sg, c + 0.62, dep + 0.2), F.P(sm + 0.55 * sg, c + 1.35, dep + 0.2), w=0.04, d=0.03)
    flag(M, F, g0 + 1.3, z1 + 1.05, dep - 0.05, "AD_flag1", side=-1, L=1.1, drop=1.45, emblem="AD_signg")
    flag(M, F, g1 - 1.5, z1 + 1.05, dep - 0.05, "AD_flagblk", side=1, L=1.0, drop=1.4, emblem="AD_umb_w")
    flag(M, F, g1 - 0.65, z1 + 1.05, dep - 0.05, "AD_flagblk", side=1, L=1.0, drop=1.4, emblem="AD_umb_w")
    # -- the cupola: a square white base with a pink balustrade, an octagonal drum with arched windows, a grey dome,
    # a lantern, the flag
    q = F.p(sm, -3.6)
    zr = ztop - 0.3
    loft_rect(M["AD_trim"], P3(q, zr), F.e, F.n, [(1.5, 1.5, 0), (1.5, 1.5, 1.9), (1.65, 1.65, 1.9), (1.65, 1.65, 2.1)])
    for k in range(4):
        a = math.atan2(F.e[1], F.e[0]) + k * math.pi / 2
        n2 = np.array([math.cos(a), math.sin(a)]); e2 = np.array([-n2[1], n2[0]])
        arched_window(M["AD_glass"], q + n2 * 1.52 - e2 * 0.35, q + n2 * 1.52 + e2 * 0.35, n2, zr + 0.4, zr + 1.3, off=0.01)
    for sg in (-1, 1):
        for vec, ax in ((F.n, F.e), (F.e, F.n)):
            for t in np.arange(-1.4, 1.45, 0.28):
                p = q + vec * sg * 1.5 + ax * t
                lathe(M["AD_pink"], (p[0], p[1], zr + 2.1), [(0.06, 0), (0.09, 0.2), (0.05, 0.4), (0.07, 0.48), (0, 0.48)], n=6)
    loft_rect(M["AD_pink"], P3(q, zr + 2.58), F.e, F.n, [(1.58, 1.58, 0), (1.58, 1.58, 0.08)])
    zc = zr + 2.1
    lathe(M["AD_trim"], (q[0], q[1], zc), [(1.05, 0.0), (1.05, 2.1), (1.3, 2.1), (1.3, 2.32), (0.0, 2.32)], n=8)
    a0 = math.atan2(F.e[1], F.e[0])
    for k in range(8):
        a = a0 + k * math.pi / 4
        box(M["AD_trim"], P3(q + np.array([math.cos(a), math.sin(a)]) * 1.07, zc + 1.05), (0.08, 0.08, 1.05))
    for k in range(8):
        a = a0 + math.pi / 8 + k * math.pi / 4
        n2 = np.array([math.cos(a), math.sin(a)]); e2 = np.array([-n2[1], n2[0]])
        arched_window(M["AD_glass"], q + n2 * 0.99 - e2 * 0.24, q + n2 * 0.99 + e2 * 0.24, n2, zc + 0.35, zc + 1.4, off=0.02)
    lathe(M["AD_dome"], (q[0], q[1], zc + 2.32), [(1.2, 0), (1.15, 0.4), (0.92, 0.95), (0.55, 1.35), (0.18, 1.58), (0.0, 1.62)], n=8)
    lathe(M["AD_trim"], (q[0], q[1], zc + 3.85), [(0.22, 0), (0.22, 0.32), (0.28, 0.36), (0.0, 0.52)], n=8)
    sphere(M["AD_signg"], (q[0], q[1], zc + 4.45), 0.12, n=6, m=4)
    top = P3(q, zc + 4.5)
    frustum(M["AD_trim"], top, top + UP * 3.6, 0.04, 0.03, n=6)
    us_flag(M, top + UP * 3.5, F.e, w=1.7, h=0.9)
    # -- the lamps with three globes in front of the piers
    for s in (sm - 1.125, sm + 1.125):
        x, y = F.p(s, dep + 0.35)
        lamp_arms(M, x, y, ctx.gr.z(x, y), F.e, top=True, h=3.0)
        ctx.fixed_lamps.append((x, y))


def west_house(ctx, F, zb, zf, ztop):
    """The low house west of the Pirates (behind the palms in v2 0:07:48): cream stucco, 2 storeys, arched ground-floor
    windows, shuttered windows above, a slate hip roof; two palms in front."""
    M = ctx.M; L = F.L
    z1 = zf + 3.8
    ss = (L * 0.28, L * 0.72)
    gw = [opening(s, 1.2, zf + 0.8, zf + 2.4, 0.6) for s in ss]
    uw = [opening(s, 1.0, z1 + 0.4, z1 + 2.2) for s in ss]
    wall_with(M, F, "AD_cream", 0.0, L, zb, ztop, gw + uw)
    for h in gw:
        window_full(M, F, h, frame_m="AD_trim", reveal="AD_cream", depth=0.3, du=0.3, dz=0.45)
    for h in uw:
        x0, y0, x1, y1 = h.bounds
        window_full(M, F, h, frame_m="AD_trim", reveal="AD_cream", depth=0.3, du=0.5, dz=0.45, hood=True)
        shutter_pair(M, F, (x0 + x1) / 2, x1 - x0, y0, y1, "AD_shutter", "AD_odoor")
    F.box(M["AD_trim"], L / 2, z1 - 0.05, 0.1, L / 2, 0.1, 0.1)
    cornice(M, F, 0.0, L, ztop, out=0.35)
    rng = np.random.default_rng(7)
    for s, d, h in ((1.4, 3.6, 7.5), (3.9, 6.2, 8.6)):
        x, y = F.p(s, d)
        palm_tree(M, x, y, ctx.gr.z(x, y), h, math.atan2(F.n[1], F.n[0]) + rng.uniform(-0.6, 0.6), rng)


def palm_tree(M, x, y, z, h, lean, rng, kind="canary"):
    """A palm's spec (plants phase 3, 2026-10-05): the page grows it (plants.js). Only a marker triangle goes in AD_palmt
    (src/palm_specs.py reads it back out of the model): the base, the crown (the trunk bending towards `lean`), the kind.
    The old mesh's random draws are kept so the caller's sequence is unchanged."""
    import palm_specs
    ax, ay = math.cos(lean), math.sin(lean)
    bend = rng.uniform(0.5, 1.2)
    for f in range(12):
        rng.uniform(-0.2, 0.2); rng.uniform(2.4, 3.3); rng.uniform(0.3, 0.8)
    t = palm_specs.marker(x, y, z, h, ax * bend, ay * bend, kind)
    M["AD_palmt"].add(t, [UP, UP, UP])


def tan_plain(ctx, F, zb, zf, ztop):
    """A short face of the tan house: plain tan stucco under its cornice (v2 0:07:48), a glazed arch under the veranda."""
    M = ctx.M; L = F.L
    holes = [opening(L / 2, 1.3, zf, zf + 2.5, 0.65)] if L > 2.3 else []
    wall_with(M, F, "AD_tan", 0.0, L, zb, ztop, holes)
    for h in holes:
        window_full(M, F, h, frame_m="AD_trim", reveal="AD_tan", depth=0.3, du=0.33, dz=0.5)
    cornice(M, F, 0.0, L, ztop, out=0.4)


def tan_gable(ctx, F, zb, zf, ztop):
    """The tan house's face next to the Pirates' right bay: its round gable with the sunburst lunette (pc4-6, v2
    0:07:48: right beside the Pirates' cornice), plain stucco, a glazed arch under the veranda."""
    M = ctx.M; L = F.L
    tan_plain(ctx, F, zb, zf, ztop)
    sg = L / 2
    gab = sbox(0.0, ztop - 0.05, L, ztop + 0.3).union(ellipse(sg, ztop + 0.3, L / 2 - 0.1, 1.35, 24).intersection(sbox(0, ztop + 0.3, L, ztop + 3)))
    F.plate(M["AD_tan"], gab, d=0.0, t=0.4)
    F.plate(M["AD_trim"], gab.difference(gab.buffer(-0.13, join_style=2)).difference(sbox(-1, ztop - 1, L + 1, ztop + 0.31)), d=0.07, t=0.07)
    niche = ellipse(sg, ztop + 0.35, L / 2 - 0.55, 0.98, 24).intersection(sbox(0, ztop + 0.35, L, ztop + 3))
    recess(M, F, niche, 0.12, "AD_tan", fill="AD_tan2")
    c = F.P(sg, ztop + 0.37, -0.08)
    for i in range(13):                                                  # the sunburst
        t = math.pi * (i + 0.5) / 13
        r = F.E * math.cos(t) * (L / 2 - 0.65) + UP * math.sin(t) * 0.88; t2 = F.E * -math.sin(t) + UP * math.cos(t)
        tri(M["AD_signg" if i % 2 else "AD_orange"], c + r * 0.4 + t2 * 0.08, c + r * 0.4 - t2 * 0.08, c + r, F.N)
    sphere(M["AD_signg"], c, 0.28, n=10, m=5, sc=(1, 0.25, 1))
    F.box(M["AD_brick"], L - 0.3, ztop + 0.9, -1.2, 0.35, 0.5, 1.1)                 # the chimney behind (v2 0:07:48)
    F.box(M["AD_trim"], L - 0.3, ztop + 2.05, -1.2, 0.42, 0.57, 0.06)


def tan_main(ctx, F, zb, zf, ztop):
    """The tan house's main face, angling back (pc4-6 right, v2 0:07:48): plain tan stucco with the teal ship plaque,
    glazed arches under the veranda, the cornice; the veranda in front of the whole tan front (white posts, a lattice
    valance with a scalloped edge, a sloping pinkish metal roof with standing seams) and its hanging oval sign."""
    M = ctx.M; L = F.L
    gw = [opening(s, 1.45, zf, zf + 2.5, 0.72) for s in (1.6, L - 1.6)]
    wall_with(M, F, "AD_tan", 0.0, L, zb, ztop, gw)
    for h in gw:
        window_full(M, F, h, frame_m="AD_trim", reveal="AD_tan", depth=0.3, du=0.36, dz=0.5)
    cornice(M, F, 0.0, L, ztop, out=0.4)
    ship = unary_union([Polygon([(-0.75, -0.2), (0.75, -0.2), (0.55, -0.45), (-0.55, -0.45)]),
                        Polygon([(-0.1, -0.15), (-0.1, 0.55), (-0.6, -0.12)]), Polygon([(0.05, -0.15), (0.05, 0.45), (0.5, -0.12)])])
    F.plate(M["AD_tealdoor"], shapely.affinity.translate(ship, L * 0.55, zf + 5.3), d=0.04, t=0.04)
    R = pc_R()
    for a, b in ((R, osm_pt(65)), (osm_pt(65), osm_pt(63)), (osm_pt(63), osm_pt(62))):
        veranda(M, Face(a, b), zf, ctx)
    Fv = Face(R, osm_pt(65))
    Fv.plate(M["AD_sign"], ellipse(Fv.L / 2, zf + 2.55, 0.5, 0.3), d=2.55)
    Fv.plate(M["AD_trim"], ellipse(Fv.L / 2, zf + 2.55, 0.56, 0.36).difference(ellipse(Fv.L / 2, zf + 2.55, 0.5, 0.3)), d=2.55)


def veranda(M, F, zf, ctx, dep=2.6):
    zv = zf + 3.1
    L = F.L
    ps = np.linspace(0.15, L - 0.15, max(2, int(L / 2.4) + 1))
    for s in ps:
        frustum(M["AD_trim"], F.P(s, zf, dep), F.P(s, zv + 0.5, dep), 0.075, 0.075, n=8)
        frustum(M["AD_trim"], F.P(s, zf, dep), F.P(s, zf + 0.4, dep), 0.13, 0.1, n=8)
        F.box(M["AD_trim"], s, zv + 0.45, dep, 0.12, 0.12, 0.08)
    val = sbox(0.0, zv, L, zv + 0.55)
    F.plate(M["AD_trim"], lattice_geom(val), d=dep + 0.02)
    F.plate(M["AD_trim"], unary_union([ellipse(s, zv, 0.16, 0.13, 8).intersection(sbox(s - 1, zv - 1, s + 1, zv)) for s in np.arange(0.17, L, 0.34)]), d=dep + 0.02)
    quad(M["AD_vroof"], F.P(-0.05, zv + 1.4), F.P(L + 0.05, zv + 1.4), F.P(L + 0.05, zv + 0.6, dep + 0.25), F.P(-0.05, zv + 0.6, dep + 0.25), UP)
    quad(M["AD_trim"], F.P(0.0, zv + 0.58), F.P(L, zv + 0.58), F.P(L, zv + 0.58, dep), F.P(0.0, zv + 0.58, dep), -UP)
    for s in np.arange(0.3, L, 0.5):
        bar(M["AD_vroof"], F.P(s, zv + 1.42), F.P(s, zv + 0.62, dep + 0.25), w=0.02, d=0.03)
    F.box(M["AD_trim"], L / 2, zv + 0.63, dep + 0.22, L / 2 + 0.05, 0.05, 0.05)


def pc_umbrella_spots():
    """In front of the veranda (pc2, pc6): blue / white umbrellas with a white fringe."""
    out = []
    for a, b, ss in ((pc_R(), osm_pt(65), (1.4,)), (osm_pt(63), osm_pt(62), (1.4, 4.6))):
        F = Face(a, b)
        out += [F.p(s, 4.6) for s in ss]
    return out


# ---- Cafe Orleans
def co_blue(ctx, zb, zf, ztop):
    """Cafe Orleans row, left (co2, co3): the grey-blue house; recessed arched dark-wood doors, arched French windows
    with curtains, a two-storey grey cast-iron gallery from the pavement with lace arches, hanging baskets, cresting."""
    M = ctx.M
    F = Face(*co_line("blue")); L = F.L
    z1, z2 = zf + 4.0, zf + 7.4
    ss = (L / 6, L / 2, 5 * L / 6)
    gd = [opening(s, 1.35, zf, zf + 2.55, 0.68) for s in ss]
    up = [opening(s, 1.05, z + 0.25, z + 2.25, 0.52) for z in (z1, z2) for s in ss]
    wall_with(M, F, "AD_oblue", 0.0, L, zb, ztop, gd + up)
    for h in gd:
        x0, y0, x1, y1 = h.bounds
        recess(M, F, h, 0.35, "AD_oblue", fill="AD_door")
        F.plate(M["AD_glass"], h.intersection(sbox(x0, zf + 1.2, x1, y1 + 1)).buffer(-0.12), d=-0.33)
        bars(M, "AD_door", F, h.intersection(sbox(x0, zf + 1.2, x1, y1 + 1)), -0.32, du=0.34, dz=0.36, w=0.035)
        frame(M, "AD_trim", F, h, 0.12, d=0.0)
    for h in up:
        window_full(M, F, h, frame_m="AD_trim", reveal="AD_oblue", depth=0.3, du=0.52, dz=0.45, curtains=True)
    cornice(M, F, 0.0, L, ztop, out=0.35)
    gallery(M, F, 0.1, L - 0.1, [z1, z2], ztop - 0.75, 2.0, "AD_giron", zground=zf, bays=3, boxes=("AD_fl_red",),
            cresting=True, spandrel=0.95)
    for sa, sb in zip(np.linspace(0.1, L - 0.1, 4)[:-1], np.linspace(0.1, L - 0.1, 4)[1:]):    # hanging baskets
        for zc in (z2, ztop - 0.75):
            p = F.P((sa + sb) / 2, zc - 1.35, 1.6)
            bar(M["AD_rope"], p, p + UP * 1.2, w=0.01, d=0.01)
            sphere(M["AD_leaf"], p, 0.3, n=7, m=4)
            sphere(M["AD_leaf"], p - UP * 0.3, 0.18, n=6, m=3, sc=(1, 1, 1.5))
            sphere(M["AD_fl_red"], p + UP * 0.15 + F.N * 0.18, 0.13, n=6, m=3)


def co_cream(ctx, zb, zf, ztop):
    """Cafe Orleans itself (co1-3): cream stucco; a curved gable with an oculus and a chimney at each end; louvred vents;
    shuttered top-floor windows on little balconies; arched first-floor windows, a balcony across with the sign;
    white small-paned French doors behind a red scalloped awning."""
    M = ctx.M
    F = Face(*co_line("cream")); W = F.L
    z1, z2 = zf + 4.0, zf + 7.4
    sm = W / 2
    s2 = (W * 0.28, W * 0.72)
    shop = sbox(0.35, zf, W - 0.35, zf + 2.9)
    win1 = [opening(s, 1.05, z1 + 0.3, z1 + 2.05, 0.52) for s in s2]
    win2 = [opening(s, 0.95, z2 + 0.35, z2 + 2.15) for s in s2]
    vents = [sbox(s - 0.35, ztop - 1.4, s + 0.35, ztop - 1.0) for s in s2]
    wall_with(M, F, "AD_cream", 0.0, W, zb, ztop, [shop] + win1 + win2 + vents)
    # the shop front: French doors with small panes between white mullions
    recess(M, F, shop, 0.25, "AD_trim", fill="AD_glass")
    for s in np.linspace(0.35, W - 0.35, 5):
        F.box(M["AD_trim"], s, zf + 1.45, -0.2, 0.07, 0.05, 1.45)
    bars(M, "AD_trim", F, shop, -0.22, du=0.29, dz=0.42, w=0.025)
    F.box(M["AD_trim"], sm, zf + 0.25, -0.2, W / 2 - 0.35, 0.05, 0.25)
    for h in win1:
        x0, y0, x1, y1 = h.bounds
        window_full(M, F, h, reveal="AD_cream", depth=0.3, du=0.52, dz=0.4, curtains=True, sill=False)
        shutter_pair(M, F, (x0 + x1) / 2, x1 - x0, y0, y1 - 0.2, "AD_louver", "AD_louverd")
    for h in win2:
        x0, y0, x1, y1 = h.bounds
        window_full(M, F, h, reveal="AD_cream", depth=0.3, du=0.48, dz=0.45, sill=False)
        shutter_pair(M, F, (x0 + x1) / 2, x1 - x0, y0 + 0.9, y1, "AD_louver", "AD_louverd", open_=False)
        shutter_pair(M, F, (x0 + x1) / 2, x1 - x0, y0, y1, "AD_louver", "AD_louverd")
        balcony(M, F, (x0 + x1) / 2 - 0.85, (x0 + x1) / 2 + 0.85, y0 - 0.05, 0.55, iron="AD_black", slab="AD_black", boxes=("AD_fl_red",))
    for h in vents:
        recess(M, F, h, 0.15, "AD_trim", fill="AD_text")
        bars(M, "AD_louver", F, h, -0.08, dz=0.07, w=0.03)
        frame(M, "AD_trim", F, h, 0.08)
    balcony(M, F, 0.25, W - 0.25, z1 + 0.05, 0.75, iron="AD_black", slab="AD_black", boxes=("AD_fl_red", "AD_fl_pur"))
    F.box(M["AD_trim"], sm, z2 - 0.05, 0.08, W / 2, 0.08, 0.08)
    cornice(M, F, 0.0, W, ztop, out=0.35)
    # the gable: concave shoulders, a round top, the oculus; chimneys
    pts = [(sm - W / 2, ztop)]
    pts += [(sm - 2.2 + math.sin(t), ztop + 1.5 - math.cos(t)) for t in np.linspace(0, math.pi / 2, 7)]
    pts += [(sm - 1.2 * math.cos(t), ztop + 1.5 + 1.2 * math.sin(t)) for t in np.linspace(0, math.pi, 13)[1:-1]]
    pts += [(sm + 2.2 - math.sin(t), ztop + 1.5 - math.cos(t)) for t in np.linspace(math.pi / 2, 0, 7)]
    pts += [(sm + W / 2, ztop)]
    gab = Polygon(pts).buffer(0)
    ocu = Point(sm, ztop + 1.55).buffer(0.4, 16)
    F.plate(M["AD_cream"], gab.difference(ocu), d=0.0, t=0.35)
    F.plate(M["AD_trim"], gab.difference(gab.buffer(-0.14, join_style=2)).difference(sbox(-1, ztop - 1, W + 1, ztop + 0.05)), d=0.07, t=0.07)
    recess(M, F, ocu, 0.3, "AD_cream", fill="AD_glass")
    frame(M, "AD_trim", F, ocu, 0.12)
    for s in (0.45, W - 0.45):
        F.box(M["AD_brick"], s, ztop + 1.0, -0.55, 0.32, 0.42, 1.25)
        F.box(M["AD_trim"], s, ztop + 2.3, -0.55, 0.4, 0.5, 0.07)
    # the sign on the balcony
    F.box(M["AD_black"], sm, z1 + 1.35, 0.92, 1.32, 0.06, 0.36)
    F.box(M["AD_sign"], sm, z1 + 1.35, 0.97, 1.2, 0.03, 0.28)
    loft_rect(M["AD_black"], F.P(sm, z1 + 1.7, 0.92), F.e, F.n, [(1.38, 0.13, 0.0), (1.2, 0.04, 0.16)])
    F.plate(M["AD_signr"], shapely.affinity.translate(text_poly("CAFE ORLÉANS", 0.2, "georgiab.ttf"), sm, z1 + 1.35), d=1.01)
    # the awning
    aw = 1.7
    quad(M["AD_awning"], F.P(0, z1 - 0.2, 0.05), F.P(W, z1 - 0.2, 0.05), F.P(W, z1 - 0.95, aw), F.P(0, z1 - 0.95, aw), UP + F.N)
    F.plate(M["AD_awning"], sbox(0.0, z1 - 1.3, W, z1 - 0.95).union(unary_union(
        [ellipse(s, z1 - 1.3, 0.2, 0.14, 8).intersection(sbox(s - 1, z1 - 2, s + 1, z1 - 1.3)) for s in np.arange(0.2, W, 0.4)])), d=aw)
    for s in (0, W):
        tri(M["AD_awning"], F.P(s, z1 - 0.2, 0.05), F.P(s, z1 - 0.95, aw), F.P(s, z1 - 1.3, aw), F.E)
    F.plate(M["AD_umb_w"], shapely.affinity.translate(text_poly("CAFE ORLÉANS", 0.16, "georgiab.ttf"), sm, z1 - 1.13), d=aw + 0.02)
    for s in (0.0, W):
        x, y = F.p(s, 3.0)
        lamp_arms(M, x, y, ctx.gr.z(x, y), F.e, top=False, h=3.2)
        ctx.fixed_lamps.append((x, y))


def co_salmon(ctx, zb, zf, ztop):
    """Cafe Orleans row, right (co2, co3): the salmon house, 2 storeys under the slate roof with a dormer; recessed green
    arched French doors with fanlights, tall green-shuttered windows, a white lace gallery on green posts."""
    M = ctx.M
    F = Face(*co_line("salmon")); s0, s1 = 0.0, F.L
    z1 = zf + 4.0
    xs = np.linspace(s0, s1, 4)
    ss = (xs[:-1] + xs[1:]) / 2
    gd = [opening(s, 1.45, zf, zf + 2.5, 0.72) for s in ss]
    up = [opening(s, 1.1, z1 + 0.25, z1 + 2.75) for s in ss]
    wall_with(M, F, "AD_osalmon", s0, s1, zb, ztop, gd + up)
    for h in gd:
        x0, y0, x1, y1 = h.bounds
        recess(M, F, h, 0.35, "AD_osalmon")
        F.plate(M["AD_odoor"], h.intersection(sbox(x0, y0, x1, zf + 2.5)), d=-0.35)
        F.plate(M["AD_glass"], h.intersection(sbox(x0, zf + 2.55, x1, y1 + 1)), d=-0.34)
        for s in ((x0 + x1) / 2 - 0.36, (x0 + x1) / 2 + 0.36):
            F.box(M["AD_glass"], s, zf + 1.55, -0.32, 0.24, 0.01, 0.75)
            bars(M, "AD_odoor", F, sbox(s - 0.24, zf + 0.8, s + 0.24, zf + 2.3), -0.3, du=0.24, dz=0.3, w=0.03)
        for i in range(1, 6):
            t = math.pi * i / 6
            c = F.P((x0 + x1) / 2, zf + 2.5, -0.3)
            bar(M["AD_trim"], c, c + F.E * 0.72 * math.cos(t) + UP * 0.72 * math.sin(t), w=0.025, d=0.02)
        frame(M, "AD_trim", F, h, 0.12)
    for h in up:
        x0, y0, x1, y1 = h.bounds
        window_full(M, F, h, reveal="AD_osalmon", depth=0.3, du=0.55, dz=0.45, curtains=True)
        shutter_pair(M, F, (x0 + x1) / 2, x1 - x0, y0, y1, "AD_shutter", "AD_odoor")
    cornice(M, F, s0, s1, ztop, out=0.35)
    gallery(M, F, s0 + 0.1, s1 - 0.1, [z1], zf + 7.3, 2.2, "AD_trim", cols="AD_shutter", lace="AD_trim", zground=zf,
            bays=4, boxes=("AD_fl_org", "AD_fl_yel", "AD_fl_red"), spandrel=0.85)
    p = F.p((s0 + s1) / 2, -1.3)                                         # the dormer
    box(M["AD_osalmon"], P3(p, ztop + 0.8), (0.7, 0.6, 0.8), F.B)
    quad(M["AD_glass"], P3(p + F.e * -0.35 + F.n * 0.62, ztop + 0.3), P3(p + F.e * 0.35 + F.n * 0.62, ztop + 0.3),
         P3(p + F.e * 0.35 + F.n * 0.62, ztop + 1.3), P3(p + F.e * -0.35 + F.n * 0.62, ztop + 1.3), F.N)
    bar(M["AD_trim"], P3(p + F.n * 0.64, ztop + 0.3), P3(p + F.n * 0.64, ztop + 1.3), w=0.03, d=0.02)
    loft_rect(M["AD_slate"], P3(p, ztop + 1.6), F.e, F.n, [(0.85, 0.75, 0.0), (0.05, 0.75, 0.6)])


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


def umbrella(M, x, y, z, r=1.4, h=2.4, mats=("AD_umb_o",), table=True, fringe=None):
    frustum(M["AD_iron"], (x, y, z), (x, y, z + h + 0.3), 0.03, 0.03, n=4)
    n = 8
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        tri(M[mats[k % len(mats)]], (x, y, z + h + 0.45), (x + r * math.cos(a0), y + r * math.sin(a0), z + h),
            (x + r * math.cos(a1), y + r * math.sin(a1), z + h), UP)
        if fringe:                                       # a scalloped valance round the rim (Cafe Orleans)
            p0 = np.array([x + r * math.cos(a0), y + r * math.sin(a0), z + h])
            p1 = np.array([x + r * math.cos(a1), y + r * math.sin(a1), z + h])
            o = np.array([math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0.0])
            quad(M[fringe], p0, p1, p1 - UP * 0.16, p0 - UP * 0.16, o)
            for t in (0.25, 0.75):
                m = p0 + (p1 - p0) * t
                tri(M[fringe], m - (p1 - p0) * 0.25 - UP * 0.16, m + (p1 - p0) * 0.25 - UP * 0.16, m - UP * 0.3, o)
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
                h = 6.0 if poly.area > 1000 else 5.0       # show buildings stay under the sight line over the facades (v2 0:07:48)
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
                umbrella(M, x, y, gr.z(x, y), r=1.3, mats=("AD_umb_r",), fringe="AD_umb_w"); n_umb += 1   # co1-3
    for x, y in ((-262, 776), (-257, 769), (-267, 768), (-262, 761), (-270, 780)):
        if free(x, y):
            umbrella(M, x, y, gr.z(x, y), r=1.9, h=2.6, mats=("AD_umb_o",)); n_umb += 1
    for x, y in pc_umbrella_spots():                      # blue / white umbrellas in front of the veranda (pc2, pc6)
        if free(x, y):
            umbrella(M, x, y, gr.z(x, y), r=1.5, mats=("AD_umb_t", "AD_umb_w"), fringe="AD_umb_w"); n_umb += 1
    info["umbrellas"] = n_umb
    # the terrace's entrance before Cafe Orleans (co3): brick piers with white cherubs
    Fc = Face(*co_line("cream"))
    for sg in (-1, 1):
        x, y = Fc.p(Fc.L / 2 + sg * 1.7, 13.0)
        if free(x, y) or pv.buffer(1.0).contains(Point(x, y)):
            z = gr.z(x, y)
            box(M["AD_brick"], (x, y, z + 0.5), (0.32, 0.32, 0.5))
            box(M["AD_trim"], (x, y, z + 1.04), (0.38, 0.38, 0.05))
            lathe(M["AD_trim"], (x, y, z + 1.09), [(0.18, 0), (0.2, 0.25), (0.13, 0.55), (0.0, 0.6)], n=8)
            sphere(M["AD_trim"], (x, y, z + 1.75), 0.13, n=8, m=5)
            for w in (-1, 1):
                q = np.array([x, y, z + 1.5]) + np.r_[Fc.e, 0] * w * 0.12
                tri(M["AD_trim"], q, q + np.r_[Fc.e, 0] * w * 0.28 + UP * 0.25, q + UP * 0.3 - np.r_[Fc.n, 0] * 0.1, np.r_[Fc.n, 0])
    # lamps (along the facades, and along the beds elsewhere; the photographed facades placed their own)
    lamps = list(ctx.fixed_lamps)
    n_fixed = len(lamps)
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
    for x, y in lamps[n_fixed:]:
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
