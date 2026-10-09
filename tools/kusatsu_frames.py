#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
草津ジオラマ用: 参考動画のフレーム抽出と一覧シート作成 (画像はリポジトリに入れない。reference/kusatsu/ は .gitignore 対象)。

  python tools/kusatsu_frames.py extract            # reference/kusatsu/videos/*.mp4 -> frames/<id>/f_000001.jpg (STEP 秒ごと, 幅960)
  python tools/kusatsu_frames.py sheet <id> [t0 t1] # 時刻ラベル付き 6x5 一覧 -> sheets/<id>/<id>_HHMMSS.jpg
  python tools/kusatsu_frames.py overview <id>      # 30 秒ごとの概観(6x5 = 15 分/枚) -> sheets_overview/<id>/
  python tools/kusatsu_frames.py sheets             # 全動画の一覧を作る
フレーム f_000001 = 0 秒、以後 STEP 秒ごと。フレームはテクスチャにしない(目視参考のみ)。
"""
import glob, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "reference", "kusatsu")
STEP = 3
W, H, COLS, ROWS = 320, 180, 6, 5


def hms(s):
    return "%d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60)


def secs(t):
    p = [int(x) for x in str(t).split(":")]
    while len(p) < 3:
        p.insert(0, 0)
    return p[0] * 3600 + p[1] * 60 + p[2]


def extract():
    for v in sorted(glob.glob(os.path.join(REF, "videos", "*.mp4"))):
        vid = os.path.splitext(os.path.basename(v))[0]
        out = os.path.join(REF, "frames", vid)
        if glob.glob(os.path.join(out, "f_*.jpg")):
            print("skip", vid); continue
        os.makedirs(out, exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", v, "-vf", f"fps=1/{STEP},scale=960:-2",
                        "-q:v", "4", os.path.join(out, "f_%06d.jpg")], check=True)
        print(vid, len(glob.glob(os.path.join(out, "f_*.jpg"))))


def sheet(vid, t0=None, t1=None, every=1):
    fr = sorted(glob.glob(os.path.join(REF, "frames", vid, "f_*.jpg")))
    every = int(every)
    a = secs(t0) // STEP if t0 else 0
    b = min(len(fr), secs(t1) // STEP + 1) if t1 else len(fr)
    out = os.path.join(REF, "sheets" + ("_overview" if every > 1 else ""), vid); os.makedirs(out, exist_ok=True)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    n = COLS * ROWS
    for s in range(a, b, n * every):
        im = Image.new("RGB", (W * COLS, H * ROWS), "black"); d = ImageDraw.Draw(im)
        for k, i in enumerate(range(s, min(s + n * every, b), every)):
            t = Image.open(fr[i]).convert("RGB").resize((W, H))
            x, y = (k % COLS) * W, (k // COLS) * H
            im.paste(t, (x, y)); d.rectangle([x, y, x + 64, y + 20], fill="black")
            d.text((x + 3, y + 1), hms(i * STEP), fill="yellow", font=font)
        name = "%s_%02d%02d%02d.jpg" % (vid, s * STEP // 3600, s * STEP // 60 % 60, s * STEP % 60)
        im.save(os.path.join(out, name), quality=80)
    print(vid, "sheets ->", out)


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "extract":
        extract()
    elif c == "sheet":
        sheet(*sys.argv[2:5])
    elif c == "overview":
        sheet(sys.argv[2], None, None, 10)
    elif c == "sheets":
        for d in sorted(os.listdir(os.path.join(REF, "frames"))):
            sheet(d)
    else:
        print(__doc__)
