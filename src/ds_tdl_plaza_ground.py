"""東京ディズニーランドの「プラザ」(ハブ)の地面 -- the ground of the hub between World Bazaar's far exit and Cinderella
Castle's gate (plain Python: shapely + numpy, Blender is not needed; no trees, no round clipped shrubs).

  python src/ds_tdl_plaza_ground.py      # -> output/disneysea/models/tdl_plaza_ground.json (glTF, buffer embedded) + a summary
  python src/export_mock.py              # rebuilds the page; D.models picks the file up ("tdl_plaza_ground", layer ディズニーランド)

Same method as ds_tdl_ground.py (the entrance plaza) and ds_tdl_hotel_ground.py (round the hotel), whose helpers it reuses
(Terrain, Mesh, cdt, top_surface, wall, free_edges, write_gltf); its "planter" idea (curb + a top a little lower) is
reused too, with one addition (a flower ribbon, see below). CLIP (a box, not a fitted outline) is the working area;
ds_ground.py cuts this model's footprint out of the Land's general ground (ZONES["tdl_land_ground"]["cut_models"]),
so nothing is drawn twice.

What is modelled (OSM, plateau_data/disneyland_osm.json):
  paving   every highway=pedestrian area (the round plaza itself has no single way for it in OSM -- it is a soup of
           small pedestrian-area and footway polygons/lines, ways 1307945742 / 1309519858 / 1309519859 / 1283322075
           among many smaller ones) plus footway lines (3.0 m; "Parade Route" 1116305417, wider, 9.0 m, ESTIMATE) and
           the small bridge polygons over the stream (bridge=yes area=yes: they are drawn as ordinary paving, not
           lifted or cut by the water below, e.g. 1283322088/89, 1290633113, 1287531441, 1293447016/30/31/38).
           Gaps left over inside CLIP by the mapped pieces (slivers between polygons, an untagged area=yes/layer=1
           patch at (-459.6, 694.8)) default to paving too, the same "fill" idea as ds_tdl_hotel_ground.py's FILL_BOX,
           but built from all the OSM lines inside CLIP rather than a hand-picked set.
  planters every leisure=garden / landuse=grass,meadow,flowerbed polygon inside CLIP, small and large alike: the
           big lawns (72241312, 217618802, 217730934, 217803066) and every small flower bed, INCLUDING the small
           fenced garden right at the round island's centre (way 71900258, ~13 m across, centred (-426.8, 687.4)) and
           four more round it (1291243499/501/503/505, 21-73 m2) -- together, with the paving between them, these
           make the "radial paving with grass wedges" the aerial photo shows; no wedge shape is invented, they are
           the real OSM beds. A thin ribbon of pale flowers (TP_flower) runs just inside the curb before the green top
           (the castle-garden photo, commons_castle_garden_flowerbed_edge.jpg: a flower edge, no raised curb in the
           photo itself, but a curb is kept here for consistency with the other ground files and because the beds
           double as low barriers guests cannot cross).
  hub      a two-tone ring pattern (like ds_tdl_ground.paving_pattern, but centred on the hub and re-implemented
           locally since that function is hard-wired to the entrance gate) is laid over the paving within
           HUB_PATTERN_R m of HUB_C, for the radiating look; farther out (the approach to World Bazaar and the
           castle) the paving is a single tone.
  left out the statue and its pedestal (phase 4), the stage buildings, street furniture, hedges as 3-D objects (the
           barrier=hedge ways only helped locate bed edges while reading the photo, nothing is built from them),
           the castle forecourt itself: ds_tdl_cinderella.py's build_forecourt() already paves it in detail (the
           compass rose, the ramps) up to about y=649 -- its model footprint is cut out of this one, so this script
           only paves the approach between that and the hub, not the forecourt pattern the task sheet asked about
           (checked: it turned out to already exist).
Centre of the hub (HUB_C): the OSM "Partners" node (1345595271, tourism=artwork) and the "プラザガーデン" node sit at
  about (-456, 750), some 70 m from the round island the aerial photo clearly shows (the radiating garden beds
  above are centred at (-427, 687), confirmed against two more aerial calibration points -- Crystal Palace and
  the Castle forecourt node landed exactly where OSM says once the same pixel<->metre mapping was used). Read as an
  OSM placement error (a single point, not surveyed) and the photo + the bed ways taken as the true centre.
Overlaps avoided: this script cuts its own paving/planters against (a) OSM building polygons inside CLIP (nothing is
  built there yet in the mock for Crystal Palace / Plaza Pavilion / the bandstand -- phase 5 -- but their footprints
  are already real) and (b) the actual exported footprints (model_footprint(), reusing ds_ground.py's function) of
  the models already standing here: cinderella, tdl_world_bazaar, tdl_plaza_buildings, tdl_water, tdl_ground. Using
  the real triangles (not the OSM footprint) means the cut follows what is actually built, including the Ice Cream
  Cones gazebo and the castle's forecourt/bridge/moat, whatever their internal working frames.
Water: not modelled here (ds_tdl_water.py already has these bodies -- W1293446995, W1293447029, W1293447035,
  W1293447036 and more -- in plateau_data/disneyland_water.json, rendered by tdl_water.json/.glb); this script only
  makes sure its own paving does not cover them (except the little bridges, above).
Heights: the same DEM terrain as the other ground files (ds_tdl_ground.Terrain), no flat platform of its own -- HUB_C
  is 232 m from the entrance gate, well outside ds_tdl_ground's own FLAT_R1 (105 m), so that flattening has already
  faded out by here and the DEM is used as is. Not checked against the castle model's own floor height at the seam
  (cinderella.py places its forecourt from a single reference height, not a per-vertex DEM read like this script),
  so there may be a small step right at that cut edge -- not measured.
Mesh: as ds_tdl_ground.py (cells, constrained Delaunay, a 0.15 m skirt on the free edges, except along the cuts).
ESTIMATES: CLIP's box (not fitted to any real outline), the footway/Parade Route widths, the hub pattern's ring
  spacing and radius, the flower ribbon's width and colour, the paving colour (aerial photo, washed out; commons
  photos of the castle gate show a beige/grey stone -- used here for the whole plaza, not just the forecourt).
"""
import sys, math, pathlib

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, polygonize

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ds_disneyland as DL
import ds_tdl_ground as G
import ds_tdl_hotel_ground as H
import ds_ground as GR

OUT = ROOT / "output" / "disneysea" / "models" / "tdl_plaza_ground.json"
CLIP = box(-530.0, 555.0, -345.0, 800.0)          # WB's far exit (-477, 794) to just past the gate GATE (-388.6, 578.2); the west edge
                                                    # reaches -530 (not -495) so the Tomorrowland-ward pedestrian bridge (way 1283322088,
                                                    # highway=pedestrian/bridge=yes/area=yes, x -525.0..-482.1) is inside CLIP whole,
                                                    # not cut in half by the box (phase 6: this was the hub-west seam's cause, see below)
HUB_C = (-427.0, 687.0)                            # the round island's real centre (see docstring); OSM's POI is ~70 m off
HUB_PATTERN_R = 75.0                               # the two-tone ring pattern reaches this far from HUB_C
RING_STEP, RING_ARC, LINE_W = 9.0, 12.0, 0.8       # the ring pattern: spacing, panel arc length, joint-line width (m)
W_FOOT, W_PARADE = 3.0, 9.0                        # footway / Parade Route width (m, ESTIMATES: OSM gives no width here)
FLOWER_W = 0.35                                    # the pale flower ribbon just inside each bed's curb (m)
CUT_MODELS = ("cinderella", "tdl_world_bazaar", "tdl_plaza_buildings", "tdl_water", "tdl_ground")
# Colours by zone (read off Google's satellite view and the user's Crystal Palace photos, 2026-09-30): the island inside
# the parade circle is a pale pinkish beige; the parade circle itself (RING_R) slate asphalt; outside it the paving takes
# the colour of the land it leads to -- red brick towards World Bazaar (the Plaza Garden side), green-grey towards
# Adventureland / Crystal Palace, mauve-brown towards Westernland, grey-lilac towards the castle, blue-grey towards
# Tomorrowland. SECTORS: (key, from, to) plan bearings round HUB_C, split half way between the exits.
RING_R = (47.5, 59.5)
SECTORS = (("wb", 85.0, 155.5), ("adv", 16.0, 85.0), ("west", -47.0, 16.0), ("fan", -117.5, -47.0), ("tom", 155.5, 242.5))
NAMES = ("TP_paving", "TP_paving2", "TP_line", "TP_ring", "TP_curb", "TP_soil", "TP_flower", "TP_edge") + tuple(
    f"TP_paving_{k}{v}" for k, _, _ in SECTORS for v in ("", "2"))


def _closed_polys(pred):
    return [p for p in (Polygon(w["pts"]).buffer(0) for w in DL.DATA["ways"]
                        if w["closed"] and len(w["pts"]) >= 4 and pred(w["tags"]))
            if p.intersects(CLIP) and not p.is_empty]


def _foot_width(t):
    if t.get("name") == "Parade Route":
        return W_PARADE
    try:
        return float(str(t["width"]).replace("m", "").strip())
    except (KeyError, ValueError):
        return W_FOOT


def plan():
    # models already standing here (their real exported footprint) and OSM buildings not modelled yet: no ground under them.
    # tdl_water's footprint is the one CUT_MODELS entry a bridge can legitimately sit over (the others are solid buildings a
    # bridge polygon never overlaps in practice), so it is kept out of `blocked` and subtracted together with the raw OSM
    # water tag below -- both give way to `bridge` (phase 6 fix: the Tomorrowland-ward pedestrian bridge, way 1283322088,
    # used to be cut out here because it sits on top of the tdl_water model's real pond footprint, leaving a hole with no
    # ground on either side of it -- the walk-blocking "step" reported after phase 5 turned out to be this hole, not a
    # height mismatch between tdl_plaza_ground and tdl_land_ground).
    water_solid = GR.model_footprint("tdl_water") or Polygon()
    solid = unary_union([g for g in (GR.model_footprint(m) for m in CUT_MODELS if m != "tdl_water") if g is not None and not g.is_empty])
    buildings = unary_union(_closed_polys(lambda t: "building" in t and t["building"] not in ("roof", "no")))
    blocked = unary_union([solid, buildings])

    water = unary_union(_closed_polys(lambda t: t.get("natural") == "water" or bool(t.get("water"))))
    bridge = unary_union(_closed_polys(lambda t: t.get("highway") == "pedestrian" and t.get("bridge") in ("yes", "viaduct")))
    gardens = unary_union(_closed_polys(lambda t: t.get("leisure") == "garden" or t.get("landuse") in ("grass", "meadow", "flowerbed")))
    pedestrian = unary_union(_closed_polys(lambda t: t.get("highway") == "pedestrian"))

    footways = unary_union([LineString(w["pts"]).buffer(_foot_width(w["tags"]) / 2, cap_style=2, join_style=1)
                            for w in DL.DATA["ways"] if w["tags"].get("highway") == "footway" and len(w["pts"]) >= 2
                            and LineString(w["pts"]).intersects(CLIP)])

    z_paving = unary_union([pedestrian, footways]).intersection(CLIP)
    z_paving = z_paving.difference(blocked).difference(unary_union([water, water_solid]).difference(bridge))

    planters = [q for q in G._polys(gardens.difference(unary_union([blocked, water_solid]))) if q.area >= G.MIN_PLANTER]
    pl_all = unary_union(planters) if planters else Polygon()
    z_paving = z_paving.difference(pl_all)

    # fill: gaps left inside CLIP by the mapped pieces (slivers, the untagged layer=1 patch) default to paving,
    # the same idea as ds_tdl_hotel_ground.py's FILL_BOX but driven by every relevant OSM line inside CLIP
    lines = []
    for w in DL.DATA["ways"]:
        t = w["tags"]
        if len(w["pts"]) < 2 or not LineString(w["pts"]).intersects(CLIP):
            continue
        if (t.get("highway") in ("footway", "pedestrian", "steps") or "building" in t or t.get("barrier")
                or t.get("natural") == "water" or t.get("water") or t.get("leisure") == "garden"
                or t.get("landuse") in ("grass", "meadow", "flowerbed")):
            lines.append(LineString(w["pts"]))
    lines.append(CLIP.exterior)
    faces = [f for f in polygonize(unary_union(lines)) if CLIP.contains(f.representative_point()) and f.area > 1.0]
    built = unary_union([blocked, unary_union([water, water_solid]).difference(bridge), z_paving, pl_all])
    fill_paving, fill_green = [], []
    for f in faces:
        rest = f.difference(built)
        if rest.area < 1.0:
            continue
        if f.intersection(gardens).area > 0.5 * f.area:
            fill_green += [p for p in G._polys(rest) if p.area >= G.MIN_PLANTER]
        else:
            fill_paving.append(rest)
    z_paving = unary_union([z_paving] + fill_paving)
    planters = planters + fill_green

    keep = lambda g: unary_union([p for p in G._polys(g) if p.area > 0.6])
    # `void` (for the Terrain's height fill) keeps the whole tdl_water footprint, bridge included: the DEM dips under the
    # pond (it is reading the water/bed, not ground), so the bridge deck's height should come from the harmonic fill off
    # the real ground at its ends, same as any other hole, not from that dip -- only the mesh (paving) itself carries the
    # bridge-over-water exception (`blocked` above), so the two stay separate.
    return dict(paving=keep(z_paving), planters=planters, blocked=blocked, water=water, void=unary_union([blocked, water_solid]))


def hub_pattern(zone, center, base_name):
    """A two-tone ring pattern radiating from `center` (like ds_tdl_ground.paving_pattern, re-implemented here since
    that one is hard-wired to the entrance gate's centre): alternating rings, a pale joint line between them."""
    if zone.is_empty:
        return []
    cx, cy = center
    minx, miny, maxx, maxy = zone.bounds
    max_r = math.hypot(max(abs(minx - cx), abs(maxx - cx)), max(abs(miny - cy), abs(maxy - cy))) + RING_STEP
    rings = np.arange(0.0, max_r + RING_STEP, RING_STEP)
    panels = [[], []]
    for i in range(len(rings) - 1):
        r0, r1 = max(rings[i], 0.05), rings[i + 1]
        n = max(6, round(2 * math.pi * (r0 + r1) / 2 / RING_ARC))
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            m = 6
            outer = [(cx + r1 * math.cos(a0 + (a1 - a0) * t / m), cy + r1 * math.sin(a0 + (a1 - a0) * t / m)) for t in range(m + 1)]
            inner = [(cx + r0 * math.cos(a1 - (a1 - a0) * t / m), cy + r0 * math.sin(a1 - (a1 - a0) * t / m)) for t in range(m + 1)]
            cell = Polygon(outer + inner).buffer(-(LINE_W / 2 + 0.6), join_style=2).buffer(0.6, resolution=4)
            if not cell.is_empty:
                panels[i % 2].append(cell)
    p0 = unary_union(panels[0]).intersection(zone) if panels[0] else Polygon()
    p1 = unary_union(panels[1]).intersection(zone) if panels[1] else Polygon()
    band = zone.difference(p0).difference(p1)
    return [(base_name, p0), (base_name + "2", p1), ("TP_line", band)]


def add_planter(meshes, T, q):
    """Like ds_tdl_ground.add_planter (a curb ring round a lower top), with one addition: a thin ribbon of pale
    flowers (TP_flower) just inside the curb before the green top (see the docstring)."""
    q = shapely.geometry.polygon.orient(q, 1.0)
    q_in = q.buffer(-G.CURB_W, join_style=2)
    ring = q.difference(q_in) if not q_in.is_empty else q
    tris = []
    for poly in G._polys(ring):
        for c in G.cdt(poly):
            z = T.z(c[:, 0], c[:, 1]) + G.CURB_H
            dx, dy = T.grad(c[:, 0], c[:, 1])
            n = np.stack([-dx, -dy, np.ones(3)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
            meshes["TP_curb"].add(np.column_stack([c[:, :2], z]), n); tris.append(c)
    qline = q.exterior
    for a, b in G.free_edges(tris):
        za, zb = float(T.z(a[0], a[1])) + G.CURB_H, float(T.z(b[0], b[1])) + G.CURB_H
        if qline.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < 0.03:
            G.wall(meshes["TP_curb"], a, b, za, zb, za - G.CURB_H - 0.02, zb - G.CURB_H - 0.02)
        else:
            G.wall(meshes["TP_curb"], a, b, za, zb, za - G.SOIL_DROP, zb - G.SOIL_DROP)
    if q_in.is_empty:
        return
    flower = q_in.buffer(-FLOWER_W, join_style=2)
    ribbon = q_in.difference(flower) if not flower.is_empty else q_in
    for name, geom in (("TP_flower", ribbon), ("TP_soil", flower)):
        for poly in G._polys(geom):
            for c in G.cdt(poly):
                z = T.z(c[:, 0], c[:, 1]) + G.CURB_H - G.SOIL_DROP
                dx, dy = T.grad(c[:, 0], c[:, 1])
                n = np.stack([-dx, -dy, np.ones(3)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
                meshes[name].add(np.column_stack([c[:, :2], z]), n)


def build():
    P = plan()
    T = G.Terrain(unary_union([P["paving"]] + P["planters"]).bounds, void=P["void"].buffer(H.BUILDING_MARGIN))
    meshes = {n: G.Mesh(n) for n in NAMES}
    pl_lines = unary_union([q.exterior for q in P["planters"]]) if P["planters"] else None

    disk = lambda r: Point(*HUB_C).buffer(r, resolution=32)
    island = P["paving"].intersection(disk(RING_R[0]))
    ring = P["paving"].intersection(disk(RING_R[1])).difference(disk(RING_R[0]))
    outer = P["paving"].difference(disk(RING_R[1]))
    pieces = hub_pattern(island, HUB_C, "TP_paving") + [("TP_ring", ring)]
    for key, a0, a1 in SECTORS:
        wedge = Polygon([HUB_C] + [(HUB_C[0] + 600 * math.cos(math.radians(a)), HUB_C[1] + 600 * math.sin(math.radians(a)))
                                   for a in np.linspace(a0, a1, 16)])
        part = outer.intersection(wedge)
        near = part.intersection(disk(HUB_PATTERN_R))
        pieces += hub_pattern(near, HUB_C, f"TP_paving_{key}") + [(f"TP_paving_{key}", part.difference(near))]
    for name, piece in pieces:
        if not piece.is_empty:
            G.add_zone(meshes, T, name, piece, edge="TP_edge", avoid=pl_lines)
    for q in P["planters"]:
        add_planter(meshes, T, q)
    return P, T, meshes


def main():
    P, T, meshes = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = G.write_gltf(OUT, meshes)
    zs = np.concatenate([np.array(m.tris)[:, :, 2].ravel() for m in meshes.values() if m.tris])
    print(f"[plaza ground] {OUT.name} {OUT.stat().st_size / 1024:.0f} KB, {n} triangles, z {zs.min():.2f} .. {zs.max():.2f} m")
    print("  areas m2: paving %.0f, %d planters %.0f" % (P["paving"].area, len(P["planters"]), sum(q.area for q in P["planters"])))
    print("  triangles:", {k: len(m.tris) for k, m in meshes.items()})


if __name__ == "__main__":
    main()
