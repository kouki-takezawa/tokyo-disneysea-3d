"""Tokyo Disneyland and the Maihama station area for the outline mock (no bpy needed).

Source: plateau_data/disneyland_osm.json (fetch_disneyland.py), separate from the DisneySea data so
refetching it never changes the DisneySea pipeline. Ground heights come from the same GSI DEM5A mosaic
(ds_levels), which already covers Tokyo Disneyland and Maihama Station.

  build(datum) -> {"disneyland": {...}, "maihama": {...}}   (local metres, same origin as DisneySea)
  python ds_disneyland.py --levels   # stairs / path heights / walls -> plateau_data/disneyland_levels.json
                                      # (ds_levels.compute on disneyland_osm_raw.json, DisneySea's datum)

Lands: a building belongs to the land of a POI (or named building) inside its footprint, else to the land
of the nearest such point within POI_REACH m, else to "other" (backstage, parking, service buildings).
"""
import json, math, pathlib
import ds_levels as LV
from ds_core import point_in_poly, poly_centroid, poly_area, _clean_ring

ROOT = pathlib.Path(__file__).resolve().parent
DATA = json.loads((ROOT / "plateau_data" / "disneyland_osm.json").read_text(encoding="utf-8"))
WAYS = {w["id"]: w for w in DATA["ways"]}
TDL_PARK_WAY = 1282875870          # 東京ディズニーランド (tourism=theme_park)
TDS_PARK_WAY = 203538370           # 東京ディズニーシー: its contents are drawn by the DisneySea layers
MAIHAMA_STATION = "舞浜"
POI_REACH = 90.0
DEFAULT_H, OTHER_H = 12.0, 10.0    # estimates for untagged buildings (m)
RESORT_LINE_Z, JR_Z = 8.0, 10.0    # viaduct heights above the promenade datum (estimates)
NAME_HEIGHT = {"シンデレラ城": 51.0}

LANDS = [   # (key, 日本語, name substrings of POIs / buildings that identify the land)
    ("world_bazaar", "ワールドバザール", (
        "ワールドバザール", "プロムナードギフト", "カメラセンター", "メインストリート", "Eastside", "グランドエンポーリアム",
        "センターストリート", "グレートアメリカン・ワッフル", "ハウス・オブ・グリーティング", "マジックショップ",
        "シルエットスタジオ", "タウンセンター", "Disney Gallery", "ハリントンズ", "ホームストア", "ペニーアーケード",
        "ディズニーカンパニー", "トイ・ステーション", "リフレッシュメントコーナー", "ペイストリーパレス", "スウィートハート",
        "Guest Relations", "ビビディ・バビディ", "オムニバス", "シェアリング・ザ・マジック", "ベビーセンター", "メインエントランス")),
    ("adventureland", "アドベンチャーランド", (
        "アドベンチャーランド", "ブルーバイユー", "クリスタルアーツ", "パイレーツ", "ラ・プティート", "ゴールデンガリオン",
        "カフェ・オーリンズ", "サファリ・トレーディング", "ル・マルシェ・ブルー", "チキ・トロピック", "ジャングルクルーズ",
        "Jungle Cruise", "elephant", "African Veldt", "Schweitzer", "Salesman Sam", "Native Territory", "クリスタルパレス",
        "チキルーム", "カリブの海賊", "ウエスタンリバー鉄道", "ポリネシアン", "Asian Ruins", "チャイナボイジャー", "シアターオーリンズ",
        "Base Camp")),
    ("westernland", "ウエスタンランド", (
        "ウエスタンランド", "ペコスビル", "トレーディングポスト", "ビッグ サンダー", "ビッグサンダー", "Big Thunder",
        "ダイヤモンドホースシュー", "ハングリー ベア", "カントリーベア", "ゼネラルストア", "ウエスタンウエア", "ウッドチャック",
        "カウボーイ・クックハウス", "ハッピーキャンパー", "フロンティア・ウッドクラフト", "トムソーヤ", "トムの船着き場",
        "サムクレメンズ", "開拓者の船着き場", "スピニング岩", "スマグラー", "Mark Twain", "マークトウェイン", "ティータートッター",
        "ハックルベリー", "インディアン", "Indian Camp", "ダスティベンド", "スティルウォーター", "燃える小屋", "ハーパーの粉ひき",
        "魚釣りドック", "Primeval World")),
    ("critter_country", "クリッターカントリー", (
        "クリッターカントリー", "スプラッシュ", "ビーバーブラザーズ", "フートハラー", "グランマ・サラ", "ブレア・ラビット", "ラケッティ")),
    ("fantasyland", "ファンタジーランド", (
        "ファンタジーランド", "シンデレラ", "白雪姫", "ガラスの靴", "トルバドール", "キャプテンフック", "ピーターパン",
        "魔法使いの弟子", "キングダム・トレジャー", "ファンタジーギフト", "ベビーマイン", "フィルハーマジック", "空飛ぶダンボ",
        "美女と野獣", "モーリス", "ガストン", "ル・フウズ", "ラ・タベルヌ", "ハーモニーフェア", "ピノキオ", "プレジャーアイランド",
        "クイーン・オブ・ハート", "スモールワールド", "イッツ・ア・スモールワールド", "プーさん", "ホーンテッドマンション",
        "ヴィレッジ・ショップス", "ビッグポップ", "キャッスルカールセル", "アリスのティーパーティー", "ストロンボリ", "ビレッジペイストリー",
        "クレオズ")),
    ("toontown", "トゥーンタウン", (
        "トゥーンタウン", "トゥーントーン", "ディンギー", "ミッキーの噴水", "ヒューイ・デューイ", "ギャグファクトリー",
        "ミニーのスタイルスタジオ", "ミッキーの家", "ミニーの家", "ロジャーラビット", "グーフィー", "チップとデール", "ドナルドのボート",
        "ガジェット")),
    ("tomorrowland", "トゥモローランド", (
        "トゥモローランド", "パン・ギャラクティック", "ソフトランディング", "コズミック・エンカウンター", "ポッピングポッド",
        "トレジャーコメット", "スティッチエンカウンター", "スターゲイザー", "ベイマックス", "モンスターズ・インク", "スター・ツアーズ",
        "ショーベース", "プラズマ・レイズ", "スペース・マウンテン", "バズ・ライトイヤー")),
]
OTHER = len(LANDS)   # バックステージ・その他
BACKSTAGE_NAMES = ("機関庫", "従業員", "メンテナンス")   # named, but not part of a land
LEVELS_JSON = ROOT / "plateau_data" / "disneyland_levels.json"
PATH_W = {"pedestrian": 8.0, "footway": 3.5, "steps": 3.5, "service": 5.0, "corridor": 3.0}


def compute_levels(datum):
    return LV.compute(raw_name="disneyland_osm_raw.json", park_id=TDL_PARK_WAY, out_name=LEVELS_JSON.name, datum=datum)


def load_levels(datum):
    if LEVELS_JSON.exists():
        return json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    return compute_levels(datum)


def R(pts):
    return [[round(x, 1), round(y, 1)] for x, y in pts]


def ring_of(w):
    return _clean_ring(w["pts"])


def outer_rings(rel):
    """Outer rings of a multipolygon relation (member ways chained end to end)."""
    segs = [list(map(tuple, WAYS[m["way"]]["pts"])) for m in rel["members"] if m["role"] == "outer" and m["way"] in WAYS]
    rings = []
    while segs:
        cur = segs.pop(0)
        grown = True
        while cur[0] != cur[-1] and grown:
            grown = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]: cur += s[1:]
                elif s[-1] == cur[-1]: cur += s[::-1][1:]
                elif s[-1] == cur[0]: cur = s[:-1] + cur
                elif s[0] == cur[0]: cur = s[::-1][:-1] + cur
                else: continue
                segs.pop(i); grown = True; break
        if len(cur) >= 4:
            rings.append(_clean_ring(cur))
    return rings


def land_of_name(name):
    if any(k in name for k in BACKSTAGE_NAMES):
        return None
    return next((i for i, (_, _, keys) in enumerate(LANDS) if any(k in name for k in keys)), None)


def build(datum):
    park = ring_of(WAYS[TDL_PARK_WAY])
    tds = ring_of(WAYS[TDS_PARK_WAY]) if TDS_PARK_WAY in WAYS else []
    in_tdl = lambda x, y: point_in_poly(x, y, park)
    z_of = lambda x, y: round(LV.dem_abs(x, y) - datum, 2)

    # land marker points: named POIs and named buildings inside the park
    marks = []
    for p in DATA["pois"]:
        n = p["tags"].get("name", "")
        if n and in_tdl(*p["xy"]):
            li = land_of_name(n)
            if li is not None: marks.append((*p["xy"], li))
    for w in DATA["ways"]:
        n = w["tags"].get("name", "")
        if n and "building" in w["tags"] and w["closed"] and in_tdl(*poly_centroid(w["pts"])):
            li = land_of_name(n)
            if li is not None: marks.append((*poly_centroid(w["pts"]), li))

    def land_of(ring):
        inside = [li for x, y, li in marks if point_in_poly(x, y, ring)]
        if inside:
            return max(sorted(set(inside)), key=inside.count)
        cx, cy = poly_centroid(ring)
        best, bd = OTHER, POI_REACH ** 2
        for x, y, li in marks:
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d < bd: best, bd = li, d
        return best

    def height(tags, li):
        n = tags.get("name", "")
        for k, h in NAME_HEIGHT.items():
            if k in n: return h
        try:
            return float(str(tags.get("height")).split(";")[0].replace("m", "").strip())
        except ValueError:
            pass
        if tags.get("building:levels"):
            try: return max(4.0, float(tags["building:levels"]) * 3.6)
            except ValueError: pass
        return OTHER_H if li == OTHER else DEFAULT_H

    construction = []   # areas under construction: [(ring, name)]
    for w in DATA["ways"]:
        t = w["tags"]
        if w["closed"] and (t.get("landuse") == "construction" or "construction" in t) and "building" not in t and in_tdl(*poly_centroid(w["pts"])):
            construction.append((ring_of(w), t.get("name", "建設工事")))

    items = [(w["tags"], [ring_of(w)]) for w in DATA["ways"] if "building" in w["tags"] and w["closed"]]
    items += [(r["tags"], outer_rings(r)) for r in DATA["relations"] if "building" in r["tags"]]
    buildings, pts_by_land = [], {i: [] for i in range(len(LANDS))}
    for tags, rings in items:
        rings = [r for r in rings if len(r) >= 3]
        if not rings or not in_tdl(*poly_centroid(rings[0])):
            continue
        cx, cy = poly_centroid(rings[0]); a = poly_area(rings[0])
        site = next((n for r, n in construction if point_in_poly(cx, cy, r)), None)
        if any(k in tags.get("name", "") for k in BACKSTAGE_NAMES):
            li = OTHER
        elif site is not None and land_of_name(site) is not None:   # e.g. the new Tomorrowland attraction site
            li = land_of_name(site)
        else:
            li = land_of(rings[0])
        b = {"r": [R(r) for r in rings], "h": round(height(tags, li), 1), "p": li, "z": z_of(cx, cy)}
        if site is not None: b["c"] = site
        if tags.get("name"): b["n"] = tags["name"]
        buildings.append(b)
        if li != OTHER: pts_by_land[li].append((cx, cy, a))
    labels = []
    for li, pts in pts_by_land.items():
        if pts:
            A = sum(a for *_, a in pts)
            labels.append({"n": LANDS[li][1], "p": li, "x": round(sum(x * a for x, _, a in pts) / A), "y": round(sum(y * a for _, y, a in pts) / A)})

    def areas(pred):
        out = []
        for w in DATA["ways"]:
            if w["closed"] and pred(w["tags"]) and in_tdl(*poly_centroid(w["pts"])): out.append(R(ring_of(w)))
        for r in DATA["relations"]:
            if pred(r["tags"]):
                out += [R(o) for o in outer_rings(r) if len(o) >= 3 and in_tdl(*poly_centroid(o))]
        return out
    water = areas(lambda t: t.get("natural") == "water" or t.get("water") or t.get("leisure") == "swimming_pool")
    green = areas(lambda t: t.get("leisure") in ("park", "garden") or t.get("landuse") in ("grass", "meadow") and not t.get("tourism"))
    trees = areas(lambda t: t.get("landuse") == "forest" or t.get("natural") in ("wood", "scrub"))
    lev = load_levels(datum)
    paths = []   # same format as the DisneySea paths in export_mock: l, w, z, b (bridge), u (tunnel), a (area), s (stair)
    for w in DATA["ways"]:
        hw = w["tags"].get("highway")
        if hw not in PATH_W or not in_tdl(*poly_centroid(w["pts"])):
            continue
        p = {"l": R(w["pts"]), "w": PATH_W[hw]}
        lw = lev["ways"].get(str(w["id"]))
        if lw and len(lw["z"]) == len(w["pts"]):
            p["z"] = lw["z"]
            if lw["kind"] == "bridge": p["b"] = 1
            elif lw["kind"] == "tunnel": p["u"] = 1
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
            if w["tags"].get("name"): p["s"]["n"] = w["tags"]["name"]
        paths.append(p)
    walls = [{"t": wl["type"], "h": wl["h"], "l": wl["pts"], "z": wl["z"]} for wl in lev["walls"]]
    LV.DATUM = datum
    contours = {str(k): v for k, v in LV.contours(park, interval=1.0).items()}
    rail = [R(w["pts"]) for w in DATA["ways"] if w["tags"].get("railway") in ("narrow_gauge", "rail", "light_rail")
            and "京葉" not in w["tags"].get("name", "") and in_tdl(*poly_centroid(w["pts"]))]

    xs = [p[0] for p in park]; ys = [p[1] for p in park]
    step = 10
    g0x, g0y = math.floor(min(xs)), math.floor(min(ys))
    nx, ny = int((max(xs) - g0x) / step) + 2, int((max(ys) - g0y) / step) + 2
    hgrid = {"x0": g0x, "y0": g0y, "step": step, "nx": nx, "ny": ny,
             "v": [round(LV.dem_abs(g0x + i * step, g0y + j * step) - datum, 1) for j in range(ny) for i in range(nx)]}

    disneyland = {"park": R(park), "lands": [{"id": k, "ja": ja} for k, ja, _ in LANDS] + [{"id": "other", "ja": "バックステージ・その他"}],
                  "buildings": buildings, "labels": labels, "water": water, "green": green, "trees": trees,
                  "paths": paths, "walls": walls, "contours": contours, "levels": {"counts": lev["counts"]},
                  "construction": [{"n": n, "r": R(r)} for r, n in construction], "rail": rail, "hgrid": hgrid}

    # ---- Maihama station and around: JR Keiyo line near the station, the whole Resort Line loop and its
    # stations, Ikspiari, hotels, station buildings, and the walkways between the station and the park gates
    st = next(p for p in DATA["pois"] if p["tags"].get("railway") == "station" and p["tags"].get("name") == MAIHAMA_STATION)
    sx, sy = st["xy"]
    outside_parks = lambda x, y: not in_tdl(x, y) and not (tds and point_in_poly(x, y, tds))
    jr = []
    for w in DATA["ways"]:
        if w["tags"].get("railway") == "rail" and "京葉" in w["tags"].get("name", ""):
            run = [p for p in w["pts"] if math.hypot(p[0] - sx, p[1] - sy) < 420]
            if len(run) > 1: jr.append(R(run))
    loop = [R(w["pts"]) for w in DATA["ways"] if w["tags"].get("railway") == "monorail" and w["tags"].get("service") != "yard"]
    try:   # the loop's southern ways lie only in the DisneySea extract
        import ds_core as C
        have = {w["id"] for w in DATA["ways"]}
        loop += [R(w["pts"]) for w in C.DATA["ways"] if w["tags"].get("railway") == "monorail"
                 and w["tags"].get("service") != "yard" and w["id"] not in have]
    except Exception:
        pass
    stations = [{"n": p["tags"]["name"], "x": round(p["xy"][0], 1), "y": round(p["xy"][1], 1),
                 "k": "monorail" if p["tags"].get("station") == "monorail" else "jr"}
                for p in DATA["pois"] if p["tags"].get("railway") == "station" and p["tags"].get("name")
                and (p["tags"].get("station") == "monorail" or p["tags"]["name"] == MAIHAMA_STATION)]
    platforms = [R(ring_of(w)) for w in DATA["ways"] if w["tags"].get("railway") == "platform" and w["closed"]
                 and (outside_parks(*poly_centroid(w["pts"])) or math.hypot(*(a - b for a, b in zip(poly_centroid(w["pts"]), (sx, sy)))) < 60)]
    places = []   # Ikspiari, hotels, station buildings
    def add_place(tags, rings, kind):
        rings = [r for r in rings if len(r) >= 3]
        if not rings: return
        cx, cy = poly_centroid(rings[0])
        if not outside_parks(cx, cy) and kind != "station": return
        h = height(tags, OTHER) if (tags.get("height") or tags.get("building:levels")) else {"hotel": 30.0, "mall": 15.0, "station": 9.0}[kind]
        places.append({"n": tags.get("name", ""), "k": kind, "r": [R(r) for r in rings], "h": round(h, 1), "z": z_of(cx, cy)})
    for w in DATA["ways"]:
        t = w["tags"]
        if not w["closed"]: continue
        if "イクスピアリ" in t.get("name", "") and "building" in t: add_place(t, [ring_of(w)], "mall")
        elif t.get("tourism") == "hotel" or ("building" in t and "ホテル" in t.get("name", "") and "パーキング" not in t.get("name", "")):
            add_place(t, [ring_of(w)], "hotel")
        elif t.get("building") == "train_station": add_place(t, [ring_of(w)], "station")
    for r in DATA["relations"]:
        t = r["tags"]
        if t.get("tourism") == "hotel": add_place(t, outer_rings(r), "hotel")
        elif t.get("building") == "train_station": add_place(t, outer_rings(r), "station")
    gate = next((poly_centroid(w["pts"]) for w in DATA["ways"] if w["tags"].get("name") == "東京ディズニーランド メインエントランス"), (-544, 933))
    lo_x, hi_x = min(sx, gate[0]) - 120, max(sx, gate[0]) + 200
    lo_y, hi_y = min(sy, gate[1]) - 80, max(sy, gate[1]) + 90
    walks = [R(w["pts"]) for w in DATA["ways"] if w["tags"].get("highway") in ("footway", "pedestrian", "steps")
             and all(lo_x < x < hi_x and lo_y < y < hi_y for x, y in w["pts"]) and outside_parks(*poly_centroid(w["pts"]))]
    maihama = {"station": {"n": "舞浜駅(JR 京葉線)", "x": round(sx, 1), "y": round(sy, 1)}, "gate": {"n": "東京ディズニーランド メインエントランス", "x": round(gate[0], 1), "y": round(gate[1], 1)},
               "jr": jr, "jr_z": JR_Z, "loop": loop, "loop_z": RESORT_LINE_Z, "stations": stations, "platforms": platforms,
               "places": places, "walks": walks}
    return {"disneyland": disneyland, "maihama": maihama}


if __name__ == "__main__":
    import collections, sys
    datum = json.loads((ROOT / "plateau_data" / "disneysea_levels.json").read_text(encoding="utf-8"))["datum_m"]   # DisneySea's 0 m
    if "--levels" in sys.argv:
        r = compute_levels(datum)
        print("stairs by basis:", r["counts"], " walls:", len(r["walls"]), " ways:", len(r["ways"]))
        sys.exit()
    out = build(datum)
    d, m = out["disneyland"], out["maihama"]
    c = collections.Counter(b["p"] for b in d["buildings"])
    print("buildings", len(d["buildings"]), {d["lands"][k]["ja"]: v for k, v in sorted(c.items())})
    print("water", len(d["water"]), "green", len(d["green"]), "trees", len(d["trees"]), "paths", len(d["paths"]), "rail", len(d["rail"]),
          "stairs", sum(1 for p in d["paths"] if "s" in p), "walls", len(d["walls"]), "contour levels", len(d["contours"]),
          "construction", [c["n"] for c in d["construction"]], "under construction bldgs", [(b.get("n", ""), d["lands"][b["p"]]["ja"]) for b in d["buildings"] if "c" in b])
    print("labels", [(l["n"], l["x"], l["y"]) for l in d["labels"]])
    print("maihama jr", len(m["jr"]), "loop", len(m["loop"]), "stations", [s["n"] for s in m["stations"]], "platforms", len(m["platforms"]),
          "places", [(p["n"], p["k"]) for p in m["places"]], "walks", len(m["walks"]))
    print("json size KB", len(json.dumps(out, ensure_ascii=False, separators=(",", ":"))) // 1024)
