// Far (low-detail) copies of the mock's heavy models: models/web/<id>.json -> models/web/<id>_far.json
//   node tools/lod/lod.mjs <models/web dir> id [id ...]
// The page shows the far copy until the camera comes near the model (mock_template.html, LOD_NEAR), so phones
// never hold every full model at once. Small parts that cannot be seen from far away are dropped (DROP), the rest is
// welded and simplified (meshoptimizer, error as a fraction of each mesh's size), then Draco-compressed and embedded
// as a data URI like the other web copies (src/compress_models.py runs this after compressing).
import fs from "node:fs";
import path from "node:path";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { weld, prune, dedup, draco, compactPrimitive } from "@gltf-transform/functions";
import { MeshoptSimplifier } from "meshoptimizer";
import draco3d from "draco3dgltf";

// mesh names (after the part prefix) not worth drawing from 150 m+: curtains, lamps, railings, lettering, shop interiors
const DROP = /_(hotel_)?(curtain|lamp|bulb|iron|bronze|gilt|brass|letters|clock|fl(pink|purple|white)|flowers?_\w+|flower_\w+|screen|insulator|copper_wire|wbz_(floor|m_\w+|display|shopglass|door|brass|leaf)|pb_display|hotel_leaf|hedge)$/;
const ERROR = 0.004;    // simplification error, fraction of the mesh radius
const ERROR_OF = [[/_hotel_gold$/, 0.012]];   // the hotel's window surrounds: nearly the wall colour, gone from far away
// meshoptimizer's simplifier with Prune: also removes separate small pieces (balusters, finials, window bars) below the
// error, which the plain simplifier cannot reduce; replaces gltf-transform's simplify()
const simplifyPrune = () => (doc) => {
  MeshoptSimplifier.useExperimentalFeatures = true;
  for (const mesh of doc.getRoot().listMeshes()) for (const prim of mesh.listPrimitives()) {
    const idx = prim.getIndices(), pos = prim.getAttribute("POSITION");
    if (!idx || idx.getCount() < 3) continue;
    const err = (ERROR_OF.find(([re]) => re.test(mesh.getName())) || [0, ERROR])[1];
    const ind = new Uint32Array(idx.getArray()), P = new Float32Array(pos.getArray());
    const [out] = MeshoptSimplifier.simplify(ind, P, 3, 0, err, ["Prune"]);
    if (!out.length) { prim.dispose(); continue; }
    idx.setArray(pos.getCount() > 65535 ? out : new Uint16Array(out));
    compactPrimitive(prim);
  }
};

const [dir, ...ids] = process.argv.slice(2);
await MeshoptSimplifier.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  "draco3d.decoder": await draco3d.createDecoderModule(),
  "draco3d.encoder": await draco3d.createEncoderModule(),
});
for (const id of ids) {
  const src = path.join(dir, id + ".json"), dst = path.join(dir, id + "_far.json");
  const json = JSON.parse(fs.readFileSync(src, "utf8"));
  const resources = {};
  for (const b of json.buffers || []) if (b.uri && b.uri.startsWith("data:")) {
    const name = `buf${Object.keys(resources).length}.bin`;
    resources[name] = new Uint8Array(Buffer.from(b.uri.split(",")[1], "base64")); b.uri = name;
  }
  const doc = await io.readJSON({ json, resources });
  const root = doc.getRoot();
  let tris0 = 0, tris1 = 0;
  const count = () => root.listMeshes().reduce((n, m) => n + m.listPrimitives().reduce((k, p) => k + (p.getIndices() ? p.getIndices().getCount() : p.getAttribute("POSITION").getCount()) / 3, 0), 0);
  tris0 = count();
  for (const node of root.listNodes()) {
    const m = node.getMesh();
    if (m && DROP.test(m.getName() || node.getName())) { node.dispose(); }
  }
  await doc.transform(prune(), dedup(), weld(), simplifyPrune(), prune(),
    draco({ quantizePosition: 16 }));
  tris1 = count();
  const out = await io.writeJSON(doc, { format: "gltf" });
  for (const b of out.json.buffers || []) if (b.uri && out.resources[b.uri]) {
    b.uri = "data:application/octet-stream;base64," + Buffer.from(out.resources[b.uri]).toString("base64");
  }
  fs.writeFileSync(dst, JSON.stringify(out.json));
  const mb = f => (fs.statSync(f).size / 1e6).toFixed(2);
  console.log(`[lod] ${id}: ${Math.round(tris0).toLocaleString()} -> ${Math.round(tris1).toLocaleString()} triangles, ${mb(src)} -> ${mb(dst)} MB`);
}
