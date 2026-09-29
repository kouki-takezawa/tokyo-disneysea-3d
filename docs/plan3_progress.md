# 計画3 進み具合(2026-09-29 時点)

ランドのプラザ(WB 出口〜シンデレラ城)+アイスクリームコーン。

| フェーズ | 内容 | 状態 |
|---|---|---|
| 0 | 資料(OSM・航空写真・Commons) → `docs/plaza/README.md` | 済 3939f88 |
| 1 | アイスクリームコーン外観 | 済 086882c |
| 2 | アイスクリームコーン店内 | 済(e2736d3 + 残りの確認) |
| 3 | プラザの地面(新規 `ds_tdl_plaza_ground.py`、Blender なし)→ モックをユーザーに見せる | 未 |
| 4 | 中央: パートナーズ像・ステージ2つ・街灯・ベンチ・柵 | 未 |
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

## 手順メモ

```
blender -b --python src/ds_tdl_world_bazaar.py -- --cams wbz_icc_in,wbz_icc_in2 --samples 24 --percent 40
blender -b --python src/export_models.py -- --parts tdl_world_bazaar
python src/export_mock.py          # 圧縮(models/web/)と tds_outline.html まで
git push → Vercel 自動デプロイ → gh api repos/kouki-takezawa/tokyo-disneysea-3d/commits/<sha>/statuses
```
