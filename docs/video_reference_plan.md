# 動画フレームを作成データとして使う作業計画 (2026-09-30)

ディズニーランド(TDL)の歩き撮り動画2本から2秒ごとにフレームを切り出し、モックの形状・配置・色の参考データとして使う。

## 元動画

| # | タイトル | 長さ | チャンネル | URL |
|---|---|---|---|---|
| 1 | 夕暮れ時のディズニーランド「全エリア」を丁寧に歩く(Twilight Time Walking Tour) | 1:21:48 | Poneco Disney | https://www.youtube.com/watch?v=a9bWFNMwjrs |
| 2 | [4K JAPAN WALK] Tokyo Disneyland Walking Tour (Jul. 2021) | 1:19:34 | Japan Osanpo Walker | https://www.youtube.com/watch?v=Si90OMF1dD4 |

- 1は夕暮れ、2は昼。**形状・配置は両方、昼の色や質感は2を優先**して見る。
- フレームや動画そのものはリポジトリに入れない(数GBあり、他者の著作物)。目視の参考のみとし、テクスチャとして貼らない。
- YouTube Shorts は参考にしない。

## 抽出手順 (再現用)

```powershell
# 1080p以下のmp4で取得(最高画質は13GB超で遅いので避ける)
python -m yt_dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]" --merge-output-format mp4 -o video.mp4 "<URL>"
# 2秒ごとに切り出し
ffmpeg -i video.mp4 -vf fps=0.5 frames/frame_%06d.png
# 時刻名フォルダ(HH_MM_SS)へ整理、--html でギャラリー
python tools/organize_frames.py --dir frames --html
```

- スクリプト: `tools/extract_frames.ps1`(一括実行)、`tools/organize_frames.py`(整理・ギャラリー)。
- 出力先は OneDrive の外(`C:\temp\...`)にする。数GBのPNGが同期されるため。
- 実績: 1が2,454枚(約14GB)、2が2,387枚(約3.8GB)。フォルダ名の時刻が動画内の再生位置に対応する(`01_05_10` = 1:05:10)。

## 使い方の計画

1. **エリア別の時刻表を作る**: 各動画で、どの時刻にどのエリア(ワールドバザール、アドベンチャーランド、ウエスタンランド、クリッターカントリー、ファンタジーランド、トゥーンタウン、トゥモローランド)を歩いているかを、ギャラリーで拾って `docs/` に表にする。
2. **建物・地面の参考写真を選ぶ**: 既存の計画(エントランス、プラザ、各ランド)の不足部分について、該当時刻のフレームを数枚だけ目視で選ぶ。選んだ時刻だけをメモし、画像は保存しない。
3. **モックに反映**: 形状・寸法・色の食い違いを直す。夜景版は作らない、木・ヤシは足さない(既存の方針どおり)。
4. **足りなければ再抽出**: 選んだ時刻の前後だけ `-ss` / `-to` と `fps=1` で細かく切り出す。

## 後片付け

- ローカルの切り出し画像(`C:\temp\disneyland\frames`、`C:\temp\disneyland2\frames`)は、この計画書を入れた後に削除する。
- 元動画(mp4)は再抽出用に残す。不要になったら削除。
