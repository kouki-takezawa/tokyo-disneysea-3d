"""東京ディズニーランド全体の地面 -- the ground of the whole of Tokyo Disneyland, from its car parks to the back of the park
(plain Python: shapely + numpy, Blender is not needed; no trees). Same method as ds_tdl_ground.py, whose helpers it reuses.

  python ds_tdl_land_ground.py       # -> output/disneysea/models/tdl_land_ground.json (glTF, buffer embedded) + a summary
  python export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_land_ground", layer ディズニーランド)

Area: the park (OSM way 1282875870, which already takes in the big car park to the south-west) and the surface car parks next to it
  (amenity=parking within LOT_REACH m: the lots west of the park, グーフィー / ピノキオ / ティンカーベル ...), closed by CLOSE m so the
  strips between them are included. Left to the models already made: the entrance plaza (ds_tdl_ground.py) and the ground round
  the hotel and the station (ds_tdl_hotel_ground.py). DisneySea is outside.
What each piece is (OSM, plateau_data/disneyland_osm.json; the first that applies wins):
  (hole)   buildings (not the roofs on posts; not the booths and shelters under SMALL_BUILDING m2): nothing is built there, EXCEPT the passages through them: footways / service
           roads / pedestrian areas tagged tunnel=building_passage or covered=yes, and the ones with layer<0 that stay inside a
           building footprint (the arcades, the gate tunnels): ground at the terrain height, PASSAGE_W m wide
  water    natural=water / water=* (ways and multipolygons: the Rivers of America, the moats, ponds)  -> a flat surface at the
           water level (the 10th percentile of the ground round it - WATER_DROP), with a bank from the ground down to it
  paving   highway=pedestrian areas (ways and multipolygons) and the footways / steps / pedestrian lines (3.5 m, 8 m)
  road     highway=service and the other roads inside the area (5 m; 7 m for tertiary and up)  -> asphalt
  parking  amenity=parking areas on the ground  -> asphalt (darker)
  grass    leisure=garden / park, landuse=grass / meadow / flowerbed / farmland, natural=grassland
  wood     landuse=forest, natural=wood / scrub  -> dark planted ground (trees are left out)
  rock     natural=scree / bare_rock / sand (Big Thunder Mountain, the islands)
  earth    landuse=construction
  ground   everything else inside the area (backstage yards, the gaps between the mapped pieces)
Heights: the same terrain as ds_tdl_ground.py (GSI DEM5A on the mock's datum, smoothed; flat under the entrance model), the DEM
  under buildings filled from the ground round them (it is not ground), level with the Resort Line station's floor next to it.
Mesh: every piece is cut into CELL_LAND m cells and triangulated (constrained Delaunay); a skirt on the free edges.
ESTIMATES: the widths, the colours, the water levels, which lots count. The rides' own ground (inside the show buildings) is not
  modelled; the castles and the mountains sit on this ground as their models do.
"""
import sys, json, math, pathlib, time

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ds_disneyland as DL
import ds_tdl_ground as G
import ds_tdl_hotel_ground as H

OUT = ROOT / "output" / "disneysea" / "models" / "tdl_land_ground.json"
LOT_REACH, CLOSE = 30.0, 25.0
CELL_LAND, TILE = 8.0, 64.0
PASSAGE_W = 4.0
SMALL_BUILDING = 50.0                          # m2: the ground goes on under smaller buildings (booths, shelters: holes would be specks)
W_FOOT, W_PED, W_SERVICE, W_ROAD = 3.5, 8.0, 5.0, 7.0
WATER_DROP, BANK_BELOW = 0.6, 0.3
ROADS = ("service", "unclassified", "residential", "tertiary", "secondary", "primary", "living_street", "track")
KINDS = ("TL_water", "TL_paving", "TL_road", "TL_parking", "TL_grass", "TL_wood", "TL_rock", "TL_earth", "TL_ground")


# ---------------------------------------------------------------- OSM areas
def _mp(r):
    """Polygons of a multipolygon relation, inner rings cut out."""
    outers = [Polygon(o).buffer(0) for o in DL.outer_rings(r) if len(o) >= 4]
    inners = []
    for m in r["members"]:
        if m["role"] == "inner" and m["way"] in DL.WAYS and len(DL.WAYS[m["way"]]["pts"]) >= 4:
            inners.append(Polygon(DL.WAYS[m["way"]]["pts"]).buffer(0))
    if not outers:
        return Polygon()
    g = unary_union(outers)
    return g.difference(unary_union(inners)) if inners else g


def areas(pred, clip):
    """Union of the closed ways and multipolygons whose tags match, clipped."""
    out = []
    for w in DL.DATA["ways"]:
        if w["closed"] and len(w["pts"]) >= 4 and pred(w["tags"]):
            p = Polygon(w["pts"]).buffer(0)
            if p.intersects(clip):
                out.append(p)
    for r in DL.DATA["relations"]:
        if r["tags"].get("type") == "multipolygon" or r["tags"].get("type") is None:
            if pred(r["tags"]):
                p = _mp(r)
                if not p.is_empty and p.intersects(clip):
                    out.append(p)
    return unary_union(out).intersection(clip) if out else Polygon()


def on_ground(t):
    try:
        layer = int(str(t.get("layer", "0")).split(";")[0])
    except ValueError:
        layer = 0
    return layer <= 0 and t.get("bridge") in (None, "no")


def is_building(t):
    return "building" in t and t["building"] not in ("roof", "no") and not ("parking" in t and t.get("parking") == "surface")


# ---------------------------------------------------------------- plan
def plan():
    park = Polygon(DL.ring_of(DL.WAYS[DL.TDL_PARK_WAY])).buffer(0)
    tds = Polygon(DL.ring_of(DL.WAYS[DL.TDS_PARK_WAY])).buffer(0) if DL.TDS_PARK_WAY in DL.WAYS else Polygon()
    lots = [Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"]
            if w["tags"].get("amenity") == "parking" and w["closed"] and len(w["pts"]) >= 4 and not is_building(w["tags"])
            and w["tags"].get("parking") not in ("underground", "multi-storey") and on_ground(w["tags"])
            and Polygon(w["pts"]).buffer(0).distance(park) < LOT_REACH]
    region = unary_union([park] + lots).buffer(CLOSE, join_style=2).buffer(-CLOSE, join_style=2)
    region = region.difference(tds)
    # already modelled: the entrance plaza and the hotel / station ground
    E = G.plan(); HP = H.plan()
    done = unary_union([E["closed"], HP["road"], HP["path"], HP["plaza"], HP["station"], HP["station_path"]] + HP["planters"])
    region = region.difference(done)
    clip = region

    # buildings and the passages through them
    bl = [Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"] if w["closed"] and len(w["pts"]) >= 4 and is_building(w["tags"])]
    bl += [_mp(r) for r in DL.DATA["relations"] if is_building(r["tags"])]
    bl = unary_union([b for b in bl if not b.is_empty and b.area >= SMALL_BUILDING and b.intersects(clip)])
    passages = []
    for w in DL.DATA["ways"]:
        t = w["tags"]
        if t.get("highway") not in ("footway", "pedestrian", "service", "steps", "corridor") or len(w["pts"]) < 2:
            continue
        ls = LineString(w["pts"])
        if not ls.intersects(bl):
            continue
        tunnel_like = t.get("tunnel") == "building_passage" or t.get("covered") == "yes" or (t.get("tunnel") and ls.within(bl.buffer(2.0)))
        if tunnel_like:
            passages.append(ls.buffer(PASSAGE_W / 2, cap_style=2, join_style=1))
    for w in DL.DATA["ways"]:   # pedestrian areas inside buildings (arcades)
        t = w["tags"]
        if w["closed"] and len(w["pts"]) >= 4 and t.get("highway") == "pedestrian" and (t.get("covered") == "yes" or t.get("tunnel")):
            passages.append(Polygon(w["pts"]).buffer(0))
    passage = unary_union(passages).intersection(bl).intersection(clip) if passages else Polygon()
    holes = bl.difference(passage)
    open_ = clip.difference(holes)

    # water
    water = areas(lambda t: (t.get("natural") == "water" or t.get("water") in ("pond", "river", "lake", "moat", "reservoir", "canal")
                             or t.get("waterway") == "riverbank" or t.get("leisure") == "swimming_pool" or t.get("amenity") == "fountain")
                  and on_ground(t), open_)

    def lines(pred, width):
        out = []
        for w in DL.DATA["ways"]:
            t = w["tags"]
            if len(w["pts"]) >= 2 and pred(t) and on_ground(t) and not (t.get("tunnel") in ("yes", "culvert") and not t.get("tunnel") == "building_passage"):
                if w["closed"] and (t.get("area") == "yes" or t.get("highway") == "pedestrian"):
                    continue
                ls = LineString(w["pts"])
                if ls.intersects(open_):
                    out.append(ls.buffer(width(t) / 2, cap_style=2, join_style=1))
        return unary_union(out).intersection(open_) if out else Polygon()

    ped_areas = areas(lambda t: t.get("highway") == "pedestrian" and on_ground(t), open_)
    paths = lines(lambda t: t.get("highway") in ("footway", "steps", "corridor", "path", "cycleway"), lambda t: W_FOOT)
    paths = unary_union([paths, lines(lambda t: t.get("highway") == "pedestrian", lambda t: W_PED)])
    roads = lines(lambda t: t.get("highway") in ROADS, lambda t: W_ROAD if t.get("highway") in ("tertiary", "secondary", "primary") else W_SERVICE)
    parking = areas(lambda t: t.get("amenity") == "parking" and not is_building(t) and t.get("parking") not in ("underground", "multi-storey")
                    and on_ground(t), open_)
    grass = areas(lambda t: t.get("leisure") in ("garden", "park") or t.get("landuse") in ("grass", "meadow", "flowerbed", "farmland",
                                                                                           "village_green") or t.get("natural") == "grassland", open_)
    wood = areas(lambda t: t.get("landuse") == "forest" or t.get("natural") in ("wood", "scrub"), open_)
    rock = areas(lambda t: t.get("natural") in ("scree", "bare_rock", "sand", "rock"), open_)
    earth = areas(lambda t: t.get("landuse") == "construction", open_)

    taken = Polygon()
    zones = {}
    for name, g in (("TL_water", water), ("TL_paving", unary_union([ped_areas, paths, passage])), ("TL_road", roads),
                    ("TL_parking", parking), ("TL_rock", rock), ("TL_grass", grass), ("TL_wood", wood), ("TL_earth", earth)):
        g = g.difference(taken) if not taken.is_empty else g
        zones[name] = unary_union([p for p in G._polys(g) if p.area > 0.5])
        taken = unary_union([taken, zones[name]])
    zones["TL_ground"] = unary_union([p for p in G._polys(open_.difference(taken)) if p.area > 0.5])
    # each water body with its level (computed in build(), from the terrain)
    bodies = [p for p in G._polys(zones["TL_water"]) if p.area > 2.0]
    return dict(region=region, park=park, lots=lots, holes=holes, passage=passage, zones=zones, bodies=bodies,
                station=HP["station"], void=holes.buffer(H.BUILDING_MARGIN).union(water.buffer(1.0)))


# ---------------------------------------------------------------- mesh
def top_surface_cells(mesh, T, geom, dz_of=None):
    """As ds_tdl_ground.top_surface, but in two steps (TILE m tiles, then CELL_LAND m cells) so big geometries stay fast.
    dz_of(poly) -> a constant height to use instead of the terrain (water)."""
    tris = []
    for part in G._polys(geom):
        shapely.prepare(part)
        minx, miny, maxx, maxy = part.bounds
        for ti in range(int(math.floor(minx / TILE)), int(math.ceil(maxx / TILE))):
            for tj in range(int(math.floor(miny / TILE)), int(math.ceil(maxy / TILE))):
                tb = box(ti * TILE, tj * TILE, (ti + 1) * TILE, (tj + 1) * TILE)
                if not part.intersects(tb):
                    continue
                tile = part.intersection(tb)
                if tile.is_empty:
                    continue
                if tile.area > 0.999 * TILE * TILE:        # a full tile: cells straight away
                    pieces = [box(ti * TILE + i * CELL_LAND, tj * TILE + j * CELL_LAND, ti * TILE + (i + 1) * CELL_LAND, tj * TILE + (j + 1) * CELL_LAND)
                              for i in range(int(TILE / CELL_LAND)) for j in range(int(TILE / CELL_LAND))]
                else:
                    cells = [box(ti * TILE + i * CELL_LAND, tj * TILE + j * CELL_LAND, ti * TILE + (i + 1) * CELL_LAND, tj * TILE + (j + 1) * CELL_LAND)
                             for i in range(int(TILE / CELL_LAND)) for j in range(int(TILE / CELL_LAND))]
                    pieces = [q for q in shapely.intersection(tile, np.array(cells, dtype=object)) if not q.is_empty and q.area > 1e-4]
                for q in pieces:
                    tris += G.cdt(q)
    out = []
    for c in tris:
        z = T.z(c[:, 0], c[:, 1])
        dx, dy = T.grad(c[:, 0], c[:, 1])
        n = np.stack([-dx, -dy, np.ones(3)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
        mesh.add(np.column_stack([c[:, :2], z]), n)
        out.append(c)
    return out


class Level:
    """A flat 'terrain' at height z (water surfaces)."""
    def __init__(self, z):
        self.zc = z

    def z(self, x, y):
        return np.full(np.shape(x), self.zc, float)

    def grad(self, x, y):
        return np.zeros(np.shape(x)), np.zeros(np.shape(y))


def build():
    t0 = time.time()
    P = plan()
    print(f"  plan {time.time() - t0:.0f} s", flush=True)
    T = G.Terrain(P["region"].bounds, void=P["void"], flats=[(P["station"], H.STATION_GROUND, H.STATION_FLAT_R0, H.STATION_FLAT_R1)])
    print(f"  terrain {time.time() - t0:.0f} s", flush=True)
    meshes = {n: G.Mesh(n) for n in KINDS + ("TL_bank", "TL_edge")}
    # water: each body flat at its level, a bank from the ground down past it
    levels = []
    for b in P["bodies"]:
        ring = b.exterior
        pts = [ring.interpolate(d) for d in np.linspace(0, ring.length, max(8, int(ring.length / 3)), endpoint=False)]
        zs = sorted(float(T.z(p.x, p.y)) for p in pts)
        lv = zs[max(0, len(zs) // 10)] - WATER_DROP
        levels.append(lv)
        top_surface_cells(meshes["TL_water"], Level(lv), b)
    water_u = unary_union(P["bodies"]) if P["bodies"] else Polygon()
    shapely.prepare(water_u)
    body_tree = shapely.STRtree(P["bodies"]) if P["bodies"] else None
    all_tris = []
    for name in KINDS[1:]:
        g = P["zones"][name]
        if g.is_empty:
            continue
        all_tris += top_surface_cells(meshes[name], T, g)
        print(f"  {name} {len(meshes[name].tris)} tris, {time.time() - t0:.0f} s", flush=True)
    # skirts and banks on the outline of all the land pieces together (the pieces share their edges)
    n_bank = 0
    for a, b in G.free_edges(all_tris):
        mid = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        za, zb = float(T.z(a[0], a[1])), float(T.z(b[0], b[1]))
        if body_tree is not None and water_u.distance(mid) < 0.05:
            k = body_tree.nearest(mid)
            lv = levels[int(k)] - BANK_BELOW
            G.wall(meshes["TL_bank"], a, b, za, zb, min(lv, za - 0.05), min(lv, zb - 0.05)); n_bank += 1
        else:
            G.wall(meshes["TL_edge"], a, b, za, zb, za - G.SKIRT, zb - G.SKIRT)
    print(f"  banks {n_bank}, {time.time() - t0:.0f} s", flush=True)
    return P, T, meshes


def main():
    P, T, meshes = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, meshes)
    print(f"[land ground] {OUT.name} {OUT.stat().st_size / 1e6:.1f} MB, {n} triangles")
    print("  areas m2:", {k: round(v.area) for k, v in P["zones"].items()}, "passages %.0f, holes (buildings) %.0f" % (P["passage"].area, P["holes"].area))
    print("  triangles:", {k: len(m.tris) for k, m in meshes.items()})


if __name__ == "__main__":
    main()
