# 計画3 進み具合(2026-09-29 時点)

ランドのプラザ(WB 出口〜シンデレラ城)+アイスクリームコーン。

| フェーズ | 内容 | 状態 |
|---|---|---|
| 0 | 資料(OSM・航空写真・Commons) → `docs/plaza/README.md` | 済 3939f88 |
| 1 | アイスクリームコーン外観 | 済 086882c |
| 2 | アイスクリームコーン店内 | ほぼ済(このコミット)。残りは下記 |
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

## 明日の続き(フェーズ2の残り)

1. **モックの散歩で店内を確認していない**。Playwright で `TDS_WALK` を店内に(ICC ローカル (x,y) → WB (-9.4-x, -112-y))、ドアから入れるか・カウンターで止まるか・色(サーモン/水色)を見る。
2. Cycles では店内が暗い(照明が小さな球だけ)。必要なら天井にライトを足す。モックでは問題ないはず。
3. 写真6の季節の垂れ幕(ダック・ファミリー)は期間限定なので入れていない。
4. 前からの残り: リフレッシュメントコーナーのマンサードが裏から黒く見える(範囲外)。

その後 `/clear` → 「計画3のフェーズ3から」。

## 手順メモ

```
blender -b --python src/ds_tdl_world_bazaar.py -- --cams wbz_icc_in,wbz_icc_in2 --samples 24 --percent 40
blender -b --python src/export_models.py -- --parts tdl_world_bazaar
python src/export_mock.py          # 圧縮(models/web/)と tds_outline.html まで
git push → Vercel 自動デプロイ → gh api repos/kouki-takezawa/tokyo-disneysea-3d/commits/<sha>/statuses
```
