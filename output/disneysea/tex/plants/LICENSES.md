# 植物テクスチャの出典とライセンス

すべて ambientCG(https://ambientcg.com)の素材で、**CC0 1.0 Universal**(パブリックドメイン相当、帰属表示不要)。
確認: 各アセットのページ(https://ambientcg.com/a/<ID>)と https://docs.ambientcg.com/license/ に
"All ambientCG assets are provided under the Creative Commons CC0 1.0 Universal License" とある(2026-10-05 確認)。
元の zip(1K-JPG)はリポジトリに入れていない。加工は Pillow での縮小・色+不透明度の合成・PNG 256色化・WebP 化のみ。

| ファイル(.png/.webp = 透過、.jpg/.webp = 不透明) | 出典 URL | アセット ID | ライセンス | 加工 | 用途の想定 |
|---|---|---|---|---|---|
| leaf_evergreen_oval | https://ambientcg.com/a/LeafSet022 | LeafSet022 | CC0 | 1024px、Color+Opacity→RGBA | 濃い常緑広葉(クスノキ類) |
| leaf_evergreen_round | https://ambientcg.com/a/LeafSet024 | LeafSet024 | CC0 | 同上 | 濃い常緑広葉(丸葉・低木の刈り込み) |
| leaf_deciduous_light | https://ambientcg.com/a/LeafSet014 | LeafSet014 | CC0 | 同上 | 明るい落葉広葉(ケヤキ類) |
| conifer_sprig | https://ambientcg.com/a/LeafSet019 | LeafSet019 | CC0 | 同上 | 針葉樹の枝葉(ヒマラヤスギ・モミ) |
| pine_needles | https://ambientcg.com/a/PineNeedles001 | PineNeedles001 | CC0 | 同上 | マツの針葉(色は茶色寄り、シェーダーで緑に染める) |
| leaf_narrow_palm | https://ambientcg.com/a/LeafSet013 | LeafSet013 | CC0 | 1024x512 | ヤシの小葉(細長い1枚ずつ。ヤシの専用素材は ambientCG に無い) |
| grass_blades / grass_blades2 | https://ambientcg.com/a/Foliage001 , https://ambientcg.com/a/Foliage006 | Foliage001, Foliage006 | CC0 | 1024px、RGBA | 草の葉(一枚板に貼って草むらに) |
| bark_grey_color/normal | https://ambientcg.com/a/Bark001 | Bark001 | CC0 | 512px、NormalGL | 広葉樹の幹 |
| bark_pine_red_color/normal | https://ambientcg.com/a/Bark014 | Bark014 | CC0 | 512px、NormalGL | マツ・ヒマラヤスギの幹(赤茶) |
| bark_palm_brown_color/normal | https://ambientcg.com/a/Bark012 | Bark012 | CC0 | 512px、NormalGL | ヤシの幹(縦繊維。輪の節はシェーダー側で足す) |
| lawn_bright_color/normal | https://ambientcg.com/a/Grass005 | Grass005 | CC0 | 512px、NormalGL | 芝の地面 |
| meadow_rough_color/normal | https://ambientcg.com/a/Grass004 | Grass004 | CC0 | 512px、NormalGL | 荒れた草地(ウエスタンランド・クリッターカントリー) |

形式: 透過のものは .png(256色)と .webp、不透明のものは .jpg と .webp。法線は OpenGL 規約(Three.js の normalMap はそのまま)。

## 派生ファイル(フェーズ1、2026-10-05)

`tools/make_leaf_atlases.py`(Pillow)が上の CC0 の WebP(8bit の透過。256 色 PNG は使わない)から作る。ライセンスは元と同じ CC0。

| ファイル | 元 | 内容 |
|---|---|---|
| leaves_near.webp(2048²)/ leaves_far.webp(1024²) | 行ごとに LeafSet022(常緑広葉)・LeafSet014(落葉広葉)・PineNeedles001(マツ、緑に染めた針葉の束)・LeafSet019(針葉樹の小枝) | 4×4 のアトラス(1 行 = 1 種類 × 4 枚)。近: 小枝に葉を並べた房 / マツは枝先の針葉のブラシ / モミ・ヒノキは扇に開いた小枝。遠(中景・遠景用): 房を丸く(マツは平たく)積んだ塊。フェーズ2(2026-10-05)で、フェーズ1の種類別 2×2(cluster_*.webp)を置き換え |
| bark_atlas_color.webp / _normal.webp | Bark001 / Bark014 | 1024×512: 灰色の樹皮(広葉樹)と赤茶の樹皮(マツ・針葉樹)を左右に並べた(全種類で 1 つの材質にするため) |
| palm_frond.webp | LeafSet013(leaf_narrow_palm) | 小葉を中軸の両側に並べた羽状のヤシの葉 1 枚(下が付け根) |

透明部分の色は近くの葉の色で埋めてある(ミップマップで縁が黒・白にならないように)。
