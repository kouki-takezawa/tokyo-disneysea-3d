#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動画フレームのコンタクトシート(時刻ラベル付きの一覧画像)を作る / 区間データを引く。

  # 区間データ docs/video_frames/segments.json を引く(エリア名・ランド名・メモの部分一致)
  python tools/frame_sheet.py find トゥーンタウン
  # 動画 v2 の 0:31:00〜0:33:00 を 2 秒ごとに一覧にする(1 枚 30 コマ)
  python tools/frame_sheet.py sheet v2 0:31:00 0:33:00 --step 2 --out C:/temp/sheets
  # 全体を 20 秒ごとに
  python tools/frame_sheet.py sheet v1 --step 20 --out C:/temp/sheets

フレームは frame_000001.jpg = 0:00:00、以後 2 秒ごと。organize_frames.py で HH_MM_SS フォルダに
分けた後でも分ける前でも読める。画像そのものはリポジトリに入れない(docs/video_reference_plan.md)。
"""
import argparse
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEGMENTS = os.path.join(ROOT, "docs", "video_frames", "segments.json")
INTERVAL = 2                       # seconds between frames
W, H, COLS, ROWS = 320, 180, 6, 5  # one sheet = 1920 x 900, 30 frames


def secs(t):
    p = [int(x) for x in str(t).replace("_", ":").split(":")]
    while len(p) < 3:
        p.insert(0, 0)
    return p[0] * 3600 + p[1] * 60 + p[2]


def hms(s):
    return "%d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60)


def load():
    with open(SEGMENTS, encoding="utf-8") as f:
        return json.load(f)


def find(words):
    d = load()
    for vid, v in d["videos"].items():
        for s in v["segments"]:
            text = " ".join(str(s.get(k, "")) for k in ("land", "area", "see", "note"))
            if all(w in text for w in words):
                print(f"{vid} {s['t0']}-{s['t1']}  [{s['land']}] {s['area']}  {s.get('see', '')}")


def sheet(vid, t0, t1, step, out, src=None):
    from PIL import Image, ImageDraw, ImageFont
    src = src or load()["videos"][vid]["frames_dir"]
    files = glob.glob(os.path.join(src, "**", "frame_*.jpg"), recursive=True)
    by_t = {(int(os.path.basename(f)[6:12]) - 1) * INTERVAL: f for f in files}
    step = max(INTERVAL, step // INTERVAL * INTERVAL)
    pick = [t for t in sorted(by_t) if t0 <= t <= t1 and (t - t0) % step == 0]
    os.makedirs(out, exist_ok=True)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i in range(0, len(pick), COLS * ROWS):
        chunk = pick[i:i + COLS * ROWS]
        rows = -(-len(chunk) // COLS)
        img = Image.new("RGB", (W * COLS, H * rows))
        d = ImageDraw.Draw(img)
        for k, t in enumerate(chunk):
            x, y = (k % COLS) * W, (k // COLS) * H
            img.paste(Image.open(by_t[t]).convert("RGB").resize((W, H)), (x, y))
            d.rectangle([x, y, x + 100, y + 26], fill=(0, 0, 0))
            d.text((x + 4, y + 1), hms(t), fill=(255, 255, 0), font=font)
        p = os.path.join(out, "%s_%s.jpg" % (vid, hms(chunk[0]).replace(":", "_")))
        img.save(p, quality=80)
        print(p, len(chunk))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find")
    f.add_argument("words", nargs="+")
    s = sub.add_parser("sheet")
    s.add_argument("video")
    s.add_argument("t0", nargs="?", default="0:00:00")
    s.add_argument("t1", nargs="?", default="9:59:59")
    s.add_argument("--step", type=int, default=20)
    s.add_argument("--out", default="C:/temp/sheets")
    s.add_argument("--src")
    a = ap.parse_args()
    if a.cmd == "find":
        find(a.words)
    else:
        sheet(a.video, secs(a.t0), secs(a.t1), a.step, a.out, a.src)
