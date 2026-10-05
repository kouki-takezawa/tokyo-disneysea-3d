# 植物をリアルにする計画(2026-10-05)

ユーザー指示(2026-10-05):「草や木など植物がポリゴンっぽいので Three.js でリアルに。造形はそれぞれ違うので使い回しはあまりしない」
→ 提案に対して「CC0 スキャン素材(案②)、スマホでも動くように、範囲は全部」。

## 方針

- **1本ずつ違う形**: 木・ヤシ・刈り込みは位置から決まる乱数の種で個別に生成(枝分かれ・樹冠形・高さ・傾き・葉の垂れ・枯れ葉の数)。同じ形のインスタンスの使い回しはしない。描画数を抑えるため、樹種ごとに結合した BufferGeometry にまとめる。
- **輪郭と光**: 葉は CC0 の葉テクスチャを貼った透過の板(alphaTest + alphaToCoverage)。樹冠は法線を球状に寄せて柔らかい陰影、逆光の透け(簡易透過光)、葉ごと・木ごとの色ゆらぎ、頂点シェーダーで風。
- **素材**: CC0 スキャン素材(ambientCG / Poly Haven など。CC0 のみ、ライセンスを `output/disneysea/tex/plants/LICENSES.md` に記録)。スマホ向けに縮小・アトラス化し、合計を数 MB に抑える。
- **形の生成は Three.js 側に1本化**: Blender 側のヤシ(palm(), palm_tree() など)は「位置・高さ・傾き・種」だけを書き出し、ページで生成する。GLB 内の古い植物メッシュはページで非表示または書き出しから外す。
- **スマホでも動く**: 品質段階(high / mid / low)を端末で自動選択(`?q=` で強制可)。木は 近=全形 / 中=葉板を間引いた同じ木 / 遠=同じ木から作った低解像度版(別の木の使い回しにしない)。生成は Web Worker、視点の近くから順に作る。草の葉は近くだけ(low は半径を縮める)。水の屈折パスには植物を入れない。
- 夜景は作らない。動画フレームはテクスチャにしない・リポジトリに入れない(目視のみ)。YouTube Shorts は使わない。ユーザーの写真(`images/`)を優先。
- 別タブの未コミット変更(`tools/organize_frames.py`、`output/disneysea/models/woody*` など)は勝手にコミット・破棄しない。

## 対象(範囲は全部)

| 種類 | 今の所在 | フェーズ |
|---|---|---|
| OSM の木 約3,200本 | `mock_data.json` の `trees3d`、`three.buildTrees`(mock_template.html) | 1(試作)・2 |
| ヤシ・鉢の木 | `ds_tdl_adventureland.py` palm_tree、`ds_tdl_plaza_buildings.py` palm、`ds_tdl_wb_r2.py` palm、`ds_tdl_world_bazaar.py` 鉢の木 など | 3 |
| 丸い刈り込み・植え込み・トピアリー | `shrubs3d`、`shrubify()`(HEDGE_KEY)、`ds_tdl_entrance.py` topiary、`ds_tdl_hotel.py` mickey/spiral topiary、`*_hedge` 材質 | 4 |
| 芝・草地・草むら・花壇 | `WG_grass` `TL_grass` `WS_grass` `ST_grass` `ST_bed_*` `WL_grass/fern`(grass_tuft)、`*_flower` 材質 | 5 |

正確な一覧はフェーズ0で `inventory.md` に作る。

## フェーズとモデル

| フェーズ | 内容 | モデル |
|---|---|---|
| 0 資料と素材 | 植物の棚卸し(全モデルの植物メッシュ名・材質名・数、データの木の数)を `inventory.md` に。エリアごとの樹種を動画フレーム・写真から同定して `species.md`(樹種・樹高・樹冠形・葉色・季節感、参照フレーム時刻)。CC0 素材(広葉の葉板、針葉、ヤシの葉、樹皮2〜3種、芝、花)を取得し、スマホ向けに縮小して `output/disneysea/tex/plants/` へ。今の性能の基準値(PC とスマホ相当の描画数・三角形・fps)を `tools/perf_check.py` で測る | Sonnet 5.5 |
| 1 基盤と試作 | `plants.js`(または mock_template 内のまとまり):葉の材質(透過・球状法線・透け・風・色ゆらぎ)、木の生成(space colonization、Worker)、距離による段階、品質段階の自動選択。エントランス付近で 広葉樹1種+ヤシ1本+芝 を試作し、フレームと並べて確認 | Opus 5.5 |
| 2 木 全種・全域 | `species.md` の全樹種プリセット、エリアごとの樹種割り当て、`trees3d` 全部を生成。古い `buildTrees` を置き換え | Opus 5.5 |
| 3 ヤシ・鉢の木 | Blender 側のヤシ・鉢の木を仕様の書き出しに変え(GLB から外す)、ページで1本ずつ生成(輪の節、小葉の並んだ葉、垂れ・ねじれ・枯れ葉) | Opus 5.5 |
| 4 刈り込み・植え込み・トピアリー | `shrubify` に葉板を散らして輪郭を崩す、丸い刈り込みを1個ずつ変形、トピアリーに葉の材質 | Opus 5.5 |
| 5 芝・草地・花壇 | 近くは GPU の草の葉(長さ・倒れ・色を場所のノイズで、風)、遠くは地面テクスチャへつなぐ。花壇の花 | Opus 5.5 |
| 6 スマホ調整と全体確認 | スマホ相当(Playwright のモバイル端末エミュレーション+CPU 制限)と PC で計測、段階の距離・密度を調整、全エリアを歩いて確認、README・進み具合、Vercel 確認 | Sonnet 5.5 |

各フェーズ = 1コミット + push + Vercel の status が success。終わったら下の「進み具合」に `済(commit、日付)` と要点を追記。

## 運用

- 1会話 = 1フェーズ。終わったら「/clear してから『植物計画のフェーズN から』」と案内する。
- モデルはサブエージェントの model 指定で切り替える。メインの会話は段取りと確認・報告だけ。
- 確認は数値(描画数・三角形・fps)+散歩画面の縮小スクショ1〜2枚とフレームの比較。大きいファイルは grep で位置を探して部分だけ読む。
- `mock_template.html` を直したら、`tds_outline.html` への反映方法(export_mock.py)に従う。

## 進み具合

- 計画作成: 2026-10-05
- フェーズ0 済(commit、2026-10-05): `inventory.md`(植物は GLB 内で約 11 万三角形、`trees3d` 3,220 本のうち高さ既知 150、`buildTrees` は約 61 万三角形・3 描画)、`species.md`(エリア別の樹種とプリセット案。TDS は動画に写らず未確認)、`baseline.md`(PC/スマホ相当の描画数・三角形・fps。fps は揺れが大きく、描画数・三角形が基準)。CC0 素材(ambientCG、葉の透過アトラス 6・草 2・樹皮 3 色+法線・芝 2、計 3.4 MB)を `output/disneysea/tex/plants/`、出典は `LICENSES.md`。ヤシ専用の葉は無く、小葉 1 枚の透過+手続き生成で代替。`.gitignore` に `tex/` を追加(`output/disneysea/*` が無視していたため)。
