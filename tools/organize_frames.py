#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フレーム画像を時系列フォルダに整理するスクリプト
frames/frame_000001.png → frames/00_00_00/frame_000001.png など
"""

from pathlib import Path


def organize_frames(frames_dir="frames", frame_interval=2):
    frames_path = Path(frames_dir)

    if not frames_path.exists():
        print(f"エラー: {frames_dir} ディレクトリが見つかりません")
        return False

    frame_files = sorted(frames_path.glob("frame_*.png"))

    if not frame_files:
        print(f"エラー: {frames_dir} に frame_*.png ファイルが見つかりません")
        return False

    print(f"対象フレーム数: {len(frame_files)}")
    print(f"フレーム間隔: {frame_interval}秒")

    organized_count = 0

    for idx, frame_file in enumerate(frame_files):
        total_seconds = idx * frame_interval
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        folder_name = f"{hours:02d}_{minutes:02d}_{seconds:02d}"
        folder_path = frames_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        frame_file.rename(folder_path / frame_file.name)
        organized_count += 1

        if organized_count % 100 == 0:
            print(f"進捗: {organized_count}/{len(frame_files)} ({organized_count*100//len(frame_files)}%)")

    print("\n✓ 整理完了！")
    print(f"  整理されたフレーム: {organized_count}個")
    print(f"  出力ディレクトリ: {frames_path.absolute()}")

    subdirs = sorted([d for d in frames_path.iterdir() if d.is_dir()])
    if subdirs:
        print(f"  作成されたタイムフォルダ: {len(subdirs)}個")
        print(f"  最初: {subdirs[0].name}")
        print(f"  最後: {subdirs[-1].name}")

        total_size = sum(f.stat().st_size for f in frames_path.rglob("*.png"))
        print(f"  合計ファイルサイズ: {total_size / (1024 * 1024):.2f}MB")

    return True


def create_summary_html(frames_dir="frames", output_file="summary.html"):
    """抽出フレームのHTMLサマリーを作成(summary.html はフレームフォルダの隣ではなく cwd に出力)"""
    frames_path = Path(frames_dir)
    subdirs = sorted([d for d in frames_path.iterdir() if d.is_dir()])

    if not subdirs:
        print("整理されたフレームフォルダが見つかりません")
        return False

    output_path = Path(output_file).absolute()
    total_frames = sum(len(list(d.glob("*.png"))) for d in subdirs)

    cards = ""
    for subdir in subdirs[:24]:  # 最初の24個のみ表示
        frames = sorted(subdir.glob("*.png"))
        if frames:
            rel = Path(frames[0].absolute()).relative_to(output_path.parent) \
                if output_path.parent in frames[0].absolute().parents else frames[0].absolute()
            cards += f"""
            <div class="frame-group">
                <img src="{rel.as_posix()}" alt="Frame {subdir.name}">
                <div class="timestamp">{subdir.name}</div>
                <div class="frame-count">{len(frames)} frames</div>
            </div>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Disneyland Frames Summary</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f5f5f5; }}
h1 {{ color: #333; text-align: center; }}
.stats {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }}
.frame-group {{ background: white; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: transform 0.2s; }}
.frame-group:hover {{ transform: scale(1.05); }}
.frame-group img {{ width: 100%; border-radius: 4px; margin-bottom: 8px; }}
.timestamp {{ font-weight: bold; color: #2196F3; text-align: center; }}
.frame-count {{ font-size: 0.9em; color: #666; text-align: center; }}
</style>
</head>
<body>
<h1>🏰 Tokyo Disneyland - Frame Gallery</h1>
<div class="stats">
<h3>統計情報</h3>
<p>総時間フォルダ: {len(subdirs)}</p>
<p>総フレーム数: {total_frames}</p>
<p>抽出方法: 2秒ごと</p>
</div>
<div class="grid">{cards}</div>
</body>
</html>
"""
    output_path.write_text(html_content, encoding="utf-8")
    print(f"✓ HTMLサマリーを作成しました: {output_path}")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="フレーム画像を時系列フォルダに整理")
    parser.add_argument("--dir", default="frames", help="フレームディレクトリ (デフォルト: frames)")
    parser.add_argument("--interval", type=int, default=2, help="フレーム間隔秒数 (デフォルト: 2)")
    parser.add_argument("--html", action="store_true", help="HTMLサマリーを作成")
    args = parser.parse_args()

    if organize_frames(args.dir, args.interval) and args.html:
        create_summary_html(args.dir)


if __name__ == "__main__":
    main()
