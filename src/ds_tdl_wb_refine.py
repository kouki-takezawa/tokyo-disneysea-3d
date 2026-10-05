"""World Bazaar, the re-refinement from the three new walk videos (docs/video_frames/refine_WB.md, stage B, 2026-10-05):
the "large" items 2 .. 4 -- the bridge over the end of Center Street's east arm, Penny Arcade's hall and the corridor
behind the shops (R2-34), Home Store's faces, its corner porch and the cobalt shop beside it. Item 1 (the east arm's
colonnade) is ds_tdl_world_bazaar.arcade_front; the salmon ceilings are ds_tdl_entrance's.

Called from ds_tdl_world_bazaar (build_street, build_shops / shop_interior, build_block_walls); nothing here imports
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
