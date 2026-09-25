"""The ground of the two parks: Tokyo Disneyland and Tokyo DisneySea (plain Python: shapely, numpy, OpenCV; Blender is not
needed; no trees). Nothing is built outside the parks. The method of ds_tdl_ground.py (the entrance plaza) and ds_tdl_hotel_ground.py
(round the hotel), whose models stay as they are: this fills the rest.

  python src/ds_ground.py                  # both zones -> output/disneysea/models/{tdl_land_ground,tds_ground}.json
  python src/ds_ground.py tds_ground       # one zone
  python src/export_mock.py                # rebuilds the page; D.models picks the files up

Zones (ZONES):
  tdl_land_ground  Tokyo Disneyland: the park outline (OSM way 1282875870, with the big car park to the south-west) and the surface
                   car parks next to it (within LOT_REACH m), closed by CLOSE m. 8 m cells.
  tds_ground       Tokyo DisneySea: its park outline (ds_core.PARK). 8 m cells.
  Each zone leaves out the other zones, the entrance plaza (ds_tdl_ground.py) and the ground round the hotel (ds_tdl_hotel_ground.py).
Models already there: their plan footprint (read from the glTF in output/disneysea/models/, rasterised at FOOT_PX m) is cut out of
  the ground, so nothing is drawn twice: DisneySea's water (with its quays and piers), the plaza, the AquaSphere and the volcano; the
  a Land water model (WATER_MODEL_TDL), once it exists.
What each piece is (OSM, both extracts merged; the first that applies wins):
  (hole)   buildings (not the roofs on posts; not the booths and shelters under SMALL_BUILDING m2): nothing is built there, EXCEPT
           the passages through them: footways / service roads / pedestrian areas tagged tunnel=building_passage or covered=yes, and
           the ones with a tunnel tag that stay inside a building footprint (arcades, gate tunnels): ground, PASSAGE_W m wide
  (open)   water (natural=water / water=* / pools / fountains): no ground and no water surface; the water models are made
           separately (DisneySea's; the Land's in another tab), so the ground stops at the shore, with a skirt for their quays
  paving   highway=pedestrian areas and the footways / steps / pedestrian lines (3.5 m, 8 m)
  road     service roads 5 m, residential / unclassified 7 m, tertiary and up 10 m, trunk / motorway 14 m (ESTIMATES) -> asphalt
  parking  amenity=parking areas on the ground  -> darker asphalt
  grass    gardens, parks, pitches, golf, grass, meadows, flowerbeds, farmland, grassland
  wood     forest, wood, scrub  -> dark planted ground (trees are left out)
  rock     scree, bare rock, sand, beach
  earth    construction sites, brownfield
  rail     landuse=railway  -> ballast
  ground   everything else (yards, the gaps between the mapped pieces)
Mesh: every piece is cut into cells and triangulated (constrained Delaunay); the pieces are simplified together by SIMPLIFY m
  (shapely.coverage_simplify, so the shared edges stay shared); a 0.15 m skirt on the free edges, except round the buildings.
Heights: the GSI DEM5A on the mock's datum (ds_levels), smoothed; the DEM under buildings and water is not ground, so it is filled
  from the ground round them; flat under the entrance model (ds_tdl_ground); level with the Resort Line station's floor beside it;
  level with the DisneySea plaza model round it.
ESTIMATES: widths, colours, the zones' edges. The ground inside the rides' buildings is not modelled.
"""
import sys, json, math, base64, pathlib, time

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_core as C
import ds_disneyland as DL
import ds_tdl_ground as G
import ds_tdl_hotel_ground as H

MODELS_DIR = ROOT / "output" / "disneysea" / "models"
LOT_REACH, CLOSE = 30.0, 25.0
PASSAGE_W = 4.0
SMALL_BUILDING = 50.0
W_FOOT, W_PED = 3.5, 8.0
ROAD_W = {"service": 5.0, "living_street": 5.0, "track": 4.0, "residential": 7.0, "unclassified": 7.0, "tertiary": 10.0,
          "tertiary_link": 7.0, "secondary": 10.0, "secondary_link": 7.0, "primary": 12.0, "primary_link": 7.0, "trunk": 14.0,
          "trunk_link": 7.0, "motorway": 14.0, "motorway_link": 7.0}
FOOT_PX = 0.5
FOOT_SIMPLIFY = 0.6                       # m: the models' footprints (raster outlines) are simplified this much
SIMPLIFY = 0.3                            # m: the pieces' outlines are simplified this much (together, as a coverage)
WATER_MODEL_TDL = "tdl_water"            # a Land water model, when one is made (another tab: ds_tdl_water.py)
KINDS = ("TL_paving", "TL_road", "TL_parking", "TL_rail", "TL_grass", "TL_wood", "TL_rock", "TL_earth", "TL_ground")
ZONES = {
    "tdl_land_ground": dict(cell=8.0, tile=64.0, water_models=[WATER_MODEL_TDL], cut_models=[]),
    "tds_ground": dict(cell=8.0, tile=64.0, water_models=["water"], cut_models=["water", "plaza", "aquasphere", "volcano"]),
}


# ---------------------------------------------------------------- OSM (both extracts merged)
class Src:
    def __init__(self):
        self.ways = {}
        for w in C.DATA["ways"] + DL.DATA["ways"]:
            self.ways.setdefault(w["id"], w)
        self.rels = {}
        for r in C.DATA["relations"] + DL.DATA["relations"]:
            self.rels.setdefault(r["id"], r)
        self.origin = DL.DATA["origin"]

    def rings(self, way_ids):
        return C.closed_rings(self.ways, way_ids)

    def mp(self, r):
        outs = [Polygon(o).buffer(0) for o in self.rings([m["way"] for m in r["members"] if m.get("role") == "outer" and "way" in m])]
        ins = [Polygon(o).buffer(0) for o in self.rings([m["way"] for m in r["members"] if m.get("role") == "inner" and "way" in m])]
        if not outs:
            return Polygon()
        g = unary_union(outs)
        return g.difference(unary_union(ins)) if ins else g


S = None


def src():
    global S
    if S is None:
        S = Src()
    return S


def areas(pred, clip):
    """Union of the closed ways and multipolygons whose tags match, clipped."""
    s = src(); out = []
    bb = box(*clip.bounds)
    for w in s.ways.values():
        if w["closed"] and len(w["pts"]) >= 4 and pred(w["tags"]):
            p = Polygon(w["pts"]).buffer(0)
            if p.intersects(bb) and p.intersects(clip):
                out.append(p)
    for r in s.rels.values():
        if r["tags"].get("type", "multipolygon") == "multipolygon" and pred(r["tags"]) and len(r["members"]) < 400:
            p = s.mp(r)
            if not p.is_empty and p.intersects(bb) and p.intersects(clip):
                out.append(p)
    return unary_union(out).intersection(clip) if out else Polygon()


def on_ground(t):
    try:
        layer = int(str(t.get("layer", "0")).split(";")[0])
    except ValueError:
        layer = 0
    return layer <= 0 and t.get("bridge") in (None, "no")


def is_building(t):
    return "building" in t and t["building"] not in ("roof", "no") and t.get("parking") != "surface"


# ---------------------------------------------------------------- model footprints
def model_footprint(name):
    """Plan footprint of a model file (its triangles projected, rasterised at FOOT_PX m), or None when there is no file."""
    f = MODELS_DIR / f"{name}.json"
    if not f.exists():
        return None
    import cv2
    d = json.loads(f.read_text(encoding="utf-8"))
    buf = base64.b64decode(d["buffers"][0]["uri"].split(",", 1)[1])

    def acc(i):
        a = d["accessors"][i]; bv = d["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a["componentType"]]
        arr = np.frombuffer(buf, dtype=dt, count=a["count"] * n, offset=bv.get("byteOffset", 0) + a.get("byteOffset", 0))
        return arr.reshape(-1, n) if n > 1 else arr

    def local(n):
        if "matrix" in n:
            return np.array(n["matrix"], float).reshape(4, 4).T
        t = n.get("translation", [0, 0, 0]); q = n.get("rotation", [0, 0, 0, 1]); sc = n.get("scale", [1, 1, 1])
        x, y, z, w = q
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M = np.eye(4); M[:3, :3] = R * np.array(sc)[None, :]; M[:3, 3] = t
        return M
    tris = []

    def walk(i, M):
        n = d["nodes"][i]; M = M @ local(n)
        if "mesh" in n:
            for p in d["meshes"][n["mesh"]]["primitives"]:
                P = acc(p["attributes"]["POSITION"]).astype(float)
                P = (np.c_[P, np.ones(len(P))] @ M.T)[:, :3]
                idx = acc(p["indices"]).astype(int) if "indices" in p else np.arange(len(P))
                tris.append(P[idx].reshape(-1, 3, 3))
        for c in n.get("children", []):
            walk(c, M)
    for i in d["scenes"][d.get("scene", 0)]["nodes"]:
        walk(i, np.eye(4))
    T = np.concatenate(tris)
    xy = np.stack([T[:, :, 0], -T[:, :, 2]], -1)                   # glTF (x, up, -y) -> plan (x, y)
    x0, y0 = xy[..., 0].min() - 2, xy[..., 1].min() - 2
    x1, y1 = xy[..., 0].max() + 2, xy[..., 1].max() + 2
    W, Hh = int((x1 - x0) / FOOT_PX) + 1, int((y1 - y0) / FOOT_PX) + 1
    img = np.zeros((Hh, W), np.uint8)
    pix = np.round(np.stack([(xy[..., 0] - x0) / FOOT_PX, (y1 - xy[..., 1]) / FOOT_PX], -1)).astype(np.int32)
    for tri in pix:                                                  # one by one: fillPoly on a list uses even-odd, overlaps cancel
        cv2.fillConvexPoly(img, tri, 255)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cs, hier = cv2.findContours(img, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    if hier is not None:
        for k, c in enumerate(cs):
            if hier[0][k][3] >= 0 or len(c) < 3:
                continue
            to = lambda cc: [(x0 + px * FOOT_PX, y1 - py * FOOT_PX) for px, py in cc[:, 0]]
            holes = [to(cs[j]) for j in range(len(cs)) if hier[0][j][3] == k and len(cs[j]) >= 3]
            p = Polygon(to(c), holes).buffer(0)
            if p.area > 1.0:
                polys.append(p)
    return unary_union(polys).buffer(FOOT_PX / 2).simplify(FOOT_SIMPLIFY) if polys else Polygon()


# ---------------------------------------------------------------- zone areas
def zone_regions():
    s = src()
    tdl_park = Polygon(DL.ring_of(DL.WAYS[DL.TDL_PARK_WAY])).buffer(0)
    tds_park = Polygon(C.PARK).buffer(0)
    lots = [Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"]
            if w["tags"].get("amenity") == "parking" and w["closed"] and len(w["pts"]) >= 4 and not is_building(w["tags"])
            and w["tags"].get("parking") not in ("underground", "multi-storey") and on_ground(w["tags"])
            and Polygon(w["pts"]).buffer(0).distance(tdl_park) < LOT_REACH]
    E = G.plan(); HP = H.plan()
    done = unary_union([E["closed"], HP["road"], HP["path"], HP["plaza"], HP["station"], HP["station_path"]] + HP["planters"])
    tdl = unary_union([tdl_park] + lots).buffer(CLOSE, join_style=2).buffer(-CLOSE, join_style=2).difference(tds_park).difference(done)
    tds = tds_park.difference(done)
    return {"tdl_land_ground": tdl, "tds_ground": tds}, dict(station=HP["station"], done=done)


# ---------------------------------------------------------------- plan of one zone
def plan(zone, region):
    cfg = ZONES[zone]
    clip = region
    # models already covering part of the zone: cut them out; a water model replaces the zone's own water
    cut = [model_footprint(m) for m in cfg["cut_models"]]
    wmod = [model_footprint(m) for m in cfg["water_models"]]
    has_water_model = any(g is not None for g in wmod)
    wcut = unary_union([g for g in wmod if g is not None and not g.is_empty]) if has_water_model else Polygon()
    cut = unary_union([g for g in cut + wmod if g is not None and not g.is_empty])
    if not cut.is_empty:
        clip = clip.difference(cut)

    bl = [Polygon(w["pts"]).buffer(0) for w in src().ways.values() if w["closed"] and len(w["pts"]) >= 4 and is_building(w["tags"])]
    bl += [src().mp(r) for r in src().rels.values() if is_building(r["tags"]) and len(r["members"]) < 400]
    bl = unary_union([b for b in bl if not b.is_empty and b.area >= SMALL_BUILDING and b.intersects(clip)])
    passages = []
    for w in src().ways.values():
        t = w["tags"]
        if t.get("highway") not in ("footway", "pedestrian", "service", "steps", "corridor") or len(w["pts"]) < 2:
            continue
        ls = LineString(w["pts"])
        if not ls.intersects(bl):
            continue
        if t.get("tunnel") == "building_passage" or t.get("covered") == "yes" or (t.get("tunnel") and ls.within(bl.buffer(2.0))):
            passages.append(ls.buffer(PASSAGE_W / 2, cap_style=2, join_style=1))
        elif w["closed"] and len(w["pts"]) >= 4 and t.get("highway") == "pedestrian" and (t.get("covered") == "yes" or t.get("tunnel")):
            passages.append(Polygon(w["pts"]).buffer(0))
    passage = unary_union(passages).intersection(bl).intersection(clip) if passages else Polygon()
    holes = bl.difference(passage)
    open_ = clip.difference(holes)

    # water is left open: the water models (DisneySea's, and the Land's being made in another tab) fill it
    water = areas(lambda t: (t.get("natural") == "water" or t.get("water") in ("pond", "river", "lake", "moat", "reservoir", "canal", "basin")
                             or t.get("waterway") == "riverbank" or t.get("leisure") == "swimming_pool" or t.get("amenity") == "fountain")
                  and on_ground(t), open_)
    open_ = open_.difference(water)

    def lines(pred, width):
        out = []
        bb = box(*open_.bounds)
        for w in src().ways.values():
            t = w["tags"]
            if len(w["pts"]) < 2 or not pred(t) or not on_ground(t) or (t.get("tunnel") and t.get("tunnel") != "building_passage"):
                continue
            if w["closed"] and (t.get("area") == "yes" or t.get("highway") == "pedestrian"):
                continue
            ls = LineString(w["pts"])
            if ls.intersects(bb):
                out.append(ls.buffer(width(t) / 2, cap_style=2, join_style=1))
        return unary_union(out).intersection(open_) if out else Polygon()

    ped = areas(lambda t: t.get("highway") == "pedestrian" and on_ground(t), open_)
    paths = unary_union([lines(lambda t: t.get("highway") in ("footway", "steps", "corridor", "path", "cycleway", "platform"), lambda t: W_FOOT),
                         lines(lambda t: t.get("highway") == "pedestrian", lambda t: W_PED)])
    roads = lines(lambda t: t.get("highway") in ROAD_W, lambda t: ROAD_W[t["highway"]])
    parking = areas(lambda t: t.get("amenity") == "parking" and not is_building(t) and t.get("parking") not in ("underground", "multi-storey")
                    and on_ground(t), open_)
    rail = areas(lambda t: t.get("landuse") == "railway", open_)
    grass = areas(lambda t: t.get("leisure") in ("garden", "park", "pitch", "golf_course", "playground", "track", "sports_centre")
                  or t.get("landuse") in ("grass", "meadow", "flowerbed", "farmland", "village_green", "recreation_ground")
                  or t.get("natural") == "grassland", open_)
    wood = areas(lambda t: t.get("landuse") == "forest" or t.get("natural") in ("wood", "scrub", "heath"), open_)
    rock = areas(lambda t: t.get("natural") in ("scree", "bare_rock", "sand", "rock", "beach", "shingle"), open_)
    earth = areas(lambda t: t.get("landuse") in ("construction", "brownfield", "landfill"), open_)

    taken, zones = Polygon(), {}
    for name, g in (("TL_paving", unary_union([ped, paths, passage])), ("TL_road", roads), ("TL_parking", parking),
                    ("TL_rail", rail), ("TL_rock", rock), ("TL_grass", grass), ("TL_wood", wood), ("TL_earth", earth)):
        g = g.difference(taken) if not taken.is_empty else g
        zones[name] = unary_union([p for p in G._polys(g) if p.area > 0.5])
        taken = unary_union([taken, zones[name]])
    zones["TL_ground"] = unary_union([p for p in G._polys(open_.difference(taken)) if p.area > 0.5])
    # simplify all the pieces together, so their shared edges stay shared (no cracks between them)
    names = [k for k, v in zones.items() if not v.is_empty]
    simp = shapely.coverage_simplify(np.array([zones[k] for k in names], dtype=object), SIMPLIFY)
    for k, g in zip(names, simp):
        zones[k] = unary_union([q for q in G._polys(g.buffer(0)) if q.area > 0.5])
    return dict(region=region, open=open_, holes=holes, passage=passage, zones=zones, water=water, cut=cut,
                void=unary_union([holes.buffer(H.BUILDING_MARGIN), water.buffer(1.0), wcut.buffer(1.0)]))   # the DEM on water is not ground


# ---------------------------------------------------------------- mesh
def top_surface_cells(mesh, T, geom, cell, tile):
    """Terrain over `geom`, cut into tile m tiles then cell m cells (fast on big geometries), constrained Delaunay."""
    tris = []
    n = int(tile / cell)
    for part in G._polys(geom):
        shapely.prepare(part)
        minx, miny, maxx, maxy = part.bounds
        for ti in range(int(math.floor(minx / tile)), int(math.ceil(maxx / tile))):
            for tj in range(int(math.floor(miny / tile)), int(math.ceil(maxy / tile))):
                tb = box(ti * tile, tj * tile, (ti + 1) * tile, (tj + 1) * tile)
                if not part.intersects(tb):
                    continue
                piece = part.intersection(tb)
                if piece.is_empty:
                    continue
                cells = np.array([box(ti * tile + i * cell, tj * tile + j * cell, ti * tile + (i + 1) * cell, tj * tile + (j + 1) * cell)
                                  for i in range(n) for j in range(n)], dtype=object)
                if piece.area > 0.999 * tile * tile:
                    qs = cells
                else:
                    qs = [q for q in shapely.intersection(piece, cells) if not q.is_empty and q.area > 1e-4]
                for q in qs:
                    tris += G.cdt(q)
    for c in tris:
        z = T.z(c[:, 0], c[:, 1])
        dx, dy = T.grad(c[:, 0], c[:, 1])
        nn = np.stack([-dx, -dy, np.ones(3)], 1); nn /= np.linalg.norm(nn, axis=1, keepdims=True)
        mesh.add(np.column_stack([c[:, :2], z]), nn)
    return tris


def build(zone, region, extra):
    t0 = time.time()
    cfg = ZONES[zone]
    P = plan(zone, region)
    print(f"  [{zone}] plan {time.time() - t0:.0f} s", flush=True)
    flats = [(extra["station"], H.STATION_GROUND, H.STATION_FLAT_R0, H.STATION_FLAT_R1)]
    if zone == "tds_ground":
        pz = model_footprint("plaza")
        if pz is not None:
            flats.append((pz, json.loads((ROOT / "plateau_data" / "disneysea_plaza.json").read_text(encoding="utf-8"))["ground"] + 0.045, 0.5, 12.0))
    T = G.Terrain(P["region"].bounds, void=P["void"], flats=flats)
    print(f"  [{zone}] terrain {time.time() - t0:.0f} s", flush=True)
    meshes = {n: G.Mesh(n) for n in KINDS + ("TL_edge",)}
    all_tris = []
    for name in KINDS:
        g = P["zones"][name]
        if not g.is_empty:
            all_tris += top_surface_cells(meshes[name], T, g, cfg["cell"], cfg["tile"])
    print(f"  [{zone}] surfaces {sum(len(m.tris) for m in meshes.values())} tris, {time.time() - t0:.0f} s", flush=True)
    hole_edge = P["holes"].boundary
    shapely.prepare(hole_edge)
    for a, b in G.free_edges(all_tris):
        mid = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        za, zb = float(T.z(a[0], a[1])), float(T.z(b[0], b[1]))
        if hole_edge.distance(mid) < 0.2:
            continue                                                   # a building's edge: nothing meets the ground there
        G.wall(meshes["TL_edge"], a, b, za, zb, za - G.SKIRT, zb - G.SKIRT)   # also along the water: it meets the water models' quays
    return P, meshes


def main():
    want = [a for a in sys.argv[1:] if a in ZONES] or list(ZONES)
    t0 = time.time()
    regions, extra = zone_regions()
    print(f"[ground] zones {time.time() - t0:.0f} s: " + ", ".join(f"{k} {v.area / 1e6:.2f} km2" for k, v in regions.items()), flush=True)
    for zone in want:
        P, meshes = build(zone, regions[zone], extra)
        out = MODELS_DIR / f"{zone}.json"
        n = G.write_gltf(out, meshes)
        print(f"[ground] {out.name} {out.stat().st_size / 1e6:.1f} MB, {n} triangles; areas m2:",
              {k[3:]: round(v.area) for k, v in P["zones"].items()}, "passages %.0f, cut by models %.0f" % (P["passage"].area, P["cut"].area),
              flush=True)


if __name__ == "__main__":
    main()
