# 植物の棚卸し(2026-10-05、フェーズ0)

調べ方: `output/disneysea/models/*.json`(glTF JSON)の全メッシュを材質・ノード名・三角形数(indices/3)で走査。GLB の中身も同じ。
**注意**: メッシュ名は `<モデル接頭辞>_<部品>`(例 `AD_leaf`)で、材質はページ側の `MODEL_MAT`(mock_template.html の `ST_*` / `AD_*` などの色表)が名前で当てる。GLB の材質名は空。1メッシュ=1プリミティブで、種類ごとに結合済み(つまり1本ずつのオブジェクトではない)。

## 1. モデル内の植物メッシュ(三角形数は概数)

### 木・ヤシ・竹・低木の葉

| モデル(json) | メッシュ | 三角形 | 何か | 作った場所(src) |
|---|---|---|---|---|
| plaza | PZ_Trunk / PZ_Canopy | 1,148 / 3,280 | プラザの木(幹+樹冠のブロック)。PZ_Soil 266 は植え込みの土 | `ds_plaza.py` 171〜185行(PZ_Soil_/PZ_Trunk_/PZ_Canopy_ を結合) |
| tdl_adventureland | AD_palmt / AD_palml | 1,056 / 384 | ヤシの幹(7角形の円錐台を積む)/葉(四角板) | `ds_tdl_adventureland.py` `palm_tree()` 1238行(幹 `frustum`、葉 `quad`、頭 `sphere`) |
| 同 | AD_leaf / AD_leafr | 20,194 / 4,158 | 熱帯の茂み(球・三角の葉、赤い葉 leafr) | 同 `fern()` 1817行、`sphere(M["AD_leaf"],…)` 732/1162/1367行、植栽ループ 1894・1906行、鉢 2112〜2113行 |
| 同 | AD_fern | 9,540 | シダ(扇状の板) | 同 `fern(mat="AD_fern")` |
| 同 | AD_bamboo | 4,824 | 竹の柵 | 同 `bamboo_fence()` 1838行 |
| 同 | AD_pot | 3,000 | 鉢(植木鉢本体) | 同 2112行 |
| tdl_plaza_buildings | PB_pb_trunk / PB_pb_leaf | 2,260 / 880 | ヤシ(幹・葉) | `ds_tdl_plaza_buildings.py` `palm()` 372行、材質 72〜74行、書き出し 477〜478行。`PB_pb_hedge` 24 は植え込み |
| tdl_world_bazaar | WZ_wbz_palm_trunk / _leaf | 2,712 / 1,056 | ヤシ(WB 東出口外ほか) | `ds_tdl_wb_r2.py` `palm()` 88行 → `ds_tdl_plaza_buildings.palm` を呼ぶ。材質 `ds_tdl_world_bazaar.py` 238〜239行 |
| 同 | WZ_wbz_topiary | 22,464 | 丸い刈り込み球・鉢植え(ガス灯の球と同じ `globe_lamp_bm`) | `ds_tdl_wb_r2.py` 85行、`ds_tdl_wb_refine.py` 1265/1553行、材質 `ds_tdl_world_bazaar.py` 234行 |
| 同 | WZ_wbz_leaf | 5,172 | 葉(バルコニー・吊り鉢など) | 材質 `ds_tdl_world_bazaar.py` 187行 |
| 同 | WZ_hedge 12 / WZ_wbz_ts_canopy 168 | | 生け垣の小片 / 日よけ(植物ではない) | |
| tdl_hotel | HO_hotel_leaf | 5,456 | ホテル周りの葉・トピアリー(ミッキー/渦巻き) | `ds_tdl_hotel.py` `mickey_topiary()` 817行・`spiral_topiary()` 826行、材質 78行 |
| tdl_entrance | EN_hedge / EN_hedge_bright | 11,196 / 384 | 刈り込み・生け垣(ミッキー花壇の外周、バルコニーの植栽、トピアリー) | `ds_tdl_entrance.py` 76/104行(材質)、1342行 `ST_Bed_shrubs`、1404行 `ST_Plaza_bed_green`、1548行 `topiary()`、532行 `ST_WB_balcony_planting`、1583〜1622行(鉢・生け垣) |
| tdl_westernland | WL_leaf / WL_fern / WL_grass | 9,530 / 8,168 / 6,535 | 茂み・シダ・草の束 | `ds_tdl_westernland.py` `flower_clump()` 1539行、`fan()` 1547行、`grass_tuft()` 1559行、散布 1613〜1652行 |
| tdl_plaza_hub / stitch / terrace | PH_hedge 224、SE_hedge 120(+SE_planter 130)、TT_hedge 128(+TT_planter 20) | | 生け垣・植木箱 | 各 `ds_tdl_plaza_hub.py` / `ds_tdl_stitch_encounter.py` / `ds_tdl_tomorrowland_terrace.py` |

### 花壇の花・植え込み・芝(ほとんど「地面の色板」)

| モデル | メッシュ | 三角形 | 何か | 作った場所 |
|---|---|---|---|---|
| tdl_entrance | EN_flower_white 12,700 / EN_flowers_red 10,964 / EN_flowers_pink 8,000 / EN_flower_purple 4,400 | 計 36k | ミッキー花壇などの花(粒の集まり) | `ds_tdl_entrance.py` `build_flowerbed()` 1272行ほか |
| 同 | EN_bed_brick 1,152 / _lawn 380 / _lime 660 / _olive 1,640 | | 花壇の色面(レンガ・芝・ライム・オリーブ) | 同 |
| tdl_world_bazaar | WZ_flowers_red 14,784 / _pink 6,084 / WZ_wbz_flowers_yellow 2,160 | | 花 | WB 各ファイル |
| tdl_hotel | HO_hotel_flpink/flpurple/flwhite | | ホテル花壇の花 | `ds_tdl_hotel.py` `flower_bed()` 760行 |
| tdl_plaza_ground | TP_flower 2,092 / TP_soil 897 | | プラザ縁の花の帯/植え込みの土面 | `ds_tdl_plaza_ground.py` 209〜231行 |
| tdl_plaza_hub / stitch / terrace | PH_flower 576、SE_flower 2、TT_flower 4 | | 花 | |
| tdl_adv_ground | AG_bed 2,856 / AG_soil 1,349 / AG_street 462 | | アドベンチャーランドの植え込み面 | `ds_tdl_adventureland.py` 285行(`G.top_surface(AG_bed)`) |
| tdl_west_ground | WG_grass 2,385 / WG_bed 607 / WG_mulch 1,839 / WG_soil 3,517 | | 草地・植え込み・マルチ・土(WG_soil=低木の塊) | `ds_tdl_westernland.py` 280行 |
| tdl_ground / tdl_hotel_ground | TG_soil 365 / TH_soil 263 | | エントランス・ホテルの植え込みの土面 | |
| tdl_land_ground | TL_grass_<land>(計 3,448)/ TL_wood_<land>(計 6,788) | | ランドごとの芝生/樹林帯(地面の色面。wb 337 adv 75 west 182 critter 262 fan 1,125 toon 1,043 tom 424 / 木: wb 806 adv 1,423 west 1,758 critter 522 fan 1,365 toon 498 tom 416) | `ds_ground.py` 65・314行(KINDS、`("TL_grass", grass), ("TL_wood", wood)` をランド別に分割) |
| tds_ground | TL_grass 5,881 | | シー側の草地 | `ds_ground.py` |
| tdl_water / water | WS_grass 2,648 / 1,376、WS_bed 1,646 / 2,517(水底。植物ではない) | | 土手の草地 | `export_models.py` 131〜137行(`mat_bank_grass` → WS_grass) |
| bb_castle / cinderella | BC_grass 24 / CC_grass 348 | | 城前の芝 | `ds_tdl_bb_castle.py` / `ds_tdl_cinderella.py` |
| tracks | TK_canopy 48 | | 線路の屋根(植物ではない、名前だけ) | |

合計(木・ヤシ・茂み・刈り込みの立体のみ。地面の色面と花は除く): 約 **11 万三角形**(AD 約 4.3 万、WZ topiary 2.2 万、EN_hedge 1.1 万、WL 約 2.4 万、HO 5.5 千、WB/PB ヤシ 約 7 千、PZ 4.4 千ほか)。
**木らしい1本ずつの形は、ヤシ(AD_palm*/PB/WZ ヤシ)とプラザの PZ_Trunk/Canopy だけ**。ほかは茂み・球の寄せ集め。植え込みは土面(HEDGE_KEY)をページが刈り込みの塊に持ち上げる。

## 2. mock_template.html の植物まわり(行は 2026-10-05 時点)

| 行 | 何 | 役割 |
|---|---|---|
| 1397〜1700 | `MODEL_MAT`(1396行〜) | メッシュ名の接頭辞→材質(色・粗さ)。植物は `PZ_Trunk 0x4a3828`/`PZ_Canopy 0x3c6a2e flatShading`(1405)、`ST_hedge 0x2d5a26`・`ST_grass`・`ST_flowers_*`・`ST_bed_*`(1423〜1436)、`ST_wbz_topiary/palm_trunk/palm_leaf/leaf`(1458〜1460,1512)、`ST_hotel_leaf`(1528)、`ST_pb_trunk/leaf/hedge`(1541)、`TP_soil/TP_flower`(1561)、`PH_hedge`(1580)、`TT_hedge/flower`(1598)、`SE_hedge`(1606)、`AG_bed/AG_soil`(1626)、`AD_fern/leaf/leafr/bamboo/palmt/palml`(1642〜1655)、`WG_*`(1659〜1663)、`WL_leaf/fern/grass`(1676)、`TL_grass/TL_wood`(1688)、`WS_grass`(1400)。1705行でランド別 `TL_<kind>_<land>` を生成 |
| 2104 | `HEDGE_KEY = /^(TG_soil\|TH_soil\|TP_soil\|AG_soil\|WG_soil\|PZ_Soil)/` | この名前のメッシュを植え込みとして刈り込み塊にする(2205行で判定) |
| 2106〜2156 | `shrubify(T, o)` | 平らな緑の面を 0.4〜0.8 m 持ち上げ、縁を丸め、土まで壁を下ろす。`o.userData.hedge = true` |
| 2158〜2200 | `makeHedge(T)` | 刈り込み用の手続きシェーダー材質(葉の塊・暗い隙間・先端の明るさ・バンプ。1材質を全体で共有) |
| 3161〜3175 | `woods(key, r, gzf)` | 平面図の林ポリゴンに 9 m 間隔の「木の記号」(幹+樹冠の線)を引く。3175 `D.trees`、3301 `DL.trees`。線だけで立体ではない |
| 3411〜3448 | `three.buildTrees` | `trees3d` 1本ごとに InstancedMesh: 幹(6角柱 CylinderGeometry 1本=12三角形)+樹冠2個(IcosahedronGeometry(1,1)=80三角形×2、flatShading、5色からランダム)。`shrubs3d` は Icosahedron(1,2)=320 三角形の球。h=0 は 5〜10 m の乱数。`trees3d` グループが約 61 万三角形・3 メッシュ(3 描画)。4361 行で呼ぶ。`mdl.trees3d` で表示切替 |

## 3. mock_data.json の trees3d / shrubs3d

生成: `src/export_mock.py` 277〜302 行(OSM `natural=tree`、`plateau_data/disneyland_osm.json` と `disneysea_osm.json` の pois、重複除去)、304〜335 行(植え込みの木と低木: 縁が 5 m を超える花壇に木を並べ、両端に低木。高さ `min(9, 4+bw*0.9)`)、340〜353 行(建物の中の木を除く)、356〜357 行(`out["trees3d"]` `out["shrubs3d"]`)。

- **trees3d: 3,220 本**(フラット [x,y,h])。h が分かるのは **150 本のみ**(OSM の height タグ+エントランス周り 10〜14 m の常緑+WB 東出口外 14 m 指定)、**3,070 本は h=0(不明)**。分かる 150 本の高さ: 5.3〜14.0 m、中央値 9.0 m(5〜8 m: 21 本、8〜12 m: 100 本、12 m〜: 29 本)。h=0 は描画時に 5〜10 m の乱数。
- **shrubs3d: 95 個**(半径 0.37〜1.1 m)。70 個がランド内(エントランス広場・ホテル周りの花壇)、25 個は園外側(x -686〜-458, y 873〜1079)。
- エリア別の本数(座標は mock のローカル m。TDL ≒ x<-250、TDS ≒ 公園ポリゴン内 x>-100):
  - TDS 公園ポリゴン内 **715**(OSM。園全体、特にメディテレーニアンハーバー周りの散らばり)
  - TDL 公園ポリゴン内 **705**: アドベンチャーランド 131、ファンタジーランド 124、ワールドバザール 97(うち 37 は高さ指定)、トゥモローランド 87、クリッターカントリー 87、ウエスタンランド 45、トゥーンタウン 20(最寄りのランド名札で分類)、エントランス箱(x -640〜-430, y 800〜990)は 81 本(全部高さ指定 10〜14 m)
  - 公園の外(舞浜周辺・パーキング・道路・ホテル・イクスピアリ側): **1,800**(TDL 西〜南 887 と TDL 外周 475 ほか。見える範囲に入れば歩いて見える木)
  - 高さの分布は上記(OSM の木はほぼ高さ無し。エリア別の実際の樹高は species.md の目安を使う)

## 4. mock_template.html と tds_outline.html の関係

**生成元は `output/disneysea/mock_template.html`(手で編集するのはこちら)で、`tds_outline.html` は生成物**(Vercel が配信する公開ページ)。`python src/export_mock.py`(の末尾 364〜369 行)が `mock_data.json` を作り、そのあとテンプレートの `__DATA__` を `mock_data.json` の中身で置換して `tds_outline.html` に書き出す。テンプレートだけ直しても `tds_outline.html` は変わらないので、必ず export_mock.py を走らせて両方コミットする(perf_check.py も `tds_outline.html` を読む)。
