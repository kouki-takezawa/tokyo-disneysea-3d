"""Mount Prometheus / Mysterious Island rock massif as a heightfield (plain Python, no bpy).

Why not a cone: the first draft put a 70 m-radius cone on the OSM summit POI
(-50,-111), which buried the caldera lagoon. GSI DEM5A shows what is really there:
the whole Mysterious Island block is a flat plateau ~5.3 m above the promenade
(the rock itself was filtered out of the DEM as a structure), with the caldera
lagoon in the middle (water tab: body "R3531413_lagoon", harbour tunnels under
the rock). So the massif is modelled ON that plateau as a ring around the lagoon:

  summit   51 m above the promenade (public figure) near the OSM POI, south rim
  rim      ~20 m crest about 22 m out from the lagoon shore
  caldera  within 6 m of the lagoon shore the rock drops to the plateau (quay/paths)
  open     ground-level paths (+3 m or higher on the plateau) and buildings stay
           clear (3 m / 1.5 m), so guests' routes inside the caldera are not buried
  edges    rock tapers into the plateau edge over 6 m (steep faces to the harbour)

  python ds_volcano.py   -> plateau_data/disneysea_volcano.json (2 m grid, heights
                            relative to the promenade datum) + summary
"""
import json, math, pathlib, sys
import numpy as np
import cv2

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ds_levels as LV

OUT = ROOT / "plateau_data" / "disneysea_volcano.json"
BBOX = (-150.0, -175.0, 45.0, 5.0)        # x0, y0, x1, y1 (local m)
STEP = 2.0
SUMMIT = (-50.0, -111.0)                  # OSM POI プロメテウス火山
SUMMIT_Z = 51.0                           # above the promenade datum
RIM_H, RIM_D, RIM_W = 20.0, 22.0, 12.0    # rim crest height above plateau, distance from lagoon shore, width
CONE_R = 48.0
APRON, APRON_W = 6.0, 10.0                # caldera floor band along the lagoon, blend width
EDGE_W = 6.0
PLATEAU_MIN = 3.5                         # DEM (rel) above which a cell belongs to the plateau
KEEP_PATH, KEEP_BLDG = 3.0, 1.5


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def build():
    lev = LV.levels()  # committed levels JSON (--relevel: recompute from the raw OSM); also sets LV.DATUM
    x0, y0, x1, y1 = BBOX
    nx, ny = int((x1 - x0) / STEP) + 1, int((y1 - y0) / STEP) + 1
    xs = x0 + np.arange(nx) * STEP
    ys = y0 + np.arange(ny) * STEP
    base = np.array([[LV.dem(x, y) for x in xs] for y in ys])          # filled DEM, relative

    def to_px(pts):
        return np.array([[(x - x0) / STEP, (y - y0) / STEP] for x, y in pts], np.float32)

    def raster_poly(rings, buf=0.0):
        m = np.zeros((ny, nx), np.uint8)
        for r in rings:
            cv2.fillPoly(m, [np.round(to_px(r)).astype(np.int32)], 1)
        if buf > 0:
            k = int(math.ceil(buf / STEP)) * 2 + 1
            m = cv2.dilate(m, np.ones((k, k), np.uint8))
        return m

    def raster_lines(lines, buf):
        m = np.zeros((ny, nx), np.uint8)
        for l in lines:
            cv2.polylines(m, [np.round(to_px(l)).astype(np.int32)], False, 1, thickness=max(1, int(round(2 * buf / STEP))))
        return m

    water = json.loads((ROOT / "plateau_data" / "disneysea_water.json").read_text(encoding="utf-8"))
    lagoon = next(b for b in water["bodies"] if b["id"].endswith("_lagoon"))
    lag = raster_poly([lagoon["ring"]])
    harbor_cut = raster_poly([b["ring"] for b in water["bodies"] if b["cut"] and not b["id"].endswith("_lagoon")])

    # plateau: connected component of DEM >= PLATEAU_MIN that contains the summit, minus open water
    plat = ((base >= PLATEAU_MIN) & (harbor_cut == 0)).astype(np.uint8)
    n, lab = cv2.connectedComponents(plat | lag)
    si, sj = int((SUMMIT[1] - y0) / STEP), int((SUMMIT[0] - x0) / STEP)
    plat = ((lab == lab[si, sj]) & (lag == 0)).astype(np.uint8)

    # keep-clear masks: ground-level paths on the plateau, buildings
    osm = {w["id"]: w for w in json.loads((ROOT / "plateau_data" / "disneysea_osm.json").read_text(encoding="utf-8"))["ways"]}
    walk = []
    for wid, v in lev["ways"].items():
        w = osm.get(int(wid))
        if not w or v["kind"] not in ("ground", "bridge", "steps"):
            continue
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in w["pts"]) and max(v["z"]) >= 3.0:
            walk.append(w["pts"])
    keep = raster_lines(walk, KEEP_PATH)
    bl = [w["pts"] for w in osm.values() if "building" in w["tags"] and w["closed"]
          and all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in w["pts"])]
    keep |= raster_poly(bl, KEEP_BLDG)

    # distance fields (metres)
    d_lag = cv2.distanceTransform((1 - lag).astype(np.uint8), cv2.DIST_L2, 5) * STEP
    d_edge = cv2.distanceTransform(plat, cv2.DIST_L2, 5) * STEP
    d_keep = cv2.distanceTransform((1 - keep).astype(np.uint8), cv2.DIST_L2, 5) * STEP
    X, Y = np.meshgrid(xs, ys)
    d_sum = np.hypot(X - SUMMIT[0], Y - SUMMIT[1])

    plateau_z = np.where(plat > 0, base, 0.0)
    peak_above = SUMMIT_Z - float(base[si, sj])
    cone = peak_above * np.clip(1 - d_sum / CONE_R, 0, 1) ** 1.25
    rim = RIM_H * np.exp(-((d_lag - RIM_D) / RIM_W) ** 2)
    h = np.maximum(cone, rim)
    h *= _smooth((d_lag - APRON) / APRON_W)          # caldera floor along the lagoon
    h *= _smooth(d_edge / EDGE_W)                    # taper into the plateau edge
    h *= _smooth(d_keep / 4.0)                       # paths and buildings stay clear
    h *= plat
    z = plateau_z + h
    z[lag > 0] = np.nan                              # lagoon: water, not rock

    zmax = float(np.nanmax(z))
    k = np.unravel_index(np.nanargmax(z), z.shape)
    over_lagoon = int(((h > 0.5) & (lag > 0)).sum())
    res = {"x0": x0, "y0": y0, "step": STEP, "nx": nx, "ny": ny,
           "z": [None if not np.isfinite(v) else round(float(v), 2) for v in z.ravel()],
           "rock": [int(v) for v in (h > 0.3).ravel()],
           "h": [round(float(v), 2) for v in h.ravel()],            # rock height above the plateau (flat draft uses this)
           "summit": {"x": round(float(xs[k[1]]), 1), "y": round(float(ys[k[0]]), 1), "z": round(zmax, 1)},
           "params": {"summit_z": SUMMIT_Z, "rim_h": RIM_H, "rim_d": RIM_D, "cone_r": CONE_R, "apron": APRON},
           "plateau_cells": int(plat.sum()), "rock_cells": int((h > 0.3).sum())}
    OUT.write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    print(f"[volcano] {OUT.name}: grid {nx}x{ny} @ {STEP} m, plateau {plat.sum() * STEP * STEP:.0f} m2, "
          f"rock {(h > 0.3).sum() * STEP * STEP:.0f} m2, summit {zmax:.1f} m at ({xs[k[1]]:.0f},{ys[k[0]]:.0f}), "
          f"rock cells over lagoon: {over_lagoon}, kept-clear paths {len(walk)} buildings {len(bl)}")
    return res


def contours(res, interval=2.0):
    """Marching-squares contours of the massif (relative m) -> {level: [x1,y1,x2,y2,...]}."""
    nx, ny, st, x0, y0 = res["nx"], res["ny"], res["step"], res["x0"], res["y0"]
    g = np.array([np.nan if v is None else v for v in res["z"]], float).reshape(ny, nx)
    rock = np.array(res["rock"]).reshape(ny, nx) > 0
    g = np.where(np.isfinite(g), g, 0.0)
    out = {}
    lv = interval * math.ceil(6.0 / interval)        # start above the plateau so only rock is drawn
    while lv < np.max(g):
        segs = []
        a, b, c, d = g[:-1, :-1], g[:-1, 1:], g[1:, 1:], g[1:, :-1]
        cells = np.argwhere(((a > lv) | (b > lv) | (c > lv) | (d > lv)) & ~((a > lv) & (b > lv) & (c > lv) & (d > lv))
                            & (rock[:-1, :-1] | rock[1:, 1:]))
        for i, j in cells:
            vs = [((i, j), g[i, j]), ((i, j + 1), g[i, j + 1]), ((i + 1, j + 1), g[i + 1, j + 1]), ((i + 1, j), g[i + 1, j])]
            pts = []
            for q in range(4):
                (p1, v1), (p2, v2) = vs[q], vs[(q + 1) % 4]
                if (v1 > lv) != (v2 > lv):
                    t = (lv - v1) / (v2 - v1)
                    pts.append((x0 + (p1[1] + (p2[1] - p1[1]) * t) * st, y0 + (p1[0] + (p2[0] - p1[0]) * t) * st))
            for q in range(0, len(pts) - 1, 2):
                segs += [round(pts[q][0], 1), round(pts[q][1], 1), round(pts[q + 1][0], 1), round(pts[q + 1][1], 1)]
        if segs:
            out[str(round(lv, 1))] = segs
        lv += interval
    return out


if __name__ == "__main__":
    build()
