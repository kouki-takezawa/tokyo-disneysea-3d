"""A preview of the rebuilt Bon Voyage and gateway cupola on their own, before they go into the main mock.

  python tools/bv_mock.py      # -> output/disneysea/models/bv_mock.json (glTF), shown by output/disneysea/bv_mock.html

Builds the gateway model (src/ds_tdl_gateway.py), keeps the triangles near Bon Voyage and the cupola (with the deck, the stairs and
the ground between them), moves them to a local origin, and stores camera viewpoints like the user's photos in the scene's extras.
"""
import sys, math, pathlib

import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import shapely

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_tdl_gateway as GW
import ds_tdl_ground as G
import ds_disneyland as DL

OUT = ROOT / "output" / "disneysea" / "models" / "bv_mock.json"


def main():
    P, T, M, ZD = GW.build()
    ring = [tuple(p) for p in DL.WAYS[GW.BV_WAY]["pts"]]
    poly = Polygon(ring[:-1] if ring[0] == ring[-1] else ring).buffer(0.6, join_style=2).buffer(-0.6, join_style=2).simplify(0.4)
    cup = [Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"] if "キューポラ" in w["tags"].get("name", "")][0]
    keep = unary_union([poly.buffer(45), cup.buffer(28), poly.centroid.buffer(1).union(cup.centroid.buffer(1)).convex_hull.buffer(22)])
    shapely.prepare(keep)
    o = poly.centroid
    ox, oy, oz = o.x, o.y, ZD
    out = {}
    for name, m in M.items():
        k = G.Mesh(name)
        for tri, nrm in zip(m.tris, m.nrm):
            c = tri.mean(0)
            if keep.contains(Point(c[0], c[1])):
                k.add(tri - np.array([ox, oy, oz]), nrm)
        if k.tris:
            out[name] = k
    n = G.write_gltf(OUT, out)

    # viewpoints (plan x, y, z -> glTF x, z, -y), like the photos
    def V(x, y, z):
        return [round(x - ox, 2), round(z - oz, 2), round(-(y - oy), 2)]
    hb, d, v, _ = GW.hat_frame(P, poly)
    p_nw = Point(hb.x - d[0] * 52, hb.y - d[1] * 52)          # on the deck at the north-west end of the shop, looking along it
    p_se = Point(hb.x - d[0] * 5, hb.y - d[1] * 5)
    zg = float(T.z(hb.x, hb.y))
    cen = poly.centroid
    if np.dot(v, [cen.x - hb.x, cen.y - hb.y]) > 0:
        v = -v                                                     # v points away from the shop
    c = cup.centroid
    lsc = min((l for l, _ in P["dlines"] if l.length > 40), key=lambda l: l.distance(c))
    tc = lsc.project(c)
    q0, q1 = lsc.interpolate(max(0, tc - 8)), lsc.interpolate(min(lsc.length, tc + 8))
    dc = np.array([q1.x - q0.x, q1.y - q0.y]); dc /= np.linalg.norm(dc)
    if dc[0] < 0:
        dc = -dc
    views = {
        "bv": {"label": "ボン・ヴォヤージュ(歩道橋から)", "eye": V(p_nw.x, p_nw.y, ZD + 2.2), "target": V(p_se.x, p_se.y, ZD + 4.5)},
        "hatbox": {"label": "帽子箱(下の道から)", "eye": V(hb.x + d[0] * 26 + v[0] * 14, hb.y + d[1] * 26 + v[1] * 14, zg + 1.7),
                   "target": V(hb.x, hb.y, zg + 7.0)},
        "inside": {"label": "帽子箱の中の通路", "eye": V(hb.x - d[0] * (GW.HB_D / 2 + 4), hb.y - d[1] * (GW.HB_D / 2 + 4), ZD + 1.6),
                   "target": V(hb.x + d[0] * 8, hb.y + d[1] * 8, ZD + 3.0)},
        "cupola": {"label": "キューポラ(舞浜駅側から)", "eye": V(c.x - dc[0] * 22, c.y - dc[1] * 22, ZD + 1.7), "target": V(c.x, c.y, ZD + 6.0)},
        "aerial": {"label": "上から", "eye": V(o.x + 60, o.y - 70, ZD + 55), "target": V((o.x + c.x) / 2, (o.y + c.y) / 2, ZD)},
    }
    import json
    doc = json.loads(OUT.read_text())
    doc["scenes"][0]["extras"] = {"views": views}
    OUT.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"[bv_mock] {OUT.name}: {n} triangles, {OUT.stat().st_size / 1024:.0f} KB; meshes {sorted(out)}")


if __name__ == "__main__":
    main()
