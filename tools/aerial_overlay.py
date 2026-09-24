"""Overlay the mock's data on the GSI aerial photo, to check positions by eye (no Blender needed).

  python tools/aerial_overlay.py X0 Y0 X1 Y1 [OUT.jpg] [--z 18]

X0 Y0 X1 Y1 is the box in local metres (origin 35.6267N 139.8851E, +X east, +Y north). Reads the data
embedded in output/disneysea/tds_outline.html; tiles are cached in plateau_data/gsi_photo/ (git-ignored).
Drawn: DisneySea buildings (coloured by land), Disneyland buildings, water, park boundaries, the Resort Line,
the entrance / Maihama layers. A 10 m grid is drawn when the box is small.
The photo predates Fantasy Springs (opened 2024): it cannot check that area.
"""
import io, json, math, pathlib, re, sys, urllib.request
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "plateau_data" / "gsi_photo"
URL = "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
COL = [(255, 170, 40), (230, 110, 80), (170, 190, 200), (60, 220, 220), (200, 120, 255), (255, 230, 60), (140, 230, 90), (255, 120, 200)]
DLCOL = [(255, 90, 120), (60, 230, 120), (255, 140, 60), (190, 240, 60), (200, 140, 255), (255, 210, 0), (80, 170, 255), (200, 200, 200)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    z = int(sys.argv[sys.argv.index("--z") + 1]) if "--z" in sys.argv else 18
    if "--z" in sys.argv:
        args.remove(sys.argv[sys.argv.index("--z") + 1])
    x0, y0, x1, y1 = map(float, args[:4])
    out = pathlib.Path(args[4]) if len(args) > 4 else ROOT / "aerial_overlay.jpg"
    page = (ROOT / "output" / "disneysea" / "tds_outline.html").read_text(encoding="utf-8")
    M = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S).group(1).replace(r"<\/", "</"))
    lat0, lon0 = M["origin"]

    def gp(x, y):
        lat, lon = y / 110574 + lat0, x / (111320 * math.cos(math.radians(lat0))) + lon0
        n = 2 ** z
        return ((lon + 180) / 360 * n * 256,
                (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n * 256)
    a, b = gp(x0, y1), gp(x1, y0)
    tx0, ty0, tx1, ty1 = int(a[0] // 256), int(a[1] // 256), int(b[0] // 256), int(b[1] // 256)
    CACHE.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            f = CACHE / f"{z}_{tx}_{ty}.jpg"
            if not f.exists():
                req = urllib.request.Request(URL.format(z=z, x=tx, y=ty), headers={"User-Agent": "tds-draft/1.0"})
                f.write_bytes(urllib.request.urlopen(req, timeout=30).read())
            img.paste(Image.open(f).convert("RGB"), ((tx - tx0) * 256, (ty - ty0) * 256))
    d = ImageDraw.Draw(img, "RGBA")
    P = lambda pts: [(gp(x, y)[0] - tx0 * 256, gp(x, y)[1] - ty0 * 256) for x, y in pts]
    ring = lambda r, c, w: d.line(P(r + [r[0]]), fill=c, width=w)
    DL, MH = M.get("disneyland"), M.get("maihama")
    for r in M["water"] + M["ponds"]: ring(r, (0, 200, 255, 255), 2)
    for b in M["buildings"]:
        for r in b["r"]: ring(r, COL[b["p"]] + (255,), 2)
    ring(M["park"], (255, 255, 255, 255), 3)
    if DL:
        for r in DL["water"]: ring(r, (0, 220, 255, 255), 2)
        for b in DL["buildings"]:
            for r in b["r"]: ring(r, DLCOL[b["p"]] + (255,), 2)
        ring(DL["park"], (255, 255, 255, 255), 3)
    if MH:
        for l in MH["loop"]: d.line(P(l), fill=(0, 255, 255, 255), width=3)
        for l in MH["jr"]: d.line(P(l), fill=(255, 0, 255, 255), width=3)
        for p in MH["places"]:
            for r in p["r"]: ring(r, (255, 255, 255, 255), 2)
    for l in M["rail"]: d.line(P(l), fill=(255, 0, 255, 255), width=3)
    if max(x1 - x0, y1 - y0) <= 250:
        for gx in range(int(x0 // 10) * 10, int(x1) + 1, 10): d.line(P([(gx, y0), (gx, y1)]), fill=(255, 255, 255, 200 if gx % 50 == 0 else 70), width=1)
        for gy in range(int(y0 // 10) * 10, int(y1) + 1, 10): d.line(P([(x0, gy), (x1, gy)]), fill=(255, 255, 255, 200 if gy % 50 == 0 else 70), width=1)
    A, B = P([(x0, y1)])[0], P([(x1, y0)])[0]
    img.crop((int(A[0]), int(A[1]), int(B[0]), int(B[1]))).save(out, quality=88)
    print("saved", out)


if __name__ == "__main__":
    main()
