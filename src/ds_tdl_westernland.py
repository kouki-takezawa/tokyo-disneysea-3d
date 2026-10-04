"""ウエスタンランド -- Westernland of Tokyo Disneyland: the frontier town round its big rose-paved plaza, Big Thunder
Mountain, the Mark Twain landing with the riverboat, Camp Woodchuck, the Western River Railroad's track and trestles, the
Rivers of America banks and Tom Sawyer Island (video-frame plan, range 2; plain Python, Blender is not needed; no trees,
no palms, no round clipped shrubs, no night version):

  python src/ds_tdl_westernland.py     # -> output/disneysea/models/tdl_west_ground.json (ground, beds, kerbs, marks)
                                       #    + output/disneysea/models/tdl_westernland.json (buildings, rocks, props, planting)
  python src/ds_ground.py tdl_land_ground   # the Land's ground, now cut round tdl_west_ground
  python src/export_mock.py            # rebuilds the page (layer ディズニーランド)

Sources (docs/video_frames/range2.md has the frame list):
  video frames (view only, never copied or used as textures): v2 (daytime) -- the Westernland bridge by the hub with its
    X-braced timber railings (0:15:04), the Diamond Horseshoe (cream, two storeys, red arched doors, a gallery with gilt
    ornaments and pink awnings, the corner sign; 0:16:40-0:16:46), the big plaza (rose-red paving, yellow and white dash
    marks, boulder-kerbed beds; 0:16:52-0:17:58), the Hungry Bear / Country Bear log buildings (stone chimney, log gallery,
    cedar shingles, the COUNTRY BEAR JAMBOREE banner; 0:17:22, 0:18:10), the covered wagon and the bear statue (0:17:16,
    0:18:04), the shop row (cream clapboard with a lace valance and a balcony with flower boxes, red board-and-batten
    false front "Land Enterprise Co.", boardwalks; 0:18:16-0:18:28), the stone house, the green clapboard house and the
    brick TOWN HALL with a white portico, balcony and cupola (0:18:52-0:19:10), the log-rail fences, wagon wheels and log
    wagon (0:18:40), Big Thunder Mountain (red-orange fluted rock with strata, the timber mine structures, head-frame
    tower, stack, a round hedge with radial yellow dashes, grey-beige asphalt, weathered board planters, red boulders;
    0:19:14-0:19:44), the Western River Railroad trestle over the path (0:19:32-0:19:44, 0:21:20), the river path (rose
    paving, log fences, board planters, green benches; 0:20:02-0:20:56), the landing's forecourt (a pale cobbled circle
    with a mint border, yellow flower bed; 0:20:38-0:21:14); v1 (dusk) 0:58:00-1:08:10 for the shapes: the landing
    building (red brick, arched windows, green roofs, a white portico, the central tower and two small domes; 0:59:40-
    1:00:00), the riverboat, the log fences and lanterns on the river path (1:00:40-1:02:00), Big Thunder's front with
    the old locomotive, cacti and rope queue (1:03:40-1:04:40), the shop row with galleries (1:05:00-1:07:40).
  OSM (plateau_data/disneyland_osm.json): the building ways below; gardens, grass, forest, scrub, sand; water (Rivers of
    America 1125423); the narrow-gauge railway ways (ウエスタンリバー鉄道) with their bridge/tunnel tags; the roller
    coaster track ways of Big Thunder (tunnel / layer tags); POIs for the shop names (トレーディングポスト, ゼネラル
    ストア, ウエスタンウエア, ウエスタンランド写真館, カントリーベア・シアター, ハングリーベア・レストラン, ザ・ダイヤモンド
    ホースシュー, ペコスビル・カフェ, フロンティア・ウッドクラフト, カウボーイ・クックハウス, ハッピーキャンパーサプライ,
    ウエスタンランド・シューティングギャラリー, キャンプ・ウッドチャック・キッチン).
  Google's satellite view at zoom 19 (0.2425 m per pixel, centred on the requested point): the roofs (the Trading Post
    block's red roof, the grey roofs of the Hungry Bear block, the landing's green roof), the rock extent of Big Thunder
    (inside the railway loop), the pink-red paving and where it turns grey-beige (Big Thunder front, Camp Woodchuck).
  web (general knowledge, names checked on tokyodisneyresort.jp): Big Thunder Mountain (1987, a mine train through red
    sandstone spires modelled on Monument Valley), the Mark Twain Riverboat (a three-deck stern-wheeler, twin black stacks,
    the landing's Victorian house), Tom Sawyer Island (rafts from the landing by Camp Woodchuck; Fort Sam Clemens, a log
    stockade; Harper's Mill with its wheel; the tipis of the camp), the Diamond Horseshoe (a saloon-theatre restaurant),
    Pecos Bill Cafe, Country Bear Theater, the Western River Railroad (a narrow-gauge steam line on a berm and trestles).

What is modelled (every height is an ESTIMATE: ground floor 3.9 m, upper 3.2 m, false fronts 1-2 m over the eaves):
  town        the public edges of each building become a row of false-front storefronts 6-10 m wide (red board-and-
              batten, grey weathered boards, cream / green / yellow clapboard, logs, sandstone, brick), with a raised
              timber boardwalk (0.28 m, walkable), a veranda on posts or a two-storey gallery with railings and flower
              boxes, doors, sash windows, cornices with brackets, hanging and fascia signs (text_poly letters), lanterns;
              the backs are plain board walls; the roofs are cedar shingle hips (grey tin on the big blocks).
  landmarks   the Diamond Horseshoe and Pecos Bill (the Westernland half of way 196942701, split with ds_tdl_plaza_hub
              via DH_PART), the log Hungry Bear / Country Bear block (stone chimney, banner), the brick Town Hall with its
              portico and cupola, the Assayer's Office with its water tank, the Big Thunder station (timber, two storeys),
              the Mark Twain landing (brick, green roofs, a white portico, the tower and two domes) with its pier and the
              riverboat moored there (hull, three decks with railings, twin stacks, pilot house, red stern wheel).
  Big Thunder a mass of fluted red sandstone spires over the mountain footprint (MOUNTAIN: the show buildings and the
              sand ways inside the railway loop), each spire a stack of irregular prisms banded by height (three reds),
              cliffs round the edge; the coaster track (the non-tunnel OSM track ways) on timber bents; mine shacks, a
              head-frame tower, a brick stack and a water tower on the rocks; low cacti, agaves and boulders at the base.
  railway     the Western River Railroad's narrow-gauge ways in the area: ballast, ties and rails on the ground, on a
              timber trestle (deck, bents, railings) where they cross the guest paths (plus the OSM bridge ways).
  island      Tom Sawyer Island's buildings: Fort Sam Clemens as log blockhouses in a pointed-log stockade, tipis at the
              camp, Harper's Mill with a wheel, log cabins; the burning cabin on the far bank.
  ground      (tdl_west_ground) the guest area of the land (ds_ground's Westernland region inside BOX, minus the models
              already there and the water): rose-red paving (the plaza, the street, the river path), grey-beige asphalt
              (Big Thunder front and Camp Woodchuck, Z_TAN), sandy dirt (the OSM sand ways, the island, the far bank),
              a pale cobbled circle with a mint band in front of the landing, yellow / white dash marks; stone river-bank
              edges; every OSM garden / grass / forest / scrub as a bed: boulder kerbs in the town, weathered board
              planters by Big Thunder and on the river path, a soil ribbon with flowers, grasses and ferns, a shrub mass
              inside (the page's hedge shader, key WG_soil).
  details     log-rail fences along the river and the beds, hitching rails, water troughs, barrels, crates, hay bales,
              wagon wheels, the covered wagon, a log wagon, the bear statue, lamps (lantern posts), green benches, wooden
              bins, flag pole, rope queue posts at Big Thunder, planters with flowers, sage-like shrubs, grass tufts.
ESTIMATES: all heights; which edge carries which storefront style (drawn per segment with a fixed seed, the landmark ones
  placed on the edges named in FRONTS); the rock heights (a height field peaking at 30 m); the coaster heights; the
  railway's berm and trestle heights (4.8 m clearance); the zones' borders (hand drawn polygons, +-5 m); plant scatter.
  Interiors are not modelled: doors are closed.
Walk: buildings are closed solids; boardwalks (0.28 m) and the landing pier are walkable steps; bed kerbs 0.35 m and board
  planters 0.6 m are walls; the railway trestles are above head height; fences are walls.
Frame: the mock's local metres (+x east, +y north), z up; plan (x, y, z) -> glTF (x, z, -y) by ds_tdl_ground.write_gltf.
"""
import sys, math, pathlib

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, MultiPoint, box as sbox
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, substring

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
import ds_ground as GR
from ds_tdl_plaza_center import tri, frustum, box, lathe, sphere, Surface
from ds_tdl_plaza_hub import load_tris, quad, P3, UP, loft_rect, arched_window, bar, DH_PART
from ds_tdl_tomorrowland_terrace import polys, cap, sides, plate, text_poly
from ds_tdl_adventureland import ring_edges, rect_of, B3, hip_strip, closed_polys, grid_lines, checker

MODELS = ROOT / "output" / "disneysea" / "models"
OUT_G = MODELS / "tdl_west_ground.json"
OUT_B = MODELS / "tdl_westernland.json"

BOX = sbox(-352.0, 488.0, 70.0, 722.0)
# Fantasyland / Critter Country corners inside BOX (their ground and buildings are left alone)
FANTASY = Polygon([(-352, 488), (-352, 614), (-286, 614), (-240, 612), (-240, 560), (-225, 540), (-222, 488)])
# the 13 small OSM ways on the west of the Hungry Bear block are the piers of its log gallery, not buildings
PIERS = tuple(range(1298740615, 1298740628))
CUT_MODELS = ("tdl_plaza_ground", "tdl_plaza_hub", "tdl_plaza_center", "tdl_adv_ground", "tdl_adventureland", "tdl_water")
WATER_REL = 1125423
# OSM ids
PAVILION = 196942701                 # its Westernland half (DH_PART) is the Diamond Horseshoe + Pecos Bill Cafe
TRADING, BEARS, SMALL_STONE = 1239567026, 163053907, 227754663
ASSAYER = 1116316887
BT_STATION, BT_SHED, DIORAMA = 17739030, 1293816876, 72865512
BT_SHOW = (1294893202, 1294893203, 1294893204)
MOUNTAIN_SAND = (258432731, 1058049810, 258432729, 305168858, 1054306118)
LANDING = 218979636
FORT = (779793839, 779793840, 779793841, 779793842, 779793843, 1294689579, 1294689580)
MILL = 1294689557
WOODCHUCK = (763060486, 1289598789, 1289598790, 1289598791, 1289598792, 1289598796, 1289598798, 1077351363)
BRIDGE_WAY = 1288837469              # the timber footbridge from the hub into Westernland (its deck is tdl_plaza_ground's)
STREAM_BRIDGE = 1291298629           # the small bridge south of the landing
# ground zones (plan polygons, first match wins; the rest is the rose paving)
Z_TAN = Polygon([(-176, 572), (-176, 628), (-165, 662), (-150, 712), (-20, 712), (-20, 572)])
Z_WILD = Polygon([(-40, 490), (-40, 575), (-20, 575), (-20, 722), (70, 722), (70, 490)])     # the island's east end and the far bank
ISLAND_REL = 17739029
CIRCLE_C, CIRCLE_R = (-203.0, 552.0), 7.5          # the cobbled circle in front of the landing (0:20:38-0:21:14; ESTIMATE of place)
GREEN_LANDUSE = ("grass", "meadow", "flowerbed", "forest", "village_green")
GREEN_NATURAL = ("wood", "scrub", "grassland", "heath")
CURB_H, CURB_W, RIBBON = 0.3, 0.35, 0.8
BOARD_H = 0.6                          # weathered board planters (Big Thunder, the river path)
DECK_H, DECK_D = 0.28, 2.8             # boardwalk height / depth in front of the shops
G_NAMES = ("WG_rose", "WG_rose2", "WG_tan", "WG_tan2", "WG_dirt", "WG_dirt2", "WG_cob", "WG_cob2", "WG_mint", "WG_dash",
           "WG_line", "WG_edge", "WG_stone", "WG_board", "WG_bed", "WG_soil", "WG_bank", "WG_mulch", "WG_grass", "WG_joint")
FLOWERS = ("WL_fl_red", "WL_fl_yel", "WL_fl_pink", "WL_fl_wht", "WL_fl_pur", "WL_fl_org")
WALLS = ("WL_red", "WL_grey", "WL_cream", "WL_green", "WL_yellow", "WL_log", "WL_stone", "WL_brick", "WL_tan", "WL_brown", "WL_blue")
B_NAMES = WALLS + ("WL_logd", "WL_white", "WL_trim", "WL_trimr", "WL_roof", "WL_roofd", "WL_tin", "WL_groof", "WL_glass",
                   "WL_door", "WL_deck", "WL_post", "WL_sign", "WL_signr", "WL_signg", "WL_text", "WL_textw", "WL_gold",
                   "WL_awn", "WL_awnw", "WL_rock1", "WL_rock2", "WL_rock3", "WL_rockd", "WL_cactus", "WL_agave", "WL_rail",
                   "WL_tie", "WL_ballast", "WL_canvas", "WL_wheel", "WL_hay", "WL_barrel", "WL_hoop", "WL_water", "WL_lamp",
                   "WL_glow", "WL_bench", "WL_benchg", "WL_bin", "WL_leaf", "WL_fern", "WL_grass", "WL_sage", "WL_boat",
                   "WL_boatr", "WL_boatk", "WL_boatd", "WL_tipi", "WL_tipid", "WL_show", "WL_chim", "WL_cupola", "WL_iron",
                   "WL_bear", "WL_timber", "WL_flag", "WL_rope", "WL_qpost", "WL_brickd", "WL_lace", "WL_berm") + FLOWERS
RNG = np.random.default_rng(1983)


# ---------------------------------------------------------------- small helpers
def V(p):
    return np.array([p[0], p[1]], float)


def N3(n):
    return np.array([n[0], n[1], 0.0])


def way(i):
    for w in DL.DATA["ways"]:
        if w["id"] == i:
            return w
    return None


def poly_of(i):
    w = way(i)
    if w is not None:
        return Polygon(w["pts"]).buffer(0)
    for r in DL.DATA["relations"]:
        if r["id"] == i:
            return unary_union([Polygon(x).buffer(0) for x in DL.outer_rings(r)])
    return Polygon()


def jitter_ring(c, r, n, amp, rng=RNG, rot=0.0):
    """An irregular n-gon round c (plan): radii r * (1 +- amp)."""
    return [(c[0] + r * (1 + amp * rng.uniform(-1, 1)) * math.cos(rot + 2 * math.pi * k / n),
             c[1] + r * (1 + amp * rng.uniform(-1, 1)) * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def prism(mesh, ring0, z0, ring1, z1, top=True, bottom=False):
    """A solid between two plan rings with the same number of corners (ring0 at z0, ring1 at z1): sides and caps."""
    n = len(ring0)
    c0 = np.mean(np.array(ring0), 0); c1 = np.mean(np.array(ring1), 0)
    for k in range(n):
        a0, b0 = ring0[k], ring0[(k + 1) % n]
        a1, b1 = ring1[k], ring1[(k + 1) % n]
        out = N3((np.array(a0) + np.array(b0)) / 2 - c0)
        quad(mesh, P3(a0, z0), P3(b0, z0), P3(b1, z1), P3(a1, z1), out + UP * 0.1)
        if top:
            tri(mesh, P3(c1, z1), P3(a1, z1), P3(b1, z1), UP)
        if bottom:
            tri(mesh, P3(c0, z0), P3(b0, z0), P3(a0, z0), -UP)


# ---------------------------------------------------------------- the plan
def plan():
    lands = GR.land_regions(BOX)
    area = BOX.intersection(lands["west"].buffer(6.0)).difference(FANTASY)
    cut = unary_union([g for g in (GR.model_footprint(m) for m in CUT_MODELS) if g is not None and not g.is_empty])
    piers = unary_union([poly_of(i) for i in PIERS])
    bld_list = [p for p in closed_polys(lambda t: "building" in t and t["building"] not in ("roof", "no")) if p.intersects(BOX) and not piers.contains(p.centroid)]
    buildings = unary_union(bld_list)
    water = unary_union([p for p in closed_polys(lambda t: t.get("natural") == "water" or bool(t.get("water"))) if p.intersects(BOX)])
    mountain = unary_union([poly_of(i) for i in BT_SHOW + MOUNTAIN_SAND]).buffer(2.5, join_style=1).buffer(-2.5, join_style=1)
    mountain = mountain.difference(poly_of(BT_STATION).buffer(1.2)).difference(poly_of(BT_SHED).buffer(0.5))
    mountain = unary_union([p for p in polys(mountain, 50.0)])
    area = area.difference(cut.buffer(0.05)).difference(water)
    gardens = unary_union([p for p in closed_polys(lambda t: t.get("leisure") == "garden" or t.get("landuse") in GREEN_LANDUSE
                                                   or t.get("natural") in GREEN_NATURAL) if p.intersects(BOX)])
    open_ = area.difference(buildings).difference(mountain.buffer(0.3))
    # guest paths (OSM footways / pedestrian lines and areas) and the railway's berm: the narrow-gauge corridor is planted
    # except where a guest path crosses it (there the track goes over on a trestle)
    pl, pa_ = [], []
    for w in DL.DATA["ways"]:
        hw = w["tags"].get("highway")
        if hw in ("footway", "pedestrian", "path", "steps") and len(w["pts"]) >= 2 and w["tags"].get("tunnel") != "yes":
            if w["closed"] and len(w["pts"]) >= 4 and (hw == "pedestrian" or w["tags"].get("area") == "yes"):
                pa_.append(Polygon(w["pts"]).buffer(0))
            else:
                pl.append(LineString(w["pts"]).buffer(2.2, cap_style=2))
    paths = unary_union(pl + pa_).intersection(BOX.buffer(20))
    rails = [LineString(w["pts"]) for w in DL.DATA["ways"] if w["tags"].get("railway") == "narrow_gauge" and w["tags"].get("tunnel") != "yes" and len(w["pts"]) >= 2]
    berm = unary_union([r.buffer(3.2, cap_style=2) for r in rails]).intersection(open_).difference(paths.buffer(0.6))
    berm = unary_union([q for q in G._polys(berm) if q.area > 6.0])
    gardens = unary_union([gardens, berm])
    beds = [q for q in G._polys(open_.intersection(gardens)) if q.area >= 2.0]
    beds = [q.buffer(-0.02, join_style=2) for q in beds]
    beds = [q for q in beds if not q.is_empty and q.geom_type == "Polygon"]
    paving = unary_union([p for p in G._polys(open_.difference(unary_union(beds).buffer(0.02))) if p.area > 1.0])
    sand = unary_union([p for p in closed_polys(lambda t: t.get("natural") == "sand") if p.intersects(BOX)]).difference(mountain)
    island = poly_of(ISLAND_REL).buffer(4.0)
    return dict(area=area, paving=paving, beds=beds, buildings=buildings, water=water, cut=cut, mountain=mountain,
                sand=sand, island=island, bld_list=bld_list, paths=paths, berm=berm)


def zone_of_pt(p, P):
    if Z_WILD.contains(p) or P["island"].contains(p):
        return "wild"
    if Z_TAN.contains(p):
        return "tan"
    return "rose"


def zone_of(q, P):
    return zone_of_pt(q.representative_point(), P)


def surface(meshes, T, name, geom, dz=0.0, skirt="WG_edge", kerb=None):
    """Terrain (+dz) over geom; its free edges get a skirt (or a kerb face down to the terrain when raised)."""
    tris = []
    for poly in G._polys(geom):
        if poly.area > 1e-3:
            tris += G.top_surface(meshes[name], T, poly, dz=dz)
    for a, b in G.free_edges(tris):
        za, zb = float(T.z(a[0], a[1])) + dz, float(T.z(b[0], b[1])) + dz
        G.wall(meshes[kerb or skirt], a, b, za, zb, za - dz - 0.15, zb - dz - 0.15)
    return tris


def add_bed(meshes, T, q, kind):
    """A bed: kerb ring (stones, or weathered boards standing BOARD_H high), a soil ribbon, a shrub mass inside (WG_soil)."""
    h = BOARD_H if kind == "board" else CURB_H
    mat = {"board": "WG_board", "stone": "WG_stone", "wild": "WG_dirt2"}[kind]
    q = orient(q, 1.0)
    w = 0.12 if kind == "board" else CURB_W
    q_in = q.buffer(-w, join_style=2)
    ring = q.difference(q_in) if not q_in.is_empty else q
    tris = []
    if kind == "wild":
        h = 0.08
    for poly in G._polys(ring):
        tris += G.top_surface(meshes[mat], T, poly, dz=h)
    for a, b in G.free_edges(tris):
        za, zb = float(T.z(a[0], a[1])) + h, float(T.z(b[0], b[1])) + h
        G.wall(meshes[mat], a, b, za, zb, za - h - 0.1, zb - h - 0.1)
    if q_in.is_empty:
        return None, None, h
    soil_h = h - (0.1 if kind == "board" else 0.06)
    inner = q_in.buffer(-RIBBON, join_style=2) if q_in.area > 8.0 else Polygon()
    rib = q_in.difference(inner) if not inner.is_empty else q_in
    for poly in G._polys(rib):
        G.top_surface(meshes["WG_grass" if kind == "wild" else ("WG_mulch" if kind == "board" else "WG_bed")], T, poly, dz=soil_h)
    for poly in G._polys(inner):
        G.top_surface(meshes["WG_soil"], T, poly, dz=soil_h)
    return rib, inner, soil_h


def dash_rows(geom, P, step=5.5):
    """Yellow parade dashes (0:18:28, 0:18:40): rows parallel to the building fronts, 5.5 m apart, dashes 1.2 m every 3 m."""
    out = []
    bl = P["buildings"]
    for d in (4.5, 4.5 + step, 4.5 + 2 * step):
        ring = bl.buffer(d, join_style=2).boundary.intersection(geom.buffer(-0.8))
        for ls in getattr(ring, "geoms", [ring]):
            if ls.geom_type != "LineString" or ls.length < 4:
                continue
            for s in np.arange(1.0, ls.length - 1.2, 3.0):
                seg = substring(ls, s, s + 1.2)
                if seg.length > 0.6:
                    out.append(seg.buffer(0.06, cap_style=2))
    return unary_union(out) if out else Polygon()


def build_ground():
    P = plan()
    void = unary_union([P["buildings"], P["water"], P["mountain"]]).buffer(3.0)
    T = G.Terrain(P["area"].buffer(10).bounds, void=void)
    meshes = {n: G.Mesh(n) for n in G_NAMES}
    pav = P["paving"]
    island = P["island"]
    # zones of the paving
    wild = pav.intersection(unary_union([Z_WILD, island]))
    rest = pav.difference(Z_WILD).difference(island)
    tan = rest.intersection(Z_TAN)
    rose = rest.difference(Z_TAN)
    dirt_extra = rose.intersection(P["sand"]).union(tan.intersection(P["sand"]))
    rose = rose.difference(P["sand"]); tan = tan.difference(P["sand"])
    circle = Point(*CIRCLE_C).buffer(CIRCLE_R, 48).intersection(rose)
    band = circle.difference(Point(*CIRCLE_C).buffer(CIRCLE_R - 0.7, 48))
    inner_c = circle.difference(band)
    rose = rose.difference(circle)
    info = dict(rose=round(rose.area), tan=round(tan.area), wild=round(wild.area), dirt=round(dirt_extra.area), circle=round(circle.area))
    # marks on the rose paving: yellow dash rows, a white line pair along the street (parade lines), slight tone patches
    dashes = dash_rows(rose, P).intersection(rose)
    patches = []
    x0, y0, x1, y1 = rose.bounds
    for _ in range(int(rose.area / 350)):
        c = (RNG.uniform(x0, x1), RNG.uniform(y0, y1))
        patches.append(Polygon(jitter_ring(c, RNG.uniform(2.5, 6.0), 9, 0.3)))
    patches = unary_union(patches).intersection(rose).difference(dashes.buffer(0.02)) if patches else Polygon()
    surface(meshes, T, "WG_rose", rose.difference(dashes.buffer(0.02)).difference(patches))
    surface(meshes, T, "WG_rose2", patches)
    surface(meshes, T, "WG_dash", dashes, dz=0.004)
    # grey-beige asphalt with joints and white lines (0:19:26-0:19:38)
    lines = grid_lines(tan.bounds, 6.0, 0.06, math.radians(12)).intersection(tan)
    tdash = dash_rows(tan, P).intersection(tan)
    tpatch = []
    tx0, ty0, tx1, ty1 = tan.bounds if not tan.is_empty else (0, 0, 1, 1)
    for _ in range(int(tan.area / 300)):
        tpatch.append(Polygon(jitter_ring((RNG.uniform(tx0, tx1), RNG.uniform(ty0, ty1)), RNG.uniform(2.0, 5.0), 8, 0.3)))
    tpatch = unary_union(tpatch).intersection(tan).difference(lines).difference(tdash) if tpatch else Polygon()
    surface(meshes, T, "WG_tan", tan.difference(lines).difference(tdash).difference(tpatch))
    surface(meshes, T, "WG_tan2", tpatch)
    surface(meshes, T, "WG_joint", lines, dz=0.003)
    surface(meshes, T, "WG_dash", tdash, dz=0.004)
    # sandy dirt (island paths, the far bank, the sand ways outside the mountain)
    dirt = unary_union([wild, dirt_extra])
    dpatch = []
    dx0, dy0, dx1, dy1 = dirt.bounds if not dirt.is_empty else (0, 0, 1, 1)
    for _ in range(int(dirt.area / 120)):
        dpatch.append(Polygon(jitter_ring((RNG.uniform(dx0, dx1), RNG.uniform(dy0, dy1)), RNG.uniform(1.0, 3.0), 7, 0.4)))
    dpatch = unary_union(dpatch).intersection(dirt) if dpatch else Polygon()
    surface(meshes, T, "WG_dirt", dirt.difference(dpatch))
    surface(meshes, T, "WG_dirt2", dpatch)
    # the landing's cobbled circle: checker of pale cobbles, a mint band
    ca, cb, cj = checker(inner_c, 0.5, math.radians(20))
    for name, g in (("WG_cob", ca), ("WG_cob2", cb), ("WG_cob", cj)):
        surface(meshes, T, name, g, dz=0.01)
    surface(meshes, T, "WG_mint", band, dz=0.012)
    # the river bank: a band of stones along the water where the ground meets it
    bank = P["area"].intersection(P["water"].buffer(0.9)).difference(P["water"])
    bank = bank.intersection(P["paving"].buffer(0.05).union(unary_union(P["beds"]).buffer(0.05)))
    # beds
    ribs, inners, bedinfo = [], [], []
    for q in P["beds"]:
        z = zone_of(q, P)
        near_mtn = q.distance(P["mountain"]) < 12
        kind = "wild" if (z == "wild" or P["berm"].buffer(0.5).contains(q.representative_point())) else ("board" if (z == "tan" or near_mtn or (q.representative_point().y < 575 and q.area < 400)) else "stone")
        if z == "rose" and q.area > 600:
            kind = "stone"
        rib, inner, soil_h = add_bed(meshes, T, q, kind)
        bedinfo.append((q, kind, soil_h))
        if rib is not None:
            ribs.append((rib, kind, soil_h)); inners.append((inner, kind, soil_h))
    info["beds"] = (len(P["beds"]), round(sum(q.area for q in P["beds"])), {k: sum(1 for _, kk, _ in bedinfo if kk == k) for k in ("stone", "board", "wild")})
    # stone bank edge (drawn last, slightly raised, only where it is not a bed kerb)
    for poly in G._polys(bank):
        G.top_surface(meshes["WG_bank"], T, poly, dz=0.05)
    return P, T, meshes, dict(ribs=ribs, inners=inners, beds=bedinfo, rose=rose, tan=tan, dirt=dirt), info


# ---------------------------------------------------------------- the town: storefronts
# sign texts for the POIs near a storefront (the OSM names, in the English the signs use; the rest get generic signs)
POI_SIGNS = {"トレーディングポスト": "TRADING POST", "ゼネラルストア": "GENERAL STORE", "ウエスタンウエア": "WESTERN WEAR",
             "ウエスタンランド写真館": "PICTURE PARLOUR", "カントリーベア・シアター": "COUNTRY BEAR THEATER",
             "ハングリー ベア レストラン": "HUNGRY BEAR", "ザ・ダイヤモンドホースシュー": "THE DIAMOND HORSESHOE",
             "ペコスビル・カフェ": "PECOS BILL CAFE", "フロンティア・ウッドクラフト": "FRONTIER WOODCRAFT",
             "カウボーイ・クックハウス": "COWBOY COOKHOUSE", "ハッピーキャンパーサプライ": "HAPPY CAMPER SUPPLY",
             "ウエスタンランド・シューティングギャラリー": "SHOOTIN' GALLERY", "キャンプ・ウッドチャック・キッチン": "CAMP WOODCHUCK",
             "カントリーベア・バンドワゴン": "BANDWAGON"}
GENERIC_SIGNS = ("LAND ENTERPRISE CO.", "DRY GOODS", "ASSAYER", "BARBER SHOP", "HOTEL", "FEED & SEED", "GUNSMITH",
                 "SADDLERY", "LAND OFFICE", "BANK", "TELEGRAPH", "MERCANTILE", "BOOTS & HATS", "GAZETTE")
STYLE_WALL = {"red": "WL_red", "grey": "WL_grey", "cream": "WL_cream", "green": "WL_green", "yellow": "WL_yellow",
              "log": "WL_log", "stone": "WL_stone", "brick": "WL_brick", "tan": "WL_tan", "brown": "WL_brown", "blue": "WL_blue",
              "dh": "WL_cream", "pecos": "WL_yellow", "townhall": "WL_brick"}
TOWN_STYLES = ("red", "grey", "cream", "green", "yellow", "tan", "brown", "stone", "red", "cream", "blue")
SIDING = {"red": "batten", "grey": "batten", "brown": "batten", "cream": "clap", "green": "clap", "yellow": "clap", "tan": "clap",
          "blue": "clap", "log": "log", "stone": "stone", "brick": "brick", "dh": "clap", "pecos": "clap", "townhall": "brick"}


class Ctx:
    def __init__(self, M, gr, P):
        self.M, self.gr, self.P = M, gr, P
        self.paving = P["paving"]
        self.pv = P["paving"].buffer(0.6)
        self.bld = P["buildings"]
        self.beds = unary_union(P["beds"]) if P["beds"] else Polygon()
        self.decks = []              # (polygon, z top)
        self.lamp_spots, self.hitch = [], []
        self.pois = [(p["tags"]["name"], Point(*p["xy"])) for p in DL.DATA["pois"] if p["tags"].get("name") in POI_SIGNS]
        self.generic = 0
        self.signs_used = set()
        self.solid = []              # plan footprints of things added outside the OSM buildings (props keep off them)

    def space(self, a, b, nrm):
        best = 30.0
        for t in (0.2, 0.5, 0.8):
            m = a + (b - a) * t
            ray = LineString([m + nrm * 0.4, m + nrm * 30.0])
            hit = ray.intersection(self.bld)
            if not hit.is_empty:
                best = min(best, 0.4 + Point(*(m + nrm * 0.4)).distance(hit))
        return best

    def is_front(self, a, b, nrm, reach=2.0):
        m = (a + b) / 2
        return self.pv.contains(Point(*(m + nrm * reach))) or self.pv.contains(Point(*(m + nrm * 0.8)))

    def sign_for(self, m, nrm):
        q = Point(*(m + nrm * 4.0))
        best = min(self.pois, key=lambda t: t[1].distance(q), default=None)
        if best is not None and best[1].distance(q) < 14.0 and POI_SIGNS[best[0]] not in self.signs_used:
            self.signs_used.add(POI_SIGNS[best[0]])
            return POI_SIGNS[best[0]]
        s = GENERIC_SIGNS[self.generic % len(GENERIC_SIGNS)]; self.generic += 1
        return s


def floor_of(ctx, poly):
    zlo, zhi = ctx.gr.span(poly, 0.8)
    return zlo - 0.5, zhi + 0.05


def wall_quad(M, mat, pa, pb, z0, z1, nrm, off=0.0):
    n3 = N3(nrm)
    quad(M[mat], P3(pa, z0) + n3 * off, P3(pb, z0) + n3 * off, P3(pb, z1) + n3 * off, P3(pa, z1) + n3 * off, n3)


def siding(M, mat, pa, pb, z0, z1, nrm, kind):
    """Surface relief on a wall: clapboard lips (horizontal), battens (vertical), log rounds, stone courses, brick bands."""
    e = (pb - pa); L = np.linalg.norm(e)
    if L < 0.3:
        return
    e = e / L; n3 = N3(nrm); e3 = N3(e)
    if kind == "clap":
        for z in np.arange(z0 + 0.3, z1 - 0.05, 0.3):
            quad(M[mat], P3(pa, z) + n3 * 0.035, P3(pb, z) + n3 * 0.035, P3(pb, z - 0.05) + n3 * 0.001, P3(pa, z - 0.05) + n3 * 0.001, n3 * 0.3 - UP)
    elif kind == "batten":
        for t in np.arange(0.3, L - 0.1, 0.55):
            q = pa + e * t
            quad(M[mat], P3(q, z0) + n3 * 0.04, P3(q + e * 0.07, z0) + n3 * 0.04, P3(q + e * 0.07, z1) + n3 * 0.04, P3(q, z1) + n3 * 0.04, n3)
            quad(M[mat], P3(q, z0), P3(q, z0) + n3 * 0.04, P3(q, z1) + n3 * 0.04, P3(q, z1), -e3)
    elif kind == "log":
        for z in np.arange(z0 + 0.2, z1, 0.42):
            a0, b0 = P3(pa - e * 0.15, z), P3(pb + e * 0.15, z)
            quad(M["WL_log"], a0 - UP * 0.16 + n3 * 0.02, b0 - UP * 0.16 + n3 * 0.02, b0 + n3 * 0.14, a0 + n3 * 0.14, n3 - UP * 0.8)
            quad(M["WL_log"], a0 + n3 * 0.14, b0 + n3 * 0.14, b0 + UP * 0.16 + n3 * 0.02, a0 + UP * 0.16 + n3 * 0.02, n3 + UP * 0.8)
    elif kind == "stone":
        k = 0
        for z in np.arange(z0 + 0.45, z1, 0.45):
            quad(M["WL_tan"], P3(pa, z - 0.06) + n3 * 0.03, P3(pb, z - 0.06) + n3 * 0.03, P3(pb, z) + n3 * 0.03, P3(pa, z) + n3 * 0.03, n3)
            for t in np.arange(0.35 + 0.3 * (k % 2), L - 0.2, 0.75):
                q = pa + e * t
                quad(M["WL_tan"], P3(q, z - 0.45) + n3 * 0.03, P3(q + e * 0.05, z - 0.45) + n3 * 0.03, P3(q + e * 0.05, z) + n3 * 0.03, P3(q, z) + n3 * 0.03, n3)
            k += 1
    elif kind == "brick":
        for z in np.arange(z0 + 0.6, z1, 0.6):
            quad(M["WL_brickd"], P3(pa, z - 0.04) + n3 * 0.02, P3(pb, z - 0.04) + n3 * 0.02, P3(pb, z) + n3 * 0.02, P3(pa, z) + n3 * 0.02, n3)


def window(M, c, nrm, e, z0, w, h, trim="WL_white", mullion=True, shutters=None):
    """A sash / shop window centred on plan point c: glass, a frame, a sill and a head, optional shutters."""
    n3, e3 = N3(nrm), N3(e)
    B = (e3, n3, UP)
    quad(M["WL_glass"], P3(c - e * w / 2, z0) + n3 * 0.03, P3(c + e * w / 2, z0) + n3 * 0.03, P3(c + e * w / 2, z0 + h) + n3 * 0.03, P3(c - e * w / 2, z0 + h) + n3 * 0.03, n3)
    box(M[trim], P3(c, z0 - 0.05) + n3 * 0.06, (w / 2 + 0.12, 0.07, 0.05), B)
    box(M[trim], P3(c, z0 + h + 0.08) + n3 * 0.05, (w / 2 + 0.14, 0.06, 0.08), B)
    for s in (-1, 1):
        box(M[trim], P3(c + e * s * (w / 2 + 0.04), z0 + h / 2) + n3 * 0.05, (0.05, 0.04, h / 2), B)
    if mullion:
        box(M[trim], P3(c, z0 + h / 2) + n3 * 0.045, (0.025, 0.02, h / 2), B)
        box(M[trim], P3(c, z0 + h * 0.55) + n3 * 0.045, (w / 2, 0.02, 0.025), B)
    if shutters:
        for s in (-1, 1):
            box(M[shutters], P3(c + e * s * (w / 2 + 0.3), z0 + h / 2) + n3 * 0.06, (0.24, 0.03, h / 2), B)


def door(M, c, nrm, e, z0, w=1.4, h=2.4, mat="WL_door", arched=False):
    n3, e3 = N3(nrm), N3(e)
    B = (e3, n3, UP)
    if arched:
        arched_window(M["WL_white"], c - e * (w / 2 + 0.12), c + e * (w / 2 + 0.12), nrm, z0, z0 + h - w / 2, off=0.03)
        arched_window(M[mat], c - e * w / 2, c + e * w / 2, nrm, z0, z0 + h - w / 2 - 0.05, off=0.05)
        return
    quad(M[mat], P3(c - e * w / 2, z0) + n3 * 0.04, P3(c + e * w / 2, z0) + n3 * 0.04, P3(c + e * w / 2, z0 + h) + n3 * 0.04, P3(c - e * w / 2, z0 + h) + n3 * 0.04, n3)
    for s in (-0.25, 0.25):
        quad(M["WL_glass"], P3(c + e * (s * w - 0.18 * w), z0 + h * 0.5) + n3 * 0.05, P3(c + e * (s * w + 0.18 * w), z0 + h * 0.5) + n3 * 0.05,
             P3(c + e * (s * w + 0.18 * w), z0 + h * 0.9) + n3 * 0.05, P3(c + e * (s * w - 0.18 * w), z0 + h * 0.9) + n3 * 0.05, n3)
    box(M["WL_trim"], P3(c, z0 + h + 0.1) + n3 * 0.05, (w / 2 + 0.15, 0.06, 0.1), B)
    for s in (-1, 1):
        box(M["WL_trim"], P3(c + e * s * (w / 2 + 0.05), z0 + h / 2) + n3 * 0.05, (0.06, 0.04, h / 2), B)


def sign_board(M, text, c, nrm, e, z, h=0.34, bg="WL_sign", fg="WL_text", maxw=None, t=0.05):
    """A flat board with raised letters, centred on plan point c at height z, facing nrm. Returns its width."""
    g = text_poly(text, h).simplify(h * 0.06)
    x0, y0, x1, y1 = g.bounds
    w = (x1 - x0)
    if maxw and w > maxw - 0.5:
        s = max(0.2, (maxw - 0.5) / w)
        g = shapely.affinity.scale(g, s, s, origin=(0, 0)); w *= s; h *= s
    n3, e3 = N3(nrm), N3(e)
    cc = P3(c, z)
    plate(M[bg], sbox(-w / 2 - 0.25, -h / 2 - 0.18, w / 2 + 0.25, h / 2 + 0.18), cc, e3, UP, n3, off=t, back=M[bg], t=t)
    plate(M[fg], g, cc, e3, UP, n3, off=t + 0.015)
    return w + 0.5


def false_front_top(M, mat, trim, pa, pb, nrm, z, kind, rise):
    """The shaped top of a false front above z (on the wall plane): flat / stepped / pediment / arched, with a cap."""
    e = pb - pa; L = np.linalg.norm(e); e = e / L
    c = (pa + pb) / 2
    hw = L / 2
    if kind == "stepped":
        shape = Polygon([(-hw, 0), (hw, 0), (hw, rise * 0.45), (hw * 0.55, rise * 0.45), (hw * 0.55, rise), (-hw * 0.55, rise), (-hw * 0.55, rise * 0.45), (-hw, rise * 0.45)])
    elif kind == "pediment":
        shape = Polygon([(-hw, 0), (hw, 0), (hw, rise * 0.35), (0, rise * 1.1), (-hw, rise * 0.35)])
    elif kind == "arched":
        pts = [(-hw, 0), (hw, 0), (hw, rise * 0.4)]
        for k in range(1, 8):
            a = math.pi * k / 8
            pts.append((hw * math.cos(a), rise * 0.4 + rise * 0.6 * math.sin(a)))
        pts.append((-hw, rise * 0.4))
        shape = Polygon(pts)
    else:
        shape = sbox(-hw, 0, hw, rise)
    plate(M[mat], shape, P3(c, z), N3(e), UP, N3(nrm), off=0.0, back=M[mat], t=0.15)
    # cap moulding along the top outline
    cs = list(shape.exterior.coords)
    for (u0, w0), (u1, w1) in zip(cs[:-1], cs[1:]):
        if w0 < 0.05 and w1 < 0.05:
            continue
        a3 = P3(c + e * u0, z + w0) + N3(nrm) * 0.05; b3 = P3(c + e * u1, z + w1) + N3(nrm) * 0.05
        bar(M[trim], a3, b3, w=0.12, d=0.22)


def veranda(ctx, pa, pb, nrm, zd, zroof, depth, roofmat="WL_roof", lace=False, balcony=False, posts="WL_post"):
    """Posts along the boardwalk edge, a lean-to roof (or a balcony deck with railings and flower boxes)."""
    M = ctx.M
    e = pb - pa; L = np.linalg.norm(e); e = e / L; n3 = N3(nrm); B = B3(e, nrm)
    n_p = max(2, int(round(L / 3.0)) + 1)
    for t in np.linspace(0.25, L - 0.25, n_p):
        q = pa + e * t + nrm * (depth - 0.25)
        box(M[posts], P3(q, (zd + zroof) / 2), (0.08, 0.08, (zroof - zd) / 2), B)
        bar(M[posts], P3(q, zroof - 0.5), P3(q - nrm * 0.45, zroof - 0.02), w=0.05, d=0.05)
    bar(M[posts], P3(pa + nrm * (depth - 0.25), zroof), P3(pb + nrm * (depth - 0.25), zroof), w=0.14, d=0.12)
    if balcony:
        slab_ = Polygon([pa, pb, pb + nrm * depth, pa + nrm * depth])
        cap(M["WL_deck"], slab_, zroof + 0.12)
        cap(M["WL_deck"], slab_, zroof, down=True)
        sides(M["WL_deck"], slab_, zroof, zroof + 0.12)
        q0, q1 = pa + nrm * (depth - 0.1), pb + nrm * (depth - 0.1)
        zr = zroof + 0.12
        bar(M["WL_white"], P3(q0, zr + 1.0), P3(q1, zr + 1.0), w=0.07, d=0.05)
        bar(M["WL_white"], P3(q0, zr + 0.1), P3(q1, zr + 0.1), w=0.05, d=0.04)
        for t in np.arange(0.0, L + 1e-6, 0.16):
            q = q0 + e * t
            bar(M["WL_white"], P3(q, zr + 0.1), P3(q, zr + 1.0), w=0.03, d=0.03)
        for t in np.arange(0.9, L - 0.6, 2.2):                       # flower boxes on the rail (red geraniums, 0:18:16)
            q = q0 + e * t + nrm * 0.12
            box(M["WL_brown"], P3(q, zr + 1.1), (0.45, 0.13, 0.1), B)
            for j in (-0.3, 0.0, 0.3):
                sphere(M["WL_fl_red" if (int(t * 3) + int(j * 10)) % 3 else "WL_leaf"], P3(q + e * j, zr + 1.28), 0.16, n=5, m=3)
        for q in (pa, pb):
            bar(M["WL_white"], P3(q + nrm * 0.1, zr + 1.0), P3(q + nrm * (depth - 0.1), zr + 1.0), w=0.07, d=0.05)
    else:
        z_in, z_out = zroof + 0.55, zroof + 0.05
        A, Bq = P3(pa - e * 0.1, z_in), P3(pb + e * 0.1, z_in)
        C, D = P3(pb + e * 0.1 + nrm * (depth + 0.2), z_out), P3(pa - e * 0.1 + nrm * (depth + 0.2), z_out)
        quad(M[roofmat], A, Bq, C, D, UP + n3 * 0.3)
        quad(M["WL_roofd"], A - UP * 0.08, Bq - UP * 0.08, C - UP * 0.08, D - UP * 0.08, -UP)
        quad(M["WL_trim"], D, C, C - UP * 0.2, D - UP * 0.2, n3)
    if lace:                                                       # a scalloped valance under the beam (0:18:16)
        nsc = max(2, int(L / 1.1))
        pts = [(0.0, 0.0), (0.0, -0.42)]
        for k in range(nsc):
            x = L * k / nsc
            for j in (0.2, 0.4, 0.6, 0.8, 1.0):
                pts.append((x + L / nsc * j, -0.42 + 0.24 * math.sin(math.pi * min(j, 1.0))))
        pts.append((L, 0.0))
        shape = Polygon(pts).buffer(0)
        plate(M["WL_lace"], shape, P3(pa + nrm * (depth - 0.2), zroof - 0.07), N3(e), UP, n3, back=M["WL_lace"], t=0.03)


def boardwalk(ctx, pa, pb, nrm, depth):
    """The raised plank walk in front of a storefront (clipped to the paving, off the beds and other buildings)."""
    strip = Polygon([pa, pb, pb + nrm * depth, pa + nrm * depth]).buffer(0)
    strip = strip.intersection(ctx.paving.buffer(0.1)).difference(ctx.beds.buffer(0.15))
    strip = strip.difference(ctx.bld.buffer(-0.02))
    if strip.area < 1.0:
        return None
    zs = [ctx.gr.z(*q) for q in (pa + nrm * depth, pb + nrm * depth, (pa + pb) / 2 + nrm * depth, pa + nrm, pb + nrm)]
    zt = max(zs) + DECK_H
    ctx.decks.append((strip, zt))
    return zt


def storefront(ctx, pa, pb, nrm, zb, zf, style, n, sign=None, deck=True, top="flat"):
    """One storefront segment on the plan edge pa-pb (facing nrm): wall + siding, doors and windows, floor bands, cornice,
    a false front, a sign, a boardwalk with a veranda / balcony. Returns the top of the front."""
    M = ctx.M
    e = pb - pa; L = np.linalg.norm(e); e = e / L; n3 = N3(nrm); B = B3(e, nrm)
    mat = STYLE_WALL[style]
    trim = "WL_white" if style in ("cream", "green", "yellow", "blue", "dh", "pecos", "townhall", "brick", "stone") else "WL_trim"
    space = ctx.space(pa, pb, nrm)
    zd = zf
    if deck and space > 5.5:
        zdd = boardwalk(ctx, pa, pb, nrm, DECK_D)
        if zdd is not None:
            zd = zdd
    h1, hu = 3.9, 3.2
    zeave = zf + h1 + (n - 1) * hu
    rise = {"flat": 1.0, "stepped": 1.8, "pediment": 1.6, "arched": 1.7, "none": 0.0}[top]
    zt = zeave + 0.3
    wall_quad(M, mat, pa, pb, zb, zt, nrm)
    siding(M, mat, pa, pb, max(zd, zb), zt, nrm, SIDING[style])
    if rise > 0:
        false_front_top(M, mat, trim, pa, pb, nrm, zt, top, rise)
    # ground floor: a door in the middle bay, windows in the others
    nb = max(1, int(round(L / 2.6))); bw = L / nb
    mid = nb // 2
    arch = style in ("dh", "townhall", "brick")
    for k in range(nb):
        c = pa + e * (k + 0.5) * bw
        if bw < 1.4:
            continue
        if k == mid or (style == "dh" and k % 2 == 0):
            door(M, c, nrm, e, zd, w=min(1.5, bw - 0.6), h=2.6, mat="WL_trimr" if style == "dh" else "WL_door", arched=arch)
        elif arch:
            arched_window(M["WL_white"], c - e * 0.7, c + e * 0.7, nrm, zd + 0.8, zd + 2.3, off=0.03)
            arched_window(M["WL_glass"], c - e * 0.58, c + e * 0.58, nrm, zd + 0.85, zd + 2.3, off=0.05)
        else:
            window(M, c, nrm, e, zd + 0.75, min(1.7, bw - 0.8), 1.7, trim=trim)
    # upper floors: sash windows, a floor band
    for f in range(1, n):
        zz = zf + h1 + (f - 1) * hu
        box(M[trim], P3((pa + pb) / 2, zz) + n3 * 0.06, (L / 2, 0.08, 0.1), B)
        for k in range(nb):
            c = pa + e * (k + 0.5) * bw
            if bw < 1.4:
                continue
            if style == "dh":
                arched_window(M["WL_white"], c - e * 0.55, c + e * 0.55, nrm, zz + 0.6, zz + 2.0, off=0.03)
                arched_window(M["WL_glass"], c - e * 0.45, c + e * 0.45, nrm, zz + 0.65, zz + 2.0, off=0.05)
                A4 = [P3(c - e * 0.7, zz + 2.75) + n3 * 0.05, P3(c + e * 0.7, zz + 2.75) + n3 * 0.05, P3(c + e * 0.7, zz + 2.05) + n3 * 0.75, P3(c - e * 0.7, zz + 2.05) + n3 * 0.75]
                quad(M["WL_awn"], *A4, n3 + UP)                    # pink awning over the upper window (0:16:40)
                for s in (-1, 1):
                    tri(M["WL_awn"], P3(c + e * s * 0.7, zz + 2.75) + n3 * 0.05, P3(c + e * s * 0.7, zz + 2.05) + n3 * 0.75, P3(c + e * s * 0.7, zz + 2.05) + n3 * 0.05, N3(e * s))
            else:
                window(M, c, nrm, e, zz + 0.7, 0.9, 1.5, trim=trim, mullion=False, shutters="WL_trimr" if style in ("cream", "yellow") and k % 2 == 0 else None)
    # cornice with brackets under the false front, corner boards
    box(M[trim], P3((pa + pb) / 2, zt - 0.15) + n3 * 0.2, (L / 2 + 0.1, 0.22, 0.12), B)
    for t in np.arange(0.3, L - 0.2, 1.5):
        box(M[trim], P3(pa + e * t, zt - 0.38) + n3 * 0.12, (0.05, 0.12, 0.13), B)
    for s in (0.0, 1.0):
        box(M[trim], P3(pa + e * L * s, (zb + zt) / 2) + n3 * 0.05, (0.09, 0.07, (zt - zb) / 2), B)
    if style == "dh":                                               # gilt balls along the top (0:16:40)
        for t in np.arange(0.5, L, 2.4):
            sphere(M["WL_gold"], P3(pa + e * t + nrm * 0.1, zt + rise + 0.2), 0.18, n=6, m=4)
    if sign:
        zsg = zt + rise * 0.35 if rise > 0.8 else zt - 0.8
        bg, fg = (("WL_signr", "WL_textw") if style in ("cream", "yellow", "tan", "stone") else ("WL_sign", "WL_text"))
        if style == "dh":
            bg, fg = "WL_gold", "WL_trimr"
        sign_board(M, sign, (pa + pb) / 2 + nrm * 0.18, nrm, e, zsg, h=0.36 if L > 6 else 0.28, bg=bg, fg=fg, maxw=L - 0.6, t=0.05)
    if zd > zf + 0.1:                                               # veranda / gallery on the boardwalk
        if n >= 2 and style in ("cream", "dh", "pecos", "yellow", "green") and L > 5:
            veranda(ctx, pa, pb, nrm, zd, zf + h1, DECK_D, balcony=True, lace=style in ("cream", "dh"), posts="WL_white" if style in ("cream", "dh") else "WL_post")
        else:
            veranda(ctx, pa, pb, nrm, zd, zf + 3.25, DECK_D, roofmat="WL_tin" if style in ("grey", "brown") else "WL_roof", lace=style == "cream")
        ctx.hitch.append((pa + nrm * (DECK_D + 0.9), pb + nrm * (DECK_D + 0.9)))
        ctx.lamp_spots.append((pa + pb) / 2 + nrm * (DECK_D + 0.6))
    c = pa + e * (mid + 0.5) * bw                                   # lanterns either side of the door
    for s in (-1, 1):
        q = c + e * s * 1.15 + nrm * 0.25
        box(M["WL_lamp"], P3(q, zd + 2.62), (0.1, 0.1, 0.1))
        box(M["WL_glow"], P3(q, zd + 2.4), (0.08, 0.08, 0.13))
        bar(M["WL_iron"], P3(q - nrm * 0.2, zd + 2.72), P3(q, zd + 2.72), w=0.03, d=0.03)
    return zt + rise


def town_hall(ctx, pa, pb, nrm, zb, zf, roof_z):
    """The brick TOWN HALL (0:19:04): two storeys, arched openings, a white portico with a balcony, a cupola tower."""
    M = ctx.M
    e = pb - pa; L = np.linalg.norm(e); e = e / L; n3 = N3(nrm); B = B3(e, nrm)
    zt = storefront(ctx, pa, pb, nrm, zb, zf, "townhall", 2, sign=None, deck=False, top="flat")
    c = (pa + pb) / 2
    w = min(2.6, L / 2 - 0.4)
    for s in (-1, 1):                                              # two white columns
        q = c + e * s * w + nrm * 2.4
        frustum(M["WL_white"], P3(q, zf - 0.1), P3(q, zf + 3.7), 0.17, 0.14, n=10)
        box(M["WL_white"], P3(q, zf + 0.15), (0.26, 0.26, 0.2))
    slab_ = Polygon([c - e * (w + 0.4), c + e * (w + 0.4), c + e * (w + 0.4) + nrm * 2.8, c - e * (w + 0.4) + nrm * 2.8])
    cap(M["WL_white"], slab_, zf + 3.95); cap(M["WL_white"], slab_, zf + 3.7, down=True)
    sides(M["WL_white"], slab_, zf + 3.7, zf + 3.95)
    cap(M["WL_deck"], slab_.buffer(-0.02), zf + 0.12)
    sides(M["WL_stone"], slab_.buffer(-0.02), zf - 0.3, zf + 0.12)
    ctx.solid.append(slab_)
    plate(M["WL_white"], Polygon([(-w - 0.4, 0), (w + 0.4, 0), (0, 0.9)]), P3(c + nrm * 2.8, zf + 3.95), N3(e), UP, n3, back=M["WL_white"], t=0.1)
    sign_board(M, "TOWN HALL", c + nrm * 2.85, nrm, e, zf + 3.45, h=0.3, bg="WL_white", fg="WL_text", maxw=2 * w, t=0.03)
    q0, q1 = c - e * (w + 0.35) + nrm * 2.7, c + e * (w + 0.35) + nrm * 2.7   # balcony railing on the portico
    for t in np.arange(0.0, 2 * w + 0.7, 0.18):
        q = q0 + e * t
        bar(M["WL_white"], P3(q, zf + 3.95), P3(q, zf + 4.85), w=0.035, d=0.035)
    bar(M["WL_white"], P3(q0, zf + 4.9), P3(q1, zf + 4.9), w=0.08, d=0.06)
    tc = c - nrm * 3.0                                             # the cupola tower on the roof behind the front
    zr = max(roof_z, zt)
    loft_rect(M["WL_white"], P3(tc, zr - 1.5), e, nrm, [(1.3, 1.3, 0.0), (1.3, 1.3, 3.2)])
    box(M["WL_white"], P3(tc, zr + 1.8), (1.55, 1.55, 0.08), B)
    for s in range(4):
        d = [e, nrm, -e, -nrm][s]; d2 = [nrm, -e, -nrm, e][s]
        for t in np.linspace(-1.45, 1.45, 11):
            q = tc + d * 1.5 + d2 * t
            bar(M["WL_white"], P3(q, zr + 1.85), P3(q, zr + 2.5), w=0.03, d=0.03)
    for su in (-1, 1):
        for sv in (-1, 1):
            q = tc + e * su * 0.9 + nrm * sv * 0.9
            box(M["WL_white"], P3(q, zr + 3.0), (0.1, 0.1, 1.2), B)
    loft_rect(M["WL_cupola"], P3(tc, zr + 4.2), e, nrm, [(1.3, 1.3, 0.0), (0.9, 0.9, 0.5), (0.05, 0.05, 2.3)])
    frustum(M["WL_iron"], P3(tc, zr + 6.4), P3(tc, zr + 7.4), 0.03, 0.02, n=4)
    return zt


def roof_over(M, poly, H, roof, big_tin=True):
    if poly.area > 900 and big_tin:
        inner = poly.buffer(-2.4, join_style=2)
        cap(M["WL_tin"], inner if not inner.is_empty else poly, H + 1.6)
        hip_strip(M[roof], M["WL_tin"], poly, H, 2.6, 1.6, out=0.2)
    else:
        c, u, v, hu, hv = rect_of(poly)
        if poly.area / (4 * hu * hv) > 0.8:
            rh = min(3.2, 0.6 * hv + 0.6)
            loft_rect(M[roof], P3(c, H), u, v, [(hu + 0.4, hv + 0.4, 0.0), (max(hu - hv, 0.05) + 0.05, 0.05, rh)])
        else:
            cap(M[roof], poly, H)
            hip_strip(M[roof], M[roof], poly, H, 3.0, 2.0, out=0.4)


def plain_block(ctx, poly, n, fronts, roof="WL_roof", back="WL_brown", deck=True, big_tin=True):
    """A town block: its public edges become storefronts (styles from `fronts(edge_i, seg_i, nseg, a, b, nrm)`, a dict
    or None), the others plain board walls; a shingle hip roof (a flat tin roof with a hip rim on the big blocks)."""
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    H = zf + 3.9 + (n - 1) * 3.2 + 0.3
    fr = 0
    tops, pending = [], []
    for ei, (a, b, nrm) in enumerate(ring_edges(poly)):
        L = np.linalg.norm(b - a)
        if L > 2.5 and ctx.is_front(a, b, nrm):
            nseg = max(1, int(round(L / RNG.uniform(6.5, 9.5))))
            for s in range(nseg):
                pa, pb = a + (b - a) * s / nseg, a + (b - a) * (s + 1) / nseg
                spec = fronts(ei, s, nseg, a, b, nrm)
                if spec is None:
                    wall_quad(M, back, pa, pb, zb, H, nrm)
                    continue
                pending.append((pa, pb, nrm, spec))
            fr += 1
        else:
            wall_quad(M, back, a, b, zb, H, nrm)
            if L > 1.0:
                siding(M, back, a, b, zb, H, nrm, "batten" if L < 25 else "clap")
    for pa, pb, nrm, spec in pending:
        style = spec.get("style", "red")
        if style == "townhall":
            tops.append(town_hall(ctx, pa, pb, nrm, zb, zf, H + 2.0))
        else:
            tops.append(storefront(ctx, pa, pb, nrm, zb, zf, style, spec.get("n", n), sign=spec.get("sign"), deck=deck,
                                   top=spec.get("top", "flat")))
    roof_over(M, poly, H, roof, big_tin)
    return dict(fronts=fr, segs=len(pending), top=round(max(tops) if tops else H, 1))


def chimney(M, q, z0, z1, mat="WL_stone"):
    box(M[mat], P3(q, (z0 + z1) / 2), (0.7, 0.55, (z1 - z0) / 2))
    box(M[mat], P3(q, z1 + 0.1), (0.8, 0.65, 0.1))


def water_tank(M, q, z0, r=1.3, h=2.0, legs=3.2):
    """A timber water tank on a trestle (0:13:40): four legs, bracing, a hooped barrel, a conical lid."""
    for su in (-1, 1):
        for sv in (-1, 1):
            p = (q[0] + su * r * 0.8, q[1] + sv * r * 0.8)
            box(M["WL_timber"], (p[0], p[1], z0 + legs / 2), (0.1, 0.1, legs / 2))
    for su in (-1, 1):
        bar(M["WL_timber"], (q[0] - r * 0.8, q[1] + su * r * 0.8, z0 + 0.4), (q[0] + r * 0.8, q[1] + su * r * 0.8, z0 + legs - 0.3), w=0.06, d=0.06)
        bar(M["WL_timber"], (q[0] + su * r * 0.8, q[1] - r * 0.8, z0 + 0.4), (q[0] + su * r * 0.8, q[1] + r * 0.8, z0 + legs - 0.3), w=0.06, d=0.06)
    box(M["WL_timber"], (q[0], q[1], z0 + legs + 0.05), (r + 0.1, r + 0.1, 0.08))
    frustum(M["WL_barrel"], (q[0], q[1], z0 + legs), (q[0], q[1], z0 + legs + h), r, r * 0.93, n=12)
    for k in (0.2, 0.55, 0.9):
        frustum(M["WL_hoop"], (q[0], q[1], z0 + legs + h * k - 0.04), (q[0], q[1], z0 + legs + h * k + 0.04), r * (1 - 0.07 * k) + 0.03, r * (1 - 0.07 * k) + 0.03, n=12, caps=False)
    lathe(M["WL_roofd"], (q[0], q[1], z0 + legs + h), [(r * 1.02, 0), (0.0, 0.7)], n=12)


# ---------------------------------------------------------------- the town: the blocks
def face(nrm):
    if nrm[0] < -0.7:
        return "w"
    if nrm[0] > 0.7:
        return "e"
    return "s" if nrm[1] < 0 else "n"


def town_fronts(ctx, first=0, n=2, styles=TOWN_STYLES, sign_every=1):
    """A fronts() for plain_block: styles drawn in turn (seeded), signs from the POIs nearby or the generic list."""
    k = [first]

    def f(ei, s, nseg, a, b, nrm):
        st = styles[(k[0] * 7 + 3) % len(styles)]; k[0] += 1
        pa, pb = a + (b - a) * s / nseg, a + (b - a) * (s + 1) / nseg
        sign = ctx.sign_for((pa + pb) / 2, nrm) if k[0] % sign_every == 0 else None
        top = ("flat", "stepped", "pediment", "arched", "flat")[k[0] % 5]
        return dict(style=st, n=1 if st == "stone" else n, sign=sign, top=top)
    return f


def diamond_horseshoe(ctx, poly):
    """The Westernland half of way 196942701: the Diamond Horseshoe on the south / west faces (cream, two storeys, red
    arched doors, a gallery with a lace valance and gilt balls, pink awnings, the corner sign), Pecos Bill Cafe on the east."""
    done = {"dh": False}

    def f(ei, s, nseg, a, b, nrm):
        fc = face(nrm)
        if fc == "e":
            return dict(style="pecos", n=2, sign="PECOS BILL CAFE" if s == 0 else None, top="stepped")
        sign = None
        if not done["dh"] and fc in ("s", "w"):
            sign = "THE DIAMOND HORSESHOE"; done["dh"] = True
        return dict(style="dh", n=2, sign=sign, top="arched" if sign else "flat")
    return plain_block(ctx, poly, 2, f, roof="WL_roofd", back="WL_cream")


def bears_block(ctx, poly):
    """163053907: the log Hungry Bear / Country Bear Theater on the west (stone chimney, banner), the south row (stone
    house, green clapboard, the brick Town Hall; 0:18:52-0:19:10), the Shootin' Gallery on the east."""
    south = iter(["stone", "green", "townhall", "red", "yellow", "grey"])
    flags = {"cb": False, "hb": False}

    def f(ei, s, nseg, a, b, nrm):
        fc = face(nrm)
        if fc in ("w", "n"):
            sign = None
            if not flags["hb"]:
                sign = "HUNGRY BEAR RESTAURANT"; flags["hb"] = True
            elif not flags["cb"]:
                sign = "COUNTRY BEAR THEATER"; flags["cb"] = True
            return dict(style="log", n=2, sign=sign, top="none")
        if fc == "s":
            st = next(south, "brown")
            return dict(style=st, n=1 if st == "stone" else 2, sign=None if st == "townhall" else ctx.sign_for(a + (b - a) * (s + 0.5) / nseg, nrm), top="pediment" if st == "green" else "flat")
        return dict(style="red", n=2, sign="SHOOTIN' GALLERY" if s == 0 else None, top="stepped")
    info = plain_block(ctx, poly, 2, f, roof="WL_roof", back="WL_log")
    # stone chimneys on the log part (0:17:22), a banner on the gallery (0:18:10)
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    edges = [t for t in ring_edges(poly) if face(t[2]) == "w" and np.linalg.norm(t[1] - t[0]) > 6]
    if edges:
        a, b, nrm = max(edges, key=lambda t: np.linalg.norm(t[1] - t[0]))
        e = (b - a) / np.linalg.norm(b - a)
        for t in (0.25, 0.8):
            q = a + (b - a) * t - nrm * 2.5
            chimney(M, q, zf + 6.0, zf + 11.5)
        q = a + (b - a) * 0.65 + nrm * (DECK_D + 0.05)
        plate(M["WL_canvas"], sbox(-3.2, -0.55, 3.2, 0.55), P3(q, zf + 4.6), N3(e), UP, N3(nrm), back=M["WL_canvas"], t=0.02)
        plate(M["WL_signr"], text_poly("COUNTRY BEAR JAMBOREE", 0.42), P3(q, zf + 4.6), N3(e), UP, N3(nrm), off=0.025)
        for s in (-1, 1):                                          # flower boxes on the log gallery
            qq = q + e * s * 4.5
            box(M["WL_log"], P3(qq, zf + 4.3), (0.9, 0.2, 0.15), B3(e, nrm))
            for j in np.linspace(-0.7, 0.7, 5):
                sphere(M["WL_fl_red" if int(j * 10) % 2 else "WL_fl_yel"], P3(qq + e * j, zf + 4.55), 0.17, n=5, m=3)
    return info


def small_shop(ctx, poly, name_hint=None):
    """A small timber shop (6-120 m2): false-front on the public edges, board walls elsewhere, a shingle roof."""
    style = TOWN_STYLES[int(RNG.integers(len(TOWN_STYLES)))]

    def f(ei, s, nseg, a, b, nrm):
        pa, pb = a + (b - a) * s / nseg, a + (b - a) * (s + 1) / nseg
        return dict(style=style, n=1, sign=ctx.sign_for((pa + pb) / 2, nrm) if s == 0 else None, top=("stepped", "flat", "pediment")[int(RNG.integers(3))])
    return plain_block(ctx, poly, 1, f, roof="WL_roof", back=STYLE_WALL[style], deck=poly.area > 25)


def booth(ctx, poly, wall="WL_brown", roof="WL_roof", h=2.6):
    """A tiny booth / shed: board walls, a counter window on the public side, a shingle hip roof."""
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    for a, b, nrm in ring_edges(poly):
        wall_quad(M, wall, a, b, zb, zf + h, nrm)
        L = np.linalg.norm(b - a)
        if L > 1.2 and ctx.is_front(a, b, nrm, 1.2):
            e = (b - a) / L
            quad(M["WL_glass"], P3(a + e * 0.25, zf + 1.0) + N3(nrm) * 0.03, P3(b - e * 0.25, zf + 1.0) + N3(nrm) * 0.03,
                 P3(b - e * 0.25, zf + 2.0) + N3(nrm) * 0.03, P3(a + e * 0.25, zf + 2.0) + N3(nrm) * 0.03, N3(nrm))
            box(M["WL_trim"], P3((a + b) / 2, zf + 1.0) + N3(nrm) * 0.2, (L / 2 - 0.1, 0.22, 0.04), B3(e, nrm))
    c, u, v, hu, hv = rect_of(poly)
    loft_rect(M[roof], P3(c, zf + h), u, v, [(hu + 0.35, hv + 0.35, 0.0), (max(hu - hv, 0.05) + 0.05, 0.05, min(1.6, hv + 0.4))])
    return "booth"


def canopy(ctx, poly, roof="WL_roof"):
    M = ctx.M
    c, u, v, hu, hv = rect_of(poly)
    zb, zf = floor_of(ctx, poly)
    for su in (-1, 1):
        for sv in (-1, 1):
            p = c + su * (hu - 0.2) * u + sv * (hv - 0.2) * v
            box(M["WL_post"], P3(p, (zb + zf + 2.9) / 2), (0.1, 0.1, (zf + 2.9 - zb) / 2))
    loft_rect(M[roof], P3(c, zf + 2.9), u, v, [(hu + 0.3, hv + 0.3, 0), (max(hu - hv, 0.05), 0.05, min(1.4, hv + 0.3))])
    return "canopy"


def covered_wagon(M, c, e, z, kiosk=False):
    """A covered wagon (0:17:16, 1:07:40): a blue-grey box on four wheels, canvas hoops, a tongue."""
    e = np.asarray(e, float); e = e / np.linalg.norm(e); n = np.array([-e[1], e[0]])
    B = B3(e, n)
    L, W = (3.6, 1.5) if not kiosk else (4.2, 1.8)
    box(M["WL_blue"], P3(c, z + 1.05), (L / 2, W / 2, 0.35), B)
    for su in (-1, 1):
        for sv in (-1, 1):
            q = c + e * su * (L / 2 - 0.5) + n * sv * (W / 2 + 0.08)
            r = 0.75 if su < 0 else 0.6
            ring = [(q + e * r * math.cos(2 * math.pi * k / 12), z + r + r * math.sin(2 * math.pi * k / 12)) for k in range(12)]
            for (p0, z0), (p1, z1) in zip(ring, ring[1:] + ring[:1]):
                bar(M["WL_wheel"], P3(p0, z0), P3(p1, z1), w=0.07, d=0.07)
            for k in range(0, 12, 2):
                bar(M["WL_wheel"], P3(q, z + r), P3(ring[k][0], ring[k][1]), w=0.035, d=0.035)
    # the canvas cover: hoops lofted as an arch
    prof = [(W / 2 + 0.1) * math.cos(math.pi * k / 8) for k in range(9)]
    hts = [1.4 + 1.1 * math.sin(math.pi * k / 8) for k in range(9)]
    for k in range(8):
        for s0, s1 in ((-L / 2 + 0.2, L / 2 - 0.2),):
            A = P3(c + e * s0 + n * prof[k], z + hts[k]); Bq = P3(c + e * s1 + n * prof[k], z + hts[k])
            C = P3(c + e * s1 + n * prof[k + 1], z + hts[k + 1]); D = P3(c + e * s0 + n * prof[k + 1], z + hts[k + 1])
            quad(M["WL_canvas"], A, Bq, C, D, UP + N3(n) * math.cos(math.pi * (k + 0.5) / 8))
    for s in (-1, 1):
        pts2 = [(n * prof[k], hts[k]) for k in range(9)]
        cc = c + e * s * (L / 2 - 0.2)
        for k in range(8):
            tri(M["WL_canvas"], P3(cc, z + 1.4), P3(cc + pts2[k][0], z + pts2[k][1]), P3(cc + pts2[k + 1][0], z + pts2[k + 1][1]), N3(e * s))
    bar(M["WL_wheel"], P3(c + e * L / 2, z + 0.9), P3(c + e * (L / 2 + 2.0), z + 0.35), w=0.08, d=0.08)


def bear_statue(M, c, z, face_dir):
    """The carved bear with a sign (0:18:04): a brown bear on a stump holding a board."""
    f = np.array([face_dir[0], face_dir[1], 0.0]); f /= np.linalg.norm(f)
    frustum(M["WL_log"], (c[0], c[1], z), (c[0], c[1], z + 0.5), 0.45, 0.42, n=8)
    sphere(M["WL_bear"], (c[0], c[1], z + 1.25), 0.45, n=8, m=6, sc=(1.0, 0.9, 1.5))
    sphere(M["WL_bear"], np.array([c[0], c[1], z + 2.15]) + f * 0.08, 0.3, n=8, m=5)
    sphere(M["WL_bear"], np.array([c[0], c[1], z + 2.1]) + f * 0.32, 0.12, n=6, m=4)
    for s in (-1, 1):
        r = np.cross(f, UP) * s
        sphere(M["WL_bear"], np.array([c[0], c[1], z + 2.42]) + r * 0.2, 0.09, n=6, m=3)
    r = np.cross(f, UP)
    plate(M["WL_sign"], sbox(-0.45, -0.25, 0.45, 0.25), np.array([c[0], c[1], z + 1.3]) + f * 0.5, r, UP, f, back=M["WL_timber"], t=0.04)
    plate(M["WL_text"], text_poly("COUNTRY BEAR", 0.1), np.array([c[0], c[1], z + 1.35]) + f * 0.5, r, UP, f, off=0.02)


def locomotive(M, c, e, z):
    """The old mine locomotive at Big Thunder's front (1:04:40): boiler, cab, stack, big wheels."""
    e = np.asarray(e, float); e /= np.linalg.norm(e); n = np.array([-e[1], e[0]]); B = B3(e, n)
    box(M["WL_iron"], P3(c, z + 0.5), (2.2, 0.8, 0.12), B)
    frustum(M["WL_boatk"], P3(c - e * 0.6, z + 1.35), P3(c + e * 1.9, z + 1.35), 0.6, 0.6, n=12)
    box(M["WL_timber"], P3(c - e * 1.5, z + 1.5), (0.7, 0.85, 0.9), B)
    loft_rect(M["WL_roofd"], P3(c - e * 1.5, z + 2.4), e, n, [(0.85, 1.0, 0), (0.85, 1.0, 0.1)])
    frustum(M["WL_boatk"], P3(c + e * 1.4, z + 1.8), P3(c + e * 1.4, z + 2.8), 0.18, 0.45, n=10)
    for t in (-1.2, 0.0, 1.2):
        for s in (-1, 1):
            q = c + e * t + n * s * 0.85
            frustum(M["WL_boatr"], P3(q, z + 0.55) - N3(n) * 0.06 * s, P3(q, z + 0.55) + N3(n) * 0.06 * s, 0.55, 0.55, n=12)
    lathe(M["WL_gold"], (*(c + e * 0.6), z + 1.9), [(0.2, 0), (0.18, 0.3), (0.1, 0.4), (0, 0.42)], n=8)


# ---------------------------------------------------------------- Big Thunder Mountain
PEAKS = (((-124.0, 690.0), 29.0, 15.0), ((-96.0, 664.0), 22.0, 13.0), ((-68.0, 650.0), 17.0, 11.0), ((-114.0, 624.0), 12.0, 8.0),
         ((-58.0, 692.0), 16.0, 10.0), ((-84.0, 700.0), 18.0, 9.0), ((-134.0, 668.0), 10.0, 7.0))


def rock_height(mt, x, y):
    d = mt.boundary.distance(Point(x, y))
    base = 6.0 + sum(h * math.exp(-((x - c[0]) ** 2 + (y - c[1]) ** 2) / (s * s)) for c, h, s in PEAKS)
    return min(base, 2.5 + d * 2.0)


def rock_column(M, c, zg, H, r, rng):
    """A fluted sandstone spire: stacked irregular hexagonal prisms, tapering, banded by height (three reds)."""
    n = 6
    sec = 2.8
    ns = max(1, int(math.ceil((H - zg) / sec)))
    rot = rng.uniform(0, 6.3)
    base = [rng.uniform(0.82, 1.18) for _ in range(n)]
    rings = []
    for k in range(ns + 1):
        t = k / ns
        rk = r * (1.0 - 0.45 * t ** 1.6) * (1.0 + 0.08 * math.sin(k * 1.7 + rot))
        off = np.array([math.cos(rot), math.sin(rot)]) * 0.25 * t * r
        rings.append([(c[0] + off[0] + rk * base[j] * (1 + rng.uniform(-0.06, 0.06)) * math.cos(rot + 2 * math.pi * j / n),
                       c[1] + off[1] + rk * base[j] * (1 + rng.uniform(-0.06, 0.06)) * math.sin(rot + 2 * math.pi * j / n)) for j in range(n)])
    for k in range(ns):
        z0 = zg - 0.4 if k == 0 else zg + k * (H - zg) / ns
        z1 = zg + (k + 1) * (H - zg) / ns
        band = int((z0 + z1) / 2 / 2.3) % 5
        mat = ("WL_rock1", "WL_rock2", "WL_rock1", "WL_rock3", "WL_rock2")[band]
        prism(M[mat], rings[k], z0, rings[k + 1], z1, top=(k == ns - 1))
    return ns


def big_thunder(ctx):
    """The rock mass (spires on a jittered hex grid over MOUNTAIN), mine shacks, head-frame tower, stack, water tower."""
    M = ctx.M; mt = ctx.P["mountain"]; gr = ctx.gr
    rng = np.random.default_rng(1987)
    x0, y0, x1, y1 = mt.bounds
    inner = mt.buffer(-0.6)
    cols = 0; secs = 0
    sp = 4.4
    for j, y in enumerate(np.arange(y0, y1 + sp, sp * 0.866)):
        for x in np.arange(x0 + (sp / 2 if j % 2 else 0.0), x1 + sp, sp):
            q = (x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8))
            if not inner.contains(Point(q)):
                continue
            zg = gr.z(*q)
            H = zg + rock_height(mt, *q) * rng.uniform(0.78, 1.15)
            r = rng.uniform(2.7, 3.6)
            if rng.random() < 0.06:                                  # a slender tall spire
                H += rng.uniform(3.0, 7.0); r *= 0.75
            secs += rock_column(M, q, zg, H, r, rng); cols += 1
    # boulders round the base
    nb = 0
    for q in [g.exterior.interpolate(d) for g in polys(mt.buffer(1.2)) for d in np.arange(0.0, g.exterior.length, 2.7)]:
        if ctx.bld.buffer(0.5).contains(q) or not ctx.paving.buffer(1.0).contains(q) and not ctx.beds.contains(q):
            continue
        rr = rng.uniform(0.45, 1.1)
        sphere(M["WL_rock2" if rng.random() < 0.5 else "WL_rock1"], (q.x, q.y, gr.z(q.x, q.y) + rr * 0.35), rr, n=6, m=4, sc=(1.2, 1.0, 0.8))
        nb += 1
    # head-frame tower (0:19:14), brick stack, water tower on the rocks, mine shacks on stilts (the small OSM ways there)
    tq = (-131.0, 664.0)
    zt0 = gr.z(*tq)
    for su in (-1, 1):
        for sv in (-1, 1):
            box(M["WL_timber"], (tq[0] + su * 1.4, tq[1] + sv * 1.4, zt0 + 8.0), (0.14, 0.14, 8.0))
    for k in range(5):
        z = zt0 + 1.5 + k * 3.0
        for su in (-1, 1):
            bar(M["WL_timber"], (tq[0] - 1.4, tq[1] + su * 1.4, z), (tq[0] + 1.4, tq[1] + su * 1.4, z + 2.8), w=0.08, d=0.08)
            bar(M["WL_timber"], (tq[0] + su * 1.4, tq[1] - 1.4, z + 2.8), (tq[0] + su * 1.4, tq[1] + 1.4, z), w=0.08, d=0.08)
    box(M["WL_deck"], (tq[0], tq[1], zt0 + 16.1), (2.2, 2.2, 0.12))
    box(M["WL_grey"], (tq[0], tq[1], zt0 + 17.3), (1.3, 1.3, 1.1))
    loft_rect(M["WL_tin"], (tq[0], tq[1], zt0 + 18.4), (1, 0), (0, 1), [(1.6, 1.6, 0), (0.05, 0.05, 1.2)])
    frustum(M["WL_wheel"], (tq[0], tq[1] + 1.5, zt0 + 15.0), (tq[0], tq[1] + 1.7, zt0 + 15.0), 1.2, 1.2, n=12)
    sq = (-112.0, 671.0)
    frustum(M["WL_chim"], (sq[0], sq[1], gr.z(*sq)), (sq[0], sq[1], gr.z(*sq) + 21.0), 0.9, 0.6, n=8)
    frustum(M["WL_boatk"], (sq[0], sq[1], gr.z(*sq) + 21.0), (sq[0], sq[1], gr.z(*sq) + 21.6), 0.75, 0.75, n=8)
    water_tank(M, (-100.0, 686.0), gr.z(-100.0, 686.0) + rock_height(mt, -100.0, 686.0) * 0.55, r=1.6, h=2.2, legs=3.0)
    shacks = 0
    for i in (1348136442, 1348136443, 1348136444, 1348136445, 1294893205, 1348136440, 1289598799, 1347244465):
        p = poly_of(i)
        if p.is_empty:
            continue
        c, u, v, hu, hv = rect_of(p)
        hu, hv = max(hu, 1.4), max(hv, 1.2)
        zg = gr.z(*c)
        zfl = zg + (rock_height(mt, *c) * 0.45 if mt.buffer(4).contains(Point(*c)) else 0.0)
        if zfl > zg + 0.5:
            for su in (-1, 1):
                for sv in (-1, 1):
                    q = c + su * (hu - 0.2) * u + sv * (hv - 0.2) * v
                    box(M["WL_timber"], P3(q, (zg + zfl) / 2), (0.1, 0.1, (zfl - zg) / 2 + 0.3))
        loft_rect(M["WL_grey" if shacks % 2 else "WL_brown"], P3(c, zfl), u, v, [(hu, hv, 0.0), (hu, hv, 2.8)], cap=False)
        loft_rect(M["WL_tin"], P3(c, zfl + 2.8), u, v, [(hu + 0.35, hv + 0.35, 0.0), (hu + 0.35, 0.05, min(1.5, hv))])
        for s in (-1, 1):
            tri(M["WL_grey" if shacks % 2 else "WL_brown"], P3(c + u * s * hu - v * hv, zfl + 2.8), P3(c + u * s * hu + v * hv, zfl + 2.8), P3(c + u * s * hu, zfl + 2.8 + min(1.5, hv)), N3(u * s))
        shacks += 1
    return dict(columns=cols, sections=secs, boulders=nb, shacks=shacks)


def coaster(ctx):
    """Big Thunder's track where OSM does not put it in a tunnel: two rails and ties on a timber trestle of bents."""
    M = ctx.M; mt = ctx.P["mountain"]; gr = ctx.gr
    n_b = 0; L = 0.0
    for w in DL.DATA["ways"]:
        t = w["tags"]
        if t.get("roller_coaster") != "track" or t.get("tunnel") == "yes" or len(w["pts"]) < 2:
            continue
        ls = LineString(w["pts"])
        if not BOX.contains(ls.centroid):
            continue
        L += ls.length
        pts = [ls.interpolate(d) for d in np.arange(0.0, ls.length + 0.01, 2.5)]
        zs = []
        for q in pts:
            zg = gr.z(q.x, q.y)
            h = 3.2 + (0.3 * rock_height(mt, q.x, q.y) if mt.buffer(3).contains(q) else 0.0)
            zs.append(zg + min(h, 10.0))
        for k in range(len(pts) - 1):
            a, b = V(pts[k].coords[0]), V(pts[k + 1].coords[0])
            e = b - a; Ls = np.linalg.norm(e)
            if Ls < 1e-3:
                continue
            e /= Ls; n = np.array([-e[1], e[0]])
            for s in (-0.5, 0.5):
                bar(M["WL_rail"], P3(a + n * s, zs[k] + 0.18), P3(b + n * s, zs[k + 1] + 0.18), w=0.07, d=0.09)
            if k % 2 == 0:
                box(M["WL_tie"], P3(a, zs[k] + 0.07), (0.12, 0.8, 0.07), B3(e, n))
            if k % 2 == 0:
                zg = gr.z(*a)
                if zs[k] - zg > 0.8:
                    for s in (-0.7, 0.7):
                        box(M["WL_timber"], P3(a + n * s, (zg - 0.2 + zs[k]) / 2), (0.1, 0.1, (zs[k] - zg + 0.2) / 2), B3(e, n))
                    bar(M["WL_timber"], P3(a - n * 0.7, zg + 0.3), P3(a + n * 0.7, zs[k] - 0.2), w=0.06, d=0.06)
                    box(M["WL_timber"], P3(a, zs[k] - 0.05), (0.1, 0.85, 0.08), B3(e, n))
                    n_b += 1
    return dict(track_m=round(L), bents=n_b)


# ---------------------------------------------------------------- the Western River Railroad
def railway(ctx):
    """Narrow-gauge track: ballast, ties, rails; a berm (dark planted slopes) or, over the guest paths, a timber trestle
    with a plank deck, bents and railings (0:19:32-0:19:44, 0:21:20). Height 4.6 m over the ground (ESTIMATE)."""
    M = ctx.M; gr = ctx.gr; P = ctx.P
    blocked = unary_union([P["buildings"].buffer(1.0), P["mountain"].buffer(0.5), P["water"].buffer(0.5)])
    walk = P["paths"].intersection(P["paving"].buffer(0.5)).buffer(2.0)
    total = tr = 0.0
    for w in DL.DATA["ways"]:
        t = w["tags"]
        if t.get("railway") != "narrow_gauge" or t.get("tunnel") == "yes" or len(w["pts"]) < 2:
            continue
        ls = LineString(w["pts"]).intersection(BOX.difference(FANTASY.buffer(-8)))
        for part in getattr(ls, "geoms", [ls]):
            if part.geom_type != "LineString" or part.length < 2:
                continue
            total += part.length
            ds = np.arange(0.0, part.length + 0.01, 3.5)
            pts = [V(part.interpolate(d).coords[0]) for d in ds]
            zg = np.array([gr.z(*q) for q in pts])
            zg_s = np.convolve(np.pad(zg, 6, mode="edge"), np.ones(13) / 13, mode="valid")
            zr = zg_s + 4.6
            for k in range(len(pts) - 1):
                a, b = pts[k], pts[k + 1]
                e = b - a; Ls = np.linalg.norm(e)
                if Ls < 1e-3:
                    continue
                e /= Ls; n = np.array([-e[1], e[0]]); B = B3(e, n)
                m = (a + b) / 2
                over = walk.contains(Point(*m)) or blocked.contains(Point(*m)) or t.get("bridge") == "yes"
                za, zb_ = zr[k], zr[k + 1]
                for s in (-0.46, 0.46):
                    bar(M["WL_rail"], P3(a + n * s, za + 0.14), P3(b + n * s, zb_ + 0.14), w=0.05, d=0.08)
                box(M["WL_tie"], P3(a, za + 0.03), (0.1, 0.85, 0.05), B)
                if over:
                    tr += Ls
                    quad(M["WL_deck"], P3(a - n * 1.6, za - 0.05), P3(b - n * 1.6, zb_ - 0.05), P3(b + n * 1.6, zb_ - 0.05), P3(a + n * 1.6, za - 0.05), UP)
                    for s in (-1, 1):
                        quad(M["WL_timber"], P3(a + n * 1.6 * s, za - 0.65), P3(b + n * 1.6 * s, zb_ - 0.65), P3(b + n * 1.6 * s, zb_ - 0.05), P3(a + n * 1.6 * s, za - 0.05), N3(n * s))
                        bar(M["WL_timber"], P3(a + n * 1.55 * s, za + 1.0), P3(b + n * 1.55 * s, zb_ + 1.0), w=0.1, d=0.08)
                        bar(M["WL_timber"], P3(a + n * 1.55 * s, za + 0.5), P3(b + n * 1.55 * s, zb_ + 0.5), w=0.06, d=0.06)
                        bar(M["WL_timber"], P3(a + n * 1.55 * s, za - 0.05), P3(a + n * 1.55 * s, za + 1.0), w=0.09, d=0.09)
                    quad(M["WL_timber"], P3(a - n * 1.6, za - 0.65), P3(a + n * 1.6, za - 0.65), P3(b + n * 1.6, zb_ - 0.65), P3(b - n * 1.6, zb_ - 0.65), -UP)
                    if k % 2 == 0:                                   # a bent: two posts, a cap, X braces
                        zg0 = gr.z(*a)
                        if not P["paving"].buffer(0.4).contains(Point(*a)):
                            for s in (-1.2, 1.2):
                                box(M["WL_timber"], P3(a + n * s, (zg0 - 0.2 + za - 0.65) / 2), (0.15, 0.15, (za - 0.45 - zg0) / 2), B)
                            bar(M["WL_timber"], P3(a - n * 1.2, zg0 + 0.4), P3(a + n * 1.2, za - 1.0), w=0.08, d=0.08)
                            bar(M["WL_timber"], P3(a + n * 1.2, zg0 + 0.4), P3(a - n * 1.2, za - 1.0), w=0.08, d=0.08)
                else:
                    quad(M["WL_ballast"], P3(a - n * 1.3, za - 0.05), P3(b - n * 1.3, zb_ - 0.05), P3(b + n * 1.3, zb_ - 0.05), P3(a + n * 1.3, za - 0.05), UP)
                    for s in (-1, 1):                                # berm slopes
                        ga, gb = gr.z(*(a + n * s * 4.2)), gr.z(*(b + n * s * 4.2))
                        quad(M["WL_berm"] if "WL_berm" in M else M["WL_leaf"], P3(a + n * s * 1.3, za - 0.05), P3(b + n * s * 1.3, zb_ - 0.05),
                             P3(b + n * s * 4.2, gb - 0.2), P3(a + n * s * 4.2, ga - 0.2), N3(n * s) + UP)
    return dict(rail_m=round(total), trestle_m=round(tr))


# ---------------------------------------------------------------- the Mark Twain landing and the riverboat
def landing(ctx, water_z):
    """218979636 (a roof in OSM): the landing house (v1 0:59:40-1:00:00): red brick, arched windows, a green hip roof, a
    white portico on the land side, a central tower with a green dome, small domed pavilions at the ends; the boarding
    gallery and the plank pier on the river side; returns the pier's outer edge (for the boat)."""
    M = ctx.M; gr = ctx.gr; P = ctx.P
    poly = poly_of(LANDING)
    c, u, v, hu, hv = rect_of(poly)
    # v towards the water
    if P["water"].distance(Point(*(c + v * (hv + 3)))) > P["water"].distance(Point(*(c - v * (hv + 3)))):
        v = -v
    if u[0] * v[1] - u[1] * v[0] < 0:
        u = -u
    zb, zf = floor_of(ctx, poly)
    zf += 0.15
    bu, bv0, bv1 = hu - 0.4, -hv + 2.2, hv * 0.15               # the closed house (land side), the gallery (river side)
    body = Polygon([c + u * s1 * bu + v * s2 for s1, s2 in ((-1, bv0), (1, bv0), (1, bv1), (-1, bv1))])
    B = (N3(u), N3(v), UP)
    for a, b, nrm in ring_edges(body):
        wall_quad(M, "WL_brick", a, b, zb, zf + 4.4, nrm)
        siding(M, "WL_brick", a, b, zf, zf + 4.4, nrm, "brick")
        L = np.linalg.norm(b - a); e = (b - a) / L
        box(M["WL_white"], P3((a + b) / 2, zf + 4.25) + N3(nrm) * 0.1, (L / 2 + 0.1, 0.14, 0.18), B3(e, nrm))
        box(M["WL_stone"], P3((a + b) / 2, zf + 0.25) + N3(nrm) * 0.06, (L / 2 + 0.06, 0.08, 0.3), B3(e, nrm))
        for t in np.arange(1.4, L - 1.0, 2.4):
            q = a + e * t
            arched_window(M["WL_white"], q - e * 0.62, q + e * 0.62, nrm, zf + 0.9, zf + 2.6, off=0.03)
            arched_window(M["WL_glass"], q - e * 0.5, q + e * 0.5, nrm, zf + 0.95, zf + 2.6, off=0.05)
    cap(M["WL_brick"], body, zf + 4.4)
    # green hip roof over the whole footprint (house + gallery)
    loft_rect(M["WL_groof"], P3(c, zf + 4.4), u, v, [(hu + 0.5, hv + 0.5, 0.0), (hu - 1.5, max(hv - 2.0, 0.3), 2.0)])
    # gallery on the river side: white posts, a stone-edged plank floor
    gal = Polygon([c + u * s1 * bu + v * s2 for s1, s2 in ((-1, bv1), (1, bv1), (1, hv + 0.2), (-1, hv + 0.2))])
    cap(M["WL_deck"], gal, zf); sides(M["WL_stone"], gal, zb, zf)
    for t in np.linspace(-bu + 0.3, bu - 0.3, 9):
        q = c + u * t + v * (hv - 0.1)
        frustum(M["WL_white"], P3(q, zf), P3(q, zf + 4.4), 0.12, 0.1, n=8)
        bar(M["WL_white"], P3(q, zf + 3.9), P3(q - v * 0.6, zf + 4.35), w=0.05, d=0.05)
    # the portico on the land side (centre), columns and a pediment with the name
    pc = c + v * bv0
    port = Polygon([pc + u * s1 * 3.4 + v * s2 for s1, s2 in ((-1, -3.0), (1, -3.0), (1, 0.0), (-1, 0.0))])
    cap(M["WL_deck"], port, zf); sides(M["WL_stone"], port, zb, zf)
    for s1 in (-3.1, -1.1, 1.1, 3.1):
        q = pc + u * s1 - v * 2.7
        frustum(M["WL_white"], P3(q, zf), P3(q, zf + 4.2), 0.2, 0.16, n=10)
    slab_ = Polygon([pc + u * s1 * 3.6 + v * s2 for s1, s2 in ((-1, -3.2), (1, -3.2), (1, 0.0), (-1, 0.0))])
    cap(M["WL_white"], slab_, zf + 4.55); cap(M["WL_white"], slab_, zf + 4.2, down=True); sides(M["WL_white"], slab_, zf + 4.2, zf + 4.55)
    plate(M["WL_white"], Polygon([(-3.6, 0), (3.6, 0), (0, 1.6)]), P3(pc - v * 3.2, zf + 4.55), N3(u), UP, N3(-v), back=M["WL_white"], t=0.12)
    loft_rect(M["WL_groof"], P3(pc - v * 1.6, zf + 4.55), u, v, [(3.7, 1.7, 0.0), (3.7, 0.05, 1.5)])
    sign_board(M, "MARK TWAIN RIVERBOAT", pc - v * 3.26, -v, u, zf + 3.85, h=0.26, bg="WL_white", fg="WL_text", maxw=6.6, t=0.02)
    ctx.solid.append(port.buffer(0.2))
    # the central tower and the two end pavilions (octagonal white drums, green domes)
    tz = zf + 4.4 + 2.0
    loft_rect(M["WL_white"], P3(c, zf + 4.0), u, v, [(1.3, 1.3, 0.0), (1.3, 1.3, 4.4)])
    for s in range(4):
        d = [u, v, -u, -v][s]; d2 = [v, -u, -v, u][s]
        arched_window(M["WL_glass"], c + d * 1.31 - d2 * 0.5, c + d * 1.31 + d2 * 0.5, d, zf + 5.9, zf + 7.4, off=0.02, n=4)
    lathe(M["WL_groof"], (c[0], c[1], zf + 8.4), [(1.6, 0.0), (1.5, 0.5), (1.1, 1.3), (0.5, 1.9), (0.0, 2.1)], n=10)
    frustum(M["WL_iron"], (c[0], c[1], zf + 10.4), (c[0], c[1], zf + 12.2), 0.04, 0.02, n=4)
    tri(M["WL_iron"], (c[0], c[1], zf + 11.9), (c[0] + 0.7, c[1], zf + 11.7), (c[0], c[1], zf + 11.5), (0, 1, 0))
    for s in (-1, 1):
        q = c + u * s * (hu - 1.4) + v * (bv0 + 1.4)
        lathe(M["WL_white"], (q[0], q[1], zf + 4.0), [(1.4, 0.0), (1.4, 2.4), (1.55, 2.5), (0.0, 2.5)], n=8)
        lathe(M["WL_groof"], (q[0], q[1], zf + 6.5), [(1.6, 0.0), (1.4, 0.6), (0.9, 1.3), (0.3, 1.7), (0.0, 1.8)], n=8)
        frustum(M["WL_iron"], (q[0], q[1], zf + 8.3), (q[0], q[1], zf + 9.2), 0.03, 0.02, n=4)
    ctx.lamp_spots += [pc - v * 4.2 + u * 4.5, pc - v * 4.2 - u * 4.5]
    # the pier: planks from the gallery out over the water, posts into the river
    pier = Polygon([c + u * s1 * (hu + 3.0) + v * s2 for s1, s2 in ((-1, hv + 0.2), (1, hv + 0.2), (1, hv + 4.2), (-1, hv + 4.2))])
    pz = zf
    cap(M["WL_deck"], pier, pz); sides(M["WL_timber"], pier, water_z - 0.3, pz)
    for t in np.arange(-hu - 2.8, hu + 3.0, 2.2):
        q = c + u * t + v * (hv + 4.05)
        frustum(M["WL_timber"], P3(q, water_z - 0.5), P3(q, pz + 1.0), 0.14, 0.14, n=6)
    ctx.decks.append((pier, pz))
    ctx.solid.append(pier.buffer(0.5)); ctx.solid.append(poly.buffer(0.5))
    return c + v * (hv + 4.2), u, v


def riverboat(M, c, u, v, zw):
    """The Mark Twain moored at the landing (web: a three-deck stern-wheeler ~32 m long, twin black stacks with crowns, a
    pilot house, a red stern wheel; v1 0:58:40, 1:03:00 for the look): c = the middle of its side against the pier."""
    u = np.asarray(u, float); v = np.asarray(v, float)
    Wd = 9.0; Lh = 30.0
    cc = c + v * (Wd / 2 + 0.6)
    def outline(hl, hw, bow=4.5):
        pts = [(-hl, -hw), (hl - bow, -hw), (hl, 0.0), (hl - bow, hw), (-hl, hw)]
        return [cc + u * a + v * b for a, b in pts]
    def ring3(pts, z):
        return [P3(p, z) for p in pts]
    # hull: white with a red band, a dark bottom
    lo, hi = outline(Lh / 2 - 0.6, Wd / 2 - 0.8), outline(Lh / 2, Wd / 2)
    prism(M["WL_boatr"], [tuple(p) for p in lo], zw - 0.8, [tuple(p) for p in hi], zw + 0.3, top=False)
    prism(M["WL_boat"], [tuple(p) for p in hi], zw + 0.3, [tuple(p) for p in hi], zw + 1.3, top=True)
    decks = [(zw + 1.3, Lh / 2, Wd / 2, 11.0, 3.2, 2.7), (zw + 4.2, Lh / 2 - 1.5, Wd / 2 - 0.3, 9.0, 3.0, 2.5), (zw + 6.9, 7.5, 3.4, 4.0, 2.2, 2.3)]
    for k, (z, hl, hw, cl, cw, ch) in enumerate(decks):
        if k > 0:
            pts = outline(hl, hw, bow=3.5 if k == 1 else 2.0)
            prism(M["WL_boat"], [tuple(p) for p in pts], z - 0.25, [tuple(p) for p in pts], z, top=True, bottom=True)
            if k == 1:                                             # the gingerbread fascia under the upper deck
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    e = b - a; L = np.linalg.norm(e)
                    if L > 1:
                        e /= L
                        for t in np.arange(0.3, L - 0.2, 0.9):
                            q = a + e * t
                            frustum(M["WL_boat"], P3(q, z - 2.9 + 0.02), P3(q, z - 0.25), 0.06, 0.06, n=4)
        cab = [cc + u * a + v * b for a, b in ((-cl, -cw), (cl, -cw), (cl, cw), (-cl, cw))]
        cab_p = Polygon(cab)
        sides(M["WL_boat"], cab_p, z, z + ch); cap(M["WL_boatd"], cab_p, z + ch)
        for a, b, nrm in ring_edges(cab_p):
            L = np.linalg.norm(b - a); e = (b - a) / L
            for t in np.arange(0.9, L - 0.5, 1.5):
                q = a + e * t
                quad(M["WL_glass"], P3(q - e * 0.4, z + 0.9) + N3(nrm) * 0.03, P3(q + e * 0.4, z + 0.9) + N3(nrm) * 0.03,
                     P3(q + e * 0.4, z + ch - 0.4) + N3(nrm) * 0.03, P3(q - e * 0.4, z + ch - 0.4) + N3(nrm) * 0.03, N3(nrm))
        # deck railing along the edge
        pts = outline(hl, hw, bow=4.5 if k == 0 else (3.5 if k == 1 else 2.0))
        for a, b in zip(pts, pts[1:] + pts[:1]):
            e = b - a; L = np.linalg.norm(e)
            if L < 0.5:
                continue
            e /= L; n = np.array([-e[1], e[0]])
            a2, b2 = a - n * 0.15, b - n * 0.15
            bar(M["WL_boat"], P3(a2, z + 1.0), P3(b2, z + 1.0), w=0.07, d=0.06)
            for t in np.arange(0.0, L, 0.35):
                q = a2 + e * t
                bar(M["WL_boat"], P3(q, z), P3(q, z + 1.0), w=0.025, d=0.025)
    # pilot house, stacks, stern wheel, flag
    ph = cc + u * 2.5
    zp = decks[2][0] + decks[2][5]
    loft_rect(M["WL_boat"], P3(ph, zp), u, v, [(1.3, 1.3, 0.0), (1.3, 1.3, 2.0)])
    for s in range(4):
        d = [u, v, -u, -v][s]; d2 = [v, -u, -v, u][s]
        quad(M["WL_glass"], P3(ph + d * 1.31 - d2 * 1.0, zp + 0.9), P3(ph + d * 1.31 + d2 * 1.0, zp + 0.9), P3(ph + d * 1.31 + d2 * 1.0, zp + 1.8), P3(ph + d * 1.31 - d2 * 1.0, zp + 1.8), N3(d))
    loft_rect(M["WL_boatd"], P3(ph, zp + 2.0), u, v, [(1.6, 1.6, 0.0), (1.0, 1.0, 0.45)])
    lathe(M["WL_gold"], (ph[0], ph[1], zp + 2.45), [(0.2, 0), (0.08, 0.5), (0, 0.6)], n=6)
    for s in (-1, 1):
        q = cc + u * 7.5 + v * s * 1.7
        frustum(M["WL_boatk"], P3(q, decks[1][0]), P3(q, zw + 17.0), 0.5, 0.5, n=10)
        lathe(M["WL_boatk"], (q[0], q[1], zw + 17.0), [(0.5, 0.0), (0.95, 1.0), (0.95, 1.15), (0.8, 1.15), (0.45, 0.2)], n=10)
    bar(M["WL_boatk"], P3(cc + u * 7.5 - v * 1.7, zw + 14.0), P3(cc + u * 7.5 + v * 1.7, zw + 14.0), w=0.06, d=0.06)
    wc = cc - u * (Lh / 2 + 2.4)
    for s in (-1, 1):                                               # wheel rims and spokes
        rim = [wc + v * s * 3.4 + u * 3.0 * math.cos(2 * math.pi * k / 16) for k in range(16)]
        zr = [zw + 2.6 + 3.0 * math.sin(2 * math.pi * k / 16) for k in range(16)]
        for k in range(16):
            bar(M["WL_boatr"], P3(rim[k], zr[k]), P3(rim[(k + 1) % 16], zr[(k + 1) % 16]), w=0.12, d=0.12)
            if k % 2 == 0:
                bar(M["WL_boatr"], P3(wc + v * s * 3.4, zw + 2.6), P3(rim[k], zr[k]), w=0.07, d=0.07)
    for k in range(12):                                             # paddles
        a = 2 * math.pi * k / 12
        q = wc + u * 2.8 * math.cos(a)
        box(M["WL_boatr"], P3(q, zw + 2.6 + 2.8 * math.sin(a)), (0.35, 3.4, 0.05), (N3(u) * math.cos(a) + UP * math.sin(a), N3(v), np.cross(N3(u) * math.cos(a) + UP * math.sin(a), N3(v))))
    frustum(M["WL_iron"], P3(wc - v * 3.6, zw + 2.6), P3(wc + v * 3.6, zw + 2.6), 0.2, 0.2, n=8)
    for s in (-1, 1):
        bar(M["WL_boat"], P3(cc - u * (Lh / 2 - 0.5) + v * s * 3.4, zw + 4.0), P3(wc + v * s * 3.4, zw + 2.6), w=0.2, d=0.2)
    fq = cc + u * (Lh / 2 - 0.5)
    frustum(M["WL_iron"], P3(fq, zw + 1.3), P3(fq, zw + 7.5), 0.05, 0.03, n=4)
    tri(M["WL_flag"], P3(fq, zw + 7.4), P3(fq - u * 1.4, zw + 7.0), P3(fq, zw + 6.6), N3(v))
    for s in (-1, 1):                                               # the name boards on the pilot-house deck
        plate(M["WL_boat"], sbox(-2.2, -0.3, 2.2, 0.3), P3(cc + v * s * 3.45, decks[2][0] - 0.6), N3(u * s), UP, N3(v * s), t=0.02)
        plate(M["WL_text"], text_poly("MARK TWAIN", 0.36), P3(cc + v * s * 3.45, decks[2][0] - 0.6), N3(u * s), UP, N3(v * s), off=0.02)


# ---------------------------------------------------------------- Camp Woodchuck, the island, the far bank
def log_cabin(ctx, poly, roof="WL_roof", h=3.0, wall="WL_log", sign=None, porch=True):
    """A log cabin: log walls (rounds), a door and small windows on the public side, a shingle gable, a stone chimney."""
    M = ctx.M
    zb, zf = floor_of(ctx, poly)
    c, u, v, hu, hv = rect_of(poly)
    P = poly if poly.area / (4 * hu * hv) < 0.8 else Polygon([c + u * a * hu + v * b * hv for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a, b, nrm in ring_edges(P):
        wall_quad(M, wall, a, b, zb, zf + h, nrm)
        siding(M, wall, a, b, zf, zf + h, nrm, "log")
        L = np.linalg.norm(b - a)
        if L > 2.5 and ctx.is_front(a, b, nrm, 1.5):
            e = (b - a) / L
            door(M, (a + b) / 2, nrm, e, zf, w=1.0, h=2.1)
            if L > 5:
                for s in (-1, 1):
                    window(M, (a + b) / 2 + e * s * min(2.0, L / 2 - 0.9), nrm, e, zf + 0.9, 0.8, 0.9, trim="WL_trim", mullion=True)
            if sign:
                sign_board(M, sign, (a + b) / 2 + N3(nrm)[:2] * 0.1, nrm, e, zf + h - 0.35, h=0.26, maxw=L - 0.6)
                sign = None
    rh = min(3.0, hv * 0.9 + 0.4)
    loft_rect(M[roof], P3(c, zf + h), u, v, [(hu + 0.45, hv + 0.45, 0.0), (hu + 0.45, 0.05, rh)])
    for s in (-1, 1):
        tri(M[wall], P3(c + u * s * hu - v * hv, zf + h), P3(c + u * s * hu + v * hv, zf + h), P3(c + u * s * hu, zf + h + rh), N3(u * s))
    if poly.area > 20:
        chimney(M, c + u * (hu - 0.3), zf + h - 1.0, zf + h + rh + 1.0)
    return "cabin"


def tipi(M, c, z, r=1.4, h=4.2, rng=RNG):
    lathe(M["WL_tipi"], (c[0], c[1], z), [(r, 0.0), (r * 0.12, h * 0.86), (0.0, h * 0.88)], n=9)
    frustum(M["WL_tipid"], (c[0], c[1], z + h * 0.28), (c[0], c[1], z + h * 0.38), r * 0.73, r * 0.63, n=9, caps=False)
    frustum(M["WL_tipid"], (c[0], c[1], z + 0.05), (c[0], c[1], z + 0.35), r * 1.005, r * 0.93, n=9, caps=False)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        bar(M["WL_timber"], (c[0] + r * 0.2 * math.cos(a), c[1] + r * 0.2 * math.sin(a), z + h * 0.75),
            (c[0] - r * 0.1 * math.cos(a), c[1] - r * 0.1 * math.sin(a), z + h * 1.12), w=0.05, d=0.05)
    quad(M["WL_logd"], (c[0] + r * 0.98, c[1] - 0.3, z), (c[0] + r * 0.98, c[1] + 0.3, z), (c[0] + r * 0.72, c[1] + 0.25, z + 1.2), (c[0] + r * 0.72, c[1] - 0.25, z + 1.2), (1, 0, 0.3))


def fort(ctx, polys_):
    """Fort Sam Clemens: log blockhouses (the upper storey overhangs) inside a pointed-log stockade round them."""
    M = ctx.M; gr = ctx.gr
    for p in polys_:
        zb, zf = floor_of(ctx, p)
        c, u, v, hu, hv = rect_of(p)
        hu, hv = max(hu, 1.5), max(hv, 1.5)
        loft_rect(M["WL_log"], P3(c, zb), u, v, [(hu, hv, 0.0), (hu, hv, zf - zb + 3.0)], cap=False)
        if p.area > 12:
            loft_rect(M["WL_logd"], P3(c, zf + 3.0), u, v, [(hu + 0.6, hv + 0.6, 0.0), (hu + 0.6, hv + 0.6, 2.6)], cap=False)
            loft_rect(M["WL_roofd"], P3(c, zf + 5.6), u, v, [(hu + 0.9, hv + 0.9, 0.0), (0.05, 0.05, 2.0)])
        else:
            loft_rect(M["WL_roofd"], P3(c, zf + 3.0), u, v, [(hu + 0.4, hv + 0.4, 0.0), (0.05, 0.05, 1.4)])
    hull = unary_union(polys_).convex_hull.buffer(3.5)
    ring = hull.exterior
    n = 0
    for d in np.arange(0.0, ring.length, 0.34):
        q = ring.interpolate(d)
        z = gr.z(q.x, q.y)
        h = 3.6 + 0.25 * math.sin(d * 3.1)
        frustum(M["WL_log"], (q.x, q.y, z - 0.2), (q.x, q.y, z + h), 0.17, 0.16, n=5, caps=False)
        lathe(M["WL_logd"], (q.x, q.y, z + h), [(0.16, 0.0), (0.0, 0.45)], n=5)
        n += 1
    return n


def mill(ctx, p):
    """Harper's Mill: a log mill with a gable and a water wheel on the side nearest the water."""
    log_cabin(ctx, p, roof="WL_roofd", h=3.4)
    M = ctx.M
    c, u, v, hu, hv = rect_of(p)
    s = 1 if ctx.P["water"].distance(Point(*(c + u * (hu + 2)))) < ctx.P["water"].distance(Point(*(c - u * (hu + 2)))) else -1
    wc = c + u * s * (hu + 0.5)
    zb, zf = floor_of(ctx, p)
    z0 = zf + 1.6
    for k in range(10):
        a = 2 * math.pi * k / 10
        bar(M["WL_timber"], P3(wc, z0), P3(wc + v * 2.2 * math.cos(a), z0 + 2.2 * math.sin(a)), w=0.08, d=0.5)
        a2 = 2 * math.pi * (k + 1) / 10
        bar(M["WL_logd"], P3(wc + v * 2.2 * math.cos(a), z0 + 2.2 * math.sin(a)), P3(wc + v * 2.2 * math.cos(a2), z0 + 2.2 * math.sin(a2)), w=0.1, d=0.6)


# ---------------------------------------------------------------- props
def lamp(M, x, y, z):
    """A dark lantern post (0:20:08): a tapered iron post, a four-sided lantern with a lit glass, a cap."""
    lathe(M["WL_lamp"], (x, y, z), [(0.14, 0.0), (0.14, 0.35), (0.06, 0.6), (0.05, 3.0), (0.1, 3.1), (0.0, 3.12)], n=6)
    box(M["WL_glow"], (x, y, z + 3.42), (0.16, 0.16, 0.28))
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(M["WL_lamp"], (x + sx * 0.16, y + sy * 0.16, z + 3.42), (0.02, 0.02, 0.3))
    loft_rect(M["WL_lamp"], (x, y, z + 3.72), (1, 0), (0, 1), [(0.24, 0.24, 0.0), (0.03, 0.03, 0.3)])


def bench(M, x, y, z, face_dir, green=False):
    """A park bench: wooden slats on green iron ends (0:18:28, 0:20:44)."""
    f = np.array([face_dir[0], face_dir[1], 0.0]); f /= (np.linalg.norm(f) or 1); r = np.array([f[1], -f[0], 0.0])
    Pb = lambda a, b, c: np.array([x, y, z]) + a * r + b * f + c * UP
    for s in (-0.85, 0.85):
        box(M["WL_benchg"], Pb(s, 0.0, 0.4), (0.04, 0.28, 0.4), (r, f, UP))
    slat = "WL_benchg" if green else "WL_bench"
    for vv in (0.16, 0.04, -0.08):
        box(M[slat], Pb(0, vv, 0.45), (0.95, 0.05, 0.025), (r, f, UP))
    for ww in (0.62, 0.8):
        box(M[slat], Pb(0, -0.22, ww), (0.95, 0.025, 0.06), (r, f, UP))


def barrel(M, x, y, z, r=0.3, h=0.85):
    lathe(M["WL_barrel"], (x, y, z), [(r * 0.85, 0.0), (r, h * 0.5), (r * 0.85, h), (0.0, h)], n=8)
    for k in (0.15, 0.85):
        frustum(M["WL_hoop"], (x, y, z + h * k - 0.03), (x, y, z + h * k + 0.03), r * 0.92, r * 0.92, n=8, caps=False)


def crate(M, x, y, z, s=0.35, rot=0.0):
    e = np.array([math.cos(rot), math.sin(rot), 0.0]); n = np.array([-e[1], e[0], 0.0])
    box(M["WL_timber"], (x, y, z + s), (s, s, s), (e, n, UP))
    box(M["WL_brown"], (x, y, z + s), (s + 0.02, s * 0.2, s + 0.02), (e, n, UP))


def hay_bale(M, x, y, z, rot=0.0):
    e = np.array([math.cos(rot), math.sin(rot), 0.0]); n = np.array([-e[1], e[0], 0.0])
    box(M["WL_hay"], (x, y, z + 0.25), (0.55, 0.35, 0.25), (e, n, UP))


def wagon_wheel(M, c, z, face_dir, r=0.6):
    f = np.array([face_dir[0], face_dir[1]], float); f /= (np.linalg.norm(f) or 1); t = np.array([-f[1], f[0]])
    rim = [(c + t * r * math.cos(2 * math.pi * k / 12), z + r + r * math.sin(2 * math.pi * k / 12)) for k in range(12)]
    for (p0, z0), (p1, z1) in zip(rim, rim[1:] + rim[:1]):
        bar(M["WL_wheel"], P3(p0, z0), P3(p1, z1), w=0.06, d=0.06)
    for k in range(0, 12, 2):
        bar(M["WL_wheel"], P3(c, z + r), P3(rim[k][0], rim[k][1]), w=0.03, d=0.03)


def trough(M, x, y, z, rot):
    e = np.array([math.cos(rot), math.sin(rot), 0.0]); n = np.array([-e[1], e[0], 0.0])
    loft_rect(M["WL_timber"], (x, y, z), e, n, [(0.8, 0.3, 0.0), (0.9, 0.38, 0.55)], cap=False)
    box(M["WL_water"], (x, y, z + 0.45), (0.85, 0.33, 0.02), (e, n, UP))


def hitching_rail(M, p0, p1, z_of):
    p0, p1 = V(p0), V(p1)
    L = np.linalg.norm(p1 - p0)
    if L < 1.5:
        return
    za, zb = z_of(*p0), z_of(*p1)
    for q, zz in ((p0, za), (p1, zb)):
        box(M["WL_post"], P3(q, zz + 0.45), (0.07, 0.07, 0.55))
    bar(M["WL_post"], P3(p0, za + 0.95), P3(p1, zb + 0.95), w=0.08, d=0.08)


def log_fence(M, line, z_of, h=1.0, step=2.2):
    """A log-rail fence (0:18:40, 0:20:08): posts every 2.2 m, two rails."""
    L = line.length
    if L < 1.0:
        return 0
    n = 0
    for d in np.arange(0.0, L + 0.01, step):
        q = line.interpolate(min(d, L)); z = z_of(q.x, q.y)
        frustum(M["WL_log"], (q.x, q.y, z - 0.1), (q.x, q.y, z + h + 0.08), 0.08, 0.07, n=6)
        n += 1
    pts = [line.interpolate(min(d, L)) for d in np.arange(0.0, L + step, step)]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        za, zb = z_of(p0.x, p0.y), z_of(p1.x, p1.y)
        for hh in (h * 0.5, h * 0.95):
            bar(M["WL_log"], (p0.x, p0.y, za + hh), (p1.x, p1.y, zb + hh), w=0.09, d=0.09)
    return n


def xbrace_rail(M, line, z_of, h=1.05, step=2.4):
    """The Westernland bridge's railing (0:15:04): posts, a top rail, X braces between them."""
    L = line.length
    pts = [line.interpolate(min(d, L)) for d in np.arange(0.0, L + step * 0.99, step)]
    for p in pts:
        z = z_of(p.x, p.y)
        box(M["WL_brown"], (p.x, p.y, z + h / 2), (0.08, 0.08, h / 2 + 0.05))
    for p0, p1 in zip(pts[:-1], pts[1:]):
        za, zb = z_of(p0.x, p0.y), z_of(p1.x, p1.y)
        bar(M["WL_brown"], (p0.x, p0.y, za + h), (p1.x, p1.y, zb + h), w=0.12, d=0.1)
        bar(M["WL_brown"], (p0.x, p0.y, za + 0.1), (p1.x, p1.y, zb + 0.1), w=0.08, d=0.08)
        bar(M["WL_brown"], (p0.x, p0.y, za + 0.12), (p1.x, p1.y, zb + h - 0.05), w=0.06, d=0.06)
        bar(M["WL_brown"], (p0.x, p0.y, za + h - 0.05), (p1.x, p1.y, zb + 0.12), w=0.06, d=0.06)


# ---------------------------------------------------------------- planting
def flower_clump(M, x, y, z, mat, s=1.0):
    r = 0.2 * s
    pts = [(x + r * math.cos(2 * math.pi * k / 6), y + r * math.sin(2 * math.pi * k / 6), z + 0.26 * s) for k in range(6)]
    for k in range(6):
        tri(M["WL_leaf"], (x, y, z), pts[k], pts[(k + 1) % 6], np.array([pts[k][0] - x, pts[k][1] - y, -0.2]))
        tri(M[mat], (x, y, z + 0.36 * s), pts[k], pts[(k + 1) % 6], UP)


def fan(M, x, y, z, s=1.0, mat="WL_fern", n=6, rot=0.0, up=0.55):
    """Ferns, agaves, grass: n leaves arching out from the centre (two triangles each)."""
    for k in range(n):
        a = rot + 2 * math.pi * k / n
        d = np.array([math.cos(a), math.sin(a)]); w = np.array([-d[1], d[0]])
        base = np.array([x, y, z])
        mid = base + np.r_[d * 0.45 * s, up * s]
        tip = base + np.r_[d * 0.9 * s, 0.2 * s + (up - 0.55) * s]
        tri(M[mat], base, mid + np.r_[w * 0.13 * s, 0], mid - np.r_[w * 0.13 * s, 0], UP)
        tri(M[mat], mid + np.r_[w * 0.13 * s, 0], tip, mid - np.r_[w * 0.13 * s, 0], UP)


def grass_tuft(M, x, y, z, s=1.0, rot=0.0, mat="WL_grass"):
    for k in range(5):
        a = rot + 2 * math.pi * k / 5
        d = np.array([math.cos(a), math.sin(a)]) * 0.18 * s
        tri(M[mat], (x - d[1] * 0.3, y + d[0] * 0.3, z), (x + d[1] * 0.3, y - d[0] * 0.3, z), (x + d[0] * 1.6, y + d[1] * 1.6, z + 0.6 * s), UP)


def sage(M, x, y, z, s=1.0):
    """A low grey-green sage-like shrub: a flattened low-poly mound."""
    sphere(M["WL_sage"], (x, y, z + 0.22 * s), 0.45 * s, n=5, m=2, sc=(1.0, 1.0, 0.6))


def cactus(M, x, y, z, h=1.8, rng=RNG):
    """A low column cactus with two arms (kept under 2.5 m: no trees)."""
    frustum(M["WL_cactus"], (x, y, z), (x, y, z + h), 0.2, 0.17, n=6)
    lathe(M["WL_cactus"], (x, y, z + h), [(0.17, 0.0), (0.0, 0.14)], n=6)
    for s in (-1, 1):
        if rng.random() < 0.8:
            a = rng.uniform(0, 6.3)
            d = np.array([math.cos(a), math.sin(a), 0.0])
            zz = z + h * rng.uniform(0.35, 0.6)
            p0 = np.array([x, y, zz]); p1 = p0 + d * 0.45 * s
            frustum(M["WL_cactus"], p0, p1, 0.12, 0.12, n=4, caps=False)
            frustum(M["WL_cactus"], p1, p1 + UP * h * 0.35, 0.12, 0.1, n=4)


def planting(ctx, beds, gr_z, rng):
    """Flowers, grasses, ferns, sage on the beds' soil ribbons (per kerb kind), taller clumps in the shrub masses, cacti
    and agaves in the beds by Big Thunder."""
    M = ctx.M; count = 0
    mt = ctx.P["mountain"]
    pal = {"stone": ("WL_fl_red", "WL_fl_yel", "WL_fl_wht", "WL_fl_pink", "WL_fl_pur", "WL_fl_org"),
           "board": ("WL_fl_yel", "WL_fl_red", "WL_fl_org", "WL_fl_wht"), "wild": ("WL_fl_wht", "WL_fl_yel")}
    for rib, kind, soil_h in beds["ribs"]:
        pl = pal[kind]
        desert = rib.distance(mt) < 14
        for p in G._polys(rib):
            mid = p.buffer(-0.18)
            for g in (G._polys(mid) or [p]):
                ring = g.exterior
                run_col = pl[int(rng.integers(len(pl)))]; run_left = 0
                step = 0.62 if kind != "wild" else 1.1
                for d in np.arange(0.0, ring.length, step):
                    q = ring.interpolate(d); z = gr_z(q.x, q.y) + soil_h
                    if run_left <= 0:
                        run_col = pl[int(rng.integers(len(pl)))]; run_left = int(rng.integers(4, 12))
                    run_left -= 1
                    k = rng.random()
                    if desert:
                        if k < 0.07:
                            cactus(M, q.x, q.y, z, h=rng.uniform(0.9, 2.2), rng=rng)
                        elif k < 0.45:
                            fan(M, q.x, q.y, z, s=rng.uniform(0.5, 0.8), mat="WL_agave", n=8, rot=rng.uniform(0, 6.3), up=0.75)
                        elif k < 0.7:
                            grass_tuft(M, q.x, q.y, z, s=rng.uniform(0.8, 1.3), rot=rng.uniform(0, 6.3))
                        elif k < 0.85:
                            sage(M, q.x, q.y, z, s=rng.uniform(0.7, 1.1))
                        else:
                            flower_clump(M, q.x, q.y, z, ("WL_fl_yel", "WL_fl_org")[int(rng.integers(2))], s=0.9)
                    elif kind == "wild":
                        if k < 0.45:
                            grass_tuft(M, q.x, q.y, z, s=rng.uniform(0.8, 1.4), rot=rng.uniform(0, 6.3))
                        elif k < 0.75:
                            fan(M, q.x, q.y, z, s=rng.uniform(0.6, 1.0), rot=rng.uniform(0, 6.3))
                        elif k < 0.92:
                            sage(M, q.x, q.y, z, s=rng.uniform(0.8, 1.3))
                        else:
                            flower_clump(M, q.x, q.y, z, run_col, s=0.9)
                    else:
                        if k < 0.55:
                            flower_clump(M, q.x, q.y, z, run_col, s=rng.uniform(0.85, 1.2))
                        elif k < 0.72:
                            fan(M, q.x, q.y, z, s=rng.uniform(0.55, 0.9), rot=rng.uniform(0, 6.3))
                        elif k < 0.86:
                            grass_tuft(M, q.x, q.y, z, s=rng.uniform(0.8, 1.2), rot=rng.uniform(0, 6.3))
                        else:
                            sage(M, q.x, q.y, z, s=rng.uniform(0.6, 1.0))
                    count += 1
    for inner, kind, soil_h in beds["inners"]:
        for p in G._polys(inner):
            n = int(p.area / (6.0 if kind != "wild" else 12.0))
            x0, y0, x1, y1 = p.bounds
            for _ in range(min(n, 400)):
                q = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
                if not p.contains(q):
                    continue
                z = gr_z(q.x, q.y) + soil_h + 0.5
                k = rng.random()
                if k < 0.4:
                    fan(M, q.x, q.y, z, s=rng.uniform(1.1, 1.6), mat="WL_leaf" if rng.random() < 0.5 else "WL_fern", n=7, rot=rng.uniform(0, 6.3))
                elif k < 0.7 and kind != "wild":
                    flower_clump(M, q.x, q.y, z + 0.1, FLOWERS[int(rng.integers(len(FLOWERS)))], s=1.3)
                else:
                    grass_tuft(M, q.x, q.y, z, s=1.5, rot=rng.uniform(0, 6.3))
                count += 1
    return count


# ---------------------------------------------------------------- assembly
def items_in_scope(P):
    """(id, tags, polygon) of the OSM buildings this module replaces: centroid in BOX, not in FANTASY, not already another
    model's (MODEL_KEYS), not a land other than Westernland by name, not underground."""
    out = []
    for w in DL.DATA["ways"]:
        if "building" in w["tags"] and w["closed"] and len(w["pts"]) >= 4:
            out.append((w["id"], w["tags"], Polygon(w["pts"]).buffer(0)))
    for r in DL.DATA["relations"]:
        if "building" in r["tags"]:
            rings = DL.outer_rings(r)
            if rings:
                out.append((r["id"], r["tags"], Polygon(rings[0]).buffer(0)))
    res = []
    for oid, tags, poly in out:
        if poly.is_empty or poly.area < 1.5:
            continue
        c = poly.centroid
        if not BOX.contains(c) or FANTASY.contains(c):
            continue
        if oid != PAVILION and DL.MODEL_KEYS.get(oid, "dlwest") != "dlwest":
            continue
        if DL.land_of_name(tags.get("name", "")) not in (None, 2):
            continue
        if tags.get("layer") == "-1":
            continue
        res.append((oid, tags, poly))
    return res


def water_level(P):
    bb = BOX.bounds
    try:
        t = load_tris(MODELS / "tdl_water.json", lambda n: True, bb)
        S = Surface(t)
        zs = [S.z(x, y) for x, y in ((-175, 540), (-150, 560), (-100, 560), (-60, 600))]
        zs = [z for z in zs if z is not None]
        if zs:
            return float(np.median(zs))
    except Exception:
        pass
    return -1.6


def build():
    P, T, gm, beds, ginfo = build_ground()
    info = dict(ground=ginfo)
    tris = [np.array(m.tris) for k, m in gm.items() if m.tris and k not in ("WG_edge",)]
    own = np.concatenate([t.reshape(-1, 3, 3) for t in tris])
    bb = BOX.buffer(30).bounds
    others = [load_tris(MODELS / "tdl_plaza_ground.json", lambda n: n != "TP_edge", bb),
              load_tris(MODELS / "tdl_land_ground.json", lambda n: n != "TL_edge", bb),
              load_tris(MODELS / "tdl_adv_ground.json", lambda n: n != "AG_edge", bb)]

    class GrS:
        def __init__(self):
            self.a = Surface(own); self.b = Surface(np.concatenate([o for o in others if len(o)]))

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
    ctx = Ctx(M, gr, P)
    zw = water_level(P)
    info["water_z"] = round(zw, 2)
    items = items_in_scope(P)
    info["ids"] = sorted(i for i, _, _ in items if i != PAVILION)
    styles = {}
    island = P["island"]
    fort_polys = []
    for oid, tags, poly in items:
        try:
            roof_only = tags.get("building") == "roof"
            if oid in PIERS:
                styles[oid] = "pier"; continue
            if oid == PAVILION:
                part = max(polys(poly.intersection(DH_PART)), key=lambda g: g.area)
                styles[oid] = ("dh", diamond_horseshoe(ctx, part))
            elif oid == TRADING:
                styles[oid] = ("town", plain_block(ctx, poly, 2, town_fronts(ctx, 0)))
            elif oid == BEARS:
                styles[oid] = ("bears", bears_block(ctx, poly))
            elif oid == SMALL_STONE:
                styles[oid] = ("stone", plain_block(ctx, poly, 1, lambda *a: dict(style="stone", n=1, sign=ctx.sign_for((a[3] + a[4]) / 2, a[5]) if a[1] == 0 else None)))
            elif oid == ASSAYER:
                styles[oid] = ("assayer", plain_block(ctx, poly, 2, lambda *a: dict(style="grey", n=2, sign="ASSAYER'S OFFICE" if a[1] == 0 else None, top="stepped"), back="WL_grey"))
                zb, zf = floor_of(ctx, poly)
                c = poly.representative_point()
                water_tank(M, (c.x, c.y), zf + 7.4, r=1.3, h=2.0, legs=1.4)
            elif oid == BT_STATION:
                styles[oid] = ("station", plain_block(ctx, poly, 2, lambda *a: dict(style="grey" if a[1] % 2 else "brown", n=2,
                               sign="BIG THUNDER MOUNTAIN" if a[1] == 0 else None, top="stepped"), roof="WL_tin", back="WL_grey"))
            elif oid == BT_SHED:
                zb, zf = floor_of(ctx, poly)
                sides(M["WL_grey"], poly, zb, zf + 6.0); roof_over(M, poly, zf + 6.0, "WL_tin")
                styles[oid] = "shed"
            elif oid == DIORAMA or oid in BT_SHOW:
                if oid in BT_SHOW:
                    styles[oid] = "rock"; continue                       # under the rock mass
                zb, zf = floor_of(ctx, poly)
                sides(M["WL_show"], poly, zb, zf + 8.5); cap(M["WL_show"], poly, zf + 8.5)
                styles[oid] = "show"
            elif oid == LANDING:
                styles[oid] = "landing"; continue                        # built below
            elif oid in FORT:
                fort_polys.append(poly); styles[oid] = "fort"
            elif oid == MILL:
                mill(ctx, poly); styles[oid] = "mill"
            elif oid in WOODCHUCK:
                styles[oid] = log_cabin(ctx, poly, roof="WL_roof", h=3.4, sign="CAMP WOODCHUCK" if oid == 763060486 else None)
            elif roof_only:
                styles[oid] = canopy(ctx, poly) if poly.area > 8 else booth(ctx, poly)
            elif poly.area < 8 and poly.centroid.x > -20 and (island.contains(poly.centroid) or Z_WILD.contains(poly.centroid)):
                c = poly.centroid
                tipi(M, (c.x, c.y), gr.z(c.x, c.y), r=max(1.1, math.sqrt(poly.area / math.pi) + 0.2))
                styles[oid] = "tipi"
            elif island.contains(poly.centroid) or Z_WILD.contains(poly.centroid):
                styles[oid] = log_cabin(ctx, poly, roof="WL_roofd", wall="WL_logd" if oid == 1295345351 else "WL_log")
            elif poly.area < 14:
                styles[oid] = booth(ctx, poly)
            elif oid == 1303823621:                                        # Country Bear Bandwagon: a covered-wagon kiosk
                c, u, v, hu, hv = rect_of(poly)
                covered_wagon(M, c, u, gr.z(*c), kiosk=True); styles[oid] = "wagon"
            elif poly.area < 150:
                styles[oid] = ("shop", small_shop(ctx, poly))
            else:
                styles[oid] = ("town", plain_block(ctx, poly, 2, town_fronts(ctx, len(styles))))
        except Exception as ex:
            import traceback; traceback.print_exc()
            styles[oid] = f"FAILED {ex!r}"[:160]
    if fort_polys:
        info["stockade"] = fort(ctx, fort_polys)
    pp = [poly_of(i) for i in PIERS]
    pp = [p for p in pp if not p.is_empty]
    if pp:                                                             # the Hungry Bear gallery piers: log posts, a shingle roof
        zb, zf = floor_of(ctx, unary_union(pp).convex_hull)
        for p in pp:
            c = p.centroid
            frustum(M["WL_log"], (c.x, c.y, zb), (c.x, c.y, zf + 3.6), 0.28, 0.26, n=8)
        hull = unary_union(pp).convex_hull.buffer(1.2, join_style=2)
        c, u, v, hu, hv = rect_of(hull)
        loft_rect(M["WL_roof"], P3(c, zf + 3.6), u, v, [(hu + 0.3, hv + 0.3, 0.0), (hu + 0.3, 0.05, min(1.8, hv))])
        ctx.solid.append(hull)
        info["piers"] = len(pp)
    info["styles"] = {k: (v if isinstance(v, str) else v[0]) for k, v in styles.items()}
    info["failed"] = {k: v for k, v in styles.items() if isinstance(v, str) and v.startswith("FAILED")}
    # boardwalk decks (union per height)
    for strip, zt in ctx.decks:
        for p in polys(strip, 0.3):
            cap(M["WL_deck"], p, zt)
            for a, b, nrm in ring_edges(p):
                za, zb2 = gr.z(*a) - 0.1, gr.z(*b) - 0.1
                quad(M["WL_timber"], P3(a, za), P3(b, zb2), P3(b, zt), P3(a, zt), N3(nrm))
            L = p.exterior.length
            for d in np.arange(0.0, L, 0.6):                              # plank seams along the edge (cheap: short dark strips)
                pass
    info["decks"] = len(ctx.decks)
    # landing + riverboat
    try:
        edge, u, v = landing(ctx, zw)
        riverboat(M, edge, u, v, zw)
        info["landing"] = "ok"
    except Exception as ex:
        import traceback; traceback.print_exc()
        info["landing"] = f"FAILED {ex!r}"
    # Big Thunder, coaster, railway
    info["big_thunder"] = big_thunder(ctx)
    info["coaster"] = coaster(ctx)
    info["railway"] = railway(ctx)
    # the hub bridge's X-braced railings
    bw = way(BRIDGE_WAY)
    if bw is not None:
        bp = Polygon(bw["pts"]).buffer(0)
        for a, b, nrm in ring_edges(bp):
            if np.linalg.norm(b - a) > 4 and P["water"].buffer(1.5).intersects(LineString([a, b]).buffer(0.5)):
                e = (b - a) / np.linalg.norm(b - a)
                xbrace_rail(M, LineString([a - nrm * 0.2 + e * 0.3, b - nrm * 0.2 - e * 0.3]), lambda x, y: gr.z(x, y))
    sb = way(STREAM_BRIDGE)
    if sb is not None:
        bp = Polygon(sb["pts"]).buffer(0)
        zt = gr.z(*bp.centroid.coords[0]) + 0.05
        cap(M["WL_deck"], bp, zt); sides(M["WL_timber"], bp, zt - 0.5, zt)
        ctx.decks.append((bp, zt))
        for a, b, nrm in ring_edges(bp):
            if np.linalg.norm(b - a) > 3:
                log_fence(M, LineString([a - nrm * 0.15, b - nrm * 0.15]), lambda x, y: zt)
    # ---- props
    rng = np.random.default_rng(55)
    keep_off = unary_union([P["buildings"].buffer(0.6), unary_union([d for d, _ in ctx.decks]).buffer(0.3) if ctx.decks else Polygon(),
                            unary_union(ctx.solid).buffer(0.3) if ctx.solid else Polygon(), P["mountain"].buffer(1.0)])
    pv = P["paving"].buffer(-0.8)
    free = lambda x, y: pv.contains(Point(x, y)) and not keep_off.contains(Point(x, y))
    taken = []
    def ok(x, y, r):
        if not free(x, y):
            return False
        if any((x - a) ** 2 + (y - b) ** 2 < (r + rr) ** 2 for a, b, rr in taken):
            return False
        taken.append((x, y, r)); return True
    # hitching rails, troughs, barrels and crates along the boardwalks
    n_h = n_p = 0
    for p0, p1 in ctx.hitch:
        p0, p1 = V(p0), V(p1)
        e = p1 - p0; L = np.linalg.norm(e)
        if L < 3:
            continue
        e /= L
        k = rng.random()
        m = (p0 + p1) / 2
        if k < 0.35 and ok(*(m), 1.2):
            hitching_rail(M, m - e * 1.2, m + e * 1.2, gr.z); n_h += 1
        elif k < 0.5 and ok(*m, 1.0):
            trough(M, m[0], m[1], gr.z(*m), math.atan2(e[1], e[0])); n_h += 1
        q = p0 + e * 0.6
        if ok(*q, 0.5):
            barrel(M, q[0], q[1], gr.z(*q)); n_p += 1
            if rng.random() < 0.5:
                q2 = q + e * 0.75
                crate(M, q2[0], q2[1], gr.z(*q2), rot=rng.uniform(0, 3)); n_p += 1
        if rng.random() < 0.3:
            q = p1 - e * 0.8
            if ok(*q, 0.7):
                hay_bale(M, q[0], q[1], gr.z(*q), rot=math.atan2(e[1], e[0])); n_p += 1
    info["hitch_troughs"], info["barrels_crates"] = n_h, n_p
    # lamps along the boardwalks and the beds, benches by the beds, bins
    lamps = []
    for q in ctx.lamp_spots:
        q = V(q)
        if free(*q) and all(np.hypot(q[0] - a, q[1] - b) > 9 for a, b in lamps):
            lamps.append((q[0], q[1]))
    benches = []
    stones = 0
    for q, kind, soil_h in beds["beds"]:
        ring = q.buffer(0.75, join_style=2).exterior
        for d in np.arange(3.0, ring.length - 2.0, 10.0):
            s = ring.interpolate(d); s2 = ring.interpolate(d + 0.5)
            t = np.array([s2.x - s.x, s2.y - s.y]); t /= (np.linalg.norm(t) or 1)
            nrm = np.array([t[1], -t[0]])
            if q.contains(Point(s.x + nrm[0], s.y + nrm[1])):
                nrm = -nrm
            if not free(s.x + nrm[0] * 0.4, s.y + nrm[1] * 0.4):
                continue
            if kind != "wild" and q.area > 10 and d % 20 < 10 and len(benches) < 110:
                if all(np.hypot(s.x - a, s.y - b) > 6 for a, b, _ in benches):
                    benches.append((s.x, s.y, nrm)); taken.append((s.x, s.y, 1.0))
            elif all(np.hypot(s.x - a, s.y - b) > 13 for a, b in lamps) and q.area > 6:
                lamps.append((s.x, s.y))
        if kind == "stone":                                             # rounded river stones on the kerb (0:17:52)
            r2 = orient(q, 1.0).exterior
            for d in np.arange(0.0, r2.length, 0.85):
                s = r2.interpolate(d)
                rr = rng.uniform(0.28, 0.4)
                a = rng.uniform(0, 3.14); ea = np.array([math.cos(a), math.sin(a), 0.0])
                box(M["WL_stone"], (s.x, s.y, gr.z(s.x, s.y) + CURB_H + 0.05), (rr * 0.75, rr * 0.6, rr * 0.45), (ea, np.cross(UP, ea), UP))
                stones += 1
    for x, y in lamps:
        lamp(M, x, y, gr.z(x, y))
    for k, (x, y, nrm) in enumerate(benches):
        bench(M, x, y, gr.z(x, y), nrm, green=y < 600)
        if k % 3 == 0:
            e = np.array([-nrm[1], nrm[0]])
            bx, by = x + e[0] * 1.5, y + e[1] * 1.5
            loft_rect(M["WL_bin"], (bx, by, gr.z(bx, by)), (1, 0), (0, 1), [(0.3, 0.3, 0), (0.3, 0.3, 1.0)])
            loft_rect(M["WL_roofd"], (bx, by, gr.z(bx, by) + 1.0), (1, 0), (0, 1), [(0.36, 0.36, 0), (0.1, 0.1, 0.2)])
    info["lamps"], info["benches"], info["kerb_stones"] = len(lamps), len(benches), stones
    # log fences: along the water where the paving meets it, and on the river side of the beds
    n_f = 0
    edge = P["paving"].boundary.intersection(P["water"].buffer(2.5))
    for ls in getattr(edge, "geoms", [edge]):
        if ls.geom_type == "LineString" and ls.length > 3:
            n_f += log_fence(M, ls.simplify(0.3).parallel_offset(0.4, "left") if False else ls.simplify(0.3), gr.z)
    for q, kind, soil_h in beds["beds"]:
        if kind == "board" and q.representative_point().y < 575 and q.area > 15:
            ring = q.buffer(0.35, join_style=2).exterior
            pieces = ring.difference(P["buildings"].buffer(1.0)).intersection(P["paving"].buffer(0.5))
            for ls in getattr(pieces, "geoms", [pieces]):
                if ls.geom_type == "LineString" and ls.length > 3:
                    n_f += log_fence(M, ls.simplify(0.3), gr.z, h=0.9)
    info["fence_posts"] = n_f
    # landmarks: bear statue, covered wagon, log wagon, locomotive, flag pole, wagon wheels, queue posts
    def near_free(x, y, r=1.5, tries=40):
        for k in range(tries):
            a = k * 2.4; d = 0.6 * k
            q = (x + d * math.cos(a), y + d * math.sin(a))
            if ok(q[0], q[1], r):
                return q
        return None
    q = near_free(-243.0, 607.0, 2.5)
    if q:
        covered_wagon(M, q, (1.0, 0.2), gr.z(*q), kiosk=True)
    near = min((b for b in beds["beds"] if b[1] == "stone"), key=lambda b: b[0].distance(Point(-236, 615)), default=None)
    if near is not None:
        s = near[0].buffer(-0.6).representative_point() if not near[0].buffer(-0.6).is_empty else near[0].representative_point()
        bear_statue(M, (s.x, s.y), gr.z(s.x, s.y) + near[2], (-1.0, 0.2))
        info["bear"] = (round(s.x, 1), round(s.y, 1))
    q = near_free(-300.0, 628.0, 2.5)
    if q:
        covered_wagon(M, q, (0.3, 1.0), gr.z(*q))
    q = near_free(-172.0, 622.0, 2.5)
    if q:                                                               # a log wagon (0:18:40)
        e = np.array([1.0, 0.25]); e /= np.linalg.norm(e); n = np.array([-e[1], e[0]])
        z = gr.z(*q)
        box(M["WL_timber"], P3(q, z + 0.9), (1.6, 0.6, 0.08), B3(e, n))
        for s in (-1, 1):
            for t in (-1, 1):
                wagon_wheel(M, V(q) + e * t * 1.1 + n * s * 0.7, z, n)
        for j in range(5):
            frustum(M["WL_log"], P3(V(q) - e * 2.0 + n * (j % 3 - 1) * 0.4, z + 1.2 + (j // 3) * 0.35), P3(V(q) + e * 2.0 + n * (j % 3 - 1) * 0.4, z + 1.2 + (j // 3) * 0.35), 0.18, 0.18, n=7)
    st = poly_of(BT_STATION)
    if not st.is_empty:
        a, b, nrm = min(ring_edges(st), key=lambda t: ((t[0] + t[1]) / 2)[0])
        e = (b - a) / np.linalg.norm(b - a)
        q = V((a + b) / 2) + nrm * 9.0
        if free(*q):
            locomotive(M, q, e, gr.z(*q)); taken.append((q[0], q[1], 3.0))
        for row in (5.5, 7.0):                                         # rope queue posts (1:04:40)
            pts = [a + nrm * row + e * t for t in np.arange(0.0, np.linalg.norm(b - a), 1.8)]
            pts = [p for p in pts if free(*p)]
            for p in pts:
                frustum(M["WL_qpost"], P3(p, gr.z(*p)), P3(p, gr.z(*p) + 1.0), 0.05, 0.05, n=6)
            for p0, p1 in zip(pts[:-1], pts[1:]):
                if np.linalg.norm(p1 - p0) < 2.0:
                    bar(M["WL_rope"], P3(p0, gr.z(*p0) + 0.85), P3(p1, gr.z(*p1) + 0.85), w=0.025, d=0.025)
    q = near_free(-92.0, 572.0, 1.0)
    if q:                                                               # flag pole at Camp Woodchuck (0:19:50)
        z = gr.z(*q)
        frustum(M["WL_white"], (q[0], q[1], z), (q[0], q[1], z + 10.0), 0.1, 0.05, n=8)
        sphere(M["WL_gold"], (q[0], q[1], z + 10.1), 0.12, n=6, m=4)
        quad(M["WL_flag"], (q[0], q[1], z + 9.8), (q[0] + 1.6, q[1], z + 9.7), (q[0] + 1.6, q[1], z + 8.7), (q[0], q[1], z + 8.6), (0, 1, 0))
    n_w = 0
    for q0, kind, soil_h in beds["beds"]:
        if kind == "stone" and q0.area > 20 and n_w < 14:
            s = q0.exterior.interpolate(0.3, normalized=True)
            z = gr.z(s.x, s.y) + soil_h
            c0 = q0.centroid
            wagon_wheel(M, (s.x, s.y), z, (c0.x - s.x, c0.y - s.y)); n_w += 1
    info["wheels"] = n_w
    info["plants"] = planting(ctx, beds, gr.z, rng)
    return gm, M, info


def main():
    gm, M, info = build()
    MODELS.mkdir(parents=True, exist_ok=True)
    ng = G.write_gltf(OUT_G, {k: m for k, m in gm.items() if m.tris})
    nb = G.write_gltf(OUT_B, {k: m for k, m in M.items() if m.tris})
    print(f"[westernland] {OUT_G.name} {OUT_G.stat().st_size / 1024:.0f} KB {ng} tris; {OUT_B.name} {OUT_B.stat().st_size / 1024:.0f} KB {nb} tris")
    for k, v in info.items():
        print(f"  {k}: {v}")
    big = sorted(((len(m.tris), k) for k, m in M.items()), reverse=True)[:14]
    print("  top meshes:", big)


if __name__ == "__main__":
    main()
