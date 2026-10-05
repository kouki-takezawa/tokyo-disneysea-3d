/* plants.js -- trees, palms and grass grown in the page (docs/plants/plan.md).

   Every tree is its own: the shape comes from a seed made from its position (space colonisation grows the branches
   towards points scattered in the crown of its kind, or whorls of branches for the conifers), so no two are alike and
   the same tree always comes back the same. Every tree of mock_data's trees3d (OSM and the beds' trees) is grown here,
   its kind picked from the area it stands in (docs/plants/species.md). The shapes are built in Web Workers, nearest
   first, and merged into a few meshes per block (all kinds share one leaf atlas and one bark atlas):
     near  (cell of 40 m, within QUALITY.near)    the whole tree: branches down to 3 cm, leaf spray cards on the twigs
     mid   (block of 80 m, within QUALITY.mid)    the same tree: limbs only, fewer and larger clump cards facing out
     far   (block of 320 m)                       the same tree again, low: trunk and main limbs, two clump cards a lump
   A mid block hides its cells that show near, a far block the cells that show near or mid (a mask per block, the
   vertices thrown off-screen). Until a far block is built, the mock's old instanced trees stand in (ctx.hideOld).
   Leaves: alpha-tested cards (alphaToCoverage), normals bent towards the crown's ellipsoid (soft shading), light through
   the leaves when the sun is behind them, colour varied per tree and per card, darker inside the crown, wind in the
   vertex shader (one smooth field per tree, so twigs and their leaves move together).
   Phase 1 (2026-10-05): the generator, the trial round the entrance (one broadleaf kind, one palm, a lawn patch).
   Phase 2 (2026-10-05): every kind of species.md, every tree, the mid and far levels lighter and merged per block.
   Phase 3 (2026-10-05): palms and bamboo. The models' palms are specs now (src/palm_specs.py: mock_data's palms3d, the
   position, ground, height, lean and kind); they and the palms / bamboo of MIX are grown here: canary palms, washingtonias
   with their skirts, bamboo clumps (the palm atlas, palm_atlas.webp).
   The plants are in a group named "plants": the water's refraction pass (renderBufferDirect patch) leaves them out. */
(function () {
"use strict";
const TEX = "tex/plants/";
const CELL = 40, MID = 80, FAR = 320, MPER = MID / CELL, FPER = FAR / CELL;   // 2 x 2 cells a mid block, 8 x 8 a far one

/* ---------- quality: high / mid / low, picked from the device, ?q= forces one ---------- */
const QUALITY = {
  high: { near: 55, mid: 150, cards: 1.0, farScale: 1.0, farMax: 1e9, workers: 3, grass: 26, grassDensity: 1.0 },
  mid:  { near: 34, mid: 100, cards: 0.7, farScale: 1.2, farMax: 900, workers: 2, grass: 15, grassDensity: 0.5 },
  low:  { near: 22, mid: 65,  cards: 0.5, farScale: 1.4, farMax: 600, workers: 1, grass: 9,  grassDensity: 0.3 },
};
function pickQuality() {
  let q = null;
  try { q = new URLSearchParams(location.search).get("q"); } catch (e) { /* no URL API */ }
  if (QUALITY[q]) return { name: q, forced: true };
  const coarse = matchMedia("(pointer: coarse)").matches;
  const cores = navigator.hardwareConcurrency || 4, mem = navigator.deviceMemory || 4;
  return { name: coarse ? (cores >= 6 && mem >= 4 ? "mid" : "low") : (cores >= 4 ? "high" : "mid"), forced: false };
}

/* ---------- where a tree stands -> its kind (docs/plants/species.md) ---------- */
const WBA = 25 * Math.PI / 180, WB0 = [-521.3, 891.2];   // the World Bazaar frame (ds_tdl_entrance.WB)
const toWB = (x, y) => { const dx = x - WB0[0], dy = y - WB0[1]; return [dx * Math.cos(WBA) + dy * Math.sin(WBA), -dx * Math.sin(WBA) + dy * Math.cos(WBA)]; };
const fromWB = (u, v) => [WB0[0] + u * Math.cos(WBA) - v * Math.sin(WBA), WB0[1] + u * Math.sin(WBA) + v * Math.cos(WBA)];
function inEntrance(x, y) {
  if (x > -640 && x < -430 && y > 800 && y < 990) return true;          // the entrance box (export_mock.py's tall evergreens)
  const [u, v] = toWB(x, y);
  return u > 55 && u < 110 && v > -125 && v < -60;                      // outside the east exit: the big spreading trees
}
const TRIAL_LAWN = { x: -518, y: 925, r: 46 };                          // the lawns inside the entrance plaza's arc
const LANDS = ["wb", "adventureland", "westernland", "critter", "fantasyland", "toontown", "tomorrowland"];   // DL.labels[].p
const ZONES = [   // places inside a land with their own planting (video v2 times in species.md)
  { n: "plaza", x: -439, y: 713, r: 85 },    // the hub: zelkova-type woods round the north and east, a camphor or two
  { n: "snow", x: -334, y: 600, r: 45 },     // north-west of the castle: pines and firs with light deciduous trees
  { n: "belle", x: -622, y: 497, r: 80 },    // Belle's village: dense firs, a few light deciduous trees
];
const MIX = {   // kind -> share, per area (palm = canary palm, washi = washingtonia, take = bamboo clump: phase 3)
  wb:            { kusu: 1 },
  adventureland: { kusu: 0.425, keyaki: 0.13, washi: 0.22, palm: 0.18, take: 0.045 },   // v2 0:09:20 .. 0:13:30
  westernland:   { matsu: 0.6, kusu: 0.4 },
  critter:       { katsura: 0.55, matsu: 0.25, kusu: 0.2 },
  fantasyland:   { kusu: 0.5, katsura: 0.25, momi: 0.25 },
  belle:         { momi: 0.65, katsura: 0.35 },
  snow:          { matsu: 0.35, momi: 0.35, keyaki: 0.3 },
  plaza:         { keyaki: 0.6, kusu: 0.4 },
  toontown:      { keyaki: 0.35, matsu: 0.3, momi: 0.35 },
  tomorrowland:  { sakura: 0.45, itosugi: 0.35, kusu: 0.2 },
  tds:           { kusu: 0.3, kasamatsu: 0.25, itosugi: 0.15, keyaki: 0.12, palm: 0.12, washi: 0.06 },   // not seen on video: a guess (species.md)
  outside:       { kusu: 0.4, keyaki: 0.25, matsu: 0.25, sakura: 0.1 },        // Maihama's streets, the hotels, the car parks
};
function pip(x, y, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
function areaOf(x, y, A) {
  if (inEntrance(x, y)) return "wb";
  if (A.tdl && pip(x, y, A.tdl)) {
    for (const z of ZONES) if (Math.hypot(x - z.x, y - z.y) < z.r) return z.n;
    let best = "wb", bd = Infinity;
    for (const l of A.lands || []) { const d = Math.hypot(x - l.x, y - l.y); if (d < bd) { bd = d; best = LANDS[l.p] || "wb"; } }
    return best;
  }
  if (A.tds && pip(x, y, A.tds)) return "tds";
  return "outside";
}
const frac = h => (h >>> 0) / 4294967296;
const mixHash = h => { h = Math.imul(h ^ (h >>> 16), 0x45d9f3b); h = Math.imul(h ^ (h >>> 16), 0x45d9f3b); return (h ^ (h >>> 16)) >>> 0; };
function pickKind(mix, r) { let acc = 0; const ks = Object.keys(mix); for (const k of ks) { acc += mix[k]; if (r < acc) return k; } return ks[ks.length - 1]; }

/* ---------- the generator (runs in the workers; GEN.toString() is the workers' source) ---------- */
function GEN() {
  const lerp = (r, t) => r[0] + (r[1] - r[0]) * t;
  const mkRand = seed => { let s = (seed >>> 0) || 0x9e3779b9; return () => { s = (s ^ (s << 13)) >>> 0; s = (s ^ (s >>> 17)) >>> 0; s = (s ^ (s << 5)) >>> 0; return s / 4294967296; }; };
  /* presets (docs/plants/species.md). form: crown (space colonisation in lobes inside an envelope), pads (black pine:
     flat layered pads), umbrella (stone pine: one flat top), cone (whorls of branches, fir / cypress). row: the leaf atlas
     row (0 broadleaf evergreen, 1 deciduous, 2 pine, 3 conifer). barkK: 0 grey bark, 1 red pine bark. h: the height when
     the data has none. width: crown width / height. slots: cards round a twig tip, then 1, 2, 3 nodes back; under: extra
     cards facing down on the crown's lower half. midKeep: the share of twigs with a clump card in the mid copy. */
  const GREY = [0.42, 0.39, 0.35], PINE = [0.46, 0.33, 0.26];   // the bark atlas halves' mean colours (plain bark)
  const SP = {
    kusu:    { form: "crown", row: 0, barkK: 0, plain: GREY, h: [9, 14], crownBase: [0.13, 0.22], width: [1.0, 1.25], trunkR: 0.03, lean: [0.01, 0.05],
               lobes: [6, 9], lobeR: [0.42, 0.68], lobeY: 0.6, shell: 0.16, env: "ell", pts: 560, up: 0.06, droop: 0.02,
               card: [1.15, 1.5], slots: [5, 3, 2, 1], under: 2, midKeep: 0.3, tint: [0.62, 0.8, 0.46], bark: [0.95, 0.92, 0.88] },
    keyaki:  { form: "crown", row: 1, barkK: 0, plain: GREY, h: [10, 16], crownBase: [0.12, 0.2], width: [0.85, 1.1], trunkR: 0.024, lean: [0.0, 0.03],
               lobes: [6, 9], lobeR: [0.34, 0.52], lobeY: 0.62, shell: 0.3, env: "obo", pts: 430, up: 0.34, droop: 0.0,
               card: [1.0, 1.3], slots: [4, 2, 1, 1], under: 0, midKeep: 0.26, tint: [0.86, 0.94, 0.66], bark: [1.0, 0.98, 0.95] },
    katsura: { form: "crown", row: 1, barkK: 0, plain: GREY, h: [10, 14], crownBase: [0.13, 0.2], width: [0.55, 0.72], trunkR: 0.024, lean: [0.0, 0.01],
               lobes: [5, 7], lobeR: [0.4, 0.6], lobeY: 0.7, shell: 0.2, env: "ell", pts: 440, up: 0.26, droop: 0.0,
               card: [0.95, 1.25], slots: [4, 3, 1, 1], under: 1, midKeep: 0.28, tint: [0.9, 0.95, 0.62], bark: [1.18, 1.14, 1.06] },
    sakura:  { form: "crown", row: 1, barkK: 0, plain: GREY, h: [6, 9], crownBase: [0.25, 0.35], width: [1.2, 1.45], trunkR: 0.036, lean: [0.02, 0.07],
               lobes: [5, 8], lobeR: [0.38, 0.55], lobeY: 0.45, shell: 0.22, env: "ell", pts: 440, up: 0.02, droop: 0.05,
               card: [0.95, 1.25], slots: [5, 3, 2, 1], under: 1, midKeep: 0.3, tint: [0.66, 0.8, 0.5], bark: [0.72, 0.62, 0.6] },
    matsu:   { form: "pads", row: 2, barkK: 1, plain: PINE, h: [9, 15], crownBase: [0.42, 0.58], width: [0.75, 1.05], trunkR: 0.026, lean: [0.04, 0.12],
               lobes: [3, 5], lobeR: [0.3, 0.46], flat: 0.36, shell: 0.2, pts: 520, up: 0.16, droop: 0.0,
               card: [1.0, 1.35], slots: [5, 3, 2, 1], under: 1, midKeep: 0.32, tint: [0.88, 0.92, 0.82], bark: [1.0, 1.0, 1.0] },
    kasamatsu: { form: "umbrella", row: 2, barkK: 1, plain: PINE, h: [10, 15], crownBase: [0.6, 0.72], width: [1.0, 1.3], trunkR: 0.028, lean: [0.02, 0.07],
               lobes: [5, 7], lobeR: [0.3, 0.42], flat: 0.42, shell: 0.22, pts: 420, up: 0.3, droop: 0.0,
               card: [0.9, 1.2], slots: [4, 2, 1, 1], under: 1, midKeep: 0.32, tint: [0.82, 0.9, 0.76], bark: [1.05, 1.0, 0.95] },
    momi:    { form: "cone", row: 3, barkK: 1, plain: PINE, h: [11, 17], crownBase: [0.03, 0.08], width: [0.36, 0.46], trunkR: 0.022, lean: [0.0, 0.012],
               whorl: [0.38, 0.52], perWhorl: [5, 7], elev: [-0.3, -0.02], tipUp: 0.35, taper: 0.95,
               card: [0.85, 1.1], slots: [2, 1, 1], under: 0, midKeep: 0.22, tint: [0.6, 0.74, 0.66], bark: [0.9, 0.85, 0.82] },
    palm:    { form: "palm", h: [5, 9] },    // canary palm   (heights for the trees of MIX; the shapes: canary(), washi(), take())
    washi:   { form: "palm", h: [9, 14] },   // washingtonia
    take:    { form: "palm", h: [6, 9] },    // bamboo clump
    itosugi: { form: "cone", row: 3, barkK: 1, plain: PINE, h: [5, 9], crownBase: [0.03, 0.08], width: [0.17, 0.24], trunkR: 0.024, lean: [0.0, 0.01],
               whorl: [0.3, 0.42], perWhorl: [4, 6], elev: [0.95, 1.2], tipUp: 0.1, taper: 0.55,
               card: [0.6, 0.85], slots: [2, 1, 1], under: 0, midKeep: 0.3, tint: [0.66, 0.8, 0.58], bark: [0.9, 0.85, 0.82] },
  };
  class Buf {
    constructor() { this.p = []; this.n = []; this.t = []; this.c = []; this.s = []; this.k = []; this.i = []; this.v = 0; }
    vert(x, y, z, nx, ny, nz, u, v, r, g, b, w, ph, cell) {
      this.p.push(x, y, z); this.n.push(nx, ny, nz); this.t.push(u, v); this.c.push(r, g, b); this.s.push(w, ph); this.k.push(cell);
      return this.v++;
    }
    tri(a, b, c) { this.i.push(a, b, c); }
    out(transfer) {
      if (!this.v) return null;
      const col = new Uint8Array(this.c.length);
      for (let i = 0; i < col.length; i++) col[i] = Math.max(0, Math.min(255, Math.round(this.c[i] * 255)));
      const o = { pos: new Float32Array(this.p), nrm: new Float32Array(this.n), uv: new Float32Array(this.t), col,
                  sway: new Float32Array(this.s), cell: new Uint8Array(this.k),
                  idx: this.v > 65535 ? new Uint32Array(this.i) : new Uint16Array(this.i) };
      for (const k of ["pos", "nrm", "uv", "col", "sway", "cell", "idx"]) transfer.push(o[k].buffer);
      return o;
    }
  }
  const norm = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const CACHE = new Map();   // seed -> skeleton, for the near and mid copies of the trees round the viewer

  /* radii by the pipe model (r^2 of the parent = sum of the children's), then mapped so a twig tip is 1 cm and the
     trunk has the preset's size (the skeleton has far fewer tips than a real tree, so the plain model makes twigs fat) */
  function finish(S, rb) {
    const { X, Y, Z, par } = S, N = X.length, kids = Array.from({ length: N }, () => []);
    for (let n = 1; n < N; n++) kids[par[n]].push(n);
    if (S.smooth) for (let pass = 0; pass < 2; pass++) {   // smooth the zigzag of the growth (chains only)
      for (let n = 2; n < N; n++) {
        if (kids[n].length !== 1) continue;
        const p = par[n], c = kids[n][0];
        X[n] = X[n] * 0.5 + (X[p] + X[c]) * 0.25; Y[n] = Y[n] * 0.5 + (Y[p] + Y[c]) * 0.25; Z[n] = Z[n] * 0.5 + (Z[p] + Z[c]) * 0.25;
      }
    }
    const r = new Float32Array(N), tipDepth = new Int32Array(N);
    for (let n = N - 1; n >= 0; n--) {
      if (!kids[n].length) { r[n] = 1; tipDepth[n] = 0; continue; }
      let s = 0, td = 1e9; for (const c of kids[n]) { s += r[c] * r[c]; td = Math.min(td, tipDepth[c] + 1); }
      r[n] = Math.sqrt(s); tipDepth[n] = td;
    }
    const TIP = 0.01, gam = Math.log(rb / TIP) / Math.log(Math.max(2, r[0]));
    for (let n = 0; n < N; n++) r[n] = TIP * Math.pow(r[n], gam);
    for (let n = 0; n <= S.nT; n++) r[n] = Math.max(r[n], rb * (1.12 - 0.25 * n / S.nT));   // a sturdy trunk, flared at the foot
    const main = new Int32Array(N).fill(-1);
    for (let n = 0; n < N; n++) { let m = -1; for (const c of kids[n]) if (m < 0 || r[c] > r[m]) m = c; main[n] = m; }
    Object.assign(S, { kids, r, main, tipDepth, N });
    return S;
  }

  /* broadleaf and pine skeletons: a trunk to the crown's base, then space colonisation towards points in lobes / pads */
  function colonise(t, R, sp) {
    const H = t.h, cb = H * lerp(sp.crownBase, R()), W = H * lerp(sp.width, R()) * 0.5, ch = H - cb, cy = cb + ch * 0.5;
    const X = [], Y = [], Z = [], par = [];
    const D = Math.max(0.28, H * 0.03);
    const la = R() * 6.283, lean = lerp(sp.lean, R()) * H, kink = sp.form === "crown" ? 0 : (R() - 0.5) * 0.08 * H;
    const tx = Math.cos(la) * lean, tz = Math.sin(la) * lean;
    const nT = Math.max(2, Math.ceil(cb / D));
    for (let k = 0; k <= nT; k++) {   // pines: a trunk that bends back on itself a little
      const f = k / nT, kb = Math.sin(f * Math.PI) * kink;
      X.push(tx * f * f - Math.sin(la) * kb + (k ? (R() - 0.5) * 0.06 : 0)); Y.push(cb * f); Z.push(tz * f * f + Math.cos(la) * kb + (k ? (R() - 0.5) * 0.06 : 0)); par.push(k - 1);
    }
    // attraction points: lobes inside the crown's envelope (crown), flat pads in layers (pads), one flat top (umbrella)
    const nl = Math.round(lerp(sp.lobes, R())), lobes = [];
    for (let i = 0; i < nl; i++) {
      if (sp.form === "crown") {
        const a = R() * 6.283, r = Math.sqrt(R()) * W * 0.5;
        lobes.push([tx + Math.cos(a) * r, cy + (R() - 0.45) * ch * sp.lobeY, tz + Math.sin(a) * r, W * lerp(sp.lobeR, R()), 0.8]);
      } else if (sp.form === "pads") {
        const f = nl > 1 ? i / (nl - 1) : 1, a = R() * 6.283, r = W * (0.25 + R() * 0.5) * (1 - 0.55 * f);
        lobes.push([tx + Math.cos(a) * r, cb + ch * (0.12 + 0.8 * f) + (R() - 0.5) * 0.5, tz + Math.sin(a) * r, W * lerp(sp.lobeR, R()) * (1.15 - 0.4 * f), sp.flat]);
      } else {
        const a = R() * 6.283, r = Math.sqrt(R()) * W * 0.62;
        lobes.push([tx + Math.cos(a) * r, H - ch * (0.25 + R() * 0.3), tz + Math.sin(a) * r, W * lerp(sp.lobeR, R()), sp.flat]);
      }
    }
    const P = [];
    for (let tries = 0; P.length < sp.pts * 3 && tries < sp.pts * 40; tries++) {
      const L = lobes[Math.floor(R() * nl)];
      let dx = R() * 2 - 1, dy = R() * 2 - 1, dz = R() * 2 - 1; const dl = Math.hypot(dx, dy, dz);
      if (dl > 1 || dl < 1e-3) continue;
      const rr = L[3] * Math.pow(R(), sp.shell) / dl;   // shell < 1/3: more points near each lobe's surface (a dense skin)
      const x = L[0] + dx * rr, y = L[1] + dy * rr * L[4], z = L[2] + dz * rr;
      if (y < cb + 0.4 || y > H) continue;
      if (sp.form === "crown") {
        const yn = (y - cy) / (ch * 0.5), hr = Math.hypot(x - tx, z - tz) / W;
        const wAt = Math.sqrt(Math.max(0, 1 - yn * yn)) * (sp.env === "obo" ? 0.62 + 0.38 * (yn + 1) * 0.5 * 1.6 : 1);
        if (hr > Math.min(1, wAt) || Math.abs(yn) > 1) continue;
      }
      P.push(x, y, z);
    }
    const np = P.length / 3, alive = new Uint8Array(np).fill(1), best = new Int32Array(np).fill(-1), bd = new Float32Array(np).fill(1e9);
    const di = W * (sp.form === "crown" ? 0.95 : 1.25), dk = D * 1.25, di2 = di * di, dk2 = dk * dk;
    const consider = (from, to) => {
      for (let i = 0; i < np; i++) {
        if (!alive[i]) continue;
        const x = P[i * 3], y = P[i * 3 + 1], z = P[i * 3 + 2];
        for (let n = from; n < to; n++) {
          const d = (X[n] - x) ** 2 + (Y[n] - y) ** 2 + (Z[n] - z) ** 2;
          if (d < bd[i]) { bd[i] = d; best[i] = n; }
        }
        if (bd[i] < dk2) alive[i] = 0;
      }
    };
    consider(Math.max(0, nT - Math.ceil(nT * 0.4)), X.length);   // the upper trunk may branch, not its foot
    const kidDirs = new Map();
    for (let it = 0; it < 160 && X.length < 2600; it++) {
      const acc = new Map();
      for (let i = 0; i < np; i++) {
        if (!alive[i] || bd[i] > di2) continue;
        const n = best[i], d = Math.sqrt(bd[i]) || 1;
        let a = acc.get(n); if (!a) acc.set(n, a = [0, 0, 0]);
        a[0] += (P[i * 3] - X[n]) / d; a[1] += (P[i * 3 + 1] - Y[n]) / d; a[2] += (P[i * 3 + 2] - Z[n]) / d;
      }
      if (!acc.size) break;
      const start = X.length;
      for (const [n, a] of acc) {
        const v = norm([a[0], a[1] + sp.up * Math.hypot(a[0], a[1], a[2]), a[2]]);
        const ks = kidDirs.get(n) || [];
        if (ks.some(k => dot(k, v) > 0.985)) continue;
        ks.push(v); kidDirs.set(n, ks);
        X.push(X[n] + v[0] * D); Y.push(Y[n] + v[1] * D - sp.droop * D); Z.push(Z[n] + v[2] * D); par.push(n);
      }
      if (X.length === start) break;
      consider(start, X.length);
    }
    const S = { X, Y, Z, par, H, cb, W, ch, cy, tx, tz, sp, nT, leafY: cb * 0.85, smooth: true };
    return finish(S, H * sp.trunkR * (0.85 + R() * 0.3));
  }

  /* conifers: a straight trunk to the top, whorls of branches shorter towards the top (fir: level, drooping, the tips
     turned up; cypress: short and steep, a column), each branch a chain with flat side twigs every other node */
  function coneSkel(t, R, sp) {
    const H = t.h, W = H * lerp(sp.width, R()) * 0.5, hb = H * lerp(sp.crownBase, R());
    const X = [], Y = [], Z = [], par = [];
    const D = Math.max(0.25, H * 0.03), la = R() * 6.283, lean = lerp(sp.lean, R()) * H;
    const tx = Math.cos(la) * lean, tz = Math.sin(la) * lean;
    const nAll = Math.ceil(H / D);
    for (let k = 0; k <= nAll; k++) { const f = k / nAll; X.push(tx * f * f); Y.push(H * f); Z.push(tz * f * f); par.push(k - 1); }
    const nT = Math.max(2, Math.ceil(hb / D));
    let az = R() * 6.283;
    for (let y = hb + 0.2; y < H - 0.35; y += lerp(sp.whorl, R())) {
      const rel = (y - hb) / (H - hb), nb = Math.round(lerp(sp.perWhorl, R()));
      const tn = Math.min(nAll, Math.round(y / D));
      for (let b = 0; b < nb; b++) {
        az += 2.39996 + (R() - 0.5) * 0.5;
        const L = W * Math.pow(1 - rel, sp.taper) * (0.8 + R() * 0.4) + 0.15, el0 = lerp(sp.elev, R());
        const steps = Math.max(2, Math.round(L / Math.max(0.22, L / 6))), st = L / steps;
        const hx = Math.cos(az), hz = Math.sin(az);
        let px = X[tn], py = Y[tn], pz = Z[tn], prev = tn;
        for (let s = 1; s <= steps; s++) {
          const f = s / steps, el = el0 + sp.tipUp * f * f;
          px += hx * Math.cos(el) * st; py += Math.sin(el) * st; pz += hz * Math.cos(el) * st;
          X.push(px); Y.push(py); Z.push(pz); par.push(prev); const me = X.length - 1;
          if (s < steps && s % 2 === 1) for (const side of [-1, 1]) {   // flat side twigs, in the branch's plane
            const tl = Math.min(0.55, (L - f * L) * 0.5 + 0.12), sa = side * (0.7 + R() * 0.4);
            const ca = Math.cos(sa), sn = Math.sin(sa), dx = hx * ca - hz * sn, dz = hx * sn + hz * ca;
            X.push(px + dx * tl * 0.5); Y.push(py + Math.sin(el) * tl * 0.3); Z.push(pz + dz * tl * 0.5); par.push(me);
            X.push(px + dx * tl); Y.push(py + Math.sin(el) * tl * 0.5 - 0.03); Z.push(pz + dz * tl); par.push(X.length - 2);
          }
          prev = me;
        }
      }
    }
    const S = { X, Y, Z, par, H, cb: hb, W, ch: H - hb, cy: hb + (H - hb) * 0.45, tx, tz, sp, nT, leafY: hb * 0.9, smooth: false };
    return finish(S, H * sp.trunkR * (0.85 + R() * 0.3));
  }

  function skeleton(t, keep) {
    const key = t.seed + ":" + t.sp + ":" + t.h;
    let S = CACHE.get(key);
    if (S) { CACHE.delete(key); CACHE.set(key, S); return S; }
    const R = mkRand(t.seed), sp = SP[t.sp];
    S = sp.form === "cone" ? coneSkel(t, R, sp) : colonise(t, R, sp);
    const RV = mkRand((t.seed ^ 0x2545f491) >>> 0);
    S.seed2 = (t.seed ^ 0x5bd1e995) >>> 0; S.ph = RV() * 6.283; S.cs = 0.9 + RV() * 0.2;
    if (keep) { CACHE.set(key, S); if (CACHE.size > 500) CACHE.delete(CACHE.keys().next().value); }
    return S;
  }

  // the wind's weight at a point of the tree (local metres): 0 at the trunk's foot, rising up and out; one smooth field
  const swayW = (S, x, y, z) => {
    const up = Math.max(0, Math.min(1, (y - S.cb * 0.5) / (S.H - S.cb * 0.5)));
    const out = Math.min(1.5, Math.hypot(x - S.tx * y / S.H, z - S.tz * y / S.H) / S.W);
    return up * up * 0.55 + out * out * 0.45;
  };

  /* bark: one tube per chain (a branch followed through its thickest child), rings parallel-transported along it.
     u carries the bark kind (+64 per kind: the page wraps u inside that half of the bark atlas). plain: the mid and far
     copies put their bark in the leaf mesh (one draw a block) as untextured vertex colour (u = 2: the leaf shader's flag) */
  function bark(S, lod, B, g, wx, wz, cell, col, plain) {
    const minR = (S.sp.form === "cone" ? [0.025, 0.07, 0.12] : [0.04, 0.12, 0.16])[lod];   // thinner twigs are inside the leaf sprays
    const sidesOf = r => lod === 0 ? (r > 0.22 ? 7 : r > 0.1 ? 5 : 3) : lod === 1 ? (r > 0.2 ? 5 : r > 0.1 ? 4 : 3) : (r > 0.25 ? 4 : 3);
    const stride = [1, 2, 3][lod], uK = 64 * S.sp.barkK;
    const chains = [], stack = [[-1, 0]];
    while (stack.length) {
      const [from, n0] = stack.pop();
      const ch = from < 0 ? [n0] : [from, n0];
      let n = n0;
      while (true) {
        for (const c of S.kids[n]) if (c !== S.main[n]) stack.push([n, c]);
        const m = S.main[n]; if (m < 0) break; ch.push(m); n = m;
      }
      chains.push(ch);
    }
    for (const ch of chains) {
      const first = ch.length > 1 && ch[0] !== 0 && S.par[ch[1]] === ch[0] ? 1 : 0;   // a side branch starts in its parent
      let len = ch.length;
      for (let k = first; k < ch.length; k++) if (S.r[ch[k]] < minR) { len = k; break; }
      if (len - first < 1 || len < 2) continue;
      const all = ch.slice(0, len), nodes = [];
      for (let k = 0; k < all.length; k++) if (k <= first || k === all.length - 1 || (k - first) % stride === 0) nodes.push(all[k]);
      const sides = sidesOf(S.r[nodes[first]]), rep = Math.max(1, Math.round(2 * Math.PI * S.r[nodes[first]] / 0.55));
      let Nv = null, vAcc = 0, prevP = null;
      const ringStart = [];
      for (let k = 0; k < nodes.length; k++) {
        const n = nodes[k], p = [S.X[n], S.Y[n], S.Z[n]];
        const a = nodes[Math.max(0, k - 1)], b = nodes[Math.min(nodes.length - 1, k + 1)];
        const T = norm([S.X[b] - S.X[a], S.Y[b] - S.Y[a], S.Z[b] - S.Z[a]]);
        if (!Nv) { Nv = Math.abs(T[1]) < 0.9 ? norm(cross(T, [0, 1, 0])) : norm(cross(T, [1, 0, 0])); }
        else { const d = dot(Nv, T); Nv = norm([Nv[0] - T[0] * d, Nv[1] - T[1] * d, Nv[2] - T[2] * d]); }
        const Bv = cross(T, Nv);
        const rad = k < first + 1 && first ? S.r[nodes[1]] * 1.05 : S.r[n];
        if (prevP) vAcc += Math.hypot(p[0] - prevP[0], p[1] - prevP[1], p[2] - prevP[2]);
        prevP = p;
        ringStart.push(B.v);
        for (let s = 0; s <= sides; s++) {
          const an = 2 * Math.PI * s / sides, ca = Math.cos(an), sa = Math.sin(an);
          const d = [Nv[0] * ca + Bv[0] * sa, Nv[1] * ca + Bv[1] * sa, Nv[2] * ca + Bv[2] * sa];
          const x = p[0] + d[0] * rad, y = p[1] + d[1] * rad, z = p[2] + d[2] * rad;
          const sh = 0.75 + 0.25 * Math.min(1, y / Math.max(1, S.cb));   // darker low down (grime, shade under the crown)
          if (plain) B.vert(wx + x, g + y, wz + z, d[0], d[1], d[2], 2, 0, col[0] * sh * S.sp.plain[0], col[1] * sh * S.sp.plain[1], col[2] * sh * S.sp.plain[2], swayW(S, x, y, z), S.ph, cell);
          else B.vert(wx + x, g + y, wz + z, d[0], d[1], d[2], uK + s / sides * rep, vAcc / 1.1, col[0] * sh, col[1] * sh, col[2] * sh, swayW(S, x, y, z), S.ph, cell);
        }
      }
      for (let k = 0; k + 1 < ringStart.length; k++) {
        const a = ringStart[k], b = ringStart[k + 1];
        for (let s = 0; s < sides; s++) { B.tri(a + s, b + s, b + s + 1); B.tri(a + s, b + s + 1, a + s + 1); }
      }
    }
  }

  /* leaves. near: spray cards round each twig tip (more on the tip, fewer back along the twig, extra ones facing down
     under the crown); mid: a clump card on some of the twigs, facing out of the crown; far: the crown cut into lumps,
     two crossed clump cards a lump. The atlas row is the kind's; the four tiles of a row are picked per card. */
  function leaves(S, lod, B, g, wx, wz, cell, cards, farScale) {
    const sp = S.sp, cone = sp.form === "cone", pine = sp.row === 2;
    const anchors = [];
    for (let n = 1; n < S.N; n++) if (S.tipDepth[n] <= (cone ? 2 : 3) && S.Y[n] > S.leafY) anchors.push(n);
    if (!anchors.length) return;
    let mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (const n of anchors) { const p = [S.X[n], S.Y[n], S.Z[n]]; for (let i = 0; i < 3; i++) { mn[i] = Math.min(mn[i], p[i]); mx[i] = Math.max(mx[i], p[i]); } }
    const C = [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2 + 0.3, (mn[2] + mx[2]) / 2];
    const E = [Math.max(1, (mx[0] - mn[0]) / 2 + 0.5), Math.max(1, (mx[1] - mn[1]) / 2 + 0.5), Math.max(1, (mx[2] - mn[2]) / 2 + 0.5)];
    const RC = mkRand(S.seed2);
    const tint = [sp.tint[0] * (0.9 + RC() * 0.2), sp.tint[1] * (0.9 + RC() * 0.2), sp.tint[2] * (0.85 + RC() * 0.3)];
    const bright = 0.88 + RC() * 0.24, v0 = (3 - sp.row) * 0.25;
    const shadeAt = (x, y, z, k) => {
      const e = Math.min(1, Math.hypot((x - C[0]) / E[0], (y - C[1]) / E[1], (z - C[2]) / E[2]));
      const ao = (0.45 + 0.55 * e * e) * (0.8 + 0.2 * Math.max(0, Math.min(1, (y - C[1] + E[1]) / (2 * E[1]))));
      return [tint[0] * k * ao * bright, tint[1] * k * ao * bright, tint[2] * k * ao * bright];
    };
    const nrmAt = (x, y, z, cn) => {
      const s = norm([(x - C[0]) / (E[0] * E[0]), (y - C[1]) / (E[1] * E[1]), (z - C[2]) / (E[2] * E[2])]);
      return norm([s[0] * 0.78 + cn[0] * 0.22, s[1] * 0.78 + cn[1] * 0.22 + 0.06, s[2] * 0.78 + cn[2] * 0.22]);
    };
    const card = (base, d, side, size, w, tile, flip, k) => {
      const cn0 = cross(side, d), o = norm([base[0] - C[0], base[1] - C[1], base[2] - C[2]]);
      const cn = dot(cn0, o) < 0 ? [-cn0[0], -cn0[1], -cn0[2]] : cn0;
      const u0 = (tile & 3) * 0.25 + 0.004;
      const i0 = B.v;
      for (const [a, b] of [[-0.5, 0], [0.5, 0], [0.5, 1], [-0.5, 1]]) {
        const x = base[0] + side[0] * a * w + d[0] * b * size, y = base[1] + side[1] * a * w + d[1] * b * size, z = base[2] + side[2] * a * w + d[2] * b * size;
        const nn = nrmAt(x, y, z, cn), c = shadeAt(x, y, z, k);
        const fu = flip ? 0.5 - a : a + 0.5;
        B.vert(wx + x, g + y, wz + z, nn[0], nn[1], nn[2], u0 + fu * 0.242, v0 + 0.004 + b * 0.242, c[0], c[1], c[2], swayW(S, x, y, z), S.ph, cell);
      }
      B.tri(i0, i0 + 1, i0 + 2); B.tri(i0, i0 + 2, i0 + 3);
    };
    const frame = (nrm, spin) => {   // two unit vectors spanning the plane facing nrm, turned by spin
      const ref = Math.abs(nrm[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
      const a0 = norm(cross(ref, nrm)), b0 = cross(nrm, a0), c = Math.cos(spin), s = Math.sin(spin);
      return [[a0[0] * c + b0[0] * s, a0[1] * c + b0[1] * s, a0[2] * c + b0[2] * s], [b0[0] * c - a0[0] * s, b0[1] * c - a0[1] * s, b0[2] * c - a0[2] * s]];
    };
    const outOf = p => norm([(p[0] - C[0]) / E[0], (p[1] - C[1]) / E[1], (p[2] - C[2]) / E[2]]);
    if (lod === 0) {
      // every slot draws the same numbers whether it is used or not, so a tree's cards do not depend on the quality
      const nSlot = sp.slots[0] + sp.under;
      for (const n of anchors) {
        const p = [S.X[n], S.Y[n], S.Z[n]], qn = S.par[n];
        const tw = norm([p[0] - S.X[qn], p[1] - S.Y[qn], p[2] - S.Z[qn]]), o = outOf(p);
        const slots = sp.slots[Math.min(S.tipDepth[n], sp.slots.length - 1)], under = o[1] < 0.15 ? sp.under : 0;
        for (let j = 0; j < nSlot; j++) {
          const keep = RC(), sz = lerp(sp.card, RC()), tile = Math.floor(RC() * 4) & 3, flip = RC() < 0.5;
          const r1 = RC() * 2 - 1, r2 = RC() * 2 - 1, r3 = RC() * 2 - 1, k = 0.8 + RC() * 0.35, spin = RC() * 6.283;
          const isUnder = j >= sp.slots[0];
          if (isUnder ? j - sp.slots[0] >= under : j >= slots) continue;
          if (keep > cards) continue;
          const size = sz * (j && !isUnder ? 0.85 : 1);
          let d;
          if (isUnder) d = norm([o[0] * 0.7 + r1 * 0.5, -0.65 + r2 * 0.2, o[2] * 0.7 + r3 * 0.5]);
          else if (cone) d = norm([tw[0] * 0.8 + o[0] * 0.25 + r1 * 0.25, tw[1] * 0.8 + o[1] * 0.15 + r2 * 0.15 - 0.05, tw[2] * 0.8 + o[2] * 0.25 + r3 * 0.25]);
          else if (pine) d = norm([tw[0] * 0.3 + o[0] * 0.45 + r1 * 0.5, tw[1] * 0.3 + o[1] * 0.3 + r2 * 0.3 + 0.5, tw[2] * 0.3 + o[2] * 0.45 + r3 * 0.5]);
          else { const spread = j ? 1.0 : 0.55; d = norm([tw[0] * 0.4 + o[0] * 0.65 + r1 * spread, tw[1] * 0.4 + o[1] * 0.65 + r2 * spread * 0.7 + 0.18, tw[2] * 0.4 + o[2] * 0.65 + r3 * spread]); }
          let side;
          if (cone) {   // fir sprays lie flat: the card's width stays near the horizontal
            const h = norm(cross(d, [0, 1, 0])), tilt = (spin - 3.14) * 0.12, up = cross(h, d);
            side = norm([h[0] + up[0] * tilt, h[1] + up[1] * tilt, h[2] + up[2] * tilt]);
          } else side = frame(d, spin)[0];
          const base = [p[0] - d[0] * 0.15 * size, p[1] - d[1] * 0.15 * size, p[2] - d[2] * 0.15 * size];
          card(base, d, side, size, size, tile, flip, k);
        }
      }
    } else if (lod === 1) {
      const mS = cone ? Math.max(1.0, Math.min(2.2, S.W * 0.55)) : Math.max(1.3, Math.min(3.0, S.W * 0.42));
      const keepAt = sp.midKeep * (0.55 + 0.45 * cards);
      for (const n of anchors) {
        const keep = RC(), sz = RC(), tile = Math.floor(RC() * 4) & 3, flip = RC() < 0.5, spin = RC() * 6.283, k = 0.85 + RC() * 0.25;
        const r1 = RC() * 2 - 1, r2 = RC() * 2 - 1, r3 = RC() * 2 - 1;
        if (keep > keepAt) continue;
        const p = [S.X[n], S.Y[n], S.Z[n]], o = outOf(p);
        const lift = cone || pine ? 0.45 : 0.1;
        const f = frame(norm([o[0] + r1 * 0.35, o[1] + r2 * 0.25 + lift, o[2] + r3 * 0.35]), spin);
        const size = mS * (0.85 + 0.3 * sz);
        const c0 = [p[0] + o[0] * 0.15, p[1] + o[1] * 0.15, p[2] + o[2] * 0.15];
        card([c0[0] - f[1][0] * size * 0.5, c0[1] - f[1][1] * size * 0.5, c0[2] - f[1][2] * size * 0.5], f[1], f[0], size, size, tile, flip, k);
      }
    } else {
      const cs = (cone ? Math.max(1.4, S.W * 0.6) : Math.max(1.8, S.W * 0.5)) * farScale, cellsMap = new Map();
      for (const n of anchors) {
        const key = Math.floor((S.X[n] - C[0]) / cs) + "," + Math.floor((S.Y[n] - C[1]) / cs) + "," + Math.floor((S.Z[n] - C[2]) / cs);
        let a = cellsMap.get(key); if (!a) cellsMap.set(key, a = [0, 0, 0, 0]);
        a[0] += S.X[n]; a[1] += S.Y[n]; a[2] += S.Z[n]; a[3]++;
      }
      for (const a of cellsMap.values()) {
        const tile = Math.floor(RC() * 4) & 3, spin = RC() * 6.283, k = 0.85 + RC() * 0.25;
        if (a[3] < 2) continue;
        const p = [a[0] / a[3], a[1] / a[3], a[2] / a[3]], o = outOf(p), size = cs * 1.75;
        const f = frame(norm([o[0], o[1] + (cone || pine ? 0.4 : 0.1), o[2]]), spin * 0.3);
        card([p[0] - f[1][0] * size * 0.5, p[1] - f[1][1] * size * 0.5, p[2] - f[1][2] * size * 0.5], f[1], f[0], size, size, tile, false, k);
        const oh = norm([o[0] + 1e-3, 0, o[2]]);   // a standing card across it: the lump's outline seen from the side
        card([p[0], p[1] - size * 0.5, p[2]], [0, 1, 0], oh, size, size, (tile + 1) & 3, true, k * 0.95);
      }
    }
  }

  function tree(t, lod, parts, cards, farScale) {
    const S = skeleton(t, lod < 2);
    const wz = -t.y, wx = t.x, c = S.cs, b = S.sp.bark;
    // tree space -> world: x east, y up, z = -north
    const lk = lod === 0 ? "leafN" : "leafF", LB = parts[lk] || (parts[lk] = new Buf());
    bark(S, lod, lod === 0 ? parts.bark || (parts.bark = new Buf()) : LB, t.g, wx, wz, t.cell, [c * b[0], c * b[1], c * b[2]], lod > 0);
    leaves(S, lod, LB, t.g, wx, wz, t.cell, cards, farScale);
  }

  /* ---------- palms and bamboo (phase 3): every one from its own seed; trunk, fronds, fans and culms ----------
     The palm atlas (palm_atlas.webp) is 4 x 2 tiles of 256 x 512, base at the bottom of each: row 0 frond | dead frond |
     fan | dead fan, row 1 bamboo | bamboo | frond | fan. Near: the trunk is its own textured mesh (palmBark); mid and far:
     the trunk goes plain into the frond mesh (u = 2), so a block with palms costs one draw more, not two. */
  const tile = (c, r, lu, lv) => [(c + 0.006 + lu * 0.988) * 0.25, (r ? 0 : 0.5) + (0.004 + lv * 0.992) * 0.5];
  const UPV = [0, 1, 0];
  // rings along a curve P(f) (tree space: x east, y up, z = -north), radius rr(f, k), colour cf(f, k), sway weight w(f)
  function tube(B, t, P, rr, cf, wf, sides, segs, plain, ph) {
    const wx = t.x, wz = -t.y, g = t.g, rings = [];
    let Nv = null;
    for (let k = 0; k <= segs; k++) {
      const f = k / segs, p = P(f), a = P(Math.max(0, f - 0.01)), b = P(Math.min(1, f + 0.01));
      const T = norm([b[0] - a[0], b[1] - a[1], b[2] - a[2]]);
      if (!Nv) Nv = norm(cross(T, [1, 0, 0])); else { const d = dot(Nv, T); Nv = norm([Nv[0] - T[0] * d, Nv[1] - T[1] * d, Nv[2] - T[2] * d]); }
      const Bv = cross(T, Nv), r = rr(f, k), c = cf(f, k), w = wf(f);
      rings.push(B.v);
      for (let s = 0; s <= sides; s++) {
        const an = 2 * Math.PI * s / sides, ca = Math.cos(an), sa = Math.sin(an);
        const d = [Nv[0] * ca + Bv[0] * sa, Nv[1] * ca + Bv[1] * sa, Nv[2] * ca + Bv[2] * sa];
        B.vert(wx + p[0] + d[0] * r, g + p[1] + d[1] * r, wz + p[2] + d[2] * r, d[0], d[1], d[2],
               plain ? 2 : s / sides * Math.max(1, Math.round(r * 9)), plain ? 0 : p[1] / 0.9, c[0], c[1], c[2], w, ph, t.cell);
      }
    }
    for (let k = 0; k + 1 < rings.length; k++)
      for (let s = 0; s < sides; s++) { const a = rings[k], b = rings[k + 1]; B.tri(a + s, b + s, b + s + 1); B.tri(a + s, b + s + 1, a + s + 1); }
  }
  // the crown's normal: bent out from its centre C, up a little (soft light over the whole crown, as the trees' cards)
  const crownN = (x, y, z, C, sq) => { const s = norm([x - C[0], (y - C[1]) * sq, z - C[2]]); return norm([s[0] * 0.6, s[1] * 0.6 + 0.4, s[2] * 0.6]); };
  const leanOf = (t, R, amt) => t.lean ? [t.lean[0], -t.lean[1]] : (() => { const a = R() * 6.283, m = amt * t.h; return [Math.cos(a) * m, Math.sin(a) * m]; })();

  /* a pinnate frond: a strip V-folded along the rachis, arching out and down from the crown, twisting a little */
  function frond(F, t, top, C, az0, el, L, droop, twist, lod, tl, col, ph, w0) {
    const segF = [8, 5, 3][lod], wx = t.x, wz = -t.y, g = t.g;
    const hor = [Math.cos(az0), 0, Math.sin(az0)], sideH = [-hor[2], 0, hor[0]];
    let p = [top[0] + hor[0] * 0.15, top[1], top[2] + hor[2] * 0.15], ang = el;
    const i0 = F.v, dead = tl[0] === 1;
    for (let j = 0; j <= segF; j++) {
      const sj = j / segF;
      const wid = L * 0.125 * Math.sin(Math.PI * Math.min(1, 0.06 + sj * 0.98)) * (lod === 2 ? 1.25 : 1) + 0.03;
      const roll = twist * sj, fold = wid * (dead ? 0.12 : 0.32);
      const side = [sideH[0] * Math.cos(roll), Math.sin(roll), sideH[2] * Math.cos(roll)];
      const up = [-hor[0] * Math.sin(ang) * 0.3, 1, -hor[2] * Math.sin(ang) * 0.3];
      const w = w0 + (1 - w0) * Math.pow(sj, 1.3);
      for (const [a, u] of [[-1, 0], [0, 0.5], [1, 1]]) {
        const x = p[0] + side[0] * a * wid + (a ? up[0] * fold : 0), y = p[1] + side[1] * a * wid + (a ? up[1] * fold : 0), z = p[2] + side[2] * a * wid + (a ? up[2] * fold : 0);
        const nn = crownN(x, y, z, C, 1.5), ao = 0.68 + 0.32 * sj, uv = tile(tl[0], tl[1], u, sj);
        F.vert(wx + x, g + y, wz + z, nn[0], nn[1], nn[2], uv[0], uv[1], col[0] * ao, col[1] * ao, col[2] * ao, w, ph, t.cell);
      }
      const step = L / segF;
      p = [p[0] + hor[0] * Math.cos(ang) * step, p[1] + Math.sin(ang) * step, p[2] + hor[2] * Math.cos(ang) * step];
      ang -= droop * (0.6 + sj) / segF * 2.2;
    }
    for (let j = 0; j < segF; j++) {
      const a = i0 + j * 3, b = a + 3;
      F.tri(a, b, b + 1); F.tri(a, b + 1, a + 1); F.tri(a + 1, b + 1, b + 2); F.tri(a + 1, b + 2, a + 2);
    }
  }

  /* canary palm (Phoenix): a thick trunk with the rings of old leaf bases, a knobbly head, 30-50 arching pinnate fronds,
     the oldest hanging dead and brown, now and then one broken short */
  function canary(t, lod, parts) {
    const R = mkRand(t.seed), H = t.h, r0 = 0.27 + R() * 0.09, [lx, lz] = leanOf(t, R, 0.07), ph = R() * 6.283;
    const P = f => [lx * f * f, H * f, lz * f * f];
    const F = parts.frond || (parts.frond = new Buf());
    const B = lod === 0 ? parts.palmBark || (parts.palmBark = new Buf()) : F;
    const segs = [Math.round(H / 0.2), Math.round(H / 0.6), 3][lod], tone = 0.85 + R() * 0.2;
    tube(B, t, P, (f, k) => r0 * (1.15 - 0.2 * f + (f < 0.05 ? 0.3 * (1 - f / 0.05) : 0)) * (lod === 0 ? 1 + 0.05 * Math.cos(k * Math.PI) : 1),
         f => lod ? [0.42 * tone, 0.36 * tone, 0.28 * tone] : [0.95 * tone, 0.9 * tone, 0.85 * tone], f => 0.2 * f * f,
         [12, 7, 5][lod], segs, lod > 0, ph);
    const tp = P(1);
    // the head: a swollen knob of leaf bases, greenish
    tube(B, t, f => [tp[0], H + f * 0.9 - 0.15, tp[2]], f => r0 * (1.2 + 0.35 * Math.sin(Math.PI * Math.min(1, f * 1.1))) * (1 - 0.55 * f * f),
         f => lod ? [0.4, 0.4, 0.26] : [0.72, 0.7, 0.5], () => 0.2, [12, 7, 5][lod], [4, 3, 2][lod], lod > 0, ph);
    const top = [tp[0], H + 0.45, tp[2]], C = [top[0], top[1] - 0.6, top[2]];
    const n = 30 + Math.floor(R() * 20), nDead = 3 + Math.floor(R() * 6);
    for (let f = 0; f < n + nDead; f++) {
      const dead = f >= n, q = f / n;
      const az0 = f * 2.39996 + (R() - 0.5) * 0.35;
      const el = dead ? -1.2 - R() * 0.3 : 1.25 - q * 1.7 + (R() - 0.5) * 0.3;
      let L = dead ? 2.4 + R() * 0.9 : 3.2 + R() * 1.2;
      if (!dead && R() < 0.06) L *= 0.55;   // a broken one
      const droop = dead ? 0.12 : 0.55 + R() * 0.5 + q * 0.45, twist = (R() - 0.5) * 0.7, k = 0.85 + R() * 0.3;
      const alt = R() < 0.5;
      if (lod === 2 && f % 2) continue;
      if (lod === 1 && f % 3 === 2) continue;
      const tl = dead ? [1, 0] : alt ? [2, 1] : [0, 0];
      const col = dead ? [0.95 * k, 0.88 * k, 0.8 * k] : [0.55 * k, 0.72 * k, 0.42 * k];
      frond(F, t, [top[0], top[1] - (dead ? 0.45 : q * 0.25), top[2]], C, az0, el, L * (lod === 2 ? 1.05 : 1), droop, twist, lod, tl, col, ph, 0.2);
    }
  }

  /* washingtonia: a slender tall trunk flared at the foot, a skirt of dead fans hanging under the crown (often trimmed
     short in the park), a ball of 22-32 fan leaves on long petioles, the lowest drooping and dry */
  function washi(t, lod, parts) {
    const R = mkRand(t.seed), H = t.h, r0 = 0.17 + R() * 0.05, [lx, lz] = leanOf(t, R, 0.05), ph = R() * 6.283;
    const P = f => [lx * f * f, H * f, lz * f * f];
    const F = parts.frond || (parts.frond = new Buf());
    const B = lod === 0 ? parts.palmBark || (parts.palmBark = new Buf()) : F;
    const tone = 0.8 + R() * 0.2, wx = t.x, wz = -t.y, g = t.g;
    tube(B, t, P, (f, k) => r0 * (1.05 - 0.15 * f + (f < 0.04 ? 0.6 * (1 - f / 0.04) ** 2 : 0)) * (lod === 0 ? 1 + 0.03 * Math.cos(k * Math.PI) : 1),
         () => lod ? [0.45 * tone, 0.41 * tone, 0.36 * tone] : [0.86 * tone, 0.84 * tone, 0.8 * tone], f => 0.25 * f * f,
         [10, 6, 4][lod], [Math.round(H / 0.25), Math.round(H / 0.8), 3][lod], lod > 0, ph);
    const tp = P(1), top = [tp[0], H + 0.15, tp[2]], C = [top[0], top[1] + 0.2, top[2]];
    // the skirt: hanging dead fans pressed round the trunk, wider at the top
    const skirt = R() < 0.6 ? 0.25 + R() * 0.45 : 1.2 + R() * 2.2;   // most are trimmed in the park (v2 1:10:04)
    const nS = Math.round([22, 12, 6][lod] * (skirt > 1 ? 1 : 0.7)), rows = [3, 2, 1][lod];
    for (let s = 0; s < nS; s++) {
      const az = (s + R() * 0.6) / nS * 6.283, half = 0.42 + R() * 0.2, len = skirt * (0.75 + R() * 0.4), k = 0.8 + R() * 0.3;
      const i0 = F.v;
      for (let j = 0; j <= rows; j++) {
        const sj = j / rows, y = H - 0.1 - sj * len, rr = r0 + 0.12 + (1 - sj) * 0.28 + R() * 0.03, fp = P(Math.max(0, y / H));
        for (const [a, u] of [[-1, 0], [0, 0.5], [1, 1]]) {
          const an = az + a * half, x = fp[0] + Math.cos(an) * rr, z = fp[2] + Math.sin(an) * rr;
          const uv = tile(3, 0, u, 1 - sj * 0.95);
          F.vert(wx + x, g + y, wz + z, Math.cos(an), 0.25, Math.sin(an), uv[0], uv[1], 0.74 * k, 0.68 * k, 0.6 * k, 0.25 * (y / H) ** 2, ph, t.cell);
        }
      }
      for (let j = 0; j < rows; j++) {
        const a = i0 + j * 3, b = a + 3;
        F.tri(a, b, b + 1); F.tri(a, b + 1, a + 1); F.tri(a + 1, b + 1, b + 2); F.tri(a + 1, b + 2, a + 2);
      }
    }
    // the fans
    const n = 30 + Math.floor(R() * 13), nDry = 2 + Math.floor(R() * 4);
    const na = [10, 6, 3][lod], nr = [3, 2, 1][lod];
    for (let f = 0; f < n + nDry; f++) {
      if (lod === 2 && f % 2) continue;
      if (lod === 1 && f % 4 === 3) continue;
      const dry = f >= n, q = f / n;
      const az = f * 2.39996 + (R() - 0.5) * 0.4;
      const el = dry ? -0.9 - R() * 0.4 : 1.35 - q * 1.55 + (R() - 0.5) * 0.3;
      const pl = (dry ? 0.9 : 1.1 + R() * 0.7), Rf = 1.0 + R() * 0.4, spread = 2.2 + R() * 0.6, k = 0.85 + R() * 0.3;
      const hor = [Math.cos(az), 0, Math.sin(az)], side = [-hor[2], 0, hor[0]];
      const dir = norm([hor[0] * Math.cos(el), Math.sin(el), hor[2] * Math.cos(el)]);
      const base = [top[0] + hor[0] * 0.1, top[1] - (dry ? 0.3 : 0), top[2] + hor[2] * 0.1];
      const tip = [base[0] + dir[0] * pl, base[1] + dir[1] * pl - 0.08 * pl, base[2] + dir[2] * pl];
      // the petiole: a thin plain strip
      if (lod < 2) {
        const i0 = F.v, pc = dry ? [0.55, 0.45, 0.32] : [0.36, 0.4, 0.22];
        for (const [p, w] of [[base, 0.2], [tip, 0.45]])
          for (const a of [-1, 1]) F.vert(wx + p[0] + side[0] * a * 0.04, g + p[1], wz + p[2] + side[2] * a * 0.04, 0, 1, 0, 2, 0, pc[0], pc[1], pc[2], w, ph, t.cell);
        F.tri(i0, i0 + 2, i0 + 3); F.tri(i0, i0 + 3, i0 + 1);
      }
      // the blade: a fan round the petiole's end, its middle along the petiole bent down, the plane tilted up (palmate,
      // a shallow V along the costa), the segment tips drooping
      const mid = norm([dir[0], dir[1] - 0.35, dir[2]]), nrm = norm(cross(mid, side));
      const tl = dry ? [3, 0] : R() < 0.5 ? [2, 0] : [3, 1];
      const col = dry ? [0.95 * k, 0.9 * k, 0.82 * k] : [0.86 * k, 0.92 * k, 0.8 * k], hang = dry ? 0.7 : 0.25 + R() * 0.25;
      const i0 = F.v;
      for (let j = 0; j <= nr; j++) {
        const rho = j / nr;
        for (let i = 0; i <= na; i++) {
          const a = (i / na - 0.5) * spread, ca = Math.cos(a), sa = Math.sin(a);
          const r = Rf * rho, vee = 0.22 * r * Math.abs(sa);
          const x = tip[0] + (mid[0] * ca + side[0] * sa) * r + nrm[0] * vee, y = tip[1] + (mid[1] * ca + side[1] * sa) * r + nrm[1] * vee - hang * r * rho,
                z = tip[2] + (mid[2] * ca + side[2] * sa) * r + nrm[2] * vee;
          const nn = crownN(x, y, z, C, 1.2), uv = tile(tl[0], tl[1], i / na, rho), ao = 0.7 + 0.3 * rho;
          F.vert(wx + x, g + y, wz + z, nn[0], nn[1], nn[2], uv[0], uv[1], col[0] * ao, col[1] * ao, col[2] * ao, 0.45 + 0.55 * rho, ph, t.cell);
        }
      }
      for (let j = 0; j < nr; j++)
        for (let i = 0; i < na; i++) {
          const a = i0 + j * (na + 1) + i, b = a + na + 1;
          F.tri(a, b, b + 1); F.tri(a, b + 1, a + 1);
        }
    }
  }

  /* a clump of bamboo (moso type): 8-18 culms from a patch of 1-2.4 m, leaning out and arching at the top, nodes every
     ~35 cm, sprays of narrow leaves hanging from the upper half */
  function take(t, lod, parts) {
    const R = mkRand(t.seed), H = t.h, ph = R() * 6.283, wx = t.x, wz = -t.y, g = t.g;
    const F = parts.frond || (parts.frond = new Buf());
    const n = 8 + Math.floor(R() * 11), patch = 0.5 + R() * 0.7, C = [0, H * 0.7, 0];
    for (let c = 0; c < n; c++) {
      const a = R() * 6.283, d = patch * Math.sqrt(R()), bx = Math.cos(a) * d, bz = Math.sin(a) * d;
      const Hc = H * (0.6 + R() * 0.4), rc = 0.02 + R() * 0.025 * (Hc / H), out = a + (R() - 0.5) * 0.8;
      const ox = Math.cos(out), oz = Math.sin(out), lean = 0.04 + R() * 0.14, arch = 0.2 + R() * 0.3, cph = ph + R();
      const P = f => [bx + ox * (lean * Hc * f + arch * Hc * f * f * f), Hc * f * (1 - 0.3 * arch * f * f), bz + oz * (lean * Hc * f + arch * Hc * f * f * f)];
      if (lod === 2 && c % 2) continue;
      const nodes = [Math.round(Hc / 0.35), 5, 2][lod], k = 0.85 + R() * 0.25;
      if (lod < 2 || c % 2 === 0)
        tube(F, t, P, (f, i) => rc * (1 - 0.5 * f) * (lod === 0 && i % 2 === 0 ? 1.15 : 1),   // even rings: the nodes
             (f, i) => lod === 0 && i % 2 === 0 ? [0.62 * k, 0.62 * k, 0.4 * k] : [0.42 * k, 0.55 * k, 0.24 * k], f => f * f,
             [5, 3, 3][lod], lod === 0 ? nodes * 2 : nodes, true, cph);
      // leaf sprays from the upper half: cards hanging from the culm, turned every way
      const nS = Math.round([20, 9, 4][lod] * (Hc / 8));
      for (let s = 0; s < nS; s++) {
        const f = 0.35 + 0.67 * Math.pow((s + R()) / nS, 0.8), p = P(Math.min(1, f)), yaw = R() * 6.283, cw = (lod === 2 ? 1.5 : lod ? 1.25 : 1) * (0.7 + R() * 0.35), ch = cw * 1.9;
        const hx = Math.cos(yaw), hz = Math.sin(yaw), tl = R() < 0.5 ? [0, 1] : [1, 1], kk = 0.8 + R() * 0.3;
        const i0 = F.v;
        for (let j = 0; j <= 2; j++) {
          const sj = j / 2, y = p[1] - ch * (1 - sj) * 0.85, o = 0.35 * cw * (1 - sj) * (1 - sj);
          for (const [u, a] of [[0, -0.5], [1, 0.5]]) {   // the bottom swings out, away from the clump
            const x = p[0] + hx * a * cw + ox * o, z = p[2] + hz * a * cw + oz * o;
            const nn = crownN(x, y, z, C, 0.8), uv = tile(tl[0], tl[1], u, sj);
            F.vert(wx + x, g + y, wz + z, nn[0], nn[1], nn[2], uv[0], uv[1], 0.92 * kk, 0.98 * kk, 0.8 * kk, f * f * (0.6 + 0.4 * sj), cph, t.cell);
          }
        }
        for (let j = 0; j < 2; j++) { const a = i0 + j * 2, b = a + 2; F.tri(a, b, b + 1); F.tri(a, b + 1, a + 1); }
      }
    }
  }
  const PALM = { palm: canary, washi, take };

  function run(job) {
    const parts = {}, transfer = [];
    for (const t of job.trees) {
      if (PALM[t.sp]) PALM[t.sp](t, job.lod, parts); else tree(t, job.lod, parts, job.cards, job.farScale);
    }
    const out = {};
    for (const [k, b] of Object.entries(parts)) { const o = b.out(transfer); if (o) out[k] = o; }
    return { id: job.id, parts: out, transfer };
  }
  return { run, skeleton, SP };
}

/* ---------- the page side ---------- */
function hashSeed(x, y) {   // the tree's seed from its position (0.1 m), the same on every visit
  let h = Math.imul(Math.round(x * 10) | 0, 73856093) ^ Math.imul(Math.round(y * 10) | 0, 19349663);
  h = Math.imul(h ^ (h >>> 13), 0x5bd1e995); return (h ^ (h >>> 15)) >>> 0;
}

const WIND_GLSL = `
uniform float uTime;
attribute vec2 aSway;
vec3 plantWind(vec3 p, float w, float ph, float amp, float flut) {
  vec2 dir = vec2(0.82, 0.57);
  float g = sin(uTime * 0.85 + ph + dot(p.xz, vec2(0.031, 0.027))) * 0.6 + sin(uTime * 1.63 + ph * 1.3 + p.x * 0.05) * 0.4;
  float f = sin(uTime * 5.1 + dot(p, vec3(2.3, 1.9, 2.9)));
  return vec3(dir.x, 0.0, dir.y) * (0.3 + 0.7 * g) * w * amp + vec3(-dir.y * 0.4, 0.5, dir.x * 0.4) * f * w * flut;
}
`;
const hideGLSL = n4 => `
uniform vec4 uHide[${n4}];
attribute float aCell;
float plantHidden(float c) {
  int i = int(c * 0.25 + 0.01); float j = c - float(i) * 4.0; vec4 h = uHide[i];
  return j < 0.5 ? h.x : j < 1.5 ? h.y : j < 2.5 ? h.z : h.w;
}
`;
// leaf cards: the atlas; u > 1.5 marks plain bark merged into a mid / far leaf mesh (vertex colour only, opaque)
const PLAIN_MAP = `
#ifdef USE_MAP
  vec4 sampledDiffuseColor = vUv.x > 1.5 ? vec4(1.0) : texture2D( map, vUv );
  diffuseColor *= sampledDiffuseColor;
#endif
`;
// the bark atlas: grey | pine side by side; u = kind * 64 + the tube's u, wrapped inside the kind's half
const BARK_GLSL = `
vec4 barkTex(sampler2D s, vec2 uv) {
  float k = floor(uv.x / 64.0);
  vec2 w = vec2(0.006 + fract(uv.x) * 0.488 + k * 0.5, fract(uv.y));
#if __VERSION__ >= 300
  return textureGrad(s, w, dFdx(uv) * vec2(0.488, 1.0), dFdy(uv) * vec2(0.488, 1.0));
#else
  return texture2D(s, w);
#endif
}
`;

function init(ctx) {
  const T = ctx.T, Q = pickQuality(), q = QUALITY[Q.name];
  ctx.eyeU = ctx.eyeU || { value: new T.Vector3() };
  const group = new T.Group(); group.name = "plants";
  ctx.root.add(group);
  const loader = new T.TextureLoader();
  const tex = (f, rep) => { const t = loader.load(TEX + f, () => ctx.changed(false)); t.anisotropy = 4; if (rep) t.wrapS = t.wrapT = T.RepeatWrapping; return t; };

  // materials: one per kind of part; mid and far blocks get their own copies (the hide mask is per block)
  const shaded = (mat, o) => {
    mat.onBeforeCompile = sh => {
      sh.uniforms.uTime = ctx.time;
      if (o.hide) sh.uniforms.uHide = { value: o.hide };
      if (o.transl) sh.uniforms.uTransl = { value: o.transl };
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", "#include <common>\n" + WIND_GLSL + (o.hide ? hideGLSL(o.hide.length / 4) : "") +
                 (o.grass ? "uniform vec3 uEye;\nuniform float uGrassR;\n" : ""))
        .replace("#include <begin_vertex>", "#include <begin_vertex>\n" +
                 (o.grass ? "{ float dc = distance(transformed.xz, uEye.xz); float k = 1.0 - smoothstep(uGrassR * 0.65, uGrassR, dc);\n" +
                            "  transformed.y -= aSway.x * aSway.y * (1.0 - k); transformed += plantWind(transformed, aSway.x * aSway.x * k, 0.0, 0.045, 0.012); }\n"
                          : `transformed += plantWind(transformed, aSway.x, aSway.y, ${o.amp.toFixed(3)}, ${o.flut.toFixed(3)});\n`))
        .replace("#include <project_vertex>", "#include <project_vertex>\n" + (o.hide ? "if (plantHidden(aCell) > 0.5) gl_Position = vec4(0.0, 0.0, -2.0, 1.0);\n" : ""));
      if (o.grass) { sh.uniforms.uEye = ctx.eyeU; sh.uniforms.uGrassR = { value: q.grass }; }
      if (o.bark) {
        sh.fragmentShader = sh.fragmentShader
          .replace("#include <common>", "#include <common>\n" + BARK_GLSL)
          .replace("#include <map_fragment>", T.ShaderChunk.map_fragment.replace("texture2D( map, vUv )", "barkTex( map, vUv )"))
          .replace("#include <normal_fragment_maps>", T.ShaderChunk.normal_fragment_maps.replace("texture2D( normalMap, vUv )", "barkTex( normalMap, vUv )"));
      }
      if (o.leaf) {
        sh.fragmentShader = sh.fragmentShader
          .replace("#include <common>", "#include <common>\nuniform float uTransl;\n")
          .replace("#include <map_fragment>", PLAIN_MAP)
          .replace("#include <normal_fragment_begin>", "float faceDirection = gl_FrontFacing ? 1.0 : -1.0;\nvec3 normal = normalize(vNormal);\nvec3 geometryNormal = normal;\n")
          .replace("#include <output_fragment>", `
#if NUM_DIR_LIGHTS > 0
{ vec3 Lv = directionalLights[0].direction, Vv = normalize(vViewPosition);
  float back = pow(clamp(dot(-Vv, Lv), 0.0, 1.0), 4.0), thru = clamp(-dot(normal, Lv), 0.0, 1.0);
  outgoingLight += diffuseColor.rgb * directionalLights[0].color * uTransl * (vUv.x > 1.5 ? 0.0 : 0.7 * back + 0.3 * thru) * vec3(1.0, 1.1, 0.6); }
#endif
#include <output_fragment>`);
      }
    };
    mat.customProgramCacheKey = () => "plants2:" + JSON.stringify([o.hide ? o.hide.length : 0, !!o.leaf, !!o.grass, !!o.bark, o.amp, o.flut]);
    return mat;
  };
  const T_ = {
    leafN: tex("leaves_near.webp"), leafF: tex("leaves_far.webp"), frond: tex("palm_atlas.webp"),
    bark: tex("bark_atlas_color.webp", true), barkN: tex("bark_atlas_normal.webp", true),
    palm: tex("bark_palm_brown_color.webp", true), palmN: tex("bark_palm_brown_normal.webp", true),
  };
  const KIND = {   // part key -> how its material is made
    bark: o => shaded(new T.MeshStandardMaterial({ map: T_.bark, normalMap: T_.barkN, roughness: 0.95, vertexColors: true }), { amp: 0.16, flut: 0, bark: true, ...o }),
    palmBark: o => shaded(new T.MeshStandardMaterial({ map: T_.palm, normalMap: T_.palmN, roughness: 0.95, vertexColors: true }), { amp: 0.35, flut: 0, ...o }),   // = frond: the crown stays on the trunk
    leafN: o => shaded(new T.MeshStandardMaterial({ map: T_.leafN, alphaTest: 0.5, alphaToCoverage: true, side: T.DoubleSide, roughness: 0.82, vertexColors: true }), { amp: 0.16, flut: 0.03, leaf: true, transl: 0.55, ...o }),
    leafF: o => shaded(new T.MeshStandardMaterial({ map: T_.leafF, alphaTest: 0.45, alphaToCoverage: true, side: T.DoubleSide, roughness: 0.85, vertexColors: true }), { amp: 0.16, flut: 0.0, leaf: true, transl: 0.45, ...o }),
    frond: o => shaded(new T.MeshStandardMaterial({ map: T_.frond, alphaTest: 0.5, alphaToCoverage: true, side: T.DoubleSide, roughness: 0.75, vertexColors: true }), { amp: 0.35, flut: 0.04, leaf: true, transl: 0.6, ...o }),
  };
  const DEPTH = {};   // alpha-tested shadow casters for the cards
  const depthFor = key => {
    if (!T_[key] || key.startsWith("bark") || key === "palm") return null;
    if (DEPTH[key]) return DEPTH[key];
    const dm = DEPTH[key] = new T.MeshDepthMaterial({ depthPacking: T.RGBADepthPacking, map: T_[key], alphaTest: 0.5, side: T.DoubleSide });
    dm.onBeforeCompile = sh => { sh.fragmentShader = sh.fragmentShader.replace("#include <map_fragment>", PLAIN_MAP); };   // plain bark casts too
    dm.customProgramCacheKey = () => "plants2-depth";
    return dm;
  };
  const shared = {};
  const matFor = (key, hide) => hide ? KIND[key]({ hide }) : (shared[key] || (shared[key] = KIND[key]({})));

  const meshOf = (parts, hide) => {
    const g = new T.Group();
    for (const [key, a] of Object.entries(parts)) {
      const geo = new T.BufferGeometry();
      geo.setAttribute("position", new T.BufferAttribute(a.pos, 3));
      geo.setAttribute("normal", new T.BufferAttribute(a.nrm, 3));
      geo.setAttribute("uv", new T.BufferAttribute(a.uv, 2));
      geo.setAttribute("color", new T.BufferAttribute(a.col, 3, true));
      geo.setAttribute("aSway", new T.BufferAttribute(a.sway, 2));
      if (hide) geo.setAttribute("aCell", new T.BufferAttribute(a.cell, 1));
      geo.setIndex(new T.BufferAttribute(a.idx, 1));
      geo.computeBoundingSphere();
      const m = new T.Mesh(geo, matFor(key, hide));
      m.name = "plant-" + key;
      if (ctx.shadows) { m.castShadow = true; m.receiveShadow = true; const dm = depthFor(key); if (dm) m.customDepthMaterial = dm; }
      g.add(m);
    }
    return g;
  };
  const freeGroup = g => { g.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material && o.material !== shared[o.name.slice(6)]) o.material.dispose?.(); }); g.parent && g.parent.remove(g); };

  // every tree of the data, its kind from where it stands; and the trial palm
  const gen = GEN();
  const trees = [], kinds = {};
  const D3 = ctx.trees || [], A = ctx.areas || {};
  for (let i = 0; i < D3.length; i += 3) {
    const x = D3[i], y = D3[i + 1], s = hashSeed(x, y);
    const mix = MIX[areaOf(x, y, A)];
    const cellR = frac(mixHash(Math.imul(Math.floor(x / 28), 92837111) ^ Math.imul(Math.floor(y / 28), 689287499)));
    const r1 = frac(mixHash(s ^ 0x68e31da4)), r2 = frac(mixHash(s ^ 0x1b56c4e9));
    const sp = pickKind(mix, r1 < 0.7 ? cellR : r2);   // mostly the patch's kind (plantings come in groups), some mixed in
    const h = D3[i + 2] || lerpH(gen.SP[sp].h, frac(mixHash(s ^ 0x7f4a7c15)));
    trees.push({ x, y, h: Math.round(h * 10) / 10, seed: s, sp, i: i / 3 });
    kinds[sp] = (kinds[sp] || 0) + 1;
  }
  function lerpH(r, f) { return r[0] + (r[1] - r[0]) * f; }
  // the models' palms (specs: [x, y, ground, height, crown dx, dy, kind], src/palm_specs.py)
  const PS = ctx.palms || [];
  for (let i = 0; i < PS.length; i++) {
    const [x, y, g, h, dx, dy, k] = PS[i], sp = k === 1 ? "washi" : "palm";
    trees.push({ x, y, g, h, lean: [dx, dy], seed: hashSeed(x, y), sp, i: -1 });
    kinds[sp] = (kinds[sp] || 0) + 1;
  }

  // cells (near), mid blocks, far blocks
  const cells = new Map(), mids = new Map(), blocks = new Map();
  const newBox = () => [1e9, 1e9, -1e9, -1e9];
  for (const t of trees) {
    if (t.g == null) t.g = ctx.heightAt(t.x, t.y) ?? 0;
    const cx = Math.floor(t.x / CELL), cy = Math.floor(t.y / CELL);
    const mx = Math.floor(cx / MPER), my = Math.floor(cy / MPER), bx = Math.floor(cx / FPER), by = Math.floor(cy / FPER);
    let b = blocks.get(bx + "," + by);
    if (!b) blocks.set(bx + "," + by, b = { trees: [], box: newBox(), cells: [], hide: new Float32Array(FPER * FPER), mesh: null, pending: false, d: 0 });
    let m = mids.get(mx + "," + my);
    if (!m) mids.set(mx + "," + my, m = { trees: [], box: newBox(), cells: [], hide: new Float32Array(4), mesh: null, pending: false, d: 0 });
    let c = cells.get(cx + "," + cy);
    if (!c) {
      cells.set(cx + "," + cy, c = { trees: [], box: newBox(), lv: null, pending: false, mid: m, block: b, s: 2, d: 0,
                                     iM: (cx - mx * MPER) + (cy - my * MPER) * MPER, iB: (cx - bx * FPER) + (cy - by * FPER) * FPER });
      m.cells.push(c); b.cells.push(c);
    }
    t.c = c;
    c.trees.push(t); m.trees.push(t); b.trees.push(t);
    const pad = t.h * 0.6;
    for (const o of [c, m, b]) { o.box[0] = Math.min(o.box[0], t.x - pad); o.box[1] = Math.min(o.box[1], t.y - pad); o.box[2] = Math.max(o.box[2], t.x + pad); o.box[3] = Math.max(o.box[3], t.y + pad); }
  }

  // the workers (or, without workers, the same code on this thread a job at a time)
  const pool = [];
  const nW = Math.max(1, Math.min(q.workers, (navigator.hardwareConcurrency || 2) - 1));
  try {
    const src = "const GEN = " + GEN.toString() + ";\nconst G = GEN();\nonmessage = e => { const r = G.run(e.data); postMessage(r, r.transfer); };";
    const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
    for (let i = 0; i < nW; i++) {
      const w = { worker: new Worker(url), job: null };
      w.worker.onmessage = e => done(w, e.data);
      w.worker.onerror = e => { console.warn("plants worker:", e.message); w.dead = true; if (w.job) { w.job.target.pending = false; w.job = null; } };
      pool.push(w);
    }
  } catch (e) { pool.length = 0; }
  if (!pool.length) pool.push({ worker: null, job: null });
  let jobId = 0;
  const cellOf = { 0: () => 0, 1: t => t.c.iM, 2: t => t.c.iB };
  const send = (w, job) => {
    job.id = ++jobId; w.job = job; job.target.pending = true; job.sent = performance.now();
    const ci = cellOf[job.lod];
    const msg = { id: job.id, lod: job.lod, cards: q.cards, farScale: q.farScale,
                  trees: job.target.trees.map(t => ({ x: t.x, y: t.y, g: t.g, h: t.h, seed: t.seed, sp: t.sp, lean: t.lean, cell: ci(t) })) };
    if (w.worker) w.worker.postMessage(msg);
    else setTimeout(() => done(w, gen.run(msg)), 0);
  };
  const stats = { jobs: 0, ms: 0, t0: performance.now(), farDone: 0, genMs: 0 };
  const oldHidden = [];
  const done = (w, r) => {
    const job = w.job; w.job = null;
    if (!job || job.id !== r.id) return;
    const o = job.target; o.pending = false;
    stats.jobs++; stats.genMs += performance.now() - job.sent;
    if (job.lod === 2) {
      o.mesh = meshOf(r.parts, o.hide); group.add(o.mesh);
      const idx = o.trees.filter(t => t.i >= 0).map(t => t.i);
      oldHidden.push(...idx); ctx.hideOld?.(idx);   // the stand-in instanced trees of this block go
      if (++stats.farDone === blocks.size) stats.ms = performance.now() - stats.t0;
    } else if (job.lod === 1) {
      o.mesh = meshOf(r.parts, o.hide); o.mesh.visible = false; group.add(o.mesh);
    } else {
      o.lv = meshOf(r.parts, null); o.lv.visible = false; group.add(o.lv);
    }
    last = 0; tick(performance.now(), true);
  };

  // grass: blades on the lawn meshes of the trial patch, once the ground models are in (tiles of 12 m: culled per tile)
  const grassMat = shaded(new T.MeshStandardMaterial({ vertexColors: true, side: T.DoubleSide, roughness: 0.9 }), { grass: true, amp: 0, flut: 0 });
  let grassSig = "";
  const shown = o => { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; };
  const buildGrass = () => {   // again whenever the lawn meshes change (a far copy replaced by the full model)
    const meshes = [];
    ctx.root.traverse(o => { if (o.isMesh && /^(TL_grass|EN_bed_lawn|ST_bed_lawn)/.test(o.name) && shown(o)) meshes.push(o); });
    const sig = meshes.map(m => m.uuid).sort().join();
    if (!meshes.length || sig === grassSig) return false;
    grassSig = sig;
    for (const m of [...grassGroup.children]) { m.geometry.dispose(); grassGroup.remove(m); }
    const R = (() => { let s = 0x2545f491; return () => { s = (s ^ (s << 13)) >>> 0; s = (s ^ (s >>> 17)) >>> 0; s = (s ^ (s << 5)) >>> 0; return s / 4294967296; }; })();
    const tiles = new Map(), dens = 70 * q.grassDensity, L = TRIAL_LAWN, v = [new T.Vector3(), new T.Vector3(), new T.Vector3()];
    const e1 = new T.Vector3(), e2 = new T.Vector3(), nn = new T.Vector3();
    for (const m of meshes) {
      m.updateMatrixWorld(true);
      const pos = m.geometry.attributes.position, idx = m.geometry.index, nt = idx ? idx.count / 3 : pos.count / 3;
      for (let t = 0; t < nt; t++) {
        for (let k = 0; k < 3; k++) v[k].fromBufferAttribute(pos, idx ? idx.getX(t * 3 + k) : t * 3 + k).applyMatrix4(m.matrixWorld);
        const cx = (v[0].x + v[1].x + v[2].x) / 3, cy = -(v[0].z + v[1].z + v[2].z) / 3;
        const far = Math.max(...v.map(p => Math.hypot(p.x - L.x, -p.z - L.y)));
        if (Math.hypot(cx - L.x, cy - L.y) > L.r + 30 && far > L.r + 30) continue;
        e1.subVectors(v[1], v[0]); e2.subVectors(v[2], v[0]); nn.crossVectors(e1, e2);
        const area = nn.length() / 2; if (area < 1e-4 || Math.abs(nn.y) / (2 * area) < 0.75) continue;
        let n = area * dens; n = Math.floor(n) + (R() < n % 1 ? 1 : 0);
        for (let i = 0; i < n; i++) {
          let a = R(), b = R(); if (a + b > 1) { a = 1 - a; b = 1 - b; }
          const x = v[0].x + e1.x * a + e2.x * b, y = v[0].y + e1.y * a + e2.y * b, z = v[0].z + e1.z * a + e2.z * b;
          if (Math.hypot(x - L.x, -z - L.y) > L.r) continue;
          const tk = Math.floor(x / 12) + "," + Math.floor(z / 12);
          let tl = tiles.get(tk); if (!tl) tiles.set(tk, tl = { p: [], n: [], c: [], s: [], i: [], v: 0 });
          const yaw = R() * 6.283, h = 0.05 + R() * 0.07, w = 0.008 + R() * 0.008, lean = R() * 0.5, ld = R() * 6.283;
          const sx = Math.cos(yaw) * w, sz = Math.sin(yaw) * w, lx = Math.cos(ld) * Math.sin(lean) * h, lz = Math.sin(ld) * Math.sin(lean) * h;
          const patch = 0.85 + 0.15 * Math.sin(x * 0.7 + Math.sin(z * 0.43) * 2) * Math.sin(z * 0.61 - x * 0.2);
          const k = (0.85 + R() * 0.3) * patch, base = [0.17 * k, 0.27 * k, 0.07 * k], tip = [0.36 * k, 0.53 * k, 0.18 * k];
          const i0 = tl.v;
          const P = [[x - sx, y, z - sz, 0], [x + sx, y, z + sz, 0], [x - sx * 0.6 + lx * 0.45, y + h * 0.55, z - sz * 0.6 + lz * 0.45, 0.55], [x + sx * 0.6 + lx * 0.45, y + h * 0.55, z + sz * 0.6 + lz * 0.45, 0.55], [x + lx, y + h, z + lz, 1]];
          for (const [px, py, pz, f] of P) {
            tl.p.push(px, py, pz); tl.n.push(Math.cos(yaw + 1.57) * 0.25, 1, Math.sin(yaw + 1.57) * 0.25);
            tl.c.push(base[0] + (tip[0] - base[0]) * f, base[1] + (tip[1] - base[1]) * f, base[2] + (tip[2] - base[2]) * f); tl.s.push(f, h);
          }
          tl.i.push(i0, i0 + 1, i0 + 3, i0, i0 + 3, i0 + 2, i0 + 2, i0 + 3, i0 + 4); tl.v += 5;
        }
      }
    }
    let blades = 0;
    for (const tl of tiles.values()) {
      const geo = new T.BufferGeometry();
      geo.setAttribute("position", new T.Float32BufferAttribute(tl.p, 3));
      geo.setAttribute("normal", new T.Float32BufferAttribute(tl.n, 3));
      geo.setAttribute("color", new T.Float32BufferAttribute(tl.c, 3));
      geo.setAttribute("aSway", new T.Float32BufferAttribute(tl.s, 2));
      geo.setIndex(tl.v > 65535 ? new T.Uint32BufferAttribute(tl.i, 1) : new T.Uint16BufferAttribute(tl.i, 1));
      geo.computeBoundingSphere();
      const m = new T.Mesh(geo, grassMat); m.name = "plant-grass"; m.receiveShadow = !!ctx.shadows;
      m.userData.c = geo.boundingSphere.center; m.userData.r = geo.boundingSphere.radius;
      grassGroup.add(m); blades += tl.v / 5;
    }
    stats.grassBlades = blades; stats.grassTiles = tiles.size;
    return true;
  };
  const grassGroup = new T.Group(); grassGroup.name = "plants-grass"; group.add(grassGroup);

  // every 250 ms: what each cell shows (near / mid / far), the jobs to send (nearest first), what to show and free
  let last = 0;
  const boxDist = (b, ex, ey, ez) => Math.hypot(Math.max(b[0] - ex, 0, ex - b[2]), Math.max(b[1] - ey, 0, ey - b[3]), ez);
  function tick(now, force) {
    if (!force && now - last < 250) return;
    last = now;
    const e = ctx.eye(); if (!e) return;
    const ex = e.x, ey = -e.z, ez = Math.max(0, e.y - 2);
    ctx.eyeU.value.copy(e);
    let changed = false;
    for (const b of blocks.values()) b.d = boxDist(b.box, ex, ey, ez);
    for (const m of mids.values()) m.d = boxDist(m.box, ex, ey, ez);
    for (const c of cells.values()) {
      c.d = boxDist(c.box, ex, ey, ez);
      const s = c.d < q.near && c.lv ? 0 : c.mid.d < q.mid && c.mid.mesh ? 1 : 2;
      if (s !== c.s) { changed = true; c.s = s; }
      if (c.lv) c.lv.visible = s === 0;
      c.mid.hide[c.iM] = s !== 1 ? 1 : 0;
      c.block.hide[c.iB] = s !== 2 ? 1 : 0;
      if (c.lv && c.d > q.near * 1.4 && s !== 0) { freeGroup(c.lv); c.lv = null; }
    }
    for (const m of mids.values()) {
      if (!m.mesh) continue;
      const vis = m.cells.some(c => c.s === 1);
      m.mesh.visible = vis;
      if (!vis && m.d > q.mid * 1.3) { freeGroup(m.mesh); m.mesh = null; }
    }
    for (const b of blocks.values()) if (b.mesh) b.mesh.visible = b.d < q.farMax && b.cells.some(c => c.s === 2);
    // jobs: the far block round the viewer first (every tree needs one), then near cells and mid blocks by distance
    for (const w of pool) {
      if (w.job || w.dead) continue;
      let best = null, bestD = Infinity;
      for (const b of blocks.values()) if (!b.mesh && !b.pending && b.d < q.farMax && b.d < bestD) { best = { target: b, lod: 2 }; bestD = b.d; }
      for (const m of mids.values()) if (!m.mesh && !m.pending && m.d < q.mid && m.d + 15 < bestD) { best = { target: m, lod: 1 }; bestD = m.d + 15; }
      for (const c of cells.values()) if (!c.lv && !c.pending && c.d < q.near && c.d + 5 < bestD) { best = { target: c, lod: 0 }; bestD = c.d + 5; }
      if (!best) break;
      send(w, best);
    }
    if (now - (tick.gl || 0) > 3000) {
      tick.gl = now;
      try { if (buildGrass()) changed = true; } catch (err) { console.warn("grass:", err); tick.gl = 1e12; }
    }
    for (const m of grassGroup.children) {   // tiles beyond the blades' reach: not drawn at all
      const c = m.userData.c, vis = Math.hypot(c.x - e.x, c.z - e.z) - m.userData.r < q.grass;
      if (m.visible !== vis) { m.visible = vis; changed = true; }
    }
    if (changed) ctx.changed(true);
  }

  return {
    group, quality: Q.name, forcedQuality: Q.forced,
    covers: () => false,   // every data tree is grown here (the mock's instanced ones stand in until their block is built)
    oldHidden,             // data indices of the stand-ins already replaced (buildTrees applies them if it runs late)
    tick,
    treeList: () => trees.map(t => [t.x, t.y, t.sp, t.h]),   // for checks (perf / screenshots by kind)
    stats: () => {
      let tris = 0, meshes = 0;
      group.traverse(o => { if (o.isMesh && o.visible) { let p = o.parent, v = true; while (p) { if (!p.visible) v = false; p = p.parent; } if (v) { meshes++; tris += o.geometry.index.count / 3; } } });
      const lv = [0, 0, 0]; for (const c of cells.values()) lv[c.s]++;
      return { quality: Q.name, trees: trees.length, kinds, cells: cells.size, mids: mids.size, blocks: blocks.size, workers: pool.filter(w => w.worker).length,
               jobs: stats.jobs, farDone: stats.farDone, allFarMs: Math.round(stats.ms), genMs: Math.round(stats.genMs), cellsNearMidFar: lv,
               meshes, tris, grassBlades: stats.grassBlades || 0, grassTiles: stats.grassTiles || 0 };
    },
  };
}

window.TDS_PLANTS = { init, QUALITY, GEN, areaOf, MIX };
})();
