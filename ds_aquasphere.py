"""ディズニーシー・アクアスフィア — detailed build (Blender 5.2), replacing the draft sphere.

User spec (2026-09-23): globe diameter 8 m on a 2 m pedestal; the bench-height rim
around the pool is 0.40 m. Public sources: total height ~10 m (2 + 8 OK), water
runs over the surface, it turns counter-clockwise once every ~3 min 30 s.
Reference photo: output/.. (user-supplied) - teal pool, carved beige rim, beige
paved ring with dark round inlays, blue-grey plaza with white radial lines,
low rectangular stone blocks, black lamp posts, MiraCosta behind (to the west).

Data
  OSM way 72388087 (natural=water, amenity=fountain, barrier=fence): centre
  (360.85, 36.37), radius 11.16 m (16-point circle). Unnamed building 217618801
  on the same circle is skipped by ds_buildings (LANDMARK_SKIP_IDS).
  Levels (water tab, plateau_data/disneysea_water.json): ground -0.39, water -0.64,
  depth 0.30, relative to datum 5.29 m ASL. All heights below are RELATIVE to
  ground_z so the same build fits the flat Blender draft (ground_z=0).
  Globe: NOAA ETOPO 0.2 deg (public domain) -> plateau_data/globe/globe_color.png,
  globe_height.png (16 bit), globe_landmask.png (equirectangular 4096x2048).

ASSUMPTIONS (confirm with the user): pedestal 2 m is measured from the plaza,
the 0.40 m applies to the pool rim and to the loose stone blocks, blocks are
tangential, 16 of them at r 17 m; 12 radial white lines; 8 lamps at r 19 m.
"""
import math, pathlib, json
try:  # SPEC and mock_geometry() also work in plain Python (export_mock.py)
    import bpy, bmesh
    from mathutils import Vector, Matrix
except ImportError:
    bpy = bmesh = Vector = Matrix = None

ROOT = pathlib.Path(__file__).resolve().parent
GLOBE_DIR = ROOT / "plateau_data" / "globe"

SPEC = dict(
    cx=360.85, cy=36.37, pool_r=11.16, rim_w=0.60, rim_h=0.40,
    ground_rel=-0.39, water_below_ground=0.25, pool_depth=0.30,
    globe_d=8.0, pedestal_h=2.0, tilt_deg=23.4, face_lon_deg=15.0, face_offset_deg=55.0,   # offset calibrated on the first render (Indian Ocean was in front)
    rev_seconds=210.0,
    ring_w=2.4, inlays=24, inlay_r=0.30,
    blocks=16, block_size=(2.0, 0.7, 0.40), block_r=17.0,
    plaza_lines=12, plaza_line_w=0.25, plaza_r=30.0,
    lamps=8, lamp_r=19.0, lamp_h=3.6,
)


def _water_levels():
    """Take the pool level from the water tab if it exported one."""
    f = ROOT / "plateau_data" / "disneysea_water.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        for b in d.get("bodies", []):
            if str(b.get("id", "")).endswith("72388087") and "level" in b:
                return float(b["level"]), float(b.get("ground", SPEC["ground_rel"]))
    except Exception:
        pass
    return None


def coastlines(step=5):
    """Coastline segments (lon, lat degrees) from the ETOPO grid at step*0.2 deg (0 m contour), cached."""
    cache = GLOBE_DIR / f"coast_{step}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    lines = (GLOBE_DIR / "etopo_12.asc").read_text().splitlines()
    rows = [[float(v) for v in l.split()] for l in lines[6:] if l.strip()]
    z = [r[:-1:step] for r in rows[::step]]                       # north row first, lon -180..180
    ny, nx = len(z), len(z[0]); dlon, dlat = 360.0 / nx, 180.0 / (ny - 1)
    P = lambda i, j: (-180 + j * dlon, 90 - i * dlat)
    segs = []
    for i in range(ny - 1):
        for j in range(nx):
            jj = (j + 1) % nx
            c = [((i, j), z[i][j]), ((i, jj), z[i][jj]), ((i + 1, jj), z[i + 1][jj]), ((i + 1, j), z[i + 1][j])]
            pts = []
            for q in range(4):
                (a, va), (b, vb) = c[q], c[(q + 1) % 4]
                if (va > 0) != (vb > 0):
                    t = va / (va - vb)
                    (lo1, la1), (lo2, la2) = P(*a), P(*b)
                    if b[1] == 0 and a[1] == nx - 1: lo2 += 360
                    if a[1] == 0 and b[1] == nx - 1: lo1 += 360
                    pts.append((lo1 + (lo2 - lo1) * t, la1 + (la2 - la1) * t))
            for q in range(0, len(pts) - 1, 2):
                segs += [round(pts[q][0], 2), round(pts[q][1], 2), round(pts[q + 1][0], 2), round(pts[q + 1][1], 2)]
    cache.write_text(json.dumps(segs))
    return segs


def mock_geometry(ground_rel=None):
    """Same layout as build(), as plain numbers for the outline mock (heights relative to the DEM datum)."""
    S = SPEC
    lv = _water_levels()
    g = S["ground_rel"] if ground_rel is None else ground_rel
    wz = g - S["water_below_ground"] if lv is None else g + (lv[0] - lv[1])
    r_out = S["pool_r"]; r_ring = r_out + S["ring_w"]
    ring_mid = r_out + S["ring_w"] / 2
    pol = lambda r, a: [round(S["cx"] + r * math.cos(a), 2), round(S["cy"] + r * math.sin(a), 2)]
    lines, patches = [], []
    for k in range(S["plaza_lines"]):
        a = 2 * math.pi * k / S["plaza_lines"]
        lines.append(pol(r_ring, a) + pol(S["plaza_r"], a))
        patches += [pol(r_ring + 3.0, a), pol(r_ring + 9.0, a)]
    blocks = []
    bx, by, bz = S["block_size"]
    for k in range(S["blocks"]):
        a = 2 * math.pi * (k + 0.5) / S["blocks"]
        c = (S["cx"] + S["block_r"] * math.cos(a), S["cy"] + S["block_r"] * math.sin(a))
        t = (-math.sin(a), math.cos(a)); n = (math.cos(a), math.sin(a))   # long side tangential
        blocks.append([[round(c[0] + sx * bx / 2 * t[0] + sy * by / 2 * n[0], 2), round(c[1] + sx * bx / 2 * t[1] + sy * by / 2 * n[1], 2)]
                       for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    ent = math.atan2(2.0 - S["cy"], 390.0 - S["cx"])
    return {"cx": S["cx"], "cy": S["cy"], "g": g, "water": round(wz, 2), "depth": S["pool_depth"],
            "pool_r": r_out, "rim_w": S["rim_w"], "rim_h": S["rim_h"], "ring_r": r_ring, "plaza_r": S["plaza_r"],
            "inlays": [pol(ring_mid, 2 * math.pi * (k + 0.5) / S["inlays"]) for k in range(S["inlays"])], "inlay_r": S["inlay_r"],
            "lines": lines, "line_w": S["plaza_line_w"], "patches": patches, "patch_r": 0.9,
            "blocks": blocks, "block_h": bz,
            "lamps": [pol(S["lamp_r"], 2 * math.pi * k / S["lamps"]) for k in range(S["lamps"])], "lamp_h": S["lamp_h"],
            "ped_h": S["pedestal_h"], "foam_r": [2.4, 1.2],
            # globe orientation = build(): world = Rz(axis) . Ry(tilt) . Rz(spin) . p_local, p_local angle = longitude
            "globe": {"r": S["globe_d"] / 2, "cz": round(g + S["pedestal_h"] + S["globe_d"] / 2, 2),
                      "axis": round(ent, 4), "tilt": round(math.radians(S["tilt_deg"]), 4),
                      "spin": round(math.radians(-S["face_lon_deg"] + S["face_offset_deg"]), 4)},
            "coast": coastlines()}


# ---------------------------------------------------------------- globe textures (plain Python)
def generate_textures(w=4096):
    """ETOPO 0.2 deg -> globe_color.png / globe_height.png (16 bit) / globe_landmask.png, equirectangular w x w/2.

    Look of the rebuilt globe (v2): deep navy-teal oceans with the sea-floor relief faintly shaded,
    continents in a warm weathered stone that reads as carved relief (strong hillshade), ice caps pale.
    Height: the coast is a clean step (continents stand proud like the carved original), mountains
    rise further, the sea floor dips slightly:
      land 0.5 + 0.5 * (0.35 + 0.65 * sqrt(z / 5000)),  ocean 0.5 - 0.1 * (-z / 7000)
      python ds_aquasphere.py --textures
    """
    import numpy as np, cv2

    def _png(path, arr):   # cv2.imwrite cannot open non-ASCII Windows paths (this folder has one)
        path.write_bytes(cv2.imencode(".png", arr)[1].tobytes())
    rows = [l.split() for l in (GLOBE_DIR / "etopo_12.asc").read_text().splitlines()[6:] if l.strip()]
    z = np.array(rows, dtype=np.float32)[:, :-1]                      # north row first, drop the wrapped column
    h = w // 2
    Z = cv2.resize(z, (w, h), interpolation=cv2.INTER_CUBIC)
    lat = np.linspace(90, -90, h)[:, None] * np.ones((1, w))
    land = Z > 0
    gy, gx = np.gradient(cv2.GaussianBlur(Z, (0, 0), 1.2))           # hillshade from the NW
    shade_l = np.clip(1.0 + (-gx - gy) / 700.0, 0.62, 1.30)[..., None]
    shade_o = np.clip(1.0 + (-gx - gy) / 2600.0, 0.85, 1.12)[..., None]

    def lerp(a, b, t):
        return np.asarray(a, np.float32) * (1 - t[..., None]) + np.asarray(b, np.float32) * t[..., None]
    d = np.clip(-Z / 6500.0, 0, 1) ** 0.55
    ocean = lerp((0.13, 0.40, 0.50), (0.025, 0.10, 0.22), d)
    shelf = np.clip((Z + 250) / 250.0, 0, 1) * (~land)
    ocean = ocean * (1 - shelf[..., None]) + np.array((0.20, 0.50, 0.56), np.float32) * shelf[..., None]
    ocean = ocean * shade_o
    t = np.clip(Z / 4200.0, 0, 1) ** 0.7
    ground = lerp((0.66, 0.58, 0.43), (0.47, 0.39, 0.28), t)
    hi = np.clip((Z - 2600) / 2000.0, 0, 1)
    ground = ground * (1 - hi[..., None]) + np.array((0.74, 0.71, 0.64), np.float32) * hi[..., None]
    ice = np.clip((np.abs(lat) - 64) / 14.0, 0, 1) ** 1.4
    ground = (ground * (1 - ice[..., None]) + np.array((0.88, 0.89, 0.88), np.float32) * ice[..., None]) * shade_l
    col = np.where(land[..., None], ground, ocean)
    col = cv2.GaussianBlur(np.clip(col, 0, 1).astype(np.float32), (0, 0), 0.6)
    _png(GLOBE_DIR / "globe_color.png", (col[..., ::-1] * 255).astype(np.uint8))
    hl = 0.5 + 0.5 * (0.35 + 0.65 * np.sqrt(np.clip(Z / 5000.0, 0, 1)))
    ho = 0.5 - 0.1 * np.clip(-Z / 7000.0, 0, 1)
    hgt = np.where(land, hl, ho)
    _png(GLOBE_DIR / "globe_height.png", (np.clip(hgt, 0, 1) * 65535).astype(np.uint16))
    _png(GLOBE_DIR / "globe_landmask.png", land.astype(np.uint8) * 255)
    print(f"[aquasphere] textures {w}x{h} written to {GLOBE_DIR}")


# ---------------------------------------------------------------- materials
def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def _principled(name, color, rough=0.5, **kw):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    _set(b, "Base Color", (*color, 1)); _set(b, "Roughness", rough)
    for k, v in kw.items():
        _set(b, k.replace("_", " "), v)
    mat.diffuse_color = (*color, 1)
    return mat, nt, b


def _noise_bump(nt, bsdf, scale, strength, dist=0.02):
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = dist
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return nz


def mat_stone(name="mat_aq_stone", color=(0.80, 0.70, 0.55)):
    mat, nt, b = _principled(name, color, 0.65)
    # soft mottling like the sandstone rim in the photo
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*[c * 0.88 for c in color], 1); ramp.color_ramp.elements[1].color = (*color, 1)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    _noise_bump(nt, b, 40, 0.15)
    return mat


def mat_water():
    mat, nt, b = _principled("mat_aq_water", (0.10, 0.46, 0.47), 0.03,   # teal as in the photo; mostly opaque so it reads as water
                             Transmission_Weight=0.3, IOR=1.33)
    _noise_bump(nt, b, 3.0, 0.25, 0.05)
    return mat


def mat_foam():
    mat, nt, b = _principled("mat_aq_foam", (0.95, 0.97, 0.98), 0.45, Subsurface_Weight=0.4)
    _noise_bump(nt, b, 12, 0.6, 0.05)
    return mat


def mat_running_water(name="mat_aq_film", streak=(7.0, 7.0, 0.7), strength=0.35, aerated=0.0):
    """Thin sheet of water running down (vertical streaks: noise squashed along Z).
    aerated 0..1: white, air-filled falling water (curtain) instead of a clear film."""
    mat, nt, b = _principled(name, (0.78 + 0.12 * aerated, 0.90 + 0.06 * aerated, 0.93 + 0.05 * aerated),
                             0.02 + 0.18 * aerated, Transmission_Weight=1.0 - 0.5 * aerated, IOR=1.33)
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = streak
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 6
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = 0.01
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return mat


def mat_bronze():
    mat, nt, b = _principled("mat_aq_bronze", (0.36, 0.30, 0.20), 0.38, Metallic=0.85)
    _noise_bump(nt, b, 18, 0.2)
    return mat


def mat_globe():
    mat, nt, b = _principled("mat_aq_globe", (0.3, 0.5, 0.8), 0.3, Coat_Weight=1.0, Coat_Roughness=0.03)
    nodes, links = nt.nodes, nt.links
    uv = nodes.new("ShaderNodeTexCoord")

    def img(fname, noncolor=False):
        n = nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(str(GLOBE_DIR / fname), check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = "Non-Color"
        links.new(uv.outputs["UV"], n.inputs["Vector"])
        return n
    col, hgt, mask = img("globe_color.png"), img("globe_height.png", True), img("globe_landmask.png", True)
    links.new(col.outputs["Color"], b.inputs["Base Color"])
    # oceans: glassy water film; land: matte sculpted stone
    rough = nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value, rough.inputs["To Max"].default_value = 0.06, 0.42
    links.new(mask.outputs["Color"], rough.inputs["Value"]); links.new(rough.outputs["Result"], b.inputs["Roughness"])
    coat = nodes.new("ShaderNodeMath"); coat.operation = "SUBTRACT"; coat.inputs[0].default_value = 1.0
    links.new(mask.outputs["Color"], coat.inputs[1])
    if "Coat Weight" in b.inputs:
        links.new(coat.outputs["Value"], b.inputs["Coat Weight"])
    bp = nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; bp.inputs["Distance"].default_value = 0.03
    links.new(hgt.outputs["Color"], bp.inputs["Height"]); links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return mat


# ---------------------------------------------------------------- geometry helpers
def _obj(bm, name, mat, loc, col, up=False):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if up:  # flat pieces: recalc is ambiguous on open sheets, and a downward normal renders black in Cycles
        for f in bm.faces:
            if f.normal.z < 0:
                f.normal_flip()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat); o.location = loc
    col.objects.link(o)
    return o


def lathe(profile, segs=160):
    """Revolve a (r, z) profile around Z; returns a bmesh."""
    bm = bmesh.new()
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in profile])
    for k in range(segs):
        r0, r1 = rings[k], rings[(k + 1) % segs]
        for i in range(len(profile) - 1):
            try:
                bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return bm


def disc(r, z, segs=160, r_in=0.0):
    prof = [(r_in, z), (r, z)] if r_in > 0 else [(0.0, z), (r, z)]
    return lathe(prof, segs)


def box(sx, sy, sz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, sz / 2), verts=bm.verts)
    return bm


# ---------------------------------------------------------------- build
def build(ground_z=None, col=None, animate=False, fps=24):
    """ground_z: plaza height in the target scene (0 in the flat draft; SPEC ground_rel with DEM)."""
    S = SPEC
    lv = _water_levels()
    g = S["ground_rel"] if ground_z is None else ground_z
    wz = g - S["water_below_ground"] if lv is None else g + (lv[0] - lv[1])
    col = col or bpy.data.collections.get("Landmarks") or bpy.context.scene.collection
    C = (S["cx"], S["cy"], 0.0)
    r_out, r_in = S["pool_r"], S["pool_r"] - S["rim_w"]
    pv = g + 0.045   # paving top: above the draft's path/plaza sheets (ds_terrain PATH_Z = 0.03)
    stone, dark = mat_stone(), mat_stone("mat_aq_inlay", (0.28, 0.25, 0.22))
    paving = mat_stone("mat_aq_plaza", (0.42, 0.50, 0.60))
    white = mat_stone("mat_aq_line", (0.92, 0.92, 0.90))
    objs = {}

    # pool floor + water
    objs["floor"] = _obj(disc(r_in, wz - S["pool_depth"]), "AQ_PoolFloor", mat_stone("mat_aq_poolfloor", (0.55, 0.72, 0.78)), C, col, up=True)
    objs["water"] = _obj(disc(r_in, wz), "AQ_Water", mat_water(), C, col, up=True)

    # rim: plinth, carved groove band, overhanging cap (profile read off the photo), 0.40 m above the plaza
    h = S["rim_h"]
    prof = [(r_in, wz - S["pool_depth"]), (r_in, g + h - 0.06), (r_in - 0.03, g + h - 0.06), (r_in - 0.03, g + h),
            (r_out + 0.03, g + h), (r_out + 0.03, g + h - 0.06), (r_out, g + h - 0.06), (r_out, g + 0.25),
            (r_out - 0.035, g + 0.23), (r_out - 0.035, g + 0.14), (r_out, g + 0.12), (r_out, g - 0.02)]
    objs["rim"] = _obj(lathe(prof), "AQ_Rim", stone, C, col)

    # beige paved ring with dark round inlays, then the blue-grey plaza with white radial lines
    objs["ring"] = _obj(disc(r_out + S["ring_w"], pv + 0.004, r_in=r_out), "AQ_PavedRing", stone, C, col, up=True)
    bm = bmesh.new()
    for k in range(S["inlays"]):
        a = 2 * math.pi * (k + 0.5) / S["inlays"]; rr = r_out + S["ring_w"] / 2
        ret = bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=S["inlay_r"])
        bmesh.ops.translate(bm, verts=ret["verts"], vec=(rr * math.cos(a), rr * math.sin(a), pv + 0.008))
    objs["inlays"] = _obj(bm, "AQ_Inlays", dark, C, col, up=True)
    objs["plaza"] = _obj(disc(S["plaza_r"], pv, r_in=r_out + S["ring_w"]), "AQ_Plaza", paving, C, col, up=True)
    bm = bmesh.new()
    for k in range(S["plaza_lines"]):
        a = 2 * math.pi * k / S["plaza_lines"]; ca, sa = math.cos(a), math.sin(a); w = S["plaza_line_w"] / 2
        r0, r1 = r_out + S["ring_w"], S["plaza_r"]
        vs = [bm.verts.new((r * ca - s * w * sa, r * sa + s * w * ca, pv + 0.006)) for r, s in ((r0, -1), (r1, -1), (r1, 1), (r0, 1))]
        bm.faces.new(vs)
        for rr in (r0 + 3.0, r0 + 9.0):  # round light patches along the lines (photo)
            ret = bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=0.9)
            bmesh.ops.translate(bm, verts=ret["verts"], vec=(rr * ca, rr * sa, pv + 0.007))
    objs["lines"] = _obj(bm, "AQ_PlazaLines", white, C, col, up=True)

    # 0.40 m stone blocks (tangential), lamps
    bx, by, bz = S["block_size"]
    for k in range(S["blocks"]):
        a = 2 * math.pi * (k + 0.5) / S["blocks"]
        o = _obj(box(bx, by, bz), f"AQ_Block_{k:02d}", stone,
                 (C[0] + S["block_r"] * math.cos(a), C[1] + S["block_r"] * math.sin(a), g), col)
        o.rotation_euler.z = a + math.pi / 2
        bev = o.modifiers.new("bevel", "BEVEL"); bev.width = 0.03; bev.segments = 2
    lamp_mat, _, _ = _principled("mat_aq_lamp", (0.05, 0.05, 0.05), 0.4, Metallic=1.0)
    for k in range(S["lamps"]):
        a = 2 * math.pi * k / S["lamps"]
        bm = lathe([(0.0, 0), (0.16, 0), (0.16, 0.5), (0.07, 0.6), (0.06, S["lamp_h"] - 0.5), (0.22, S["lamp_h"] - 0.45),
                    (0.18, S["lamp_h"]), (0.0, S["lamp_h"] + 0.1)], 16)
        _obj(bm, f"AQ_Lamp_{k}", lamp_mat, (C[0] + S["lamp_r"] * math.cos(a), C[1] + S["lamp_r"] * math.sin(a), g), col)

    # pedestal: stone core hidden inside a flared white-water skirt, 2 m from the plaza to the globe's underside
    top = g + S["pedestal_h"]
    objs["core"] = _obj(lathe([(0, wz - S["pool_depth"]), (1.1, wz - S["pool_depth"]), (1.1, top), (0, top)], 48),
                        "AQ_PedestalCore", stone, C, col)
    # v2: a bronze cradle cups the globe; the water running off the globe spills over its lip as a
    # clear curtain down to the pool and churns into a ring of white water where it lands
    cradle = [(1.0, top - 0.7), (1.6, top - 0.45), (2.05, top - 0.05), (2.36, top + 0.42), (2.48, top + 0.50),
              (2.44, top + 0.56), (2.30, top + 0.50)]
    objs["cradle"] = _obj(lathe(cradle, 128), "AQ_Cradle", mat_bronze(), C, col)
    curtain = [(2.50, top + 0.50), (2.62, top + 0.20), (2.78, top - 0.45), (2.92, g + 0.55), (3.02, wz + 0.10), (3.05, wz - 0.02)]
    objs["curtain"] = _obj(lathe(curtain, 128), "AQ_Curtain", mat_running_water("mat_aq_curtain", (16.0, 16.0, 0.3), 0.9, aerated=0.8), C, col)
    foam = [(2.75, wz - 0.02), (2.9, wz + 0.16), (3.2, wz + 0.22), (3.55, wz + 0.10), (3.8, wz - 0.02)]
    objs["foam"] = _obj(lathe(foam, 96), "AQ_Foam", mat_foam(), C, col)
    disp_tex = bpy.data.textures.new("AQ_FoamNoise", "CLOUDS"); disp_tex.noise_scale = 0.12; disp_tex.noise_depth = 3
    objs["foam"].modifiers.new("sub", "SUBSURF").levels = 2          # subdivide first so the churn shows
    m = objs["foam"].modifiers.new("foam", "DISPLACE"); m.texture = disp_tex; m.strength = 0.12

    # globe: tilted axis empty (north tipped toward the entrance side), globe spins about its local Z
    R = S["globe_d"] / 2
    axis = bpy.data.objects.new("AQ_Axis", None); axis.location = (C[0], C[1], top + R); col.objects.link(axis)
    ent = math.atan2(2.0 - C[1], 390.0 - C[0])             # direction to Park Entrance South (OSM toll booths)
    axis.rotation_euler = (0.0, 0.0, ent)
    tilt = bpy.data.objects.new("AQ_Tilt", None); tilt.parent = axis; col.objects.link(tilt)
    tilt.rotation_euler = (0.0, math.radians(S["tilt_deg"]), 0.0)    # +Y rotation tips +Z toward +X (the entrance)
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")   # calc_uvs only fills an existing UV layer
    bmesh.ops.create_uvsphere(bm, u_segments=384, v_segments=192, radius=R, calc_uvs=True)
    globe = _obj(bm, "AQ_Globe", mat_globe(), (0, 0, 0), col)
    globe.parent = tilt
    globe.rotation_euler.z = math.radians(-S["face_lon_deg"] + S["face_offset_deg"])
    gd = globe.modifiers.new("relief", "DISPLACE")          # continents stand ~4 cm proud, like the carved original
    gt = bpy.data.textures.new("AQ_GlobeHeight", "IMAGE"); gt.image = bpy.data.images.load(str(GLOBE_DIR / "globe_height.png"), check_existing=True)
    gt.image.colorspace_settings.name = "Non-Color"
    gd.texture = gt; gd.texture_coords = "UV"; gd.strength = 0.24; gd.mid_level = 0.5   # v2 heights: coast step ~4 cm, peaks ~12 cm
    if animate:  # counter-clockwise seen from above, one turn per rev_seconds
        sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, int(S["rev_seconds"] * fps)
        prefs = bpy.context.preferences.edit
        old = prefs.keyframe_new_interpolation_type
        prefs.keyframe_new_interpolation_type = "LINEAR"   # 5.x layered actions: avoid walking action.fcurves
        globe.keyframe_insert("rotation_euler", index=2, frame=1)
        globe.rotation_euler.z += 2 * math.pi
        globe.keyframe_insert("rotation_euler", index=2, frame=sc.frame_end)
        prefs.keyframe_new_interpolation_type = old
    objs["globe"] = globe
    # water film running over the whole globe (it does not spin: the water falls, the globe turns under it)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=192, v_segments=96, radius=R + 0.035)
    objs["film"] = _obj(bm, "AQ_WaterFilm", mat_running_water(), (C[0], C[1], top + R), col)
    print(f"[aquasphere] ground {g:+.2f} water {wz:+.2f} globe centre {top + R:+.2f} top {top + 2 * R:+.2f} "
          f"(levels from {'water tab' if lv else 'SPEC'})")
    return objs


if __name__ == "__main__" and bpy is None:
    import sys
    if "--textures" in sys.argv:
        generate_textures()
