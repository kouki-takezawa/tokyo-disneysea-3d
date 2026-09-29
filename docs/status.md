# 実装状況

| 項目 | 状態 | 主なファイル |
|---|---|---|
| シーの建物 700 棟・エリア 8 つの色分け | 済(高さの大半は推定) | `ds_buildings.py`, `ds_core.py` |
| 地形・緑地・岩場・園路・高架鉄道 | 済 | `ds_terrain.py` |
| 階段・橋・トンネル・壁・地面の高低差 | 済(一部は向きの確認が必要) | `ds_levels.py` |
| 水面(水位・水深・護岸・カルデラ湖) | 済 | `ds_water.py`, `disneysea_water_blender.py` |
| プロメテウス火山の岩山 | 済(Blender で岩肌まで) | `ds_volcano.py`, `ds_volcano_model.py` |
| アクアスフィア(地球儀の噴水) | 済(詳細モデル) | `ds_aquasphere.py` |
| ディズニーシー・プラザ(アクアスフィア周りの地面) | 済 | `ds_plaza.py` |
| 入場口・駅(リゾートライン駅とゲート) | 済(モックのレイヤー) | `ds_core.py` の `entrance_layer()` |
| ディズニーランド(建物 375 棟・7 エリアの色分け・階段・高低差) | 済(モックのレイヤー。高さの大半は推定) | `fetch_disneyland.py`, `ds_disneyland.py` |
| 舞浜駅・周辺(JR・リゾートライン全周・イクスピアリ・ホテル・歩道) | 済(モックのレイヤー) | `ds_disneyland.py` |
| モック(地図・俯瞰・散歩、PC とスマホ) | 済 | `export_mock.py`, `output/disneysea/mock_template.html` |
| Blender で作ったものをモックに 3D モデルとして表示 | 済(水面・アクアスフィア・プラザ・火山) | `export_models.py` |
| 東京ディズニーランド・ステーション(参考動画と同じ作り方。写真・航空写真・OSM の外形から) | 済(Blender で作り、モックの 3D モデルに) | `ds_tdl_station.py` |
| 電車(リゾートライン)の Blender モデル(写真と跨座式モノレールの構造から、外装・台車・車内・ガラスまで) | 済(モックの電車はこのモデル。JS 版は `train.html` だけに残す) | `train_blender.py`, `docs/train/spec.md` |
| リゾートラインの電車をモックで走らせる(2 編成が全周を周回、4 駅で停車) | 済(Blender の車両。地図は印、俯瞰・散歩は 3D。車内はカメラから 150 m 以内だけ) | `output/disneysea/models/train.json`, `mock_template.html` の `RL` |
| 京葉線の電車(E233 系 10 両、上下線、舞浜駅に停車) | 済(モック。舞浜駅の前後 約 790 m だけ) | `mock_template.html` の `MOV` |
| 施設の検索 | 済(モック) | `mock_template.html` |
| 屋根だけの構造物を屋根の板に・樹林を木の記号に | 済(モック。屋根は Blender の下書きも) | `ds_core.py`, `ds_buildings.py`, `mock_template.html` |
| 東京ディズニーランドのエントランス(メインエントランスのゲート・ワールドバザールの入口・ミッキーの花壇。参考動画・写真・OSM から) | 済(Blender で作り、ユーザーの確認後にモックの 3D モデルに) | `ds_tdl_entrance.py` |
| ワールドバザール(入口をユーザーの写真で採寸し直した。ガラス屋根の通り・約 50 軒のお店・歩いて入れる店内) | 済(モックに反映) | `ds_tdl_entrance.py` 1 節, `ds_tdl_world_bazaar.py` |
| 東京ディズニーランドホテル(中庭側を写真から。New Grand Wing と奥の棟は簡略) | 済(モックに反映) | `ds_tdl_hotel.py` |
| モデルの Draco 圧縮(モック用の軽いコピー、約 120 MB → 10 MB) | 済 | `compress_models.py`(`export_mock.py` が呼ぶ) |
| エントランス広場まわりの建物(ゲート外の東西の建物・保安検査の屋根・小さな建物・トイレ・ワールドバザール西の店・モンスターズ・インクの外観) | 済(モックに反映) | `ds_tdl_plaza_buildings.py` |
| モックの見た目(金属やガラスへの空の映り込み、太陽の影。木は置かない) | 済(影はスマホでは切る) | `mock_template.html`, `export_mock.py`(`trees3d`) |
| 東京ディズニーランドのエントランス広場の地面(ゲートの前後の舗装・縁石・植え込み。木は作らない) | 済(Blender なし。純 Python で作り、モックの 3D モデルに) | `ds_tdl_ground.py` |
| 東京ディズニーランドホテル周辺の道(車道・園路・歩行者広場・ホテルと駅の間・駅の中の通路。ホテルの建物の場所は作らない) | 済(Blender なし。純 Python で作り、モックの 3D モデルに) | `ds_tdl_hotel_ground.py` |
| 宣伝用の動画(絵本を開いて中の紙の世界を旅する、約 50 秒・オリジナルの音楽つき。操作画面は映さない) | 済(リポジトリの `promo/` だけ。アプリには含めない) | `promo/promo.html`, `promo/record.py`, `promo/music.py` |
| 地面(ランド全体・シー全体。パークの外は作らない。舗装・道路・駐車場・線路敷・芝・林・岩場・工事中。建物と水面の場所は作らず、建物を抜ける通路は作る。木は作らない) | 済(Blender なし。純 Python で作り、モックの 3D モデルに) | `ds_ground.py` |
| ランドの駐車場(レイヤー「駐車場」。平面 39・立体 3) | 済(モックのレイヤー) | `ds_disneyland.py` |
| 線路(リゾートラインの桁・橋脚・電車線、京葉線の高架・線路・架線・舞浜駅のホーム) | 済(Blender で作り、自分で 3 回見直してからモックに。ユーザーの指示で Blender での確認は省略) | `ds_tracks.py` |
| 美女と野獣の城(橋・門・両翼とドーム・中庭と回廊・大階段・積み重なる本館と円塔・天守・岩場と滝、写真 約 150 枚から) | 済(ユーザーが Blender で確認して OK、モックの 3D モデルに) | `ds_tdl_bb_castle.py` |
| シンデレラ城(ユーザーが選んだ参考モデル TurboSquid 1439041 の 360° 画像 72 枚と静止画 39 枚から、同じ形に) | 済(ユーザーが Blender で確認して OK、モックの 3D モデルに) | `ds_tdl_cinderella.py` |
| ランドの水面(水域 35 か所の水位・水深・岸の種類。アメリカ河・ジャングルクルーズの川・シンデレラ城の堀。シーと同じ作り方) | 済(ユーザーが Blender で確認して OK、モックの 3D モデルに) | `ds_tdl_water.py`, `tdl_water_blender.py` |
| 空(昼 12:00 固定。太陽の向きは日付と舞浜の緯度経度から計算。空のドーム・太陽の光・水面の映り。夜や時刻の切り替えは無効にした) | 済(モック) | `mock_template.html` の `SKY_KEYS`, `skyCalc()`, `applySky()` |
| 地面のレンガ調(ランド・シーの舗装と地面に、目地つきの running bond のレンガ模様。各ランドの地面色が下地。遠くと斜めから見たときは平均色に切り替えてちらつきを抑える) | 済(モック。UV 不要のシェーダー) | `mock_template.html` の `brickify()`, `BRICK_KEY` |
| 優先パーツの作り込み(ミラコスタ、コロンビア号、シンデレラ城など) | これから | — |
| ランド・舞浜駅を Blender のシーンに入れる | スクリプトは済(Blender では未実行) | `disneyland_blender.py` |
