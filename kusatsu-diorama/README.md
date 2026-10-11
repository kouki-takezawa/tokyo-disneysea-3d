# 草津温泉 湯畑ジオラマ

湯畑を中心に半径200 mを切り出した、静止のジオラマ(Three.js)。実測の標高(国土地理院 DEM5A、1:1)・OSMの建物外形・動画フレームから起こした建物と小物。看板は読めたものだけ実名。個人利用。

- 開く: `python -m http.server 8796` → http://127.0.0.1:8796/kusatsu-diorama/(ES モジュールなのでファイルを直接開かない)。スマホは自動で軽量画質。`?q=light|standard`、`?spin`、`?stats`。
- 操作: ドラッグで回転、ホイール/ピンチでズーム、右ドラッグ/2本指で移動。ボタンで視点(全景・湯畑・湯滝・湯樋・光泉寺の石段・西の河原通り)、建物・看板の表示切替、自動回転。
- 中身: `models/terrain.glb`(地形・台座・道・石段)、`yubatake.glb`、`buildings_A..D.glb`(区域別の建物)、`props.glb`(街灯・電柱と電線・自販機・標識・白線・幟)、`plants.glb`(確認できた位置の木)、`signs.json`(看板・幟・標識の文字面。ビューアが canvas で文字を貼る)。合計 約 0.84M 三角形・約 7.7 MB。
- 作り方(Blender 5.2 ヘッドレス): リポジトリの `kusatsu/kd_*.py`。`kd_terrain.py`(地形+全区域)、`kd_zone_A..D.py`(建物)、`kd_props.py`、`kd_plants.py`。計画と各フェーズの数値・未対応は `docs/kusatsu/`。
- 静止: 人・車・湯の流れ・湯けむり・雲は作っていない。夜景なし。
- 出典: 地図 OpenStreetMap contributors(ODbL)、標高 国土地理院。フレーム画像・動画はテクスチャにしていない(リポジトリに含めない)。
