"""Render the promo film (promo/promo.html) frame by frame into an MP4.

The page draws each frame from the time alone (PROMO.frameAt(ms)), so the film comes out the same however slow the machine is.
Serves the repository over a local HTTP server (the page reads output/disneysea/mock_data.json), drives headless Chromium with Playwright, pipes the screenshots into ffmpeg,
and lays the music (promo/music.py) under it.

    pip install playwright imageio-ffmpeg numpy
    python promo/music.py                             # -> promo/music.m4a
    python promo/record.py                            # -> promo/promo.mp4 (1920x1080, 30 fps, about 50 s)
    python promo/record.py --stills 3,8,15,30   # only a few frames as JPEG, to check the look

--three FILE serves three.min.js from a local file (for machines that cannot reach cdn.jsdelivr.net).
"""
import argparse
import functools
import http.server
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "promo" / "promo.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--start", type=float, default=0, help="seconds")
    ap.add_argument("--end", type=float, default=None, help="seconds (default: the whole film)")
    ap.add_argument("--stills", default="", help="comma-separated seconds: write JPEG stills instead of the film")
    ap.add_argument("--three", default="", help="a local three.min.js (0.147.0) to serve instead of the CDN")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--proxy-fonts", action="store_true", help="fetch the web fonts in Python instead of the browser")
    ap.add_argument("--chromium", default="", help="a Chromium executable, when Playwright's own browser is not installed")
    a = ap.parse_args()

    srv = serve()
    url = f"http://127.0.0.1:{srv.server_address[1]}/promo/promo.html?record"
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=a.chromium or None, args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = br.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        pg.on("console", lambda m: m.type in ("error", "warning") and print("[page]", m.text, file=sys.stderr))
        pg.on("requestfailed", lambda r: print("[request failed]", r.url, r.failure, file=sys.stderr))
        pg.on("pageerror", lambda e: print("[page error]", e, file=sys.stderr))
        if a.three:
            body = Path(a.three).read_bytes()
            pg.route(THREE_URL, lambda route: route.fulfill(body=body, content_type="application/javascript"))
        ua = pg.evaluate("navigator.userAgent")

        def fetch(route):   # web fonts through Python's own HTTPS (its CA store), for a browser that does not trust the local proxy
            try:
                req = urllib.request.Request(route.request.url, headers={"User-Agent": ua})
                with urllib.request.urlopen(req, timeout=60) as res:
                    route.fulfill(status=res.status, body=res.read(), headers={"content-type": res.headers.get("content-type", ""), "access-control-allow-origin": "*"})
            except Exception as e:
                print("[font fetch failed]", route.request.url, e, file=sys.stderr)
                route.continue_()

        if a.proxy_fonts:
            pg.route("https://fonts.googleapis.com/**", fetch)
            pg.route("https://fonts.gstatic.com/**", fetch)
        pg.goto(url)
        pg.wait_for_function("document.body.dataset.ready === '1'", timeout=600_000)
        dur = pg.evaluate("PROMO.duration") / 1000

        def shot(sec):
            pg.evaluate(f"PROMO.frameAt({sec * 1000})")
            return pg.screenshot(type="jpeg", quality=95)

        if a.stills:
            out = Path(a.out).with_suffix("")
            out.parent.mkdir(parents=True, exist_ok=True)
            for s in a.stills.split(","):
                f = Path(f"{out}_{float(s):05.1f}s.jpg")
                f.write_bytes(shot(float(s)))
                print(f)
            br.close()
            return

        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        end = a.end if a.end is not None else dur
        music = ROOT / "promo" / "music.m4a"
        cmd = [ff, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(a.fps), "-c:v", "mjpeg", "-i", "-"]
        if music.exists():
            cmd += ["-ss", f"{a.start:.3f}", "-i", str(music), "-c:a", "copy", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = round((end - a.start) * a.fps)
        for i in range(n):
            enc.stdin.write(shot(a.start + i / a.fps))
            if i % a.fps == 0:
                print(f"\r{a.start + i / a.fps:5.1f} / {end:.1f} s", end="", flush=True)
        enc.stdin.close()
        enc.wait()
        print(f"\n{out}")
        br.close()
    srv.shutdown()


if __name__ == "__main__":
    main()
