"""Check the walk's collision grid (buildGrid in mock_template.html) in headless Chromium on this PC's GPU.

  python tools/walk_grid_check.py              # PC screen (mouse)
  python tools/walk_grid_check.py --phone      # iPhone 13 screen (touch)

1. Equivalence: at 6 places, the grid built only near the walker (GRID_R) and the whole-park grid give the same
   feet heights, surface heights, wall stops and camera hits for 3000 random samples within 90 m.
2. Load: enter the walk at the default start, then run 3 s at a time, keeping a heading while it gets somewhere; prints every grid built at once (ms), long tasks,
   the JS heap, how far the walker went (path and from the start), and page errors. Then glides from World Bazaar to
   Cinderella Castle at running speed and checks a new grid is built (over frames) every GRID_MOVE m, the walker never
   gets past GRID_EDGE from the grid in use, and nothing freezes.
The page is patched in memory only (to reach the grid functions); nothing on disk changes. Needs: pip install playwright.
"""
import json, math, random, subprocess, sys, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent / "output" / "disneysea"
PORT = 8791
PHONE = "--phone" in sys.argv
PLACES = ["tdl_station", "tdl_world_bazaar", "tdl_hotel", "cinderella", "aquasphere", "volcano"]
SAMPLES, RADIUS = 3000, 90

GRID_LINE = "const GRID_R = 120, GRID_MOVE = 50, GRID_EDGE = 95, GRID_MS = 8;"
HOOK = ("let GRID_R = 120; const GRID_MOVE = 50, GRID_EDGE = 95, GRID_MS = 8; window.__gb = []; window.__gdone = []; window.__grid = { get wk() { return wk; }, setR: v => { GRID_R = v; }, "
        "build: () => { grid = null; buildGrid(); }, modelHits: (x, z) => modelHits(x, z), groundAt: (x, z, y) => groundAt(x, z, y), "
        "hitsWall: (...a) => hitsWall(...a), camHit: (...a) => camHit(...a), size: () => grid ? grid.tris.length / 9 : 0, off: () => gridC ? Math.hypot(wk.x - gridC[0], wk.z - gridC[1]) : 1e9 };")

SAMPLE_JS = """
([cx, cz, pts]) => {
  const G = __grid, out = [];
  for (const [dx, dz, y, sx, sz, cy] of pts) {
    const x = cx + dx, z = cz + dz;
    const hs = G.modelHits(x, z).map(v => +v.toFixed(3)).sort((a, b) => a - b);
    const g = G.groundAt(x, z, y);
    out.push([hs.join(","), g == null ? "null" : g.toFixed(3), G.hitsWall(x, z, x + sx, z + sz, y) ? 1 : 0,
              G.camHit(x, z, y + 1.5, x + sx * 4, z + sz * 4, y + 1.5 + cy).toFixed(4)]);
  }
  return out;
}
"""


def main():
    from playwright.sync_api import sync_playwright
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    ok = True
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--enable-precise-memory-info"])
            ctx = b.new_context(**p.devices["iPhone 13"]) if PHONE else b.new_context(viewport={"width": 1600, "height": 900})
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))

            def patch(route):
                r = route.fetch(); body = r.text()
                a = "const three = { ready: false, active: false, animated: [], dirty: true, inputAt: 0 };"
                assert a in body and GRID_LINE in body, "the page changed: update the patch in walk_grid_check.py"
                body = body.replace(a, a + " window.__three = three;").replace(GRID_LINE, HOOK)
                body = body.replace("  function buildGrid() {", "  function buildGrid() { const __t = performance.now(); try { return buildGrid0(); } "
                                    "finally { __gb.push(Math.round(performance.now() - __t)); } }\n  function buildGrid0() {", 1)
                done = "gridKey = key; gridC = [gx, gz];"
                assert done in body, "the page changed: update the patch in walk_grid_check.py"
                body = body.replace(done, done + " __gdone.push(Math.round(performance.now()));")
                route.fulfill(response=r, body=body)
            page.route("**/tds_outline.html", patch)
            page.goto(f"http://localhost:{PORT}/tds_outline.html")
            page.evaluate("() => { window.__lt = []; new PerformanceObserver(l => l.getEntries().forEach(e => __lt.push(Math.round(e.duration)))).observe({ entryTypes: ['longtask'] }); }")
            page.wait_for_function("() => window.__three && __three.ready", timeout=120000)
            page.evaluate("TDS_SKIP()")
            page.wait_for_timeout(8000)

            # 2. load: enter the walk and move
            page.evaluate("() => { __lt.length = 0; __gb.length = 0; }")
            page.evaluate("TDS_WALK()")
            page.wait_for_function("() => window.__grid && __three.walking", timeout=60000)
            page.wait_for_timeout(6000)
            start = page.evaluate("TDS_WALK_STATE()")
            heap, path, prev = [], 0.0, start
            rnd = random.Random(1)
            yaw, far = rnd.uniform(0, 2 * math.pi), 0.0
            for i in range(24):   # run 3 s at a time (keys straight into the walker's key set); keep the heading while it gets somewhere
                page.evaluate("yaw => { __grid.wk.yaw = yaw; __grid.wk.keys.add('KeyW'); __grid.wk.keys.add('ShiftLeft'); }", yaw)
                page.wait_for_timeout(3000)
                page.evaluate("() => __grid.wk.keys.clear()")
                cur = page.evaluate("TDS_WALK_STATE()")
                step = math.hypot(cur["x"] - prev["x"], cur["y"] - prev["y"]); path += step; prev = cur
                far = max(far, math.hypot(cur["x"] - start["x"], cur["y"] - start["y"]))
                if step < 8: yaw = rnd.uniform(0, 2 * math.pi)
                heap.append(page.evaluate("performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1e6) : null"))
            end = prev
            load = {"gridBuildsMs": page.evaluate("__gb"), "longtasksOver200ms": sorted([x for x in page.evaluate("__lt") if x > 200], reverse=True),
                    "heapMB": heap, "pathM": round(path, 1), "farthestM": round(far, 1), "fromStartM": round(math.hypot(end["x"] - start["x"], end["y"] - start["y"]), 1),
                    "feetZ": [round(start["z"], 2), round(end["z"], 2)]}
            print("load:", json.dumps(load))
            # glide at running speed (6 m/s, walls ignored) from World Bazaar to Cinderella Castle: new grids every GRID_MOVE m,
            # built over frames; the walker must never get further than GRID_EDGE (+ a frame's step) from the grid in use
            page.evaluate("TDS_WALK(0, 0)")
            page.wait_for_timeout(1000)
            glide = page.evaluate("""async () => {
              const c = id => { const b = __three.models[id].box; return [(b[0] + b[3]) / 2, (b[2] + b[5]) / 2]; };
              const [ax, az] = c('tdl_world_bazaar'), [bx, bz] = c('cinderella'), L = Math.hypot(bx - ax, bz - az);
              TDS_WALK(ax, -az); await new Promise(r => setTimeout(r, 6000));
              __gb.length = 0; __gdone.length = 0; __lt.length = 0; const t0 = performance.now();
              let d = 0, last = t0, maxOff = 0;
              while (d < L) {
                await new Promise(r => requestAnimationFrame(r));
                const now = performance.now(); d = Math.min(L, d + 6 * Math.min(0.25, (now - last) / 1000)); last = now;
                __grid.wk.x = ax + (bx - ax) * d / L; __grid.wk.z = az + (bz - az) * d / L;
                maxOff = Math.max(maxOff, __grid.off());
              }
              await new Promise(r => setTimeout(r, 3000));
              return { lengthM: Math.round(L), seconds: +((performance.now() - t0) / 1000).toFixed(1), gridsBuilt: __gdone.length,
                       atOnceMs: [...__gb], maxOffM: +maxOff.toFixed(1), longtasksOver200ms: __lt.filter(x => x > 200) };
            }""")
            print("glide:", json.dumps(glide))
            ok &= glide["gridsBuilt"] >= glide["lengthM"] // 50 and glide["maxOffM"] <= 97
            # 1. equivalence at each place
            for pid in PLACES:
                box = page.evaluate("id => __three.models[id] && __three.models[id].box", pid)
                if not box:
                    print(f"{pid}: no model"); ok = False; continue
                cx, cz = (box[0] + box[3]) / 2, (box[2] + box[5]) / 2
                page.evaluate("([x, z]) => TDS_WALK(x, -z)", [cx, cz])
                page.wait_for_timeout(9000)   # the full models nearby load
                page.evaluate("() => __grid.wk.keys.clear()")
                r = random.Random(pid)
                pts = []
                for _ in range(SAMPLES):
                    a, d = r.uniform(0, 6.2832), RADIUS * r.random() ** 0.5
                    pts.append([d * math.cos(a), d * math.sin(a), r.uniform(-3, 40), r.uniform(-1.5, 1.5), r.uniform(-1.5, 1.5), r.uniform(-1, 3)])
                page.evaluate("() => { __grid.setR(120); __grid.build(); }")
                wx, wz = page.evaluate("() => [__grid.wk.x, __grid.wk.z]")
                near_n = page.evaluate("__grid.size()")
                near = page.evaluate(SAMPLE_JS, [wx, wz, pts])
                page.evaluate("() => { __grid.setR(Infinity); __grid.build(); }")
                full_n = page.evaluate("__grid.size()")
                full = page.evaluate(SAMPLE_JS, [wx, wz, pts])
                page.evaluate("() => { __grid.setR(120); __grid.build(); }")
                diff = [i for i in range(SAMPLES) if near[i] != full[i]]
                kinds = [sum(1 for i in diff if near[i][k] != full[i][k]) for k in range(4)]
                ok &= not diff
                print(f"{pid}: grid tris near {near_n:.0f} / whole {full_n:.0f}; differing samples {len(diff)} "
                      f"(surfaces {kinds[0]}, feet {kinds[1]}, walls {kinds[2]}, camera {kinds[3]})")
            print("page errors:", errs[:5] or "none")
            ok &= not errs
            b.close()
    finally:
        srv.terminate()
    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
