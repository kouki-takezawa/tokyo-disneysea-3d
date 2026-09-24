"""Building footprint blocking for the DisneySea draft.

Every OSM building/roof footprint becomes a simple extruded box at an
estimated height (see ds_core.height_for_way). Footprints that match
DETAIL_PRIORITY are tagged onto a separate collection + a text list file so
a later pass can rebuild just those with real facade detail, matching the
level of the reference models on Sketchfab (see ds_core docstring) without
touching anything else.
"""
import bpy, pathlib
from ds_core import (DATA, get_collection, flat_material, extrude_footprint, extrude_loops, is_roof, ROOF_T,
                      link, ways_with, height_for_way, nearest_port, multipolygons,
                      poly_centroid, ring_inside, in_park, PORT_COLOR, DETAIL_PRIORITY,
                      LANDMARK_SKIP, LANDMARK_SKIP_IDS)

REPORT = pathlib.Path(__file__).parent / "output" / "detail_priority_todo.txt"


def _is_priority(name):
    return any(key in name for key in DETAIL_PRIORITY)


def build_buildings():
    col_by_port = {p: get_collection(f"Buildings_{p}") for p in PORT_COLOR}
    col_priority = get_collection("Buildings_PRIORITY_todo")
    mats = {p: flat_material(f"mat_bldg_{p}", c, roughness=0.8) for p, c in PORT_COLOR.items()}
    mat_priority = flat_material("mat_bldg_priority", (0.95, 0.15, 0.15), roughness=0.6)

    n_box, n_priority = 0, 0
    priority_hits = []
    seen_names = set()
    items = [(w, [w["pts"]]) for w in ways_with("building")]
    for r, outers, inners in multipolygons("building"):
        for j, o in enumerate(outers):
            fake = {"id": r["id"] * 10 + j, "tags": r["tags"], "pts": o}
            items.append((fake, [o] + [i for i in inners if ring_inside(i, o)]))
    if True:
        for w, loops in items:
            if not in_park(w["pts"]) or w["id"] in LANDMARK_SKIP_IDS:
                continue
            name = w["tags"].get("name", "") or w["tags"].get("name:en", "")
            if name and any(k in name for k in LANDMARK_SKIP):
                continue
            cx, cy = poly_centroid(w["pts"])
            port = nearest_port(cx, cy, w["pts"])
            height = height_for_way(w)
            is_pri = bool(name) and _is_priority(name)
            z0 = max(0.0, height - ROOF_T) if is_roof(w["tags"]) else 0.0   # roof-only structures: a slab, open underneath
            obj = extrude_loops(f"Bldg_{w['id']}", loops, z0, height - z0,
                                mat_priority if is_pri else mats[port])
            if not obj:
                continue
            link(obj, col_priority if is_pri else col_by_port[port])
            if is_pri:
                n_priority += 1
                if name not in seen_names:
                    priority_hits.append((name, port, round(height, 1), w["id"]))
                    seen_names.add(name)
            else:
                n_box += 1

    print(f"[buildings] boxed={n_box} priority_flagged={n_priority}")
    if priority_hits:
        REPORT.parent.mkdir(exist_ok=True)
        lines = ["# Detail-priority buildings still at box stage (red material)",
                 "# name | port | draft_height_m | osm_way_id", ""]
        lines += [f"{n} | {p} | {h} | {i}" for n, p, h, i in sorted(priority_hits, key=lambda r: r[1])]
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print(f"[buildings] wrote {REPORT}")
    return n_box, n_priority
