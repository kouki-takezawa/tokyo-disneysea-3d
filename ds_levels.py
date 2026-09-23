"""Terrain heights, stairs and bridges for the DisneySea draft (no bpy needed).

Ground: GSI DEM5A (5 m airborne-laser DEM, z15 PNG tiles cached in
plateau_data/gsi_dem5a/, mosaic.npy + mosaic.json) with gaps (water, voids)
filled from neighbours. Heights are RELATIVE to DATUM = median DEM height on
the park's ground-level paths (~4.5 m above sea level), so the promenade is z=0.

Stairs: OSM has position/length for ~98 flights but step_count/incline on only
one, so each flight gets a rise, a direction and a BASIS:
  "dem"     both ends differ by >= 0.5 m in the DEM -> rise and direction measured
  "link"    one end joins a bridge / elevated walkway (layer>=1) -> that end is up,
            or joins a tunnel (layer<0) -> that end is down; rise from length
  "length"  rise from length (0.16 m riser / 0.30 m tread, <= 3 m); direction
            from the sign of the small DEM difference
  "unknown" as "length" but no usable direction (flagged for the user to check)
Path network is split at stairs into level components; small components fed by
a stair are shifted so the stair actually connects (raised terraces / sunken
landings) while the main promenade stays on the DEM.

  python ds_levels.py          # builds plateau_data/disneysea_levels.json and prints a summary
"""
import json, math, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
PD = ROOT / "plateau_data"
LAT0, LON0 = 35.6267, 139.8851
KX, KY = 111320.0 * math.cos(math.radians(LAT0)), 110574.0
RISER, TREAD, MAX_RISE = 0.16, 0.30, 3.0
SMALL_COMPONENT_M = 250.0          # path length below which a component may be shifted
WALL_H = {"wall": 2.5, "hedge": 1.2, "fence": 1.1, "retaining_wall": None, "embankment": None}
LEVEL_OVERRIDE = {}                # way_id -> {"rise": m, "up": "start"|"end"} from user corrections

# ---------------------------------------------------------------- DEM
_M = json.loads((PD / "gsi_dem5a" / "mosaic.json").read_text())
_H = np.load(PD / "gsi_dem5a" / "mosaic.npy").astype(np.float64)
_N = 2 ** _M["z"]


def _fill(h):
    """Fill NaNs by repeated neighbour averaging (water, voids)."""
    h = h.copy()
    for _ in range(400):
        nan = ~np.isfinite(h)
        if not nan.any():
            break
        p = np.pad(h, 1, constant_values=np.nan)
        stack = np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
        cnt = np.isfinite(stack).sum(0)
        s = np.nansum(stack, 0)
        upd = nan & (cnt > 0)
        h[upd] = s[upd] / cnt[upd]
    return h


_RAW_VALID = np.isfinite(_H)
_HF = _fill(_H)


def _pix(x, y):
    lat, lon = LAT0 + y / KY, LON0 + x / KX
    fx = (lon + 180) / 360 * _N
    fy = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * _N
    return (fy - _M["ty0"]) * 256 - 0.5, (fx - _M["tx0"]) * 256 - 0.5


def dem_abs(x, y):
    """Bilinear DEM height above sea level (m)."""
    i, j = _pix(x, y)
    i0, j0 = int(math.floor(i)), int(math.floor(j))
    i0 = min(max(i0, 0), _HF.shape[0] - 2); j0 = min(max(j0, 0), _HF.shape[1] - 2)
    fi, fj = min(max(i - i0, 0), 1), min(max(j - j0, 0), 1)
    a, b, c, d = _HF[i0, j0], _HF[i0, j0 + 1], _HF[i0 + 1, j0], _HF[i0 + 1, j0 + 1]
    return a * (1 - fi) * (1 - fj) + b * (1 - fi) * fj + c * fi * (1 - fj) + d * fi * fj


DATUM = 4.5  # replaced by compute() with the measured path median


def dem(x, y):
    """Height relative to the promenade datum (m)."""
    return dem_abs(x, y) - DATUM


def pixel_size_m():
    return 40075016.686 * math.cos(math.radians(LAT0)) / (_N * 256)


# ---------------------------------------------------------------- geometry helpers
def _xy(lat, lon):
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


def _pip(x, y, poly):
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _length(pts):
    return sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))


def _beyond(pts, at_end, d=2.0):
    """Point d metres beyond the start or end of a polyline, along its direction."""
    if at_end:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
    else:
        (x0, y0), (x1, y1) = pts[1], pts[0]
    L = math.dist((x0, y0), (x1, y1)) or 1.0
    return x1 + (x1 - x0) / L * d, y1 + (y1 - y0) / L * d


def _layer(t):
    try:
        return int(t.get("layer", 0))
    except ValueError:
        return 0


# ---------------------------------------------------------------- main solve
def compute():
    global DATUM
    raw = json.loads((PD / "disneysea_osm_raw.json").read_text(encoding="utf-8"))
    nodes = {e["id"]: _xy(e["lat"], e["lon"]) for e in raw["elements"] if e["type"] == "node" and "lat" in e}
    ways = [e for e in raw["elements"] if e["type"] == "way"]
    park_way = next(w for w in ways if w["id"] == 203538370)
    park = [nodes[n] for n in park_way["nodes"] if n in nodes]

    hw = []
    for w in ways:
        t = w.get("tags", {})
        if "highway" not in t or t["highway"] in ("platform",):
            continue
        pts = [nodes[n] for n in w["nodes"] if n in nodes]
        if len(pts) < 2:
            continue
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        if not _pip(cx, cy, park):
            continue
        hw.append({"id": w["id"], "t": t, "nodes": [n for n in w["nodes"] if n in nodes], "pts": pts,
                   "steps": t["highway"] == "steps", "layer": _layer(t),
                   "bridge": t.get("bridge") in ("yes", "viaduct"), "tunnel": t.get("tunnel") == "yes" or _layer(t) < 0})

    ground_pts = [p for w in hw if not (w["steps"] or w["bridge"] or w["tunnel"] or w["layer"] > 0) for p in w["pts"]]
    DATUM = float(np.median([dem_abs(x, y) for x, y in ground_pts]))

    node_ways = {}
    for k, w in enumerate(hw):
        for n in w["nodes"]:
            node_ways.setdefault(n, []).append(k)

    # ---- level components: union non-stair ways that share nodes
    parent = list(range(len(hw)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for n, ks in node_ways.items():
        ks = [k for k in ks if not hw[k]["steps"]]
        for k in ks[1:]:
            parent[find(k)] = find(ks[0])
    comp_len = {}
    for k, w in enumerate(hw):
        if not w["steps"]:
            comp_len[find(k)] = comp_len.get(find(k), 0.0) + _length(w["pts"])
    main = max(comp_len, key=comp_len.get)

    def end_info(w, at_end):
        n = w["nodes"][-1] if at_end else w["nodes"][0]
        others = [hw[k] for k in node_ways.get(n, []) if hw[k] is not w and not hw[k]["steps"]]
        comps = {find(hw.index(o)) for o in others}
        return {"node": n, "up_hint": any(o["bridge"] or o["layer"] > 0 for o in others),
                "down_hint": any(o["tunnel"] for o in others), "comps": comps}

    # ---- stairs
    stairs = {}
    counts = {"dem": 0, "link": 0, "length": 0, "unknown": 0}
    for w in hw:
        if not w["steps"]:
            continue
        L = _length(w["pts"])
        hA, hB = dem(*_beyond(w["pts"], False)), dem(*_beyond(w["pts"], True))
        a, b = end_info(w, False), end_info(w, True)
        est = min(MAX_RISE, max(1, round(L / TREAD)) * RISER)
        ov = LEVEL_OVERRIDE.get(w["id"])
        if ov:
            rise, up, basis = ov["rise"], ov["up"], "user"
        elif abs(hB - hA) >= 0.5:
            rise, up, basis = abs(hB - hA), ("end" if hB > hA else "start"), "dem"
        elif a["up_hint"] != b["up_hint"] or a["down_hint"] != b["down_hint"]:
            up = "end" if (b["up_hint"] or a["down_hint"]) else "start"
            rise, basis = est, "link"
        elif w["t"].get("incline") in ("up", "down"):
            up = "end" if w["t"]["incline"] == "up" else "start"
            rise, basis = (float(w["t"]["step_count"]) * RISER if w["t"].get("step_count") else est), "link"
        elif abs(hB - hA) >= 0.1:
            rise, up, basis = est, ("end" if hB > hA else "start"), "length"
        else:
            rise, up, basis = est, "end", "unknown"
        counts[basis if basis in counts else "dem"] += 1
        lo_h = hA if up == "end" else hB
        if basis == "dem":
            z0, z1 = hA, hB
        else:
            z0, z1 = (lo_h, lo_h + rise) if up == "end" else (lo_h + rise, lo_h)
        stairs[w["id"]] = {"rise": round(rise, 2), "steps": max(1, round(rise / RISER)), "up": up,
                           "basis": basis, "z0": z0, "z1": z1, "len": round(L, 1), "A": a, "B": b}

    # ---- shift small components so non-DEM stairs connect
    shift_votes = {}
    for sid, s in stairs.items():
        if s["basis"] == "dem":
            continue
        for info, z_end in ((s["A"], s["z0"]), (s["B"], s["z1"])):
            n = info["node"]
            for c in info["comps"]:
                if c == main or comp_len.get(c, 1e9) > SMALL_COMPONENT_M:
                    continue
                shift_votes.setdefault(c, []).append(z_end - dem(*nodes[n]))
    shift = {c: float(np.mean(v)) for c, v in shift_votes.items()}

    # ---- per-way heights
    out_ways = {}
    for k, w in enumerate(hw):
        if w["steps"]:
            s = stairs[w["id"]]
            n = len(w["pts"]); L = _length(w["pts"]) or 1; acc = [0.0]
            for q in range(1, n):
                acc.append(acc[-1] + math.dist(w["pts"][q - 1], w["pts"][q]))
            z = [s["z0"] + (s["z1"] - s["z0"]) * a / L for a in acc]
            out_ways[w["id"]] = {"z": z, "kind": "steps"}
            continue
        off = shift.get(find(k), 0.0)
        z = [dem(x, y) + off for x, y in w["pts"]]
        kind = "tunnel" if w["tunnel"] else ("bridge" if (w["bridge"] or w["layer"] > 0) else "ground")
        if kind == "bridge":
            # deck: ends from whatever they join (stair tops / ground), interior interpolated + a slight arch
            def end_z(n_id, fallback):
                for kk in node_ways.get(n_id, []):
                    o = hw[kk]
                    if o["steps"]:
                        s = stairs[o["id"]]
                        return s["z0"] if o["nodes"][0] == n_id else s["z1"]
                return fallback
            za, zb = end_z(w["nodes"][0], z[0]), end_z(w["nodes"][-1], z[-1])
            if w["layer"] >= 2:
                za, zb = max(za, 5.0), max(zb, 5.0)
            L = _length(w["pts"]) or 1; acc = [0.0]
            for q in range(1, len(w["pts"])):
                acc.append(acc[-1] + math.dist(w["pts"][q - 1], w["pts"][q]))
            arch = 0.6 if w["bridge"] and L > 8 else 0.0
            z = [za + (zb - za) * a / L + arch * math.sin(math.pi * a / L) for a in acc]
        out_ways[w["id"]] = {"z": z, "kind": kind}

    # ---- walls / hedges / fences / retaining walls / embankments
    walls = []
    for w in ways:
        t = w.get("tags", {})
        typ = t.get("barrier") if t.get("barrier") in WALL_H else ("embankment" if t.get("man_made") == "embankment" else None)
        if not typ:
            continue
        pts = [nodes[n] for n in w["nodes"] if n in nodes]
        if len(pts) < 2:
            continue
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        if not _pip(cx, cy, park):
            continue
        h = WALL_H[typ]
        if h is None:  # height = DEM difference across the line, sampled at the middle segment
            m = len(pts) // 2
            (x0, y0), (x1, y1) = pts[max(0, m - 1)], pts[min(len(pts) - 1, m)]
            L = math.dist((x0, y0), (x1, y1)) or 1
            nx, ny = -(y1 - y0) / L * 4, (x1 - x0) / L * 4
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            h = max(0.8, abs(dem(mx + nx, my + ny) - dem(mx - nx, my - ny)))
        walls.append({"id": w["id"], "type": typ, "h": round(h, 2), "pts": pts,
                      "z": [dem(x, y) for x, y in pts]})

    res = {"datum_m": round(DATUM, 2), "pixel_m": round(pixel_size_m(), 2), "counts": counts,
           "ways": {str(k): {"z": [round(v, 2) for v in val["z"]], "kind": val["kind"]} for k, val in out_ways.items()},
           "stairs": {str(k): {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in s.items() if kk not in ("A", "B")}
                      for k, s in stairs.items()},
           "walls": [{"id": wl["id"], "type": wl["type"], "h": wl["h"],
                      "pts": [[round(x, 1), round(y, 1)] for x, y in wl["pts"]], "z": [round(v, 2) for v in wl["z"]]} for wl in walls],
           "shifted_components": len(shift)}
    (PD / "disneysea_levels.json").write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return res


def contours(park, interval=1.0, blur=2):
    """Marching-squares contour segments of the filled DEM (relative heights), clipped to the park bbox.
    Returns {level: [x1,y1,x2,y2, ...]} in local metres."""
    xs = [p[0] for p in park]; ys = [p[1] for p in park]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    i_a, j_a = _pix(x0, y1); i_b, j_b = _pix(x1, y0)
    i_a, j_a = max(0, int(i_a) - 2), max(0, int(j_a) - 2)
    i_b, j_b = min(_HF.shape[0] - 1, int(i_b) + 3), min(_HF.shape[1] - 1, int(j_b) + 3)
    g = _HF[i_a:i_b + 1, j_a:j_b + 1] - DATUM
    for _ in range(blur):  # 3x3 box blur to calm the 5 m noise
        p = np.pad(g, 1, mode="edge")
        g = sum(p[a:a + g.shape[0], b:b + g.shape[1]] for a in range(3) for b in range(3)) / 9.0

    # pixel (i, j) -> local xy via inverse of _pix
    def to_xy(i, j):
        fy = (i + i_a + 0.5) / 256 + _M["ty0"]; fx = (j + j_a + 0.5) / 256 + _M["tx0"]
        lon = fx / _N * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * fy / _N))))
        return (lon - LON0) * KX, (lat - LAT0) * KY
    out = {}
    lo, hi = math.floor(np.nanmin(g) / interval) * interval, math.ceil(np.nanmax(g) / interval) * interval
    lv = lo
    while lv <= hi:
        segs = []
        a = g[:-1, :-1]; b = g[:-1, 1:]; c = g[1:, 1:]; d = g[1:, :-1]
        idx = ((a > lv) * 1 | (b > lv) * 2 | (c > lv) * 4 | (d > lv) * 8)
        ii, jj = np.nonzero((idx != 0) & (idx != 15))
        for i, j in zip(ii, jj):
            va, vb, vc, vd = g[i, j], g[i, j + 1], g[i + 1, j + 1], g[i + 1, j]
            pts = []
            for (p1, v1), (p2, v2) in (((( i, j), va), ((i, j + 1), vb)), (((i, j + 1), vb), ((i + 1, j + 1), vc)),
                                        (((i + 1, j + 1), vc), ((i + 1, j), vd)), (((i + 1, j), vd), ((i, j), va))):
                if (v1 > lv) != (v2 > lv):
                    t = (lv - v1) / (v2 - v1)
                    pts.append((p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t))
            for k in range(0, len(pts) - 1, 2):
                (pi1, pj1), (pi2, pj2) = pts[k], pts[k + 1]
                xa, ya = to_xy(pi1, pj1); xb, yb = to_xy(pi2, pj2)
                if _pip((xa + xb) / 2, (ya + yb) / 2, park):
                    segs += [round(xa, 1), round(ya, 1), round(xb, 1), round(yb, 1)]
        if segs:
            out[round(lv, 2)] = segs
        lv += interval
    return out


if __name__ == "__main__":
    r = compute()
    print(f"datum {r['datum_m']} m ASL, DEM pixel {r['pixel_m']} m")
    print("stairs by basis:", r["counts"], " shifted components:", r["shifted_components"])
    kinds = {}
    for v in r["ways"].values():
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    print("ways by kind:", kinds, " walls:", len(r["walls"]))
    s = r["stairs"].get("1292406716")
    print("check way 1292406716:", s)
    zs = [z for v in r["ways"].values() if v["kind"] == "ground" for z in v["z"]]
    print("ground path z range (rel): %.2f .. %.2f, median %.2f" % (min(zs), max(zs), float(np.median(zs))))
