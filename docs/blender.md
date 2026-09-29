# Blender での作業

## 別の端末で作業する(Blender がある端末など)

1. `git clone` して `pip install -r requirements.txt`(通常の Python 側のみ。Blender のスクリプトは Blender に同梱の Python で動くので不要)。
2. Blender のスクリプトは、コミット済みの JSON・DEM・地球儀テクスチャ・`output/disneysea/models/` だけを使う。元の OSM がなくても動く。
3. 使うコマンド(Blender は 5.2。**同時に 1 つだけ**起動する。複数だと落ちたり止まったりした):

```
blender -b --python src/disneysea_draft.py -- --cams aerial,top --samples 16        # 下書き全体
blender -b --python src/disneysea_water_blender.py -- --cams harbor,caldera         # 水面
blender -b --python src/tdl_water_blender.py -- --cams rivers,moat,jungle,tom        # ランドの水面
blender -b --python src/export_models.py -- --parts water,aquasphere,plaza,volcano  # モック用の 3D モデル
blender -b --python src/export_models.py -- --parts tdl_station,train                # 東京ディズニーランド・ステーションと電車
blender -b --python src/export_models.py -- --parts tdl_entrance                     # 東京ディズニーランドのエントランス
blender -b --python src/export_models.py -- --parts bb_castle                        # 美女と野獣の城
blender -b --python src/export_models.py -- --parts cinderella                       # シンデレラ城
blender -b --python src/ds_tdl_cinderella.py -- --tt 1,13,25,37,49,61 --quick        # シンデレラ城: 参考の 360° 画像と同じ角度のレンダー
blender -b --python src/export_models.py -- --parts tracks                           # 線路(リゾートライン・京葉線)
blender -b --python src/ds_tracks.py -- --samples 24                                 # 線路の確認レンダーと .blend
blender -b --python src/ds_tdl_entrance.py -- --samples 32                           # エントランスの確認レンダーと .blend
blender -b --python src/export_models.py -- --parts tdl_world_bazaar                 # ワールドバザール(通り・お店・店内)
blender -b --python src/ds_tdl_world_bazaar.py -- --cams wbz_street,wbz_shopfront,wbz_inside --samples 32   # 確認レンダーと .blend
blender -b --python src/export_models.py -- --parts tdl_hotel                        # 東京ディズニーランドホテル
blender -b --python src/ds_tdl_hotel.py -- --cams court,gates_wide,aerial --samples 32   # ホテルの確認レンダーと .blend
blender -b --python src/ds_tdl_station.py -- --samples 32                            # 駅の確認レンダーと .blend(電車も停車中)
blender -b --python src/export_models.py -- --parts aquasphere --render             # アクアスフィアの確認レンダー
```

4. モデルを書き出し直したら、`python src/export_mock.py` を実行してからコミットする。`export_mock.py` は新しくなったモデルの Draco 圧縮版を `models/web/` に作る(Node.js の `npx` が要る。無ければそのモデルだけ圧縮前のファイルを読む)。

**Blender で最初にやること(2026-09-24 時点で未実行):**

- [ ] `disneysea_draft.py` で下書きを出し直す。トリトンの屋根(`ds_landmarks.build_triton_dome`、`ds_core.TRITON_ROOF`)を屋内ホールの上(中心 -188, -43、軒 15 m・頂点 27.5 m)に移したが、Blender ではまだ確かめていない。
- [ ] `docs/draft/` の画像を撮り直す。エリアの色分けを 2026-09-24 に直したので、今の画像は古い色分けのまま。
- [ ] ランド・舞浜駅: `blender -b --python src/disneyland_blender.py -- --cams aerial,castle,maihama` を動かす(`ds_disneyland.py` のデータから、建物・水面・緑地・木・線路・京葉線の高架・リゾートラインの桁・舞浜駅周辺の建物を組む)。`python src/disneyland_blender.py --summary` で、Blender なしに中身の数を見られる。
- [x] 東京ディズニーランド・ステーション: `ds_tdl_station.py` で作り、ユーザーが Blender で確認して OK(2026-09-24)。モックに反映済み。
- [x] エントランス: `ds_tdl_entrance.py` で作り、ユーザーが Blender で確認して OK(花壇は 2 回直した: 入場口に向けて傾ける、円形にして真上からミッキーに見えるように)。モックに反映済み(2026-09-24)。
- [x] 電車: `train_blender.py` を v2 に作り込み(外装・台車・車内・ガラス)、モックの電車をこのモデルに差し替えた(2026-09-24)。汚れのベイクは TODO。

座標: 原点 35.6267N 139.8851E(メディテレーニアンハーバー付近)、+X が東、+Y が北、単位はメートル。
高さ: 国土地理院 DEM5A で測った園路の中央値(標高 5.29 m。厳密には 5.285778 m を `datum_exact` に保存)を 0 m とする。ランドも同じ基準。

## Blender で作るときの参考動画(必ず見る)

- **https://www.youtube.com/watch?v=-VIztXefx5Y** — ディズニーランド・ステーション(ディズニーリゾートライン)の 3D モデルを作っている動画。駅・建物などを Blender で作るときは、形の取り方・作る順番・細部の作り込みをこの動画に合わせる。
- **同じ投稿者の、ほかのディズニーパーク関連の動画も、常に参考にする。** Blender で何かを作り始める前に、その投稿者のチャンネルで、作る対象(建物・乗り物・エリアなど)の動画があるかを確かめ、あれば見てから作る。
- 動画を参考にして作ったものは、どの動画のどこを参考にしたかを、そのパーツの説明(`docs/parts.md` や `docs/`)に書く。
- 動画の画像・映像そのものはリポジトリに入れない(見て参考にするだけ)。
