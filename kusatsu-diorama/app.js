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
  e.currentTarget.textContent = on ? '建物:表示' : '建物:非表示';
});
$('#spin').addEventListener('click', (e) => { controls.autoRotate = !controls.autoRotate; e.currentTarget.classList.toggle('on', controls.autoRotate); });
renderer.domElement.addEventListener('pointerdown', () => { tween = null; });
renderer.domElement.addEventListener('wheel', () => { tween = null; }, { passive: true });

// ---- 読み込み
const draco = new DRACOLoader().setDecoderPath('./lib/draco/');
const loader = new GLTFLoader().setDRACOLoader(draco);
const FILES = ['terrain.glb', 'yubatake.glb', 'buildings_A.glb', 'buildings_B.glb', 'buildings_C.glb', 'buildings_D.glb'];
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
    if (/^Roads|^Stairs/.test(o.name)) { m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -2; }
    if (/^Yb_Pave/.test(o.name)) { m.polygonOffset = true; m.polygonOffsetFactor = -3; m.polygonOffsetUnits = -3; }   // 湯畑の周回路(地形に重ねる)
    if (/^Yb_Flow|^Yb_Splash/.test(o.name)) { m.roughness = 0.35; o.castShadow = false; }
    if (/^Water/.test(o.name)) { m.roughness = 0.12; m.metalness = 0.0; m.envMapIntensity = 1; o.castShadow = false; }
    if (m.vertexColors === undefined) m.vertexColors = true;
  });
}
const progress = () => { $('#msg').textContent = `読み込み中… ${done}/${FILES.length}`; };
progress();
await Promise.all(FILES.map((f) => loader.loadAsync('./models/' + f + '?v=' + (qs.get('v') || '5')).then((g) => {
  prep(g.scene, f); world.add(g.scene); loaded[f] = g.scene; done++; progress();
}).catch((e) => { console.error('load fail', f, e); done++; progress(); })));

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
