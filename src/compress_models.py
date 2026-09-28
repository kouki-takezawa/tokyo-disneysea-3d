"""Draco-compressed copies of the mock's 3D models for the page (output/disneysea/models/web/<id>.json).

  python src/compress_models.py            # every model that is newer than its compressed copy
  python src/compress_models.py --force    # all of them again

The models in output/disneysea/models/*.json stay as they are (plain glTF, buffer embedded): other scripts read them
(ds_ground.py rasterises their triangles, ds_tdl_hotel.py samples tdl_hotel_ground.json). The page loads the copies in
models/web/, compressed with gltf-transform (Node; `npx @gltf-transform/cli@4 draco`, fetched on first use): usually
90-95 % smaller. The buffer is embedded again as a data URI (the page is also served where only .json is allowed);
texture images stay beside the originals and the copies point one folder up to them. export_mock.py runs this.
"""
import sys, json, base64, shutil, pathlib, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "output" / "disneysea" / "models"
WEB = MODELS / "web"
SKIP = {"woody"}                                        # the walker is loaded from its own Draco .glb
# models no script reads back and too big for git uncompressed (tdl_hotel is ~70 MB): only models/web/ is committed
# (.gitignore); regenerate the plain file with export_models.py before compressing again
WEB_ONLY = {"tdl_hotel", "tdl_world_bazaar", "tdl_plaza_buildings"}


def compress(src, dst):
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("npx (Node.js) not found: the page falls back to the uncompressed models")
    doc0 = json.loads(src.read_text(encoding="utf-8"))
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
        if force or not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
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
        if dst.stem not in done and (ids is None or dst.stem in ids):
            done[dst.stem] = f"models/web/{dst.name}"
    return done


if __name__ == "__main__":
    run(force="--force" in sys.argv)
