"""Draco-compressed copies of the mock's 3D models for the page (output/disneysea/models/web/<id>.json).

  python src/compress_models.py            # every model that is newer than its compressed copy
  python src/compress_models.py --force    # all of them again

The models in output/disneysea/models/*.json stay as they are (plain glTF, buffer embedded): other scripts read them
(ds_ground.py rasterises their triangles, ds_tdl_hotel.py samples tdl_hotel_ground.json). The page loads the copies in
models/web/, compressed with gltf-transform (Node; `npx @gltf-transform/cli@4 draco`, fetched on first use): usually
90-95 % smaller. The buffer is embedded again as a data URI (the page is also served where only .json is allowed);
texture images stay beside the originals and the copies point one folder up to them. export_mock.py runs this.

The heaviest models also get a far copy (models/web/<id>_far.json, tools/lod/lod.mjs: small parts dropped, the rest
simplified): the page shows it until the camera comes near, so phones never hold every full model at once.
"""
import sys, json, base64, shutil, pathlib, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "output" / "disneysea" / "models"
WEB = MODELS / "web"
SKIP = {"woody"}                                        # the walker is loaded from its own Draco .glb
# models no script reads back and too big for git uncompressed (tdl_hotel is ~70 MB): only models/web/ is committed
# (.gitignore); regenerate the plain file with export_models.py before compressing again
WEB_ONLY = {"tdl_hotel", "tdl_world_bazaar", "tdl_plaza_buildings", "tdl_adventureland", "tdl_westernland"}
# models with a far copy (the castles, the AquaSphere and the volcano hardly shrink or lose their look: none)
LOD = {"tdl_hotel", "tdl_world_bazaar", "tdl_entrance", "tdl_plaza_buildings", "tdl_station", "tdl_adventureland", "tdl_westernland"}
LOD_TOOL = ROOT / "tools" / "lod"
# models with plant meshes (docs/plants/inventory.md): compressed again when the confirmed zones change (plant_zones.py)
PLANT_MODELS = {"plaza", "tdl_adv_ground", "tdl_adventureland", "tdl_entrance", "tdl_ground", "tdl_hotel", "tdl_hotel_ground",
                "tdl_land_ground", "tdl_plaza_buildings", "tdl_plaza_ground", "tdl_plaza_hub", "tdl_stitch_encounter",
                "tdl_tomorrowland_terrace", "tdl_water", "tdl_west_ground", "tdl_westernland", "tdl_world_bazaar",
                "tds_ground", "water", "bb_castle", "cinderella"}
ZONES = ROOT / "docs" / "plants" / "confirmed_zones.json"


def make_far(ids):
    """models/web/<id>_far.json for the ids whose far copy is missing or older than the web copy"""
    todo = [i for i in ids if not (WEB / f"{i}_far.json").exists()
            or (WEB / f"{i}_far.json").stat().st_mtime < (WEB / f"{i}.json").stat().st_mtime]
    if not todo:
        return
    npm, node = shutil.which("npm") or shutil.which("npm.cmd"), shutil.which("node")
    if not (npm and node):
        print("[lod] node/npm not found: no far copies (the page loads the full models)")
        return
    if not (LOD_TOOL / "node_modules").exists():
        subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=LOD_TOOL, check=True)
    r = subprocess.run([node, str(LOD_TOOL / "lod.mjs"), str(WEB), *todo], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join(l for l in (r.stdout or "").splitlines() if l.startswith("[lod]")) or (r.stderr or "")[-800:])


def bounds(path):
    """[min x, y, z, max x, y, z] of a glTF's meshes (POSITION accessor bounds + node translation), in glTF axes"""
    doc = json.loads(path.read_text(encoding="utf-8"))
    lo, hi = [1e9] * 3, [-1e9] * 3
    for n in doc.get("nodes", []):
        if "mesh" not in n:
            continue
        t = n.get("translation", [0, 0, 0])
        for prim in doc["meshes"][n["mesh"]]["primitives"]:
            a = doc["accessors"][prim["attributes"]["POSITION"]]
            if "min" in a:
                lo = [min(lo[k], a["min"][k] + t[k]) for k in range(3)]
                hi = [max(hi[k], a["max"][k] + t[k]) for k in range(3)]
    return [round(v, 1) for v in lo + hi] if lo[0] < 1e9 else None


def compress(src, dst):
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("npx (Node.js) not found: the page falls back to the uncompressed models")
    doc0 = json.loads(src.read_text(encoding="utf-8"))
    try:                                                  # the plants outside the confirmed zones go (plant_zones.py; the plain file stays whole)
        import plant_zones
        uri = doc0["buffers"][0].get("uri", "") if doc0.get("buffers") else ""
        if uri.startswith("data:"):
            doc0, blob, st = plant_zones.filter_doc(doc0, base64.b64decode(uri.split(",", 1)[1]))
            if st:
                doc0["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(blob).decode("ascii")
                print(f"[compress] {src.stem}: plants outside the zones (kept / taken out) " +
                      ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(st.items())))
    except Exception as e:
        print(f"[compress] {src.stem}: zone filter skipped ({e})")
    with tempfile.TemporaryDirectory() as td:
        tmp_in = pathlib.Path(td) / "in.gltf"
        for im in doc0.get("images", []):                 # images: copied beside the input so the relative URIs resolve
            if "uri" in im and not im["uri"].startswith("data:"):
                shutil.copy(MODELS / im["uri"], pathlib.Path(td) / im["uri"])
        tmp_in.write_text(json.dumps(doc0), encoding="utf-8")
        (pathlib.Path(td) / "out").mkdir()
        out = pathlib.Path(td) / "out" / "out.gltf"
        r = subprocess.run([npx, "--yes", "@gltf-transform/cli@4", "draco", str(tmp_in), str(out), "--quantize-position", "16"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
        if r.returncode != 0 or not out.exists():
            raise RuntimeError((r.stderr or "")[-800:] or (r.stdout or "")[-800:])
        doc = json.loads(out.read_text(encoding="utf-8"))
        for b in doc.get("buffers", []):                   # embed the (one) .bin again
            if "uri" in b and not b["uri"].startswith("data:"):
                raw = (out.parent / b["uri"]).read_bytes()
                b["uri"] = "data:application/octet-stream;base64," + base64.b64encode(raw).decode("ascii")
        for i, im in enumerate(doc.get("images", [])):     # images: back to the originals, one folder up
            orig = doc0["images"][i].get("uri") if i < len(doc0.get("images", [])) else None
            if orig and not orig.startswith("data:"):
                im.pop("bufferView", None); im["uri"] = "../" + orig
    dst.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")


def run(ids=None, force=False):
    WEB.mkdir(parents=True, exist_ok=True)
    done = {}
    for src in sorted(MODELS.glob("*.json")):
        name = src.stem
        if name in SKIP or (ids is not None and name not in ids):
            continue
        dst = WEB / src.name
        stale = dst.exists() and (dst.stat().st_mtime < src.stat().st_mtime or
                                  (name in PLANT_MODELS and ZONES.exists() and dst.stat().st_mtime < ZONES.stat().st_mtime))
        if force or not dst.exists() or stale:
            try:
                compress(src, dst)
                print(f"[compress] {name}: {src.stat().st_size / 1e6:.1f} MB -> {dst.stat().st_size / 1e6:.2f} MB")
            except Exception as e:                        # keep going: the page uses the plain file for this one
                print(f"[compress] {name}: FAILED ({e})")
                if dst.exists():
                    dst.unlink()
        if dst.exists():
            done[name] = f"models/web/{src.name}"
    for dst in sorted(WEB.glob("*.json")):                # models kept only compressed in git (WEB_ONLY): no plain file here
        if dst.stem not in done and not dst.stem.endswith("_far") and (ids is None or dst.stem in ids):
            done[dst.stem] = f"models/web/{dst.name}"
    make_far([i for i in done if i in LOD])
    return done


if __name__ == "__main__":
    run(force="--force" in sys.argv)
