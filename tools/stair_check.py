"""Draw the neighbourhood of a stair to decide which way it goes up (no Blender, no aerial photo needed).

  python tools/stair_check.py sea|land WAY_ID [OUT.png] [--r 45]

Background: the GSI DEM5A (raw pixels coloured by height, voids - buildings, water - grey hatched).
On top: buildings (outlines, names), water, walls/fences, paths (bridges orange, tunnels dashed blue),
the other stairs as arrows pointing up (as the committed levels have them, basis in the label) and the
stair being checked in red with S (start) and E (end). Heights at each end of the ground paths are printed.
"""
import json, math, pathlib, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_levels as LV  # noqa: E402

PX = 8  # pixels per metre


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    r = float(sys.argv[sys.argv.index("--r") + 1]) if "--r" in sys.argv else 45.0
    if "--r" in sys.argv:
        args.remove(sys.argv[sys.argv.index("--r") + 1])
    park, sid = args[0], int(args[1])
    out = pathlib.Path(args[2]) if len(args) > 2 else ROOT / f"stair_{sid}.png"
    fn = {"sea": "disneysea", "land": "disneyland"}[park]
    O = json.loads((ROOT / "plateau_data" / f"{fn}_osm.json").read_text(encoding="utf-8"))
    L = json.loads((ROOT / "plateau_data" / f"{fn}_levels.json").read_text(encoding="utf-8"))
    sea = json.loads((ROOT / "plateau_data" / "disneysea_levels.json").read_text(encoding="utf-8"))
    LV.DATUM = sea.get("datum_exact", sea["datum_m"])   # both parks share the DisneySea datum
    ways = {w["id"]: w for w in O["ways"]}
    st = ways[sid]
    cx = sum(p[0] for p in st["pts"]) / len(st["pts"]); cy = sum(p[1] for p in st["pts"]) / len(st["pts"])
    W = int(2 * r * PX)
    img = Image.new("RGB", (W, W + 40), (255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    to = lambda x, y: ((x - cx + r) * PX, (cy - y + r) * PX)

    # DEM: colour by height (-2.5 .. +3.5 m), voids hatched
    lo, hi = -2.5, 3.5
    for py in range(0, W, 4):
        for px in range(0, W, 4):
            x, y = cx - r + (px + 2) / PX, cy + r - (py + 2) / PX
            i, j = LV._pix(x, y)
            if LV._RAW_VALID[int(round(i)), int(round(j))]:
                t = min(1, max(0, (LV.dem(x, y) - lo) / (hi - lo)))
                col = (int(40 + 215 * t), int(90 + 120 * (1 - abs(t - 0.5) * 2)), int(255 - 215 * t))
            else:
                col = (205, 205, 205) if (px + py) // 4 % 4 else (170, 170, 170)
            d.rectangle([px, py, px + 3, py + 3], fill=col)
    # DEM values every 5 m (raw pixels only)
    for gy in range(int(-r) // 5 * 5, int(r) + 1, 5):
        for gx in range(int(-r) // 5 * 5, int(r) + 1, 5):
            x, y = cx + gx, cy + gy
            i, j = LV._pix(x, y)
            if LV._RAW_VALID[int(round(i)), int(round(j))]:
                d.text(to(x, y), f"{LV.dem(x, y):.1f}", fill=(0, 0, 0), font=font)

    def line(pts, **kw):
        if len(pts) > 1:
            d.line([to(*p) for p in pts], **kw)
    near = lambda w: any(abs(p[0] - cx) < r + 20 and abs(p[1] - cy) < r + 20 for p in w["pts"])
    for w in O["ways"]:
        if not near(w):
            continue
        t = w["tags"]
        if t.get("natural") == "water":
            d.polygon([to(*p) for p in w["pts"]], outline=(0, 60, 200))
        elif "building" in t or "building:part" in t:
            line(w["pts"] + [w["pts"][0]], fill=(90, 40, 20), width=2)
            if t.get("name"):
                d.text(to(*w["pts"][0]), t["name"][:24], fill=(90, 40, 20), font=font)
        elif t.get("barrier") in ("wall", "fence", "retaining_wall", "hedge"):
            line(w["pts"], fill=(120, 0, 120), width=1)
    for w in O["ways"]:
        t = w["tags"]
        if "highway" not in t or not near(w) or w["id"] == sid:
            continue
        if t["highway"] == "steps":
            s = L["stairs"].get(str(w["id"]))
            pts = w["pts"] if not s or s["up"] == "end" else w["pts"][::-1]
            line(pts, fill=(0, 120, 0), width=5)
            a, b = to(*pts[-2]), to(*pts[-1])
            d.ellipse([b[0] - 6, b[1] - 6, b[0] + 6, b[1] + 6], fill=(0, 120, 0))
            d.text((b[0] + 7, b[1]), f"{w['id']} {s['basis'] if s else '?'}", fill=(0, 90, 0), font=font)
            continue
        col = (230, 120, 0) if (t.get("bridge") or int(t.get("layer", "0").split(";")[0] or 0) > 0) else \
              (0, 90, 255) if (t.get("tunnel") or t.get("layer", "0").startswith("-")) else (40, 40, 40)
        line(w["pts"], fill=col, width=3)
        z = L["ways"].get(str(w["id"]), {}).get("z")
        if z:
            for k in (0, -1):
                d.text(to(*w["pts"][k]), f"{z[k]:.2f}", fill=col, font=font)
    line(st["pts"], fill=(230, 0, 0), width=6)
    for lab, p in (("S", st["pts"][0]), ("E", st["pts"][-1])):
        q = to(*p)
        d.ellipse([q[0] - 8, q[1] - 8, q[0] + 8, q[1] + 8], outline=(230, 0, 0), width=3)
        d.text((q[0] + 10, q[1] - 12), lab, fill=(230, 0, 0), font=font)
    s = L["stairs"][str(sid)]
    d.text((6, W + 4), f"{park} {sid} {st['tags']}  len {s['len']} m, now: up={s['up']} ({s['basis']})", fill=(0, 0, 0), font=font)
    d.text((6, W + 20), f"DEM colour {lo}..{hi} m (blue low, red high), grey = no DEM; green arrows point up; grid 5 m, {2 * r:.0f} m wide",
           fill=(0, 0, 0), font=font)
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
