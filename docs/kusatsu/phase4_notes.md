# 草津計画 フェーズ4 メモ(建物の共通部品、2026-10-10)

## 作ったファイル

| パス | 内容 |
|---|---|
| `kusatsu/kd_parts.py`(新規) | 部品ライブラリ。`BuildingSpec` などの仕様と `build_building(spec, field)`。幾何は numpy/python だけ(Blender 無しでも三角形数を数えられる)、`PB.to_objects()` だけ bpy |
| `kusatsu/kd_parts_test.py`(新規) | 試作 5 棟の spec(`proto_specs()`)と実行。`--count` で Blender 無しの三角形数 |
| `kusatsu/kd_buildings.py`(変更) | `build_boxes(…, zones, skip)` を分離。`build_buildings()` は「区域に spec があれば本物、無ければ仮の箱」 |
| `kusatsu/kd_terrain.py`(変更) | 建物の書き出しが区域ごとのオブジェクトのリスト(箱+材質別の本物)に対応。本物があれば位置 16 bit |
| `kusatsu-diorama/app.js`, `index.html` | モデルのキャッシュ既定 `?v=4`、`app.js?v=8` |
| `kusatsu-diorama/models/buildings_A..D.glb` | 試作 5 棟入り(残りは仮の箱) |
| `output/kusatsu/` | `kusatsu_parts_test.blend`、`parts_test_stats.json`(1 棟ごとの数値・看板の面)、`run_parts.log`、確認スクショ `p4_*.jpg` |

## 実行

```
tasklist | grep -i blender      # 他タブの Blender が無いこと(1 つずつ)
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python kusatsu/kd_parts_test.py  > output/kusatsu/run_parts.log 2>&1   # 約 4 秒、区域 4 つの glb
   オプション: -- --only=AC(区域を絞る) --lod=0(全部を遠景の品質に) --out-web=DIR
python kusatsu/kd_parts_test.py --count       # Blender 無しで 1 棟ごとの三角形数(材質別)
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python kusatsu/kd_terrain.py   # 地形+建物全部(kd_parts の spec を自動で使う)
python -m http.server 8793 --bind 127.0.0.1   # http://127.0.0.1:8793/kusatsu-diorama/?shot&q=standard
```
確認のコツ: 仮の箱が視点をふさぐので、`__v.scene.traverse(o => { if (/^Buildings_/.test(o.name)) o.visible = false })` で箱だけ隠す。Blender (x,y,z) → Three (x, z, -y)。

## 部品一覧(kd_parts.py)

| 種類 | 関数・仕様 | 中身 |
|---|---|---|
| 屋根 | `Roof(kind=…)` → `roof_gable / roof_hip / roof_irimoya / roof_shed / roof_flat`、`hogyo` は `roof_hip(hogyo=True)` | 切妻(軒の出・けらば・破風板・鼻隠し・棟・鬼瓦・降り棟・懸魚)、寄棟(隅棟)、入母屋(寄棟部の高さ割合 `irimoya_k`、妻壁は漆喰/真壁/木連格子、妻の出)、宝形(宝珠)、片流れ、陸屋根(パラペット・笠木・塔屋)。茅(`mat='kaya'`)は厚み 0.6 m・軒先の丸い小口・棟の押さえと烏おどし |
| 千鳥破風 | `Roof.chidori=[(位置 -1..1, 幅, ±1)]` | 屋根面に載る三角の破風(小窓・破風板・懸魚・棟) |
| 屋根材 | `roof_plane(pts, kind, …)` | 瓦(段の色むら+lod2 は段の小口、丸瓦の筋 0.30/0.36 m)、`metal`(縦ハゼ 0.45 m)、`teppan`(瓦棒 0.42 m)、`tonton`(杉板の段 0.2 m)、`kaya`(段 0.36 m) |
| 壁 | `WallFinish(kind, color, pitch, timber, koshi)` | plaster/mortar/spray/paint(平滑)、board_h(下見板の段)、board_v(縦板+押縁)、tile(目地。lod2 は 1 枚ずつ)、stone(切石を 1 個ずつ出す)、stone_round(玉石のふくらみ)、louver(縦格子張り)。`koshi=(高さ, kind, 色)` で腰壁+見切り |
| 化粧柱・梁 | `Timber(color, w, proud, posts, beams, braces)` | 柱(柱間ごと/間隔)、胴差・桁・長押(開口の上)・窓台、筋交い(開口の無い柱間)。開口を避けて分割。妻壁にも束と梁 |
| 開口 | `Facade.pattern` の文字(下表) | 全部に見込み(壁厚 `rev`、店先は 0.7 m)。窓枠・方立・中桟・水切り・額縁 |
| 出入り | `setbacks={階: {辺: m}}` | 内へ=段状のテラス(床・スラブの小口・手すり)、負=張り出し(下面・持ち送り) |
| 庇・下屋 | `Pent(floor, side, depth, slope, mat, z)` | 屋根材の割り・鼻隠し・瓦の軒先・端板・水切り・持ち送り(腕木+方杖)、`rafters=True` で垂木、`side='all'` で全周 |
| バルコニー | `Balcony(floor, side, depth, z, rail, extend, gap)` | 床板・手すり(wood 縦子/lattice/steel ステンレス 3 段/wall 腰壁/glass)、持ち送り、`extend` で角を回す縁側、`gap` で階段の切れ目 |
| 付属物 | `Attach(kind=…)` | `ac` 室外機(格子の丸・配管・壁付けの腕)、`pipe`、`sign`(yoko/flat/tate 突き出し/roof/hang、**枠と無地の板だけ**。面の中心・法線は `signs` に記録)、`lanterns` 提灯の列、`nobori` 幟(竿+静止した旗、両面)、`chimney`、`tank`、`tent`(庇テント・縞)、`stair` 外階段、`steps` 石段、`noren`、`crest` 紋、`box`、`porch`(玄関ポーチ・向拝。屋根 gable/shed/kara=唐破風、石の基壇と段、礎石、虹梁、暖簾・提灯)、`cupola` 越屋根・小塔(ルーバー) |
| 雨樋 | `Roof.gutters` / `Pent.gutter` | 軒樋+鶴首+縦樋(地面まで) |
| 材質 | `MATERIALS`(`kusatsu_wall/wood/paint/roof/metal/stone/glass/dark/fabric/thatch`) | 頂点色(Col)を Base Color に。粗さ・金属度は材質ごと。色は `PAL` |
| 経年 | `BuildingSpec.age`(0..1)→ `weather()` | 頂点色に足元の汚れ(高さ 0.9 m で減衰)・縦の雨だれ(縦長のノイズ)・大きな色むら。材質ごとの効き(壁 1.0、木 0.7、石 0.8、ガラス 0) |

開口の文字(1 文字=1 柱間、`R/S/H/P` は続けると 1 つの開口): `W` 窓(引き違い)、`w` 小窓、`T` 縦長窓(欄間の桟)、`L` 格子窓、`R` 連窓、`A` 半円アーチ窓、`K` 花頭窓、`D` 格子戸(引き戸 2〜4 枚)、`G` ガラス戸、`P` 板戸(上に格子の欄間)、`S` 店先(奥の暗がり+陳列台+暖簾)、`H` シャッター(ケース・ガイド・閉じ具合)、`.` 壁。`win`/`ground` に複数文字を入れると模様として繰り返す(例 `'.L.'`)。大きさは `SIZES` を `Facade.sizes` で上書き。

### BuildingSpec のフィールド

| フィールド | 既定 | 意味 |
|---|---|---|
| `id` | 必須 | OSM の id(`buildings_index.json` と同じ。relation は `r<id>_<k>`) |
| `name`, `zone`, `note` | | 名前・区域(A〜D)・メモ |
| `ring` | None | 外形(Blender x,y)。None なら OSM。向拝の張り出しを外すなど自分で直すときに渡す |
| `floors`, `floor_h` | 2, 3.0 | 階数、階高(数値か階ごとのリスト) |
| `found`, `found_h`, `found_col` | concrete, 0.3 | 基礎(concrete/stone/stone_round/none)。基礎の天端=1 階の床=敷地+`found_h`。下端は周り 1 m の地面の最低-0.25。石は上から `found_h+0.35` だけ積み、深い所はコンクリート |
| `base_z` | None | 1 階の床の Z を直接指定 |
| `front` | None | 正面の方位(真北から時計回りの度、または `'ENE'`)。None=最長辺 |
| `walls` | `{'*': WallFinish()}` | 階ごとの壁(`{1: …, '*': …}`) |
| `side_walls` | {} | 辺ごとの上書き `{'front': {1: …}}` |
| `facades` | `{'*': Facade()}` | 辺ごとの窓割り。キーは 辺番号 → 8 方位('NW') → 'front/back/left/right'(正面に向かって左右)→ '*' の順に探す |
| `setbacks` | {} | `{階: {辺: m}}`(その階から上。正=内へ、負=張り出し) |
| `terrace_rail` | 'wall' | セットバックのテラスの手すり |
| `balconies`, `pents`, `attach` | [] | 上の表 |
| `roof` | `Roof()` | 屋根(棟の向き `axis`='long'/'short'/方位、`eave`, `verge`, `slope`, `kengyo`, `chidori`, `parapet`, `penthouse` …) |
| `wings` | [] | 別棟の BuildingSpec(`same_level=True` なら床の高さを親に合わせる)。lod は棟ごと |
| `use_obb` | False | 外形を最小回転矩形にする(OSM の外形がギザギザのとき) |
| `lod` | 1 | 0=遠景(開口は面だけ・屋根の割り・付属の細部なし)、1=標準(小口を省く)、2=主役(垂木・細かい格子・石 1 個ずつ・瓦の段)。`Facade.lod` で面ごとに上限(裏側を軽く) |
| `age`, `seed` | 0.4 | 経年、乱数の種(既定は id の crc32) |
| `replaces` | None | 消す仮の箱の id(既定 [id]) |

屋根は最上階の外形の**最小回転矩形**に載る(L 字などは `wings` で分ける)。切妻・片流れは最上階の壁を屋根の下まで伸ばす(妻壁、`Roof.gable_window` で小窓)。

## 試作 5 棟の数値(三角形、`--count` と Blender の書き出し)

| 建物 | id | lod0 | lod1 | lod2(使用) | 主な部品 |
|---|---|---|---|---|---|
| ちちや | 605309932 | 552 | 6,016 | **8,713** | 切妻・妻入り(北西)、漆喰+化粧柱梁+筋交い、2 階格子窓、1 階店先+暖簾、瓦の下屋、赤提灯 9、看板枠 3、紋、懸魚 |
| 大東館 本館+西棟 | r12857070_1 | 6,378 | 9,796 | 9,796(本館 lod0+西棟 lod1) | 西棟 5 階の段状セットバック+腰壁の手すり、縦フィン、陸屋根・塔屋 |
| 大東館 1 階の飲食店 | r12857070_0 | 479 | **2,409** | 2,409 | 黒い縦板、店先+暖簾、瓦の下屋、白提灯 8、看板枠、屋上のボンベ 3 |
| 御座之湯 | 954786837 | 1,031 | 13,089 | **21,056** | 入母屋とんとん葺き、2 階の連窓が張り出し(持ち送り)、1 階の下屋、杉板(縦/下見板)、切妻の玄関ポーチ+白い暖簾+提灯 |
| 山本館 | 948490088 | 1,921 | 22,741 | **31,185** | 入母屋+千鳥破風 2、黒柱白壁、各階の庇 2 段、2・3 階の木の手すり、切石の基礎、唐破風の玄関(朱茶の柱) |
| 光泉寺 本堂 | 1311927446 | 2,052 | 8,950 | **12,584** | 入母屋の金属板(縦ハゼ)、朱の柱・長押+白壁、花頭窓・連子窓・板戸+欄間、縁+ステンレスの手すり(階段で切れる)、朱の垂木、向拝、石段 5 段 |

- 区域別 glb(箱+本物): A 223 KB / 26,071、B 186 KB / 23,461、C 278 KB / 34,834、D 113 KB / 13,622。建物 合計 約 98k 三角形、800 KB。ジオラマ全体 約 294k(地形 97k+湯畑 99k+建物 98k)。描画 23 回(材質別に区域ごと最大 10 オブジェクト)。
- 書き出しは約 4 秒(5 棟)。1 棟の幾何は 0.01〜0.4 秒。
- 予算の目安: 標準(lod1)の 2〜3 階の店 3〜8k、大きな旅館 13〜23k。主役(lod2)は 1.5 倍前後。全 247 棟を lod1 中心で作ると 1.0〜1.3M に収まる見込み(主役 20 棟 lod2・その他 lod1・遠い奥の旅館は lod0)。

## 写真との見比べ(縮小スクショ `output/kusatsu/p4_*.jpg`)

- ちちや(R f_000057 / S f_000052): 妻の白漆喰と濃茶の柱梁・筋交い、2 階の格子窓 2 連、「ちちや」の白い看板の枠、頂部の丸い紋、黒い破風、1 階の濃茶と瓦の庇の赤提灯が同じ並び。妻入りの向き(北西=湯畑側)はカードの「正面 西南西」と違うが、S 2:33・S 6:27 で妻面が湯畑・南の交差点側に見えるので妻入りにした。差: 実物は 1 階の店内が明るく商品が見える(こちらは暗がり+陳列台)、暖簾の白い文字なし、縦看板の文字なし。
- 山本館(R f_000587): 3 段の軒線(庇 2 段+屋根)、窓前の木の手すり、黒い柱と白壁の割り、切石の基礎、入母屋と千鳥破風、唐破風が合う。差: 実物の 2・3 階の窓は障子とガラスの細かい割り(こちらは 2 枚の引き違い)、庇の持ち送りの繰形は四角い材、唐破風の彫刻は懸魚型の板だけ。OSM の外形の凹み(角の段)で庇と手すりが途切れる所がある。
- 光泉寺 本堂(R f_000460): 花頭窓・連子窓・中央の板戸と格子の欄間、朱の柱と長押、白壁、縁のステンレス手すり(階段の上で切れる)、石段 5 段、朱の垂木が合う。差: 向拝の屋根は実物より薄く見える(人の目の高さだとよく見える)、組物(出三斗・蟇股)は角材の束 1 つ、扁額は無地の板、賽銭箱・香炉・吊りの鉦なし(フェーズ8/9 の小物)。屋根の色は明るい灰で合わせた。
- 御座之湯(Y f_000049 / R f_000408): 橙茶の杉板、2 階の連続ガラス窓(張り出しと持ち送り)、1 階の灰褐色の下屋、白い暖簾と提灯の玄関ポーチ、入母屋のとんとん葺きが合う。差: 実物の 2 階のガラスは空を写して明るい青(環境マップが無いので暗めの青灰)、妻の白漆喰の割り・小窓は推定、とんとん葺きの段は遠目で細かい縞(モアレ)が出やすい(段の小口の色を薄めて軽減)。
- 大東館(S f_000104): 西棟の段状に下がる白いバルコニー、黒い 1 階の店の白提灯の列と瓦の庇、屋上のボンベが合う。差: 本館は遠景の品質(窓は面だけ)、実物の各窓のバルコニーの凹みと室外機は省略、緑の縦書きの文字なし(看板枠だけ)。OSM の relation の外形をそのまま 8 階にしているので、本館の形・高さは推定。

## 落とし穴

- `C.srgb()` は `#rrggbb` の 6 桁だけ(`#333` は不可)。
- 細い部材は面数が効く。`Builder.sk('v'|'h'|'b')` で見えない小口を省く(lod1 は縦材の上下・横材の左右も省く)。格子・手すり子は両面の 2 枚。
- `Wall.beam` の既定は全面(持ち送りなど壁から離れる材は下面も見える)。壁に貼り付く材だけ `skip=('-z',)`。
- 斜面の建物は基礎が 4〜5 m になる(山本館・御座之湯の裏)。石を全部積むと 1 棟 5k 増えるので、石は上から `found_h+0.35` だけ、下はコンクリートの面。
- 位置の量子化 14 bit(区域の大きさで約 1.2 cm)だと 2〜3 cm の部材が崩れる → 本物を含む区域は 16 bit。
- 屋根は最小回転矩形に載るので、凹んだ外形(L 字・コの字)では空中に張り出す。`wings` で分けるか `ring` を直す。入母屋の妻壁・千鳥破風の色は最上階の `walls` の色(`Roof.gable_col` で上書き)。
- `Balcony.s0/s1` の負の値は「終点から」の意味。角を回すときは `extend`。
- `Attach.side` は「その向きの最長の辺」に付く。`s` は辺の始点(正面に向かって左)からの m、`at` は割合。
- 経年は頂点色に掛けるので、面が大きいと色むらはなめらか(細かい汚れは出ない)。ガラス・暗がりには掛けない。
- 看板の文字はまだ無い。`Built.signs`(`parts_test_stats.json` の `signs`)に板の中心・法線・右・幅・高さ・`text` があるので、フェーズ9 はここに文字の面を貼る。

## フェーズ5〜8 で区域のスクリプトを並列に書くときの注意

- ファイル名は **`kusatsu/kd_zone_<A|B|C|D>.py`**(1 区域 1 ファイル。さらに分けるときは `kd_zone_A_east.py` などに spec 関数を書き、`kd_zone_A.py` の `specs()` で集める)。`kd_parts.py` は共有ライブラリなので、区域の作業中に直すのは 1 人だけ(足りない部品は区域のファイル内で関数を書き、後でまとめて移す)。
- `kd_zone_<Z>.py` に `specs()` があれば、`kd_terrain.py` と `kd_parts.run_zone()` がそれを使う(試作 5 棟は `kd_parts_test.proto_specs()` からの仮の取り込みなので、区域ファイルを作ったら**その区域の試作 spec をコピーして入れる**こと。入れないと試作が消えて箱に戻る)。
- Blender の実行は 1 つずつ(tasklist で確認)。スクリプト作り・資料読みは並列で可。
- 書き方の例:

```python
# kusatsu/kd_zone_A.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_parts as P
from kd_parts import BuildingSpec, WallFinish, Timber, Facade, Balcony, Pent, Roof, Attach

def honda():   # おみやげの本多(A_honda、S 6:30)
    return BuildingSpec(
        id='605085501', name='おみやげの本多', zone='A', floors=3, floor_h=[3.4, 3.0, 2.8], front='WSW',
        walls={1: WallFinish('board_v', '#4a3326'), '*': WallFinish('plaster', timber=Timber('#2b2420', braces=True))},
        facades={'front': Facade(pattern={1: 'SSSS', 2: 'LWWL'}, frame='wood', noren='#273149'), '*': Facade(win='W.', lod=1)},
        pents=[Pent(1, 'front', depth=0.9)],
        roof=Roof('gable', 'kawara', slope=0.55, kengyo=True),
        attach=[Attach('sign', side='front', floor=2, z=2.4, w=3.0, h=0.7, text='おみやげの本多')],
        lod=2)

def specs():
    import kd_parts_test as T
    return [T.chichiya(), *T.daitokan(), honda()]     # 試作を引き継ぐ

if __name__ == '__main__':
    P.run_zone('A')      # 箱(残り)+本物 → kusatsu-diorama/models/buildings_A.glb、数値 output/kusatsu/parts_A.json
```

- 動画で確認できない約 150 棟は、区域ごとに「様式の型」(例: 白漆喰+濃茶の化粧柱梁の 2 階切妻、黒い縦板張り、白い吹付+横窓の陸屋根)を関数にして、`buildings_index.json` の id・階数・面積から spec を量産する(lod1、裏側は `Facade.lod=0`)。
- 品質の目安: 主役(カードあり・道に面す)lod2、その他 lod1、奥・裏側は lod0 か `Facade.lod`。区域ごとに `python kusatsu/kd_zone_A.py` 相当の `--count` を作って三角形を確認してから Blender を回す。

## 未対応

- 唐破風の彫刻・組物(出三斗・蟇股)・持ち送りの繰形は簡略形(板・角材)。瓦は桟瓦と本瓦を区別していない。
- 曲線の屋根(反り・起り)なし。軒先は直線。
- 看板の文字面(フェーズ9)。ガラスの映り込み(環境マップはフェーズ11)。店内の明るさ・商品。
- 遠景用の別 glb(間引き)は作っていない(`--lod=0` で全部を遠景の品質にした glb は作れる)。
- 試作以外の約 240 棟は仮の箱のまま。大東館の本館・山本館の別棟(954629633)は形が推定/未作成。
