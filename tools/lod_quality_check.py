"""Check the quality steps (resolution and full models, QUALITY / lodTick in mock_template.html) in headless Chromium on this PC's GPU.

  python tools/lod_quality_check.py              # PC screen (mouse)
  python tools/lod_quality_check.py --phone      # iPhone 13 screen (touch)

1. Full models at the Land entrance: how many of the 5 models with a far copy are held full (at most the cap).
2. Slow frames: every frame is made 40 ms slower; the step must go down to the lowest, with the pixel ratio, reach and cap of that step.
3. Idle: frames fast again but nothing drawn every frame; the step must not change.
4. Fast frames while drawing: the step must come back up to 0, never going down on the way.
5. Leaving: the camera 1.5 km away; the full models are freed (far copies only) and the GPU holds fewer geometries.
The page is patched in memory only (to reach `three` and slow the frames); nothing on disk changes. Needs: pip install playwright.
"""
import json, subprocess, sys, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent / "output" / "disneysea"
PORT = 8792
PHONE = "--phone" in sys.argv
FAR_IDS = ["tdl_station", "tdl_entrance", "tdl_world_bazaar", "tdl_hotel", "tdl_plaza_buildings"]
THREE_LINE = "const three = { ready: false, active: false, animated: [], dirty: true, inputAt: 0 };"

# slow every frame by window.__slow ms (once per frame), and while window.__busy keep the page drawing every frame
INIT_JS = """
(() => {
  const raf = window.requestAnimationFrame.bind(window);
  let lastT = -1;
  window.__slow = 0; window.__busy = false;
  window.requestAnimationFrame = cb => raf(t => {
    if (t !== lastT) { lastT = t; if (window.__slow) { const e = performance.now() + window.__slow; while (performance.now() < e); }
                       if (window.__busy && window.__three) __three.dirty = true; }
    cb(t);
  });
})();
"""


def state(page):
    return page.evaluate("""() => { const L = TDS_LOD(), S = TDS_STATS();
      const full = Object.entries(L.models).filter(([id, v]) => v !== 'far').map(([id]) => id);
      return { level: L.quality ? L.quality.level : null, median: L.quality ? L.quality.median : null, pixelRatio: +S.pixelRatio.toFixed(3),
               reach: L.reach ?? null, cap: L.cap ?? null, full, geometries: S.geometries, textures: S.textures }; }""")


def watch(page, seconds, until=None):
    """sample the state every 0.5 s; stop early when until(state) holds"""
    seen = []
    for _ in range(int(seconds * 2)):
        page.wait_for_timeout(500)
        s = state(page); seen.append(s["level"])
        if until and until(s): break
    return s, seen


def focus_on(page, mid, dist):
    page.evaluate("([id, d]) => { const b = __three.models[id].box; TDS_FOCUS((b[0] + b[3]) / 2, -(b[2] + b[5]) / 2, 0, d); }", [mid, dist])


def main():
    from playwright.sync_api import sync_playwright
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    ok = True
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
                assert THREE_LINE in body, "the page changed: update the patch in lod_quality_check.py"
                route.fulfill(response=r, body=body.replace(THREE_LINE, THREE_LINE + " window.__three = three;"))
            page.route("**/tds_outline.html", patch)
            page.goto(f"http://localhost:{PORT}/tds_outline.html")
            page.wait_for_function("() => window.__three && __three.ready", timeout=120000)
            page.evaluate("TDS_SKIP()")
            page.wait_for_timeout(8000)
            new = state(page)["level"] is not None
            print("page:", "with quality steps" if new else "before the change (no quality steps)")

            # 1. full models at the Land entrance, drawing every frame at the page's own speed
            page.evaluate("() => { __busy = true; }")
            focus_on(page, "tdl_entrance", 80)
            s, seen = watch(page, 25)
            full = [i for i in s["full"] if i in FAR_IDS]
            print("1. entrance:", json.dumps({"fullModels": full, "cap": s["cap"], "reach": s["reach"], "level": s["level"],
                                                "medianFrameMs": s["median"], "pixelRatio": s["pixelRatio"]}))
            if not new:
                print("page errors:", errs[:5] or "none"); b.close(); return
            ok &= len(full) <= s["cap"]

            # 2. slow frames: down to the lowest step
            page.evaluate("() => { __slow = 40; }")
            s, seen = watch(page, 30, lambda s: s["level"] == 3)
            downs = [x for i, x in enumerate(seen) if i and x != seen[i - 1]]
            print("2. slow:", json.dumps({"levels": downs, **{k: s[k] for k in ("level", "median", "pixelRatio", "reach", "cap")}, "fullModels": s["full"]}))
            ok &= s["level"] == 3 and all(seen[i] >= seen[i - 1] for i in range(1, len(seen)))
            ok &= len([i for i in s["full"] if i in FAR_IDS]) <= s["cap"]

            # 3. idle: fast frames but nothing drawn every frame, the step stays
            page.evaluate("() => { __busy = false; __slow = 0; }")
            s, seen = watch(page, 10)
            print("3. idle:", json.dumps({"levels": sorted(set(seen))}))
            ok &= set(seen) == {3}

            # 4. fast frames while drawing: back up to 0, never down on the way
            page.evaluate("() => { __busy = true; }")
            s, seen = watch(page, 60, lambda s: s["level"] == 0)
            ups = [x for i, x in enumerate(seen) if i and x != seen[i - 1]]
            print("4. fast:", json.dumps({"levels": ups, "seconds": len(seen) / 2, **{k: s[k] for k in ("level", "median", "pixelRatio", "reach", "cap")}}))
            ok &= s["level"] == 0 and all(seen[i] <= seen[i - 1] for i in range(1, len(seen)))

            # 5. leaving: 1.5 km away, the full models are freed
            before = state(page)
            focus_on(page, "volcano", 300)
            s, _ = watch(page, 10)
            gone = [i for i in s["full"] if i in FAR_IDS]
            print("5. away:", json.dumps({"fullModelsBefore": [i for i in before["full"] if i in FAR_IDS], "fullModelsAfter": gone,
                                           "geometries": [before["geometries"], s["geometries"]], "textures": [before["textures"], s["textures"]]}))
            ok &= not gone and s["geometries"] < before["geometries"]

            print("page errors:", errs[:5] or "none")
            ok &= not errs
            b.close()
    finally:
        srv.terminate()
    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
