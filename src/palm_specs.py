"""Palms as specs, grown in the page (docs/plants/plan.md, phase 3).

The model scripts no longer build palm meshes. Where a palm stands they leave a MARKER: one triangle in the palm's trunk
mesh (base on the ground, the crown's centre, and a tag point whose height above the base gives the kind), so it goes
through every frame, parent and ground lift of the export exactly as the old palm did. collect() (export_mock.py runs
it before the Draco copies are made) reads the markers out of the plain models/<id>.json, takes those meshes out of the
model and keeps the palms in models/palms.json:

  {"<model id>": [[x, y, ground, height, crown dx, crown dy, kind], ...], ...}     (mock metres, y north; kind 0 canary,
                                                                                   1 washingtonia)

The page (plants.js) grows every palm from its spec, its shape from a seed made from its position. A model that is not
exported again keeps its palms in palms.json (its JSON has no markers left to read).

  python src/palm_specs.py            # collect from every model JSON (export_mock.py does this itself)
"""
import json, base64, math, pathlib, re, struct

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "output" / "disneysea" / "models"
OUT = MODELS / "palms.json"
KINDS = ("canary", "washi")
MESH = re.compile(r"^(AD_palmt|AD_palml|PB_pb_trunk|PB_pb_leaf|WZ_wbz_palm_trunk|WZ_wbz_palm_leaf)$")


def marker(x, y, z, h, dx, dy, kind):
    """The marker triangle (x east, y north, z up): the base, the crown (h up, leaning dx, dy), the tag (5 cm east of
    the base, 0.1 m per kind index + 0.1 up)."""
    k = KINDS.index(kind)
    return [(x, y, z), (x + dx, y + dy, z + h), (x + 0.05, y, z + 0.1 * (k + 1))]


def _accessor(doc, blob, i):
    a = doc["accessors"][i]; bv = doc["bufferViews"][a["bufferView"]]
    fmt = {5126: "f", 5125: "I", 5123: "H", 5121: "B"}[a["componentType"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    size = struct.calcsize(fmt)
    stride = bv.get("byteStride") or size * n
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return [struct.unpack_from("<" + fmt * n, blob, off + k * stride) for k in range(a["count"])]


def _decode(doc, blob, mesh):
    """The palms of a marker mesh in mock coordinates, or None if the mesh is not markers (an old palm model)."""
    out = []
    for prim in mesh["primitives"]:
        P = _accessor(doc, blob, prim["attributes"]["POSITION"])
        I = [v[0] for v in _accessor(doc, blob, prim["indices"])] if "indices" in prim else list(range(len(P)))
        if len(I) % 3:
            return None
        for t in range(0, len(I), 3):
            v = sorted((P[I[t + k]] for k in range(3)), key=lambda p: p[1])   # glTF y is up: base, tag, crown
            base, tag, top = v
            h = top[1] - base[1]
            lift = tag[1] - base[1]
            if h < 2.0 or abs(math.hypot(tag[0] - base[0], tag[2] - base[2]) - 0.05) > 0.01 or lift < 0.05 or lift > 0.25:
                return None
            k = round(lift / 0.1) - 1
            out.append([round(base[0], 2), round(-base[2], 2), round(base[1], 2), round(h, 2),
                        round(top[0] - base[0], 2), round(-(top[2] - base[2]), 2), k])
    return out


def collect(ids=None):
    """Read and strip the markers of the models (all with a JSON when ids is None); update palms.json. Returns it."""
    specs = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    files = [MODELS / f"{i}.json" for i in ids] if ids else sorted(MODELS.glob("*.json"))
    for f in files:
        if not f.exists() or f.name == OUT.name:
            continue
        txt = f.read_text(encoding="utf-8")
        if not any(m in txt for m in ("palmt", "palml", "pb_trunk", "pb_leaf", "palm_trunk", "palm_leaf")):
            continue
        doc = json.loads(txt)
        nodes = [n for n in doc.get("nodes", []) if "mesh" in n and MESH.match(doc["meshes"][n["mesh"]].get("name") or n.get("name", ""))]
        if not nodes:
            continue
        uri = doc["buffers"][0].get("uri", "")
        if not uri.startswith("data:"):
            print(f"[palms] {f.name}: buffer not embedded, skipped"); continue
        blob = base64.b64decode(uri.split(",", 1)[1])
        palms, ok = [], True
        for n in nodes:
            got = _decode(doc, blob, doc["meshes"][n["mesh"]])
            if got is None:
                ok = False; break
            palms += got
        if not ok:
            print(f"[palms] {f.name}: palm meshes are not markers (an old export?) -- left as they are"); continue
        for n in nodes:
            del n["mesh"]                       # the marker meshes go (the nodes stay as empties)
        f.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
        specs[f.stem] = palms
        print(f"[palms] {f.name}: {len(palms)} palms read, their markers taken out")
    for k, v in specs.items():                  # two markers within a metre (a planter too short for two) are one palm
        keep = []
        for p in v:
            if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 1.0 for q in keep):
                keep.append(p)
        specs[k] = keep
    OUT.write_text(json.dumps(specs, separators=(",", ":")), encoding="utf-8")
    return specs


if __name__ == "__main__":
    s = collect()
    print({k: len(v) for k, v in s.items()})
