"""Import the Blender-side scripts with stub bpy / bmesh / mathutils and run a few pure-logic paths.
Catches syntax errors, missing names and broken imports on a machine without Blender.

  python tools/blender_smoke.py            # checks this repository
  python tools/blender_smoke.py <clone>    # checks another checkout (e.g. a fresh clone)
"""
import sys, types, importlib, traceback, pathlib
from unittest.mock import MagicMock

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent).resolve()
sys.path.insert(0, str(REPO))
sys.argv = [sys.argv[0]]          # scripts parse args after "--"


class Vec(tuple):   # enough of mathutils.Vector for arithmetic in module-level code
    def __new__(cls, v=(0, 0, 0)): return super().__new__(cls, tuple(v))
    def __getattr__(self, k): return MagicMock()


mathutils = types.ModuleType("mathutils")
mathutils.Vector = MagicMock(side_effect=lambda *a, **k: MagicMock())
mathutils.Matrix = MagicMock()
geom = types.ModuleType("mathutils.geometry")
geom.tessellate_polygon = MagicMock(return_value=[(0, 1, 2)])
mathutils.geometry = geom
for name, mod in (("bpy", MagicMock()), ("bmesh", MagicMock()), ("mathutils", mathutils), ("mathutils.geometry", geom)):
    sys.modules[name] = mod

results = []
MODULES = ["ds_core", "ds_terrain", "ds_buildings", "ds_landmarks", "ds_aquasphere", "ds_plaza", "ds_volcano_model",
           "disneysea_water_blender", "export_models", "disneysea_draft", "train_blender", "disneyland_blender", "ds_tdl_station", "ds_tdl_entrance", "ds_tracks", "ds_tdl_bb_castle", "ds_tdl_cinderella", "tdl_water_blender"]
for m in MODULES:
    try:
        importlib.import_module(m)
        results.append((m, "import ok", ""))
    except SystemExit as e:
        results.append((m, "import exited", str(e)))
    except Exception:
        results.append((m, "IMPORT FAILED", traceback.format_exc(limit=3)))

CALLS = [
    ("ds_landmarks.build_triton_dome()", lambda: sys.modules["ds_landmarks"].build_triton_dome()),
    ("ds_core.TRITON_ROOF", lambda: sys.modules["ds_core"].TRITON_ROOF),
    ("ds_core.nearest_port(-181,206)", lambda: sys.modules["ds_core"].nearest_port(-181, 206)),
    ("ds_volcano_model: data file", lambda: sys.modules["ds_volcano_model"].SRC.exists()),
    ("disneysea_water_blender.WATER_JSON", lambda: sys.modules["disneysea_water_blender"].WATER_JSON.exists()),
    ("ds_aquasphere globe textures", lambda: all((sys.modules["ds_aquasphere"].GLOBE_DIR / f).exists()
                                                  for f in ("globe_color.png", "globe_height.png", "globe_landmask.png"))),
    ("ds_plaza plan json", lambda: (REPO / "plateau_data" / "disneysea_plaza.json").exists()),
    ("disneyland_blender.summary()", lambda: sys.modules["disneyland_blender"].summary()),
    ("train_blender.SPEC == train_model.js S", lambda: train_spec_matches()),
    ("train_blender.sections(head)", lambda: len(sys.modules["train_blender"].sections(15.05, True))),
    ("ds_tdl_station.to_local(station node)", lambda: tuple(round(v, 1) for v in sys.modules["ds_tdl_station"].to_local(-581.44, 1020.43))),
]


def train_spec_matches():
    """The Blender train uses the same numbers as the JS model (S in output/disneysea/train_model.js)."""
    import re
    js = (REPO / "output" / "disneysea" / "train_model.js").read_text(encoding="utf-8")
    keys = {"headLen": "head_len", "midLen": "mid_len", "width": "width", "gap": "gap", "cars": "cars", "yBot": "y_bot", "yTop": "y_top",
            "roofR": "roof_r", "noseLen": "nose_len", "rake": "rake", "windBot": "wind_bot", "floor": "floor", "ceil": "ceil"}
    spec, bad = sys.modules["train_blender"].SPEC, []
    for jk, pk in keys.items():
        m = re.search(rf"\b{jk}:\s*(-?[\d.]+)", js)
        if not m or abs(float(m.group(1)) - spec[pk]) > 1e-9:
            bad.append((jk, m and m.group(1), spec[pk]))
    if bad:
        raise AssertionError(f"differs from train_model.js: {bad}")
    return "all match"
for label, fn in CALLS:
    try:
        results.append((label, "ok", repr(fn())[:120]))
    except Exception:
        results.append((label, "FAILED", traceback.format_exc(limit=4)))
for r in results:
    print(" | ".join(r))
