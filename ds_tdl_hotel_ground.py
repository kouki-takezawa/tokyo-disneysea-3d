"""東京ディズニーランドホテル周辺の道 -- the roads and paths round the Tokyo Disneyland Hotel (plain Python: shapely + numpy,
Blender is not needed; nothing is built where the hotel stands; no trees). Same method as ds_tdl_ground.py, whose helpers it reuses.

  python ds_tdl_hotel_ground.py      # -> output/disneysea/models/tdl_hotel_ground.json (glTF, buffer embedded) + a summary
  python export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_hotel_ground", layer 舞浜駅・周辺)

What is modelled (OSM, plateau_data/disneyland_osm.json), within REACH m of the hotel (way 218553057) and on the ground:
  roads    highway=service: the hotel's drives, the round-about, the parking aisles beside the hotel  -> asphalt.
           Two-way 6.0 m, one-way 4.5 m, parking aisle 5.5 m (ESTIMATES; OSM has no widths here).
  paths    highway=footway: the promenade to the station, the paths round the hotel  -> pale stone, 3.0 m (the OSM width where given);
           the fine paths inside the gardens (the ovals with radial and ring paths) 1.8 m.
  plazas   highway=pedestrian areas and the relation for ミッキー＆フレンズ・スクエア (18377374; its inner ring, the round bed with the
           statue, is a planter: curb + green top)  -> pink brick, like the entrance plaza.
Left out: the hotel and every other building's footprint (roofs on posts stay), water, tunnels / underpasses, bridges (the
  Gateway walkway), covered ways, stairs (the terrain carries them), the public road 浦安市道幹線7号 (tertiary), the parking aisles of
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
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
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
NAMES = ("TH_road", "TH_path", "TH_plaza", "TH_curb", "TH_soil", "TH_edge")


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
    keep = lambda g: unary_union([p for p in G._polys(g) if p.area > 0.6])         # drop slivers
    return dict(road=keep(z_road), path=keep(z_path), plaza=keep(z_plaza), planters=planters, hotel=hotel, void=solid.buffer(BUILDING_MARGIN))


def build():
    P = plan()
    zones = [("TH_road", P["road"]), ("TH_path", P["path"]), ("TH_plaza", P["plaza"])]
    T = G.Terrain(unary_union([g for _, g in zones] + P["planters"]).bounds, void=P["void"])
    meshes = {n: G.Mesh(n) for n in NAMES}
    pl_lines = unary_union([q.exterior for q in P["planters"]]) if P["planters"] else None
    for name, g in zones:
        if not g.is_empty:
            G.add_zone(meshes, T, name, g, edge="TH_edge", avoid=pl_lines)
    for q in P["planters"]:
        G.add_planter(meshes, T, q, curb="TH_curb", soil="TH_soil")
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
