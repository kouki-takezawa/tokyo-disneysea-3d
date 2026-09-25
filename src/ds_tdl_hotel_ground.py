"""東京ディズニーランドホテル周辺の道 -- the roads and paths round the Tokyo Disneyland Hotel (plain Python: shapely + numpy,
Blender is not needed; nothing is built where the hotel stands; no trees). Same method as ds_tdl_ground.py, whose helpers it reuses.

  python src/ds_tdl_hotel_ground.py      # -> output/disneysea/models/tdl_hotel_ground.json (glTF, buffer embedded) + a summary
  python src/export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_hotel_ground", layer 舞浜駅・周辺)

What is modelled (OSM, plateau_data/disneyland_osm.json), within REACH m of the hotel (way 218553057) and on the ground:
  roads    highway=service: the hotel's drives, the round-about, the parking aisles beside the hotel  -> asphalt.
           Two-way 6.0 m, one-way 4.5 m, parking aisle 5.5 m (ESTIMATES; OSM has no widths here).
  paths    highway=footway: the promenade to the station, the paths round the hotel  -> pale stone, 3.0 m (the OSM width where given);
           the fine paths inside the gardens (the ovals with radial and ring paths) 1.8 m.
  plazas   highway=pedestrian areas and the relation for ミッキー＆フレンズ・スクエア (18377374; its inner ring, the round bed with the
           statue, is a planter: curb + green top)  -> pink brick, like the entrance plaza.
  fill     the promenade between the hotel and the station and the ground round the station (OSM draws it as lines only): the faces
           enclosed by the OSM linework (roads, footways, fences, building / garden / water outlines, the Resort Line beam) inside
           FILL_BOX, less what is already built. Faces that are gardens / lawns / flower beds become planters (curb + green top);
           within FILL_ROAD_W / 2 of a service road it is asphalt, the rest pink brick (as the photo: the road past the station is grey,
           the walkways either side are brick). Only whole faces (never cut by the box).
  station  the passages through the station (the 7 short footways with tunnel / covered / layer=-1 inside its footprint; OSM
           calls them tunnels, they are the "中道" under and between the station's wings)  -> pale stone, 4 m, and a stone floor
           under the whole footprint, at the Blender station's ground (-1.79 m) so there is never a blank under it. The DEM beside the
           station is up to 1.5 m lower (-3.3 m on the hotel side), which left an open step at its walls: the ground is level with
           the floor within STATION_FLAT_R0 m of the station and blends back into the DEM by STATION_FLAT_R1 m.
Left out: the hotel and every other building's footprint (roofs on posts stay), water, tunnels / underpasses (except the station's),
  bridges (the Gateway walkway), covered ways (except the station's), stairs (the terrain carries them), the public road 浦安市道幹線7号 (tertiary), the parking aisles of
  the big car parks farther out, and the entrance plaza (ds_tdl_ground.py builds it: its area is cut out here).
Heights: the same terrain as the entrance plaza (GSI DEM5A on the mock's datum, smoothed), so the two meet. Under the buildings
  the DEM is not ground (the hotel's footprint is a flat -0.8 m fill), so those nodes are filled from the ground round them.
  NOTE: the DEM puts the hotel's north approach (the loop road, the porte-cochere, the woods inside the loop) on a flat platform
  about +5.8 m high, with the ramps to the -1 m ground on the north and west sides (the hotel is layer=1 in OSM, with an
  underpass below it). The ground follows it. Not checked against anything but the DEM.
Mesh: as ds_tdl_ground.py (cells, constrained Delaunay, a 0.15 m skirt on the free edges).
ESTIMATES: widths, colours (aerial photo, washed out), which ways count as "round the hotel" (REACH). The photo predates the
  2023 changes at the entrance; the hotel side has not been checked against a recent photo.
"""
import sys, math, pathlib

import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.geometry import box
from shapely.ops import unary_union, polygonize

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G

OUT = ROOT / "output" / "disneysea" / "models" / "tdl_hotel_ground.json"
HOTEL_WAY = 218553057
SQUARE_REL = 18377374                          # ミッキー＆フレンズ・スクエア
ENTRANCE_RELS = (17641752, 17641753)           # the entrance plaza (ds_tdl_ground.py)
REACH = 60.0                                   # a way counts when at least half of it is within REACH m of the hotel
CLIP = 85.0                                    # ... and is cut at this distance
W_SERVICE, W_ONEWAY, W_AISLE, W_FOOT, W_GARDEN = 6.0, 4.5, 5.5, 3.0, 1.8
BUILDING_MARGIN = 4.0                          # the terrain under the buildings (+ this margin) is filled from the ground round them
FILL_BOX = (-650.0, 990.0, -500.0, 1080.0)     # the promenade between the hotel and the station (local m: x0, y0, x1, y1)
STATION_REL = 17744015                         # 東京ディズニーランド・ステーション
STATION_GROUND = -1.79                         # the Blender station's floor (ds_tdl_station.FRAME["ground_datum"])
W_STATION_PATH = 4.0
STATION_FLAT_R0, STATION_FLAT_R1 = 4.0, 22.0    # the ground meets the station's floor: level within 4 m of it, back to the DEM by 22 m
FILL_ROAD_W = 12.0                             # the carriageway in the fill: this wide along the service road (the photo: two lanes + bays)
NAMES = ("TH_road", "TH_path", "TH_plaza", "TH_curb", "TH_soil", "TH_edge", "TH_floor")


def _width(t, in_garden=False):
    try:
        return float(str(t["width"]).replace("m", "").strip())
    except (KeyError, ValueError):
        pass
    if t["highway"] == "service":
        return W_AISLE if t.get("service") == "parking_aisle" else W_ONEWAY if t.get("oneway") == "yes" else W_SERVICE
    return W_GARDEN if in_garden else W_FOOT


def _on_ground(t):
    return (t.get("tunnel") in (None, "no") and t.get("bridge") in (None, "no") and t.get("covered") in (None, "no")
            and t.get("layer", "0") == "0")


def plan():
    hotel = Polygon(DL.WAYS[HOTEL_WAY]["pts"]).buffer(0)
    near, clip = hotel.buffer(REACH), hotel.buffer(CLIP)
    rels = {r["id"]: r for r in DL.DATA["relations"]}
    square = unary_union([Polygon(o).buffer(0) for o in DL.outer_rings(rels[SQUARE_REL])])
    sq_holes = [Polygon(DL.WAYS[m["way"]]["pts"]).buffer(0) for m in rels[SQUARE_REL]["members"]
                if m["role"] == "inner" and m["way"] in DL.WAYS]

    # what is not open ground: buildings (not the roofs on posts), water, the entrance plaza, the station
    solid = [Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"]
             if w["closed"] and len(w["pts"]) >= 4 and "building" in w["tags"] and w["tags"]["building"] != "roof"]
    solid += [Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"]
              if w["closed"] and len(w["pts"]) >= 4 and (w["tags"].get("natural") == "water" or w["tags"].get("water"))]
    solid += [Polygon(o).buffer(0) for r in DL.DATA["relations"] if r["tags"].get("building") == "train_station" for o in DL.outer_rings(r)]
    solid = unary_union([g for g in solid if g.intersects(clip)])
    entrance = G.plan()["closed"]
    blocked = unary_union([solid, entrance])

    garden = unary_union([Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"]
                          if w["closed"] and len(w["pts"]) >= 4 and (w["tags"].get("leisure") in ("garden", "park")
                                                                     or w["tags"].get("landuse") in ("grass", "meadow", "flowerbed"))
                          and Polygon(w["pts"]).intersects(clip)])
    roads, paths, pedestrians = [], [], []
    for w in DL.DATA["ways"]:
        t = w["tags"]; hw = t.get("highway")
        if hw not in ("service", "footway", "pedestrian") or not _on_ground(t):
            continue
        if w["closed"] and (hw == "pedestrian" or t.get("area") == "yes") and len(w["pts"]) >= 4:
            p = Polygon(w["pts"]).buffer(0)
            if p.intersects(near) and p.area > 3:
                pedestrians.append(p)
            continue
        ls = LineString(w["pts"])
        if ls.length < 3 or ls.intersection(near).length < 0.5 * ls.length and not (ls.length < 60 and ls.intersects(near)):
            continue
        fine = hw == "footway" and ls.intersection(garden).length > 0.8 * ls.length      # a garden's own path
        (roads if hw == "service" else paths).append(ls.intersection(clip).buffer(_width(t, fine) / 2, cap_style=2, join_style=1))
    # the pedestrian-area relations near the hotel (the entrance plaza's are built by ds_tdl_ground.py)
    for r in DL.DATA["relations"]:
        if r["tags"].get("highway") == "pedestrian" and r["id"] not in ENTRANCE_RELS and r["id"] != SQUARE_REL:
            for o in DL.outer_rings(r):
                p = Polygon(o).buffer(0)
                if p.intersects(near):
                    pedestrians.append(p)
    pedestrians.append(square)

    z_road = unary_union(roads).difference(blocked)
    z_plaza = unary_union(pedestrians).difference(blocked).difference(z_road)
    z_path = unary_union(paths).difference(blocked).difference(z_road).difference(z_plaza)
    planters = [h for h in sq_holes if h.area > G.MIN_PLANTER and h.intersects(z_plaza)]
    pl_all = unary_union(planters) if planters else Polygon()
    z_plaza = z_plaza.difference(pl_all)
    z_path = z_path.difference(pl_all)
    z_road = z_road.difference(pl_all)
    # the station: its passages and a floor under the footprint (the Blender model stands on it)
    station = unary_union([Polygon(o).buffer(0) for o in DL.outer_rings(rels[STATION_REL])])
    st_paths = unary_union([LineString(w["pts"]).buffer(W_STATION_PATH / 2, cap_style=2, join_style=1) for w in DL.DATA["ways"]
                            if w["tags"].get("highway") == "footway" and not _on_ground(w["tags"]) and w["tags"].get("bridge") in (None, "no")
                            and LineString(w["pts"]).within(station.buffer(1.0))])
    z_station = st_paths.intersection(station.buffer(3.0))
    # the fill: faces of the OSM linework between the hotel and the station
    fb = box(*FILL_BOX)
    lines = []
    for w in DL.DATA["ways"]:
        t = w["tags"]
        if len(w["pts"]) < 2 or not LineString(w["pts"]).intersects(fb):
            continue
        if (t.get("highway") in ("footway", "service", "pedestrian", "steps") or "building" in t or "barrier" in t
                or t.get("railway") == "monorail" or t.get("leisure") in ("garden", "park")
                or t.get("landuse") in ("grass", "forest", "flowerbed", "meadow") or t.get("natural") in ("water", "wood", "scrub", "grassland")):
            lines.append(LineString(w["pts"]))
    lines.append(fb.exterior)
    faces = [f for f in polygonize(unary_union(lines)) if fb.contains(f.representative_point()) and f.area > 1.0]
    greens = unary_union([Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"] if w["closed"] and len(w["pts"]) >= 4 and (
        w["tags"].get("leisure") in ("garden", "park") or w["tags"].get("landuse") in ("grass", "forest", "flowerbed", "meadow")
        or w["tags"].get("natural") in ("wood", "scrub", "grassland")) and Polygon(w["pts"]).intersects(fb)])
    lanes = unary_union([LineString(w["pts"]) for w in DL.DATA["ways"] if w["tags"].get("highway") == "service" and _on_ground(w["tags"])
                         and LineString(w["pts"]).intersects(fb)]).buffer(FILL_ROAD_W / 2, cap_style=2)
    built = unary_union([blocked, z_road, z_plaza, z_path, pl_all, station])
    fill_road, fill_plaza, fill_green = [], [], []
    for f in faces:
        rest = f.difference(built)
        if rest.area < 1.0:
            continue
        if f.intersection(greens).area > 0.5 * f.area:
            fill_green += [p for p in G._polys(rest) if p.area > G.MIN_PLANTER]
        else:                                                      # the carriageway along a service road, brick beside it
            fill_road.append(rest.intersection(lanes))
            fill_plaza.append(rest.difference(lanes))
    z_road = unary_union([z_road] + fill_road)
    z_plaza = unary_union([z_plaza] + fill_plaza)
    planters = planters + fill_green
    keep = lambda g: unary_union([p for p in G._polys(g) if p.area > 0.6])         # drop slivers
    return dict(road=keep(z_road), path=keep(z_path), plaza=keep(z_plaza), planters=planters, hotel=hotel, void=solid.buffer(BUILDING_MARGIN),
                station=station, station_path=keep(z_station))


def build():
    P = plan()
    zones = [("TH_road", P["road"]), ("TH_path", P["path"]), ("TH_plaza", P["plaza"])]
    T = G.Terrain(unary_union([g for _, g in zones] + P["planters"] + [P["station"]]).bounds, void=P["void"],
                  flats=[(P["station"], STATION_GROUND, STATION_FLAT_R0, STATION_FLAT_R1)])
    meshes = {n: G.Mesh(n) for n in NAMES}
    pl_lines = unary_union([q.exterior for q in P["planters"]]) if P["planters"] else None
    for name, g in zones:
        if not g.is_empty:
            G.add_zone(meshes, T, name, g, edge="TH_edge", avoid=pl_lines)
    for q in P["planters"]:
        G.add_planter(meshes, T, q, curb="TH_curb", soil="TH_soil")
    # the station: a flat floor at the Blender station's ground under the footprint, the passages 2 cm above it
    flat = G.Terrain.__new__(G.Terrain)
    flat.z = lambda x, y, dz=0.0: np.full(np.shape(x), STATION_GROUND + dz, float)
    flat.grad = lambda x, y: (np.zeros(np.shape(x)), np.zeros(np.shape(y)))
    G.add_zone(meshes, flat, "TH_floor", P["station"], edge="TH_edge")
    lifted = G.Terrain.__new__(G.Terrain)
    lifted.z = lambda x, y: np.full(np.shape(x), STATION_GROUND + 0.02, float)
    lifted.grad = flat.grad
    for poly in G._polys(P["station_path"]):
        G.top_surface(meshes["TH_path"], lifted, poly)
    return P, T, meshes


def main():
    P, T, meshes = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, meshes)
    zs = np.concatenate([np.array(m.tris)[:, :, 2].ravel() for m in meshes.values() if m.tris])
    print(f"[hotel ground] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles, z {zs.min():.2f} .. {zs.max():.2f} m")
    print("  areas m2: roads %.0f, paths %.0f, plazas %.0f, %d planters" % (P["road"].area, P["path"].area, P["plaza"].area, len(P["planters"])))
    print("  triangles:", {k: len(m.tris) for k, m in meshes.items()})


if __name__ == "__main__":
    main()
