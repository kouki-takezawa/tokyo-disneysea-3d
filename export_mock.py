"""Export the DisneySea draft geometry as compact JSON for the outline (枠線) mock page.

  python export_mock.py        (plain Python; Blender is not needed)

Reuses ds_core / ds_terrain logic (park clipping, water holes, heights, port
classification) so the mock and the Blender draft always show the same thing.
Writes output/disneysea/mock_data.json (coords rounded to 0.1 m).
"""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

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


def main():
    T.plan_water()   # water tab's bodies (cut / surface / tunnels) when available
    out = {"origin": C.DATA["origin"], "park": R(C.PARK),
           "ports": [{"id": p, "ja": PORT_JA[p]} for p in PORTS],
           "water": [], "ponds": [], "islands": [], "buildings": [], "green": [],
           "trees": [], "rock": [], "paths": [], "rail": [], "landmarks": [], "labels": []}

    lev = LV.compute()
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

    out["walls"] = [{"t": wl["type"], "h": wl["h"], "l": wl["pts"], "z": wl["z"]} for wl in lev["walls"]]
    out["contours"] = {str(k): v for k, v in LV.contours(C.PARK, interval=1.0).items()}
    xs = [p[0] for p in C.PARK]; ys = [p[1] for p in C.PARK]
    g0x, g0y, step = math.floor(min(xs)), math.floor(min(ys)), 8
    nx, ny = int((max(xs) - g0x) / step) + 2, int((max(ys) - g0y) / step) + 2
    out["hgrid"] = {"x0": g0x, "y0": g0y, "step": step, "nx": nx, "ny": ny,
                    "v": [round(LV.dem(g0x + i * step, g0y + j * step), 1) for j in range(ny) for i in range(nx)]}

    out["entrance"] = C.entrance_layer()      # Resort Line station + ticket gates (入場口・駅 layer)
    out.update(DLM.build(out["levels"]["datum"]))   # ディズニーランド / 舞浜駅・周辺 layers (separate OSM extract)
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
         "r": C.TRITON_ROOF["r"], "z": C.TRITON_ROOF["eaves"], "h": C.TRITON_ROOF["peak"] - C.TRITON_ROOF["eaves"]},
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
              ("plaza", "paths", []), ("volcano", "landmarks", ["volc"])]   # plaza ground: shown with the 園路 layer; the path lines elsewhere stay
    mdir = ROOT / "output" / "disneysea" / "models"
    out["models"] = [{"id": i, "layer": lay, "src": f"models/{i}.json", "hides": hides}   # glTF JSON (the host serves .json, not .glb)
                     for i, lay, hides in MODELS if (mdir / f"{i}.json").exists()]

    path = ROOT / "output" / "disneysea" / "mock_data.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[mock] {path} {path.stat().st_size / 1024:.0f} KB  "
          f"bldg={len(out['buildings'])} water={len(out['water'])} paths={len(out['paths'])}")
    # always rebuild the publishable page from the template (keeps other tabs' template hooks)
    tpl = ROOT / "output" / "disneysea" / "mock_template.html"
    page = tpl.read_text(encoding="utf-8").replace("__DATA__", path.read_text(encoding="utf-8").replace("</", "<\/"))
    (ROOT / "output" / "disneysea" / "tds_outline.html").write_text(page, encoding="utf-8")
    print(f"[mock] page tds_outline.html {len(page.encode('utf-8')) / 1024:.0f} KB")


main()
