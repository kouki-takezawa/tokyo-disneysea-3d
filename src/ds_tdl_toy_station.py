"""東京ディズニーランド トイ・ステーション -- the toy shop's two entrances and the hall between them (Blender 5.2).

Called from ds_tdl_world_bazaar (build_shops: SPECIAL[("ASW", 0)] -> small_front; build_block_walls: the west face of
the OSM block 72216845 -> big_front). Plain helpers on ds_tdl_station; nothing here imports ds_tdl_world_bazaar.

Sources (refine_R2.md "追加 A: トイ・ステーション"; looked at only, nothing copied into the repository):
  * The user's photos images/toy_station/ts1..ts8 (they come before the video):
    - ts2, ts3: the small entrance on Center Street -- olive-cream wall, white panelled pilasters and wainscot, maroon
      scalloped awnings with a white wavy edge either side, the cream frieze of blue eight-pointed stars and triangles
      above them, two display windows (striped circus tents on pale blue stands), blue-framed glass doors in a recess
      with an amber pendant, the arched navy sign "TOY STATION" in an orange bulb-lined frame with the tin rocket and
      Pluto, two slim pale-blue striped towers with red rings, cream turrets, domes and red pennants.
    - ts1, ts4, ts5, ts6: the big entrance outside, on the block's west face -- two thick yellow columns on red bases
      with red rings, pale blue-and-white striped shafts above, cream turrets, red caps and pennants; between them the
      teal sign board curving out, "TOY" in yellow with blue shadows and "STATION" in red; the arch over it with the
      rocket in a starry navy sky; blue-framed glass doors in a deep recess; the peach wall with red and teal bands and
      a cream-yellow parapet; to the left the ribbed peach canopy on yellow columns over teal-framed display windows;
      to the right a peach planter with a clipped hedge and palms.
    - ts7, ts8: inside -- an orange-peach ceiling on blue-grey beams with blue arched beams over the aisle, cream
      chandeliers, octagon-and-square tiles in brown, orange and cream, cream walls with white roller-blind windows,
      grey-green double-sided gondolas with ball finials and roundels, red-edged wall shelves, the counter with a
      brick-patterned front and a black top with a white "track", clear screens on it.
  * Position (WEB): the OSM point "トイ・ステーション" WB(-45.6, -77.5) in 72216845's western jut; the west face
    (-58.7, -70.5) -> (-54.5, -84.3) is the outside wall; the small entrance is the first 14 m of Center Street's
    south-west arm (ASW) from (-55.4, -69.5).

ESTIMATES: every size (from people and doors in the photos, +-15 %); the big entrance's place along the face (refine_R2.md
T2: WB (-56.1, -79.1)); the hall's size (the block between the two fronts); the colours are read by eye.
"""
import math

try:
    import bmesh
    from mathutils import Matrix
except ImportError:
    bmesh = Matrix = None

import ds_tdl_station as ST
from ds_tdl_station import (bm_box, bm_prism, bm_lathe, obj_bm, T, R, seg_arc, arch_opening, globe_lamp_bm, text, _principled)

BIG_DOOR = (-56.1, -79.1)          # WB: the big entrance's centre on the west face (refine_R2.md T2)
WEST_FACE = ((-58.7, -70.5), (-54.5, -84.3))
HALL_BACK = -13.0                  # the hall's back wall (ASW-local y)
HALL_EAST = 13.6                   # the hall's east wall (ASW-local x); the next shop starts at 14.0

# key: (Blender linear colour, roughness, extra) -- the web colours (sRGB by eye) are in mock_template.html MODEL_MAT
COLOURS = {
    "ts_wall": (0.64, 0.54, 0.31), "ts_panel": (0.83, 0.77, 0.61), "ts_plinth": (0.30, 0.26, 0.19), "ts_groove": (0.50, 0.42, 0.23),
    "aw_mauve": (0.22, 0.02, 0.06), "ts_star": (0.05, 0.22, 0.46), "ts_frame": (0.17, 0.13, 0.05), "ts_door": (0.10, 0.30, 0.49),
    "ts_orange": (0.87, 0.31, 0.02), "ts_navy": (0.01, 0.01, 0.10), "ts_letter": (0.75, 0.58, 0.26), "ts_rocket": (0.87, 0.58, 0.05),
    "ts_stripe": (0.38, 0.58, 0.68), "ts_red": (0.39, 0.01, 0.01), "ts_yellow": (0.75, 0.51, 0.16), "ts_stripe2": (0.58, 0.72, 0.83),
    "ts_board": (0.05, 0.31, 0.28), "ts_dots": (0.30, 0.64, 0.51), "ts_toy": (0.87, 0.46, 0.02), "ts_shadow": (0.01, 0.10, 0.40),
    "ts_station": (0.43, 0.01, 0.03), "ts_peach": (0.83, 0.43, 0.31), "ts_parapet": (0.91, 0.75, 0.35), "ts_teal": (0.02, 0.26, 0.26),
    "ts_canopy": (0.87, 0.51, 0.35), "ts_stand": (0.31, 0.58, 0.75),
    # inside (ts7, ts8)
    "ts_ceiling": (0.83, 0.26, 0.08), "ts_beam": (0.11, 0.22, 0.41), "ts_inwall": (0.83, 0.68, 0.35), "ts_gondola": (0.38, 0.46, 0.30),
    "ts_brick": (0.61, 0.13, 0.06), "ts_blind": (0.93, 0.92, 0.88), "ts_base": (0.08, 0.05, 0.03),
}


def materials(M):
    for k, c in COLOURS.items():
        M[k] = _principled(f"st_wbz_{k}", c, 0.6)[0]
    M["ts_floor"] = ST.mat_tiles("st_wbz_ts_floor", (0.68, 0.22, 0.05), (0.20, 0.05, 0.02), 0.5, (0.75, 0.55, 0.31))
    return M


class Parts(dict):
    """bmesh per material, made on first use; flush() makes one object per material."""
    def __missing__(self, k):
        self[k] = bmesh.new()
        return self[k]

    def flush(self, name):
        for k, bm_ in self.items():
            if len(bm_.verts):
                obj_bm(f"ST_WBZ_TS_{name}_{k}", bm_, k, smooth=k in ("lamp", "bulb", "ts_rocket", "topiary"))
            else:
                bm_.free()


def star8(cx, cz, r0, r1):
    return [(cx + (r1 if k % 2 == 0 else r0) * math.cos(math.pi * k / 8 + math.pi / 2),
             cz + (r1 if k % 2 == 0 else r0) * math.sin(math.pi * k / 8 + math.pi / 2)) for k in range(16)]


def scallops(P, key, x0, x1, y, z, step=0.35, depth=0.18):
    """A wavy edge hanging from z: half discs every `step`, in the xz plane at y."""
    n = max(1, round((x1 - x0) / step)); s = (x1 - x0) / n
    for k in range(n):
        c = x0 + s * (k + 0.5)
        pts = [(c - s / 2, z)] + [(c - s / 2 * math.cos(math.pi * j / 6), z - depth * math.sin(math.pi * j / 6)) for j in range(1, 6)] + [(c + s / 2, z)]
        bm_prism(P[key], pts, y, y + 0.03, "xz")


def tower(P, x, y, z0, r, h, turret_h, flag):
    """A striped round tower (ts1, ts2): red ring, striped shaft, red ring, cream turret with a window, red band or cap,
    pale blue dome (small) or red cap (big), a flagpole and a red pennant."""
    bm_lathe(P["ts_red"], [(0, 0), (r * 1.18, 0), (r * 1.18, 0.18 + r * 0.2), (0, 0.18 + r * 0.2)], 16, T(x, y, z0))
    z = z0 + 0.18 + r * 0.2
    bm_lathe(P["ts_stripe2" if r > 0.4 else "ts_stripe"], [(0, 0), (r, 0), (r, h), (0, h)], 16, T(x, y, z))
    for k in range(8):                                    # the white stripes
        a = 2 * math.pi * k / 8
        bm_box(P["ts_panel"], x + r * math.cos(a) - 0.03, x + r * math.cos(a) + 0.03, y + r * math.sin(a) - 0.03, y + r * math.sin(a) + 0.03, z, z + h)
    z += h
    bm_lathe(P["ts_red"], [(0, 0), (r * 1.18, 0), (r * 1.18, 0.2 + r * 0.2), (0, 0.2 + r * 0.2)], 16, T(x, y, z))
    z += 0.2 + r * 0.2
    rt = r * 0.9
    bm_lathe(P["ts_panel"], [(0, 0), (rt, 0), (rt, turret_h), (0, turret_h)], 12, T(x, y, z))
    bm_prism(P["glass"], arch_opening(x - rt * 0.35, x + rt * 0.35, z + turret_h * 0.25, z + turret_h * 0.65, rt * 0.35, 8), y + rt, y + rt + 0.02, "xz")
    z += turret_h
    if r > 0.4:                                           # the big towers: a red cap
        bm_lathe(P["ts_red"], [(0, 0), (rt * 1.15, 0), (rt * 1.15, 0.1), (rt * 0.5, 0.4), (0, 0.42)], 12, T(x, y, z)); z += 0.4
    else:
        bm_lathe(P["ts_red"], [(0, 0), (rt * 1.1, 0), (rt * 1.1, 0.1), (0, 0.1)], 12, T(x, y, z)); z += 0.1
        bm_lathe(P["ts_stripe"], [(0, 0), (rt * 1.05, 0), (rt * 0.7, 0.18), (0, 0.3)], 12, T(x, y, z)); z += 0.28
    bm_box(P["iron"], x - 0.02, x + 0.02, y - 0.02, y + 0.02, z, z + flag[0] + 0.1)
    bm_prism(P["ts_red"], [(x + 0.02, z + flag[0]), (x + 0.02 + flag[1], z + flag[0] - flag[2] / 2), (x + 0.02, z + flag[0] - flag[2])], y - 0.01, y + 0.01, "xz")


def rocket(P, x, y, z, L, ang=0.25):
    """The tin rocket (yellow, a red fin and window) with Pluto on it, lying along x tilted up by ang, in the xz plane."""
    r = L * 0.13
    M_ = T(x, y, z) @ R(ang, "Y") @ R(math.pi / 2, "Y")       # lathe axis (z) -> along +x
    bm_lathe(P["ts_rocket"], [(0, -L / 2), (r * 0.7, -L / 2), (r, -L * 0.3), (r, L * 0.15), (r * 0.6, L * 0.38), (0, L / 2)], 12, M_)
    bm_lathe(P["ts_red"], [(0, -L / 2 - 0.12 * L), (r * 0.5, -L / 2 - 0.12 * L), (r * 0.7, -L / 2), (0, -L / 2)], 10, M_)
    for s in (-1, 1):
        bm_prism(P["ts_red"], [(x - L * 0.45, z), (x - L * 0.25, z), (x - L * 0.55, z + s * r * 1.6)], y - 0.02, y + 0.02, "xz")
    globe_lamp_bm(P["m_brown"], x + L * 0.05, y, z + r * 1.3, r * 0.75)       # Pluto's head, ears
    bm_box(P["m_black"], x + L * 0.05 - r * 0.7, x + L * 0.05 - r * 0.4, y - 0.03, y + 0.03, z + r * 0.7, z + r * 1.6)


def bulb_frame(P, cx, z0, spring, w, rise, y, step=0.3):
    """White round bulbs round an arched frame (the sides from z0 up, then the arch)."""
    for x in (cx - w / 2, cx + w / 2):
        z = z0 + 0.15
        while z < spring:
            globe_lamp_bm(P["bulb"], x, y, z, 0.06); z += step
    pts, _ = seg_arc(cx, spring, w, rise, max(5, int(math.pi * rise / step)))
    for x, z in pts:
        globe_lamp_bm(P["bulb"], x, y, z, 0.06)


def double_doors(P, x0, x1, y, h, swing=-1):
    """Blue-framed glass double doors at y, both leaves swung open (towards +y*swing ... inwards), steel push bars."""
    w = (x1 - x0) / 2
    for k, hx in enumerate((x0, x1)):
        s = 1 if k == 0 else -1
        # an open leaf: a frame round glass, standing at the jamb, turned 90 deg
        y0, y1 = sorted((y, y + swing * w * 0.95))
        bm_box(P["ts_door"], hx + s * 0.02 - 0.04, hx + s * 0.02 + 0.04, y0, y1, 0.0, h)
        bm_box(P["shopglass"], hx + s * 0.02 - 0.045, hx + s * 0.02 + 0.045, y0 + 0.1, y1 - 0.1, 0.25, h - 0.15)
        for zz in (1.0, 1.15):
            bm_box(P["icc_steel"], hx + s * 0.02 - 0.07, hx + s * 0.02 + 0.07, y0 + 0.2, y0 + 0.6, zz, zz + 0.03)


# ------------------------------------------------------------------------------------------------- T1 the small entrance
def small_front(name, w, p0, ang):
    """ts2, ts3 (refine_R2.md T1): the front on Center Street, x 0..w (14 m) along the street, +y the street. It also
    closes the 3.3 m corner piece back to the block's west corner (x -3.3 .. 0) and builds the hall behind (T3)."""
    P = Parts()
    X0, H = -3.3, 9.0
    win = ((2.2, 4.1), (9.9, 11.8)); door = (5.9, 8.1)
    # the wall, with the openings
    bm_box(P["ts_wall"], X0, w, -0.4, 0.0, 2.9, H)
    for a, b_ in ((X0, win[0][0]), (win[0][1], door[0]), (door[1], win[1][0]), (win[1][1], w)):
        bm_box(P["ts_wall"], a, b_, -0.4, 0.0, 0.0, 2.9)
    for a, b_ in win:
        bm_box(P["ts_wall"], a, b_, -0.4, 0.0, 0.0, 0.9)
    for a, b_ in ((X0, door[0]), (door[1], w)):           # (not across the door: a 0.5 m face would stop the walk)
        bm_box(P["ts_plinth"], a, b_, 0.0, 0.05, 0.0, 0.5)
    bm_box(P["ts_plinth"], door[0], door[1], -1.1, 0.0, 0.0, 0.02)
    for a, b_ in win:                                     # white wainscot under the windows
        bm_box(P["ts_panel"], a - 0.15, b_ + 0.15, 0.0, 0.07, 0.5, 0.9)
        for k in range(4):
            xa = a + (b_ - a) * k / 4 + 0.06
            bm_box(P["ts_panel"], xa, xa + (b_ - a) / 4 - 0.12, 0.07, 0.09, 0.56, 0.84)
    for xa in (-0.6, 1.3, 4.35, 9.15, 12.2, w - 0.45):    # white panelled pilasters
        bm_box(P["ts_panel"], xa, xa + 0.6 if xa < w - 0.5 else w, 0.0, 0.08, 0.5, 3.0)
        bm_box(P["ts_panel"], xa + 0.12, xa + 0.48 if xa < w - 0.5 else w - 0.1, 0.08, 0.1, 0.8, 2.7)
    # the display windows: frames, glass, the circus tent on its pale blue stand, a gold curtain
    for a, b_ in win:
        m = (a + b_) / 2
        for x0_, x1_ in ((a - 0.15, a), (b_, b_ + 0.15)):
            bm_box(P["ts_frame"], x0_, x1_, -0.1, 0.06, 0.9, 2.9)
        bm_box(P["ts_frame"], a - 0.15, b_ + 0.15, -0.1, 0.12, 0.84, 0.9)
        bm_box(P["ts_frame"], a - 0.15, b_ + 0.15, -0.1, 0.06, 2.9, 3.05)
        bm_box(P["ts_frame"], m - 0.03, m + 0.03, -0.1, 0.0, 0.9, 2.9)
        bm_box(P["shopglass"], a, b_, -0.06, -0.04, 0.9, 2.9)
        bm_box(P["ts_stand"], m - 0.7, m + 0.7, -0.75, -0.25, 0.9, 1.25)
        bm_lathe(P["m_red"], [(0, 0), (0.62, 0), (0.62, 0.45), (0.1, 1.0), (0, 1.05)], 12, T(m, -0.6, 1.25))
        for k in range(6):                                # the tent's cream stripes
            a_ = 2 * math.pi * k / 6
            bm_box(P["m_white"], m + 0.6 * math.cos(a_) - 0.08, m + 0.6 * math.cos(a_) + 0.08, -0.6 + 0.6 * math.sin(a_) - 0.08,
                   -0.6 + 0.6 * math.sin(a_) + 0.08, 1.25, 1.72)
        bm_box(P["ts_rocket"], a + 0.02, b_ - 0.02, -0.3, -0.2, 2.55, 2.88)
        bm_box(P["display"], a, b_, -1.1, -1.05, 0.9, 2.9)
    # the door recess (0.7 m behind the wall face, open into the hall), its amber pendant
    for x0_, x1_ in ((door[0] - 0.15, door[0]), (door[1], door[1] + 0.15)):
        bm_box(P["ts_wall"], x0_, x1_, -1.1, 0.0, 0.0, 2.9)
    bm_box(P["ts_panel"], door[0], door[1], -1.1, -0.4, 2.85, 2.9)
    bm_lathe(P["lamp"], [(0, 0), (0.06, 0), (0.18, 0.18), (0, 0.2)], 8, T((door[0] + door[1]) / 2, -0.75, 2.62))
    double_doors(P, door[0] + 0.05, door[1] - 0.05, -1.1, 2.5, swing=-1)
    bm_box(P["ts_door"], door[0], door[1], -1.15, -1.05, 2.5, 2.85)
    # the scalloped maroon awnings (wall z 3.6, tip z 3.0, 1.2 m out), the white wavy edge
    for a, b_ in ((X0, 5.2), (8.8, w)):
        bm_prism(P["aw_mauve"], [(0.0, 3.6), (1.2, 3.0), (1.2, 2.94), (1.16, 2.94), (1.16, 3.0), (0.0, 3.55)], a, b_, "yz")
        scallops(P, "t_white", a, b_, 1.2, 3.0)
        for x in (a + 0.02, b_ - 0.02):                   # the side cheeks
            bm_prism(P["aw_mauve"], [(0.0, 3.6), (1.2, 3.0), (0.0, 3.0)], x - 0.01, x + 0.01, "yz")
    # the frieze: cream with blue eight-pointed stars and triangles, blue fillets (not behind the sign's arch)
    bm_box(P["t_cream"], X0, w, 0.0, 0.05, 4.0, 5.2)
    for zb in (4.0, 5.14):
        bm_box(P["ts_star"], X0, w, 0.05, 0.08, zb, zb + 0.06)
    x = X0 + 0.7
    while x < w - 0.4:
        if not (4.8 < x < 9.2):
            bm_prism(P["ts_star"], star8(x, 4.6, 0.17, 0.45), 0.05, 0.1, "xz")
            for xt in (x + 0.7,):
                if not (4.8 < xt < 9.2) and xt < w - 0.3:
                    bm_prism(P["ts_star"], [(xt - 0.25, 4.1), (xt + 0.25, 4.1), (xt, 4.53)], 0.05, 0.1, "xz")
                    bm_prism(P["ts_star"], [(xt - 0.25, 5.1), (xt, 4.67), (xt + 0.25, 5.1)], 0.05, 0.1, "xz")
        x += 1.4
    for zg in (6.6, 8.0):                                 # the plain wall above: two grooves, a cap
        bm_box(P["ts_groove"], X0, w, 0.0, 0.03, zg, zg + 0.05)
    bm_box(P["ts_panel"], X0 - 0.05, w, -0.5, 0.08, H, H + 0.15)
    bm_box(P["ts_wall"], X0, w, -1.4, -0.4, H - 0.6, H)  # (the parapet's back, over the block roof)
    # the sign: an orange bulb-lined arched frame, the navy board, the rocket, the letters
    cx = 7.0
    bm_prism(P["ts_orange"], arch_opening(5.2, 8.8, 3.7, 4.8, 1.8, 20), 0.15, 0.45, "xz")
    bm_prism(P["ts_navy"], arch_opening(5.45, 8.55, 3.95, 4.8, 1.55, 20), 0.45, 0.48, "xz")
    bm_box(P["ts_rocket"], 5.3, 8.7, 0.45, 0.5, 3.75, 3.9)
    bulb_frame(P, cx, 3.7, 4.8, 3.36, 1.68, 0.47)
    text(f"ST_WBZ_TS_{name}_toy", "TOY", 0.55, (cx, 0.5, 4.95), (math.pi / 2, 0, math.pi), "ts_letter", 0.03)
    text(f"ST_WBZ_TS_{name}_station", "STATION", 0.4, (cx, 0.5, 4.35), (math.pi / 2, 0, math.pi), "ts_letter", 0.03)
    rocket(P, cx + 0.3, 0.55, 5.85, 0.95)
    for sx, sz in ((5.9, 5.4), (8.2, 5.6), (7.9, 6.15), (6.3, 6.05)):   # stars and the moon
        globe_lamp_bm(P["ts_letter"], sx, 0.5, sz, 0.05)
    # the two towers either side of the sign
    for tx in (5.0, 9.0):
        tower(P, tx, 0.4, 3.6, 0.275, 1.45, 0.7, (0.7, 0.55, 0.3))
    P.flush(name)
    interior(name, w)


# ------------------------------------------------------------------------------------------------- T2 the big entrance
def big_front(name, L, H, a, b):
    """ts1, ts4, ts5, ts6 (refine_R2.md T2): the west face (the block-wall frame: x 0..L from a to b, +y out = west)."""
    P = Parts()
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    e = (BIG_DOOR[0] - a[0]) * ux + (BIG_DOOR[1] - a[1]) * uy      # the entrance's centre along the face
    d0, d1 = e - 1.6, e + 1.6; RD = 2.4                   # the opening, the recess's depth
    # the wall: peach, the opening; the cream-yellow parapet; red-over-teal bands
    bm_box(P["ts_peach"], 0, L, -0.4, 0.0, 3.0, H)
    bm_box(P["ts_peach"], 0, d0, -0.4, 0.0, 0.0, 3.0); bm_box(P["ts_peach"], d1, L, -0.4, 0.0, 0.0, 3.0)
    bm_box(P["ts_parapet"], -0.05, L + 0.05, -0.4, 0.06, H, H + 0.8)
    bm_box(P["ts_teal"], -0.05, L + 0.05, -0.45, 0.1, H + 0.8, H + 0.9)
    for zr in (6.55, H + 0.3):
        bm_box(P["ts_teal"], 0, L, 0.0, 0.05, zr, zr + 0.15)
        bm_box(P["ts_station"], 0, L, 0.0, 0.05, zr + 0.2, zr + 0.45)
    bm_box(P["ts_teal"], 0, L, 0.0, 0.06, 0.0, 0.3)
    # the recess: peach cheeks, a dark soffit, the doors at the back into the hall
    for x0_, x1_ in ((d0 - 0.15, d0), (d1, d1 + 0.15)):
        bm_box(P["ts_peach"], x0_, x1_, -RD, 0.0, 0.0, 3.0)
    bm_box(P["ts_beam"], d0, d1, -RD, 0.0, 3.0, 3.15)
    bm_box(P["ts_teal"], d0, d1, -0.1, 0.05, 2.7, 3.0)
    bm_box(P["ts_floor"], d0, d1, -RD, 0.0, 0.0, 0.03)
    double_doors(P, d0 + 0.1, d1 - 0.1, -RD, 2.7, swing=-1)
    bm_box(P["ts_door"], d0, d1, -RD - 0.05, -RD + 0.05, 2.7, 3.0)
    # the two big columns
    for cx in (e - 2.4, e + 2.4):
        bm_lathe(P["ts_red"], [(0, 0), (0.75, 0), (0.75, 0.6), (0.65, 0.7), (0, 0.7)], 20, T(cx, 1.6, 0.0))
        bm_lathe(P["ts_yellow"], [(0, 0), (0.55, 0), (0.55, 3.5), (0, 3.5)], 20, T(cx, 1.6, 0.7))
        for k in range(1, 4):                             # shallow rings on the shaft
            bm_lathe(P["ts_yellow"], [(0, 0), (0.57, 0), (0.57, 0.04), (0, 0.04)], 20, T(cx, 1.6, 0.7 + k * 0.9))
        tower(P, cx, 1.6, 4.2, 0.45, 3.6, 1.0, (1.0, 0.7, 0.4))
    # the sign board, curving out between the columns: teal with pale dots, a blue rim; the letters
    n = 12; yb = lambda x: 1.9 + 0.5 * (1 - ((x - e) / 3.0) ** 2)
    for k in range(n):
        xa, xb = e - 3.0 + 6.0 * k / n, e - 3.0 + 6.0 * (k + 1) / n
        q = [(xa, yb(xa) - 0.15), (xb, yb(xb) - 0.15), (xb, yb(xb)), (xa, yb(xa))]
        bm_prism(P["ts_board"], q, 4.6, 7.0, "xy")
        bm_prism(P["ts_door"], q, 4.5, 4.62, "xy"); bm_prism(P["ts_door"], q, 6.98, 7.1, "xy")
        bm_prism(P["ts_canopy"], [(xa, 0.0), (xb, 0.0), (xb, yb(xb) - 0.15), (xa, yb(xa) - 0.15)], 4.45, 4.5, "xy")   # its soffit
        for j in range(2):                                # the pale dots
            dx_ = xa + (xb - xa) * (j + 0.5) / 2
            for dz in (4.85, 6.75):
                globe_lamp_bm(P["ts_dots"], dx_, yb(dx_), dz, 0.07)
    yf = yb(e) + 0.05
    text(f"ST_WBZ_TS_{name}_toy_sh", "TOY", 1.2, (e + 0.08, yf - 0.05, 5.95), (math.pi / 2, 0, math.pi), "ts_shadow", 0.1)
    text(f"ST_WBZ_TS_{name}_toy", "TOY", 1.2, (e, yf + 0.05, 6.03), (math.pi / 2, 0, math.pi), "ts_toy", 0.1)
    text(f"ST_WBZ_TS_{name}_station_sh", "STATION", 0.55, (e + 0.05, yf - 0.05, 5.0), (math.pi / 2, 0, math.pi), "ts_shadow", 0.06)
    text(f"ST_WBZ_TS_{name}_station", "STATION", 0.55, (e, yf + 0.03, 5.05), (math.pi / 2, 0, math.pi), "ts_station", 0.06)
    # the arch over it: a green-and-gold bulb-lined frame round a starry navy sky with the rocket
    bm_prism(P["ts_rocket"], arch_opening(e - 2.0, e + 2.0, 7.0, 7.2, 2.0, 20), 1.55, 1.75, "xz")
    bm_prism(P["ts_teal"], arch_opening(e - 1.8, e + 1.8, 7.05, 7.2, 1.8, 20), 1.75, 1.8, "xz")
    bm_prism(P["ts_navy"], arch_opening(e - 1.6, e + 1.6, 7.1, 7.2, 1.6, 20), 1.8, 1.83, "xz")
    bulb_frame(P, e, 7.0, 7.2, 3.8, 1.9, 1.8, 0.35)
    rocket(P, e + 0.1, 1.9, 7.9, 1.6)
    for sx, sz in ((-1.1, 7.5), (0.9, 8.6), (1.2, 7.4), (-0.6, 8.7), (-1.3, 8.2)):
        globe_lamp_bm(P["bulb"], e + sx, 1.85, sz, 0.06)
    # to the left (north): the ribbed peach canopy on yellow columns over teal-framed display windows
    c0 = e + 2.4 + 0.75
    if L - c0 > 2.0:
        bm_box(P["ts_canopy"], c0, L, 0.0, 2.4, 3.8, 4.8)
        bm_box(P["ts_teal"], c0, L, 2.4, 2.45, 3.8, 3.95)
        x = c0 + 0.17
        while x < L - 0.1:
            bm_box(P["ts_peach"], x - 0.03, x + 0.03, 2.4, 2.45, 3.95, 4.8); x += 0.35
        for cx in (c0 + (L - c0) * 0.55, L - 0.5):
            bm_lathe(P["ts_yellow"], [(0, 0), (0.45, 0), (0.45, 3.8), (0, 3.8)], 16, T(cx, 2.0, 0.0))
        x = c0 + 0.3
        while x + 3.2 < L - 0.2:                          # windows 3.2 m wide between cream piers
            bm_box(P["ts_teal"], x, x + 3.2, 0.0, 0.1, 0.5, 2.9)
            bm_box(P["win_dark"], x + 0.15, x + 3.05, 0.1, 0.12, 0.65, 2.75)
            bm_box(P["t_cream"], x + 3.2, x + 4.1, 0.0, 0.15, 0.0, 3.8)
            x += 4.1
    # to the right (south): the peach planter, the clipped hedge, two palms
    if d0 - 2.4 > 1.0:
        x1p = d0 - 2.4 - 0.9
        bm_box(P["ts_canopy"], 0.2, x1p, 0.3, 1.5, 0.0, 0.7)
        bm_box(P["hedge"], 0.3, x1p - 0.1, 0.4, 1.4, 0.7, 1.4)
        import ds_tdl_plaza_buildings as PB               # (the palm of the plaza buildings)
        import random
        rng = random.Random(72216845)
        for px in (0.6, max(0.8, x1p - 0.4)):
            PB.palm(P["palm_trunk"], P["palm_leaf"], px, 2.4, rng.uniform(5.0, 6.0), rng.uniform(0, 2 * math.pi), rng, kind="canary")   # the page grows them (plants.js; ts1: drooping feathery fronds)
    # the terracotta walk before it
    bm_box(P["walk"], 0, L, 0.0, 3.0, 0.0, 0.035)
    P.flush(name)


# ------------------------------------------------------------------------------------------------- T3 the hall inside
def west_x(y):
    """The inside face of the west wall at ASW-local y (the face runs from (-3.44, -0.19) to (-2.6, -14.6))."""
    return -3.44 + 0.84 * (-y - 0.19) / 14.41 + 0.4


def interior(name, w):
    """ts7, ts8 (refine_R2.md T3): the hall from the small entrance back to the big one, in the ASW shop frame (x along
    Center Street, -y into the block). Orange-peach ceiling on blue-grey beams, blue arched beams over the aisle,
    chandeliers, octagon-and-square tiles, cream walls, grey-green gondolas, red-edged wall shelves, the brick counter."""
    import random
    P = Parts(); rng = random.Random(4561)
    yb, xe, top = HALL_BACK, HALL_EAST, 4.2
    poly = [(west_x(-0.4), -0.4), (xe, -0.4), (xe, yb), (west_x(yb), yb)]
    bm_prism(P["ts_floor"], poly, 0.0, 0.05, "xy")
    bm_prism(P["ts_ceiling"], poly, top, top + 0.15, "xy")
    bm_box(P["ts_inwall"], west_x(yb) - 0.4, xe + 0.2, yb - 0.2, yb, 0.0, top)           # the back wall
    bm_box(P["ts_inwall"], xe, xe + 0.2, yb, -0.4, 0.0, top)                             # the east wall
    for a, b_ in ((-3.0, 1.9), (4.4, 5.6), (8.4, 9.6), (12.1, xe)):                     # lining of the front wall
        bm_box(P["ts_inwall"], a, b_, -0.45, -0.4, 0.05, top)
    bm_box(P["ts_inwall"], -3.0, xe, -0.45, -0.4, 3.0, top)
    for xx in (2.0, 6.5, 11.0):                           # windows with white roller blinds on the back wall
        bm_box(P["ts_panel"], xx - 0.9, xx + 0.9, yb + 0.0, yb + 0.06, 1.0, 2.8)
        bm_box(P["display"], xx - 0.8, xx + 0.8, yb + 0.06, yb + 0.08, 1.1, 2.1)
        bm_box(P["ts_blind"], xx - 0.8, xx + 0.8, yb + 0.06, yb + 0.12, 2.1, 2.7)
        scallops(P, "ts_blind", xx - 0.8, xx + 0.8, yb + 0.12, 2.1, 0.2, 0.08)
    # the beams: a 3 m grid under the ceiling, blue arched beams across the aisle from the small door
    x = -1.0
    while x < xe:
        bm_box(P["ts_beam"], x - 0.15, x + 0.15, yb, -0.4, top - 0.4, top); x += 3.0
    y = -2.0
    while y > yb:
        bm_box(P["ts_beam"], west_x(y), xe, y - 0.15, y + 0.15, top - 0.4, top); y -= 3.0
    for y in (-3.5, -6.5, -9.5):
        bm_prism(P["ts_beam"], ST.arch_band(5.25, 8.75, 3.0, 0.8, 0.25, 14, leg=3.0), y - 0.15, y + 0.15, "xz")
    for xx in [k * 2.0 - 1.0 for k in range(8)]:          # downlights
        for yy in (-1.5, -3.5, -5.5, -7.5, -9.5, -11.5):
            if xx > west_x(yy) + 0.3:
                bm_lathe(P["lamp"], [(0, 0), (0.06, 0), (0.06, 0.02), (0, 0.02)], 8, T(xx, yy, top - 0.42))
    for cx, cy in ((7.0, -4.5), (7.0, -8.5), (2.0, -9.2)):   # chandeliers: a ring of six white glass flowers
        bm_box(P["brass"], cx - 0.01, cx + 0.01, cy - 0.01, cy + 0.01, top - 1.1, top - 0.4)
        bm_lathe(P["brass"], [(0.35, 0), (0.4, 0), (0.4, 0.04), (0.35, 0.04)], 16, T(cx, cy, top - 1.1))
        for q in range(6):
            a_ = 2 * math.pi * q / 6
            bm_lathe(P["lamp"], [(0, 0), (0.09, 0.04), (0.12, 0.16), (0, 0.12)], 8, T(cx + 0.4 * math.cos(a_), cy + 0.4 * math.sin(a_), top - 1.08))
    # gondolas: grey-green double-sided shelves with ball finials and roundels, toys on four boards
    for gx, gy, rot in ((2.5, -3.5, 0), (10.5, -3.5, 0), (10.5, -7.0, 0), (2.5, -6.0, 0), (10.0, -10.5, 0)):
        bm_box(P["ts_base"], gx - 1.2, gx + 1.2, gy - 0.45, gy + 0.45, 0.0, 0.15)
        bm_box(P["ts_gondola"], gx - 1.15, gx + 1.15, gy - 0.04, gy + 0.04, 0.15, 1.5)
        for sx in (-1, 1):
            bm_box(P["ts_gondola"], gx + sx * 1.15 - 0.08, gx + sx * 1.15 + 0.08, gy - 0.45, gy + 0.45, 0.15, 1.5)
            bm_lathe(P["ts_gondola"], [(0.15, 0), (0.25, 0), (0.25, 0.03), (0.15, 0.03)], 12, T(gx + sx * 1.24, gy, 0.85) @ R(math.pi / 2, "Y"))
            for sy in (-1, 1):
                globe_lamp_bm(P["m_white"], gx + sx * 1.15, gy + sy * 0.4, 1.6, 0.08)
        for zz in (0.35, 0.65, 0.95, 1.25):
            for sy in (-1, 1):
                bm_box(P["ts_panel"], gx - 1.07, gx + 1.07, gy + sy * 0.04, gy + sy * 0.42, zz, zz + 0.03)
                xx = gx - 1.0
                while xx < gx + 0.95:
                    c = rng.choice(("m_red", "m_blue", "m_yellow", "m_red", "m_green", "m_orange"))
                    hh = rng.uniform(0.1, 0.22)
                    bm_box(P[c], xx, xx + 0.16, gy + sy * 0.1, gy + sy * 0.32, zz + 0.03, zz + 0.03 + hh); xx += 0.2
    # red-edged shelves along the east wall
    for zz in (0.4, 0.8, 1.2, 1.6, 2.0):
        bm_box(P["in_wood"], xe - 0.5, xe, -1.6, -11.0, zz, zz + 0.04)
        bm_box(P["m_red"], xe - 0.52, xe - 0.48, -1.6, -11.0, zz - 0.04, zz + 0.04)
        yy = -1.7
        while yy > -10.9:
            bm_box(P[rng.choice(("m_red", "m_pink", "m_blue", "m_yellow"))], xe - 0.42, xe - 0.1, yy - 0.18, yy, zz + 0.04, zz + 0.04 + rng.uniform(0.12, 0.3)); yy -= 0.24
    # the counter: brick-patterned front, black top with the white "track", clear screens; party hats
    cx0, cx1, cy0, cy1 = 4.6, 8.4, -12.2, -11.4
    bm_box(P["ts_brick"], cx0, cx1, cy0, cy1, 0.0, 0.95)
    for zz in (0.25, 0.5, 0.75):
        bm_box(P["t_cream"], cx0, cx1, cy1, cy1 + 0.01, zz, zz + 0.015)
    bm_box(P["m_black"], cx0 - 0.05, cx1 + 0.05, cy0 - 0.05, cy1 + 0.1, 0.95, 1.0)
    for off in (0.25, 0.45):
        bm_box(P["m_white"], cx0, cx1, cy1 - off, cy1 - off + 0.03, 1.0, 1.005)
    bm_box(P["shopglass"], cx0 + 0.2, cx1 - 0.2, cy1 - 0.05, cy1 - 0.02, 1.0, 2.0)
    for k in range(3):
        hx = cx0 + 0.6 + k * 0.5
        bm_lathe(P[("m_blue", "m_green", "m_yellow")[k]], [(0, 0), (0.12, 0), (0, 0.3)], 8, T(hx, cy1 + 0.02, 1.0))
    # a turning rack: white disc foot, clear column, goods
    bm_lathe(P["m_white"], [(0, 0), (0.45, 0), (0.45, 0.05), (0, 0.05)], 16, T(0.8, -2.2, 0.05))
    bm_lathe(P["shopglass"], [(0, 0), (0.25, 0), (0.25, 1.8), (0, 1.8)], 12, T(0.8, -2.2, 0.1))
    for k in range(10):
        a_ = 2 * math.pi * k / 10
        bm_box(P[rng.choice(("m_pink", "m_blue", "m_yellow"))], 0.8 + 0.27 * math.cos(a_) - 0.06, 0.8 + 0.27 * math.cos(a_) + 0.06,
               -2.2 + 0.27 * math.sin(a_) - 0.06, -2.2 + 0.27 * math.sin(a_) + 0.06, 0.4 + (k % 4) * 0.35, 0.55 + (k % 4) * 0.35)
    P.flush(name + "_in")
