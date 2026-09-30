# YouTube動画からフレームを抽出するスクリプト

# 設定
$videoUrl = "https://www.youtube.com/watch?v=a9bWFNMwjrs"
$outputDir = ".\disneyland_frames"
$videoFile = ".\disneyland_video.mp4"
$framesDir = "$outputDir\frames"

# 出力ディレクトリ作成
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

if (-not (Test-Path $framesDir)) {
    New-Item -ItemType Directory -Path $framesDir | Out-Null
}

Write-Host "ステップ 1: YouTubeから動画をダウンロード中..."
# yt-dlpがインストール済みか確認
if (-not (Get-Command yt-dlp -ErrorAction SilentlyContinue)) {
    Write-Host "yt-dlpをインストール中..."
    pip install yt-dlp
}

# 動画ダウンロード
if (-not (Test-Path $videoFile)) {
    yt-dlp -f "best[ext=mp4]" -o $videoFile $videoUrl
}

Write-Host "ステップ 2: ffmpegでフレームを抽出中（2秒ごと）..."
# ffmpegがインストール済みか確認
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ffmpegをインストール中..."
    choco install ffmpeg -y
    # または: winget install FFmpeg
}

# 2秒ごと（fps=0.5）にフレーム抽出
ffmpeg -i $videoFile -vf "fps=0.5" "$framesDir\frame_%06d.png"

Write-Host "ステップ 3: 画像ファイルの情報を表示中..."
$frames = Get-ChildItem $framesDir -Filter "*.png" | Sort-Object Name
Write-Host "抽出フレーム数: $($frames.Count)"
Write-Host "最初のフレーム: $($frames[0].Name)"
Write-Host "最後のフレーム: $($frames[-1].Name)"

Write-Host "`n完了！フレームは以下に保存されています:"
Write-Host "$framesDir"
Write-Host "`n総ファイルサイズ: $((Get-ChildItem $framesDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB)MB"
