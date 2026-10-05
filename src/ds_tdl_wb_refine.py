"""World Bazaar, the re-refinement from the three new walk videos (docs/video_frames/refine_WB.md, stage B, 2026-10-05):
the "large" items 2 .. 4 -- the bridge over the end of Center Street's east arm, Penny Arcade's hall and the corridor
behind the shops (R2-34), Home Store's faces, its corner porch and the cobalt shop beside it. Item 1 (the east arm's
colonnade) is ds_tdl_world_bazaar.arcade_front; the salmon ceilings are ds_tdl_entrance's.

Stage B, large 5 .. 7 and the hand carts (same file, below): Grand Emporium's round porch and drum, the Magic Shop's and
Bibbidi's oval signs, the Sumitomo Mitsui bank and Club 33 past the east arm's end (positions by estimate), the covered
way out of the west arm's end (R2-15 / wb3 N1, by estimate), Town Center Fashions' island counter, two white hand carts.

Called from ds_tdl_world_bazaar (build_street, build_shops / shop / shop_interior, build_block_walls); nothing here imports
ds_tdl_world_bazaar (it can run as __main__), what it needs comes in as arguments.

Places (WEB / OSM, in the WB frame): the bridge spans the east arm (ARMS[1], OSM 72216847) just inside its end, between
the fronts ANE and ASE (the arm's end corners (57.6, -56.1) / (53.7, -69.4)); Penny Arcade is the OSM point (-17.0, -82.8)
(tourism=attraction) on MW2, the corridor runs behind MW2's shops inside the block 72216845 (x -20.6 .. -25.4,
y -72.5 .. -97.5; clear of the ASW / CSW shops' backs and of Pastry House); Home Store is the OSM point (46.5, -111.0) on
the north-east corner of the block 196943265, whose edges carry the faces (matched by their mid points).
Looks (outside only, the videos are not measured): wb1 oHk5xKug0rQ (daytime), wb2 B16AAdhT25E, wb3 uI7gJdVkXls (the
colours of wb3 are evening-warm: only its shapes are used). ESTIMATES: every size and height (the bridge's 5.2 m
clearance, the house on it, the arch's rise; the corridor's width 4.5 m, length 25 m and its fittings; the porch's radius).
"""
import math
import random

try:
    import bmesh
except ImportError:
    bmesh = None

from ds_tdl_station import bm_box, bm_lathe, bm_prism, obj_bm, T, R, globe_lamp_bm, text, _principled, arch_band, arch_opening, seg_arc, column_bm
from ds_tdl_entrance import frame, hexa


def materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    M["wb_navy"] = P("st_wbz_wb_navy", (0.014, 0.076, 0.19), 0.6)        # 1: the colonnade's frieze (#1F4E79)
    M["wb_bulk"] = P("st_wbz_wb_bulk", (0.024, 0.195, 0.39), 0.5)        # 1: its blue wainscot (#2B7AA8)
    M["wb_iron"] = P("st_wbz_wb_iron", (0.014, 0.068, 0.051), 0.45, Metallic=0.5)   # 2: the bridge's dark green iron (#1F4A40)
    M["wb_house"] = P("st_wbz_wb_house", (0.81, 0.58, 0.22), 0.75)       # 2: the butter yellow house on it (#E8C880)
    M["wb_frame"] = P("st_wbz_wb_frame", (0.25, 0.10, 0.04), 0.6)        # 2: its brown window frames (#8A5A3A)
    M["wb_soffit"] = P("st_wbz_wb_soffit", (0.81, 0.58, 0.43), 0.7)      # 2: the deck's peach underside (wb2 EC2, #E8C9B0)
    M["wb_slate"] = P("st_wbz_wb_slate", (0.14, 0.155, 0.17), 0.6)       # 3: Penny Arcade's grey mansard (#6A6E72)
    M["pa_floor"] = P("st_wbz_pa_floor", (0.38, 0.11, 0.03), 0.2)        # 3: the corridor (R2-34): honey parquet,
    M["pa_red"] = P("st_wbz_pa_red", (0.22, 0.01, 0.02), 0.5)            #    red panelling,
    M["pa_teal"] = P("st_wbz_pa_teal", (0.02, 0.13, 0.16), 0.6)          #    the teal coved ceiling,
    M["pa_wall"] = P("st_wbz_pa_wall", (0.75, 0.49, 0.22), 0.7)          #    gold walls
    M["hs_navy"] = P("st_wbz_hs_navy", (0.014, 0.042, 0.15), 0.45)       # 4: Home Store's navy board (wb1 X5, #1F3A6B)
    M["hs_plum"] = P("st_wbz_hs_plum", (0.14, 0.02, 0.05), 0.45)         # 4: and the maroon-purple one (wb2 HS1, #6A2A3E)
    M["hs_rose"] = P("st_wbz_hs_rose", (0.58, 0.35, 0.35), 0.7)          # 4 (user photos): the rose relief panels (#C9A0A0)
    M["hs_lblue"] = P("st_wbz_hs_lblue", (0.40, 0.55, 0.77), 0.6)        #    the blue "1890" shop's light blue trim (#A9C3E3)
    M["hs_bronze"] = P("st_wbz_hs_bronze", (0.155, 0.07, 0.045), 0.4, Metallic=0.3)   # its bronze half dome (#6E4A3C)
    # stage B, large 5 .. 7 and the hand carts (refine_WB.md)
    M["ge_aqua"] = P("st_wbz_ge_aqua", (0.46, 0.69, 0.69), 0.6)          # 6: Grand Emporium's drum band (wb3 G1, #B5D8D8)
    M["ge_red"] = P("st_wbz_ge_red", (0.55, 0.023, 0.084), 0.4)          # 6: its curved red sign (#C42A52)
    M["mg_teal"] = P("st_wbz_mg_teal", (0.028, 0.21, 0.19), 0.45)        # 7: the Magic Shop's oval board (wb1 A8, wb2 MG1, #2F7F78)
    M["mg_wall"] = P("st_wbz_mg_wall", (0.25, 0.027, 0.016), 0.7)        # 7: its maroon walls inside (wb2 MG2, #8A2E22)
    M["mg_purple"] = P("st_wbz_mg_purple", (0.069, 0.023, 0.144), 0.6)   # 7: its purple display stands (#4A2A6A)
    M["gate_soffit"] = P("st_wbz_gate_soffit", (0.83, 0.55, 0.38), 0.8)  # 6: the west end's covered way, its ceiling (wb3 N1, #EBC3A6)
    M["bench_blue"] = P("st_wbz_bench_blue", (0.39, 0.58, 0.73), 0.5)    # 6: and its pale blue benches (#A8C8DE)
    M["fs_pink"] = P("st_wbz_fs_pink", (0.89, 0.69, 0.63), 0.6)          # 6: Town Center Fashions inside (wb3 F2, #F2D8CF)
    M["fs_ceiling"] = P("st_wbz_fs_ceiling", (0.91, 0.79, 0.70), 0.7)
    M["fs_red"] = P("st_wbz_fs_red", (0.147, 0.014, 0.027), 0.9)         #    the maroon carpet (#6B1F2E)
    M["fs_navy"] = P("st_wbz_fs_navy", (0.012, 0.023, 0.091), 0.9)       #    the navy one (#1D2A55)
    M["cart_white"] = P("st_wbz_cart_white", (0.855, 0.83, 0.77), 0.7)   # wb3 C1: the hand carts' white covers (#EEEBE3)
    M["cart_wheel"] = P("st_wbz_cart_wheel", (0.69, 0.60, 0.25), 0.5)    #    and their pale yellow spoked wheels (#D8CC8A)
    # Eastside Cafe (user photos images/eastside_cafe/ec1..3 and the pale blue end-corner photos, 2026-10-05)
    M["es_grey"] = P("st_wbz_es_grey", (0.485, 0.597, 0.552), 0.8)       # the Center Street face: painted brick (#B9CBC4)
    M["es_blue"] = P("st_wbz_es_blue", (0.474, 0.546, 0.768), 0.7)       # the arm-end face: pale periwinkle (#B7C3E3)
    M["es_box"] = P("st_wbz_es_box", (0.27, 0.40, 0.62), 0.7)            # its planters' blue panels (#8FA9CF)
    _cf_materials(M)
    _rc_materials(M)
    _ge_materials(M)
    _hk_materials(M)
    return M


class Parts(dict):
    def __missing__(self, k):
        self[k] = bmesh.new()
        return self[k]

    def flush(self, name, smooth=("lamp",)):
        for k, bm_ in self.items():
            if len(bm_.verts):
                obj_bm(f"ST_WBZ_WB_{name}_{k}", bm_, k, smooth=k in smooth)
            else:
                bm_.free()


def bulb(bm, x, y, z, r):
    bm_lathe(bm, [(0, -r), (r, 0), (0, r)], 6, T(x, y, z))


# ================================================================ 2. the bridge over the east arm's end
BRIDGE = dict(t0=4.6, t1=0.6, girder=5.2, deck=5.95, spring=3.4, rise=1.5, house=3.5, eave=10.5, ridge=11.7)


def east_bridge(arm, fronts):
    """wb1 A9 (0:10:28 .. 0:10:34), wb2 EC2 (0:13:12 .. 0:13:16), R2-19: a bridge over the arm just inside its end -- a
    dark green iron segmental arch under each face with openwork rings in the spandrels and bulbs under the girder, a
    deck with a peach soffit, a cream arcaded parapet, and in the middle a two-storey butter yellow house with brown
    window frames, a bay window, a hipped roof and a small gable on each face. Local frame: x along the arm (0 = its end,
    -x back towards the crossing), y across (+y the ANE side). Clearance under the girder 5.2 m."""
    B_ = BRIDGE
    p0, p1, _ = arm
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L; nx, ny = -uy, ux
    cr = lambda a, b: a[0] * b[1] - a[1] * b[0]

    def off(seg, t):                                      # the signed offset of a front line across the arm at -t
        (ax, ay), (bx, by) = seg; cx, cy = p1[0] - ux * t, p1[1] - uy * t; e = (bx - ax, by - ay)
        return cr((ax - cx, ay - cy), e) / cr((nx, ny), e)
    tm = (B_["t0"] + B_["t1"]) / 2
    yN, yS = off(fronts["ANE"], tm), off(fronts["ASE"], tm)
    P = Parts()
    with frame("WBZ_bridge", p1[0], p1[1], math.degrees(math.atan2(uy, ux))):
        xa, xb = -B_["t0"], -B_["t1"]; zg, zd = B_["girder"], B_["deck"]
        bm_box(P["wb_soffit"], xa, xb, yS - 0.25, yN + 0.25, zg + 0.25, zd)          # the deck
        pts, (zc, Rr, _) = seg_arc(0.0, B_["spring"], yN - yS, B_["rise"], 9)
        cy_ = (yN + yS) / 2; Ro = Rr + 0.3
        for xc in (xa, xb):
            bm_box(P["wb_iron"], xc - 0.12, xc + 0.12, yS - 0.25, yN + 0.25, zg, zd)  # the girder, a cream cornice on it
            bm_box(P["t_cream"], xc - 0.18, xc + 0.18, yS - 0.25, yN + 0.25, zd, zd + 0.12)
            bm_prism(P["wb_iron"], arch_band(yS, yN, B_["spring"], B_["rise"], 0.3, 29), xc - 0.08, xc + 0.08, "yz")
            for y0 in (yS, yN):                           # the cast plates on the fronts at the springings
                bm_box(P["wb_iron"], xc - 0.16, xc + 0.16, y0 - 0.3, y0 + 0.3, B_["spring"] - 0.5, B_["spring"] + 0.5)
            y = yS + 0.9
            while y < yN - 0.8:                           # the spandrels: a ring where there is room, a post under the girder
                zo = zc + math.sqrt(max(Ro * Ro - (y - cy_) ** 2, 0.0)); gap = zg - zo
                if gap > 0.45:
                    r = min(0.34, gap / 2 - 0.05)
                    bm_lathe(P["wb_iron"], [(r - 0.05, -0.03), (r, -0.03), (r, 0.03), (r - 0.05, 0.03)], 12, T(xc, y, zo + gap / 2) @ R(math.pi / 2, "Y"))
                y2 = y + 0.55
                zo2 = zc + math.sqrt(max(Ro * Ro - (y2 - cy_) ** 2, 0.0))
                if zg - zo2 > 0.1 and y2 < yN - 0.5:
                    bm_box(P["wb_iron"], xc - 0.03, xc + 0.03, y2 - 0.02, y2 + 0.02, zo2 - 0.05, zg)
                y += 1.1
            y = yS + 0.4
            while y < yN - 0.3:                           # bulbs under the girder (wb1)
                bulb(P["lamp"], xc + (0.16 if xc > -2.0 else -0.16), y, zg - 0.07, 0.05); y += 0.6
            hh = B_["house"]                              # the cream arcaded parapet either side of the house
            for ya, yb in ((yS, -hh - 0.05), (hh + 0.05, yN)):
                bm_box(P["t_cream"], xc - 0.1, xc + 0.1, ya, yb, zd + 0.12, zd + 0.22)
                bm_box(P["t_cream"], xc - 0.12, xc + 0.12, ya, yb, zd + 1.0, zd + 1.1)
                n = max(1, round((yb - ya) / 1.0))
                for k in range(n + 1):
                    y = ya + (yb - ya) * k / n
                    bm_box(P["t_cream"], xc - 0.08, xc + 0.08, y - 0.08, y + 0.08, zd + 0.22, zd + 1.0)
                    if k < n:
                        y2 = ya + (yb - ya) * (k + 1) / n
                        bm_prism(P["t_cream"], arch_band(y + 0.08, y2 - 0.08, zd + 0.62, 0.3, 0.07, 9), xc - 0.05, xc + 0.05, "yz")
        # the house: x xa+0.2 .. xb-0.2, y -hh .. hh, two storeys on the deck
        hx0, hx1 = xa + 0.2, xb - 0.2; z0, ze = zd + 0.12, B_["eave"]; zm = (z0 + ze) / 2
        bm_box(P["wb_house"], hx0, hx1, -hh, hh, z0, ze)
        for xx in (hx0, hx1):                             # corner boards, string course, eaves cornice
            for yy in (-hh, hh):
                bm_box(P["t_cream"], xx - 0.08, xx + 0.08, yy - 0.08, yy + 0.08, z0, ze)
        bm_box(P["t_cream"], hx0 - 0.06, hx1 + 0.06, -hh - 0.06, hh + 0.06, zm - 0.06, zm + 0.06)
        bm_box(P["t_cream"], hx0 - 0.15, hx1 + 0.15, -hh - 0.15, hh + 0.15, ze - 0.15, ze)
        for sx, xx in ((-1, hx0), (1, hx1)):              # windows on both faces (brown frames), the bay upstairs
            for zz in (z0, zm):
                for yy in (-2.2, 0.0, 2.2):
                    if zz == zm and yy == 0.0:
                        bm_box(P["wb_frame"], min(xx, xx + sx * 0.5), max(xx, xx + sx * 0.5), -0.8, 0.8, zz + 0.35, zz + 1.95)
                        bm_box(P["win_dark"], min(xx + sx * 0.5, xx + sx * 0.52), max(xx + sx * 0.5, xx + sx * 0.52), -0.62, 0.62, zz + 0.5, zz + 1.75)
                        bm_box(P["shingle"], min(xx, xx + sx * 0.62), max(xx, xx + sx * 0.62), -0.9, 0.9, zz + 1.95, zz + 2.08)
                        continue
                    bm_box(P["wb_frame"], min(xx, xx + sx * 0.06), max(xx, xx + sx * 0.06), yy - 0.5, yy + 0.5, zz + 0.45, zz + 1.85)
                    bm_box(P["win_dark"], min(xx, xx + sx * 0.08), max(xx, xx + sx * 0.08), yy - 0.38, yy + 0.38, zz + 0.57, zz + 1.73)
                    bm_box(P["wb_frame"], min(xx, xx + sx * 0.1), max(xx, xx + sx * 0.1), yy - 0.02, yy + 0.02, zz + 0.57, zz + 1.73)
            for sy in (-1, 1):                            # (and one in each end wall)
                for zz in (z0, zm):
                    yy = sy * hh
                    bm_box(P["wb_frame"], (hx0 + hx1) / 2 - 0.45, (hx0 + hx1) / 2 + 0.45, min(yy, yy + sy * 0.06), max(yy, yy + sy * 0.06), zz + 0.45, zz + 1.85)
                    bm_box(P["win_dark"], (hx0 + hx1) / 2 - 0.33, (hx0 + hx1) / 2 + 0.33, min(yy, yy + sy * 0.08), max(yy, yy + sy * 0.08), zz + 0.57, zz + 1.73)
        # the hipped roof (0.3 m overhang), a gable over the bay on each face
        o = 0.3; X0, X1, Y0, Y1 = hx0 - o, hx1 + o, -hh - o, hh + o; xm_ = (X0 + X1) / 2; zr = B_["ridge"]
        rl = (Y1 - Y0) / 2 - (X1 - X0) / 2
        bm = P["shingle"]
        v = [bm.verts.new(p) for p in ((X0, Y0, ze), (X1, Y0, ze), (X1, Y1, ze), (X0, Y1, ze), (xm_, -rl, zr), (xm_, rl, zr))]
        for f in ((0, 1, 4), (2, 3, 5), (1, 2, 5, 4), (3, 0, 4, 5)):
            bm.faces.new([v[i] for i in f])
        for sx, xx in ((-1, X0), (1, X1)):
            bm_prism(P["wb_house"], [(-1.2, ze), (1.2, ze), (0.0, ze + 0.95)], min(xx, xx - sx * 1.0), max(xx, xx - sx * 1.0), "yz")
            for s in (-1, 1):                             # its little roof and the cream bargeboards
                q = [(xx, s * 1.35, ze - 0.05), (xx, 0.0, ze + 1.08), (xx - sx * 1.0, 0.0, ze + 1.08 - 0.0), (xx - sx * 1.0, s * 1.35, ze - 0.05)]
                vv = [bm.verts.new(p) for p in q]
                bm.faces.new(vv)
                bm_prism(P["t_cream"], [(s * 1.3, ze - 0.02), (0.0, ze + 0.98), (0.0, ze + 1.1), (s * 1.35, ze + 0.08)],
                         min(xx, xx + sx * 0.06), max(xx, xx + sx * 0.06), "yz")
        P.flush("bridge")                                 # (inside the frame: the meshes take its transform)


# ================================================================ 3. Penny Arcade's hall and the corridor behind the shops
CORR = dict(xa=8.1, xb=33.1, y0=-9.0, w=4.5, top=3.6)    # MW2's front frame: x along the street (WB -y), -y back (WB -x)


def chandelier3(P, x, y, ztop):
    """A brass three-tier light: a rod, a ring with 12 small bulbs (R2-34: about 1 m across)."""
    bm_box(P["brass"], x - 0.012, x + 0.012, y - 0.012, y + 0.012, ztop - 0.75, ztop)
    bm_lathe(P["brass"], [(0.42, 0), (0.48, 0), (0.48, 0.05), (0.42, 0.05)], 12, T(x, y, ztop - 0.85))
    bm_lathe(P["brass"], [(0, 0), (0.12, 0.05), (0.06, 0.2), (0, 0.22)], 8, T(x, y, ztop - 0.97))
    for q in range(12):
        a = 2 * math.pi * q / 12
        bulb(P["lamp"], x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), ztop - 0.75, 0.05)


def machine(P, x, y, face, kind):
    """A game / fortune machine against a wall (wb3 P2, R2-34): a dark wood cabinet 0.8 x 0.7 x 1.9 m, a glass window with
    a red curtain behind it (kind "fortune") or a white card on top (kind "press"); face = +1 / -1: the side it faces (y)."""
    w2 = 0.4 if kind == "fortune" else 0.3
    y0, y1 = sorted((y, y + face * 0.7))
    bm_box(P["in_wood"], x - w2, x + w2, y0, y1, 0.06, 1.96)
    yf = y + face * 0.7
    bm_box(P["pa_red"], x - w2 + 0.08, x + w2 - 0.08, min(yf - face * 0.06, yf - face * 0.04), max(yf - face * 0.06, yf - face * 0.04), 1.0, 1.7)
    bm_box(P["shopglass"], x - w2 + 0.06, x + w2 - 0.06, min(yf, yf + face * 0.02), max(yf, yf + face * 0.02), 0.95, 1.75)
    bm_box(P["brass"], x - w2 + 0.1, x + w2 - 0.1, min(yf, yf + face * 0.03), max(yf, yf + face * 0.03), 0.8, 0.88)
    if kind == "press":
        bm_box(P["t_white"], x - 0.28, x + 0.28, y0 + 0.2, y1 - 0.2, 1.96, 2.3)


def panelled_wall(P, xa, xb, y, face, top, gaps=()):
    """Red panelling to 2.0 m with a teal band and a wood cap, gold framed pictures above, along y facing face."""
    runs = [(xa, xb)]
    for g0, g1 in gaps:
        runs = [r for a, b in runs for r in ((a, min(b, g0)), (max(a, g1), b)) if r[1] - r[0] > 0.05]
    yy = lambda d: sorted((y, y + face * d))
    for a, b in runs:
        bm_box(P["pa_red"], a, b, *yy(0.03), 0.06, 2.0)
        bm_box(P["pa_teal"], a, b, *yy(0.04), 2.0, 2.15)
        bm_box(P["in_wood"], a, b, *yy(0.06), 2.15, 2.2)
        k = 0.3
        while k < b - a - 0.3:                            # the panels' mouldings
            bm_box(P["in_wood"], a + k, a + k + 0.04, *yy(0.05), 0.2, 1.85); k += 0.9
        x = a + 1.5
        while x < b - 0.9:                                # gold framed pictures every 3 m
            if top > 3.2:
                bm_box(P["brass"], x - 0.5, x + 0.5, *yy(0.05), top - 1.15, top - 0.55)
                bm_box(P["display"], x - 0.42, x + 0.42, *yy(0.06), top - 1.07, top - 0.63)
            x += 3.0


def penny_room(name, x0, x1, D, gf):
    """The shop's own hall (shop frame, x0 .. x1, from the front back to -D where the corridor's wall is): the corridor's
    finish -- parquet, red panelling, gold walls, the teal coved ceiling, bulbs, a chandelier -- and two machines on
    each side wall."""
    P = Parts(); top = gf - 0.45
    bm_box(P["pa_floor"], x0, x1, -D, -0.3, 0.0, 0.06)
    for xa_, xb_, f in ((x0, x0 + 0.15, 1), (x1 - 0.15, x1, -1)):
        bm_box(P["pa_wall"], xa_, xb_, -D, -0.3, 0.06, top)
        xi = xb_ if f > 0 else xa_
        with_x = lambda d, xi=xi, f=f: sorted((xi, xi + f * d))
        bm_box(P["pa_red"], *with_x(0.03), -D, -0.3, 0.06, 2.0)
        bm_box(P["pa_teal"], *with_x(0.04), -D, -0.3, 2.0, 2.15)
        bm_box(P["in_wood"], *with_x(0.06), -D, -0.3, 2.15, 2.2)
        bm_box(P["pa_teal"], *with_x(0.3), -D, -0.3, top - 0.3, top)               # the cove
        y = -0.8
        while y > -D + 0.3:
            bulb(P["lamp"], xi + f * 0.32, y, top - 0.32, 0.04); y -= 0.6
        for yy in (-3.0, -6.0):                           # machines along the wall, facing in
            m0, m1 = sorted((xi, xi + f * 0.7))
            bm_box(P["in_wood"], m0, m1, yy - 0.4, yy + 0.4, 0.06, 1.96)
            xf = xi + f * 0.7
            bm_box(P["pa_red"], *sorted((xf - f * 0.06, xf - f * 0.04)), yy - 0.32, yy + 0.32, 1.0, 1.7)
            bm_box(P["shopglass"], *sorted((xf, xf + f * 0.02)), yy - 0.34, yy + 0.34, 0.95, 1.75)
    bm_box(P["pa_teal"], x0, x1, -D, -0.3, top, top + 0.15)
    chandelier3(P, (x0 + x1) / 2, -D / 2, top)
    bm_box(P["pa_red"], x0 + 0.5, x1 - 0.5, -D + 0.3, -1.0, 0.06, 0.065)        # a red inlay in the parquet
    bm_box(P["pa_floor"], x0 + 0.62, x1 - 0.62, -D + 0.42, -1.12, 0.065, 0.07)
    P.flush(name + "_penny", smooth=())


def penny_corridor(name, door_x, sx0, sx1):
    """R2-34 / wb3 P2 (v2 1:15:16 .. 1:15:46, wb3 0:10:44 .. 0:11:26): the arcade corridor, 4.5 m wide and 25 m long,
    behind MW2's shops (MW2's front frame). Its east wall is the back of Penny Arcade's hall, open where the hall's door
    lines up; both ends are closed glazed doors under round fanlights. Parquet with a red inlay along the walls, red
    panelling to 2 m, gold walls with framed pictures, the teal coved ceiling with a row of bulbs, three chandeliers,
    machines along the walls."""
    C = CORR; xa, xb, ye, top = C["xa"], C["xb"], C["y0"], C["top"]; yw = ye - 0.15 - C["w"]
    P = Parts(); g0, g1 = door_x - 1.2, door_x + 1.2
    bm_box(P["pa_floor"], xa, xb, yw, ye, 0.0, 0.06)
    for y in (ye - 0.5, yw + 0.5):                        # the red inlay along both walls
        bm_box(P["pa_red"], xa + 0.3, xb - 0.3, y - 0.06, y + 0.06, 0.06, 0.066)
    for a, b in ((xa - 0.15, g0), (g1, xb + 0.15)):       # the east wall (Penny Arcade's back) with the opening
        bm_box(P["pa_wall"], a, b, ye - 0.15, ye, 0.0, top + 0.3)
    bm_box(P["pa_wall"], g0, g1, ye - 0.15, ye, 3.0, top + 0.3)
    bm_box(P["pa_red"], g0 - 0.1, g1 + 0.1, ye - 0.2, ye + 0.05, 2.9, 3.05)         # the opening's head
    bm_box(P["pa_wall"], xa - 0.15, xb + 0.15, yw - 0.15, yw, 0.0, top + 0.3)        # the west wall, the end walls
    for xx in (xa - 0.15, xb):
        bm_box(P["pa_wall"], xx, xx + 0.15, yw - 0.15, ye, 0.0, top + 0.3)
    bm_box(P["pa_teal"], xa, xb, yw, ye - 0.15, top, top + 0.15)                     # the ceiling and its cove
    for y0_, y1_ in ((ye - 0.45, ye - 0.15), (yw, yw + 0.3)):
        bm_box(P["pa_teal"], xa, xb, y0_, y1_, top - 0.3, top)
    for yb in (ye - 0.47, yw + 0.32):
        x = xa + 0.3
        while x < xb - 0.2:
            bulb(P["lamp"], x, yb, top - 0.32, 0.04); x += 0.6
    panelled_wall(P, xa, xb, ye - 0.15, -1, top, gaps=[(g0, g1)])
    panelled_wall(P, xa, xb, yw, 1, top)
    panelled_wall(P, sx0 + 0.15, sx1 - 0.15, ye, 1, top + 0.15, gaps=[(g0, g1)])     # (the hall's side of the same wall)
    for k in range(3):
        chandelier3(P, xa + (xb - xa) * (k + 0.5) / 3, (ye + yw) / 2, top)
    x = xa + 1.6; k = 0                                    # machines: fortune tellers and penny presses
    while x < xb - 1.0:
        machine(P, x, yw, 1, "press" if k % 3 == 2 else "fortune")
        if not (g0 - 0.6 < x + 2.2 < g1 + 0.6) and x + 2.2 < xb - 1.0:
            machine(P, x + 2.2, ye - 0.15, -1, "fortune" if k % 2 else "press")
        x += 4.5; k += 1
    yc = (ye - 0.15 + yw) / 2                             # the end doors under round fanlights (closed)
    for xx, s in ((xa, 1), (xb, -1)):
        xf = sorted((xx, xx + s * 0.06))
        bm_box(P["door"], *xf, yc - 0.8, yc + 0.8, 0.06, 2.6)
        bm_box(P["shopglass"], *sorted((xx + s * 0.06, xx + s * 0.08)), yc - 0.62, yc + 0.62, 1.1, 2.4)
        bm_prism(P["display"], arch_opening(yc - 0.8, yc + 0.8, 2.62, 2.62, 0.8, 12), *xf, "yz")
        bm_prism(P["t_cream"], arch_band(yc - 0.8, yc + 0.8, 2.62, 0.8, 0.14, 12, leg=2.6), *sorted((xx, xx + s * 0.1)), "yz")
    P.flush(name + "_corridor", smooth=())


# ================================================================ 4. Home Store and its neighbours (block 196943265)
# Rebuilt from the user's six photos (2026-10-05; seen in the conversation only): the corner from the plaza twice and
# close up, the blue "1890" shop beside it, the brick front with the cast-iron veranda and its ground floor with the
# benches. The faces, by the OSM edges' mid points (WB), from the Waffle Company round the corner to the Refreshment
# Corner: brick (R2-28, outer_run) -- hs_brick (the iron veranda, the "HOME STORE" oval, "FINEST WARES" / "QUALITY GOODS")
# -- sage (grey-green, "FROM MARCELINE TO YOU") -- Home Store's cream: hs (east), the chamfer (the porch on two columns,
# the corner bay, the oval sign, the dormer with the gold rose and the clock, the maroon-and-white dome, the flag), hs2
# (north) -- blue1890 -- the Refreshment Corner's brick side. Sizes from the photos with people (~1.65 m) and the
# OSM edge lengths for scale: ESTIMATES.
HS_EDGES = {"hs_brick": (54.3, -93.35), "brick_jog": (52.3, -97.9), "sage": (50.9, -100.45), "sage_jog": (50.65, -103.4),
            "hs": (49.95, -107.75), "hs2": (40.65, -112.8), "blue1890": (32.4, -111.45),
            "rc_side": (29.05, -111.95), "rc_side2": (27.5, -114.05)}
HS_CORNER = (47.4, -113.9)
HS_CHAMFER = ((48.7, -111.9), (45.5, -114.2))   # the corner's chamfer: OSM's rounded points 19 .. 21 are the bay and porch in front of it
HS_Z = dict(gf=3.25, belt=4.6, top=7.75, cor=8.1, cor1=8.55, par=9.25)
# the block's roof (ds_tdl_world_bazaar.GAZEBO_CUT, OSM order: clockwise): off the chamfer's bulge, and back 5.4 m behind the
# blue shop, which is lower than its neighbours (photo: sky over its cornice)
HS_ROOF_CUTS = [(lambda p: p[1] < -112.8 and 45.6 < p[0] < 49.0, []),
                (lambda p: -111.7 < p[1] < -111.2 and 28.8 < p[0] < 36.0, [(35.8, -111.4), (35.8, -106.0), (29.0, -106.0)])]


def home_store_kind(mid, L):
    """Which of the block's outer edges this is (by its mid point, WB): the faces above, then the R2-28 brick face south
    of them, and the chamfer's small OSM edges (built by home_store_corner)."""
    for k, p in HS_EDGES.items():
        if math.hypot(mid[0] - p[0], mid[1] - p[1]) < 1.0:
            return k
    if mid[0] > 45.0 and -98.5 < mid[1] < -77.0 and L > 4.0:
        return "brick"
    if L < 2.0 and math.hypot(mid[0] - HS_CORNER[0], mid[1] - HS_CORNER[1]) < 2.2:
        return "corner"
    return None


def oval_board(P, mat, rim, x, y, z, a, b):
    """An oval board a x b (half axes) facing +y at (x, y, z) with a rim."""
    bm_lathe(P[rim], [(0, 0), (1.0, 0), (1.0, 0.05), (0, 0.05)], 28, T(x, y, z) @ _diag(a + 0.08, b + 0.08) @ R(-math.pi / 2, "X"))
    bm_lathe(P[mat], [(0, 0), (1.0, 0), (1.0, 0.05), (0, 0.05)], 28, T(x, y + 0.04, z) @ _diag(a, b) @ R(-math.pi / 2, "X"))


def _diag(a, b):
    from mathutils import Matrix
    return Matrix.Diagonal((a, 1.0, b, 1.0))


def half_dome(bm, x, y, z, r, h, n=10, m=5):
    """A quarter sphere (scaled to height h) on the wall plane y, bulging +y: the canopy over a door."""
    rows = []
    for i in range(m + 1):
        phi = (math.pi / 2) * i / m
        row = [bm.verts.new((x + r * math.cos(phi) * math.cos(math.pi * j / n), y + r * math.cos(phi) * math.sin(math.pi * j / n),
                             z + h * math.sin(phi))) for j in range(n + 1)] if i < m else [bm.verts.new((x, y, z + h))]
        rows.append(row)
    for i in range(m):
        a, b = rows[i], rows[i + 1]
        for j in range(n):
            if len(b) == 1:
                bm.faces.new((a[j], a[j + 1], b[0]))
            else:
                bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    rim = [bm.verts.new((x + r * math.cos(math.pi * j / n), y + r * math.sin(math.pi * j / n), z)) for j in range(n + 1)]
    bm.faces.new(rim[::-1])                               # the flat underside


# ---- facets: a plan segment of a face frame (origin, unit direction); (u along, v out = left of u, z)
def _fmap(f):
    (ox, oy), (ux, uy) = f
    return lambda u, v, z: (ox + ux * u - uy * v, oy + uy * u + ux * v, z)


def fbox(bm, f, u0, u1, v0, v1, z0, z1):
    P_ = _fmap(f)
    hexa(bm, [P_(u0, v0, z0), P_(u1, v0, z0), P_(u1, v1, z0), P_(u0, v1, z0),
              P_(u0, v0, z1), P_(u1, v0, z1), P_(u1, v1, z1), P_(u0, v1, z1)])


def fprism(bm, f, pts, a0, a1, plane="uz"):
    """pts in (u, z) extruded along v (plane uz), or in (v, z) extruded along u (plane vz)."""
    P_ = _fmap(f)
    m = (lambda p, a: P_(p[0], a, p[1])) if plane == "uz" else (lambda p, a: P_(a, p[0], p[1]))
    v0 = [bm.verts.new(m(p, a0)) for p in pts]; v1 = [bm.verts.new(m(p, a1)) for p in pts]
    bm.faces.new(v0[::-1]); bm.faces.new(v1)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((v0[i], v0[j], v1[j], v1[i]))


def oriel_plan(xc, wf, d):
    """A three-sided bay on the wall y = 0 of a face frame: its plan (4 points, 45 degree sides) and its facets."""
    a, b = xc - wf / 2, xc + wf / 2
    pts = [(a - d, 0.0), (a, d), (b, d), (b + d, 0.0)]
    fs = []
    for p, q in zip(pts[:-1], pts[1:]):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        fs.append(((p, ((q[0] - p[0]) / L, (q[1] - p[1]) / L)), L))
    return pts, fs


def grow(pts, g):
    """A bay's plan pushed out by g (front and sides), kept on the wall line."""
    (x0, _), (x1, y1), (x2, _), (x3, _) = pts
    k = g * (1 + math.sqrt(2))
    return [(x0 - k, 0.0), (x1 - g * math.tan(math.pi / 8), y1 + g), (x2 + g * math.tan(math.pi / 8), y1 + g), (x3 + k, 0.0)]


def bonnet(P, f, L, z, d=0.5, h=0.42, mat="aw_maroon", edge="aw_white"):
    """A round-bellied maroon awning over a window of a facet (u 0 .. L), its lip at z, d out, with a white scalloped
    valance (photos: three over each bay)."""
    prof = [(d * math.sin(math.pi / 2 * k / 7), z + h * math.cos(math.pi / 2 * k / 7)) for k in range(8)] + [(0.0, z + h - 0.1)]
    fprism(P[mat], f, prof, 0.03, L - 0.03, "vz")
    n = max(2, round((L - 0.06) / 0.24)); s = (L - 0.06) / n
    for k in range(n):
        ua = 0.03 + k * s
        fprism(P[edge], f, [(ua + s, z + 0.03), (ua, z + 0.03)] + [(ua + s * j / 6, z - 0.08 * math.sin(math.pi * j / 6)) for j in range(7)],
               d - 0.02, d + 0.01, "uz")


def curtains(P, f, u0, u1, z0, z1, v, glass="win_dark", sheer=0.36):
    """A window on a facet: dark glass, two white drapes tied back and a valance (photos: every upper window)."""
    fbox(P[glass], f, u0, u1, v - 0.02, v, z0, z1)
    w = u1 - u0
    for a, b in ((u0, u0 + w * sheer), (u1 - w * sheer, u1)):
        fbox(P["t_white"], f, a, b, v, v + 0.025, z0 + 0.1, z1 - 0.05)
    fbox(P["t_white"], f, u0, u1, v, v + 0.035, z1 - 0.3, z1)


def oriel(P, xc, wf, d, z0, z1, trim="t_white", awn=True):
    """A bay window on the upper floor (face frame): a stepped corbel, the ribbed apron, a window on each facet between
    slim posts (curtains), a round maroon awning over each, the entablature merging with the frieze over it."""
    pts, fs = oriel_plan(xc, wf, d)
    za, zw0, zw1 = z0 + 0.7, z0 + 0.82, z1 - 0.38
    for g, z_a, z_b in ((-0.3, z0 - 0.45, z0 - 0.22), (-0.12, z0 - 0.22, z0)):     # the corbel
        q = grow(pts, g)
        bm_prism(P[trim], [(x, max(0.0, y)) for x, y in q], z_a, z_b, "xy")
    bm_prism(P[trim], pts, z0, za, "xy")                                              # the apron
    for f, L in fs:
        for z in (z0 + 0.12, z0 + 0.32, z0 + 0.52):
            fbox(P[trim], f, 0.04, L - 0.04, 0.0, 0.035, z, z + 0.06)
        fbox(P[trim], f, 0.08, L - 0.08, 0.0, 0.02, z0 + 0.08, za - 0.08)
    bm_prism(P[trim], grow(pts, 0.05), za, zw0, "xy")                                 # the sill
    for f, L in fs:
        curtains(P, f, 0.07, L - 0.07, zw0, zw1, -0.06)
        if L > 1.2:
            fbox(P[trim], f, L / 2 - 0.03, L / 2 + 0.03, -0.06, 0.0, zw0, zw1)
    for x, y in pts:                                                                   # the posts
        bm_box(P[trim], x - 0.07, x + 0.07, max(-0.05, y - 0.08), y + 0.02, zw0, zw1)
    bm_prism(P[trim], grow(pts, 0.02), zw1, z1 - 0.15, "xy")                           # the entablature
    bm_prism(P[trim], grow(pts, 0.1), z1 - 0.15, z1, "xy")
    if awn:
        for f, L in fs:
            bonnet(P, f, L, zw1 - 0.34, d=0.52, h=0.5)


def rose_panel(P, m, w, z0, z1, wall_y=0.0):
    """The rose relief panel in the belt between the floors (photos: one over each display window): a white moulded
    frame, the rose field, a raised oval cartouche with a scroll either side."""
    y = wall_y
    bm_box(P["t_white"], m - w / 2, m + w / 2, y, y + 0.04, z0, z1)
    bm_box(P["hs_rose"], m - w / 2 + 0.07, m + w / 2 - 0.07, y + 0.04, y + 0.06, z0 + 0.07, z1 - 0.07)
    zc = (z0 + z1) / 2
    bm_lathe(P["hs_rose"], [(0, 0), (1.0, 0), (0.85, 0.035), (0.5, 0.06), (0, 0.07)], 12, T(m, y + 0.06, zc) @ _diag(0.2, 0.15) @ R(-math.pi / 2, "X"))
    for sx in (-1, 1):
        bm_lathe(P["hs_rose"], [(0, 0), (1.0, 0), (0.6, 0.04), (0, 0.05)], 8, T(m + sx * 0.36, y + 0.06, zc) @ _diag(0.17, 0.06) @ R(-math.pi / 2, "X"))
        bm_lathe(P["t_white"], [(0, 0), (1.0, 0), (0, 0.03)], 6, T(m + sx * 0.56, y + 0.06, zc + 0.03) @ _diag(0.05, 0.05) @ R(-math.pi / 2, "X"))


def display_window(P, m, hw, z0, z1, rng=None):
    """A recessed ground-floor display window (0.27 m deep) with a white architrave, a transom bar, a lit display with
    shelves of goods behind the glass."""
    bm_box(P["display"], m - hw, m + hw, -0.3, -0.27, z0, z1)
    bm_box(P["shopglass"], m - hw, m + hw, -0.13, -0.12, z0, z1)
    bm_box(P["t_white"], m - hw, m + hw, -0.15, -0.09, z1 - 0.5, z1 - 0.44)
    for z in (z0 + 0.55, z0 + 1.35):
        bm_box(P["in_wood"], m - hw + 0.05, m + hw - 0.05, -0.27, -0.16, z - 0.03, z)
        for k in range(3):
            x = m - hw + 0.2 + (2 * hw - 0.4) * k / 2
            mat = ("brass", "flowers_pink", "aw_maroon", "t_cream")[(k + int(z * 10)) % 4]
            bm_box(P[mat], x - 0.09, x + 0.09, -0.25, -0.17, z, z + 0.16 + 0.06 * (k % 2))
    for x0, x1, za, zb in ((m - hw - 0.1, m - hw, z0 - 0.05, z1 + 0.1), (m + hw, m + hw + 0.1, z0 - 0.05, z1 + 0.1), (m - hw - 0.1, m + hw + 0.1, z1, z1 + 0.1)):
        bm_box(P["t_white"], x0, x1, 0.0, 0.05, za, zb)
    bm_box(P["t_white"], m - hw - 0.12, m + hw + 0.12, 0.0, 0.09, z0 - 0.1, z0)        # the sill


def hband(bm, L, e0, e1, y0, y1, z0, z1):
    """A horizontal member along the face projecting to y1, mitred round convex corners (e = tan of half the turn)."""
    bm_box(bm, -y1 * e0, L + y1 * e1, y0, y1, z0, z1)


def hs_face(name, L, e0=0.0, e1=0.0, bays=None, wf=1.3, porch=False):
    """Home Store's cream face (x 0 .. L, +y out; photos): ground-floor display windows recessed between white
    pilasters, the white cornice over them, the belt with a rose relief panel over each window, the upper floor's
    three-sided bays (white, curtained, a round maroon awning over each window) between panelled pilasters, the frieze,
    the cornice on modillions, the panelled parapet. porch: the chamfer's ground floor instead (home_store_corner)."""
    Z = HS_Z; P = Parts(); W, Tm = "w_hs_cream", "t_white"
    bays = bays if bays is not None else [L * 0.28, L * 0.72]
    if porch:
        hs_porch(P, L)
    else:
        nw = max(2, round(L / 1.75)); pitch = L / nw
        wins = [pitch * (k + 0.5) for k in range(nw)]
        hw = min(0.62, pitch / 2 - 0.3)
        xs = [0.0] + [v for m in wins for v in (m - hw, m + hw)] + [L]
        for a, b in zip(xs[0::2], xs[1::2]):                                         # the piers and their pilasters
            bm_box(P[W], a, b, -0.3, 0.0, 0.0, Z["gf"])
            c = (a + b) / 2; pw_ = max(0.1, min(0.2, (b - a) / 2 - 0.12))
            bm_box(P[Tm], c - pw_ - 0.04, c + pw_ + 0.04, 0.0, 0.1, 0.0, 0.45)
            bm_box(P[Tm], c - pw_, c + pw_, 0.0, 0.07, 0.45, Z["gf"] - 0.3)
            bm_box(P[W], c - pw_ + 0.06, c + pw_ - 0.06, 0.07, 0.08, 0.7, Z["gf"] - 0.55)   # its sunk panel's field
            bm_box(P[Tm], c - pw_ - 0.05, c + pw_ + 0.05, 0.0, 0.11, Z["gf"] - 0.3, Z["gf"] - 0.12)
        for m in wins:
            bm_box(P[W], m - hw, m + hw, -0.3, 0.0, 0.0, 0.55)                       # the bulkhead, panelled
            bm_box(P[Tm], m - hw + 0.08, m + hw - 0.08, 0.0, 0.03, 0.1, 0.42)
            bm_box(P[W], m - hw, m + hw, -0.3, 0.0, 3.05, Z["gf"])
            display_window(P, m, hw, 0.55, 3.05)
        for m in wins:
            rose_panel(P, m, 2 * hw + 0.1, Z["gf"] + 0.48, Z["belt"] - 0.3)
    hband(P[Tm], L, e0, e1, -0.3, 0.2, Z["gf"] - 0.12, Z["gf"] + 0.12)                 # the cornice over the ground floor
    hband(P[Tm], L, e0, e1, -0.3, 0.28, Z["gf"] + 0.12, Z["gf"] + 0.24)
    bm_box(P[W], 0.0, L, -0.3, 0.0, Z["gf"], Z["top"])                                 # the walls up to the frieze
    hband(P[Tm], L, e0, e1, -0.3, 0.06, Z["belt"] - 0.12, Z["belt"])                   # the sill course
    edges = sorted([(xc - wf / 2 - 0.58, xc + wf / 2 + 0.58) for xc in bays])
    gaps = [(0.0, edges[0][0])] + [(edges[i][1], edges[i + 1][0]) for i in range(len(edges) - 1)] + [(edges[-1][1], L)]
    for a, b in gaps:                                                                  # the upper pilasters, panelled
        for c in ([a + 0.22, b - 0.22] if b - a > 1.3 else [(a + b) / 2]) if b - a > 0.45 else []:
            bm_box(P[Tm], c - 0.18, c + 0.18, 0.0, 0.07, Z["belt"], Z["top"])
            for z0_ in (Z["belt"] + 0.3, Z["top"] - 0.85):
                bm_box(P[W], c - 0.1, c + 0.1, 0.07, 0.09, z0_, z0_ + 0.55)
                bm_box(P["hs_rose"], c - 0.06, c + 0.06, 0.09, 0.1, z0_ + 0.2, z0_ + 0.35)
    for xc in bays:
        oriel(P, xc, wf, 0.58 if not porch else 0.6, Z["belt"], Z["top"])
    # the frieze, the cornice on modillions, the parapet
    bm_box(P[W], 0.0, L, -0.3, 0.02, Z["top"], Z["cor"])
    hband(P[Tm], L, e0, e1, -0.3, 0.1, Z["top"], Z["top"] + 0.1)
    hband(P[Tm], L, e0, e1, -0.3, 0.16, Z["cor"], Z["cor"] + 0.1)
    hband(P[Tm], L, e0, e1, -0.3, 0.22, Z["cor"] + 0.1, Z["cor"] + 0.18)
    hband(P[Tm], L, e0, e1, -0.3, 0.55, Z["cor1"] - 0.17, Z["cor1"])
    n = max(2, round(L / 0.42))
    for k in range(n):
        x = L * (k + 0.5) / n
        bm_box(P[Tm], x - 0.05, x + 0.05, 0.0, 0.48, Z["cor"] + 0.18, Z["cor1"] - 0.17)
        bm_box(P[Tm], x - 0.04, x + 0.04, 0.0, 0.18, Z["cor"] + 0.02, Z["cor"] + 0.1)
    bm_box(P[W], 0.0, L, -0.3, 0.0, Z["cor1"], Z["par"])
    hband(P[Tm], L, e0, e1, -0.35, 0.08, Z["par"] - 0.1, Z["par"])
    hband(P[Tm], L, e0, e1, -0.3, 0.05, Z["cor1"], Z["cor1"] + 0.08)
    np_ = max(1, round(L / 1.6))
    for k in range(np_):
        a, b = L * k / np_ + 0.18, L * (k + 1) / np_ - 0.18
        bm_box(P[Tm], a, b, 0.0, 0.025, Z["cor1"] + 0.18, Z["par"] - 0.18)
        bm_box(P[W], a + 0.06, b - 0.06, 0.025, 0.035, Z["cor1"] + 0.24, Z["par"] - 0.24)
        bm_box(P[Tm], L * k / np_ - 0.1, L * k / np_ + 0.1, 0.0, 0.08, Z["cor1"], Z["par"] + 0.12)
    bm_box(P[Tm], L - 0.1, L + 0.0, 0.0, 0.08, Z["cor1"], Z["par"] + 0.12)
    P.flush(name + "_hs", smooth=("lamp",))


def hs_porch(P, L):
    """The chamfer's ground floor (photos): the entrance recessed 1.1 m behind two white columns on pedestals, a round
    arch between them with a lantern hanging in it, the soffit carrying the corner bay, glazed doors folded back into
    the dark shop, a flower pot either side."""
    W, Tm, D = "w_hs_cream", "t_white", 1.1; gf = HS_Z["gf"]; m = L / 2
    bm_box(P[W], m - 0.8, m + 0.8, -D - 0.3, -D, 2.75, gf)                            # the back wall: over the door,
    for x0, x1 in ((0.0, 0.32), (L - 0.32, L)):                                        # the returns,
        bm_box(P[W], x0, x1, -D - 0.3, 0.0, 0.0, gf)
    for x0, x1 in ((0.32, m - 0.8), (m + 0.8, L - 0.32)):                              # glazed sidelights beside the door
        bm_box(P[W], x0, x1, -D - 0.3, -D, 0.0, 0.42); bm_box(P[W], x0, x1, -D - 0.3, -D, 2.68, gf)
        bm_box(P["display"], x0, x1, -D - 0.32, -D - 0.3, 0.42, 2.68)
        for z0, z1 in ((0.36, 0.46), (2.62, 2.72)):
            bm_box(P[Tm], x0, x1, -D - 0.05, -D + 0.04, z0, z1)
        bm_box(P[Tm], (x0 + x1) / 2 - 0.03, (x0 + x1) / 2 + 0.03, -D - 0.05, -D + 0.02, 0.46, 2.62)
    bm_box(P["win_dark"], m - 0.8, m + 0.8, -D - 0.33, -D - 0.3, 0.0, 2.75)             # the dark shop inside the door
    bm_box(P[Tm], m - 0.85, m + 0.85, -D, -D + 0.06, 2.62, 2.75)
    for sx in (-1, 1):                                                                  # the glazed leaves folded back
        x = m + sx * 0.76
        bm_box(P["door"], x - 0.03, x + 0.03, -D - 0.25 + 0.05, -D + 0.45, 0.02, 2.55)
        bm_box(P["shopglass"], x - 0.035, x + 0.035, -D - 0.12, -D + 0.33, 0.9, 2.4)
    bm_box(P["t_cream"], 0.0, L, -D - 0.3, 0.75, -0.05, 0.05)                           # the floor and the step
    bm_box(P[Tm], 0.0, L, -D - 0.3, 0.65, gf - 0.1, gf)                                 # the soffit
    for x in (0.55, L - 0.55):                                                          # the columns
        bm_box(P[Tm], x - 0.27, x + 0.27, 0.3 - 0.27, 0.3 + 0.27, 0.05, 0.5)
        bm_box(P[Tm], x - 0.3, x + 0.3, 0.0, 0.6, 0.05, 0.12)
        column_bm(P[Tm], x, 0.3, 0.5, gf - 0.65, 0.17, 12)
        bm_box(P[Tm], x - 0.3, x + 0.3, 0.0, 0.6, gf - 0.18, gf - 0.1)
    x0, x1 = 0.75, L - 0.75                                                             # the arch, its spandrels
    bm_prism(P[Tm], arch_band(x0, x1, 2.55, 0.45, 0.12, 14), 0.24, 0.38, "xz")
    pts, _ = seg_arc((x0 + x1) / 2, 2.55, x1 - x0, 0.45, 14)
    bm_prism(P[W], [(x0 - 0.2, gf - 0.18), (x1 + 0.2, gf - 0.18), (x1 + 0.2, 2.55)] + pts + [(x0 - 0.2, 2.55)], 0.26, 0.36, "xz")
    bm_box(P["brass"], m - 0.012, m + 0.012, 0.29, 0.31, 2.6, 3.0)                       # the lantern
    bm_lathe(P["brass"], [(0, 0), (0.12, 0), (0.16, 0.06), (0.05, 0.12), (0, 0.12)], 8, T(m, 0.3, 2.62))
    globe_lamp_bm(P["lamp"], m, 0.3, 2.45, 0.15)
    for x in (0.0, L):                                                                  # flower pots by the columns
        xx = x + (0.35 if x == 0.0 else -0.35)
        bm_lathe(P["brick"], [(0, 0), (0.18, 0), (0.25, 0.42), (0.27, 0.46), (0, 0.46)], 10, T(xx, 0.95, 0.0))
        globe_lamp_bm(P["leaf"], xx, 0.95, 0.62, 0.26)
        for dx, dy in ((-0.1, 0.05), (0.1, 0.0), (0.0, 0.12)):
            globe_lamp_bm(P["flowers_pink"], xx + dx, 0.95 + dy, 0.8, 0.09)


def home_store_corner():
    """The chamfer between the east and north faces (WB frame in, its own frame for the face): Home Store's porch and
    corner bay (hs_face(porch=True)), the oval sign on the belt, and over the cornice the dormer (the gold rose
    window, an arched top with a round clock) in front of the dome -- a cream drum, maroon gores with white ribs and a
    white band, a lantern with gilt cresting, the flagpole and the flag (photos)."""
    (ax, ay), (bx, by) = HS_CHAMFER
    L = math.hypot(bx - ax, by - ay); Z = HS_Z; m = L / 2
    with frame("HS_corner", ax, ay, math.degrees(math.atan2(by - ay, bx - ax))):
        hs_face("hs_chamfer", L, 0.335, 0.499, [m], wf=1.6, porch=True)
        P = Parts()
        # the sign: a plum oval with a gilt rim and crest, blue ribbons either side, two bell lamps over it
        ys, zs = 0.66, 4.12
        oval_board(P, "hs_plum", "brass", m, ys, zs, 1.2, 0.46)
        for sx in (-1, 1):
            xa, xb = m + sx * 1.05, m + sx * 1.75
            bm_prism(P["w_cobalt"], [(xa, zs - 0.16), (xb, zs - 0.2), (xb - sx * 0.14, zs + 0.0), (xb, zs + 0.2), (xa, zs + 0.16)], ys + 0.0, ys + 0.04, "xz")
            bm_lathe(P["brass"], [(0, 0), (0.05, 0), (0.18, 0.2), (0.2, 0.26), (0, 0.3)], 10, T(m + sx * 0.75, ys + 0.1, zs + 0.5) @ R(math.pi, "X"))
            globe_lamp_bm(P["lamp"], m + sx * 0.75, ys + 0.1, zs + 0.18, 0.07)
        bm_lathe(P["brass"], [(0, 0), (1.0, 0), (1.0, 0.06), (0, 0.06)], 16, T(m, ys + 0.02, zs + 0.62) @ _diag(0.3, 0.22) @ R(-math.pi / 2, "X"))
        for dx in (-0.16, 0.0, 0.16):
            bm_box(P["brass"], m + dx - 0.035, m + dx + 0.035, ys, ys + 0.07, zs + 0.78, zs + 0.95 - abs(dx) * 0.5)
        P.flush("hs_sign", smooth=("lamp",))
        text("ST_WBZ_hs_sign_the", "The", 0.13, (m, ys + 0.1, zs + 0.27), (math.pi / 2, 0, math.pi), "t_cream", 0.01)
        text("ST_WBZ_hs_sign_name", "HOME STORE", 0.34, (m, ys + 0.1, zs + 0.0), (math.pi / 2, 0, math.pi), "t_cream", 0.02)
        text("ST_WBZ_hs_sign_from", "FROM MARCELINE TO YOU", 0.075, (m, ys + 0.1, zs - 0.27), (math.pi / 2, 0, math.pi), "t_cream", 0.008)
        # the dormer over the cornice
        P = Parts(); W, Tm = "w_hs_cream", "t_white"; zp = Z["par"]
        zk = zp + 1.45
        bm_box(P[W], m - 0.95, m + 0.95, -0.7, 0.0, Z["cor1"], zk)
        for sx in (-1, 1):
            bm_box(P[Tm], m + sx * 0.95 - 0.13, m + sx * 0.95 + 0.13, -0.7, 0.07, Z["cor1"], zk)
            bm_lathe(P[Tm], [(0, 0), (0.1, 0), (0.1, 0.1), (0.05, 0.25), (0, 0.3)], 8, T(m + sx * 0.95, -0.03, zk + 0.16))
        zr = zp + 0.72                                                                  # the gold rose: a ring, four lobes, a boss
        bm_lathe(P["win_dark"], [(0, 0), (0.55, 0), (0.55, 0.02), (0, 0.02)], 20, T(m, 0.0, zr) @ R(-math.pi / 2, "X"))
        for r_, x_, z_ in [(0.6, m, zr)] + [(0.26, m + 0.24 * math.cos(a), zr + 0.24 * math.sin(a)) for a in (0, math.pi / 2, math.pi, 1.5 * math.pi)] + [(0.13, m, zr)]:
            bm_lathe(P["brass"], [(r_ - 0.05, 0.0), (r_, 0.0), (r_, 0.06), (r_ - 0.05, 0.06), (r_ - 0.05, 0.0)], 20, T(x_, 0.0, z_) @ R(-math.pi / 2, "X"))
        bm_box(P[Tm], m - 1.1, m + 1.1, -0.7, 0.14, zk, zk + 0.16)
        za = zk + 0.16; ra = 0.62                                                       # the arched top on the dome, the clock in it
        bm_box(P[W], m - ra, m + ra, -0.9, 0.0, za, za + 0.3)
        bm_prism(P[W], [(x, za + 0.3 + y) for x, y in half_disc(ra, m, 14)], -0.9, 0.0, "xz")
        bm_prism(P[Tm], arch_band(m - ra, m + ra, za + 0.3, ra, 0.1, 14, leg=0.3), 0.0, 0.08, "xz")
        bm_lathe(P["brass"], [(0, 0), (0.3, 0), (0.3, 0.05), (0, 0.05)], 16, T(m, 0.0, za + 0.42) @ R(-math.pi / 2, "X"))
        bm_lathe(P["clock"], [(0, 0), (0.25, 0), (0.25, 0.08), (0, 0.08)], 16, T(m, 0.0, za + 0.42) @ R(-math.pi / 2, "X"))
        bm_lathe(P["brass"], [(0, 0), (0.07, 0), (0.03, 0.35), (0, 0.4)], 6, T(m, -0.2, za + 0.3 + ra + 0.05))
        # the dome
        cx, cy, zd = m, -2.15, zp + 0.95
        bm_lathe(P[W], [(0, Z["cor1"]), (2.15, Z["cor1"]), (2.15, zd), (0, zd)], 24, T(cx, cy, 0.0))               # the drum
        bm_lathe(P[Tm], [(2.05, zd - 0.15), (2.3, zd - 0.15), (2.3, zd), (2.05, zd), (2.05, zd - 0.15)], 24, T(cx, cy, 0.0))
        prof = [(2.18, 0.0), (2.16, 0.25), (2.09, 0.68), (1.94, 1.18), (1.64, 1.68), (1.2, 2.12), (0.71, 2.43), (0.36, 2.57)]
        bm_lathe(P["aw_maroon"], [(0, 0)] + prof + [(0, prof[-1][1])], 32, T(cx, cy, zd))
        nr = 16
        for k in range(nr):                                                            # the white ribs
            a = 2 * math.pi * k / nr; ca, sa = math.cos(a), math.sin(a)
            for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
                pts3 = []
                for (r, z) in ((r0, z0), (r1, z1)):
                    for dr in (0.0, 0.05):
                        for t in (-0.06, 0.06):
                            pts3.append((cx + (r + dr) * ca - t * sa, cy + (r + dr) * sa + t * ca, zd + z))
                # bottom loop (profile point 0): inner -t, inner +t, outer +t, outer -t; top loop the same at point 1
                b = [pts3[0], pts3[1], pts3[3], pts3[2]]; t_ = [pts3[4], pts3[5], pts3[7], pts3[6]]
                hexa(P[Tm], b + t_)
        bm_lathe(P[Tm], [(2.13, 0.55), (2.17, 0.55), (2.13, 0.75), (2.09, 0.75), (2.13, 0.55)], 32, T(cx, cy, zd))  # the white band
        zl = zd + prof[-1][1]                                                                 # the lantern, its gilt cresting
        bm_lathe(P[W], [(0, 0), (0.36, 0), (0.36, 0.42), (0, 0.42)], 12, T(cx, cy, zl))
        bm_lathe(P[Tm], [(0, 0), (0.44, 0), (0.44, 0.08), (0.2, 0.2), (0, 0.22)], 12, T(cx, cy, zl + 0.42))
        for k in range(12):
            a = 2 * math.pi * k / 12
            bm_lathe(P["brass"], [(0, 0), (0.025, 0), (0, 0.22)], 4, T(cx + 0.4 * math.cos(a), cy + 0.4 * math.sin(a), zl + 0.5))
        for k in range(4):
            a = math.pi / 4 + math.pi / 2 * k
            bm_box(P["win_dark"], cx + 0.33 * math.cos(a) - 0.06, cx + 0.33 * math.cos(a) + 0.06, cy + 0.33 * math.sin(a) - 0.06,
                   cy + 0.33 * math.sin(a) + 0.06, zl + 0.1, zl + 0.34)
        zf = zl + 0.64                                                                 # the flagpole and the flag
        bm_lathe(P[Tm], [(0, 0), (0.05, 0), (0.03, 3.0), (0, 3.0)], 8, T(cx, cy, zf))
        globe_lamp_bm(P["brass"], cx, cy, zf + 3.05, 0.07)
        fx0, fz1 = cx + 0.04, zf + 2.95
        for k in range(7):
            bm_box(P["aw_red" if k % 2 == 0 else Tm], fx0, fx0 + 1.3, cy - 0.015, cy + 0.015, fz1 - 0.1 * (k + 1), fz1 - 0.1 * k)
        bm_box(P["hs_navy"], fx0, fx0 + 0.55, cy - 0.02, cy + 0.02, fz1 - 0.4, fz1)
        P.flush("hs_dome", smooth=("lamp", "aw_maroon"))


def blue_1890(name, L):
    """The blue shop between Home Store and the Refreshment Corner (photo; x 0 .. L, +y out): blue piers with light blue
    sunk panels; on the ground floor two curtained bay windows either side of the door under a bronze half dome with a
    lantern and the plum "HOME STORE" oval over it; a cornice, a band of light blue balusters with two bell lamps; six
    round-headed curtained windows between slim colonnettes; over them two half sunbursts and four small arches; the
    cornice on brackets; the segmental crown with the "1890" plaque, an urn on a pedestal at each end. Lower than its
    neighbours: its own roof, with walls up to theirs."""
    P = Parts(); Bm, Lb = "w_cobalt", "hs_lblue"; pw = 0.45; m = L / 2
    zg, zb, zw, zs, zh, zc, zt = 3.2, 3.55, 4.3, 5.5, 6.0, 7.05, 7.4
    for x0 in (0.0, L - pw):                                                           # the piers
        bm_box(P[Bm], x0, x0 + pw, -0.3, 0.12, 0.0, zt)
        for z0, z1 in ((0.45, zg - 0.2), (zb + 0.1, zw - 0.1), (zw + 0.15, zh - 0.1), (zh + 0.25, zc - 0.1)):
            bm_box(P[Lb], x0 + 0.08, x0 + pw - 0.08, 0.12, 0.15, z0, z1)
            bm_box(P[Bm], x0 + 0.13, x0 + pw - 0.13, 0.15, 0.165, z0 + 0.05, z1 - 0.05)
    # ground floor: the wall round the door, the door, the two bays
    for x0, x1 in ((pw, m - 0.55), (m + 0.55, L - pw)):
        bm_box(P[Bm], x0, x1, -0.3, 0.0, 0.0, zg)
    bm_box(P[Bm], m - 0.55, m + 0.55, -0.3, 0.0, 2.6, zg)
    bm_box(P[Lb], m - 0.62, m + 0.62, 0.0, 0.07, 2.55, 2.68)
    for sx in (-1, 1):
        bm_box(P[Lb], m + sx * 0.585 - 0.06, m + sx * 0.585 + 0.06, 0.0, 0.07, 0.0, 2.6)
    bm_box(P["in_floor"], m - 0.55, m + 0.55, -1.6, 0.3, -0.05, 0.05)                   # the shop seen through the door
    bm_box(P["display"], m - 0.6, m + 0.6, -1.65, -1.6, 0.05, 2.6)
    for sx in (-1, 1):
        bm_box(P["in_wall"], m + sx * 0.55 - 0.03, m + sx * 0.55 + 0.03, -1.6, -0.3, 0.05, 2.6)
    bm_box(P["door"], m - 0.55, m - 0.5, -0.3, 0.35, 0.05, 2.5)                          # one leaf open
    half_dome(P["hs_bronze"], m, 0.0, 2.68, 0.78, 0.5, 12, 6)                           # the half dome, ribbed, its lantern
    for k in range(1, 6):
        a = math.pi * k / 6
        bm_box(P["brass"], m + 0.79 * math.cos(a) - 0.02, m + 0.79 * math.cos(a) + 0.02, 0.79 * math.sin(a) - 0.02, 0.79 * math.sin(a) + 0.02, 2.62, 2.7)
    bm_lathe(P["brass"], [(0, 0), (0.06, 0), (0.02, 0.25), (0, 0.3)], 6, T(m, 0.05, 3.15))
    bm_box(P["brass"], m - 0.01, m + 0.01, 0.3, 0.32, 2.3, 2.68)
    globe_lamp_bm(P["lamp"], m, 0.31, 2.2, 0.12)
    for c in (pw + 1.15, L - pw - 1.15):                                                 # the bays
        pts, fs = oriel_plan(c, 1.3, 0.5)
        bm_prism(P[Bm], pts, 0.0, 0.72, "xy")
        for f, Lf in fs:
            fbox(P[Lb], f, 0.06, Lf - 0.06, 0.0, 0.03, 0.15, 0.6)
            fbox(P[Bm], f, 0.11, Lf - 0.11, 0.03, 0.04, 0.2, 0.55)
            fbox(P["display"], f, 0.06, Lf - 0.06, -0.08, -0.06, 0.78, 2.5)
            fbox(P["shopglass"], f, 0.06, Lf - 0.06, -0.02, 0.0, 0.78, 2.5)
            fbox(P["t_white"], f, 0.06, Lf - 0.06, -0.06, -0.02, 2.22, 2.5)              # the curtain valance
            for u in (0.06, Lf - 0.24):
                fbox(P["t_white"], f, u, u + 0.18, -0.06, -0.03, 1.2, 2.45)
        bm_prism(P[Lb], grow(pts, 0.03), 0.72, 0.8, "xy")
        for x, y in pts:
            bm_box(P[Lb], x - 0.06, x + 0.06, max(-0.05, y - 0.07), y + 0.03, 0.78, 2.5)
        bm_prism(P[Bm], grow(pts, 0.02), 2.5, 2.88, "xy")
        bm_prism(P[Lb], grow(pts, 0.1), 2.88, 3.0, "xy")
        for f, Lf in fs[1:2]:
            for u in (Lf * 0.25, Lf * 0.75):                                            # the rings on the bay's frieze
                Pm = _fmap(f)(u, 0.03, 2.69)
                bm_lathe(P[Lb], [(0.07, 0), (0.11, 0), (0.11, 0.03), (0.07, 0.03), (0.07, 0)], 12, T(*Pm) @ R(-math.pi / 2, "X"))
    # the cornice over the ground floor, the band of balusters, the bell lamps
    bm_box(P[Lb], pw - 0.05, L - pw + 0.05, 0.0, 0.3, zg, zg + 0.12)
    bm_box(P[Bm], pw, L - pw, -0.3, 0.0, zg, zw)
    bm_box(P[Lb], pw - 0.05, L - pw + 0.05, -0.3, 0.38, zb - 0.12, zb)
    for k in range(int((L - 2 * pw) / 0.16)):
        x = pw + 0.08 + k * 0.16
        bm_box(P[Lb], x - 0.025, x + 0.025, 0.0, 0.05, zg + 0.14, zb - 0.14)
    bm_box(P[Lb], pw, L - pw, 0.0, 0.08, zb + 0.06, zb + 0.13)
    for k in range(int((L - 2 * pw - 0.2) / 0.22)):
        x = pw + 0.2 + k * 0.22
        bm_lathe(P[Lb], [(0, 0), (0.04, 0), (0.025, 0.15), (0.045, 0.4), (0.025, 0.55), (0.04, 0.6), (0, 0.6)], 6, T(x, 0.06, zb + 0.13))
    bm_box(P[Lb], pw, L - pw, -0.3, 0.14, zw - 0.1, zw)
    for sx in (-1, 1):
        x = m + sx * 1.6
        bm_box(P["iron"], x - 0.015, x + 0.015, 0.0, 0.42, zb + 0.15, zb + 0.18)
        bm_box(P["iron"], x - 0.01, x + 0.01, 0.4, 0.42, zb - 0.15, zb + 0.18)
        bm_lathe(P["brass"], [(0, 0), (0.04, 0), (0.17, 0.2), (0.19, 0.26), (0, 0.28)], 10, T(x, 0.41, zb - 0.1) @ R(math.pi, "X"))
        globe_lamp_bm(P["lamp"], x, 0.41, zb - 0.38, 0.06)
    # the sign over the door
    oval_board(P, "hs_plum", "brass", m, 0.42, zg + 0.22, 0.82, 0.3)
    bm_lathe(P["brass"], [(0, 0), (1.0, 0), (1.0, 0.05), (0, 0.05)], 14, T(m, 0.44, zg + 0.62) @ _diag(0.18, 0.14) @ R(-math.pi / 2, "X"))
    # the upper floor: six round-headed windows, colonnettes
    n = 6; pitch = (L - 2 * pw - 0.5) / n; ww = 0.62; x0w = pw + 0.25
    xs = [x0w + pitch * (k + 0.5) for k in range(n)]
    cuts = [x0w] + [v for c in xs for v in (c - ww / 2, c + ww / 2)] + [L - pw - 0.25]
    bm_box(P[Bm], pw, x0w, -0.3, 0.0, zw, zh); bm_box(P[Bm], L - pw - 0.25, L - pw, -0.3, 0.0, zw, zh)
    for a, b in zip(cuts[0::2], cuts[1::2]):
        bm_box(P[Bm], a, b, -0.3, 0.0, zw, zs)
    for c in xs:
        a, b = c - ww / 2, c + ww / 2
        bm_box(P[Bm], a, b, -0.3, 0.0, zw, zw + 0.15)
        pts, _ = seg_arc(c, zs, ww, ww / 2, 10)
        bm_prism(P[Bm], [(a - 0.001, zh), (b + 0.001, zh), (b, zs)] + pts + [(a, zs)], -0.3, 0.0, "xz")
        bm_prism(P["win_dark"], arch_opening(a, b, zw + 0.15, zs, ww / 2, 10), -0.18, -0.16, "xz")
        bm_prism(P["t_white"], arch_opening(a + 0.05, b - 0.05, zw + 0.25, zs, ww / 2 - 0.05, 10), -0.16, -0.13, "xz")   # the curtains
        bm_box(P["win_dark"], c - 0.07, c + 0.07, -0.135, -0.125, zw + 0.25, zs - 0.15)
        bm_prism(P["t_cream"], arch_band(a, b, zs, ww / 2, 0.06, 10, leg=zs - zw - 0.15), 0.0, 0.04, "xz")
        bm_box(P[Lb], a - 0.06, b + 0.06, 0.0, 0.1, zw + 0.05, zw + 0.15)
    for c in [(xs[k] + xs[k + 1]) / 2 for k in range(n - 1)]:
        column_bm(P[Lb], c, 0.08, zw + 0.15, zs - zw - 0.15, 0.055, 8)
    bm_box(P[Lb], pw, L - pw, 0.0, 0.12, zh - 0.02, zh + 0.22)                           # the entablature
    # the lunettes: two half sunbursts and four small arches
    bm_box(P[Bm], pw, L - pw, -0.3, 0.0, zh, zc)
    for cx_ in (pw + 0.95, L - pw - 0.95):
        bm_prism(P[Lb], [(cx_ + x, zh + 0.22 + z) for x, z in ring_sector2(0.6, 0.72, 15)], 0.0, 0.06, "xz")
        bm_prism(P[Lb], [(cx_ + x, zh + 0.22 + z) for x, z in half_disc(0.16, 0.0, 8)], 0.0, 0.06, "xz")
        for k in range(1, 9):
            a = math.pi * k / 9; ca, sa = math.cos(a), math.sin(a)
            bm_prism(P[Lb], [(cx_ + 0.16 * ca - 0.018 * sa, zh + 0.22 + 0.16 * sa + 0.018 * ca), (cx_ + 0.16 * ca + 0.018 * sa, zh + 0.22 + 0.16 * sa - 0.018 * ca),
                             (cx_ + 0.6 * ca + 0.03 * sa, zh + 0.22 + 0.6 * sa - 0.03 * ca), (cx_ + 0.6 * ca - 0.03 * sa, zh + 0.22 + 0.6 * sa + 0.03 * ca)], 0.0, 0.045, "xz")
    a0, a1 = pw + 2.0, L - pw - 2.0
    for k in range(4):
        xa, xb = a0 + (a1 - a0) * k / 4 + 0.05, a0 + (a1 - a0) * (k + 1) / 4 - 0.05
        bm_prism(P[Lb], arch_band(xa, xb, zh + 0.5, (xb - xa) / 2, 0.05, 8, leg=0.25), 0.0, 0.05, "xz")
    # the cornice, the crown with "1890", the urns
    bm_box(P[Lb], -0.05, L + 0.05, -0.3, 0.2, zc, zc + 0.12)
    for k in range(int(L / 0.45)):
        x = 0.25 + k * 0.45
        bm_box(P[Bm], x - 0.05, x + 0.05, 0.0, 0.32, zc + 0.12, zt - 0.12)
    bm_box(P[Lb], -0.1, L + 0.1, -0.3, 0.4, zt - 0.12, zt)
    bm_prism(P[Bm], arch_opening(m - 1.4, m + 1.4, zt, zt + 0.15, 0.75, 14), -0.3, 0.05, "xz")
    bm_prism(P[Lb], arch_band(m - 1.4, m + 1.4, zt + 0.15, 0.75, 0.12, 14), -0.3, 0.12, "xz")
    oval_board(P, Bm, "t_white", m, 0.05, zt + 0.45, 0.42, 0.2)
    bm_lathe(P["brass"], [(0, 0), (0.08, 0), (0.05, 0.12), (0.1, 0.2), (0, 0.45)], 8, T(m, -0.1, zt + 0.98))
    for x0 in (0.0, L - pw):
        bm_box(P[Bm], x0, x0 + pw, -0.3, 0.15, zt, zt + 0.45)
        bm_box(P[Lb], x0 - 0.03, x0 + pw + 0.03, -0.33, 0.18, zt + 0.45, zt + 0.53)
        bm_lathe(P[Bm], [(0, 0), (0.1, 0), (0.06, 0.08), (0.17, 0.25), (0.06, 0.42), (0.04, 0.5), (0, 0.7)], 10, T(x0 + pw / 2, -0.07, zt + 0.53))
    # its own roof; walls up to the neighbours' roof behind and beside it
    bm_box(P["shingle"], 0.0, L, -5.4, -0.3, zt - 0.2, zt - 0.1)
    bm_box(P["w_hs_cream"], 0.0, L, -5.5, -5.4, zt - 0.2, 8.5)
    bm_box(P["w_hs_cream"], 0.0, 0.3, -5.5, -0.3, zt - 0.2, HS_Z["par"])
    bm_box(P["brick"], L - 0.3, L, -5.5, -0.3, zt - 0.2, 9.2)
    P.flush(name + "_1890", smooth=("lamp", "hs_bronze"))
    text(f"ST_WBZ_{name}_1890", "1890", 0.22, (m, 0.16, zt + 0.45), (math.pi / 2, 0, math.pi), "t_white", 0.01)
    text(f"ST_WBZ_{name}_hs1890", "HOME STORE", 0.17, (m, 0.53, zg + 0.22), (math.pi / 2, 0, math.pi), "t_cream", 0.01)


def ring_sector2(r0, r1, n):
    """An upper half ring (x, z) round the origin."""
    out = [(r1 * math.cos(math.pi * k / n), r1 * math.sin(math.pi * k / n)) for k in range(n + 1)]
    inn = [(r0 * math.cos(math.pi * k / n), r0 * math.sin(math.pi * k / n)) for k in range(n + 1)]
    return out + inn[::-1]


def sage_front(name, L, H):
    """The grey-green front between the brick one and Home Store (photos: "FROM MARCELINE TO YOU" on its fascia; x 0 ..
    L, +y out): a glazed white door and a display window with round heads, the fascia with navy letters between white
    mouldings, two tall round-headed upper windows in cream architraves with keystones and curtains, the cornice on
    brackets, the parapet."""
    P = Parts(); W, Tm = "w_bluegrey", "t_white"
    dx, wx = L * 0.3, L * 0.7
    ops = sorted([(dx - 0.6, dx + 0.6, 2.5, 0.6), (wx - 0.8, wx + 0.8, 2.4, 0.5)])
    cuts = [0.0] + [v for a, b, _, _ in ops for v in (a, b)] + [L]
    for a, b in zip(cuts[0::2], cuts[1::2]):
        bm_box(P[W], a, b, -0.3, 0.0, 0.0, 3.35)
    for a, b, zs, r in ops:
        pts, _ = seg_arc((a + b) / 2, zs, b - a, r, 12)
        bm_prism(P[W], [(a, 3.35), (b, 3.35), (b, zs)] + pts + [(a, zs)], -0.3, 0.0, "xz")
        bm_prism(P[Tm], arch_band(a, b, zs, r, 0.1, 12, leg=zs), 0.0, 0.06, "xz")
        bm_lathe(P[Tm], [(0, 0), (1, 0), (1, 0.08), (0, 0.08)], 4, T((a + b) / 2, 0.0, zs + r + 0.05) @ _diag(0.1, 0.14) @ R(-math.pi / 2, "X"))
    a, b, zs, r = next(o for o in ops if abs((o[0] + o[1]) / 2 - dx) < 0.01)            # the door: glazed white leaves, fanlight
    bm_prism(P["display"], arch_opening(a, b, 0.0, zs, r, 12), -0.32, -0.3, "xz")
    for x0, x1 in ((a + 0.04, (a + b) / 2 - 0.01), ((a + b) / 2 + 0.01, b - 0.04)):
        bm_box(P[Tm], x0, x1, -0.2, -0.15, 0.02, zs - 0.08)
        bm_box(P["shopglass"], x0 + 0.08, x1 - 0.08, -0.15, -0.14, 0.9, zs - 0.2)
        bm_box(P["in_wall"], x0 + 0.08, x1 - 0.08, -0.2, -0.19, 0.9, zs - 0.2)
    bm_box(P["t_cream"], a, b, -0.3, 0.3, -0.05, 0.05)
    a, b, zs, r = next(o for o in ops if abs((o[0] + o[1]) / 2 - wx) < 0.01)            # the window
    bm_box(P[W], a, b, -0.3, 0.0, 0.0, 0.6)
    bm_box(P[Tm], a - 0.05, b + 0.05, 0.0, 0.1, 0.52, 0.62)
    bm_prism(P["display"], arch_opening(a, b, 0.6, zs, r, 12), -0.3, -0.28, "xz")
    bm_prism(P["shopglass"], arch_opening(a, b, 0.6, zs, r, 12), -0.14, -0.13, "xz")
    bm_box(P[Tm], (a + b) / 2 - 0.03, (a + b) / 2 + 0.03, -0.15, -0.1, 0.6, zs)
    bm_box(P[Tm], a, b, -0.15, -0.1, zs - 0.05, zs)
    # the fascia and its letters
    bm_box(P[Tm], -0.02, L + 0.02, -0.3, 0.16, 3.35, 3.45)
    bm_box(P[W], 0.0, L, -0.3, 0.06, 3.45, 3.95)
    bm_box(P[Tm], -0.02, L + 0.02, -0.3, 0.2, 3.95, 4.08)
    # the upper floor
    zu0, zus, zu1 = 4.6, 6.6, 7.05
    ups = [(L * 0.28 - 0.5, L * 0.28 + 0.5), (L * 0.72 - 0.5, L * 0.72 + 0.5)]
    cuts = [0.0] + [v for a, b in ups for v in (a, b)] + [L]
    bm_box(P[W], 0.0, L, -0.3, 0.0, 4.08, zu0)
    for a, b in zip(cuts[0::2], cuts[1::2]):
        bm_box(P[W], a, b, -0.3, 0.0, zu0, H - 0.45)
    for a, b in ups:
        c = (a + b) / 2
        pts, _ = seg_arc(c, zus, b - a, 0.45, 12)
        bm_prism(P[W], [(a, H - 0.45), (b, H - 0.45), (b, zus)] + pts + [(a, zus)], -0.3, 0.0, "xz")
        bm_prism(P["win_dark"], arch_opening(a, b, zu0, zus, 0.45, 12), -0.22, -0.2, "xz")
        bm_prism(P[Tm], arch_opening(a + 0.06, b - 0.06, zu0 + 0.1, zus, 0.4, 12), -0.2, -0.18, "xz")
        bm_box(P["win_dark"], c - 0.12, c + 0.12, -0.18, -0.17, zu0 + 0.2, zus - 0.1)
        bm_box(P["t_cream"], c - 0.02, c + 0.02, -0.17, -0.14, zu0 + 0.1, zus + 0.4)
        bm_prism(P["t_cream"], arch_band(a, b, zus, 0.45, 0.12, 12, leg=zus - zu0), 0.0, 0.07, "xz")
        bm_prism(P["t_cream"], [(c - 0.1, zus + 0.42), (c + 0.1, zus + 0.42), (c + 0.14, zus + 0.75), (c - 0.14, zus + 0.75)], 0.0, 0.12, "xz")
        bm_box(P["t_cream"], a - 0.12, b + 0.12, 0.0, 0.14, zu0 - 0.1, zu0)
        for sx in (-1, 1):
            bm_box(P["t_cream"], c + sx * 0.4 - 0.05, c + sx * 0.4 + 0.05, 0.0, 0.12, zu0 - 0.3, zu0 - 0.1)
    for x0 in (0.0, L - 0.3):                                                          # the end pilasters
        bm_box(P[Tm], x0, x0 + 0.3, 0.0, 0.08, 4.08, H - 0.45)
    bm_box(P[Tm], -0.03, L + 0.03, -0.3, 0.14, H - 0.45, H - 0.35)                       # the cornice, brackets, parapet
    for k in range(max(2, round(L / 0.7))):
        x = L * (k + 0.5) / max(2, round(L / 0.7))
        bm_box(P[Tm], x - 0.05, x + 0.05, 0.0, 0.38, H - 0.35, H - 0.1)
    bm_box(P[Tm], -0.05, L + 0.05, -0.3, 0.45, H - 0.1, H + 0.02)
    bm_box(P[W], 0.0, L, -0.3, 0.0, H + 0.02, H + 0.7)
    bm_box(P[Tm], -0.05, L + 0.05, -0.35, 0.06, H + 0.7, H + 0.8)
    P.flush(name + "_sage", smooth=())
    text(f"ST_WBZ_{name}_marceline", "FROM MARCELINE TO YOU", 0.23, (L / 2, 0.08, 3.7), (math.pi / 2, 0, math.pi), "hs_navy", 0.015)


def lace_rings(bm, x0, x1, z0, z1, y, cell=0.2, keep=None, t=0.014):
    """Cast-iron lace as a pierced pattern: touching rings in a grid, a small diamond between each four (keep(x, z, r)
    drops the rings outside a shape)."""
    nx = max(1, round((x1 - x0) / cell)); nz = max(1, round((z1 - z0) / cell))
    sx, sz = (x1 - x0) / nx, (z1 - z0) / nz; r = min(sx, sz) / 2; bw = r * 0.26
    prof = [(r - bw, -t), (r, -t), (r, t), (r - bw, t), (r - bw, -t)]
    for i in range(nx):
        for j in range(nz):
            x, z = x0 + sx * (i + 0.5), z0 + sz * (j + 0.5)
            if keep and not keep(x, z, r):
                continue
            bm_lathe(bm, prof, 8, T(x, y, z) @ R(math.pi / 2, "X"))
            if i < nx - 1 and j < nz - 1 and (not keep or keep(x + sx / 2, z + sz / 2, r * 0.3)):
                d = r * 0.28
                xc, zc = x + sx / 2, z + sz / 2
                bm_prism(bm, [(xc, zc - d), (xc + d, zc), (xc, zc + d), (xc - d, zc)], y - t, y + t, "xz")


def lattice_arcs(bm, a, b, z0, z1, y0, y1, n=3, w=0.025):
    """A transom's tracery of intersecting arcs (photos: the brick front's windows), between z0 and z1."""
    s = (b - a) / n
    for k in range(-1, n):
        xa, xb = a + s * k, a + s * (k + 2)
        if xa >= a - 1e-6 and xb <= b + 1e-6:
            bm_prism(bm, arch_band(xa, xb, z0, min((z1 - z0) * 0.9, (xb - xa) / 2), w, 10), y0, y1, "xz")
    bm_box(bm, a, b, y0, y1, z0 - w, z0)


def bench(P, x, y, L_=1.6):
    """A green slatted bench with iron ends, its back to the wall (photos)."""
    for k in range(4):
        yy = y + 0.12 + k * 0.11
        bm_box(P["bench_green"], x - L_ / 2, x + L_ / 2, yy, yy + 0.08, 0.42, 0.46)
    for k in range(3):
        zz = 0.55 + k * 0.13
        yy = y + 0.06 - (zz - 0.5) * 0.15
        bm_box(P["bench_green"], x - L_ / 2, x + L_ / 2, yy, yy + 0.03, zz, zz + 0.09)
    for sx in (-1, 1):
        xe = x + sx * (L_ / 2 - 0.08)
        for y0, y1, z0, z1 in ((0.04, 0.09, 0.0, 0.9), (0.5, 0.55, 0.0, 0.42), (0.04, 0.58, 0.62, 0.66), (0.52, 0.57, 0.42, 0.66),
                               (0.08, 0.54, 0.38, 0.42)):
            bm_box(P["iron"], xe - 0.03, xe + 0.03, y + y0, y + y1, z0, z1)


def wall_lantern(P, x, z):
    """A black wall lantern on a bracket (photos: either side of the brick front's sign)."""
    bm_box(P["iron"], x - 0.07, x + 0.07, 0.0, 0.03, z + 0.15, z + 0.55)
    bm_box(P["iron"], x - 0.015, x + 0.015, 0.0, 0.3, z + 0.42, z + 0.46)
    bm_lathe(P["iron"], [(0, 0), (0.08, 0), (0.1, 0.05), (0, 0.06)], 6, T(x, 0.3, z - 0.06))
    bm_lathe(P["lamp"], [(0, 0), (0.08, 0), (0.11, 0.32), (0, 0.32)], 6, T(x, 0.3, z))
    bm_lathe(P["iron"], [(0, 0), (0.15, 0), (0.0, 0.16)], 6, T(x, 0.3, z + 0.32))


def brick_front(name, L, H):
    """The brick front south of the grey-green one (photos; x 0 .. L, +y out): four tall windows recessed in the brick
    with teal frames, glazing bars and transoms of intersecting arcs, the glazed white doors folded open in the middle,
    the plum "HOME STORE" oval with the light blue plates "FINEST WARES" / "QUALITY GOODS" and a lantern either side;
    the cast-iron veranda along the upper floor (posts, a lace railing with flower boxes, lace spandrels under arches,
    hanging baskets) in front of four curtained windows; the cream cornice and parapet with a raised middle; two green
    benches against the wall."""
    P = Parts(); Wb, Tf = "brick", "t_dkgreen"; m = L / 2
    zg, D = 4.3, 1.25
    gx = [m - 3.85, m - 2.0, m + 2.0, m + 3.85]
    ops = sorted([(x - 0.62, x + 0.62) for x in gx] + [(m - 0.85, m + 0.85)])
    cuts = [0.0] + [v for a, b in ops for v in (a, b)] + [L]
    for a, b in zip(cuts[0::2], cuts[1::2]):
        bm_box(P[Wb], a, b, -0.3, 0.0, 0.0, zg)
    for a, b in ops:
        bm_box(P[Wb], a, b, -0.3, 0.0, 3.3, zg)
        bm_box(P[Wb], a - 0.06, b + 0.06, 0.0, 0.03, 3.3, 3.48)                         # a brick soldier course over it
    for x in gx:                                                                        # the windows
        a, b = x - 0.62, x + 0.62
        bm_box(P[Wb], a, b, -0.3, 0.0, 0.0, 0.45)
        bm_box(P[Tf], a + 0.04, b - 0.04, 0.0, 0.03, 0.08, 0.38)
        bm_box(P["t_cream"], a - 0.05, b + 0.05, 0.0, 0.08, 0.4, 0.48)
        bm_box(P["display"], a, b, -0.3, -0.28, 0.45, 3.3)
        bm_box(P["shopglass"], a, b, -0.2, -0.19, 0.45, 3.3)
        for x0, x1, z0, z1 in ((a, a + 0.09, 0.45, 3.3), (b - 0.09, b, 0.45, 3.3), (a, b, 0.45, 0.55), (a, b, 3.2, 3.3), (a, b, 2.55, 2.65)):
            bm_box(P[Tf], x0, x1, -0.22, -0.12, z0, z1)
        for k in range(1, 3):
            xx = a + (b - a) * k / 3
            bm_box(P[Tf], xx - 0.02, xx + 0.02, -0.19, -0.15, 0.55, 2.55)
        for z in (1.25, 1.9):
            bm_box(P[Tf], a + 0.09, b - 0.09, -0.19, -0.15, z - 0.02, z + 0.02)
        lattice_arcs(P[Tf], a + 0.09, b - 0.09, 2.65, 3.2, -0.19, -0.15)
    a, b = m - 0.85, m + 0.85                                                           # the door, the shop behind it
    bm_box(P["in_floor"], a, b, -2.2, 0.3, -0.05, 0.05)
    bm_box(P["display"], a - 0.4, b + 0.4, -2.25, -2.2, 0.05, 3.0)
    for x0 in (a - 0.4, b + 0.34):
        bm_box(P["in_wall"], x0, x0 + 0.06, -2.2, -0.3, 0.05, 3.0)
    bm_box(P["in_ceiling"], a - 0.4, b + 0.4, -2.2, -0.3, 3.0, 3.05)
    bm_box(P["in_wood"], a + 0.1, b - 0.1, -2.15, -1.7, 0.05, 1.9)
    for x0, x1, z0, z1 in ((a, a + 0.08, 0.0, 3.3), (b - 0.08, b, 0.0, 3.3), (a, b, 2.85, 2.95), (a, b, 3.22, 3.3)):
        bm_box(P[Tf], x0, x1, -0.2, -0.05, z0, z1)
    lattice_arcs(P[Tf], a + 0.08, b - 0.08, 2.95, 3.22, -0.16, -0.12, n=4)
    for sx in (-1, 1):                                                                  # the folding leaves, open
        x = m + sx * 0.82
        for k, (y0, y1) in enumerate(((0.0, 0.4), (0.4, 0.8))):
            bm_box(P["t_white"], x - 0.025, x + 0.025, y0, y1, 0.02, 2.82)
            bm_box(P["shopglass"], x - 0.03, x + 0.03, y0 + 0.07, y1 - 0.07, 1.0, 2.7)
            for z in (1.45, 1.9, 2.3):
                bm_box(P["t_white"], x - 0.03, x + 0.03, y0, y1, z - 0.015, z + 0.015)
    # the sign, its plates, the lanterns
    oval_board(P, "hs_plum", "brass", m, 0.04, 3.82, 1.15, 0.36)
    bm_lathe(P["brass"], [(0, 0), (1.0, 0), (1.0, 0.05), (0, 0.05)], 14, T(m, 0.06, 4.28) @ _diag(0.2, 0.14) @ R(-math.pi / 2, "X"))
    for sx in (-1, 1):
        x = m + sx * 2.15
        bm_box(P["brass"], x - 0.62, x + 0.62, 0.0, 0.04, 3.68, 3.96)
        bm_box(P["hs_lblue"], x - 0.58, x + 0.58, 0.04, 0.06, 3.71, 3.93)
        wall_lantern(P, m + sx * 1.38, 3.55)
    # the veranda: floor, posts, lace
    bm_box(P["t_cream"], -0.05, L + 0.05, 0.0, D + 0.05, zg + 0.05, zg + 0.22)
    bm_box(P["t_white"], -0.05, L + 0.05, D - 0.05, D + 0.08, zg - 0.08, zg + 0.3)
    zt = 7.45
    posts = [0.12 + (L - 0.24) * k / 5 for k in range(6)]
    for x in posts:
        bm_box(P["hall_iron"], x - 0.05, x + 0.05, D - 0.18, D - 0.08, zg + 0.22, zt)
        bm_box(P["hall_iron"], x - 0.09, x + 0.09, D - 0.22, D - 0.04, zg + 0.22, zg + 0.4)
        bm_box(P["hall_iron"], x - 0.08, x + 0.08, D - 0.21, D - 0.05, zt - 0.95, zt - 0.85)
    yl = D - 0.13
    bm_box(P["hall_iron"], 0.0, L, yl - 0.03, yl + 0.03, zg + 1.15, zg + 1.2)
    bm_box(P["hall_iron"], 0.0, L, yl - 0.02, yl + 0.02, zg + 0.28, zg + 0.31)
    for a, b in zip(posts[:-1], posts[1:]):
        lace_rings(P["hall_iron"], a + 0.05, b - 0.05, zg + 0.31, zg + 1.15, yl, 0.21)
        sp, rise = zt - 1.0, 0.55                                                       # an arch from post to post, lace above it
        pts, (zc, Rr, half) = seg_arc((a + b) / 2, sp, b - a - 0.1, rise, 14)
        bm_prism(P["hall_iron"], arch_band(a + 0.05, b - 0.05, sp, rise, 0.05, 14), yl - 0.015, yl + 0.015, "xz")
        cxm = (a + b) / 2
        keep = lambda x, z, r, cxm=cxm, zc=zc, Rr=Rr: math.hypot(x - cxm, z - zc) > Rr + 0.05 + r and z < zt - 0.1
        lace_rings(P["hall_iron"], a + 0.05, b - 0.05, sp - 0.3, zt - 0.08, yl, 0.18, keep)
        bm_box(P["hall_iron"], a, b, yl - 0.02, yl + 0.02, zt - 0.1, zt - 0.06)
        x = (a + b) / 2                                                                 # the hanging basket
        bm_box(P["iron"], x - 0.006, x + 0.006, yl - 0.25, yl - 0.24, zt - 1.0, zt - 0.1)
        bm_lathe(P["wood"], [(0, 0), (0.18, 0.05), (0.2, 0.2), (0, 0.2)], 8, T(x, yl - 0.25, zt - 1.3))
        globe_lamp_bm(P["leaf"], x, yl - 0.25, zt - 1.12, 0.24)
        for dz in (-0.25, -0.38):
            globe_lamp_bm(P["leaf"], x + 0.1, yl - 0.2, zt - 1.12 + dz, 0.08)
        bm_box(P["t_dkgreen"], x - 0.4, x + 0.4, yl - 0.1, yl + 0.1, zg + 1.2, zg + 1.38)   # the flower box on the rail
        for k in range(4):
            globe_lamp_bm(P["flowers_red" if k % 2 else "flowers_pink"], x - 0.3 + 0.2 * k, yl, zg + 1.45, 0.1)
    bm_box(P["hall_iron"], -0.05, L + 0.05, 0.0, D + 0.02, zt, zt + 0.08)                 # its roof, a fascia
    bm_box(P["t_white"], -0.05, L + 0.05, D - 0.02, D + 0.04, zt - 0.05, zt + 0.12)
    # the upper floor: four curtained windows with arched-lattice top lights
    zu0, zu1 = zg + 0.5, zg + 2.65
    cuts = [0.0] + [v for x in gx for v in (x - 0.5, x + 0.5)] + [L]
    for a, b in zip(cuts[0::2], cuts[1::2]):
        bm_box(P[Wb], a, b, -0.3, 0.0, zg, H - 0.6)
    for x in gx:
        a, b = x - 0.5, x + 0.5
        bm_box(P[Wb], a, b, -0.3, 0.0, zg, zu0); bm_box(P[Wb], a, b, -0.3, 0.0, zu1, H - 0.6)
        bm_box(P["win_dark"], a, b, -0.22, -0.2, zu0, zu1)
        for x0, x1, z0, z1 in ((a, a + 0.08, zu0, zu1), (b - 0.08, b, zu0, zu1), (a, b, zu0, zu0 + 0.08), (a, b, zu1 - 0.08, zu1), (a, b, zu1 - 0.6, zu1 - 0.53)):
            bm_box(P[Tf], x0, x1, -0.2, -0.1, z0, z1)
        for x0, x1 in ((a + 0.1, a + 0.4), (b - 0.4, b - 0.1)):
            bm_box(P["t_white"], x0, x1, -0.2, -0.17, zu0 + 0.1, zu1 - 0.62)
        bm_box(P[Tf], x - 0.02, x + 0.02, -0.17, -0.13, zu0 + 0.08, zu1 - 0.6)
        lattice_arcs(P[Tf], a + 0.08, b - 0.08, zu1 - 0.53, zu1 - 0.08, -0.18, -0.14)
        bm_box(P["t_cream"], a - 0.06, b + 0.06, 0.0, 0.06, zu1, zu1 + 0.1)
    # the cornice and the parapet with its raised middle
    bm_box(P["t_cream"], -0.05, L + 0.05, -0.3, 0.12, H - 0.6, H - 0.45)
    for k in range(max(2, round(L / 0.55))):
        x = L * (k + 0.5) / max(2, round(L / 0.55))
        bm_box(P["t_cream"], x - 0.05, x + 0.05, 0.0, 0.32, H - 0.45, H - 0.22)
    bm_box(P["t_cream"], -0.08, L + 0.08, -0.3, 0.4, H - 0.22, H - 0.1)
    bm_box(P["t_cream"], 0.0, L, -0.3, 0.0, H - 0.1, H + 0.5)
    for k in range(4):
        a, b = L * k / 4 + 0.2, L * (k + 1) / 4 - 0.2
        bm_box(P["t_white"], a, b, 0.0, 0.03, H + 0.02, H + 0.4)
        bm_box(P["t_cream"], a + 0.05, b - 0.05, 0.03, 0.04, H + 0.07, H + 0.35)
    bm_box(P["t_cream"], -0.05, L + 0.05, -0.35, 0.06, H + 0.5, H + 0.6)
    bm_box(P["t_cream"], m - 1.5, m + 1.5, -0.3, 0.04, H + 0.6, H + 0.95)
    bm_box(P["t_cream"], m - 1.6, m + 1.6, -0.35, 0.1, H + 0.95, H + 1.05)
    for sx in (-1, 1):
        bench(P, m + sx * 2.9, 0.05)
    P.flush(name + "_brick", smooth=("lamp", "leaf", "flowers_red", "flowers_pink"))
    text(f"ST_WBZ_{name}_hsb", "HOME STORE", 0.3, (m, 0.15, 3.84), (math.pi / 2, 0, math.pi), "t_cream", 0.015)
    for sx, body in ((-1, "FINEST WARES"), (1, "QUALITY GOODS")):
        text(f"ST_WBZ_{name}_plate{sx}", body, 0.11, (m + sx * 2.15, 0.07, 3.82), (math.pi / 2, 0, math.pi), "hs_navy", 0.006)


def home_store_face(name, L, H, kind, outer_run, rng):
    """One outer edge of the block in its frame (x 0 .. L, +y out), by kind (home_store_kind)."""
    if kind in ("hs", "hs2"):
        hs_face(name, L, *((0.0, 0.335) if kind == "hs" else (0.499, 0.0)))
    elif kind == "blue1890":
        blue_1890(name, L)
    elif kind == "sage":
        sage_front(name, L, H)
    elif kind == "hs_brick":
        brick_front(name, L, H)
    elif kind == "sage_jog":
        outer_run(name, L, H, "w_bluegrey", "t_white", rng)
    else:                                                 # brick_jog, the Refreshment Corner's brick sides
        outer_run(name, L, H, "brick", "t_cream" if kind.startswith("rc") else "t_aqua", rng)


# ================================================================ stage B, large 5 .. 7 (refine_WB.md): signs, porches, the bank
def arc_letters(name, body, size, cx, cy, R, z, mat, step):
    """body set letter by letter round a vertical drum (centre (cx, cy), radius R, bulging +y) at height z, facing out,
    read from the street (the first letter on +x); step: the arc per letter."""
    n = len(body)
    for k, ch in enumerate(body):
        if ch == " ":
            continue
        t = math.pi / 2 + (k - (n - 1) / 2) * step / R
        text(f"ST_WBZ_{name}_{k}", ch, size, (cx + R * math.cos(t), cy + R * math.sin(t), z), (math.pi / 2, 0, t + math.pi / 2), mat, 0.015)


def half_disc(r, x=0.0, n=16):
    """A half disc on the wall plane y = 0 bulging +y, centred on x (for bm_prism, plane xy)."""
    return [(x + r * math.cos(math.pi * j / n), r * math.sin(math.pi * j / n)) for j in range(n + 1)]


def ge_porch(name, dx, gf):
    """wb3 G1 (0:02:02 .. 0:02:14, 0:03:20 .. 0:03:30), wb1 E4 / M4: Grand Emporium's round porch -- four thick cream
    columns on a half-round step, the entablature, and on it the drum of the first floor bulging out over the porch: a
    pale aqua band with "MILLINERY  FINE GIFTS  NOVELTIES", the curved red sign with gold letters "GRAND EMPORIUM", a
    cream cornice and a gilt crest. Shop frame (the front on y = 0, +y the street), centred on the door at dx.
    (The video shows it on the corner, chamfered towards the crossing; there the crossing's lattice tower (R1, WB
    (-11.0, -41.7)) stands, so it is on the Main Street face over the door -- by estimate.)"""
    P = Parts(); Rp = 2.5
    bm_prism(P["t_cream"], half_disc(Rp + 0.3, dx), 0.0, 0.12, "xy")                 # the step
    for a in (28.0, 74.0, 106.0, 152.0):                                              # the columns (wb3: four)
        x, y = dx + Rp * math.cos(math.radians(a)), Rp * math.sin(math.radians(a))
        bm_box(P["t_cream"], x - 0.36, x + 0.36, y - 0.36, y + 0.36, 0.12, 0.75)
        column_bm(P["t_cream"], x, y, 0.75, 2.75, 0.225, 16)
    bm_prism(P["t_white"], half_disc(Rp + 0.42, dx), 3.5, 3.95, "xy")                # the entablature (its soffit: the porch ceiling)
    bm_prism(P["t_cream"], half_disc(Rp + 0.5, dx), 3.95, 4.08, "xy")
    bm_box(P["iron"], dx - 0.01, dx + 0.01, 1.2 - 0.01, 1.2 + 0.01, 2.95, 3.5)       # a lamp under it
    globe_lamp_bm(P["lamp"], dx, 1.2, 2.85, 0.16)
    Rd = 2.3                                                                           # the drum
    bm_prism(P["ge_aqua"], half_disc(Rd, dx, 20), 4.08, 5.6, "xy")
    for z0, z1, r in ((4.08, 4.22, Rd + 0.08), (5.55, 5.72, Rd + 0.1)):
        bm_prism(P["t_cream"], half_disc(r, dx, 20), z0, z1, "xy")
    bm_prism(P["ge_red"], half_disc(Rd + 0.05, dx, 20), 5.72, 6.75, "xy")              # the red sign, gilt edges
    for z0, z1 in ((5.72, 5.8), (6.67, 6.75)):
        bm_prism(P["brass"], half_disc(Rd + 0.1, dx, 20), z0, z1, "xy")
    bm_prism(P["t_cream"], half_disc(Rd + 0.25, dx, 20), 6.75, 6.95, "xy")             # cornice, the crest
    bm_lathe(P["brass"], [(0, 0), (0.45, 0), (0.45, 0.06), (0, 0.06)], 16, T(dx, Rd + 0.05, 7.35) @ _diag(1.0, 0.75) @ R(-math.pi / 2, "X"))
    bm_box(P["t_cream"], dx - 0.6, dx + 0.6, Rd - 0.2, Rd + 0.05, 6.95, 7.75)
    P.flush(name + "_ge", smooth=("lamp",))
    arc_letters(name + "_ge_sign", "GRAND EMPORIUM", 0.5, dx, 0.0, Rd + 0.07, 6.24, "letters", 0.4)
    arc_letters(name + "_ge_band", "MILLINERY  FINE GIFTS  NOVELTIES", 0.2, dx, 0.0, Rd + 0.01, 4.9, "t_dkgreen", 0.165)


def shop_signs(name, w, st, gf, H, bx):
    """Signs added to a shop() front (shop frame): oval_sign -- a flat oval board on the first floor over the middle
    (the Magic Shop, wb2 MG1 0:06:14 .. 0:06:30: teal rim, pale face, its name, purple flowers either side);
    oval_blade -- an oval board hanging from an iron scroll bracket at the blade's place (Bibbidi Bobbidi Boutique, wb2
    BB1 0:10:26 .. 0:10:42: pink with a gilt rim)."""
    P = Parts()
    o = st.get("oval_sign")
    if o:
        y0, z = o.get("y", 0.05), o.get("z", gf + 1.2)
        oval_board(P, o["face"], o["rim"], w / 2, y0, z, 1.05, 0.5)
        text(f"ST_WBZ_{name}_oval", o["text"], 0.24, (w / 2, y0 + 0.11, z), (math.pi / 2, 0, math.pi), o["textmat"], 0.015)
        for sx in (-1, 1):
            for dz, r in ((0.0, 0.2), (-0.15, 0.16)):
                globe_lamp_bm(P["m_purple"], w / 2 + sx * 1.35, y0 + 0.15, z - 0.25 + dz, r)
    o = st.get("oval_blade")
    if o:
        zc = 3.15
        bm_box(P["iron"], bx - 0.03, bx + 0.03, 0.12, 1.45, 3.92, 3.98)               # the bracket: arm, scrolls, a lamp on it
        bm_box(P["iron"], bx - 0.02, bx + 0.02, 0.12, 0.16, 3.0, 3.98)
        for y, r in ((0.55, 0.22), (1.0, 0.18)):
            bm_lathe(P["iron"], [(r - 0.03, -0.015), (r, -0.015), (r, 0.015), (r - 0.03, 0.015)], 10, T(bx, y, 3.92 - r) @ R(math.pi / 2, "Y"))
        bm_lathe(P["brass"], [(0, 0), (0.08, 0), (0.1, 0.25), (0, 0.3)], 6, T(bx, 0.3, 3.98))
        globe_lamp_bm(P["lamp"], bx, 0.3, 4.12, 0.07)
        for y in (0.5, 1.2):
            bm_box(P["iron"], bx - 0.008, bx + 0.008, y - 0.008, y + 0.008, zc + 0.42, 3.92)
        for r_, mat, t0 in ((1.0, o["rim"], -0.03), (0.92, o["face"], -0.045)):
            bm_lathe(P[mat], [(0, t0), (1.0, t0), (1.0, -t0), (0, -t0)], 24,
                     T(bx, 0.85, zc) @ R(math.pi / 2, "Y") @ _diag2(0.45 * r_, 0.62 * r_))
        for sx in (-1, 1):
            text(f"ST_WBZ_{name}_blade{sx}", o["text"], 0.13, (bx + sx * 0.05, 0.85, zc), (math.pi / 2, 0, sx * math.pi / 2), o["textmat"], 0.008)
    P.flush(name + "_signs", smooth=("lamp", "m_purple"))


def _diag2(a, b):
    from mathutils import Matrix
    return Matrix.Diagonal((a, b, 1.0, 1.0))


# the Sumitomo Mitsui bank and Club 33 (wb2 BK1 / C33 0:04:42 .. 0:06:10). Placed by web sources (refine_WB.md,
# 位置修正(WEB基準)): Club 33's door is between the Magic Shop and the bank (happyell.co.jp/club33, castel.jp/p/453 --
# "クラブ33の隣にあるマジックショップ" / "クラブ33の隣にある三井住友銀行"), on Center Street on the Adventureland side
# (+x here: turn left at the crossing, the Magic Shop on the right -- happyell, matsunosuke.jp/club-33), at the outer end
# (laughingplace.com: "on the outside area"). So, going out of the arm: the Magic Shop (OSM point) -- Club 33 on ASE's
# last shop slot (5.2 m, ds_tdl_world_bazaar VIDEO_WALLS["ASE"], club33_front) -- the bank: its ATM corner on the edge
# (53.7, -69.4)-(56.7, -70.2) that carries ASE's front line on past the arm's end (bank_atm) and the main front on the
# edge (57.0, -69.1)-(59.9, -69.9) (carried on 0.3 m west, sumitomo_bank), both facing the covered way (EXT_E, OSM
# 1338996034). OSM has no point for either; the bank's split into the ATM corner and the main front is an estimate.
BANK = dict(p0=(56.71, -69.02), ang=math.degrees(math.atan2(-0.8, 2.9)), w=4.9)
ATM_EDGE = dict(p0=(53.7, -69.4), p1=(56.7, -70.2))


def bank_edge(mid):
    """The block's edges the bank's front stands on (their outer_run walls are left out)."""
    return 56.8 < mid[0] < 61.8 and -71.8 < mid[1] < -68.8


def _bank_style(**kw):
    st = dict(wall="bank_ivory", trim="bankteal", frame_trim="bankteal", fat_frame=True, floors=3, roof="parapet", win="arch",
              awning=("aw_green", "aw_white"), win_awn=False, balcony=True, ironmat="t_white", oriel=False, door="mid",
              signmat="aw_green", signtext="t_cream", sign="SUMITOMO MITSUI BANKING CORPORATION", door_mat="aw_maroon",
              pilasters=True, depth=3.0, theme="cards", deco=False, cresting=False, clapboard=0.3)
    st.update(kw)
    return st


def sumitomo_bank(shop):
    """wb2 BK1 (0:04:42 .. 0:05:26), wb1 A10 (0:10:34 .. 0:10:46): three storeys of ivory weatherboarding framed in teal
    (pilasters, broad frames round the shop windows, the window heads), green-and-white striped awnings, a balcony with
    a white balustrade, the green board with cream letters, the maroon door. A shop() front (WB frame), 3 m deep."""
    with frame("WBZ_bank", BANK["p0"][0], BANK["p0"][1], BANK["ang"]):
        shop("BANK", BANK["w"], _bank_style(), None)


def bank_atm(shop):
    """The bank's ATM corner (the branch has four ATMs and a counter; web sources, see above): the same front as the
    bank's on the edge between Club 33 and the bank's main front, 1.1 m back from it, with "SMBC ATM" on the board and
    no balcony. A shop() front (WB frame), 3 m deep."""
    (ax, ay), (bx_, by) = ATM_EDGE["p0"], ATM_EDGE["p1"]
    with frame("WBZ_bank_atm", ax, ay, math.degrees(math.atan2(by - ay, bx_ - ax))):
        shop("BANK_ATM", math.hypot(bx_ - ax, by - ay), _bank_style(sign="SMBC ATM", balcony=False), None)


def club33_front(name, w):
    """wb2 C33 (0:05:28 .. 0:06:10): Club 33's white stucco front -- a round-arched recess with the maroon double doors
    (leaded lights, an amber fanlight), a brass lantern in it, the bronze "33" plaque on the pier, potted rubber plants
    in white boxes either side; upstairs an arched window in a red frame with a lace curtain. In the current shop
    frame (x 0..w along the front, the street on +y): ASE's last slot, under the bridge (east_bridge: its girder at
    5.2 m, so the window sits below it and the front goes up to the block's roof, 8.5 m)."""
    P = Parts(); H = 8.0
    a, b = w / 2 - 0.9, w / 2 + 0.9                   # the recess, 0.6 m deep
    bm_box(P["t_white"], 0.0, w, -3.0, -0.6, 0.0, H)
    for x0, x1 in ((0.0, a), (b, w)):
        bm_box(P["t_white"], x0, x1, -0.6, 0.0, 0.0, H)
    bm_box(P["t_white"], a, b, -0.6, 0.0, 3.1, H)
    pts, _ = seg_arc(w / 2, 2.4, b - a, 0.7, 12)
    bm_prism(P["t_white"], [(a, 3.1)] + pts[::-1] + [(b, 3.1)], -0.6, 0.0, "xz")   # the spandrels over the arch
    bm_prism(P["t_cream"], arch_band(a, b, 2.4, 0.7, 0.14, 12, leg=2.4), 0.0, 0.05, "xz")
    bm_box(P["t_cream"], 0.0, w, -0.05, 0.08, 0.0, 0.35)                           # plinth, string course, cornice
    bm_box(P["t_cream"], -0.05, w + 0.05, 0.0, 0.12, 3.55, 3.75)
    bm_box(P["t_cream"], -0.08, w + 0.08, 0.0, 0.3, H - 0.4, H - 0.1)
    bm_box(P["t_white"], 0.0, w, -0.3, 0.0, H, H + 0.6)
    bm_box(P["t_cream"], -0.05, w + 0.05, -0.35, 0.05, H + 0.6, H + 0.7)
    for sx in (-1, 1):                                # the doors (two leaves), their leaded lights
        x0, x1 = sorted((w / 2, w / 2 + sx * 0.72))
        bm_box(P["aw_maroon"], x0, x1, -0.66, -0.6, 0.0, 2.35)
        bm_box(P["shopglass"], x0 + 0.12, x1 - 0.12, -0.6, -0.58, 1.1, 2.1)
        bm_box(P["brass"], (x0 + x1) / 2 - sx * 0.25 - 0.015, (x0 + x1) / 2 - sx * 0.25 + 0.015, -0.58, -0.54, 1.0, 1.2)
    bm_prism(P["display"], arch_opening(w / 2 - 0.72, w / 2 + 0.72, 2.35, 2.4, 0.62, 12), -0.66, -0.62, "xz")
    bm_box(P["iron"], w / 2 - 0.01, w / 2 + 0.01, -0.31, -0.29, 2.6, 3.0)        # the lantern
    bm_box(P["iron"], w / 2 - 0.12, w / 2 + 0.12, -0.42, -0.18, 2.25, 2.6)
    globe_lamp_bm(P["lamp"], w / 2, -0.3, 2.42, 0.09)
    px = b + (w - b) / 2                              # the "33" plaque
    bm_box(P["brass"], px - 0.24, px + 0.24, 0.0, 0.04, 2.35, 2.83)
    text(f"ST_WBZ_club33_{name}_plaque", "33", 0.26, (px, 0.05, 2.59), (math.pi / 2, 0, math.pi), "door", 0.01)
    for x in (a / 2, px):                             # the potted plants
        bm_box(P["t_cream"], x - 0.24, x + 0.24, 0.2, 0.68, 0.0, 0.6)
        bm_lathe(P["iron"], [(0, 0), (0.03, 0), (0.025, 1.0), (0, 1.0)], 6, T(x, 0.44, 0.6))
        for dz, ox, r in ((1.2, 0.06, 0.32), (1.55, -0.08, 0.28), (1.85, 0.02, 0.22)):
            globe_lamp_bm(P["topiary"], x + ox, 0.44, dz, r)
    m = w / 2                                          # upstairs: the arched window, red frame, lace curtain (under the girder)
    bm_prism(P["aw_red"], arch_opening(m - 0.55, m + 0.55, 3.95, 5.05, 0.55, 12), 0.0, 0.07, "xz")
    bm_prism(P["t_white"], arch_opening(m - 0.45, m + 0.45, 4.05, 5.05, 0.45, 12), 0.07, 0.08, "xz")
    bm_box(P["t_cream"], m - 0.75, m + 0.75, 0.0, 0.2, 3.8, 3.95)
    P.flush(f"club33_{name}", smooth=("lamp", "topiary"))


# ================================================================ 6. the covered way out of the west arm's end (wb3 N1, R2-15)
GATE = dict(L=7.0, hw=6.1, ceil=4.7, top=8.4, strip=1.7)


def bench_blue(P, x, y, a):
    """A pale blue bench with white edges (wb3 N1 / C2), a = the direction it faces (rad)."""
    M_ = T(x, y, 0.0) @ R(a - math.pi / 2, "Z")

    def bx(k, *b):
        vs = bm_box(P[k], *b); bmesh.ops.transform(P[k], matrix=M_, verts=vs)
    for sx in (-0.85, 0.85):
        bx("t_white", sx - 0.05, sx + 0.05, -0.28, 0.28, 0.0, 0.45)
    bx("bench_blue", -1.0, 1.0, -0.3, 0.3, 0.38, 0.46)
    bx("t_white", -1.02, 1.02, -0.32, 0.32, 0.36, 0.39)


def west_gate(arm):
    """wb3 N1 (0:04:30 .. 0:04:50), R2-15 (v2 1:11:04 .. 1:11:28): the covered way out of Center Street's west arm.
    OSM has no building here: by estimate it stands across the gap between the blocks' ends (365357846 / 72216845,
    12.2 m) and runs 7 m out along the footway 629990047, short of the junction with the footway from the north
    (1294701305, about 7.4 m out). A flat cream-pink ceiling at 4.7 m with round lights; on the right going out
    (365357846's side) a strip of shop windows -- tall lattice sashes over a blue wainscot, the navy frieze of white
    stars, a maroon scalloped awning, pale blue benches; on the left square cream columns open to the outside; over it
    all a cream storey with the sun medallion and a crown on the outer face (R2-15). Local: x out along the arm, +y
    across towards 72216845."""
    p0, p1, _ = arm
    L_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); ux, uy = (p1[0] - p0[0]) / L_, (p1[1] - p0[1]) / L_
    G = GATE; L, hw, zc, top = G["L"], G["hw"], G["ceil"], G["top"]; ys = -hw + G["strip"]
    P = Parts()
    with frame("WBZ_west_gate", p1[0], p1[1], math.degrees(math.atan2(uy, ux))):
        bm_box(P["walk"], 0.3, L + 0.2, -hw, hw, 0.0, 0.045)                          # the floor (terracotta, as the street's)
        bm_box(P["gate_soffit"], 0.0, L, ys, hw, zc, zc + 0.12)                        # the ceiling, the slab and the storey over it
        bm_box(P["w_cream2"], 0.0, L, -hw, hw, zc + 0.12, top)
        bm_box(P["t_cream"], -0.05, L + 0.1, -hw - 0.1, hw + 0.1, top - 0.35, top)     # cornice, parapet
        bm_box(P["w_cream2"], 0.0, L, -hw, hw, top, top + 0.6)
        bm_box(P["t_cream"], 0.0, L + 0.12, -hw - 0.12, hw + 0.12, top + 0.6, top + 0.72)
        bm_box(P["t_cream"], L - 0.05, L + 0.12, ys, hw, zc - 0.45, zc + 0.12)         # the lintel over the mouth
        for k in range(3):                                # round lights in the ceiling
            for j in range(4):
                bm_lathe(P["lamp"], [(0, 0), (0.16, 0), (0.16, 0.03), (0, 0.03)], 10, T(1.2 + 2.2 * k, ys + 1.3 + 2.4 * j, zc - 0.03))
        # the strip of shops on the right: a body to the ceiling, its face on y = ys
        bm_box(P["w_cream2"], 0.0, L - 0.35, -hw, ys - 0.35, 0.0, zc + 0.12)
        for nm, fx, fa, x1, bn in (("n", 0.0, 0.0, L, (1.9, 5.1)), ("out", L, -90.0, G["strip"], ())):
            with frame(f"WBZ_west_gate_{nm}", fx, ys, fa):  # the strip's face; its outer end (facing out), short
                Pf = Parts()                              # (meshes take the frame they are flushed in)
                shopface(Pf, 0.0, x1, zc, benches=bn)
                Pf.flush(f"west_gate_{nm}", smooth=())
        for x, y in ((4.4, hw - 0.45), (L - 0.3, hw - 0.45)):   # square cream columns (the strip's end pier at the mouth)
            bm_box(P["t_cream"], x - 0.4, x + 0.4, y - 0.4, y + 0.4, 0.0, 0.5)
            bm_box(P["t_cream"], x - 0.3, x + 0.3, y - 0.3, y + 0.3, 0.5, zc - 0.5)
            bm_box(P["t_cream"], x - 0.38, x + 0.38, y - 0.38, y + 0.38, zc - 0.5, zc)
        for x in (1.75, 5.25):                            # the storey's windows on the outer sides
            for y in (-hw - 0.02, hw):
                bm_box(P["t_cream"], x - 0.62, x + 0.62, y, y + 0.02, zc + 0.75, zc + 2.85)
                bm_box(P["win_dark"], x - 0.5, x + 0.5, y - 0.01, y + 0.03, zc + 0.85, zc + 2.75)
        # the outer face: the sun medallion between two windows, a crown on the parapet (R2-15)
        mz = zc + 1.9
        bm_lathe(P["t_cream"], [(0, 0), (1.0, 0), (1.0, 0.12), (0.6, 0.18), (0, 0.2)], 20, T(L, 0.0, mz) @ R(math.pi / 2, "Y"))
        for k in range(16):
            a = 2 * math.pi * k / 16
            c_, s_ = math.cos(a), math.sin(a)
            bm_prism(P["t_cream"], [(1.0 * c_ - 0.14 * s_, mz + 1.0 * s_ + 0.14 * c_), (1.5 * c_, mz + 1.5 * s_),
                                    (1.0 * c_ + 0.14 * s_, mz + 1.0 * s_ - 0.14 * c_)], L, L + 0.08, "yz")
        for y in (-3.8, 3.8):
            bm_box(P["t_cream"], L, L + 0.02, y - 0.6, y + 0.6, zc + 0.75, zc + 2.85)
            bm_box(P["win_dark"], L + 0.01, L + 0.03, y - 0.48, y + 0.48, zc + 0.85, zc + 2.75)
        for y, h in ((-1.6, 0.9), (0.0, 1.5), (1.6, 0.9)):
            bm_prism(P["t_cream"], [(y - 0.55, top + 0.72), (y + 0.55, top + 0.72), (y, top + 0.72 + h)], L - 0.1, L + 0.05, "yz")
        P.flush("west_gate", smooth=("lamp",))


def shopface(P, x0, x1, zc, benches=()):
    """A shop face along x0..x1 on y = 0 facing +y (wb3 N1, 0:04:36 .. 0:04:44): a blue wainscot, tall lattice sashes in
    cream frames with a lit display behind, the navy frieze with white stars, a maroon scalloped awning; benches."""
    n = max(1, round((x1 - x0) / 2.3))
    bm_box(P["display"], x0, x1, -0.32, -0.3, 0.9, 3.3)
    for k in range(n):
        a, b = x0 + (x1 - x0) * k / n, x0 + (x1 - x0) * (k + 1) / n
        bm_box(P["t_cream"], a, a + 0.3, 0.0, 0.08, 0.0, 3.4)                           # the pier
        bm_box(P["wb_bulk"], a + 0.3, b, -0.05, 0.03, 0.0, 0.9)                         # the wainscot
        bm_box(P["shopglass"], a + 0.3, b, -0.06, -0.04, 0.9, 3.3)
        m = (a + 0.3 + b) / 2
        for xx in (m - (b - a - 0.3) / 4, m, m + (b - a - 0.3) / 4):                     # the lattice
            bm_box(P["t_cream"], xx - 0.025, xx + 0.025, -0.04, 0.0, 0.9, 3.3)
        for zz in (0.9, 1.7, 2.5, 3.3):
            bm_box(P["t_cream"], a + 0.3, b, -0.04, 0.02, zz - 0.03, zz + 0.03)
    bm_box(P["t_cream"], x1 - 0.3, x1, 0.0, 0.08, 0.0, 3.4)
    bm_box(P["wb_navy"], x0, x1, 0.0, 0.06, 3.85, zc - 0.05)                          # the frieze of stars
    x = x0 + 0.3
    while x < x1 - 0.2:
        bm_prism(P["t_white"], [(x - 0.13, (3.85 + zc) / 2), (x, 3.9), (x + 0.13, (3.85 + zc) / 2), (x, zc - 0.1)], 0.06, 0.075, "xz")
        x += 0.6
    x = x0 + 0.2                                           # the awning, scalloped
    while x < x1 - 0.2:
        xb = min(x + 0.5, x1 - 0.2)
        bm_prism(P["aw_maroon"], [(0.05, 3.8), (0.9, 3.35), (0.9, 3.25), (0.05, 3.7)], x, xb, "yz")
        bm_prism(P["aw_maroon"], [(x + (xb - x) * (1 - j / 6), 3.25 - 0.14 * math.sin(math.pi * j / 6)) for j in range(7)], 0.87, 0.9, "xz")
        x = xb
    for bxx in benches:
        bench_blue(P, bxx, 0.75, math.pi / 2)


# ================================================================ wb3 C1: the white hand carts (the user asked for them)
def hand_cart(P, x, y, ang):
    """A small white vendor's cart, shut under its cover (wb3 0:06:32 .. 0:06:36, 0:10:26 .. 0:10:34): a box on two
    big pale yellow spoked wheels at one end, two legs and a handle at the other, the white cloth cover with a rounded
    top hanging over its sides. Local x along the cart, 1.75 m long, 0.9 m wide, 1.65 m high. ESTIMATE (sizes)."""
    M_ = T(x, y, 0.0) @ R(ang, "Z")

    def bx(k, *b):
        vs = bm_box(P[k], *b); bmesh.ops.transform(P[k], matrix=M_, verts=vs)
    bx("cart_white", -0.85, 0.75, -0.45, 0.45, 0.42, 1.3)                          # the cover over the box
    bx("cart_white", -0.88, 0.78, -0.48, 0.48, 0.38, 0.46)                         # its hem
    top = [(0.45 * math.cos(math.pi * j / 8), 1.3 + 0.32 * math.sin(math.pi * j / 8)) for j in range(9)]
    n0 = len(P["cart_white"].verts)
    bm_prism(P["cart_white"], top, -0.85, 0.75, "yz")
    P["cart_white"].verts.ensure_lookup_table()
    bmesh.ops.transform(P["cart_white"], matrix=M_, verts=[P["cart_white"].verts[i] for i in range(n0, len(P["cart_white"].verts))])
    for sy in (-1, 1):                                    # the wheels: rim, hub, eight spokes
        Mw = M_ @ T(-0.45, sy * 0.52, 0.36) @ R(math.pi / 2, "X")
        bm_lathe(P["cart_wheel"], [(0.31, -0.025), (0.36, -0.025), (0.36, 0.025), (0.31, 0.025)], 16, Mw)
        bm_lathe(P["cart_wheel"], [(0, -0.06), (0.06, -0.06), (0.06, 0.06), (0, 0.06)], 8, Mw)
        for q in range(8):
            vs = bm_box(P["cart_wheel"], 0.05, 0.32, -0.012, 0.012, -0.012, 0.012)
            bmesh.ops.transform(P["cart_wheel"], matrix=Mw @ R(2 * math.pi * q / 8, "Z"), verts=vs)
        bx("cart_wheel", 0.55, 0.6, sy * 0.38 - 0.025, sy * 0.38 + 0.025, 0.0, 0.42)   # a leg at the other end
    bx("cart_wheel", -0.5, -0.4, -0.55, 0.55, 0.33, 0.39)                         # the axle
    bx("brass", 0.75, 1.15, -0.02, 0.02, 0.86, 0.9)                                # the handle
    bx("brass", 1.13, 1.17, -0.25, 0.25, 0.86, 0.9)


CARTS = [(-10.3, -82.35, math.pi / 2)]                    # WB: in front of Penny Arcade, on the entrance side of its door
CART_ARM = (25.0, 5.3)                                    # and on the west arm (ARMS[0]) beside Toy Station: t from the crossing, offset


def vendor_carts(arms):
    """wb3 C1 (0:06:32 .. 0:06:36, 0:10:26, 0:10:34): two carts, by estimate, out of the walkers' way -- one on the
    sidewalk in front of Penny Arcade (OSM point (-17.0, -82.8)), on the entrance side of its door, 1.3 m off the front
    (clear of the planter (-10, -84), Harrington's veranda and the bench (-10.2, -79)); one on the west arm's south-side sidewalk beside Toy
    Station (its small front ends about t 24.7), in the 4 m between the benches at t 22 and t 28 -- clear of Toy
    Station's door (t 30.6 .. 32.8)."""
    P = Parts()
    for x, y, a in CARTS:
        hand_cart(P, x, y, a)
    p0, p1, _ = arms[0]
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    t, off = CART_ARM
    hand_cart(P, p0[0] + ux * t - uy * off, p0[1] + uy * t + ux * off, math.atan2(uy, ux))
    P.flush("carts", smooth=())


# ================================================================ 6. Town Center Fashions inside (wb3 F2)
def fashion_island(bmk, x, y, r, top):
    """wb3 F2 (0:07:16 .. 0:07:24): the octagonal pink island counter with gilt trims and its canopy on four slim posts
    (a pink octagonal frieze, a cream scalloped valance)."""
    octo = lambda rr: [(x + rr * math.cos(math.pi * (k + 0.5) / 4), y + rr * math.sin(math.pi * (k + 0.5) / 4)) for k in range(8)]
    bm_prism(bmk("fs_pink"), octo(r), 0.06, 0.9, "xy")
    bm_prism(bmk("brass"), octo(r + 0.06), 0.9, 0.95, "xy")
    bm_prism(bmk("brass"), octo(r + 0.02), 0.1, 0.15, "xy")
    zc0 = min(2.7, top - 0.75)
    for k in range(4):
        a = math.pi * (k + 0.5) / 2
        px, py = x + 0.55 * r * math.cos(a), y + 0.55 * r * math.sin(a)
        bm_box(bmk("t_cream"), px - 0.04, px + 0.04, py - 0.04, py + 0.04, 0.95, zc0)
    bm_prism(bmk("fs_pink"), octo(r + 0.15), zc0, zc0 + 0.45, "xy")
    bm_prism(bmk("brass"), octo(r + 0.2), zc0 + 0.45, zc0 + 0.5, "xy")
    bm = bmk("t_cream")
    for k in range(8):                                    # the valance: five scallops under each side
        a0, a1 = math.pi * (k + 0.5) / 4, math.pi * (k + 1.5) / 4
        xa, ya = x + (r + 0.16) * math.cos(a0), y + (r + 0.16) * math.sin(a0)
        xb, yb = x + (r + 0.16) * math.cos(a1), y + (r + 0.16) * math.sin(a1)
        for j in range(5):
            f0, f1 = j / 5, (j + 1) / 5
            q0 = (xa + (xb - xa) * f0, ya + (yb - ya) * f0); q1 = (xa + (xb - xa) * f1, ya + (yb - ya) * f1)
            bm.faces.new((bm.verts.new((*q0, zc0)), bm.verts.new((*q1, zc0)), bm.verts.new(((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2, zc0 - 0.18))))


# ================================================================ 7. Eastside Cafe: two faces (user photos, 2026-10-05)
EASTSIDE_END = dict(p0=(56.5, -60.3), p1=(57.6, -56.1))     # the arm hall's end wall north of the covered way (EXT_E): faces west


def _fan(P, x0, x1, zs, rise):
    """A fanlight in a round-arched head: the dark opening, a cream band round it, radial bars from the centre."""
    m = (x0 + x1) / 2; r = (x1 - x0) / 2
    bm_prism(P["display"], arch_opening(x0 + 0.1, x1 - 0.1, zs - 0.55, zs, rise - 0.1, 12), 0.0, 0.05, "xz")
    bm_prism(P["t_cream"], arch_band(x0, x1, zs, rise, 0.12, 12, leg=0.55), 0.0, 0.08, "xz")
    for k in range(1, 8):                               # the fan's bars, from a point at the springing line
        a = math.pi * k / 8
        tx, tz = m + (r - 0.12) * math.cos(a), zs + (rise - 0.12) * math.sin(a)
        d = (tx - m, tz - zs); L = math.hypot(*d); nx, nz = -d[1] / L * 0.012, d[0] / L * 0.012
        bm_prism(P["t_cream"], [(m - nx, zs - nz), (tx - nx, tz - nz), (tx + nx, tz + nz), (m + nx, zs + nz)], 0.05, 0.075, "xz")


def eastside_front(name, w):
    """The Center Street face (user photos ec1 .. ec3): painted pale grey-green brick over a cream ground floor -- on the
    left the porch with two white posts, the glass door and the gold "EASTSIDE CAFE"; right of it two display windows
    with white bars; a fanlight in a round-arched cream head over the porch and over the windows; above, two cream bay
    windows with a cornice, and a cream cornice and a white parapet. In the current shop frame (x 0..w, street on +y);
    ANE's end shop (6.2 m). Solid behind (the room is not walked into)."""
    P = Parts(); H = 8.5
    bm_box(P["t_cream"], 0.0, w, -3.0, 0.0, 0.0, 3.1)
    bm_box(P["es_grey"], 0.0, w, -3.0, 0.0, 3.1, H)
    bm_box(P["t_cream"], 0.0, w, -0.05, 0.12, 0.0, 0.5)                              # plinth
    bm_box(P["t_cream"], -0.04, w + 0.04, 0.0, 0.14, 2.9, 3.2)                       # the sign band
    m1, m2 = 1.5, 4.6
    for x in (0.4, 2.6):                                                             # the porch: two posts and a roof
        bm_lathe(P["t_white"], [(0, 0), (0.13, 0), (0.1, 0.3), (0.08, 0.5), (0.08, 2.6), (0.12, 2.7), (0, 2.7)], 8, T(x, 0.95, 0.0))
    bm_box(P["t_white"], 0.25, 2.75, 0.0, 1.1, 2.7, 2.9)
    bm_box(P["display"], 0.6, 2.4, 0.0, 0.05, 0.0, 2.55)                             # the door and its glass
    bm_box(P["shopglass"], 0.75, 1.3, 0.05, 0.08, 0.5, 2.4); bm_box(P["shopglass"], 1.7, 2.25, 0.05, 0.08, 0.5, 2.4)
    for x0 in (3.3, 4.65):                                                           # two display windows
        bm_box(P["t_cream"], x0 - 0.1, x0 + 1.4, 0.0, 0.1, 0.5, 2.8)
        bm_box(P["shopglass"], x0, x0 + 1.3, 0.1, 0.13, 0.7, 2.7)
        for k in (1, 2):
            bm_box(P["t_white"], x0 + k * 0.43 - 0.015, x0 + k * 0.43 + 0.015, 0.13, 0.16, 0.7, 2.7)
        for z in (1.4, 2.05):
            bm_box(P["t_white"], x0, x0 + 1.3, 0.13, 0.16, z - 0.015, z + 0.015)
    text(f"ST_WBZ_eastside_{name}_sign", "EASTSIDE CAFE", 0.2, (1.5, 0.16, 3.0), (math.pi / 2, 0, math.pi), "brass", 0.015)
    _fan(P, 0.2, 2.8, 3.9, 0.8)                                                      # the fanlights over the porch and the windows
    _fan(P, 3.3, 5.9, 3.9, 0.8)
    for m in (m1, m2):                                                               # the bay windows
        bay = [(m - 0.95, 0.0), (m + 0.95, 0.0), (m + 0.6, 0.75), (m - 0.6, 0.75)]
        bm_prism(P["t_cream"], bay, 5.0, 7.3, "xy")
        bm_prism(P["t_white"], [(m - 1.02, -0.02), (m + 1.02, -0.02), (m + 0.66, 0.82), (m - 0.66, 0.82)], 4.85, 5.0, "xy")
        bm_prism(P["t_white"], [(m - 1.02, -0.02), (m + 1.02, -0.02), (m + 0.66, 0.82), (m - 0.66, 0.82)], 7.3, 7.5, "xy")
        bm_box(P["shopglass"], m - 0.42, m + 0.42, 0.74, 0.77, 5.35, 7.0)
        bm_box(P["t_white"], m - 0.015, m + 0.015, 0.77, 0.8, 5.35, 7.0)
        for sx in (-1, 1):
            bm_box(P["shopglass"], m + sx * 0.8 - 0.02, m + sx * 0.8 + 0.02, 0.2, 0.55, 5.35, 7.0)
        for sx in (-0.45, 0.45):                                                     # the X panels under the sill
            bm_box(P["t_white"], m + sx - 0.22, m + sx + 0.22, 0.2, 0.22, 5.1, 5.3)
    bm_box(P["t_cream"], -0.05, w + 0.05, -0.1, 0.3, H - 0.45, H - 0.1)              # cornice and parapet
    bm_box(P["t_white"], 0.0, w, -0.1, 0.1, H - 0.1, H + 0.5)
    P.flush(f"eastside_{name}", smooth=("lamp", "topiary"))


def eastside_end():
    """The arm-end face (user photos, the pale blue corner): periwinkle weatherboard over a white ground floor with two
    tall lattice windows, a white balcony with a turned-post balustrade over it, upstairs two pairs of a tall window under a
    round one, a cream cornice, blue planter boxes with shrubs in front. Faces west into the arm hall; 4.3 m wide."""
    (ax, ay), (bx_, by) = EASTSIDE_END["p0"], EASTSIDE_END["p1"]
    L = math.hypot(bx_ - ax, by - ay); H = 8.2
    with frame("WBZ_eastside_end", ax, ay, math.degrees(math.atan2(by - ay, bx_ - ax))):
        P = Parts()
        bm_box(P["t_white"], 0.0, L, -2.5, 0.0, 0.0, 3.5)
        bm_box(P["es_blue"], 0.0, L, -2.5, 0.0, 3.5, H)
        bm_box(P["es_blue"], 0.0, L, -0.02, 0.06, 0.0, 0.6)                          # the blue panelled base
        for x0 in (0.35, 2.2):                                                       # the two tall lattice windows
            bm_box(P["shopglass"], x0, x0 + 1.75, 0.06, 0.09, 0.7, 3.2)
            for k in range(1, 4):
                bm_box(P["t_white"], x0 + k * 0.4375 - 0.015, x0 + k * 0.4375 + 0.015, 0.09, 0.12, 0.7, 3.2)
            for z in (1.3, 1.9, 2.5):
                bm_box(P["t_white"], x0, x0 + 1.75, 0.09, 0.12, z - 0.015, z + 0.015)
        for x in (0.0, 2.1, L - 0.2):                                                # white pilasters
            bm_box(P["t_white"], x, x + 0.2, 0.0, 0.15, 0.0, 3.5)
        bm_box(P["t_white"], -0.05, L + 0.05, 0.0, 1.0, 3.45, 3.7)                   # the balcony slab
        for k in range(int(L / 0.3) + 1):                                            # the balustrade
            x = 0.08 + k * 0.3
            if x < L - 0.04:
                bm_lathe(P["t_white"], [(0, 0), (0.04, 0), (0.025, 0.2), (0.04, 0.5), (0.045, 0.75), (0, 0.75)], 6, T(x, 0.9, 3.7))
        bm_box(P["t_white"], -0.04, L + 0.04, 0.82, 0.98, 4.43, 4.52)
        for sx in (0.0, L - 0.1):
            bm_box(P["t_white"], sx, sx + 0.1, 0.0, 1.0, 3.7, 4.43)                  # the side returns
        for cx in (1.1, 3.2):                                                        # the window pairs upstairs
            bm_box(P["t_white"], cx - 0.5, cx + 0.5, 0.0, 0.09, 4.2, 5.85)
            bm_box(P["shopglass"], cx - 0.4, cx + 0.4, 0.09, 0.11, 4.3, 5.75)
            bm_box(P["t_white"], cx - 0.015, cx + 0.015, 0.11, 0.14, 4.3, 5.75)
            bm_box(P["t_white"], cx - 0.4, cx + 0.4, 0.11, 0.14, 5.0 - 0.015, 5.0 + 0.015)
            ring = [(cx + 0.5 * math.cos(2 * math.pi * k / 16), 6.55 + 0.5 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
            gl = [(cx + 0.38 * math.cos(2 * math.pi * k / 16), 6.55 + 0.38 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
            bm_prism(P["t_white"], ring, 0.0, 0.08, "xz")                            # the round window and its frame
            bm_prism(P["shopglass"], gl, 0.08, 0.1, "xz")
        bm_box(P["t_cream"], -0.06, L + 0.06, -0.1, 0.3, H - 0.55, H - 0.2)          # the cornice with dentils
        x = 0.0
        while x < L:
            bm_box(P["t_cream"], x, min(x + 0.1, L), 0.0, 0.34, H - 0.75, H - 0.55); x += 0.22
        bm_box(P["t_white"], 0.0, L, -0.1, 0.1, H - 0.2, H + 0.4)
        for x0 in (0.3, 2.35):                                                       # the blue planter boxes and their shrubs
            bm_box(P["es_box"], x0, x0 + 1.6, 1.15, 1.75, 0.0, 0.5)
            bm_box(P["t_white"], x0 - 0.03, x0 + 1.63, 1.12, 1.78, 0.48, 0.55)
            globe_lamp_bm(P["topiary"], x0 + 0.8, 1.45, 0.85, 0.42)
        P.flush("eastside_end", smooth=("lamp", "topiary"))


# ================================================================ 8. Center Street Coffeehouse (user photos + wb3 3:52 .. 4:00)
def _cf_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    M["cf_brick"] = P("st_wbz_cf_brick", (0.48, 0.14, 0.105), 0.85)        # the upper wall: salmon-red brick (#B8695B)
    M["cf_pier"] = P("st_wbz_cf_pier", (0.35, 0.08, 0.05), 0.8)            # the banded red-brown piers (#A0503F)
    M["cf_ivory"] = P("st_wbz_cf_ivory", (0.80, 0.76, 0.64), 0.7)          # the ground floor's pale wall (#E8E2D2)
    M["cf_teal"] = P("st_wbz_cf_teal", (0.08, 0.43, 0.43), 0.5)            # the crown's teal border, the frieze (#4FB0B0)
    M["cf_door"] = P("st_wbz_cf_door", (0.14, 0.02, 0.02), 0.5)            # the maroon doors, the letters (#4A1E1E)
    M["cf_signface"] = P("st_wbz_cf_signface", (0.72, 0.70, 0.66), 0.35, Metallic=0.6)   # the stainless sign slab
    M["cf_wall"] = P("st_wbz_cf_wall", (0.46, 0.58, 0.57), 0.7)            # inside: pale blue-grey walls
    M["cf_col"] = P("st_wbz_cf_col", (0.48, 0.62, 0.60), 0.45)             # the round columns (#B9D1CE)
    M["cf_ceiling"] = P("st_wbz_cf_ceiling", (0.80, 0.72, 0.55), 0.8)      # the cream ceiling
    M["cf_seat"] = P("st_wbz_cf_seat", (0.40, 0.08, 0.05), 0.6)            # the chairs' red-brown seats
    M["cf_black"] = P("st_wbz_cf_black", (0.02, 0.02, 0.02), 0.4)          # the foyer's black tiles
    M["cf_car_a"] = P("st_wbz_cf_car_a", (0.55, 0.12, 0.05), 0.9)          # the dining room's carpet: red-orange,
    M["cf_car_b"] = P("st_wbz_cf_car_b", (0.04, 0.30, 0.30), 0.9)          # teal,
    M["cf_car_c"] = P("st_wbz_cf_car_c", (0.75, 0.62, 0.42), 0.9)          # cream
    return M


def coffeehouse(name, w):
    """The whole shop in the current shop frame (x 0..w, the front on y = 0, the street on +y, the room behind it).
    Outside (the user's photos): two banded red-brown piers, between them the ivory ground floor with two big oval chrome
    windows (the X of chrome bars across them) either side of the maroon double doors, the stainless sign slab with
    "COFFEEHOUSE" in maroon letters and two orange neon lines, the teal-edged Art Deco crown ("center" | "street" either
    side of a cream fluted fin), small windows with green awnings, a cream band with the "1892" plaque and a curved cap.
    Inside (wb3 3:52 .. 4:00 and the photos): a black-and-white chequered foyer with a reception stand, the dining room
    with a patterned carpet, chrome-and-red tables and chairs, two round pale columns, a stepped cream cove, amber cove
    lights along the walls."""
    from mathutils import Matrix
    P = Parts(); gf = 4.2; D = 7.0
    dx = w / 2; pw = min(0.7, w * 0.09)
    xa, xb = pw, w - pw
    gl, gr = (xa, dx - 0.78), (dx + 0.78, xb)             # the wall's two stretches either side of the doors
    for x0, x1 in ((0.0, pw), (w - pw, w)):               # piers (banded)
        bm_box(P["cf_pier"], x0, x1, -0.3, 0.22, 0.0, 9.8)
        z = 0.5
        while z < 9.4:
            bm_box(P["cf_pier"], x0 - 0.02, x1 + 0.02, 0.22, 0.27, z, z + 0.2); z += 0.4
        bm_box(P["cf_pier"], x0 - 0.1, x1 + 0.1, -0.3, 0.4, 9.4, 9.8)
        bm_box(P["t_cream"], x0 - 0.1, x1 + 0.1, 0.0, 0.3, 0.0, 0.45)
    zc = 1.95                                             # the ground floor: ivory wall with the oval holes, and the ovals
    for a, b_ in (gl, gr):
        m_ = (a + b_) / 2; rx = min(1.2, (b_ - a) / 2 - 0.12); rz = min(1.0, rx * 0.83)
        if rx < 0.7:
            bm_box(P["cf_ivory"], a, b_, -0.3, 0.0, 0.0, gf)
            continue
        bm_box(P["cf_ivory"], a, m_ - rx, -0.3, 0.0, 0.0, gf); bm_box(P["cf_ivory"], m_ + rx, b_, -0.3, 0.0, 0.0, gf)
        n = max(6, int(2 * rx / 0.12)); sw = 2 * rx / n
        for k in range(n):
            xm = m_ - rx + sw * (k + 0.5); h = rz * math.sqrt(max(0.0, 1 - ((xm - m_) / rx) ** 2))
            bm_box(P["cf_ivory"], xm - sw / 2, xm + sw / 2, -0.3, 0.0, 0.0, zc - h)
            bm_box(P["cf_ivory"], xm - sw / 2, xm + sw / 2, -0.3, 0.0, zc + h, gf)
        sc = Matrix.Diagonal((rx + 0.06, 1.0, rz + 0.06, 1.0))
        bm_lathe(P["chrome"], [(0.86, 0), (1.0, 0), (1.0, 0.12), (0.86, 0.12)], 28, T(m_, 0.04, zc) @ sc @ R(-math.pi / 2, "X"))
        pts = [(m_ + (rx - 0.02) * math.cos(2 * math.pi * k / 28), zc + (rz - 0.02) * math.sin(2 * math.pi * k / 28)) for k in range(28)]
        bm_prism(P["shopglass"], pts, -0.12, -0.1, "xz")
        for dz in (-0.5, 0.0, 0.5):                       # the chrome bars: three horizontals, the upright, two diagonals
            hw_ = rx * math.sqrt(max(0.0, 1 - (dz / rz) ** 2)) * 0.97
            bm_box(P["chrome"], m_ - hw_, m_ + hw_, 0.0, 0.05, zc + dz - 0.02, zc + dz + 0.02)
        bm_box(P["chrome"], m_ - 0.02, m_ + 0.02, 0.0, 0.05, zc - rz * 0.97, zc + rz * 0.97)
        for s_ in (-1, 1):
            bm_prism(P["chrome"], [(m_ - s_ * rx * 0.6, zc - rz * 0.8), (m_ + s_ * rx * 0.6, zc + rz * 0.8),
                                   (m_ + s_ * rx * 0.6 + 0.04, zc + rz * 0.8), (m_ - s_ * rx * 0.6 + 0.04, zc - rz * 0.8)], 0.0, 0.05, "xz")
    bm_box(P["cf_ivory"], dx - 0.78, dx + 0.78, -0.3, 0.0, 3.0, gf)             # above the doorway; the maroon leaves swung in
    for sx in (-1, 1):
        hx = dx + sx * 0.78
        bm_box(P["cf_door"], hx - 0.04, hx + 0.04, -1.2, -0.3, 0.0, 2.95)
        bm_box(P["brass"], hx - sx * 0.08, hx - sx * 0.06, -1.15, -1.1, 1.0, 1.3)
    bm_box(P["chrome"], dx - 0.78, dx + 0.78, -0.3, 0.0, 0.0, 0.03)
    sx0, sx1 = pw + 0.25, w - pw - 0.25                  # the stainless sign slab and its neon
    bm_box(P["cf_signface"], sx0, sx1, 0.0, 0.5, 3.05, 3.95)
    bm_box(P["chrome"], sx0 - 0.06, sx1 + 0.06, -0.02, 0.56, 3.95, 4.05)
    bm_box(P["chrome"], sx0 - 0.06, sx1 + 0.06, -0.02, 0.56, 2.98, 3.05)
    for z in (3.2, 3.8):
        bm_box(P["neon_red"], sx0 + 0.3, sx1 - 0.3, 0.5, 0.53, z, z + 0.03)
    sz = min(0.42, (sx1 - sx0 - 0.8) / 8.5)
    text(f"ST_WBZ_cf_{name}_sign", "COFFEEHOUSE", sz, (dx, 0.54, 3.38), (math.pi / 2, 0, math.pi), "cf_door", 0.02)
    bm_box(P["neon_red"], dx - 0.35, dx + 0.35, 0.5, 0.56, 3.12, 3.3)                   # the small red "UCC" tag
    for s_ in (-1, 1):                                    # the crown: teal-edged arched panels either side of a cream fin
        a0 = dx + s_ * 0.3; a1 = dx + s_ * 2.0
        lo, hi = (a0, a1) if s_ > 0 else (a1, a0)
        pts, _ = seg_arc((lo + hi) / 2, 4.5, hi - lo, 0.6, 12)
        bm_prism(P["cf_teal"], [(lo, 4.0), (hi, 4.0)] + pts, 0.0, 0.1, "xz")
        bm_prism(P["t_cream"], [(lo + 0.08, 4.1), (hi - 0.08, 4.1)] + [(x, z - 0.08) for x, z in pts], 0.1, 0.13, "xz")
        text(f"ST_WBZ_cf_{name}_crown{s_}", "center" if s_ < 0 else "street", 0.17, ((lo + hi) / 2, 0.14, 4.2), (math.pi / 2, 0, math.pi), "cf_door", 0.01)
    bm_box(P["t_cream"], dx - 0.28, dx + 0.28, 0.0, 0.2, 3.95, 5.9)
    for k in range(-2, 3):                                # the fluting
        bm_box(P["cf_ivory"], dx + k * 0.1 - 0.02, dx + k * 0.1 + 0.02, 0.2, 0.24, 4.0, 5.8)
    bm_box(P["t_cream"], dx - 0.2, dx + 0.2, 0.0, 0.16, 5.9, 6.2)
    bm_box(P["cf_brick"], pw, w - pw, -0.3, 0.0, gf, 8.5)  # the upper wall: brick and windows with green awnings
    nwin = 3 if w >= 6.0 else 2
    for k in range(nwin):
        x = pw + (w - 2 * pw) * (k + 0.5) / nwin; ww = 0.95
        bm_box(P["t_cream"], x - ww / 2 - 0.1, x + ww / 2 + 0.1, 0.0, 0.08, 6.0, 7.9)
        bm_box(P["glass"], x - ww / 2, x + ww / 2, 0.08, 0.1, 6.1, 7.7)
        bm_box(P["t_white"], x - ww / 2 + 0.05, x + ww / 2 - 0.05, 0.1, 0.12, 6.1, 7.2)            # the curtain
        bm_box(P["t_cream"], x - 0.02, x + 0.02, 0.1, 0.13, 6.1, 7.7)
        bm_box(P["t_cream"], x - ww / 2 - 0.2, x + ww / 2 + 0.2, 0.0, 0.2, 5.8, 6.0)              # the sill
        bm_box(P["t_cream"], x - ww / 2 - 0.15, x + ww / 2 + 0.15, 0.0, 0.14, 7.9, 8.1)           # the lintel
        for j in range(5):                                                                         # the arch's stones
            bm_box(P["t_cream"], x - ww / 2 - 0.1 + j * (ww + 0.2) / 5 + 0.02, x - ww / 2 - 0.1 + (j + 1) * (ww + 0.2) / 5 - 0.02, 0.0, 0.06, 8.1, 8.35)
        for j in range(8):                                                                         # the green awning
            xa_ = x - ww / 2 - 0.1 + j * (ww + 0.2) / 8
            bm_prism(P["aw_green" if j % 2 == 0 else "aw_white"], [(0.05, 7.85), (0.6, 7.2), (0.6, 7.05), (0.05, 7.7)], xa_, xa_ + (ww + 0.2) / 8, "yz")
    bm_box(P["t_cream"], pw - 0.05, w - pw + 0.05, -0.1, 0.3, 8.5, 8.8)                            # cornice, the band, plaque, cap
    bm_box(P["t_cream"], pw, w - pw, -0.1, 0.1, 8.8, 9.7)
    bm_box(P["t_white"], dx - 0.9, dx + 0.9, 0.1, 0.16, 8.95, 9.5)
    text(f"ST_WBZ_cf_{name}_year", "1892", 0.34, (dx, 0.18, 9.12), (math.pi / 2, 0, math.pi), "cf_door", 0.012)
    pts, _ = seg_arc(dx, 9.7, w - 2 * pw, 0.8, 18)
    bm_prism(P["cf_pier"], [(pw, 9.7), (w - pw, 9.7)] + pts, -0.1, 0.2, "xz")
    # ---- the inside
    x0, x1 = 0.0, w; top = 4.0
    bm_box(P["cf_black"], x0, x1, -2.0, -0.3, 0.0, 0.05)                                           # the foyer: black and white
    for i in range(int((x1 - x0) / 0.5) + 1):
        for j in range(4):
            if (i + j) % 2 == 0 and x0 + i * 0.5 < x1:
                bm_box(P["t_white"], x0 + i * 0.5, min(x0 + (i + 1) * 0.5, x1), -2.0 + j * 0.425, -2.0 + (j + 1) * 0.425, 0.0, 0.052)
    rng = random.Random(1892)
    ncx = max(1, int((x1 - x0) / 0.8)); ncy = int((D - 2.0) / 0.8)
    for i in range(ncx):                                                                            # the carpet
        for j in range(ncy):
            k = ("cf_car_a", "cf_car_b", "cf_car_c", "cf_car_a")[(i * 3 + j * 5 + rng.randrange(2)) % 4]
            bm_box(P[k], x0 + (x1 - x0) * i / ncx, x0 + (x1 - x0) * (i + 1) / ncx, -2.0 - (D - 2.0) * (j + 1) / ncy, -2.0 - (D - 2.0) * j / ncy, 0.0, 0.05)
    for a, b_, c0, c1 in ((x0, x0 + 0.15, -D, -0.3), (x1 - 0.15, x1, -D, -0.3), (x0, x1, -D - 0.15, -D)):
        bm_box(P["cf_wall"], a, b_, c0, c1, 0.05, top)
        bm_box(P["cf_teal"], a, b_, c0, c1, 3.2, 3.6)                                              # the diamond frieze
        bm_box(P["chrome"], a, b_, c0, c1, 3.6, 3.65)
    bm_box(P["cf_ceiling"], x0, x1, -D - 0.15, -0.3, top, top + 0.15)
    for sxs in (x0 + 0.15, x1 - 0.35):                                                             # amber cove lights
        bm_box(P["display"], sxs, sxs + 0.2, -D, -0.6, top - 0.1, top)
    bm_box(P["display"], x0 + 0.15, x1 - 0.15, -D, -D + 0.2, top - 0.1, top)
    cx, cy = dx, -D * 0.55
    for r, z0_, z1_ in ((min(w * 0.45, 2.4), 3.85, 4.0), (min(w * 0.33, 1.8), 3.7, 3.85), (min(w * 0.22, 1.2), 3.55, 3.7)):
        bm_lathe(P["cf_ceiling"], [(0, z0_), (r, z0_), (r, z1_), (0, z1_)], 24, T(cx, cy, 0.0))
        bm_lathe(P["display"], [(r - 0.02, z0_ - 0.03), (r, z0_ - 0.03), (r, z0_), (r - 0.02, z0_)], 24, T(cx, cy, 0.0))
    for fx in (w * 0.28, w * 0.72):                                                                # two round columns
        fy = -D * 0.5
        bm_lathe(P["cf_col"], [(0, 0.05), (0.34, 0.05), (0.32, 0.3), (0.32, 3.2), (0.4, 3.45), (0.7, 3.95), (0, 3.95)], 18, T(fx, fy, 0.0))
        for z in (1.0, 2.0):
            bm_lathe(P["chrome"], [(0.325, z), (0.34, z), (0.34, z + 0.04), (0.325, z + 0.04)], 18, T(fx, fy, 0.0))
        bm_lathe(P["cf_teal"], [(0.4, 3.45), (0.42, 3.45), (0.42, 3.62), (0.4, 3.62)], 18, T(fx, fy, 0.0))
    bm_box(P["cf_door"], x1 * 0.08, x1 * 0.08 + 1.0, -1.6, -0.9, 0.05, 1.05)                       # the reception stand
    bm_box(P["brass"], x1 * 0.08 - 0.02, x1 * 0.08 + 1.02, -1.62, -0.88, 1.05, 1.1)
    for row, ty in enumerate((-3.2, -4.8, -6.2)):                                                  # tables and chairs
        xs = [0.9 + 1.9 * k for k in range(int((w - 1.0) / 1.9) + 1) if 0.9 + 1.9 * k < w - 0.8]
        for tx in xs:
            if abs(tx - dx) < 0.9 and row == 0:
                continue
            if any(math.hypot(tx - fx, ty + D * 0.5) < 1.0 for fx in (w * 0.28, w * 0.72)):
                continue
            bm_lathe(P["chrome"], [(0, 0.05), (0.2, 0.05), (0.04, 0.12), (0.04, 0.72), (0.48, 0.72), (0.48, 0.77), (0, 0.77)], 14, T(tx, ty, 0.0))
            for sx_ in (-0.62, 0.62):
                cxx, cyy = tx + sx_, ty
                bm_box(P["cf_seat"], cxx - 0.22, cxx + 0.22, cyy - 0.22, cyy + 0.22, 0.44, 0.5)
                bm_box(P["chrome"], cxx + (0.19 if sx_ < 0 else -0.23), cxx + (0.23 if sx_ < 0 else -0.19), cyy - 0.2, cyy + 0.2, 0.5, 0.95)
                for lx, ly in ((-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2)):
                    bm_box(P["chrome"], cxx + lx - 0.015, cxx + lx + 0.015, cyy + ly - 0.015, cyy + ly + 0.015, 0.05, 0.44)
    P.flush(f"coffeehouse_{name}", smooth=("lamp",))


# ================================================================ 9. Refreshment Corner's room (user photos 2026-10-05)
def _rc_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    M["rc_pink"] = P("st_wbz_rc_pink", (0.80, 0.36, 0.34), 0.8)           # the walls: salmon pink (#E4A09C)
    M["rc_mint"] = P("st_wbz_rc_mint", (0.55, 0.78, 0.68), 0.5)           # the wainscot and counter panels (#B9DDD0)
    M["rc_white"] = P("st_wbz_rc_white", (0.85, 0.83, 0.78), 0.5)         # the counter's body, the fretwork
    M["rc_ceiling"] = P("st_wbz_rc_ceiling", (0.84, 0.80, 0.70), 0.8)     # the cream ceiling
    M["rc_tile"] = P("st_wbz_rc_tile", (0.82, 0.80, 0.76), 0.35)          # the floor's white tile
    M["rc_tilered"] = P("st_wbz_rc_tilered", (0.62, 0.12, 0.10), 0.4)     # the red diamonds in it
    M["rc_cola_red"] = P("st_wbz_rc_cola_red", (0.55, 0.03, 0.04), 0.3, Emission_Color=(1.0, 0.25, 0.2, 1), Emission_Strength=0.8)
    M["rc_cola_green"] = P("st_wbz_rc_cola_green", (0.20, 0.55, 0.10), 0.3, Emission_Color=(0.5, 0.9, 0.2, 1), Emission_Strength=0.8)
    M["rc_roof_a"] = P("st_wbz_rc_roof_a", (0.10, 0.30, 0.16), 0.6)       # the mansard's scales: deep green,
    M["rc_roof_b"] = P("st_wbz_rc_roof_b", (0.12, 0.42, 0.30), 0.6)       # and the lighter teal-green between
    return M


def refreshment_room(L, m, D=7.0):
    """The counter-service room behind the Refreshment Corner's centre door (photos: the pink walls with a mint panelled
    wainscot and a frieze, the cream ceiling, the white tile floor with red diamonds, the white curved counter with mint
    panels and the white fretwork gallery over the back bar, brass queue rails, three Coca-Cola stained-glass drum lamps).
    In the exit building's frame: x 0..L, the front wall on y = 0 (thickness to -0.3), the room behind on -y; the door at m."""
    P = Parts(); top = 4.0; x0, x1 = 0.2, L - 0.2
    # floor: white tile with red diamonds (and the doorstep across the wall's thickness out to the pavement)
    bm_box(P["rc_tile"], x0, x1, -D, -0.3, 0.0, 0.05)
    bm_box(P["rc_tile"], m - 1.3, m + 1.3, -0.35, 0.6, 0.0, 0.05)
    nx = int((x1 - x0) / 0.7); ny = int((D - 0.3) / 0.7)
    for i in range(nx):
        for j in range(ny):
            cx_ = x0 + 0.7 * (i + 0.5); cy_ = -0.3 - 0.7 * (j + 0.5)
            bm_prism(P["rc_tilered"], [(cx_ - 0.14, cy_), (cx_, cy_ + 0.14), (cx_ + 0.14, cy_), (cx_, cy_ - 0.14)], 0.05, 0.057, "xy")
    # walls and ceiling
    for a, b_, c0, c1 in ((x0, x0 + 0.15, -D, -0.3), (x1 - 0.15, x1, -D, -0.3), (x0, x1, -D - 0.15, -D)):
        bm_box(P["rc_pink"], a, b_, c0, c1, 0.05, top)
        bm_box(P["rc_mint"], a, b_, c0, c1, 0.05, 1.1)                                   # the wainscot
        bm_box(P["rc_white"], a, b_, c0, c1, 1.1, 1.18)
        bm_box(P["rc_white"], a, b_, c0, c1, 3.55, 3.62)                                 # the frieze: a band of lighter pink
        bm_box(P["rc_white"], a, b_, c0, c1, top - 0.1, top)
    bm_box(P["rc_ceiling"], x0, x1, -D - 0.15, -0.3, top, top + 0.15)
    for k in range(int((x1 - x0 - 0.6) / 1.2)):                                          # the inset wainscot panels, back wall
        px = x0 + 0.5 + k * 1.2
        bm_box(P["rc_white"], px, px + 0.9, -D + 0.0, -D + 0.03, 0.25, 0.95)
    # the back bar: a gallery of white fretwork arches over the serving counter
    cy = -D + 2.6
    bm_box(P["rc_white"], x0 + 2.0, x1 - 2.0, cy - 0.45, cy + 0.45, 0.05, 0.9)          # the counter's body
    bm_box(P["rc_mint"], x0 + 1.95, x1 - 1.95, cy - 0.5, cy + 0.5, 0.9, 1.0)            # its top
    n = int((x1 - x0 - 4.0) / 1.2)
    for k in range(n):
        ax = x0 + 2.0 + (x1 - x0 - 4.0) * (k + 0.5) / n
        bm_box(P["rc_mint"], ax - 0.45, ax + 0.45, cy + 0.45, cy + 0.5, 0.2, 0.8)       # the mint inset panels on the counter's front
    ga, gb = x0 + 1.8, x1 - 1.8
    bm_box(P["rc_white"], ga, gb, -D + 0.05, -D + 0.25, 2.6, 2.75)                       # the gallery over the back bar
    for k in range(int((gb - ga) / 0.25) + 1):
        bm_box(P["rc_white"], ga + k * 0.25 - 0.02, ga + k * 0.25 + 0.02, -D + 0.1, -D + 0.18, 2.75, 3.3)
    bm_box(P["rc_white"], ga, gb, -D + 0.05, -D + 0.25, 3.3, 3.4)
    bm_box(P["rc_mint"], ga, gb, -D + 0.05, -D + 0.5, 0.05, 0.9)                         # the back bar
    # queue rails: brass posts and rails in a zig-zag in front of the counter
    for k in range(6):
        px = x0 + 3.2 + (x1 - x0 - 6.4) * k / 5; py = cy + 1.6 + (0.5 if k % 2 else 0.0)
        bm_box(P["brass"], px - 0.025, px + 0.025, py - 0.025, py + 0.025, 0.05, 1.0)
        if k and k != 3:                                  # (no rail across the middle: the way to the counter)
            qx = x0 + 3.2 + (x1 - x0 - 6.4) * (k - 1) / 5; qy = cy + 1.6 + (0.5 if (k - 1) % 2 else 0.0)
            bm_prism(P["brass"], [(qx, qy - 0.01), (px, py - 0.01), (px, py + 0.01), (qx, qy + 0.01)], 0.95, 0.99, "xy")
    # three Coca-Cola stained-glass drum lamps on rods
    for lx in (L * 0.25, L * 0.5, L * 0.75):
        ly = cy + 1.0
        bm_box(P["brass"], lx - 0.01, lx + 0.01, ly - 0.01, ly + 0.01, 3.3, top)
        bm_lathe(P["rc_cola_green"], [(0, 3.28), (0.55, 3.28), (0.55, 3.4), (0, 3.4)], 14, T(lx, ly, 0.0))
        bm_lathe(P["rc_cola_red"], [(0.55, 3.4), (0.55, 3.72), (0.5, 3.72), (0.5, 3.4)], 14, T(lx, ly, 0.0))
        bm_lathe(P["rc_cola_green"], [(0.55, 3.72), (0.55, 3.8), (0, 3.8)], 14, T(lx, ly, 0.0))
    P.flush("refreshment_room", smooth=("lamp",))


# ================================================================ 10. Grand Emporium's upper floors (user photos images/grand_emporium/ge1..4)
def _ge_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    M["ge_cream"] = P("st_wbz_ge_cream2", (0.85, 0.78, 0.58), 0.75)       # the cream upper wall (#EEE7C9)
    M["ge_blue"] = P("st_wbz_ge_blue", (0.46, 0.55, 0.66), 0.75)          # the pale blue-grey top wall and pediment (#B4C4D4)
    M["ge_frame"] = P("st_wbz_ge_frame", (0.33, 0.47, 0.58), 0.6)         # the pale blue window frames (#9CB6C9)
    M["ge_lead"] = P("st_wbz_ge_lead", (0.25, 0.34, 0.40), 0.4, Metallic=0.2)   # the leaded glass of the tall upper windows
    return M


def ge_upper(name, w, z0, pediment=False):
    """Grand Emporium's floors over the ground floor (photos ge1 .. ge4): a cream storey with one row of tall round-
    headed windows (pale blue frames, leaded glass, carved brackets between them under the cornice), a band of red
    dashes at its foot, the pale blue-grey top wall with cream-framed recessed panels, a cream cornice on corbels; with
    pediment=True (the Main Street face) a round-arched pediment over the middle with two small arched windows.
    Shop frame: the front on y = 0, +y the street; z0 = where the ground floor's parapet ends."""
    P = Parts(); zt = 8.45; H = 9.65
    bm_box(P["ge_cream"], 0.0, w, -0.35, 0.0, z0, zt)
    bm_box(P["ge_blue"], 0.0, w, -0.35, 0.0, zt, H)
    bm_box(P["t_cream"], -0.05, w + 0.05, -0.35, 0.08, zt - 0.08, zt + 0.1)                 # the string course
    x = 0.3
    while x < w - 0.5:                                                                      # the red dashes
        L_ = 1.1 if int(x / 1.4) % 2 == 0 else 0.3
        bm_box(P["ge_red"], x, min(x + L_, w - 0.3), 0.0, 0.05, z0 + 0.2, z0 + 0.38)
        x += L_ + 0.35
    n = max(2, int((w - 0.8) / 2.0)); ww = 0.95
    for k in range(n):                                                                      # the tall windows
        cx = 0.4 + (w - 0.8) * (k + 0.5) / n
        zb, zs = z0 + 0.7, zt - 1.35
        bm_prism(P["ge_frame"], arch_opening(cx - ww / 2 - 0.12, cx + ww / 2 + 0.12, zb - 0.1, zs, ww / 2 + 0.12, 12), 0.0, 0.09, "xz")
        bm_prism(P["ge_lead"], arch_opening(cx - ww / 2, cx + ww / 2, zb, zs, ww / 2, 12), 0.09, 0.11, "xz")
        bm_box(P["ge_frame"], cx - 0.015, cx + 0.015, 0.11, 0.14, zb, zs + ww / 2 - 0.05)   # the mullion and a transom bar
        bm_box(P["ge_frame"], cx - ww / 2, cx + ww / 2, 0.11, 0.14, zs - 0.015, zs + 0.015)
        bm_box(P["t_cream"], cx - ww / 2 - 0.2, cx + ww / 2 + 0.2, 0.0, 0.2, zb - 0.22, zb - 0.1)   # the sill
        if k:                                                                               # a bracket and a raised panel between windows
            bx = 0.4 + (w - 0.8) * k / n
            bm_box(P["t_cream"], bx - 0.14, bx + 0.14, 0.0, 0.28, zt - 0.75, zt - 0.1)
            bm_box(P["t_cream"], bx - 0.3, bx + 0.3, 0.0, 0.05, zb + 0.2, zs - 0.4)
    nb = max(1, int((w - 0.6) / 1.7))
    for k in range(nb):                                                                     # the top wall's recessed panels
        px = 0.3 + (w - 0.6) * (k + 0.5) / nb; pw_ = (w - 0.6) / nb - 0.3
        for a_, b_, c0, c1 in ((px - pw_ / 2, px + pw_ / 2, zt + 0.25, zt + 0.33), (px - pw_ / 2, px + pw_ / 2, H - 0.58, H - 0.5)):
            bm_box(P["t_cream"], a_, b_, 0.0, 0.04, c0, c1)
        for xe in (px - pw_ / 2, px + pw_ / 2 - 0.08):
            bm_box(P["t_cream"], xe, xe + 0.08, 0.0, 0.04, zt + 0.25, H - 0.5)
    bm_box(P["t_cream"], -0.08, w + 0.08, -0.35, 0.4, H - 0.4, H)                          # the cornice and its corbels
    x = 0.4
    while x < w - 0.3:
        bm_box(P["t_cream"], x - 0.08, x + 0.08, 0.0, 0.34, H - 0.85, H - 0.4); x += 0.8
    bm_box(P["t_cream"], -0.05, w + 0.05, -0.35, 0.1, H, H + 0.25)
    if pediment:
        pw2 = min(w - 1.0, 4.6); mx = w / 2
        pts, _ = seg_arc(mx, H + 0.25, pw2, 1.2, 20)
        bm_prism(P["ge_blue"], [(mx - pw2 / 2, H + 0.25), (mx + pw2 / 2, H + 0.25)] + pts, -0.35, 0.0, "xz")
        bm_prism(P["t_cream"], arch_band(mx - pw2 / 2, mx + pw2 / 2, H + 0.25, 1.2, 0.2, 20), -0.35, 0.12, "xz")
        for s_ in (-1, 1):
            cx = mx + s_ * 0.55
            bm_prism(P["ge_frame"], arch_opening(cx - 0.4, cx + 0.4, H + 0.35, H + 0.75, 0.4, 10), 0.0, 0.08, "xz")
            bm_prism(P["ge_lead"], arch_opening(cx - 0.3, cx + 0.3, H + 0.45, H + 0.75, 0.3, 10), 0.08, 0.1, "xz")
    P.flush(f"ge_upper_{name}", smooth=())


# ================================================================ 11. Restaurant Hokusai (user photos images/restaurant_hokusai/rh1..3, wb3 12:02 .. 13:00)
def _hk_materials(M):
    P = lambda n, c, r=0.6, **kw: _principled(n, c, r, **kw)[0]
    M["hk_pier"] = P("st_wbz_hk_pier", (0.48, 0.62, 0.57), 0.7)           # the pale grey-green piers and cornices (#B9CFC7)
    M["hk_tile"] = P("st_wbz_hk_tile", (0.27, 0.39, 0.33), 0.8)           # the second floor's grey-green tiled wall (#8FA89B)
    M["hk_white"] = P("st_wbz_hk_white", (0.88, 0.87, 0.82), 0.5)         # the window frames, panels, balusters
    M["hk_teal"] = P("st_wbz_hk_teal", (0.03, 0.30, 0.30), 0.5)           # the awnings' teal stripes, the sign's rim (#2F8F8F)
    M["hk_wall"] = P("st_wbz_hk_wall", (0.62, 0.38, 0.18), 0.8)           # inside: warm tan walls (#D6A06A)
    M["hk_floor"] = P("st_wbz_hk_floor", (0.10, 0.045, 0.025), 0.4)       # dark wood floor
    M["hk_gold"] = P("st_wbz_hk_gold", (0.78, 0.58, 0.20), 0.4, Metallic=0.3)   # the gold folding screens
    M["hk_wave"] = P("st_wbz_hk_wave", (0.08, 0.20, 0.32), 0.6)           # the Great Wave painted on them
    M["hk_red"] = P("st_wbz_hk_red", (0.70, 0.14, 0.05), 0.6)             # Red Fuji in its frame
    return M


def hokusai(name, w, D=7.0):
    """The whole shop in the current shop frame (front on y = 0, the street on +y): three bays between pale grey-green
    piers -- a window with a lattice transom, the open door under its lattice transom, a window pair -- white panels
    over them, a tiled second floor with three windows under teal-and-white awnings, the cream-and-green parapet with
    balusters either side of a gable with the "1897" tablet and an octagonal window, the oval "HOKUSAI" blade sign.
    Inside (wb3 12:20 .. 12:36): warm tan walls, a dark wood floor, gold folding screens painted with the Great Wave,
    the framed Red Fuji, low tables."""
    P = Parts(); gf = 4.6; H = 8.4; top = 4.0
    pw = min(0.7, w * 0.09); dw = max(1.9, min(2.4, w * 0.3)); bs = (w - 4 * pw - dw) / 2.0
    wid = [bs, dw, bs]
    px = [0.0, pw + bs, 2 * pw + bs + dw, 3 * pw + 2 * bs + dw]               # the four piers' left edges
    bays = [(px[i] + pw, px[i] + pw + wid[i]) for i in range(3)]
    for x0 in px:                                                             # the piers, the whole height, with capitals
        bm_box(P["hk_pier"], x0, x0 + pw, -0.3, 0.12, 0.0, H + 0.9)
        bm_box(P["hk_pier"], x0 - 0.06, x0 + pw + 0.06, 0.0, 0.2, 0.0, 0.5)
        bm_box(P["hk_pier"], x0 - 0.06, x0 + pw + 0.06, 0.0, 0.2, H + 0.5, H + 0.9)
    bm_box(P["hk_pier"], 0.0, w, -0.3, 0.1, gf - 0.1, gf + 0.15)               # the cornice over the ground floor
    for i, (a, b_) in enumerate(bays):
        m = (a + b_) / 2
        # ground floor
        if i == 1:                                                            # the door bay: the open doorway
            hw = min(0.85, (b_ - a) / 2 - 0.15)
            bm_box(P["hk_white"], a, m - hw, -0.3, 0.0, 0.0, 3.5); bm_box(P["hk_white"], m + hw, b_, -0.3, 0.0, 0.0, 3.5)
            bm_box(P["hk_white"], a, b_, -0.3, 0.0, 3.5, gf - 0.1)
            bm_box(P["hk_teal"], m - hw - 0.05, m + hw + 0.05, 0.0, 0.1, 3.4, 3.55)        # the door head
            for k in range(1, 8):                                                           # the lattice transom
                bm_box(P["hk_white"], m - hw + (2 * hw) * k / 8 - 0.012, m - hw + (2 * hw) * k / 8 + 0.012, 0.0, 0.05, 2.9, 3.4)
            bm_box(P["shopglass"], m - hw, m + hw, -0.02, 0.0, 2.9, 3.4)
            for sx in (-1, 1):                                                              # the dark leaves, one swung in
                bm_box(P["cf_door"], m + sx * (hw - 0.04) - 0.04, m + sx * (hw - 0.04) + 0.04, -1.0 if sx < 0 else -0.5, -0.3, 0.0, 2.85)
        else:
            bm_box(P["hk_white"], a, b_, -0.3, 0.0, 0.0, 0.9)                               # the white panelled base
            bm_box(P["hk_pier"], a, b_, 0.0, 0.04, 0.2, 0.7)
            bm_box(P["hk_white"], a, b_, -0.3, 0.0, 3.4, gf - 0.1)
            bm_box(P["shopglass"], a + 0.12, b_ - 0.12, -0.02, 0.02, 0.9, 3.4)
            bm_box(P["hk_white"], a + 0.05, b_ - 0.05, 0.02, 0.07, 3.2, 3.4)
            for k in range(1, 6):                                                           # the lattice transom
                xx = a + 0.12 + (b_ - a - 0.24) * k / 6
                bm_box(P["hk_white"], xx - 0.012, xx + 0.012, 0.02, 0.06, 3.0, 3.2)
            for z in (1.9, 2.9):
                bm_box(P["hk_white"], a + 0.1, b_ - 0.1, 0.02, 0.07, z - 0.02, z + 0.02)
            if i == 2:
                bm_box(P["hk_white"], m - 0.02, m + 0.02, 0.02, 0.07, 0.9, 3.0)
        bm_box(P["hk_white"], a + 0.05, b_ - 0.05, 0.0, 0.03, gf - 0.9, gf - 0.2)           # the wide white panel over each bay
        # second floor: tiled wall, window, awning
        bm_box(P["hk_tile"], a, b_, -0.3, 0.0, gf + 0.15, H)
        ww = min(1.0, (b_ - a) - 0.7)
        bm_box(P["hk_white"], m - ww / 2 - 0.1, m + ww / 2 + 0.1, 0.0, 0.07, gf + 0.8, gf + 2.7)
        bm_box(P["glass"], m - ww / 2, m + ww / 2, 0.07, 0.09, gf + 0.9, gf + 2.6)
        bm_box(P["t_white"], m - ww / 2 + 0.05, m + ww / 2 - 0.05, 0.09, 0.11, gf + 0.9, gf + 2.2)    # the curtain
        bm_box(P["hk_white"], m - 0.015, m + 0.015, 0.09, 0.12, gf + 0.9, gf + 2.6)
        bm_prism(P["hk_white"], [(m - ww / 2 - 0.2, gf + 2.7), (m + ww / 2 + 0.2, gf + 2.7), (m, gf + 3.2)], 0.0, 0.1, "xz")   # a pedimented head
        for j in range(8):                                                                          # the teal-and-white awning
            xa_ = m - ww / 2 - 0.15 + j * (ww + 0.3) / 8
            bm_prism(P["hk_teal" if j % 2 == 0 else "t_white"], [(0.05, gf + 2.65), (0.75, gf + 2.0), (0.75, gf + 1.85), (0.05, gf + 2.5)],
                     xa_, xa_ + (ww + 0.3) / 8, "yz")
    bm_box(P["hk_pier"], 0.0, w, -0.35, 0.3, H, H + 0.35)                       # the parapet: cornice with dentils, the balusters
    x = 0.1
    while x < w - 0.1:
        bm_box(P["hk_pier"], x, x + 0.1, 0.0, 0.3, H - 0.12, H); x += 0.22
    for xa_, xb_ in ((0.0, bays[1][0] - 0.1), (bays[1][1] + 0.1, w)):
        bm_box(P["hk_white"], xa_, xb_, -0.3, 0.0, H + 0.35, H + 0.5)
        n = max(2, int((xb_ - xa_) / 0.3))
        for k in range(n):
            bx = xa_ + (xb_ - xa_) * (k + 0.5) / n
            bm_lathe(P["hk_white"], [(0, 0), (0.05, 0), (0.035, 0.2), (0.06, 0.5), (0.035, 0.8), (0.05, 0.9), (0, 0.9)], 6, T(bx, -0.1, H + 0.5))
        bm_box(P["hk_white"], xa_, xb_, -0.3, 0.1, H + 1.4, H + 1.5)
    gx0, gx1 = bays[1][0] - pw * 0.4, bays[1][1] + pw * 0.4                     # the gable over the middle
    mx = w / 2
    bm_prism(P["hk_pier"], [(gx0, H + 0.35), (gx1, H + 0.35), (mx, H + 2.6)], -0.35, 0.1, "xz")
    bm_prism(P["hk_white"], [(gx0 + 0.3, H + 0.45), (gx1 - 0.3, H + 0.45), (mx, H + 2.2)], 0.1, 0.14, "xz")
    bm_box(P["t_white"], mx - 0.45, mx + 0.45, 0.14, 0.18, H + 0.65, H + 1.1)   # the "1897" tablet
    text(f"ST_WBZ_hk_{name}_year", "1897", 0.26, (mx, 0.2, H + 0.78), (math.pi / 2, 0, math.pi), "cf_door", 0.01)
    pts = [(mx + 0.38 * math.cos(2 * math.pi * k / 8 + math.pi / 8), H + 1.65 + 0.38 * math.sin(2 * math.pi * k / 8 + math.pi / 8)) for k in range(8)]
    bm_prism(P["hk_white"], pts, 0.14, 0.2, "xz")                               # the octagonal window
    bm_prism(P["glass"], [(mx + 0.28 * math.cos(2 * math.pi * k / 8 + math.pi / 8), H + 1.65 + 0.28 * math.sin(2 * math.pi * k / 8 + math.pi / 8)) for k in range(8)], 0.2, 0.22, "xz")
    # the oval blade sign beside the door, on a scrolled bracket
    bx = bays[1][1] - 0.05
    bm_box(P["iron"], bx - 0.03, bx + 0.03, 0.1, 1.1, 3.6, 3.66)
    bm_box(P["iron"], bx - 0.015, bx + 0.015, 0.1, 0.14, 3.2, 3.66)
    for r_, mat in ((1.0, "hk_teal"), (0.88, "t_cream")):
        bm_lathe(P[mat], [(0, -0.03), (1.0, -0.03), (1.0, 0.03), (0, 0.03)], 20,
                 T(bx, 0.7, 2.75) @ R(math.pi / 2, "Y") @ _diag2(0.42 * r_, 0.55 * r_))
    text(f"ST_WBZ_hk_{name}_blade", "HOKUSAI", 0.12, (bx, 0.74, 2.75), (math.pi / 2, 0, math.pi / 2), "hk_teal", 0.01)
    # ---- the inside
    x0, x1 = 0.2, w - 0.2
    bm_box(P["hk_floor"], x0, x1, -D, -0.3, 0.0, 0.05)
    bm_box(P["hk_floor"], bays[1][0] + 0.3, bays[1][1] - 0.3, -0.35, 0.6, 0.0, 0.05)             # the doorstep (across the wall's thickness)
    for a, b_, c0, c1 in ((x0, x0 + 0.15, -D, -0.3), (x1 - 0.15, x1, -D, -0.3), (x0, x1, -D - 0.15, -D)):
        bm_box(P["hk_wall"], a, b_, c0, c1, 0.05, top)
        bm_box(P["cf_door"], a, b_, c0, c1, 0.05, 0.9)                                          # the dark wainscot
        bm_box(P["cf_door"], a, b_, c0, c1, top - 0.15, top)
    bm_box(P["hk_wall"], x0, x1, -D - 0.15, -0.3, top, top + 0.15)
    bm_box(P["display"], x0 + 0.5, x1 - 0.5, -D + 0.1, -0.6, top - 0.1, top)                    # a lit ceiling cove
    # gold folding screens with the Great Wave, along the back wall and the left wall
    def screen(xa_, xb_, y, face_y, n=4):
        pw_ = (xb_ - xa_) / n
        for k in range(n):
            sx = xa_ + k * pw_
            off = 0.0 if k % 2 == 0 else 0.12
            bm_box(P["hk_gold"], sx + 0.02, sx + pw_ - 0.02, y + off, y + off + 0.04, 0.1, 2.0)
            bm_box(P["cf_door"], sx, sx + pw_, y + off - 0.01, y + off + 0.05, 0.08, 0.12)
            bm_box(P["cf_door"], sx, sx + pw_, y + off - 0.01, y + off + 0.05, 1.98, 2.02)
        # the wave: stepped blue crest on the lower right panels
        for k, hgt in enumerate((0.5, 0.9, 1.3, 1.1)):
            bm_box(P["hk_wave"], xa_ + (k + 0.1) * pw_, xa_ + (k + 0.9) * pw_, y + 0.05, y + 0.07, 0.15, 0.15 + hgt)
    screen(x0 + 1.0, x1 - 1.0, -D + 0.05, 0.0, 6)
    bm_box(P["cf_door"], (x0 + x1) / 2 - 0.55, (x0 + x1) / 2 + 0.55, -D + 0.02, -D + 0.07, 1.45, 2.15)    # the framed Red Fuji
    bm_box(P["hk_red"], (x0 + x1) / 2 - 0.4, (x0 + x1) / 2 + 0.4, -D + 0.07, -D + 0.08, 1.55, 2.05)
    # low tables and cushions
    for tx in (x0 + 1.4, (x0 + x1) / 2, x1 - 1.4):
        for ty in (-2.6, -4.4):
            if abs(tx - w / 2) < 0.8 and ty > -3.5:
                continue                                                                         # (the way in from the door)
            bm_box(P["cf_door"], tx - 0.55, tx + 0.55, ty - 0.4, ty + 0.4, 0.68, 0.75)
            for sx_, sy_ in ((-0.5, -0.35), (0.5, -0.35), (-0.5, 0.35), (0.5, 0.35)):
                bm_box(P["cf_door"], tx + sx_ - 0.03, tx + sx_ + 0.03, ty + sy_ - 0.03, ty + sy_ + 0.03, 0.05, 0.68)
            for sx_ in (-0.9, 0.9):
                bm_box(P["cf_seat"], tx + sx_ - 0.22, tx + sx_ + 0.22, ty - 0.22, ty + 0.22, 0.36, 0.5)
                bm_box(P["cf_door"], tx + sx_ - 0.02, tx + sx_ + 0.02, ty - 0.2, ty + 0.2, 0.05, 0.36)
    P.flush(f"hokusai_{name}", smooth=())
