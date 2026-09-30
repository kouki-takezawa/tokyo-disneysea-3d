"""Check the page's weight fixes in headless Chromium on this PC's GPU (2026-09-30).

  python tools/perf_check.py              # PC screen (mouse)
  python tools/perf_check.py --phone      # iPhone 13 screen (touch; the CPU 4x slower while the page opens)
  python tools/perf_check.py --shots DIR  # also save the harbour view as DIR/harbour_<pc|phone>.png

1. Opening: the time the water script takes (it parses the page data once and leaves the label maths for the plan view),
   and no layer lines built while every layer is off.
2. Walk, standing still: draws a second (the idle rate, not every frame), then walking: every frame.
3. Refraction (transmission draws the whole scene twice): only the Disney Sea / Land water on a PC at quality step 0;
   none on a phone, none on a PC once the quality has stepped down to 2 or lower; the castle bell never.
4. Key 2 (wire + models): the layer lines are built then and shown.
The page is patched in memory only (to reach `three`, time the water script and slow the frames); nothing on disk changes.
Needs: pip install playwright.
"""
import json, subprocess, sys, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent / "output" / "disneysea"
PORT = 8796
PHONE = "--phone" in sys.argv
SHOTS = pathlib.Path(sys.argv[sys.argv.index("--shots") + 1]) if "--shots" in sys.argv else None
THREE_LINE = "const three = { ready: false, active: false, animated: [], dirty: true, inputAt: 0 };"
EXT_OPEN = "<script id=\"ext-water\">"
EXT_END = "window.TDS_EXT = {\r\n"

INIT_JS = """
(() => {
  const raf = window.requestAnimationFrame.bind(window);
  let lastT = -1;
  window.__slow = 0;
  window.requestAnimationFrame = cb => raf(t => {
    if (t !== lastT) { lastT = t; if (window.__slow) { const e = performance.now() + window.__slow; while (performance.now() < e); } }
    cb(t);
  });
})();
"""
TRANSMISSIVE = "() => { const n = []; __three.scene.traverse(o => { if (o.isMesh && o.visible && o.material && o.material.transmission > 0) n.push(o.name); }); return n; }"
LINES = "() => { let n = 0, v = 0; __three.root.traverse(o => { if (o.isLineSegments && o.parent === __three.root) { n++; if (o.visible) v++; } }); return [n, v]; }"


def main():
    from playwright.sync_api import sync_playwright
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    ok, out = True, {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
            ctx = b.new_context(**p.devices["iPhone 13"]) if PHONE else b.new_context(viewport={"width": 1600, "height": 900})
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.add_init_script(INIT_JS)

            def patch(route):
                r = route.fetch(); body = r.text()
                for s in (THREE_LINE, EXT_OPEN, EXT_END):
                    assert s in body, "the page changed: update the patch in perf_check.py (" + s.strip() + ")"
                body = body.replace(THREE_LINE, THREE_LINE + " window.__three = three;")
                body = body.replace(EXT_OPEN, EXT_OPEN + "window.__e0 = performance.now();", 1)
                body = body.replace(EXT_END, "window.__extMs = performance.now() - window.__e0; " + EXT_END, 1)
                route.fulfill(response=r, body=body)
            page.route("**/tds_outline.html", patch)
            cdp = ctx.new_cdp_session(page)
            if PHONE: cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            page.goto(f"http://localhost:{PORT}/tds_outline.html")
            page.wait_for_function("() => window.__three && __three.ready", timeout=180000)
            if PHONE: cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
            lines = page.evaluate(LINES)
            out["1_opening"] = {"waterScriptMs": round(page.evaluate("__extMs")), "lineObjects": lines[0]}
            ok &= lines[0] <= 2   # the park outline and the grid only

            page.evaluate("TDS_SKIP()"); page.wait_for_timeout(9000)
            page.evaluate("TDS_WALK()"); page.wait_for_timeout(6000)
            rate = lambda: (lambda d0: (page.wait_for_timeout(3000), (page.evaluate("__three.draws") - d0) / 3)[1])(page.evaluate("__three.draws"))
            idle = rate()
            page.keyboard.down("KeyW"); page.wait_for_timeout(500); moving = rate(); page.keyboard.up("KeyW")
            out["2_walk"] = {"idleDrawsPerSec": round(idle, 1), "walkingDrawsPerSec": round(moving, 1)}
            ok &= (12 if PHONE else 18) <= idle <= (21 if PHONE else 31) and moving > idle * 1.1

            page.keyboard.press("Escape"); page.wait_for_timeout(2500)
            page.evaluate("() => TDS_FOCUS(-60, -40, 0, 420)"); page.wait_for_timeout(3000)
            page.evaluate("() => { __three.dirty = true; }"); page.wait_for_timeout(500)
            tr = page.evaluate(TRANSMISSIVE)
            out["3_refraction"] = {"transmissive": tr, "calls": page.evaluate("TDS_STATS().calls"), "level": page.evaluate("TDS_STATS().quality.level")}
            ok &= "BC_bell" not in tr and (not tr if PHONE else set(tr) <= {"WS_water"} and len(tr) > 0)
            if SHOTS:
                SHOTS.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(SHOTS / f"harbour_{'phone' if PHONE else 'pc'}.png"))
            if not PHONE:   # slow frames: down to step 3, the water loses its refraction
                page.evaluate("() => { __slow = 40; }")
                for _ in range(60):
                    page.evaluate("() => { __three.dirty = true; }"); page.wait_for_timeout(500)
                    if page.evaluate("TDS_STATS().quality.level") >= 2: break
                page.evaluate("() => { __slow = 0; }"); page.wait_for_timeout(300)
                tr2 = page.evaluate(TRANSMISSIVE)
                out["3_refraction"]["afterSlowFrames"] = {"level": page.evaluate("TDS_STATS().quality.level"), "transmissive": tr2}
                ok &= not tr2

            page.keyboard.press("Digit2"); page.wait_for_timeout(1500)
            lines = page.evaluate(LINES)
            out["4_key2"] = {"lineObjects": lines[0], "visible": lines[1]}
            ok &= lines[0] > 20 and lines[1] > 10
            out["errors"] = errs[:5]
            ok &= not errs
            b.close()
    finally:
        srv.terminate()
    print(json.dumps(out, ensure_ascii=False))
    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
