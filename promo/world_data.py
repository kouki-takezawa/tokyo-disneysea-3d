"""The data of the picture-book world in the promo film: both parks, simplified from the mock's own data.

    python promo/world_data.py    # output/disneysea/mock_data.json -> promo/world.json

Everything keeps the mock's coordinates (metres; +x east, +y north; origin near Mediterranean Harbor), so the parks,
the water, the buildings and the landmarks sit where they really are. Only the shapes are simplified (the book draws them
as paper). Needs shapely 2.1 or later (as src/ds_ground.py).
"""
import json
import math
from pathlib import Path

from shapely.geometry import MultiPoint, Point, Polygon
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "output" / "disneysea" / "mock_data.json"
OUT = Path(__file__).resolve().parent / "world.json"


def ring(pts, tol):
    """A simplified outer ring, rounded to 0.1 m (None when it collapses)."""
    try:
        p = make_valid(Polygon(pts)).buffer(0)
    except Exception:
        return None
    if p.is_empty:
        return None
    if p.geom_type != "Polygon":
        p = max(p.geoms, key=lambda g: g.area)
    p = p.simplify(tol, preserve_topology=True)
    if p.is_empty or p.area < 1:
        return None
    return [[round(x, 1), round(y, 1)] for x, y in list(p.exterior.coords)[:-1]]


def polys(lst, tol, min_area=0):
    out = []
    for pts in lst:
        if len(pts) < 3 or Polygon(pts).area < min_area:
            continue
        r = ring(pts, tol)
        if r and len(r) >= 3:
            out.append(r)
    return out


def main():
    d = json.loads(SRC.read_text())
    dl = d["disneyland"]
    castle = max(dl["buildings"], key=lambda b: b["h"])   # Cinderella Castle, the tallest building in Tokyo Disneyland (51 m)
    cc = Polygon(castle["r"][0]).centroid
    bazaar = next(l for l in dl["labels"] if l["n"] == "ワールドバザール")

    def buildings(bs, park, skip=None):
        out = []
        for b in bs:
            r = ring(b["r"][0], 0.8)
            if not r or len(r) < 3:
                continue
            a = Polygon(r).area
            if a < 8:
                continue
            if skip and Polygon(r).centroid.distance(skip[0]) < skip[1]:
                continue
            h = min(b["h"], 2 * math.sqrt(a) + 2)   # thin towers (lamps, masts, spires) kept low: tall posts on paper read as sticks
            out.append({"r": r, "h": round(h, 1), "p": b["p"], "k": park})
        return out

    # the volcano: each 2 m contour as a ring of 48 radii around the summit (the widest point in each direction)
    s = d["volcano"]["summit"]
    layers = []
    for z, flat in sorted(d["volcano"]["contours"].items(), key=lambda kv: float(kv[0])):
        z = float(z)
        if z % 2:
            continue
        pts = [(flat[i] - s["x"], flat[i + 1] - s["y"]) for i in range(0, len(flat) - 1, 2)]
        bins = [0.0] * 48
        for x, y in pts:
            a = int((math.atan2(y, x) + math.pi) / (2 * math.pi) * 48) % 48
            bins[a] = max(bins[a], math.hypot(x, y))
        if not any(bins):
            continue
        for _ in range(3):   # fill directions with no points from their neighbours
            bins = [b or max(bins[i - 1], bins[(i + 1) % 48]) for i, b in enumerate(bins)]
        for _ in range(2):   # soften the outline
            bins = [(bins[i - 1] + 2 * bins[i] + bins[(i + 1) % 48]) / 4 for i in range(48)]
        layers.append({"z": z, "r": [round(b, 1) for b in bins]})

    # trees: a few points inside the tree areas of both parks
    trees = []
    for lst in (d["trees"], dl["trees"]):
        for pts in lst:
            if len(pts) < 3:
                continue
            p = make_valid(Polygon(pts))
            if p.area < 60:
                continue
            n = min(4, max(1, int(p.area / 900)))
            c = p.representative_point()
            trees.append([round(c.x, 1), round(c.y, 1)])
            if n > 1:
                minx, miny, maxx, maxy = p.bounds
                k = 0
                for i in range(40):
                    q = Point(minx + (maxx - minx) * ((i * 0.618) % 1), miny + (maxy - miny) * ((i * 0.382) % 1))
                    if p.contains(q):
                        trees.append([round(q.x, 1), round(q.y, 1)])
                        k += 1
                        if k >= n - 1:
                            break

    ship = next(l for l in d["landmarks"] if l["t"] == "ship")
    mermaid = next(l for l in d["landmarks"] if l["t"] == "dome")
    world = {
        "tds": ring(d["park"], 1.5),
        "tdl": ring(dl["park"], 1.5),
        "water": polys(d["water"] + dl["water"], 1.2, 30),
        "islands": polys(d["islands"], 1.0, 20),
        "green": polys(d["green"] + dl["green"], 1.0, 150),
        "buildings": buildings(d["buildings"], "s") + buildings(dl["buildings"], "l", (cc, 34)),
        "trees": trees,
        "volcano": {"x": s["x"], "y": s["y"], "z": s["z"], "layers": layers},
        "aquasphere": {"x": d["aquasphere"]["cx"], "y": d["aquasphere"]["cy"]},
        "mermaid": {"x": mermaid["x"], "y": mermaid["y"], "r": mermaid["r"]},
        "ship": [[round(x, 1), round(y, 1)] for x, y in ship["r"]],
        "castle": {"x": round(cc.x, 1), "y": round(cc.y, 1), "h": castle["h"], "face": [bazaar["x"], bazaar["y"]]},
        "tot": {"x": 292.5, "y": -303.0},
        "labels": [{"n": l["n"], "x": l["x"], "y": l["y"]} for l in d["labels"] + dl["labels"]],
        "harbor": {"x": 150, "y": -20},
    }
    OUT.write_text(json.dumps(world, ensure_ascii=False, separators=(",", ":")))
    print(OUT, OUT.stat().st_size, "bytes;", len(world["buildings"]), "buildings,", len(world["water"]), "water,", len(trees), "trees,", len(layers), "volcano layers")


if __name__ == "__main__":
    main()
