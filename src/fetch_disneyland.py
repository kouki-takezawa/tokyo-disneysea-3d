"""東京ディズニーランド・舞浜駅まわりのデータ取得 (OSM Overpass)

シーのデータ(disneysea_osm.json)とは別ファイルに保存する。取り直してもシー側の処理は変わらない。

  python src/fetch_disneyland.py            # plateau_data/disneyland_osm.json
  python src/fetch_disneyland.py --refetch  # OSM を取り直す

座標はシーと同じ(原点 35.6267N 139.8851E, +X 東, +Y 北, m)。
標高はシーと同じ DEM5A のタイル(plateau_data/gsi_dem5a/)がランドと舞浜駅まで覆っているので、それを使う。
"""
import json, sys, pathlib
from fetch_disneysea import overpass, to_xy

BBOX = (35.6270, 139.8730, 35.6392, 139.8935)   # S, W, N, E (ランド + 舞浜駅 + イクスピアリ・ホテル)
PD = pathlib.Path(__file__).resolve().parent.parent / "plateau_data"
OUT = PD / "disneyland_osm.json"
RAW = PD / "disneyland_osm_raw.json"


def fetch_osm():
    if RAW.exists() and "--refetch" not in sys.argv:
        return json.loads(RAW.read_text(encoding="utf-8"))
    s, w, n, e = BBOX
    q = f"""[out:json][timeout:170][bbox:{s},{w},{n},{e}];
(way; relation["type"="multipolygon"]; node[~"."~"."];);
out body; >; out skel qt;"""
    data = overpass(q)
    RAW.write_text(json.dumps(data), encoding="utf-8")
    return data


def convert(data):
    nodes = {el["id"]: (el["lat"], el["lon"]) for el in data["elements"] if el["type"] == "node" and "lat" in el}
    out = {"origin": (35.6267, 139.8851), "bbox": BBOX, "ways": [], "relations": [], "pois": []}
    for el in data["elements"]:
        if el["type"] == "way":
            pts = [to_xy(*nodes[i]) for i in el["nodes"] if i in nodes]
            if len(pts) >= 2 and el.get("tags"):
                out["ways"].append({"id": el["id"], "tags": el["tags"], "closed": el["nodes"][0] == el["nodes"][-1],
                                    "pts": [(round(x, 2), round(y, 2)) for x, y in pts]})
        elif el["type"] == "relation":
            out["relations"].append({"id": el["id"], "tags": el.get("tags", {}),
                                     "members": [{"role": m["role"], "way": m["ref"]} for m in el["members"] if m["type"] == "way"]})
        elif el["type"] == "node" and el.get("tags"):
            x, y = to_xy(el["lat"], el["lon"])
            out["pois"].append({"id": el["id"], "tags": el["tags"], "xy": (round(x, 2), round(y, 2))})
    # multipolygon member ways usually carry no tags of their own: keep them untagged-but-referenced
    ref = {m["way"] for r in out["relations"] for m in r["members"]}
    have = {w["id"] for w in out["ways"]}
    for el in data["elements"]:
        if el["type"] == "way" and el["id"] in ref and el["id"] not in have:
            pts = [to_xy(*nodes[i]) for i in el["nodes"] if i in nodes]
            if len(pts) >= 2:
                out["ways"].append({"id": el["id"], "tags": {}, "closed": el["nodes"][0] == el["nodes"][-1],
                                    "pts": [(round(x, 2), round(y, 2)) for x, y in pts]})
    return out


def main():
    out = convert(fetch_osm())
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"ways={len(out['ways'])} rels={len(out['relations'])} pois={len(out['pois'])} -> {OUT}")


if __name__ == "__main__":
    main()
