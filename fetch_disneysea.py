"""東京ディズニーシー 下書き用データ取得 (OSM Overpass)

園の周辺 bbox 内の建物・水面・園路・線路・植栽・POI を全部取り、
ローカル座標(m)に変換して plateau_data/disneysea_osm.json に保存する。

座標: 原点 = ORIGIN(メディテレーニアンハーバー付近), +X 東, +Y 北
"""
import json, math, sys, time, urllib.request, urllib.parse, pathlib

ORIGIN = (35.6267, 139.8851)          # lat, lon
BBOX = (35.6195, 139.8765, 35.6340, 139.8935)   # S, W, N, E (園+周辺道路/海)
OUT = pathlib.Path(__file__).with_name("plateau_data") / "disneysea_osm.json"
RAW = OUT.with_name("disneysea_osm_raw.json")
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

def overpass(q):
    for attempt in range(3):
        for m in MIRRORS:
            try:
                req = urllib.request.Request(
                    m, data=urllib.parse.urlencode({"data": q}).encode(),
                    headers={"User-Agent": "tds-draft/1.0 (personal 3D study)"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r)
            except Exception as e:
                print("  mirror fail", m, e, file=sys.stderr)
        time.sleep(10)
    raise SystemExit("overpass failed")

def to_xy(lat, lon):
    k = 111320.0
    return ((lon - ORIGIN[1]) * k * math.cos(math.radians(ORIGIN[0])),
            (lat - ORIGIN[0]) * 110574.0)

def main():
    if RAW.exists() and "--refetch" not in sys.argv:
        data = json.loads(RAW.read_text(encoding="utf-8"))
    else:
        s, w, n, e = BBOX
        q = f"""[out:json][timeout:170][bbox:{s},{w},{n},{e}];
(way; relation["type"="multipolygon"]; node[~"."~"."];);
out body; >; out skel qt;"""
        data = overpass(q)
        RAW.parent.mkdir(exist_ok=True)
        RAW.write_text(json.dumps(data), encoding="utf-8")
    nodes = {el["id"]: (el["lat"], el["lon"]) for el in data["elements"]
             if el["type"] == "node" and "lat" in el}
    ways = {el["id"]: el for el in data["elements"] if el["type"] == "way"}
    out = {"origin": ORIGIN, "ways": [], "relations": [], "pois": []}
    for w in ways.values():
        pts = [to_xy(*nodes[i]) for i in w["nodes"] if i in nodes]
        if len(pts) < 2:
            continue
        out["ways"].append({"id": w["id"], "tags": w.get("tags", {}),
                            "closed": w["nodes"][0] == w["nodes"][-1],
                            "pts": [(round(x, 2), round(y, 2)) for x, y in pts]})
    for el in data["elements"]:
        if el["type"] == "relation":
            mem = [{"role": m["role"], "way": m["ref"]} for m in el["members"]
                   if m["type"] == "way"]
            out["relations"].append({"id": el["id"], "tags": el.get("tags", {}),
                                     "members": mem})
        elif el["type"] == "node" and el.get("tags"):
            x, y = to_xy(el["lat"], el["lon"])
            out["pois"].append({"id": el["id"], "tags": el["tags"],
                                "xy": (round(x, 2), round(y, 2))})
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"ways={len(out['ways'])} rels={len(out['relations'])} pois={len(out['pois'])} -> {OUT}")

if __name__ == "__main__":
    main()
