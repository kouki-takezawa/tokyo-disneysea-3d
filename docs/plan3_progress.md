# 計画3 進み具合(2026-09-29 時点)

ランドのプラザ(WB 出口〜シンデレラ城)+アイスクリームコーン。

| フェーズ | 内容 | 状態 |
|---|---|---|
| 0 | 資料(OSM・航空写真・Commons) → `docs/plaza/README.md` | 済 3939f88 |
| 1 | アイスクリームコーン外観 | 済 086882c |
| 2 | アイスクリームコーン店内 | 済(e2736d3 + 残りの確認) |
| 3 | プラザの地面(新規 `ds_tdl_plaza_ground.py`、Blender なし)→ モックをユーザーに見せる | 済 a47e016 |
| 4 | 中央: パートナーズ像・ステージ2つ・街灯・ベンチ・柵(新規 `ds_tdl_plaza_center.py`) | 済 |
| 5 | 周りの建物(新規 `ds_tdl_plaza_hub.py`) | 未 |
| 6 | つなぎ目・散歩で駅→城を確認・圧縮・README・本番反映 | 未 |

## フェーズ2でやったこと

`src/ds_tdl_world_bazaar.py`
- `ice_cream_cones()`: ドア奥の暗い箱を撤去。店の裏にある窓(正面の 2 区画 u=6.8/9.73 と東面の大窓)は壁に穴を開け、ガラスを `shopglass` に(`icc_window(..., clear=True)`)。ほかの窓は今までどおり暗いガラス。
- `icc_interior()`: 部屋は ICC フレームで x 0.3〜11.2、y -0.3〜-5.3、天井 3.9(`ICC["room"]`, `ICC_CEIL`)。奥の Main Street の店(y<-5.7)とは重ならない。
  - 床: 白地に水色の 0.6 m 市松。壁: 腰壁(白、奥の壁はクリーム)+チェアレール+サーモンピンクの上壁+白いコーニス+パネル枠(`icc_inner_wall`、穴は `wall_holes`)。
  - カウンター(`icc_counter`): 長い辺 x 2.2〜10.4(y=-2.9 が客側の面)+東の窓側に折り返し。ピンクのパネルとひし形、白い柱+透かしのフリーズと持ち送り、サーモンの帯+楕円のメダリオン、楕円のメニュー看板、アイスの並ぶガラスケース2つ。
  - 奥: ステンレスの作業台と機械5台、額の絵。客側: シャンデリア3つ、真鍮の柵。
  - `xform_new()`: ローカル座標で作って行列で移す。**bm_lathe の remove_doubles で空いた頂点スロットが再利用されるので、「末尾の頂点=新規」は成り立たない** → タグ方式にしてある。
- 材質を追加: `icc_salmon / icc_blue / icc_rose / icc_steel / icc_waffle`(モックの `MODEL_MAT` にも `ST_wbz_icc_*` を追加済み)。
- 確認カメラ: `wbz_icc_in`(東の窓側からカウンター)、`wbz_icc_in2`(西からカウンターと折り返し)。

## フェーズ2の残り(2026-09-29 済)

- モックの散歩で確認: ドア前(ICC (3.9, 3.0)、yaw 25°)から W で入れる。カウンター客側の面(y=-2.9)の約 0.3 m 手前で止まる。サーモンの上壁・水色の市松・ピンクのカウンター・シャンデリアが出ている。正面の大窓は内側からはレースのカーテン(クリーム)に見える。
- 直したこと: メインストリートのガラス屋根の城側の端の鉄柱(WB (-12.25, -106.6) = ICC (2.85, -5.4))が店の奥の壁にまたがって室内に緑の柱として出ていた → `icc_interior()` で壁柱(白の腰+サーモン+コーニス)で包み、作業台と機械を少し西へ。
- 残した: Cycles で店内が暗い(ライトなし。確認用レンダだけの問題でモックは平気)。季節の垂れ幕は入れない。リフレッシュメントコーナーのマンサードが裏から黒い(範囲外)。
- Playwright の確認: ICC ローカル (x,y) → WB (-9.4-x, -112-y) → local (-521.3 + wx cos25 - wy sin25, 891.2 + wx sin25 + wy cos25)。`python -m http.server` で output/disneysea を配信し `TDS_WALK(x, y, yaw, pitch)`、W キーで歩く、`TDS_WALK_STATE()` で位置。

次は `/clear` → 「計画3のフェーズ3から」。

## フェーズ3でやったこと

新規 `src/ds_tdl_plaza_ground.py`(plain Python、Blender不要)。WB奥の出口(-477,794)〜シンデレラ城の門GATE(-388.6,578.2)のプラザ(ハブ)の地面。
- 中心 HUB_C=(-427.0, 687.0) を採用。OSM「Partners」ノード(-456.5,751.8)は航空写真+実際の放射状ガーデン帯(OSM way 71900258 ほか)から約70mずれている(OSM側の点の位置誤りと判断)。航空写真の2点(クリスタルパレス、キャッスルフォアコート)でピクセル<->メートル較正を検証済み。
- 舗装はOSMのhighway=pedestrian area全件+footway(Parade Route含む)+橋の小ポリゴン(舗装のまま)+隙間はpolygonizeで埋める(ds_tdl_hotel_ground.pyのFILL_BOXと同じ考え方)。花壇/芝はleisure=garden・landuse=grass等を全部ds_tdl_ground.add_planter相当(縁石+緑の上面、白い花のリボンTP_flower付き)で処理。中心の小さな円形ガーデンと周囲4区画が実データのまま「放射状の芝生くさび」になる(合成形状ではない)。
- 既存モデルとの重なりはds_ground.model_footprint()で cinderella/tdl_world_bazaar/tdl_plaza_buildings/tdl_water/tdl_ground の実フットプリントを差し引いて回避。調査の結果、城のフォアコート(コンパスローズ舗装)はds_tdl_cinderella.pyのbuild_forecourt()で既に作成済みと判明(タスクの「GATE手前は細かめ」は不要、docstringに明記)。
- `ds_ground.py`のZONES["tdl_land_ground"]["cut_models"]に"tdl_plaza_ground"を追加(既存の地面を切り抜く、tds_groundがplaza/aquasphere/volcanoを切り抜くのと同じ流儀)。`export_mock.py`のMODELSに登録。`mock_template.html`にTP_*マテリアルとHEDGE_KEYへのTP_soil追加。
- Playwright確認: `python -m http.server`配信、`TDS_WALK(-477,794,-2.753,-0.05)`でWB出口から城向き(南158°)、`TDS_FOCUS(-427,687,0.5,190,0.6,1.35)`で俯瞰。俯瞰図は航空写真の放射状パターンとよく一致。Wキーで歩行、フォールなし・引っかかりなし(ただしモデル読み込みが重くメインスレッドが詰まるため移動量は小さい)。
- モデル読み込みの注意: このモックは全モデル(~19個)をメインスレッドで1個ずつ同期読み込みするため、`tdl_plaza_ground`の読み込みに70〜90秒かかることがある。散歩モードで開始すると比較的早く読み込まれる。`page.screenshot()`のタイムアウトは長め(120秒)にすること。

## フェーズ4でやったこと

新規 `src/ds_tdl_plaza_center.py`(plain Python、Blender不要)→ `output/disneysea/models/tdl_plaza_center.json`(33.6k 三角形、頂点約6.7万、Draco後 0.16 MB)。フェーズ3の `tdl_plaza_ground.json` の三角形を読み戻し、実際に作られた舗装・花壇(他モデルで切り抜いた後の形)の上に置く。高さもその三角形から取る。
- パートナーズ像: HUB_C (-427,687) の円形花壇(半径約6.4m、重心は HUB_C から0.7m)の中央。台座は明るい石の多段円柱(下段 r2.05・h0.85 → 段 → 胴 r1.30 → コーニス、上面 z=2.87)、正面にブロンズ銘板。像はブロンズ色の低ポリ人型(ウォルト約1.9m、右手を上げて前を指す、左手でミッキーの手をつなぐ。ミッキーは左側、約1.1m)。向きは WB 出口 (-477,794) 方向(方位 115°=北西寄り、城を背に)。写真なし・一般知識のみ。
- ステージ「プラザガーデン」(12028823101): 専用wayはないが、ノードのすぐ脇に芝生72241312の南縁を回る barrier=wall の2本の弧(1298497935〜42)と3か所の steps(1298497922〜27)がある → 2段の弧状ステージと解釈(推定)。1段目=2本の壁の間 +0.30m、2段目=内側の壁〜芝生 +0.60m(どちらも散歩のSTEP 0.55m以内の段差なので上がれる)、stepsの位置に踏み段。地面が0.7m傾いているので天端は地面に沿わせた(平らだと前縁が0.76mになり上がれなかった)。
- ステージ「キャッスルフォアコート」(6293190962, (-411,655)): cinderella モデル(build_forecourt の城前ステージ)の南端 y=649.3 から6.4m北の点=観客側の広場を指すノードと判断。ステージは既存なので作らない(重複なし)。
- 柵: HUB_C から80m以内の花壇の縁石の上に低い鉄柵(濃緑、縁石上0.55m、支柱約1.5m間隔+上下2本の横桟、両面描画の縦板なので軽い)。支柱1261本・延長約1.9km。ステージが芝生に接する所は省略。
- 街灯59本(濃緑の柱+白い球グローブ、3.8m)・ベンチ48基(濃緑すのこ+鋳鉄の脇)を花壇の縁に沿って自動配置(舗装の上だけ、花壇・ステージ・像の花壇の周りは避ける、ベンチは花壇を背に道向き)。位置は推定(実物の測量なし)。
- 当たり判定は既存の仕組み(急な面=壁、平らな面=床)のまま。Playwrightで確認: 像の花壇に向かって歩くと中心から6.9m(柵の外)で止まる。ステージは南から歩いて1段目→2段目に上がり、芝生の縁で止まる。
- 登録: `export_mock.py` の MODELS に `tdl_plaza_center`(layer disneyland)、`mock_template.html` に `PC_*` 材質。
- 確認画像(scratchpad): `p4_walk_statue.png`(WB側から像と城)、`p4_statue_close.png`、`p4_stage.png`、`p4_focus.png`(俯瞰)。

残り: 像は低ポリで顔・服の細部なし。プラザガーデンの実際の姿(屋根や背景の有無)は写真がなく未確認。街灯・ベンチの本当の位置は不明(自動配置)。柵の意匠(唐草・フープ)は省略。周りの建物はフェーズ5。

手順: `python src/ds_tdl_plaza_ground.py`(地面を作り直したら)→ `python src/ds_tdl_plaza_center.py` → `python src/export_mock.py`。

## 手順メモ

```
python src/ds_tdl_plaza_ground.py  # -> output/disneysea/models/tdl_plaza_ground.json + 要約
python src/ds_ground.py tdl_land_ground   # cut_models適用後の再生成(1分程度)
python src/ds_tdl_plaza_center.py  # -> tdl_plaza_center.json(地面の三角形を読むので地面の後)
python src/export_mock.py          # 圧縮(models/web/)と tds_outline.html まで
git push → Vercel 自動デプロイ → gh api repos/kouki-takezawa/tokyo-disneysea-3d/commits/<sha>/statuses
```
