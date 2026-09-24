"""Railway structures of the Maihama area: the Disney Resort Line (straddle monorail) and the JR Keiyo Line viaduct
(Blender 5.2).

  blender -b --python ds_tracks.py -- --cams rl_curve,rl_close,rl_bayside,jr_station,jr_close,jr_aerial,overview --samples 24
  blender -b --python export_models.py -- --parts tracks      # the mock's model (models/tracks.json)

Data: the mock's own lines (tds_outline.html: maihama.loop = the Resort Line, maihama.jr = the two Keiyo Line tracks,
maihama.platforms = the OSM platforms), the DEM grids for the ground under the piers. DisneySea frame metres, heights
on the promenade datum (the same numbers the mock's trains run on: Resort Line beam top loop_z + 0.9 = 4.21 m, Keiyo
Line rail top jr_z = 10.0 m).

Resort Line (straddle monorail, built like the Alweg / Hitachi lines):
  * the running beam: a prestressed concrete girder 0.85 m wide and 1.5 m deep (the train's tyres run on its top, the
    guide and stabilising wheels on its sides), in spans of about 22 m with steel finger plates over the joints
  * power: two conductor rails on each side of the beam, low down, on insulator brackets (one bracket + Array + Curve
    along the beam, the video's way of repeating a part along a path)
  * piers at the joints: a rounded column from the ground, a flared hammerhead cap, bearings under the beam
  * platforms of Resort Gateway, Bayside and Tokyo DisneySea stations at the car floor (beam top + 1 m), with a
    yellow edge line, screen doors and a canopy; Tokyo Disneyland Station has its own Blender model (ds_tdl_station),
    so the track model leaves out its span
Keiyo Line (JR East elevated section at Maihama, double track, 1,067 mm gauge):
  * a reinforced concrete rigid-frame viaduct: deck slab whose width follows the two tracks (they spread round the
    island platform), sound-barrier parapets, two-column bents every 10 m with cross beams
  * slab track: concrete track slabs, 50 kg rails (head, web, foot), fastenings
  * overhead line: H-steel masts both sides with a truss beam over both tracks every 50 m, messenger wire and contact
    wire over each track
  * Maihama station: the island platform (OSM) at rail top + 1.1 m with a long canopy on columns

ESTIMATES (no drawings): beam depth, span 22 m, pier shapes, conductor rail heights, viaduct deck width (tracks +
2.8 m each side), parapet 1.6 m, bent spacing 10 m, mast spacing 50 m, wire heights (contact 5.1 m, messenger 6.2 m
above the rail), platform canopies. Heights follow the mock (see above), not survey data.
"""
import sys, math, json, re, argparse, pathlib, time

try:
    import bpy, bmesh
    from mathutils import Vector, Matrix
except ImportError:
    bpy = bmesh = Vector = Matrix = None

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ds_tdl_station as ST
from ds_tdl_station import B, obj_bm, bm_box, bm_lathe, bm_prism, T, R, _principled, _mottle, text

OUT = ROOT / "output" / "disneyland" / "tracks"
RL_STATIONS = False          # the other three Resort Line stations are built separately later (user, 2026-09-25)
WEB = False                  # export_objects() sets it: lighter piers, sampling and fittings for the mock
SPEC = dict(beam_w=0.85, beam_d=1.5, span=22.0, jr_gauge=1.067, jr_deck_edge=2.8, parapet=1.6, bent=10.0, mast=50.0,
            contact=5.1, messenger=6.2, platform_jr=1.1, ground_fallback=-2.3)


# ================================================================ data
def data():
    page = (ROOT / "output" / "disneysea" / "tds_outline.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S).group(1).replace(r"<\/", "</"))


def make_ground(D):
    grids = [D["hgrid"]] + ([D["disneyland"]["hgrid"]] if D.get("disneyland", {}).get("hgrid") else [])

    def g(G, x, y):
        fi, fj = (x - G["x0"]) / G["step"], (y - G["y0"]) / G["step"]; i, j = int(math.floor(fi)), int(math.floor(fj))
        if i < 0 or j < 0 or i >= G["nx"] - 1 or j >= G["ny"] - 1:
            return None
        v = lambda a, b: G["v"][b * G["nx"] + a]; u, w = fi - i, fj - j
        return v(i, j) * (1 - u) * (1 - w) + v(i + 1, j) * u * (1 - w) + v(i, j + 1) * (1 - u) * w + v(i + 1, j + 1) * u * w

    def h(x, y):
        for G in grids:
            r = g(G, x, y)
            if r is not None:
                return r
        return SPEC["ground_fallback"]
    return h


def chain_loop(lines):
    """The Resort Line ways joined into one closed ring (as the mock's RL does), anticlockwise."""
    d2 = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    rest = [[(p[0], p[1]) for p in l] for l in lines]
    pts = rest.pop(0)
    while rest:
        end = pts[-1]; bi, bd, rev = 0, 1e18, False
        for i, s in enumerate(rest):
            a, b = d2(end, s[0]), d2(end, s[-1])
            if a < bd:
                bd, bi, rev = a, i, False
            if b < bd:
                bd, bi, rev = b, i, True
        s = rest.pop(bi)
        if rev:
            s.reverse()
        pts += s[1:] if bd < 0.5 else s
    if d2(pts[0], pts[-1]) < 0.5:
        pts.pop()
    area = sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))
    if area < 0:
        pts.reverse()
    return pts


def chaikin(pts, closed, it=2):
    """Corner cutting: smooth curves out of the OSM polylines (the offset from the lines is well under a metre)."""
    for _ in range(it):
        out = []
        n = len(pts)
        rng = range(n) if closed else range(n - 1)
        if not closed:
            out.append(pts[0])
        for i in rng:
            a, b = pts[i], pts[(i + 1) % n]
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def resample(pts, step, closed):
    P = pts + ([pts[0]] if closed else [])
    cum = [0.0]
    for a, b in zip(P[:-1], P[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    L = cum[-1]; n = max(2, int(round(L / step)))
    out, j = [], 0
    for k in range(n + (0 if closed else 1)):
        s = L * k / n
        while j < len(cum) - 2 and cum[j + 1] < s:
            j += 1
        t = (s - cum[j]) / max(1e-9, cum[j + 1] - cum[j])
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t, s))
    return out, L


def frames(pts, closed):
    """Tangent and left normal at each point (mitred: the normal is scaled so offsets keep their width at bends)."""
    n = len(pts); out = []
    for i in range(n):
        a = pts[i - 1] if (closed or i > 0) else pts[i]
        b = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        p = pts[i]
        t0 = (p[0] - a[0], p[1] - a[1]); t1 = (b[0] - p[0], b[1] - p[1])
        l0, l1 = math.hypot(*t0) or 1, math.hypot(*t1) or 1
        t0 = (t0[0] / l0, t0[1] / l0) if l0 > 1e-9 else None
        t1 = (t1[0] / l1, t1[1] / l1) if l1 > 1e-9 else None
        if t0 is None or (not closed and i == 0):
            t = t1
        elif t1 is None or (not closed and i == n - 1):
            t = t0
        else:
            t = (t0[0] + t1[0], t0[1] + t1[1]); lt = math.hypot(*t) or 1; t = (t[0] / lt, t[1] / lt)
        nrm = (-t[1], t[0])
        k = 1.0
        if t0 and t1 and (closed or 0 < i < n - 1):
            k = 1.0 / max(0.5, (-t0[1] * nrm[0] + t0[0] * nrm[1]))
        out.append((t, nrm, k))
    return out


def curvature(pts, closed):
    """Signed curvature (1/m, + = turning left) at each point, smoothed."""
    n = len(pts); out = []
    for i in range(n):
        a = pts[i - 1] if (closed or i > 0) else pts[i]; b = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]; p = pts[i]
        h0 = math.atan2(p[1] - a[1], p[0] - a[0]) if (a != p) else None; h1 = math.atan2(b[1] - p[1], b[0] - p[0]) if (b != p) else None
        if h0 is None or h1 is None:
            out.append(0.0); continue
        d = (h1 - h0 + math.pi) % (2 * math.pi) - math.pi
        out.append(d / max(1e-6, 0.5 * (math.hypot(p[0] - a[0], p[1] - a[1]) + math.hypot(b[0] - p[0], b[1] - p[1]))))
    for _ in range(4):
        out = [(out[i - 1] + 2 * out[i] + out[(i + 1) % n]) / 4 if (closed or 0 < i < n - 1) else out[i] for i in range(n)]
    return out


def sweep(bm, pts, profile, closed, z_of, cap=True, mitre=True, roll=None):
    """Extrude a closed (y, z) profile along plan points; z_of(i) gives the base height at point i; roll(i) (rad)
    turns the profile about its origin (a banked beam on a curve)."""
    F = frames([(p[0], p[1]) for p in pts], closed)
    rings = []
    for i, p in enumerate(pts):
        t, nrm, k = F[i]; k = k if mitre else 1.0; z0 = z_of(i)
        c = roll(i) if roll else 0.0; cc, sc = math.cos(c), math.sin(c)
        prof = [(y * cc - z * sc, y * sc + z * cc) for y, z in profile] if c else profile
        rings.append([bm.verts.new((p[0] + nrm[0] * y * k, p[1] + nrm[1] * y * k, z0 + z)) for y, z in prof])
    m = len(profile)
    segs = len(rings) if closed else len(rings) - 1
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % len(rings)]
        for j in range(m):
            jj = (j + 1) % m
            try:
                bm.faces.new((a[j], a[jj], b[jj], b[j]))
            except ValueError:
                pass
    if cap and not closed:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return rings


def poly_curve(name, pts, z, closed=False):
    """A poly curve object through plan points at height z (for Array + Curve)."""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.twist_mode = "Z_UP"
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], z if not callable(z) else z(i), 1)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu); B.col.objects.link(o); o.parent = B.root; o.hide_render = True
    return o


# ================================================================ materials
def materials():
    M = ST.materials()
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    for key, name, col, sc in (("beam", "st_beam", (0.52, 0.51, 0.48), 3.0), ("pier", "st_pier", (0.58, 0.57, 0.54), 2.0),
                               ("viaduct", "st_viaduct", (0.47, 0.47, 0.45), 2.5)):   # weathered concrete: mottled, a little bumpy
        mat, nt, b = _principled(name, col, 0.85); _mottle(nt, b, col, sc, 0.8, 0.12); M[key] = mat
    M["steel"] = P("st_steel", (0.55, 0.57, 0.60), 0.35, Metallic=0.9)
    M["rail"] = P("st_rail", (0.42, 0.40, 0.38), 0.3, Metallic=0.9)
    M["slab"] = P("st_slab", (0.42, 0.42, 0.40), 0.9)
    mat, nt, b = _principled("st_deck_top", (0.16, 0.16, 0.16), 0.95); _mottle(nt, b, (0.16, 0.16, 0.16), 1.5, 0.8, 0.1); M["deck_top"] = mat
    M["barrier"] = P("st_barrier", (0.68, 0.70, 0.70), 0.5, Metallic=0.3)
    M["insulator"] = P("st_insulator", (0.30, 0.22, 0.18), 0.4)
    M["copper_wire"] = P("st_copper_wire", (0.45, 0.32, 0.20), 0.35, Metallic=0.9)
    M["mast"] = P("st_mast", (0.50, 0.53, 0.55), 0.5, Metallic=0.7)
    M["canopy"] = P("st_canopy", (0.86, 0.87, 0.88), 0.5)
    mat, nt, b = _principled("st_ground_ctx", (0.22, 0.26, 0.17), 0.95); _mottle(nt, b, (0.22, 0.26, 0.17), 0.05, 0.7, 0.0); M["ground_ctx"] = mat
    return M


# ================================================================ the Resort Line
def build_resort_line(D, h, skip):
    S = SPEC; zt = D["maihama"]["loop_z"] + 0.9; zb = zt - S["beam_d"]
    loop = chaikin(chain_loop(D["maihama"]["loop"]), True, 2)
    pts, L = resample(loop, 4.0 if WEB else 2.0, True)
    keep = [True for p in pts]                               # the beam runs unbroken, through Tokyo Disneyland Station too
    # runs of kept points (the loop is cut where Tokyo Disneyland Station's own model takes over)
    runs, cur = [], []
    for i, p in enumerate(pts):
        if keep[i]:
            cur.append(p)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        if runs and keep[0]:
            runs[0] = cur + runs[0]
        else:
            runs.append(cur)
    closed = all(keep)
    hw = S["beam_w"] / 2
    beam = [(hw, 0.0), (hw, -1.0), (hw - 0.06, -S["beam_d"] + 0.05), (hw - 0.1, -S["beam_d"]), (-hw + 0.1, -S["beam_d"]),
            (-hw + 0.06, -S["beam_d"] + 0.05), (-hw, -1.0), (-hw, 0.0)]
    bm_b, bm_r, bm_p, bm_s, bm_j = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    rail = [(0.0, 0.0), (0.07, 0.0), (0.07, 0.11), (0.0, 0.11)]
    piers = []
    kap = curvature([(p[0], p[1]) for p in pts], True); ki = {id(p): kap[i] for i, p in enumerate(pts)}
    CANT_MAX = math.radians(6.0)
    for run in runs:
        roll = lambda i, run=run: max(-CANT_MAX, min(CANT_MAX, ki[id(run[i])] * 220.0))   # radius 100 m -> about 2.2 deg
        sweep(bm_b, run, beam, closed, lambda i: zt, roll=roll)
        for side in (-1, 1):                               # conductor rails, low on the beam sides (the collector shoes' height)
            for dz in ((-1.03,) if WEB else (-0.95, -1.12)):
                prof = [(side * (hw + 0.09 + y), z + dz) for y, z in rail]
                sweep(bm_r, run, prof if side > 0 else [(y, z) for y, z in prof][::-1], closed, lambda i: zt, roll=roll)
        # joints every span: finger plates on the top, a pier under each
        s0 = run[0][2]
        for p in run:
            if (p[2] - s0) % S["span"] < (4.0 if WEB else 2.0) - 1e-6 and not skip(p[0], p[1]):   # no piers inside the station
                piers.append(p)
    F = frames([(p[0], p[1]) for p in pts], True)
    idx = {id(p): i for i, p in enumerate(pts)}
    for p in piers:
        i = idx[id(p)]; t, nrm, _ = F[i]
        g = h(p[0], p[1])
        ang = math.atan2(t[1], t[0])
        M = Matrix.Translation((p[0], p[1], 0.0)) @ Matrix.Rotation(ang, 4, "Z")
        # column: round, 1.5 m across, rising from a footing to a trumpet-shaped head that takes the beam
        top = zb - 0.12
        prof = [(0.0, g - 0.3), (1.1, g - 0.3), (1.1, g + 0.05), (0.78, g + 0.12), (0.75, top - 2.4)]
        for k in range(1, 5 if WEB else 9):                   # the flare: a quarter circle of radius 1.9 m
            a_ = math.pi / 2 * k / (4 if WEB else 8)
            prof.append((0.75 + 1.9 * (1 - math.cos(a_)) * 0.32, top - 2.4 + 2.3 * math.sin(a_)))
        prof += [(1.36, top), (0.0, top)]
        bm_lathe(bm_p, prof, 12 if WEB else 24, M)
        for dx in (-0.45, 0.45):                             # bearings and the finger plate over the joint
            vs = bm_box(bm_s, -0.18, 0.18, -0.3, 0.3, zb - 0.12, zb)
            for v in vs:
                v.co = Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(ang, 4, "Z") @ Vector((v.co.x + dx, v.co.y, v.co.z))
        vs = bm_box(bm_s, -0.25, 0.25, -hw + 0.02, hw - 0.02, zt, zt + 0.012)
        for v in vs:
            v.co = M @ v.co
        for v in bm_box(bm_j, -0.02, 0.02, -hw - 0.005, hw + 0.005, zb - 0.005, zt - 0.005):   # the joint between spans
            v.co = M @ v.co
    obj_bm("TK_RL_beam", bm_b, "beam", recalc=True)
    obj_bm("TK_RL_conductor", bm_r, "iron")
    obj_bm("TK_RL_piers", bm_p, "pier", smooth=False)
    obj_bm("TK_RL_bearings", bm_s, "steel")
    obj_bm("TK_RL_joints", bm_j, "iron")
    # insulator brackets along the beam: one bracket + Array (fit to the curve) + Curve, per run and side
    for r_i, run in enumerate([] if WEB else runs):          # (the mock leaves the brackets out)
        cv = poly_curve(f"TK_RL_path{r_i}", [(p[0], p[1]) for p in run], zt, closed)
        Lr = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(run[:-1], run[1:]))
        for side in (-1, 1):
            bm = bmesh.new()
            bm_box(bm, 0.0, 0.05, side * hw, side * (hw + 0.12), -1.2, -0.9) if side > 0 else bm_box(bm, 0.0, 0.05, side * (hw + 0.12), side * hw, -1.2, -0.9)
            o = obj_bm(f"TK_RL_brackets{r_i}_{side}", bm, "insulator")
            a = o.modifiers.new("Array", "ARRAY"); a.count = max(1, int(Lr / 3.0)); a.use_relative_offset = False
            a.use_constant_offset = True; a.constant_offset_displace = (3.0, 0, 0)
            o.location = (0, 0, 0)
            mc = o.modifiers.new("Curve", "CURVE"); mc.object = cv; mc.deform_axis = "POS_X"
            o.location = cv.location
    return pts


def build_rl_platforms(D, h, skip):
    """Platforms of the other three Resort Line stations: slab at the car floor, edge line, screen doors, canopy."""
    MH = D["maihama"]; zf = MH["loop_z"] + 0.9 + 1.0
    loop = chain_loop(MH["loop"])
    bm_s, bm_y, bm_d, bm_c, bm_k = (bmesh.new() for _ in range(5))
    for r in MH["platforms"]:
        cx, cy = sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)
        if math.hypot(cx - MH["station"]["x"], cy - MH["station"]["y"]) < 60 or skip(cx, cy):
            continue                                        # the JR island platform is built with the Keiyo Line
        # the platform's long axis and the side facing the beam
        best = max(((a, b) for a, b in zip(r, r[1:] + r[:1])), key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
        ux, uy = best[1][0] - best[0][0], best[1][1] - best[0][1]; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
        nx, ny = -uy, ux
        us = [(p[0] - cx) * ux + (p[1] - cy) * uy for p in r]; vs = [(p[0] - cx) * nx + (p[1] - cy) * ny for p in r]
        u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
        q = min(loop, key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
        beam_side = 1 if (q[0] - cx) * nx + (q[1] - cy) * ny > 0 else -1
        M = Matrix(((ux, nx, 0, cx), (uy, ny, 0, cy), (0, 0, 1, 0), (0, 0, 0, 1)))

        def boxm(bm, a0, a1, b0, b1, z0, z1):
            for v in bm_box(bm, a0, a1, b0, b1, z0, z1):
                v.co = M @ v.co
        boxm(bm_s, u0, u1, v0, v1, zf - 0.5, zf)
        ve = v1 if beam_side > 0 else v0
        boxm(bm_y, u0 + 0.3, u1 - 0.3, min(ve, ve - beam_side * 0.5), max(ve - beam_side * 0.2, ve - beam_side * 0.5), zf, zf + 0.006)
        k = u0 + 0.4
        while k + 2.0 < u1:                                 # screen doors: 2 m panels with gaps
            boxm(bm_d, k, k + 1.9, min(ve - beam_side * 0.08, ve - beam_side * 0.25), max(ve - beam_side * 0.08, ve - beam_side * 0.25), zf, zf + 1.3)
            k += 2.3
        vb = v0 if beam_side > 0 else v1                    # canopy posts on the far side, roof over the platform and the track
        k = u0 + 2
        while k < u1 - 1:
            boxm(bm_k, k - 0.12, k + 0.12, vb - 0.12 * -beam_side - 0.12, vb - 0.12 * -beam_side + 0.12, zf, zf + 3.6)
            k += 8
        va, vz = min(vb, ve + beam_side * 3.0), max(vb, ve + beam_side * 3.0); vm = (va + vz) / 2
        for sgn, v_edge in ((-1, va), (1, vz)):             # gabled canopy over the platform and the train
            q = [(u0, vm, zf + 4.3), (u1, vm, zf + 4.3), (u1, v_edge, zf + 3.6), (u0, v_edge, zf + 3.6)]
            vs_ = [bm_c.verts.new(M @ Vector(c)) for c in q]
            bm_c.faces.new(vs_ if sgn > 0 else vs_[::-1])
        k = u0 + 3                                          # columns under the platform slab, down to the ground
        while k < u1 - 2:
            for vv in (v0 + 1.0, v1 - 1.0):
                gx, gy = cx + ux * k + nx * vv, cy + uy * k + ny * vv
                boxm(bm_k, k - 0.3, k + 0.3, vv - 0.3, vv + 0.3, h(gx, gy) - 0.3, zf - 0.5)
            k += 8
    obj_bm("TK_RLP_slab", bm_s, "concrete"); obj_bm("TK_RLP_edge", bm_y, "yellow"); obj_bm("TK_RLP_doors", bm_d, "white")
    c_ = obj_bm("TK_RLP_canopy", bm_c, "canopy", recalc=False)
    sd = c_.modifiers.new("Solidify", "SOLIDIFY"); sd.thickness = 0.12
    obj_bm("TK_RLP_posts", bm_k, "mast")


# ================================================================ the Keiyo Line
def nearest_on(line, p):
    best = (1e18, None)
    for a, b in zip(line[:-1], line[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        q = (a[0] + dx * t, a[1] + dy * t); d = math.hypot(p[0] - q[0], p[1] - q[1])
        if d < best[0]:
            best = (d, q)
    return best


def build_keiyo(D, h):
    S = SPEC; MH = D["maihama"]; zr = MH["jr_z"]; zd = zr - 0.55          # rail top; deck top (slab track + rail below it)
    A, Bl = [(p[0], p[1]) for p in MH["jr"][0]], [(p[0], p[1]) for p in MH["jr"][1]]
    if (A[-1][0] - A[0][0]) * (Bl[-1][0] - Bl[0][0]) + (A[-1][1] - A[0][1]) * (Bl[-1][1] - Bl[0][1]) < 0:
        Bl = Bl[::-1]
    tracks = [resample(A, 5.0 if WEB else 2.5, False)[0], resample(Bl, 5.0 if WEB else 2.5, False)[0]]
    # centre line and half width of the deck: the two tracks plus the edge width each side
    mid, half = [], []
    for p in tracks[0]:
        d, q = nearest_on(Bl, p)
        mid.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, p[2])); half.append(d / 2 + S["jr_deck_edge"])
    for _ in range(6):                                       # smooth the width where the tracks spread
        half = [half[0]] + [(half[i - 1] + 2 * half[i] + half[i + 1]) / 4 for i in range(1, len(half) - 1)] + [half[-1]]
    F = frames([(p[0], p[1]) for p in mid], False)
    # deck: a slab with a variable width (built ring by ring), parapets on its edges
    bm = bmesh.new(); rings = []
    for i, p in enumerate(mid):
        t, nrm, k = F[i]; w = half[i]
        prof = [(w, 0.0), (w, -1.0), (w - 0.6, -1.4), (-w + 0.6, -1.4), (-w, -1.0), (-w, 0.0)]
        rings.append([bm.verts.new((p[0] + nrm[0] * y, p[1] + nrm[1] * y, zd + z)) for y, z in prof])
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(6):
            bm.faces.new((a[j], a[(j + 1) % 6], b[(j + 1) % 6], b[j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    obj_bm("TK_JR_deck", bm, "viaduct")
    bm = bmesh.new()
    for side in (-1, 1):
        rings = []
        for i, p in enumerate(mid):
            t, nrm, k = F[i]; w = half[i] * side
            prof = [(w, 0.0), (w, S["parapet"]), (w - side * 0.25, S["parapet"]), (w - side * 0.25, 0.0)]
            rings.append([bm.verts.new((p[0] + nrm[0] * y, p[1] + nrm[1] * y, zd + z)) for y, z in prof])
        for a, b in zip(rings[:-1], rings[1:]):
            for j in range(4):
                bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    obj_bm("TK_JR_parapets", bm, "viaduct")
    bm, bmp = bmesh.new(), bmesh.new()
    for side in (-1, 1):
        rings = []
        for i, p in enumerate(mid):
            t, nrm, k = F[i]; w = side * (half[i] - 0.12)
            prof = [(w - 0.03, S["parapet"]), (w + 0.03, S["parapet"]), (w + 0.03, S["parapet"] + 1.4), (w - 0.03, S["parapet"] + 1.4)]
            rings.append([bm.verts.new((p[0] + nrm[0] * y, p[1] + nrm[1] * y, zd + z)) for y, z in prof])
        for a_, b_ in zip(rings[:-1], rings[1:]):
            for j in range(4):
                bm.faces.new((a_[j], a_[(j + 1) % 4], b_[(j + 1) % 4], b_[j]))
        for i in range(0, len(mid), 1):                      # H-posts every 2.5 m (5 m in the mock)
            p = mid[i]; t, nrm, k = F[i]; ang = math.atan2(t[1], t[0]); w = side * (half[i] - 0.12)
            for v in bm_box(bmp, -0.06, 0.06, w - 0.08, w + 0.08, S["parapet"] + zd, S["parapet"] + 1.5 + zd):
                v.co = Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(ang, 4, "Z") @ v.co
    obj_bm("TK_JR_barriers", bm, "barrier"); obj_bm("TK_JR_barrier_posts", bmp, "mast")
    bm = bmesh.new()                                         # cable troughs inside the parapets (the walkways)
    for side in (-1, 1):
        rings = []
        for i, p in enumerate(mid):
            t, nrm, k = F[i]; y0 = side * (half[i] - 0.3); y1 = side * (half[i] - 0.9)
            prof = [(y0, 0.0), (y0, 0.35), (y1, 0.35), (y1, 0.0)]
            rings.append([bm.verts.new((p[0] + nrm[0] * y, p[1] + nrm[1] * y, zd + z)) for y, z in prof])
        for a_, b_ in zip(rings[:-1], rings[1:]):
            for j in range(4):
                bm.faces.new((a_[j], a_[(j + 1) % 4], b_[(j + 1) % 4], b_[j]))
    obj_bm("TK_JR_troughs", bm, "concrete")
    bm = bmesh.new()                                         # waterproofed deck surface (dark), between the troughs
    rings = []
    for i, p in enumerate(mid):
        t, nrm, k = F[i]; w = half[i] - 0.9
        rings.append([bm.verts.new((p[0] + nrm[0] * y, p[1] + nrm[1] * y, zd + 0.01)) for y in (w, -w)])
    for a_, b_ in zip(rings[:-1], rings[1:]):
        bm.faces.new((a_[0], b_[0], b_[1], a_[1]))
    obj_bm("TK_JR_decksurface", bm, "deck_top", recalc=False)
    # bents: two columns and a cross beam every 10 m
    bm = bmesh.new()
    for i in range(0, len(mid), int(S["bent"] / (5.0 if WEB else 2.5))):
        p = mid[i]; t, nrm, k = F[i]; w = half[i] - 1.3; g = h(p[0], p[1])
        ang = math.atan2(t[1], t[0]); M = Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(ang, 4, "Z")
        for sy in (-1, 1):
            for v in bm_box(bm, -0.45, 0.45, sy * w - 0.45, sy * w + 0.45, g - 0.3, zd - 1.4):
                v.co = M @ v.co
        for v in bm_box(bm, -0.4, 0.4, -w - 0.45, w + 0.45, zd - 2.3, zd - 1.4):
            v.co = M @ v.co
    for i in (0, len(mid) - 1):                              # end walls (the data stops here: the viaduct goes on)
        p = mid[i]; t, nrm, k = F[i]; ang = math.atan2(t[1], t[0]); w = half[i]
        for v in bm_box(bm, -0.3, 0.3, -w, w, h(p[0], p[1]) - 0.3, zd):
            v.co = Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(ang, 4, "Z") @ v.co
    obj_bm("TK_JR_bents", bm, "pier")
    # slab track and rails for each track
    bm_sl, bm_rl, bm_fs = bmesh.new(), bmesh.new(), bmesh.new()
    g2 = S["jr_gauge"] / 2 + 0.036
    rail = [(-0.065, 0.0), (0.065, 0.0), (0.065, 0.012), (0.01, 0.03), (0.01, 0.125), (0.034, 0.13), (0.034, 0.16), (-0.034, 0.16),
            (-0.034, 0.13), (-0.01, 0.125), (-0.01, 0.03), (-0.065, 0.012)]
    for tr in tracks:
        pts = [(p[0], p[1], p[2]) for p in tr]
        sweep(bm_sl, pts, [(1.2, 0.0), (1.2, 0.2), (-1.2, 0.2), (-1.2, 0.0)], False, lambda i: zd)
        for sy in (-1, 1):
            sweep(bm_rl, pts, [(sy * g2 + y, z) for y, z in rail][::-1] if sy < 0 else [(sy * g2 + y, z) for y, z in rail], False, lambda i: zr - 0.16)
        Ft = frames([(p[0], p[1]) for p in tr], False)
        for i, p in enumerate(tr):                          # fastenings every 2.5 m (both rails)
            t, nrm, _ = Ft[i]; ang = math.atan2(t[1], t[0])
            for sy in (-1, 1):
                for v in bm_box(bm_fs, -0.12, 0.12, sy * g2 - 0.14, sy * g2 + 0.14, zd + 0.2, zr - 0.13):
                    v.co = Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(ang, 4, "Z") @ v.co
    obj_bm("TK_JR_slabtrack", bm_sl, "slab"); obj_bm("TK_JR_rails", bm_rl, "rail"); obj_bm("TK_JR_fastenings", bm_fs, "iron")
    # overhead line: masts both sides + a truss beam every 50 m, contact and messenger wires over each track
    bm_m, bm_w = bmesh.new(), bmesh.new()
    step = int(S["mast"] / (5.0 if WEB else 2.5))
    for i in range(0, len(mid), step):
        p = mid[i]; t, nrm, k = F[i]; w = half[i] - 0.5; ang = math.atan2(t[1], t[0])
        M = Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(ang, 4, "Z")
        top = zr + S["messenger"] + 0.9
        for sy in (-1, 1):
            for v in bm_box(bm_m, -0.15, 0.15, sy * w - 0.12, sy * w + 0.12, zd, top):
                v.co = M @ v.co
        for dz in (0.0, 0.55):                              # the truss: two chords and diagonals
            for v in bm_box(bm_m, -0.07, 0.07, -w, w, top - 0.1 - dz, top - dz):
                v.co = M @ v.co
        n = max(2, int(2 * w / 1.1))
        for j in range(n):
            y0 = -w + 2 * w * j / n; y1 = -w + 2 * w * (j + 1) / n
            a, b = Vector((0, y0, top - 0.6)), Vector((0, y1, top - 0.05))
            if j % 2:
                a, b = Vector((0, y0, top - 0.05)), Vector((0, y1, top - 0.6))
            d = b - a; L = d.length; mid_ = (a + b) / 2; rot = Matrix.Rotation(math.atan2(d.z, d.y), 4, "X")
            for v in bm_box(bm_m, -0.03, 0.03, -L / 2, L / 2, -0.03, 0.03):
                v.co = M @ (Matrix.Translation(mid_) @ rot @ v.co)
        for tr in tracks:                                   # droppers' hangers: a short post from the truss to each wire pair
            d, q = nearest_on([(pp[0], pp[1]) for pp in tr], (p[0], p[1]))
            yy = (q[0] - p[0]) * nrm[0] + (q[1] - p[1]) * nrm[1]
            for v in bm_box(bm_m, -0.04, 0.04, yy - 0.04, yy + 0.04, zr + S["contact"], top - 0.6):
                v.co = M @ v.co
    for tr in tracks:
        pts = [(p[0], p[1], p[2]) for p in tr]
        for zz, r in ((S["contact"], 0.012), (S["messenger"], 0.01)):
            prof = [(r * math.cos(2 * math.pi * k / 4), r * math.sin(2 * math.pi * k / 4)) for k in range(4)]
            sweep(bm_w, pts, prof, False, lambda i, zz=zz: zr + zz, mitre=False)
    for tr in tracks:
        for i in range(0, len(tr), 1 if WEB else 2):          # droppers every 5 m
            p = tr[i]
            for v in bm_box(bm_w, -0.006, 0.006, -0.006, 0.006, zr + S["contact"], zr + S["messenger"]):
                v.co += Vector((p[0], p[1], 0))
    obj_bm("TK_JR_masts", bm_m, "mast"); obj_bm("TK_JR_wires", bm_w, "copper_wire")
    # Maihama station: the island platform at rail top + 1.1 m, canopy on columns
    J = MH["station"]
    for r in MH["platforms"]:
        cx, cy = sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)
        if math.hypot(cx - J["x"], cy - J["y"]) >= 60:
            continue
        zp = zr + S["platform_jr"]
        bm = bmesh.new(); bm_prism(bm, [(p[0], p[1]) for p in r], zd, zp, "xy"); obj_bm("TK_JRP_platform", bm, "concrete")
        # the long axis of the platform: canopy strip down its middle, columns every 10 m
        e = max(zip(r, r[1:] + r[:1]), key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
        ux, uy = e[1][0] - e[0][0], e[1][1] - e[0][1]; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
        us = [(p[0] - cx) * ux + (p[1] - cy) * uy for p in r]
        bm_c, bm_k, bm_y = bmesh.new(), bmesh.new(), bmesh.new()
        M = Matrix(((ux, -uy, 0, cx), (uy, ux, 0, cy), (0, 0, 1, 0), (0, 0, 0, 1)))
        vv = [(p[0] - cx) * -uy + (p[1] - cy) * ux for p in r]; hwp = (max(vv) - min(vv)) / 2
        for sy in (-1, 1):                                  # gabled canopy: two slopes from the ridge over the centre
            q = [(min(us) + 8, 0.0, zp + 4.7), (max(us) - 8, 0.0, zp + 4.7), (max(us) - 8, sy * (hwp + 0.4), zp + 4.1), (min(us) + 8, sy * (hwp + 0.4), zp + 4.1)]
            vs = [bm_c.verts.new(M @ Vector(c)) for c in q]
            bm_c.faces.new(vs if sy > 0 else vs[::-1])
        for v in bm_box(bm_c, min(us) + 8, max(us) - 8, -0.2, 0.2, zp + 4.0, zp + 4.7):   # ridge beam
            v.co = M @ v.co
        k = min(us) + 10
        while k < max(us) - 8:
            for v in bm_box(bm_k, k - 0.15, k + 0.15, -0.15, 0.15, zp, zp + 4.2):
                v.co = M @ v.co
            k += 10
        for sy in (-1, 1):                                  # yellow tactile lines 0.8 m in from both edges
            for v in bm_box(bm_y, min(us) + 4, max(us) - 4, sy * (hwp - 0.8) - 0.15, sy * (hwp - 0.8) + 0.15, zp, zp + 0.008):
                v.co = M @ v.co
        c_ = obj_bm("TK_JRP_canopy", bm_c, "canopy", recalc=False)
        sd = c_.modifiers.new("Solidify", "SOLIDIFY"); sd.thickness = 0.12
        obj_bm("TK_JRP_columns", bm_k, "mast"); obj_bm("TK_JRP_lines", bm_y, "yellow")


# ================================================================ context and scene
def build_context(D, h, bbox):
    x0, y0, x1, y1 = bbox; step = 20.0
    ctx = bpy.data.collections.new("Context"); bpy.context.scene.collection.children.link(ctx)
    old = B.col; B.col = ctx
    bm = bmesh.new(); nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    V = [[bm.verts.new((x0 + i * step, y0 + j * step, h(x0 + i * step, y0 + j * step) - 0.05)) for i in range(nx)] for j in range(ny)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    obj_bm("CTX_terrain", bm, "ground_ctx", recalc=False)
    B.col = old


def station_skip():
    """Inside Tokyo Disneyland Station's own model (its beam runs 60 m each way from its centre)."""
    def skip(x, y):
        u, v = ST.to_local(x, y)
        return abs(u) < 47.0 and abs(v) < 16.0          # the station building (its ground floor holds the beam up)
    return skip


def build(context=True, train=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    B.col = bpy.data.collections.new("Tracks"); sc.collection.children.link(B.col)
    B.cutters = bpy.data.collections.new("Cutters"); sc.collection.children.link(B.cutters)
    B.root = bpy.data.objects.new("Tracks", None); B.col.objects.link(B.root); B.hide = []
    B.M = materials()
    D = data(); h = make_ground(D); skip = station_skip()
    t0 = time.time()
    pts = build_resort_line(D, h, skip)
    if RL_STATIONS:
        build_rl_platforms(D, h, skip)
    build_keiyo(D, h)
    if context:
        build_context(D, h, (-900.0, 40.0, 520.0, 1260.0))
    if train:
        try:                                               # a Resort Line train on the beam, for scale
            import train_blender as TB
            objs = TB.build("train", "yellow")
            i = min(range(len(pts)), key=lambda k: math.hypot(pts[k][0] + 770.0, pts[k][1] - 95.0))   # on the Bayside curve
            p = pts[i]; q = pts[(i + 5) % len(pts)]
            e = bpy.data.objects.new("TK_Train", None); B.col.objects.link(e)
            e.location = (p[0], p[1], D["maihama"]["loop_z"] + 0.9); e.rotation_euler = (0, 0, math.atan2(q[1] - p[1], q[0] - p[0]))
            for o in objs:
                o.parent = e
        except Exception as ex:
            print("[tracks] no train:", repr(ex))
    print(f"[tracks] built {len(B.col.objects)} objects in {time.time() - t0:.1f}s")
    return D


CAMS = {   # name -> (location, target, lens)
    "rl_curve": ((-760.0, 60.0, 14.0), (-790.0, 131.0, 4.0), 28),        # Bayside curve
    "rl_close": ((-690.0, 925.0, 5.0), (-708.0, 969.0, 3.5), 30),       # beam, pier, conductor rails
    "rl_bayside": ((-820.0, 170.0, 9.0), (-790.0, 131.0, 5.0), 24),     # Bayside platform
    "jr_station": ((-60.0, 1010.0, 16.0), (-123.0, 1052.0, 10.0), 24),  # Maihama platform
    "jr_close": ((-330.0, 1150.0, 13.0), (-300.0, 1140.0, 10.2), 20),   # rails, slab track, masts
    "jr_aerial": ((80.0, 820.0, 120.0), (-150.0, 1060.0, 5.0), 28),
    "overview": ((500.0, -250.0, 520.0), (-200.0, 600.0, 0.0), 26),
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", default=",".join(CAMS))
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--percent", type=int, default=50)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    build()
    ST.world_sky()
    cams = {}
    for n, (loc, tgt, lens) in CAMS.items():
        cam = bpy.data.cameras.new("CAM_" + n); cam.lens = lens; cam.clip_start = 0.1; cam.clip_end = 5000
        co = bpy.data.objects.new("CAM_" + n, cam); B.col.objects.link(co)
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cams[n] = co
    bpy.context.scene.camera = cams["overview"]
    bpy.ops.wm.save_as_mainfile(filepath=str((OUT / "tracks.blend").resolve()))
    which = [c for c in a.cams.split(",") if c and c != "none"]
    if which:
        old = ST.OUT; ST.OUT = OUT
        try:
            ST.render(cams, which, a.samples, a.percent, "WORKBENCH" if a.quick else "CYCLES", "tracks")
        finally:
            ST.OUT = old


def export_objects(merged):
    global WEB
    WEB = True
    build(context=False, train=False)
    groups = {}
    for o in B.col.objects:
        if o.type not in ("MESH", "CURVE") or o.hide_render:
            continue
        mats = [m for m in (o.data.materials if o.data else []) if m]
        if mats:
            groups.setdefault("TK_" + mats[0].name[3:], []).append((o, 0.0))
    out = bpy.data.collections.new("Export"); bpy.context.scene.collection.children.link(out)
    return [merged(k, parts, out) for k, parts in sorted(groups.items())]


if __name__ == "__main__" and bpy is not None:
    main()
