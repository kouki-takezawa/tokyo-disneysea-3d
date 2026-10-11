// 草津温泉 湯畑ジオラマ ビューア(フェーズ2〜3)。three r170 をローカル配置。
// 座標: three の x=東、y=標高-1153、z=-北(Blender の x, z, -y)。
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const qs = new URLSearchParams(location.search);
const $ = (s) => document.querySelector(s);
let saved = null;
try { saved = localStorage.getItem('kd_quality'); } catch (e) { /* 無効でも動く */ }
const coarse = matchMedia('(pointer:coarse)').matches || innerWidth < 700;
const QUALITY = qs.get('q') || saved || (coarse ? 'light' : 'standard');
// 品質段階: 軽量=影なし・等倍ピクセル・アンチエイリアスなし / 標準=影(4096)・最大2倍ピクセル・アンチエイリアス
const Q = {
  light:    { dpr: 1,   shadow: 0,    aa: false, far: 1600 },
  standard: { dpr: 2,   shadow: 4096, aa: true,  far: 2400 },
}[QUALITY] || { dpr: 1, shadow: 0, aa: false, far: 1600 };
$('#quality').value = QUALITY in { light: 1, standard: 1 } ? QUALITY : 'standard';
$('#quality').addEventListener('change', (e) => {
  try { localStorage.setItem('kd_quality', e.target.value); } catch (er) { /* */ }
  const u = new URL(location.href); u.searchParams.set('q', e.target.value); location.href = u.toString();
});

const renderer = new THREE.WebGLRenderer({ antialias: Q.aa, alpha: true, powerPreference: 'high-performance', preserveDrawingBuffer: qs.has('shot') });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, Q.dpr));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = Q.shadow > 0;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 1, Q.far);

// ---- ライティング(太陽 + 空)
scene.add(new THREE.HemisphereLight(0xdfeaf6, 0x8a7d66, 1.6));
const sun = new THREE.DirectionalLight(0xfff1dc, 3.0);
sun.position.set(-160, 260, 120);        // 南西(+z=南)の高い位置
sun.target.position.set(0, 0, 0);
scene.add(sun, sun.target);
if (Q.shadow) {
  sun.castShadow = true;
  sun.shadow.mapSize.set(Q.shadow, Q.shadow);
  const s = sun.shadow.camera;
  s.left = -250; s.right = 250; s.top = 250; s.bottom = -250; s.near = 10; s.far = 900;
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.35;
}

// ---- 操作
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 4;
controls.maxDistance = 750;
controls.minPolarAngle = 0.05;
controls.maxPolarAngle = Math.PI * 0.5 + 0.05;
controls.screenSpacePanning = false;
controls.autoRotateSpeed = 1.4;
controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
controls.addEventListener('change', () => { clampTarget(); });
function clampTarget() {
  const t = controls.target;
  const r = Math.hypot(t.x, t.z);
  if (r > 200) { t.x *= 200 / r; t.z *= 200 / r; }
  t.y = Math.min(Math.max(t.y, -10), 60);
}

// 視点: 位置 pos、注視点 tgt(three 座標)
const VIEWS = {
  all:      { pos: [300, 250, 400],  tgt: [0, -4, 0] },
  yubatake: { pos: [26, 66, 40],     tgt: [1, -1, -5] },
  yutaki:   { pos: [9, 3.5, -41],    tgt: [12, -2.5, -22] },   // 北の湯滝と見学デッキ(R 0:03 の向き)
  yutoi:    { pos: [-15, 7, 40],     tgt: [2, -0.5, -4] },     // 湯樋の列を南から(K 8:39 の向き)
  stairs:   { pos: [-8, 27, 54],     tgt: [-76, 12, 96] },
  nishi:    { pos: [-30, 30, -20],   tgt: [-100, 6, -60] },
};
let tween = null;
function goView(name, instant) {
  const v = VIEWS[name]; if (!v) return;
  document.querySelectorAll('#bar [data-view]').forEach((b) => b.classList.toggle('on', b.dataset.view === name));
  const p1 = new THREE.Vector3(...v.pos), t1 = new THREE.Vector3(...v.tgt);
  const asp = innerWidth / innerHeight;
  if (asp < 1) p1.sub(t1).multiplyScalar(Math.min(2.4, Math.pow(1 / asp, 1.0))).add(t1);   // 縦長画面は少し引く
  if (instant) { camera.position.copy(p1); controls.target.copy(t1); controls.update(); return; }
  tween = { t: 0, p0: camera.position.clone(), t0: controls.target.clone(), p1, t1 };
}
document.querySelectorAll('#bar [data-view]').forEach((b) => b.addEventListener('click', () => goView(b.dataset.view)));
$('#bld').addEventListener('click', (e) => {
  const on = !e.currentTarget.classList.toggle('off');
  for (const f of FILES) if (f.startsWith('buildings') && loaded[f]) loaded[f].visible = on;
  signGroup.visible = on;
  e.currentTarget.textContent = on ? '建物:表示' : '建物:非表示';
});
$('#spin').addEventListener('click', (e) => { controls.autoRotate = !controls.autoRotate; e.currentTarget.classList.toggle('on', controls.autoRotate); });
renderer.domElement.addEventListener('pointerdown', () => { tween = null; });
renderer.domElement.addEventListener('wheel', () => { tween = null; }, { passive: true });

// ---- 読み込み
const draco = new DRACOLoader().setDecoderPath('./lib/draco/');
const loader = new GLTFLoader().setDRACOLoader(draco);
const FILES = ['terrain.glb', 'yubatake.glb', 'buildings_A.glb', 'buildings_B.glb', 'buildings_C.glb', 'buildings_D.glb', 'props.glb'];
const world = new THREE.Group();
scene.add(world);
const loaded = {};
let done = 0;
function prep(root, name) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const m = o.material;
    o.castShadow = Q.shadow > 0 && !/Roads|Water|Yb_Pave|Yb_Bed/.test(o.name);
    o.receiveShadow = Q.shadow > 0;
    if (/^Roads|^Stairs|^Props_wall/.test(o.name)) { m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -2; }
    if (/^Yb_Pave/.test(o.name)) { m.polygonOffset = true; m.polygonOffsetFactor = -3; m.polygonOffsetUnits = -3; }   // 湯畑の周回路(地形に重ねる)
    if (/^Yb_Flow|^Yb_Splash/.test(o.name)) { m.roughness = 0.35; o.castShadow = false; }
    if (/^Water/.test(o.name)) { m.roughness = 0.12; m.metalness = 0.0; m.envMapIntensity = 1; o.castShadow = false; }
    if (m.vertexColors === undefined) m.vertexColors = true;
  });
}
const progress = () => { $('#msg').textContent = `読み込み中… ${done}/${FILES.length}`; };
progress();
await Promise.all(FILES.map((f) => loader.loadAsync('./models/' + f + '?v=' + (qs.get('v') || '9')).then((g) => {
  prep(g.scene, f); world.add(g.scene); loaded[f] = g.scene; done++; progress();
}).catch((e) => { console.error('load fail', f, e); done++; progress(); })));


// ---- 看板・幟・標識の文字(signs.json): canvas に描いた文字を板の面に貼る(フェーズ9)
const signGroup = new THREE.Group();
signGroup.name = 'Signs';
world.add(signGroup);
const SIGN_FONT = '"Yu Mincho","Hiragino Mincho ProN","Noto Serif JP","MS PMincho",serif';
function signCanvas(s, back) {
  const ppm = Math.min(320, 1024 / Math.max(s.w, s.h));
  const cw = Math.max(16, Math.ceil(s.w * ppm)), ch = Math.max(16, Math.ceil(s.h * ppm));
  const cv = document.createElement('canvas'); cv.width = cw; cv.height = ch;
  const g = cv.getContext('2d');
  const solid = s.kind === 'road' || s.kind === 'nobori';
  if (back) { g.fillStyle = s.back || '#8d9397'; g.fillRect(0, 0, cw, ch); return cv; }
  if (solid) {
    g.fillStyle = s.bg;
    if (s.shape === 'circle') { g.beginPath(); g.arc(cw / 2, ch / 2, Math.min(cw, ch) / 2, 0, 7); g.fill(); g.strokeStyle = '#f4f6f8'; g.lineWidth = cw * 0.07; g.beginPath(); g.arc(cw / 2, ch / 2, Math.min(cw, ch) * 0.42, 0, 7); g.stroke(); }
    else if (s.shape === 'tri') {
      g.fillStyle = '#ffffff'; g.beginPath(); g.moveTo(0, 0); g.lineTo(cw, 0); g.lineTo(cw / 2, ch); g.closePath(); g.fill();
      g.fillStyle = s.bg; g.beginPath(); g.moveTo(cw * 0.14, ch * 0.07); g.lineTo(cw * 0.86, ch * 0.07); g.lineTo(cw / 2, ch * 0.78); g.closePath(); g.fill();
    } else g.fillRect(0, 0, cw, ch);
    if (s.border) { g.strokeStyle = s.fg; g.lineWidth = Math.max(2, cw * 0.012); g.strokeRect(cw * 0.03, ch * 0.05, cw * 0.94, ch * 0.9); }
  }
  g.fillStyle = s.fg; g.textAlign = 'center'; g.textBaseline = 'middle';
  if (s.arrow) {
    g.beginPath(); const m = Math.min(cw, ch);
    g.moveTo(cw / 2 - m * 0.3, ch / 2 - m * 0.07); g.lineTo(cw / 2 + m * 0.05, ch / 2 - m * 0.07); g.lineTo(cw / 2 + m * 0.05, ch / 2 - m * 0.2);
    g.lineTo(cw / 2 + m * 0.3, ch / 2); g.lineTo(cw / 2 + m * 0.05, ch / 2 + m * 0.2); g.lineTo(cw / 2 + m * 0.05, ch / 2 + m * 0.07); g.lineTo(cw / 2 - m * 0.3, ch / 2 + m * 0.07);
    g.closePath(); g.fill(); return cv;
  }
  const vertical = s.vertical || s.w < s.h * 0.7;
  if (s.shape === 'tri') {
    g.font = `bold ${Math.round(ch * 0.2)}px ${SIGN_FONT}`; g.fillText(s.text, cw / 2, ch * 0.3, cw * 0.6); return cv;
  }
  if (vertical) {
    const parts = s.text.split(' ');
    const big = parts[parts.length - 1], small = parts.length > 1 ? parts.slice(0, -1).join('') : '';
    const n = [...big].length + (small ? [...small].length * 0.6 + 0.4 : 0);
    const fs = Math.min(cw * 0.78, ch * 0.92 / n);
    let y = (ch - n * fs) / 2;
    if (small) { g.font = `bold ${Math.round(fs * 0.6)}px ${SIGN_FONT}`; for (const c of small) { g.fillText(c, cw / 2, y + fs * 0.3); y += fs * 0.6; } y += fs * 0.4; }
    g.font = `bold ${Math.round(fs)}px ${SIGN_FONT}`;
    for (const c of big) { g.fillText(c, cw / 2, y + fs / 2); y += fs; }
  } else {
    const lines = s.text.split('\n');
    let fs = Math.min(ch * 0.74 / lines.length, 200);
    g.font = `bold 100px ${SIGN_FONT}`;
    const wmax = Math.max(...lines.map((l) => g.measureText(l).width)) / 100;
    fs = Math.min(fs, cw * 0.92 / wmax);
    g.font = `bold ${Math.round(fs)}px ${SIGN_FONT}`;
    lines.forEach((l, i) => g.fillText(l, cw / 2, ch / 2 + (i - (lines.length - 1) / 2) * fs * 1.12));
  }
  return cv;
}
function signPlane(s, flip, back) {
  const tex = new THREE.CanvasTexture(signCanvas(s, back));
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const m = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85, metalness: 0, transparent: true, alphaTest: 0.03, depthWrite: false,
    polygonOffset: true, polygonOffsetFactor: -6, polygonOffsetUnits: -6 });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(s.w, s.h), m);
  // Blender (x, y, z) -> three (x, z, -y)
  const R = new THREE.Vector3(s.right[0], s.right[2], -s.right[1]), N = new THREE.Vector3(s.normal[0], s.normal[2], -s.normal[1]);
  const C0 = new THREE.Vector3(s.center[0], s.center[2], -s.center[1]);
  const off = (s.th || 0) + 0.004;
  if (flip) { R.negate(); N.negate(); }
  mesh.matrixAutoUpdate = false;
  mesh.matrix.makeBasis(R, new THREE.Vector3(0, 1, 0), N).setPosition(C0.clone().addScaledVector(N, off));
  mesh.receiveShadow = false;
  return mesh;
}
try {
  const signs = await (await fetch('./models/signs.json?v=' + (qs.get('v') || '9'))).json();
  for (const s of signs) {
    signGroup.add(signPlane(s, false, false));
    if (s.two) signGroup.add(signPlane(s, true, !!s.back));
  }
} catch (e) { console.error('signs.json', e); }

// 地面の高さ(カメラが地面に潜らないように)
const GN = 202, GC = 2;   // 2 m 格子の高さ表(頂点の最大値)
const gridY = new Float32Array(GN * GN).fill(-999);
world.traverse((o) => {
  if (!(o.isMesh && o.name === 'Terrain')) return;
  const p = o.geometry.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const gx = Math.round((p.getX(i) + 202) / GC), gz = Math.round((p.getZ(i) + 202) / GC);
    if (gx < 0 || gz < 0 || gx >= GN || gz >= GN) continue;
    const k = gz * GN + gx; if (p.getY(i) > gridY[k]) gridY[k] = p.getY(i);
  }
});
function groundY(x, z) {
  const gx = Math.round((x + 202) / GC), gz = Math.round((z + 202) / GC);
  if (gx < 0 || gz < 0 || gx >= GN || gz >= GN) return -999;
  let y = gridY[gz * GN + gx];
  for (let d = 1; y < -900 && d < 4; d++) y = Math.max(y, gridY[Math.min(GN - 1, gz + d) * GN + gx], gridY[Math.max(0, gz - d) * GN + gx]);
  return y;
}

goView(qs.get('view') || 'all', true);
if (qs.has('spin')) { controls.autoRotate = true; $('#spin').classList.add('on'); }
$('#msg').classList.add('hide');

// ---- 描画
function resize() {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  // 縦長の画面では視野を広げて全景が収まるように
  camera.fov = innerWidth < innerHeight ? 52 : 38;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize); resize();

const clock = new THREE.Clock();
let frames = 0, fpsT = 0, fps = 0;
function loop() {
  const dt = Math.min(clock.getDelta(), 0.1);
  if (tween) {
    tween.t = Math.min(1, tween.t + dt / 1.4);
    const k = tween.t * tween.t * (3 - 2 * tween.t);
    camera.position.lerpVectors(tween.p0, tween.p1, k);
    controls.target.lerpVectors(tween.t0, tween.t1, k);
    if (tween.t >= 1) tween = null;
  }
  controls.update();
  // 地面より下に潜らない
  const gy = groundY(camera.position.x, camera.position.z);
  const lim = Math.hypot(camera.position.x, camera.position.z) <= 200 ? gy + 3 : -999;
  if (camera.position.y < lim) camera.position.y = lim;
  renderer.render(scene, camera);
  frames++; fpsT += dt;
  if (fpsT > 1) { fps = frames / fpsT; frames = 0; fpsT = 0; if (qs.has('stats')) showStats(); }
  requestAnimationFrame(loop);
}
function showStats() {
  const i = renderer.info;
  const el = $('#stats'); el.style.display = 'block';
  el.textContent = `fps ${fps.toFixed(0)}  q=${QUALITY}\ncalls ${i.render.calls}  tris ${i.render.triangles}\ngeom ${i.memory.geometries}  tex ${i.memory.textures}`;
}
window.__v = {
  THREE, scene, camera, controls, renderer, goView, groundY, VIEWS,
  jump(pos, tgt) { tween = null; camera.position.set(...pos); controls.target.set(...tgt); controls.update(); },
  stats() { const i = renderer.info; return { calls: i.render.calls, tris: i.render.triangles, geoms: i.memory.geometries, fps }; },
};
window.__ready = true;
loop();
