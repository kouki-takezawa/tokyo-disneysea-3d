# 草津 湯畑ジオラマ 参考資料(フェーズ0、2026-10-10)

ルール: 動画・画像は目視参考のみ。テクスチャにしない。フレームと動画は `reference/kusatsu/`(`.gitignore` 対象、リポジトリに入れない)。YouTube Shorts は使わない(下の動画は `/shorts/ID` が `watch?v=ID` に 303 リダイレクトされるのを確認済み=通常動画)。Street View は目視の数枚のみ、大量取得・テクスチャ化はしない。

## 1. 歩き動画(フレーム化済み。3 秒ごと、幅960 px)

保存先: `reference/kusatsu/videos/<ID>.mp4`、`reference/kusatsu/frames/<ID>/f_000001.jpg`(=0 秒、以後3秒ごと)、一覧 `reference/kusatsu/sheets/<ID>/<ID>_HHMMSS.jpg`(6x5、時刻ラベル付き)。作り方は `python tools/kusatsu_frames.py extract` / `sheets`。

| ID | 長さ | チャンネル・題 | 使いどころ(見どころ) |
|---|---|---|---|
| rSRX6OiqD3M | 46:30 | BLA BLA WALKER「[4K] KUSATSU Onsen Hot Spring Walking Tour 草津温泉 温泉街 食べ歩き 散歩」 | 4K 歩き。温泉街全体、湯畑の周回、店並びの正面、看板の実名 |
| 8HhbV3SiG-Q | 21:34 | Walking around Japan「【草津温泉】4K 湯畑と西の河原周辺を散策」 | 湯畑〜西の河原通りの建物の並びと坂 |
| slMuRNf8PKg | 23:08 | 路地ヤロウ「Walking around Yubatake area in Kusatsu … December 2022」 | 湯畑の周回、冬の色(湯けむり多め)、御座之湯・熱乃湯・白旗の湯 |
| 6NnVe-DsYhI | 9:39 | よっしぃ「【草津温泉】湯畑から西の河原通って大露天風呂へ(前編)【4K】」 | 湯畑→西の河原通り(北西)の道沿いの建物 |
| 154mpRTH35s | 34:42 | KIT KIT おいしい旅「【草津温泉】観光＆グルメ完全ガイド 歩いて巡る全45ヵ所」 | 店の正面と看板の実名、旅館の外観(説明テロップ付き) |

URL は `https://www.youtube.com/watch?v=<ID>`。時刻ごとの場所索引は、フレームを目視して `docs/kusatsu/refs/index.md` に作る(フェーズ1以降、必要な範囲から)。

### 次に当たる候補(未取得)

- Um4ItL8x_i4 kankan&kankan「初めて行く人必見 草津温泉の見どころ」(31:08)
- RItmTonCtbM 亀仙人.「西の河原露天風呂 西の河原 湯畑 地蔵の湯 2019」(27:31、範囲外の地蔵の湯含む)
- CEpVb-rQw5o 散歩・旅Senchan「草津西の河原公園を早朝散歩」(12:16、範囲は西の河原公園の外)
- 夜景動画(Va5YxDDSgRU など)は夜景を作らないので使わない。

## 2. 記事・公式ページ(情報の出典)

| URL | 内容 |
|---|---|
| https://tabi-mag.jp/why-yubatake/ , https://www.fun-japan.jp/jp/articles/10824 , https://rurubu.jp/andmore/spot/80008136 | 湯畑: 湯樋7本(幅45 cm・高18 cm・長40 m、岩手産アカマツ、傾斜0.6度)、瓢箪形で60 m x 20 m、毎分約4,000 L |
| https://rurubu.jp/andmore/spot/80008138 | 湯けむり亭: 総檜造りの東屋、江戸期の共同湯「松乃湯」跡 |
| https://news.allabout.co.jp/articles/o/116188/ , https://www.jeepe.jp/ja/articles/kusatsu-gozanoyu-onsen-guide-2440 , https://onsen.nifty.com/kusatsu-gunma-onsen/onsen010699/ | 御座之湯: 2013年再建、杉板のとんとん葺き、漆喰壁、木の湯・石の湯、光泉寺石段の右隣 |
| https://www.nta.co.jp/media/tripa/articles/Ehy8q , https://tabi-mag.jp/gu0060/ | 熱乃湯: 2015年新装、2階建て高天井、大正ロマン、ガス灯、湯もみショー |
| https://www.asahi-net.or.jp/~UE3T-CB/spa/sirohatanoyu/sirohatanoyu.htm , https://news.mynavi.jp/article/20151217-kusatsu/ | 白旗の湯: 1994年建て替え、無料共同湯で最大級 |
| https://www.mapple.net/article/39915/ , https://icotto.jp/presses/21259 | 和風むら加盟宿(山本館・益成屋・奈良屋・草津館・群龍館ほか)、松村屋旅館(木造3階) |
| https://www.mapple.net/region/a0301110401/spot/ , https://www.yukoyuko.net/onsen/spot/s0001631 | 光泉寺: 行基開創と伝わる、石段、本堂・釈迦堂 |
| https://www.kusatsu-onsen.ne.jp/ | 草津温泉観光協会(公式)。足湯・共同湯の詳細ページ(`onsen/detail/index.php?c=5&g=1&kcd=190` など) |
| https://www.geospatial.jp/ckan/dataset/plateau , https://www.mlit.go.jp/plateau/open-data/ | PLATEAU のカタログ。群馬県は前橋市・桐生市・館林市のみで**草津町は無い**(確認日 2026-10-10) |

## 3. 地図・標高データ

- OSM(Overpass): `plateau_data/kusatsu_osm.json`(原点 36.622927, 138.596740、半径260 m、910 要素)。(c) OpenStreetMap contributors, ODbL。
- 国土地理院 DEM5A(標高タイル `dem5a_png` z15): `plateau_data/kusatsu_dem.json`(4 m 格子、±300 m、151x151)。
- 登記所備付地図(法務省)に草津町あり(G空間情報センター `houmusyouchizu-2026-1-521`)。建物の外形精度が必要なら将来使える(未取得)。
