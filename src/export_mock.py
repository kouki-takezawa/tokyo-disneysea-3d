"""Export the DisneySea draft geometry as compact JSON for the outline (枠線) mock page.

  python src/export_mock.py             (plain Python; Blender is not needed)
  python src/export_mock.py --relevel   also recompute stairs / path levels from the raw OSM extracts
                                    (plateau_data/*_osm_raw.json, not in git; they are refetched copies,
                                     so relevelling may change the levels and volcano data)

Reuses ds_core / ds_terrain logic (park clipping, water holes, heights, port
classification) so the mock and the Blender draft always show the same thing.
Writes output/disneysea/mock_data.json (coords rounded to 0.1 m).
"""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import ds_core as C
import ds_terrain as T
import ds_levels as LV
import ds_volcano as VO
import ds_aquasphere as AQ
import ds_disneyland as DLM
import math

PORTS = list(C.PORT_COLOR)
PORT_JA = {
    "mediterranean_harbor": "メディテレーニアンハーバー",
    "american_waterfront": "アメリカンウォーターフロント",
    "mysterious_island": "ミステリアスアイランド",
    "port_discovery": "ポートディスカバリー",
    "mermaid_lagoon": "マーメイドラグーン",
    "arabian_coast": "アラビアンコースト",
    "lost_river_delta": "ロストリバーデルタ",
    "fantasy_springs": "ファンタジースプリングス",
}


def R(ring):
    return [[round(x, 1), round(y, 1)] for x, y in C._clean_ring(ring)]


def L(line):
    return [[round(x, 1), round(y, 1)] for x, y in line]


# Directions the user confirmed by eye (way id -> "start" | "end": which end is the top). Checked before the DEM
# guess; the stair gets basis "user". Filled in from tools/stair_check.py pictures / the user's own knowledge.
STAIR_UP_OVERRIDE = {}


def resolve_stairs(paths):
    """Stairs whose direction ds_levels could not tell ("unknown": the DEM just past both ends differs by < 0.1 m).
    Look farther: the DEM 6, 10 and 15 m beyond each end. If the difference has the same sign at all three and
    reaches 0.25 m, or one end joins a tunnel (that end is down), take that direction (basis "wide"). The stair's
    heights are flipped when the top turns out to be at the start. Works on the committed data (no raw OSM)."""
    def beyond(l, at_end, d):
        (x0, y0), (x1, y1) = (l[-2], l[-1]) if at_end else (l[1], l[0])
        L = math.dist((x0, y0), (x1, y1)) or 1.0
        return x1 + (x1 - x0) / L * d, y1 + (y1 - y0) / L * d
    ends = [(tuple(q["l"][0]), q) for q in paths] + [(tuple(q["l"][-1]), q) for q in paths]
    def joins_tunnel(pt, me):
        return any(q is not me and q.get("u") and math.dist(pt, e) < 0.5 for e, q in ends)
    for p in paths:
        s = p.get("s")
        if not s or s["basis"] != "unknown":
            continue
        l = p["l"]
        ov = STAIR_UP_OVERRIDE.get(s.get("id"))
        if ov:
            s["basis"] = "user"
            if ov != s["up"] and p.get("z"):
                p["z"] = p["z"][::-1]
            s["up"] = ov
            continue
        diffs = [LV.dem(*beyond(l, True, d)) - LV.dem(*beyond(l, False, d)) for d in (6, 10, 15)]
        if joins_tunnel(l[-1], p) != joins_tunnel(l[0], p):
            up = "start" if joins_tunnel(l[-1], p) else "end"
        elif (all(v > 0 for v in diffs) or all(v < 0 for v in diffs)) and max(abs(v) for v in diffs) >= 0.25:
            up = "end" if diffs[0] > 0 else "start"
        else:
            continue
        s["basis"] = "wide"
        if up != s["up"] and p.get("z"):
            p["z"] = p["z"][::-1]
        s["up"] = up


def main():
    T.plan_water()   # water tab's bodies (cut / surface / tunnels) when available
    out = {"origin": C.DATA["origin"], "park": R(C.PARK),
           "ports": [{"id": p, "ja": PORT_JA[p]} for p in PORTS],
           "water": [], "ponds": [], "islands": [], "buildings": [], "green": [],
           "trees": [], "rock": [], "paths": [], "rail": [], "landmarks": [], "labels": []}

    lev = LV.levels()   # committed plateau_data/disneysea_levels.json unless --relevel
    out["levels"] = {"datum": lev["datum_m"], "pixel": lev["pixel_m"], "counts": lev["counts"]}

    def water_level(ring):
        zs = sorted(LV.dem(x, y) for x, y in ring[:: max(1, len(ring) // 40)])
        return round(zs[max(0, len(zs) // 10)] - 0.6, 2)
    out["water_z"] = []
    LVL = T.STATE["levels"]
    for ring, inners, tag in T.STATE["holes"]:
        out["water"].append(R(ring))
        out["water_z"].append(LVL[tag]["level"] if tag in LVL else water_level(ring))
    out["islands"] = [R(i) for i in T.STATE["islands"]]
    out["ponds"] = [R(r) for r, _ in T.STATE["surface_water"]]
    out["ponds_z"] = [LVL[t]["level"] if t in LVL else water_level(r) + 0.5 for r, t in T.STATE["surface_water"]]
    out["water_tunnels"] = [R(r) for r in T.STATE["tunnels"]]
    out["water_source"] = T.STATE["source"]
    hz = [LVL[t]["level"] for _, _, t in T.STATE["holes"] if t == "R3531413" and t in LVL]
    out["water_tunnels_z"] = hz[0] if hz else -1.0

    # buildings (same selection as ds_buildings)
    items = [(w, [w["pts"]]) for w in C.ways_with("building")]
    for r, outers, inners in C.multipolygons("building"):
        for j, o in enumerate(outers):
            items.append(({"id": r["id"] * 10 + j, "tags": r["tags"], "pts": o},
                          [o] + [i for i in inners if C.ring_inside(i, o)]))
    port_pts = {p: [] for p in PORTS}
    for w, loops in items:
        if not C.in_park(w["pts"]):
            continue
        name = w["tags"].get("name", "") or w["tags"].get("name:en", "")
        if (name and any(k in name for k in C.LANDMARK_SKIP)) or w["id"] in C.LANDMARK_SKIP_IDS:
            continue
        cx, cy = C.poly_centroid(w["pts"])
        port = C.nearest_port(cx, cy, w["pts"])
        port_pts[port].append((cx, cy, C.poly_area(w["pts"])))
        pri = bool(name) and any(k in name for k in C.DETAIL_PRIORITY)
        b = {"r": [R(l) for l in loops], "h": round(C.height_for_way(w), 1), "p": PORTS.index(port),
             "z": round(LV.dem(cx, cy), 2)}
        if pri:
            b["x"] = 1
        if C.is_roof(w["tags"]):
            b["rf"] = 1   # roof only (canopy / shelter): a slab on posts, open underneath
        if name:
            b["n"] = name
        out["buildings"].append(b)

    for (k, v), spec in T.GREEN.items():
        key = "trees" if v in ("forest", "wood") else "green"
        for w in C.ways_with(k, v):
            if C.in_park(w["pts"]):
                out[key].append(R(w["pts"]))
        for r, outers, _ in C.multipolygons(k, v):
            out[key] += [R(o) for o in outers if C.in_park(o)]

    for key in ("scree", "bare_rock"):
        rings = [w["pts"] for w in C.ways_with("natural", key)]
        rings += [o for _, outers, _ in C.multipolygons("natural", key) for o in outers]
        for ring in rings:
            if C.in_park(ring):
                a = C.poly_area(ring)
                cx, cy = C.poly_centroid(ring)
                out["rock"].append({"r": R(ring), "h": round(min(14.0, 1.5 + a ** 0.5 * 0.35), 1), "z": round(LV.dem(cx, cy), 2)})

    widths = {"pedestrian": 8.0, "footway": 3.5, "steps": 3.5, "service": 5.0, "corridor": 3.0}
    for hw, wd in widths.items():
        for w in C.ways_with("highway", hw, closed_only=False):
            if not C.in_park(w["pts"]):
                continue
            p = {"l": L(w["pts"]), "w": wd}
            lw = lev["ways"].get(str(w["id"]))
            if lw and len(lw["z"]) == len(w["pts"]):
                p["z"] = lw["z"]
                if lw["kind"] == "bridge":
                    p["b"] = 1
                elif lw["kind"] == "tunnel":
                    p["u"] = 1
            elif w["tags"].get("bridge") in ("yes", "viaduct"):
                p["b"] = 1
            if w["closed"] and (hw == "pedestrian" or w["tags"].get("area") == "yes"):
                p["a"] = 1
            st = lev["stairs"].get(str(w["id"]))
            if st:
                p["s"] = {k: st[k] for k in ("rise", "steps", "up", "basis", "len")}
                p["s"]["id"] = w["id"]
                if w["tags"].get("width"):
                    try: p["w"] = float(w["tags"]["width"])
                    except ValueError: pass
                if w["tags"].get("name"):
                    p["s"]["n"] = w["tags"]["name"]
            out["paths"].append(p)

    for w in C.ways_with("railway", "narrow_gauge", closed_only=False):
        if "エレクトリックレールウェイ" in w["tags"].get("name", "") and C.in_park(w["pts"]):
            out["rail"].append(L(w["pts"]))

    resolve_stairs(out["paths"])
    # named points (attractions, shops, restaurants, services) for the search box
    out["pois"] = [{"n": p["tags"]["name"], "x": round(p["xy"][0], 1), "y": round(p["xy"][1], 1),
                    "p": PORTS.index(C.nearest_port(p["xy"][0], p["xy"][1], [p["xy"]])),
                    "k": next((p["tags"][k] for k in ("attraction", "tourism", "amenity", "shop", "leisure") if k in p["tags"]), "")}
                   for p in C.DATA["pois"] if p["tags"].get("name") and C.point_in_poly(*p["xy"], C.PARK)]
    out["walls"] = [{"t": wl["type"], "h": wl["h"], "l": wl["pts"], "z": wl["z"]} for wl in lev["walls"]]
    out["contours"] = {str(k): v for k, v in LV.contours(C.PARK, interval=1.0).items()}
    xs = [p[0] for p in C.PARK]; ys = [p[1] for p in C.PARK]
    g0x, g0y, step = math.floor(min(xs)), math.floor(min(ys)), 8
    nx, ny = int((max(xs) - g0x) / step) + 2, int((max(ys) - g0y) / step) + 2
    out["hgrid"] = {"x0": g0x, "y0": g0y, "step": step, "nx": nx, "ny": ny,
                    "v": [round(LV.dem(g0x + i * step, g0y + j * step), 1) for j in range(ny) for i in range(nx)]}

    out["entrance"] = C.entrance_layer()      # Resort Line station + ticket gates (入場口・駅 layer)
    out.update(DLM.build(out["levels"]["datum"]))   # ディズニーランド / 舞浜駅・周辺 layers (separate OSM extract)
    resolve_stairs(out["disneyland"]["paths"])
    import ds_tracks   # the Resort Line beam: [x, y, beam top z, curvature] every 5 m round the loop (ds_tracks.beam_profile)
    beam = out["maihama"]["beam"] = ds_tracks.beam_profile(out)[0]
    blen = sum(math.hypot(beam[i][0] - beam[i - 1][0], beam[i][1] - beam[i - 1][1]) for i in range(len(beam)))
    out["maihama"]["stops"] = [{"n": n, "s": round(s, 1)} for n, s in ds_tracks.station_arcs(out["maihama"], beam, blen)]   # m along beam
    out["aquasphere"] = AQ.mock_geometry()     # same layout as the Blender build (ds_aquasphere.SPEC)
    vres = VO.build()
    out["volcano"] = {"contours": VO.contours(vres, 2.0), "summit": vres["summit"]}

    # landmarks: same parameters as ds_landmarks.py
    out["landmarks"] = [
        {"t": "massif", "n": "プロメテウス火山", "x": -50, "y": -111, "z": 51},   # rock ring = out["volcano"] contours
        # AquaSphere: globe 8 m on a 2 m pedestal (user spec), pool r 11.16 (OSM 72388087), rim 0.40 m; ground -0.39 (water tab)
        {"t": "sphere", "n": "アクアスフィア(直径8 m・台座2 m)", "x": 360.85, "y": 36.37, "r": 4.0, "z": -0.39 + 2.0 + 4.0,
         "basin": 11.16, "rim_h": 0.40, "g": -0.39, "ped": 2.0},
        {"t": "dome", "n": "マーメイドラグーン(屋内ホールの八角屋根)", "x": C.TRITON_ROOF["x"], "y": C.TRITON_ROOF["y"],
         "r": C.TRITON_ROOF["r"], "h": C.TRITON_ROOF["peak"] - C.TRITON_ROOF["eaves"], "z": C.TRITON_ROOF["eaves"]},
    ]
    ship = next((w for w in C.DATA["ways"]
                 if any(k in w["tags"].get("name", "") + w["tags"].get("name:en", "") for k in C.LANDMARK_SKIP)), None)
    if ship:
        out["landmarks"].append({"t": "ship", "n": "S.S.コロンビア号", "r": R(ship["pts"])})

    for p in PORTS:  # area label at the area-weighted building centroid
        pts = port_pts[p]
        if pts:
            A = sum(a for _, _, a in pts) or 1
            out["labels"].append({"n": PORT_JA[p], "p": PORTS.index(p), "x": round(sum(x * a for x, _, a in pts) / A),
                                  "y": round(sum(y * a for _, y, a in pts) / A), "k": "port"})

    # water tab (ds_water.py): shore types, depth, piers, per-body info -> drawn by the ext-water hook
    wj = ROOT / "plateau_data" / "disneysea_water.json"
    if wj.exists():
        W = json.loads(wj.read_text(encoding="utf-8"))
        out["water3"] = {
            "bodies": [{"id": b["id"], "n": b["name"], "k": b["kind"], "p": PORTS.index(b["port"]), "z": b["level"],
                        "d": b["depth"], "f": b["freeboard"], "g": b["basis"], "a": b["area"], "cut": b["cut"],
                        "r": R(b["ring"]), "i": [R(h) for h in b["inners"]]} for b in W["bodies"]],
            "shores": [{"t": s["t"], "b": s["b"], "l": L(s["l"])} for s in W["shores"]],
            "piers": [R(p["ring"]) for p in W["piers"]],
            "len": W["shore_length"]}

    # Blender-built parts (export_models.py): shown as solid models in 3D, replacing their draft wireframe
    MODELS = [("water", "water", ["water"]), ("aquasphere", "landmarks", ["aqwire", "aqglobe", "aqcoast"]),
              ("plaza", "paths", []), ("volcano", "landmarks", ["volc"]),   # plaza ground: shown with the 園路 layer; the path lines elsewhere stay
              ("tdl_station", "maihama", ["mhstation"]),                    # ds_tdl_station.py: replaces the station building's box
              ("tdl_entrance", "disneyland", []),                           # ds_tdl_entrance.py: gates, World Bazaar front, plaza
              ("tdl_world_bazaar", "disneyland", ["dlwbroof"]),
              ("tdl_hotel", "maihama", ["mhtdlhotel"]),
              ("tdl_plaza_buildings", "disneyland", ["dlplazab"]),         # ds_tdl_plaza_buildings.py: the buildings round the plaza, Monsters, Inc.                     # ds_tdl_hotel.py: 東京ディズニーランドホテル (replaces its box)             # ds_tdl_world_bazaar.py: Main / Center Street under the glass roof
              ("tdl_ground", "disneyland", []),                             # ds_tdl_ground.py: the entrance plaza's paving, curbs and planters (plain Python)
              ("tdl_hotel_ground", "maihama", []),                          # ds_tdl_hotel_ground.py: the roads and paths round the Tokyo Disneyland Hotel (plain Python)
              ("tdl_gateway", "maihama", []),                               # ds_tdl_gateway.py: 舞浜駅南口〜ボン・ヴォヤージュ〜ランド・ステーションの地面・歩道橋・ボン・ヴォヤージュ(plain Python)
              ("tdl_land_ground", "disneyland", []),                        # ds_ground.py: the ground of the whole Land and its car parks (plain Python)
              ("tds_ground", "paths", []),                                  # ds_ground.py: the ground of DisneySea (round the water, plaza and volcano models)
              ("tracks", "maihama", ["mhline", "mhjr"]),
              ("bb_castle", "disneyland", []),
              ("cinderella", "disneyland", []),
              ("tdl_water", "disneyland", ["dlwater"])]                     # ds_tdl_water.py + tdl_water_blender.py: ランドの水面 (replaces the Land's water outlines)                              # ds_tdl_cinderella.py: シンデレラ城                               # ds_tdl_bb_castle.py: 美女と野獣の城                      # ds_tracks.py: Resort Line beam + Keiyo Line viaduct
    mdir = ROOT / "output" / "disneysea" / "models"
    import compress_models                                  # Draco copies for the page (models/web/); the plain files stay for the scripts
    web = compress_models.run([i for i, _, _ in MODELS])
    out["models"] = [{"id": i, "layer": lay, "src": web.get(i, f"models/{i}.json"), "hides": hides}   # glTF JSON (the host serves .json, not .glb)
                     for i, lay, hides in MODELS if (mdir / f"{i}.json").exists() or i in web]
    for m in out["models"]:   # where it is (the page loads the nearest first) and its far copy (shown until the camera comes near)
        f = ROOT / "output" / "disneysea" / m["src"]
        if f.exists():
            m["box"] = compress_models.bounds(f)
        far = compress_models.WEB / f"{m['id']}_far.json"
        if m["id"] in compress_models.LOD and far.exists():
            m["far"] = f"models/web/{far.name}"
    if (mdir / "train.json").exists():   # the Resort Line cars (export_models.py --parts train), posed by the page's timetable
        out["train"] = "models/train.json"
    if (mdir / "woody.json").exists():   # the walker (woody.py --web-glb, glb_to_json): replaces the box figure in 散歩
        out["woody"] = "models/woody.json"

    # trees for the 3D view (the page instances one low-poly tree per point): OSM natural=tree nodes of both extracts
    trees, seen = [], set()
    for fn in ("disneyland_osm.json", "disneysea_osm.json"):
        f = ROOT / "plateau_data" / fn
        if not f.exists():
            continue
        for p in json.loads(f.read_text(encoding="utf-8")).get("pois", []):
            if p["tags"].get("natural") != "tree":
                continue
            x, y = round(p["xy"][0], 1), round(p["xy"][1], 1)
            if (x, y) in seen:
                continue
            seen.add((x, y))
            h = p["tags"].get("height")
            try:
                h = round(float(str(h).replace("m", "")), 1) if h else 0
            except ValueError:
                h = 0
            trees += [x, y, h]
    # the planting beds of the entrance plaza and round the hotel (the ground models' planters, from OSM; the park map
    # shows a tree or clipped shrubs in each): a tree in each bed (a row along the long ones), clipped shrubs at the ends
    shrubs = []
    try:
        import ds_tdl_ground, ds_tdl_hotel_ground, ds_tdl_gateway
        from shapely.geometry import LineString, Point
        beds = list(ds_tdl_ground.plan()["planters"]) + list(ds_tdl_hotel_ground.plan()["planters"]) + list(ds_tdl_gateway.plan()["planters"])
        for q in beds:
            if q.is_empty or q.area < 3.0:
                continue
            mr = q.minimum_rotated_rectangle
            c = list(mr.exterior.coords)[:4]
            e1 = math.hypot(c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = math.hypot(c[2][0] - c[1][0], c[2][1] - c[1][1])
            (a, b) = ((c[0], c[1]), (c[3], c[2])) if e1 >= e2 else ((c[1], c[2]), (c[0], c[3]))
            m0 = ((a[0][0] + b[0][0]) / 2, (a[0][1] + b[0][1]) / 2); m1 = ((a[1][0] + b[1][0]) / 2, (a[1][1] + b[1][1]) / 2)
            bl, bw = max(e1, e2), min(e1, e2)
            n = max(1, int(bl / 7.0))
            for k in range(n):
                t = (k + 0.5) / n
                x, y = m0[0] + (m1[0] - m0[0]) * t, m0[1] + (m1[1] - m0[1]) * t
                if q.contains(Point(x, y)):
                    trees += [round(x, 1), round(y, 1), round(min(9.0, 4.0 + bw * 0.9), 1)]
            if bl > 5.0:                                      # clipped round shrubs at both ends
                for t in (0.12, 0.88):
                    x, y = m0[0] + (m1[0] - m0[0]) * t, m0[1] + (m1[1] - m0[1]) * t
                    if q.contains(Point(x, y)):
                        shrubs += [round(x, 1), round(y, 1), round(min(1.1, bw * 0.25), 2)]
    except Exception as e:                                    # the ground scripts need shapely: without it, only OSM's trees
        print("[mock] plaza planting skipped:", e)
    out["trees3d"] = []                                      # no trees (the user's request, 2026-09-28); was: flat [x, y, height, ...]
    out["shrubs3d"] = []                                     # no round shrubs either (the user's request, 2026-09-28); was: shrubs, flat [x, y, radius, ...]

    path = ROOT / "output" / "disneysea" / "mock_data.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[mock] {path} {path.stat().st_size / 1024:.0f} KB  "
          f"bldg={len(out['buildings'])} water={len(out['water'])} paths={len(out['paths'])}")
    # always rebuild the publishable page from the template (keeps other tabs' template hooks)
    tpl = ROOT / "output" / "disneysea" / "mock_template.html"
    # the Resort Line cars are the Blender model (models/train.json); train_model.js now only serves train.html
    page = tpl.read_text(encoding="utf-8")
    page = page.replace("__DATA__", path.read_text(encoding="utf-8").replace("</", r"<\/"))
    (ROOT / "output" / "disneysea" / "tds_outline.html").write_text(page, encoding="utf-8")
    print(f"[mock] page tds_outline.html {len(page.encode('utf-8')) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
