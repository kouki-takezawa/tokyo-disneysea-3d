"""東京ディズニーランド・ステーション (Disney Resort Line) -- detailed build for Blender 5.2.

  blender -b --python ds_tdl_station.py -- --cams park,hotel,concourse,platform,stairs,aerial --samples 32
  blender -b --python ds_tdl_station.py -- --cams none            # build + save the .blend only
  then open output/disneyland/station/tdl_station.blend in Blender to look around (cameras CAM_*)

Output: output/disneyland/station/tdl_station.blend and station_<cam>.png (local check, not committed).

Method: the reference video (README: 【背景メイキング】ディズニーランドステーション / WALT.) builds the gate hall
in this order, and this script keeps it:
  1. the clock first, as the reference for the other sizes (video 0:27)
  2. the half-round fan window round it: one ray + Array (object offset = a turned empty); the bead ring as
     Array + Curve on a semicircle (video: 配列 + カーブ); stone frame, keystone
  3. the glass vault: ribs and glazing bars as Array, bent over the vault arc with a Curve modifier
  4. pedestal, frieze of arched plaques (one plaque + Array), columns, Bevel on the stone edges
  5. star medallions and scroll brackets (curves with a bevel) at the column heads, fretwork between columns
  6. then the rest of the building round it; materials: a cream base + variants, brick, copper, gold, glass
The video only models what its one fisheye camera sees; this build does the whole station so the mock can use it.

Sources (looked at only; nothing copied into the repository):
  * OSM: station building outline (the 舞浜駅・周辺 layer, a 9 m box in the mock), platform way 809639816,
    monorail ways 680462531 / 866212217, station node 8073893293.
  * ja.wikipedia 東京ディズニーランド・ステーション駅: elevated, 1 side platform / 1 track, gates on the same 2F as
    the platform (one space), Victorian style matching the park's main entrance, glass roof over the gates, murals
    of park attractions in the arches under the platform, a Mickey clock in the middle, 2 escalators (up / down),
    2 lifts, lockers and toilets on the ground floor, opened 2001-07-27.
  * Wikimedia Commons, Category:Tokyo Disneyland Station (CC BY / CC BY-SA / CC0): park-side facade (two segmental
    arches, bay window, clock in a half-round fan window, glass vault behind, stairs with green roofs both sides),
    hotel-side facade (sign board, murals in the arch lunettes, open arcade with fretwork arches, fan window under a
    slate hood), stair / escalator entrance (pedimented kiosk "DISNEY RESORT LINE", barrel canopy), platform (tiles,
    screen doors, cream columns, globe lamps), gate hall (glass barrel vault, star medallions, green banners).
  * GSI aerial photo (tools/aerial_overlay.py) for the outline.

Frame: station-local metres. Origin = the middle of the park-side centre block on the platform axis,
(-583.08, 1023.04) in the DisneySea frame; +X (u) runs along the track to the ENE (24.78 deg), +Y (v) points to the
hotel (NNW). Ground = 0 (the DEM ground here is about -1.79 m on the DisneySea datum: added when exported).

ESTIMATES (no drawings or measurements; scaled from photos with the OSM outline as the ruler):
  platform / gate floor 7.0 m, beam top 6.0 m (car floor 1.0 m above the beam, train_blender SPEC), eaves 11.0 m,
  centre-block cornice 11.5 m, glass vault radius 6.4 m springing at 11.6 m (crown 18 m), clock hub 12.9 m,
  arches 7.3 m wide springing at 4.6 m, stair 44 steps, escalators about 30 deg. The mock draws this beam at 8.9 m on
  the datum (about 10.7 m above this ground), so the mock's viaduct and trains need the same heights before this
  model goes in.
"""
import sys, math, json, re, argparse, pathlib, time

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix
except ImportError:          # FRAME / SPEC / to_local work in plain Python
    bpy = bmesh = Vector = Matrix = None

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "output" / "disneyland" / "station"

FRAME = dict(x=-583.08, y=1023.04, ang_deg=24.78, ground_datum=-1.79)
SPEC = dict(
    F2=7.0, slab=0.6, beam_top=6.0, beam_w=0.85, beam_d=1.6, track_v=3.6,
    bar_u=45.8, bar_v0=-4.0, bar_v1=7.6,                  # the long block along the track
    plat_u=41.0, plat_edge=1.95,                          # platform u -41..41, v -4 .. edge
    cb_u=9.8, cb_v0=-15.0,                                # park-side centre block (gate hall)
    wing_u=19.2, wing_v0=-13.5,                           # 2F verandas between the hall and the stairs
    st_u1=32.3, st_v0=-13.9, st_v1=-11.35, esc_v0=-10.95, esc_v1=-9.05,
    eave=11.0, cornice=11.5, ridge=12.9,
    vault_r=6.4, vault_z=11.6, vault_v0=-14.8, vault_v1=7.9,
    hub_z=12.9, fan_r=2.75, frame_w=0.5, clock_r=0.95,
    arch_half=(0.9, 8.2), arch_spring=4.6, arch_rise=1.8,
)
TRAIN_LEN = 2 * 15.05 + 4 * 13.70 + 5 * 0.55
# sun (a lamp): from the south-south-east, in front of the park face and a little to its right as in the photo
SUN_EL, SUN_AZ, SUN_W = 38.0, -15.0, 3.5     # elevation, azimuth (deg, from +X = east, counter-clockwise), W/m2


def to_local(x, y):
    a = math.radians(FRAME["ang_deg"]); dx, dy = x - FRAME["x"], y - FRAME["y"]
    return (dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a))


def to_world(u, v):
    a = math.radians(FRAME["ang_deg"])
    return (FRAME["x"] + u * math.cos(a) - v * math.sin(a), FRAME["y"] + u * math.sin(a) + v * math.cos(a))


def mock_data():
    page = (ROOT / "output" / "disneysea" / "tds_outline.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S).group(1).replace(r"<\/", "</"))


# ================================================================ materials (last in the video; defined first here)
class B:
    col = None; root = None; M = {}; cutters = None; hide = []


def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def _principled(name, color, rough=0.5, **kw):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    _set(b, "Base Color", (*color, 1)); _set(b, "Roughness", rough)
    for k, v in kw.items():
        _set(b, k.replace("_", " "), v)
    mat.diffuse_color = (*color, 1)
    return mat, nt, b


def _bump(nt, b, height_socket, strength, dist=0.01):
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = dist
    nt.links.new(height_socket, bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])


def _mottle(nt, b, color, scale=5.0, amount=0.9, bump=0.06):
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*[c * amount for c in color], 1); ramp.color_ramp.elements[1].color = (*color, 1)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    if bump:
        nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 60
        nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"]); _bump(nt, b, nz2.outputs["Fac"], bump)


def _wall_uv(nt):
    """(along-the-wall, height) for vertical walls in either direction: (x + y, z)."""
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"; comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0]); nt.links.new(sep.outputs[0], add.inputs[0]); nt.links.new(sep.outputs[1], add.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs[0]); nt.links.new(sep.outputs[2], comb.inputs[1])
    return comb.outputs[0]


def mat_brick(name="st_brick"):
    mat, nt, b = _principled(name, (0.45, 0.19, 0.12), 0.85)
    br = nt.nodes.new("ShaderNodeTexBrick")
    _set(br, "Color1", (0.26, 0.08, 0.05, 1)); _set(br, "Color2", (0.20, 0.07, 0.045, 1)); _set(br, "Mortar", (0.33, 0.28, 0.24, 1))
    _set(br, "Scale", 1.0); _set(br, "Mortar Size", 0.009); _set(br, "Brick Width", 0.23); _set(br, "Row Height", 0.075)
    br.offset = 0.5
    nt.links.new(_wall_uv(nt), br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    _bump(nt, b, br.outputs["Fac"], -0.35, 0.004)
    return mat


def mat_tiles(name, c1, c2, size=0.3, grout=(0.55, 0.45, 0.38)):
    mat, nt, b = _principled(name, c1, 0.6)
    tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
    _set(br, "Color1", (*c1, 1)); _set(br, "Color2", (*c2, 1)); _set(br, "Mortar", (*grout, 1)); _set(br, "Scale", 1.0)
    _set(br, "Mortar Size", 0.006); _set(br, "Brick Width", size); _set(br, "Row Height", size); br.offset = 0.0
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    _bump(nt, b, br.outputs["Fac"], -0.2, 0.003)
    return mat


def mat_copper(name="st_copper"):
    mat, nt, b = _principled(name, (0.36, 0.62, 0.56), 0.45, Metallic=0.35)
    tc = nt.nodes.new("ShaderNodeTexCoord"); wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"; wv.bands_direction = "X"; _set(wv, "Scale", 1.2); _set(wv, "Distortion", 0.0)
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"]); _bump(nt, b, wv.outputs["Fac"], 0.25, 0.01)
    nz = nt.nodes.new("ShaderNodeTexNoise"); _set(nz, "Scale", 3.0); ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.30, 0.55, 0.50, 1); ramp.color_ramp.elements[1].color = (0.42, 0.68, 0.61, 1)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return mat


def mat_mural(name="st_mural"):
    """Painted lunettes: a soft blue-green-gold painting, not a copy of the real murals."""
    mat, nt, b = _principled(name, (0.18, 0.30, 0.36), 0.7)
    nz = nt.nodes.new("ShaderNodeTexNoise"); _set(nz, "Scale", 1.6); _set(nz, "Detail", 8.0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp; cr.elements[0].position = 0.3; cr.elements[0].color = (0.05, 0.12, 0.22, 1)
    cr.elements[1].position = 0.75; cr.elements[1].color = (0.55, 0.62, 0.45, 1)
    e = cr.elements.new(0.52); e.color = (0.16, 0.34, 0.33, 1)
    e = cr.elements.new(0.85); e.color = (0.85, 0.72, 0.40, 1)
    nt.links.new(_wall_uv(nt), nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return mat


def mat_checker(name="st_checker"):
    mat, nt, b = _principled(name, (0.62, 0.55, 0.55), 0.8)
    tc = nt.nodes.new("ShaderNodeTexCoord"); ck = nt.nodes.new("ShaderNodeTexChecker")
    _set(ck, "Color1", (0.70, 0.64, 0.64, 1)); _set(ck, "Color2", (0.52, 0.46, 0.50, 1)); _set(ck, "Scale", 0.8)
    nt.links.new(tc.outputs["Object"], ck.inputs["Vector"]); nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
    return mat


def clear_glass(name, color, alpha):
    mat, nt, b = _principled(name, color, 0.02, Transmission_Weight=1.0, IOR=1.05, Alpha=alpha)
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(mat, attr, val)
        except (AttributeError, TypeError):
            pass
    mat.use_backface_culling = False
    mat.diffuse_color = (*color, alpha)
    return mat


def materials():
    M = {}
    mat, nt, b = _principled("st_cream", (0.84, 0.78, 0.64), 0.6); _mottle(nt, b, (0.84, 0.78, 0.64)); M["cream"] = mat
    mat, nt, b = _principled("st_trim", (0.92, 0.89, 0.80), 0.5); _mottle(nt, b, (0.92, 0.89, 0.80), 8, 0.94, 0.03); M["trim"] = mat
    mat, nt, b = _principled("st_stone", (0.66, 0.65, 0.62), 0.75); _mottle(nt, b, (0.66, 0.65, 0.62), 4, 0.88); M["stone"] = mat
    M["brick"] = mat_brick()
    M["copper"] = mat_copper()
    M["slate"] = _principled("st_slate", (0.17, 0.21, 0.28), 0.45, Metallic=0.2)[0]
    M["gold"] = _principled("st_gold", (0.86, 0.64, 0.28), 0.25, Metallic=1.0)[0]
    # see-through glass in every viewport: thin transmission for Cycles plus alpha blending (EEVEE / Material Preview)
    M["glass"] = clear_glass("st_glass", (0.90, 0.95, 0.97), 0.18)
    M["amber"] = clear_glass("st_amber", (0.95, 0.72, 0.30), 0.6)
    M["dark_glass"] = clear_glass("st_dark_glass", (0.80, 0.88, 0.92), 0.25)       # window panes: clear, you see in and out
    M["tile"] = mat_tiles("st_tile", (0.64, 0.36, 0.25), (0.60, 0.33, 0.23))
    M["paving"] = mat_tiles("st_paving", (0.38, 0.19, 0.18), (0.35, 0.18, 0.17), 0.6, (0.33, 0.25, 0.24))
    M["checker"] = mat_checker()
    M["iron"] = _principled("st_iron", (0.06, 0.08, 0.07), 0.4, Metallic=0.7)[0]
    M["white"] = _principled("st_white", (0.93, 0.93, 0.91), 0.35)[0]
    M["black"] = _principled("st_black", (0.03, 0.03, 0.03), 0.4)[0]
    M["concrete"] = _principled("st_concrete", (0.66, 0.66, 0.64), 0.85)[0]
    M["awning"] = _principled("st_awning", (0.45, 0.07, 0.07), 0.7)[0]
    M["lamp"] = _principled("st_lamp", (1.0, 0.95, 0.85), 0.3, Emission_Color=(1.0, 0.86, 0.62, 1), Emission_Strength=3.0)[0]
    M["mural"] = mat_mural()
    M["sign"] = _principled("st_sign", (0.10, 0.20, 0.21), 0.5)[0]
    M["gate"] = _principled("st_gate", (0.42, 0.43, 0.45), 0.4, Metallic=0.5)[0]
    M["gate_panel"] = _principled("st_gate_panel", (0.05, 0.36, 0.28), 0.4)[0]
    M["banner"] = _principled("st_banner", (0.06, 0.24, 0.17), 0.8)[0]
    M["yellow"] = _principled("st_yellow", (0.85, 0.62, 0.05), 0.6)[0]
    M["escalator"] = _principled("st_escalator", (0.55, 0.56, 0.58), 0.35, Metallic=0.9)[0]
    M["context"] = _principled("st_context", (0.80, 0.74, 0.60), 0.8)[0]
    M["context_roof"] = _principled("st_context_roof", (0.25, 0.36, 0.55), 0.6)[0]
    M["grass"] = _principled("st_grass", (0.12, 0.25, 0.08), 0.9)[0]
    return M


# ================================================================ geometry helpers (all in station-local metres)
def _link(o, parent=None):
    B.col.objects.link(o)
    o.parent = parent if parent is not None else B.root
    return o


def obj_bm(name, bm, mat, smooth=False, recalc=True, parent=None):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        me.shade_smooth()
    if mat is not None:
        me.materials.append(B.M[mat] if isinstance(mat, str) else mat)
    return _link(bpy.data.objects.new(name, me), parent)


def bm_box(bm, x0, x1, y0, y1, z0, z1):
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=vs)
    bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=vs)
    return vs


def box(name, bxs, mat, bevel=0.0):
    """One box (x0, x1, y0, y1, z0, z1) or a list of them -> one object."""
    if isinstance(bxs[0], (int, float)):
        bxs = [bxs]
    bm = bmesh.new()
    for b in bxs:
        bm_box(bm, *b)
    o = obj_bm(name, bm, mat)
    if bevel:
        bevel_mod(o, bevel)
    return o


def mirror_u(bx):
    x0, x1, *r = bx
    return (-x1, -x0, *r)


def sym(bxs):
    """Boxes plus their mirror images across u = 0."""
    return list(bxs) + [mirror_u(b) for b in bxs]


def bevel_mod(o, w, segs=2):
    m = o.modifiers.new("Bevel", "BEVEL"); m.width = w; m.segments = segs; m.limit_method = "ANGLE"
    return m


def array_mod(o, count, offset, name="Array"):
    m = o.modifiers.new(name, "ARRAY"); m.count = count
    m.use_relative_offset = False; m.use_constant_offset = True; m.constant_offset_displace = offset
    return m


def radial_array(o, count, step):
    """Array with an object offset: a child empty turned by `step` about the object's local Z (the video's fan rays)."""
    e = bpy.data.objects.new(o.name + "_step", None); B.col.objects.link(e)
    e.parent = o; e.rotation_euler = (0, 0, step); e.empty_display_size = 0.2
    m = o.modifiers.new("Radial", "ARRAY"); m.count = count
    m.use_relative_offset = False; m.use_object_offset = True; m.offset_object = e
    return m


def arc_curve(name, r, a0=0.0, a1=math.pi, n=65, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0)):
    """A poly arc in the local XY plane (Z = the out-of-plane side); stood upright by rot."""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.twist_mode = "Z_UP"
    sp = cu.splines.new("POLY"); sp.points.add(n - 1)
    for i, p in enumerate(sp.points):
        a = a0 + (a1 - a0) * i / (n - 1)
        p.co = (r * math.cos(a), r * math.sin(a), 0, 1)
    o = _link(bpy.data.objects.new(name, cu)); o.location = loc; o.rotation_euler = rot
    o.hide_render = True
    return o


def bend(o, curve):
    """Curve modifier: local X runs along the curve from its first point, +Y bends towards the centre."""
    o.location = curve.location; o.rotation_euler = curve.rotation_euler
    m = o.modifiers.new("Curve", "CURVE"); m.object = curve; m.deform_axis = "POS_X"
    return m


def bm_prism(bm, pts, a0, a1, plane="xy"):
    """Polygon pts (2D) extruded from a0 to a1: plane xy -> along z, xz -> along y, yz -> along x."""
    def P(p, a):
        return (p[0], p[1], a) if plane == "xy" else (p[0], a, p[1]) if plane == "xz" else (a, p[0], p[1])
    v0 = [bm.verts.new(P(p, a0)) for p in pts]; v1 = [bm.verts.new(P(p, a1)) for p in pts]
    n = len(pts)
    bm.faces.new(v0[::-1]); bm.faces.new(v1)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((v0[i], v0[j], v1[j], v1[i]))


def prism(name, polys, a0, a1, mat, plane="xy", bevel=0.0):
    if isinstance(polys[0][0], (int, float)):
        polys = [polys]
    bm = bmesh.new()
    for p in polys:
        bm_prism(bm, p, a0, a1, plane)
    o = obj_bm(name, bm, mat)
    if bevel:
        bevel_mod(o, bevel)
    return o


def bm_loft(bm, lo, hi):
    """Closed solid between two polygons with the same vertex count (3D points)."""
    v0 = [bm.verts.new(p) for p in lo]; v1 = [bm.verts.new(p) for p in hi]
    n = len(lo)
    bm.faces.new(v0[::-1]); bm.faces.new(v1)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((v0[i], v0[j], v1[j], v1[i]))


def bm_lathe(bm, profile, segs=24, M=None):
    """Revolve (r, z) around Z; r = 0 points close the ends. M places the result."""
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        ring = []
        for r, z in profile:
            p = Vector((r * math.cos(a), r * math.sin(a), z))
            ring.append(bm.verts.new(M @ p if M is not None else p))
        rings.append(ring)
    new = [v for r in rings for v in r]
    for k in range(segs):
        r0, r1 = rings[k], rings[(k + 1) % segs]
        for i in range(len(profile) - 1):
            try:
                bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=new, dist=1e-5)


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def R(angle, axis):
    return Matrix.Rotation(angle, 4, axis)


def seg_arc(cx, cz, w, rise, n=16):
    """Segmental arc over a chord w centred on cx, springing at cz, from the right end to the left end."""
    Rr = (w * w / 4 + rise * rise) / (2 * rise); zc = cz + rise - Rr; half = math.asin(min(1.0, (w / 2) / Rr))
    pts = [(cx + Rr * math.sin(half - 2 * half * i / (n - 1)), zc + Rr * math.cos(half - 2 * half * i / (n - 1))) for i in range(n)]
    return pts, (zc, Rr, half)


def arch_opening(x0, x1, z0, spring, rise, n=16):
    pts, _ = seg_arc((x0 + x1) / 2, spring, x1 - x0, rise, n)
    return [(x0, z0), (x1, z0)] + pts


def arch_band(x0, x1, spring, rise, width, n=18, leg=0.0):
    """Voussoir band round a segmental arch (an upside-down U); leg carries both ends down."""
    cx = (x0 + x1) / 2
    _, (zc, Rr, half) = seg_arc(cx, spring, x1 - x0, rise, n)
    Ro = Rr + width
    ang = [half - 2 * half * i / (n - 1) for i in range(n)]
    inner = [(cx + Rr * math.sin(t), zc + Rr * math.cos(t)) for t in ang]
    outer = [(cx + Ro * math.sin(t), zc + Ro * math.cos(t)) for t in ang]
    if leg:
        outer = [(outer[0][0], outer[0][1] - leg)] + outer + [(outer[-1][0], outer[-1][1] - leg)]
        inner = [(inner[0][0], inner[0][1] - leg)] + inner + [(inner[-1][0], inner[-1][1] - leg)]
    return outer + inner[::-1]


def ring_sector(r0, r1, a0=0.0, a1=math.pi, n=33, cx=0.0, cz=0.0):
    ang = [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]
    outer = [(cx + r1 * math.cos(a), cz + r1 * math.sin(a)) for a in ang]
    inner = [(cx + r0 * math.cos(a), cz + r0 * math.sin(a)) for a in ang]
    return outer + inner[::-1]


def half_disc(r, n=33, cx=0.0, cz=0.0):
    return [(cx + r * math.cos(math.pi * i / (n - 1)), cz + r * math.sin(math.pi * i / (n - 1))) for i in range(n)]


def cutter(name, shapes, target_objs, plane="xz", a=(0, 0)):
    """Boolean difference (EXACT) with a hidden cutter made of boxes (6-tuples) and/or prisms (polys over a)."""
    bm = bmesh.new()
    for p in shapes:
        if isinstance(p[0], (int, float)):
            bm_box(bm, *p)
        else:
            bm_prism(bm, p, a[0], a[1], plane)
    c = obj_bm(name, bm, None)
    B.cutters.objects.link(c); B.col.objects.unlink(c)
    c.display_type = "WIRE"; c.hide_render = True
    for t in (target_objs if isinstance(target_objs, (list, tuple)) else [target_objs]):
        m = t.modifiers.new("Cut", "BOOLEAN"); m.object = c; m.operation = "DIFFERENCE"; m.solver = "EXACT"
        m.use_self = True; m.use_hole_tolerant = True     # the targets are several touching boxes in one mesh
    return c


def curve_obj(name, pts, mat, bevel=0.03, parent=None):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = bevel; cu.bevel_resolution = 2
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    cu.materials.append(B.M[mat])
    return _link(bpy.data.objects.new(name, cu), parent)


def scroll_pts(L, h, curl0=0.14, curl1=0.10, n=14):
    """C-scroll bracket in its own plane (a, z): a volute at the column (0, 0), a sweep up to (L, h), a small
    volute under the beam."""
    pts = []
    for i in range(n + 1):                  # volute at the column, from its eye outwards, ending heading up
        t = i / n; th = math.pi + 1.75 * math.pi * (1 - t); r = 0.03 + (curl0 - 0.03) * t
        pts.append((curl0 + r * math.cos(th), r * math.sin(th)))
    for i in range(1, n + 1):               # the sweep
        t = (math.pi / 2) * i / n
        pts.append((L * (1 - math.cos(t)), h * math.sin(t)))
    for i in range(1, n + 1):               # small volute under the beam, curling down
        t = i / n; th = math.pi / 2 - 1.75 * math.pi * t; r = curl1 - (curl1 - 0.025) * t
        pts.append((L + r * math.cos(th), h - curl1 + r * math.sin(th)))
    return pts


def bm_star(bm, R_, r_, h, M):
    """Five-pointed star in XY, raised to a point h along +Z (back at z = 0), placed by M."""
    ring = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5; rr = R_ if k % 2 == 0 else r_
        ring.append(bm.verts.new(M @ Vector((rr * math.cos(a), rr * math.sin(a), 0))))
    top = bm.verts.new(M @ Vector((0, 0, h)))
    bm.faces.new(ring[::-1])
    for k in range(10):
        bm.faces.new((ring[k], ring[(k + 1) % 10], top))


def column_bm(bm, x, y, z0, h, r, segs=None):
    segs = segs or (16 if r >= 0.18 else 12 if r >= 0.12 else 8)
    prof = [(0, 0), (r * 1.4, 0), (r * 1.4, 0.10), (r * 1.25, 0.16), (r * 1.1, 0.24), (r, 0.30),
            (r * 0.92, h - 0.42), (r * 1.02, h - 0.36), (r * 1.3, h - 0.20), (r * 1.5, h - 0.12), (r * 1.5, h), (0, h)]
    bm_lathe(bm, prof, segs, T(x, y, z0))


def globe_lamp_bm(bm, x, y, z, r=0.16):
    prof = [(0, -r)] + [(r * math.sin(math.pi * i / 10), -r * math.cos(math.pi * i / 10)) for i in range(1, 10)] + [(0, r)]
    bm_lathe(bm, prof, 12, T(x, y, z))


def text(name, body, size, loc, rot, mat, extrude=0.02):
    cu = bpy.data.curves.new(name, "FONT"); cu.body = body; cu.size = size; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.extrude = extrude; cu.resolution_u = 2 if size > 0.3 else 1     # letters are small: keep the triangle count down
    for f in ("C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf"):
        if pathlib.Path(f).exists():
            cu.font = bpy.data.fonts.load(f, check_existing=True); break
    cu.materials.append(B.M[mat])
    o = _link(bpy.data.objects.new(name, cu)); o.location = loc; o.rotation_euler = rot
    return o


def railing(name, p0, p1, z0, mat, h=1.05, step=0.14):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
    n = int(L / step)
    lo, hi = (min(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1))
    box(name + "_rails", [(lo[0] - 0.03, hi[0] + 0.03, lo[1] - 0.04, hi[1] + 0.04, z0 + h - 0.06, z0 + h),
                          (lo[0] - 0.02, hi[0] + 0.02, lo[1] - 0.03, hi[1] + 0.03, z0 + 0.1, z0 + 0.15)], mat)
    b = box(name + "_bars", (x0 - 0.012, x0 + 0.012, y0 - 0.012, y0 + 0.012, z0 + 0.15, z0 + h - 0.06), "iron")
    array_mod(b, n + 1, (ux * step, uy * step, 0))


# ================================================================ 1. the clock (the reference, as in the video)
def build_clock(v_face, hub, name="Clock", facing=-1):
    """Mickey clock with its dial at v_face, facing -v (the park side) or +v (into the gate hall)."""
    r = SPEC["clock_r"]
    turn = R(math.pi, "Z") if facing > 0 else Matrix.Identity(4)
    face = T(0, v_face, hub) @ turn @ R(math.pi / 2, "X")   # local XY = the dial plane, local +Z = outwards
    bm = bmesh.new(); bm_lathe(bm, [(0, 0), (r, 0), (r, 0.12), (0, 0.12)], 64, face @ T(0, 0, -0.12))
    obj_bm(f"ST_{name}_face", bm, "white")
    bm = bmesh.new()                                         # gold bezel, a flat torus
    bm_lathe(bm, [(r - 0.02, 0.0), (r + 0.10, 0.0), (r + 0.14, 0.06), (r + 0.10, 0.12), (r - 0.02, 0.12), (r - 0.06, 0.06), (r - 0.02, 0.0)],
             64, face @ T(0, 0, -0.06))
    obj_bm(f"ST_{name}_bezel", bm, "gold", smooth=True)
    bm = bmesh.new()                                         # Mickey: head and ears
    for cx, cy, rr in ((0, -0.08, 0.27), (-0.29, 0.22, 0.16), (0.29, 0.22, 0.16)):
        bm_lathe(bm, [(0, 0), (rr, 0), (rr, 0.015), (0, 0.015)], 32, face @ T(cx, cy, 0.0))
    obj_bm(f"ST_{name}_mickey", bm, "black")
    bm = bmesh.new()                                         # hands at 10:10
    for ang, ln, w in ((math.radians(150), 0.48, 0.05), (math.radians(30), 0.72, 0.035)):
        m = face @ T(0, 0, 0.03) @ R(ang, "Z")
        for v in bm_box(bm, 0.0, ln, -w / 2, w / 2, 0, 0.012):
            v.co = m @ v.co
    obj_bm(f"ST_{name}_hands", bm, "black")
    bm = bmesh.new(); bm_box(bm, r * 0.76, r * 0.92, -0.025, 0.025, 0.0, 0.02)   # one hour mark ...
    marks = obj_bm(f"ST_{name}_marks", bm, "gold")
    marks.location = (0, v_face + 0.005 * facing, hub); marks.rotation_euler = (math.pi / 2, 0, math.pi if facing > 0 else 0)
    radial_array(marks, 12, math.pi / 6)                    # ... and Array round the dial


# ================================================================ 2. the half-round fan window round the clock
def build_fan(v_plane, hub, facing=-1, name="FanS", gold=False):
    """Stone frame, rays (one ray + radial Array), bead ring (Array + Curve), glass. facing -1 = park side."""
    S = SPEC; r_in, fw = S["fan_r"], S["frame_w"]; d = facing
    rot = (math.pi / 2, 0, 0) if d < 0 else (math.pi / 2, 0, math.pi)
    prism(f"ST_{name}_frame", ring_sector(r_in, r_in + fw, 0, math.pi, 49, 0, hub), v_plane - 0.25, v_plane + 0.25, "trim", "xz", bevel=0.03)
    prism(f"ST_{name}_hubring", ring_sector(1.05, 1.28, 0, math.pi, 33, 0, hub), v_plane - 0.12, v_plane + 0.12, "trim", "xz")
    prism(f"ST_{name}_glass", [half_disc(r_in, 49, 0, hub)], v_plane - 0.015, v_plane + 0.015, "gold" if gold else "amber", "xz")
    bm = bmesh.new(); bm_box(bm, 1.28, r_in, -0.04, 0.04, -0.07, 0.07)          # one ray ...
    ray = obj_bm(f"ST_{name}_rays", bm, "trim")
    ray.location = (0, v_plane + 0.06 * d, hub); ray.rotation_euler = rot
    radial_array(ray, 17, math.pi / 16)                                           # ... repeated round the hub
    # bead ring inside the frame: one bead, Array fitted to the arc, Curve modifier (video: 配列 + カーブ)
    arc = arc_curve(f"ST_{name}_beadarc", r_in - 0.12, 0, math.pi, 65, (0, v_plane + 0.12 * d, hub), rot)
    bm = bmesh.new(); bm_box(bm, 0.0, 0.11, -0.055, 0.055, -0.05, 0.05)
    bead = obj_bm(f"ST_{name}_beads", bm, "gold" if gold else "trim")
    a = bead.modifiers.new("Array", "ARRAY"); a.fit_type = "FIT_CURVE"; a.curve = arc
    a.use_relative_offset = True; a.relative_offset_displace = (2.2, 0, 0)
    bend(bead, arc)
    box(f"ST_{name}_keys", [(-0.3, 0.3, v_plane - 0.32, v_plane + 0.32, hub + r_in - 0.05, hub + r_in + fw + 0.22),
                             (-r_in - fw - 0.1, -r_in + 0.05, v_plane - 0.3, v_plane + 0.3, hub - 0.25, hub + 0.05),
                             (r_in - 0.05, r_in + fw + 0.1, v_plane - 0.3, v_plane + 0.3, hub - 0.25, hub + 0.05)], "trim", 0.02)


# ================================================================ 3. the glass barrel vault over the gate hall
def build_vault():
    S = SPEC; r, zc, v0, v1 = S["vault_r"], S["vault_z"], S["vault_v0"], S["vault_v1"]
    L, span = math.pi * r, v1 - v0
    arc = arc_curve("ST_Vault_arc", r, 0, math.pi, 97, (0, 0, zc))
    # glass skin: a strip x = 0..L (arc length), local z = -v1..-v0 (local z is -v after standing up), bent over the arc
    bm = bmesh.new(); rows = 64
    ring = [(bm.verts.new((L * i / rows, -0.005, -v1)), bm.verts.new((L * i / rows, -0.005, -v0))) for i in range(rows + 1)]
    for i in range(rows):
        bm.faces.new((ring[i][0], ring[i + 1][0], ring[i + 1][1], ring[i][1]))
    glass = obj_bm("ST_Vault_glass", bm, "glass", recalc=False)
    bend(glass, arc)
    sd = glass.modifiers.new("Solidify", "SOLIDIFY"); sd.thickness = 0.02
    glass.visible_shadow = False
    # heavy ribs (7) and light glazing bars (25) across the vault: one bar along the arc + Array along the axis
    for nm, w, dep, cnt in (("ribs", 0.14, 0.34, 7), ("bars", 0.05, 0.12, 25)):
        bm = bmesh.new()
        for i in range(48):
            bm_box(bm, L * i / 48, L * (i + 1) / 48, 0.005, dep, -v1 - w / 2, -v1 + w / 2)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        o = obj_bm(f"ST_Vault_{nm}", bm, "white")
        array_mod(o, cnt, (0, 0, span / (cnt - 1)))
        bend(o, arc)
    # longitudinal glazing bars every 7.5 deg: one bar along the axis, Array along the arc, then bent
    bm = bmesh.new(); bm_box(bm, -0.03, 0.03, 0.005, 0.11, -v1, -v0)
    pur = obj_bm("ST_Vault_purlins", bm, "white")
    array_mod(pur, 25, (L / 24, 0, 0))
    bend(pur, arc)
    box("ST_Vault_beams", sym([(r - 0.25, r + 0.35, v0, v1, zc - 0.75, zc)]), "trim", 0.03)
    # glazed ends: end glass round the fan frame, an edge ring, radial glazing bars
    fr = S["fan_r"] + S["frame_w"]
    for vp, nm in ((v0 + 0.05, "S"), (v1 - 0.05, "N")):
        prism(f"ST_Vault_end{nm}_glass", [ring_sector(fr - 0.05, r, 0, math.pi, 49, 0, zc)], vp - 0.01, vp + 0.01, "glass", "xz").visible_shadow = False
        prism(f"ST_Vault_end{nm}_ring", ring_sector(r - 0.18, r + 0.02, 0, math.pi, 65, 0, zc), vp - 0.08, vp + 0.08, "white", "xz")
        bm = bmesh.new(); bm_box(bm, fr - 0.05, r - 0.1, -0.035, 0.035, -0.05, 0.05)
        sp = obj_bm(f"ST_Vault_end{nm}_bars", bm, "white")
        sp.location = (0, vp, zc); sp.rotation_euler = (math.pi / 2, 0, 0)
        radial_array(sp, 13, math.pi / 12)


# ================================================================ 4. pedestals, frieze, columns of the hall
def plaque_outline(w, h, n=12):
    pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h - w / 2)]
    pts += [(w / 2 * math.cos(math.pi * i / (n - 1)), h - w / 2 + w / 2 * math.sin(math.pi * i / (n - 1))) for i in range(1, n - 1)]
    return pts + [(-w / 2, h - w / 2)]


def frieze(name, x0, x1, z0, v_face, d, w=0.42, h=0.58, gap=0.16, mat="trim"):
    """Row of arched plaques on a face at v_face (d = outward): one plaque + Array (video: 装飾は同じもの → 配列)."""
    n = int((x1 - x0 + gap) // (w + gap)); start = (x0 + x1) / 2 - (n * (w + gap) - gap) / 2 + w / 2
    pts = [(start + x, z0 + z) for x, z in plaque_outline(w, h)]
    o = prism(name, [pts], min(v_face, v_face + 0.05 * d), max(v_face, v_face + 0.05 * d), mat, "xz")
    array_mod(o, n, (w + gap, 0, 0))
    return o


def build_gables():
    """Both gables of the vault. The park-side one carries the clock, which is built first (the reference)."""
    S = SPEC; hub, v0, v1 = S["hub_z"], S["vault_v0"], S["vault_v1"]
    top = S["cornice"] + 0.1
    fr = S["fan_r"] + S["frame_w"]
    build_clock(v0 - 0.62, hub - 0.05)                       # 1. the clock (park side) ...
    build_clock(v0 + 0.45, hub - 0.05, "ClockIn", facing=1)  # ... and its face into the gate hall (the video's view)
    build_fan(v0 - 0.05, hub, -1, "FanS")                    # 2. its fan window
    box("ST_GableS_pedestal", [(-3.4, 3.4, v0 - 0.45, v0 + 0.25, top, hub - 0.2),
                                (-3.55, 3.55, v0 - 0.55, v0 + 0.3, hub - 0.2, hub - 0.05)], "trim", 0.03)
    frieze("ST_GableS_frieze", -3.2, 3.2, top + 0.12, v0 - 0.45, -1)
    frieze("ST_GableS_frieze_in", -3.2, 3.2, top + 0.12, v0 + 0.25, 1)
    bm = bmesh.new()
    bm_lathe(bm, [(0, 0), (0.22, 0), (0.22, 0.1), (0.12, 0.2), (0.16, 0.45), (0.05, 0.75), (0.02, 1.1), (0, 1.15)], 16, T(0, v0 - 0.05, hub + fr + 0.2))
    obj_bm("ST_GableS_finial", bm, "gold", smooth=True)
    # hotel side: pedestal, gold fan with a medallion, slate hood over it
    box("ST_GableN_pedestal", [(-3.4, 3.4, v1 - 0.25, v1 + 0.45, S["eave"] - 0.2, hub - 0.2),
                                (-3.55, 3.55, v1 - 0.3, v1 + 0.55, hub - 0.2, hub - 0.05)], "trim", 0.03)
    frieze("ST_GableN_frieze", -3.2, 3.2, S["eave"], v1 + 0.45, 1)
    build_fan(v1 + 0.05, hub, 1, "FanN", gold=True)
    bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.8, 0), (0.85, 0.08), (0.8, 0.16), (0, 0.2)], 48, T(0, v1 + 0.2, hub) @ R(-math.pi / 2, "X"))
    obj_bm("ST_GableN_medallion", bm, "gold", smooth=True)
    prism("ST_GableN_hood", [ring_sector(fr, fr + 0.45, 0, math.pi, 49, 0, hub)], v1 - 0.2, v1 + 1.0, "slate", "xz", bevel=0.03)
    bm = bmesh.new()
    bm_lathe(bm, [(0, 0), (0.25, 0), (0.25, 0.1), (0.14, 0.25), (0.18, 0.5), (0.05, 0.85), (0.02, 1.2), (0, 1.25)], 16, T(0, v1 + 0.4, hub + fr + 0.4))
    obj_bm("ST_GableN_finial", bm, "gold", smooth=True)


def build_hall():
    """Columns, star medallions, scroll brackets, fretwork, gates, banners, lamps of the gate hall."""
    S = SPEC; F2, r, zc = S["F2"], S["vault_r"], S["vault_z"]
    cv = [-14.2, -9.3, -4.4, 1.2, 7.3]                       # columns under the springing beams (both sides)
    bm = bmesh.new()
    for s in (-1, 1):
        for v in cv[:-1]:
            column_bm(bm, s * (r + 0.05), v, F2, zc - 0.75 - F2, 0.2)
    obj_bm("ST_Hall_columns", bm, "trim", smooth=True)
    box("ST_Hall_plinths", [(s * (r + 0.05) - 0.32, s * (r + 0.05) + 0.32, v - 0.32, v + 0.32, F2, F2 + 0.35) for s in (-1, 1) for v in cv[:-1]], "trim", 0.02)
    # star medallions on the beams' inner faces above each column and between (ring + gold star)
    bm_r, bm_s = bmesh.new(), bmesh.new()
    spots = cv[:-1] + [(cv[i] + cv[i + 1]) / 2 for i in range(len(cv) - 1)]
    for s in (-1, 1):
        for v in spots:
            M = T(s * (r - 0.26), v, zc - 0.38) @ R(-s * math.pi / 2, "Y")
            bm_lathe(bm_r, [(0.24, 0), (0.33, 0), (0.33, 0.05), (0.24, 0.05)], 20, M)
            bm_lathe(bm_r, [(0, 0), (0.24, 0), (0.24, 0.015), (0, 0.015)], 20, M)
            bm_star(bm_s, 0.22, 0.09, 0.07, M @ T(0, 0, 0.02))
    obj_bm("ST_Hall_medallion_rings", bm_r, "trim")
    obj_bm("ST_Hall_stars", bm_s, "gold")
    # scroll brackets: C-scrolls from each column head up to the beam, both ways along the beam
    for s in (-1, 1):
        for i, v in enumerate(cv[:-1]):
            for d in (-1, 1):
                if i == 0 and d < 0:
                    continue
                P = [(s * (r - 0.02), v + d * a, zc - 1.45 + z) for a, z in scroll_pts(1.25, 0.62)]
                curve_obj(f"ST_Hall_scroll_{'W' if s < 0 else 'E'}{i}{'a' if d < 0 else 'b'}", P, "trim", 0.035)
    # fretwork plates between the columns: a plate with a segmental opening per bay
    bm = bmesh.new()
    for i in range(len(cv) - 1):
        a0, a1 = cv[i] + 0.25, cv[i + 1] - 0.25
        pts, _ = seg_arc((a0 + a1) / 2, zc - 1.25, a1 - a0, 0.45, 20)
        poly = [(a1, zc - 0.75), (a0, zc - 0.75)] + pts[::-1]
        for s in (-1, 1):
            bm_prism(bm, poly, min(s * (r - 0.02), s * (r + 0.04)), max(s * (r - 0.02), s * (r + 0.04)), "yz")
    obj_bm("ST_Hall_fretwork", bm, "trim")
    # frieze of small gilded plaques along the beams' inner faces (one + Array)
    for s in (-1, 1):
        pts = [(S["vault_v0"] + 0.9 + v, zc - 0.62 + z) for v, z in plaque_outline(0.3, 0.42)]
        o = prism(f"ST_Hall_frieze{'W' if s < 0 else 'E'}", [pts], min(s * (r - 0.25), s * (r - 0.29)), max(s * (r - 0.25), s * (r - 0.29)), "gold", "yz")
        array_mod(o, 40, (0, 0.52, 0))
    # ticket gates across the hall (one cabinet + Array) with green tops; offices each side
    g = box("ST_Hall_gates", (-5.9, -5.62, -10.1, -8.9, F2, F2 + 1.0), "gate", 0.02); array_mod(g, 10, (1.3, 0, 0))
    g2 = box("ST_Hall_gate_panels", (-5.93, -5.59, -10.0, -9.3, F2 + 1.0, F2 + 1.06), "gate_panel"); array_mod(g2, 10, (1.3, 0, 0))
    box("ST_Hall_offices", [(-9.45, -7.4, -14.4, -11.0, F2, F2 + 2.6), (7.4, 9.45, -14.4, -11.0, F2, F2 + 2.6)], "cream", 0.02)
    box("ST_Hall_office_windows", [(-7.42, -7.37, -14.0, -11.4, F2 + 1.0, F2 + 2.1), (7.37, 7.42, -14.0, -11.4, F2 + 1.0, F2 + 2.1)], "sign")
    # hanging banners (character banners in the photo: plain green here) and pendant lamps
    box("ST_Hall_banners", [(s * 4.2 - 0.45, s * 4.2 + 0.45, v - 0.01, v + 0.01, zc - 1.6, zc + 1.3) for s in (-1, 1) for v in (-12.0, -6.5)], "banner")
    bm = bmesh.new()
    for v in (-11.8, -7.0, -1.5):
        for s in (-1, 1):
            bm_lathe(bm, [(0, 0), (0.14, 0.05), (0.2, 0.3), (0.1, 0.42), (0, 0.45)], 16, T(s * 2.6, v, zc + 1.3))
    obj_bm("ST_Hall_pendants", bm, "lamp", smooth=True)
    box("ST_Hall_cords", [(s * 2.6 - 0.01, s * 2.6 + 0.01, v - 0.01, v + 0.01, zc + 1.75, zc + 4.9) for v in (-11.8, -7.0, -1.5) for s in (-1, 1)], "iron")


# ================================================================ 5. the building round the hall
def build_shell():
    S = SPEC; F2, sl, U, V0, V1 = S["F2"], S["slab"], S["bar_u"], S["bar_v0"], S["bar_v1"]
    cb, cv0, wu, wv0 = S["cb_u"], S["cb_v0"], S["wing_u"], S["wing_v0"]
    tv, eave = S["track_v"], S["eave"]
    # ---- ground floor: brick blocks either side of the through passage (lockers, toilets, offices)
    gw = box("ST_Ground_blocks", sym([(-U, -cb, V0, V1 - 0.5, 0, F2 - sl), (-wu, -cb, wv0, V0, 0, F2 - sl)]), "brick")
    doors = sym([(-14.5 - 1.1, -14.5 + 1.1, wv0 - 0.1, wv0 + 0.4, 0, 2.9)] + [(u - 1.1, u + 1.1, V0 - 0.1, V0 + 0.4, 0, 3.1) for u in (-42.0, -36.5)])
    doors += sym([(u - 1.1, u + 1.1, V1 - 0.9, V1 - 0.4, 0, 3.1) for u in (-40.0, -30.0, -20.0)])
    cutter("ST_Ground_doorcut", doors, gw)
    south = [d for d in doors if d[2] < 0]; north = [d for d in doors if d[2] > 0]
    box("ST_Ground_doors", [(d[0] + 0.15, d[1] - 0.15, d[2] + 0.3, d[2] + 0.36, 0, d[5] - 0.1) for d in south]
        + [(d[0] + 0.15, d[1] - 0.15, d[2] + 0.04, d[2] + 0.1, 0, d[5] - 0.1) for d in north], "sign")
    box("ST_Ground_door_heads", [(d[0] - 0.15, d[1] + 0.15, d[2] - 0.05, d[2] + 0.12, d[5], d[5] + 0.32) for d in south]
        + [(d[0] - 0.15, d[1] + 0.15, d[3] - 0.12, d[3] + 0.05, d[5], d[5] + 0.32) for d in north], "trim", 0.02)
    box("ST_Ground_plinth", sym([(-U - 0.05, -cb, V0 - 0.08, V0, 0, 0.55), (-U - 0.05, -cb, V1 - 0.5, V1 - 0.42, 0, 0.55),
                                  (-wu, -cb, wv0 - 0.08, wv0, 0, 0.55), (-U - 0.08, -U, V0, V1 - 0.5, 0, 0.55)]), "stone")
    box("ST_Ground_quoins", sym([(-U - 0.1, -U + 0.5, V0 - 0.1, V0 + 0.5, 0, F2 - sl), (-U - 0.1, -U + 0.5, V1 - 1.0, V1 - 0.4, 0, F2 - sl),
                                  (-wu - 0.1, -wu + 0.5, wv0 - 0.1, wv0 + 0.5, 0, F2 - sl)]), "trim", 0.02)
    # ---- 2F slabs: platform side up to the edge, the ledge beyond the track, hall + verandas; the track well
    box("ST_Floor_2F", [(-U, U, V0, S["plat_edge"], F2 - sl, F2), (-U, U, tv + 1.65, V1, F2 - sl, F2),
                        (-wu, wu, cv0, V0, F2 - sl, F2)], "tile")
    box("ST_Floor_well", (-U, U, S["plat_edge"], tv + 1.65, 3.8, 4.4), "concrete")
    box("ST_Floor_tactile", (-S["plat_u"], S["plat_u"], S["plat_edge"] - 0.9, S["plat_edge"] - 0.6, F2, F2 + 0.006), "yellow")
    # ---- the passage under the station: park face (two segmental arches), hotel face (lintels + murals)
    a0, a1 = S["arch_half"]; sp, rise = S["arch_spring"], S["arch_rise"]
    fs = box("ST_ParkFace_wall", (-cb, cb, cv0, cv0 + 0.5, 0, F2 + 0.15), "brick")
    cutter("ST_ParkFace_archcut", [arch_opening(a0, a1, -1, sp, rise), arch_opening(-a1, -a0, -1, sp, rise)], fs, "xz", (cv0 - 1, cv0 + 1))
    prism("ST_ParkFace_archbands", [arch_band(a0, a1, sp, rise, 0.45, 20, leg=0.3), arch_band(-a1, -a0, sp, rise, 0.45, 20, leg=0.3)],
          cv0 - 0.14, cv0 + 0.05, "trim", "xz", bevel=0.02)
    kz = sp + rise
    box("ST_ParkFace_piers", [(-a0, a0, cv0 - 0.2, cv0 + 0.5, 0, F2 + 0.15), (a1, cb, cv0 - 0.2, cv0 + 0.5, 0, F2 + 0.15),
                              (-cb, -a1, cv0 - 0.2, cv0 + 0.5, 0, F2 + 0.15)], "trim", 0.03)
    box("ST_ParkFace_imposts", [(x0 - 0.12, x1 + 0.12, cv0 - 0.32, cv0 + 0.5, sp - 0.3, sp) for x0, x1 in ((-a0, a0), (a1, cb), (-cb, -a1))], "trim", 0.03)
    box("ST_ParkFace_keys", [(c - 0.3, c + 0.3, cv0 - 0.24, cv0 + 0.1, kz - 0.15, kz + 0.55) for c in ((a0 + a1) / 2, -(a0 + a1) / 2)], "trim", 0.02)
    box("ST_ParkFace_string", (-cb - 0.1, cb + 0.1, cv0 - 0.28, cv0 + 0.3, F2 - 0.1, F2 + 0.15), "trim", 0.02)
    lamps = [(u, v + d * 0.55, d) for u in (-a0 - 0.05, a0 + 0.05, -a1 - 0.05, a1 + 0.05) for v, d in ((cv0 - 0.2, -1), (V1 + 0.18, 1))]
    bm = bmesh.new()
    for u, v, d in lamps:
        globe_lamp_bm(bm, u, v, sp - 0.95, 0.17)
    obj_bm("ST_Passage_lamps", bm, "lamp", smooth=True)
    box("ST_Passage_lamp_arms", [(u - 0.03, u + 0.03, min(v, v - d * 0.55), max(v, v - d * 0.55), sp - 0.8, sp - 0.74) for u, v, d in lamps], "iron")
    bm = bmesh.new()
    for v in (-9.5, -3.0):
        column_bm(bm, 0, v, 0, F2 - sl, 0.33)
    obj_bm("ST_Passage_columns", bm, "trim", smooth=True)
    box("ST_Passage_ceiling", (-cb, cb, cv0, V1, F2 - sl - 0.02, F2 - sl), "trim")
    fn = box("ST_HotelFace_wall", (-cb, cb, V1 - 0.5, V1, 0, 8.1), "brick")
    lint = sp - 0.2
    cutter("ST_HotelFace_cut", [(a0, a1, V1 - 1, V1 + 1, -1, lint), (-a1, -a0, V1 - 1, V1 + 1, -1, lint)], fn)
    lun = [arch_opening(a0 + 0.2, a1 - 0.2, lint + 0.35, lint + 0.35, rise), arch_opening(-a1 + 0.2, -a0 - 0.2, lint + 0.35, lint + 0.35, rise)]
    prism("ST_HotelFace_murals", lun, V1 + 0.01, V1 + 0.04, "mural", "xz")
    prism("ST_HotelFace_archbands", [arch_band(a0, a1, lint + 0.35, rise + 0.1, 0.4, 20, leg=0.35), arch_band(-a1, -a0, lint + 0.35, rise + 0.1, 0.4, 20, leg=0.35)],
          V1, V1 + 0.14, "trim", "xz", bevel=0.02)
    box("ST_HotelFace_lintels", [(a0 - 0.1, a1 + 0.1, V1 - 0.55, V1 + 0.16, lint, lint + 0.35), (-a1 - 0.1, -a0 + 0.1, V1 - 0.55, V1 + 0.16, lint, lint + 0.35)], "trim", 0.02)
    box("ST_HotelFace_piers", [(-a0, a0, V1 - 0.5, V1 + 0.18, 0, lint + 0.35), (a1, cb, V1 - 0.5, V1 + 0.18, 0, lint + 0.35),
                               (-cb, -a1, V1 - 0.5, V1 + 0.18, 0, lint + 0.35)], "trim", 0.03)
    box("ST_HotelFace_sign", (-6.6, 6.6, V1, V1 + 0.14, 6.85, 7.75), "sign", 0.02)
    box("ST_HotelFace_sign_frame", [(-6.75, 6.75, V1, V1 + 0.18, 6.75, 6.85), (-6.75, 6.75, V1, V1 + 0.18, 7.75, 7.85),
                                    (-6.95, -6.6, V1, V1 + 0.18, 6.95, 7.65), (6.6, 6.95, V1, V1 + 0.18, 6.95, 7.65)], "gold")
    text("ST_HotelFace_sign_text", "TOKYO DISNEYLAND STATION", 0.5, (0, V1 + 0.15, 7.3), (math.pi / 2, 0, math.pi), "trim")
    # ---- the parapet along the hotel side (the arcade stands on it) with its coping
    box("ST_North_parapet", sym([(-U, -cb, V1 - 0.5, V1, F2 - sl, 8.1)]), "brick")
    box("ST_North_coping", (-U - 0.1, U + 0.1, V1 - 0.6, V1 + 0.1, 8.1, 8.25), "trim", 0.02)
    # ---- 2F park-side wall (stone, paired arched windows under red awnings), end walls
    sw = box("ST_2F_southwall", sym([(-U, -wu, V0 - 0.35, V0, F2, eave - 0.2), (-U, -U + 0.35, V0, V1 - 0.5, F2, eave - 0.2)]), "stone")
    pairs = [22.5, 27.5, 32.5, 37.5, 42.5]
    wx = [s * c + dx for c in pairs for s in (-1, 1) for dx in (-0.6, 0.6)]
    cutter("ST_2F_windowcut", [arch_opening(x - 0.42, x + 0.42, F2 + 0.8, F2 + 2.7, 0.42, 12) for x in wx], sw, "xz", (V0 - 1.0, V0 + 0.6))
    box("ST_2F_windowglass", [(x - 0.42, x + 0.42, V0 - 0.2, V0 - 0.16, F2 + 0.8, F2 + 3.15) for x in wx], "dark_glass")
    prism("ST_2F_windowbands", [arch_band(s * c - 1.1, s * c + 1.1, F2 + 2.7, 0.8, 0.28, 16, leg=0.25) for c in pairs for s in (-1, 1)],
          V0 - 0.5, V0 - 0.3, "trim", "xz")
    box("ST_2F_sills", [(s * c - 1.2, s * c + 1.2, V0 - 0.55, V0 - 0.3, F2 + 0.6, F2 + 0.8) for c in pairs for s in (-1, 1)], "trim", 0.02)
    q = [(0.0, -0.95)] + [(0.55 * math.sin(math.pi / 2 * i / 10), 0.95 * math.cos(math.pi / 2 * i / 10) - 0.95) for i in range(11)]
    bm = bmesh.new()
    for x in wx:                                              # red awnings: quarter-round hoods over each window
        bm_prism(bm, [(V0 - 0.35 - a, F2 + 3.2 + z) for a, z in q], x - 0.45, x + 0.45, "yz")
    obj_bm("ST_2F_awnings", bm, "awning")
    box("ST_2F_innerwall", sym([(-wu, -cb, V0 - 0.3, V0, F2, eave - 0.2)]), "cream")
    box("ST_2F_pilasters", sym([(-U - 0.15, -U + 0.45, V0 - 0.5, V0 + 0.2, F2, eave - 0.2), (-wu - 0.05, -wu + 0.35, V0 - 0.45, V0, F2, eave - 0.2)]
                               + [(-c - 2.5, -c - 2.1, V0 - 0.45, V0, F2, eave - 0.2) for c in pairs[1:]]), "trim", 0.02)
    bm = bmesh.new()                                          # wall lamps and doors along the platform's back wall
    for s in (-1, 1):
        for u in (13.0, 19.0, 25.0, 31.0, 37.0, 43.0):
            globe_lamp_bm(bm, s * u, V0 + 0.5, F2 + 2.35, 0.14)
    obj_bm("ST_Platform_walllamps", bm, "lamp", smooth=True)
    box("ST_Platform_doors", sym([(-u - 0.6, -u + 0.6, V0, V0 + 0.05, F2, F2 + 2.4) for u in (16.0, 28.0, 40.0)]), "sign")
    # ---- centre block 2F (park face): windows, bay window, pilasters, cornice, parapet
    top = S["cornice"]
    cw = box("ST_Centre_wall", [(-cb, cb, cv0, cv0 + 0.4, F2 + 0.15, top - 0.3)] + sym([(-cb, -cb + 0.35, cv0, V0, F2, top - 0.3)]), "cream")
    grp = [4.3, 5.4, 6.5]
    cuts = [arch_opening(s * x - 0.4, s * x + 0.4, F2 + 0.7, F2 + 2.75, 0.4, 12) for s in (-1, 1) for x in grp]
    cuts.append([(-1.8, F2 + 0.35), (1.8, F2 + 0.35), (1.8, F2 + 3.4), (-1.8, F2 + 3.4)])
    cutter("ST_Centre_windowcut", cuts, cw, "xz", (cv0 - 1, cv0 + 1))
    cutter("ST_Centre_sidecut", sym([(-cb - 1, -cb + 1, -12.2, -5.6, F2, F2 + 3.3)]), cw)
    box("ST_Centre_windowglass", [(s * x - 0.4, s * x + 0.4, cv0 + 0.18, cv0 + 0.22, F2 + 0.7, F2 + 3.2) for s in (-1, 1) for x in grp], "dark_glass")
    prism("ST_Centre_windowcaps", [arch_band(s * 5.4 - 1.75, s * 5.4 + 1.75, F2 + 3.35, 0.45, 0.25, 16, leg=0.2) for s in (-1, 1)],
          cv0 - 0.12, cv0 + 0.05, "trim", "xz", bevel=0.02)
    box("ST_Centre_mullions", [(s * x - 0.08, s * x + 0.08, cv0 - 0.06, cv0 + 0.2, F2 + 0.6, F2 + 2.9) for s in (-1, 1) for x in (3.8, 4.85, 5.95, 7.0)]
        + [(s * 5.4 - 1.8, s * 5.4 + 1.8, cv0 - 0.15, cv0 + 0.2, F2 + 0.45, F2 + 0.62) for s in (-1, 1)], "trim", 0.015)
    box("ST_Centre_pilasters", sym([(-cb - 0.15, -cb + 0.45, cv0 - 0.2, cv0 + 0.4, F2 + 0.15, top - 0.3), (-2.75, -2.2, cv0 - 0.2, cv0 + 0.4, F2 + 0.15, top - 0.3)]), "trim", 0.02)
    box("ST_Centre_cornice", [(-cb - 0.35, cb + 0.35, cv0 - 0.4, cv0 + 0.45, top - 0.3, top - 0.1), (-cb - 0.45, cb + 0.45, cv0 - 0.5, cv0 + 0.45, top - 0.1, top + 0.05)]
        + sym([(-cb - 0.45, -cb + 0.3, cv0 - 0.5, V0, top - 0.3, top + 0.05)]), "trim", 0.02)
    dent = box("ST_Centre_dentils", (-cb - 0.2, -cb - 0.08, cv0 - 0.33, cv0, top - 0.42, top - 0.3), "trim"); array_mod(dent, 81, (0.25, 0, 0))
    box("ST_Centre_parapet", [(-cb, cb, cv0 - 0.2, cv0 + 0.15, top + 0.05, top + 0.6)] + sym([(-cb, -cb + 0.35, cv0, V0, top + 0.05, top + 0.6)]), "cream", 0.02)
    box("ST_Centre_roof", sym([(-cb, -S["vault_r"] + 0.3, cv0 + 0.2, V0, top - 0.3, top - 0.1)]), "concrete")
    bm = bmesh.new()
    for u in (-cb, -3.4, 3.4, cb):
        bm_lathe(bm, [(0, 0), (0.2, 0), (0.2, 0.1), (0.1, 0.2), (0.2, 0.45), (0.12, 0.62), (0.03, 0.75), (0, 0.78)], 16, T(u, cv0 - 0.05, top + 0.6))
    obj_bm("ST_Centre_urns", bm, "trim", smooth=True)
    # bay window (oriel) over the central pier: sill, glass, posts, header, cap, corbel with a pendant
    bay = [(-1.85, cv0 + 0.05), (1.85, cv0 + 0.05), (1.25, cv0 - 0.95), (-1.25, cv0 - 0.95)]
    scale = lambda k, ky=None: [(x * k, cv0 + 0.05 + (y - cv0 - 0.05) * (ky or k)) for x, y in bay]
    prism("ST_Bay_sill", [bay], F2 + 0.3, F2 + 0.8, "trim", bevel=0.02)
    prism("ST_Bay_glass", [scale(0.94)], F2 + 0.8, F2 + 3.1, "dark_glass")
    prism("ST_Bay_header", [bay], F2 + 3.1, F2 + 3.5, "trim", bevel=0.02)
    wide = scale(1.08, 1.1)
    prism("ST_Bay_cornice", [wide], F2 + 3.5, F2 + 3.62, "trim")
    bm = bmesh.new(); bm_loft(bm, [(x, y, F2 + 3.62) for x, y in wide], [(x, y, F2 + 4.1) for x, y in scale(0.35, 0.3)])
    obj_bm("ST_Bay_roof", bm, "slate")
    box("ST_Bay_posts", [(x - 0.07, x + 0.07, y - 0.07, y + 0.07, F2 + 0.8, F2 + 3.1) for x, y in bay[1:3] + [(0.42, cv0 - 0.95), (-0.42, cv0 - 0.95)]], "trim")
    bm = bmesh.new(); bm_loft(bm, [(x, y, F2 - 0.55) for x, y in scale(0.3, 0.25)], [(x, y, F2 + 0.3) for x, y in bay])
    obj_bm("ST_Bay_corbel", bm, "trim")
    bm = bmesh.new(); bm_lathe(bm, [(0, -0.55), (0.06, -0.5), (0.16, -0.3), (0.12, -0.1), (0.2, 0.0), (0, 0.02)], 16, T(0, cv0 - 0.2, F2 - 0.55))
    obj_bm("ST_Bay_pendant", bm, "gold", smooth=True)
    # ---- verandas (2F) between the hall and the stairs: columns, railing, beam
    bm = bmesh.new()
    for s in (-1, 1):
        for u in (10.6, 13.5, 16.4, 19.0):
            column_bm(bm, s * u, wv0 + 0.25, F2, 3.2, 0.13)
    obj_bm("ST_Veranda_columns", bm, "trim", smooth=True)
    for s, nm in ((-1, "W"), (1, "E")):
        railing(f"ST_Veranda{nm}_rail", (s * 10.0, wv0 + 0.25), (s * 19.0, wv0 + 0.25), F2, "white")
    box("ST_Veranda_beam", sym([(-wu - 0.3, -cb, wv0, wv0 + 0.5, F2 + 3.2, F2 + 3.55)]), "trim", 0.02)
    # ---- the arcade on the hotel side: columns on the parapet, fretwork arches between them, entablature
    us = sorted({round(s * x, 2) for s in (-1, 1) for x in [2.15, 6.45] + [6.45 + 3.0 * k for k in range(1, 13)] + [45.4]})
    bm = bmesh.new()
    for u in us:
        column_bm(bm, u, V1 - 0.25, 8.25, eave - 0.5 - 8.25, 0.15)
    obj_bm("ST_Arcade_columns", bm, "trim", smooth=True)
    bm = bmesh.new()
    for a, b_ in zip(us[:-1], us[1:]):
        pts, _ = seg_arc((a + b_) / 2, eave - 1.05, b_ - a - 0.3, 0.4 if b_ - a < 5 else 0.7, 18)
        bm_prism(bm, [(b_ - 0.15, eave - 0.5), (a + 0.15, eave - 0.5)] + pts[::-1], V1 - 0.28, V1 - 0.2, "xz")
    obj_bm("ST_Arcade_fretwork", bm, "trim")
    box("ST_Arcade_entablature", (-U - 0.1, U + 0.1, V1 - 0.55, V1 + 0.05, eave - 0.5, eave), "trim", 0.02)
    box("ST_South_entablature", sym([(-U - 0.1, -wu, V0 - 0.5, V0 + 0.1, eave - 0.2, eave)]), "trim", 0.02)
    # ---- trusses under the platform roof (one tie beam + Array), pendant lamps
    for s, nm in ((-1, "W"), (1, "E")):
        t = box(f"ST_Roof_ties{nm}", (s * 8.0 - 0.1, s * 8.0 + 0.1, V0, V1 - 0.5, eave - 0.45, eave - 0.15), "trim")
        array_mod(t, 13, (s * 3.0, 0, 0))
    bm = bmesh.new()
    for s in (-1, 1):
        for u in range(12, 44, 6):
            bm_lathe(bm, [(0, 0), (0.12, 0.02), (0.28, 0.18), (0.08, 0.3), (0, 0.32)], 16, T(s * u, -1.2, eave - 1.25))
    obj_bm("ST_Platform_pendants", bm, "lamp", smooth=True)
    # ---- platform screen doors: one panel + Array
    ps = box("ST_Platform_screens", (-S["plat_u"] + 0.2, -S["plat_u"] + 2.2, S["plat_edge"] - 0.3, S["plat_edge"] - 0.1, F2, F2 + 1.3), "white", 0.02)
    array_mod(ps, 36, (2.3, 0, 0))


# ================================================================ roofs
def hip(bm, x0, x1, y0, y1, ze, zr, gable=None):
    """Hip roof surface, ridge along x; gable = 'x0' / 'x1' leaves that end open (a gable wall closes it)."""
    d = (y1 - y0) / 2; ym = (y0 + y1) / 2
    ra, rb = x0 + (0 if gable == "x0" else d), x1 - (0 if gable == "x1" else d)
    if rb < ra:
        ra = rb = (x0 + x1) / 2
    V = lambda x, y, z: bm.verts.new((x, y, z))
    a, b_, c, e = V(x0, y0, ze), V(x1, y0, ze), V(x1, y1, ze), V(x0, y1, ze)
    r0 = V(ra, ym, zr); r1 = r0 if rb == ra else V(rb, ym, zr)
    if r1 is r0:
        bm.faces.new((a, b_, r0)); bm.faces.new((c, e, r0))
    else:
        bm.faces.new((a, b_, r1, r0)); bm.faces.new((c, e, r0, r1))
    if gable != "x0":
        bm.faces.new((e, a, r0))
    if gable != "x1":
        bm.faces.new((b_, c, r1))


def hip_y(bm, x0, x1, y0, y1, ze, zr):
    """Hip roof with the ridge along y (the kiosks are deeper than wide)."""
    d = min((x1 - x0) / 2, (y1 - y0) / 2); xm = (x0 + x1) / 2
    V = lambda x, y, z: bm.verts.new((x, y, z))
    a, b_, c, e = V(x0, y0, ze), V(x1, y0, ze), V(x1, y1, ze), V(x0, y1, ze)
    r0, r1 = V(xm, y0 + d, zr), V(xm, y1 - d, zr)
    bm.faces.new((a, b_, r0)); bm.faces.new((b_, c, r1, r0)); bm.faces.new((c, e, r1)); bm.faces.new((e, a, r0, r1))


def roof_obj(name, fill, mat="copper", thick=0.22):
    bm = bmesh.new(); fill(bm)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    o = obj_bm(name, bm, mat, recalc=False)
    m = o.modifiers.new("Solidify", "SOLIDIFY"); m.thickness = thick; m.offset = -1.0
    return o


def build_roofs():
    S = SPEC; U, V0, V1, ze, zr, r = S["bar_u"], S["bar_v0"], S["bar_v1"], S["eave"], S["ridge"], S["vault_r"]
    cb, wu, wv0, F2 = S["cb_u"], S["wing_u"], S["wing_v0"], S["F2"]
    y0, y1 = V0 - 0.7, V1 + 0.8; ym = (y0 + y1) / 2
    roof_obj("ST_Roof_platformW", lambda bm: hip(bm, -U - 0.6, -r - 0.3, y0, y1, ze, zr, gable="x1"))
    roof_obj("ST_Roof_platformE", lambda bm: hip(bm, r + 0.3, U + 0.6, y0, y1, ze, zr, gable="x0"))
    # cream ceiling boards under the platform roof (the photos show a light ceiling between the tie beams)
    for nm, x0, x1, g in (("W", -U - 0.1, -r - 0.3, "x1"), ("E", r + 0.3, U + 0.1, "x0")):
        bm = bmesh.new(); hip(bm, x0, x1, V0 - 0.1, V1 - 0.45, ze - 0.3, zr - 0.35, gable=g)
        bm.normal_update()
        for f in bm.faces:
            if f.normal.z > 0:
                f.normal_flip()
        obj_bm(f"ST_Roof_ceiling{nm}", bm, "trim", recalc=False)
    tri = [[(y0 + 0.3, ze - 0.2), (y1 - 0.3, ze - 0.2), (ym, zr - 0.1)]]
    prism("ST_Roof_gableW", tri, -r - 0.35, -r - 0.05, "trim", "yz")
    prism("ST_Roof_gableE", tri, r + 0.05, r + 0.35, "trim", "yz")
    for s, nm in ((-1, "W"), (1, "E")):                      # verandas: low hips
        x0, x1 = sorted((s * (cb + 0.3), s * (wu + 0.5)))
        roof_obj(f"ST_Roof_veranda{nm}", lambda bm, x0=x0, x1=x1: hip(bm, x0, x1, wv0 - 0.6, V0 - 0.1, F2 + 3.55, F2 + 4.9))
    for s, nm in ((-1, "W"), (1, "E")):                      # ridge cresting: one iron spike + Array
        x_start = s * (r + 0.4); n = int((U + 0.6 - (y1 - y0) / 2 - r - 0.4) / 0.45)
        bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.035, 0), (0.02, 0.28), (0.05, 0.32), (0, 0.45)], 8, T(x_start, ym, zr))
        c = obj_bm(f"ST_Roof_cresting{nm}", bm, "iron")
        array_mod(c, n, (s * 0.45, 0, 0))


# ================================================================ stairs and escalators (park side, both ends)
def build_stairs():
    S = SPEC; F2 = S["F2"]; ut, ub = S["wing_u"], S["st_u1"]
    v0, v1, e0, e1 = S["st_v0"], S["st_v1"], S["esc_v0"], S["esc_v1"]
    nst = 44; rise, run = F2 / nst, (ub - ut) / nst
    zl = lambda a: F2 * (ub - a) / (ub - ut)                    # stair line at distance a from the centre
    ue_b, ue_t = ub - 0.9, ut                                    # escalator incline from ue_b (z 0.2) to ue_t (z F2)
    ze = lambda a: 0.2 + (F2 - 0.2) * (ue_b - a) / (ue_b - ue_t)

    def poly(s, pts):                                            # (distance, z) -> (u, z), counter-clockwise
        p = [(s * a, z) for a, z in pts]
        area = sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))
        return p if area > 0 else p[::-1]

    for s, nm in ((-1, "W"), (1, "E")):
        U = lambda a, s=s: s * a
        prof = [(ub, 0.0)]                                       # steps: one saw-tooth profile across the stair
        for i in range(nst):
            a = ub - i * run
            prof += [(a, (i + 1) * rise), (a - run, (i + 1) * rise)]
        prof += [(ut - 0.6, F2), (ut - 0.6, F2 - 0.45), (ub - 1.0, 0.0)]
        prism(f"ST_Stair{nm}_steps", [poly(s, prof)], v0, v1, "tile", "xz")
        prism(f"ST_Stair{nm}_under", [poly(s, [(ub - 1.0, 0.0), (ut, 0.0), (ut, F2 - 0.55)])], v0 + 0.1, v1 - 0.1, "brick", "xz")
        for vv, k in ((v0 + 0.05, "a"), (v1 - 0.05, "b")):     # sloped rails
            prism(f"ST_Stair{nm}_rail{k}", [poly(s, [(ub, zl(ub) + 0.95), (ut, zl(ut) + 0.95), (ut, zl(ut) + 1.05), (ub, zl(ub) + 1.05)])],
                  vv - 0.04, vv + 0.04, "white", "xz")
        b = box(f"ST_Stair{nm}_bars", (U(ub - 0.15) - 0.015, U(ub - 0.15) + 0.015, v0 + 0.03, v0 + 0.07, rise, rise + 0.95), "white")
        array_mod(b, nst, (-s * run, 0, rise))                  # one baluster + Array climbing the flight
        bm = bmesh.new()
        for k in range(5):
            a = ub - 0.4 - k * (ub - ut - 0.8) / 4
            for vv in (v0 + 0.05, v1 - 0.05):
                column_bm(bm, U(a), vv, zl(a), 2.75, 0.09)
        obj_bm(f"ST_Stair{nm}_posts", bm, "trim", smooth=True)
        vm = (v0 + v1) / 2

        def stair_roof(bm, s=s):
            a0, a1 = ub + 0.3, ut - 0.2
            z0, z1 = zl(a0) + 2.85, zl(a1) + 2.85
            P = lambda a, v, z: bm.verts.new((s * a, v, z))
            e0a, e1a, r0, r1 = P(a0, v0 - 0.45, z0), P(a1, v0 - 0.45, z1), P(a0, vm, z0 + 0.8), P(a1, vm, z1 + 0.8)
            f0a, f1a = P(a0, v1 + 0.45, z0), P(a1, v1 + 0.45, z1)
            bm.faces.new((e0a, e1a, r1, r0)); bm.faces.new((f1a, f0a, r0, r1))
        roof_obj(f"ST_Stair{nm}_roof", stair_roof)
        # ---- escalator: truss, step band, glass balustrades, handrails, barrel canopy with ribs
        prism(f"ST_Esc{nm}_truss", [poly(s, [(ub + 0.3, -0.3), (ue_b, -0.3), (ue_t, F2 - 1.1), (ue_t - 1.2, F2 - 1.1), (ue_t - 1.2, F2),
                                              (ue_t, F2), (ue_b, 0.2), (ub + 0.3, 0.2)])], e0 + 0.1, e1 - 0.1, "stone", "xz")
        prism(f"ST_Esc{nm}_band", [poly(s, [(ub + 0.3, 0.2), (ue_b, 0.2), (ue_t, F2), (ue_t - 1.2, F2), (ue_t - 1.2, F2 + 0.03), (ue_t, F2 + 0.03),
                                             (ue_b, 0.23), (ub + 0.3, 0.23)])], e0 + 0.25, e1 - 0.25, "escalator", "xz")
        for vv, k in ((e0 + 0.12, "a"), (e1 - 0.12, "b")):
            prism(f"ST_Esc{nm}_glass{k}", [poly(s, [(ub, 0.23), (ue_b, 0.23), (ue_t, F2 + 0.03), (ue_t - 0.8, F2 + 0.03), (ue_t - 0.8, F2 + 0.95),
                                                    (ue_t, F2 + 0.95), (ue_b, 1.15), (ub, 1.15)])], vv - 0.02, vv + 0.02, "glass", "xz").visible_shadow = False
            prism(f"ST_Esc{nm}_hand{k}", [poly(s, [(ub - 0.1, 1.15), (ue_b, 1.15), (ue_t, F2 + 0.95), (ue_t - 0.8, F2 + 0.95), (ue_t - 0.8, F2 + 1.03),
                                                   (ue_t, F2 + 1.03), (ue_b, 1.23), (ub - 0.1, 1.23)])], vv - 0.05, vv + 0.05, "black", "xz")
        # barrel canopy: half cylinder along the incline, ribs = one rib + Array along the incline
        ec = (e0 + e1) / 2; rc = (e1 - e0) / 2 + 0.25
        d = Vector((U(ue_t) - U(ue_b), 0, ze(ue_t) - ze(ue_b))); Lc = d.length; d.normalize()
        base = Vector((U(ue_b + 0.6), ec, ze(ue_b + 0.6) + 2.35))
        bm = bmesh.new(); ring0, ring1 = [], []
        for i in range(17):
            th = math.pi * i / 16
            off = Vector((0, rc * math.cos(th), rc * math.sin(th)))
            ring0.append(bm.verts.new(base + off)); ring1.append(bm.verts.new(base + off + d * (Lc - 0.2)))
        for i in range(16):
            bm.faces.new((ring0[i], ring0[i + 1], ring1[i + 1], ring1[i]))
        bm.normal_update()
        cano = obj_bm(f"ST_Esc{nm}_canopy", bm, "copper", recalc=False)
        m = cano.modifiers.new("Solidify", "SOLIDIFY"); m.thickness = 0.05
        bm = bmesh.new()
        for i in range(16):
            th0, th1 = math.pi * i / 16, math.pi * (i + 1) / 16
            qd = [Vector((0, rr * math.cos(th), rr * math.sin(th))) for rr, th in ((rc + 0.01, th0), (rc + 0.07, th0), (rc + 0.07, th1), (rc + 0.01, th1))]
            va = [bm.verts.new(base + p) for p in qd]; vb = [bm.verts.new(base + p + d * 0.08) for p in qd]
            bm.faces.new(va); bm.faces.new(vb[::-1])
            for j in range(4):
                bm.faces.new((va[j], va[(j + 1) % 4], vb[(j + 1) % 4], vb[j]))
        rib = obj_bm(f"ST_Esc{nm}_ribs", bm, "copper")
        array_mod(rib, 14, tuple(d * ((Lc - 0.3) / 13)))
        bm = bmesh.new()
        for k in range(5):
            a = ue_b + 0.6 - k * (ue_b - ue_t - 1.0) / 4
            for vv in (e0 - 0.2, e1 + 0.2):
                column_bm(bm, U(a), vv, ze(a) - (0.3 if k == 0 else 0.0), 2.35 + (0.3 if k == 0 else 0.0), 0.07)
        obj_bm(f"ST_Esc{nm}_posts", bm, "trim", smooth=True)
        portal = arch_band(e0 - 0.35, e1 + 0.35, 2.6, 1.0, 0.35, 18, leg=2.6)
        prism(f"ST_Esc{nm}_portal", [portal], min(U(ub + 0.2) - 0.25, U(ub + 0.2) + 0.25), max(U(ub + 0.2) - 0.25, U(ub + 0.2) + 0.25), "trim", "yz", bevel=0.02)
        # entrance kiosk at the foot of the stair: columns, entablature, pediment, "DISNEY RESORT LINE", hip roof
        k0, k1 = ub + 0.1, ub + 1.7
        bm = bmesh.new()
        for a in (k0 + 0.2, k1 - 0.2):
            for vv in (v0 - 0.1, v1 + 0.1):
                column_bm(bm, U(a), vv, 0, 3.0, 0.13)
        obj_bm(f"ST_Kiosk{nm}_columns", bm, "trim", smooth=True)
        ka, kb = sorted((U(k0), U(k1)))
        box(f"ST_Kiosk{nm}_entablature", (ka - 0.1, kb + 0.1, v0 - 0.35, v1 + 0.35, 3.0, 3.45), "trim", 0.02)
        box(f"ST_Kiosk{nm}_signboard", (min(U(k1 + 0.1), U(k1 + 0.16)), max(U(k1 + 0.1), U(k1 + 0.16)), v0 - 0.1, v1 + 0.1, 3.06, 3.39), "stone")
        text(f"ST_Kiosk{nm}_text", "DISNEY RESORT LINE", 0.2, (U(k1 + 0.18), (v0 + v1) / 2, 3.225), (math.pi / 2, 0, s * math.pi / 2), "sign", 0.01)
        prism(f"ST_Kiosk{nm}_pediment", [[(v0 - 0.35, 3.45), (v1 + 0.35, 3.45), ((v0 + v1) / 2, 4.2)]], ka - 0.05, kb + 0.05, "trim", "yz", bevel=0.02)
        roof_obj(f"ST_Kiosk{nm}_roof", lambda bm, ka=ka, kb=kb: hip_y(bm, ka - 0.35, kb + 0.35, v0 - 0.6, v1 + 0.6, 3.45, 4.9))
        bm = bmesh.new(); bm_lathe(bm, [(0, 0), (0.1, 0), (0.1, 0.1), (0.05, 0.2), (0.08, 0.35), (0.02, 0.6), (0, 0.62)], 12, T((ka + kb) / 2, (v0 + v1) / 2, 4.85))
        obj_bm(f"ST_Kiosk{nm}_finial", bm, "gold", smooth=True)


# ================================================================ track, context
def build_track_and_context(context=True, reach=170.0):
    S = SPEC
    MH = mock_data()["maihama"]
    zt, zb = S["beam_top"], S["beam_top"] - S["beam_d"]
    bm, piers = bmesh.new(), bmesh.new()
    inside = lambda u, v: abs(u) < S["bar_u"] + 3 and S["cb_v0"] - 3 < v < S["bar_v1"] + 3
    for line in MH["loop"]:
        P = [to_local(x, y) for x, y in line]
        P = [p for p in P if abs(p[0]) < reach and abs(p[1]) < 150]
        for (ua, va), (ub_, vb) in zip(P[:-1], P[1:]):
            L = math.hypot(ub_ - ua, vb - va)
            if L < 1e-3:
                continue
            nx, ny = -(vb - va) / L * S["beam_w"] / 2, (ub_ - ua) / L * S["beam_w"] / 2
            bm_prism(bm, [(ua + nx, va + ny), (ua - nx, va - ny), (ub_ - nx, vb - ny), (ub_ + nx, vb + ny)], zb, zt, "xy")
        run = 0.0
        for (ua, va), (ub_, vb) in zip(P[:-1], P[1:]):
            L = math.hypot(ub_ - ua, vb - va); k = 25.0 - run
            while k <= L:
                t = k / L; u, v = ua + (ub_ - ua) * t, va + (vb - va) * t
                if not inside(u, v):
                    bm_lathe(piers, [(0, 0), (0.75, 0), (0.75, zb - 0.9), (1.3, zb - 0.3), (1.3, zb), (0, zb)], 20, T(u, v, 0))
                k += 25.0
            run = (run + L) % 25.0
    obj_bm("ST_Track_beam", bm, "concrete")
    obj_bm("ST_Track_piers", piers, "concrete", smooth=True)
    if not context:
        return
    ctx = bpy.data.collections.new("Context"); bpy.context.scene.collection.children.link(ctx)
    old = B.col; B.col = ctx
    box("CTX_ground", (-200, 200, -160, 170, -0.2, 0.0), "paving")
    box("CTX_checker", (-14, 14, -42, -24, 0.0, 0.01), "checker")
    box("CTX_planters", [(-40, -18, -34, -26, 0, 0.45), (18, 40, -34, -26, 0, 0.45)], "grass")
    k = 0
    for p in MH["places"]:
        if p.get("k") != "hotel":
            continue
        for ring in p["r"]:
            loc = [to_local(x, y) for x, y in ring]
            if min(math.hypot(u, v) for u, v in loc) > 220:
                continue
            if loc[0] == loc[-1]:
                loc = loc[:-1]
            k += 1
            prism(f"CTX_hotel{k}", [loc], 0.0, 30.0, "context")
            prism(f"CTX_hotel{k}_roof", [loc], 30.0, 30.6, "context_roof")
    B.col = old


def build_train():
    """The Resort Line set (train_blender: the same numbers as the mock's JS train) stopped at the platform."""
    import train_blender as TB
    objs = TB.build("train", "blue")
    t = bpy.data.objects.new("ST_Train", None); B.col.objects.link(t); t.parent = B.root
    t.location = (TRAIN_LEN / 2, SPEC["track_v"], SPEC["beam_top"]); t.rotation_euler = (0, 0, math.pi)   # nose to -u (to Bayside)
    for o in objs:
        o.parent = t
        for m in o.modifiers:              # hide the window cutters (train_blender parents them to the car)
            if m.type == "BOOLEAN" and m.object is not None:
                B.hide.append(m.object)
    return t


# ================================================================ scene, cameras, render
CAMERAS = {   # name -> (location, target, lens mm or 'fisheye'), station-local
    "park": ((0.0, -60.0, 1.7), (0.0, -8.0, 10.0), 24),
    "hotel": ((3.0, 36.0, 1.7), (0.0, 5.0, 8.0), 20),
    "concourse": ((0.0, -3.0, 8.7), (0.0, -14.8, 13.0), "fisheye"),
    "gates": ((0.0, -0.8, 8.6), (0.0, -14.0, 11.8), 16),
    "platform": ((-30.0, -2.0, 8.65), (8.0, 1.8, 9.0), 20),
    "stairs": ((-44.0, -25.0, 1.7), (-27.0, -11.0, 4.2), 24),
    "aerial": ((75.0, -85.0, 62.0), (0.0, 0.0, 7.0), 30),
}


def world_sky():
    sc = bpy.context.scene
    world = bpy.data.worlds.get("W") or bpy.data.worlds.new("W"); sc.world = world
    if world.node_tree is None:
        world.use_nodes = True
    nt = world.node_tree; nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "MULTIPLE_SCATTERING"
    except TypeError:
        pass
    sky.sun_elevation = math.radians(SUN_EL); sky.sun_rotation = math.radians(90 - SUN_AZ + FRAME["ang_deg"])
    try:
        sky.sun_disc = False             # the sun is a lamp (sharp, controllable shadows); the sky gives the fill
    except AttributeError:
        pass
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 0.035
    o = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs["Background"], o.inputs["Surface"])
    sun = bpy.data.objects.get("Sun")
    if sun is None:
        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = SUN_W; sun.data.angle = math.radians(0.8)
    el, az = math.radians(SUN_EL), math.radians(SUN_AZ - FRAME["ang_deg"])   # SUN_AZ is on the map; the scene is station-local
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    sun.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()


def add_cameras():
    out = {}
    for name, (loc, tgt, lens) in CAMERAS.items():
        cam = bpy.data.cameras.new("CAM_" + name)
        if lens == "fisheye":
            cam.type = "PANO"; cam.panorama_type = "FISHEYE_EQUISOLID"; cam.fisheye_lens = 8.0; cam.fisheye_fov = math.radians(180)
        else:
            cam.lens = lens
        cam.clip_start = 0.05; cam.clip_end = 2000
        co = bpy.data.objects.new("CAM_" + name, cam); B.col.objects.link(co); co.parent = B.root
        co.location = loc
        co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        out[name] = co
    return out


def build(train=True, context=True, reach=170.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    B.col = bpy.data.collections.new("TDL_Station"); sc.collection.children.link(B.col)
    B.cutters = bpy.data.collections.new("Cutters"); sc.collection.children.link(B.cutters)
    B.root = bpy.data.objects.new("TDL_Station", None); B.col.objects.link(B.root)
    # the .blend keeps the station at the origin (easy to look at); export_models places it with FRAME
    B.root.location = (0.0, 0.0, 0.0); B.root.rotation_euler = (0, 0, 0); B.hide = []
    B.M = materials()
    t0 = time.time()
    build_gables()          # 1-2: the clock first, then its fan window and the gables
    build_vault()           # 3
    build_hall()            # 4-5
    build_shell()           # 6: the building round the hall
    build_roofs()
    build_stairs()
    build_track_and_context(context, reach)
    if train:
        try:
            build_train()
        except Exception as ex:               # train_blender had never run in Blender: never block the station
            print("[station] train skipped:", repr(ex))
    for c in B.cutters.objects:
        c.parent = B.root
    cams = add_cameras()
    print(f"[station] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")
    return cams


def render(cams, which, samples, percent, engine="CYCLES", prefix="station"):
    sc = bpy.context.scene
    if engine == "WORKBENCH":        # quick shape check: flat material colours, cavity, shadows
        sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading
        sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_cavity = True; sh.show_shadows = True
    else:
        sc.render.engine = "CYCLES"
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.resolution_percentage = percent
    sc.view_settings.view_transform = "AgX"
    for name in which:
        sc.camera = cams[name]
        sc.render.filepath = str((OUT / f"{prefix}_{name}{'_wb' if engine == 'WORKBENCH' else ''}.png").resolve())
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[station] rendered {name} in {time.time() - t:.0f}s")


def frame_view():
    """Saved 3D views look at the station from the park side, with material colours and a long clip range."""
    from mathutils import Euler
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type != "VIEW_3D":
                continue
            for sp in area.spaces:
                if sp.type != "VIEW_3D":
                    continue
                sp.clip_start, sp.clip_end = 0.1, 5000.0
                sp.shading.type = "SOLID"; sp.shading.color_type = "MATERIAL"
                sp.shading.show_cavity = True
                r3 = sp.region_3d
                r3.view_perspective = "PERSP"
                r3.view_location = (0.0, -6.0, 7.0); r3.view_distance = 95.0
                r3.view_rotation = Euler((math.radians(68), 0, math.radians(-28)), "XYZ").to_quaternion()


# ================================================================ for the outline mock (export_models.py --parts tdl_station)
def export_objects(merged):
    """Build without train / context, then one mesh per material ("ST_<material>") in the mock's frame:
    DisneySea local metres, heights on the DEM datum (the station ground is FRAME ground_datum). `merged` is
    export_models.merged(name, [(obj, dz)], col) with every object's world matrix and modifiers applied."""
    build(train=False, context=False, reach=60.0)
    B.root.location = (FRAME["x"], FRAME["y"], 0.0); B.root.rotation_euler = (0, 0, math.radians(FRAME["ang_deg"]))
    for o in B.col.objects:                  # web weight: no bevels, thinner scroll curves (the .blend keeps them)
        for m in o.modifiers:
            if m.type == "BEVEL":
                m.show_viewport = False
        if o.type == "CURVE" and o.data.bevel_depth > 0:
            o.data.bevel_resolution = 0; o.data.resolution_u = 4
    bpy.context.view_layer.update()
    groups = {}
    for o in B.col.objects:
        if o.type not in ("MESH", "CURVE", "FONT") or o.hide_render or o.name.startswith("CAM_"):
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if not mats:
            continue
        groups.setdefault("ST_" + mats[0].name[3:], []).append((o, FRAME["ground_datum"]))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default="park,hotel,concourse,platform,stairs,aerial")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--percent", type=int, default=80)
    ap.add_argument("--no-train", action="store_true")
    ap.add_argument("--no-context", action="store_true")
    ap.add_argument("--quick", action="store_true", help="Workbench renders (shape check) instead of Cycles")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    cams = build(train=not a.no_train, context=not a.no_context)
    world_sky()
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.camera = cams["park"]
    for c in list(B.cutters.objects) + B.hide:
        c.hide_set(True)
    frame_view()
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "tdl_station.blend").resolve()))
    print("[station] saved", OUT / "tdl_station.blend")
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        render(cams, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES")


if __name__ == "__main__" and bpy is not None:
    main()
