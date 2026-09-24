/* Disney Resort Line train (Type X / Type C look), shared by train.html and the map mock (tds_outline.html).
 *
 *   const TM = TrainModel.create(THREE, { linear, envMap });
 *   const U = TM.uniforms("blue");                       // colour band of one train (each train has its own)
 *   const t = TM.buildTrain(U, { simple, merge });       // { group, slots, gangways, cars, length, mats }
 *
 * Car-local axes: x along the car (nose at +x), y up (beam top = 0), z sideways; metres.
 * A train is 6 cars in `slots` (one Group per car, placed at the car's rear end along the train, front at +x)
 * plus the gangways between them. `simple` builds the far-away version: a coarse shell with the windows
 * painted dark instead of cut out, and no interior (a few hundred triangles per car instead of ~16 000).
 * `merge` bakes each car's interior into one mesh per material (far fewer draw calls; same look).
 * `linear`: the page renders without sRGB output, so the drawn textures are shown as stored.
 * Dimensions and sources: docs/train/spec.md.
 */
window.TrainModel = (() => {
function create(T, opt = {}) {
/* ---------- spec (m) ---------- */
const S = {
  headLen: 15.05, midLen: 13.70, width: 2.98, gap: 0.55, cars: 6,     // Wikipedia
  yBot: -0.9, yTop: 3.95, roofR: 1.1, noseLen: 0.9,                   // estimates (from photos)
  floor: 1.0, ceil: 3.18,                                              // interior levels (estimates)
  beamW: 0.85, beamH: 1.4, pillarEvery: 30, pillarH: 8.0,
};
const W = S.width, HW = W / 2;
const SCHEMES = {
  blue:   { name: "ブルー", a: 0x2f7fd6, b: 0x9cc9f2 },
  yellow: { name: "イエロー", a: 0xf2b51c, b: 0xfbe18a },
  purple: { name: "パープル", a: 0x8a4fc0, b: 0xc9a6e6 },
  green:  { name: "グリーン", a: 0x3fa34d, b: 0xa5d9a0 },
  peach:  { name: "ピーチ", a: 0xf08a7a, b: 0xf8c8bd },
};
const uniforms = k => ({ a: { value: new T.Color(SCHEMES[k].a) }, b: { value: new T.Color(SCHEMES[k].b) } });

/* ---------- textures drawn here (no photos are used) ---------- */
function canvasTex(w, h, draw, repeat) {
  const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
  const t = new T.CanvasTexture(c); t.encoding = opt.linear ? T.LinearEncoding : T.sRGBEncoding; t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 4;
  if (repeat) t.repeat.set(repeat[0], repeat[1]); return t;
}
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const seatTex = canvasTex(256, 256, (g, w, h) => {   // dark grey moquette with small coloured squares and triangles
  g.fillStyle = "#3a3b40"; g.fillRect(0, 0, w, h);
  const cols = ["#d9382f", "#e6c34a", "#c9c9c4", "#8b8d92", "#4f5157", "#2f8c9c"];
  for (let i = 0; i < 260; i++) { g.fillStyle = cols[Math.floor(rnd() * cols.length)]; const x = rnd() * w, y = rnd() * h, s = 5 + rnd() * 9;
    g.save(); g.translate(x, y); g.rotate(rnd() * 3); if (rnd() < 0.5) g.fillRect(-s / 2, -s / 2, s, s); else { g.beginPath(); g.moveTo(0, -s / 2); g.lineTo(s / 2, s / 2); g.lineTo(-s / 2, s / 2); g.fill(); } g.restore(); }
}, null);
const dotTex = canvasTex(128, 128, (g, w, h) => {      // observation bench: magenta with big yellow dots
  g.fillStyle = "#d2185b"; g.fillRect(0, 0, w, h); g.fillStyle = "#f1cf3d";
  [[30, 32, 22], [92, 60, 26], [40, 100, 16], [110, 12, 12]].forEach(([x, y, r]) => { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); });
}, null);
const checkTex = canvasTex(64, 64, (g, w, h) => {
  g.fillStyle = "#cbb98a"; g.fillRect(0, 0, w, h); g.fillStyle = "#a99a6f"; g.fillRect(0, 0, w / 2, h / 2); g.fillRect(w / 2, h / 2, w / 2, h / 2);
}, null);

/* ---------- materials ---------- */
const std = (o) => new T.MeshStandardMaterial(o);
// interior surfaces are partly self-lit (like the cabin lighting), so the cabin reads through the windows
const lit = (c, k = 0.45, o = {}) => new T.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: k, roughness: 0.7, ...o, ...(o.map ? { emissiveMap: o.map } : {}) });
const M = {
  cream: lit(0xf2ecdc), floor: lit(0xd8b53f, 0.3), ceil: lit(0xf6f1e4, 0.6), seat: lit(0xffffff, 0.35, { map: seatTex }), dots: lit(0xffffff, 0.35, { map: dotTex }),
  check: lit(0xffffff, 0.3, { map: checkTex }), steel: lit(0xc9ced3, 0.2, { roughness: 0.3, metalness: 0.6 }), dark: std({ color: 0x23262b, roughness: 0.6, metalness: 0.3 }),
  cab: std({ color: 0x17191c, roughness: 0.45, metalness: 0.4 }), rubber: std({ color: 0x141414, roughness: 0.95 }), orange: lit(0xe8541f, 0.5),
  strapBand: lit(0xf5c518, 0.5), roofUnit: std({ color: 0xd7dade, roughness: 0.6 }),
  lamp: new T.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfffbe6, emissiveIntensity: 2.4 }),
  strip: new T.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 1.6 }),
  screen: new T.MeshStandardMaterial({ color: 0x0b1a22, emissive: 0x37c0d8, emissiveIntensity: 1.0 }),
  screen2: new T.MeshStandardMaterial({ color: 0x0b1a22, emissive: 0xe0a030, emissiveIntensity: 0.9 }),
  bellows: std({ color: 0x3a3d42, roughness: 0.85, side: T.DoubleSide }), concrete: std({ color: 0x9c9a94, roughness: 0.92 }),
  ground: std({ color: 0x5d6d4e, roughness: 1 }), road: std({ color: 0x55575a, roughness: 0.95 }),
};

/* ---------- body shell: a lofted skin whose windows are real holes (discarded in the shader) ---------- */
const GLSL_COMMON = (kind, L) => `
varying vec3 vLP; varying vec3 vLN; uniform vec3 uA; uniform vec3 uB;
const float CL = ${L.toFixed(3)}; const int KIND = ${kind};
float sdE(vec2 p, vec2 c, vec2 r){ return length((p - c) / r) - 1.0; }
float sdRB(vec2 p, vec2 c, vec2 h, float r){ vec2 q = abs(p - c) - h + r; return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r; }
float mickey(vec2 p, vec2 c){   // tall Mickey head: oval face + two ears
  float h = sdE(p, c, vec2(0.34, 0.44));
  float e1 = sdE(p, c + vec2(-0.36, 0.46), vec2(0.19)), e2 = sdE(p, c + vec2(0.36, 0.46), vec2(0.19));
  return min(h, min(e1, e2));
}
float doorX(int k){ return k == 0 ? 1.95 : (KIND == 0 ? CL - 1.95 : CL - 5.6); }
bool sideHole(vec2 p){
  float d = 1.0;
  if (KIND == 0) { for (int i = 0; i < 4; i++) d = min(d, mickey(p, vec2(3.9 + 1.9 * float(i), 2.35))); }
  else { for (int i = 0; i < 3; i++) d = min(d, mickey(p, vec2(3.9 + 1.9 * float(i), 2.35))); d = min(d, sdE(p, vec2(12.35, 2.4), vec2(0.9, 0.55))); }
  for (int k = 0; k < 2; k++) { float dx = doorX(k); d = min(d, sdE(p, vec2(dx - 0.4, 2.3), vec2(0.22, 0.6))); d = min(d, sdE(p, vec2(dx + 0.4, 2.3), vec2(0.22, 0.6))); }
  return d < 0.0;
}
bool frontHole(vec2 p){   // p = (z, y): three panes, the centre one is the gangway door
  float d = sdRB(p, vec2(0.0, 2.62), vec2(0.36, 0.52), 0.06);
  d = min(d, sdRB(p, vec2(-0.69, 2.62), vec2(0.24, 0.52), 0.1));
  d = min(d, sdRB(p, vec2(0.69, 2.62), vec2(0.24, 0.52), 0.1));
  return d < 0.0;
}`;
const VARYINGS = sh => { sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vLP; varying vec3 vLN;").replace("#include <begin_vertex>", "#include <begin_vertex>\nvLP = position; vLN = normal;"); };
const GLSL_DISCARD = `{ if (abs(vLN.z) > 0.75) { if (sideHole(vLP.xy)) discard; } else if (KIND == 1 && vLN.x > 0.9) { if (frontHole(vLP.zy)) discard; } }`;
const GLSL_COLOR = `{
  vec3 white = vec3(0.93, 0.94, 0.95), silver = vec3(0.66, 0.69, 0.72), c = white;
  bool sideF = abs(vLN.z) > abs(vLN.x); float u = sideF ? vLP.x : vLP.z, y = vLP.y;
  float wv = sin(u * 1.7) * 0.10 + sin(u * 0.83 + 1.0) * 0.05;       // wavy top edge of the colour band
  float yA = 1.45 + wv, yB = yA + 0.2 + wv * 0.5;
  if (y < 0.55) c = silver; else if (y < yA) c = uA; else if (y < yB) c = uB;
  if (KIND == 1 && vLN.x > 0.9) { if (y >= 0.55 && y < 2.02) c = uA; if (y >= 2.02 && y < 3.2 && abs(vLP.z) < 0.98) c = vec3(0.07); }
  if (sideF) {
    for (int k = 0; k < 2; k++) { float dx = doorX(k);
      if (abs(vLP.x - dx) < 0.012 && y > 0.95 && y < 3.15) c = vec3(0.10);                       // door leaf seam
      if (abs(abs(vLP.x - dx) - 0.78) < 0.02 && y > 0.95 && y < 3.15) c = vec3(0.16); }          // door frame
    for (int k = 0; k < 2; k++) { float cx = k == 0 ? CL * 0.28 : CL * 0.72; float r = length(vec2(vLP.x - cx, (y - 0.12) * 0.85));
      if (r < 0.27) { c = vec3(0.42, 0.45, 0.48); if (fract(y * 15.0) < 0.42) c *= 0.65; } }  // round louvred vents on the skirt
  }
  if (!gl_FrontFacing) c = vec3(0.95, 0.92, 0.84);   // inside of the shell = cabin wall
  diffuseColor.rgb = c;
}`;
// far-away version: windows are painted dark glass instead of cut out (there is no cabin behind them)
const GLSL_PAINT = `{ if ((abs(vLN.z) > 0.75 && sideHole(vLP.xy)) || (KIND == 1 && vLN.x > 0.9 && frontHole(vLP.zy))) diffuseColor.rgb = vec3(0.09, 0.13, 0.17); }`;
function skinMaterial(kind, L, U, solid = false) {
  const m = new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.34, metalness: 0.05, clearcoat: 0.7, clearcoatRoughness: 0.15, side: T.DoubleSide });
  if (opt.envMap) m.envMap = opt.envMap;
  if (opt.linear) m.envMapIntensity = 0.5;
  // without sRGB output / tone mapping the shell's own colours would burn out under the page's lights
  const gain = opt.linear ? "diffuseColor.rgb *= 0.6;" : "";
  m.onBeforeCompile = sh => {
    sh.uniforms.uA = U.a; sh.uniforms.uB = U.b; VARYINGS(sh);
    sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\n" + GLSL_COMMON(kind, L))
      .replace("#include <clipping_planes_fragment>", "#include <clipping_planes_fragment>\n" + (solid ? "" : GLSL_DISCARD))
      .replace("#include <color_fragment>", "#include <color_fragment>\n" + GLSL_COLOR + (solid ? GLSL_PAINT : "") + gain)
      .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\nif (!gl_FrontFacing) totalEmissiveRadiance += vec3(0.28);");
  };
  m.customProgramCacheKey = () => `skin${kind}${solid ? "s" : ""}`;
  return m;
}
// glass: transparent, reflective, kept only where the shell has a window hole
function glassMaterial(kind, L, front) {
  const m = new T.MeshPhysicalMaterial({ color: 0x0f1a24, roughness: 0.04, metalness: 0.1, transparent: true, opacity: 0.5, envMapIntensity: 1.8, depthWrite: false, side: T.DoubleSide });
  if (opt.envMap) m.envMap = opt.envMap;
  m.onBeforeCompile = sh => {
    VARYINGS(sh);
    sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\n" + GLSL_COMMON(kind, L))
      .replace("#include <clipping_planes_fragment>", "#include <clipping_planes_fragment>\n" + (front ? "if (!frontHole(vLP.zy)) discard;" : "if (!sideHole(vLP.xy)) discard;"));
  };
  m.customProgramCacheKey = () => `glass${kind}${front ? 1 : 0}`;
  return m;
}
function section(w, y0, y1, rt, rb, n = 10) {
  const pts = [], hw = w / 2; rt = Math.min(rt, hw, (y1 - y0) / 2); rb = Math.min(rb, hw, (y1 - y0) / 2);
  const arc = (cz, cy, r, a0, a1) => { for (let i = 0; i <= n; i++) { const a = a0 + (a1 - a0) * i / n; pts.push([cz + r * Math.cos(a), cy + r * Math.sin(a)]); } };
  arc(hw - rt, y1 - rt, rt, 0, Math.PI / 2); arc(-hw + rt, y1 - rt, rt, Math.PI / 2, Math.PI);
  arc(-hw + rb, y0 + rb, rb, Math.PI, 1.5 * Math.PI); arc(hw - rb, y0 + rb, rb, 1.5 * Math.PI, 2 * Math.PI);
  return pts;
}
// nose: quarter-round loft (rounded plan corners, roof and chin) ending in a flat front face; the rear end stays open
// n: segments per rounded corner of the cross-section, N: sections along the nose (fewer for the far-away version)
function skinGeometry(L, head, wScale = 1, n = 10, N = 12) {
  const Ln = S.noseLen, w0 = W * wScale, secs = [];
  secs.push({ x: 0, w: w0, top: S.yTop, bot: S.yBot, rt: S.roofR });
  secs.push({ x: head ? L - Ln : L, w: w0, top: S.yTop, bot: S.yBot, rt: S.roofR });
  if (head) for (let i = 1; i <= N; i++) { const th = i / N * Math.PI / 2, e = 1 - Math.cos(th);
    secs.push({ x: L - Ln + Ln * Math.sin(th), w: w0 - 0.9 * e, top: S.yTop - 0.55 * e, bot: S.yBot + 0.95 * e, rt: S.roofR - 0.7 * e }); }
  const pos = [], sideIdx = [], capIdx = [];
  secs.forEach(s => section(s.w, s.bot, s.top, s.rt, 0.18, n).forEach(([z, y]) => pos.push(s.x, y, z)));
  const P = 4 * (n + 1), skip = 3 * n + 2;    // segment `skip` is the flat bottom: left open so the beam passes under the car
  for (let s = 0; s < secs.length - 1; s++) for (let p = 0; p < P; p++) {
    if (p === skip) continue;
    const q = (p + 1) % P, a = s * P + p, b = s * P + q, c = (s + 1) * P + q, d = (s + 1) * P + p; sideIdx.push(a, b, c, a, c, d);
  }
  if (head) {   // front face: duplicated ring (sharp edge) + centre fan
    const last = secs.length - 1, base = pos.length / 3; let cy = 0;
    for (let p = 0; p < P; p++) { const i = last * P + p; pos.push(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]); cy += pos[i * 3 + 1]; }
    const ci = pos.length / 3; pos.push(secs[last].x, cy / P, 0);
    for (let p = 0; p < P; p++) capIdx.push(ci, base + p, base + (p + 1) % P);
  }
  const tn = (idx, i) => { const A = new T.Vector3().fromArray(pos, idx[i] * 3), B = new T.Vector3().fromArray(pos, idx[i + 1] * 3), C = new T.Vector3().fromArray(pos, idx[i + 2] * 3); return B.sub(A).cross(C.sub(A)); };
  const flip = idx => { for (let i = 0; i < idx.length; i += 3) { const t = idx[i + 1]; idx[i + 1] = idx[i + 2]; idx[i + 2] = t; } };
  if (tn(sideIdx, 0).z < 0) flip(sideIdx);            // the first side quad lies on the +z wall
  if (capIdx.length && tn(capIdx, 0).x < 0) flip(capIdx);
  const g = new T.BufferGeometry(); g.setAttribute("position", new T.Float32BufferAttribute(pos, 3)); g.setIndex(sideIdx.concat(capIdx)); g.computeVertexNormals(); return g;
}

/* ---------- small builders ---------- */
const add = (parent, geo, mat, x, y, z, o = {}) => { const m = new T.Mesh(geo, mat); m.position.set(x, y, z); if (o.rx) m.rotation.x = o.rx; if (o.ry) m.rotation.y = o.ry; if (o.rz) m.rotation.z = o.rz;
  m.castShadow = o.shadow !== false; m.receiveShadow = true; parent.add(m); return m; };
const box = (parent, w, h, d, mat, x, y, z, o) => add(parent, new T.BoxGeometry(w, h, d), mat, x, y, z, o);
// box whose UVs are in metres / tile, so a pattern keeps its size on long benches
function tbox(parent, w, h, d, mat, x, y, z, tile = 0.5) {
  const g = new T.BoxGeometry(w, h, d), uv = g.attributes.uv, dims = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
  for (let f = 0; f < 6; f++) for (let v = 0; v < 4; v++) { const i = f * 4 + v; uv.setXY(i, uv.getX(i) * dims[f][0] / tile, uv.getY(i) * dims[f][1] / tile); }
  return add(parent, g, mat, x, y, z);
}
const cyl = (parent, r, h, mat, x, y, z, axis = "y") => add(parent, new T.CylinderGeometry(r, r, h, 20), mat, x, y, z, axis === "z" ? { rx: Math.PI / 2 } : axis === "x" ? { rz: Math.PI / 2 } : {});
const tube = (parent, pts, r, mat) => add(parent, new T.TubeGeometry(new T.CatmullRomCurve3(pts.map(p => new T.Vector3(...p))), 24, r, 8, false), mat, 0, 0, 0);

// bake a group's meshes into one mesh per material (instanced meshes are kept as they are)
function mergeByMaterial(g) {
  g.updateMatrixWorld(true);
  const byMat = new Map(), keep = [], out = new T.Group();
  g.traverse(o => { if (!o.isMesh) return; if (o.isInstancedMesh) { keep.push(o); return; } if (!byMat.has(o.material)) byMat.set(o.material, []); byMat.get(o.material).push(o); });
  const v = new T.Vector3(), nm = new T.Matrix3();
  for (const [mat, list] of byMat) {
    let nv = 0, ni = 0;
    list.forEach(o => { const a = o.geometry.attributes.position; nv += a.count; ni += o.geometry.index ? o.geometry.index.count : a.count; });
    const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), idx = new Uint32Array(ni);
    let vo = 0, io = 0;
    for (const o of list) {
      const geo = o.geometry, p = geo.attributes.position, n = geo.attributes.normal, t = geo.attributes.uv;
      nm.getNormalMatrix(o.matrixWorld);
      for (let i = 0; i < p.count; i++) {
        v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld); v.toArray(pos, (vo + i) * 3);
        if (n) { v.fromBufferAttribute(n, i).applyMatrix3(nm).normalize(); v.toArray(nor, (vo + i) * 3); }
        if (t) { uv[(vo + i) * 2] = t.getX(i); uv[(vo + i) * 2 + 1] = t.getY(i); }
      }
      if (geo.index) for (let i = 0; i < geo.index.count; i++) idx[io++] = geo.index.getX(i) + vo;
      else for (let i = 0; i < p.count; i++) idx[io++] = vo + i;
      vo += p.count;
    }
    const mg = new T.BufferGeometry();
    mg.setAttribute("position", new T.BufferAttribute(pos, 3)); mg.setAttribute("normal", new T.BufferAttribute(nor, 3)); mg.setAttribute("uv", new T.BufferAttribute(uv, 2));
    mg.setIndex(new T.BufferAttribute(idx, 1));
    const m = new T.Mesh(mg, mat); m.castShadow = true; m.receiveShadow = true; out.add(m);
  }
  keep.forEach(o => { o.matrix.copy(o.matrixWorld); o.matrix.decompose(o.position, o.quaternion, o.scale); out.add(o); });
  return out;
}

/* ---------- car interior ---------- */
function interior(L, head) {
  const g = new T.Group(), f = S.floor, c = S.ceil, Li = head ? L - S.noseLen - 0.05 : L;   // Li: where the full-width cabin ends
  box(g, Li - 0.05, 0.06, 2.92, M.floor, Li / 2, f - 0.03, 0);                                  // floor
  box(g, Li - 0.05, 0.05, 2.7, M.ceil, Li / 2, c + 0.02, 0);                                    // ceiling
  if (head) { box(g, L - Li - 0.12, 0.06, 1.9, M.floor, (Li + L - 0.12) / 2, f - 0.03, 0); box(g, L - Li - 0.12, 0.05, 1.7, M.ceil, (Li + L - 0.12) / 2, c + 0.02, 0); }
  [-1, 1].forEach(s => box(g, Li - 3.4, 0.03, 0.22, M.strip, Li / 2, c - 0.02, s * 0.85));      // light strips
  [-1, 1].forEach(s => box(g, Li - 0.3, 0.16, 0.06, M.cream, Li / 2, c - 0.12, s * 1.36));      // upper wall band / duct
  // coupling-end wall with a passage opening (you can see down the train)
  box(g, 0.05, c - f, 1.0, M.cream, 0.03, (c + f) / 2, -0.95); box(g, 0.05, c - f, 1.0, M.cream, 0.03, (c + f) / 2, 0.95); box(g, 0.05, 0.9, 0.95, M.cream, 0.03, c - 0.45, 0);
  [-1, 1].forEach(s => cyl(g, 0.025, c - f, M.steel, 0.12, (c + f) / 2, s * 0.5));
  // benches between the door pairs (backrests under the window sills), with arched grab rails at the ends
  (head ? [[3.2, 8.4]] : [[3.2, 10.5]]).forEach(([x0, x1]) => [-1, 1].forEach(s => {
    const len = x1 - x0, cx = (x0 + x1) / 2;
    box(g, len, 0.42, 0.5, M.steel, cx, f + 0.21, s * 1.1);                                     // steel base
    tbox(g, len, 0.13, 0.56, M.seat, cx, f + 0.49, s * 1.13, 0.6);                              // cushion
    tbox(g, len, 0.42, 0.13, M.seat, cx, f + 0.72, s * 1.38, 0.6);                              // backrest
    tbox(g, 0.13, 0.36, 0.56, M.seat, x0, f + 0.68, s * 1.13, 0.6); tbox(g, 0.13, 0.36, 0.56, M.seat, x1, f + 0.68, s * 1.13, 0.6);
    [x0 - 0.12, x1 + 0.12].forEach((x, k) => tube(g, [[x, f + 0.45, s * 0.86], [x, f + 1.1, s * 0.95], [x, f + 1.7, s * 1.1], [x + (k ? 0.35 : -0.35), c - 0.15, s * 1.3]], 0.03, M.steel));
  }));
  // ceiling rails with straps (yellow band, orange ball, black ring)
  const sx0 = 3.2, sx1 = head ? 8.3 : 10.4, step = 0.6, cnt = Math.floor((sx1 - sx0) / step) + 1, rows = [-0.62, 0.62];
  rows.forEach(z => box(g, sx1 - sx0 + 1.0, 0.03, 0.03, M.steel, (sx0 + sx1) / 2, c - 0.09, z));
  const im = new T.InstancedMesh(new T.TorusGeometry(0.06, 0.013, 8, 16), M.dark, cnt * 2), ib = new T.InstancedMesh(new T.SphereGeometry(0.03, 10, 8), M.orange, cnt * 2),
        ia = new T.InstancedMesh(new T.BoxGeometry(0.03, 0.34, 0.008), M.strapBand, cnt * 2), o = new T.Object3D();
  let k = 0;
  rows.forEach(z => { for (let i = 0; i < cnt; i++) { const x = sx0 + i * step;
    o.rotation.set(0, 0, 0); o.position.set(x, c - 0.4, z); o.updateMatrix(); ia.setMatrixAt(k, o.matrix);
    o.position.set(x, c - 0.6, z); o.updateMatrix(); ib.setMatrixAt(k, o.matrix);
    o.rotation.y = Math.PI / 2; o.position.set(x, c - 0.72, z); o.updateMatrix(); im.setMatrixAt(k, o.matrix); k++; } });
  [im, ib, ia].forEach(m => { m.castShadow = false; g.add(m); });
  // door poles with orange caps, beside each door
  [1.95, head ? L - 5.6 : L - 1.95].forEach(dx => [-1, 1].forEach(sd => [-0.95, 0.95].forEach(off => {
    cyl(g, 0.022, c - f - 0.1, M.steel, dx + off, (c + f) / 2, sd * 1.41);
    [f + 0.15, f + 1.1, c - 0.15].forEach(y => add(g, new T.SphereGeometry(0.04, 10, 8), M.orange, dx + off, y, sd * 1.41));
  })));
  if (head) {   // cab: console with two screens and a lever, right-hand switch panel, observation bench on the left
    const cx = L - 0.9;
    box(g, 0.75, 0.82, 1.15, M.cab, cx, f + 0.41, 0.45); box(g, 0.75, 0.05, 1.2, M.cab, cx, f + 0.85, 0.45);
    add(g, new T.PlaneGeometry(0.34, 0.22), M.screen, cx - 0.05, f + 1.05, 0.25, { ry: -Math.PI / 2 });
    add(g, new T.PlaneGeometry(0.30, 0.22), M.screen2, cx - 0.05, f + 1.05, 0.68, { ry: -Math.PI / 2 });
    box(g, 0.18, 0.06, 0.12, M.steel, cx + 0.05, f + 0.92, 0.45);
    box(g, 0.5, 1.7, 0.32, M.cab, L - 2.0, f + 0.85, 1.28);
    for (let i = 0; i < 10; i++) box(g, 0.02, 0.06, 0.05, i % 3 ? M.orange : M.screen, L - 2.26, f + 0.3 + i * 0.14, 1.28 + (i % 2 ? 0.05 : -0.05));
    tbox(g, 1.3, 0.04, 1.0, M.check, L - 1.7, f + 0.005, -0.2, 0.6);
    box(g, 1.5, 0.4, 0.5, M.cab, L - 1.7, f + 0.2, -1.1); tbox(g, 1.5, 0.13, 0.56, M.dots, L - 1.7, f + 0.47, -1.13, 0.9); tbox(g, 1.5, 0.45, 0.13, M.dots, L - 1.7, f + 0.72, -1.38, 0.9);
  }
  return g;
}

/* ---------- one car ---------- */
function buildCar(L, head, U, o = {}) {
  const car = new T.Group(), kind = head ? 1 : 0, mats = [];
  const skin = new T.Mesh(skinGeometry(L, head), skinMaterial(kind, L, U)); skin.castShadow = true; skin.receiveShadow = true; car.add(skin); mats.push(skin.material);
  // side glass (both sides) and the front glass, in car-local coordinates so the hole test lines up
  const gs = new T.PlaneGeometry(L - 0.4, 1.6); gs.translate(L / 2, 2.4, HW + 0.006);
  const gs2 = gs.clone(); gs2.scale(1, 1, -1);
  const gm = glassMaterial(kind, L, false); [gs, gs2].forEach(gg => { const m = new T.Mesh(gg, gm); m.renderOrder = 2; car.add(m); }); mats.push(gm);
  if (head) { const gf = new T.PlaneGeometry(2.0, 1.2); gf.rotateY(Math.PI / 2); gf.translate(L + 0.006, 2.62, 0);
    const fm = glassMaterial(kind, L, true); const m = new T.Mesh(gf, fm); m.renderOrder = 2; car.add(m); mats.push(fm); }
  const parts = new T.Group();
  parts.add(interior(L, head));
  [2.5, L * 0.5 + 1.2, L - (head ? 4.2 : 2.5)].forEach(x => box(parts, 1.6, 0.16, 1.0, M.roofUnit, x, S.yTop + 0.06, 0));   // roof units
  // bogies: deck under the floor, running tyres on the beam, guide wheels + side frames along the beam
  [2.7, L - 2.7].forEach(bx => {
    box(parts, 2.6, 0.14, 1.0, M.dark, bx, S.floor - 0.12, 0);
    [-0.85, 0.85].forEach(dx => cyl(parts, 0.44, 0.34, M.rubber, bx + dx, 0.44, 0, "z"));
    [-1, 1].forEach(s => { box(parts, 2.4, 0.85, 0.1, M.dark, bx, 0.38, s * (S.beamW / 2 + 0.3)); [-0.8, 0.8].forEach(dx => cyl(parts, 0.2, 0.3, M.rubber, bx + dx, -0.2, s * (S.beamW / 2 + 0.16))); });
  });
  if (head) {   // oval headlights, coupler, destination strip
    [-1, 1].forEach(s => { const l = new T.Mesh(new T.SphereGeometry(1, 20, 12), M.lamp); l.scale.set(0.05, 0.12, 0.2); l.position.set(L + 0.005, 1.28, s * 0.74); parts.add(l); });
    cyl(parts, 0.11, 0.3, M.steel, L + 0.05, 0.22, 0, "x"); box(parts, 0.14, 0.24, 0.9, M.dark, L - 0.02, 0.28, 0);
    box(parts, 0.04, 0.12, 0.7, M.strip, L + 0.005, 3.28, 0);
  }
  car.add(o.merge ? mergeByMaterial(parts) : parts);
  car.userData.mats = mats;
  return car;
}
// far-away car: coarse shell, painted windows, headlights; no cabin, glass or bogies
const LAMP_GEO = new T.SphereGeometry(1, 8, 6);
function buildSimpleCar(L, head, U) {
  const car = new T.Group(), kind = head ? 1 : 0;
  car.add(new T.Mesh(skinGeometry(L, head, 1, 2, 3), skinMaterial(kind, L, U, true)));
  if (head) [-1, 1].forEach(s => { const l = new T.Mesh(LAMP_GEO, M.lamp); l.scale.set(0.05, 0.12, 0.2); l.position.set(L + 0.005, 1.28, s * 0.74); car.add(l); });
  car.userData.mats = [car.children[0].material];
  return car;
}
// gangway: a slightly narrower open tube joining the car ends
const gangwayGeo = [null, null];
function gangway(simple) {
  const k = simple ? 1 : 0;
  if (!gangwayGeo[k]) gangwayGeo[k] = simple ? skinGeometry(S.gap + 0.04, false, 0.94, 2) : skinGeometry(S.gap + 0.04, false, 0.94);
  const m = new T.Mesh(gangwayGeo[k], M.bellows); m.castShadow = true; return m;
}

/* ---------- train: 6 cars, front at +x ---------- */
// cars[i] = { start, L, head }: car i spans x = start .. start + L (x = 0 is the middle of the train)
function layout() {
  const lens = []; for (let i = 0; i < S.cars; i++) lens.push(i === 0 || i === S.cars - 1 ? S.headLen : S.midLen);
  const total = lens.reduce((a, b) => a + b, 0) + S.gap * (S.cars - 1), cars = []; let x = -total / 2;
  lens.forEach((L, i) => { cars.push({ start: x, L, head: i === 0 || i === S.cars - 1 }); x += L + S.gap; });
  return { cars, length: total };
}
// slots[i]: a Group at the car's rear end (x = cars[i].start), facing +x; the car sits inside it
// (car 0, the rear head car, is turned round inside its slot). gangways[i] joins car i and car i + 1.
function buildTrain(U, o = {}) {
  const { cars, length } = layout(), group = new T.Group(), slots = [], gangways = [], mats = [];
  cars.forEach(({ start, L, head }, i) => {
    const car = o.simple ? buildSimpleCar(L, head, U) : buildCar(L, head, U, o);
    if (i === 0) { car.rotation.y = Math.PI; car.position.x = L; }
    const slot = new T.Group(); slot.position.x = start; slot.add(car); group.add(slot); slots.push(slot); mats.push(...car.userData.mats);
    if (i < cars.length - 1) { const gw = gangway(o.simple); gw.position.x = start + L - 0.02; group.add(gw); gangways.push(gw); }
  });
  mats.push(M.bellows);
  return { group, slots, gangways, cars, length, mats };
}

return { S, SCHEMES, M, uniforms, buildCar, buildSimpleCar, gangway, buildTrain, layout, skinGeometry, box };
}
return { create };
})();
