/* plants.js -- trees, palms and grass grown in the page (docs/plants/plan.md).

   Every tree is its own: the shape comes from a seed made from its position (space colonisation grows the branches
   towards points scattered in a lobed crown), so no two are alike and the same tree always comes back the same.
   The shapes are built in a Web Worker, nearest first, and merged per kind into a few meshes:
     near  (cell of 40 m, within QUALITY.near)  the whole tree: branches down to twigs, a leaf spray card on every twig
     mid   (cell of 40 m, within QUALITY.mid)   the same tree: the thinner twigs dropped, half the cards, a little larger
     far   (block of 160 m)                     the same tree again, low: trunk and main limbs, crossed clump cards
   A far block hides the trees of its cells that show near or mid (a uniform per block, vertices thrown off-screen).
   Leaves: alpha-tested cards (alphaToCoverage), normals bent towards the crown's ellipsoid (soft shading), light through
   the leaves when the sun is behind them, colour varied per tree and per card, darker inside the crown, wind in the
   vertex shader (one smooth field per tree, so twigs and their leaves move together).
   Phase 1 (2026-10-05): the trial round the entrance (TRIAL): one broadleaf kind, one palm, a lawn patch. The other
   trees stay the mock's instanced ones (three.buildTrees skips the ones covered here).
   The plants are in a group named "plants": the water's refraction pass (renderBufferDirect patch) leaves them out. */
(function () {
"use strict";
const TEX = "tex/plants/";
const CELL = 40, BLOCK = 160, PER = BLOCK / CELL;   // 4 x 4 cells a block

/* ---------- quality: high / mid / low, picked from the device, ?q= forces one ---------- */
const QUALITY = {
  high: { near: 55, mid: 150, cards: 1.0, grass: 26, grassDensity: 1.0 },
  mid:  { near: 34, mid: 100, cards: 0.7, grass: 15, grassDensity: 0.5 },
  low:  { near: 22, mid: 65,  cards: 0.5, grass: 9,  grassDensity: 0.3 },
};
function pickQuality() {
  let q = null;
  try { q = new URLSearchParams(location.search).get("q"); } catch (e) { /* no URL API */ }
  if (QUALITY[q]) return { name: q, forced: true };
  const coarse = matchMedia("(pointer: coarse)").matches;
  const cores = navigator.hardwareConcurrency || 4, mem = navigator.deviceMemory || 4;
  return { name: coarse ? (cores >= 6 && mem >= 4 ? "mid" : "low") : (cores >= 4 ? "high" : "mid"), forced: false };
}

/* ---------- the trial area (phase 1): the entrance plaza and the beds outside World Bazaar's east exit ---------- */
const WBA = 25 * Math.PI / 180, WB0 = [-521.3, 891.2];   // the World Bazaar frame (ds_tdl_entrance.WB)
const toWB = (x, y) => { const dx = x - WB0[0], dy = y - WB0[1]; return [dx * Math.cos(WBA) + dy * Math.sin(WBA), -dx * Math.sin(WBA) + dy * Math.cos(WBA)]; };
const fromWB = (u, v) => [WB0[0] + u * Math.cos(WBA) - v * Math.sin(WBA), WB0[1] + u * Math.sin(WBA) + v * Math.cos(WBA)];
function inTrial(x, y) {
  if (x > -640 && x < -430 && y > 800 && y < 990) return true;          // the entrance box (export_mock.py's tall evergreens)
  const [u, v] = toWB(x, y);
  return u > 55 && u < 110 && v > -125 && v < -60;                      // outside the east exit: the big spreading trees
}
const TRIAL_PALMS = [fromWB(72, -106)];                                 // one palm by the beds of the east exit (GLB palms stay)
const TRIAL_LAWN = { x: -518, y: 925, r: 46 };                          // the lawns inside the entrance plaza's arc

/* ---------- the generator (runs in the worker; GEN.toString() is the worker's source) ---------- */
function GEN() {
  const lerp = (r, t) => r[0] + (r[1] - r[0]) * t;
  const mkRand = seed => { let s = (seed >>> 0) || 0x9e3779b9; return () => { s = (s ^ (s << 13)) >>> 0; s = (s ^ (s >>> 17)) >>> 0; s = (s ^ (s << 5)) >>> 0; return s / 4294967296; }; };
  const SP = {   // presets (docs/plants/species.md): heights come from the data, the rest from here
    kusu: { crownBase: [0.2, 0.3], width: [1.0, 1.25], trunkR: 0.028, lobes: [5, 8], pts: 520, card: [1.15, 1.55],
            tint: [0.48, 0.68, 0.36], up: 0.08, droop: 0.02 },
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
                  sway: new Float32Array(this.s), cell: new Float32Array(this.k),
                  idx: this.v > 65535 ? new Uint32Array(this.i) : new Uint16Array(this.i) };
      for (const k of ["pos", "nrm", "uv", "col", "sway", "cell", "idx"]) transfer.push(o[k].buffer);
      return o;
    }
  }
  const norm = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

  /* the skeleton: a trunk to the crown's base, then space colonisation towards points in a few overlapping lobes */
  function skeleton(t) {
    const R = mkRand(t.seed), sp = SP[t.sp];
    const H = t.h, cb = H * lerp(sp.crownBase, R()), W = H * lerp(sp.width, R()) * 0.5, ch = H - cb, cy = cb + ch * 0.5;
    const X = [], Y = [], Z = [], par = [];
    const D = Math.max(0.28, H * 0.03);
    const la = R() * 6.283, lean = (0.01 + R() * 0.04) * H;
    const tx = Math.cos(la) * lean, tz = Math.sin(la) * lean;
    const nT = Math.max(2, Math.ceil(cb / D));
    for (let k = 0; k <= nT; k++) {
      const f = k / nT;
      X.push(tx * f * f + (k ? (R() - 0.5) * 0.06 : 0)); Y.push(cb * f); Z.push(tz * f * f + (k ? (R() - 0.5) * 0.06 : 0)); par.push(k - 1);
    }
    // attraction points in lobes inside the crown's ellipsoid (denser towards each lobe's surface)
    const nl = Math.round(lerp(sp.lobes, R())), lobes = [];
    for (let i = 0; i < nl; i++) {
      const a = R() * 6.283, r = Math.sqrt(R()) * W * 0.5;
      lobes.push([tx + Math.cos(a) * r, cy + (R() - 0.35) * ch * 0.45, tz + Math.sin(a) * r, W * (0.42 + R() * 0.3)]);
    }
    const P = [];
    for (let tries = 0; P.length < sp.pts * 3 && tries < sp.pts * 40; tries++) {
      const L = lobes[Math.floor(R() * nl)];
      let dx = R() * 2 - 1, dy = R() * 2 - 1, dz = R() * 2 - 1; const dl = Math.hypot(dx, dy, dz);
      if (dl > 1 || dl < 1e-3) continue;
      const rr = L[3] * Math.pow(R(), 0.33) / dl;
      const x = L[0] + dx * rr, y = L[1] + dy * rr * 0.8, z = L[2] + dz * rr;
      const ex = (x - tx) / W, ey = (y - cy) / (ch * 0.5), ez = (z - tz) / W;
      if (ex * ex + ey * ey + ez * ez > 1 || y < cb + 0.4) continue;
      P.push(x, y, z);
    }
    const np = P.length / 3, alive = new Uint8Array(np).fill(1), best = new Int32Array(np).fill(-1), bd = new Float32Array(np).fill(1e9);
    const di = W * 0.95, dk = D * 1.25, di2 = di * di, dk2 = dk * dk;
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
    const N = X.length, kids = Array.from({ length: N }, () => []);
    for (let n = 1; n < N; n++) kids[par[n]].push(n);
    // smooth the zigzag of the growth (chains only, not the foot of the trunk)
    for (let pass = 0; pass < 2; pass++) {
      for (let n = 2; n < N; n++) {
        if (kids[n].length !== 1) continue;
        const p = par[n], c = kids[n][0];
        X[n] = X[n] * 0.5 + (X[p] + X[c]) * 0.25; Y[n] = Y[n] * 0.5 + (Y[p] + Y[c]) * 0.25; Z[n] = Z[n] * 0.5 + (Z[p] + Z[c]) * 0.25;
      }
    }
    // radii by the pipe model (r^2 of the parent = sum of the children's), then mapped so a twig tip is 1 cm and the
    // trunk has the preset's size (the skeleton has far fewer tips than a real tree, so the plain model makes twigs fat)
    const r = new Float32Array(N), tipDepth = new Int32Array(N);
    for (let n = N - 1; n >= 0; n--) {
      if (!kids[n].length) { r[n] = 1; tipDepth[n] = 0; continue; }
      let s = 0, td = 1e9; for (const c of kids[n]) { s += r[c] * r[c]; td = Math.min(td, tipDepth[c] + 1); }
      r[n] = Math.sqrt(s); tipDepth[n] = td;
    }
    const rb = H * sp.trunkR * (0.85 + R() * 0.3), TIP = 0.01;
    const gam = Math.log(rb / TIP) / Math.log(Math.max(2, r[0]));
    for (let n = 0; n < N; n++) r[n] = TIP * Math.pow(r[n], gam);
    for (let n = 0; n <= nT; n++) r[n] = Math.max(r[n], rb * (1.12 - 0.25 * n / nT));   // a sturdy trunk, flared at the foot
    let main = new Int32Array(N).fill(-1);
    for (let n = 0; n < N; n++) { let m = -1; for (const c of kids[n]) if (m < 0 || r[c] > r[m]) m = c; main[n] = m; }
    return { X, Y, Z, par, kids, r, main, tipDepth, N, H, cb, W, ch, cy, tx, tz, R, sp, nT };
  }

  // the wind's weight at a point of the tree (local metres): 0 at the trunk's foot, rising up and out; one smooth field
  const swayW = (S, x, y, z) => {
    const up = Math.max(0, Math.min(1, (y - S.cb * 0.5) / (S.H - S.cb * 0.5)));
    const out = Math.min(1.5, Math.hypot(x - S.tx * y / S.H, z - S.tz * y / S.H) / S.W);
    return up * up * 0.55 + out * out * 0.45;
  };

  /* bark: one tube per chain (a branch followed through its thickest child), rings parallel-transported along it */
  function bark(S, lod, B, g, wx, wz, cell, ph, col) {
    const minR = [0.022, 0.07, 0.1][lod];   // thinner twigs are inside the leaf sprays
    const sidesOf = r => lod === 0 ? (r > 0.15 ? 8 : r > 0.06 ? 5 : 3) : lod === 1 ? (r > 0.15 ? 6 : r > 0.07 ? 4 : 3) : (r > 0.18 ? 5 : 3);
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
      const nodes = ch.slice(0, len);
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
          const sh = 0.75 + 0.25 * Math.min(1, y / S.cb);   // darker low down (grime, shade under the crown)
          B.vert(wx + x, g + y, wz + z, d[0], d[1], d[2], s / sides * rep, vAcc / 1.1, col[0] * sh, col[1] * sh, col[2] * sh, swayW(S, x, y, z), ph, cell);
        }
      }
      for (let k = 0; k + 1 < ringStart.length; k++) {
        const a = ringStart[k], b = ringStart[k + 1];
        for (let s = 0; s < sides; s++) { B.tri(a + s, b + s, b + s + 1); B.tri(a + s, b + s + 1, a + s + 1); }
      }
    }
  }

  /* leaves: a spray card on each twig (near: all, mid: half and larger), crossed clump cards in a few cells (far) */
  function leaves(S, lod, B, g, wx, wz, cell, ph, cards) {
    const anchors = [];
    for (let n = 1; n < S.N; n++) if (S.tipDepth[n] <= 3 && S.Y[n] > S.cb * 0.85) anchors.push(n);
    if (!anchors.length) return;
    let mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (const n of anchors) { const p = [S.X[n], S.Y[n], S.Z[n]]; for (let i = 0; i < 3; i++) { mn[i] = Math.min(mn[i], p[i]); mx[i] = Math.max(mx[i], p[i]); } }
    const C = [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2 + 0.3, (mn[2] + mx[2]) / 2];
    const E = [Math.max(1, (mx[0] - mn[0]) / 2 + 0.5), Math.max(1, (mx[1] - mn[1]) / 2 + 0.5), Math.max(1, (mx[2] - mn[2]) / 2 + 0.5)];
    const RC = mkRand(S.seed2);
    const tint = [S.sp.tint[0] * (0.9 + RC() * 0.2), S.sp.tint[1] * (0.9 + RC() * 0.2), S.sp.tint[2] * (0.85 + RC() * 0.3)];
    const bright = 0.88 + RC() * 0.24;
    const shadeAt = (x, y, z, k) => {
      const e = Math.min(1, Math.hypot((x - C[0]) / E[0], (y - C[1]) / E[1], (z - C[2]) / E[2]));
      const ao = (0.42 + 0.58 * e * e) * (0.82 + 0.18 * Math.max(0, Math.min(1, (y - C[1] + E[1]) / (2 * E[1]))));
      return [tint[0] * k * ao * bright, tint[1] * k * ao * bright, tint[2] * k * ao * bright];
    };
    const nrmAt = (x, y, z, cn) => {
      const s = norm([(x - C[0]) / (E[0] * E[0]), (y - C[1]) / (E[1] * E[1]), (z - C[2]) / (E[2] * E[2])]);
      return norm([s[0] * 0.78 + cn[0] * 0.22, s[1] * 0.78 + cn[1] * 0.22 + 0.06, s[2] * 0.78 + cn[2] * 0.22]);
    };
    const card = (base, d, side, size, w, tile, flip, k) => {
      const cn0 = cross(side, d), o = norm([base[0] - C[0], base[1] - C[1], base[2] - C[2]]);
      const cn = dot(cn0, o) < 0 ? [-cn0[0], -cn0[1], -cn0[2]] : cn0;
      const u0 = (tile % 2) * 0.5, v0 = tile < 2 ? 0.5 : 0;
      const i0 = B.v;
      for (const [a, b] of [[-0.5, 0], [0.5, 0], [0.5, 1], [-0.5, 1]]) {
        const x = base[0] + side[0] * a * w + d[0] * b * size, y = base[1] + side[1] * a * w + d[1] * b * size, z = base[2] + side[2] * a * w + d[2] * b * size;
        const nn = nrmAt(x, y, z, cn), c = shadeAt(x, y, z, k);
        B.vert(wx + x, g + y, wz + z, nn[0], nn[1], nn[2], u0 + (flip ? 0.5 - (a + 0.5) * 0.5 : (a + 0.5) * 0.5), v0 + b * 0.5,
               c[0], c[1], c[2], swayW(S, x, y, z), ph, cell);
      }
      B.tri(i0, i0 + 1, i0 + 2); B.tri(i0, i0 + 2, i0 + 3);
    };
    if (lod < 2) {
      // a clump of sprays round each twig tip (4), fewer further back along the twig (2, 1, 1): the crown's leafy masses.
      // Every slot draws the same numbers whatever the level, so the near and the mid tree are the same tree.
      const SLOTS = [5, 3, 2, 1];
      for (const n of anchors) {
        const p = [S.X[n], S.Y[n], S.Z[n]], qn = S.par[n];
        const tw = norm([p[0] - S.X[qn], p[1] - S.Y[qn], p[2] - S.Z[qn]]);
        const o = norm([(p[0] - C[0]) / E[0], (p[1] - C[1]) / E[1], (p[2] - C[2]) / E[2]]);
        for (let j = 0; j < 5; j++) {
          const keep = RC(), sz = lerp(S.sp.card, RC()), tile = Math.floor(RC() * 4) & 3, flip = RC() < 0.5;
          const r1 = RC() * 2 - 1, r2 = RC() * 2 - 1, r3 = RC() * 2 - 1, k = 0.8 + RC() * 0.35, spin = RC() * 6.283;
          if (j >= SLOTS[S.tipDepth[n]] || keep > (lod === 0 ? cards : cards * 0.3)) continue;
          const size = sz * (lod === 1 ? 1.6 : 1) * (j ? 0.85 : 1);
          const spread = j ? 1.0 : 0.55;
          const d = norm([tw[0] * 0.4 + o[0] * 0.65 + r1 * spread, tw[1] * 0.4 + o[1] * 0.65 + r2 * spread * 0.7 + 0.18, tw[2] * 0.4 + o[2] * 0.65 + r3 * spread]);
          const ref = Math.abs(d[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
          const a0 = norm(cross(d, ref)), b0 = cross(d, a0);
          const side = norm([a0[0] * Math.cos(spin) + b0[0] * Math.sin(spin), a0[1] * Math.cos(spin) + b0[1] * Math.sin(spin), a0[2] * Math.cos(spin) + b0[2] * Math.sin(spin)]);
          const base = [p[0] - d[0] * 0.15 * size, p[1] - d[1] * 0.15 * size, p[2] - d[2] * 0.15 * size];
          card(base, d, side, size, size, tile, flip, k);
        }
      }
    } else {
      const cs = Math.max(1.8, S.W * 0.55), cellsMap = new Map();
      for (const n of anchors) {
        const key = Math.floor((S.X[n] - C[0]) / cs) + "," + Math.floor((S.Y[n] - C[1]) / cs) + "," + Math.floor((S.Z[n] - C[2]) / cs);
        let a = cellsMap.get(key); if (!a) cellsMap.set(key, a = [0, 0, 0, 0]);
        a[0] += S.X[n]; a[1] += S.Y[n]; a[2] += S.Z[n]; a[3]++;
      }
      for (const a of cellsMap.values()) {
        const tile = Math.floor(RC() * 4) & 3, spin = RC() * 3.1416, k = 0.85 + RC() * 0.25;
        if (a[3] < 2) continue;
        const p = [a[0] / a[3], a[1] / a[3], a[2] / a[3]], size = cs * 1.9;
        const h0 = [Math.cos(spin), 0, Math.sin(spin)], h1 = [-Math.sin(spin), 0, Math.cos(spin)];
        const base = [p[0], p[1] - size * 0.5, p[2]];
        card(base, [0, 1, 0], h0, size, size, tile, false, k);
        card(base, [0, 1, 0], h1, size, size, (tile + 1) & 3, true, k);
        card([p[0] - h1[0] * size * 0.5, p[1] + size * 0.1, p[2] - h1[2] * size * 0.5], h1, h0, size, size, (tile + 2) & 3, false, k * 1.05);   // lying flat: seen from above
      }
    }
  }

  function broadleaf(t, lod, parts, cards) {
    const S = skeleton(t);
    S.seed2 = (t.seed ^ 0x5bd1e995) >>> 0;
    const ph = S.R() * 6.283, cs = 0.9 + S.R() * 0.2;
    const wz = -t.y, wx = t.x;
    // tree space -> world: x east, y up, z = -north
    bark(S, lod, parts.bark || (parts.bark = new Buf()), t.g, wx, wz, t.cell, ph, [cs, cs * 0.97, cs * 0.92]);
    leaves(S, lod, parts[lod < 2 ? "leafN" : "leafF"] || (parts[lod < 2 ? "leafN" : "leafF"] = new Buf()), t.g, wx, wz, t.cell, ph, cards);
  }

  /* a canary palm: a thick ringed trunk with a knobbly head, a crown of arching pinnate fronds (V-folded strips with
     the frond texture), the oldest hanging dead and brown */
  function palm(t, lod, parts) {
    const R = mkRand(t.seed);
    const H = t.h, r0 = 0.27 + R() * 0.08, la = R() * 6.283, bend = (0.02 + R() * 0.05) * H;
    const ax = Math.cos(la), az = Math.sin(la), ph = R() * 6.283;
    const wx = t.x, wz = -t.y, g = t.g;
    const at = f => [ax * bend * f * f, H * f, az * bend * f * f];
    const B = parts.palmBark || (parts.palmBark = new Buf());
    const sides = [12, 8, 5][lod], segs = [Math.round(H / 0.22), Math.round(H / 0.5), 4][lod];
    const ringW = f => 0.2 * f * f;   // the trunk sways a little at the top; the fronds start from the same weight
    const rings = [];
    let Nv = null;
    for (let k = 0; k <= segs + 2; k++) {
      const head = k > segs, f = head ? 1 + (k - segs) * 0.06 : k / segs;
      const p = at(Math.min(f, 1)); if (head) p[1] = H + (k - segs) * 0.35;
      const T = norm([2 * ax * bend * Math.min(f, 1) / H, 1, 2 * az * bend * Math.min(f, 1) / H]);
      if (!Nv) Nv = norm(cross(T, [1, 0, 0])); else { const d = dot(Nv, T); Nv = norm([Nv[0] - T[0] * d, Nv[1] - T[1] * d, Nv[2] - T[2] * d]); }
      const Bv = cross(T, Nv);
      const knob = lod < 2 ? 1 + 0.045 * Math.cos(k * Math.PI) : 1;   // the leaf-scar rings
      const rr = head ? r0 * (k === segs + 1 ? 1.45 : 0.9) : r0 * (1.18 - 0.22 * f + (f < 0.06 ? 0.25 * (1 - f / 0.06) : 0)) * knob;
      rings.push(B.v);
      for (let s = 0; s <= sides; s++) {
        const an = 2 * Math.PI * s / sides, d = [Nv[0] * Math.cos(an) + Bv[0] * Math.sin(an), Nv[1] * Math.cos(an) + Bv[1] * Math.sin(an), Nv[2] * Math.cos(an) + Bv[2] * Math.sin(an)];
        const c = head ? [0.62, 0.6, 0.42] : [0.95, 0.9, 0.85];
        B.vert(wx + p[0] + d[0] * rr, g + p[1] + d[1] * rr, wz + p[2] + d[2] * rr, d[0], d[1], d[2], s / sides * 3, p[1] / 0.9,
               c[0], c[1], c[2], ringW(Math.min(f, 1)), ph, t.cell);
      }
    }
    for (let k = 0; k + 1 < rings.length; k++)
      for (let s = 0; s < sides; s++) { const a = rings[k], b = rings[k + 1]; B.tri(a + s, b + s, b + s + 1); B.tri(a + s, b + s + 1, a + s + 1); }
    // fronds
    const F = parts.frond || (parts.frond = new Buf());
    const top = [at(1)[0], H + 0.25, at(1)[2]], n = 40, segF = [8, 5, 3][lod];
    const C = [top[0], top[1] - 0.6, top[2]];
    for (let f = 0; f < n; f++) {
      const dead = f >= n - 6, q = f / n;
      const az0 = f * 2.39996 + (R() - 0.5) * 0.3, el = dead ? -1.25 - R() * 0.25 : 1.2 - q * 1.6 + (R() - 0.5) * 0.25;
      const L = dead ? 2.6 + R() * 0.8 : 3.4 + R() * 1.1, droop = dead ? 0.15 : 0.6 + R() * 0.5 + q * 0.4, twist = (R() - 0.5) * 0.6;
      const k = dead ? 1 : 0.85 + R() * 0.3;
      const col = dead ? [0.62 * k, 0.48 * k, 0.28 * k] : [0.55 * k, 0.72 * k, 0.40 * k];
      if (lod === 2 && f % 2) continue;   // far: every other frond, a little wider
      const hor = [Math.cos(az0), 0, Math.sin(az0)], sideH = [-hor[2], 0, hor[0]];
      let p = [top[0] + hor[0] * 0.15, top[1] - (dead ? 0.3 : 0), top[2] + hor[2] * 0.15], ang = el, s = 0;
      const i0 = F.v;
      for (let j = 0; j <= segF; j++) {
        const sj = j / segF;
        const wid = L * 0.125 * Math.sin(Math.PI * Math.min(1, 0.06 + sj * 0.98)) * (lod === 2 ? 1.25 : 1) + 0.03;
        const roll = twist * sj, fold = wid * (dead ? 0.1 : 0.32);
        const side = [sideH[0] * Math.cos(roll), Math.sin(roll), sideH[2] * Math.cos(roll)];
        const up = [-hor[0] * Math.sin(ang) * 0.3, 1, -hor[2] * Math.sin(ang) * 0.3];
        const w = 0.2 + 0.8 * Math.pow(sj, 1.3);
        for (const [a, u] of [[-1, 0], [0, 0.5], [1, 1]]) {
          const x = p[0] + side[0] * a * wid + (a ? up[0] * fold : 0), y = p[1] + side[1] * a * wid + (a ? up[1] * fold : 0), z = p[2] + side[2] * a * wid + (a ? up[2] * fold : 0);
          const sn = norm([x - C[0], (y - C[1]) * 1.5, z - C[2]]), nn = norm([sn[0] * 0.55, sn[1] * 0.55 + 0.45, sn[2] * 0.55]);
          const ao = 0.7 + 0.3 * sj;
          F.vert(wx + x, g + y, wz + z, nn[0], nn[1], nn[2], u, sj, col[0] * ao, col[1] * ao, col[2] * ao, w, ph, t.cell);
        }
        const step = L / segF;
        p = [p[0] + hor[0] * Math.cos(ang) * step, p[1] + Math.sin(ang) * step, p[2] + hor[2] * Math.cos(ang) * step];
        ang -= droop * (0.6 + sj) / segF * 2.2; s += step;
      }
      for (let j = 0; j < segF; j++) {
        const a = i0 + j * 3, b = a + 3;
        F.tri(a, b, b + 1); F.tri(a, b + 1, a + 1); F.tri(a + 1, b + 1, b + 2); F.tri(a + 1, b + 2, a + 2);
      }
    }
  }

  function run(job) {
    const parts = {}, transfer = [];
    for (const t of job.trees) {
      if (t.sp === "palm") palm(t, job.lod, parts); else broadleaf(t, job.lod, parts, job.cards);
    }
    const out = {};
    for (const [k, b] of Object.entries(parts)) { const o = b.out(transfer); if (o) out[k] = o; }
    return { id: job.id, parts: out, transfer };
  }
  return { run, skeleton };
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

function init(ctx) {
  const T = ctx.T, Q = pickQuality(), q = QUALITY[Q.name];
  ctx.eyeU = ctx.eyeU || { value: new T.Vector3() };
  const group = new T.Group(); group.name = "plants";
  ctx.root.add(group);
  const loader = new T.TextureLoader();
  const tex = (f, rep) => { const t = loader.load(TEX + f, () => ctx.changed(false)); t.anisotropy = 4; if (rep) t.wrapS = t.wrapT = T.RepeatWrapping; return t; };

  // materials: one per kind; far blocks get their own copies (the hide mask is per block)
  const shaded = (mat, o) => {
    mat.onBeforeCompile = sh => {
      sh.uniforms.uTime = ctx.time;
      if (o.hide) sh.uniforms.uHide = { value: o.hide };
      if (o.transl) sh.uniforms.uTransl = { value: o.transl };
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", "#include <common>\n" + WIND_GLSL + (o.hide ? "uniform float uHide[16];\nattribute float aCell;\n" : "") +
                 (o.grass ? "uniform vec3 uEye;\nuniform float uGrassR;\n" : ""))
        .replace("#include <begin_vertex>", "#include <begin_vertex>\n" +
                 (o.grass ? "{ float dc = distance(transformed.xz, uEye.xz); float k = 1.0 - smoothstep(uGrassR * 0.65, uGrassR, dc);\n" +
                            "  transformed.y -= aSway.x * aSway.y * (1.0 - k); transformed += plantWind(transformed, aSway.x * aSway.x * k, 0.0, 0.045, 0.012); }\n"
                          : `transformed += plantWind(transformed, aSway.x, aSway.y, ${o.amp.toFixed(3)}, ${o.flut.toFixed(3)});\n`))
        .replace("#include <project_vertex>", "#include <project_vertex>\n" + (o.hide ? "if (uHide[int(aCell + 0.5)] > 0.5) gl_Position = vec4(0.0, 0.0, -2.0, 1.0);\n" : ""));
      if (o.grass) { sh.uniforms.uEye = ctx.eyeU; sh.uniforms.uGrassR = { value: q.grass }; }
      if (o.leaf) {
        sh.fragmentShader = sh.fragmentShader
          .replace("#include <common>", "#include <common>\nuniform float uTransl;\n")
          .replace("#include <normal_fragment_begin>", "float faceDirection = gl_FrontFacing ? 1.0 : -1.0;\nvec3 normal = normalize(vNormal);\nvec3 geometryNormal = normal;\n")
          .replace("#include <output_fragment>", `
#if NUM_DIR_LIGHTS > 0
{ vec3 Lv = directionalLights[0].direction, Vv = normalize(vViewPosition);
  float back = pow(clamp(dot(-Vv, Lv), 0.0, 1.0), 4.0), thru = clamp(-dot(normal, Lv), 0.0, 1.0);
  outgoingLight += diffuseColor.rgb * directionalLights[0].color * uTransl * (0.7 * back + 0.3 * thru) * vec3(1.0, 1.1, 0.6); }
#endif
#include <output_fragment>`);
      }
    };
    mat.customProgramCacheKey = () => "plants:" + JSON.stringify([!!o.hide, !!o.leaf, !!o.grass, o.amp, o.flut]);
    return mat;
  };
  const T_ = {
    leafN: tex("cluster_broadleaf_near.webp"), leafF: tex("cluster_broadleaf_far.webp"), frond: tex("palm_frond.webp"),
    bark: tex("bark_grey_color.webp", true), barkN: tex("bark_grey_normal.webp", true),
    palm: tex("bark_palm_brown_color.webp", true), palmN: tex("bark_palm_brown_normal.webp", true),
  };
  const KIND = {   // part key -> how its material is made
    bark: o => shaded(new T.MeshStandardMaterial({ map: T_.bark, normalMap: T_.barkN, roughness: 0.95, vertexColors: true }), { amp: 0.16, flut: 0, ...o }),
    palmBark: o => shaded(new T.MeshStandardMaterial({ map: T_.palm, normalMap: T_.palmN, roughness: 0.95, vertexColors: true }), { amp: 0.35, flut: 0, ...o }),   // = frond: the crown stays on the trunk
    leafN: o => shaded(new T.MeshStandardMaterial({ map: T_.leafN, alphaTest: 0.5, alphaToCoverage: true, side: T.DoubleSide, roughness: 0.82, vertexColors: true }), { amp: 0.16, flut: 0.03, leaf: true, transl: 0.55, ...o }),
    leafF: o => shaded(new T.MeshStandardMaterial({ map: T_.leafF, alphaTest: 0.45, alphaToCoverage: true, side: T.DoubleSide, roughness: 0.85, vertexColors: true }), { amp: 0.16, flut: 0.0, leaf: true, transl: 0.45, ...o }),
    frond: o => shaded(new T.MeshStandardMaterial({ map: T_.frond, alphaTest: 0.5, alphaToCoverage: true, side: T.DoubleSide, roughness: 0.75, vertexColors: true }), { amp: 0.35, flut: 0.04, leaf: true, transl: 0.6, ...o }),
  };
  const DEPTH = {};   // alpha-tested shadow casters for the cards
  const depthFor = key => {
    if (!T_[key] || key.startsWith("bark") || key === "palm") return null;
    return DEPTH[key] || (DEPTH[key] = new T.MeshDepthMaterial({ depthPacking: T.RGBADepthPacking, map: T_[key], alphaTest: 0.5, side: T.DoubleSide }));
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

  // the trees of the trial: data trees inside the area (one broadleaf kind) and the trial palm
  const trees = [];
  const D3 = ctx.trees || [];
  for (let i = 0; i < D3.length; i += 3) {
    const x = D3[i], y = D3[i + 1]; if (!inTrial(x, y)) continue;
    const s = hashSeed(x, y);
    trees.push({ x, y, h: D3[i + 2] || (8 + (s % 1000) / 1000 * 4), seed: s, sp: "kusu" });
  }
  for (const [x, y] of TRIAL_PALMS) { const s = hashSeed(x, y); trees.push({ x, y, h: 6.0 + (s % 1000) / 1000 * 1.5, seed: s, sp: "palm" }); }
  const cells = new Map(), blocks = new Map();
  for (const t of trees) {
    t.g = ctx.heightAt(t.x, t.y) ?? 0;
    const cx = Math.floor(t.x / CELL), cy = Math.floor(t.y / CELL), bx = Math.floor(cx / PER), by = Math.floor(cy / PER);
    const ck = cx + "," + cy, bk = bx + "," + by;
    let b = blocks.get(bk);
    if (!b) blocks.set(bk, b = { key: bk, trees: [], box: [1e9, 1e9, -1e9, -1e9], hide: new Array(16).fill(0), mesh: null, pending: false });
    let c = cells.get(ck);
    if (!c) cells.set(ck, c = { key: ck, block: b, idx: (cx - bx * PER) + (cy - by * PER) * PER, trees: [], box: [1e9, 1e9, -1e9, -1e9], lv: [null, null], pending: [false, false], shown: 2 });
    t.cell = c.idx;
    c.trees.push(t); b.trees.push(t);
    const pad = t.h * 0.6;
    for (const o of [c, b]) { o.box[0] = Math.min(o.box[0], t.x - pad); o.box[1] = Math.min(o.box[1], t.y - pad); o.box[2] = Math.max(o.box[2], t.x + pad); o.box[3] = Math.max(o.box[3], t.y + pad); }
  }

  // the worker (or, without workers, the same code on this thread a job at a time)
  const gen = GEN();
  let worker = null, busy = null;
  try {
    const src = "const GEN = " + GEN.toString() + ";\nconst G = GEN();\nonmessage = e => { const r = G.run(e.data); postMessage(r, r.transfer); };";
    worker = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
    worker.onmessage = e => done(e.data);
    worker.onerror = e => { console.warn("plants worker:", e.message); worker = null; busy = null; };
  } catch (e) { worker = null; }
  let jobId = 0;
  const jobs = new Map();
  const send = job => {
    job.id = ++jobId; jobs.set(job.id, job); busy = job;
    const msg = { id: job.id, lod: job.lod, cards: q.cards, trees: job.trees.map(t => ({ x: t.x, y: t.y, g: t.g, h: t.h, seed: t.seed, sp: t.sp, cell: t.cell })) };
    if (worker) worker.postMessage(msg);
    else setTimeout(() => done(gen.run(msg)), 0);
  };
  const stats = { jobs: 0, ms: 0, t0: performance.now() };
  const done = r => {
    const job = jobs.get(r.id); jobs.delete(r.id); busy = null;
    stats.jobs++; stats.ms = performance.now() - stats.t0;
    if (!job) return;
    if (job.block) {
      const b = job.block; b.pending = false;
      b.mesh = meshOf(r.parts, b.hide); group.add(b.mesh);
    } else {
      const c = job.cell; c.pending[job.lod] = false;
      if (job.stale) return;
      c.lv[job.lod] = meshOf(r.parts, null); c.lv[job.lod].visible = false; group.add(c.lv[job.lod]);
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

  // every 250 ms: the level each cell wants, the jobs to send (nearest first), what to show and free
  let last = 0;
  const boxDist = (b, ex, ey, ez) => Math.hypot(Math.max(b[0] - ex, 0, ex - b[2]), Math.max(b[1] - ey, 0, ey - b[3]), ez);
  function tick(now, force) {
    if (!force && now - last < 250) return;
    last = now;
    const e = ctx.eye(); if (!e) return;
    const ex = e.x, ey = -e.z, ez = Math.max(0, e.y - 2);
    ctx.eyeU.value.copy(e);
    let changed = false, best = null, bestD = Infinity;
    for (const c of cells.values()) {
      const d = boxDist(c.box, ex, ey, ez), want = d < q.near ? 0 : d < q.mid ? 1 : 2;
      if (want < 2 && !c.lv[want] && !c.pending[want] && d < bestD) { best = { cell: c, lod: want, trees: c.trees }; bestD = d; }
      const show = want < 2 && c.lv[want] ? want : want < 2 && c.lv[1 - want] ? 1 - want : 2;
      if (show !== c.shown || force) {
        for (let l = 0; l < 2; l++) if (c.lv[l]) c.lv[l].visible = l === show;
        if (c.block.hide[c.idx] !== (show < 2 ? 1 : 0)) { c.block.hide[c.idx] = show < 2 ? 1 : 0; }
        if (show !== c.shown) changed = true;
        c.shown = show;
      }
      if (c.lv[0] && d > q.near * 1.4 && c.shown !== 0) { freeGroup(c.lv[0]); c.lv[0] = null; }
      if (c.lv[1] && d > q.mid * 1.3 && c.shown !== 1) { freeGroup(c.lv[1]); c.lv[1] = null; }
    }
    for (const b of blocks.values()) {
      if (b.mesh || b.pending) continue;
      const d = boxDist(b.box, ex, ey, ez) + 30;   // a near cell first, then its block
      if (d < bestD) { best = { block: b, lod: 2, trees: b.trees }; bestD = d; }
    }
    if (best && !busy) {
      if (best.block) best.block.pending = true; else best.cell.pending[best.lod] = true;
      send(best);
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
    covers: inTrial,   // the mock's instanced trees leave these out
    tick,
    stats: () => {
      let tris = 0, meshes = 0;
      group.traverse(o => { if (o.isMesh && o.visible) { let p = o.parent, v = true; while (p) { if (!p.visible) v = false; p = p.parent; } if (v) { meshes++; tris += o.geometry.index.count / 3; } } });
      return { quality: Q.name, trees: trees.length, cells: cells.size, blocks: blocks.size, worker: !!worker, jobs: stats.jobs, ms: Math.round(stats.ms),
               shown: [...cells.values()].map(c => c.shown).join(""), meshes, tris, grassBlades: stats.grassBlades || 0, grassTiles: stats.grassTiles || 0 };
    },
  };
}

window.TDS_PLANTS = { init, QUALITY, GEN };
})();
