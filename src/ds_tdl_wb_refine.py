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

try:
    import bmesh
except ImportError:
    bmesh = None

from ds_tdl_station import bm_box, bm_lathe, bm_prism, obj_bm, T, R, globe_lamp_bm, text, _principled, arch_band, arch_opening, seg_arc, column_bm
from ds_tdl_entrance import frame


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
HS_EDGES = {"bluegrey": (50.9, -100.45), "hs": (49.95, -107.75), "hs2": (40.65, -112.8), "cobalt": (32.4, -111.45)}
HS_CORNER = (47.4, -113.9)


def home_store_kind(mid, L):
    """Which of the block's outer edges this is (by its mid point, WB): the R2-28 brick faces south of y -98.5, then
    (wb2 HS2, from the Waffle Company north) the blue-grey panelled front, Home Store's cream round the corner, and
    beside the Refreshment Corner (wb2 BL1) the cobalt shop."""
    if mid[0] > 45.0 and -98.5 < mid[1] < -77.0 and L > 4.0:
        return "brick"
    for k, p in HS_EDGES.items():
        if math.hypot(mid[0] - p[0], mid[1] - p[1]) < 1.0:
            return k
    if L < 2.0 and math.hypot(mid[0] - HS_CORNER[0], mid[1] - HS_CORNER[1]) < 2.2:
        return "corner"
    return None


def scallop_hood(P, a, b, z, d=0.6):
    """A maroon hood over a window, sloping out d m from z+0.4 to z, with a white scalloped edge (wb1 X5, wb2 HS1)."""
    bm_prism(P["aw_maroon"], [(0.0, z + 0.4), (d, z), (d, z - 0.1), (0.0, z + 0.3)], a, b, "yz")
    n = max(2, round((b - a) / 0.28))
    for k in range(n):
        xa, xb = a + (b - a) * k / n, a + (b - a) * (k + 1) / n
        bm_prism(P["aw_white"], [(xa + (xb - xa) * (1 - j / 6), z - 0.1 - 0.1 * math.sin(math.pi * j / 6)) for j in range(7)], d - 0.03, d, "xz")


def oval_board(P, mat, rim, x, y, z, a, b):
    """An oval board a x b (half axes) facing +y at (x, y, z) with a rim."""
    bm_lathe(P[rim], [(0, 0), (1.0, 0), (1.0, 0.05), (0, 0.05)], 28, T(x, y, z) @ _diag(a + 0.08, b + 0.08) @ R(-math.pi / 2, "X"))
    bm_lathe(P[mat], [(0, 0), (1.0, 0), (1.0, 0.05), (0, 0.05)], 28, T(x, y + 0.04, z) @ _diag(a, b) @ R(-math.pi / 2, "X"))


def _diag(a, b):
    from mathutils import Matrix
    return Matrix.Diagonal((a, 1.0, b, 1.0))


def home_store_face(name, L, H, kind, outer_run, rng):
    """One outer edge of the block (x 0 .. L, +y out): outer_run's wall in the face's colour, then its extras --
    hs / hs2: Home Store's cream (wb1 #E8DCC0) with rose panels under the upper windows, white medallions, maroon
    scalloped hoods over them; on hs (by the OSM point) the navy oval board with a gold rim and letters (wb1 X5), on hs2
    the maroon-purple one with cream letters "HOME STORE / FROM MARCELINE'S TO YOU" (wb2 HS1). bluegrey: a small navy
    HOME STORE plaque (wb1 X5). cobalt: the bay window with curved glass and the door under a blue-grey half dome
    (wb2 BL1)."""
    wall = {"bluegrey": "w_bluegrey", "cobalt": "w_cobalt"}.get(kind, "w_hs_cream")
    outer_run(name, L, H, wall, "t_white", rng)
    P = Parts()
    nb = max(1, round(L / 4.0)) if L >= 2.5 else 0
    bays = [(L * k / nb, L * (k + 1) / nb) for k in range(nb)]
    ms = [(a + b) / 2 for a, b in bays if b - a > 2.2]
    if kind in ("hs", "hs2"):
        for m in ms:
            scallop_hood(P, m - 0.72, m + 0.72, 6.85)
            bm_box(P["w_pink"], m - 0.55, m + 0.55, 0.0, 0.04, 4.02, 4.4)
        for a, b in bays[1:]:
            bm_lathe(P["t_white"], [(0, 0), (0.26, 0), (0.26, 0.05), (0, 0.05)], 16, T(a, 0.0, 7.25) @ R(-math.pi / 2, "X"))
    if kind == "hs":
        sx = L - 2.4
        oval_board(P, "hs_navy", "brass", sx, 0.3, 3.4, 1.75, 0.5)
        text(f"ST_WBZ_{name}_homestore", "HOME STORE", 0.36, (sx, 0.4, 3.4), (math.pi / 2, 0, math.pi), "brass", 0.02)
    if kind == "hs2" and ms:
        sx = (bays[0][1] if len(bays) > 1 else L / 2)
        oval_board(P, "hs_plum", "t_cream", sx, 0.05, 5.55, 0.95, 0.55)
        text(f"ST_WBZ_{name}_homestore2", "HOME STORE", 0.24, (sx, 0.15, 5.65), (math.pi / 2, 0, math.pi), "t_cream", 0.015)
        text(f"ST_WBZ_{name}_marceline", "FROM MARCELINE'S TO YOU", 0.075, (sx, 0.15, 5.33), (math.pi / 2, 0, math.pi), "t_cream", 0.01)
    if kind == "bluegrey":
        bm_box(P["hs_navy"], L / 2 - 0.65, L / 2 + 0.65, 0.12, 0.17, 3.2, 3.6)
        bm_box(P["brass"], L / 2 - 0.7, L / 2 + 0.7, 0.1, 0.15, 3.16, 3.64)
        text(f"ST_WBZ_{name}_homestore3", "HOME STORE", 0.14, (L / 2, 0.19, 3.4), (math.pi / 2, 0, math.pi), "brass", 0.01)
        for a, b in bays:                                 # the panelled front: raised white frames between the windows
            for x0 in (a + 0.45, b - 0.75):
                if b - a > 2.2:
                    bm_box(P["t_white"], x0, x0 + 0.3, 0.0, 0.05, 4.4, 6.6)
    if kind == "cobalt" and len(ms) >= 2:
        m = ms[0]                                         # the bay window, its glass curving round the corners
        ring = lambda rx, ry: [(m + rx * math.cos(math.pi * j / 10), ry * math.sin(math.pi * j / 10)) for j in range(11)][::-1]
        bm_prism(P["w_cobalt"], ring(1.45, 0.8), 0.0, 0.55, "xy")
        bm_prism(P["win_dark"], ring(1.38, 0.72), 0.55, 2.85, "xy")
        bm_prism(P["w_cobalt"], ring(1.5, 0.85), 2.85, 3.15, "xy")
        bm_prism(P["t_white"], ring(1.55, 0.9), 3.15, 3.22, "xy")
        for j in range(1, 10, 2):
            a = math.pi * j / 10
            x, y = m + 1.41 * math.cos(a), 0.75 * math.sin(a)
            bm_box(P["t_white"], x - 0.03, x + 0.03, y - 0.03, y + 0.03, 0.55, 2.85)
        m = ms[1]                                         # the door, its blue-grey half dome
        bm_box(P["door"], m - 0.65, m + 0.65, 0.12, 0.18, 0.06, 2.6)
        for x0, x1 in ((m - 0.8, m - 0.65), (m + 0.65, m + 0.8)):
            bm_box(P["w_cobalt"], x0, x1, 0.1, 0.22, 0.0, 2.75)
        bm_box(P["w_cobalt"], m - 0.8, m + 0.8, 0.1, 0.22, 2.6, 2.75)
        half_dome(P["w_bluegrey"], m, 0.0, 2.95, 0.95, 0.7)
    P.flush(name + "_hs", smooth=("lamp", "w_bluegrey"))


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


def home_store_corner():
    """wb1 X5 (0:08:22 .. 0:08:34), wb2 HS1 (0:02:00 .. 0:02:14), R2-28 (v2 7:12 .. 7:16): Home Store's round corner
    porch -- four white round columns (0.35 m) on a fan of steps, an entablature and flat roof, globe lamps over the
    middle columns -- and the small clock turret on the roof over the corner. WB frame."""
    P = Parts()
    cx, cy, Rc = 46.5, -112.0, 4.0
    angs = [-20.0, -48.0, -76.0, -104.0]
    fan = lambda r: [(cx, cy)] + [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in
                                  [-14.0 - 96.0 * k / 12 for k in range(13)]]
    bm_prism(P["t_cream"], fan(Rc + 0.45), 0.0, 0.1, "xy")                          # the step
    for a in angs:
        x, y = cx + Rc * math.cos(math.radians(a)), cy + Rc * math.sin(math.radians(a))
        bm_box(P["t_white"], x - 0.28, x + 0.28, y - 0.28, y + 0.28, 0.1, 0.6)
        column_bm(P["t_white"], x, y, 0.6, 2.95, 0.175, 12)
    bm_prism(P["t_white"], fan(Rc + 0.35), 3.55, 3.85, "xy")                        # entablature and roof
    bm_prism(P["t_cream"], fan(Rc + 0.5), 3.85, 3.97, "xy")
    for a in angs[1:3]:
        x, y = cx + (Rc + 0.1) * math.cos(math.radians(a)), cy + (Rc + 0.1) * math.sin(math.radians(a))
        bm_lathe(P["brass"], [(0, 0), (0.08, 0), (0.05, 0.3), (0.1, 0.38), (0, 0.4)], 8, T(x, y, 3.97))
        globe_lamp_bm(P["lamp"], x, y, 4.55, 0.2)
    tx, ty, z0 = 46.0, -112.3, 8.5                        # the clock turret (wb2 HS1)
    bm_box(P["t_white"], tx - 0.7, tx + 0.7, ty - 0.7, ty + 0.7, z0, z0 + 2.1)
    bm_box(P["t_cream"], tx - 0.8, tx + 0.8, ty - 0.8, ty + 0.8, z0 + 2.1, z0 + 2.25)
    for M_ in (T(tx + 0.7, ty, z0 + 1.35) @ R(math.pi / 2, "Y"), T(tx, ty - 0.7, z0 + 1.35) @ R(math.pi / 2, "X")):
        bm_lathe(P["brass"], [(0, -0.03), (0.47, -0.03), (0.47, 0.03), (0, 0.03)], 20, M_)
        bm_lathe(P["clock"], [(0, -0.05), (0.4, -0.05), (0.4, 0.05), (0, 0.05)], 20, M_)
    bm_lathe(P["shingle"], [(0, 0), (0.78, 0), (0.72, 0.3), (0.5, 0.62), (0.22, 0.82), (0, 0.88)], 12, T(tx, ty, z0 + 2.25))
    bm_lathe(P["brass"], [(0, 0), (0.06, 0), (0.03, 0.5), (0, 0.55)], 6, T(tx, ty, z0 + 3.1))
    P.flush("hs_corner", smooth=("lamp",))


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
